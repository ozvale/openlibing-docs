# fix-ruleset-rulecount-mismatch

## 需求背景

codecheck 仓规则集列表页面接口显示的规则集规则数（ruleCount）与实际规则数不一致。前端在规则集集合列表页面看到的规则数恒为 0，而进入规则集详情/编辑页面才看到真实数量，造成数据展示矛盾，影响用户对规则集规模的判断。

关联业务 Issue: https://gitcode.com/openlibing/openlibing-codecheck/issues/126

## 功能描述

### 做什么

1. 修复 `RuleSetListImpl` 三个查询方法，为返回的每个 `CodeCheckProjectRuleSetVo` 正确填充 `ruleCount` 字段。
2. 修复 `JsonUtil.ruleCount` 统计逻辑，使其去重、过滤空值、null 安全，空规则集返回 0。
3. 统一规则数统计方式，使 `RuleSetListImpl` 与 `RuleDelegateImpl.getProjectRuleSet` 返回的 ruleCount 一致。

### 不做什么

- 不修改 MongoDB 持久化结构（`ruleCount` 仍是 `@Transient` 字段）。
- 不修改 `numCriterion`（华为云同步字段）相关逻辑。
- 不修改前端代码（仅后端接口返回值修正）。
- 不重构其他无关的 ruleIds 解析调用点。

## 验收标准

- [ ] `RuleSetListImpl.getProjectRuleSetList` 返回的每个规则集 ruleCount 与实际规则数一致
- [ ] `RuleSetListImpl.getPersonalRuleSetList` 返回的每个规则集 ruleCount 与实际规则数一致
- [ ] `RuleSetListImpl.getProjectSingleRuleSet` 返回的每个规则集 ruleCount 与实际规则数一致
- [ ] ruleCount 统计逻辑去重、过滤空值，空规则集返回 0，null 安全
- [ ] 与 `RuleDelegateImpl.getProjectRuleSet` 返回的 ruleCount 一致
- [ ] 补充/更新相关单元测试并通过

## 影响范围

- 仓库：openlibing-codecheck
- 模块：规则集列表查询（RuleSetListImpl）、规则数统计工具（JsonUtil）
- 接口：
  - `GET /operate/project/ruleSetList`
  - `GET /operate/personal/ruleSetList`
  - `GET /operate/project/single/ruleSetList`
- 无数据库 schema 变化
- 无外部接口契约变化（仅修正返回字段值）
