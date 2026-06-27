## Why

`gitUrlList.vue` 开源片段引用合规表格已完成前端改造：`matched`（匹配度）列启用 `sortable: 'custom'`，并在调用 `POST /open/scan/scanIssue/query` 时透传 `sortColumn` / `sortOrder`。后端 `ScanIssueQueryVO` 尚未定义排序字段，`OpenScanServiceImpl.getScanIssue` 仍硬编码 `scanFile ASC`，导致前端排序交互无法生效。

## What Changes

- `ScanIssueQueryVO` 新增可选字段 `sortColumn`、`sortOrder`
- 新增 `ScanIssueColumnList` 白名单枚举，首期支持 `matched` → Mongo 字段 `matched`
- `getScanIssue` 在 Mongo 查询阶段应用动态排序（排序必须在 `skip/limit` 之前）
- `matched` 字段（`"90%"` 字符串）按数值排序，复用 `FileUtil.getMatchedScore` 语义
- 无排序参数或非法参数时，保持现有默认行为：`scanFile ASC`
- 补充单元测试覆盖升序/降序/默认/非法列名

## Capabilities

### New Capabilities

- `sca-scan-issue-query-sort`：`scanIssue/query` 接口支持按匹配度等服务端分页排序

### Modified Capabilities

（无既有 OpenSpec 能力需变更）

## Impact

- **后端仓**：`openlibing-sca`
  - `ScanIssueQueryVO.java`
  - 新增 `ScanIssueColumnList.java`（`common/enums`）
  - `OpenScanServiceImpl.java`（`getScanIssue` 及排序辅助方法）
  - `FileUtil.java`（可选：将 `getMatchedScore` 提升为 public 供测试复用）
  - 测试：`OpenScanServiceImplTest` 或新建专项测试
- **前端**：已完成，无需改动（参数契约见 `gitUrlList.vue`）
- **关联变更**：`openspec/changes/giturllist-match-degree-sort`（前端方案，已落地）

## 前端契约（已实现，后端须对齐）

| 字段 | 值 | 说明 |
|------|-----|------|
| `sortColumn` | `"matched"` | 与列 prop 一致 |
| `sortOrder` | `"ascending"` / `"descending"` | Element Plus 约定 |
| 取消排序 | 不传两字段 | 回退 `scanFile ASC` |
