# /full-codecheck-record/list 接入静态告警降级查询 - 需求提案

## 1. 背景

### 1.1 现状

机机接口 `POST /machine-api/v1/full-codecheck-record/list` 当前只查询 MongoDB 集合 `task_result_summary`，该集合由华为云 CodeCheck 全量检查任务完成后通过 RabbitMQ 事件驱动入库（`SaveFullTaskResult.createDailyCheckSyncTask` → `FullSummaryOperation.saveInfo`）。

接口定位为「task_result_summary 表入湖接口」：外部数据湖服务通过该接口拉取 codecheck 摘要数据入库。

### 1.2 问题

并非所有项目下的代码仓分支都接入了华为云 CodeCheck。当某项目/仓库/分支未接入华为云 CodeCheck 时，`task_result_summary` 中无对应记录，接口返回空结果，入湖消费方拿不到该仓库的任何 codecheck 数据。

实际上这些仓库可能已经接入了 CodeQL（通过 SARIF 上报链路入库到 `static_alarm_scan_run` / `static_alarm_issue` 表，详见 `static-alarm` spec），但当前接口不会查询这部分数据。

### 1.3 需求

调整 `/full-codecheck-record/list` 接口行为：当 `task_result_summary` 查询不到数据时，降级到 CodeQL 数据源（多表关联查询）组装出结构等价的结果返回。

## 2. 验收标准

### 2.1 功能验收

| 编号 | 验收点                                                  | 期望                                                                                                         |
| ---- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| AC-1 | `task_result_summary` 命中                              | 走原查询路径，返回华为云 summary 数据；CodeQL 降级路径不被触发                                               |
| AC-2 | `task_result_summary` total==0 且指定了仓库定位字段     | 降级到 CodeQL，返回由 `static_alarm_scan_run` + `static_alarm_issue` 组装出的等价结构数据                    |
| AC-3 | `task_result_summary` total==0 且未指定任何仓库定位字段 | 不降级，直接返回空结果，避免无条件全量查询触发 CodeQL 扫表                                                   |
| AC-4 | 两边都查不到                                            | 返回空 PageVo，不抛异常                                                                                      |
| AC-5 | 降级路径支持分页                                        | `pageNum` + `pageSize` 同时非空时分页，否则全量（与原接口分页语义对齐）                                      |
| AC-6 | 降级路径返回结构                                        | 与原接口 `CodeCheckResultSummaryDTO` 字段结构一致，入湖消费方无需改代码                                      |
| AC-7 | 原华为云路径行为不变                                    | `FullSummaryOperation.queryFullSummaryList` 不修改，`/codecheck/full/task/result/summary` 等同类接口不受影响 |

### 2.2 非功能验收

| 编号  | 验收点       | 期望                                                                            |
| ----- | ------------ | ------------------------------------------------------------------------------- |
| NFR-1 | 接口契约不变 | 路径、HTTP 方法、入参 DTO、出参结构均不变                                       |
| NFR-2 | 异常隔离     | CodeQL 降级路径内部异常不应影响接口可用性，异常时回退到返回空结果并记录错误日志 |
| NFR-3 | 可观测       | 降级触发、CodeQL 查询耗时、降级路径异常均有日志，便于排查入湖消费方问题         |

## 3. 范围

### 3.1 In Scope

- **openlibing-codecheck 仓**：
  - 修改 `CheckboardDelegateImpl#queryFullTaskResultSummary`：增加降级逻辑
  - 新增 `StaticAlarmSummaryOperation`：静态告警多表关联查询与 DTO 组装（含 `queryStaticAlarmSummaryList` 主入口、`buildCriteriaFromQuery` 条件翻译、`batchAggregateIssues` 聚合、`enrichRepoAndProjectInfo` / `enrichCodeMetrics` 批量反查与度量关联、`toDto` 组装）
  - 新增 `CodeMetricsFeignClient`：Feign 调用 coderepo 机机接口 `/project-repo/internal/metrics/code/latest-by-commit/batch`
  - 修改 `StaticAlarmScanRunEntity`：新增 8 个快照字段（7 个计数快照 + `snapshot_computed` 标志位）：`issue_snapshot`（由 `issue_count` 更名）/ `solve_snapshot` / `ignore_snapshot` / `critical_count_snapshot` / `major_count_snapshot` / `minor_count_snapshot` / `suggestion_count_snapshot` / `snapshot_computed`；同时移除 `new_issue_count` / `resolved_issue_count` 等老字段
  - 测试：补充 `CheckboardDelegateImplTest` 降级路径用例 + 新增 `StaticAlarmSummaryOperationTest`
