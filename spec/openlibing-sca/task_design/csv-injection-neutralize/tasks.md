# csv-injection-neutralize — 实现任务

## 进度: 4/4 complete

- [x] Task 1: `CSVInjection#transData` 从递归剥离改为单引号前缀，null 返回空串（`85542090`）
- [x] Task 2: `CSVInjection#validate` 改为"全角转半角 + 去 NUL 后首字符集合判定"，移除正则常量（`85542090`）
- [x] Task 3: `OpenScanServiceImpl#insertScanIssue` 双重 `transData` 调用简化为单次（`85542090`）
- [x] Task 4: 重写 `CSVInjectionTest` 为前缀语义并补充幂等/换行/全角/NUL 用例（`85542090`）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                            | 关联        |
| ---------- | --------------------------------------------------------------- | ----------- |
| `85542090` | fix(analysis): neutralize CSV injection via single quote prefix | `Refs #131` |

关键 diff：

- `CSVInjection`：删除 `COMPLILE = Pattern.compile("^[=+\\-&\\\\@\"].{0,}")` 与 `Matcher`；新增 `DANGEROUS_LEADING_CHARS = "=+-&\\@\""`；`transData` 危险时返回 `"'" + data`；`convertToHalfWidth` 上界 `'｠'` → `'ｓ'`。
- `OpenScanServiceImpl`：`cell2.setCellValue(CSVInjection.transData(CSVInjection.transData(value)))` → 单次调用（当前 L4150）。
- `CSVInjectionTest`：11 个用例，覆盖 `transData_shouldPrefixSingleQuote_whenLeadingSpecialCharacters`、`...MultipleLeadingSpecialCharactersWithSinglePrefix`、`...PreserveOriginalData`、`...BeIdempotent`、`...NeutralizeValuesWithLineBreaks`、`...NeutralizeFullWidthLeadingCharacters`、`...NeutralizeNulLeadingCharacters`、`...ReturnOriginalString_whenNoLeadingSpecialCharacters`、`...HandleSpecialCharactersInMiddle`、`...ReturnEmptyString_whenEmptyOrNull`、`validate_shouldDetectDangerousLeadingCharacters`。

验证方式：

- 单测：`CSVInjectionTest` 11 个用例已按前缀语义重写；本次回溯未执行 `mvn test`，实际执行结果未验证。
- 静态核实：`CSVInjection.java` 当前无 `Pattern` / `Matcher` 引用，`DANGEROUS_LEADING_CHARS` 与 `transData` 为前缀实现；`OpenScanServiceImpl` 中无 `transData(CSVInjection.transData(...))` 形式调用（仅测试内保留幂等断言）。

## 备注：与 issue 正文的差异

issue 描述为"匹配到特定字符开头时通过 substring 丢弃首字符，若第二个字符仍是特殊字符则可绕过"。实际旧实现是**递归** `transData(data.substring(1))`，连续特殊字符会被逐层剥离而非直接绕过；可证实的缺陷是正则 `.{0,}` 不匹配行终止符（`=\ncmd` 整条放行）以及递归剥离损坏合法数据。文档按代码证据记录，详见 `design.md` D1/D3。
