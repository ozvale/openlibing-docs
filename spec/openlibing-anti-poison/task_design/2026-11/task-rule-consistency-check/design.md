# task-rule-consistency-check — 技术设计

## 方案概述

在 `updateTaskRule` 既有权限校验通过后、执行更新前，遍历入参 `antiCheckRules`，复用现有 `CheckRuleOperation.queryRuleSetById(ruleSetId)` 查询 `anti_check_rule_set`，校验规则集存在且 `projectId` 与 `repoInfoVO.getProjectId()` 一致，否则返回 403。

## 架构决策

1. **校验位置**：放在 service 层 `updateTaskRule` 内，与同类越权防护（`createRuleSet` 中"修改规则集先校验归属"）保持一致风格。
2. **权限等价性**：规则集全部归属 repo 所在社区后，现有 `checkProjectManagerPermission(userId, repoInfo.getProjectId())` 一处校验即等价于"userId 是规则集所在社区的项目管理员"，无需重复校验。
3. **复用查询**：直接使用已有的 `queryRuleSetById`（findOne by `_id`），不新增 Operation 方法。
4. **空列表语义**：`antiCheckRules` 为空时沿用现状（`updateTaskRule` 操作层对空列表不写 `anti_check_rules` 字段），仅对非空条目做校验；ruleSetId 为空白视为非法，返回 403。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| src/main/java/com/openlibing/antipoison/business/service/impl/CheckRuleServiceImpl.java | 修改 | updateTaskRule 增加归属一致性校验 |
| src/test/java/com/openlibing/antipoison/business/service/impl/CheckRuleServiceImplTest.java | 修改 | 补充正反场景单测 |

## 风险 & 缓解

- 若存量任务规则集中已绑定了跨社区规则集，更新时需重新传全量合法列表才能通过——属预期安全行为。
- 通用规则集（如"通用检查规则集"）若 projectId 与社区不一致，将被拦截——按用户要求严格同社区，如后续需放行再迭代。

## 跨仓影响

无外部接口契约变化；docs 仓仅落 spec 文档。
