# /full-codecheck-record/list 接入静态告警降级查询 - 技术设计

> 状态：最终方案。字段映射口径已落定，跨仓改动清单已列明。

## 1. 现状回顾

### 1.1 接口现状

- 路径：`POST /machine-api/v1/full-codecheck-record/list`
- 入参：`QueryTaskSummaryMachineApiModel`（机机接口专用 DTO，分页字段无校验注解）
- 出参：`DataResult<PageVo>`，`PageVo.list` 元素为 `CodeCheckResultSummaryDTO`
- 当前实现：`MachineApiCheckboardController#queryFullTaskResultSummary` → `CheckboardDelegateImpl#queryFullTaskResultSummary` → `FullSummaryOperation#queryFullSummaryList`
- 数据源：MongoDB `task_result_summary` 集合（华为云 CodeCheck 入库）
- 接口定位：**面向入湖消费方的查询接口**（外部数据湖服务通过该接口拉取 `task_result_summary` 数据去入库）

### 1.2 写入链路（参考）

`task_result_summary` 入库由 `SaveFullTaskResult#createDailyCheckSyncTask` 完成，触发条件为 RabbitMQ `fullcodecheck_queue` 消费事件。所有正常入库的 summary 都会被 `setObProjectId`，故原查询硬过滤 `obProjectId exists true` 是安全的。

### 1.3 CodeQL 数据链路（参考）

CodeQL 数据通过 SARIF 上报链路入库，涉及表：

- `static_alarm_scan_run`：扫描记录表（一次扫描一条）
- `static_alarm_issue`：静态告警问题表（按指纹去重，多次扫描复用）
- `hw_project_info`：项目-hw 映射表（`project_id ↔ hw_project_id`）
- `repo_info`：仓库信息表（通过 `projectId` 反查 `repoId`）

CodeQL 度量数据位于 `openlibing-coderepo` 仓：

- `code_metrics_record`：顶层度量（`metrics_data_json`）
- `code_metrics_file_detail`：文件级度量明细（`metrics_json`）

详见 `spec/openlibing-codecheck/task_design/static-alarm/design.md`。

## 2. 设计目标

1. **契约不变**：接口路径、HTTP 方法、入参、出参结构不变
2. **行为变化可隔离**：降级逻辑独立放在新 Operation，不污染原 `FullSummaryOperation`
3. **降级触发可控**：只在「明确指定了仓库定位字段但 task_result_summary 无数据」时触发
4. **可观测**：降级触发、查询耗时、异常均有日志
5. **可演进**：静态告警字段口径补充时只改 `StaticAlarmSummaryOperation` 内部，不影响外部契约
6. **跨仓协同**：本次改动覆盖 `openlibing-codecheck` 与 `openlibing-coderepo` 两仓，跨仓改动通过 PR 矩阵同步

## 3. 整体方案

### 3.1 调用链路（改造后）

```
MachineApiCheckboardController#queryFullTaskResultSummary
  └─ CheckboardDelegateImpl#queryFullTaskResultSummary（修改）
       ├─ fullSummaryOperation.queryFullSummaryList(query)      // 原华为云路径
       │     └─ 返回 PageVo pageVoHw
       ├─ if (pageVoHw.total == 0 && hasRepoLocator(query))
       │     └─ staticAlarmSummaryOperation.queryStaticAlarmSummaryList(query)  // 新增降级路径
       │           ├─ buildCriteriaFromQuery(query)              // 翻译过滤条件
       │           ├─ countScanRun / pageScanRun                  // scan_run 分页
       │           ├─ batchAggregateIssues(scanRunIds)            // issue 按状态聚合
       │           ├─ enrichRepoAndProjectInfo(scanRuns)         // 反查 repo_info / hw_project_info
       │     ├─ enrichCodeMetrics(scanRuns)                 // Feign 调 coderepo 按 repo_url+branch+commit_id 关联度量
      │           // 以 scan_run 为主，按 commit_id 精确匹配取最近的 code_metrics_record
       │           │     // 找不到则度量字段走默认值（详见 §4.6）
       │           └─ toDtos(scanRuns, issueStats, metrics)       // 组装 DTO
       │     └─ 返回 PageVo pageVoStaticAlarm
       └─ return DataResult.successData(pageVoStaticAlarm != null ? pageVoStaticAlarm : pageVoHw)
```

### 3.2 降级触发判定

```java
private boolean shouldFallbackToStaticAlarm(PageVo pageVo, QuerySummaryModel query) {
  // 1. 原查询无数据
  if (pageVo.getTotal() != 0 || CollectionUtils.isNotEmpty(pageVo.getList())) {
    return false;
  }
  // 2. 至少一个仓库定位字段非空（避免无条件查询触发 CodeQL 扫表）
  return hasRepoLocator(query);
}

private boolean hasRepoLocator(QuerySummaryModel query) {
  return StringUtils.isNotBlank(query.getProjectName())
      || StringUtils.isNotBlank(query.getRepoName())
      || StringUtils.isNotBlank(query.getRepoUrl())
      || StringUtils.isNotBlank(query.getGitUrl())
      || (query.getProjectId() != null)
      || CollectionUtils.isNotEmpty(query.getRepoIds());
}
```

**为什么要求仓库定位字段非空**：

- 入湖消费方典型场景是「拉取某个项目/仓库的 codecheck 数据入湖」，无仓库定位的全量查询在入湖场景下没有意义
- 不限制时，任意一次空查询都会触发 CodeQL `static_alarm_scan_run` 全表 count + find，可能造成性能压力
- 与同仓历史 spec「查询必须有定位条件」的口径一致

## 4. CodeQL 数据组装层

### 4.1 类结构

