# UT 覆盖率上报与分支管理页展示 — 设计文档

## 1. 方案设计

### 需求背景

平台需要沉淀各代码仓分支的 UT（单元测试）覆盖率数据并在分支管理页查看。当前 coderepo 仅有代码度量（code metrics）指标，缺少 UT 覆盖率数据的接收、存储与展示链路。

### 整体方案

三仓跨仓改造，复用现有 code metrics 的 OBS + MQ 异步导入模式：

```
[CI 插件 upload-ut-action]
  用户指定目录 UT 报告（jacoco/coverage.py/go test/gcov/llvm-cov/cargo-llvm-cov/c8）
  → 解析转换标准 JSON（总体指标 + 文件明细）
  → 上传 OBS（openlibing-gitcode-action/ut-coverage-action/ 前缀，public-read）
  → 回调 coderepo POST /coverage/ut/report（仅传 gitUrl/branchName/pipelineRunId/obsUrl）
        ↓
[coderepo] /coverage/ut/report → MQ ut_coverage_import_queue（异步）
  → UtCoverageImportConsumer 下载 OBS 标准 JSON → 解析后双写：
      ① 历史表 code_ut_record 插入一条完整记录（含文件明细 JSON）
      ② 最新数据 upsert 到分支表 repo_branch 对应字段
        ↓
[coderepo] 分支列表接口直接读 repo_branch 返回各分支最新 UT 覆盖率
        ↓
[web] 分支管理页新增「UT覆盖率」列（从分支表数据渲染）→ 点击下钻文件明细（查历史表最新一条）
```

### 关键决策

| 决策点     | 决策                                                                       | 理由                                                   |
| ---------- | -------------------------------------------------------------------------- | ------------------------------------------------------ |
| 上报方式   | OBS + MQ 异步                                                              | 复用 code metrics 成熟链路，与用户确认一致             |
| 存储       | 最新数据存分支表 `repo_branch`（加字段），历史数据新建 `code_ut_record` 表 | 用户指定方案                                           |
| 页面数据源 | 分支表 `repo_branch` 直接读取最新值                                        | 用户指定；避免列表查询 join 历史表                     |
| 历史表     | 仅记录 + 供下钻取明细，不参与列表聚合                                      | 用户指定                                               |
| 明细存储   | `code_ut_record.coverage_file_detail_json` LONGTEXT                        | UT 明细量小（每文件数值），免建明细表                  |
| 下钻接口   | 新增 `POST /coverage/ut/file-detail`                                       | 从历史表（按分支最新一条）的文件明细 JSON 解析分页返回 |
| 指标缺省   | lineCoverage 必填必有；branch/method/class 可缺省（工具不支持时不传）      | 用户指定；页面不展示空指标                             |
| 插件       | 新建 `upload-ut-action` 独立仓                                             | 用户确认；复用 upload-sarif 的 OIDC/OBS/APIG 基础设施  |

## 2. 实现逻辑设计

### 2.1 coderepo 上报链路

1. `UtCoverageController.reportUtCoverage`：校验 DTO → 序列化为持久化消息 → `rabbitTemplate.convertAndSend("", utCoverageImportQueue, message)` → 返回"已受理"
2. `UtCoverageImportConsumer`（@RabbitListener，复用 `codeMetricsListenerContainerFactory`，并发 2-4）：反序列化 → 带内重重试（3 次，退避 1s/5s/15s）→ 调 `UtCoverageService.reportUtCoverage`
3. `UtCoverageServiceImpl.reportUtCoverage`：
   - 由 gitUrl 反查 `repo_info` 得到 repoId（双写与幂等均需要）
   - `obsBucketService.downloadToTempFile(obsUrl)` 流式下载到临时文件
   - fastjson2 `JSON.parseObject` 解析标准 JSON（UT 文件量小，整体解析即可）
   - 组装 `CodeUtRecordEntity`（历史记录）：4 覆盖率字段（可空）、coverageFileDetailJson（文件明细数组序列化）、pipelineRunId/commitId/runNumber/检测时间/status 等 → 插入 `code_ut_record`
   - 更新 `repo_branch`：按 (repoId, branchName) upsert 最新 4 覆盖率 + utPipelineRunId + utDetectionTime（唯一索引 uk_repo_branch_repo_id_name 定位）
   - 幂等：按 gitUrl+branchName+pipelineRunId 查历史表，已存在则跳过插入（仅允许重复消费）
   - finally 删除临时文件

### 2.2 coderepo 查询链路

