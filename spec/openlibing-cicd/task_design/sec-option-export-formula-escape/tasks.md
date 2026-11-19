# sec-option-export-formula-escape: 实现步骤

## 编码

- [x] 确认 `ExcelUtils.isFormulaInjectionRisk` 与 `ExcelFormulaEscapeConverter` 已在 `!636` 落地，本次复用不重复实现
- [x] 在 `SecOptionScanServiceImpl` 的导出 `ExcelWriter` 上注册 `ExcelFormulaEscapeConverter`
- [x] 新增私有静态内部类 `FormulaGuardStyleApplier`，按文本判定结果切换基准样式与 `quotePrefix` 样式
- [x] 超链接单元格处理器改用 `FormulaGuardStyleApplier` 设置样式
- [x] 覆盖率着色处理器（表头 / 明细 / 键列）改用 `FormulaGuardStyleApplier` 设置样式
- [x] 非 `XSSF` 工作簿降级为不标记，不抛异常

## 测试

- [x] `SecOptionScanServiceImplTest` 覆盖危险前缀被标记
- [x] `SecOptionScanServiceImplTest` 覆盖普通文本不被标记
- [x] `SecOptionScanServiceImplTest` 覆盖样式覆盖后标记保留
- [x] 本地执行相关单测通过
- [x] spotless / checkstyle / spotbugs / pmd 通过

## 交付

- [x] 业务分支 `fix-549-secoption-excel-formula-escape` 提交并推送
- [x] 业务 PR #686 创建并关联 Issue #549，打 `ai-assisted` 标签
- [x] PR 合入 master（merge commit `d77b33028`）

## 回归（前端配合，待人工执行）

- [ ] 构建产物 → 安全编译选项 → 包详情 → 导出，任务创建与下载正常
- [ ] 导出文件可正常打开，基础信息、选项明细、着色与改造前一致
- [ ] 危险前缀字段显示为文本，不出现 `#NAME?` 或被当作公式计算
