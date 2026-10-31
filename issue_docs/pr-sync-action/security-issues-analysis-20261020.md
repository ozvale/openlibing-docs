# pr-sync-action 安全 issue 定性分析（2026-10-20 首轮 / 2026-10-23 复检）

> 首轮定性基于分支 `fix-security-remediation` 的代码快照，**把「PR #5 分支已改」误记为「master 已修复」**。
> 2026-10-23 复检改用双基线重新核实全部 18 条 open issue：
>
> - **基线 A（交付态）**：`upstream/master` = `db5d28c16d38ca7904a6d16348a5bac33589bbd0`
> - **基线 B（在途整改）**：PR #5 分支 `origin/fix-issue5-8-token-log-url` = `c299859191cfd7e99024655a9515f813c38463a0`（open，未合入）
> - 依据：gitcode-security-remediation skill Phase 1 + `security-remediation-playbook.md` + `security-non-issue-catalog.md`

## 0. 复检结论速览

1. **master 上 16 条安全 issue 全部仍然存在**，首轮文档中标为「已修复」的 #8 / #6 / #17 实际只存在于未合入的 PR #5。
2. **PR #5 的实际改动小于其描述**：PR 正文称「覆盖全部日志出口（OIDC 与 AppCode 双模式）：请求行、响应行、非 2xx 错误消息」，实测 AppCode 分支的响应日志与非 2xx 错误消息**未脱敏**，属**半整改状态**。
3. 因此 #11 / #16 / #21 / #22 不能视为「已由 PR #5 解决」，仍需一个等价加固 PR 补齐 AppCode 响应/错误脱敏。

## 1. 汇总

| 分类 | Issue | 处理建议 |
|---|---|---|
| 已整改·待 PR #5 合入 | #5 #6 #7 #8 #17 | 代码在 PR #5 分支，master 未生效；待 review 合入后复检关闭 |
| 真问题·等价加固（本轮可做） | #11 #16 #21 #22 | 补 AppCode 响应日志/错误消息脱敏，与 PR #5 同文件同函数，建议作为 PR #5 的追加 commit 或紧随其后的小 PR |
| 真问题·须用户评审 | #9 #12 #13 #18 | 触发硬规则 2（后端契约/阈值/失败语义/新增输入拒绝），先出《业务逻辑影响评估》 |
| 平台/后端依赖·暂缓 | #10 #20 | #10 待流水线全量声明 id-token + 网关 IAM；#20 待上游 oidc-client 依赖升级 |
| 非问题（已确认 2026-10-23） | #15 | 已按跨仓「自有门禁可变 tag」判定归档到 `security-non-issue-catalog.md` |
| 非安全类 issue（不在整改范围） | #1 #19 | 功能需求 / 功能发布 issue |

## 2. 已整改·待 PR #5 合入（5 条）

| Issue | 内容 | master 现状（基线 A） | PR #5 分支（基线 B） | 结论 |
|---|---|---|---|---|
| #5 | SENS-11 core.info 明文打印含 accessToken 的完整请求体 | `src/apig-client.ts:85`、`:135` 原样打印 `bodyStr` | 两处均过 `redactSensitive` | 待合入 |
| #7 | SENS-03 CI 日志与归档长期留存明文 accessToken | 同 #5；另 `:98-102`（OIDC 响应）、`:158`（AppCode 响应）明文 | OIDC 响应已脱敏；**AppCode `:158` 未脱敏** | 待合入，且需补 AppCode 侧（并入第 3 节） |
| #6 | SENS-11 Gitee access_token 以 URL 查询参数传输 | `gitee-label-client.ts:19`、`gitee-pr-client.ts:24` 拼 `?access_token=` | 改 `Authorization: Bearer`（`gitee-label-client.ts:27-32`） | 待合入 |
| #17 | 红线 Gitee 出站调用 token 拼入 URL 查询串 | 同 #6，同一根因 | 同 #6 一并整改 | 待合入 |
| #8 | SENINFO 公网地址环境域名硬编码 | `label-manager.ts:11`、`gitcode-pr-client.ts:6`、`gitee-label-client.ts:6`、`gitee-pr-client.ts:6` 硬编码 | 改 `GITCODE_API_URL` / `GITEE_API_URL` 注入，默认值不变并登记 `gitleaks:allow` | 待合入 |

