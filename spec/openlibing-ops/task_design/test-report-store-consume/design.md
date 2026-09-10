# 测试报告持久化存储与消费 设计文档

> 关联需求：https://gitcode.com/openlibing/openlibing-ops/issues/123
> 版本：v3.1（2026-09-09，v3 基础上补充**流水线重试判定**：raw/sdi 表各加 `source_end_time` 列，两段反查改为「未处理 OR 源表 end_time 更新」时间比较，解决三平台重试后三 ID 不变导致的漏扫）
> 版本：v3（2026-09-08，采集改为 **raw→sdi 两段式**：先入 `raw_test_report` 原始 JSON，再清洗成每模板一张 sdi 表）
> 目标仓：`openlibing-ops`（REST + MCP 消费）、SeaTunnel 插件工程（raw 采集轻量 transform，仓待确认）、openlibing-docs（DS 工作流定义/SQL 归档）
> 数据底座：Doris（raw 层 + sdi 清洗层 + Doris 模板登记表）

---

## 1. 需求概述

为平台新增「测试报告上报」能力：

- **测试报告** = 多种模板的结构化测试数据，**一个模板对应一张数据库表**；**一条数据 = 一条测试任务 + 执行结果**（明细事实，非文档）。
- 业务（测试）团队把**按约定 schema 解析好的规范 JSON 文件**放到华为云 OBS 桶（产出侧解析归测试团队，平台不介入）。
- 平台侧从 OBS 拉取 JSON → **原始 JSON 整份落 raw 层 → 清洗成 sdi 层**（入库侧归平台，仿既有 raw→sdi 链路）。
- 平台提供 **REST API + MCP** 两种消费能力（MCP 为平台首次建设，POC 已验证）。

## 2. 职责边界（PM 对齐后调整）

| 环节 | 责任方 | 说明 |
| --- | --- | --- |
| 原始测试结果 → 规范 JSON | 测试团队（上游） | 按约定 schema 产出，放 OBS 桶；平台仅需 OBS 只读凭证 |
| OBS 拉 JSON → 写 raw 层 | **DolphinScheduler + SeaTunnel** | 工作流①「测试报告原始数据采集」：轻量 `TestReportReader` transform（复用 `ParseTestcase` 的 OBS 读取）读 OBS → 原始 JSON 整份入 `raw_test_report`（仿 `raw_workflow_source_github`）；**不再使用 xxl-job 中间件** |
| raw → sdi 清洗 | **DolphinScheduler + SeaTunnel** | 工作流②「测试报告数据清洗」：`JsonArrayExpand` + `Sql` 纯配置展开（参考既有 testcase raw→sdi 清洗），每模板一张 `sdi_rd_efc_test_report_<模板名>` |
| metadata xml 解析（repo_url/起止时间） | **既有链路已覆盖** | DS 正式环境已有 SeaTunnel 任务解析存储，归属字段从现有表 JOIN 补齐，不重复建设 |
| REST 查询 | openlibing-ops | 模板元数据 + 数据查询（读 sdi 表） |
| MCP 消费 | openlibing-ops（内嵌 MCP Server） | AI 客户端只读查询（读 sdi 表） |
| 不参与 | openlibing-sync | 采集迁出 sync（不新增 @XxlJob、不扩展 ObsUtilClient）；openlibing-metric 仅 POC 验证 MCP 机制 |

## 3. 总体链路

```text
测试团队脚本 → 规范JSON(外层数组,内层字典) → OBS 私有桶 op-case-result
   testcase-metadata/{pipeline_id}/{pipeline_run_id}/{job_id}/
   ├── metadata*.xml        ← 既有链路已解析（repoUrl 等），本需求不重复解析
   ├── result*.xml          ← 既有链路已解析
   └── <模板名kebab>_xxx.json   ← 测试报告 JSON（本需求采集对象）

DolphinScheduler 工作流①「测试报告原始数据采集」（cron 每小时，正式/测试 openlibing 项目）
   └─ SeaTunnel 任务（参照 [job][raw->sdi][codearts]获取测试用例数据 的 rawScript 模式）
        source: Jdbc(Doris) 待采集流水线记录（模板范围 + 已采集过滤 + 归属字段）
        transform: TestReportReader（轻量 OBS 读取，复用 ParseTestcase 代码，仅读原文不做展开）
                   → 读 OBS testcase-metadata/{p}/{r}/{j}/<模板名>_xxx.json
                   → 输出 原始 JSON 整份 + 上下文（pipeline_id/pipeline_run_id/job_id/report_file_name）
        sink: Jdbc(Doris) INSERT raw_test_report
        ▼
Doris raw_test_report（原始 JSON 整份落库，仿 raw_workflow_source_github 模式）

DolphinScheduler 工作流②「测试报告数据清洗」（cron 每小时）
   └─ SeaTunnel 任务（参照既有 raw→sdi 清洗：JsonArrayExpand + Sql 纯配置）
        source: Jdbc(Doris) 读 raw_test_report 未清洗行（时间窗口 + 已清洗过滤）
        transform: JsonArrayExpand（展开外层数组带 record_seq）→ Sql（归属字段提取）
        sink: Jdbc(Doris) INSERT sdi_rd_efc_test_report_<模板名>
        ▼
Doris sdi_rd_efc_test_report_triton_model_performance（UNIQUE KEY 兜底行级去重）
        ▼
ops  ReportController(/report/*) + 内嵌 MCP Server(/mcp) —— 共用 ReportQueryService，读 sdi 表
```

## 4. 复用的既有机制

### 4.1 模板登记机制（Doris 专用登记表 `dm_rd_efc_template_registry`，替代 MySQL 表）

模板→表映射机制复用 sync thirdapi 模块的登记思路（`model_code → table_name + status`），但**登记表改为 Doris 专用表**（不复用 MySQL `tbl_third_api_data_model`，原因见 6.1/R6）：

| 复用点 | 说明 |
| --- | --- |
| 模板→表映射 | 每模板登记一行：`table_type=test_report`，`model_code=模板名`（snake，=JSON schema title），`table_name=sdi_rd_efc_test_report_<模板名>`（数据中台统一 rd_efc 中缀，指向 sdi 清洗表） |
| 采集范围 | **`pipeline_ids` 列**（逗号分隔，**一个模板可对应多条流水线，一对多**）；为空则该模板不参与采集 |
| ops 查询 | 模板列表/字段元数据、`/report/data/query` 的模板定位 |

> 采集入库不再经过 sync 的 `DynamicDorisService`（迁至 SeaTunnel 直写 Doris）；但「列白名单 + 必填校验」思路保留在 ops 查询侧（动态 WHERE 白名单）与 SeaTunnel 插件侧（按目标表列白名单过滤）。

### 4.2 既有 SeaTunnel 采集链路（PM 确认：metadata.xml 已有解析存储）

DS 正式环境已存在完整测试数据采集链路（测试环境 `sdi_rd_efc_test_case_result_raw_codearts` 已有千万级数据）：

| 资产 | 说明 |
| --- | --- |
| 工作流 `[job][raw->sdi][codearts]获取测试用例数据`（code 169496639378624） | SeaTunnel 任务（自定义 `ParseTestcase` transform 直连 OBS `op-case-result` 桶 + `TestcaseResultParser` + `JsonPath`）→ 写 `sdi_rd_efc_test_case_result_raw_codearts/gitcode/github` |
| 已采集增量表 `sdi_rd_efc_pipeline_run_collected_testcase_codearts` | raw→sdi 工作流用 LEFT JOIN 该表做「只采集未采集过的流水线」增量过滤 |
| 归属字段来源 | `sdi_rd_efc_test_case_result_raw_*`（repo_url 等已解析入库）、`sdi_rd_efc_pipeline_run_clean_codearts`（`git_url`、`pipeline_start_time`/`pipeline_end_time`） |
| 平台 | DS 3.4.2 + SeaTunnel 2.3.13（Zeta 引擎，CCE 集群），Doris 为 SeaTunnel Jdbc 源/目标 |

**现有链路的 OBS 读取与增量机制**（分析 `nane/openlibing-seatunnel` 插件仓 `transform/parsetestcase` 包结论）：

| 项 | 现状 |
| --- | --- |
| 读取路径 | **不是全量列举桶**，而是**按流水线执行目录定向列举**：`testcase-metadata/{pipelineId}/{pipelineRunId}/{jobId}/`。`PipelineType` 支持三平台：CODEARTS=`{pipelineId}/{pipelineRunId}/{jobId}_{buildNo}`、GITCODE=`{workflowId}/{runId}/{jobRunId}`、GITHUB=`{workflowId}/{runId}/{jobId}`；`pipelineIdField` 可配（codearts 默认 pipelineId，gitcode/github 配 workflowId） |
| 增量机制 | **增量同步**：SeaTunnel source 从 `sdi_rd_efc_pipeline_run_clean_codearts` 查待采集流水线，`LEFT JOIN sdi_rd_efc_pipeline_run_collected_testcase_codearts` 过滤已采集（`c.pipeline_id IS NULL`）→ 只处理未采集过的流水线；后置 SQL 任务回写已采集表 |
| 归属字段 | 解析出的 repo_url 等已落 `sdi_rd_efc_test_case_result_raw_*`；workflow 起止时间在 `sdi_rd_efc_pipeline_run_clean_codearts`（`pipeline_start_time`/`pipeline_end_time`） |

