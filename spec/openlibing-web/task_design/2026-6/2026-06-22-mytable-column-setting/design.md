## Context

`my-table`（`components/myTable.vue`）通过 `columns` prop 声明式渲染 `el-table-column`，支持 `filterAble` 表头筛选、嵌套 `children` 多级表头、`type: selection/index` 特殊列等。CVE 模块约 22 处使用 `<my-table>`，列定义集中在 `views/cve/columns.js`。

漏洞 0Day 模块使用 `vulnTable.vue`，filter key 通过 `filterProp` 声明，与 my-table 的 `name` 字段机制不同。

项目内已有三套列配置实现（`branches.vue` 内联、`TableSetting.vue` + Pinia、`SCA` 内联 + sessionStorage），互不通用。本次抽取第四套，收敛为可复用模块。

**已确认产品约束：**

1. 列配置 UI 与导出并列（`setting-btns`）
2. 含 `children` 嵌套表头的表格不提供列配置
3. 隐藏列时自动清除对应 filter
4. 导出保持全量列（服务端）
5. 默认全显示

## Goals / Non-Goals

**Goals:**

- 提供可复用的列显隐配置（工具函数 + Composable + UI 组件）
- 自动判定页面是否 eligible（扁平列 > 10、无嵌套）
- 按用户 + 页面维度 localStorage 持久化
- 列配置确认时联动清除 hidden 列的 filter 并重置 dropdown UI
- 以 `cveData.vue` 为试点，推广至 CVE 与漏洞 0Day eligible 页面

**Non-Goals:**

- 不修改 `my-table.vue` / `vulnTable.vue` 内部实现
- 不支持嵌套列的组级/叶子级配置
- 不支持列顺序拖拽
- 不改变导出行为与后端接口
- 不统一改造 TableSetting / branches / SCA 历史实现
- 不使用 Pinia 持久化（会话级存储不满足需求）

## Decisions

### D1：页面侧集成，不改表格组件

**选择：** Composable + 独立 `TableColumnSetting` 组件，页面传 `:columns="visibleColumns"` 给 `my-table` 或 `vulnTable`。

**理由：** 表格组件无统一工具栏，CVE 各页 `tableTop` 布局差异大；内嵌列配置会与导出按钮位置冲突。

**备选：** 在表格组件内建列配置 — rejected，职责膨胀且 UI placement 不可控。

### D2：Eligibility 运行时判定

**选择：** `isColumnSettingEligible(columns)` — 任意项含 `children` 则 false；否则统计可配置列（有 `prop`、无 `type`），> 10 则 true。

**理由：** 避免维护页面白名单；嵌套列页面自动排除。

### D3：列标识与 filter key 分离

**选择：**

- 列显隐 key：`column.prop`（表格渲染与 columns 过滤依据）
- Filter 清除 key：`column.filterProp || column.name || column.prop`（与 filter-dropdown / vulnTable 的 filter 字段一致）

**理由：** CVE 列定义中 `affectedBranches` 的 filter name 为 `affectedBranchesList`；漏洞列使用 `filterProp`（如 `cveNameList`），二者均与 `prop` 不一致。

### D4：持久化 localStorage

**选择：** Key 格式 `mytable_column_{storageKey}_{userId}`，值为 `prop[]` JSON。

**理由：** 与 `branches.vue` 一致，跨会话保留；Pinia 仅内存不满足。

**默认：** 无存储或解析失败 → 全部可配置列可见（`getDefaultVisibleKeys` + `normalizeVisibleKeys` 兜底）。

### D5：不可取消列规则

**选择：**

- `type` 列（selection/index）：始终显示，不出现在配置面板
- `fixed: true` 或 `columnSettingDisabled: true` 列：面板中 `disabled`，不可取消

**理由：** 与 CVE 固定列（CVE 编号、Issue ID）、漏洞「漏洞名称」列及 repair 详情 selection 列一致。

### D6：Filter 联动流程

**选择：** 用户点击「确认」后：

1. `confirmSetting()` 调用 `getClearedFilterKeys` 对比新旧 visibleKeys，找出被隐藏且 `filterAble` 的列
2. 从页面 filter 对象 delete 对应 filterKey
3. 调用 `$refs.table.initOptions()` 清空所有 dropdown（my-table / vulnTable 均有此能力）
4. 若有 filter 被清除 → 页码置 1 + 重新请求数据

**理由：** 避免「列已隐藏但数据仍被过滤」的幽灵状态。

### D7：UI 交互

**选择：** 对齐 `branches.vue` — Popover、checkbox 三列网格、全选/半选、恢复默认、取消/确认（确认才生效）。

**理由：** 项目内最新、交互最完整的列配置参考。

### D8：vulnTable 复用

**选择：** 同一套 `tableColumnSetting.js` + `useTableColumnSetting` + `TableColumnSetting`，页面侧 `@confirm` 回调调用 `vulnTableRef.initOptions()`。

**理由：** 列定义结构与 my-table 兼容（prop / filterAble / filterProp），无需 fork 组件。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| `initOptions()` 清空所有 filter dropdown，不仅是 hidden 列 | 可接受：确认列配置后用户预期为「应用新视图」；visible 列 filter 需重新选择 |
| 多 Tab 页面 storageKey 冲突 | 每 Tab/表格独立 `storageKey`（如 `cve-term-overdue-warning`） |
| Options API 页面（cveData）与 Composition API 混用 | Composable 可在 setup 中调用，spread 返回值到 setup return |
| `columns.js` 未标 `defaultVisible` | 默认全显示，与产品决策一致 |
| localStorage 配额或隐私模式失败 | try/catch 静默降级，仍可用但不持久化 |

## Migration Plan

1. **Phase 1** ✅：新增基础设施（utils + composable + 组件）
2. **Phase 2** ✅：`cveData.vue` 试点接入
3. **Phase 3** ✅：`cveRepair.vue`、`cveAbnormal.vue`、`cveDuplicateReport.vue`、`cveTerm.vue`（双 Tab）推广
4. **Phase 3b** ✅：`vulnerabilityView/created.vue`（vulnTable）接入
5. **Phase 4** 🔄：扫描其余 eligible 页面批量接入（`cveStock`、`cvePendingReport` 等）
6. **Phase 5** ⏳：lint / 单元测试 / 手动验收 / 归档

**回滚：** 移除页面侧 `TableColumnSetting` 与 composable 调用，恢复 `:columns="原始列集"` 即可；localStorage key 可保留不影响。

## Open Questions

（无。产品五条决策已在 explore 阶段确认。）