1. 分支列表接口（`queryRepoBranchInfo` / `queryProjectBranch` → `buildProjectBranchInfoList`）：直接读取 `repo_branch` 表的 UT 字段，映射到 VO `utCoverage`，无需 join 历史表
2. `POST /coverage/ut/file-detail`：
   - 由 repoId 反查 repoUrl（gitUrl）
   - 按 (gitUrl, branchName) 查 `code_ut_record` 最新一条（可选按 pipelineRunId 精确定位）
   - 解析 `coverage_file_detail_json` → 分页/排序返回

### 2.3 插件解析流程

1. 扫描用户指定目录，按特征识别报告类型（优先级：具体扩展名 > 内容嗅探）
2. 各工具解析器产出统一中间结构（总体指标 + 文件明细数组）
3. 组装标准 JSON：`{gitUrl, branchName, pipelineRunId, commitId, lineCoverage, branchCoverage?, methodCoverage?, classCoverage?, fileDetails: [{filePath, lineCoverage, branchCoverage?, methodCoverage?, classCoverage?, lineCovered, lineTotal, branchCovered?, branchTotal?, methodCovered?, methodTotal?, classCovered?, classTotal?}]}`
4. 上传 OBS：`ut-coverage-action/{repoName}/{yyyyMMdd}.{HH}/{runId|manual}/ut-coverage.json`，ACL public-read，失败指数退避 3 次
5. OIDC 换证（`@openlibing/huaweicloud-oidc-client`）→ APIG V11 签名回调 `/coverage/ut/report`，失败退避重试 3 次（回调失败不阻断流程，OBS 已上传，可补导入）

## 3. 类设计

### coderepo 新增

| 类                                              | 说明                                                                                                         |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `UtCoverageController`                          | `POST /coverage/ut/report`（上报）+ `POST /coverage/ut/file-detail`（下钻）                                  |
| `UtCoverageReportDTO`                           | gitUrl/branchName/pipelineRunId/obsUrl（@NotBlank 校验）                                                     |
| `UtCoverageFileDetailQueryDTO`                  | repoId/branchName/pipelineRunId（可选）/pageNum/pageSize/sortByField/sort/fileName                           |
| `UtCoverageService` / `UtCoverageServiceImpl`   | reportUtCoverage（OBS 下载+解析+双写）、getUtCoverageFileDetail（下钻）                                      |
| `UtCoverageImportConsumer`                      | MQ 消费，复用 codeMetricsListenerContainerFactory，带内重重试                                                |
| `UtCoverageRabbitConfig`                        | 新队列 `ut_coverage_import_queue`                                                                            |
| `CodeUtRecordEntity`                            | 历史表实体（4 覆盖率可空 + 明细 JSON）                                                                       |
| `CodeUtRecordMapper` / `CodeUtRecordMapper.xml` | insert + selectLatestByGitUrlBranch + selectByPipelineRunId                                                  |
| `UtCoverageFileDetailVO`                        | gitUrl/repoName/branchName/pipelineRunId/runNumber/pipelineLink/checkTime/total/pageNum/pageSize/fileDetails |
| `UtCoverageFileItemVO`                          | filePath/lineCoverage/branchCoverage/methodCoverage/classCoverage/lineCovered/lineTotal 等                   |

### coderepo 修改

| 类                                         | 修改                                                                                                       |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `RepoBranchInfoEntity`                     | 新增 utLineCoverage/utBranchCoverage/utMethodCoverage/utClassCoverage/utPipelineRunId/utDetectionTime 字段 |
| `RepoBranchInfoMapper.xml`                 | 新增 upsert UT 覆盖率的 UPDATE 语句                                                                        |
| `ObsBucketServiceImpl`                     | `downloadToTempFile` 前缀白名单扩展为含 `ut-coverage-action/`                                              |
| `RepoBranchInfoVO` / `ProjectBranchInfoVO` | 新增 utCoverage 字段                                                                                       |
| `RepoServiceImpl`                          | queryRepoBranchInfo / buildProjectBranchInfoList 把分支表 UT 字段映射到 VO                                 |
| `db.changelog.xml`                         | 新增 changeSet：repo_branch 加 6 字段 + 建 code_ut_record 表                                               |
| `application.yaml`                         | 新增 `ut_coverage_import_queue` 配置                                                                       |

> 注：`CodeMetricsRecordEntity` / `CodeMetricsRecordMapper.xml` / `CodeMetricsServiceImpl` 不修改（UT 数据不再复用 code_metrics_record，零侵入现有 code metrics 链路）。

