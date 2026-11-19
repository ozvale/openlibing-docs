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
- 受保护样式按处理器实例懒克隆一次并复用，避免每行建样式导致 xlsx 样式表膨胀；代价是同一处理器内多套基准样式时只保留首个外观（表头/键列为固定文案，实际不命中危险前缀，影响面仅限理论保真度），已登记为后续优化项
- 未对仓库内其他导出链路做统一改造，本次范围限定安全编译选项导出单个接口

## 与既有 spec 的口径关系

`sec-option-detail-export/design.md` 原定"前置单引号 + 行模型装配处统一处理"，与本次实现不同。已在原文件加勘误注记指向本 spec，并在本 spec `design.md` 第 1 章记录切换原因。

## 检视闭环

- "守卫样式只缓存一份，多套基准样式会串样式"：确认为实现层面的保真缺口，已如实写入 `design.md` 第 2 章「已知限制」，并登记后续按 `baseStyle` 身份缓存的优化项；当前导出实际表现无可见错位
- "仓库内其他 EasyExcel 写点未覆盖"：确认本次范围仅安全编译选项导出链路，其余链路属独立整改，已写入残余风险与待办
- "与既有 spec 冲突"：确认存在口径差异，已在既有 spec 加勘误、在本 spec 说明差异原因

## 可复用经验

- EasyExcel 中 Converter 与 CellWriteHandler 的执行顺序是 Converter → CellWriteHandler；只要链路里有自定义样式处理器，就必须在处理器侧重新施加 `quotePrefix`，只在 Converter 注册是无效的
- `quotePrefix` 仅在 `XSSFCellStyle` 暴露，非 XSSF 工作簿要显式降级，否则会抛类型异常

## 回归状态

前端页面回归（构建产物 → 安全编译选项 → 包详情 → 导出）已在 Issue #549 评论区给出步骤，待人工执行，不在本次归档内标记完成。

## 归档日期

2026-11-19