本需求采集**参考此模式分两段**：

1. **工作流①（raw 采集）**：source 增量过滤 + 定向列举 → **复用 `ParseTestcase` 的 OBS 读取代码，仅输出 JSON 原文**（新增轻量 transform，参照 `ParseTestcaseTransform`/`TestCaseMetadataParser`，只改输出不做解析）→ 原始 JSON 整份写 `raw_test_report`（仿 `raw_workflow_source_github`：原始数据先落库，不展开）。
2. **工作流②（sdi 清洗）**：source 读 `raw_test_report` → `JsonArrayExpand` 展开外层数组（带 record_seq）+ `Sql` 归属字段提取 → 写 `sdi_rd_efc_test_report_<模板名>`（每模板一张，参考既有 testcase raw→sdi 清洗脚本，如 #21 的 StageParser/JobParser 展开模式）。**纯配置，无新增解析插件**。

**本需求在 `nane/openlibing-seatunnel` 仓新增**：一个**轻量 OBS 读取 transform**（参照 `ParseTestcase` 的 OBS 读取，仅输出 JSON 原文，不做解析展开）；sdi 清洗段不新增插件。

## 5. 数据契约（对上游）

| 项 | 约定 |
| --- | --- |
| OBS 桶 | 私有桶 `op-case-result`（openlibing 账号下），平台持只读凭证 |
| OBS 路径 | `testcase-metadata/{pipeline_id}/{pipeline_run_id}/{job_id}/`，报告 JSON 与 metadata xml **同路径** |
| 报告文件名 | `<模板名>_xxx.json`，同一属性多个单词用 `-` 分隔（kebab-case），如 `triton-model-performance_20260904.json` |
| JSON 结构 | 外层列表、内层字典；列表内每条 = 一条测试任务 + 执行结果 |
| 模板名 | 与 JSON schema `title` 一致（snake_case，如 `triton_model_performance`），登记于 `dm_rd_efc_template_registry.model_code` |
| 模板识别规则 | 文件名**第一个下划线前**的部分 = kebab 形式的模板名（如 `triton-model-performance_xxx.json` → `triton-model-performance`）；模板名单词间用 `-` 分隔、**不含下划线**，故首个下划线即模板名与后缀的分隔符；kebab → snake 映射到 model_code（`triton_model_performance`） |
| 表名规则 | 数据中台（Doris）统一中缀 `rd_efc`（研发效能）：**raw 层 `raw_test_report`**（仿 `raw_workflow_source_github`，不强制 rd_efc 中缀）、**sdi 层 `sdi_rd_efc_test_report_<模板名>`**（每模板一张，如 `sdi_rd_efc_test_report_triton_model_performance`）；**登记表同样遵循**（`dm_rd_efc_template_registry`） |
| 唯一键（sdi 层） | `(pipeline_id, pipeline_run_id, job_id, report_file_name, record_seq)`，`record_seq`=JSON 数组下标+1 |
| 唯一键（raw 层） | `(pipeline_id, pipeline_run_id, job_id, report_file_name)`（一份原始 JSON 一行，UNIQUE KEY 防重复落库） |
| 三 ID 来源 | `pipeline_id/pipeline_run_id/job_id` 由 SeaTunnel 插件从 **OBS 路径 + 流水线执行记录透传**，**不要求 JSON 内容携带**；业务 JSON 只含模板业务字段，平台归属字段全部由平台补齐 |
| 归属字段 | repo_url、workflow 起止时间由既有表 JOIN 补齐（`sdi_rd_efc_pipeline_run_clean_codearts` / `sdi_rd_efc_test_case_result_raw_*`），**不解析 xml** |

> 注：不同平台流水线定义不同（GitCode/GitHub 上报为 workflow_id，metadata 路径为 pipeline_id），平台统一以 `pipeline_id / pipeline_run_id / job_id` 三列存储，不做别名映射。

## 6. 数据模型

### 6.1 模板登记表 `dm_rd_efc_template_registry`（Doris，新建）

**不复用 MySQL `tbl_third_api_data_model`**：third_api 语义是"第三方 API 数据模型"，与测试报告不符；且正式环境无 MySQL 只读账号，采集侧无法读取。新建 **Doris 专用模板登记表**，以 `table_type` 区分模板类型（当前 `test_report`），采集与消费共同读取（Doris 账号已有，**零 MySQL 依赖**）：

```sql
CREATE TABLE `dm_rd_efc_template_registry` (
  `table_type`     VARCHAR(32)  NOT NULL COMMENT '模板表类型：test_report（测试报告）',
  `model_code`     VARCHAR(128) NOT NULL COMMENT '模板 code',
  `model_name`     VARCHAR(255) COMMENT '模板名称',
  `table_name`     VARCHAR(255) NOT NULL COMMENT 'Doris 真实表名',
  `status`         TINYINT      NOT NULL DEFAULT 1 COMMENT '0停用 1启用',
  `description`    VARCHAR(512) COMMENT '描述',
  `pipeline_ids`   VARCHAR(512) COMMENT '采集流水线白名单（逗号分隔，一对多）；为空则该模板不参与采集',
  `create_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=OLAP UNIQUE KEY(`table_type`, `model_code`) COMMENT='模板登记表（按 table_type 区分模板类型）';
