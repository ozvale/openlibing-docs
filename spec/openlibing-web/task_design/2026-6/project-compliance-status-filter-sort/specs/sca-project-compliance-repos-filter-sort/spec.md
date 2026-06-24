## ADDED Requirements

### Requirement: 项目合规任务状态列表头展示筛选入口

项目合规表格（`projectCompliance`）的「任务状态」列 SHALL 在表头展示 `filterDropdown` 筛选控件，选项包含：成功（`success`）、失败（`fail`）。

#### Scenario: 用户打开任务状态筛选下拉

- **WHEN** 用户在项目合规表格点击「任务状态」列表头的筛选图标
- **THEN** 系统展示包含「成功」「失败」两个可勾选项的下拉面板
- **AND** 面板提供搜索框、全选、筛选与重置按钮

#### Scenario: 有选中项时筛选图标高亮

- **WHEN** 用户已勾选至少一个任务状态且尚未重置
- **THEN** 表头筛选图标以高亮颜色（`#409eff`）显示

### Requirement: 任务状态筛选确认触发服务端列表刷新

用户点击「筛选」后，系统 SHALL 将选中状态值作为 `repoResult` 查询参数附加到 `GET license/repos` 请求，并将页码重置为第 1 页后重新加载表格数据。

#### Scenario: 单选任务状态筛选

- **WHEN** 用户仅勾选「失败」并点击「筛选」
- **THEN** 系统请求 `license/repos` 时携带 `repoResult=fail`
- **AND** 表格展示接口返回的当前页数据
- **AND** `pageNo` 重置为 1

#### Scenario: 多选任务状态筛选

- **WHEN** 用户勾选「成功」与「失败」并点击「筛选」
- **THEN** 系统请求 `license/repos` 时携带 `repoResult=success,fail`（逗号分隔多值）

#### Scenario: 重置任务状态筛选

- **WHEN** 用户在下拉面板点击「重置」
- **THEN** 系统清除本地 `repoResult` 筛选条件
- **AND** 后续 `license/repos` 请求不再携带 `repoResult` 参数
- **AND** 页码重置为 1 并刷新列表

### Requirement: 项目合规表格支持服务端自定义排序

项目合规表格中标记为可排序的列（`scanTime`、`fileNum`、`compatibilityNumber`、`incompatibleNumber`、`unrecognizedNumber`）SHALL 使用 `sortable: 'custom'`，排序变更时向 `license/repos` 透传 `sortColumn` 与 `sortOrder` 并重新请求全量分页数据。

#### Scenario: 按最新扫描时间降序排序

- **WHEN** 用户点击「最新扫描时间」列排序为降序
- **THEN** 系统请求 `license/repos` 时携带 `sortColumn=scanTime` 与 `sortOrder=descending`
- **AND** 表格展示服务端返回的排序后当前页数据

#### Scenario: 按文件总数升序排序

- **WHEN** 用户点击「文件总数」列排序为升序
- **THEN** 系统请求携带 `sortColumn=fileNum` 与 `sortOrder=ascending`

#### Scenario: 嵌套列合规数排序

- **WHEN** 用户点击「合规数」嵌套列排序
- **THEN** 系统请求携带 `sortColumn=compatibilityNumber` 与对应的 `sortOrder`

#### Scenario: 取消排序

- **WHEN** 用户第三次点击同一排序列取消排序
- **THEN** 系统清空 `sortColumn`/`sortOrder` 或不再透传排序参数
- **AND** 列表恢复默认顺序

### Requirement: 筛选与排序可叠加

在已设置任务状态筛选的条件下，用户仍 SHALL 能够对支持排序的列执行自定义排序，请求同时携带 `repoResult`、`sortColumn`、`sortOrder`。

#### Scenario: 筛选失败后按扫描时间排序

- **WHEN** 用户已筛选「失败」状态
- **AND** 用户点击「最新扫描时间」列排序
- **THEN** 系统请求同时包含 `repoResult=fail`、`sortColumn=scanTime`、`sortOrder`
- **AND** 返回结果在失败状态集合内按指定顺序排列

### Requirement: 上下文切换时清空筛选与排序状态

当用户切换社区、平台、代码仓或 Tab（`activeName`）时，系统 SHALL 清空项目合规的 `repoResult` 筛选条件、排序状态，并重建筛选下拉组件。

#### Scenario: 切换社区清空筛选与排序

- **WHEN** `chooseCommunityValue` 发生变化
- **THEN** 系统清空 `repoResult` 筛选条件与 `sortParams`
- **AND** 项目合规表格排序指示器恢复默认
- **AND** 列表按新社区重新加载（不带 `repoResult` 与排序参数）

#### Scenario: 切换到开源 Tab 不应用项目合规筛选

- **WHEN** 用户从「项目合规」切换到「开源片段引用合规」
- **THEN** 项目合规的 `repoResult` 筛选状态被清空
- **AND** 开源表格使用独立的 `scanResult` 筛选逻辑

### Requirement: 任务状态展示与交互值域一致

项目合规表格 SHALL 以 `success`/`fail` 作为任务状态展示与失败原因弹窗的判断依据，与 `repoResult` 后端字段值域一致。

#### Scenario: 展示成功状态

- **WHEN** 行数据 `scanResult`（映射自 `repoResult`）为 `success`
- **THEN** 单元格展示「成功」及成功样式
- **AND** 点击不弹出错误原因对话框

#### Scenario: 展示失败状态并可查看原因

- **WHEN** 行数据 `scanResult` 为 `fail`
- **THEN** 单元格展示「失败」及失败样式
- **AND** 用户点击可打开错误原因对话框

### Requirement: 未筛选未排序时保持现网兼容

未设置任务状态筛选且未自定义排序时，系统 SHALL 保持与变更前一致的 `license/repos` 请求参数与列表行为。

#### Scenario: 默认加载项目合规列表

- **WHEN** 用户进入项目合规 Tab 且未操作筛选或排序
- **THEN** `license/repos` 请求不包含 `repoResult`、`sortColumn`、`sortOrder` 参数
- **AND** 列表数据与分页行为与变更前一致