### 插件 upload-ut-action 新增

| 文件                                   | 说明                                             |
| -------------------------------------- | ------------------------------------------------ |
| `index.js`                             | 主流程（参数 → 扫描 → 解析 → 转换 → OBS → 回调） |
| `src/parser/ReportScanner.js`          | 扫描目录识别工具报告                             |
| `src/parser/JacocoParser.js`           | jacoco.xml 解析                                  |
| `src/parser/CoveragePyParser.js`       | coverage.json 解析                               |
| `src/parser/GoTestParser.js`           | coverage.out 解析                                |
| `src/parser/GcovParser.js`             | .gcov / llvm-cov lcov 解析                       |
| `src/parser/C8Parser.js`               | coverage-final.json 解析                         |
| `src/parser/CargoLlvmCovParser.js`     | cargo-llvm-cov（lcov/json）解析                  |
| `src/normalizer/CoverageNormalizer.js` | 统一结构 → 标准 JSON（可缺省指标）               |
| `src/obs/ObsUploader.js`               | OIDC 换证 + OBS 上传 + APIG 回调                 |
| `action.yml`                           | report_dir/env_type 等输入                       |

### web 新增/修改

| 文件                         | 修改                                                                            |
| ---------------------------- | ------------------------------------------------------------------------------- |
| `branches.vue`               | 新增「UT覆盖率」列（显示 lineCoverage，如 85.3%），点击 emit goUtCoverageDetail |
| `UtCoverageDetailDialog.vue` | 新增：指标概览（仅展示有数据的指标）+ 文件明细表格（分页/排序）                 |
| `index.vue`                  | 新增 goUtCoverageDetail 处理，打开弹窗                                          |
| `api.ts` / `url.ts`          | 新增 utCoverageFileDetail 调用                                                  |

## 4. 数据模型设计

### 4.1 分支表 `repo_branch` 新增字段（最新数据）

Liquibase changeSet `20260917_add_ut_coverage_to_repo_branch`：

| 字段                 | 类型              | 说明                                                |
| -------------------- | ----------------- | --------------------------------------------------- |
| `ut_line_coverage`   | DECIMAL(5,2) NULL | UT 行覆盖率（%），唯一必有指标                      |
| `ut_branch_coverage` | DECIMAL(5,2) NULL | UT 分支覆盖率（%），可缺省                          |
| `ut_method_coverage` | DECIMAL(5,2) NULL | UT 方法覆盖率（%），可缺省                          |
| `ut_class_coverage`  | DECIMAL(5,2) NULL | UT 类覆盖率（%），可缺省                            |
| `ut_pipeline_run_id` | VARCHAR(512) NULL | 最近一次 UT 上报的流水线执行 ID（下钻定位历史记录） |
| `ut_detection_time`  | DATETIME NULL     | 最近一次 UT 检测完成时间                            |

### 4.2 历史表 `code_ut_record`（新建）

Liquibase changeSet `20260917_create_table_code_ut_record`：

| 字段                        | 类型                                        | 说明                             |
| --------------------------- | ------------------------------------------- | -------------------------------- |
| `id`                        | BIGINT UNSIGNED PK                          | 主键，雪花算法                   |
| `git_url`                   | VARCHAR(512) NOT NULL                       | 仓库 URL                         |
| `branch_name`               | VARCHAR(255) NOT NULL                       | 分支名称                         |
| `pipeline_run_id`           | VARCHAR(512) NULL                           | 流水线执行 ID（幂等 + 下钻定位） |
| `run_number`                | VARCHAR(64) NULL                            | 流水线运行编号                   |
| `commit_id`                 | VARCHAR(64) NULL                            | commit ID                        |
| `line_coverage`             | DECIMAL(5,2) NULL                           | 行覆盖率（%）                    |
| `branch_coverage`           | DECIMAL(5,2) NULL                           | 分支覆盖率（%），可缺省          |
| `method_coverage`           | DECIMAL(5,2) NULL                           | 方法覆盖率（%），可缺省          |
| `class_coverage`            | DECIMAL(5,2) NULL                           | 类覆盖率（%），可缺省            |
| `coverage_file_detail_json` | LONGTEXT NULL                               | 文件级明细 JSON 数组             |
| `detection_completed_at`    | DATETIME NULL                               | 检测完成时间                     |
| `status`                    | TINYINT NOT NULL DEFAULT 0                  | 0-成功，1-失败                   |
| `error_message`             | TEXT NULL                                   | 失败原因                         |
| `create_time`               | DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间                         |

