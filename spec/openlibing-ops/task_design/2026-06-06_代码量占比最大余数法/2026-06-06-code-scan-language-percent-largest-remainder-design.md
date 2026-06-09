# 代码量占比计算：四舍五入改为最大余数法

## 问题背景

当前代码量占比计算使用 `RoundingMode.HALF_UP`（四舍五入）逐项计算百分比，导致各语言占比之和可能不等于 100%。

### 问题代码

文件：`DwiCodeScanLanguageServiceImpl.java` 第 176-183 行

```java
private BigDecimal calculatePercentage(int part, int total) {
    if (total == 0) {
        return BigDecimal.ZERO;
    }
    return BigDecimal.valueOf(part)
        .divide(BigDecimal.valueOf(total), 4, RoundingMode.HALF_UP)
        .multiply(BigDecimal.valueOf(100))
        .setScale(2, RoundingMode.HALF_UP);
}
```

### 问题举例

3 种语言代码行分别为 100、100、100，总计 300 行：

| 语言 | 精确占比 | 四舍五入后 |
|------|----------|-----------|
| Java | 33.333...% | 33.33% |
| Python | 33.333...% | 33.33% |
| Go | 33.333...% | 33.33% |
| **合计** | 100.00% | **99.99%** |

## 修改方案：最大余数法（Largest Remainder Method）

### 算法原理

1. 计算每项的**精确百分比**（不截断）
2. 对每项取**地板值**（向下取整到 2 位小数）
3. 计算地板值之和与目标值（100.00）的**差值**
4. 按每项的**余数**（精确值 - 地板值）从大到小排序
5. 将差值按 `0.01` 为单位，依次分配给余数最大的项

### 算法示例

输入：100、100、100，scale=2

| 步骤 | Java | Python | Go |
|------|------|--------|-----|
| 精确值 | 33.3333 | 33.3333 | 33.3333 |
| 地板值 | 33.33 | 33.33 | 33.33 |
| 余数 | 0.0033 | 0.0033 | 0.0033 |
| 差值 | - | - | - |

地板值之和 = 99.99，目标 = 100.00，差值 = 0.01，需分配 1 个 0.01。

余数相同，按原始顺序第一个（Java）优先分配 → Java = 33.34，其余 = 33.33，合计 = 100.00。

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `NumberUtil.java` | 新增 `distributeByLargestRemainder` 静态工具方法 |
| `DwiCodeScanLanguageServiceImpl.java` | 修改 `calculatePercentages` 方法，改用最大余数法；删除 `calculatePercentage` 私有方法 |
| `NumberUtilTest.java` | 新增 `distributeByLargestRemainder` 的单元测试 |

## 详细设计

### 1. NumberUtil 新增方法

```java
/**
 * 最大余数法分配百分比，保证各项占比之和精确等于 100.00
 *
 * @param values 各项的值
 * @param scale  百分比保留小数位数（通常为 2）
 * @return 各项百分比列表，顺序与输入一致，求和 = 10^scale
 */
public static List<BigDecimal> distributeByLargestRemainder(List<Integer> values, int scale)
```

核心逻辑伪代码：

```
total = sum(values)
if total == 0:
    return [0.00, 0.00, ...]  // 与输入等长

target = 10^scale  // scale=2 时为 100

for each value:
    exact = value * target / total       // 精确百分比（高精度）
    floor = floor(exact, scale)          // 地板值
    remainder = exact - floor            // 余数

diff = target - sum(floor_values)        // 差值（以 0.01 为单位）

按余数降序排列索引，前 diff 个索引的 floor 值 +0.01

返回结果列表（保持原始顺序）
```

### 2. DwiCodeScanLanguageServiceImpl 修改

将 `calculatePercentages` 方法中三组百分比（codeLines / commentLines / blankLines）的逐项 `calculatePercentage` 调用，替换为对每组分别调用 `NumberUtil.distributeByLargestRemainder`：

```java
private List<DwiCodeScanLanguageDetailResp> calculatePercentages(
        List<DwiCodeScanLanguage> codeScanLanguages,
        DwiCodeScanLanguageDetailResp summaryResp) {

    List<Integer> codeLineValues = codeScanLanguages.stream()
        .map(l -> Optional.ofNullable(l.getCodeLines()).orElse(0))
        .collect(Collectors.toList());
    List<Integer> commentLineValues = codeScanLanguages.stream()
        .map(l -> Optional.ofNullable(l.getCommentLines()).orElse(0))
        .collect(Collectors.toList());
    List<Integer> blankLineValues = codeScanLanguages.stream()
        .map(l -> Optional.ofNullable(l.getBlankLines()).orElse(0))
        .collect(Collectors.toList());

    int totalCodeLines = Optional.ofNullable(summaryResp.getCodeLines()).orElse(0);
    int totalCommentLines = Optional.ofNullable(summaryResp.getCommentLines()).orElse(0);
    int totalBlankLines = Optional.ofNullable(summaryResp.getBlankLines()).orElse(0);

    List<BigDecimal> codeLinePercentages = totalCodeLines > 0
        ? NumberUtil.distributeByLargestRemainder(codeLineValues, 2)
        : Collections.nCopies(codeScanLanguages.size(), BigDecimal.ZERO);
    List<BigDecimal> commentLinePercentages = totalCommentLines > 0
        ? NumberUtil.distributeByLargestRemainder(commentLineValues, 2)
        : Collections.nCopies(codeScanLanguages.size(), BigDecimal.ZERO);
    List<BigDecimal> blankLinePercentages = totalBlankLines > 0
        ? NumberUtil.distributeByLargestRemainder(blankLineValues, 2)
        : Collections.nCopies(codeScanLanguages.size(), BigDecimal.ZERO);

    List<DwiCodeScanLanguageDetailResp> respList = new ArrayList<>();
    for (int i = 0; i < codeScanLanguages.size(); i++) {
        DwiCodeScanLanguageDetailResp resp = new DwiCodeScanLanguageDetailResp(codeScanLanguages.get(i));
        resp.setCodeLinesPercentage(codeLinePercentages.get(i));
        resp.setCommentLinesPercentage(commentLinePercentages.get(i));
        resp.setBlankLinesPercentage(blankLinePercentages.get(i));
        respList.add(resp);
    }
    return respList;
}
```

原有的 `calculatePercentage` 私有方法删除（不再使用）。

### 3. 单元测试覆盖

| 测试场景 | 输入 | 预期 |
|----------|------|------|
| 等分场景 | (100, 100, 100) | 求和 = 100.00 |
| 不等分 | (1, 1, 1, 97) | 求和 = 100.00 |
| 余数竞争 | (1, 1, 2) | 求和 = 100.00，余数大的优先 |
| 单项 | (100) | 100.00 |
| 含零值 | (0, 50, 50) | 求和 = 100.00，0 值对应 0.00 |
| 全零 | (0, 0, 0) | 全部 0.00 |
| 大量项 | 10 项随机值 | 求和 = 100.00 |

## 不变范围

- 响应类 `DwiCodeScanLanguageDetailResp` 无需修改（字段类型不变，仍为 `BigDecimal`）
- 其他使用 `RoundingMode.HALF_UP` 的场景（如 `ResourceService` 的 passRate 计算）不在本次修改范围，因为那些是单个百分比值，不存在"多项求和"的问题

## 验证方式

1. 单元测试：`NumberUtilTest` 中新增测试用例全部通过
2. 手动验证：调用代码扫描语言占比接口，确认各语言占比之和 = 100.00%
