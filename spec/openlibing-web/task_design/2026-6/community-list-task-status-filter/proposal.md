## Why

风险数据看板（`communityList.vue`）开源片段引用合规表格的「任务状态」列目前仅展示扫描结果，用户无法按成功/失败/执行中快速筛选代码仓记录。在已有平台、代码仓等顶部筛选之外，表头筛选能缩短定位异常扫描任务的路径，与发布评审等模块的 `filterDropdown` 交互保持一致。

## What Changes

- 在 `openSourceCompliance` 表格的「任务状态」（`scanResult`）列表头接入 `filterDropdown` 组件，提供多选筛选（成功 / 失败 / 执行中）
- 筛选确认后将选中状态值写入 `getRepos`（`open/scan/repos`）请求参数，触发服务端重新分页查询
- 切换社区、平台、代码仓或 Tab 时重置任务状态筛选条件与下拉 UI 状态
- 筛选重置时移除 `scanResult` 参数，恢复全量列表
- **范围限定**：仅改动 `openlibing-web` 前端；不修改 `projectCompliance` 表格

## Capabilities

### New Capabilities

- `sca-community-repos-status-filter`: 社区风险看板 `open/scan/repos` 列表的任务状态表头筛选能力，含前端 UI、请求参数契约与筛选重置行为

### Modified Capabilities

（无既有 openspec spec 需变更）

## Impact

- **前端文件**：`apps/web-openlibing/src/views/sca/softInformation/communityList.vue`（主改动）、复用 `apps/web-openlibing/src/components/filterDropdown.vue`
- **API 调用**：`softWareCompent.getRepos` → `GET /gateway/openlibing-sca/open/scan/repos`，新增透传 `scanResult` 查询参数（多选值数组或约定格式）
- **后端依赖（假设）**：`ScanCommunityReq` / `getScanByCommunity` 需支持按 `scanResult` 过滤；当前后端 DTO 尚未声明该字段，本变更以前端接入与参数透传为主，后端对齐为联调前提
- **无破坏性变更**：未筛选时请求参数与现网行为一致
