## Why

`openlibing-web` 已在风险数据看板（`communityList.vue`）为「任务状态」列接入表头筛选，并通过 `GET open/scan/repos` 透传 `scanResult=1,-1,0` 等查询参数。当前 `openlibing-sca` 的 `ScanCommunityReq` 未声明该字段，`getScanByCommunity` 也未按任务状态过滤，导致前端筛选无效。需在后端补齐与前端一致的筛选能力，完成联调闭环。

## What Changes

- 在 `ScanCommunityReq` 新增可选查询参数 `scanResult`（逗号分隔多值，如 `1,-1`）
- 在 `OpenScanServiceImpl.getScanByCommunity` 中，于缓存命中后、排序分页前对列表做内存过滤
- 筛选后更新响应 `total` 为过滤后条数，保证前端分页正确
- `totalCount` / `riskCount` 保持社区级汇总不变（与前端 design 默认一致）
- 新增单元测试覆盖 `filterByScanResult` 及筛选与排序/分页叠加场景
- 不修改 SQL/Mapper、不调整 Redis 列表缓存 key

## Capabilities

### New Capabilities

- `open-scan-repos-status-filter`: `GET /open/scan/repos` 按 `scanResult`（任务状态）筛选社区代码仓扫描记录的后端能力

### Modified Capabilities

（无既有 openspec spec 需变更）

## Impact

- **关联前端变更**：`openlibing-web` change `community-list-task-status-filter`（已实现 UI 与参数透传）
- **后端文件**：`ScanCommunityReq.java`、`OpenScanServiceImpl.java`、新建 `OpenScanServiceImplTest.java`
- **API**：`GET /open/scan/repos` 新增可选 query 参数 `scanResult`，无 breaking change
- **缓存**：Redis 列表缓存 key 不变；`scanResult` 在缓存命中后后置过滤
- **数据字段**：`ScanInfoVO.scanResult` 来源于 `tbl_scan.scan_result`，值域 `1` / `-1` / `0`
