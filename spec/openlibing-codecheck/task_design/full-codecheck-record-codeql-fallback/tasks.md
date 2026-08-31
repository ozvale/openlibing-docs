# /full-codecheck-record/list 接入 CodeQL 降级查询 - 实现任务

> 状态：草稿。CodeQL 数据口径相关任务（标 ⏳ 的部分）待补充。

## Phase 1：上下文与设计（已完成）

- [x] 分析 `/full-codecheck-record/list` 接口现状
- [x] 分析 `task_result_summary` 入库场景
- [x] 分析 CodeQL 数据链路（`static_alarm_scan_run` / `static_alarm_issue`）
- [x] 确认流程模式：Standard
- [x] 确认降级触发条件：要求至少一个仓库定位字段非空
- [x] 落盘 spec 草稿（proposal.md + design.md + tasks.md）

## Phase 2：CodeQL 数据口径补充（待用户补充）

- [ ] ⏳ 补充 CodeQL 数据表清单与关联关系到 design.md §4.3
- [ ] ⏳ 补充各 DTO 字段在 CodeQL 表的取数口径到 design.md §4.3
- [ ] ⏳ 补充 `repoId / projectName / obProjectId` 在 CodeQL 侧的获取方式
- [ ] ⏳ 确认 CodeQL 是否有「已失效/审核中」状态对齐
- [ ] ⏳ 确认是否需要来源标识字段（如 `type="codeql"`）
- [ ] ⏳ 补充过滤条件翻译细则到 design.md §4.4

## Phase 3：编码实现

### 3.1 准备工作

- [ ] 在 openlibing-codecheck 仓基于 origin/master 新建分支 `feat-full-codecheck-record-codeql-fallback`
- [ ] 确认当前 develop_202608_iter2 分支上的 MongoConfig/RedisConfig 改动已处理（提交或 stash）

### 3.2 新增 CodeQlSummaryOperation

- [ ] 新增 `CodeQlSummaryOperation.java`
  - [ ] 实现 `queryCodeQlSummaryList(QuerySummaryModel query): PageVo` 主入口
  - [ ] 实现 `buildCriteriaFromQuery(query): Criteria` 条件翻译
  - [ ] 实现 `countScanRun(criteria): long`
  - [ ] 实现 `pageScanRun(criteria, query): List<StaticAlarmScanRunEntity>`
  - [ ] 实现 `batchAggregateIssues(scanRunIds): Map<scanRunId, IssueStats>`
  - [ ] 实现 `toDto(scanRun, issueStats): CodeCheckResultSummaryDTO` 单条转换
  - [ ] 显式排序：`scanStartAt DESC`
  - [ ] 分页语义：同时非空才分页
  - [ ] 异常处理：内部异常向上抛（由 Delegate 层兜底）

### 3.3 修改 CheckboardDelegateImpl

- [ ] 修改 `queryFullTaskResultSummary(QuerySummaryModel query)`
  - [ ] 调用原 `fullSummaryOperation.queryFullSummaryList(query)`
  - [ ] 实现 `shouldFallbackToCodeQl(pageVo, query)` 判定
  - [ ] 实现 `hasRepoLocator(query)` 检查
  - [ ] 降级路径调用 `codeQlSummaryOperation.queryCodeQlSummaryList(query)`
  - [ ] 异常隔离：try-catch CodeQL 异常，记错误日志，回退空结果

### 3.4 测试

- [ ] 新增 `CodeQlSummaryOperationTest.java`
  - [ ] 用例：条件翻译正确性
  - [ ] 用例：scan_run 聚合正确性
  - [ ] 用例：issue 统计回填正确性
  - [ ] 用例：分页参数生效
  - [ ] 用例：异常路径
- [ ] 修改 `CheckboardDelegateImplTest.java`
  - [ ] 用例：task_result_summary 命中 → 不降级
  - [ ] 用例：task_result_summary 空 + 有定位字段 → 降级
  - [ ] 用例：task_result_summary 空 + 无定位字段 → 不降级
  - [ ] 用例：两边都空 → 返回空
  - [ ] 用例：CodeQL 异常 → 返回空 + 记日志
  - [ ] 用例：降级路径分页生效

### 3.5 自检与交付

- [ ] 编译通过
- [ ] 单元测试通过
- [ ] 提交单轮 commit（遵循 commit 规范：`feat(codecheck): add codeql fallback ...`）
- [ ] 向用户交付，进入用户自测/反馈循环

## Phase 4：业务 PR

- [ ] 用户自测确认完成
- [ ] 通过 `gitcode pr create` 创建业务 PR
- [ ] 补打 `ai-assisted` 标签：`gitcode pr edit <n> -R openlibing/openlibing-codecheck --labels ai-assisted`
- [ ] 关联业务 Issue

## Phase 5：归档

- [ ] 用户触发归档
- [ ] 补充 archive.md
- [ ] 通过 docs PR 提交归档到 openlibing-docs 仓主干
- [ ] docs PR 补打 `ai-assisted` 标签
- [ ] 确认业务 Issue 状态正确