索引：`INDEX idx_git_branch (git_url(255), branch_name, detection_completed_at)`

### 4.3 标准上报 JSON（插件 → OBS → 后端解析）

```json
{
  "gitUrl": "https://gitcode.com/owner/repo",
  "branchName": "master",
  "pipelineRunId": "123456",
  "commitId": "abc123",
  "lineCoverage": 85.3,
  "branchCoverage": 78.1,
  "methodCoverage": 92.0,
  "classCoverage": 95.2,
  "fileDetails": [
    {
      "filePath": "src/main/java/Foo.java",
      "lineCoverage": 90.0,
      "branchCoverage": 80.0,
      "methodCoverage": 100.0,
      "classCoverage": 100.0,
      "lineCovered": 90,
      "lineTotal": 100,
      "branchCovered": 8,
      "branchTotal": 10,
      "methodCovered": 4,
      "methodTotal": 4,
      "classCovered": 1,
      "classTotal": 1
    }
  ]
}
```

- `lineCoverage` 必填（所有工具均应产出）；`branchCoverage` / `methodCoverage` / `classCoverage` 及对应明细字段可缺省（工具不支持时不传）
- 后端解析容错：缺省指标存 NULL，页面不展示该指标

## 5. 性能设计

- UT 文件量小（通常几十 KB ~ 几百 KB），JSON 整体解析无 OOM 风险，无需流式四遍解析
- 下载临时文件用后即删，避免磁盘占用
- 分支列表直接读 `repo_branch` 表字段，无额外 join/聚合，性能与现有列表一致
- 下钻从 `code_ut_record` 按 (gitUrl, branchName) 取最新一条（走 idx_git_branch 索引），明细在内存分页
- MQ 消费者复用 codeMetricsListenerContainerFactory（prefetch=1），避免消息积压

## 6. API接口设计

### POST /coverage/ut/report（机机接口，APIG）

请求：

```json
{
  "gitUrl": "https://...",
  "branchName": "master",
  "pipelineRunId": "123",
  "obsUrl": "https://openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com/ut-coverage-action/..."
}
```

响应：`{ "code": 200, "data": "上报已受理，正在异步导入" }`

### POST /coverage/ut/file-detail（web 下钻）

请求：

```json
{
  "repoId": 1,
  "branchName": "master",
  "pipelineRunId": "",
  "pageNum": 1,
  "pageSize": 10,
  "sortByField": "lineCoverage",
  "sort": "desc",
  "fileName": ""
}
```

（pipelineRunId 可选：传则精确定位该次记录，不传取分支最新一条）
响应：`{ "code": 200, "data": { "gitUrl", "repoName", "branchName", "pipelineRunId", "runNumber", "pipelineLink", "checkTime", "total", "pageNum", "pageSize", "fileDetails": [...] } }`

### 分支列表接口（现有，新增返回字段）

`/repo/branch/list`、`/project-repo/query-repo-branch` 返回行新增：

```json
"utCoverage": { "lineCoverage": 85.3, "branchCoverage": 78.1, "methodCoverage": null, "classCoverage": null, "pipelineRunId": "123" }
```

无数据显示 null；null 指标前端不展示。

## 7. 安全设计

- **鉴权**：`/coverage/ut/report` 为机机接口，经 APIG 网关暴露（与 CodeMetricsController 同策略，网关鉴权/限流）；web 下钻接口复用 `verifyPermissionsByProduct` 仓库权限校验（与现有 file-detail 一致）
- **敏感信息**：日志只打 gitUrl/branchName/pipelineRunId；OBS 凭证仅服务端持有，插件用 OIDC 临时凭证（短期有效）上传，对象 ACL public-read（与 code metrics 一致，后端匿名 HTTP GET 下载）
- **硬编码**：无硬编码凭证；OBS 桶/前缀、APIG 域名从配置/常量读取，与 code metrics 一致
- **审计日志**：上报接口 logger.info 记录 gitUrl/pipelineRunId/branchName；入库成功/失败均记录日志与失败记录（status + errorMessage）

## 不涉及 / 不做

- 不改造现有 code metrics 的 OBS 下载、解析、入库逻辑与表（UT 零侵入）
- 不改 `code_metrics_record` / `code_metrics_file_detail` 表
- 不做覆盖率历史趋势（历史表仅记录，后续需求再扩展）
