## ADDED Requirements

### Requirement: license/repos 支持按 repoResult 筛选

`GET /license/repos` SHALL 接受可选 query 参数 `repoResult`（逗号分隔多值），按 `LicenseInfoVO.repoResult` 对社区 License 仓库列表做内存过滤。

#### Scenario: 未传 repoResult 时返回全量

- **WHEN** 客户端请求 `license/repos` 且不携带 `repoResult` 参数
- **THEN** 系统返回与变更前一致的全量去重列表（经 stats 填充与 removeIf 后）
- **AND** 响应 `total` 为处理后列表条数

#### Scenario: 单值筛选失败状态

- **WHEN** 客户端请求携带 `repoResult=fail`
- **THEN** 响应 `list` 中每条记录的 `repoResult` 均为 `fail`
- **AND** 响应 `total` 等于过滤后条数

#### Scenario: 多值筛选成功与失败

- **WHEN** 客户端请求携带 `repoResult=success,fail`
- **THEN** 响应 `list` 包含 `repoResult` 为 `success` 或 `fail` 的记录
- **AND** 不包含 `repoResult` 为 null 或不匹配值的记录

#### Scenario: 无匹配记录

- **WHEN** 客户端请求携带 `repoResult` 但无记录匹配
- **THEN** 响应 `list` 为空数组
- **AND** 响应 `total` 为 0

### Requirement: license/repos 支持服务端自定义排序

`GET /license/repos` SHALL 接受可选 query 参数 `sortColumn` 与 `sortOrder`，对全量处理后的列表做内存排序后再分页。

#### Scenario: 按 scanTime 降序排序

- **WHEN** 客户端请求携带 `sortColumn=scanTime` 与 `sortOrder=descending`
- **THEN** 响应 `list` 按 `licenseCreateTime` 降序排列
- **AND** 分页基于排序后全量列表

#### Scenario: 按 fileNum 升序排序

- **WHEN** 客户端请求携带 `sortColumn=fileNum` 与 `sortOrder=ascending`
- **THEN** 响应 `list` 按 MongoDB 统计填充后的 `fileNum` 升序排列

#### Scenario: 嵌套统计列排序

- **WHEN** 客户端请求携带 `sortColumn=compatibilityNumber`（或 `incompatibleNumber`、`unrecognizedNumber`）及有效 `sortOrder`
- **THEN** 系统按对应字段对全量列表排序后分页返回

#### Scenario: 无排序参数时使用默认排序

- **WHEN** 客户端未携带 `sortColumn` 或 `sortOrder`
- **THEN** 系统按 `licenseCreateTime` 降序作为默认排序
- **AND** 分页基于默认排序后的列表

#### Scenario: 非法 sortColumn 忽略自定义排序

- **WHEN** 客户端携带不在白名单内的 `sortColumn`
- **THEN** 系统回退至默认排序（`licenseCreateTime` 降序）

### Requirement: 筛选与排序可叠加且分页正确

系统 SHALL 支持 `repoResult` 筛选与 `sortColumn`/`sortOrder` 同时使用，并在排序前完成全量 MongoDB 统计填充。

#### Scenario: 筛选失败后按扫描时间排序

- **WHEN** 客户端请求同时携带 `repoResult=fail`、`sortColumn=scanTime`、`sortOrder=descending` 及分页参数
- **THEN** 系统先在失败状态集合内排序
- **AND** 再按 `pageNo`/`pageSize` 返回对应页
- **AND** `total` 为筛选后全量条数

#### Scenario: 翻页保持排序

- **WHEN** 客户端在已排序状态下请求 `pageNo=2`
- **THEN** 系统返回排序后全量列表的第 2 页数据
- **AND** `total` 不变

### Requirement: 向后兼容现有查询参数

`GET /license/repos` 在新增参数之外 SHALL 继续支持 `community`、`pageNo`、`pageSize`、`platform`、`repository` 等现有 query 参数。

#### Scenario: 现有 platform/repository 过滤仍生效

- **WHEN** 客户端携带 `platform` 或 `repository` 参数
- **THEN** SQL 层过滤行为与变更前一致
- **AND** repoResult 筛选与排序在 SQL 结果之上后置处理
