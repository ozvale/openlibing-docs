## Why

StaticAlarm 告警列表页面的后端接口进行了重构，返回了新的状态字段（`pendingCount`、`ignoredFalsePositiveCount`、`ignoredTestUsageCount`、`ignoredWontFixCount`、`resolvedAutoCount`），废弃了原有的 `unresolvedCount`/`closedCount` 字段。同时，列表查询接口的请求参数也发生了变化，原有的 `closed` 和 `statuses` 字段被 `tab` 字段取代。前端需要同步适配这些变化，并利用新字段优化 UI 展示，提升用户体验。

## What Changes

- **状态字段适配**：将前端状态展示从 `unresolvedCount`/`closedCount` 改为 `pendingCount` + `ignored*Count` 三字段 + `resolvedAutoCount`
- **状态标签拆分**：将原有的"已关闭"标签拆分为"已修复"和"已忽略"两个独立标签，各自展示对应数量
- **接口参数变更**：列表查询参数从 `closed`/`statuses` 改为 `tab` 字段（取值 PENDING/IGNORED/RESOLVED）
- **状态值同步**：已修复状态值 `RESOLVED_AUTO` 改为 `RESOLVED`，与后端保持一致
- **忽略原因筛选**：新增 `shieldTypes` 筛选条件，仅在"已忽略"状态下展示，支持多选，选项后显示对应数量
- **数据来源筛选优化**：从多选改为单选，避免多选只能传第一个值的 bug

## Capabilities

### New Capabilities

- `shield-types-filter`: 忽略原因多选筛选，仅在已忽略状态下展示，下拉选项后显示对应数量（误报/测试使用/不修复）

### Modified Capabilities

- `status-tab-switch`: 状态标签从"待处理/已关闭"二态改为"待处理/已修复/已忽略"三态
- `data-source-filter`: 数据来源筛选从多选改为单选
- `api-request-params`: 列表查询参数从 `closed`/`statuses` 改为 `tab` 字段

## Impact

- **前端代码**: `StaticAlarm/index.vue`（模板+脚本改造）、`utils/staticAlarmSearchQuery.ts`（搜索查询解析/序列化逻辑）、`components/GithubHeaderFilter.vue`（头部筛选展示）、`components/GithubIssueSearch.vue`（搜索框筛选）
- **API 交互**: 列表接口请求参数 `closed`/`statuses` 废弃，改为 `tab`；数量接口返回字段 `unresolvedCount`/`closedCount` 废弃，改为 `pendingCount`/`ignoredFalsePositiveCount`/`ignoredTestUsageCount`/`ignoredWontFixCount`/`resolvedAutoCount`
- **数据结构**: `StaticAlarmFilter` 中 `sources` 类型从 `string[]` 改为 `string`；`MULTI_FILTER_KEYS` 移除 `sources`
- **测试**: `staticAlarmSearchQuery.spec.ts` 更新状态值和 `sources` 相关断言
