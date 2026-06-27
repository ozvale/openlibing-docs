## Why

风险数据看板「项目合规」（`projectCompliance`）表格的任务状态列目前仅展示 `repoResult` 映射值，无法像同页「开源片段引用合规」Tab 一样按状态快速筛选。同时，该表格若干列配置了 `sortable: true`，触发的是 Element Plus **当前页客户端排序**，与已有服务端分页（`getProjectRepos` → `license/repos`）不一致，翻页后排序结果失真。需在仅改前端的前提下，对齐 openSource Tab 已验证的 `filterDropdown` + 自定义排序模式，并为后续后端联调预留参数契约。

## What Changes

- 在 `projectCompliance` 表格「任务状态」（`scanResult` / 原始 `repoResult`）列表头接入 `filterDropdown`，提供多选筛选（成功 / 失败）
- 筛选确认后将选中值写入 `getProjectRepos` 请求参数（`repoResult`，逗号分隔），页码重置为 1 后重新请求
- 将 `projectCompliance` 表格可排序列由 `sortable: true` 改为 `sortable: 'custom'`，绑定 `@sort-change`，向 `license/repos` 透传 `sortColumn` / `sortOrder`
- 嵌套列「合规数 / 未确认数 / 未识别数」同样改为服务端自定义排序
- 复用组件内已有 `tableFilters`、`handleTableFilter`、`filterResetKey` 机制；切换社区/平台/代码仓/Tab 时重置筛选与排序
- 修正 `projectCompliance` 任务状态单元格与 `showCause` 对 `success`/`fail` 值域的判断（与 `repoResult` 实际存储一致）
- **范围限定**：仅改动 `openlibing-web` 前端；不修改 `openlibing-sca` 后端（参数透传 + 联调约定）

## Capabilities

### New Capabilities

- `sca-project-compliance-repos-filter-sort`: 社区风险看板 `license/repos` 列表的任务状态表头筛选与服务端自定义排序能力，含前端 UI、请求参数契约与上下文重置行为

### Modified Capabilities

（无既有 openspec spec 需变更）

## Impact

- **前端文件**：`apps/web-openlibing/src/views/sca/softInformation/communityList.vue`（主改动）、复用 `apps/web-openlibing/src/components/filterDropdown.vue`
- **API 调用**：`softWareCompent.getProjectRepos` → `GET /gateway/openlibing-sca/license/repos`，新增透传 `repoResult`、`sortColumn`、`sortOrder`
- **与既有变更关系**：`community-list-task-status-filter` 已覆盖 `openSourceCompliance`；本变更独立覆盖 `projectCompliance`，不重复改造开源 Tab
- **后端依赖（假设）**：`ScanCommunityDto` / `LicenseServiceImpl.getScanByCommunity` 需后续支持 `repoResult` 筛选与自定义排序；当前以前端接入与参数透传为主
- **无破坏性变更**：未筛选、未排序时请求参数与现网行为一致
