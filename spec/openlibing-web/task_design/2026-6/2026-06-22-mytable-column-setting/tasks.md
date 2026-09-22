## 1. 基础设施

- [x] 1.1 新增 `utils/tableColumnSetting.js`：`hasNestedColumns`、`getConfigurableItems`、`isColumnSettingEligible`、`getColumnKey`、`getFilterKey`、`filterColumns`、`getClearedFilterKeys`、`normalizeVisibleKeys`、`buildStorageKey`、`readStoredColumnKeys`、`writeStoredColumnKeys`

- [x] 1.2 新增 `composables/useTableColumnSetting.js`：storageKey/userId/columns 入参，返回 eligible、visibleColumns、Popover 状态与 confirm/cancel/reset 方法

- [x] 1.3 新增 `components/TableColumnSetting.vue`：Popover + checkbox 网格 + 全选/恢复默认/取消/确认（对齐 branches.vue 交互）


## 2. cveData 试点接入

- [x] 2.1 在 `cveData.vue` 的 `setting-btns` 中并列添加 `TableColumnSetting`（`storageKey: 'cve-data'`）

- [x] 2.2 将 `my-table` 的 `:columns` 改为 composable 返回的 `visibleColumns`

- [x] 2.3 实现 `onColumnSettingConfirm`：清除 hidden 列 filter、`initOptions()`、重置页码、`getCVEData()` 重查

- [x] 2.4 手动验收：默认全显示、持久化、fixed 列 disabled、隐藏 filter 列联动、导出行为不变

## 3. cveRepair 修复详情 Tab 推广

- [x] 3.1 在 `cveRepair.vue` 修复详情 Tab 的 `setting-btns` 接入列配置（`storageKey: 'cve-repair-detail'`）

- [x] 3.2 联动 `softwareFilter` / `cveDataFilters` 与 `$refs.table.initOptions()`

- [x] 3.3 验证 selection 列始终显示且不出现在配置面板

## 4. CVE 模块其余页面推广

- [x] 4.1 接入 `cveAbnormal.vue`（`storageKey: 'cve-abnormal'`）

- [x] 4.2 接入 `cveDuplicateReport.vue`（`storageKey: 'cve-duplicate-report'`）

- [x] 4.3 接入 `cveTerm.vue` 超期预警 Tab（`storageKey: 'cve-term-overdue-warning'`）

- [x] 4.4 接入 `cveTerm.vue` 超期告警 Tab（`storageKey: 'cve-term-overdue-alarm'`）


## 5. 漏洞 0Day 模块推广

- [x] 5.1 在 `vulnerabilityView/created.vue` 接入列配置（`storageKey: 'vuln-created'`，表格组件 `vulnTable`）

- [x] 5.2 实现 filter 联动：`query` 对象清除 + `vulnTableRef.initOptions()` + 重查

- [x] 5.3 漏洞名称列通过 `columnSettingDisabled: true` 设为不可取消


