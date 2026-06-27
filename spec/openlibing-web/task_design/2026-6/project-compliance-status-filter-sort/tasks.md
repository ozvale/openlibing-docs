## 1. 列配置

- [x] 1.1 为 `table.projectColumn` 中 `scanResult` 列增加 `filterAble: true`、`name: 'repoResult'`、`newFilterIcon: true` 及静态 `filters`（成功=`success`、失败=`fail`）
- [x] 1.2 将 `projectColumn` 中 `scanTime`、`fileNum` 的 `sortable: true` 改为 `sortable: 'custom'`
- [x] 1.3 扩展 `statusMap`，补充 `success`/`fail` 中文映射

## 2. 项目合规表头筛选 UI

- [x] 2.1 在 `projectCompliance` 表格 `el-table-column` `v-for` 内增加 `#header` 插槽：当 `column.filterAble` 为 true 时渲染 `filterDropdown`
- [x] 2.2 绑定 `:key`（含 `filterResetKey`）、`:options`、`:label`、`:name`、`:prop`、`:new-filter-icon` 及 `@change="handleTableFilter"`

## 3. 服务端自定义排序

- [x] 3.1 为 `projectCompliance` 的 `el-table` 增加 `ref="projectComplianceTable"` 与 `@sort-change="handleCustomSort"`
- [x] 3.2 将嵌套列「合规数 / 未确认数 / 未识别数」的 `sortable` 改为 `'custom'`
- [x] 3.3 在 `resetQueryContext()` 中增加 `this.$refs.projectComplianceTable?.clearSort()`

## 4. 请求参数透传

- [x] 4.1 在 `initQueryData()` 的 `projectCompliance` 分支合并 `repoResult`（逗号分隔，来自 `tableFilters.repoResult`）
- [x] 4.2 在同一分支合并 `sortColumn`、`sortOrder`（来自 `sortParams`，无排序时不传）
- [x] 4.3 确认 `handleTableFilter` 筛选变更时重置 `pageNo=1`（已存在逻辑，验证对 projectCompliance 生效）

## 5. 任务状态展示修正

- [x] 5.1 修正 `projectCompliance` 单元格模板：`showCause` 失败判断使用 `'fail'` 而非 `'-1'`
- [x] 5.2 确认成功/失败图标与样式类名与 `success`/`fail` 值域一致

## 6. 验证

- [x] 6.1 未筛选未排序时，`license/repos` 请求参数与变更前一致
- [x] 6.2 勾选任务状态筛选后，请求携带 `repoResult` 且 `pageNo=1`
- [x] 6.3 点击可排序列后，请求携带 `sortColumn`/`sortOrder` 且翻页后排序指示保持
- [x] 6.4 筛选与排序叠加时，请求同时携带 `repoResult`、`sortColumn`、`sortOrder`
- [x] 6.5 切换社区/Tab 后，筛选图标恢复未高亮、排序指示清除、请求不再带筛选排序参数

## 7. 联调备注（非阻塞）

- [x] 7.1 与 `openlibing-sca` 确认 `license/repos` 对 `repoResult`、`sortColumn`、`sortOrder` 的支持计划；后端未就绪前前端仅完成参数透传

> 前端按 design 约定透传 `repoResult=success,fail`（逗号分隔）及 Element Plus 排序参数。后端 `ScanCommunityDto` / `LicenseServiceImpl` 尚未支持，需后续联调生效。
