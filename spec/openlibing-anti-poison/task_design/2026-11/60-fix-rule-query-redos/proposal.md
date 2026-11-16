# 60-fix-rule-query-redos — 需求背景与验收标准

## 背景

`/checkRule/query/rules` 规则查询接口中，rulename 参数做了白名单校验（不含正则特殊字符），但 desc 参数直接使用前端输入、未做任何校验，可构造恶意正则输入造成 ReDoS。同时 `escapeSpecialWord` 方法存在逻辑缺陷：每次只转义一个字符，且下一次处理会覆盖上一次的转义结果，无法实现有效的正则字符转义。

关联业务 Issue：openlibing/openlibing-anti-poison#60

## 需求范围

- 对 desc 参数补充与 rulename 一致的校验（白名单/特殊字符校验）
- 修复 escapeSpecialWord 方法，正确转义输入中的全部正则特殊字符且不被后续处理覆盖

## 验收标准

- [x] desc 参数完成校验，恶意正则输入被拒绝（已随业务 PR openlibing/openlibing-anti-poison#139 交付）
- [x] escapeSpecialWord 修复后转义结果正确（已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

无。