```

> **字段精简**：不设 `id` 主键——`(table_type, model_code)` 本身唯一（Doris UNIQUE KEY 模型只支持一组 key，避免 id 与业务唯一键并存）；不设 `schema_version`——当前采集/消费两侧均无使用方，后续确有 schema 演进需求再加。

- **登记单写**：新增模板 = INSERT 本表一条（`table_type='test_report'`），采集与 ops 消费都读它，无双处维护
- **语义正确**：不硬套 third_api；后续其他类型模板新增 `table_type` 即可扩展
- **校验机制复用**：列白名单/必填仍来自 Doris `information_schema.columns`（third_api 同款机制，ops 侧已实现等价校验）

### 6.2 采集/消费读取登记范围

- **采集（SeaTunnel）**：source JOIN `dm_rd_efc_template_registry`（`table_type='test_report'` 且 `status=1`），`SPLIT_BY_STRING(pipeline_ids, ',')` + `ARRAY_CONTAINS` 白名单过滤（见 7.2）
- **消费（ops）**：`ReportTemplateModelMapper` 查同一张表定位真实表名（表名白名单），白名单校验逻辑不变
- **免 MySQL 连接**：登记范围全部落在 Doris，不引入 MySQL 账号/密码暴露面（Catalog 方案已否决，见 13 章 R6）

### 6.3 raw 层表 `raw_test_report`（原始 JSON 整份落库）

**仿 `raw_workflow_source_github` 模式**：少量定位字段 + `data_json` 整份原始 JSON + `create_time`，不解析、不展开：

```sql
CREATE TABLE `raw_test_report` (
  `pipeline_id`      varchar(128)  NULL COMMENT '流水线ID（GitCode/GitHub 为 workflow_id，必填）',
  `pipeline_run_id`  varchar(128)  NULL COMMENT '流水线执行ID（必填）',
  `job_id`           varchar(128)  NULL COMMENT '任务ID（必填）',
  `report_file_name` varchar(255)  NULL COMMENT '报告文件名（必填，含扩展名）',
  `model_code`       varchar(128)  NULL COMMENT '模板 code（由文件名前缀识别，冗余便于排查）',
  `data_json`        json          NULL COMMENT '原始 JSON 整份（外层数组原文）',
  `source_end_time`  datetime      NULL COMMENT '采集时源表执行结束时间（重试判定：源表 end_time 更新则重采）',
  `create_time`      datetime      NULL COMMENT '平台入库时间'
) ENGINE=OLAP
UNIQUE KEY(`pipeline_id`, `pipeline_run_id`, `job_id`, `report_file_name`)
COMMENT '测试报告原始 JSON（仿 raw_workflow_source_github）'
DISTRIBUTED BY HASH(`pipeline_id`) BUCKETS 10
PROPERTIES (
"replication_allocation" = "tag.location.default: 2",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true"
);
```

- 唯一键 = 四元组（一份原始 JSON 一行），Doris MOW 同键覆盖 = 防重复落库兜底。
- 保留原始数据：后续 schema 演进/重新清洗/追溯审计均可基于 raw 重放，无需重拉 OBS。

### 6.4 sdi 清洗层表 `sdi_rd_efc_test_report_<模板名>`（每模板一张，本期 1 模板验证）

```sql
CREATE TABLE `sdi_rd_efc_test_report_triton_model_performance` (
  `pipeline_id`         varchar(128)  NULL COMMENT '流水线ID（GitCode/GitHub 为 workflow_id，必填）',
  `pipeline_run_id`     varchar(128)  NULL COMMENT '流水线执行ID（必填）',
  `job_id`              varchar(128)  NULL COMMENT '任务ID（必填）',
  `report_file_name`    varchar(255)  NULL COMMENT '报告文件名（必填）',
  `record_seq`          int           NULL COMMENT '记录序号=JSON数组下标+1（必填）',
  `repo_url`            varchar(512)  NULL COMMENT '代码仓库地址（JOIN 既有表补齐）',
  `workflow_start_time` datetime      NULL COMMENT '流水线开始时间（JOIN 既有表补齐）',
  `workflow_end_time`   datetime      NULL COMMENT '流水线结束时间（JOIN 既有表补齐）',
  `source_end_time`     datetime      NULL COMMENT '清洗时源表执行结束时间（透传 raw，重试判定：raw 更新则重清洗）',
  `report_upload_time`  datetime      NULL COMMENT '平台入库时间',
  `model_name`          varchar(255)  NULL COMMENT '模型名称',
  `model_config`        varchar(512)  NULL COMMENT '模型配置',
  `eager_device_time`   double        NULL COMMENT 'eager 卡侧时长（us）',
  `inductor_device_time` double       NULL COMMENT 'inductor 卡侧时长（us）'
) ENGINE=OLAP
UNIQUE KEY(`pipeline_id`, `pipeline_run_id`, `job_id`, `report_file_name`, `record_seq`)
COMMENT 'Triton模型性能测试报告清洗层(SDI)'
DISTRIBUTED BY HASH(`pipeline_id`) BUCKETS 10
PROPERTIES (
"replication_allocation" = "tag.location.default: 2",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true"
);
```

- 每模板一张表，表名 = `sdi_rd_efc_test_report_<模板名>`，模板名 = JSON schema title（snake）。
- 唯一键 = 五元组（Issue「唯一记录键值组」），Doris MOW 同键覆盖 = 行级幂等兜底。
- DDL 存档 openlibing-docs（DBA 执行）；后续新增模板复制本 DDL 改表名/业务字段即可。

### 6.5 增量判定：状态完成 + 时间窗口 + 反查 + 重试时间比较（不新增台账表）

**不新增台账表**（台账表方案已否决，见 13 章 R5），分两段增量判定：

**① 工作流①（raw 采集）增量**：source 从流水线记录查待采集行，**只采「已完成」执行记录**（codearts `pipeline_status='COMPLETED'`、GitHub `status='completed'`、GitCode `status='COMPLETED'`——执行完成 = 目录报告文件已齐，一次采全，无需担心后续补传），再 `LEFT JOIN raw_test_report` 反查已落库（`d.pipeline_id IS NULL` 才处理）→ 有报告即落库，下轮被反查排除。**重试判定**：`source_end_time` 记录采集时源表执行结束时间，反查条件扩展为「未落库 **OR** 源表 end_time > 已落库 source_end_time」（重试后三 ID 不变但 end_time 更新 → 判定为重试新数据 → 重新采集覆盖）。

**② 工作流②（sdi 清洗）增量**：source 读 `raw_test_report`，`LEFT JOIN sdi_rd_efc_test_report_<模板名>` 反查已清洗（`s.pipeline_id IS NULL` 才处理）→ 已清洗的排除。**重试判定**：`source_end_time` 透传 raw 的值，反查条件扩展为「未清洗 **OR** raw.source_end_time > 已清洗 source_end_time」（重试重采后 raw 更新 → 判定需重清洗）。

两段均配合**时间窗口**自然淘汰：

- **重试/封存** = 时间窗口自然淘汰 + **end_time 时间比较**：只扫描 `pipeline_start_time > NOW() - 窗口` 内的流水线；窗口内重试过的（end_time 更新）会被时间比较判定为新数据重新采集，未重试的每轮重扫，出窗口不再扫（等价封存）。
- **重试语义**：三平台源表均为 Doris UNIQUE KEY（MOW），重试后源表**覆盖原行**（三 ID 不变、end_time 更新，实测 gitcode/github 同键多行=0）；CodeArts 因 `step_daily_build_number` 递增，拼接 jobId 变化天然区分。落到 raw/sdi：同名报告文件同键覆盖（不产生重复行），新增文件则新增行。
- **正常场景 OBS 开销与台账方案持平**：有报告的 job 落库后即被反查排除（扫 1 次停）；无报告的 job 数量少，窗口内重扫空目录成本低。
- **状态过滤收益**：跳过未完成/异常执行记录（RUNNING/FAILED/CANCELED 等），不扫它们的 OBS 目录，省无谓开销；同时保证采集到的报告文件完整（执行完成时文件已全部上传）。
- **实现最简**：无台账表、无后置 SQL、无镜像同步。

**已知代价（业务方确认后接受）**：

| 代价 | 说明 | 缓解 |
| --- | --- | --- |
| 无显式状态/审计 | 排障时查不到"哪些 job 超时无报告"（运维视角损失，不影响消费） | 可接受则忽略；需要审计再补台账 |
| **晚完成 > 窗口漏采** | job 在 run 开始后超过窗口时长才上传报告 → 出窗口漏采 | 窗口参数化 `${report_window_hours}`（默认 24h），**需与业务方确认报告上传时效 ≤ 24h** |
| **执行完成与文件落盘时间差** | 理论上执行完成时文件已齐；若存在极端异步上传（完成标记早于文件落盘），首轮可能漏采部分文件，但该 job 未落 raw（反查不排除）会在窗口内下轮重扫补齐 | 依赖反查重扫兜底，无需额外处理 |
| 无显式封存标记 | bug 节点靠窗口自然淘汰，无 status 可查 | 等效淘汰，仅缺标记 |

## 7. 采集设计（DolphinScheduler + SeaTunnel）

### 7.1 新增 DS 工作流（两个，raw→sdi 两段式）

| 工作流 | 职责 | 调度 |
| --- | --- | --- |
| ① `[job][raw->raw][openlibing]测试报告原始数据采集` | OBS 读测试报告 JSON → 原始 JSON 整份写 `raw_test_report` | **每小时**（cron `0 0 * * * ? *`），失败告警 |
| ② `[job][raw->sdi][openlibing]测试报告数据清洗` | 读 `raw_test_report` → `JsonArrayExpand` 展开 → 写 `sdi_rd_efc_test_report_<模板名>` | **每小时**（cron `0 0 * * * ? *`），失败告警 |

- 两工作流 openlibing 项目，正式/测试环境各一；PM 决策：不新增台账表、无后置 SQL、无镜像同步。
- 增量判定 = 时间窗口 + 反查 + 重试时间比较（raw/sdi 两段，见 6.5/7.4）。

### 7.2 工作流① rawScript（OBS → raw_test_report）

```hocon
env {
  execution.parallelism = 4
  job.mode = "BATCH"
  checkpoint.interval = 30000
  checkpoint.timeout = 900000
}

