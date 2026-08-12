# 代码仓列表表头筛选条件反显并展示数量 — 实现任务

## 进度: 5/5 complete

### Task 1: 新增 queryRepoFilterMeta 接口

**文件**: `apps/web-openlibing/src/api/Repos/api.ts`、`apps/web-openlibing/src/api/Repos/url.ts`

- [x] `url.ts` 新增 `QUERY_REPO_FILTER_META = CODE_REPO + '/project-repo/query-repo-filter-meta'`
- [x] `api.ts` 新增 `queryRepoFilterMeta` RequestFunc

### Task 2: 拉取查询条件

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] 新增 `latestFilterMetaRequestId` 防并发覆盖、`repoFilterMeta` ref 保存返回数据
- [x] `getFilterMetaData()` 复用 `getQueryData()` 剔除分页/排序字段，追加固定 `filterMetaDimensions`
- [x] `fetchRepoFilterMeta()` 在首次加载/切换项目/筛选变化时调用
- [x] 翻页、排序处理函数不触发查询条件接口

### Task 3: options 合并与数量展示

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] `buildFilterOptions(dimension, localOptions)` 按后端 value 构建并拼接 `(count)`
- [x] 特殊 value 映射：`--`→未知、`''`→无，本地有映射优先用本地 label
- [x] 各维度 `*FilterOptions` computed（平台/用途/可见性/开源类型/状态/语言/接管PR/自动触发/人员四列/默认分支/是-否三列）
- [x] 表头 ColumnFilter 与顶部搜索条 `repoSearchCategories` 统一使用带 count 的 options

### Task 4: 筛选类型改造

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] 人员类四列 + 默认分支改为 checkbox 多选 + 顶部模糊搜索
- [x] 是/否类三列新增 checkbox 多选筛选
- [x] 传参字段复数化（`repoOwners`/`createBys`/`updateBys`/`defaultBranchNames`/`isAutoFormats` 等），并同步 `repoSearchModel` getter/setter
- [x] 是/否类三列宽度 100px → 140px

### Task 5: 组件支持强制搜索框

**文件**: `apps/web-openlibing/src/views/Repos/components/ColumnFilter.vue`、`apps/web-openlibing/src/components/CategorySearch/CategorySearchEditor.vue`

- [x] `ColumnFilter` 新增 `searchable` prop，`filterCategory.searchable` 纳入判断
- [x] `CategorySearchEditor` 搜索框显示条件由 `searchable && options>6` 改为 `searchable`
