## Why

屏蔽规则管理页（managerConfiguration）当前仅通过顶部供应商 autocomplete 做单一模糊搜索，且 `querySearch` 从未接通联想数据，筛选能力弱且交互分散。用户需要在表格列头直接对平台、供应商、组件名称进行多选筛选，并对创建时间列排序，与 SCA 模块其他页面（如 communityList）的表格筛选体验保持一致。数据已全量加载且分页在前端实现，列头筛选与排序应在前端完成，无需后端改动。

## What Changes

- 在 `tableList.vue` 表格为**平台**、**供应商**、**组件名称**三列增加 `filterDropdown` 列头筛选
  - 平台：静态选项 `gitcode`、`gitee`
  - 供应商、组件名称：从当前 `tableDatas` 全量数据去重生成选项
- 移除 `index.vue` 顶部供应商 `el-autocomplete` 搜索（L70-83）及关联的 `searchKeyword`、`querySearch`、`searchKeywordFn`
- 列表请求不再传 `vendor` 模糊参数；供应商筛选改由前端 `tableFilters` 实现
- **创建时间**列增加前端排序（`sortable: 'custom'` + `@sort-change`），在筛选后的数据上排序后再分页 slice
- 筛选、排序与现有前端分页联动：先 filter → sort → slice
- 分页状态由父组件 `pageNum`/`pageSize` 通过 `v-model:page`/`v-model:limit` 与子组件分页器同步；筛选/排序后页码重置为 1
- 列头筛选图标高亮与垂直居中（不修改 `filterDropdown.vue`，由 `tableFilters` + 表头样式实现）

## Capabilities

### New Capabilities

- `sca-manager-config-table-filters`: 屏蔽规则管理表格列头筛选（平台/供应商/组件名称）与创建时间前端排序，替代顶部供应商搜索

### Modified Capabilities

（无现有 openspec spec 需修改）

## Impact

- **前端文件**
  - `apps/web-openlibing/src/views/sca/managerConfiguration/index.vue` — 移除 autocomplete、维护 `tableFilters`/`sortParams`/`pageNum`/`pageSize`、改造 `fetchFrontData` 流水线
  - `apps/web-openlibing/src/views/sca/managerConfiguration/components/tableList.vue` — 列配置扩展、`filterDropdown` 表头、`sort-change` 事件、`v-model:page`/`limit` 分页同步、表头样式与高亮
- **复用组件** — `@/components/filterDropdown.vue`（参考 `communityList.vue` 模式；**不修改**该组件，高亮由 `tableList` 外层样式实现）
- **后端 / API** — 无变更；`shieldList` 仍一次返回全量，不再依赖 `vendor` 参数做列筛选
- **用户体验** — 顶部供应商搜索移除，等价能力迁移至「供应商」列头筛选
