# 安全编译选项导出 Excel 公式注入防护（#549）— 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/549 （安全问题，已关闭）
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/pulls/686
- 分支: `fix-549-secoption-excel-formula-escape` → `master`
- 合并: merge commit `d77b33028`
- 前置能力: PR `!636`（`fix-excel-formula-injection`，commit `2e52407fb`、`b5a6f7105`）提供的 `ExcelUtils.isFormulaInjectionRisk` 与 `ExcelFormulaEscapeConverter`

## 交付历程

- commit `3f197cd44`: fix(security) — 导出写入器注册 `ExcelFormulaEscapeConverter`
- commit `72e14071b`: fix(security) — 新增 `FormulaGuardStyleApplier`，在超链接与覆盖率着色处理器覆盖样式后仍保留 `quotePrefix`

## 关键验证

- `SecOptionScanServiceImplTest` 新增 3 类断言：危险前缀被标记、普通文本不被标记、样式覆盖后标记保留
- 导出文件可见文本与改造前一致，防护只体现为单元格解析方式（`quotePrefix`）差异
- 非 `XSSF` 工作簿降级不标记，不抛异常
- spotless / checkstyle / spotbugs / pmd 通过

## 设计偏差与取舍

- 未在 `ExcelUtils` 中重复实现判定逻辑，直接复用 `!636` 已合入的通用能力，避免同类规则出现两份
- 未采用"值前缀拼接 `'`"方案：会改变用户可见文本，导出文件是交付物，不接受内容被改写
- 受保护样式按处理器实例懒克隆一次并复用，避免每行建样式导致 xlsx 样式表膨胀

## 可复用经验

- EasyExcel 中 Converter 与 CellWriteHandler 的执行顺序是 Converter → CellWriteHandler；只要链路里有自定义样式处理器，就必须在处理器侧重新施加 `quotePrefix`，只在 Converter 注册是无效的
- `quotePrefix` 仅在 `XSSFCellStyle` 暴露，非 XSSF 工作簿要显式降级，否则会抛类型异常

## 回归状态

前端页面回归（构建产物 → 安全编译选项 → 包详情 → 导出）已在 Issue #549 评论区给出步骤，待人工执行，不在本次归档内标记完成。

## 归档日期

2026-11-19