> 等价性：默认值与原硬编码完全一致，仅新增环境变量覆盖能力；输出契约未变。

## 3. 真问题·等价加固——脱敏补漏（4 条，本轮建议做）

| Issue | 扫描器 | 问题点 |
|---|---|---|
| #11 | 威胁分析 | 请求/响应日志明文打印含 accessToken 的 body，令牌进入 CI 日志 |
| #16 | 红线 7.1.11 | `apig-client.ts:85/135` 请求体整体打印 |
| #21 | 安全编码要求 | 请求体整包打印 + OIDC/AppCode **响应体**整包打印 + Gitee token URL 传参 |
| #22 | 安全功能规范 | OIDC 与 AppCode 两条路径均把含 accessToken 的请求体原样输出 |

**复检证据（master db5d28c）**

| 位置 | 代码 | 是否含敏感数据 | PR #5 是否处理 |
|---|---|---|---|
| `src/apig-client.ts:85` | `core.info(\`[APIG] → ${url.href} ${bodyStr}\`)`（OIDC） | 含 accessToken | 已脱敏 |
| `src/apig-client.ts:98-102` | `core.info(\`[APIG] ← ${res.status} ...\`)`（OIDC） | 可能回显 | 已脱敏 |
| `src/apig-client.ts:135` | `core.info(\`[APIG] → ${url.href} ${bodyStr}\`)`（AppCode） | 含 accessToken | 已脱敏 |
| `src/apig-client.ts:158` | `core.info(\`[APIG] ← ${res.statusCode} ${data}\`)`（AppCode） | 可能回显 | **未处理** |
| `src/apig-client.ts:167` | `new Error(\`APIG 返回非 2xx: ..., body: ${data}\`)`（AppCode） | 可能回显 | **未处理** |
| `gitee-label-client.ts:19` / `gitee-pr-client.ts:24` | `?access_token=` 拼接 | 明文令牌入 URL | 已改 Bearer 头 |

**定性**：真问题·等价加固（日志脱敏，硬规则 1 白名单内）。

**整改方案**：沿用 PR #5 已引入的 `redactSensitive()`，把 `requestViaAppCode` 的响应日志与非 2xx 错误消息也过脱敏，与 OIDC 路径对齐，消除半整改状态。输出契约不变（仅日志/错误文本中的令牌被掩码）。

**PR 策略**：改动点与 PR #5 完全同文件同函数（`src/apig-client.ts` → `requestViaAppCode`），按 skill 2.1「同一段代码强耦合」应并入 PR #5（追加 commit），不另起 PR 造成两 PR 触碰同一段代码。关联 `Fixes #11 #16 #21 #22`。

## 4. 真问题·须用户评审（4 条）

| Issue | 内容 | 代码证据（master db5d28c） | 改动类别 |
|---|---|---|---|
| #9 | 仓库访问令牌明文中转至第三方 APIG 网关 | `main.ts:39-40` 取 `git_token`/平台 token，`:67` 写入触发体 `accessToken`，`types.ts:102` 定义该字段 | 数据处理链路 / 后端契约 |
| #18 | 通用 HTTP 封装允许 http 明文降级 | `http-request.ts:48`、`label-manager.ts:55`、`apig-client.ts:150` 均为 `url.startsWith("https:") ? https : http` | 新增输入拒绝 |
| #12 | 轮询间隔缺少合理下限 | `main.ts:89-90` 默认 60s、`:97-98` 仅校验 `>= 1`；`action.yml:33` 文案建议不低于 30 | 资源限制阈值 |
| #13 | 标签操作静默吞错 | `label-manager.ts:91-94` 添加失败仅 `core.warning`、`:115-118` 批量删除失败仅 `core.warning`，无失败上报 | 失败语义变化 |

