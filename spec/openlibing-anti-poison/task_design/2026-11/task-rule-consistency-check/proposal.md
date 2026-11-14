# task-rule-consistency-check

> 关联业务 Issue: openlibing/openlibing-anti-poison#70

## 需求背景

`CheckRuleServiceImpl.updateTaskRule`（任务规则集更新接口）当前只校验 repoId 非空、repo 存在、操作人是 repo 所属社区的项目管理员，未校验入参 `antiCheckRules[].ruleSetId` 的归属。项目管理员可传入其他社区的 ruleSetId，把别的社区的规则集绑定到自己仓库任务上，存在越权绑定与数据不一致风险。

## 功能描述

- 做什么：更新任务规则集前，逐个校验入参 ruleSetId 在 `anti_check_rule_set` 中真实存在，且其 `project_id` 与 repo 所属社区一致；任一不满足则返回 403，不执行更新。
- 不做什么：不改变接口出入参结构；不调整其他校验顺序与既有逻辑；不处理通用规则集的特殊放行（按用户要求严格同社区）。

## 验收标准

- [ ] 传入不存在的 ruleSetId 时，接口返回 403 且不更新数据
- [ ] 传入属于其他社区的 ruleSetId 时，接口返回 403 且不更新数据
- [ ] 全部 ruleSetId 属于同一社区且操作人是该项目管理员时，接口正常更新
- [ ] 补充单测覆盖上述正反场景并通过

## 影响范围

- 业务仓：`openlibing-anti-poison`
  - `src/main/java/com/openlibing/antipoison/business/service/impl/CheckRuleServiceImpl.java`
  - `src/test/java/com/openlibing/antipoison/business/service/impl/CheckRuleServiceImplTest.java`
