# suppression-tools-extension — 实现任务

## 进度: 8/8 complete

### 核心改动

- [x] Task 1: 在 `SuppressionStrategy` 新增 11 个工具枚举（typos/detect-secrets/gitleaks/pylint/Bandit/checkstyle/PMD/SpotBugs/spotless/rustfmt/clippy），枚举数 14→25
- [x] Task 2: `SuppressionPattern` 内部类新增 `skipValidation` 布尔字段，新增三参构造函数
- [x] Task 3: `MatchResult` record 新增 `skipValidation` 参数，保留两参构造函数兼容旧调用
- [x] Task 4: 新增 `identifyAllToolsAndTypes` 方法，返回 `List<MatchResult>`，支持多工具匹配同一注释（如 `# noqa` 同时匹配 flake8 和 ruff），同一工具多 pattern 命中只取第一个
- [x] Task 5: 移除所有成对块级注释的 END 标记正则（NOLINTEND/eslint-enable/prettier-ignore-end 等），原 `BLOCK_PAIRED` 起始标记统一改为 `LINE`
- [x] Task 6: CodeQL 按汇总表修正为 `// lgtm` / `# lgtm` / `// codeql [rule]` 行级语法
- [x] Task 7: detect-secrets 精确匹配 6 种注释前缀（`#`、`//`、`/*...*/`、`'`、`--`、`<!-- ... -->`）
- [x] Task 8: gitleaks 新增 `skipValidation=true`，跳过嵌套校验（可出现在行内任意位置）

### SuppressionScanServiceImpl 改动

- [x] Task 9: 新增 `TYPOS_CONFIG_PATTERN`、`isTyposConfigFile`、`buildTyposResult`，在 `processDiffFile` 和 `processCompareFile` 中插入 typos 配置文件检测逻辑
- [x] Task 10: `scanAddedLines` 方法调整，支持 `skipValidation` 标志判断和多工具结果生成
- [x] Task 11: 移除全部块级处理逻辑（`BlockCommentContext`/`processPairedBlockComment`/`handleBlockStart/End`/`findMatchingStartMarker/EndMarker`/`extractBlockCodeSnippet`/`isInvalidBlockOrFileComment`），改为对每个匹配工具生成独立结果

### 测试

- [x] Task 12: `SuppressionStrategyTest` 适配枚举数 14→25，新增多工具匹配/CodeQL/detect-secrets/gitleaks 测试
- [x] Task 13: `SuppressionScanServiceImplTest` 适配新行为（块级/文件级注释不再要求行首、`# noqa` 返回 2 个结果），新增 typos 配置文件检测测试

### 验证

- [x] Task 14: 编译通过（`mvn compile`）
- [x] Task 15: 相关单元测试全部通过（`SuppressionStrategyTest` + `SuppressionScanServiceImplTest`）
