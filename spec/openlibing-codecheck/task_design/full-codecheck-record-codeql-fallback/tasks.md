# /full-codecheck-record/list 接入静态告警降级查询 - 实现任务

> 状态：最终版。数据口径已全部落定（见 design.md），实现已随业务 PR openlibing/openlibing-codecheck#327 交付。

## Phase 1：上下文与设计（已完成）

- [x] 分析 `/full-codecheck-record/list` 接口现状
- [x] 分析 `task_result_summary` 入库场景
- [x] 分析静态告警数据链路（`static_alarm_scan_run` / `static_alarm_issue`）
- [x] 确认流程模式：Standard
- [x] 确认降级触发条件：要求至少一个仓库定位字段非空
- [x] 落盘 spec（proposal.md + design.md + tasks.md）

## Phase 2：数据口径确认（已完成，结论已落入 design.md）

- [x] 补充静态告警数据表清单与关联关系到 design.md §4.3（含度量关联 commit 三元组方案 §4.6）
- [x] 补充各 DTO 字段在静态告警表的取数口径到 design.md §4.3.2（50 字段映射表）
- [x] 确认 `repoId / projectName / obProjectId` 获取方式：`repo_info` / `project_info` / `hw_project_info` 批量反查 + 入参 `projectId` 透传（design.md §4.1 `enrichRepoAndProjectInfo`）
- [x] 确认状态对齐：`mapScanRunStatus` 映射 `SUCCESS→success / FAILED→failed / PARSING→processing`，`inReview` / `invalid` 固定 0（无需审批）
- [x] 确认来源标识：不新增字段，`checkType="source"` / `type="new"` 固定值（design.md §4.3.2 #17 / #20）
- [x] 补充过滤条件翻译细则到 design.md §4.4（含 `tool != "CodeQL"` 法律合规固定过滤 §4.7）

## Phase 3：编码实现（已完成，随 PR openlibing-codecheck#327 交付）

### 3.1 准备工作

- [x] 在 openlibing-codecheck 仓基于 origin/master 新建分支 `feat-full-codecheck-record-codeql-fallback`
- [x] 合入 `add-count-yym` 分支（scan_run 8 个快照字段落地，本分支仅消费）

### 3.2 新增 StaticAlarmSummaryOperation

- [x] 新增 `StaticAlarmSummaryOperation.java`
  - [x] 实现 `queryStaticAlarmSummaryList(QuerySummaryModel query): PageVo` 主入口（count + 分页内联）
  - [x] 实现 `buildCriteriaFromQuery(query): Criteria` 条件翻译（含 `tool != "CodeQL"` 固定过滤）
  - [x] 实现 `batchAggregateIssues(scanRuns): Map<pipelineRunId, IssueStats>` 聚合（issue 表外键为 `pipeline_run_id`，快照未就绪才聚合，`needIssueAggregationFallback` 判定）
  - [x] 实现 `enrichRepoAndProjectInfo(scanRuns)`：批量反查 `repo_info` / `project_info` / `hw_project_info`，内存 Map 关联（避免 N+1）
  - [x] 实现 `enrichCodeMetrics(scanRuns)`：收集 `(repo_url, branch, commit_id)` 三元组，按 ≤100 条/批切分（与 coderepo 入参上限对齐）Feign 分批调用 coderepo，单批失败局部降级（该批走默认值），内存按 `groupKey` 合并关联
  - [x] 实现 `toDto(scanRun, issueStats, metrics): CodeCheckResultSummaryDTO` 单条转换（含 `resolveXxxCount` 快照优先/聚合兜底、`applyMetrics` 度量填充）
  - [x] 显式排序：`scanStartAt DESC`
  - [x] 分页语义：同时非空才分页
  - [x] 异常处理：内部异常向上抛（由 Delegate 层兜底）

### 3.3 修改 CheckboardDelegateImpl

- [x] 修改 `queryFullTaskResultSummary(QuerySummaryModel query)`
  - [x] 调用原 `fullSummaryOperation.queryFullSummaryList(query)`
  - [x] 实现 `shouldFallbackToStaticAlarm(pageVo, query)` 判定
  - [x] 实现 `hasRepoLocator(query)` 检查
  - [x] 降级路径调用 `staticAlarmSummaryOperation.queryStaticAlarmSummaryList(query)`
  - [x] 异常隔离：try-catch 降级路径异常，记错误日志，回退空结果

### 3.4 新增 Feign client 与 DTO

- [x] 新增 `CodeMetricsFeignClient`：`POST /project-repo/internal/metrics/code/latest-by-commit/batch`
- [x] 新增 `LatestMetricsByCommitQueryDTO` / `CodeMetricsSnapshotDTO`（Feign 契约副本，coderepo 侧为权威定义）

### 3.5 自检与交付

- [x] 编译通过
- [x] 全量单元测试通过（PR 流水线验证，含 `ProblemshieldDelegateInReviewNegativeTest` 偶发 UnnecessaryStubbing 修复）
- [x] 提交单轮 commit（遵循 commit 规范）
- [x] 向用户交付，进入用户自测/反馈循环

## Phase 4：业务 PR（已完成）

- [x] 用户自测确认完成
- [x] 创建业务 PR：openlibing/openlibing-codecheck#327（`feat-full-codecheck-record-codeql-fallback` → `release_20260831_iter2`）
- [x] 补打 `ai-assisted` 标签
- [x] 关联业务 Issue：openlibing/openlibing-codecheck#178

## 测试覆盖情况

- [x] coderepo 侧：`CodeMetricsServiceImplTest` 补充 3 个批量查询用例（同一 commit 重跑取 `detection_completed_at` 最新 / 无命中返回空列表 + 空入参短路 / 多仓库多分支多 commit 混合查询各自正确）
- [ ] codecheck 侧：`StaticAlarmSummaryOperationTest` / `CheckboardDelegateImplTest` 降级路径用例（遗留项 proposal L-4，后续迭代补充）

## Phase 5：归档（进行中）

- [x] 通过 docs PR 提交 spec 到 openlibing-docs 仓主干（openlibing-docs#889，含本次检视修订）
- [x] docs PR 补打 `ai-assisted` 标签
- [ ] 用户确认业务 PR 合入后补充 archive.md、确认业务 Issue 状态
