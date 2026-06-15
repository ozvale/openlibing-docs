# Proposal: fragment 代码片段加密存储及日志泄露防护

## 需求背景

openlibing-codecheck 的 `task_result_details` 和 `task_inc_result_details` 两张 MongoDB 集合中，`fragment` 字段存储了用户源代码上下文片段（`CodeCheckIssueFragment.lineContent`）。这些代码数据属于用户数据，可能包含敏感信息（如明文密钥、API Token 等），存在以下安全风险：

1. **明文存储**：fragment.lineContent 以明文存储在 MongoDB 中，数据库被攻破后可直接获取用户源代码
2. **日志泄露**：DatarecoveryDelegateImpl 中直接打印 `List<DefectVo>.toString()`，会将完整代码片段写入日志文件
3. **toString 泄露**：DefectVo 使用 Lombok `@Data` 注解，自动生成的 `toString()` 会递归打印 fragment 内容，任何日志打印 DefectVo 对象都会泄露代码片段
4. **规则示例泄露**：CodeCheckRuleVo 等 5 个规则类的 `rightExample`/`errorExample` 字段同样会被 `toString()` 打印到日志

## 验收标准

- [ ] 新数据入库后 MongoDB 中 fragment.lineContent 为密文
- [ ] 前端查询问题详情时 fragment 正常显示（自动解密）
- [ ] 历史未加密数据查询不受影响（解密失败保留原值）
- [ ] 日志中不再出现 fragment 代码片段内容
- [ ] 日志中不再出现 rightExample/errorExample 内容
- [ ] 加密失败时中断入库，避免明文入库

## 关联

- 业务 Issue: yanzhaohong/openlibing-codecheck#3
- 业务 PR: openlibing/openlibing-codecheck#203
