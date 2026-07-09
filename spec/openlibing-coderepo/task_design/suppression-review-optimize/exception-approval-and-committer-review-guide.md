# 例外备案与 Committer 审核一体化工程指导

## 适用范围

- 平台：GitCode / GitHub
- 目标读者：开发者（提交者）、Committer（审核者）

---

## 1. 概述

代码检查工具在扫描代码时会发现告警。开发者有时需要通过抑制注释或注解临时屏蔽某些告警，常见原因包括误报、第三方代码无法修改、历史遗留暂不修复等。但抑制注释一旦滥用会掩盖真实问题，因此需要：

1. **自动识别**：openlibing.ci 自动扫描 PR 中的告警抑制注释，汇总为文件级评论表格
2. **例外备案**：开发者在 PR 描述中逐条说明抑制理由
3. **Committer 审核**：Committer 基于自动评论和开发者说明审核合理性

---

## 2. 支持的告警抑制注释语法

openlibing.ci 当前支持识别以下工具的抑制注释/注解：

### 2.1 Python 工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **flake8** | `# noqa`、`# noqa: E501`、`# flake8: noqa` | `import os  # noqa: F401` |
| **ruff** | `# noqa`、`# ruff: disable[RULE]`、`# fmt: skip`、`# fmt: off` | `import os  # ruff: disable[F401]` |
| **mypy** | `# type: ignore`、`# type: ignore[CODE]`、`# mypy: disable-error-code="CODE"` | `x: int = "str"  # type: ignore[assignment]` |
| **pylint** | `# pylint: disable=RULE`、`# pylint: disable-next=RULE`、`# pylint: skip-file` | `x = 1  # pylint: disable=invalid-name` |
| **Bandit** | `# nosec`、`# nosec B101, B601` | `eval(expr)  # nosec B307` |
| **codespell** | `# codespell:ignore WORD` | `# codespell:ignore someword` |
| **detect-secrets** | `# pragma: allowlist secret`、`// pragma: allowlist-nextline secret` | `API_KEY = "xxx"  # pragma: allowlist secret` |
| **semgrep** | `# nosemgrep`、`# nosemgrep: RULE_ID`、`// nosemgrep: RULE_ID` | `eval(x)  # nosemgrep: python.lang.security.audit.eval-detected` |

### 2.2 Java 工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **PMD** | `// NOPMD`、`// NOPMD <reason>`、`@SuppressWarnings("PMD.RuleName")` | `int x = 200;  // NOPMD business port` |
| **checkstyle** | `// SUPPRESS CHECKSTYLE`、`// CHECKSTYLE:OFF` | `// SUPPRESS CHECKSTYLE LineLength` |
| **SpotBugs** | `@SuppressFBWarnings(value="RULE", justification="reason")` | `@SuppressFBWarnings(value="MS_SHOULD_BE_FINAL")` |
| **spotless** | `// spotless:off` | `// spotless:off`（仅识别起始标记） |

> **checkstyle 说明**：`// SUPPRESS CHECKSTYLE` 和 `// CHECKSTYLE:OFF` 在 Java 文件中写在 `//` 注释内是合法用法；在 `.sh`、`.properties` 等非 Java 文件中，`# // CHECKSTYLE:OFF` 写在 `#` 注释内也是合法用法（`//` 是字面量，非注释前缀）。

### 2.3 C/C++ 工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **clang-tidy** | `// NOLINT`、`// NOLINTNEXTLINE(rule)`、`// NOLINTBEGIN`/`NOLINTEND` | `auto x = cast<int>(y);  // NOLINT(cppcoreguidelines-pro-type-vararg)` |
| **clang-format** | `// clang-format off`、`/* clang-format off */` | `// clang-format off` |

### 2.4 JavaScript/TypeScript/CSS 工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **ESLint** | `// eslint-disable RULE`、`// eslint-disable-next-line RULE`、`/* eslint-disable RULE */`、`/* eslint-disable-line RULE */`、`/* eslint-disable-next-line RULE */` | `console.log(x);  // eslint-disable-next-line no-console` |
| **Prettier** | `// prettier-ignore`、`/* prettier-ignore */`、`# prettier-ignore`、`<!-- prettier-ignore -->`、`! prettier-ignore`、`<!-- prettier-ignore-start -->`、`<!-- prettier-ignore-attribute -->` | `/* prettier-ignore */` |
| **stylelint** | `/* stylelint-disable RULE */`、`/* stylelint-disable-line RULE */`、`/* stylelint-disable-next-line RULE */` | `/* stylelint-disable-next-line color-hex-length */` |

### 2.5 Go 工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **golangci-lint** | `//nolint`、`//nolint:linter` | `var x = unsafe.Pointer(nil)  //nolint:unsafe` |
| **gitleaks** | `gitleaks:allow` | `API_KEY = "xxx"  # gitleaks:allow` |

> **gitleaks 说明**：`gitleaks:allow` 可出现在行内任意位置（含非注释中），用于标记该行不进行密钥检测。

### 2.6 Shell/Docker 工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **ShellCheck** | `# shellcheck disable=SCXXXX` | `# shellcheck disable=SC2086` |
| **hadolint** | `# hadolint ignore=DLXXXX`、`# hadolint global ignore=DLXXXX` | `# hadolint ignore=DL3008` |

