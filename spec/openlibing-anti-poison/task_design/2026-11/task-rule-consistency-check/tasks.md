# task-rule-consistency-check — 实现任务

## 进度: 4/4 complete

- [x] Task 1: updateTaskRule 增加 ruleSetId 存在性 + 归属社区一致性校验（403 拦截）— commit 158bde7
- [x] Task 2: 补充单测：不存在 ruleSetId / 跨社区 ruleSetId / 空白 ruleSetId / 合法更新（CheckRuleServiceImplTest 40 用例全通过）
- [x] Task 3: 运行相关单测与编译验证（mvn test + pre-commit 钩子全绿）
- [x] Task 4: 提交 commit（Refs #70，已随业务 PR openlibing/openlibing-anti-poison#139 合入 release_20261116_iter1）
