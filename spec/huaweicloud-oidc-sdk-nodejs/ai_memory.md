# huaweicloud-oidc-sdk-nodejs · AI 记忆

## 安全整改结论（可复用）

- **#11 华为云账号 ID 硬编码（2026-11-03 用户裁决：非问题）**
  `src/config.js` 中 `accountId: '4d29a984...'` 与 `audience` / `agencyName` / `oidcProviderName`
  同属 SDK 内置默认配置，使用方可通过 `configure()` 覆盖；accountId 为账号标识而非凭证，
  不构成凭证泄露或越权面。后续同根因扫描命中直接复用此结论，不再重复分析；
  如需外置默认账号 ID，走功能增强需求，不纳入安全整改。

- **2026-10-29 整改批次已落地主线（!11 ~ !14）**
  - `!11` fix-sec-log-mask：日志脱敏（OIDC 失败响应体 `maskBody`、URL `_safeUrlForLog`、
    可控值 `_oneLine` 折叠换行/控制字符）→ #10 #17 #21
  - `!12` fix-sec-npmrc-token：发布流程 `umask 077` + `if: always()` 清理 `~/.npmrc` → #7 #15
  - `!13` fix-sec-signer-header：`getHeaderIgnoreCase` + canonical 头小写归并 → #16
  - `!14` fix-sec-obs-ssl-verify：测试 Action 显式 `sslVerify: true` → #20
  以上 issue 已于 2026-11-03 核实并关闭。

## 待办 / 暂缓

- **undici CVE 批次（#22–#37）与 #19：已整改（PR #15，待合入）**
  最终方案不是升级 undici（Node 16 运行时无法满足 undici 6+ 的 Node ≥18.17 要求），
  而是**移除 undici 依赖**：新增 `_nodeFetch` 基于 Node 内置 http/https 的等价实现，
  并用 `overrides` 固定传递依赖版本。结论：受运行时版本约束的 HTTP 库 CVE，
  优先移除依赖 + 运行时内置能力等价实现，禁止连带升级运行时。
  issue #19 / #22–#37 待 PR 合入后统一关闭。

- **#18 STS 端点拼接 / http 协议校验：已整改（PR #16 + #17，待合入）**
  `configure()` 对 `region`（`[a-z0-9-]`）与 `stsAssumePath`（以 `/` 开头、不含 `@`/空白/`?`/`#`/`://`）
  做白名单校验；`sendRequest()` 首行拒绝非 https 协议，URL 无法解析时同样拒绝。
  2026-11-04 用户确认采用「全量拒绝 http」方案并接受测试用例调整；
  端到端已在 `openlibing-test/openlibing-cicd-test` PR #282 验证通过
  （OIDC 取 token → STS 换证 → APIG 调用 → OBS 上传全链路正常）。
  issue #18 待 PR 合入后关闭。