### 2.7 Rust 工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **rustfmt** | `#![rustfmt::skip]`（文件级）、`#[rustfmt::skip]`（行级/块级）、`#[cfg_attr(..., rustfmt::skip)]` | `#[rustfmt::skip]` |
| **clippy** | `#![allow(clippy::RULE)]`（文件级）、`#[allow(clippy::RULE)]`（行级/块级）、`#[expect(clippy::RULE)]` | `#[allow(clippy::unnecessary_wraps)]` |

### 2.8 通用工具

| 工具 | 抑制语法 | 示例 |
|------|---------|------|
| **CodeQL** | `// lgtm`、`// lgtm[RULE]`、`# lgtm`、`# lgtm[RULE]`、`// codeql[RULE]` | `// lgtm[cpp/constant-comparison]` |

---

## 3. 开发者指南

### 3.1 何时应该使用抑制注释

✅ 合理场景：误报、第三方代码、生成的代码、历史遗留暂不修复、团队讨论确认的写法

### 3.2 何时不应使用抑制注释

❌ 不合理场景：图省事不想修、未分析就抑制、大范围抑制（如整个方法）、永久抑制从不回顾

### 3.3 最佳实践

**附带理由**：`// NOPMD 使用魔法值 200 是业务协议端口` 优于 `// NOPMD`

**最小化范围**：精确抑制单行/单规则，避免抑制整个方法或全规则

**指定规则名**：`@SuppressWarnings("PMD.AvoidMagicNumbers")` 优于 `@SuppressWarnings("PMD")`

### 3.4 在 PR 描述中备案

提交 PR 时，在描述中包含"例外备案"小节，逐条说明每条抑制注释的理由：

```markdown
## 例外备案

1. **src/main/NetworkConfig.java:42** `// NOPMD` — PMD — 端口号是 HTTP 标准端口，无需配置化
2. **src/main/LegacyParser.java:88** `@SuppressWarnings("unchecked")` — SpotBugs — 历史代码，下个迭代重构
```

---

## 4. Committer 审核标准

### 4.1 审核入口

Committer 在 PR 检视时，会看到 openlibing.ci 自动下发的文件级评论：

```
【openlibing.ci】PR中识别到代码检查告警抑制 3 处，详情见下表，请Committer检视合理性。

| 文件路径 | 行号 | 代码片段 | 工具 |
|---------|------|---------|------|
| src/main/NetworkConfig.java | [42](url#L42) | `// NOPMD` | PMD |
| src/main/LegacyParser.java | [88](url#L88) | `@SuppressWarnings("unchecked")` | SpotBugs |
| src/test/MockData.java | [15](url#L15) | `// NOPMD` | PMD |
```

点击行号链接可跳转到对应代码行。

### 4.2 审核维度

| 维度 | 通过标准 | 驳回标准 |
|------|---------|---------|
| **合理性** | 理由成立 | 无理由或理由不成立 |
| **必要性** | 确需抑制，无更好方案 | 可修改代码消除告警 |
| **范围** | 最小化（单行/单规则） | 大范围（整个方法/全规则） |
| **可追溯** | PR 描述有对应备案条目 | 无备案 |
| **时效性** | 临时抑制有修复计划 | 临时抑制无修复计划 |

### 4.3 审核决策

| 决策 | 说明 |
|------|------|
| ✅ **通过** | 抑制合理 |
| ⚠️ **要求修改** | 需调整（缩小范围、补充理由） |
| ❌ **驳回** | 不合理，必须移除并修复告警 |

---

## 5. 自动化检视机制

### 5.1 触发时机

| 事件 | 行为 |
|------|------|
| PR 创建/重新打开 | 全量扫描 PR 修改文件，下发文件级评论 |
| PR 推送更新 | 全量重扫，PATCH 编辑已有评论（不新增评论，不刷屏） |

### 5.2 评论形态

- 评论挂在 PR 第一个修改文件上（GitCode: `position_type=binary`，GitHub: `subject_type=file`）
- 所有抑制注释汇总为一个表格，列含文件路径、行号（带跳转链接）、代码片段、工具
- 单条评论超 65535 字符自动拆分多条

### 5.3 平台支持

| 平台 | 评论方式 | 认证方式 |
|------|---------|---------|
| GitCode | `position_type=binary` | `PRIVATE-TOKEN` |
| GitHub | `subject_type=file` | `Authorization: Bearer` |

---

## 6. 常见问题

### 抑制注释未识别

1. 检查语法是否符合第 2 节规范
2. 检查文件是否在 PR 修改范围内
3. 检查工具是否在支持列表中

### 评论丢失/未出现

1. 检查代码仓是否开启了"告警抑制自动检视"开关
2. 检查 webhook 是否配置成功
3. 检查项目 token 是否有效

### 评论未更新

1. 确认推送是有效代码变更（GitCode: `source update`，GitHub: `synchronize`）
2. 检查评论是否被手动删除（会自动降级为新建）

---

## 修订记录

| 日期 | 版本 | 修订内容 |
|------|------|---------|
| 2026-07-09 | v2.0 | 全面对齐 SuppressionStrategy 支持的工具和语法；移除 Gitee 平台；精简为用户导向文档 |
| 2026-07-02 | v1.0 | 初版发布 |
