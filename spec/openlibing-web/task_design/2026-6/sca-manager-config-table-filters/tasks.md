## 1. tableList.vue 列头筛选与排序 UI

- [x] 1.1 引入 `filterDropdown` 组件，扩展 `tableHeader`：`platform`、`vendor`、`shieldRole` 增加 `filterAble`、`newFilterIcon`；`platform` 配置静态 `filters`（gitcode、gitee）
- [x] 1.2 在 `el-table-column` 增加 `#header` 插槽：对 `filterAble` 列渲染 `filterDropdown`，绑定 `filters`、`filterResetKey`，`@change` emit `filter`
- [x] 1.3 `created` 列设置 `sortable: 'custom'`，`el-table` 增加 `@sort-change` 并 emit `sortChange` 给父组件
- [x] 1.4 新增 props：`filterResetKey`、`columnFilters`（或合并到列配置的动态 filters 由父传入 `tableHeader` 覆盖项）

## 2. index.vue 前端筛选/排序流水线

- [x] 2.1 新增 `tableFilters`、`sortParams`（默认 `created` descending）、`filterResetToken`；实现 `applyTableFilters`、`applySort`、`getFilteredDatas` 工具方法
- [x] 2.2 改造 `fetchFrontData`：对 `getFilteredDatas()` 结果 slice，不再直接 slice `tableDatas`
- [x] 2.3 `getShieldList` 成功后从 `tableDatas` 去重生成 `vendor`、`shieldRole` 的 `filters` 并更新列配置；移除 `vendor: searchKeyword` 参数
- [x] 2.4 实现 `handleTableFilter`：更新 `tableFilters`，`pageNum = 1`，调用 `pageChange`
- [x] 2.5 实现 `handleSortChange`：更新 `sortParams`，`pageNum = 1`，调用 `pageChange`
- [x] 2.6 社区/仓库切换（`changeCommunity`、`changeChildCommunity`、`queryPRCommitData`）时重置 `tableFilters`、`sortParams`、`filterResetToken`

## 3. 移除顶部供应商搜索

- [x] 3.1 删除 `index.vue` L70-83 `el-autocomplete` 模板及相关样式（`.el-icon-search` 若仅用于此处可清理）
- [x] 3.2 删除 `searchKeyword` data、`querySearch`、`searchKeywordFn` 方法
- [x] 3.3 确认 `getShieldList` 不再依赖 `searchKeyword`；删除未使用的 `Search` 图标 import（如有）

## 4. 父子组件联调

- [x] 4.1 `index.vue` 向 `tableList` 传递 `filterResetKey`、动态列 filters，监听 `@filter`、`@sortChange`
- [x] 4.2 验证分页 `total` 为筛选后条数；多列筛选 AND 组合正确
- [x] 4.3 验证创建时间升序/降序在筛选后数据上生效
- [x] 4.4 父组件 `v-model:page`/`v-model:limit` 与子组件分页器同步；筛选/排序后页码重置且 UI 一致
- [x] 4.5 `fetchFrontData` 在筛选后总条数不足时自动校正 `pageNum`

## 5. UI 细节

- [x] 5.1 移除 `el-table` `:key="tableShowDatas?.length"`，避免筛选后 remount 丢失筛选图标状态
- [x] 5.2 `tableFilters` 驱动 `is-filter-active` 表头筛选图标高亮（不修改 `filterDropdown.vue`）
- [x] 5.3 表头文字与筛选图标垂直居中样式

## 6. 手动验收

- [x] 6.1 平台列仅显示 gitcode/gitee，多选筛选正确
- [x] 6.2 供应商、组件名称选项来自全量数据去重，筛选后分页正确
- [x] 6.3 顶部无供应商搜索框；切换仓库后筛选与排序重置
- [x] 6.4 删除、批量删除、立即生效、添加规则等现有功能不受影响
- [x] 6.5 第 2 页应用筛选后分页器与表格均显示第 1 页
