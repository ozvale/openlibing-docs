# validate-product-name — 技术设计

## 方案概述

在 ReleaseBaseServiceImpl 中新增私有校验方法 validateProductName，在创建和修改发布评审单的入口处调用，拒绝不合理的产品名称。

## 架构决策

- **校验位置选择**：在 Service 层而非 DTO 注解层实现校验
  - 原因：校验规则涉及多条件组合判断（长度 + 纯数字 + 字符类型），自定义注解实现过于复杂，Service 层私有方法更清晰易维护
  - 校验失败返回 `DataResult.failureMessage()`，与现有校验模式一致

- **校验规则设计**：
  1. 非空检查（兜底，DTO 层已有 @NotBlank）
  2. trim 后长度 ≥ 2（拒绝单字符如 "1"、"a"）
  3. 不能为纯数字（拒绝 "1"、"123"）
  4. 必须包含至少一个字母或中文字符（拒绝 "---"、"!!!" 等纯特殊字符）

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| ReleaseBaseServiceImpl.java | 修改 | 新增 validateProductName 私有方法 + 两处调用 |
| ReleaseBaseServiceImplTest.java | 修改 | 新增 6 个测试用例 |

## 风险 & 缓解

- **误拒合法名称**：校验规则要求至少含一个字母或中文，可能影响纯日文/韩文等产品名。当前系统面向中文用户，风险极低；如后续需支持可放宽为 Unicode 字母范围。
- **既有数据**：已有评审单中可能存在不符合新规则的名称，新规则仅在创建/修改时生效，不影响存量数据。

## 跨仓影响

无。仅修改 openlibing-platform-release 业务仓。