- **openlibing-coderepo 仓**：
  - 修改 `InternalProjectRepoController`：新增机机接口 `POST /project-repo/internal/metrics/code/latest-by-commit/batch`，按 `git_url + branch_name + commit_id` 三元组精确关联（`status=0`，同一 commit 重跑取 `detection_completed_at` 最新一条），支持批量入参
  - 修改 `CodeMetricsService` / `Impl`：新增 `getLatestMetricsByCommitBatch(List<LatestMetricsByCommitQueryDTO>)` 批量查询方法
  - 修改 `CodeMetricsRecordEntity` + Liquibase：`code_metrics_record` 新增 `commit_id` 字段
  - 修改插件上报逻辑：`metrics_data_json` 新增 6 个字段（`codeLineTotal` / `commentLines` / `complexityCount` / `cyclomaticComplexityPerFile` / `duplicatedBlocks` / `duplicatedLines`）+ `commitId` 上报
  - 测试：`CodeMetricsServiceImplTest` 补充批量查询用例

### 3.2 Out of Scope

- `/codecheck/full/task/result/summary` 等其他机机接口不做降级（独立链路）
- `task_result_summary` 写入路径不修改
- 原 `FullSummaryOperation.queryFullSummaryList` 内部行为不修改
- 不引入新的外部依赖（Feign 除外，若已存在则复用）

## 4. 字段映射与遗留项

### 4.1 字段映射方案

字段映射最终方案见 `design.md` §4.3。摘要：

- **不对接字段（12 个）**：`inReviewCount` / `invalidCount` / `commentRatio` / `fileDuplicationTotal` / `filesTotal` / `methodLines` / `methodsTotal` / `unsafeFunctionsCount` / `nonHeaderFileDuplicationRate` / `mrId` / `prId` / `mrUrl`
- **对接字段（50 个）**：见 `design.md` §4.3.2 字段映射表

### 4.2 遗留项

| 编号 | 遗留项                                                                                                                                  | 时机           |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| L-1  | ~~`result` 字段在 CodeQL 路径的过滤实现~~ 已定口径：查询层不做 result 过滤，`DTO.result` 由 `issue_snapshot` 推导（见 design.md §10）   | 已完成         |
| L-2  | ~~coderepo `metrics_data_json` 6 个新增字段的具体字段名~~ 已随 coderepo PR（openlibing-coderepo#159）落地，字段名与 design.md §5.2 一致 | 已完成         |
| L-3  | 12 个不对接字段的消费方兼容性确认（入湖消费方是否接受 DTO 字段缺失或 null）                                                             | 业务对接时确认 |
| L-4  | codecheck 降级路径的单元测试（`StaticAlarmSummaryOperationTest` / `CheckboardDelegateImplTest` 降级用例）尚未落地                       | 后续迭代补充   |

## 5. 关联

- 关联代码仓：`openlibing/openlibing-codecheck`
- 关联 Issue：openlibing/openlibing-codecheck#178
- 关联业务 PR：openlibing/openlibing-codecheck#327
- 关联 spec：`spec/openlibing-codecheck/task_design/static-alarm/`（CodeQL SARIF 解析链路与表结构来源）
- 关联 spec：`spec/openlibing-codecheck/task_design/machine-api-summary-dto/`（机机接口 DTO 拆分历史）
