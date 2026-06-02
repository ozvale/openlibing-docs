# Proposal: 修复抑制注释扫描的字符串字面量误识别

## 需求背景

`scanSuppressionComments` 方法用于代码提交（创建 PR 或在 PR 中提交代码）时检测提交代码中的三方检查工具告警抑制注释，并返回检测到的代码块和对应的工具、注释类型。

当前方法存在 bug：对非注释屏蔽的代码也会误识别为注释。例如 `PipelineDelegateImpl.submitCodeInspectionOpinions` 方法中的提示文本：

```java
"请在本地拉取最新代码并修正后重新提交，同时添加告警抑制（如# ruff: noqa，// clang-format off），避免提交时再次触发自动修改"
```

其中 `如# ruff: noqa` 和 `// clang-format off` 是提示文本中的示例，并非真正的抑制注释，但被错误识别。

## 根因

`scanAddedLines` 方法使用 `combinedPattern.find()` 在代码行中搜索告警抑制注释时，正则模式没有约束注释标记符（`#`、`//`、`/*`、`<!--`）必须出现在合法的注释位置。当标记符前面紧跟非空白字符（如中文字符）时，说明它在字符串字面量内部，不是真正的注释。

## 修复方案

在 `scanAddedLines` 方法中，匹配到抑制注释后增加位置校验：注释标记符必须位于行首或前面紧跟空白字符，否则跳过该匹配。

## 影响范围

- 仓库：`openlibing-codecheck`
- 模块：`SuppressionScanServiceImpl.scanAddedLines`
- 接口变化：无
- 数据模型变化：无

## 验收标准

1. 字符串字面量中的抑制注释示例（如 `如# ruff: noqa`、`（// clang-format off`）不被误识别
2. 真实的抑制注释（行首或空白后跟注释标记符）仍能正确匹配
3. 现有测试全部通过
4. 新增测试用例覆盖误识别场景

## 关联

- 业务 Issue: openlibing/openlibing-codecheck#110
- 业务 PR: openlibing/openlibing-codecheck#198