source {
  Jdbc {
    plugin_output = "pending_pipeline"
    url = "${openlibing_doris_url}"
    query = """
      /* 三平台 UNION：codearts / github / gitcode 各自映射三 ID + 起止时间 + repoUrl */
      /* 状态过滤：只采「已完成」的执行记录（执行完成 = 目录文件已齐，一次采全，不依赖反查排除兜漏采；同时跳过未完成/异常记录省 OBS 开销） */
      SELECT 'codearts' AS platform,
             t.pipeline_id AS pipelineId, t.pipeline_run_id AS pipelineRunId,
             /* codearts OBS job 目录 = step_build_job_id_日期_当天第N次（20260728.10 → _20260728_10） */
             CONCAT(t.step_build_job_id, '_', REPLACE(t.step_daily_build_number, '.', '_')) AS jobId,
             t.git_url AS repoUrl,
             t.pipeline_start_time AS workflowStartTime, t.pipeline_end_time AS workflowEndTime
      FROM sdi_rd_efc_pipeline_run_clean_codearts t
      JOIN ( -- Doris 模板登记表（6.1）：采集范围白名单（Doris 账号，免 MySQL）
        SELECT model_code, SPLIT_BY_STRING(pipeline_ids, ',') AS pids
        FROM dm_rd_efc_template_registry
        WHERE table_type = 'test_report' AND status = 1 AND pipeline_ids IS NOT NULL AND pipeline_ids <> ''
          AND model_code = 'triton_model_performance'   /* 下推到子查询，只拉 1 行 */
      ) cfg
      LEFT JOIN ( -- 反查：窗口内已入 raw 的 job 用数据自身当"已处理"标记（不新增台账表，见 6.5）
        SELECT pipeline_id, pipeline_run_id, job_id,
               MAX(source_end_time) AS max_source_end_time   /* 已落库的最新采集源表结束时间 */
        FROM raw_test_report
        WHERE create_time > NOW() - INTERVAL ${report_window_hours} HOUR
        GROUP BY pipeline_id, pipeline_run_id, job_id
      ) d
        ON t.pipeline_id = d.pipeline_id AND t.pipeline_run_id = d.pipeline_run_id
       AND CONCAT(t.step_build_job_id, '_', REPLACE(t.step_daily_build_number, '.', '_')) = d.job_id
      WHERE (d.pipeline_id IS NULL OR t.pipeline_end_time > d.max_source_end_time)  /* 未落 raw 或重试更新（end_time 变新）才处理 */
        AND ARRAY_CONTAINS(cfg.pids, t.pipeline_id)        /* 登记范围白名单过滤 */
        AND t.pipeline_start_time > NOW() - INTERVAL ${report_window_hours} HOUR  /* 时间窗口：晚完成/异常节点出窗口自然淘汰 */
        AND t.pipeline_status = 'COMPLETED'   /* 只采已完成执行记录 */
        AND LOWER(t.job_name) LIKE 'test%'

      UNION ALL

      /* GitHub：workflow 级数字 ID；job 目录 = {workflow_id}/{run_id}/{workflow_job_id}（纯数字，无后缀） */
      SELECT 'github' AS platform,
             CAST(r.workflow_id AS STRING) AS pipelineId,
             CAST(j.workflow_run_id AS STRING) AS pipelineRunId,
             CAST(j.workflow_job_id AS STRING) AS jobId,
             j.repo_url AS repoUrl,
             r.run_started_at AS workflowStartTime, r.updated_at AS workflowEndTime
      FROM sdi_rd_efc_workflow_run_job_github j
      LEFT JOIN sdi_rd_efc_workflow_run_raw_github r ON j.workflow_run_id = r.run_id
      JOIN ( SELECT model_code, SPLIT_BY_STRING(pipeline_ids, ',') AS pids
             FROM dm_rd_efc_template_registry
             WHERE table_type = 'test_report' AND status = 1 AND pipeline_ids IS NOT NULL AND pipeline_ids <> ''
               AND model_code = 'triton_model_performance'
      ) cfg
      LEFT JOIN ( SELECT pipeline_id, pipeline_run_id, job_id,
                         MAX(source_end_time) AS max_source_end_time
                  FROM raw_test_report
                  WHERE create_time > NOW() - INTERVAL ${report_window_hours} HOUR
                  GROUP BY pipeline_id, pipeline_run_id, job_id
      ) d
        ON CAST(r.workflow_id AS STRING) = d.pipeline_id
       AND CAST(j.workflow_run_id AS STRING) = d.pipeline_run_id
       AND CAST(j.workflow_job_id AS STRING) = d.job_id
      WHERE (d.pipeline_id IS NULL OR r.updated_at > d.max_source_end_time)  /* 重试后 run updated_at 变新 → 重新采集 */
        AND ARRAY_CONTAINS(cfg.pids, CAST(r.workflow_id AS STRING))
        AND r.run_started_at > NOW() - INTERVAL ${report_window_hours} HOUR
        AND j.status = 'completed'   /* 只采已完成 job */
        AND LOWER(j.job_name) LIKE 'test%'

      UNION ALL

      /* GitCode：hex ID；job 目录 = {workflow_id}/{workflow_run_id}/{job_id} */
      SELECT 'gitcode' AS platform,
             t.workflow_id AS pipelineId, t.workflow_run_id AS pipelineRunId,
             t.job_id AS jobId,
             t.repo_url AS repoUrl,
             t.start_time AS workflowStartTime, t.end_time AS workflowEndTime
      FROM sdi_rd_efc_workflow_run_raw_gitcode t
      JOIN ( SELECT model_code, SPLIT_BY_STRING(pipeline_ids, ',') AS pids
             FROM dm_rd_efc_template_registry
             WHERE table_type = 'test_report' AND status = 1 AND pipeline_ids IS NOT NULL AND pipeline_ids <> ''
               AND model_code = 'triton_model_performance'
      ) cfg
      LEFT JOIN ( SELECT pipeline_id, pipeline_run_id, job_id,
                         MAX(source_end_time) AS max_source_end_time
                  FROM raw_test_report
                  WHERE create_time > NOW() - INTERVAL ${report_window_hours} HOUR
                  GROUP BY pipeline_id, pipeline_run_id, job_id
      ) d
        ON t.workflow_id = d.pipeline_id AND t.workflow_run_id = d.pipeline_run_id
       AND t.job_id = d.job_id
      WHERE (d.pipeline_id IS NULL OR t.end_time > d.max_source_end_time)  /* 重试后 end_time 变新 → 重新采集 */
        AND ARRAY_CONTAINS(cfg.pids, t.workflow_id)
        AND t.start_time > NOW() - INTERVAL ${report_window_hours} HOUR
        AND t.status = 'COMPLETED'   /* 只采已完成 workflow */
        AND LOWER(t.job_name) LIKE 'test%'
    """
  }
}

transform {
  // 测试报告原文读取（新增轻量 OBS 读取 transform，复用 ParseTestcase 的 OBS 列举/下载代码；不做解析/展开）
  //    登记范围白名单已在 source SQL 内过滤（ARRAY_CONTAINS），此处无需再过滤
  //    jobId 语义：codearts=step_build_job_id_日期_当天第N次（source 已 CONCAT 拼好）；GitHub=workflow_job_id
  TestReportReader {
    plugin_input = ["pending_pipeline"]
    plugin_output = "raw_report_rows"
    ak = "${OBS_AK}"
    sk = "${OBS_SK}"
    endPoint = "obs.cn-southwest-2.myhuaweicloud.com"
    bucketName = "op-case-result"
    prefix = "testcase-metadata"
    templateCode = "triton_model_performance"   // 文件名前缀匹配 kebab(模板名)_
    outputFieldName = "RawJson"
  }
}

sink {
  Jdbc {
    plugin_input = ["raw_report_rows"]
    url = "${openlibing_doris_url}"
    query = """
      INSERT INTO raw_test_report (
        pipeline_id, pipeline_run_id, job_id, report_file_name, model_code, data_json,
        source_end_time, create_time
      ) VALUES (?, ?, ?, ?, 'triton_model_performance', ?, ?, NOW());
    """
    auto_commit = true
    batch_size = 100
  }
}
```

**`TestReportReader` 轻量 transform**（新增，复用 `ParseTestcase` 的 OBS 读取代码）：
- 输入：流水线记录行 `(pipeline_id, pipeline_run_id, job_id, workflowEndTime, 模板参数)`
- 行为：按 `testcase-metadata/{pipeline_id}/{pipeline_run_id}/{job_id}/` 列举并下载文件名匹配 `<kebab(模板名)>_*.json` 的文件 → **输出原始 JSON 整份（不解析、不展开）** + 上下文字段（含文件名）
- 输出字段：`pipelineId/pipelineRunId/jobId/reportFileName + RawJson + sourceEndTime`（`sourceEndTime` 透传输入行 `workflowEndTime`，sink 写 raw 表 `source_end_time` 列）
- 实现方式：在 `nane/openlibing-seatunnel` 仓参照 `ParseTestcaseTransform`/`TestCaseMetadataParser` 的 OBS 读取逻辑新建轻量类（仅输出原文，无解析逻辑），**sdi 清洗段不新增插件**（见 7.3 纯配置）

### 7.3 工作流② rawScript（raw_test_report → sdi 清洗层）

```hocon
env {
  execution.parallelism = 4
  job.mode = "BATCH"
  checkpoint.interval = 30000
  checkpoint.timeout = 900000
}

source {
  Jdbc {
    plugin_output = "report_detail"
    url = "${openlibing_doris_url}"
    query = """
      SELECT y.pipeline_id, y.pipeline_run_id, y.job_id, y.report_file_name,
             y.record_seq,
             COALESCE(y.repo_url, s.repo_url)                    AS repo_url,
             COALESCE(y.workflow_start_time, s.wf_start_time)    AS workflow_start_time,
             COALESCE(y.workflow_end_time,   s.wf_end_time)      AS workflow_end_time,
             y.source_end_time, y.model_name, y.model_config,
             y.eager_device_time, y.inductor_device_time
      FROM (
        -- 层3：ROW_NUMBER + JSON 提取（在 LATERAL VIEW 结果之上）
        SELECT x.pipeline_id, x.pipeline_run_id, x.job_id, x.report_file_name,
               ROW_NUMBER() OVER (
                 PARTITION BY x.pipeline_id, x.pipeline_run_id, x.job_id, x.report_file_name
                 ORDER BY x.el
               ) AS record_seq,
               JSON_EXTRACT_STRING(x.el, '$.model_name')           AS model_name,
               JSON_EXTRACT_STRING(x.el, '$.model_config')         AS model_config,
               CAST(JSON_EXTRACT_STRING(x.el, '$.eager_device_time')    AS DOUBLE) AS eager_device_time,
               CAST(JSON_EXTRACT_STRING(x.el, '$.inductor_device_time') AS DOUBLE) AS inductor_device_time,
               x.repo_url, x.workflow_start_time, x.workflow_end_time, x.source_end_time
        FROM (
          -- 层2：LATERAL VIEW EXPLODE（无窗口函数；JOIN 必须放内层，LATERAL VIEW 不能紧跟 JOIN）
          SELECT r.pipeline_id, r.pipeline_run_id, r.job_id, r.report_file_name, e.el,
                 r.repo_url, r.workflow_start_time, r.workflow_end_time, r.source_end_time
          FROM (
            -- 层1：raw + 反查排除（Doris 限制 lateral view 与窗口函数同层，故分层嵌套；归属字段三平台 JOIN 见下方 s 子查询）
            SELECT r.pipeline_id, r.pipeline_run_id, r.job_id, r.report_file_name, r.data_json,
                   NULL AS repo_url, NULL AS workflow_start_time, NULL AS workflow_end_time,
                   r.source_end_time
            FROM raw_test_report r
            LEFT JOIN ( -- 反查：窗口内已清洗的（四元组）排除 + 重试时间比较（不新增台账表，见 6.5）
              SELECT pipeline_id, pipeline_run_id, job_id, report_file_name,
                     MAX(source_end_time) AS max_source_end_time   /* 已清洗的最新源表结束时间 */
              FROM sdi_rd_efc_test_report_triton_model_performance
              WHERE report_upload_time > NOW() - INTERVAL ${report_window_hours} HOUR
              GROUP BY pipeline_id, pipeline_run_id, job_id, report_file_name
            ) s
              ON r.pipeline_id = s.pipeline_id AND r.pipeline_run_id = s.pipeline_run_id
             AND r.job_id = s.job_id AND r.report_file_name = s.report_file_name
            WHERE (s.pipeline_id IS NULL OR r.source_end_time > s.max_source_end_time)  /* 未清洗或重试重采（raw 更新）才处理 */
              AND r.create_time > NOW() - INTERVAL ${report_window_hours} HOUR
              AND r.model_code = 'triton_model_performance'
          ) r
          LATERAL VIEW EXPLODE_JSON_ARRAY_JSON(r.data_json) e AS el
        ) x
      ) y
      LEFT JOIN ( -- 归属字段兜底：三平台来源表 JOIN（codearts / github / gitcode，只取已完成记录）
        SELECT pipeline_id, pipeline_run_id,
               CONCAT(step_build_job_id, '_', REPLACE(step_daily_build_number, '.', '_')) AS job_id,
               git_url AS repo_url,
               pipeline_start_time AS wf_start_time, pipeline_end_time AS wf_end_time
        FROM sdi_rd_efc_pipeline_run_clean_codearts
        WHERE pipeline_end_time > NOW() - INTERVAL ${report_window_hours} HOUR
          AND pipeline_status = 'COMPLETED'
        UNION ALL
        SELECT CAST(r.workflow_id AS STRING) AS pipeline_id,
               CAST(j.workflow_run_id AS STRING) AS pipeline_run_id,
               CAST(j.workflow_job_id AS STRING) AS job_id,
               j.repo_url,
               r.run_started_at AS workflow_start_time, r.updated_at AS workflow_end_time
        FROM sdi_rd_efc_workflow_run_job_github j
        LEFT JOIN sdi_rd_efc_workflow_run_raw_github r ON j.workflow_run_id = r.run_id
        WHERE r.run_started_at > NOW() - INTERVAL ${report_window_hours} HOUR
          AND j.status = 'completed'
        UNION ALL
        SELECT workflow_id AS pipeline_id, workflow_run_id AS pipeline_run_id, job_id,
               repo_url, start_time AS workflow_start_time, end_time AS workflow_end_time
        FROM sdi_rd_efc_workflow_run_raw_gitcode
        WHERE start_time > NOW() - INTERVAL ${report_window_hours} HOUR
          AND status = 'COMPLETED'
      ) s
        ON y.pipeline_id = s.pipeline_id AND y.pipeline_run_id = s.pipeline_run_id
       AND y.job_id = s.job_id
      ORDER BY y.report_file_name, y.record_seq
    """
  }
}

