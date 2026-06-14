## ADDED Requirements

### Requirement: open/scan/repos 支持 scanResult 查询参数

`GET /open/scan/repos` SHALL 接受可选 query 参数 `scanResult`，值为逗号分隔的任务状态字符串。合法状态值为 `1`（成功）、`-1`（失败）、`0`（执行中）。未传该参数时，接口行为 MUST 与变更前一致。

#### Scenario: 未传 scanResult 保持现网行为

- **WHEN** 客户端请求 `open/scan/repos` 且不包含 `scanResult` 参数
- **THEN** 返回的 `list` 与 `total` 与变更前逻辑一致

#### Scenario: 单值筛选失败状态

- **WHEN** 客户端请求携带 `scanResult=-1`
- **THEN** 返回的 `list` 中每条记录的 `scanResult` 均为 `-1`
- **AND** `total` 等于满足条件的记录总数

#### Scenario: 多值筛选成功与执行中

- **WHEN** 客户端请求携带 `scanResult=1,0`
- **THEN** 返回的 `list` 中每条记录的 `scanResult` 为 `1` 或 `0`
- **AND** `total` 等于满足任一选中状态的记录总数

### Requirement: 筛选在排序与分页之前执行

服务端 SHALL 先按 `scanResult` 过滤完整列表，再应用 `sortColumn`/`sortOrder` 排序，最后按 `pageNo`/`pageSize` 分页。

#### Scenario: 筛选后分页

- **WHEN** 客户端携带 `scanResult=-1`、`pageNo=1`、`pageSize=10`
- **AND** 社区内失败状态记录共 25 条
- **THEN** 响应 `total` 为 25
- **AND** 响应 `list` 最多包含 10 条失败记录

#### Scenario: 筛选与自定义排序叠加

- **WHEN** 客户端同时携带 `scanResult=1`、`sortColumn=scanTime`、`sortOrder=descending`
- **THEN** 返回的 `list` 仅含成功状态记录
- **AND** 记录按扫描时间降序排列

### Requirement: 社区汇总字段不受 scanResult 筛选影响

响应中的 `totalCount`（社区告警总数）与 `riskCount`（社区待处理告警总数）SHALL 不因 `scanResult` 筛选而改变，保持社区级汇总语义。

#### Scenario: 筛选后汇总字段不变

- **WHEN** 客户端携带 `scanResult=-1` 请求列表
- **THEN** 响应 `totalCount` 与 `riskCount` 与未筛选时相同

### Requirement: scanResult 不参与 Redis 列表缓存 key

不同 `scanResult` 筛选值 SHALL 复用同一社区列表缓存；筛选 MUST 在缓存数据读取之后于内存中执行。

#### Scenario: 相同社区不同 scanResult 共用缓存

- **WHEN** 同一 `community`、`platform`、`repositoryType` 下先后请求 `scanResult=1` 与 `scanResult=-1`
- **THEN** 两次请求使用相同的 Redis 列表缓存 key（不含 scanResult）
- **AND** 各自返回对应状态的过滤结果
