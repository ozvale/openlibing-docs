## ADDED Requirements

### Requirement: 表头列配置持久化存储

SCA 软件信息页（`gitUrlList.vue`）的表头列配置（`clunmLists`）MUST 持久化到 `localStorage`，不得使用 `sessionStorage`。持久化目的为跨浏览器会话保留用户的列显隐偏好，避免关闭标签页后缓存丢失。

- 持久化 key：`clunmLists`
- 持久化 value：可见列 `id` 的逗号分隔字符串（`Array.prototype.join(',')`）
- 读取时机：组件 `created` 钩子调用 `updateSelectList()` 时，以及 Popover `@show` 触发 `updateSelectList()` 时
- 写入时机：用户点击「确认」按钮触发 `updateShowCulomList()` 时

#### Scenario: 首次访问无缓存时使用默认列配置

- **WHEN** 用户首次访问软件信息页，且 `localStorage` 中不存在 `clunmLists` 键
- **THEN** `updateSelectList()` MUST 将 `lts` 解析为空数组 `[]`
- **AND** 表格 MUST 按 `table.column` 中各列的 `show` 默认值渲染可见列
- **AND** `checkedList` MUST 包含所有 `show` 为 `true` 的列 `id`

#### Scenario: 关闭标签页后再次访问恢复列配置

- **WHEN** 用户曾在软件信息页确认过列配置（`localStorage.clunmLists` 已写入），关闭浏览器标签页后再次打开页面
- **THEN** `updateSelectList()` MUST 从 `localStorage.getItem('clunmLists')` 读取缓存值
- **AND** MUST 通过 `.split(',')` 解析为列 `id` 数组
- **AND** 表格 MUST 仅渲染 `id` 出现在解析数组中的列为可见（`show = true`），其余列 `show = false`
- **AND** `checkedList` MUST 与解析数组保持一致

#### Scenario: 确认列配置后写入 localStorage

- **WHEN** 用户在列配置 Popover 中修改勾选项并点击「确认」按钮
- **THEN** `updateShowCulomList()` MUST 遍历 `table.column`，根据 `checkedList` 更新各列 `show` 状态
- **AND** MUST 将所有 `show` 为 `true` 的列 `id` 收集到 `columnList` 数组
- **AND** MUST 调用 `localStorage.setItem('clunmLists', columnList)` 写入缓存（隐式调用数组的 `toString` 形成逗号分隔字符串）
- **AND** Popover MUST 关闭（`tebelHeaderSelectVisible = false`）

#### Scenario: 取消不写入缓存

- **WHEN** 用户修改勾选状态后点击「取消」按钮或关闭图标
- **THEN** `cancelUpdateTabelHeader()` MUST 仅关闭 Popover（`tebelHeaderSelectVisible = false`）
- **AND** MUST NOT 调用 `localStorage.setItem`
- **AND** 表格列显隐 MUST 保持确认前的状态（未应用的修改被丢弃）

### Requirement: 列配置项不可少于最小数量

列配置 Popover 中的 `el-checkbox-group` MUST 设置 `:min="5"`，用户已勾选项少于 5 时 MUST 禁止取消勾选，避免表格因列过少而不可用。

#### Scenario: 勾选数等于最小值时禁止取消

- **WHEN** 用户已勾选 5 个列，并尝试取消其中一项
- **THEN** 该 checkbox MUST 保持勾选状态（由 `el-checkbox-group` 的 `min` 属性强制）
- **AND** `checkedList` 长度不得小于 5

### Requirement: 固定列在配置面板中禁用

`table.column` 中 `disabled: true` 的列（如「文件名」「是否兼容」）MUST 在列配置 Popover 中呈现为 disabled checkbox，且 MUST 始终保持勾选状态，不得被用户取消。

#### Scenario: 固定列 checkbox 禁用且勾选

- **WHEN** 列配置 Popover 展示，某列的 `disabled` 为 `true`
- **THEN** 该列对应的 `el-checkbox` MUST 渲染为 disabled 状态
- **AND** 该列 `id` MUST 始终存在于 `checkedList` 中
- **AND** 用户点击全选/取消全选时，disabled 列 MUST 始终保留在 `checkedList` 中

#### Scenario: 全选/取消全选保留 disabled 列

- **WHEN** 用户点击「全选」checkbox 取消全选
- **THEN** `handleCheckAllChange(false)` MUST 将 `checkedList` 设为 `selectList` 中所有 `disabled: true` 项的 `id` 数组
- **AND** disabled 列 MUST NOT 被取消勾选
- **WHEN** 用户点击「全选」checkbox 选中全选
- **THEN** `handleCheckAllChange(true)` MUST 将 `checkedList` 设为 `selectList` 中所有项的 `id` 数组

### Requirement: 全选与半选状态同步

列配置 Popover 顶部的「全选」checkbox MUST 通过 `checkAll` 与 `isIndeterminate` 反映当前勾选状态：

- 勾选数等于 `selectList.length` 时，`checkAll = true`，`isIndeterminate = false`
- 勾选数大于 0 且小于 `selectList.length` 时，`checkAll = false`，`isIndeterminate = true`
- 勾选数为 0 时，`checkAll = false`，`isIndeterminate = false`（受 `:min="5"` 约束，实际场景不应发生）

#### Scenario: 勾选状态变化时更新全选指示

- **WHEN** 用户在 `el-checkbox-group` 中改变勾选项（触发 `handleCheckedTabelChange`）
- **THEN** 系统 MUST 根据当前 `checkedList` 长度与 `selectList.length` 比较
- **AND** 相等时设置 `checkAll = true`、`isIndeterminate = false`
- **AND** 不相等且非零时设置 `checkAll = false`、`isIndeterminate = true`

### Requirement: 列配置 Popover 触发时初始化勾选状态

用户点击「列配置」按钮触发 Popover 显示时，MUST 通过 `@show` 事件调用 `updateSelectList()` 重新从 `localStorage` 读取缓存并初始化 `checkedList`，确保 Popover 打开时勾选状态与最新持久化数据一致。

#### Scenario: 打开 Popover 时同步最新缓存

- **WHEN** 用户点击「列配置」按钮，Popover `@show` 事件触发
- **THEN** `updateSelectList()` MUST 清空 `checkedList`
- **AND** MUST 从 `localStorage.getItem('clunmLists')` 读取最新值并 split 为数组
- **AND** MUST 遍历 `table.column`，将缓存中存在的列 `id` 对应列 `show` 设为 `true` 并加入 `checkedList`
- **AND** 缓存中不存在的列 `id` 对应列 `show` 设为 `false`
- **AND** 当缓存为空（无 `clunmLists` 键或解析为空）时，MUST 按 `table.column` 中各列 `show` 默认值初始化 `checkedList`

### Requirement: 列标识使用 id 字段

列配置中的列标识 MUST 使用 `table.column` 中每项的 `id` 字段（字符串），不得使用 `prop`、`label` 或其他字段。`localStorage` 中持久化的字符串 MUST 为 `id` 数组的逗号分隔形式。

#### Scenario: 持久化值格式

- **WHEN** 用户确认列配置，可见列为 `id` 为 `fileName`、`compatible`、`license` 的三列
- **THEN** `localStorage.getItem('clunmLists')` MUST 返回字符串 `"fileName,compatible,license"`
- **AND** 读取时通过 `split(',')` 还原为数组 `['fileName', 'compatible', 'license']`
