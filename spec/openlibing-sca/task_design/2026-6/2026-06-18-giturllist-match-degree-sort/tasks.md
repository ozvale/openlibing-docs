## 1. 列配置



- [x] 1.1 在 `analysisTable.config.js` 的 `matched` 列增加 `sortable: 'custom'`



## 2. gitUrlList.vue 状态与事件



- [x] 2.1 新增 `DEFAULT_SORT_PARAMS` 常量及 `sortParams` 响应式状态（初始为空排序）

- [x] 2.2 在 `openSourceCompliance` 的 `el-table` 上绑定 `@sort-change="handleCustomSort"`

- [x] 2.3 在 `el-table-column` 上绑定 `:sortable="column.sortable"`

- [x] 2.4 实现 `handleCustomSort`：仅处理 `prop === 'matched'`，去重后更新 `sortParams`，重置 `pageNo`，调用 `queryRiskData()`

- [x] 2.5 实现 `resetSortParams()`，在切换 scanId / 代码仓时调用



## 3. 查询参数透传



- [x] 3.1 在 `queryRiskData` 中，当 `activeName === 'openSourceCompliance'` 且 `sortParams` 有值时，向 `params` 附加 `sortColumn`、`sortOrder`

- [x] 3.2 确认 `updateCondition`、翻页（`fetchData`）路径均走 `queryRiskData`，排序状态自动保留



## 4. 验证



- [x] 4.1 本地点击「匹配度」列头，Network 面板确认请求体含 `sortColumn`/`sortOrder` 且 `pageNo` 为 1

- [x] 4.2 翻页后确认排序参数仍携带、仅 `pageNo` 变化

- [x] 4.3 切换筛选条件后确认排序参数保留

- [x] 4.4 切换 scanId 后确认排序参数已清除

- [x] 4.5 确认 `projectCompliance` Tab 行为无变化




