## Why

`openlibing-web` 已在风险数据看板「项目合规」Tab（`communityList.vue`）为任务状态列接入表头筛选，并向 `GET license/repos` 透传 `repoResult=success,fail` 及 `sortColumn`/`sortOrder`。当前 `openlibing-sca` 的 `ScanCommunityDto` 未声明这些字段，`LicenseServiceImpl.getScanByCommunity` 固定按代码仓中文排序且 MongoDB 统计仅在分页后加载，导致前端筛选与分页排序全部无效。需在后端补齐与前端契约一致的筛选与排序能力，完成项目合规看板联调闭环。

## What Changes

- 在 `ScanCommunityDto` 新增可选查询参数 `repoResult`（逗号分隔多值，如 `success,fail`）、`sortColumn`、`sortOrder`
- 重构 `LicenseServiceImpl.getScanByCommunity`：去重后按 `repoResult` 内存过滤；将 MongoDB 统计（`getStatsBatch` + `getScanResult`）前移至排序前，以支持 `fileNum` 等衍生字段排序
- 新增 `LicenseColumnList` 排序列白名单，支持 `scanTime`、`fileNum`、`compatibilityNumber`、`incompatibleNumber`、`unrecognizedNumber`
- 筛选后更新响应 `total` 为过滤后条数；无自定义排序时默认按 `licenseCreateTime` 降序
- 新增/扩展单元测试覆盖 `filterByRepoResult`、排序分页及筛选叠加场景
- 不修改 SQL/Mapper XML（与已归档 `repos-scan-result-filter` 策略一致）

## Capabilities

### New Capabilities

- `license-repos-filter-sort`: `GET /license/repos` 按 `repoResult`（任务状态）筛选及 `sortColumn`/`sortOrder` 服务端排序的分页列表能力

### Modified Capabilities

（无既有 openspec spec 需变更）

## Impact

- **关联前端变更**：`openlibing-web` change `project-compliance-status-filter-sort`（已实现 UI 与参数透传）
- **后端文件**：`ScanCommunityDto.java`、`LicenseServiceImpl.java`、新建 `LicenseColumnList.java`、扩展 `LicenseServiceImplTest.java`
- **API**：`GET /license/repos` 新增可选 query 参数 `repoResult`、`sortColumn`、`sortOrder`，无 breaking change（未传参时行为可保持兼容，默认排序语义见 design）
- **数据字段**：`LicenseInfoVO.repoResult` 来源于 `tbl_scan.repo_result`，值域 `success` / `fail`（`ResultType` 枚举）
- **导出**：`fetchLicenseList` 复用 `getScanByCommunity`，导出顺序将跟随新排序逻辑
