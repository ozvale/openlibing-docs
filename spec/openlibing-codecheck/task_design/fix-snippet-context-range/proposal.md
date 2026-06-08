# Proposal: 修复 suppression 扫描 snippet 上下文范围计算

## 需求背景

`SuppressionScanServiceImpl.extractSimpleCodeSnippet` 方法用于从 diff 新增行中提取代码片段（snippet），展示 suppression 注释所在行的上下文代码。原实现存在两个问题：

1. **使用列表索引而非实际行号**：原实现用 `currentIndex +/- 2` 的列表索引来确定上下文范围，但 `addedLines` 仅包含 diff 中的新增行，这些行在源文件中是稀疏分布的。当新增行之间间隔较大时（如相隔数百行），会将不相关的代码行包含在 snippet 中。

2. **空行作为上下文无意义**：修复第一个问题后，基于实际行号取 ±2 范围内的行，但如果这些行中存在空行，空行作为代码上下文没有信息价值，应跳过并扩展到同方向最近的非空行。

## 验收标准

- [ ] snippet 上下文范围基于实际行号计算，不因新增行稀疏分布而引入无关行
- [ ] 上下文行中的空行被跳过，替换为同方向最近的非空行
- [ ] 扩展距离有上限（contextRange + 2），避免引入过远的无关代码
- [ ] 匹配行本身（currentIndex）不被跳过
- [ ] 已有功能不受影响：snippet 仍包含匹配行高亮、Markdown 转义等

## 关联 Issue

- openlibing/openlibing-codecheck#111
