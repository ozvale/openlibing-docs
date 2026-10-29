# static-alarm-close-reason-filter — 实现任务

## 进度: 0/53 complete

## 阶段 1：数据模型与索引（不切查询代码，可独立上线）

### 后端实体与枚举

- [ ] Task 1: 新增 `StaticAlarmListStateEnum` 枚举类，定义 7 个取值（OPEN / PENDING_REVIEW / IGNORED_FALSE_POSITIVE / IGNORED_TEST_USAGE / IGNORED_WONT_FIX / RESOLVED_AUTO / SUPPRESSED_BY_COMMENT），实现 `resolveListStatesByTab(tab)` 和 `resolveListStateByShieldType(shieldType)` 方法
- [ ] Task 2: `StaticAlarmIssueEntity` 新增 `list_state` 字段（@Field("list_state")），保留 status 字段不删除
- [ ] Task 3: 新增 `StaticAlarmListStateEnumTest` 单测，覆盖 tab 映射、shieldType 映射、兜底逻辑

### Liquibase changelog（幂等设计）

- [ ] Task 4: 在 `static_alarm_index_governance.xml` 新增 5 个 changeSet 创建索引：idx_issue_repo_key_state_first_seen / state_updated_at / state_severity / state_last_seen / repo_key_rule（使用 createIndexes 命令，background=true）
- [ ] Task 5: 在 `static_alarm_index_governance.xml` 新增 10 个 changeSet 下线旧索引：idx_issue_list / idx_issue_rule / idx_issue_list_first_seen / idx_issue_sort_last_seen / idx_issue_sort_updated_at / idx_issue_sort_severity / idx_issue_repo_key_status_sort_last_seen / idx_issue_repo_key_sort_severity / idx_issue_repo_key_sort_updated_at / idx_issue_repo_key_sort_first_seen（使用 dropIndexes 命令 + indexExists preCondition 保证幂等）
- [ ] Task 6: 新增 changeSet 执行历史数据回填脚本（aggregation pipeline 从 revisions 反推 list_state，updateOne 逐条更新）
- [ ] Task 7: 验证 Liquibase changeSet 在 beta 环境执行成功，索引数从 12 变为 7，回填后 list_state 字段覆盖所有存量记录

### 阶段 1 验证

- [ ] Task 8: 编译通过（mvn compile）
- [ ] Task 9: `StaticAlarmListStateEnumTest` 单测全部通过
- [ ] Task 10: beta 环境跑生产量级数据验证索引切换，典型查询 explain 命中新索引，无独立 SORT stage
- [ ] Task 10b: **回填验证门槛（阶段 3 查询代码切换的强制前置）**：回填脚本执行完成后，跑 `count({list_state: {$exists: false}})` 或 `count({list_state: null})`，**必须为 0**（或定位到能接受的极少量兜底记录）。未通过则不允许执行阶段 3 的查询代码切换。风险：如果回填未跑完就切查询代码，list_state 为空的历史记录不匹配任何 tab 的 list_state $in 条件，等于告警从列表页"消失"，是用户能直接感知的生产事故。

## 阶段 2：写入侧 list_state 同步（不切查询代码，新数据写 list_state）

### 写入路径改造

- [ ] Task 11: `buildIssueEntity` 新建时落 list_state：suppressed=true → SUPPRESSED_BY_COMMENT（并 push SUPPRESSED_RESOLVED 事件到 revisions）；否则 → OPEN
- [ ] Task 12: `updateExistingIssue` 翻转时同步刷新 list_state：RESOLVED→OPEN 翻回时 set list_state=OPEN（并 push REOPENED 事件）；suppressed→RESOLVED 时 set list_state=SUPPRESSED_BY_COMMENT
- [ ] Task 13: `batchShieldIssues` 在 Update 中新增 `.set("list_state", resolveListStateByShieldType(shieldType))`
- [ ] Task 14: `batchUnshieldIssues` 在 Update 中新增 `.set("list_state", StaticAlarmListStateEnum.OPEN.getCode())`
- [ ] Task 15: `resolveDisappearedIssues` 主表 status=RESOLVED 时同步 set list_state=RESOLVED_AUTO
- [ ] Task 16: 确认 `upsertInstance` 不需要同步 list_state（upsertInstance 操作的是 instance 子表 `STATIC_ALARM_ISSUE_INSTANCE`，不直接修改主表 status/list_state。主表 list_state 由 buildIssueEntity / updateExistingIssue 同步设置。upsertInstance 中的 suppressed 处理只影响 instance 子表的 scan_status 和 history）

### 新增 revisions 事件类型

- [ ] Task 17: 新增 SUPPRESSED_RESOLVED 事件类型到 revisions 事件枚举，用于 buildIssueEntity suppressed 路径审计
- [ ] Task 18: 新增 REOPENED 事件类型到 revisions 事件枚举，用于 RESOLVED→OPEN 翻回审计

### 阶段 2 验证

- [ ] Task 19: 编译通过
- [ ] Task 20: 新增 `StaticAlarmOperationTest` 单测覆盖 6 个写入路径的 list_state 同步逻辑
- [ ] Task 21: beta 环境验证新数据写入后 list_state 字段正确，status 与 list_state 一致

