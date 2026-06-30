# 开源组件运营总览看板 — 技术设计

> 模块：`openlibing-ops` 后端 + DolphinScheduler ETL
> 数据源：Doris（OLAP） / MySQL（指标 4 源端 `pipeline_info`）
> 文档版本：v1.0
> 编写日期：2026-06-30

---

## 1 状态说明

### 1.1 文档信息

| 项 | 内容 |
|---|---|
| 文档名称 | 开源组件运营总览看板技术设计 |
| 编写目的 | 在 `openlibing-ops` 后端与 DolphinScheduler ETL 上落地 11 个开源组件运营指标的端到端实现，覆盖主表聚合、资源卡片、Nightly 卡片、链接配置 CRUD、4 类明细下钻 |
| 适用范围 | `openlibing-ops` 后端服务（Spring Boot + MyBatis）+ `openlibing-ops-web` 前端 + DolphinScheduler ETL（SQL 节点 + Python 节点） |
| 关联需求 | `开源组件运营总览-需求设计说明书.md` v1.0（2026-06-29） |
| 关联接口 | `开源组件运营总览-后端接口文档.md`（交叉参考，**以最新代码为准**） |

### 1.2 变更记录

| 版本 | 日期 | 变更人 | 变更内容 |
|---|---|---|---|
| v1.0 | 2026-06-30 | AI 辅助生成 | 初版，端到端覆盖 11 个指标的实现设计 |

### 1.3 模块定位与上下游

**模块定位**：`openlibing-ops` 是 OpenLibing 工作流平台的运维与运营侧后端，负责提供主表/资源/Nightly 三大运营总览能力。本期新增「开源组件运营总览」独立看板（`/ops-overview/*` + `/common/detail` 多态分发），覆盖 11 个指标从 ETL 到接口到前端展示的完整链路。

**上游依赖**：

| 上游模块 | 依赖内容 |
|---|---|
| 已有 Doris DWI/DM 表 | `sdi_repo_info` / `sdi_project_info` / `sdi_project_common_account_info` / `dwi_rd_project_pipeline_relation` / `dwr_rd_efc_pipeline_run_fact` / `dwr_rd_efc_pipeline_run_job_fact` / `dwr_rd_efc_build_fact_nightly_test_case_pipeline_run` / `dm_rd_efc_build_dim_nightly_pipeline_day` / `dm_rd_efc_pr_sum_pipeline_statistics_day` / `dwi_code_scan_language` 等 |
| 已有 SCC 任务 | `4sdi写入dwi.py`（用于提供 `dwi_code_scan_language` 最新语言数据） |
| MySQL `pipeline_info` | DataX/DS 同步到 `raw_pipeline_info`，作为指标 4 的源端 |
| 内部 API 录入 | `dim_component_link_config`（5 列链接配置）、`dim_project_resource_total`（资源总量）由后端 API 录入 |

**下游消费者**：

| 下游模块 | 消费内容 |
|---|---|
| `openlibing-ops-web` 前端 | 6 个接口的请求/响应，主表 40+ 字段渲染、卡片汇总、明细下钻、链接配置表单 |
| OpenLibing 工作流平台 | 通过 `/common/detail` 多态分发被统一调度，复用 DetailService 模式 |
| 第三方报表 | 仅运维内部使用，无对外 SDK/导出 |

### 1.4 范围与非范围

| 范围 | 说明 |
|---|---|
| **IN** | 11 个指标的 ETL 调度、SQL/Python 脚本、后端 6 个接口、DTO 定义、Mapper XML、DetailService 多态分发、链接配置 CRUD、资源总量录入（写时校验） |
| **OUT** | 前端 UI 细节（仅约定接口契约与字段映射，不重做页面）；指标 4 源端 `pipeline_info` 同步任务本身（依赖现有 DataX/DS 同步链路）；权限模型底层实现（依赖平台 RBAC） |

---

## 2 实体设计

本章节梳理 `openlibing-ops` 后端为「开源组件运营总览」看板新增/复用的核心实体。实体按聚合根归属到主表/卡片/明细/配置四类业务上下文。

### 2.1 实体全景

| 序号 | 实体 | 聚合上下文 | 类型 | 数据源/落盘 | 备注 |
|---|---|---|---|---|---|
| 1 | `ProjectOverview`（项目运营总览） | 主表 | 聚合 | DM 表 `dm_project_quality_overview_day` + DWI 实时聚合 | 主表一行 = 一个项目 |
| 2 | `RepoQualityScan`（仓库质量扫描结果） | 主表/明细 | 实体 | DWI `dwi_repo_quality_scan_day` | 一行 = 一个仓库一次扫描 |
| 3 | `PipelineEventTrigger`（流水线自动修复触发器） | 主表 | 实体 | SDI `sdi_pipeline_event_trigger` | 一行 = 一个 eventTrigger 元素 |
| 4 | `RepoPipelineQuality`（仓库流水线质量） | 主表/明细 | 实体 | DWI `dwi_repo_pipeline_quality_day` | 一行 = 一个仓库一日聚合 |
| 5 | `ProjectResourceIndicator`（项目资源指标） | 主表/卡片 | 宽表 | DWI `dwi_project_resource_indicator_day` | 一行 = 一个项目一日聚合 |
| 6 | `ProjectNightlyResource`（Nightly 资源） | 卡片 | 实体 | DWI `dwi_project_nightly_resource_day` | 一行 = 一个项目一日 Nightly 聚合 |
| 7 | `ProjectResourceTotal`（项目资源总量） | 卡片/录入 | DIM 实体 | DIM `dim_project_resource_total` | 一行 = 一个项目一个 pipelineType |
| 8 | `ComponentLinkConfig`（组件链接配置） | 链接配置 | 配置 | DIM `dim_component_link_config` | 一行 = 一个项目一个 colKey |
| 9 | `RepoDetail`（仓库配置明细） | 明细 | 视图对象 | 多表 JOIN 计算 | 一行 = 一个仓库的指标 1-6 |
| 10 | `PipelineResourceDetail`（流水线资源明细） | 明细 | 视图对象 | `dwr_rd_efc_pipeline_run_fact` JOIN | 一行 = 一条流水线 |
| 11 | `PipelineRunRecord`（流水线运行记录） | 明细 | 视图对象 | `dwr_rd_efc_pipeline_run_fact` | 一行 = 一次运行 |
| 12 | `NightlyPipelineDetail`（Nightly 流水线明细） | 明细 | 视图对象 | `dwr_rd_efc_build_fact_nightly_test_case_pipeline_run` JOIN | 一行 = 一条 Nightly 流水线 |

### 2.2 关键实体属性

#### 2.2.1 `ProjectOverview`（项目运营总览聚合）

```text
归属聚合：开源组件运营总览看板（主表）
主键：projectId + statDate（取最新 statDate 快照）
核心字段：
  - 基础信息：projectId / projectName / productId / productName / statDate
  - snapshot 段（状态类，DM 表落盘）：
    - 5 列链接配置：ttfhw{DisplayValue,LinkUrl} / envPrepare{...} / incBuild{...} / fullBuild{...} / utExec{...}
    - 指标1 编码风格可视：styleVisibleRate（0-1）
    - 指标2 代码检查：precommitRate（0-1）
    - 指标3 代码检查规则数：checkRulesTotal（INT）
    - 指标3 分语言平均：pythonRulesAvg / cppRulesAvg / javaRulesAvg（0-1，等权AVG）
    - 指标4 自动修复：autoFixRate（0-1）
    - 指标5 例外备案：exceptionReviewRate（0-1）
  - stat 段（统计类，实时聚合）：
    - 指标6 PR执行时长：prDurationP90（分钟）
    - 指标7 PR 消耗：prCpuUsage / prNpuUsage / prMemoryUsage（核时/卡时/GB时）
    - 指标7 Nightly 消耗：nightlyCpuUsage / nightlyNpuUsage / nightlyMemoryUsage
    - 指标7 overall 消耗：overallCpuUsage / overallNpuUsage / overallMemoryUsage
    - 指标8 PR 总量：prCpuTotal / prNpuTotal / prMemoryTotal
    - 指标8 Nightly 总量：nightlyCpuTotal / nightlyNpuTotal / nightlyMemoryTotal
    - 指标8 overall 总量：overallCpuTotal / overallNpuTotal / overallMemoryTotal
    - 指标9 PR 使用率：prCpuRate / prNpuRate / prMemoryRate（0-1）
    - 指标9 Nightly 使用率：nightlyCpuRate / nightlyNpuRate / nightlyMemoryRate
    - 指标9 overall 使用率：overallCpuRate / overallNpuRate / overallMemoryRate
    - 指标7 平均消耗：prCpuAvg / prNpuAvg / nightlyCpuAvg / nightlyNpuAvg / overallCpuAvg / overallNpuAvg
    - 指标10 编译成功率：nightlyBuildSuccessRate（0-1）
    - 指标11 版本可用度：nightlyVersionAvailabilityRate（0-1）
```

#### 2.2.2 `RepoQualityScan`（仓库质量扫描结果）

```text
归属聚合：代码仓扫描（指标1-3 ETL 产物）
主键：repoId + branchName + scanDate（UNIQUE KEY）
核心字段：
  - 基础：repoId / repoGitUrl / repoName / branchName / isDefaultBranch / scanDate / scanTime
  - 指标1：top1Language / top2Language / top1CodeLines / top2CodeLines
         top1HasStyleCfg / top2HasStyleCfg / styleOverallPass（0/1/3）
  - 指标2：hasPreCommitCfg / precommitFile
  - 指标3 - Python：pythonRuffDefaultRules / pythonRuffEnabledRules / pythonRuffExtraRules
  - 指标3 - C/C++：cppClangFormatCustom / cppClangTidyChecks
  - 指标3 - Java：javaCheckstyleModules / javaSpotlessConfigured / javaSpotbugsConfigured / javaGoogleFormatFound
```

#### 2.2.3 `ProjectResourceTotal`（项目资源总量 DIM 实体）

```text
归属聚合：资源总量录入（指标8）
主键：productId + projectId + pipelineType（UNIQUE KEY）
核心字段：
  - productId / productName / projectId / projectName
  - pipelineType（Pr / Nightly）
  - type（0=云下，1=云上）
  - groupId（云上同组共享资源池标识，如 PTA_GROUP / OPENEULER_GROUP）
  - cpuTotalCores（核，DOUBLE） / npuTotalCards（卡，DOUBLE） / memoryTotalGb（GB，DOUBLE）
  - updateTime / updatedBy
```

#### 2.2.4 `ComponentLinkConfig`（组件链接配置 DIM 实体）

```text
归属聚合：链接配置 CRUD（接口 4-5）
主键：projectId + colKey（UNIQUE KEY）
核心字段：
  - projectId
  - colKey（ttfhw / envPrepare / incBuild / fullBuild / utExec，5 列固定枚举）
  - displayValue（前端展示文案）
  - linkUrl（点击跳转 URL）
  - updateTime / updatedBy
```

#### 2.2.5 `RepoDetail`（仓库配置明细视图）

```text
归属聚合：仓库下钻明细（接口 6 / category=ops-repo-detail）
主键：repoId（无时间维度，按最新扫描快照）
核心字段：
  - repoId / repoName
  - stylePass / precommitPass（0/1）
  - rulesTotal（pythonRuff + cppClangTidy + javaCheckstyle + 31*googleFormat）
  - pythonRulesTotal / cppRulesTotal / javaRulesTotal
  - hasAutoFix / usesProperCodecheck
  - prDuration（分钟，P90）
  - styleDetail / precommitDetail / rulesDetail / autoFixDetail / codecheckDetail（拼接文案）
  - noPipelineReason（无 PR 流水线时的原因文案）
```

#### 2.2.6 `PipelineResourceDetail`（流水线资源明细视图）

```text
归属聚合：流水线资源下钻（接口 6 / category=ops-resource-detail）
主键：pipelineId
核心字段：
  - pipelineId / pipelineName
  - vcpu / npu（该流水线总消耗，核时/卡时）
  - vcpuAvg / npuAvg（平均消耗 = 总消耗/运行次数）
数据源差异：
  - PR：dwi_rd_project_pipeline_relation JOIN dwr_rd_efc_pipeline_run_fact
  - Nightly：sdi_version_pipeline_base_info JOIN dwr_rd_efc_pipeline_run_fact
```

### 2.3 实体关系图

```text
                        ┌─────────────────────┐
                        │   ProjectOverview   │  (聚合根，主表)
                        └──────────┬──────────┘
                                   │ 1:N
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
   ┌─────────────────┐  ┌───────────────────┐  ┌─────────────────────┐
   │ RepoQualityScan │  │ RepoPipelineQuality│  │ ProjectResource     │
   │ (仓库质量)       │  │ (流水线质量)        │  │ Indicator (宽表)     │
   └────────┬────────┘  └──────────┬─────────┘  └──────────┬──────────┘
            │ 1:N                  │ 1:N                   │ 引用
            ▼                      ▼                       ▼
   ┌─────────────────┐  ┌───────────────────┐  ┌─────────────────────┐
   │PipelineEvent    │  │ PipelineResource  │  │ ProjectResource     │
   │Trigger          │  │ Detail (视图)      │  │ Total (DIM, 指标8)  │
   └─────────────────┘  └───────────────────┘  └─────────────────────┘

   ┌─────────────────────┐          ┌──────────────────────┐
   │ ComponentLinkConfig │          │ NightlyPipelineDetail│
   │ (DIM, 链接配置)       │          │ (视图, 指标10-11)     │
   └─────────────────────┘          └──────────────────────┘
```

### 2.4 实体一致性约束

| 约束 | 说明 |
|---|---|
| 主键唯一 | 所有 DWI/DM/DIM 表使用 UNIQUE KEY + `enable_unique_key_merge_on_write=true`，保证幂等 upsert |
| 时间口径 | 指标7 PR 用 `DATE(pipeline_start_time)`，Nightly 用 `DATE(pipeline_end_time)`，指标10/11 用 `DATE(pipeline_run_endtime)`，指标6 用 `merged_at` |
| 工作日过滤 | 指标11 版本可用度只统计 `WEEKDAY()<5 OR 节假日表 dim_holiday` |
| 云上同组使用率一致 | `pr_group_agg` / `nightly_group_agg` 按 group_id 聚合后 LEFT JOIN 同组项目，保证同组 `pr_cpu_usage_rate` 数值一致 |

---

## 3 数据库表设计

本章梳理本期新建/复用的所有 Doris 表，覆盖 RAW → SDI → DWI → DM → DIM 全部分层，并列出每个表的关键索引与字段定义。

### 3.1 分层架构概览

```text
RAW（DUPLICATE）        raw_repo_quality_scan
                       raw_pipeline_info
                              ↓
SDI（DUPLICATE）        sdi_pipeline_event_trigger
                              ↓
DWI（UNIQUE+merge_on_write）
                       dwi_repo_quality_scan_day
                       dwi_repo_pipeline_quality_day
                       dwi_project_nightly_resource_day
                       dwi_project_resource_indicator_day
                              ↓
DM（UNIQUE+merge_on_write）  dm_project_quality_overview_day
                              ↓
DIM（UNIQUE+merge_on_write）  dim_component_link_config
                              dim_project_resource_total
```

> 所有 DWI/DM/DIM 表开启 `enable_unique_key_merge_on_write=true`，INSERT 即覆盖，实现幂等 upsert。

### 3.2 RAW 层表

#### 3.2.1 `raw_repo_quality_scan`（指标1-3 扫描原始 JSON）

```sql
CREATE TABLE IF NOT EXISTS raw_repo_quality_scan (
    repo_id           INT           COMMENT '仓库ID',
    repo_git_url      VARCHAR(500)  COMMENT '仓库Git URL',
    repo_name         VARCHAR(200)  COMMENT '仓库名',
    branch_name       VARCHAR(200)  COMMENT '分支名',
    is_default_branch TINYINT       COMMENT '是否默认分支 0:否 1:是',
    scan_time         DATETIME      COMMENT '扫描时间',
    data_json         TEXT          COMMENT '质量检查原始结果JSON'
) ENGINE=OLAP
DUPLICATE KEY (repo_id, branch_name)
DISTRIBUTED BY HASH(repo_id) BUCKETS 10
PROPERTIES ("replication_num" = "3");
```

**data_json 结构**：

```json
{
  "scan_time": "2026-06-05 10:00:00",
  "top_languages": [{"name": "Python", "code_lines": 50000, "ratio": 0.55}, ...],
  "code_style": {"<lang>": {"language": "Python", "is_top2": true, "has_config": true}},
  "pre_commit": {"has_config": true, "config_file": ".pre-commit-config.yaml"},
  "check_rules": {"<lang>": {"<tool>": {"status": "ok"}}}
}
```

#### 3.2.2 `raw_pipeline_info`（指标4 MySQL 同步原始数据）

```sql
CREATE TABLE IF NOT EXISTS raw_pipeline_info (
    id                 BIGINT       COMMENT '流水线ID(MySQL snowflake)',
    source_pipeline_id VARCHAR(255) COMMENT '源流水线ID',
    pipeline_name      VARCHAR(255) COMMENT '流水线名称',
    project_id         INT          COMMENT '项目ID',
    group_id           VARCHAR(255) COMMENT '流水线分组ID',
    config_json        JSON         COMMENT '流水线配置JSON(含eventTriggers)',
    sync_time          DATETIME     COMMENT '同步时间'
) ENGINE=OLAP DUPLICATE KEY (id)
DISTRIBUTED BY HASH(id) BUCKETS 10
PROPERTIES ("replication_num" = "3");
```

