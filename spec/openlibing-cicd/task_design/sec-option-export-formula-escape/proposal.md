# sec-option-export-formula-escape: 安全编译选项导出 Excel 公式注入防护

## 需求背景

安全编译选项扫描详情导出接口（`/build-artifact/sec-option/detail/export`）生成的 Excel 中，`fileName`、`packageName`、代码仓地址等字段来源于插件上报，属外部可控输入。若值以 `=`、`+`、`-`、`@`、`\t`、`\r` 开头，Excel 打开文件时会按公式解析，构成 CSV/Excel 注入（CWE-1236）：使用者只要打开导出文件就可能触发计算或外链请求。

平台内其他导出链路已在 `!636`（`fix-excel-formula-injection`）引入通用治理能力：`ExcelUtils.isFormulaInjectionRisk` 判定危险前缀，`ExcelFormulaEscapeConverter` 对命中单元格设置 `quotePrefix`。但安全编译选项导出链路使用的是自定义 `CellWriteHandler`（超链接着色、覆盖率着色），它在 Converter 之后直接 `cell.setCellStyle(...)`，会把 `quotePrefix` 覆盖掉，因此该链路实际未受保护。

- 关联 Issue：https://gitcode.com/openlibing/openlibing-cicd/issues/549
- 关联 PR：https://gitcode.com/openlibing/openlibing-cicd/pulls/686

## 功能描述

- 在导出 `ExcelWriter` 上注册既有 `ExcelFormulaEscapeConverter`，覆盖 EasyExcel 常规取值路径
- 新增私有内联样式器 `FormulaGuardStyleApplier`，在自定义 `CellWriteHandler` 设置基准样式时按需克隆一份带 `quotePrefix` 的样式，避免后续样式覆盖导致标记丢失
- 危险值单元格保持原始文本，仅改变单元格解析方式；未命中值的单元格不新建、不修改样式
- 非 `XSSF` 工作簿降级为不标记（当前导出固定 xlsx）

## 验收标准

- [x] 导出写入器注册 `ExcelFormulaEscapeConverter`
- [x] 超链接单元格处理器与覆盖率着色处理器改写样式后，危险值单元格仍保留 `quotePrefix`
- [x] 未命中危险前缀的单元格不新建样式、不改动基准样式
- [x] 覆盖样式时只克隆一次受保护样式，其余单元格复用，不产生大量重复样式对象
- [x] 导出接口路径、入参、出参、导出文件名、Sheet 结构、列顺序与改造前一致
- [x] Excel 中用户可见文本与改造前一致（不出现前置单引号字符）
- [x] `SecOptionScanServiceImplTest` 覆盖危险前缀被标记、普通文本不误伤、样式覆盖后标记保留三类场景
- [x] 相关单测与静态检查（spotless / checkstyle / pmd / spotbugs）通过

## 影响范围

| 文件                                                                                        | 操作 | 说明                                                                                                                      |
| ------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImpl.java`     | 修改 | 导出写入器注册 `ExcelFormulaEscapeConverter`；新增 `FormulaGuardStyleApplier` 并在两类样式处理器中替换直连 `setCellStyle` |
| `src/test/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImplTest.java` | 修改 | 补充公式注入防护回归用例                                                                                                  |

无 HTTP 接口契约变化，无数据模型变化，无配置项新增，无 pom 变更。
