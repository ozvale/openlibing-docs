# fix-ruleset-export-missing-headers

## 需求背景

规则集导出功能（`/ci-portal/excel/v1/rule/set` 与 `/ci-portal/excel/v1/rule/set/export`）导出的 Excel 文件中，最后两列（columnIndex 12、13）没有标题，用户查看时无法理解这两列数据的含义。

根因：`FileDownloadDelegateImpl.ruleTitle` 数组只定义了 12 个标题（索引 0-11），但 `CodeCheckRuleVo` 中 `domainName`（columnIndex=12）和 `region`（columnIndex=13）两个字段带有 `@ExcelAttribute` 注解，`ExcelUtil.export` 按 `titles.length` 生成表头、按 `columnIndex` 生成数据单元格，导致这两列数据无表头。

## 功能描述

- 做什么：在 `ruleTitle` 数组中补充 columnIndex 12（domainName）和 13（region）两列的标题。
- 不做什么：不修正 columnIndex 11 的标题（当前"规则阈值"与 `userName` 字段语义不符的问题），保持现有行为，避免超出本次修复范围。

## 验收标准

- [ ] 导出的规则集 Excel 文件表头行有 14 列标题（columnIndex 0-13）
- [ ] columnIndex 12 标题为"华为云账号名"，对应 `domainName` 字段
- [ ] columnIndex 13 标题为"区域"，对应 `region` 字段
- [ ] 不影响其他导出功能（MR 规则集导出、语言规则集导出等）

## 影响范围

- 文件：`src/main/java/com/openlibing/codecheck/business/impl/FileDownloadDelegateImpl.java`
- 接口：`/ci-portal/excel/v1/rule/set`、`/ci-portal/excel/v1/rule/set/export`
- 关联 Issue：openlibing/openlibing-codecheck#123