```
com.openlibing.codecheck.business.operation.codecheck
  └─ StaticAlarmSummaryOperation           // 新增
       ├─ queryStaticAlarmSummaryList(QuerySummaryModel query): PageVo
       │     // 主入口：count + 分页 find 内联完成（MongoTemplate）
       ├─ buildCriteriaFromQuery(query): Criteria
       │     // 把 QuerySummaryModel 的过滤条件翻译成 CodeQL 表上的等价条件
       │     // 具体映射见 §4.4
       ├─ batchAggregateIssues(scanRuns): Map<scanRunId, IssueStats>
       │     // 按 pipeline_run_id 聚合 status / severity 各档计数
       │     // 仅对快照字段未就绪的 scan_run 聚合（needIssueAggregationFallback 判定）
       ├─ enrichRepoAndProjectInfo(scanRuns): Map<repoUrl, RepoContext>
       │     // 批量反查 repo_info / project_info / hw_project_info，内存 Map 关联
       ├─ enrichCodeMetrics(scanRuns): Map<groupKey, CodeMetricsSnapshotDTO>
       │     // Feign 调 coderepo getLatestMetricsByCommitBatch(queries)
       │     // 按 (repo_url, branch, commit_id) 三元组批量关联 code_metrics_record
       │     // 以 scan_run 为主，按 commit_id 精确匹配（详见 §4.6）
       ├─ toDto(scanRun, issueStats, metrics): CodeCheckResultSummaryDTO
       │     // 单条 scan_run + 聚合的 issue 统计 + 度量数据 → 一条 DTO
       ├─ resolveXxxCount 系列 / applyMetrics / mapScanRunStatus
       │     // 计数字段快照优先、issue 聚合兜底；度量字段填充；状态枚举映射
       └─ groupKey(repoUrl, branch, commitId): String
             // 度量关联的内存索引键
```

### 4.2 不复用 FullSummaryOperation 的原因

- `FullSummaryOperation` 强依赖 `CodeCheckResultSummaryVo`（华为云侧 VO），与 CodeQL 表结构不兼容
- `prepareSummary` 的 VO→DTO 转换逻辑包含华为云特有的字段处理，CodeQL 路径不应复用
- 解耦后，CodeQL 数据口径调整时只改一个 Operation 类，不影响华为云路径

### 4.3 字段映射方案

#### 4.3.1 不对接字段（12 个，DTO 字段不返回或置 null）

降级路径不对接以下字段，DTO 字段不返回（若 DTO 结构固定则置 null）：

`inReviewCount` / `invalidCount` / `commentRatio` / `fileDuplicationTotal` / `filesTotal` / `methodLines` / `methodsTotal` / `unsafeFunctionsCount` / `nonHeaderFileDuplicationRate` / `mrId` / `prId` / `mrUrl`

`repoUrl` 仍在对接范围内（取 `static_alarm_scan_run.repo_url`），仅 `mrUrl` 不对接。

#### 4.3.2 字段映射表（50 个字段）