sink {
  Jdbc {
    plugin_input = ["report_detail"]
    url = "${openlibing_doris_url}"
    query = """
      INSERT INTO sdi_rd_efc_test_report_triton_model_performance (
        pipeline_id, pipeline_run_id, job_id, report_file_name, record_seq,
        repo_url, workflow_start_time, workflow_end_time, source_end_time, report_upload_time,
        model_name, model_config, eager_device_time, inductor_device_time
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, ?, ?, ?);
    """
    auto_commit = true
    batch_size = 100
  }
}
```

> **方案调整（2026-09-08 实测）**：清洗段不再使用 `JsonArrayExpand` transform——测试库实测其 `output_field` 不生成 `recordSeq`（该插件只做字段透传/JSON 取值，无数组下标输出），且 sdi 五元组 UNIQUE KEY 依赖 `record_seq`。改为 **Doris SQL 原生展开**：内层 `LATERAL VIEW EXPLODE_JSON_ARRAY_JSON` 逐元素展开，外层 `ROW_NUMBER() OVER (PARTITION BY 四元组 ORDER BY e.el)` 生成 `record_seq`（= 数组下标 + 1 的等价稳定序号），JSON 字段用 `JSON_EXTRACT_STRING/DOUBLE` 提取，归属字段（repoUrl/起止时间）在子查询内 JOIN 来源表透传。**不新增/不改插件**，纯配置达成。Doris 限制窗口函数须在 LATERAL VIEW 的外层（内层 EXPLODE、外层 ROW_NUMBER），归属 JOIN 也在最外层兜底。

### 7.4 增量与幂等（时间窗口 + 反查 + 重试时间比较）

**增量判定**（不新增台账表，见 6.5）：

| 段 | 判定 | 机制 |
| --- | --- | --- |
| 工作流①（raw 采集） | 未落 raw **或重试更新** | `raw_test_report` **实际有数据** → source 反查 `LEFT JOIN ... WHERE d.pipeline_id IS NULL OR 源表.end_time > d.max_source_end_time` 排除，不再扫 OBS；**重试后 end_time 变新 → 判定重试 → 重新采集（MOW 覆盖，不重复行）** |
| 工作流②（sdi 清洗） | 未清洗 **或 raw 更新** | `sdi_rd_efc_test_report_<模板名>` **实际有数据** → source 反查四元组 `LEFT JOIN ... WHERE s.pipeline_id IS NULL OR r.source_end_time > s.max_source_end_time` 排除，不再处理；**重试重采后 raw.source_end_time 变新 → 判定需重清洗** |
| 待重试/晚完成 | 窗口内未落库/未清洗的每轮重扫；报告出现即处理，下轮被反查排除；**窗口内重试的（end_time 更新）被时间比较捕获重新采集** |
| 异常封存 | 窗口自然淘汰：出窗口（`>${report_window_hours}`）不再扫描，等价封存（无显式 status） |

**重试语义（三平台统一）**：重试后三 ID 不变但源表 `end_time` 更新（Doris UNIQUE KEY MOW 覆盖，实测 gitcode/github 同键多行=0；CodeArts `step_daily_build_number` 递增拼接 jobId 变化天然区分）。`source_end_time` 是判重依据：源表 end_time > 已落库 source_end_time ⇒ 重试新数据 ⇒ 重采/重清洗，同名文件同键覆盖、新文件新增行。

**幂等兜底**：

- 行级：raw 表四元组 UNIQUE KEY + sdi 表五元组 UNIQUE KEY（MOW 覆盖）——重复执行/并发/重试重采均不产生重复行（同键覆盖更新）。
- 调度：DS cron 每小时 + 失败告警；SeaTunnel checkpoint 容错。
- 反查子集限窗口内（`create_time/report_upload_time > now-窗口`），避免 `MAX(...) GROUP BY` 全表渐大。

**窗口参数**：`${report_window_hours}`（DS 全局参数，默认 24h）。**需与业务方确认报告上传时效 ≤ 窗口**（超过窗口才上传视为漏采，不补；调大窗口可重跑补采）。

**事后补采支持（最小修改）**：业务要求补采历史/漏采数据时，DS 控制台**手动触发工作流①并覆盖全局参数 `${report_window_hours}`** 为目标回看值（如 720 = 30 天），跑一轮补采窗口内未落 raw 的 job；已落 raw 且未重试的不重采（反查幂等），**窗口内重试过的（end_time 更新）会被时间比较判定重采覆盖**，补传报告按 UNIQUE KEY 同键覆盖更新。工作流②随 raw 更新行自动重清洗。**零代码修改**（时间条件本就参数化）。

**不依赖文件名时间戳 / OBS lastModified / 登记表 update_time 做增量水位。**

### 7.5 模板登记与范围

- 模板登记（`dm_rd_efc_template_registry`）：`table_type='test_report'`、`model_code=<模板名>`、`table_name=sdi_rd_efc_test_report_<模板名>`、`pipeline_ids=<逗号分隔流水线>`、`status=1`
- 登记数据维护：**已确认**——本期由开发手动 SQL 登记（见下方登记清单），不做管理页面
- **一模板对多流水线（一对多）**：`pipeline_ids` 逗号分隔，SeaTunnel 按白名单过滤

**模板登记清单（本期新增模板的手动步骤）**：

```sql
-- ① 建 Doris 模板登记表（一次性，DBA 执行，DDL 见 6.1）

-- ② 建 raw 表 + Doris 模板清洗表（DDL 见 6.3/6.4，由 DBA 执行）

-- ③ 登记模板条目 + 配置采集范围（采集与消费共同读取，单写一处）
INSERT INTO dm_rd_efc_template_registry
  (table_type, model_code, model_name, table_name, status, description, pipeline_ids)
VALUES
  ('test_report', 'triton_model_performance', 'Triton模型性能数据',
   'sdi_rd_efc_test_report_triton_model_performance', 1,
   'Triton模型性能测试报告（模板名=JSON schema title）', 'pipelineA,pipelineB');

