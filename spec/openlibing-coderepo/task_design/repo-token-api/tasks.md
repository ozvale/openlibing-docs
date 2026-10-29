# Tasks：【黄蓝协同】openlibing代码仓Token鉴权信息自动获取（openlibing-coderepo 侧）

## 阶段一：接口与加解密实现

- [x] 定义 API 契约：`POST /repo-token/internal/fetch`，head 三要素 + canonical + 响应结构（`api.md`）
- [x] `RepoTokenProperties`：`enabled / publicKey / fingerprint` 配置绑定、PEM 解析（兼容单行字面量 `\n`、裸 Base64）、启动指纹自检
- [x] `RepoTokenCrypto`：canonical 构造、SHA256withECDSA 签名/验签、临时 EC 密钥对生成、ECDH + SHA-256 KDF、公钥编解码、AES-256-GCM 加解密
- [x] `NonceCache` / `RedisNonceCache`：SETNX + TTL 10 分钟，异常 fail-closed
- [x] `RepoTokenAuthFilter`：开关 / 缺头 / 时间戳窗口 / nonce 格式 / body 上限 / 验签 / nonce 一次性；`BodyReplayRequest` 可重读 body
- [x] `RepoTokenFilterConfig`：过滤器注册与依赖装配（Redis nonce 缓存为必需依赖）
- [x] `RepoTokenController` / `RepoTokenService(Impl)`：批量查询、加密下发、逐条降级
- [x] `TokenExpirationNormalizer`：三平台过期时间归一化为 ISO-8601 UTC
- [x] 响应 DTO 注释与实现对齐（ECDSA/ECDH，无 RSA-OAEP / wrappedKey 残留）

## 阶段二：配套改造

- [x] `RepoInfoMapper#queryRepoInfoByUrls`：无分页按 URL 集合查询（避免多行占用 LIMIT 名额导致误报 `not_found`）
- [x] 多行选一确定性规则（`valid` 优先 → `repo_id` 最小）
- [x] MQS 去明文 token：`MqsReqMessageVO` / `PrSyncMessageContext` / `MqsMessageSenderImpl` 移除 `access_token`
- [x] `PrSyncEventHandler` / `PrSyncPushEventHandler`：不再为消息取 token；推送同步不再以令牌可用为前置门禁
- [x] `application.yaml` 仅保留开关默认值（真实值由各环境 Nacos 下发）

## 阶段三：测试与验证

- [x] 单测覆盖：配置解析/指纹（5）、Crypto（7）、过滤器（18，含 31 位/非 hex/129 位 nonce、超窗、篡改、重放、编码路径、413）、Service（11，含多行场景）、RedisNonceCache（3）、TokenExpirationNormalizer（9）、MQS 无 token 断言
- [x] 全量单元测试通过（最终 1073/1073）
- [x] checkstyle / spotbugs / pmd 全绿
- [x] 三平台 E2E（GitCode / GitHub / Gitee）：签名 → 验签 → ECDH → 解密，解密 token 经平台只读 API 实测有效
- [x] 安全断言：篡改 body 401、重放 401、AAD 调包解密失败、全降级响应无密钥、20 并发每次临时公钥唯一
- [x] PR CI 门禁：pre-commit（含 gitleaks）、SCA、code check 通过

## 阶段四：评审与合入

- [x] 处理评审意见：批量查询误报、注释与实现不一致、编码路径回退分支解码、nonce 契约未强制、验签前无界读 body、push handler 死代码
- [x] 评审意见逐条修复并推送到 PR（`cb6f0913` / `2b871b0c` / `43dc9d55` / `1da45a78`）
- [x] PR !231 合入 `release_20261019_iter1`（合并提交 `6f77f3bb`）
- [x] 增量合入 `develop_202610_iter1`（`61b71d09` / `1843107f`）

## 阶段五：归档与上线

- [x] spec 归档到 openlibing-docs（proposal / design / tasks / api / archive）
- [ ] **APIG 控制台登记**：发布 `/repo-token/v1/fetch`、绑定调用方专用 App、IP 白名单、限流（如 10 QPS）、后端 HTTPS
- [ ] 调用方接入：内网生成密钥对 → 公钥入 coderepo Nacos → 指纹交叉核对 → 调用验证
- [ ] 生产密钥替换：由调用方重新生成密钥对（当前 BETA 开发用密钥不可用于生产）
- [ ] 存量令牌治理（Gitee 失效令牌清理，独立事项）
