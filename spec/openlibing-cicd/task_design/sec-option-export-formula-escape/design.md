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

### 与既有 spec 的关系

`task_design/sec-option-detail-export/design.md` 第 7 章「导出内容转义」原定口径为"前置单引号 + 在行模型装配处统一处理"，与本节方案不同。差异原因：

- 前置单引号会改变用户可见文本，导出文件作为交付物不可接受
- 行模型装配处拿不到 `CellStyle`，无法设置 `quotePrefix`；且样式会被后续自定义 `CellWriteHandler` 覆盖

已在既有 spec 对应位置加勘误注记，指向本文件，避免两份文档口径冲突。

## 2. 实现逻辑设计

1. 导出构建 `ExcelWriter` 时链式注册 `new ExcelFormulaEscapeConverter()`
2. 新增私有静态内部类 `FormulaGuardStyleApplier`，持有懒初始化的 `guardedStyle`
3. `apply(cell, baseStyle)`：
   - 读取单元格文本，非字符串单元格（数值等）直接用 `baseStyle`
   - `ExcelUtils.isFormulaInjectionRisk(value)` 为 false → 用 `baseStyle`
   - 命中时若 `guardedStyle` 未初始化，则 `createCellStyle()` + `cloneStyleFrom(baseStyle)` + `setQuotePrefixed(true)`；随后用 `guardedStyle`
4. 超链接处理器与覆盖率处理器各自持有 `FormulaGuardStyleApplier` 实例，把原 `cell.setCellStyle(xxxStyle)` 替换为 `styleApplier.apply(cell, xxxStyle)`
5. 非 `XSSF` 工作簿（`quotePrefix` 仅在 `XSSFCellStyle` 暴露）跳过标记，导出行为降级为不保护而非报错

### 已知限制：守卫样式只缓存一份

`FormulaGuardStyleApplier` 每个实例只保存一个 `guardedStyle`，且由该处理器**首个命中的基准样式**克隆而来。而 `Sheet1StaticStyleHandler` 在一个实例内混用表头 / 明细 / 键列三套基准样式，`ValueColorHandler` 按覆盖率颜色缓存多套彩色样式。因此：

- 首个危险值单元格来自哪套基准样式，后续危险值单元格就都继承哪套外观
- 实际影响面很小：表头与键列值是代码内固定文案，不可能命中危险前缀；可能命中危险前缀的外部输入集中在明细数据列，基样式一致
- 尚未出现可见的样式错位，但这是实现层面的保真缺口，已登记为后续优化项（按 `baseStyle` 身份缓存多份克隆样式）

当前导出文件的列结构、Sheet 划分与样式表现以实际导出结果为准；`SecOptionScanServiceImpl` 内共 4 处 EasyExcel 写点（1 个 `write` + 3 个 `writerSheet`，覆盖 2 个 Sheet），均属于同一条受保护的写入链路。

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
- 受保护样式按处理器实例懒克隆一次后复用，不会随行数增长产生样式爆炸；代价是只保留首个基准样式的克隆（见第 2 章「已知限制」）
- 非危险单元格零额外样式对象，与原实现一致

## 6. API 接口设计

无变化。`/build-artifact/sec-option/detail/export` 的请求参数、响应体、异步导出任务类型（`SEC_OPTION_DETAIL`）与文件命名规则均未改动。

## 7. 安全设计

- 覆盖威胁：CWE-1236（CSV/Excel 公式注入）
- 缓解点：常规取值走 Converter，样式覆盖路径走 `FormulaGuardStyleApplier`，两条写入路径都过判定，不依赖字段白名单
- 边界：防护只作用于导出文件，不改变数据库存储值与页面展示值
- 残余风险一（已知限制）：同一处理器内多套基准样式时，危险值单元格只继承首个基准样式的外观，详见第 2 章
- 残余风险二（跨仓）：Issue #549 点名 `openlibing-codecheck` master 仍有 5 处 `EasyExcel.write` 未做公式转义（`FileDownloadDelegateImpl` 2 处、`StaticAlarmServiceImpl` 3 处），且全仓无 converter 类，需在 codecheck 仓单独立项跟踪；`openlibing-coderepo` 经评估无 Excel 导出，不涉及。本仓其他导出链路未逐一核查
- 残余风险三：后续新增的导出链路若同样自定义了 `CellWriteHandler`，需自行复用同一守卫逻辑；本次未做全局拦截
