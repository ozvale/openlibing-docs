## Why

`gitUrlList.vue` 开源片段引用合规表格（`openSourceCompliance` Tab）的「匹配度」列目前不支持排序。扫描 issue 数据量大，前端本地排序无法覆盖全量分页结果；用户需要按匹配度快速定位高风险片段，必须依赖后端排序。

## What Changes

- 为 `openSourceCompliance` 表格的「匹配度」（`matched`）列启用服务端自定义排序（`sortable: 'custom'`）
- 在 `queryRiskData` 调用 `getScanIssue` 时携带 `sortColumn` / `sortOrder` 参数（与 `communityList.vue` 约定一致）
- 排序变更时重置到第 1 页并重新请求；翻页、筛选时保留当前排序状态
- 默认不主动排序（保持后端现有默认 `scanFile ASC`），用户点击列头后才传排序参数
- **本次仅交付前端改造**；后端 `ScanIssueQueryVO` 及 Mongo 查询层排序能力由后续 PR 补齐

## Capabilities

### New Capabilities

- `sca-scan-issue-match-sort`：gitUrlList 开源合规 issue 列表按匹配度（及后续可扩展列）进行服务端分页排序

### Modified Capabilities

（无既有 OpenSpec 能力需变更）

## Impact

- **前端**：`gitUrlList.vue`、`analysisTable.config.js`
- **API 调用**：`softWareCompent.getScanIssue` 请求体新增可选字段 `sortColumn`、`sortOrder`
- **后端（待办，非本次范围）**：`openlibing-sca` 的 `ScanIssueQueryVO`、`OpenScanServiceImpl.getScanIssue` 需支持动态排序；`matched` 字段为 `"90%"` 字符串，需数值化排序
- **范围外**：`projectCompliance` Tab（`licenseIssue/query`）、其他 SCA 表格列排序扩展
