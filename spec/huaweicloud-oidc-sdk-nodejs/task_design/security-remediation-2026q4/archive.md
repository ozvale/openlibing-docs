# 【huaweicloud-oidc-sdk-nodejs】安全整改 2026Q4 — 归档

## 关联

- 业务仓：openlibing/huaweicloud-oidc-sdk-nodejs
- 安全 Issue 总量：31（非 CVE 15 条 + CVE 16 条）
- 本轮相关 Issue：#18（STS 端点拼接与 http 协议未校验）、#19（undici 5.x 已知漏洞）、#22–#37（undici 衍生 CVE 16 条）
- 业务 PR：#15（移除 undici 依赖，#19 + #22–#37）、#16（sendRequest 强制 HTTPS，#18）、#17（region / stsAssumePath 白名单校验，#18）
- 统一测试分支：`fix-security-remediation`（commit `9432784`）
- docs PR：本归档 PR

## 整改范围

### 1. 移除 undici 依赖（PR #15，覆盖 #19 与 #22–#37）

- 直接删除 `undici` 依赖，改用 Node 内置 `http` / `https` 实现等价 HTTP 请求；不升级 Node 版本（流水线运行时为 Node 16）。
- 新增 `_nodeFetch` 回退实现：仅覆盖 `sendRequest` 所需能力（method / headers / body / status / headers.forEach / text），超时 300s 与 fetch 默认量级一致。
- `overrides` 固定传递依赖版本，消除 undici 相关 CVE 的全部传递路径。

### 2. sendRequest 强制 HTTPS（PR #16，覆盖 #18 第 2 项）

- `sendRequest` 首行调用 `_assertHttps(url)`，非 `https:` 协议一律拒绝，避免 `Authorization` / `X-Security-Token` 明文传输。
- URL 无法解析时同样拒绝，防止畸形 URL 绕过协议判断。
- 错误信息只保留 origin + pathname（`_safeUrlForLog`），不带 query，避免票据入日志。

### 3. STS 端点拼接字段白名单校验（PR #17，覆盖 #18 第 1 项）

- `configure()` 写入前整体校验：`region` 仅允许小写字母、数字与连字符；`stsAssumePath` 必须以 `/` 开头，且不能包含 `@`、空白、`?`、`#` 或 `://`。
- OIDC 请求地址强制 https。

## 交付历程

| PR | 内容 | 状态 |
|---|---|---|
| #11 | 日志敏感值脱敏 | merged |
| #12 | npm token 文件权限收紧与清理 | merged |
| #13 | V11 签名 x-sdk-date 大小写不敏感查找 | merged |
| #14 | OBS 客户端开启 TLS 校验 | merged |
| #15 | 移除 undici 依赖（#19、#22–#37） | open，`ci-pipeline-passed` |
| #16 | sendRequest 强制 HTTPS（#18） | open，`ci-pipeline-passed` |
| #17 | region / stsAssumePath 校验（#18） | open，`ci-pipeline-passed` |

## 存量核对

| 指标 | 数量 |
|---|---:|
| 总体 | 31 |
| 已修复（closed） | 13 |
| 剩余（open） | 18 |

剩余 18 条均已被 #15 / #16 / #17 覆盖，属于「代码已改、PR 待合入、issue 未关单」，无真实欠账。

## 验证

- 本地单元测试：`fix-security-remediation` 分支 30 项 PASS，含 PASS 23（无全局 fetch 回退路径拒绝 http）、PASS 24（STS 端点字段校验）、PASS 28（sendRequest 拒绝 http 明文）。
- Node 16 真实网络实测：OIDC 取 token → STS 换证 → APIG 调用链路正常。
- 平台端到端：`openlibing-test/openlibing-cicd-test` PR #282 引用 fork tag `sec-https-verify`（指向 `9432784`），`/pre-commit` 触发的 Actions 运行 `oidc-https-verify` job 三个 step 全绿（test-apig / test-apig-obs / test-obs）。

## 遗留与下一步

1. #15 / #16 / #17 合入默认分支后统一关闭 #18、#19 与 #22–#37。
2. 三个 PR 均触碰 `src/http.js` 与测试文件，需按合入顺序 rebase。

## 可复用经验

- 「不升级运行时」约束下，CVE 整改最稳路径是移除引入方 + 用运行时内置能力做等价实现，配合 `overrides` 堵住传递依赖。
- 强制 HTTPS 的校验必须覆盖全部请求入口，且「URL 无法解析」也应拒绝，避免畸形输入绕过。
- 回退实现要与主路径一样受同一前置校验约束，否则 Node 16 场景会成为绕过口子。
- 安全整改 PR 允许「契约不变、行为收紧」，但新增输入拒绝类改动需先出业务逻辑影响评估并经用户确认。

## 归档日期

2026-11-05
