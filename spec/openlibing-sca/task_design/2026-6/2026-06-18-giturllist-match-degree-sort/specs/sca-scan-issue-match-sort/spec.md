## ADDED Requirements

### Requirement: 匹配度列支持服务端排序

开源片段引用合规表格（`openSourceCompliance`）的「匹配度」列 SHALL 支持用户通过列头触发服务端分页排序。

#### Scenario: 按匹配度降序排序

- **WHEN** 用户点击「匹配度」列头选择降序
- **THEN** 系统将 `pageNo` 重置为 1
- **THEN** 系统向 `POST /open/scan/scanIssue/query` 发送请求，请求体包含 `sortColumn: "matched"` 和 `sortOrder: "descending"`
- **THEN** 表格展示接口返回的当前页数据

#### Scenario: 按匹配度升序排序

- **WHEN** 用户点击「匹配度」列头选择升序
- **THEN** 系统将 `pageNo` 重置为 1
- **THEN** 请求体包含 `sortColumn: "matched"` 和 `sortOrder: "ascending"`

#### Scenario: 取消匹配度排序

- **WHEN** 用户第三次点击「匹配度」列头取消排序
- **THEN** 系统清除 `sortColumn` 和 `sortOrder`，不再向接口传递排序参数
- **THEN** 系统将 `pageNo` 重置为 1 并重新请求列表

#### Scenario: 翻页保留排序

- **WHEN** 用户已设置匹配度降序且当前在第 2 页
- **THEN** 用户切换到第 3 页
- **THEN** 请求仍携带 `sortColumn: "matched"` 和 `sortOrder: "descending"`，仅 `pageNo` 变更

#### Scenario: 筛选条件变更保留排序

- **WHEN** 用户已设置匹配度排序并修改筛选条件
- **THEN** 系统将 `pageNo` 重置为 1
- **THEN** 请求同时携带当前筛选参数与排序参数

#### Scenario: 切换扫描任务重置排序

- **WHEN** 用户切换到不同的 scanId（代码仓扫描任务）
- **THEN** 系统清除排序状态
- **THEN** 新任务的首屏请求不携带排序参数

### Requirement: 排序参数与项目约定一致

排序请求参数命名和取值 SHALL 与 SCA 模块现有服务端排序约定（如 `communityList.vue`）保持一致。

#### Scenario: 参数格式

- **WHEN** 系统发送带排序的 scanIssue 查询
- **THEN** 使用字段名 `sortColumn`（值为列 prop，如 `"matched"`）和 `sortOrder`（值为 `"ascending"` 或 `"descending"`）
- **THEN** 不使用 `sortField`/`sortType` 或其他命名

### Requirement: 排序范围限定

本次排序能力 SHALL 仅作用于 `openSourceCompliance` Tab 的 issue 列表，且仅「匹配度」列可排序。

#### Scenario: 其他 Tab 不受影响

- **WHEN** 用户处于 `projectCompliance` Tab
- **THEN** 表格不展示匹配度排序交互
- **THEN** `licenseIssue/query` 请求不携带 scanIssue 排序参数

#### Scenario: 非匹配度列不可排序

- **WHEN** 用户查看 `openSourceCompliance` 表格
- **THEN** 除「匹配度」外的列不显示排序控件
