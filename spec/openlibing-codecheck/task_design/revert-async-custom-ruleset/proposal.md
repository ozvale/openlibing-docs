# Proposal: 回退 customProjectRuleSet 异步改造为同步

## 需求背景

`/project/ruleSet/custom` 接口被改造为异步接口后，引入了两个问题：

1. **templateId 传参错误**：异步版本立即返回 `taskId`（格式如 `ruleset_3_7137c91231f23f231d_12124134513_8193`）而非华为云创建规则集后返回的真实 `templateId`。前端将 `taskId` 当作 `templateId` 传给 `/rules/setting/account` 接口，导致华为云 API 查询失败，规则集设置页面报错"获取规则列表失败"。
2. **安全增强类规则提示消失**：异步版本无法同步返回安全增强类规则的过滤提示信息，用户在导入包含安全增强类规则的规则集时不再收到提示。

## 验收标准

- [ ] 调用 `/project/ruleSet/custom` 接口导入规则集后，返回值为华为云真实 `templateId`
- [ ] 导入后进入规则集设置页面，`/rules/setting/account` 接口正常返回规则列表
- [ ] 安全增强类规则过滤提示正常显示
- [ ] 规则集创建成功后，规则集同步和权限同步逻辑正常执行

## 关联 Issue

openlibing/openlibing-codecheck#118
