# validate-product-name

## 需求背景
发布评审单的产品名称（productName）字段当前仅有 `@NotBlank` 非空校验，允许输入纯数字（如 "1"）、单字符等明显不合理的名称，影响数据质量和后续流程。

## 功能描述
- 在创建和修改发布评审单时，对 productName 字段增加基本格式校验
- 拒绝纯数字、过短（少于2个字符）、仅含特殊字符的产品名称
- 不修改数据库 schema、不修改前端、不影响已有评审单数据

## 验收标准
- [ ] 纯数字产品名称（如 "1"、"123"）被拒绝，返回明确错误信息
- [ ] 过短的产品名称（少于2个字符）被拒绝
- [ ] 仅含特殊字符的产品名称被拒绝
- [ ] 合理的产品名称（如 "openlibing-platform-release"、"产品A"）正常通过
- [ ] 创建和修改评审单两个入口都需校验
- [ ] 有对应的单元测试

## 影响范围
- `ReleaseReviewDTO` — 增加校验注解或校验逻辑
- `ReleaseBaseServiceImpl` — createReleaseReview / updateReleaseReview 方法增加校验
- `ReleaseBaseServiceImplTest` — 增加校验相关测试
