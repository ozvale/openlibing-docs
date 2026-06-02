# Tasks: 修复抑制注释扫描的字符串字面量误识别

## 实现步骤

- [x] 分析 bug 根因：`scanAddedLines` 中 `combinedPattern.find()` 未校验注释标记符位置
- [x] 修改 `scanAddedLines` 方法：匹配到抑制注释后，校验注释标记符必须位于行首或前面紧跟空白字符
- [x] 添加测试用例：验证字符串字面量中的抑制注释示例不被误识别
- [x] 添加测试用例：验证真实注释仍能正确匹配，且同一行中字符串字面量不影响真实注释匹配
- [x] 运行全部测试验证修复
- [x] 提交 commit 并创建业务 PR

## 修改文件清单

| 文件 | 变更说明 |
|------|---------|
| `SuppressionScanServiceImpl.java` | `scanAddedLines` 增加注释标记符位置校验 |
| `SuppressionScanServiceImplTest.java` | 新增 2 个测试用例覆盖误识别场景 |

## 验证方式

- 单元测试：`SuppressionScanServiceImplTest` 全部 6 个用例通过
- 手动验证：字符串 `如# ruff: noqa` 中的 `# ruff: noqa` 不被匹配
