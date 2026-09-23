# 安全威胁分析报告：sca-action

| 项 | 内容 |
|---|---|
| 仓库路径 | `D:\skill\skill收集\repo\sca-action` |
| 分析日期 | 2026-09-02 |
| 分析方法 | 静态代码审计（STRIDE-A 威胁建模 + 配置/供应链检查） |
| 报告语言 | 中文 |
| 部署分类 | CI/CD 插件（GitCode Action，`runs.using: node16`），在流水线 Runner 上执行 |

---

## 一、系统概述

### 1.1 用途与技术栈

该仓库是 **SCA（软件成分分析）PR 扫描 Action**：PR 场景下调用远程 SCA 服务（`/scan/pr`、`/scan/result`、`/open/scan/scanIssue/queryAll`）创建扫描任务、轮询结果、查询问题明细，将结果写入 Step Summary（Markdown 表格），并按风险阻断 PR。

- 语言：Node.js（内置 `https`/`fs`/`path`/`url`），无第三方运行时依赖
- 入口：`actions/sca-pr-action/action.yml:35-36` → `dist/sca-pr-scan.js`（`Sca` 类）
- 签名：`dist/signer.js`（华为云 HMAC-SHA256）
- 输出：写入 `ATOMGIT_STEP_SUMMARY` 文件，在流水线/PR 页面渲染

### 1.2 组件与信任边界

| 组件 ID | 锚点 | 说明 | 信任边界 |
|---|---|---|---|
| ActionConfig | `actions/sca-pr-action/action.yml` | 输入 AK/SK、pr-id、repository-name、project-name（必填） | 仓库维护者 → Runner |
| ScaAction | `dist/sca-pr-scan.js` | 创建任务/轮询/查明细/写 Summary | Runner 进程内 |
| SummaryWriter | `dist/sca-pr-scan.js:226-230`（`appendSummary`/`appendIssueSummary`） | 将服务端返回数据写入 Markdown 报告 | Runner → 流水线页面（渲染边界） |
| Signer | `dist/signer.js` | HMAC-SHA256 签名 | Runner 进程内 |
| Workflow | `.gitcode/workflows/*.yml` | 触发器、secrets、self-hosted runner | 代码托管平台 → Runner |
| SCAService | 远程 SCA 后端（外部服务） | 扫描服务，返回组件/文件名/URL 等数据 | 外部边界 |
| ExternalActor | PR 提交者 / 评论者 / 被扫描仓库内容 | 不可信输入来源 | 外部攻击者 |

**关键信任边界**：① 外部 PR 内容/评论 → Runner（持有 AK/SK）；② 远程服务返回的、源自**被扫描仓库文件名与开源组件元数据**的字符串 → Step Summary Markdown 渲染（流水线/PR 页面）。

---

## 二、STRIDE-A 威胁分析汇总

| STRIDE 类别 | 威胁数 | 代表性威胁 |
|---|---|---|
| S 仿冒 | 1 | 第三方 Action 未固定版本可被替换 |
| T 篡改 | 4 | 评论注入 run 脚本；Step Summary Markdown 注入；node16 EOL；scanId 未编码拼 URL |
| R 抵赖 | 0 | — |
| I 信息泄露 | 2 | 响应体全量打印日志；AK/SK 长期凭据 |
| D 拒绝服务 | 1 | self-hosted runner 被任意 PR 占用 |
| E 权限提升 | 2 | pull_request_target + 检出 PR 代码 RCE；评论注入窃取 secrets |
| A 业务滥用 | 1 | 可反复触发扫描任务消耗后端配额 |

### 关键威胁场景

**场景 1（E）**：与 malicious-code-scan-action 相同——`pre-commit.yml` 使用 `pull_request_target` 在 self-hosted runner 上检出 PR merge commit 并执行仓库内钩子，外部 PR 可 RCE 并窃取 `ROBOT_TOKEN`。

