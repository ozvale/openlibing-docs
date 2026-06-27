## ADDED Requirements

### Requirement: scanIssue 查询接口接受排序参数

`POST /open/scan/scanIssue/query` SHALL 接受可选请求字段 `sortColumn` 和 `sortOrder`，与前端 `gitUrlList.vue` 已透传格式一致。

#### Scenario: 接收匹配度降序参数

- **WHEN** 请求体包含 `sortColumn: "matched"` 和 `sortOrder: "descending"`
- **THEN** 系统按匹配度数值从高到低返回分页结果

#### Scenario: 接收匹配度升序参数

- **WHEN** 请求体包含 `sortColumn: "matched"` 和 `sortOrder: "ascending"`
- **THEN** 系统按匹配度数值从低到高返回分页结果

#### Scenario: 无排序参数

- **WHEN** 请求体不包含 `sortColumn` 或 `sortOrder`
- **THEN** 系统按 `scanFile` 升序返回结果（与改造前行为一致）

### Requirement: 匹配度按数值排序

系统 SHALL 将 `matched` 字段（如 `"90%"`）解析为数值后进行排序，不得按原始字符串字典序排序。

#### Scenario: 百分比字符串正确排序

- **WHEN** 存在 `matched` 值为 `"9%"`、`"80%"`、`"100%"`
- **THEN** 降序排序结果为 `"100%"`、`"80%"`、`"9%"`

#### Scenario: 空值或非法值排末位

- **WHEN** 存在 `matched` 为空、null 或无法解析为数字
- **THEN** 升序时这些记录排在有效数值之前（视为 -1.0）
- **THEN** 降序时这些记录排在有效数值之后

### Requirement: 排序在分页之前执行

排序 MUST 在 MongoDB 分页（skip/limit）之前完成，确保全量数据范围内的分页顺序正确。

#### Scenario: 第二页数据顺序正确

- **WHEN** 用户请求 `pageNo: 2`、`pageSize: 10` 且 `sortColumn: "matched"`、`sortOrder: "descending"`
- **THEN** 返回结果为全量降序结果的第 11–20 条，而非仅对当前页 10 条本地排序

### Requirement: 排序参数白名单校验

系统 MUST 通过白名单校验 `sortColumn`，禁止任意字段注入 Mongo 排序。

#### Scenario: 非法 sortColumn

- **WHEN** 请求体 `sortColumn` 不在白名单（如 `"__proto__"` 或未知列名）
- **THEN** 系统忽略排序参数，回退为 `scanFile` 升序默认行为

#### Scenario: 非法 sortOrder

- **WHEN** `sortColumn` 合法但 `sortOrder` 不是 `ascending` 或 `descending`
- **THEN** 系统回退为 `scanFile` 升序默认行为

### Requirement: 排序不影响总数统计

`total` 计数 SHALL 与排序无关，仅基于筛选条件。

#### Scenario: count 与 list 筛选一致

- **WHEN** 带筛选条件和排序参数查询
- **THEN** 响应 `total` 等于满足筛选条件的记录总数
- **THEN** `list` 长度为 `min(pageSize, total - (pageNo-1)*pageSize)` 或 0