## 阶段 3：查询侧切换 + 历史回填验证

### 查询路径合并与切换（前置：Task 10b 回填验证门槛必须通过）

- [ ] Task 22: `StaticAlarmOperation` 合并 `buildIssueCriteria` 与 `buildRepoCoordinatesCriteria` 为 `buildIssueCriteriaUnified`，单仓场景服务端按 repo_type/owner/repo 计算 repo_key 后走 `repo_key $in`
- [ ] Task 23: `buildStatusCriteria` 改造为 `buildListStateCriteria`，按 dto.tab 映射 list_state $in；"已忽略" tab 下叠加 shieldType 精确到单一 list_state
- [ ] Task 24: `applyStatusAndCategoryFilter` 改造为 `applyListStateAndCategoryFilter`
- [ ] Task 25: `buildIssueCriteriaWithoutStatus` / `buildRepoCoordinatesCriteriaWithoutStatus` 同步改造为不含 list_state 版本（用于按 list_state 分组聚合）
- [ ] Task 26: `countIssuesGroupByStatus` 改造为 `countIssuesGroupByListState`，用 $facet 一次拿到各 tab 数量
- [ ] Task 27: `countIssuesGroupByRepoAndStatus` 改造为 `countIssuesGroupByRepoAndListState`
- [ ] Task 28: `buildFacetCriteria` 中 status 条件改为 list_state 条件，并按 dto.tab 精确收窄（避免 $in 全部 7 值）
- [ ] Task 29: `buildSort` 清理误导性注释（fallback "last_seen_at" 是死代码），逻辑不变
- [ ] Task 30: `StaticAlarmServiceImpl` 切换调用统一查询函数 `buildIssueCriteriaUnified`

### DTO/VO 变化

- [ ] Task 31: `StaticAlarmQueryDTO` 新增 tab 字段（String，必填），去掉 statuses / closed 字段在查询逻辑中的使用
- [ ] Task 32: `StaticAlarmFilterOptionsQueryDTO` 新增 tab 字段（String，必填）
- [ ] Task 33: `StaticAlarmIssueListVO` 新增 listState 字段返回前端
- [ ] Task 33b: `StaticAlarmIssueCountVO` 去掉 unresolvedCount / closedCount 旧字段，替换为 6 个 list_state 分组计数字段（pendingCount / ignoredFalsePositiveCount / ignoredTestUsageCount / ignoredWontFixCount / resolvedAutoCount / suppressedByCommentCount）；`StaticAlarmServiceImpl.getIssueCount` 改造为按 list_state 分组填充新字段

### 阶段 3 验证

- [ ] Task 34: 编译通过
- [ ] Task 35: `StaticAlarmOperationTest` 适配 list_state 查询逻辑，覆盖 tab 映射、shieldType 二级筛选
- [ ] Task 36: beta 环境验证 list/count/filter-options 接口行为正确，P99 延迟无显著退化
- [ ] Task 37: beta 环境对生产量级数据跑 explain 验证，winningPlan 命中新索引，无独立 SORT stage

## 阶段 4：前端 tab 拆分与屏蔽类型筛选

### 前端改造

- [ ] Task 38: `StaticAlarm/index.vue` tab 由 2 个拆分为 4 个（待处理 / 已忽略 / 已修复 / 已抑制），tab 切换时传 tab 参数到 list/count/filter-options 接口
- [ ] Task 39: "已忽略" tab 下新增屏蔽类型二级筛选 UI（误报 / 测试使用 / 不修复），切换时传 shieldType 参数
- [ ] Task 40: 计数接口对接按 list_state 分组返回，IGNORED 下细分展示
- [ ] Task 41: 列表展示新增 listState 字段（如需在表格中展示）

### 阶段 4 验证

- [ ] Task 43: 前端编译通过
- [ ] Task 44: beta 环境验证 4 个 tab 切换正常，屏蔽类型二级筛选生效

## 阶段 5：beta 验证与回退预案

### beta 阶段监控

- [ ] Task 46: APM 监控 list 接口 P99 延迟，对比改造前后，确认无显著退化（< 20% 上升）
- [ ] Task 47: APM 监控 filter-options 接口 P99 延迟，重点观察大项目，P99 < 2s
- [ ] Task 48: 跑一次完整导出，确认无 OOM / 超时
- [ ] Task 49: beta 环境跑生产量级数据，典型查询 explain 验证 winningPlan 命中新索引，无独立 SORT stage

### 回退预案

- [ ] Task 50: 准备回滚 PR 模板，包含：
  - 索引 changelog 回滚（重建 10 个旧索引，删除 5 个新索引）
  - 查询代码切换回 status（buildStatusCriteria 恢复，buildIssueCriteriaUnified 拆分回原两函数）
  - list_state 字段保留写入兼容回退（即使回滚查询代码，新数据仍写 list_state，不影响回退后行为）
- [ ] Task 51: 验证回滚 PR 在 beta 环境可在 30 分钟内完成切换

### 上线生产

- [ ] Task 52: beta 验证全部通过后，合并到主分支上线生产
- [ ] Task 53: 生产环境监控 1 周，确认无异常后归档 spec 文档