| #   | DTO 字段                         | 来源表                  | 来源字段 / 规则                                                      | 备注                                                                                                                                                                                                         |
| --- | -------------------------------- | ----------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `id`                             | `static_alarm_scan_run` | `id`                                                                 | 直接取                                                                                                                                                                                                       |
| 2   | `date`                           | `static_alarm_scan_run` | `createdAt`                                                          | 格式化 `yyyy-MM-dd`                                                                                                                                                                                          |
| 3   | `dateTime`                       | `static_alarm_scan_run` | `(updatedAt - createdAt) / 1000`                                     | 秒级耗时，取整                                                                                                                                                                                               |
| 4   | `repoNameEn`                     | `static_alarm_scan_run` | `repo`                                                               | 直接取                                                                                                                                                                                                       |
| 5   | `repoId`                         | 反查 `repo_info`        | 通过 `projectId` 反查                                                | 反查不到置 null                                                                                                                                                                                              |
| 6   | `projectName`                    | 反查 project 表         | 通过 `projectId` 反查                                                | 反查不到置 null                                                                                                                                                                                              |
| 7   | `obProjectId`                    | 入参 `projectId` 透传   | —                                                                    | 与原接口硬过滤口径对齐                                                                                                                                                                                       |
| 8   | `projectId` (hwProjectId)        | 反查 `hw_project_info`  | `project_id → hw_project_id`                                         | 反查不到置 null                                                                                                                                                                                              |
| 9   | `executeTime`                    | `static_alarm_scan_run` | `createdAt`                                                          | `yyyy-MM-dd HH:mm:ss` 格式化                                                                                                                                                                                 |
| 10  | `endTime`                        | `static_alarm_scan_run` | `updatedAt`                                                          | `yyyy-MM-dd HH:mm:ss` 格式化                                                                                                                                                                                 |
| 11  | `gitBranch`                      | `static_alarm_scan_run` | `branch`                                                             | 直接取                                                                                                                                                                                                       |
| 12  | `taskId`                         | —                       | —                                                                    | 不对接，置 null                                                                                                                                                                                              |
| 13  | `taskName`                       | —                       | —                                                                    | 不对接，置 null                                                                                                                                                                                              |
| 14  | `lastCheckTime` / `lastExecTime` | `static_alarm_scan_run` | `updatedAt`                                                          | 与 endTime 一致                                                                                                                                                                                              |
| 15  | `createdAt`                      | `static_alarm_scan_run` | `createdAt`                                                          | `yyyy-MM-dd HH:mm:ss` 格式化                                                                                                                                                                                 |
| 16  | `creatorId`                      | —                       | —                                                                    | 不对接，置 null                                                                                                                                                                                              |
| 17  | `checkType`                      | 固定值                  | `"source"`                                                           | 字面字符串                                                                                                                                                                                                   |
| 18  | `result`                         | `static_alarm_scan_run` | `issue_snapshot`                                                     | `issue_snapshot > 0 ? "failed" : "pass"`（add-count-yym 分支将 `issue_count` 更名为 `issue_snapshot`）                                                                                                       |
| 19  | `codeCheckStatus`                | `static_alarm_scan_run` | `status`                                                             | `SUCCESS→"success" / FAILED→"failed" / PARSING→"processing"`                                                                                                                                                 |
| 20  | `type`                           | 固定值                  | `"new"`                                                              | —                                                                                                                                                                                                            |
| 21  | `isDeleted`                      | 固定值                  | `0`                                                                  | —                                                                                                                                                                                                            |
| 22  | `isBack`                         | 固定值                  | `false`                                                              | —                                                                                                                                                                                                            |
| 23  | `total`                          | `static_alarm_scan_run` | `issue_snapshot`                                                     | 与 `issue` 字段同值（add-count-yym 分支将 `issue_count` 更名为 `issue_snapshot`）                                                                                                                            |
| 24  | `issue`                          | `static_alarm_issue`    | `status`                                                             | `status="OPEN"` 计数，按 `scan_run_id` 聚合                                                                                                                                                                  |
| 25  | `solve`                          | `static_alarm_issue`    | `status`                                                             | `status="RESOLVED"` 计数                                                                                                                                                                                     |
| 26  | `ignore`                         | `static_alarm_issue`    | `status`                                                             | `status="IGNORED"` 计数                                                                                                                                                                                      |
| 27  | `inReview`                       | 固定值                  | `0`                                                                  | 不需要审批                                                                                                                                                                                                   |
| 28  | `invalid`                        | 固定值                  | `0`                                                                  | —                                                                                                                                                                                                            |
| 29  | `ignoreCount`                    | `static_alarm_scan_run` | `ignore_snapshot`                                                    | scan_run 新增字段；未就绪回退到 issue 表 `status="IGNORED"` 聚合                                                                                                                                             |
| 32  | `issueCount`                     | `static_alarm_scan_run` | `issue_snapshot`                                                     | scan_run 新增字段；未就绪回退到 issue 表 `status="OPEN"` 聚合                                                                                                                                                |
| 33  | `newCount`                       | `static_alarm_scan_run` | `issue_snapshot`                                                     | 与 #32 `issueCount` 同源（add-count-yym 分支已将 `issue_count` 更名为 `issue_snapshot`，原 `new_issue_count` 字段被移除，本字段语义降级为复用 `issue_snapshot`）；未就绪回退到 issue 表 `status="OPEN"` 聚合 |
| 34  | `solveCount`                     | `static_alarm_scan_run` | `solve_snapshot`                                                     | scan_run 新增字段；未就绪回退到 issue 表 `status="RESOLVED"` 聚合                                                                                                                                            |
| 35  | `criticalCount`                  | `static_alarm_scan_run` | `critical_count_snapshot`                                            | scan_run 新增字段；未就绪回退到 issue 表 `severity="Critical"` 聚合                                                                                                                                          |
| 36  | `majorCount`                     | `static_alarm_scan_run` | `major_count_snapshot`                                               | scan_run 新增字段；未就绪回退到 issue 表 `severity="High"` 聚合                                                                                                                                              |
| 37  | `minorCount`                     | `static_alarm_scan_run` | `minor_count_snapshot`                                               | scan_run 新增字段；未就绪回退到 issue 表 `severity="Medium"` 聚合                                                                                                                                            |
| 38  | `suggestionCount`                | `static_alarm_scan_run` | `suggestion_count_snapshot`                                          | scan_run 新增字段；未就绪回退到 issue 表 `severity="Low"` 聚合                                                                                                                                               |
| 39  | `codeLine`                       | `code_metrics_record`   | `metrics_data_json.codeScale`                                        | 度量数据走 §4.6 commit 精确关联；找不到记录置 0                                                                                                                                                                     |
| 40  | `codeLineTotal`                  | `code_metrics_record`   | `metrics_data_json` 新增字段（暂命名 `codeLineTotal`）               | 度量数据走 §4.6 commit 精确关联；依赖 coderepo 改造；未就绪或找不到记录置 null 或 0                                                                                                                                 |
| 41  | `codeQuality`                    | 固定值                  | `100`                                                                | —                                                                                                                                                                                                            |
| 42  | `commentLines`                   | `code_metrics_record`   | `metrics_data_json` 新增字段（暂命名 `commentLines`）                | 度量数据走 §4.6 commit 精确关联；依赖 coderepo 改造；未就绪或找不到记录置 0                                                                                                                                         |
| 44  | `complexityCount`                | `code_metrics_record`   | `metrics_data_json` 新增字段（暂命名 `complexityCount`）             | 度量数据走 §4.6 commit 精确关联；依赖 coderepo 改造；未就绪或找不到记录置 0                                                                                                                                         |
| 45  | `cyclomaticComplexityPerMethod`  | `code_metrics_record`   | `metrics_data_json.avgCyclomaticComplexity`                          | 度量数据走 §4.6 commit 精确关联；找不到记录置 0                                                                                                                                                                     |
| 46  | `cyclomaticComplexityPerFile`    | `code_metrics_record`   | `metrics_data_json` 新增字段（暂命名 `cyclomaticComplexityPerFile`） | 度量数据走 §4.6 commit 精确关联；依赖 coderepo 改造；未就绪或找不到记录置 null                                                                                                                                      |
| 47  | `duplicatedBlocks`               | `code_metrics_record`   | `metrics_data_json` 新增字段（暂命名 `duplicatedBlocks`）            | 度量数据走 §4.6 commit 精确关联；依赖 coderepo 改造；未就绪或找不到记录置 0                                                                                                                                         |
| 48  | `duplicatedLines`                | `code_metrics_record`   | `metrics_data_json` 新增字段（暂命名 `duplicatedLines`）             | 度量数据走 §4.6 commit 精确关联；依赖 coderepo 改造；未就绪或找不到记录置 0                                                                                                                                         |
| 49  | `duplicationRatio`               | `code_metrics_record`   | `metrics_data_json.totalCodeDuplicationRate`                         | 度量数据走 §4.6 commit 精确关联；找不到记录置 `"0"` 或 null                                                                                                                                                         |
| 50  | `fileDuplicationRatio`           | `code_metrics_record`   | `metrics_data_json.totalFileDuplicationRate`                         | 度量数据走 §4.6 commit 精确关联；找不到记录置 `"0"` 或 null                                                                                                                                                         |
| 57  | `metricInfo`                     | `code_metrics_record`   | `metrics_data_json` 原文                                             | 度量数据走 §4.6 commit 精确关联；找不到记录置 null 或空 JSON 字符串                                                                                                                                                 |
| 58  | `riskCoefficient`                | 固定值                  | `100`                                                                | —                                                                                                                                                                                                            |
| 59  | `taskRuleInfo`                   | —                       | —                                                                    | 不对接，置 null                                                                                                                                                                                              |
| 62  | `repoUrl`                        | `static_alarm_scan_run` | `repo_url`                                                           | 直接取（仅 `mrUrl` 不对接置 null）                                                                                                                                                                           |

