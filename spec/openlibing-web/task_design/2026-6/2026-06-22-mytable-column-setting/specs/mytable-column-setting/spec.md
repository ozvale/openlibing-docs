## ADDED Requirements

### Requirement: Eligibility 判定

系统 MUST 根据列定义自动判定是否展示列配置入口。当列定义中任意项包含 `children` 嵌套时，MUST NOT 展示列配置入口。当列定义为扁平结构且可配置列数量大于 10 时，MUST 展示列配置入口。可配置列 MUST 定义为：具有 `prop` 且不具有 `type`（如 selection、index）的列。

#### Scenario: 扁平列超过 10 列时显示入口

- **WHEN** 页面传入 `CVE_COLUMNS`（约 26 个扁平可配置列，无 children）
- **THEN** 列配置入口 MUST 在 `setting-btns` 区域可见

#### Scenario: 嵌套表头时不显示入口

- **WHEN** 页面传入 `SLO_RATE_COLUMNS`（含 children 分组表头）
- **THEN** 列配置入口 MUST NOT 显示

#### Scenario: 列数不超过 10 时不显示入口

- **WHEN** 页面传入 `TOP20_COLUMNS`（可配置列 ≤ 10）
- **THEN** 列配置入口 MUST NOT 显示

### Requirement: 列显隐配置交互

系统 MUST 提供 Popover 列配置 UI，与导出按钮并列放置。UI MUST 支持全选、半选、恢复默认、取消与确认操作。仅用户点击确认后 MUST 应用列显隐变更；取消 MUST 丢弃未确认的修改。`fixed: true` 或 `columnSettingDisabled: true` 的列 MUST 在配置面板中为 disabled 且不可取消勾选。`type` 列 MUST 始终显示且 MUST NOT 出现在配置面板中。

#### Scenario: 确认后应用列显隐

- **WHEN** 用户在列配置 Popover 中取消勾选若干列并点击确认
- **THEN** 表格 MUST 仅渲染仍勾选的列（及始终显示的 type 列）

#### Scenario: 取消不应用变更

- **WHEN** 用户修改勾选状态后点击取消
- **THEN** 表格列显隐 MUST 保持确认前的状态

#### Scenario: 固定列不可取消

- **WHEN** 列配置面板展示含 `fixed: true` 的列（如 CVE 编号）
- **THEN** 该列 checkbox MUST 为 disabled 且保持勾选

#### Scenario: 业务禁用列不可取消

- **WHEN** 列配置面板展示含 `columnSettingDisabled: true` 的列（如漏洞名称）
- **THEN** 该列 checkbox MUST 为 disabled 且保持勾选

### Requirement: 默认列集与持久化

首次访问（无 localStorage 记录）时，MUST 显示全部可配置列。用户确认列配置后，MUST 将可见列 `prop` 列表持久化到 localStorage，key MUST 包含页面 `storageKey` 与用户 `userId`。用户再次访问同一页面时 MUST 恢复上次确认的列显隐偏好。

#### Scenario: 首次访问全显示

- **WHEN** 用户首次打开 `cveData` 且无 localStorage 记录
- **THEN** 表格 MUST 显示 `CVE_COLUMNS` 中全部可配置列

#### Scenario: 刷新后保持偏好

- **WHEN** 用户已确认隐藏部分列并刷新页面
- **THEN** 表格 MUST 按 localStorage 中保存的 prop 列表渲染可见列

#### Scenario: 多 Tab 页面独立持久化

- **WHEN** 用户在 `cveTerm.vue` 超期预警 Tab 隐藏部分列后切换到超期告警 Tab
- **THEN** 两个 Tab MUST 各自按独立 storageKey 恢复列偏好，互不影响

### Requirement: 隐藏列时清除 filter

当用户确认列配置并隐藏某列时，若该列具有 `filterAble: true`，系统 MUST 从页面 filter 状态对象中移除该列对应的 filter key（`column.filterProp || column.name || column.prop`）。若因此清除了至少一个 filter，系统 MUST 重置分页到第 1 页并重新请求列表数据。系统 MUST 调用表格组件的 `initOptions()` 重置表头 filter dropdown UI。

#### Scenario: 隐藏带 filter 的列后清除筛选

- **WHEN** 用户对「漏洞等级」列应用了 filter 后在列配置中隐藏该列并确认
- **THEN** 对应 filter 条件 MUST 从 filter 状态对象中移除，且列表 MUST 按无该 filter 的条件重新加载

#### Scenario: 隐藏无 filter 的列不影响 filter 状态

- **WHEN** 用户隐藏不具有 `filterAble` 的列并确认
- **THEN** 其他列已应用的 filter MUST 保持不变

#### Scenario: vulnTable filterProp 映射

- **WHEN** 用户在漏洞「已创建」列表对 CVSS 评分列（`filterProp: 'cvssScoreList'`）应用 filter 后隐藏该列并确认
- **THEN** 系统 MUST 从 `query` 对象中删除 `cvssScoreList` 而非 `cvssScore`

### Requirement: 导出行为不变

列显隐配置 MUST NOT 改变导出功能的行为。导出 MUST 继续请求服务端并导出全量字段，与列配置无关。

#### Scenario: 隐藏列后导出仍为全量

- **WHEN** 用户隐藏部分列后点击导出
- **THEN** 导出请求参数与逻辑 MUST 与列配置引入前一致，导出内容 MUST 包含全部字段而非仅可见列

### Requirement: 表格组件无关性

列配置基础设施 MUST 同时适用于 `my-table` 与 `vulnTable` 消费页面，无需修改表格组件内部实现。

#### Scenario: vulnTable 页面接入

- **WHEN** `vulnerabilityView/created.vue` 使用 `useTableColumnSetting` 并将 `visibleColumns` 传给 `vulnTable`
- **THEN** 列配置入口与交互 MUST 与 my-table 页面行为一致
