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

- **undici 5.29.0 的 CVE 批次（#22–#37）与 #19 同根因**
  advisory 修复版本为 `6.29.1 / 7.30.1 / 8.12.2`，5.x 无修复版本。
  但三个测试 Action（test-apig-action / test-apig-obs-action / test-obs-action）运行时为 `node16`，
  而 undici 6+ 要求 Node ≥18.17，升级必须连带调整 Action 运行时（属行为变化，须评审）。
  2026-11-03 用户决定暂不升级、先自行调查，代码与 issue 均保持现状。

- **#18 STS 端点拼接 / http 协议校验（2026-11-03 用户裁决：暂不实施）**
  拟改点：`configure()` 对 `region`（`[a-z0-9-]`）与 `stsAssumePath`（以 `/` 开头、不含 `@`）
  做白名单校验；`sendRequest()` 拒绝非 https 协议。属输入拒绝 + 失败语义变化，
  影响公开 API `sendRequest` 的 http 用法，方案已评估但暂缓实施。