-- ④ 数据资产列信息无需手动登记：ops 查询与采集列白名单均读 Doris information_schema（建表后自动可得）
```

> 数据资产列信息（列名/注释/必填）由 `information_schema.columns` 动态获取（sync `DataAssetService` 与 ops 查询同源），建表即生效，无需额外登记表。

## 8. ops 消费设计（读 sdi 清洗层，逻辑不变）

> 消费侧只读 **sdi 清洗表**（登记表 `table_name` 指向 `sdi_rd_efc_test_report_<模板名>`），不直接读 raw 表。

### 8.1 REST（`ReportController`）

**① POST `/report/template/list`**（模板及字段元数据）

```jsonc
// Req：空 body
// Resp：
{ "code": 200, "data": [{
    "modelCode": "triton_model_performance",
    "modelName": "Triton模型性能数据",
    "description": "...",
    "repoUrls": ["https://gitcode.com/xxx/yyy"],
    "columns": [{ "columnName": "pipeline_id", "columnComment": "流水线ID(必填)",
                  "dataType": "varchar", "required": true }, /* ... */]
}] }
```

> 仅返回模板名 + 字段元数据 + 可用仓库列表；`repoUrls` 为该模板数据表 `SELECT DISTINCT repo_url`（无数据返回空数组），供构造 `repoUrls` 参数（支持多选）。

**② POST `/report/data/query`**（按 repo 多选 + 场景查询，分页）

```jsonc
// Req：
{ "modelCode": "triton_model_performance",
  "repoUrls": ["https://gitcode.com/xxx/yyy", "https://gitcode.com/zzz/yyy"],  // 多选；不传或空数组=全选
  "startTime": "2026-09-01 00:00:00", "endTime": "2026-09-04 00:00:00",
  "timeField": "workflow_end_time",
  "filters": [ { "field": "eager_device_time", "op": "lt", "value": 90 },
               { "field": "model_name", "op": "eq", "value": "xxx" } ],
  "page": 1, "pageSize": 20 }
// Resp：
{ "code": 200, "data": { "records": [ { "pipeline_id": "...", "repo_url": "...", "model_name": "..." } ],
                         "total": 100, "page": 1, "pageSize": 20 } }
```

- `repoUrls`：仓库地址列表（一个模板可对应多个仓库），**支持多选；不传或空数组 = 查询全部仓库**（不加 repo 过滤条件）

- `timeField` 白名单（workflow_start_time/workflow_end_time/report_upload_time），默认 workflow_end_time
- `filters[].op` 白名单（eq/ne/gt/gte/lt/lte/like/in）；`filters[].field` 仅限数据资产白名单列；动态 WHERE 全白名单校验，杜绝注入

### 8.2 MCP（内嵌 MCP Server，Streamable HTTP，端点 /mcp）

- 技术路线（POC 实测）：**Spring AI 1.1.8**（`spring-ai-bom`）+ `spring-ai-starter-mcp-server-webmvc`
- `mcp/McpServerConfig`（`@Bean reportMcpToolsProvider`，避开类名）+ `mcp/ReportMcpTools`（`@Tool` 只读查询，**方法级 `@DataSource`**：查登记表与 Doris sdi 清洗表均标 DORIS）
- `application.yaml`：`spring.ai.mcp.server`（name/protocol=STREAMABLE）
- 复刻 metric 仓 `mcp_test` 分支 POC（`McpServerConfig` + `MetricMcpTools`）+ `MCP搭建指导文档.md` 踩坑清单

#### 8.2.1 MCP 设计审查补充（2026-08-24，对照 metric POC 实测）

技术路线（Spring AI 1.1.8 + Streamable HTTP + 方法级 `@DataSource`）正确，但存在以下待优化点，**编码前需补齐设计**：

**①（严重）MCP 工具接口设计缺失**
- metric POC 工具仅 `Long metricCode` 单参数，本需求对标 REST `/report/data/query` 是 6 个复杂参数（modelCode / repoUrls / 时间范围 / timeField / filters[] / 分页），复杂度量级不同。
- 文档未定义：工具名、工具描述（`@Tool(description)`，AI 判断调用时机的依据）、每个 `@ToolParam` 的描述/类型/必填。
- `filters=[{field,op,value}]` 嵌套结构直接暴露给 AI 几乎无法正确调用。**需设计 AI 友好参数形态**（简化参数 + 内部转换，或预设场景快捷参数），而非照搬 REST DTO。

**②（严重）鉴权自相矛盾，有裸奔风险**
- 9 安全设计"本期不鉴权"与 T8"先发布再设计鉴权"存在裸奔上线窗口。
- ops 是对外 Web 服务，`/mcp` 暴露到网络不鉴权 = 任意人可调。
- **修订 T8：补硬门禁「MCP 端点上线正式环境前必须完成鉴权，不允许裸奔上线」**（T5"可后续迭代单独上"不变）。

**③（中等）验证方式缺原 REST 回归**
- metric POC 验证含"原 REST 回归"，ops 验证方式第 2 步只验 MCP 三步，未验 `/report/data/query` 回归。
- 新增 spring-ai 依赖可能引入 Bean 冲突/自动装配副作用，**验证清单补「原 REST `/report/data/query` 回归」**。

**④（中等）Spring Boot 版本兼容性未确认**
- Spring AI 1.1.x 要求 Spring Boot 3.4.x。文档未确认 ops 仓当前 Spring Boot 版本；若低于 3.4.x，spring-ai 依赖启动即失败。**编码前先确认 ops 的 Spring Boot 版本**（metric POC 跑通因其已是 3.4.x）。

**⑤（待确认）Doris 默认数据源**
- 文档称登记表与 sdi 表"均标 DORIS"。metric POC 经验：不标 `@DataSource` 默认即 DORIS（标 MYSQL 才必须）。需确认 ops 默认数据源：若默认即 DORIS，标 DORIS 冗余（无害）；若默认非 DORIS 则必须标，避免查错库。

#### 8.2.2 调用日志表（MCP 可观测性/审计，本期实现）

**定位**：MCP 是面向客户的正式能力面，需记录"谁调了、调了什么、结果如何"，支撑审计/运营分析/故障定位。**作为横切关注点，用 AOP 切面统一记录**，不在每个 `@Tool` 方法内手写。

**设计**：
- **表**：复用 metric POC 已定结构 `t_mcp_tool_call_log`（库 `openlibing_ops`），DDL 参考 `openlibing-metric/src/main/resources/sql/V2026_08_24__create_mcp_tool_call_log.sql`：

```sql
CREATE TABLE IF NOT EXISTS `t_mcp_tool_call_log` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键，自增',
  `tool_name`      VARCHAR(64)  NOT NULL COMMENT 'MCP 工具名（如 reportDataQuery）',
  `args_summary`   VARCHAR(500) DEFAULT NULL COMMENT '参数摘要（JSON，不落敏感值）',
  `caller`         VARCHAR(64)  DEFAULT NULL COMMENT '调用方标识（账号/应用）',
  `session_id`     VARCHAR(128) DEFAULT NULL COMMENT 'MCP 会话 ID（Streamable HTTP Mcp-Session-Id）',
  `success`        TINYINT      NOT NULL DEFAULT 1 COMMENT '是否成功（1：成功，0：失败）',
  `error_msg`      VARCHAR(500) DEFAULT NULL COMMENT '失败原因摘要',
  `cost_ms`        BIGINT       DEFAULT NULL COMMENT '耗时（毫秒）',
  `create_time`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted`     TINYINT      NOT NULL DEFAULT 0 COMMENT '是否删除（0：否，1：是）',
  PRIMARY KEY (`id`),
  KEY `idx_tool_name` (`tool_name`),
  KEY `idx_caller` (`caller`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='MCP 工具调用日志表';
```

- **AOP 切面**：`McpCallLogAspect` 环绕 `@Tool` 方法，方法级 `@DataSource(DataSourceEnum.MYSQL)` 写日志表（与业务查询 DORIS 数据源分离，避免污染 Doris）。
- **敏感值脱敏**：`args_summary` 只记录参数**摘要**（如 `modelCode=triton_model_performance`），不落 token/密钥/内部路径；`error_msg` 同样脱敏。
- **查询入口**：复用 `McpToolCallLogService.listRecent` 仅内部运维查看（不暴露为 MCP 工具，避免自审计工具被 AI 滥用）。

#### 8.2.3 MCP 生产级架构设计（面向客户，商业项目标准，2026-08-24 评审新增）

> 背景：ops 看板是**正式面向客户**的服务，MCP 作为新暴露能力面，须按商业项目标准设计，不允许"先裸奔再补"。本节固化为设计决策。

**① 鉴权（P0，上线硬门禁）**
- **对齐公司实际体系（2026-08-24 核实，非 Bearer/SSO）**：Web 用户面唯一认证点是 **openlibing-gateway 的 AuthFilter（JWT + CSRF 双提交）**，ops/metric/sync 服务端零认证；机机接口另有华为云 APIG App 认证（AppCode/AK-SK）。
- **主方案：MCP OAuth 2.1 授权码流 + refresh token 自动续期（2026-08-24 升级，替代静态 JWT）**：
  - **为什么**：静态 JWT 有有效期，让客户周期性更换凭证在商业产品不可接受；MCP 规范 2025-06-18 已把 **OAuth 2.1 + PKCE** 定为远程 MCP Server 的标准鉴权，Trae/OpenCode 等 MCP 客户端原生支持（元数据发现 + 动态注册 + PKCE + refresh 轮换）。
  - **客户体验**：首次配置时浏览器授权一次 → 客户端持 access+refresh token，access 过期由 refresh **自动续期**（换发新 refresh，旧作废）→ 对客户是"**配置一次、一劳永逸**"。附带收益：令牌可撤销、作用域限制、审计。
  - **落地组件**：openlibing 无现成用户级 OAuth 授权服务器（华为云 OIDC 仅 cicd 机机场景），需 **openlibing-gateway 扩展为 MCP 授权服务器**（`/authorize`、`/token`、`/register` + `/.well-known/oauth-authorization-server` 元数据，可用 Spring Authorization Server 集成）；ops `/mcp` 作为 **OAuth2 Resource Server** 校验 access token（`spring-boot-starter-oauth2-resource-server`，issuer 指向 gateway 授权服务器），并沿用 JWT 携带用户上下文支撑 ② 行级数据权限；机机调用对 CSRF 双提交豁免（API 化处理）。MCP 协议 Authorization 头标准接入。