> 字段编号沿用原始 62 字段表，未出现的编号即 §4.3.1 列出的不对接字段。

### 4.4 过滤条件翻译

| QuerySummaryModel 字段 | CodeQL 侧等价条件                                                                                                                                               |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| —（固定过滤，非入参）  | `static_alarm_scan_run.tool != "CodeQL"`（法律合规过滤，详见 §4.7，所有查询无条件附加）                                                                         |
| `projectName`          | 通过 `projectId` 反查 `project` 表得到 `projectName`，再过滤 scan_run；或入参透传                                                                               |
| `manifestBranch`       | `static_alarm_scan_run.branch` 精确匹配                                                                                                                         |
| `repoName`             | `static_alarm_scan_run.repo` 精确匹配                                                                                                                           |
| `startTime`            | `static_alarm_scan_run.createdAt >= startTime`（记录创建时间下界）                                                                                              |
| `endTime`              | `static_alarm_scan_run.updatedAt <= endTime`（记录更新时间上界）                                                                                                |
| `result`               | 后置过滤：先聚合 issue 得到 `issue_snapshot`（add-count-yym 分支将 `issue_count` 更名为 `issue_snapshot`），再按 `result` 过滤；或不在 SQL 层过滤，由应用层筛选 |
| `repoIds`              | 通过 `projectId` 反查 `repo_info` 得到 `repoId`，再过滤 scan_run                                                                                                |
| `pageNum` / `pageSize` | 仅当同时非空且 count > 0 时 skip/limit                                                                                                                          |
| 其他 DTO 字段          | 不进入 CodeQL 查询条件（与原接口口径一致）                                                                                                                      |

### 4.5 分页与排序

- **分页**：仅当 `pageNum != null && pageSize != null && count > 0` 时分页，否则全量（与原接口对齐）
- **排序**：CodeQL 路径显式按 `scan_start_at DESC`，避免入湖消费方拿到不稳定顺序
- 原华为云路径是否补排序属于另一个改进项，不在本次范围

### 4.6 度量数据关联规则

#### 4.6.1 问题背景

CodeQL 扫描与代码度量扫描是两条独立的扫描链路，执行时机不同：

- CodeQL 扫描结果写入 `static_alarm_scan_run`（含 `commit_id` / `scan_start_at` / `scan_end_at`）
- 代码度量扫描结果写入 `code_metrics_record`（含 `commit_id` / 独立的扫描时间字段）

两条扫描链路互不依赖，同一次 CodeQL 扫描与同一次度量扫描不共享 run id，无法直接 join。早期方案按 `repo_url + branch + 时序窗口` 关联，存在度量扫描时刻偏离 CodeQL 扫描导致指标失真的风险。改造后**按 `commit_id` 精确关联**：同一 commit 触发的 CodeQL 扫描与度量扫描天然对应同一份代码快照，无需时序窗口。

> 前置条件：插件端上报的 `commit_id` 已写入 `code_metrics_record.commit_id` 字段（由 coderepo `readMetaField` 解析 OBS JSON 中的 `commitId` 字段入库，详见 coderepo 仓 `saveCodeMetricsRecord` 实现）。`static_alarm_scan_run.commit_id` 字段已存在。

#### 4.6.2 关联键

按「代码仓地址 + 分支 + commit ID」三元组关联：

| CodeQL 侧字段                     | 度量侧字段                        | 关联语义                                       |
| --------------------------------- | --------------------------------- | ---------------------------------------------- |
| `static_alarm_scan_run.repo_url`  | `code_metrics_record.git_url`     | 代码仓地址                                     |
| `static_alarm_scan_run.branch`    | `code_metrics_record.branch_name` | 分支名                                         |
| `static_alarm_scan_run.commit_id` | `code_metrics_record.commit_id`   | 触发扫描的 commit ID（精确匹配，避免时序偏离） |

> 字段名以实际表结构为准（coderepo `code_metrics_record` 表分支字段为 `branch_name`，非 `branch`）。coderepo HTTP 接口入参命名见 §4.6.7。

