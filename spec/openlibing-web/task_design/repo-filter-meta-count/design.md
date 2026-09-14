# 代码仓列表表头筛选条件反显并展示数量 — 技术设计

## 方案概述

新增 `queryRepoFilterMeta` 接口，在列表加载与筛选变化时拉取当前列表结果下的筛选维度和数量；前端通过统一的 `buildFilterOptions` 工具函数将返回的 `filterMeta` 与本地 label 映射合并，生成带 `(count)` 的选项列表，供表头 ColumnFilter 与顶部搜索条共用。

## 架构决策

| 决策点           | 结论                                                                                                         | 原因                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| 拉取时机         | 首次加载 / 切换项目 / 筛选变化时拉取；翻页、排序不拉取                                                       | 数量反映"当前筛选条件下"的列表分布，翻页排序不影响分布 |
| 防并发覆盖       | 使用自增 `latestFilterMetaRequestId` 校验，仅采用最后一次请求结果                                            | 避免快速连续筛选时旧响应覆盖新响应                     |
| 入参剔除         | 复用 `getQueryData()`，剔除 `pageNum/pageSize/sortField/sortOrder`，追加固定 `filterMetaDimensions` 维度数组 | 与列表接口入参一致，仅去掉分页排序                     |
| options 合并规则 | 后端有返回时按后端 value 顺序构建；本地有映射用本地 label，否则 `--`→未知、`''`→无、其余用 value 本身        | 满足"以接口为准 + 本地 label 不变"的需求               |
| 降级策略         | 接口未返回或失败时回退本地 options，不显示 count                                                             | 保证筛选面板始终可用                                   |
| 传参字段         | 人员/分支/开关类多选字段复数化（`repoOwners`、`createBys`、`defaultBranchNames` 等）                         | 与既有 `platforms`/`purposes` 复数风格一致             |

## 涉及文件

| 文件                                                                         | 操作 | 说明                                                                                                                    |
| ---------------------------------------------------------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/api/Repos/api.ts`                                   | 修改 | 新增 `queryRepoFilterMeta` RequestFunc                                                                                  |
| `apps/web-openlibing/src/api/Repos/url.ts`                                   | 修改 | 新增 `QUERY_REPO_FILTER_META` URL                                                                                       |
| `apps/web-openlibing/src/views/Repos/index.vue`                              | 修改 | 拉取逻辑、`buildFilterOptions`、各维度 `*FilterOptions` computed、表头与顶部搜索条 options 绑定、人员/分支/开关筛选改造 |
| `apps/web-openlibing/src/views/Repos/components/ColumnFilter.vue`            | 修改 | 新增 `searchable` prop，强制开启选项搜索框                                                                              |
| `apps/web-openlibing/src/components/CategorySearch/CategorySearchEditor.vue` | 修改 | 搜索框显示条件由 `searchable && options>6` 改为 `searchable`                                                            |

## 关键实现

### 1. 接口与拉取

```ts
// getFilterMetaData：剔除分页排序，追加固定维度
function getFilterMetaData() {
  const { pageNum, pageSize, sortField, sortOrder, ...rest } = getQueryData();
  return { ...rest, filterMetaDimensions: [/* 全部可筛选维度 */] };
}
```

首次加载/切换项目与 `onFilterChange` 时调用 `fetchRepoFilterMeta()`，翻页/排序处理函数不调用。

### 2. options 合并

`buildFilterOptions(dimension, localOptions)`：

- 后端 `filterMeta[dimension]` 为空数组时返回本地 options（无 count）
- 否则按后端 value 顺序构建，label 取本地映射，特殊 value（`--`/`''`）优先固定映射，最终拼接 `(count)`

### 3. 筛选类型改造

- 人员类四列 + 默认分支：`ColumnFilter` 由 `type="text"` 改为 checkbox，options 用后端驱动，`searchable` 开启顶部模糊搜索
- 是/否类三列：checkbox 多选，options 用 `yesNoOptions` 本地映射，后端返回 1/0

## 风险 & 缓解

| 风险                                                | 缓解                                                   |
| --------------------------------------------------- | ------------------------------------------------------ |
| 后端未返回某维度（如 `updateBy`）导致该列无选项可筛 | 符合"以接口为准"约定，筛选面板为空；不阻塞其他列       |
| 频繁筛选触发多次接口                                | `latestFilterMetaRequestId` 防并发覆盖；翻页排序不触发 |
| 列宽不足容纳标题+图标                               | 是/否类三列宽度 100px → 140px                          |

## 跨仓影响

无。后端 `query-repo-filter-meta` 接口已提供，本次仅前端调用与展示。
