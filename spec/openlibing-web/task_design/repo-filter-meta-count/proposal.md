# 代码仓列表表头筛选条件反显并展示数量

## 需求背景

代码仓（Repos）列表页的列筛选与顶部搜索条目前仅展示筛选项本身，用户无法直观看到各选项对应的仓库数量，也难以在大量候选（如仓库责任人、建仓人、系统录入人、最后更新人、默认分支）中定位目标。需要新增一个查询条件接口，返回当前列表结果下各筛选项及其数量，反显到表头筛选面板与顶部搜索条。

## 功能描述

### 做什么
- 新增 `queryRepoFilterMeta` 前端接口，与列表接口入参一致（剔除分页、排序字段），返回各筛选维度的选项及 `count`
- 在首次加载、切换项目、筛选条件变化时拉取查询条件；翻页、排序时**不**重复拉取
- 表头 ColumnFilter 与顶部搜索条基于返回的 `filterMeta` 拼接 `label(count)` 展示数量
- 后端返回的 `value` 即为选项值（用于匹配列表查询），label 映射保持本地不变
- 空字符串 `value` 映射为「无」，`--` 映射为「未知」
- 人员类四列（仓库责任人/建仓人/系统录入人/最后更新人）与默认分支改为**多选 + 顶部模糊搜索**
- 是/否类开关三列（代码风格自动修复/告警抑制自动检视/自动触发接口扫描）新增多选筛选
- 传参字段名统一为复数形式（如 `repoOwners`、`createBys`、`defaultBranchNames`）

### 不做什么
- 不修改现有列表数据展示逻辑
- 不实现跨页筛选状态持久化
- 不处理 `queryRepoFilterMeta` 接口失败时的降级展示（仅回退到本地 options 不显示 count）

## 验收标准

- [ ] 首次加载 / 切换项目时拉取一次查询条件接口，表头与顶部搜索条展示 `label(count)`
- [ ] 筛选条件变化时重新拉取查询条件，数量实时更新
- [ ] 翻页、排序时不触发查询条件接口
- [ ] 人员类四列与默认分支支持多选 + 顶部模糊搜索
- [ ] 是/否类开关三列支持多选筛选
- [ ] 空字符串 value 显示为「无(数量)」，`--` 显示为「未知(数量)」
- [ ] 顶部搜索条所有 checkbox 筛选项均展示数量，与表头一致

## 影响范围

- 文件：
  - `apps/web-openlibing/src/api/Repos/api.ts`（新增 `queryRepoFilterMeta`）
  - `apps/web-openlibing/src/api/Repos/url.ts`（新增 `QUERY_REPO_FILTER_META`）
  - `apps/web-openlibing/src/views/Repos/index.vue`
  - `apps/web-openlibing/src/views/Repos/components/ColumnFilter.vue`（新增 `searchable` prop）
  - `apps/web-openlibing/src/components/CategorySearch/CategorySearchEditor.vue`（搜索框随 `searchable` 显示）
- 模块：Repos - 代码仓管理
- 接口：新增前端调用 `query-repo-filter-meta`（后端已提供）
