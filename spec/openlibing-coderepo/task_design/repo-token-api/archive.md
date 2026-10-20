# Archive：【黄蓝协同】openlibing代码仓Token鉴权信息自动获取（openlibing-coderepo 侧）

- **FE 需求名称**：【黄蓝协同】openlibing代码仓Token鉴权信息自动获取
- **业务 Issue**：openlibing/openlibing-coderepo#207（<https://gitcode.com/openlibing/openlibing-coderepo/issues/207>，已关闭）
- **业务 PR**：!231（<https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/231>）
  - 分支：`feat/repo-token-api` → `release_20261019_iter1`
  - head：`1da45a78c4dabef0c80cd7a6646e9bf7aaa9e9cf`
  - 合并提交：`6f77f3bb71746c87bb9c5f3b80186a3869181508`（!231 merge feat/repo-token-api into release_20261019_iter1，2026-10-19 19:19:49，由 openLiBingCI 自动合入）
  - 合并状态：`resolve_discussion_passed=true`、`ci_state_passed=true`、审批 2/2 通过
- **develop 同步**：`61b71d09`、`1843107f5edad734b8bfe395eb85abb9decc1e6d`（`develop_202610_iter1`）
- **归档时间**：2026-10-20

## 交付内容

1. **机机接口** `POST /repo-token/internal/fetch`（APIG 对外建议 `/repo-token/v1/fetch`）
   - 请求侧：时间戳 ±5 分钟窗口 + nonce（32~128 位 hex，Redis 一次性，TTL 10 分钟）+ `SHA256withECDSA` 验签，canonical = `timestamp + "\n" + nonce + "\n" + sha256hex(body)`；
   - 响应侧：每响应临时 EC P-256 密钥对 + 与调用方公钥 ECDH + SHA-256 派生一次性 AES-256-GCM 密钥，逐条密文下发，AAD = `repoUrl`；
   - 请求体上限 64 KB（超限 413）；接口开关关闭时 503。
2. **批量查询正确性**：新增无分页 `queryRepoInfoByUrls`；同一 `repo_url` 多行（`uk_repo_project` 为 `(repo_url, project_id)`）时按 `valid` 优先 → `repo_id` 最小选一行，避免误报 `not_found`。
3. **元信息归一化**：`tokenMeta.expiration` 统一 ISO-8601 UTC（GitCode / GitHub / Gitee 三平台格式差异自动处理，不可解析为 `null`）。
4. **Gitee 令牌放行**：平台不提供元信息时状态为 `unsupported`，令牌照常密文下发，由调用方按状态降级。
5. **MQS 去明文令牌**：`MqsReqMessageVO` / `PrSyncMessageContext` / `MqsMessageSenderImpl` 移除 `access_token`；PR/push 同步不再以令牌可用为前置门禁，黄区消费端按需自取。
6. **配置与运维**：`repo-token.enabled/public-key/fingerprint` 由 Nacos 下发；公钥指纹启动自检（不一致拒绝启动）；过滤器对 Redis 异常 fail-closed。
7. **调用方接口文档**：签名规则、字段契约、解密步骤、错误处理（本目录 `api.md`）。

## 验证证据

| 项           | 结果                                                                                                               |
| ------------ | ------------------------------------------------------------------------------------------------------------------ |
| 全量单元测试 | **1073/1073 PASS**（0 failure / 0 error）                                                                          |
| 静态检查     | checkstyle / spotbugs / pmd **全部通过**                                                                           |
| 三平台 E2E   | GitCode / GitHub / Gitee：签名 → 验签 → ECDH → 解密全链路 PASS，解密所得 token 经平台只读 API 实测有效（HTTP 200） |
| 安全断言     | 篡改 body 401、重放 nonce 401、AAD 调包解密失败、全降级响应不含 `ephemeralPublicKey`、20 并发每次临时公钥唯一      |
| PR CI        | pre-commit（含 gitleaks）、SCA、code check 通过；评审两条行内讨论已解决                                            |

## 评审问题闭环（本 PR 内修复）

| 问题                                                     | 处理                                                            |
| -------------------------------------------------------- | --------------------------------------------------------------- |
| 批量查询因多行占用 LIMIT 误报 `not_found`                | 改无分页查询 + 确定性多行选一（`2b871b0c`）                     |
| 注释仍写 RSA-OAEP / wrappedKey，与 ECDSA/ECDH 实现不一致 | 统一修正 5 处注释（`2b871b0c`）                                 |
| `shouldNotFilter` 回退分支用未解码 URI                   | 回退分支先 `UriUtils.decode` + 单测（`2b871b0c`）               |
| nonce 契约（≥32 位 hex）服务端未强制                     | 强制 32~128 位 hex + 4 个边界用例（`43dc9d55` 前置提交）        |
| 验签前 `readAllBytes` 无界读 body                        | 64 KB 上限 + `readNBytes(limit+1)` 有界读取 + 413（`1da45a78`） |
| push handler 中已无用的 token 查询与早退                 | 移除查询/早退/字段，令牌缺失不再丢事件（`1da45a78`）            |
| SCA 命中公共样板代码（`CachedBodyRequest`）              | 重写为命名流类 + 补 `getReader()`，SCA 通过（`cb6f0913`）       |
| gitleaks 将测试中高熵 nonce 字面量判为密钥               | 测试改为运行时生成 nonce（`43dc9d55`）                          |

## 遗留事项

1. **APIG 登记（阻塞对外可用）**：`/repo-token/v1/fetch` 尚未在 APIG 发布，需登记 App 授权、IP 白名单、限流（如 10 QPS）、后端 HTTPS；当前 10 QPS 仅为设计约定，未实际生效。
2. **生产密钥替换**：当前密钥对为 BETA 开发用（私钥仅在调用方内网保管），生产需调用方重新生成并经独立通道核对指纹。
3. **调用方接入验证**：需调用方按 `api.md` 实现签名与解密，完成一次真实环境联调。
4. **存量令牌治理**：Gitee 平台存在失效令牌（`token_expiration='--'` 导致 XXL-Job 不重新校验），属独立运维事项。
5. **GAMMA 环境 webhook 迁移**（与本需求无关，同期发现）：GAMMA Nacos `openlibing.coderepo.webhook.url` 仍为 legacy 路径，而代码已下线 legacy 端点，需迁移配置并触发 `refreshWebhookHandler`。