> 三元组中任一为空（最常见为 `commit_id` 缺失）则该 scan_run 跳过度量关联，相关字段走 §4.6.4 默认值。

#### 4.6.3 commit_id 精确关联算法

**以 CodeQL `scan_run` 为主，按本页 scan_run 批量执行**：

1. 遍历本页 scan_run，收集非空的 `(repo_url, branch, commit_id)` 三元组（任一为空则该条跳过度量关联，相关字段走默认值）
2. 一次性调用 coderepo 批量接口 `CodeMetricsFeignClient.getLatestMetricsByCommitBatch(queries)`（详见 §4.6.7）：
   - 过滤条件：`status = 0 AND (git_url, branch_name, commit_id) IN (...)` 三元组精确匹配
   - coderepo 侧对每个三元组取 `detection_completed_at` 最大的一条（同一 commit 因扫描器重跑可能产生多条记录，取最新一条）
3. 命中 → 按 `groupKey(repoUrl, branch, commitId)` 建立内存索引，把该 `code_metrics_record.metrics_data_json` 用于对应 scan_run 的度量字段填充
4. 未命中（该三元组从未做过代码度量扫描，或度量记录全部失败）→ 度量字段走默认值（见 §4.6.4）

> `status = 0` 过滤掉失败度量记录。`commit_id` 精确匹配天然解决时序偏离问题，无需 `detection_completed_at < scan_start_at` 时序窗口。

#### 4.6.4 找不到度量记录时的默认值

| 字段类别                                                                                                                                                                                                     | 默认值                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| `codeLine` / `codeLineTotal` / `commentLines` / `complexityCount` / `cyclomaticComplexityPerMethod` / `cyclomaticComplexityPerFile` / `duplicatedBlocks` / `duplicatedLines` / `methodsTotal` / `filesTotal` | `0` 或 `null`（按字段类型；§4.3.2 已标） |
| `duplicationRatio` / `fileDuplicationRatio`                                                                                                                                                                  | `"0"` 字符串 或 `null`                   |
| `metricInfo`                                                                                                                                                                                                 | `null` 或空 JSON 字符串                  |
| `codeQuality` / `riskCoefficient`                                                                                                                                                                            | 固定值 `100`（不依赖度量，已有规则）     |

> 若度量字段尚未在 coderepo `metrics_data_json` 中上报，同样走默认值（与 §5.2 未就绪兜底一致）。

#### 4.6.5 性能考量

- 单条 scan_run 触发一次 Feign 调用，page_size 过大时 N+1 风险高
- **本次落地即支持批量入参**（§4.6.7 `/batch` 接口），coderepo 侧一次性按 `(git_url, branch_name, commit_id) IN (...)` 三元组精确关联，返回所有命中记录，由 codecheck 内存 join
- 批量 SQL 实现方式（用户确认项 5）：

  ```sql
  -- coderepo 批量查询（伪 SQL，实际由 MyBatis foreach 拼接）
  SELECT id, git_url, branch_name, pipeline_run_id, run_number, commit_id,
         metrics_data_json, detection_started_at, detection_completed_at,
         status, create_time
  FROM code_metrics_record
  WHERE status = 0
    AND (git_url, branch_name, commit_id) IN (
      (#{q1.gitUrl}, #{q1.branchName}, #{q1.commitId}),
      (#{q2.gitUrl}, #{q2.branchName}, #{q2.commitId}),
      ...
    )
  ORDER BY git_url, branch_name, detection_completed_at DESC
  ```

  coderepo Service 收到结果后按 `(gitUrl, branchName, commitId)` 分组，每组取 `detection_completed_at` 最大的一条返回；codecheck 侧直接按 `(gitUrl, branchName, commitId)` 索引取用。

- 若入湖消费方单次查询 page_size > 50，先与消费方对齐节奏

#### 4.6.6 与 `code_metrics_file_detail` 的关联

`filesTotal` / `methodsTotal` 等需要从 `code_metrics_file_detail` 聚合的字段：

- 取 §4.6.3 命中的 `code_metrics_record.id` 作为 `record_id`
- 在 `code_metrics_file_detail` 中按 `record_id` 聚合
- 若 §4.6.3 未命中，则 file_detail 不查，相关字段走默认值

> 注：当前 §4.3.1 已将 `filesTotal` / `methodsTotal` 列入不对接字段，故 file_detail 不在本次落地链路中。若后续恢复对接，按本节规则执行。

#### 4.6.7 coderepo HTTP 接口设计

接口挂载于 coderepo 现有**机机接口专用 Controller** `InternalProjectRepoController`（类级路径 `/project-repo/internal`，与 coderepo 现有 `CodeMetricsController` 前端接口隔离），本次仅新增批量接口。

**接口契约**：

| 路径                                                                  | 方法 | 入参                                  | 出参                                       | 用途                              |
| --------------------------------------------------------------------- | ---- | ------------------------------------- | ------------------------------------------ | --------------------------------- |
| `POST /project-repo/internal/metrics/code/latest-by-commit/batch`     | POST | `List<LatestMetricsByCommitQueryDTO>` | `DataResult<List<CodeMetricsSnapshotDTO>>` | 批量查询（codecheck 唯一调用入口） |

> 不提供单条接口：单条场景由调用方以 1 元素列表复用 batch 接口，避免维护两套契约。

**入参 DTO** `LatestMetricsByCommitQueryDTO`：

```java
@Data
public class LatestMetricsByCommitQueryDTO {
  /** 代码仓地址（对应 code_metrics_record.git_url） */
  @NotBlank private String gitUrl;

  /** 分支名（对应 code_metrics_record.branch_name） */
  @NotBlank private String branchName;

  /** commit ID（对应 code_metrics_record.commit_id，由插件端上报） */
  @NotBlank private String commitId;
}
```

