# Proposal: 修复 extractSimpleCodeSnippet 上下文范围计算错误

## 需求背景

`SuppressionScanServiceImpl.extractSimpleCodeSnippet` 方法在提取代码片段时，使用列表索引（`currentIndex ± 2`）来确定上下文范围。由于 `addedLines` 列表只包含 diff 中的新增行，这些行在实际文件中是稀疏分布的，导致索引 ±2 会跨越数百行甚至更多，把无关代码纳入 snippet。

该问题同时影响 CREATE 和 UPDATE 两种事件类型，因为两条路径最终都调用同一个 `extractSimpleCodeSnippet` 方法。

## 验收标准

1. `extractSimpleCodeSnippet` 返回的 snippet 只包含实际行号在匹配行 ±2 范围内的新增行
2. CREATE 和 UPDATE 事件类型均正确
3. 当新增行紧密排列（行号连续）时，snippet 仍包含前后各 2 行上下文
4. 当匹配行在列表边界时，不会越界或遗漏

## 关联 Issue

openlibing/openlibing-codecheck#111