- **兜底（响应安全报告 FIND-01 单点失效治理）**：MCP 服务端加**服务端 token 校验**（复用 openlibing-common `FeignAccessTokenInterceptor` 思路做入站校验），网关被绕过时服务端仍拒绝匿名调用。
- 备选（不推荐为本期主方案）：华为云 APIG App 认证（AppCode/AK-SK）——应用级身份、无用户上下文，做不了行级权限。
- **硬门禁：MCP 端点上线正式环境前必须完成上述鉴权，不允许裸奔上线**（修订 T8）。

**服务端需编写的鉴权配套代码清单（ops 侧开发工作量边界）**

> 鉴权"机制"由网关提供（不用从零搭建），但**鉴权结果的使用**必须在 ops 服务端落地。以下为必写项：

| # | 组件 | 内容 | 说明 |
| --- | --- | --- | --- |
| 1 | **用户上下文解析**（必写） | `McpUserContextHolder`（ThreadLocal）+ 拦截器从网关透传 header（如 `X-User-Id`）或 JWT 中解析调用方 | 网关只校验身份，**不把用户信息带到服务端**，行级权限的前提 |
| 2 | **行级数据权限过滤**（必写，核心） | 工具方法取调用方 → 传入 `ReportQueryService` 做与 REST 一致的权限过滤（客户仅可见自己的 repo 数据） | 网关替代不了，最易漏的越权点 |
| 3 | **工具级 RBAC**（必写） | 工具方法入口判断调用方角色（如普通客户不可调内部统计工具） | 可与 1 合并为一个小工具类 |
| 4 | **服务端 token 兜底校验**（必写，建议） | 简单 Filter/Interceptor 校验服务端 token（复用 openlibing-common `FeignAccessTokenInterceptor` 思路做入站） | 响应 FIND-01：网关被绕过（内网横向/SSRF/豁免遗漏）时仍拒绝匿名调用 |

> 限流/CSRF/JWT 校验**不在 ops 写**：限流在网关/APIG 层做；JWT 与 CSRF 校验由 gateway AuthFilter 完成（网关仓只需为 `/mcp` 加路由 + 机机 CSRF 豁免配置，属跨仓配置改动）。

**② 授权与数据越权（P0）**
- **工具级权限（RBAC）**：按调用方角色限制可调工具（如普通客户不可调内部统计工具）。
- **行级数据权限**：MCP 查询**必须继承 REST 既有数据权限**——客户只能查自己可见的 repo/项目数据。⚠️ 这是最容易漏的越权点：工具若直接复用 `ReportQueryService` 而跳过权限上下文，将成为越权后门。实现：工具方法从鉴权上下文取调用方，传入 `ReportQueryService` 做与 REST 一致的权限过滤。

**③ 可观测性（P0）**
- 调用日志表（8.2.2）+ AOP 切面统一记录。
- **Metrics**：工具调用量、成功率、P95 延迟 → Prometheus + Grafana（对齐公司监控体系）。
- **告警**：鉴权失败率突增、工具失败率超阈值、延迟劣化告警。
- 调用追踪：MDC/traceId 贯通 MCP 调用与内部 DB 查询。

**④ 可靠性（P0/P1）**
- **限流/配额（P0）**：AI 客户端可能循环调用工具，按调用方/session 秒级限流，防打爆 Doris。
- **超时控制（P0）**：工具执行超时（DB 慢查询兜底）、MCP 传输超时。
- **结果上限（P0）**：MCP 工具强制 `pageSize` 上限（如 ≤100）与返回列裁剪，防 AI 拉全表。
- **降级（P1）**：Doris 不可用时返回结构化错误（AI 可理解并放弃），不挂起。

**⑤ 工具设计（P1）**
- 工具**宜少而聚合**：每工具覆盖一个完整任务（AI context 有限），对照 REST 6 参数做 **AI 友好参数形态**（见 8.2.1 ①）。
- **结构化错误返回**：失败返回可读原因（AI 能修正），不抛裸异常。
- **工具注册清单**：本期仅 report 查询；后续能力登记管理，避免工具泛滥。

**⑥ 测试（P1）**
- 单测：参数校验、白名单、错误返回。
- **协议集成测试**：自动化 `initialize → tools/list → tools/call`（非手工 curl）。
- **越权测试**：不同权限账号调用同一工具必须返回不同数据。
- 性能：限流阈值、大结果集延迟基准。

**⑦ 架构形态（决策）**
- **内嵌 + 网关前置**：ops 内嵌 MCP Server，API 网关统一收口 `/mcp`（鉴权/限流/审计/脱敏在网关层），服务端保持简单。
- **扩展点**：未来 metric 指标数据需进 MCP 时，ops 工具内部**跨服务调 metric REST 聚合**，客户端仍只连一个 `/mcp`——**不做独立 MCP 网关服务**（当前仅 ops 一个提供方，过早）。

**⑧ 仓职责（决策）**
- **仅 ops 提供 MCP**：看板查询消费统一走 ops `/mcp` 单入口。
- **metric 不本期开发**：其 POC（`mcp_test` 分支）保留为**团队赋能教材**（含 `MCP搭建指导文档.md`）。
- **sync 不开发**：采集写入侧无查询消费面，职责不匹配。

## 9. 安全设计

| 项 | 措施 |
| --- | --- |
| OBS 凭证 | 只读 AK/SK，存 SeaTunnel 参数（`${OBS_AK}/${OBS_SK}`，与既有工作流一致），不下沉代码 |
| 动态 SQL（ops 查询） | 表名/列名双重白名单（登记表 + 数据资产列信息） |
| SeaTunnel transform | `TestReportReader` 复用 `ParseTestcase`/`TestCaseMetadataParser` 的 OBS 读取防护；路径三段 ID 白名单/长度校验防穿越；sdi 清洗为纯配置（无自定义代码） |
| MCP 端点 | **上线硬门禁：正式环境前必须完成鉴权，不允许裸奔上线**。**MCP OAuth 2.1 授权码流 + refresh 自动续期**（客户配置一次长期有效）：gateway 扩展为授权服务器（`/authorize` `/token` `/register` + 元数据），ops `/mcp` 为 OAuth2 Resource Server + 服务端 token 兜底 + 工具级 RBAC + 行级数据权限继承（防越权后门）+ 限流 + 审计（调用日志表 8.2.2 + Metrics + 告警），详见 8.2.3 |

## 10. 待确认事项（需用户/PM 确认）

| # | 事项 | 当前假设/建议 | 影响 |
| --- | --- | --- | --- |
| T1 | **一个模板对应多条流水线（一对多）** | 已确认，`pipeline_ids` 逗号分隔 | 采集范围过滤 |
| T2 | **TestReportReader 轻量 transform 开发方式** | 插件仓**已定位**：`nane/openlibing-seatunnel`（`openlibing-seatunnel-plugins` 模块，**独立包 `transform/readtestreport`**，与 `parsetestcase`/`parsefilecoverage` 命名风格一致，仅复用其 OBS 列举/下载逻辑，输出原文，无解析逻辑）；**插件仓为同事个人仓（nane），开发/发布/合入需与仓主确认协作方式** | raw 采集核心，需仓主配合 |
| T3 | **SeaTunnel 读模板登记范围的方式** | **已确认：Doris 专用登记表 `dm_rd_efc_template_registry`**（`table_type='test_report'`，6.1），采集 source JOIN 它（Doris 账号已有），**免 MySQL 账号**；Catalog 直连/DS 参数化/Doris 配置表候选已收敛（见 T11） | 已定 |
| T4 | **GitHub/GitCode 流水线来源表** | **已确认（测试库实测）：三平台独立表，数据不混存 codearts 表**。codearts=`sdi_rd_efc_pipeline_run_clean_codearts`（hex 三 ID + `step_build_job_id` + `step_daily_build_number`，OBS job 目录=`CONCAT(step_build_job_id,'_',REPLACE(step_daily_build_number,'.','_'))`）；GitHub=`sdi_rd_efc_workflow_run_job_github`（run/job 为数字 ID，OBS job 目录=纯数字 `workflow_job_id` 无后缀）；GitCode=`sdi_rd_efc_workflow_run_raw_gitcode`（hex ID + `job_id` 字段，OBS 后缀待确认）。工作流①/② source 按平台映射三 ID + 起止时间（字段名以测试库核实为准）；**调试数据（adabab pipeline）实测为 codearts 平台（git_type=codehub）** | 已定（GitCode 后缀待确认） |
| T5 | **DS 工作流创建与发布** | **已确认：由用户负责**。先在测试环境（beta）充分验证（造数联调/幂等/补采），验证通过后发布正式环境；设计文档提供工作流定义、rawScript 与 cron 供创建参考。**正式环境上线门禁：测试环境全链路调通（采集+清洗+ops REST 消费）后才上正式；MCP 除外（可后续迭代单独上）** | 已定（含门禁） |
| T6 | **上游 JSON schema 完整清单（每模板一份）** | 本期仅 `triton_model_performance`；后续模板按登记制扩展 | 插件/表扩展 |
| T7 | **模板登记数据维护入口** | **已确认：本期由开发手动 SQL 登记**——INSERT `dm_rd_efc_template_registry`（`table_type='test_report'`，含 `pipeline_ids` 配置）+ 建 raw/sdi 表（DDL 见 6.3/6.4），不做管理页面；登记清单示例见 7.5 | 已定 |
| T8 | **MCP 端点鉴权/限流方案** | **已修订（2026-08-24）**：按 8.2.3 生产级架构执行——**MCP OAuth 2.1（gateway 扩展为授权服务器 + ops `/mcp` 为 OAuth2 Resource Server + refresh 自动续期，客户配置一次长期有效）** + 服务端 token 兜底 + RBAC + 行级数据权限 + 限流 + 调用日志审计；**上线硬门禁：正式环境前必须完成鉴权，不允许裸奔上线** | 已定 |
| T9 | **是否需平台 UI（ops-web）展示** | 本期仅 API/MCP | 前端排期 |
| T10 | **报告上传时效确认** | **已确认（暂定）**：窗口默认 **24h**；后续业务有需要可调大 `${report_window_hours}`（DS 参数）重跑补采，无需改代码 | 已定（暂定 24h） |
| T11 | **采集范围来源（已定）** | **已确认：Doris 专用登记表**（`dm_rd_efc_template_registry` + `table_type='test_report'`，6.1）；采集/消费共读，无 MySQL 依赖、无双处维护。曾评估：Catalog 直连（正式环境无 MySQL 只读账号且实测 `SHOW CATALOGS` 仅 internal）、DS 参数化（双处维护）、MySQL 登记表（语义不符）均被否决 | 已定 |