**出参 DTO** `CodeMetricsSnapshotDTO`（返回 `metrics_data_json` 原文，由 codecheck 自行解析各字段）：

```java
@Data
public class CodeMetricsSnapshotDTO {
  private String gitUrl;
  private String branchName;
  private String pipelineRunId;
  private String runNumber;
  /** commit ID（对应 code_metrics_record.commit_id） */
  private String commitId;
  /** 指标数据 JSON 原文（codecheck 侧自行解析取 codeScale / avgCyclomaticComplexity 等） */
  private String metricsDataJson;
  private Date detectionStartedAt;
  private Date detectionCompletedAt;
}
```

> codecheck 侧在 `business/entity/dto/metrics/` 下持有同名入参 / 出参 DTO，作为 Feign 契约副本；coderepo 侧为唯一权威定义。

**Service 方法**：

```java
public interface CodeMetricsService {
  // 新增
  List<CodeMetricsSnapshotDTO> getLatestMetricsByCommitBatch(List<LatestMetricsByCommitQueryDTO> queries);
}
```

**Mapper 方法**：

```java
public interface CodeMetricsRecordMapper {
  // 新增批量
  List<CodeMetricsRecordEntity> selectLatestByCommitBatch(
      @Param("queries") List<LatestMetricsByCommitQueryDTO> queries);
}
```

**批量 SQL**：

```sql
SELECT id, git_url, branch_name, pipeline_run_id, run_number, commit_id,
       metrics_data_json, detection_started_at, detection_completed_at,
       status, error_message, create_time
FROM code_metrics_record
WHERE status = 0
  AND (git_url, branch_name, commit_id) IN (
    <foreach collection="queries" item="q" separator=",">
      (#{q.gitUrl}, #{q.branchName}, #{q.commitId})
    </foreach>
  )
ORDER BY git_url, branch_name, detection_completed_at DESC
```

> 批量接口返回结果中，对每个 `(gitUrl, branchName, commitId)` 只取 `detection_completed_at` 最大的一条；codecheck 侧按 `(gitUrl, branchName, commitId)` 索引取用。

**索引**：表创建时已有的 `idx_git_url_branch (git_url, branch_name)` 联合索引可支撑批量 SQL 的前缀过滤；`(git_url, branch_name, commit_id)` 全量联合索引留待性能验证后评估（见 proposal 遗留项）。

### 4.7 法律合规过滤：排除 CodeQL 来源数据

#### 4.7.1 背景与约束

CodeQL 插件存在潜在法律风险，降级路径不得消费任何 CodeQL 来源的扫描数据。`static_alarm_scan_run` 表通过 `tool` 字段标识扫描工具（`CodeQL` / `SpotBugs` / `checkstyle` / `ESLint` / `golangci-lint` 等），降级路径需在查询时强制排除 `tool = 'CodeQL'` 的记录。

#### 4.7.2 过滤实现

在 `StaticAlarmSummaryOperation#buildCriteriaFromQuery` 的 `Criteria` 链首部无条件附加：

```java
criteria.and("tool").ne("CodeQL");
```

**语义**：

- 排除 `tool` 字段值为 `"CodeQL"` 的所有 scan_run 记录
- `tool` 字段缺失（null / missing）的记录视为非 CodeQL，予以保留（MongoDB `ne` 对缺失字段返回 true）
- 该过滤为**固定条件**，不暴露给入参，所有降级查询无条件生效

#### 4.7.3 影响范围

- **scan_run 层**：count + find 均附加 `tool != "CodeQL"`，CodeQL 扫描记录不参与分页
- **issue 层**：issue 通过 `pipeline_run_id` 关联 scan_run，scan_run 已过滤后，聚合 issue 时传入的 `pipeline_run_id` 列表天然不含 CodeQL 扫描的 id，故 issue 层无需重复过滤
- **度量层**：度量关联键为 `git_url + branch_name + commit_id`，与 tool 无关；CodeQL scan_run 被过滤后不会发起度量查询
- **结果口径**：降级路径返回的是「非 CodeQL 静态扫描工具」的检查结果聚合，字段映射规则不变

## 5. 跨仓改动清单

### 5.1 openlibing-codecheck 仓

| #   | 改动类型             | 改动内容                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | 影响字段                                      |
| --- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 1   | MongoDB 集合新增字段 | `static_alarm_scan_run` 新增 8 个快照字段（含 1 个标志位）：`issue_snapshot`（原 `issue_count` 更名）/ `solve_snapshot` / `ignore_snapshot` / `critical_count_snapshot` / `major_count_snapshot` / `minor_count_snapshot` / `suggestion_count_snapshot` / `snapshot_computed`（Boolean 标志位，标志前 7 个快照字段是否计算成功）。前 7 个快照字段由 `SarifParseServiceImpl` 在解析成功后调用 `StaticAlarmOperation.aggregateSnapshot` 聚合 issue 表写入；`snapshot_computed=false` 时前 7 个字段为 null，降级路径回退 issue 表实时聚合 | #29 / #32 / #33 / #34 / #35 / #36 / #37 / #38 |

> 注：`add-count-yym` 分支已将 `issue_count` 更名为 `issue_snapshot`，同时移除 `new_issue_count` / `resolved_issue_count` 两个老字段。#33 `newCount` 字段语义降级为复用 `issue_snapshot`（原 `new_issue_count` 字段已不存在）。

### 5.2 openlibing-coderepo 仓

