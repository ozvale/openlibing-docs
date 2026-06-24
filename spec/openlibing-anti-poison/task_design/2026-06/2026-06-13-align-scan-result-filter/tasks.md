## 1. 后端 ParamModel 与工具方法

- [x] 1.1 在 `ParamModel` 新增 `Integer isSuccess`、`Integer isPass` 字段及 JavaDoc（`0`=失败/未通过语义对应 false，`1`=成功/通过对应 true）
- [x] 1.2 在 `ScanResultDetailOperation` 新增 `applySuccessPassFilter(Criteria, ParamModel)` 私有方法，将 `0`/`1` 映射为 Mongo `is_success`/`is_pass` 布尔条件

## 2. 查询层筛选实现

- [x] 2.1 在 `getScanResult` 构建 Criteria 时调用 `applySuccessPassFilter`
- [x] 2.2 在 `getScanPRResultGroup` 聚合管道初始 `$match` 的 Criteria 中调用 `applySuccessPassFilter`（位于 `$group` 之前）
- [x] 2.3 确认 `ProblemShieldServiceImpl` 分页 count 查询复用同一 Operation 方法，筛选后 count 正确

## 3. 单元测试

- [x] 3.1 为 `applySuccessPassFilter` 或 `getScanResult` 补充单测：`isSuccess=1/0`、未传参、`isPass=1/0`、组合条件
- [x] 3.2 为 `getScanPRResultGroup` 补充单测：验证 `$match` 含 `is_success`/`is_pass` 条件（可 mock `MongoTemplate.aggregate`）
- [x] 3.3 更新/新增 `ParamModelTest` 覆盖新字段序列化