**场景 2（T，本仓特有）**：被扫描仓库构造特殊文件名（如 `| [点击查看](http://evil) |`）或开源组件元数据 → SCA 服务端原样返回 → `appendSummary` 未转义直接拼接进 Markdown 表格（`dist/sca-pr-scan.js:221`）→ Step Summary 在 PR 页面渲染时表格断裂、注入任意链接/文本 → 钓鱼或伪造"扫描通过"结论。

---

## 三、安全发现明细

### 高危

#### FIND-01：`pull_request_target` + self-hosted runner 检出并执行不可信 PR 代码

| 属性 | 内容 |
|---|---|
| STRIDE | E |
| CWE | [CWE-266](https://cwe.mitre.org/data/definitions/266.html)；[CWE-913](https://cwe.mitre.org/data/definitions/913.html) |
| OWASP | A01:2025 – Broken Access Control |
| 利用前提 | 能提交 PR |
| 证据 | `.gitcode/workflows/pre-commit.yml:4`（pull_request_target）；`:15`（`runs-on: ["self-hosted", ...]`）；`:21`（检出 `merge_commit_sha`）；`:36`（`uses: openlibing-pre-commit-action`）；`.pre-commit-config.yaml:41,50` |
| 风险 | 外部 PR 提交者可在持有 `secrets.ROBOT_TOKEN` 的持久化自建 Runner 上执行任意代码。 |
| 修复建议 | 不可信 PR 改用 `pull_request`（无 secrets）；self-hosted runner 仅用于可信事件或改用 ephemeral runner；钩子固定使用基础分支配置。 |
| 修复成本 | 中 |

#### FIND-02：评论正文等事件字段未转义注入 `run:` 脚本

| 属性 | 内容 |
|---|---|
| STRIDE | T / E |
| CWE | [CWE-78](https://cwe.mitre.org/data/definitions/78.html) OS 命令注入 |
| OWASP | A03:2025 – Injection |
| 利用前提 | 能发表触发词评论（`sca-pr-scan`） |
| 证据 | `.gitcode/workflows/sca-pr-scan.yml:21` `echo "comment.body: ${{ atomgit.event.comment.body }}"`；该 Job 携带 `SCAN_ACCESS_KEY`/`SCAN_SECRET_KEY`（:30-31） |
| 风险 | 评论内容可注入 shell 命令，导致 AK/SK 泄露。 |
| 修复建议 | 事件字段一律通过 `env:` 传递，脚本内引用环境变量。 |
| 修复成本 | 低 |

### 中危

#### FIND-03：服务端返回数据未转义写入 Step Summary（Markdown/链接注入）

| 属性 | 内容 |
|---|---|
| STRIDE | T |
| CWE | [CWE-116](https://cwe.mitre.org/data/definitions/116.html) 输出编码/转义不当 |
| OWASP | A03:2025 – Injection |
| 利用前提 | 能控制被扫描仓库的文件名，或能影响 SCA 服务端返回数据 |
| 证据 | `dist/sca-pr-scan.js:221` `this.appendSummary('| ' + fileName + ' | ' + ... + ' | ' + url + ' | ' + file + ' |\n')`（fileName/vendor/component/version/url/file 均直接取自服务端 JSON，:202-220）；`:230` `fs.appendFileSync(summaryPath, content, 'utf8')`；报告链接 :272/:277 |
| 风险 | Step Summary 在流水线/PR 页面渲染 Markdown。特殊文件名可破坏表格结构并注入任意 Markdown 链接/文本，实施钓鱼或伪造扫描结论；若扫描服务被篡改影响面更大。 |
| 修复建议 | 写入前对 `|`、换行、`[`、`]`、`(`、`)` 等 Markdown 特殊字符转义；URL 做白名单（仅 openlibing 域名）；对单元格内容做长度限制。 |
| 修复成本 | 低 |

#### FIND-04：第三方 Action 未固定版本

- STRIDE：T ｜ CWE：[CWE-1357](https://cwe.mitre.org/data/definitions/1357.html) ｜ OWASP：A08:2025
- 证据：`sca-pr-scan.yml:28` `uses: sca-pr-scan`；`pre-commit.yml:18,24,30,36` 均无版本/SHA。
- 建议：固定到 tag + commit SHA。
- 修复成本：低

#### FIND-05：node16 运行时 EOL

- STRIDE：T ｜ CWE：[CWE-1104](https://cwe.mitre.org/data/definitions/1104.html) ｜ OWASP：A06:2025
- 证据：`action.yml:35` `using: 'node16'`。
- 建议：升级 node20 并重新打包验证。
- 修复成本：低

### 低危 / 信息

#### FIND-06：响应体全量打印日志 + scanId 未 URL 编码拼接

- STRIDE：I / T ｜ CWE：[CWE-532](https://cwe.mitre.org/data/definitions/532.html)、[CWE-116](https://cwe.mitre.org/data/definitions/116.html) ｜ OWASP：A09:2025
- 证据：`dist/sca-pr-scan.js:78`、`:118` 打印完整响应体；`:106` `statusUrl = ... + '/scan/result?scanId=' + this.scanId`（scanId 来自服务端，未编码）。
- 建议：日志脱敏；使用 `URL`/`URLSearchParams` 构造请求。
- 修复成本：低

#### FIND-07：缺少 package-lock.json，构建不可复现

- STRIDE：T ｜ CWE：[CWE-1357](https://cwe.mitre.org/data/definitions/1357.html) ｜ OWASP：A08:2025
- 证据：`package.json`（ncc 0.38.1 / adm-zip 0.5.16 / @actions/core 1.11.1），无 lock 文件。
- 建议：提交 lock 文件并使用 `npm ci`。
- 修复成本：低

#### FIND-08：工作流无最小权限声明，可覆盖参数未受限

- STRIDE：E / A ｜ CWE：[CWE-732](https://cwe.mitre.org/data/definitions/732.html) ｜ OWASP：A01:2025
- 证据：workflow 无 `permissions:` 段；`codecheck-ip`/`codecheck-prefix`/`platform-domain` 均可被 workflow 调用方覆盖（action.yml）；`project-name` 在 action.yml 标记 `required: true`（:32）而 README 标注"否"（README:37），文档/实现不一致。
- 建议：显式声明最小 `permissions:`；服务端校验请求来源与项目绑定；修正文档。
- 修复成本：低

---

## 四、行动摘要（整改优先级）

### Quick Wins（低成本快速修复）

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-02 | 事件字段改 `env:` 传递 | 低 |
| FIND-03 | Step Summary 写入前转义 Markdown 特殊字符、URL 白名单 | 低 |
| FIND-04 | Action 引用固定 SHA | 低 |
| FIND-05 | node16 升 node20 | 低 |
| FIND-06 | 日志脱敏、URL 编码 | 低 |
| FIND-07 | 提交 lock 文件 | 低 |

### 需专项处理

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-01 | 重构 pre-commit 工作流触发器与 Runner 模型 | 中 |
| FIND-08 | 工作流最小权限、服务端项目绑定校验 | 中 |

---

## 五、分析假设与需验证项

1. 基于静态文件审计；GitCode 平台对 `pull_request_target`、secrets 掩码的实际行为需运行时验证。
2. Step Summary 的 Markdown 渲染规则（是否允许原始 HTML、链接协议限制）取决于流水线平台实现，建议在真实环境验证注入效果。
3. SCA 后端服务（`/openlibing-sca`）源码不在本次仓库范围内，其鉴权与输入处理需另行审计。

## 六、参考标准

- STRIDE-A 威胁建模；OWASP Top 10:2025；CWE/MITRE；GitHub Actions 安全加固指南（`pull_request_target`、第三方 Action 固定版本）。
