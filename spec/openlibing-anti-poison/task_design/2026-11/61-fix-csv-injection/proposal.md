# 61-fix-csv-injection — 需求背景与验收标准

## 背景

`/checkRule/query/export/rules` 规则导出中，所有写入 excel 的数据虽经 `CSVInjection.transData` 处理，但该方法存在缺陷：匹配到特定字符开头时通过 substring 丢弃首字符，若第二个字符仍是特殊字符则可绕过防护。另外规则新增接口仅对 ruleName、ruleDesc、RightExample、ErrorExample、ReviseOpinion、FileIds 做了 CSV 注入校验（isStartWithSpecialCharacter），ruleLanguage、ruleId、status、tag、linkName 等字段均未校验。

关联业务 Issue：openlibing/openlibing-anti-poison#61

## 需求范围

- 修复 CSVInjection.transData 缺陷，防止连续特殊字符绕过
- 规则新增接口对未校验字段补齐 CSV 注入校验
- 按 issue 建议：将导出的 csv/excel 单元格设置为文本格式，从根本上避免公式执行

## 验收标准

- [x] 导出文件单元格为文本格式，CSV 注入不再触发（已随业务 PR openlibing/openlibing-anti-poison#139 交付）
- [x] transData 逻辑缺陷与字段校验缺失已修复（已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

无。
