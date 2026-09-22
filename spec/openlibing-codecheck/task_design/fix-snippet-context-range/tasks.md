# Tasks: 修复 suppression 扫描 snippet 上下文范围计算

## 任务清单

- [x] T1: 将上下文范围计算从列表索引改为实际行号
  - 文件: `SuppressionScanServiceImpl.java`
  - 改动: `extractSimpleCodeSnippet` 方法中，用 `addedLineNumbers.get(i)` 的实际行号与 `currentLineNum` 的差值判断是否在 ±2 范围内，替代原来的列表索引偏移
  - commit: `b86cb29a fix(suppression): use actual line numbers for snippet context range`

- [x] T2: 跳过空行上下文并扩展到非空行
  - 文件: `SuppressionScanServiceImpl.java`
  - 改动:
    - 第一轮遍历：收集 ±2 范围内的非空行索引，跳过空行
    - 第二轮遍历：对每个被跳过的空行，调用 `findNonBlankLineInDirection` 向同方向查找最近非空行，扩展距离限制在 contextRange + 2
    - 新增 `findNonBlankLineInDirection` 辅助方法：从指定行号出发，沿指定方向查找最近的非空行号
    - 按行号排序输出 snippet
  - commit: `6caed88d fix(suppression): skip blank lines in snippet context and expand to non-blank lines`

- [x] T3: 补充单元测试
  - 文件: `SuppressionScanServiceImplTest.java`
  - 改动:
    - `testScanSuppressionComments_SparseLineNumbers_SnippetExcludesDistantLines`: 验证稀疏行号场景下 snippet 不包含远距离行
    - `testScanSuppressionComments_BlankContextLines_SkippedAndExpanded`: 验证空行上下文被跳过，snippet 中不包含空行
  - commit: 包含在 T1 和 T2 的 commit 中

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `SuppressionScanServiceImpl.java` | 修改 | 重构 `extractSimpleCodeSnippet`，新增 `findNonBlankLineInDirection` |
| `SuppressionScanServiceImplTest.java` | 新增 | 新增稀疏行号和空行上下文的测试用例 |

## 验证方式

- IDE 诊断：无语法/类型错误
- 单元测试：新增测试覆盖稀疏行号和空行场景
- 功能验证：suppression 扫描结果中代码片段上下文行正确，不含空行和远距离无关行
