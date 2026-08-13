# static-alarm-close-reason-filter

## 需求背景

openlibing-codecheck 的静态告警列表页当前只区分"待处理"与"已关闭"两个 tab，"已关闭"中混合了三类语义不同的关闭记录：人工屏蔽（误报 / 测试使用 / 不修复）、扫描消失自动修复、SARIF suppressions 注释抑制。领导关注工具误报率，需要在列表层支持按屏蔽类型筛选，并能在前端 tab 维度区分"已忽略（人工）"、"已修复（自动）"、"已抑制（注释）"三类关闭原因，便于误报率统计与人工复核。

当前实现的限制：

- 主表 `static_alarm_issue` 仅有 `status` 单字段表达状态，取值为 OPEN / IGNORED / PENDING_REVIEW / RESOLVED。
- 屏蔽类型（误报 / 测试使用 / 不修复）只写入 `revisions` 数组的 SHIELD 事件，主表无冗余字段，无法在 list 查询层按屏蔽类型筛选。
- status=RESOLVED 同时承载"扫描消失自动修复"和"SARIF suppressions 注释抑制"两种语义，无法区分。
- 当前 12 个索引中存在三元组前缀与 repo_key 前缀两套并行路径，索引数量随排序字段线性叠加，新增屏蔽类型筛选字段会进一步膨胀索引。

## 功能描述

1. **新增 `list_state` 派生字段**：将 status 与关闭原因（屏蔽类型 / 自动修复 / 注释抑制）的组合预计算为单一枚举值，写入主表，替代查询时的多字段组合判断。取值为 OPEN / PENDING_REVIEW / IGNORED_FALSE_POSITIVE / IGNORED_TEST_USAGE / IGNORED_WONT_FIX / RESOLVED_AUTO / SUPPRESSED_BY_COMMENT 共 7 种。
2. **前端 tab 拆分**：由 2 个（待处理 / 已关闭）拆分为 4 个（待处理 / 已忽略 / 已修复 / 已抑制），其中"已忽略"按屏蔽类型支持二级筛选。
3. **索引收敛**：新增 5 个 `repo_key + list_state + sortField` 索引覆盖所有排序路径，下线 10 个被替代的旧索引，从 12 个收敛到 7 个。
4. **历史数据回填**：通过 Liquibase changelog 执行一次性回填脚本，从 revisions 反推 list_state。
5. **写入侧同步**：在所有改变 status 的代码路径同步计算并落库 list_state，包括新建、扫描命中刷新、RESOLVED→OPEN 翻回、自动 RESOLVED、人工屏蔽、SARIF suppressions 标记。
6. **查询侧切换**：合并两条查询路径为统一函数，单仓场景由服务端计算 repo_key 后统一走 `repo_key $in`。`buildStatusCriteria` 改造为 `buildListStateCriteria`，按前端 tab 映射 list_state $in。

## 不做什么

- 不删除 `status` 字段：审计、revisions 历史事件流、其他潜在消费方可能依赖 status 原始值。list_state 是查询优化字段，不是替换。
- 不引入缓存：当前场景为低频查询，无热点数据访问需求。
- 不引入 Atlas Search / OpenSearch：本次不实施，留到筛选维度持续膨胀的中长期阶段评估。
- 不修改 buildSort 排序逻辑：DTO 字段默认值 "severity" 已保证 importance 走 severity_rank 排序，buildSort 中 fallback "last_seen_at" 为死代码，仅清理误导性注释，不改逻辑。
- 不修改 `idx_issue_fingerprint` 唯一索引：本次新增 list_state 字段不动 upsert 去重字段。
- 不为 lastSeenAt 排序收窄 @Pattern：保留该入参以覆盖潜在外部调用方，对应索引 `idx_issue_repo_key_state_last_seen` 保留。
- 不迁移 `resolveDisappearedIssues` 到 repo_key 路径：保持现有 repo_type+owner+repo+branch+status 查询形状，命中保留的 `idx_issue_branch_status` 索引。

## 验收标准

### 功能验收

- [ ] 主表 `static_alarm_issue` 新增 `list_state` 字段（String 类型）
- [ ] list_state 取值覆盖 7 种枚举：OPEN / PENDING_REVIEW / IGNORED_FALSE_POSITIVE / IGNORED_TEST_USAGE / IGNORED_WONT_FIX / RESOLVED_AUTO / SUPPRESSED_BY_COMMENT
- [ ] 6 个写入路径同步落库 list_state：buildIssueEntity / updateExistingIssue / batchShieldIssues / batchUnshieldIssues / resolveDisappearedIssues / upsertInstance suppressed 路径
- [ ] 前端 tab 由 2 个拆分为 4 个：待处理 / 已忽略 / 已修复 / 已抑制
- [ ] "已忽略" tab 下支持按屏蔽类型二级筛选（误报 / 测试使用 / 不修复）
- [ ] 列表查询接口支持 tab 参数，按 tab 映射 list_state $in
- [ ] 计数接口去掉旧字段 unresolvedCount / closedCount，替换为 6 个 list_state 分组计数字段（pendingCount / ignoredFalsePositiveCount / ignoredTestUsageCount / ignoredWontFixCount / resolvedAutoCount / suppressedByCommentCount）
- [ ] 筛选项接口按 tab 精确收窄 list_state，避免候选集放大
- [ ] 历史数据回填脚本执行成功，list_state 字段覆盖所有存量记录

