## Why

`my-table` 是 CVE 等模块的通用表格组件，部分页面列数超过 26 列，横向滚动体验差且无法按用户习惯裁剪视图。项目内列配置已有 branches、TableSetting、SCA 等多套重复实现，缺少面向表格消费页面的可复用方案。需要在不改动 `my-table` / `vulnTable` 渲染核心的前提下，为扁平列（>10 列、无嵌套表头）的页面提供统一的列显隐配置能力。

## What Changes

- 新增列配置工具函数、Composable 与 `TableColumnSetting` UI 组件（Popover + 全选/恢复默认/确认取消）
- 列配置入口与导出按钮并列，放置于页面 `setting-btns` 区域
- 仅对**无 `children` 嵌套**且**可配置列数 > 10** 的表格启用列配置入口
- 用户隐藏列时，自动清除该列对应的表头 filter 条件并重查数据
- 导出功能保持现状，仍导出服务端全量字段
- 默认列集为全显示；用户偏好按 `userId + 页面 storageKey` 持久化到 localStorage
- 以 `cveData.vue` 为试点，已推广至 CVE 模块 6 个页面（含 `cveTerm` 双 Tab）及漏洞 0Day「已创建」列表

## Capabilities

### New Capabilities

- `mytable-column-setting`: 表格消费页面的列显隐配置能力，包括 eligibility 判定、持久化、filter 联动与 UI 组件；适用于 `my-table` 与 `vulnTable`

### Modified Capabilities

（无。本次为新增前端能力，不改变既有 spec 级行为契约。）

## Impact

- **新增文件**：
  - `apps/web-openlibing/src/utils/tableColumnSetting.js`
  - `apps/web-openlibing/src/composables/useTableColumnSetting.js`
  - `apps/web-openlibing/src/components/TableColumnSetting.vue`
- **已接入页面**（分支 `vul/list-usability-improvement`）：

  | 页面 | storageKey | 表格组件 |
  |------|------------|----------|
  | `cve/cveData.vue` | `cve-data` | my-table |
  | `cve/cveRepair.vue`（修复详情 Tab） | `cve-repair-detail` | my-table |
  | `cve/cveAbnormal.vue` | `cve-abnormal` | my-table |
  | `cve/cveDuplicateReport.vue` | `cve-duplicate-report` | my-table |
  | `cve/cveTerm.vue`（超期预警 Tab） | `cve-term-overdue-warning` | my-table |
  | `cve/cveTerm.vue`（超期告警 Tab） | `cve-term-overdue-alarm` | my-table |
  | `Vulnerability0Day/vulnerabilityView/created.vue` | `vuln-created` | vulnTable |

- **待接入 eligible 页面**（扁平列 >10、无 children）：`cveStock.vue`、`cvePendingReport.vue`、`cveOperationLog.vue` 等
- **不修改**：`my-table.vue` / `vulnTable.vue` 内部渲染逻辑、`columns.js` 导出接口、含嵌套表头的列集页面
- **依赖**：Element Plus Popover/Checkbox、现有 `useAppStore` 获取 userId、表格组件的 `initOptions()` 重置 filter UI