## 11. 验证方式

1. **SeaTunnel transform 单测**：OBS 列举/下载 mock、原始 JSON 整份输出（不解析）、路径三段 ID 构造、XXE 防护。
2. **链路验证（造数）**：造 `triton-model-performance_test.json`（外层数组）+ 对应流水线记录 → DS 测试环境手动触发工作流① → `raw_test_report` 有原始 JSON → 触发工作流② → `sdi_rd_efc_test_report_<模板名>` 有数 → ops `/report/data/query` 命中 → MCP `initialize → tools/list → tools/call` 三步验证。
3. **幂等验证**：重复触发两个工作流，已采集/已清洗的不再处理、各表行数不翻倍。
4. **原始数据保留验证**：`raw_test_report.data_json` 与 OBS 文件内容一致（JSON 原文比对），支撑追溯/重放。
5. **编译**：ops `mvn compile/test` 通过（IDEA 内置 Maven Wrapper 全路径 mvn.cmd）。

## 12. 代码/配置清单

### 12.1 SeaTunnel 插件工程（`nane/openlibing-seatunnel`，个人仓需仓主配合）

| 文件 | 说明 |
| --- | --- |
| `transform/readtestreport/TestReportReaderTransform.java`（复用 `parsetestcase` 的 OBS 列举/下载逻辑） | 在插件仓**独立包 `transform/readtestreport`** 新增轻量类：OBS 定向列举 + 下载测试报告 JSON → **原始 JSON 整份输出**（不解析、不展开）；sdi 清洗复用既有 `JsonArrayExpandTransform` + Sql 纯配置 |
| 插件构建/发布 | 随既有 SeaTunnel 插件部署流程 |

### 12.2 openlibing-docs（本仓归档）

| 文件 | 说明 |
| --- | --- |
| `spec/openlibing-ops/task_design/test-report-store-consume/design.md` | 本设计文档 |
| SQL 执行（代码仓无 SQL 脚本归档惯例，**直接操作数据库**） | Doris 登记表建表 DDL（6.1）+ raw 表 DDL（6.3）+ sdi 模板表 DDL（6.4）+ 登记 INSERT（7.5），均以本设计文档为准执行 |
| DS 工作流定义 | SeaTunnel rawScript + SQL 任务 + cron（供 DS 控制台创建） |

### 12.3 openlibing-ops

| 文件 | 说明 |
| --- | --- |
| `api/controller/ReportController.java` | `/report/template/list` + `/report/data/query` |
| `api/request/report/*`、`api/response/report/*` | 请求/响应体 |
| `app/service/report/ReportQueryService.java` | 模板+字段元数据查询（含 repoUrls）+ 动态数据查询（白名单 WHERE + 分页） |
| `domain/mapper/report/ReportTemplateModelMapper.java` | 查 Doris 登记表 `dm_rd_efc_template_registry` 定位模板/真实表名 |
| `domain/mapper/report/DorisMetaMapper.java` + `ReportDataMapper.java` | Doris information_schema 列信息 + 动态数据查询 |
| `domain/model/report/TemplateRegistryModel.java` | 登记表实体（替代 MySQL `ThirdApiDataModel`） |
| `api/mcp/McpServerConfig.java` + `ReportMcpTools.java` | MCP 工具（方法级 @DataSource） |
| `pom.xml` / `application.yaml` | spring-ai-bom 1.1.8 + starter + mcp server 配置 |

---

## 13. 方案演进与否决记录

> 设计过程经多轮评审与 PM 对齐，以下方案被**替代或否决**，记录留存备查；**正文仅保留最终确定方案**。

| # | 被否决/被替代方案 | 否决/替代原因 | 最终采用 |
| --- | --- | --- | --- |
| R1 | sync 侧 xxl-job 采集（`@XxlJob` + 扩展 `ObsUtilClient` + `DynamicDorisService` 写 Doris） | PM 否决：看板数据量过大，xxl-job 无法满足；后续所有需求弃用 xxl-job（AGENTS.md 已固化） | DS 两工作流 + SeaTunnel + `TestReportReader` 轻量 transform（raw 采集）+ `JsonArrayExpand`/`Sql`（sdi 清洗） |
| R2 | 平台侧解析 metadata xml 取归属字段 | 既有 DS+SeaTunnel 链路已解析存储（repo_url 已在 sdi raw 表、起止时间在 clean 表），不重复建设 | source JOIN 现有表补齐归属 |
| R3 | 表名去掉 `rd_efc` 中缀（`sdi_test_report_triton_model_performance`） | 数据中台（Doris）统一 `rd_efc` 中缀（MySQL 不遵循） | `sdi_rd_efc_test_report_<模板名>` |
| R4 | 文件级已处理表（MySQL `tbl_third_api_test_report_process_record`，objectKey 幂等） | 采集迁 DS+SeaTunnel 后改为流水线执行级增量，文件级表不再需要 | 时间窗口 + raw/sdi 反查 + `source_end_time` 重试时间比较（6.5/7.4） |
| R5 | 已采集流水线三态台账表（Doris `sdi_rd_efc_test_report_scan_record`，status 0/1/2 + first/last_scan_time） | PM 决策：能不新增表就不新增 | 时间窗口 + raw/sdi 表反查 + 重试时间比较（无显式状态，代价见 6.5） |
| R6 | 登记表镜像到 Doris（`dm_rd_efc_test_report_template` + 同步任务）；Doris MySQL Catalog 跨库直连读 MySQL 登记表 | 镜像方案增加表/同步任务/延迟/镜像过期维护点；Catalog 方案正式环境无 MySQL 只读账号（实测 `SHOW CATALOGS` 仅 internal），且复用 `tbl_third_api_data_model` 语义不符 | **Doris 专用登记表 `dm_rd_efc_template_registry`**（6.1，`table_type` 区分类型），采集/消费共读、零 MySQL 依赖 |
| R7 | SeaTunnel 原生双 source（Doris + MySQL 并行输入） | 多 source schema 不一致无法 union，跨源过滤需自定义 transform，成本高 | Doris 专用登记表 `dm_rd_efc_template_registry`（source 仍为单 Jdbc，JOIN 过滤） |
| R8 | 报告前缀 = `tableName + "_"`（`sdi_rd_efc_test_report_triton_model_performance_`） | 与上游命名规范不符（模板名 kebab + 下划线） | `kebab(模板名)_`（`triton-model-performance_`） |
| R9 | **单工作流 OBS 直读解析写 dwr 事实表**（v2 方案：TestReportParser 一次读 OBS + 展开 → 写 `dwr_rd_efc_<模板名>`） | 用户评审：不符合平台既有 **raw→sdi→dwi/dm/dwr 分层惯例**（`raw_workflow_source_github`/`raw_workflow_runs_github` 等均为「原始 JSON 先落 raw，再清洗」）；原始数据不可追溯、无法重放重清洗；解析逻辑耦合在插件中 | **raw→sdi 两段式**（v3）：工作流① 轻量 `TestReportReader`（复用 `ParseTestcase` OBS 读取，仅整份读原文）→ `raw_test_report`；工作流② `JsonArrayExpand` + `Sql` 纯配置清洗（**不新增解析插件**）→ 每模板一张 `sdi_rd_efc_test_report_<模板名>`；消费读 sdi 表 |
