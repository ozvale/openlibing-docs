# Proposal：静态代码分析工具 bandit 接入 GitHub Actions

## 需求背景

openLiBing 代码检查链路原以 GitCode Actions 为主：静态分析工具产出 SARIF → `upload-sarif-action` 上传 OBS → 回调平台 → 「开发管理 - 代码检查」页展示。FE 需求「静态代码分析 GitHub 接入」已由 clang-tidy 完成首个落地，沉淀了可复用范式：`GITHUB_ACTION` 来源枚举、前端平台筛选与来源标签、双插件（`upload-sarif-action` / `pre-commit-action`）的平台识别与 OIDC 免密换证。gosec、clippy、eslint 已先后复制该范式。

本 US 将该范式复制到 Python 安全静态扫描工具 **bandit**（基于 AST 检测硬编码密码、命令注入、不安全反序列化、弱哈希、关闭证书校验等风险），补齐 Python 技术栈覆盖。

## 需求范围

- 新建 GitHub 演示仓 `bandit-full-scan-demo`（openlibing-test 组织，私仓）：被扫样例 + 规则单一事实源 + 全量扫描 / pre-commit 双工作流；
- bandit 原生 SARIF 直出接入既有上传回调链路；
- 设计文档归档 openlibing-docs（本 spec）。

## 非目标

- 不改动 `upload-sarif-action` / `pre-commit-action` / openlibing-codecheck 后端 / openlibing-web 前端（能力复用 clang-tidy US 交付成果）；
- 不含 docs 用户文档（bandit README 小节与 demos 示例，属后续 US）；
- 不调整正式环境 APIG 域名与 IAM 策略。

## 验收标准

1. GitHub 平台可运行的 bandit 流水线，覆盖 **workflow 全量扫描** 与 **pre-commit 集成** 两种入口，两条工作流均 success；
2. bandit 原生 SARIF 直出（零转换器、零预置二进制），上传 OBS 桶 `openlibing-github-action` 并回调 openLiBing，回调返回 200；
3. 全链路日志核对通过：来源标记 `GITHUB_ACTION`、OIDC 换证提供商 `GitHubActions` / 委托 `github-actions`、原生 SARIF 无兜底解析；
4. 检出口径自洽且 CI 可复现：全仓 12 条问题 / 12 类规则（insecure_demo 9 类 + high_risk_demo 3 类，safe_demo 零检出），高危样例恰好 3 条 HIGH/HIGH（B605/B701/B501）；
5. beta「代码检查」页按 GitHub 平台可筛选查看 bandit 问题列表、真实行号、源码片段与严重度标记（前端零改动，人工目检确认）；
6. GitHub 侧差异经验（插件参数兼容性、bandit 配置格式约束）沉淀到设计文档与项目记忆，供后续工具接入复用。

## 关联

- FE 需求：https://gitcode.com/openlibing/code-metrics-action/issues/74
- 演示仓：https://github.com/openlibing-test/bandit-full-scan-demo
