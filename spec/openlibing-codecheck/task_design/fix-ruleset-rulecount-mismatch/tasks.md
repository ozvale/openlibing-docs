# fix-ruleset-rulecount-mismatch — 实现任务

## 进度: 0/6 complete

- [ ] Task 1: 修正 `JsonUtil.ruleCount(String)`：null 安全、过滤空白项、去重，返回 `String[]`
- [ ] Task 2: 新增 `JsonUtil.ruleCountInt(String)` 返回 `int`，供需要直接拿数量的调用方使用
- [ ] Task 3: `RuleSetListImpl.getProjectRuleSetList` 为每个 `CodeCheckProjectRuleSetVo` 填充 ruleCount
- [ ] Task 4: `RuleSetListImpl.getPersonalRuleSetList` 与 `getProjectSingleRuleSet` 填充 ruleCount
- [ ] Task 5: 更新 `JsonUtilTest`（修正空串用例断言 + 新增去重/null/空白项用例 + ruleCountInt 用例）
- [ ] Task 6: 补充 `RuleSetListImplTest` 三个查询方法的 ruleCount 填充断言，运行 `mvn test` 验证
