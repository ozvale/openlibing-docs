# Tasks: 修复 extractSimpleCodeSnippet 上下文范围计算

## 实现步骤

- [x] 分析 bug 根因：`extractSimpleCodeSnippet` 使用列表索引而非实际行号计算上下文范围
- [x] 修改 `extractSimpleCodeSnippet` 方法：基于实际行号（`addedLineNumbers`）筛选上下文行
- [ ] 补充/更新单元测试覆盖稀疏行号场景
- [ ] 运行相关测试验证修复
- [ ] 提交 commit

## 修改文件清单

| 文件 | 变更说明 |
|------|---------|
| `SuppressionScanServiceImpl.java` | `extractSimpleCodeSnippet` 上下文范围从列表索引改为实际行号 |

## 验证方式

- 单元测试：覆盖稀疏行号场景（新增行行号间隔大于 2 时，snippet 不包含无关行）
- 手动验证：CREATE 事件中 snippet 只返回匹配行 ±2 行号范围内的代码