| #   | 改动类型            | 改动内容                                                                                                                                                                                                                                                                                                                                                                       | 影响字段                          | 未就绪兜底        |
| --- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------- | ----------------- |
| 2   | 插件 + Service 上报 | `metrics_data_json` 新增「总行数」字段（暂命名 `codeLineTotal`）                                                                                                                                                                                                                                                                                                               | #40 `codeLineTotal`               | 置 null 或 0      |
| 3   | 插件 + Service 上报 | `metrics_data_json` 新增 `commentLines` 字段                                                                                                                                                                                                                                                                                                                                   | #42 `commentLines`                | 置 0              |
| 4   | 插件 + Service 上报 | `metrics_data_json` 新增 `complexityCount` 字段                                                                                                                                                                                                                                                                                                                                | #44 `complexityCount`             | 置 0              |
| 5   | 插件 + Service 上报 | `metrics_data_json` 新增 `cyclomaticComplexityPerFile` 字段                                                                                                                                                                                                                                                                                                                    | #46 `cyclomaticComplexityPerFile` | 置 null           |
| 6   | 插件 + Service 上报 | `metrics_data_json` 新增 `duplicatedBlocks` 字段                                                                                                                                                                                                                                                                                                                               | #47 `duplicatedBlocks`            | 置 0              |
| 7   | 插件 + Service 上报 | `metrics_data_json` 新增 `duplicatedLines` 字段                                                                                                                                                                                                                                                                                                                                | #48 `duplicatedLines`             | 置 0              |
| 8   | HTTP 接口新增       | coderepo 现有机机接口专用 `InternalProjectRepoController`（类级路径 `/project-repo/internal`）新增 `POST /project-repo/internal/metrics/code/latest-by-commit/batch` 接口；按 `git_url + branch_name + commit_id` 三元组精确匹配 + `status=0` 关联，每个三元组取 `detection_completed_at` 最新一条，返回 `CodeMetricsSnapshotDTO`（含 `metrics_data_json` 原文）；供 codecheck 通过 Feign 调用。详细设计见 §4.6.7 | 所有度量字段                      | 字段全部置 null/0 |

### 5.3 PR 矩阵

- **codecheck 业务 PR**（openlibing-codecheck#327）：实现 `StaticAlarmSummaryOperation` + 修改 `CheckboardDelegateImpl` + 新增 `CodeMetricsFeignClient`；scan_run 的 8 个快照字段由 `add-count-yym` 分支（fast-forward 合并到本分支）落地，本分支仅消费
- **coderepo 业务 PR**（openlibing-coderepo#159）：`code_metrics_record` 新增 `commit_id` 字段 + 暴露 `/project-repo/internal/metrics/code/latest-by-commit/batch` 机机接口
- **code-metrics-scan 插件 PR**：`metrics_data_json` 新增 6 个字段的上报 + `commitId` 上报（`ATOMGIT_SHA`）
- **docs PR**（openlibing-docs#889）：归档 spec 三件套

跨仓改动按 §5.1 / §5.2 顺序推进：coderepo 字段就绪 → codecheck Feign 调通 → codecheck 降级路径落地。

## 6. 异常处理

### 6.1 降级路径异常

静态告警降级路径内部异常不应影响接口可用性：

```java
try {
  pageVoStaticAlarm = staticAlarmSummaryOperation.queryStaticAlarmSummaryList(query);
} catch (Exception e) {
  logger.error("Static-alarm fallback failed, query={}, falling back to empty result", query, e);
  // 不抛出，返回原 pageVoHw（空）
}
```

### 6.2 边界场景

| 场景                                                           | 处理                                                   |
| -------------------------------------------------------------- | ------------------------------------------------------ |
| task_result_summary 命中 + CodeQL 也有数据                     | 走原路径，CodeQL 不查                                  |
| task_result_summary total==0 + 无仓库定位字段                  | 不降级，直接返回空                                     |
| task_result_summary total==0 + 有定位字段 + CodeQL 也空        | 返回空 PageVo                                          |
| task_result_summary total==0 + 有定位字段 + CodeQL 异常        | 返回空 PageVo，记错误日志                              |
| 分页越界（CodeQL count > 0 但 skip 超出）                      | 返回空 list，total 仍为 count（与原接口行为一致）      |
| coderepo Feign 调用失败                                        | 度量字段全部走兜底值（null/0），不抛异常，记 warn 日志 |
| scan_run 快照字段未就绪（`snapshot_computed=false` 或为 null） | 计数字段回退到 issue 表聚合                            |
| coderepo `metrics_data_json` 字段未就绪                        | 度量字段走兜底值（见 §5.2）                            |

## 7. 影响范围

### 7.1 改动文件

#### openlibing-codecheck 仓

| 文件                                   | 改动类型                                              | 说明                                                                                                                                   |
| -------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `CheckboardDelegateImpl.java`          | 修改                                                  | `queryFullTaskResultSummary` 增加降级逻辑                                                                                              |
| `StaticAlarmSummaryOperation.java`     | 新增                                                  | 静态告警多表关联查询与 DTO 组装                                                                                                        |
| `CodeMetricsFeignClient.java`          | 新增                                                  | Feign 调用 coderepo HTTP 接口                                                                                                          |
| `StaticAlarmScanRunEntity.java`        | 修改（由 `add-count-yym` 分支 fast-forward 合并带入） | 新增 8 个快照字段（7 个计数 + `snapshot_computed` 标志位），移除 `issue_count` / `new_issue_count` / `resolved_issue_count` 3 个老字段 |
| `CheckboardDelegateImplTest.java`      | 修改                                                  | 补充降级路径用例                                                                                                                       |
| `StaticAlarmSummaryOperationTest.java` | 新增                                                  | 静态告警 Operation 单元测试                                                                                                            |

#### openlibing-coderepo 仓