> 行号相对首轮已漂移：首轮记的 `label-manager.ts:69-70`（#18）实际为 `:55`。

## 5. 平台/后端依赖·暂缓（2 条）

| Issue | 内容 | 结论 |
|---|---|---|
| #10 | App Code 静态共享凭证回退认证，缺少轮换机制 | `credential-config.ts:10-11` 明确 App Code 为未声明 id-token 时的回退路径；`:21-30` 判定 OIDC 可用性、`:38-39` 判定 AppCode 是否配置。彻底移除依赖流水线全量声明 `id-token: write` + 网关全量 IAM 认证，插件侧无法单方整改。⏸ 暂缓（待平台联动） |
| #20 | 捆绑库 actions-io 回退路径 `chmod 0666` | `dist/index.js:5881`（首轮记 5925，行号漂移），来源 `@openlibing/huaweicloud-oidc-client` 传递依赖 `@actions/io`，属第三方库内联产物，非本仓源码；仅影响 runner 本地临时目录复制。整改路径为升级上游依赖，⏸ 暂缓 |

## 6. 非问题（1 条，2026-10-23 用户确认）

| Issue | 内容 | 复检后的证据 | 非问题理由 | 决策日期 |
|---|---|---|---|---|
| #15 | 工作流 Action 与 pre-commit 钩子以可变 tag 引用 | master：`code-metrics-scan.yml:23` `code-metrics-action@v1.0.3`、`pre-commit.yml:31/91` `pr-label-action@v1.0.0`、`:79` `pre-commit-action@v1.0.2`。首轮文档所写「已固定 117c0606」**不成立**，该 SHA 只存在于统一测试分支 `fix-security-remediation`（commit `b9c05f9`）与 `update_code-metrics-scan` 分支 | 引用对象均为本组织自有门禁组件（同一信任域内部版本引用）；`.pre-commit-config.yaml` 的 rev 属 pre-commit 框架版本固定机制。与 upload-ut-action 同类判定一致 | 2026-10-23 |

**归档**：已回写 `security-non-issue-catalog.md` 的「自有门禁配置中的可变 tag 依赖」条目（新增案例行）。

## 7. 非安全类 issue（2 条，移出整改范围）

| Issue | 内容 | 结论 |
|---|---|---|
| #19 | feat(api-scan): 接入接口兼容性扫描 workflow | 功能需求，非安全扫描产出 |
| #1 | feat(plugin): 黄蓝协同 PR 同步结果回显插件 v1.0.0 | 功能发布 issue |

## 8. 本轮复检发现的偏差（需在后续整改中修正）

| 偏差 | 首轮文档表述 | 复检事实 |
|---|---|---|
| 基线混淆 | 「#8 #6 #17 已修复，待复检关闭」 | master 未生效，改动在未合入的 PR #5 |
| PR #5 覆盖率夸大 | PR 正文称「覆盖全部日志出口（OIDC 与 AppCode 双模式）」 | AppCode 响应日志 `:158`、非 2xx 错误 `:167` 未脱敏 |
| #15 证据过期 | 「code-metrics-action 已固定 commit SHA（117c0606）」 | 仅统一测试分支固定，master 仍为 `v1.0.3` |
| 行号漂移 | #18 `label-manager.ts:69-70`、#20 `dist/index.js:5925` | 实际 `label-manager.ts:55`、`dist/index.js:5881` |

## 9. 下一步计划

| 动作 | 内容 | Issue |
|---|---|---|
| 追加整改 | 在 PR #5 分支补 AppCode 响应/错误脱敏并重建 `dist/`，同步 `fix-security-remediation` | #11 #16 #21 #22 |
| 影响评估 | 对 #9 #12 #13 #18 逐条出《业务逻辑影响评估》，用户批准后编码 | 同左 |
| 暂缓登记 | #10 #20 标注待平台/依赖联动 | 同左 |
| 非问题确认 | #15 已归档到 `security-non-issue-catalog.md`（2026-10-23 用户确认） | #15 |
