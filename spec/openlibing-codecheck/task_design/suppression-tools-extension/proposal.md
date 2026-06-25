# suppression-tools-extension

## 需求背景

openlibing-codecheck 的 `SuppressionStrategy` 已支持 14 个开源代码检查工具的告警抑制注释识别（flake8、ruff、mypy 等）。PR 门禁扫描时，识别到新增代码中的告警抑制注释后，会在 PR 评论中提示 committer 关注。

根据"代码检查工具告警抑制注释汇总"表，还有 11 个常用工具的抑制注释未被识别：typos、detect-secrets、gitleaks、pylint、Bandit、checkstyle、PMD、SpotBugs、spotless、rustfmt、clippy。这些工具覆盖拼写检查、密钥扫描、Python/Java/Rust lint 等场景，社区 PR 中已出现使用这些注释抑制告警的情况，但 codecheck 无法识别，导致 committer 无法在 PR 评论中看到这些抑制行为。

此外，原实现对成对块级注释（如 `# pylint: disable` ... `# pylint: enable`）会将两个注释中间的整个 diff 块一起提交代码检视，如果用户修改了 diff 块中的非注释行代码，检视意见会变为已过期，失去对 committer 的提示作用。

## 功能描述

1. **新增 11 个工具的告警抑制注释识别**（14→25）：typos、detect-secrets、gitleaks、pylint、Bandit、checkstyle、PMD、SpotBugs、spotless、rustfmt、clippy。
2. **简化块级注释处理**：对所有工具（含已有的），不再区分行级/块级/文件级，全部按告警抑制处理，只返回注释/注解所在行。移除成对块级注释的 END 标记识别和中间代码块的合并逻辑。
3. **gitleaks 特殊处理**：`gitleaks:allow` 可出现在行内任意位置（甚至非注释中），新增 `skipValidation` 字段跳过"嵌套在字符串/注释中则无效"的校验。
4. **多工具匹配同一注释**：如 `# noqa` 同时匹配 flake8 和 ruff，`identifyAllToolsAndTypes` 返回 `List<MatchResult>`，全部返回供 coderepo 在评论中列出多个工具。
5. **typos 配置文件检测**：typos 通过 `_typos.toml` 配置文件抑制拼写告警，无代码内注释，识别到配置文件即视为告警抑制。
6. **CodeQL 注释修正**：按汇总表修正为 `// lgtm`、`# lgtm`、`// codeql [rule]` 等行级语法。
7. **detect-secrets 精确匹配**：精确匹配 6 种注释前缀（`#`、`//`、`/*...*/`、`'`、`--`、`<!-- ... -->`），不使用模糊匹配。

## 不做什么

- 不处理 typos 的用户自定义配置场景（仅识别 `_typos.toml` 配置文件本身）。
- 不识别 PMD 通用形式的 `@SuppressWarnings`（仅识别含 `"PMD"` 前缀的注解，避免与 Java 原生冲突）。
- 不修改前端页面、DB schema、API 接口定义。
- 不修改 coderepo 仓的评论生成逻辑（coderepo 侧已支持多工具评论，本次仅扩展 codecheck 的识别能力）。

## 验收标准

- [ ] `SuppressionStrategy` 枚举数从 14 扩展到 25，新增 11 个工具的正则识别规则
- [ ] typos 配置文件（`_typos.toml` / `typos.toml`）被识别为告警抑制，无需行扫描
- [ ] gitleaks 的 `gitleaks:allow` 可在行内任意位置被识别（跳过嵌套校验）
- [ ] `# noqa` 同时匹配 flake8 和 ruff，两个工具均返回
- [ ] 成对块级注释（如 `//CHECKSTYLE:OFF`）只识别起始标记，不再合并中间代码块
- [ ] CodeQL 按 `// lgtm` / `# lgtm` / `// codeql [rule]` 识别
- [ ] detect-secrets 精确匹配 6 种注释前缀，不误识别
- [ ] PMD 仅识别含 `"PMD"` 前缀的 `@SuppressWarnings`
- [ ] 编译通过，相关单元测试全部通过

## 影响范围

### 业务仓 `openlibing-codecheck`

| 文件 | 操作 | 说明 |
|------|------|------|
| `common/enums/SuppressionStrategy.java` | 修改 | 新增 11 个工具枚举；`SuppressionPattern` 新增 `skipValidation` 字段；`MatchResult` record 新增 `skipValidation`；`identifyToolAndType` 改为 `identifyAllToolsAndTypes` 返回 `List<MatchResult>` |
| `business/service/impl/SuppressionScanServiceImpl.java` | 修改 | 新增 typos 配置文件检测；`scanAddedLines` 支持 `skipValidation` 和多工具结果；移除全部块级处理逻辑 |

### docs 仓 `openlibing-docs`

| 文件 | 操作 | 说明 |
|------|------|------|
| `spec/openlibing-codecheck/task_design/suppression-tools-extension/proposal.md` | 新增 | 本文件 |
| `spec/openlibing-codecheck/task_design/suppression-tools-extension/design.md` | 新增 | 技术设计 |
| `spec/openlibing-codecheck/task_design/suppression-tools-extension/tasks.md` | 新增 | 实现任务清单 |

## 关联 Issue

- 业务 Issue: https://gitcode.com/openlibing/openlibing-codecheck/issues/127
- 业务 PR: https://gitcode.com/openlibing/openlibing-codecheck/merge_requests/229