| 文件                                          | 改动类型 | 说明                                                                        |
| --------------------------------------------- | -------- | --------------------------------------------------------------------------- |
| `InternalProjectRepoController.java`          | 修改     | 新增机机接口 `POST /metrics/code/latest-by-commit/batch`                    |
| `CodeMetricsService.java` / `Impl`            | 修改     | 新增 `getLatestMetricsByCommitBatch` 批量查询方法                           |
| `CodeMetricsRecordMapper.java` / `.xml`       | 修改     | 新增 `selectLatestByCommitBatch` 三元组 IN 批量 SQL                         |
| `LatestMetricsByCommitQueryDTO.java`          | 新增     | HTTP 接口入参 DTO（gitUrl / branchName / commitId）                         |
| `CodeMetricsSnapshotDTO.java`                 | 新增     | HTTP 接口出参 DTO（含 `metricsDataJson` 原文）                              |
| `CodeMetricsRecordEntity.java` + Liquibase    | 修改     | `code_metrics_record` 新增 `commit_id` 字段                                 |
| `CodeMetricsServiceImplTest.java`             | 修改     | 补充批量查询用例（同一 commit 重跑取最新 / 无命中返回空 / 混合查询各自正确） |
| 插件上报逻辑（code-metrics-scan）             | 修改     | `metrics_data_json` 新增 6 个字段上报 + `commitId` 上报                     |

#### openlibing-docs 仓

| 文件                                                                                                     | 改动类型 | 说明           |
| -------------------------------------------------------------------------------------------------------- | -------- | -------------- |
| `spec/openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback/{proposal,design,tasks}.md` | 新增     | 本 spec 三件套 |

### 7.2 不改动

- `MachineApiCheckboardController`：接口契约不变
- `QueryTaskSummaryMachineApiModel`：入参不变
- `FullSummaryOperation`：原华为云路径行为不变
- `/codecheck/full/task/result/summary` 等同类接口：独立链路，不做降级
- `task_result_summary` 写入路径：不动

## 8. 测试策略

### 8.1 单元测试

| 用例                                                           | 期望                                                |
| -------------------------------------------------------------- | --------------------------------------------------- |
| task_result_summary 命中                                       | 走原路径，CodeQL Operation 不被调用，返回华为云数据 |
| task_result_summary 空 + 有定位字段 + CodeQL 命中              | 走降级路径，返回 CodeQL 组装结果                    |
| task_result_summary 空 + 无定位字段                            | 不降级，返回空 PageVo                               |
| 两边都空                                                       | 返回空 PageVo                                       |
| CodeQL 异常                                                    | 返回空 PageVo，记错误日志，不抛异常                 |
| 降级带分页                                                     | 分页参数生效                                        |
| 降级无分页                                                     | 全量返回                                            |
| CodeQL 多 scan_run 聚合                                        | issue 计数正确                                      |
| scan_run 快照字段未就绪（`snapshot_computed=false` 或为 null） | 计数字段回退到 issue 表聚合                         |
| coderepo Feign 调用失败                                        | 度量字段走兜底值，不抛异常                          |
| coderepo `metrics_data_json` 字段未就绪                        | 度量字段走兜底值                                    |

### 8.2 集成测试

构造真实 scan_run + issue + code_metrics_record 数据，验证端到端组装正确性。

## 9. 关键设计决策

1. **降级独立 Operation**：不复用 `FullSummaryOperation`，避免污染原链路
2. **降级触发要求仓库定位字段**：避免无条件空查询触发全表扫描，与入湖消费方典型场景对齐
3. **异常隔离**：降级路径异常不抛出，返回空结果；跨仓调用失败走默认值
4. **结构等价**：降级路径返回 `CodeCheckResultSummaryDTO`，与原接口出参结构一致
5. **显式排序**：CodeQL 路径按 `scan_start_at DESC`
6. **分页语义对齐**：与原接口「同时非空才分页」语义保持一致
7. **跨仓协同改造**：codecheck + coderepo 同步 PR，`metrics_data_json` 字段就绪前 codecheck 走默认值
8. **不对接字段显式声明**：12 个字段不对接（见 §4.3.1），降级路径不返回或置 null
9. **度量数据 commit 精确关联**：以 CodeQL `scan_run` 为主，按 `git_url + branch_name + commit_id` 三元组精确匹配（见 §4.6），废弃早期「`repo_url + branch` + 取 `scan_start_at` 之前最近一次度量记录」的时序窗口方案；同一 commit 重跑取 `detection_completed_at` 最新一条，找不到走默认值，彻底避免度量扫描时刻偏离导致指标失真
10. **批量 Feign 调用落地**：`/latest-by-commit/batch` 接口本次已实现（§4.6.5），一次性三元组 IN 关联避免 codecheck 侧 N+1 Feign 调用

## 10. 后续演进

| 项                                                                | 时机                                        |
| ----------------------------------------------------------------- | ------------------------------------------- |
| 落地 §5 跨仓改动清单中的字段新增                                  | 进入 tasks.md 拆分后                        |
| 考虑原华为云路径补显式排序                                        | 另一个改进项                                |
| 考虑同类接口 `/codecheck/full/task/result/summary` 是否也需要降级 | 视入湖消费方需求                            |
| `result` 字段在 CodeQL 路径的过滤实现（§4.4）                     | 已定口径：查询层不做 result 过滤，`DTO.result` 由 `issue_snapshot` 推导；消费方需按 result 过滤时另行评估 |
| 度量关联 Feign 批量接口的性能优化（§4.6.5）                       | 入湖消费方 page_size 增大或接口 RT 不达标时 |
| 度量关联缓存（同 repo+branch+commitId 三元组多次查询可复用）      | 接口 RT 不达标时                            |
