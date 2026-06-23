# fix-ruleset-export-missing-headers — 技术设计

## 方案概述

在 `FileDownloadDelegateImpl.java` 的静态初始化块中，为 `ruleTitle` 数组补充 columnIndex 12（华为云账号名）和 13（区域）两个标题，使表头覆盖所有有数据的列。

## 架构决策

- 标题文案选择"华为云账号名"和"区域"，与 `CodeCheckRuleVo` 中 `domainName`、`region` 字段语义一致（`domainName` 在华为云 IAM 体系中对应账号域名），且与 `RuleModel`/`AccountUser` 中同类字段的命名习惯一致。
- 不修改 `CodeCheckRuleVo` 的 `@ExcelAttribute` 注解，避免影响数据列布局。
- 不修正 columnIndex 11 的标题（"规则阈值"），因为用户仅报告"两列没有标题"的问题，超出范围的修正需单独评估。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/codecheck/business/impl/FileDownloadDelegateImpl.java` | 修改 | `ruleTitle` 数组追加两个标题元素 |

## 风险 & 缓解

- 风险：标题文案与下游消费者预期不一致。
  缓解：文案与字段语义对齐，且仅补充缺失标题，不改变现有列顺序与已有标题。
- 风险：补充标题后表头列数与数据列数一致，但若未来 `CodeCheckRuleVo` 再新增 `@ExcelAttribute` 字段，可能再次出现错位。
  缓解：本次不引入额外校验逻辑（超出 Standard 范围），在 archive 中记录该潜在风险。

## 跨仓影响

无。