> 由 DataX/DS 同步任务从 MySQL `pipeline_info` 表增量写入，频率建议每日一次或监听 binlog。

### 3.3 SDI 层表

#### 3.3.1 `sdi_pipeline_event_trigger`（指标4 eventTriggers 展开）

```sql
CREATE TABLE IF NOT EXISTS sdi_pipeline_event_trigger (
    source_pipeline_id VARCHAR(255) COMMENT '源流水线ID',
    project_id         INT          COMMENT '项目ID',
    trigger_index      TINYINT      COMMENT '触发器在数组中的索引(0-9)',
    is_enable          VARCHAR(10)  COMMENT '是否启用(true/false)',
    action_type        VARCHAR(10)  COMMENT '触发类型(0:自动修复 1:PR 2:定时 3:手动)',
    event_type         VARCHAR(10)  COMMENT '事件类型'
) ENGINE=OLAP DUPLICATE KEY (source_pipeline_id)
DISTRIBUTED BY HASH(source_pipeline_id) BUCKETS 10
PROPERTIES ("replication_num" = "3");
```

**说明**：Doris 不支持 JSON 数组动态 UNNEST，使用 `get_json_string(config_json, '$.eventTriggers[0..9]')` 索引展开 10 个位置后 UNION ALL 写入。每次 SQL 调度 TRUNCATE 后 INSERT 全量刷新。

### 3.4 DWI 层表

#### 3.4.1 `dwi_repo_quality_scan_day`（指标1-3 仓库级日聚合）

