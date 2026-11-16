# csv-injection-neutralize — 技术设计

## 方案概述

把"递归剥离危险前导字符"替换为"单引号前缀中和"：

- `validate`：`convertToHalfWidth` + 去 NUL 后取首字符，落在 `=+-&\@"` 集合即视为危险；
- `transData`：危险时返回 `"'" + 原始数据`，否则原样返回；null 返回空串。

危险值在 Excel/CSV 打开时被解析为文本而不是公式，原始内容（除前缀之外）完整保留。

## 架构决策

| 决策                                            | 理由                                                                                                                                       |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| D1 采用单引号前缀而非继续剥离                   | 前缀改变首字符类别，公式不再成立；一次前缀即可中和任意长的连续危险字符，不需要递归；原始数据不被破坏                                       |
| D2 前缀方案天然幂等                             | 前缀后首字符为 `'`，不在危险集合内，重复调用不再追加；因此 `insertScanIssue` 的双重调用可简化为单次                                        |
| D3 危险判定改为首字符集合判断                   | 旧正则 `^[...].{0,}` 中 `.` 不匹配行终止符，`=\ncmd` 无法匹配；逐字符集合判断不依赖正则的行语义，也不受输入长度影响                        |
| D4 判定基于"转换后内容"，前缀加在"原始数据"     | 保留原有全角转半角/NUL 清理语义：`＝cmd`（全角等号）也应识别为危险；同时导出值保留原始字符，不因检测而改写数据                             |
| D5 全角区间上界 `'｠'`(U+FF60) → `'ｓ'`(U+FF53) | 原区间尾部（U+FF54-U+FF60）偏移后落到 ASCII 之外（如 DEL），转换结果不可预期；收窄到常用全角字母数字区间更安全                             |
| D6 不采用 issue 建议的"单元格文本格式"          | `transData` 是统一入口，前缀方案改动集中、覆盖全部导出点；文本格式需逐处设置 DataFormat 并共享样式，改动面更大。取舍已记录，后续可按需替换 |
| D7 双引号 `"` 仍在危险集合内                    | 保留旧行为，防止以引号起始引发的公式/字段逃逸场景被回归                                                                                    |

## 关键实现（当前代码）

```
private static final String DANGEROUS_LEADING_CHARS = "=+-&\\@\"";

public static String transData(String data) {
  if (data == null) return StringUtils.EMPTY;
  if (validate(data)) return "'" + data;
  return data;
}

public static boolean validate(String labelContent) {
  if (StringUtils.isBlank(labelContent)) return false;
  String convert = convertToHalfWidth(labelContent).replaceAll("\u0000", "");
  return StringUtils.isNotEmpty(convert)
      && DANGEROUS_LEADING_CHARS.indexOf(convert.charAt(0)) >= 0;
}
```

调用点：`OpenScanServiceImpl` 11 处（license 导出、表头、社区统计导出、PDF 导出辅助）与 `LicenseServiceImpl` 7 处（license 表格导出），共 18 处，均调用 `transData(value)` 单次；`insertScanIssue` 不再双重调用。

## 涉及文件

| 文件                                                                              | 操作 | 说明                                                                       |
| --------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/utils/security/CSVInjection.java`      | 修改 | 移除正则、改为首字符集合判定；`transData` 改为单引号前缀；全角区间上界收窄 |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java` | 修改 | `insertScanIssue` 去掉外层重复 `transData` 调用                            |
| `src/test/java/com/openlibing/sca/analysis/utils/security/CSVInjectionTest.java`  | 修改 | 重写用例为前缀语义，新增幂等、换行、全角、NUL、`validate` 用例，共 11 个   |

## 风险 & 缓解

| 风险                                                                                          | 缓解                                                                                                   |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 导出文件出现可见单引号，用户认为数据被污染                                                    | 单引号是 OWASP 推荐的 CSV 中和标识；与"数据被截断"相比可逆性更好；如需零可见改动可改文本格式方案（D6） |
| 以 `'` 开头的合法原始数据被误判                                                               | `'` 不在危险集合内，不会二次前缀；`transData` 幂等可防重复处理                                         |
| 其他导出点（`LicenseServiceImpl`、PDF 辅助方法）仍直接使用 `transData` 单次调用，行为随之改变 | 统一函数调整，所有调用点自动生效；导出内容语义变化需在测试用例中确认                                   |
| 全角区间收窄导致部分冷僻全角符号不再转半角                                                    | 仅影响检测判定，前缀仍加在原始数据上；常用全角数字/字母/等号/at 仍在区间内                             |
| 仅靠 `transData` 覆盖，若新增导出路径绕过该函数仍有注入面                                     | 现有导出点均经 `CSVInjection.transData`；新增导出需沿用统一入口（可在评审中检查）                      |

## 跨仓影响

无。spec 文档归档 `openlibing-docs` 仓。

## 明确不在范围

- 单元格文本格式（DataFormat `@`）方案。
- 导出文件列宽/样式等展示层调整。
