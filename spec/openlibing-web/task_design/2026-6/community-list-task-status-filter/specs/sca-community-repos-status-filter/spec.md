## ADDED Requirements

### Requirement: 任务状态列表头展示筛选入口

开源片段引用合规表格（`openSourceCompliance`）的「任务状态」列 SHALL 在表头展示 `filterDropdown` 筛选控件，选项包含：成功（`1`）、失败（`-1`）、执行中（`0`）。

#### Scenario: 用户打开任务状态筛选下拉

- **WHEN** 用户在风险数据看板表格点击「任务状态」列表头的筛选图标
- **THEN** 系统展示包含「成功」「失败」「执行中」三个可勾选项的下拉面板
- **AND** 面板提供搜索框、全选、筛选与重置按钮

#### Scenario: 有选中项时筛选图标高亮

- **WHEN** 用户已勾选至少一个任务状态且尚未重置
- **THEN** 表头筛选图标以高亮颜色（`#409eff`）显示

### Requirement: 筛选确认触发服务端列表刷新

用户点击「筛选」后，系统 SHALL 将选中状态值作为 `scanResult` 查询参数附加到 `GET open/scan/repos` 请求，并将页码重置为第 1 页后重新加载表格数据。

#### Scenario: 单选任务状态筛选

- **WHEN** 用户仅勾选「失败」并点击「筛选」
- **THEN** 系统请求 `open/scan/repos` 时携带 `scanResult=-1`（或等价单值格式）
- **AND** 表格展示接口返回的当前页数据
- **AND** `pageNo` 重置为 1

#### Scenario: 多选任务状态筛选

- **WHEN** 用户勾选「成功」与「执行中」并点击「筛选」
- **THEN** 系统请求 `open/scan/repos` 时携带 `scanResult=1,0`（逗号分隔多值）
- **AND** 表格展示符合任一选中状态的记录

#### Scenario: 重置任务状态筛选

- **WHEN** 用户在下拉面板点击「重置」
- **THEN** 系统清除本地 `scanResult` 筛选条件
- **AND** 后续 `open/scan/repos` 请求不再携带 `scanResult` 参数
- **AND** 页码重置为 1 并刷新列表

### Requirement: 上下文切换时清空筛选状态

当用户切换社区、平台、代码仓或 Tab（`activeName`）时，系统 SHALL 清空任务状态筛选条件并重建筛选下拉组件，避免展示与当前上下文不一致的选中态。

#### Scenario: 切换社区清空筛选

- **WHEN** `chooseCommunityValue` 发生变化
- **THEN** 系统清空 `scanResult` 筛选条件
- **AND** 任务状态筛选下拉恢复为未选中状态
- **AND** 列表按新社区重新加载（不带 `scanResult`）

#### Scenario: 切换到项目合规 Tab 不应用开源筛选

- **WHEN** 用户从「开源片段引用合规」切换到「项目合规」
- **THEN** 开源表格的 `scanResult` 筛选状态被清空
- **AND** 项目合规表格不受该筛选影响

### Requirement: 筛选与排序可叠加

在已设置任务状态筛选的条件下，用户仍 SHALL 能够对支持排序的列执行自定义排序，请求同时携带 `sortColumn`、`sortOrder` 与 `scanResult`。

#### Scenario: 筛选后按扫描时间排序

- **WHEN** 用户已筛选「失败」状态
- **AND** 用户点击「最新扫描时间」列排序
- **THEN** 系统请求同时包含 `scanResult=-1`、`sortColumn`、`sortOrder`
- **AND** 返回结果在失败状态集合内按指定顺序排列

### Requirement: 未筛选时保持现网兼容

未设置任务状态筛选时，系统 SHALL 保持与变更前一致的 `open/scan/repos` 请求参数与列表行为。

#### Scenario: 默认加载列表

- **WHEN** 用户进入页面且未操作任务状态筛选
- **THEN** `open/scan/repos` 请求不包含 `scanResult` 参数
- **AND** 列表数据与分页行为与变更前一致
