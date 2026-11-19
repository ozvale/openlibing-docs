# sec-option-export-formula-escape: 工程设计

## 1. 方案设计

Excel 公式注入有两种常见处置方式：

| 方案           | 做法               | 副作用                             |
| -------------- | ------------------ | ---------------------------------- |
| 值前缀转义     | 在值前拼接 `'`     | 用户可见文本被改变，复制出来带引号 |
| 单元格样式标记 | 设置 `quotePrefix` | 用户可见文本不变，Excel 按文本处理 |

本方案沿用平台既有的 `quotePrefix` 路线：导出文件是给人看的交付物，值本身不应被改写。

安全编译选项导出链路的特殊性在于它在数据填充后还挂了两个自定义 `CellWriteHandler`：

- `Sheet1` 基础信息块超链接处理器：给代码仓/流水线链接单元格加超链接样式
- 覆盖率着色处理器：按覆盖率给明细单元格着色

两者都直接调用 `cell.setCellStyle(...)`。EasyExcel 执行顺序是 Converter → CellWriteHandler，因此 Converter 设置的 `quotePrefix` 会被处理器覆盖。仅注册转换器无法闭环。

方案要点：在处理器内部改为"取基准样式 → 判定风险 → 命中则换用带 `quotePrefix` 的克隆样式"。

## 2. 实现逻辑设计

1. 导出构建 `ExcelWriter` 时链式注册 `new ExcelFormulaEscapeConverter()`
2. 新增私有静态内部类 `FormulaGuardStyleApplier`，持有懒初始化的 `guardedStyle`
3. `apply(cell, baseStyle)`：
   - 读取单元格文本，非字符串单元格（数值等）直接用 `baseStyle`
   - `ExcelUtils.isFormulaInjectionRisk(value)` 为 false → 用 `baseStyle`
   - 命中时若 `guardedStyle` 未初始化，则 `createCellStyle()` + `cloneStyleFrom(baseStyle)` + `setQuotePrefixed(true)`；随后用 `guardedStyle`
   - `guardedStyle` 每个处理器实例持有、只克隆一次，同一表格内复用
4. 超链接处理器与覆盖率处理器各自持有 `FormulaGuardStyleApplier` 实例，把原 `cell.setCellStyle(xxxStyle)` 替换为 `styleApplier.apply(cell, xxxStyle)`
5. 非 `XSSF` 工作簿（`quotePrefix` 仅在 `XSSFCellStyle` 暴露）跳过标记，导出行为降级为不保护而非报错

## 3. 类设计

| 类                                                          | 职责                                                               |
| ----------------------------------------------------------- | ------------------------------------------------------------------ |
| `ExcelUtils`（既有）                                        | 危险前缀常量 `=+-@\t\r` 与 `isFormulaInjectionRisk` 判定           |
| `ExcelFormulaEscapeConverter`（既有）                       | 常规取值链路上的 `quotePrefix` 标记                                |
| `SecOptionScanServiceImpl.FormulaGuardStyleApplier`（新增） | 样式处理器场景下保留 `quotePrefix`，避免被覆盖                     |
| `SecOptionScanServiceImpl` 内部处理器                       | 超链接样式、覆盖率着色，改为经 `FormulaGuardStyleApplier` 设置样式 |

`FormulaGuardStyleApplier` 为私有静态内部类，不对外暴露，不引入新工具包。

## 4. 数据模型设计

无表结构、无实体、无字段变更。导出文件的列定义、Sheet 名、数据来源均保持原样。

## 5. 性能设计

- 风险判定为单字符比较，`O(1)`
- 受保护样式每个处理器实例只克隆一次，其余危险单元格复用同一 `CellStyle`，不会随行数增长产生样式爆炸
- 非危险单元格零额外样式对象，与原实现一致

## 6. API 接口设计

无变化。`/build-artifact/sec-option/detail/export` 的请求参数、响应体、异步导出任务类型（`SEC_OPTION_DETAIL`）与文件命名规则均未改动。

## 7. 安全设计

- 覆盖威胁：CWE-1236（CSV/Excel 公式注入）
- 缓解点：常规取值走 Converter，样式覆盖路径走 `FormulaGuardStyleApplier`，两条写入路径都过判定，不依赖字段白名单
- 边界：防护只作用于导出文件，不改变数据库存储值与页面展示值
- 残余风险：后续新增的导出链路若同样自定义了 `CellWriteHandler`，需自行复用同一守卫逻辑；本次未做全局拦截