```sql
CREATE TABLE IF NOT EXISTS dwi_repo_quality_scan_day (
    repo_id            INT,
    repo_git_url       VARCHAR(500),
    repo_name          VARCHAR(200),
    branch_name        VARCHAR(200),
    is_default_branch  TINYINT,
    scan_date          DATE,
    scan_time          DATETIME,
    -- 指标1
    top1_language          VARCHAR(50),
    top2_language          VARCHAR(50),
    top1_code_lines        INT,
    top2_code_lines        INT,
    top1_has_style_cfg     TINYINT,
    top2_has_style_cfg     TINYINT,
    style_overall_pass     TINYINT COMMENT '0:否 1:是 3:无有效语言',
    -- 指标2
    has_pre_commit_cfg     TINYINT,
    pre_commit_file        VARCHAR(100),
    -- 指标3 - Python
    python_ruff_default_rules INT,
    python_ruff_enabled_rules INT,
    python_ruff_extra_rules   INT,
    -- 指标3 - C/C++
    cpp_clang_format_custom   INT,
    cpp_clang_tidy_checks     INT,
    -- 指标3 - Java
    java_checkstyle_modules   INT,
    java_spotless_configured  TINYINT,
    java_spotbugs_configured  TINYINT,
    java_google_format_found  TINYINT,
    create_time               DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=OLAP
UNIQUE KEY (repo_id, branch_name, scan_date)
DISTRIBUTED BY HASH(repo_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

#### 3.4.2 `dwi_repo_pipeline_quality_day`（指标4-5 仓库流水线级日聚合）

```sql
CREATE TABLE IF NOT EXISTS dwi_repo_pipeline_quality_day (
    project_id             INT,
    repo_id                INT,
    stat_date              DATE,
    repo_name              VARCHAR(255),
    -- 指标4
    has_auto_fix           TINYINT      COMMENT '0:否 1:是',
    auto_fix_pipeline_ids  VARCHAR(1000) COMMENT '启用auto-fix的流水线ID列表',
    -- 指标5
    has_old_codecheck      TINYINT      COMMENT '是否存在旧版codecheck任务',
    has_new_codecheck      TINYINT      COMMENT '是否存在新版检查任务(pre-commit/lintrunner)',
    uses_proper_codecheck  TINYINT      COMMENT '采用注释化屏蔽且下线例外备案',
    old_codecheck_jobs     VARCHAR(1000),
    new_codecheck_jobs     VARCHAR(1000),
    create_time            DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=OLAP
UNIQUE KEY (project_id, repo_id, stat_date)
DISTRIBUTED BY HASH(project_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

#### 3.4.3 `dwi_project_nightly_resource_day`（指标7 Nightly 资源日聚合）

```sql
CREATE TABLE IF NOT EXISTS dwi_project_nightly_resource_day (
    project_id     INT,
    stat_date      DATE,
    project_name   VARCHAR(255),
    product_id     INT,
    product_name   VARCHAR(255),
    cpu_seconds    BIGINT,
    npu_seconds    BIGINT,
    memory_seconds BIGINT,
    update_time    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=OLAP
UNIQUE KEY (project_id, stat_date)
DISTRIBUTED BY HASH(project_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

#### 3.4.4 `dwi_project_resource_indicator_day`（指标7+9+10+11 项目日聚合核心宽表）

```sql
CREATE TABLE IF NOT EXISTS dwi_project_resource_indicator_day (
    project_id   INT,
    stat_date    DATE,
    project_name VARCHAR(255),
    product_id   INT,
    product_name VARCHAR(255),
    pr_group_id        VARCHAR(255),
    nightly_group_id   VARCHAR(255),
    -- 指标7: PR/Nightly 消耗（秒）
    pr_cpu_seconds       BIGINT,
    pr_npu_seconds       BIGINT,
    pr_memory_seconds    BIGINT,
    nightly_cpu_seconds  BIGINT,
    nightly_npu_seconds  BIGINT,
    nightly_memory_seconds BIGINT,
    -- 指标9: PR/Nightly 使用率（0-1）
    pr_cpu_usage_rate    DOUBLE,
    pr_npu_usage_rate    DOUBLE,
    pr_memory_usage_rate DOUBLE,
    nightly_cpu_usage_rate    DOUBLE,
    nightly_npu_usage_rate    DOUBLE,
    nightly_memory_usage_rate DOUBLE,
    -- 指标10: 编译成功率
    nightly_build_success_rate DOUBLE,
    -- 指标11: 版本可用度
    nightly_version_availability_rate DOUBLE,
    update_time DATETIME
) ENGINE=OLAP
UNIQUE KEY (project_id, stat_date)
DISTRIBUTED BY HASH(project_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

### 3.5 DM 层表

#### 3.5.1 `dm_project_quality_overview_day`（指标1-5 项目级日快照）

```sql
CREATE TABLE IF NOT EXISTS dm_project_quality_overview_day (
    project_id              INT,
    stat_date               DATE,
    project_name            VARCHAR(255),
    product_id              INT,
    product_name            VARCHAR(255),
    -- 指标1
    style_visible_rate      DOUBLE COMMENT '编码风格可视满足率 0-1',
    -- 指标2
    precommit_rate          DOUBLE COMMENT '代码检查满足率 0-1',
    -- 指标3
    check_rules_total       INT    COMMENT '项目级规则数总和(含 google-java-format 31)',
    python_rules_avg        DOUBLE COMMENT 'Python 平均规则数',
    cpp_rules_avg           DOUBLE COMMENT 'C/C++ 平均规则数',
    java_rules_avg          DOUBLE COMMENT 'Java 平均规则数',
    -- 指标4
    auto_fix_rate           DOUBLE COMMENT '自动修复满足率 0-1',
    -- 指标5
    exception_review_rate   DOUBLE COMMENT '例外备案满足率 0-1',
    update_time             DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=OLAP
UNIQUE KEY (project_id, stat_date)
DISTRIBUTED BY HASH(project_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

> 每日调度产生新行不会覆盖历史，前端查询时取最新 `stat_date` 快照。Doris 不支持 UNIQUE KEY 表 ALTER 添加非空字段，`python_rules_avg` / `cpp_rules_avg` / `java_rules_avg` 必须 `DEFAULT NULL`。

### 3.6 DIM 层表

#### 3.6.1 `dim_component_link_config`（5 列链接配置）

```sql
CREATE TABLE IF NOT EXISTS dim_component_link_config (
    project_id     INT,
    col_key        VARCHAR(50)  COMMENT 'ttfhw/envPrepare/incBuild/fullBuild/utExec',
    display_value  VARCHAR(255) COMMENT '前端展示文案',
    link_url       VARCHAR(1000) COMMENT '点击跳转URL',
    update_time    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by     VARCHAR(100)
) ENGINE=OLAP
UNIQUE KEY (project_id, col_key)
DISTRIBUTED BY HASH(project_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

#### 3.6.2 `dim_project_resource_total`（指标8 资源总量）

```sql
CREATE TABLE IF NOT EXISTS dim_project_resource_total (
    product_id        INT,
    project_id        INT,
    pipeline_type     VARCHAR(255) COMMENT 'Pr / Nightly',
    type              INT          COMMENT '0:云下 1:云上',
    group_id          VARCHAR(255),
    product_name      VARCHAR(255),
    project_name      VARCHAR(255),
    cpu_total_cores   DOUBLE       COMMENT 'vCPU 总核数',
    npu_total_cards   DOUBLE       COMMENT 'NPU 总卡数',
    memory_total_gb   DOUBLE       COMMENT '内存总大小 GB',
    update_time       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by        VARCHAR(100)
) ENGINE=OLAP
UNIQUE KEY (product_id, project_id, pipeline_type)
DISTRIBUTED BY HASH(project_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

### 3.7 已有外部表（不在本期 ETL 范围内）

| 表名 | 用途 | 本期使用方式 |
|---|---|---|
| `sdi_repo_info` | 仓库元数据 | 关联 project_id、解析 repo_name |
| `sdi_project_info` | 项目元数据 | 补充 project_name / product_id |
| `sdi_project_common_account_info` | Git 平台认证 token | 按 platform 取 gitcode/gitee/github token + login |
| `code_repo_branch_config` | 人工配置的展示分支 | `show_branch` 优先于 SCC 默认分支扫描 |
| `dwi_code_scan_language` / `sdi_code_scan_language` | SCC 语言扫描结果 | 取 top2 语言 |
| `sdi_repo_branch_info` | 分支最新提交时间 | 增量判断（>当前-3天 才扫描） |
| `sdi_repo_pull_request_info` / `sdi_pr_pipeline_relation` | PR 与流水线映射 | 指标5 PR 流水线链路 |
| `sdi_version_pipeline_base_info` | Nightly 流水线与项目映射 | 指标7 Nightly / 指标10-11 |
| `dwi_rd_project_pipeline_relation` | 项目-仓库-流水线关系 | 指标1 排除无 PR 仓库 / 指标4 关联 / 指标7 PR |
| `dwr_rd_efc_pipeline_run_fact` | 流水线运行事实表 | 指标7 PR / 指标7 Nightly / 指标平均消耗 |
| `dwr_rd_efc_pipeline_run_job_fact` | 流水线 Job 事实表 | 指标5 job 名称匹配 |
| `dwr_rd_efc_build_fact_nightly_test_case_pipeline_run` | Nightly 构建事实表 | 指标10 编译成功率 |
| `dm_rd_efc_build_dim_nightly_pipeline_day` | Nightly 流水线日级去重表 | 指标11 版本可用度 |
| `dm_rd_efc_pr_sum_pipeline_statistics_day` | PR 流水线统计表（P90 来源） | 指标6 PR E2E P90 |
| `dim_holiday` | 节假日表 | 指标11 工作日过滤 |

### 3.8 表清单总览

| 层 | 表名 | 类型 | 用途 | 来源 |
|---|---|---|---|---|
| RAW | `raw_repo_quality_scan` | DUPLICATE | 指标1-3 扫描原始 JSON | Python 脚本 |
| RAW | `raw_pipeline_info` | DUPLICATE | 指标4 MySQL 同步原始数据 | DataX/DS |
| SDI | `sdi_pipeline_event_trigger` | DUPLICATE | 指标4 eventTriggers 展开 | SQL |
| DWI | `dwi_repo_quality_scan_day` | UNIQUE+MoW | 指标1-3 仓库级日聚合 | Python |
| DWI | `dwi_repo_pipeline_quality_day` | UNIQUE+MoW | 指标4-5 仓库流水线级日聚合 | SQL |
| DWI | `dwi_project_nightly_resource_day` | UNIQUE+MoW | 指标7 Nightly 资源日聚合 | SQL |
| DWI | `dwi_project_resource_indicator_day` | UNIQUE+MoW | 指标7+9+10+11 项目日聚合 | SQL |
| DM | `dm_project_quality_overview_day` | UNIQUE+MoW | 指标1-5 项目级日快照 | SQL |
| DIM | `dim_component_link_config` | UNIQUE+MoW | 5 列链接配置（API 录入） | API |
| DIM | `dim_project_resource_total` | UNIQUE+MoW | 指标8 资源总量（API 录入） | API |

> **MoW = `enable_unique_key_merge_on_write=true`**

---

## 4 类设计

本章梳理 `openlibing-ops` 后端为本期新增/复用的关键类，覆盖 Controller / Service / DetailService / Factory / Mapper / DTO / 工具类等。

### 4.1 类分层结构

```text
api/controller/        (HTTP 入口层)
  ├─ OpsOverviewController            @RequestMapping("/ops-overview")
  └─ CommonController                 @RequestMapping("/common")
        ↓
app/service/           (应用服务层)
  ├─ OpsOverviewService               4 合 1 主服务（主表/资源卡片/Nightly卡片/链接配置 + 4 个明细列表）
  └─ CommonService                    /common/detail 入口分发
        ↓
domain/service/repo/   (领域服务层)
  ├─ DetailService<T,R>               接口
  ├─ RepoDetailFactory                Spring 注入 List<DetailService> → Map<DetailCommonEnum, DetailService>
  └─ impl/
      ├─ OpsRepoDetailDetailService        category=ops-repo-detail
      ├─ OpsResourceDetailDetailService    category=ops-resource-detail
      ├─ OpsResourceRunsDetailService      category=ops-resource-runs
      └─ OpsNightlyDetailDetailService     category=ops-nightly-detail
        ↓
domain/mapper/         (MyBatis 映射接口层)
  ├─ DmProjectQualityOverviewDayMapper     主表 snapshot 段
  ├─ OpsMainStatMapper                     主表 stat 段（8 个 CTE）
  ├─ DimComponentLinkConfigMapper          链接配置 CRUD
  ├─ OpsRepoDetailMapper                   仓库明细
  ├─ OpsResourceDetailMapper               资源明细/卡片
  ├─ OpsResourceRunMapper                  资源运行记录
  └─ OpsNightlyDetailMapper                 Nightly 明细/卡片
        ↓
resources/mapper/*.xml  (MyBatis SQL XML)
```

### 4.2 Controller 层

#### 4.2.1 `OpsOverviewController`

```java
@RestController
@RequestMapping("/ops-overview")
public class OpsOverviewController {

    @Autowired private OpsOverviewService opsOverviewService;

    @PostMapping("/main")
    public Result<PageResult<OpsOverviewMainResp>> queryMain(
        @Validated @RequestBody OpsOverviewMainReq req) {
        return Result.success(opsOverviewService.queryMain(req));
    }

    @PostMapping("/resource-summary")
    public Result<OpsResourceSummaryResp> queryResourceSummary(
        @Validated @RequestBody OpsResourceDetailReq req) {
        return Result.success(opsOverviewService.queryResourceSummary(req));
    }

    @PostMapping("/nightly-summary")
    public Result<OpsNightlySummaryResp> queryNightlySummary(
        @Validated @RequestBody OpsNightlyDetailReq req) {
        return Result.success(opsOverviewService.queryNightlySummary(req));
    }

    @GetMapping("/link-config")
    public Result<OpsLinkConfigResp> queryLinkConfig(@RequestParam Integer projectId) {
        return Result.success(opsOverviewService.queryLinkConfig(projectId));
    }

    @PostMapping("/link-config")
    public Result<Boolean> saveLinkConfig(@Validated @RequestBody OpsLinkConfigReq req) {
        opsOverviewService.saveLinkConfig(req);
        return Result.success(true);
    }
}
```

#### 4.2.2 `CommonController`

```java
@RestController
@RequestMapping("/common")
public class CommonController {

    @Autowired private CommonService commonService;

    @PostMapping("/detail")
    public <T extends DetailReq> Result<?> queryRepoDetail(
        @Validated @RequestBody T req) {
        return commonService.queryDetail(req.getCategory(), req);
    }
}
```

### 4.3 Service 层

#### 4.3.1 `OpsOverviewService`（4 合 1 主服务）

```java
@Service
public class OpsOverviewService {

    // —— Mapper 依赖 ——
    @Autowired private DmProjectQualityOverviewDayMapper dmProjectQualityOverviewDayMapper;
    @Autowired private OpsMainStatMapper opsMainStatMapper;
    @Autowired private DimComponentLinkConfigMapper dimComponentLinkConfigMapper;
    @Autowired private OpsRepoDetailMapper opsRepoDetailMapper;
    @Autowired private OpsResourceDetailMapper opsResourceDetailMapper;
    @Autowired private OpsResourceRunMapper opsResourceRunMapper;
    @Autowired private OpsNightlyDetailMapper opsNightlyDetailMapper;

    // —— 公开查询方法 ——
    public PageResult<OpsOverviewMainResp> queryMain(OpsOverviewMainReq req);
    public OpsResourceSummaryResp queryResourceSummary(OpsResourceDetailReq req);
    public OpsNightlySummaryResp queryNightlySummary(OpsNightlyDetailReq req);
    public OpsLinkConfigResp queryLinkConfig(Integer projectId);
    public void saveLinkConfig(OpsLinkConfigReq req);
    public PageResult<OpsRepoDetailResp> queryRepoDetail(OpsRepoDetailReq req);
    public PageResult<OpsResourceDetailResp> queryResourceDetailList(OpsResourceDetailReq req);
    public PageResult<OpsResourceRunResp> queryResourceRuns(OpsResourceRunReq req);
    public PageResult<OpsNightlyDetailResp> queryNightlyDetailList(OpsNightlyDetailReq req);

    // —— 关键私有方法 ——
    private void enrichResp(List<OpsOverviewMainResp> snapshotList, List<OpsMainStat> statList,
                            OpsOverviewMainReq req, List<OpsOverviewMainResp> out);
    private void fillLinkConfig(List<OpsOverviewMainResp> rows);
    private Comparator<OpsOverviewMainResp> buildMainComparator(String sortField, String sortRule);
    private int mainFieldComparator(OpsOverviewMainResp a, OpsOverviewMainResp b, String sortField);
    private void applyRounding(OpsOverviewMainResp row);
    private void applyUsageRounding(Double value);   // 保留 4 位
    private void applyAvgRounding(Double value);     // 保留 2 位
    private void applyRulesRounding(Double value);   // 保留 2 位
    private void applyTruncate(Double value);        // 比率类截断 4 位

    // —— 排序白名单常量 ——
    public static final Set<String> MAIN_SORT_ALLOWED_FIELDS;       // 39 字段
    public static final Set<String> REPO_DETAIL_SORT_ALLOWED_FIELDS; // 9 字段
    public static final Set<String> RESOURCE_DETAIL_SORT_ALLOWED_FIELDS; // 4 字段
    public static final Set<String> NIGHTLY_DETAIL_SORT_ALLOWED_FIELDS;  // 2 字段
}
```

**职责**：

| 方法 | 职责 |
|---|---|
| `queryMain` | 主表 40+ 字段聚合查询：snapshot 段（DM 表）+ stat 段（实时 CTE 聚合），Java 层合并 + 内存排序 + subList 分页 |
| `queryResourceSummary` | 资源卡片汇总，云上/云下按 group_id/project_id 分支 |
| `queryNightlySummary` | Nightly 卡片汇总，等权 AVG 各流水线成功率 |
| `queryLinkConfig` / `saveLinkConfig` | 链接配置查询/保存（5 列枚举） |
| `queryRepoDetail` / `queryResourceDetailList` / `queryResourceRuns` / `queryNightlyDetailList` | 4 个明细列表查询（被 4 个 DetailService 调用） |
| `enrichResp` | 合并 snapshot + stat 段 + 链接配置填充 + 精度处理 |
| `fillLinkConfig` | 按 `col_key` 填充 5 列 `displayValue` / `linkUrl` |
| `buildMainComparator` | 39 字段 switch → `Comparator<OpsOverviewMainResp>`（NULLS LAST） |

#### 4.3.2 `CommonService` 与 `RepoDetailFactory`

```java
@Service
public class CommonService {
    @Autowired private RepoDetailFactory repoDetailFactory;

    public <T extends DetailReq> Result<?> queryDetail(String category, T req) {
        DetailCommonEnum type = DetailCommonEnum.valueByCategory(category);
        DetailService<T, ?> handler = repoDetailFactory.getHandle(type);
        PageResult<?> result = handler.queryDetail(req);
        return Result.success(result);
    }
}

@Component
public class RepoDetailFactory {
    private final Map<DetailCommonEnum, DetailService<?, ?>> handlers;

    public RepoDetailFactory(List<DetailService<T, R>> allHandlers) {
        this.handlers = allHandlers.stream()
            .collect(Collectors.toMap(DetailService::type, Function.identity()));
    }

    public DetailService<?, ?> getHandle(DetailCommonEnum type) {
        DetailService<?, ?> h = handlers.get(type);
        if (h == null) {
            log.error("unknown category: {}", type);
            throw new BizException(ResponseCodeEnum.BAD_REQUEST_UNKNOWN);
        }
        return h;
    }
}
```

#### 4.3.3 `DetailService` 接口与 4 个实现

```java
public interface DetailService<T extends DetailReq, R extends DetailResp> {
    DetailCommonEnum type();
    PageResult<R> queryDetail(T req);
}

// 实现示例
@Service
public class OpsRepoDetailDetailService implements DetailService<OpsRepoDetailDetailReq, OpsRepoDetailDetailResp> {
    @Autowired private OpsOverviewService opsOverviewService;

    @Override public DetailCommonEnum type() { return DetailCommonEnum.OPS_REPO_DETAIL; }

    @Override
    public PageResult<OpsRepoDetailDetailResp> queryDetail(OpsRepoDetailDetailReq req) {
        OpsRepoDetailReq inner = convert(req);
        PageResult<OpsRepoDetailResp> result = opsOverviewService.queryRepoDetail(inner);
        return result.map(this::toDetailResp);  // 字段映射含 styleDetail/precommitDetail/...
    }
}
```

**4 个实现类对比**：

| 类 | category | 委托方法 | 转换说明 |
|---|---|---|---|
| `OpsRepoDetailDetailService` | ops-repo-detail | `OpsOverviewService.queryRepoDetail` | 仓库配置明细，拼接 styleDetail/precommitDetail/rulesDetail/autoFixDetail/codecheckDetail |
| `OpsResourceDetailDetailService` | ops-resource-detail | `OpsOverviewService.queryResourceDetailList` | 流水线资源消耗明细，按 type=PR/Nightly 分支 |
| `OpsResourceRunsDetailService` | ops-resource-runs | `OpsOverviewService.queryResourceRuns` | 资源运行记录，按 pipeline_id + 时间段 |
| `OpsNightlyDetailDetailService` | ops-nightly-detail | `OpsOverviewService.queryNightlyDetailList` | Nightly 流水线明细，buildSuccess/versionAvail |

### 4.4 Mapper 层

#### 4.4.1 `DmProjectQualityOverviewDayMapper`

| Query ID | 用途 |
|---|---|
| `queryMainSnapshot` | 取项目最新 `stat_date` 快照，14 列状态类指标。WHERE 支持 `projectIds IN` + `projectName` 模糊。**不在 SQL 分页**（交给 Java 内存） |
| `countMainSnapshot` | 同上结构 SELECT COUNT(DISTINCT project_id) |

#### 4.4.2 `OpsMainStatMapper`（核心聚合）

| Query ID | 用途 |
|---|---|
| `queryMainStat` | 主表 stat 段聚合，8 个 CTE 串联：p90_stat / proj_meta / group_usage / resource_sum / pipeline_version_avail / pipeline_build_rate / nightly_rate / resource_total / pr_count / nightly_count |

#### 4.4.3 `DimComponentLinkConfigMapper`

| Query ID | 用途 |
|---|---|
| `queryByProjectId` | 按 project_id 查 `dim_component_link_config` 所有列配置 |
| `upsertConfig` | Doris UNIQUE KEY (project_id, col_key) 表，直接 INSERT 触发自动覆盖 |

#### 4.4.4 `OpsRepoDetailMapper`

| Query ID | 用途 |
|---|---|
| `queryRepoDetail` | 仓库配置明细分页。CTE `latest_scan` 取最新 scan_date；CTE `e2e_p90` 取 P90。WHERE 支持 `projectId` + `repoName` 模糊。ORDER BY `${sortField} ${sortRule}, s.repo_id`，LIMIT/OFFSET 分页 |
| `countRepoDetail` | 同结构 SELECT COUNT(DISTINCT s.repo_id) |

#### 4.4.5 `OpsResourceDetailMapper`

| Query ID | 用途 |
|---|---|
| `queryResourceDetail` | 按 type 分支查流水线资源消耗列表（含卡片字段，窗口函数 `SUM() OVER ()` + CROSS JOIN） |
| `queryResourceDetailList` | 归一化到 `/common/detail` 的流水线列表。type=PR/Nightly 各自 JOIN 链路。支持 `pipelineName` 模糊 + 排序 + 分页 |
| `countResourceDetailList` | 按 type 统计 DISTINCT pipeline_id 数 |
| `queryResourceSummary` | 资源卡片汇总（云上按 group_id，云下按 project_id），含运行次数、总量、平均消耗 |

#### 4.4.6 `OpsResourceRunMapper`

| Query ID | 用途 |
|---|---|
| `queryResourceRuns` | 按 `pipeline_id` + 时间段查 `dwr_rd_efc_pipeline_run_fact` 单流水线运行记录。CPU/NPU 秒 `CAST AS DOUBLE/3600`。ORDER BY pipeline_run_number DESC |
| `countResourceRuns` | SELECT COUNT(*) 同过滤条件 |

#### 4.4.7 `OpsNightlyDetailMapper`

| Query ID | 用途 |
|---|---|
| `queryNightlyDetail` | Nightly 流水线明细（含卡片）。CTE `pipeline_version_avail` 取 total_days/available_days；CTE `nightly_stat` 计算 build_success/version_avail。最终 SELECT 加 `AVG() OVER ()` 取 avg |
| `queryNightlyDetailList` | 归一化列表版，仅返回 pipeline_id/name/build_success/version_avail。支持 `pipelineName` 模糊 + 排序 + 分页 |
| `countNightlyDetailList` | SELECT COUNT(DISTINCT sdi.pipeline_id) |
| `queryNightlySummary` | Nightly 卡片汇总 `SELECT AVG(build_success), AVG(version_avail) FROM nightly_stat` |

### 4.5 DTO 设计

#### 4.5.1 多态分发基础类

**`DetailReq`（请求父类）**：

```java
@JsonTypeInfo(use = Id.NAME, property = "category", visible = true)
@JsonSubTypes({
    @JsonSubTypes.Type(value = OpsRepoDetailDetailReq.class, name = "ops-repo-detail"),
    @JsonSubTypes.Type(value = OpsResourceDetailDetailReq.class, name = "ops-resource-detail"),
    @JsonSubTypes.Type(value = OpsResourceRunsDetailReq.class, name = "ops-resource-runs"),
    @JsonSubTypes.Type(value = OpsNightlyDetailDetailReq.class, name = "ops-nightly-detail"),
    // ... 共 23 个子类（含其他业务线的 detail）
})
public abstract class DetailReq extends TimeReq {
    private String category;
    private Integer page;       // 默认 1
    private Integer pageSize;   // 默认 10
    private String sortField;
    @Pattern(regexp = "asc|desc")
    private String sortRule;    // 默认 DESC
    // 其他通用字段：repoId/name/number/title/stateList/各类时间窗
}
```

**`DetailResp`（响应父类）**：空基类，仅作类型约束。

#### 4.5.2 ops 主接口 Req/Resp

| 类 | 路径 | 关键字段 |
|---|---|---|
| `OpsOverviewMainReq` | `api/request/ops/` | projectIds / projectName / page / pageSize / sortField / sortRule |
| `OpsOverviewMainResp` | `api/response/ops/` | snapshot 段 14 字段 + stat 段 25 字段（共 ~40 字段） |
| `OpsResourceDetailReq` | 同上 | projectId / type(PR/Nightly) / startDate / endDate |
| `OpsResourceSummaryResp` | 同上 | totalVcpu / totalVcpuAvg / vcpuTotal / totalNpu / totalNpuAvg / npuTotal |
| `OpsNightlyDetailReq` | 同上 | projectId / startDate / endDate |
| `OpsNightlySummaryResp` | 同上 | avgBuildSuccess / avgVersionAvail |
| `OpsLinkConfigReq / Resp` | 同上 | projectId + List<ConfigItem>(colKey/displayValue/linkUrl) |
| `OpsRepoDetailReq / Resp` | 同上 | 仓库配置明细分页 |
| `OpsResourceRunReq / Resp` | 同上 | 资源运行记录分页 |

#### 4.5.3 common/detail 子类

**请求子类**（`api/request/common/detail/`）：

| 类 | 扩展字段 |
|---|---|
| `OpsRepoDetailDetailReq` | projectId + repoName（模糊搜索） |
| `OpsResourceDetailDetailReq` | projectId + type(PR/Nightly) + pipelineName（模糊搜索） |
| `OpsResourceRunsDetailReq` | pipelineId |
| `OpsNightlyDetailDetailReq` | projectId + pipelineName（模糊搜索） |

**响应子类**（`api/response/common/detail/`）：与 7.1.6 节字段一致。

### 4.6 工具类

| 工具类 | 用途 |
|---|---|
| `SortFieldValidator` | 校验 sortField/sortRule 是否在白名单，未命中抛 `BizException(BAD_REQUEST_UNKNOWN)` |
| `PageResult.of(list, total, page, pageSize)` | 构造标准分页响应 |
| `Result.success(data)` | 统一成功响应包装 |
| `BizException` + `ResponseCodeEnum` | 业务异常 + 错误码枚举 |
| `ListUtil` / `CollectionUtils` | 空集合安全处理 |

### 4.7 类依赖图

```text
OpsOverviewController ──┐
                        ├──> OpsOverviewService ──┬──> DmProjectQualityOverviewDayMapper
CommonController ──> CommonService ──> RepoDetailFactory ──> 4 × DetailService ──┘
                                                                                  │
                                                                                  ↓
                                                                         OpsOverviewService
                                                                                  │
                                                                          ┌───────┼───────┬──────────────┐
                                                                          ↓       ↓       ↓              ↓
                                                                  OpsMainStatMapper  DimComponentLinkConfigMapper
                                                                  OpsRepoDetailMapper OpsResourceDetailMapper
                                                                  OpsResourceRunMapper OpsNightlyDetailMapper
```

---

## 5 时序图设计

本章梳理「开源组件运营总览」核心场景的时序图，覆盖主表查询、链接配置 CRUD、4 类明细下钻的多态分发链路，以及 ETL 调度的全流程。

### 5.1 主表查询时序（`POST /ops-overview/main`）

```text
用户/前端            OpsOverviewController       OpsOverviewService       DmProjectQualityOverviewDayMapper      OpsMainStatMapper       DimComponentLinkConfigMapper     Doris
   │                       │                          │                              │                              │                              │              │
   │ POST /main            │                          │                              │                              │                              │              │
   │ (OpsOverviewMainReq)  │                          │                              │                              │                              │              │
   ├──────────────────────>│                          │                              │                              │                              │              │
   │                       │ SortFieldValidator       │                              │                              │                              │              │
   │                       │ .validate(39字段白名单)  │                              │                              │                              │              │
   │                       ├─────────────────────────>│                              │                              │                              │              │
   │                       │                          │ queryMainSnapshot(项目过滤)   │                              │                              │              │
   │                       │                          ├─────────────────────────────>│                              │                              │              │
   │                       │                          │                              │ SQL: latest CTE + 14列        │                              │              │
   │                       │                          │                              ├─────────────────────────────>│                              │  Doris
   │                       │                          │                              │<────── snapshot list ────────│                              │              │
   │                       │                          │<───── List<Resp> 全量 ───────│                              │                              │              │
   │                       │                          │ 提取 projectIds              │                              │                              │              │
   │                       │                          │ queryMainStat(projectIds,    │                              │                              │              │
   │                       │                          │              start, end)     │                              │                              │              │
   │                       │                          ├──────────────────────────────┴──────────────────────────────>│              │
   │                       │                          │                              │                              │ SQL: 8 CTE 聚合               │              │
   │                       │                          │                              │                              ├─────────────────────────────>│  Doris
   │                       │                          │                              │                              │<────── stat list ────────────│              │
   │                       │                          │<────────── List<OpsMainStat> ────────────────────────────────│              │
   │                       │                          │ fillLinkConfig(snapshotList) │                              │                              │              │
   │                       │                          │   ├ queryByProjectId ────────┼──────────────────────────────┼─────────────────────────────>│
   │                       │                          │   │ 按 colKey 填 displayValue │                              │                              │              │
   │                       │                          │   │<──────── List<LinkConfig> ┼──────────────────────────────┼──────────────────────────────│
   │                       │                          │ enrichResp: 合并 + applyRounding + applyTruncate               │              │
   │                       │                          │ Java 内存排序（buildMainComparator, NULLS LAST）                │              │
   │                       │                          │ Java 内存分页 subList(from, to)                                │              │
   │                       │                          │ PageResult.of(page, total, page, pageSize)                    │              │
   │                       │<─────── PageResult ──────│                              │                              │                              │              │
   │<────── Result ────────│                          │                              │                              │                              │              │
```

### 5.2 链接配置保存时序（`POST /ops-overview/link-config`）

```text
用户/前端         OpsOverviewController     OpsOverviewService     DimComponentLinkConfigMapper    Doris
   │                    │                        │                         │                       │
   │ POST /link-config  │                        │                         │                       │
   │ (OpsLinkConfigReq) │                        │                         │                       │
   ├───────────────────>│                        │                         │                       │
   │                    │ 校验 colKey 枚举合法性  │                         │                       │
   │                    ├───────────────────────>│                         │                       │
   │                    │ 遍历 List<ConfigItem>  │                         │                       │
   │                    │ for each item:         │                         │                       │
   │                    │   upsertConfig(item)   │                         │                       │
   │                    │                        ├────────────────────────>│                       │
   │                    │                        │                         │ INSERT INTO           │
   │                    │                        │                         │   dim_component_      │
   │                    │                        │                         │   link_config         │
   │                    │                        │                         │   (UNIQUE KEY MoW     │
   │                    │                        │                         │    自动覆盖)          │
   │                    │                        │                         ├──────────────────────>│  Doris
   │                    │                        │                         │<────── OK ────────────│
   │                    │                        │<─────── OK ─────────────│                       │
   │                    │<────── Result(true) ───│                         │                       │
   │<───── Result ──────│                        │                         │                       │
```

### 5.3 通用明细多态分发时序（`POST /common/detail`）

```text
前端             CommonController       CommonService        RepoDetailFactory       DetailService 实现            OpsOverviewService         Mapper/Doris
  │                  │                      │                       │                       │                              │                          │
  │ POST /detail     │                      │                       │                       │                              │                          │
  │ {                │                      │                       │                       │                              │                          │
  │   "category":    │                      │                       │                       │                              │                          │
  │   "ops-repo-     │                      │                       │                       │                              │                          │
  │    detail",      │                      │                       │                       │                              │                          │
  │   ... 其他字段    │                      │                       │                       │                              │                          │
  │ }                │                      │                       │                       │                              │                          │
  ├─────────────────>│                      │                       │                       │                              │                          │
  │                  │ @JsonSubTypes         │                       │                       │                              │                          │
  │                  │ 反序列化: 根据category │                       │                       │                              │                          │
  │                  │ → OpsRepoDetailReq    │                       │                       │                              │                          │
  │                  │   DetailReq 子类实例  │                       │                       │                              │                          │
  │                  ├─────────────────────>│                       │                       │                              │                          │
  │                  │                      │ DetailCommonEnum      │                       │                              │                          │
  │                  │                      │   .valueByCategory()  │                       │                              │                          │
  │                  │                      ├──────────────────────>│                       │                              │                          │
  │                  │                      │ getHandle(OPS_REPO_DETAIL)                  │                              │                          │
  │                  │                      ├──────────────────────>│                       │                              │                          │
  │                  │                      │<─── OpsRepoDetailDetailService ────────────│                              │                          │
  │                  │                      │                                              │                              │                          │
  │                  │                      │ DetailService.queryDetail(req)             │                              │                          │
  │                  │                      ├─────────────────────────────────────────────>│                              │                          │
  │                  │                      │                                              │ convert(req) → OpsRepoDetailReq│                          │
  │                  │                      │                                              │ OpsOverviewService.queryRepoDetail(inner)                  │
  │                  │                      │                                              ├─────────────────────────────>│                          │
  │                  │                      │                                              │                              │ OpsRepoDetailMapper       │
  │                  │                      │                                              │                              │  .queryRepoDetail()       │
  │                  │                      │                                              │                              ├─────────────────────────>│ Doris
  │                  │                      │                                              │                              │<──── List<Resp> ──────────│
  │                  │                      │                                              │<──── PageResult<OpsRepoDetailResp> ─────────────────────│
  │                  │                      │                                              │ toDetailResp()：字段映射含 styleDetail/precommitDetail/... │
  │                  │                      │<─────────────── PageResult<OpsRepoDetailDetailResp> ─────────────────────│                          │
  │                  │<──── Result ─────────│                       │                       │                              │                          │
  │<──── Result ─────│                      │                       │                       │                              │                          │
```

### 5.4 仓库下钻明细时序（`ops-repo-detail`）

```text
前端         OpsRepoDetailDetailService        OpsOverviewService             OpsRepoDetailMapper                  Doris
  │                  │                              │                              │                              │
  │ OpsRepoDetail    │                              │                              │                              │
  │ DetailReq        │                              │                              │                              │
  ├─────────────────>│                              │                              │                              │
  │                  │ SortFieldValidator           │                              │                              │
  │                  │   .validate(9字段白名单)     │                              │                              │
  │                  │                              │                              │                              │
  │                  │ convert(req)                 │                              │                              │
  │                  │   → OpsRepoDetailReq         │                              │                              │
  │                  ├─────────────────────────────>│                              │                              │
  │                  │                              │ queryRepoDetail(req)         │                              │
  │                  │                              ├─────────────────────────────>│                              │
  │                  │                              │                              │ SQL: latest_scan CTE +      │
  │                  │                              │                              │   e2e_p90 CTE + 仓库明细    │
  │                  │                              │                              ├─────────────────────────────>│  Doris
  │                  │                              │                              │<──── List<OpsRepoDetailResp> ─│
  │                  │                              │<──────── List<Resp> ─────────│                              │
  │                  │                              │ Java 内存分页                │                              │
  │                  │                              │ PageResult.of(...)           │                              │
  │                  │<──── PageResult<Resp> ───────│                              │                              │
  │                  │ result.map(this::toDetailResp)  字段映射: styleDetail/precommitDetail/rulesDetail/autoFixDetail/codecheckDetail
  │                  │ PageResult<OpsRepoDetailDetailResp>
  │<──── Result ─────│                              │                              │                              │
```

### 5.5 ETL 调度时序（指标 1-3 全链路）

```text
DolphinScheduler                SQL 节点 1                         Python 节点 (full/raw)              Python 节点 dwi           Doris
      │                              │                                       │                              │                   │
      │ 触发（每日凌晨，依赖 SCC 完成）                                       │                              │                   │
      ├─────────────────────────────>│                                       │                              │                   │
      │                              │ 查询代码仓及分支列表                  │                              │                   │
      │                              │   sdi_repo_info + ...                 │                              │                   │
      │                              ├──────────────────────────────────────┼──────────────────────────────┼──────────────────>│
      │                              │<────────── repo_url/auth_login/auth_token/repo_id/show_branch ─────────────┤
      │                              │ 参数传递给 Python 节点                │                              │                   │
      │                              ├─────────────────────────────────────>│                              │                   │
      │                              │                                       │ 解析参数                    │                   │
      │                              │                                       │ decrypt_token(salt)         │                   │
      │                              │                                       │ for each repo:              │                   │
      │                              │                                       │   checkout show_branch      │                   │
      │                              │                                       │   get_top_languages() ──────┼──────────────────>│
      │                              │                                       │   check_code_style()        │                   │
      │                              │                                       │   check_pre_commit()        │                   │
      │                              │                                       │   check_rules()             │                   │
      │                              │                                       │   INSERT raw_repo_quality_scan ────────────────>│
      │                              │                                       │<────────── 完成 ─────────────│                   │
      │                              │                                       │                              │                   │
      │                              ├───────────────────────────────────────┼─────────────────────────────>│                   │
      │                              │                                       │ code_quality_scan_dwi.py    │                   │
      │                              │                                       │ 解析 raw_repo_quality_scan.data_json ───────────>│
      │                              │                                       │ UPSERT dwi_repo_quality_scan_day (UNIQUE KEY MoW) │
      │                              │                                       │<────────── 完成 ─────────────│                   │
      │                              │                                       │                              │                   │
      │ (并行)                       │                                       │                              │                   │
      ├─────────────────────────────>│                                       │                              │                   │
      │ 4a_indicator4_expand_       │                                       │                              │                   │
      │   event_triggers.sql         │                                       │                              │                   │
      │ raw_pipeline_info ───────────┼───────────────────────────────────────┼──────────────────────────────┼──────────────────>│
      │                              │ TRUNCATE + INSERT sdi_pipeline_event_trigger                        │
      │                              │ (索引展开 0-9 共 10 位置)            │                              │                   │
      │                              ├───────────────────────────────────────┼──────────────────────────────┼──────────────────>│
      │                              │                                       │                              │                   │
      ├─────────────────────────────>│                                       │                              │                   │
      │ 5_indicator5_pr_codecheck_   │                                       │                              │                   │
      │   analysis.sql               │                                       │                              │                   │
      │   指标4+5 合并写入             │                                       │                              │                   │
      │   dwi_repo_pipeline_quality_day ─────────────────────────────────────┼──────────────────────────────┼──────────────────>│
      │                              │                                       │                              │                   │
      ├─────────────────────────────>│                                       │                              │                   │
      │ 7_indicator7_nightly_        │                                       │                              │                   │
      │   resource_aggregation.sql   │                                       │                              │                   │
      │   → dwi_project_nightly_resource_day                                  │                              │                   │
      ├──────────────────────────────┼───────────────────────────────────────┼──────────────────────────────┼──────────────────>│
      │                              │                                       │                              │                   │
      ├─────────────────────────────>│                                       │                              │                   │
      │ 8_indicator7_resource_       │                                       │                              │                   │
      │   aggregation.sql             │                                       │                              │                   │
      │   → dwi_project_resource_indicator_day                              │                              │                   │
      ├──────────────────────────────┼───────────────────────────────────────┼──────────────────────────────┼──────────────────>│
      │                              │                                       │                              │                   │
      ├─────────────────────────────>│                                       │                              │                   │
      │ 3_dm_project_quality_        │                                       │                              │                   │
      │   overview_aggregation.sql   │                                       │                              │                   │
      │   → dm_project_quality_overview_day                                 │                              │                   │
      ├──────────────────────────────┼───────────────────────────────────────┼──────────────────────────────┼──────────────────>│
      │                              │                                       │                              │                   │
      │<────── 完成 ─────────────────│                                       │                              │                   │
```

### 5.6 资源卡片查询时序（`POST /ops-overview/resource-summary`）

```text
前端                  OpsOverviewController       OpsOverviewService        OpsResourceDetailMapper              Doris
  │                          │                          │                            │                            │
  │ POST /resource-summary   │                          │                            │                            │
  │ (OpsResourceDetailReq)   │                          │                            │                            │
  ├─────────────────────────>│                          │                            │                            │
  │                          │ 校验 projectId + type    │                            │                            │
  │                          ├─────────────────────────>│                            │                            │
  │                          │                          │ queryResourceSummary(req)  │                            │
  │                          │                          ├───────────────────────────>│                            │
  │                          │                          │                            │ CTE proj_meta 区分云上/云下│
  │                          │                          │                            │   云上: JOIN dim_project_resource_total BY group_id
  │                          │                          │                            │   云下: 直查 dwi_project_resource_indicator_day
  │                          │                          │                            │ 计算 totalVcpu/totalVcpuAvg/vcpuTotal/totalNpu/... ─>│
  │                          │                          │<────── OpsResourceSummaryResp ──│                            │
  │                          │<────── Resp ────────────│                            │                            │
  │<───── Result ────────────│                          │                            │                            │
```

### 5.7 Nightly 卡片查询时序（`POST /ops-overview/nightly-summary`）

```text
前端               OpsOverviewController      OpsOverviewService      OpsNightlyDetailMapper          Doris
  │                       │                         │                          │                       │
  │ POST /nightly-summary │                         │                          │                       │
  │ (OpsNightlyDetailReq) │                         │                          │                       │
  ├──────────────────────>│                         │                          │                       │
  │                       │ 校验 projectId          │                          │                       │
  │                       ├────────────────────────>│                          │                       │
  │                       │                         │ queryNightlySummary(req)  │                       │
  │                       │                         ├─────────────────────────>│                       │
  │                       │                         │                          │ 复用 OpsMainStatMapper │
  │                       │                         │                          │   相同 CTE 逻辑        │
  │                       │                         │                          │ SELECT AVG(build_success),│
  │                       │                         │                          │        AVG(version_avail) │
  │                       │                         │                          ├──────────────────────>│
  │                       │                         │                          │<────── Resp ──────────│
  │                       │                         │<──── OpsNightlySummaryResp ─│                       │
  │                       │<────── Resp ────────────│                          │                       │
  │<────── Result ────────│                         │                          │                       │
```

---

## 6 处理逻辑

本章梳理 11 个指标的核心处理逻辑（计算规则、边界处理、合并规则）和后端接口的关键处理流程（精度、排序、分页、合并）。

### 6.1 指标 1 - 编码风格可视

#### 6.1.1 仓库级判断逻辑（Python 脚本）

```text
输入：sdi_repo_info.repo_id、sdi_repo_info.repo_url、code_repo_branch_config.show_branch
       （回退 dwi_code_scan_language 最新默认分支扫描）

Step 1: get_top_languages(repo_id) → [(Python, 50000, 0.55), (C++, 30000, 0.33)]
Step 2: 遍历 top1 + top2
        对每种语言应用 check_code_style():
          - C / C++: 根目录 .clang-format 存在且 size > 0
                       回退 pre-commit/ 子目录
          - Rust:    .rustfmt.toml
          - Python:  .pyproject.toml（以 ruff 工具识别为准）
          - JS/TS:   eslint.config.* 或 .prettierrc 任一
          - Go:      默认通过（gofmt 内置）
          - Java:    pom.xml/build.gradle/build.gradle.kts/settings.gradle*
                       grep "google-java-format" 命中则 has_config=1
Step 3: style_overall_pass:
          - 0: 不通过（top1/top2 任一不通过）
          - 1: 通过
          - 3: 无有效语言（top1/top2 都为空/不在语言列表）
Step 4: 输出 data_json 落 raw_repo_quality_scan
Step 5: code_quality_scan_dwi.py 解析后 UPSERT dwi_repo_quality_scan_day
```

**边界规则**：

| 场景 | 处理 |
|---|---|
| 仅 1 种语言 | 只看 top1，top2 字段 NULL，overall_pass 只取决于 top1 |
| Go 在 top1 或 top2 | `has_config` 强制为 1，Go 不需要配置文件 |
| 不在预定义语言列表（PHP/Ruby 等） | 默认通过，不检查配置文件 |
| 点开头 dotfile | 同时接受 `.clang-format` 和 `clang-format` |
| 配置文件搜索路径 | 根目录优先，根目录未命中回退 `pre-commit/` 子目录 |

#### 6.1.2 项目级聚合（DM SQL）

```sql
-- 排除 style_overall_pass=3 的仓库 + 排除无 PR 流水线的仓库
CAST(SUM(CASE WHEN style_overall_pass = 1 THEN 1 ELSE 0 END) AS DOUBLE)
    / NULLIF(SUM(CASE WHEN style_overall_pass IN (0, 1) THEN 1 ELSE 0 END), 0)
AS style_visible_rate
```

**分母**：style_overall_pass ∈ {0, 1} 的仓库数（排除 status=3 无有效语言的仓库，且需存在 PR 流水线配置）

### 6.2 指标 2 - 代码检查

#### 6.2.1 仓库级判断逻辑

```text
检查根目录或 pre-commit/ 子目录下：
  - .pre-commit-config.yaml 存在且非空
  - 或 .lintrunner.toml 存在且非空
任一命中 → has_pre_commit_cfg = 1，否则 0
```

#### 6.2.2 项目级聚合

```sql
-- 全部仓库计入分母（不排除无 PR 流水线）
CAST(SUM(CASE WHEN has_pre_commit_cfg = 1 THEN 1 ELSE 0 END) AS DOUBLE)
    / NULLIF(COUNT(*), 0)
AS precommit_rate
```

### 6.3 指标 3 - 代码检查规则数

#### 6.3.1 仓库级规则数统计

| 语言 | 工具 | 计算方式 |
|---|---|---|
| Python | ruff | `enabled_rules = ruff linter` 行数（默认规则数）<br>`extra_rules = enabled_rules - default_rules` |
| C / C++ | clang-format | `clang-format --style=file --dump-config` 输出顶层 key 数（行首字母且含冒号） |
| C / C++ | clang-tidy | `clang-tidy --list-checks` 输出去掉 "Enabled checks:" 标题后的行数 |
| Java | Checkstyle | `grep -c '<module name=' checkstyle.xml`（路径：./checkstyle.xml 或 ./src/checkstyle.xml 或 ./config/checkstyle.xml 或 ./checkstyle/checkstyle.xml） |
| Java | Spotless | grep "spotless" 在 pom.xml/build.gradle/build.gradle.kts 中是否出现 |
| Java | SpotBugs | **跳过**（需要编译环境，无法自动分析） |
| Java | google-java-format | grep 在 pom.xml/build.gradle/settings.gradle* 中是否出现，存在则贡献 31 条规则 |

#### 6.3.2 项目级聚合

```sql
-- 规则数总和（所有仓库累加 + google-java-format 31 条）
SUM(COALESCE(python_ruff_enabled_rules, 0) +
    COALESCE(cpp_clang_tidy_checks, 0) +
    COALESCE(java_checkstyle_modules, 0) +
    CASE WHEN java_google_format_found = 1 THEN 31 ELSE 0 END) AS check_rules_total

-- 分语言平均规则数（分母=top1或top2含该语言的仓库数）
CAST(SUM(COALESCE(python_ruff_enabled_rules, 0)) AS DOUBLE)
    / NULLIF(SUM(CASE WHEN top1_language='Python' OR top2_language='Python' THEN 1 ELSE 0 END), 0) AS python_rules_avg
```

**展示**：`checkRulesTotal` 总和 + `pythonRulesAvg` / `cppRulesAvg` / `javaRulesAvg` 分语言平均。

### 6.4 指标 4 - 代码风格自动修复

#### 6.4.1 数据流

```text
Step 1 (MySQL → Doris 同步)
  MySQL pipeline_info → DataX/DS → raw_pipeline_info (含 config_json.eventTriggers)

Step 2 (SQL 展开 eventTriggers 数组 - 索引展开 0-9 共 10 位置)
  TRUNCATE sdi_pipeline_event_trigger
  INSERT ... UNION ALL 10 个位置
    get_json_string(config_json, '$.eventTriggers[i].isEnable')
    get_json_string(config_json, '$.eventTriggers[i].actionType')
    get_json_string(config_json, '$.eventTriggers[i].eventType')

Step 3 (聚合写入 dwi_repo_pipeline_quality_day)
  按 (project_id, repo_id) 聚合：
    has_auto_fix = MAX(action_type='0' AND is_enable='true')
    auto_fix_pipeline_ids = GROUP_CONCAT(source_pipeline_id)
```

**流水线任务命名规范**（仅用于指标5）：

| 不允许 | 允许 |
|---|---|
| `codecheck`、`codecheck_codearts` | `pre-commit`、`lintrunner`、`codecheck_pre-commit`、`codecheck_lintrunner` |

#### 6.4.2 项目级聚合

```sql
CAST(SUM(CASE WHEN has_auto_fix = 1 THEN 1 ELSE 0 END) AS DOUBLE)
    / NULLIF(COUNT(*), 0) AS auto_fix_rate
```

### 6.5 指标 5 - 例外备案和 committer 审核

#### 6.5.1 数据链路

```text
sdi_repo_info
  → sdi_repo_pull_request_info (按 repo_id 关联)
  → sdi_pr_pipeline_relation   (按 pr_id 关联，拿到 pipeline_id 和 pipeline_run_id)
  → dwr_rd_efc_pipeline_run_fact (按 pipeline_id + pipeline_run_id，取最新一次)
  → dwr_rd_efc_pipeline_run_job_fact (按 pipeline_run_id 取 job 列表)
```

**过滤**：`job_status IN ('SUCCESS', 'FAILED')`，每个 pipeline 仅取最新一次运行。

#### 6.5.2 仓库级判断逻辑

```sql
-- 旧版 codecheck（不达标信号）
CASE WHEN job_name LIKE '%codecheck%'
          AND job_name NOT LIKE '%pre-commit%'
          AND job_name NOT LIKE '%lintrunner%' THEN 1 ELSE 0 END AS is_old_codecheck

-- 新版 codecheck（达标信号）
CASE WHEN job_name LIKE '%pre-commit%'
          OR job_name LIKE '%lintrunner%' THEN 1 ELSE 0 END AS is_new_codecheck

-- 达标条件
has_old_codecheck = 0 AND has_new_codecheck = 1 → uses_proper_codecheck = 1
```

#### 6.5.3 项目级聚合

```sql
CAST(SUM(CASE WHEN uses_proper_codecheck = 1 THEN 1 ELSE 0 END) AS DOUBLE)
    / NULLIF(COUNT(*), 0) AS exception_review_rate
```

### 6.6 指标 6 - PR 执行时长（P90）

#### 6.6.1 计算逻辑

```sql
-- 项目级 MAX（取各仓库 P90 中的最大值）
SELECT rel.project_id,
       MAX(PERCENTILE(CASE WHEN psr.state = 'merged' AND psr.merged_at IS NOT NULL
                            THEN TIMESTAMPDIFF(SECOND, psr.created_at, psr.merged_at)
                       END, 0.9) / 60.0) AS pr_duration_p90_min
FROM dm_rd_efc_pr_sum_pipeline_statistics_day psr
JOIN sdi_repo_info ri ON psr.repo_url = ri.repo_url
JOIN dwi_rd_project_pipeline_relation rel ON ri.repo_id = rel.repo_id
WHERE psr.pipeline_status = 'ALL_PIPELINE_STATUS'
  AND psr.data_time BETWEEN #{startDate} AND #{endDate}
GROUP BY rel.project_id;
```

**过滤条件**：
- `pipeline_status = 'ALL_PIPELINE_STATUS'`
- `state = 'merged'`
- `merged_at IS NOT NULL`

**展示**：项目级取 MAX(各仓库 P90)，仓库明细直接展示。

### 6.7 指标 7 - 流水线资源消耗

#### 6.7.1 PR 资源聚合

```sql
SELECT rel.project_id, DATE(fact.pipeline_start_time) AS stat_date,
       SUM(CAST(fact.cpu_second AS DOUBLE))    AS cpu_seconds,
       SUM(CAST(fact.npu_second AS DOUBLE))    AS npu_seconds,
       SUM(CAST(fact.memory_second AS DOUBLE)) AS memory_seconds
FROM dwr_rd_efc_pipeline_run_fact fact
JOIN dwi_rd_project_pipeline_relation rel ON fact.pipeline_id = rel.pipeline_id
WHERE DATE(fact.pipeline_start_time) BETWEEN #{startDate} AND #{endDate}
GROUP BY rel.project_id, DATE(fact.pipeline_start_time);
```

#### 6.7.2 Nightly 资源聚合

```sql
SELECT np.project_id, DATE(fact.pipeline_end_time) AS stat_date,
       SUM(CAST(fact.cpu_second AS DOUBLE))    AS cpu_seconds,
       SUM(CAST(fact.npu_second AS DOUBLE))    AS npu_seconds,
       SUM(CAST(fact.memory_second AS DOUBLE)) AS memory_seconds
FROM dwr_rd_efc_pipeline_run_fact fact
JOIN sdi_version_pipeline_base_info np ON fact.pipeline_id = np.pipeline_id
WHERE DATE(fact.pipeline_end_time) BETWEEN #{startDate} AND #{endDate}
GROUP BY np.project_id, DATE(fact.pipeline_end_time);
```

**卷积算法**：开源项目下所有流水线资源消耗，求和卷积到项目中展示。

**资源分组规则**：

| 类型 | 判定 | 计算方式 |
|---|---|---|
| 云上 | `type = 1` 且 `group_id` 非空 | 同组所有项目消耗求和作为一个整体 |
| 云下 | `type = 0` 且 `group_id = NULL` | 独立消耗，不卷积 |

**时间口径差异**：
- PR：`DATE(pipeline_start_time)`（流水线运行日）
- Nightly：`DATE(pipeline_end_time)`（流水线结束日）

### 6.8 指标 8 - 开源项目资源总量

#### 6.8.1 数据来源

`dim_project_resource_total`（DIM 层，无时间维度，API 录入）

**字段**：

| 字段 | 单位 | 说明 |
|---|---|---|
| `cpu_total_cores` | 核 | vCPU 总核数 |
| `npu_total_cards` | 卡 | NPU 总卡数 |
| `memory_total_gb` | GB | 内存总大小 |

**关键属性**：
- `pipeline_type`：Pr 或 Nightly（PR 与 Nightly 总量独立配置）
- `type`：0=云下，1=云上
- `group_id`：云上同组共享资源池标识（如 PTA_GROUP、OPENEULER_GROUP）

### 6.9 指标 9 - 资源使用率

#### 6.9.1 计算公式

```text
vCPU 资源使用率 = (Σ流水线消耗 vCPU 核时) / (vCPU 总核数 × 统计总小时数 × 3600)
NPU 资源使用率 = (Σ流水线消耗 NPU 卡时) / (NPU 总卡数 × 统计总小时数 × 3600)
内存资源使用率 = (Σ流水线消耗内存时长) / (内存总大小 × 统计总小时数 × 3600)
```

> 当前开发调测消耗暂不纳入，仅计算流水线消耗部分。

**计算口径**：
```
统计总小时数 = (DATEDIFF(endDate, startDate) + 1) × 24
统计总秒数   = 统计总小时数 × 3600
使用率      = SUM(消耗核时) / NULLIF(总量 × 统计总秒数, 0)
```

#### 6.9.2 云上 vs 云下计算差异

| 类型 | 使用率分子 | 使用率分母 |
|---|---|---|
| 云上（group_id 非空） | 同组所有项目消耗求和 | 组共享总量 × 86400 × 统计天数 |
| 云下（group_id 为空） | 该项目独立消耗 | 该项目独立总量 × 86400 × 统计天数 |

**核心约束**：云上同组项目得到相同的使用率（因为分子分母都按组聚合）。

```sql
-- PR CPU 使用率示例
CASE
    -- 云上: 组整体消耗 / 组共享总量
    WHEN pd.group_id IS NOT NULL
         AND pga.group_cpu_total IS NOT NULL AND pga.group_cpu_total > 0
    THEN pga.group_pr_cpu / (pga.group_cpu_total * 86400)
    -- 云下: 独立消耗 / 独立总量
    WHEN pd.group_id IS NULL
         AND pd.cpu_total_cores IS NOT NULL AND pd.cpu_total_cores > 0
    THEN c.pr_cpu_seconds / (pd.cpu_total_cores * 86400)
END AS pr_cpu_usage_rate
```

### 6.10 指标 10 - 编译成功率

#### 6.10.1 计算规则

```text
流水线级编译成功率 = SUM(build_pass_count) / NULLIF(SUM(build_count), 0)
项目级编译成功率   = AVG(各流水线的日成功率)    -- 等权 AVG（非加权 SUM/SUM）
```

**数据源**：`dwr_rd_efc_build_fact_nightly_test_case_pipeline_run` JOIN `sdi_version_pipeline_base_info`，按 `DATE(pipeline_run_endtime)` 聚合。

### 6.11 指标 11 - 版本可用度

#### 6.11.1 计算规则

```text
流水线级版本可用度 = MAX(is_version_available)     -- 当天任一次运行可用则该天可用
项目级版本可用度   = SUM(可用流水线数) / COUNT(有运行的流水线数)    -- 等权 AVG
```

**数据源**：`dm_rd_efc_build_dim_nightly_pipeline_day`（日级去重），过滤非工作日（`dim_holiday` 表）。

**工作日过滤**：

```sql
WHERE DATE(pipeline_run_endtime) BETWEEN #{startDate} AND #{endDate}
  AND (WEEKDAY(DATE(pipeline_run_endtime)) < 5  -- 周一~周五
       OR DATE(pipeline_run_endtime) IN (SELECT holiday_date FROM dim_holiday))  -- 节假日也算工作日
```

### 6.12 后端接口处理流程

#### 6.12.1 主表查询（`queryMain`）

```text
1. SortFieldValidator.validate(MAIN_SORT_ALLOWED_FIELDS, req.sortField, req.sortRule)
   └─ 未命中抛 BizException(BAD_REQUEST_UNKNOWN)

2. dmProjectQualityOverviewDayMapper.queryMainSnapshot(项目过滤 + projectName 模糊)
   └─ 返回 List<OpsOverviewMainResp> 全量 snapshot 列表（不分页）

3. 提取所有 projectIds

4. opsMainStatMapper.queryMainStat(projectIds, startDate, endDate)
   └─ 返回 List<OpsMainStat> stat 段（8 个 CTE 聚合）

5. enrichResp():
   a. 按 projectId 合并 snapshot + stat
   b. 装配 5 列链接配置（fillLinkConfig）：
      - 调用 DimComponentLinkConfigMapper.queryByProjectId
      - 按 col_key 填 displayValue/linkUrl
   c. 精度处理：
      - applyUsageRounding: 使用率四舍五入保留 4 位
      - applyAvgRounding: 平均消耗四舍五入保留 2 位
      - applyRulesRounding: 分语言规则数四舍五入保留 2 位
      - applyTruncate: 比率类截断（非四舍五入）保留 4 位

6. buildMainComparator(sortField, sortRule): 39 字段 switch → Comparator（NULLS LAST）
   - 默认 DESC
   - snapshot 段 14 字段 + stat 段 25 字段

7. Java 内存排序 + subList(page, pageSize) 分页
   int from = (page - 1) * pageSize;
   int to = Math.min(from + pageSize, merged.size());
   List<OpsOverviewMainResp> page = merged.subList(from, to);

8. 返回 PageResult(page, total, page, pageSize)
```

#### 6.12.2 资源卡片查询（`queryResourceSummary`）

```text
1. 校验 projectId 非空 + type ∈ {PR, Nightly}
2. OpsResourceDetailMapper.queryResourceSummary(req)
   ├─ CTE proj_meta：从 dim_project_resource_total 取 type/group_id
   ├─ type=1 云上：JOIN dim_project_resource_total BY group_id，同组项目消耗求和
   ├─ type=0 云下：直查 dwi_project_resource_indicator_day
   └─ 计算字段：
       totalVcpu      = SUM(cpu_seconds) / 3600
       totalVcpuAvg   = MAX(消耗) / NULLIF(MAX(运行次数), 0)
       vcpuTotal      = SUM(cpu_total_cores) * (DATEDIFF(end, start) + 1) * 24
       totalNpu       = SUM(npu_seconds) / 3600
       totalNpuAvg    = MAX(消耗) / NULLIF(MAX(运行次数), 0)
       npuTotal       = SUM(npu_total_cards) * (DATEDIFF(end, start) + 1) * 24
3. 返回 OpsResourceSummaryResp
```

#### 6.12.3 Nightly 卡片查询（`queryNightlySummary`）

```text
1. 校验 projectId 非空
2. OpsNightlyDetailMapper.queryNightlySummary(req)
   └─ 复用 OpsMainStatMapper 中的相同 CTE 逻辑：
       pipeline_version_avail / nightly_stat / nightly_rate
       SELECT AVG(build_success), AVG(version_avail) FROM nightly_stat
3. 返回 OpsNightlySummaryResp(avgBuildSuccess, avgVersionAvail)
```

#### 6.12.4 链接配置保存（`saveLinkConfig`）

```text
1. 校验 colKey ∈ {ttfhw, envPrepare, incBuild, fullBuild, utExec}
2. 遍历 List<ConfigItem>:
   for each item:
     DimComponentLinkConfigMapper.upsertConfig(item)
     └─ INSERT INTO dim_component_link_config (...)
        └─ Doris UNIQUE KEY (project_id, col_key) + enable_unique_key_merge_on_write=true
           → 自动覆盖实现 upsert
3. 返回 success(true)
```

#### 6.12.5 通用明细查询（`/common/detail`）

```text
1. Jackson @JsonSubTypes 反序列化：根据 req.category 字段创建对应子类实例
2. CommonService.queryDetail(category, req):
   a. DetailCommonEnum.valueByCategory(category) → 转枚举
   b. RepoDetailFactory.getHandle(type) → 取 DetailService 实现
   c. handler.queryDetail(req) → 委托回 OpsOverviewService 对应方法
3. OpsOverviewService 内部执行 SQL + 内存分页
4. 返回 PageResult
```

#### 6.12.6 精度控制总览

| 类型 | 处理 | 保留位数 |
|---|---|---|
| 使用率 / 比率 | `applyTruncate` 截断（非四舍五入） | 4 位 |
| 平均消耗 | `applyAvgRounding` 四舍五入 | 2 位 |
| 分语言规则数 | `applyRulesRounding` 四舍五入 | 2 位 |
| 资源总量 / 消耗 | `applyRounding` 四舍五入 | 2 位 |

#### 6.12.7 除零保护

所有比率/平均计算统一使用 `NULLIF(分母, 0)`，分母为 0 时返回 NULL（前端展示为 `-` 或不展示），不抛异常。

---

## 7 API & MO 设计

本章梳理本期 6 个后端接口的 API 契约（请求/响应/字段约束）和 MO 清单（关键对象）。

### 7.1 API 设计

#### 7.1.1 接口 1：主表聚合查询 `POST /ops-overview/main`

**请求 `OpsOverviewMainReq`（继承 `TimeReq`）**：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| startDate | LocalDate | 是 | - | 开始日期 `yyyy-MM-dd` |
| endDate | LocalDate | 是 | - | 结束日期 `yyyy-MM-dd` |
| projectIds | List<Integer> | 否 | null | 项目 ID 列表（空则不过滤） |
| projectName | String | 否 | null | 项目名模糊搜索（LIKE 匹配） |
| page | int | 否 | 1 | 页码（Java 内存分页） |
| pageSize | int | 否 | 10 | 每页大小 |
| sortField | String | 否 | null | 排序字段（需在 39 字段白名单内） |
| sortRule | String | 否 | DESC | asc / desc |

**响应 `OpsOverviewMainResp`（约 40 字段，分两段）**：

**snapshot 段（状态类，取最新 stat_date）**：

| 字段 | 类型 | 来源 |
|---|---|---|
| projectId / projectName / productId / productName | 基础信息 | dm_project_quality_overview_day |
| statDate | DATE | dm_project_quality_overview_day |
| ttfhwDisplayValue / ttfhwLinkUrl | 链接 | dim_component_link_config |
| envPrepareDisplayValue / envPrepareLinkUrl | 链接 | 同上 |
| incBuildDisplayValue / incBuildLinkUrl | 链接 | 同上 |
| fullBuildDisplayValue / fullBuildLinkUrl | 链接 | 同上 |
| utExecDisplayValue / utExecLinkUrl | 链接 | 同上 |
| styleVisibleRate | Double (0-1) | dm_project_quality_overview_day |
| precommitRate | Double (0-1) | 同上 |
| checkRulesTotal | Integer | 同上 |
| pythonRulesAvg / cppRulesAvg / javaRulesAvg | Double (0-1) | 同上 |
| autoFixRate | Double (0-1) | 同上 |
| exceptionReviewRate | Double (0-1) | 同上 |

**stat 段（统计类，实时计算）**：

| 字段 | 类型 | 说明 |
|---|---|---|
| prDurationP90 | Double | PR E2E P90（分钟） |
| prCpuUsage / prNpuUsage / prMemoryUsage | Double | PR 消耗（核时/卡时/GB时） |
| nightlyCpuUsage / nightlyNpuUsage / nightlyMemoryUsage | Double | Nightly 消耗 |
| overallCpuUsage / overallNpuUsage / overallMemoryUsage | Double | overall = PR + Nightly |
| prCpuTotal / prNpuTotal / prMemoryTotal | Double | PR 总量 |
| nightlyCpuTotal / nightlyNpuTotal / nightlyMemoryTotal | Double | Nightly 总量 |
| overallCpuTotal / overallNpuTotal / overallMemoryTotal | Double | overall 总量 |
| prCpuRate / prNpuRate / prMemoryRate | Double (0-1) | PR 使用率 |
| nightlyCpuRate / nightlyNpuRate / nightlyMemoryRate | Double (0-1) | Nightly 使用率 |
| overallCpuRate / overallNpuRate / overallMemoryRate | Double (0-1) | overall 使用率 |
| prCpuAvg / prNpuAvg | Double | PR 平均消耗 |
| nightlyCpuAvg / nightlyNpuAvg | Double | Nightly 平均消耗 |
| overallCpuAvg / overallNpuAvg | Double | overall 平均消耗 |
| nightlyBuildSuccessRate | Double (0-1) | 编译成功率 |
| nightlyVersionAvailabilityRate | Double (0-1) | 版本可用度 |

**包装响应**：`PageResult<OpsOverviewMainResp>`（含 list / total / page / pageSize）

#### 7.1.2 接口 2：环境资源明细卡片 `POST /ops-overview/resource-summary`

**请求 `OpsResourceDetailReq`**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | Integer | 是 | 项目 ID |
| type | String | 是 | `PR` 或 `Nightly` |
| startDate | LocalDate | 是 | 开始日期 |
| endDate | LocalDate | 是 | 结束日期 |

**响应 `OpsResourceSummaryResp`（6 字段）**：

| 字段 | 类型 | 计算口径 |
|---|---|---|
| totalVcpu | Double | 各流水线 vCPU 消耗汇总（核时） = `SUM(秒)/3600` |
| totalVcpuAvg | Double | 各流水线 CPU 平均消耗汇总（核时） = `MAX(消耗) / NULLIF(MAX(运行次数), 0)` |
| vcpuTotal | Double | vCPU 总量（核时） = `SUM(总数) × (DATEDIFF+1) × 24` |
| totalNpu | Double | NPU 消耗汇总（卡时） |
| totalNpuAvg | Double | NPU 平均消耗汇总（卡时） |
| npuTotal | Double | NPU 总量（卡时） |

**SQL 入口**：`OpsResourceDetailMapper.queryResourceSummary`，CTE `proj_meta` 区分云上/云下：
- 云上：按 `group_id` JOIN `dim_project_resource_total`，同组项目消耗求和
- 云下：按 `project_id` 直查 `dwi_project_resource_indicator_day`

#### 7.1.3 接口 3：Nightly 明细卡片 `POST /ops-overview/nightly-summary`

**请求 `OpsNightlyDetailReq`**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | Integer | 是 | 项目 ID |
| startDate | LocalDate | 是 | 开始日期 |
| endDate | LocalDate | 是 | 结束日期 |

**响应 `OpsNightlySummaryResp`（2 字段）**：

| 字段 | 类型 | 计算口径 |
|---|---|---|
| avgBuildSuccess | Double (0-1) | 平均编译成功率，按流水线等权 AVG |
| avgVersionAvail | Double (0-1) | 平均版本可用度，按流水线等权 AVG |

**SQL 入口**：`OpsNightlyDetailMapper.queryNightlySummary`，复用 `OpsMainStatMapper` 中的相同 CTE 逻辑。

#### 7.1.4 接口 4：链接配置查询 `GET /ops-overview/link-config`

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | Integer（query） | 是 | 项目 ID |

**响应 `OpsLinkConfigResp`**：

| 字段 | 类型 | 说明 |
|---|---|---|
| projectId | Integer | 项目 ID |
| configList | List<ConfigItem> | 5 列配置项 |
| ConfigItem.colKey | String | ttfhw/envPrepare/incBuild/fullBuild/utExec |
| ConfigItem.displayValue | String | 前端展示文案 |
| ConfigItem.linkUrl | String | 点击跳转 URL |

**SQL 入口**：`DimComponentLinkConfigMapper.queryByProjectId(projectId)`

#### 7.1.5 接口 5：链接配置保存 `POST /ops-overview/link-config`

**请求 `OpsLinkConfigReq`**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| projectId | Integer | 是 | 项目 ID |
| configList | List<ConfigItem> | 是 | 待保存配置项（5 列） |

**响应**：`Result.success(true)`，依赖 Doris UNIQUE KEY (project_id, col_key) 自动覆盖实现 upsert。

**SQL 入口**：`DimComponentLinkConfigMapper.upsertConfig(item)` 循环调用。

#### 7.1.6 接口 6：通用明细查询 `POST /common/detail`

**多态分发机制**：

1. `CommonController.queryRepoDetail<T extends DetailReq>(@Validated @RequestBody T req)`
2. 通过 `@JsonSubTypes` 在反序列化时根据 `category` 字段创建对应子类实例
3. `CommonService.queryDetail(category, req)` → `DetailCommonEnum.valueByCategory(category)` 转枚举
4. `RepoDetailFactory.getHandle(DetailCommonEnum)` 取对应 `DetailService`
5. `DetailService.queryDetail(req)` 委托回 `OpsOverviewService`（4 个实现都转发到主 Service）

**4 个 category 子类**：

| category | 请求子类 | 响应子类 | 转发方法 |
|---|---|---|---|
| `ops-repo-detail` | `OpsRepoDetailDetailReq` | `OpsRepoDetailDetailResp` | `OpsOverviewService.queryRepoDetail` |
| `ops-resource-detail` | `OpsResourceDetailDetailReq` | `OpsResourceDetailDetailResp` | `OpsOverviewService.queryResourceDetailList` |
| `ops-resource-runs` | `OpsResourceRunsDetailReq` | `OpsResourceRunsDetailResp` | `OpsOverviewService.queryResourceRuns` |
| `ops-nightly-detail` | `OpsNightlyDetailDetailReq` | `OpsNightlyDetailDetailResp` | `OpsOverviewService.queryNightlyDetailList` |

**`OpsRepoDetailDetailResp` 字段（仓库配置明细）**：

| 字段 | 来源表 | 说明 |
|---|---|---|
| repoId / repoName | sdi_repo_info | SUBSTRING_INDEX 解析 git url 取仓库名 |
| stylePass | dwi_repo_quality_scan_day | `style_overall_pass` |
| precommitPass | dwi_repo_quality_scan_day | `has_pre_commit_cfg` |
| rulesTotal | dwi_repo_quality_scan_day | `python_ruff + cpp_clang_tidy + java_checkstyle + 31*google_java_format` |
| pythonRulesTotal / cppRulesTotal / javaRulesTotal | 同上 | 分语言规则数 |
| hasAutoFix | dwi_repo_pipeline_quality_day | `has_auto_fix` |
| usesProperCodecheck | 同上 | `has_old_codecheck=0 AND has_new_codecheck=1` |
| prDuration | dm_rd_efc_pr_sum_pipeline_statistics_day | `PERCENTILE(TIMESTAMPDIFF(SECOND, created_at, merged_at), 0.9)/60.0` |
| styleDetail | dwi_repo_quality_scan_day | 拼接格式 `java:满足; c++:不满足(配置文件缺失)` |
| precommitDetail | 同上 | 达标 null；不达标 `无对应配置文件或文件为空` |
| rulesDetail | 同上 | 始终返回 `c++:0; java:10; python:0` |
| autoFixDetail | dwi_repo_pipeline_quality_day | 达标 `代码风格自动修复已配置(流水线:xxx)` |
| codecheckDetail | 同上 | 不达标 `流水线任务名不符合规范(旧版任务:xxx)` |
| noPipelineReason | dwi_rd_project_pipeline_relation | 无 PR 流水线时的原因文案 |

**`OpsResourceDetailDetailResp` 字段（流水线资源消耗明细）**：

| 字段 | 说明 |
|---|---|
| pipelineId / pipelineName | 流水线标识 |
| vcpu / npu | 该流水线 vCPU/NPU 消耗（核时/卡时） = `SUM(秒)/3600` |
| vcpuAvg / npuAvg | 平均消耗 = `消耗 / NULLIF(运行次数, 0)` |

PR 数据源：`dwi_rd_project_pipeline_relation` JOIN `dwr_rd_efc_pipeline_run_fact`，按 `pipeline_id` 聚合。
Nightly 数据源：`sdi_version_pipeline_base_info` JOIN `dwr_rd_efc_pipeline_run_fact`。

**`OpsResourceRunsDetailResp` 字段（资源运行记录）**：

| 字段 | 说明 |
|---|---|
| runId / pipelineRunId | 运行标识 |
| startTime | 运行开始时间 |
| status | 运行状态 |
| vcpu / npu | 单次运行 vCPU/NPU 消耗（核时/卡时） |

数据源：`dwr_rd_efc_pipeline_run_fact` 按 `pipeline_id` + 时间段查询单流水线运行记录。

**`OpsNightlyDetailDetailResp` 字段（Nightly 流水线明细）**：

| 字段 | 说明 |
|---|---|
| pipelineId / pipelineName | Nightly 流水线标识 |
| buildSuccess | 编译成功率（0-1） = `SUM(build_pass_count)/NULLIF(SUM(build_count),0)` |
| versionAvail | 版本可用度（0-1） = `SUM(available_days)/COUNT(total_days)` |

数据源：`sdi_version_pipeline_base_info` JOIN `dwr_rd_efc_build_fact_nightly_test_case_pipeline_run`。

### 7.2 MO 设计

MO（Managed Object，关键对象）清单，覆盖本期所有需要持久化或在多个接口间传递的核心对象。

| MO 名称 | 类型 | 持久化表 | 关键字段 | 接口 |
|---|---|---|---|---|
| `ProjectOverviewSnapshot` | DTO | dm_project_quality_overview_day | projectId / statDate / 5×(displayValue+linkUrl) / 6 项状态类指标 | /ops-overview/main |
| `ProjectOverviewStat` | DTO | 多表实时聚合 | projectId / prDurationP90 / 6×(usage+total+rate) / avg×6 / 2 项 Nightly 指标 | /ops-overview/main |
| `ProjectResourceIndicator` | DTO | dwi_project_resource_indicator_day | projectId / statDate / PR/Nightly cpu/npu/memory 消耗/使用率 / 编译成功率 / 版本可用度 | /ops-overview/resource-summary, /ops-overview/main |
| `NightlyPipelineSummary` | DTO | dm_rd_efc_build_dim_nightly_pipeline_day | projectId / avgBuildSuccess / avgVersionAvail | /ops-overview/nightly-summary |
| `ComponentLinkConfig` | Entity + DTO | dim_component_link_config | projectId / colKey / displayValue / linkUrl | /ops-overview/link-config |
| `ProjectResourceTotal` | Entity + DTO | dim_project_resource_total | productId / projectId / pipelineType / type / groupId / cpuTotalCores / npuTotalCards / memoryTotalGb | /ops-overview/resource-summary, /ops-overview/main |
| `RepoQualitySnapshot` | Entity | dwi_repo_quality_scan_day | repoId / branchName / scanDate / top1/top2 语言 / 6 项状态字段 / 各工具规则数 | /common/detail (ops-repo-detail) |
| `RepoPipelineQualitySnapshot` | Entity | dwi_repo_pipeline_quality_day | projectId / repoId / statDate / hasAutoFix / hasOldCodecheck / hasNewCodecheck / usesProperCodecheck | /common/detail (ops-repo-detail) |
| `RepoDetailView` | 视图对象 | 多表 JOIN | repoId / repoName / stylePass / precommitPass / rulesTotal / 分语言规则数 / hasAutoFix / usesProperCodecheck / prDuration / 5 个 detail | /common/detail (ops-repo-detail) |
| `PipelineResourceDetail` | 视图对象 | dwi_rd_project_pipeline_relation + dwr_rd_efc_pipeline_run_fact | pipelineId / pipelineName / vcpu / vcpuAvg / npu / npuAvg | /common/detail (ops-resource-detail) |
| `PipelineRunRecord` | 视图对象 | dwr_rd_efc_pipeline_run_fact | runId / pipelineRunId / startTime / status / vcpu / npu | /common/detail (ops-resource-runs) |
| `NightlyPipelineDetail` | 视图对象 | sdi_version_pipeline_base_info + dwr_rd_efc_build_fact_nightly_test_case_pipeline_run | pipelineId / pipelineName / buildSuccess / versionAvail | /common/detail (ops-nightly-detail) |

### 7.3 权限控制

#### 7.3.1 接口权限设计

| 接口 | 权限要求 | 鉴权方式 |
|---|---|---|
| `POST /ops-overview/main` | 已登录用户 | Spring Security OAuth2/JWT 鉴权（依赖平台 RBAC） |
| `POST /ops-overview/resource-summary` | 已登录用户 | 同上 |
| `POST /ops-overview/nightly-summary` | 已登录用户 | 同上 |
| `GET /ops-overview/link-config` | 已登录用户 | 同上 |
| `POST /ops-overview/link-config` | **运营管理员** | `@PreAuthorize("hasRole('OPS_ADMIN')")` 或自定义注解 |
| `POST /common/detail`（4 个 category） | 已登录用户 | 同上 |

#### 7.3.2 资源总量录入权限

`dim_project_resource_total` 由后端 API 录入（本期不直接开放 UI，预留接口给运维同事）。建议：

- 入口：`POST /ops-overview/resource-total`（本期仅设计，不实现）
- 权限：运营管理员 + 系统管理员双角色确认
- 审计：录入操作记录到 `update_time` / `updated_by` 字段

#### 7.3.3 数据权限

| 维度 | 规则 |
|---|---|
| 项目隔离 | 不做项目级数据隔离（运营总览需跨项目聚合） |
| 用户隔离 | 仅做角色控制，不做 user-level 数据过滤 |
| 接口签名 | 所有写接口要求登录态 + 角色 + 接口幂等（防重复提交） |

#### 7.3.4 输入校验

| 校验项 | 规则 |
|---|---|
| 日期范围 | `startDate <= endDate`，跨度不超过 365 天 |
| 分页参数 | page >= 1, pageSize ∈ [1, 100] |
| sortField | 必须在白名单内，未命中抛 `BizException(BAD_REQUEST_UNKNOWN)` |
| sortRule | 必须匹配 `asc|desc`，默认 DESC |
| projectIds | 元素数量不超过 100 |
| type（资源卡片） | 必须 ∈ {PR, Nightly} |
| colKey（链接配置） | 必须 ∈ {ttfhw, envPrepare, incBuild, fullBuild, utExec} |

#### 7.3.5 SQL 注入防护

| 风险点 | 防护 |
|---|---|
| `ORDER BY ${sortField}` 字符串拼接 | `SortFieldValidator` 白名单校验，未命中抛异常 |
| 模糊搜索 LIKE | MyBatis `#{}` 参数绑定，自动转义 |
| 数值/日期参数 | MyBatis `#{}` 参数绑定 + `@Validated` 类型校验 |
| IN 列表 | MyBatis foreach 拼接，元素绑定参数 |

---

## 8 特性级 DFX 设计

本章从性能、安全&隐私、一致性、集成、可配置、可扩展六个维度对本期设计进行 DFX 审视。

### 8.1 性能

#### 8.1.1 关键性能指标

| 接口 | P95 响应时间目标 | P99 响应时间目标 | TPS 上限 |
|---|---|---|---|
| `POST /ops-overview/main` | ≤ 2s | ≤ 5s | 20 QPS |
| `POST /ops-overview/resource-summary` | ≤ 1s | ≤ 3s | 50 QPS |
| `POST /ops-overview/nightly-summary` | ≤ 1s | ≤ 3s | 50 QPS |
| `GET /ops-overview/link-config` | ≤ 500ms | ≤ 1s | 100 QPS |
| `POST /ops-overview/link-config` | ≤ 500ms | ≤ 1s | 50 QPS |
| `POST /common/detail`（4 个 category） | ≤ 2s | ≤ 5s | 20 QPS |

#### 8.1.2 性能瓶颈与优化

**主表查询瓶颈**：

| 瓶颈点 | 优化策略 |
|---|---|
| snapshot 段全量查询（无 SQL 内分页） | 项目数 < 100 时可接受；超过 100 改为 SQL 内分页（需先在 SQL 内完成 stat 段聚合） |
| stat 段 8 个 CTE 串联 | 已通过 Doris 物化视图 + Bucket 10 优化；PR/Nightly 资源聚合已落 `dwi_project_resource_indicator_day` 宽表 |
| Java 内存合并 + 排序 | List size < 100，Comparator switch 简单高效；如扩展可改为 SQL 内分页 |

**明细查询瓶颈**：

| 瓶颈点 | 优化策略 |
|---|---|
| `queryRepoDetail` 多表 JOIN（5+ 张） | CTE `latest_scan` + `e2e_p90` 预聚合；DISTRIBUTED BY HASH(repo_id) BUCKETS 10 |
| `queryResourceDetailList` type=PR/Nightly 双链路 | 类型分支在 SQL 入口 IF 分支，减少 Doris FE 解析开销 |
| `queryNightlyDetailList` 工作日过滤 | CTE `pipeline_version_avail` 预聚合到日级 |

**ETL 性能**：

| 瓶颈点 | 优化策略 |
|---|---|
| Python 脚本 clone 仓库慢 | 全量模式复用处理脚本预 clone 的仓库；增量模式仅扫描最近 3 天更新的分支 |
| ruff/clang-format/clang-tidy 调用慢 | `~/.local/bin` 已加 PATH，按语言分支跳过无关工具 |
| 500 条/批 INSERT | `insert_scan_results_to_db()` 批量提交 |
| Doris JSON 数组展开 10 位置 | UNION ALL 10 次，单次调度 SQL < 5s |

#### 8.1.3 缓存策略

| 缓存对象 | TTL | 失效策略 |
|---|---|---|
| `dm_project_quality_overview_day` 主表数据 | 无（实时查询 DM 表） | ETL 调度刷新 |
| 链接配置 | 无（实时查询 DIM 表） | 写操作 Doris UNIQUE KEY 自动覆盖 |
| 资源总量 | 无（实时查询 DIM 表） | API 录入时 Doris UNIQUE KEY 自动覆盖 |
| 节假日表 `dim_holiday` | 30 天（本地 Caffeine 缓存） | 启动时加载 + 定时刷新 |

#### 8.1.4 限流降级

- 网关层：`openlibing-gateway` 限流 100 QPS / IP
- 应用层：核心接口不降级（运营看板数据准确性优先）
- 数据层：Doris FE/BE 慢查询自动熔断（依赖 Doris 集群配置）

### 8.2 安全 & 隐私

#### 8.2.1 认证授权

| 维度 | 设计 |
|---|---|
| 认证 | 依赖 OpenLibing 平台 OAuth2/JWT，前端请求携带 `Authorization: Bearer <token>` |
| 鉴权 | Spring Security `@PreAuthorize` 注解 + 平台 RBAC |
| Token 存储 | 服务端无状态（JWT），不持久化用户 Token |
| Token 刷新 | 前端自动刷新（依赖平台 token refresh 机制） |

#### 8.2.2 数据脱敏

| 敏感字段 | 脱敏方式 |
|---|---|
| `auth_token`（Git 平台凭证） | Doris 落盘前用 `java -jar utils/decrypt-tool.jar` 解密 + 使用 + 不回写；Python 脚本只在内存中使用，不打印日志 |
| `auth_login`（Git 平台用户名） | 日志中脱敏为 `auth_login=***` |
| 用户邮箱/手机号 | 本期不涉及用户隐私数据 |

#### 8.2.3 凭证保护

| 凭证类型 | 保护策略 |
|---|---|
| Git 平台 token | MySQL 加密存储 → Doris 同步后解密使用 → 不回写 |
| 数据库密码 | Windows 用户级环境变量 `GC_TOKEN`；Doris 用户名/密码通过 DS 全局参数注入 |
| Salt 加密密钥 | 启动时从 `openlibing-ops` 服务环境变量 `ROOT_SALT` 读取 |

#### 8.2.4 审计日志

| 操作 | 审计字段 |
|---|---|
| 链接配置保存 | `dim_component_link_config.updated_by` + `update_time` |
| 资源总量录入（预留） | `dim_project_resource_total.updated_by` + `update_time` |
| 异常查询 | `BizException` 抛出时记录 `category` + `requestId` |

#### 8.2.5 网络安全

| 维度 | 措施 |
|---|---|
| HTTPS | 平台网关统一 HTTPS 终止 |
| CORS | 网关层白名单，仅允许内部域名 |
| CSRF | POST 接口要求 `Content-Type: application/json` + Token 校验 |
| DDoS | 网关层限流 + IP 黑名单 |

### 8.3 一致性设计

#### 8.3.1 数据一致性约束

| 一致性维度 | 约束 |
|---|---|
| 指标 1 排除无 PR 流水线仓库 | DM SQL 通过 `WHERE EXISTS (SELECT 1 FROM dwi_rd_project_pipeline_relation pr WHERE pr.repo_id = qs.repo_id)` 实现 |
| 指标 5 仅 PR 流水线 | 通过 `sdi_repo_pull_request_info` + `sdi_pr_pipeline_relation` 关联链路保证 |
| 指标 9 云上同组使用率相同 | CTE `pr_group_agg` / `nightly_group_agg` 按 group_id 聚合后所有同组项目 LEFT JOIN 同一行 |
| 指标 10/11 工作日过滤 | 使用 `dim_holiday` 表区分节假日（节假日也算工作日，周末不算） |
| 指标 6 P90 过滤条件 | `pipeline_status='ALL_PIPELINE_STATUS' AND state='merged' AND merged_at IS NOT NULL` |

#### 8.3.2 事务一致性

| 场景 | 一致性策略 |
|---|---|
| ETL 写入（DWI/DM/DIM） | Doris UNIQUE KEY + `enable_unique_key_merge_on_write=true` 实现幂等 upsert，重复执行同一日期自动覆盖 |
| 链接配置保存 | 循环调用 `upsertConfig(item)`，单条失败不影响其他项（事务粒度=单条） |
| API 录入资源总量 | 单事务提交，失败回滚 |

#### 8.3.3 最终一致性

| 维度 | 一致性窗口 |
|---|---|
| 主表 DM 表 | 每日凌晨 ETL 完成后；用户查询时取最新 stat_date 快照 |
| stat 段实时聚合 | 即时一致（直接查 Doris DWI/DIM） |
| 资源总量录入 | 写入立即生效（Doris UNIQUE KEY MoW） |
| 链接配置保存 | 写入立即生效（Doris UNIQUE KEY MoW） |

#### 8.3.4 冲突解决

| 冲突场景 | 解决策略 |
|---|---|
| ETL 重复执行同一日期 | Doris UNIQUE KEY MoW 自动覆盖，最后写入生效 |
| 资源总量录入与 stat 段聚合冲突 | stat 段优先（基于实时 DWI/DIM），资源总量仅作为分母 |
| 链接配置并发保存 | 单条 upsert 粒度，乐观锁（Doris 默认） |

#### 8.3.5 幂等性保证

| 接口 | 幂等策略 |
|---|---|
| `POST /ops-overview/link-config` | Doris UNIQUE KEY MoW 自动覆盖 |
| `POST /ops-overview/resource-total`（预留） | 同上 |
| `POST /ops-overview/main`（GET 类） | 无副作用，天然幂等 |
| ETL 调度 | Doris UNIQUE KEY MoW 自动覆盖 |

### 8.4 集成设计

#### 8.4.1 上下游集成清单

| 上游 | 集成方式 | 频率 |
|---|---|---|
| MySQL `pipeline_info` → Doris `raw_pipeline_info` | DataX/DS 同步 | 每日增量 |
| SCC 语言扫描 → `dwi_code_scan_language` | 已有 ETL | 每日 |
| DolphinScheduler 调度 → SQL/Python 节点 | DS 任务编排 | 每日凌晨 |
| `openlibing-ops-web` 前端 → 后端 API | HTTP/JSON | 实时 |
| `openlibing-gateway` 网关 → 后端 | HTTP 反向代理 | 实时 |

#### 8.4.2 接口契约

| 契约 | 管理方式 |
|---|---|
| 后端 ↔ 前端 | Swagger/OpenAPI 3.0（生成文档 + 校验） |
| 后端 ↔ Doris | MyBatis XML（手工维护 SQL） |
| ETL ↔ Doris | 直接 SQL 脚本（DS 任务编排） |

#### 8.4.3 错误处理与降级

| 失败场景 | 降级策略 |
|---|---|
| Doris 查询超时 | 接口返回 `Result.fail(BIZ_ERROR)`，前端展示「数据加载失败，请稍后重试」 |
| Doris UNIQUE KEY 冲突 | 静默覆盖（MoW 默认行为） |
| Python 脚本执行失败 | DS 任务标记失败，触发告警 + 邮件通知 |
| Git 平台 token 失效 | Python 脚本跳过该仓库 + 记录失败原因到日志 |

#### 8.4.4 数据格式兼容

| 兼容性 | 策略 |
|---|---|
| 新增字段 | Doris 不支持 UNIQUE KEY 表 ALTER 添加非空字段 → 新字段必须 `DEFAULT NULL` |
| 字段类型变更 | 严格向前兼容，避免下游解析失败 |
| 接口字段新增 | 响应新增字段不影响前端解析（前端只取需要的字段） |
| 接口字段删除 | 重大变更，需提前通知 + 灰度发布 |

### 8.5 可配置设计

#### 8.5.1 配置项清单

| 配置项 | 配置位置 | 默认值 | 说明 |
|---|---|---|---|
| 指标 1 排除规则 | DM SQL 内嵌 | 排除无 PR 流水线仓库 + status=3 | 不外置配置 |
| 指标 3 google-java-format 贡献规则数 | Python 脚本常量 | 31 条 | 来源 Google Java Format 官方文档 |
| 指标 9 统计时长 | 接口参数 | `startDate` / `endDate` | 用户可调 |
| 链接配置 colKey 枚举 | `OpsLinkConfigReq` 校验 + DB 注释 | ttfhw/envPrepare/incBuild/fullBuild/utExec | 5 列固定 |
| 主表分页 pageSize | 接口参数 | 10 | 上限 100 |
| 排序白名单 | `OpsOverviewService.MAIN_SORT_ALLOWED_FIELDS` 常量 | 39 字段 | 不可热更新 |
| 节假日表 `dim_holiday` | Doris 维护 | 国务院每年发布的节假日 | 每年初手工维护 |
| Python 脚本工具路径 | `~/.local/bin`（PATH 环境变量） | ruff / clang-format / clang-tidy / checkstyle | DS 任务启动时注入 PATH |
| `ROOT_SALT` | 服务环境变量 | 内部加密盐 | 启动时从环境变量读取 |

#### 8.5.2 资源池组配置（云上）

| group_id | 包含项目 | 共享资源 |
|---|---|---|
| `PTA_GROUP` | FrameworkPTAdapter / MindIE / MindCluster / MindEdge / MindSDK | PR + Nightly 共用 |
| `OPENEULER_GROUP` | openEuler + UBS Core | UBS Core 无 Nightly |

> 占位 `project_id`（负数）待后续补齐真实 ID。

#### 8.5.3 ETL 调度配置

| 配置 | 值 | 说明 |
|---|---|---|
| 调度频率 | 每日凌晨 | 依赖 SCC 任务先完成 |
| 超时 | 2-4 小时 | 根据仓库数量调整 |
| 失败重试 | 1 次 | DS 默认配置 |
| DS 全局参数 | `${repo_url}` / `${auth_login}` / `${auth_token}` / `${repo_id}` / `${show_branch}` / `${salt}` / `${openlibing_doris_url}` / `${openlibing_doris_username}` / `${openlibing_doris_password}` | 通过 DS 全局变量传递 |

### 8.6 可扩展设计

#### 8.6.1 新增指标扩展点

| 扩展点 | 扩展方式 |
|---|---|
| 新增状态类指标 | 1) 新增字段到 `dm_project_quality_overview_day` 2) 在 DM SQL CTE 中聚合 3) 主表 Resp 新增字段 4) 排序白名单新增字段 |
| 新增统计类指标 | 1) `OpsMainStatMapper.queryMainStat` 新增 CTE 2) 主表 Resp 新增字段 3) 排序白名单新增字段 |
| 新增明细下钻 | 1) 新建 `DetailService` 实现类 + `DetailCommonEnum` 枚举值 2) 新建 `Mapper` + XML 3) `OpsOverviewService` 新增查询方法 |

#### 8.6.2 新增语言扩展点

| 语言 | 工具 | 扩展点 |
|---|---|---|
| Rust | rustfmt | `check_code_style()` 增加 Rust 分支 + 配置项检测 |
| JavaScript | eslint / prettier | `check_code_style()` + `check_rules()` 增加 JS/TS 分支 |
| Go | gofmt（默认通过） | 无需扩展，已默认通过 |

#### 8.6.3 新增资源类型扩展点

| 资源类型 | 扩展方式 |
|---|---|
| 新增 GPU 资源 | `dim_project_resource_total` + `dwi_project_resource_indicator_day` + `dwr_rd_efc_pipeline_run_fact` 新增 gpu_seconds 字段 + SQL 新增聚合 |
| 新增存储资源 | 同上模式 |

#### 8.6.4 新增聚合维度扩展点

| 维度 | 扩展方式 |
|---|---|
| 产品级聚合 | DM SQL CTE 按 `product_id` 分组 + 主表 Resp 新增产品级字段 |
| 仓库级聚合 | 仓库明细 `OpsRepoDetailDetailResp` 已支持 |

#### 8.6.5 横向扩展

| 扩展点 | 策略 |
|---|---|
| Doris 节点扩容 | Doris 集群本身支持水平扩展（FE/BE 节点） |
| 后端服务扩容 | Spring Boot 无状态服务，支持 K8s 水平扩缩 |
| ETL 调度扩容 | DolphinScheduler Worker 节点扩展 |
| Python 脚本并行化 | 仓库级别可改为多 Worker 并行（DS 分片参数） |

---

## 9 关键技术设计

本章梳理本期实现中的关键技术点，覆盖 ETL 调度、JSON 数组展开、多态分发、UNIQUE KEY upsert、云上同组使用率一致性、工作日过滤等。

### 9.1 关键技术点清单

| 序号 | 关键技术点 | 涉及指标 | 复杂度 | 风险等级 |
|---|---|---|---|---|
| KT-1 | Doris JSON 数组索引展开 | 指标 4 | 中 | 低 |
| KT-2 | Doris UNIQUE KEY + MoW 幂等 upsert | 指标 1-8 全量 | 中 | 低 |
| KT-3 | 云上同组使用率一致性（CTE group_agg） | 指标 9 | 高 | 中 |
| KT-4 | 工作日过滤（dim_holiday 表 + WEEKDAY） | 指标 11 | 中 | 低 |
| KT-5 | 多态分发（@JsonSubTypes + Factory） | 接口 6 | 中 | 低 |
| KT-6 | Python 脚本多语言配置检测（ruff/clang-tidy/checkstyle） | 指标 1-3 | 高 | 中 |
| KT-7 | Java 内存合并 + 排序 + subList 分页 | 接口 1 主表 | 中 | 低 |
| KT-8 | Doris UNIQUE KEY 表 ALTER 限制 | DM 表新增字段 | 低 | 中 |
| KT-9 | 8 个 CTE 串联的 stat 段实时聚合 | 接口 1 stat 段 | 高 | 中 |
| KT-10 | Python 脚本 + Git 平台认证 + safe.directory | 指标 1-3 ETL | 中 | 中 |

### 9.2 KT-1：JSON 数组索引展开

#### 9.2.1 背景

Doris 不支持 PostgreSQL `JSONB ARRAY` 动态 UNNEST，无法使用 `unnest(config_json->'eventTriggers')`。需要手动展开数组的每个位置。

#### 9.2.2 方案

使用 `get_json_string(config_json, '$.eventTriggers[i].field')` 按索引 i 取出元素，UNION ALL 拼接 N 个位置（本期固定 10 个位置 0-9）。

```sql
TRUNCATE TABLE sdi_pipeline_event_trigger;
INSERT INTO sdi_pipeline_event_trigger (source_pipeline_id, project_id, trigger_index,
                                         is_enable, action_type, event_type)
SELECT source_pipeline_id, project_id, 0,
       get_json_string(config_json, '$.eventTriggers[0].isEnable'),
       get_json_string(config_json, '$.eventTriggers[0].actionType'),
       get_json_string(config_json, '$.eventTriggers[0].eventType')
FROM raw_pipeline_info
WHERE get_json_string(config_json, '$.eventTriggers[0].isEnable') IS NOT NULL
UNION ALL
SELECT source_pipeline_id, project_id, 1,
       get_json_string(config_json, '$.eventTriggers[1].isEnable'),
       get_json_string(config_json, '$.eventTriggers[1].actionType'),
       get_json_string(config_json, '$.eventTriggers[1].eventType')
FROM raw_pipeline_info
WHERE get_json_string(config_json, '$.eventTriggers[1].isEnable') IS NOT NULL
UNION ALL
-- ... 共 10 个位置 (0-9)
```

#### 9.2.3 注意事项

| 注意点 | 说明 |
|---|---|
| 数组长度上限 | 本期固定 10 个位置，超过的 pipeline 不在指标 4 统计范围内（实际生产中超过 10 个 eventTriggers 的极少） |
| 性能 | UNION ALL 10 次 ≈ 单 SQL < 5s，符合 ETL 调度预期 |
| 扩展 | 如未来需要支持更多位置，可改为 Python 脚本展开 + 批量 INSERT |

### 9.3 KT-2：Doris UNIQUE KEY + MoW 幂等 upsert

#### 9.3.1 背景

ETL 调度场景下需要保证重复执行同一日期的 SQL 不会产生脏数据（重复行）。传统方案是 `TRUNCATE + INSERT`，但在大表上 `TRUNCATE` 会锁表且删除历史快照。

#### 9.3.2 方案

Doris UNIQUE KEY + `enable_unique_key_merge_on_write=true`（MoW 模式）实现幂等 upsert：

- **UNIQUE KEY** 定义主键列（一个或多个）
- **MoW 模式** 保证相同 UNIQUE KEY 的行会被覆盖，而非追加
- 直接 `INSERT INTO ...` 即可，无需 `TRUNCATE`

```sql
CREATE TABLE dwi_repo_quality_scan_day (
    ...
) ENGINE=OLAP
UNIQUE KEY (repo_id, branch_name, scan_date)
DISTRIBUTED BY HASH(repo_id) BUCKETS 10
PROPERTIES ("replication_num" = "3", "enable_unique_key_merge_on_write" = "true");
```

#### 9.3.3 应用表清单

所有 DWI/DM/DIM 表（参见 3.4-3.6 节）均采用此模式：

| 表 | UNIQUE KEY |
|---|---|
| `dwi_repo_quality_scan_day` | (repo_id, branch_name, scan_date) |
| `dwi_repo_pipeline_quality_day` | (project_id, repo_id, stat_date) |
| `dwi_project_nightly_resource_day` | (project_id, stat_date) |
| `dwi_project_resource_indicator_day` | (project_id, stat_date) |
| `dm_project_quality_overview_day` | (project_id, stat_date) |
| `dim_component_link_config` | (project_id, col_key) |
| `dim_project_resource_total` | (product_id, project_id, pipeline_type) |

#### 9.3.4 注意事项

| 注意点 | 说明 |
|---|---|
| ALTER TABLE 添加非空字段 | Doris UNIQUE KEY 表不支持添加非空字段 → 必须 `DEFAULT NULL` |
| 性能 | MoW 模式写入比 DUPLICATE KEY 慢约 10-20%，但 ETL 调度场景可接受 |
| 一致性 | 同一 UNIQUE KEY 的多行写入顺序不保证，需要业务层保证幂等 |

### 9.4 KT-3：云上同组使用率一致性

#### 9.4.1 背景

指标 9 中云上项目共享资源池（通过 `group_id` 标识）。同一 group 下的多个项目使用率应该相同（因为分子分母都按组聚合）。需要保证 SQL 计算结果在同组项目行上数值一致。

#### 9.4.2 方案

CTE `pr_group_agg` / `nightly_group_agg` 按 `group_id` 聚合后 LEFT JOIN 所有同组项目：

```sql
-- CTE group_usage: 云上同组消耗求和
SELECT pd.group_id, c.stat_date,
       SUM(c.pr_cpu_seconds)    AS group_pr_cpu,
       SUM(c.pr_npu_seconds)    AS group_pr_npu,
       SUM(c.pr_memory_seconds) AS group_pr_memory,
       MAX(pd.cpu_total_cores)  AS group_cpu_total,
       MAX(pd.npu_total_cards)  AS group_npu_total,
       MAX(pd.memory_total_gb)  AS group_memory_total
FROM combined c
JOIN pr_dim pd ON c.project_id = pd.project_id
WHERE pd.group_id IS NOT NULL   -- 仅云上
GROUP BY pd.group_id, c.stat_date

-- 最终 SELECT CASE WHEN 区分云上/云下
CASE
    WHEN pd.group_id IS NOT NULL AND pga.group_cpu_total > 0
        THEN pga.group_pr_cpu / (pga.group_cpu_total * 86400)
    WHEN pd.group_id IS NULL AND pd.cpu_total_cores > 0
        THEN c.pr_cpu_seconds / (pd.cpu_total_cores * 86400)
END AS pr_cpu_usage_rate
```

#### 9.4.3 关键点

- **同组项目 LEFT JOIN 同一行**：所有 `PTA_GROUP` 项目查询时 LEFT JOIN 同一行 `pr_group_agg`，因此同组项目 `pr_cpu_usage_rate` 必然相同
- **MAX 取总量**：组共享总量用 `MAX(pd.cpu_total_cores)` 而不是 `SUM`，因为 `dim_project_resource_total` 中每个项目的总量相同，取任一项目的即可
- **NULLIF 保护**：`group_cpu_total > 0` 防止除零
- **云下独立计算**：不参与 `pr_group_agg`，直接在 CASE WHEN 中计算

#### 9.4.4 注意事项

| 注意点 | 说明 |
|---|---|
| group_id 一致性 | `dim_project_resource_total` 的 `group_id` 必须与 `dwi_rd_project_pipeline_relation` 等表保持一致，否则 LEFT JOIN 失败导致使用率不一致 |
| 数据缺失 | 同组项目某天无流水线运行时，group_agg 中无该天数据，前端展示 NULL |
| 时区 | 时间字段统一使用 Doris 服务器时区（UTC+8） |

### 9.5 KT-4：工作日过滤

#### 9.5.1 背景

指标 11 版本可用度只统计工作日（周一~周五 + 节假日），周末不算。需要排除周末但保留调休工作日（如国庆假期中的周末调休）。

#### 9.5.2 方案

使用 `WEEKDAY() < 5` 判断周一~周五，并 `IN (SELECT holiday_date FROM dim_holiday)` 包含节假日（因为节假日也算工作日，如春节调休的周末也算工作日）：

```sql
WHERE DATE(pipeline_run_endtime) BETWEEN #{startDate} AND #{endDate}
  AND (WEEKDAY(DATE(pipeline_run_endtime)) < 5  -- 周一~周五
       OR DATE(pipeline_run_endtime) IN (SELECT holiday_date FROM dim_holiday))  -- 节假日也算工作日
```

> `dim_holiday` 表存储所有「节假日」日期（包括调休的周末）。表内出现的日期即使是周末也算工作日，不在表内的周末则被排除。

#### 9.5.3 数据维护

| 来源 | 更新频率 | 维护方式 |
|---|---|---|
| 国务院办公厅每年发布的节假日通知 | 每年初 | 运维手工维护 dim_holiday 表 |
| 调休公告 | 临时 | 节假日当天或前 1 天补录 |

### 9.6 KT-5：多态分发（@JsonSubTypes + Factory）

#### 9.6.1 背景

`/common/detail` 是 OpenLibing 平台的统一明细接口，被 23 个业务线（23 个 `DetailService` 实现）共用。前端通过 `category` 字段区分业务类型。

#### 9.6.2 方案

**Jackson 多态反序列化**：`@JsonTypeInfo` + `@JsonSubTypes` 在反序列化时根据 `category` 字段自动创建对应子类实例。

```java
@JsonTypeInfo(use = Id.NAME, property = "category", visible = true)
@JsonSubTypes({
    @JsonSubTypes.Type(value = OpsRepoDetailDetailReq.class, name = "ops-repo-detail"),
    @JsonSubTypes.Type(value = OpsResourceDetailDetailReq.class, name = "ops-resource-detail"),
    @JsonSubTypes.Type(value = OpsResourceRunsDetailReq.class, name = "ops-resource-runs"),
    @JsonSubTypes.Type(value = OpsNightlyDetailDetailReq.class, name = "ops-nightly-detail"),
    // ... 共 23 个子类
})
public abstract class DetailReq extends TimeReq {
    private String category;
    // ... 其他通用字段
}
```

**Factory 模式分发**：`RepoDetailFactory` 在 Spring 启动时注入所有 `DetailService` 实现，构建 `Map<DetailCommonEnum, DetailService>`：

```java
@Component
public class RepoDetailFactory {
    private final Map<DetailCommonEnum, DetailService<?, ?>> handlers;

    public RepoDetailFactory(List<DetailService<T, R>> allHandlers) {
        this.handlers = allHandlers.stream()
            .collect(Collectors.toMap(DetailService::type, Function.identity()));
    }

    public DetailService<?, ?> getHandle(DetailCommonEnum type) {
        DetailService<?, ?> h = handlers.get(type);
        if (h == null) {
            log.error("unknown category: {}", type);
            throw new BizException(ResponseCodeEnum.BAD_REQUEST_UNKNOWN);
        }
        return h;
    }
}
```

#### 9.6.3 关键点

| 关键点 | 说明 |
|---|---|
| `visible = true` | 反序列化后 `category` 字段仍保留在子类实例中，业务可读 |
| `Id.NAME` + `property = "category"` | 通过 JSON 中的 `category` 字段识别类型 |
| 工厂注入 | Spring 自动注入 `List<DetailService>`，无需手工注册 |
| 未知 category | 抛 `BizException(BAD_REQUEST_UNKNOWN)`，前端可识别 |

### 9.7 KT-6：Python 多语言工具链调用

#### 9.7.1 背景

指标 1-3 需要在服务器端 clone 代码仓后调用 ruff / clang-format / clang-tidy / checkstyle 等工具扫描配置。涉及 Python 子进程调用、PATH 注入、safe.directory 等。

#### 9.7.2 方案

**PATH 注入**：

```python
import os
os.environ['PATH'] = os.path.expanduser('~/.local/bin') + ':' + os.environ['PATH']
```

**safe.directory 设置**：

```bash
git config --global --add safe.directory '*'
# 或在 checkout 时显式指定
git -c safe.directory='*' checkout show_branch
```

**子进程调用示例**：

```python
import subprocess

def check_python_ruff(repo_path: str) -> dict:
    # 默认规则数
    result = subprocess.run(
        ['ruff', 'linter', '--isolated', '--select', 'E,F,W', '--no-cache'],
        cwd=repo_path, capture_output=True, text=True, timeout=60
    )
    default_rules = len(result.stdout.strip().split('\n')) if result.returncode == 0 else 0
    
    # 启用规则数
    result = subprocess.run(
        ['ruff', 'linter', '--no-cache'],
        cwd=repo_path, capture_output=True, text=True, timeout=60
    )
    enabled_rules = len(result.stdout.strip().split('\n')) if result.returncode == 0 else 0
    
    return {
        'default_rules': default_rules,
        'enabled_rules': enabled_rules,
        'extra_rules': max(0, enabled_rules - default_rules),
    }
```

#### 9.7.3 关键点

| 关键点 | 说明 |
|---|---|
| PATH 注入 | DS 任务默认 PATH 不含 `~/.local/bin`，脚本启动时需注入 |
| safe.directory | 处理脚本预 clone 的仓库所有权可能不同，需跳过 dubious ownership |
| 超时控制 | 每个工具调用设置 60s 超时，防止卡死 |
| 异常处理 | 工具调用失败返回空结果，不阻塞整个仓库扫描 |
| 批量插入 | `insert_scan_results_to_db()` 500 条/批 INSERT，避免频繁连接 |

### 9.8 KT-7：Java 内存合并 + 排序 + subList 分页

#### 9.8.1 背景

主表查询需要合并两段（snapshot 段 + stat 段），且 stat 段排序字段无法在 snapshot 段 SQL 中完成。需要 Java 层合并 + 排序 + 分页。

#### 9.8.2 方案

```java
// 1. 全量查 snapshot 段
List<OpsOverviewMainResp> snapshotList = dmProjectQualityOverviewDayMapper.queryMainSnapshot(filter);

// 2. 提取 projectIds，全量查 stat 段
List<Integer> projectIds = snapshotList.stream().map(OpsOverviewMainResp::getProjectId).collect(toList());
List<OpsMainStat> statList = opsMainStatMapper.queryMainStat(projectIds, startDate, endDate);

// 3. Java 内存合并
List<OpsOverviewMainResp> merged = enrichResp(snapshotList, statList);

// 4. Java 内存排序（NULLS LAST）
merged.sort(buildMainComparator(req.getSortField(), req.getSortRule()));

// 5. Java 内存分页
int from = (req.getPage() - 1) * req.getPageSize();
int to = Math.min(from + req.getPageSize(), merged.size());
List<OpsOverviewMainResp> page = merged.subList(from, to);

return PageResult.of(page, merged.size(), req.getPage(), req.getPageSize());
```

#### 9.8.3 关键点

| 关键点 | 说明 |
|---|---|
| 项目数 < 100 | 内存排序 + subList 性能可接受；超过 100 改为 SQL 内分页 |
| NULLS LAST | 排序时 NULL 字段排在最后，避免污染排序结果 |
| Comparator switch | 39 字段 switch 简单高效，新增字段需同步修改白名单 |
| 不可变 subList | 返回 subList 是源 List 的视图，外部修改会影响源 List；返回前应 `new ArrayList<>(subList)` 包装 |

### 9.9 KT-8：Doris UNIQUE KEY 表 ALTER 限制

#### 9.9.1 背景

Doris 在 UNIQUE KEY 表上不支持添加非空字段。DM 表新增 `python_rules_avg` / `cpp_rules_avg` / `java_rules_avg` 字段时必须使用 `DEFAULT NULL`。

#### 9.9.2 方案

```sql
-- 错误：会报错
ALTER TABLE dm_project_quality_overview_day ADD COLUMN python_rules_avg DOUBLE NOT NULL;

-- 正确：使用 DEFAULT NULL
ALTER TABLE dm_project_quality_overview_day ADD COLUMN python_rules_avg DOUBLE DEFAULT NULL;
```

#### 9.9.3 关键点

| 关键点 | 说明 |
|---|---|
| 已有数据兼容 | 新字段默认 NULL，已有数据行不影响 |
| 业务处理 | 前端展示时 NULL 渲染为 `-` 或不展示 |
| 后续添加 | 后续如需添加更多字段，必须遵循 `DEFAULT NULL` 规范 |

### 9.10 KT-9：8 个 CTE 串联的 stat 段实时聚合

#### 9.10.1 背景

主表 stat 段需要实时计算多个指标（P90 / PR 消耗 / Nightly 消耗 / 使用率 / 编译成功率 / 版本可用度 / 平均消耗），每个指标来自不同的表，需要 8+ 个 CTE 串联。

#### 9.10.2 方案

`OpsMainStatMapper.queryMainStat` 8 个 CTE：

| CTE | 作用 | 数据源 |
|---|---|---|
| `p90_stat` | PR E2E P90 | dm_rd_efc_pr_sum_pipeline_statistics_day |
| `proj_meta` | 项目级 type/group_id | dim_project_resource_total |
| `group_usage` | 云上同组消耗求和 | dwi_project_resource_indicator_day + dim |
| `resource_sum` | 项目级 PR/Nightly 消耗 | dwi_project_resource_indicator_day |
| `pipeline_version_avail` | Nightly 版本可用度 | dm_rd_efc_build_dim_nightly_pipeline_day + dim_holiday |
| `pipeline_build_rate` + `nightly_rate` | Nightly 编译成功率 + 版本可用度 | dwr_rd_efc_build_fact_nightly_test_case_pipeline_run |
| `resource_total` | 资源总量 | dim_project_resource_total |
| `pr_count` / `nightly_count` | PR/Nightly 运行次数 | dwr_rd_efc_pipeline_run_fact |

最终 SELECT 使用 `CASE WHEN` 区分云上/云下计算使用率。

#### 9.10.3 关键点

| 关键点 | 说明 |
|---|---|
| CTE 顺序 | 后续 CTE 引用前序 CTE 的输出，必须按依赖顺序排列 |
| 性能 | Doris FE 会优化 CTE，单 SQL 通常 < 5s |
| 复用 | `OpsNightlyDetailMapper.queryNightlySummary` 复用 `pipeline_version_avail` / `nightly_stat` / `nightly_rate` CTE |
| NULL 处理 | `IFNULL(rt.*, 0)` + `NULLIF(分母, 0)` 双重保护 |

### 9.11 KT-10：Python 脚本 + Git 平台认证 + safe.directory

#### 9.11.1 背景

指标 1-3 ETL 需要 clone 私有仓库，依赖 Git 平台（gitcode/gitee/github）的认证 token。处理脚本预 clone 的仓库可能被当前用户识别为「dubious ownership」。

#### 9.11.2 方案

**Token 解密**：

```python
import subprocess

def decrypt_token(encrypted_token: str, salt: str) -> str:
    if not salt:
        return encrypted_token
    result = subprocess.run(
        ['java', '-jar', 'utils/decrypt-tool.jar', encrypted_token, salt],
        capture_output=True, text=True, timeout=10
    )
    return result.stdout.strip() if result.returncode == 0 else ''
```

**构造认证 URL**：

```python
def construct_auth_url(repo_url: str, login: str, token: str) -> str:
    # protocol://login:token@host/path
    parts = repo_url.split('://', 1)
    if len(parts) == 2:
        return f"{parts[0]}://{login}:{token}@{parts[1]}"
    return repo_url
```

**safe.directory 设置**：

```bash
git config --global --add safe.directory '*'
```

#### 9.11.3 关键点

| 关键点 | 说明 |
|---|---|
| Token 不落盘 | 仅在内存中使用，不打印日志，不写入 raw_repo_quality_scan |
| Token 加密 | MySQL 加密存储 → Doris 同步后解密使用 → 不回写 |
| dubious ownership | 处理脚本预 clone 的仓库所有权可能不同，全局 `safe.directory='*'` 跳过检查 |
| 用户执行 | DS 任务节点：root 初始化环境，dolphinscheduler 用户执行扫描 |

---

## 附录 A：变更记录

| 版本 | 日期 | 变更内容 |
|---|---|---|
| v1.0 | 2026-06-30 | 初版，基于需求设计说明书 v1.0 完成端到端技术设计，覆盖状态/实体/表/类/时序/逻辑/API&MO/DFX/关键技术 9 个章节 |