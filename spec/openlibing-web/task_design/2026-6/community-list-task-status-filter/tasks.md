## 1. 列配置与组件注册

- [x] 1.1 在 `communityList.vue` 中 import 并注册 `filterDropdown` 组件
- [x] 1.2 为 `table.column` 中 `scanResult` 列增加 `filterAble: true`、`name: 'scanResult'`、`newFilterIcon: true` 及静态 `filters`（成功/失败/执行中，value 为 `1`/`-1`/`0`）

## 2. 表头筛选 UI

- [x] 2.1 在 `openSourceCompliance` 表格的 `el-table-column` `v-for` 内增加 `#header` 插槽：当 `column.filterAble` 为 true 时渲染 `filterDropdown`
- [x] 2.2 为 `filterDropdown` 绑定 `:key`（含 `filterResetKey`）、`:options`、`:label`、`:name`、`:prop`、`:new-filter-icon` 及 `@change="handleTableFilter"`

## 3. 筛选状态与请求参数

- [x] 3.1 在 `data()` 中新增 `tableFilters: {}`、`filterResetToken: 0`，计算属性或方法生成 `filterResetKey`
- [x] 3.2 实现 `handleTableFilter({ name, data })`：更新 `tableFilters`、将 `pageNo` 置 1、调用 `initQueryData()`
- [x] 3.3 在 `initQueryData()` 的 `openSourceCompliance` 分支中，将 `scanResult` 筛选值以逗号分隔字符串合并进 `getRepos` 的 `params`（无选中时不传）

## 4. 上下文重置

- [x] 4.1 抽取 `resetTableFilters()`：清空 `tableFilters`、`filterResetToken += 1`
- [x] 4.2 在 `chooseCommunityValue`、`choosePlatformValue`、`chooseGitUrlValue`、`activeName` 的 `watch` 中调用 `resetTableFilters()`（与现有 `sortParams` 重置并列）

## 5. 验证

- [x] 5.1 本地验证：未筛选时列表请求参数与变更前一致
- [x] 5.2 本地验证：勾选任务状态并筛选后，请求携带 `scanResult` 且 `pageNo=1`
- [x] 5.3 本地验证：点击重置或切换社区后，筛选图标恢复未高亮、请求不再带 `scanResult`
- [x] 5.4 本地验证：筛选状态下自定义排序请求同时携带 `sortColumn`/`sortOrder` 与 `scanResult`

## 6. 联调备注（非阻塞）

- [x] 6.1 与 `openlibing-sca` 确认 `open/scan/repos` 对 `scanResult` 参数格式（逗号分隔 / 多值 query）的支持情况；若格式需调整，仅改 `initQueryData` 参数序列化逻辑

> 前端已按 design 约定透传 `scanResult=1,-1,0`（逗号分隔）。后端 `ScanCommunityReq` 尚未声明该字段，需联调确认后生效。