### 索引验收

- [ ] 新增 5 个索引：idx_issue_repo_key_state_first_seen / state_updated_at / state_severity / state_last_seen / repo_key_rule
- [ ] 下线 10 个旧索引：idx_issue_list / idx_issue_rule / idx_issue_list_first_seen / idx_issue_sort_last_seen / idx_issue_sort_updated_at / idx_issue_sort_severity / idx_issue_repo_key_status_sort_last_seen / idx_issue_repo_key_sort_severity / idx_issue_repo_key_sort_updated_at / idx_issue_repo_key_sort_first_seen
- [ ] 最终索引数为 7 个
- [ ] Liquibase changelog 幂等（dropIndex 使用 ifExists 检查）

### 性能验收

- [ ] list 接口 P99 延迟无显著退化（< 20% 上升）
- [ ] filter-options 接口 P99 < 2s（大项目下）
- [ ] 导出接口无 OOM / 超时
- [ ] 典型查询 explain 验证 winningPlan 命中新索引，无独立 SORT stage

### 回退预案

- [ ] 准备回滚 PR 模板，索引 changelog + 查询代码切换可在 30 分钟内完成
- [ ] list_state 字段保留写入兼容回退（即使回滚查询代码，新数据仍写 list_state，不影响回退后行为）

### 发布顺序硬性检查项（强制前置门槛）

- [ ] 步骤 1：部署新字段 + 写入逻辑 + 回填脚本 + 新索引（不切查询代码），Liquibase changelog 执行成功
- [ ] 步骤 2：回填脚本执行完成后，跑 `count({list_state: {$exists: false}})` 或 `count({list_state: null})`，**必须为 0**（或定位到能接受的极少量兜底记录）
- [ ] 步骤 3：确认回填覆盖率为 100% 后，才允许切换查询代码到 buildListStateCriteria，切换后跑 list 接口验证 4 个 tab 数据正确，无告警"消失"

## 影响范围

### 业务仓 `openlibing-codecheck`

| 文件                                                                             | 操作 | 说明                                                                                                                                          |
| -------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `business/entity/alarm/StaticAlarmIssueEntity.java`                              | 修改 | 新增 `list_state` 字段                                                                                                                        |
| `common/enums/alarm/StaticAlarmListStateEnum.java`                               | 新增 | list_state 枚举定义与映射方法                                                                                                                 |
| `business/operation/alarm/StaticAlarmOperation.java`                             | 修改 | 合并查询路径；buildStatusCriteria → buildListStateCriteria；6 个写入路径同步落 list_state；buildFacetCriteria 按 tab 收窄；buildSort 注释清理 |
| `business/service/impl/alarm/StaticAlarmServiceImpl.java`                        | 修改 | 切换调用统一查询函数；countIssuesGroupByListState                                                                                             |
| `business/entity/dto/alarm/StaticAlarmQueryDTO.java`                             | 修改 | 新增 tab 字段                                                                                                                                 |
| `business/entity/dto/alarm/StaticAlarmFilterOptionsQueryDTO.java`                | 修改 | 新增 tab 字段                                                                                                                                 |
| `business/entity/vo/alarm/StaticAlarmIssueListVO.java`                           | 修改 | 新增 listState 字段返回前端                                                                                                                   |
| `business/vo/alarm/StaticAlarmIssueCountVO.java`                                 | 修改 | 去掉 unresolvedCount / closedCount 旧字段，替换为 6 个 list_state 分组计数字段                                                                |
| `src/main/resources/db/changelog/mongo/v1.0.0/static_alarm_index_governance.xml` | 修改 | 新增 5 个索引 changeSet + 下线 10 个旧索引 changeSet + 历史回填 changeSet                                                                     |
| `src/test/java/.../StaticAlarmListStateEnumTest.java`                            | 新增 | 枚举映射方法单测                                                                                                                              |
| `src/test/java/.../StaticAlarmOperationTest.java`                                | 修改 | 适配 list_state 查询与写入逻辑                                                                                                                |

### 业务仓 `openlibing-web`

| 文件                                                  | 操作 | 说明                                                     |
| ----------------------------------------------------- | ---- | -------------------------------------------------------- |
| `apps/web-openlibing/src/views/StaticAlarm/index.vue` | 修改 | tab 拆分为 4 个；屏蔽类型二级筛选 UI；listState 字段对接 |

### docs 仓 `openlibing-docs`

| 文件                                                                                 | 操作 | 说明         |
| ------------------------------------------------------------------------------------ | ---- | ------------ |
| `spec/openlibing-codecheck/task_design/static-alarm-close-reason-filter/proposal.md` | 新增 | 本文件       |
| `spec/openlibing-codecheck/task_design/static-alarm-close-reason-filter/design.md`   | 新增 | 技术设计     |
| `spec/openlibing-codecheck/task_design/static-alarm-close-reason-filter/tasks.md`    | 新增 | 实现任务清单 |

## 关联 Issue

待创建（业务 Issue 链接）
