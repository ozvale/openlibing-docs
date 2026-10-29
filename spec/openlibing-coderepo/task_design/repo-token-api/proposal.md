# Proposal：【黄蓝协同】openlibing代码仓Token鉴权信息自动获取（openlibing-coderepo 侧）

## 需求背景

- 黄蓝协同场景下，内网指定服务需要**按仓库地址获取代码仓 token**，用于自身的代码仓调用能力（如 PR 门禁、分支校验等）。
- openlibing-coderepo 部署在外网，调用方位于内网，链路为 `内网服务 → APIG 网关 → 外网 coderepo`。该链路跨内外网、不可整体信任，因此必须同时满足：
  1. **防伪造**：只有被授权的调用方能调；
  2. **防窃听**：token 不能被链路上任何节点看到，且不依赖 TLS 配置是否完全正确；
  3. **防重放 / 防篡改**：报文（时间戳、nonce、body）必须被绑定。
- 同时发现历史问题：黄蓝协同 MQS 消息体携带**明文仓库 token**（`MqsReqMessageVO.access_token`），随消息在 MQ 中流转，属于凭证外泄风险（关联 #193 / #165 / #176）。

- **FE 需求名称**：【黄蓝协同】openlibing代码仓Token鉴权信息自动获取
- **业务 Issue**：openlibing/openlibing-coderepo#207（<https://gitcode.com/openlibing/openlibing-coderepo/issues/207>，已关闭）
- **业务 PR**：openlibing-coderepo !231（<https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/231>）
  - 分支：`feat/repo-token-api` → `release_20261019_iter1`
  - 合并提交：`6f77f3bb`（!231 merge feat/repo-token-api into release_20261019_iter1，2026-10-19 19:19:49）

## 范围

仅涉及 `openlibing-coderepo` 单仓：

1. 新增机机接口 `POST /repo-token/internal/fetch`（APIG 对外建议路径 `/repo-token/v1/fetch`）；
2. 请求侧验签过滤器：时间戳窗口 + nonce 格式/一次性 + SHA256withECDSA 验签（canonical 含 body 摘要）；
3. 响应侧加密：每响应生成临时 EC 密钥对，与调用方公钥 ECDH 派生一次性 AES-256-GCM 密钥，逐条密文下发（AAD 绑定 repoUrl）；
4. 令牌元信息归一化：`tokenMeta.expiration` 统一为 ISO-8601 UTC（GitCode / GitHub / Gitee 三平台原始格式差异自动处理）；
5. Gitee 平台（元信息 unavailable → `unsupported`）令牌放行策略；
6. 黄蓝协同 MQS 消息体移除明文 `access_token`；
7. 调用方接入文档（签名规则、字段契约、解密步骤、错误处理）。

**不在本需求范围**（需单独协作）：

- APIG 控制台登记（App 授权 / IP 白名单 / 限流 / 后端 HTTPS）——属网关侧配置，本服务不重复建设；
- 调用方密钥生成、保管与轮换（调用方内网侧自行完成，双方通过指纹交叉校验）；
- 存量令牌治理（如 Gitee 失效令牌清理）。

## 验收标准

1. 合法签名请求返回 200，逐仓库返回状态；`valid` / `unsupported` 下发密文，`invalid` / `unknown` / `not_found` / `unavailable` 仅返回元数据、不下发密文；
2. 篡改 body / 重放 nonce / 时间戳超窗 / 缺签名头 / 非 hex 或长度不符的 nonce → 401；接口开关关闭 → 503；请求体超过 64 KB → 413；
3. `nonce` 强制 32~128 位 hex，且 Redis SETNX 一次性（TTL 10 分钟），登记必须晚于验签；
4. token 明文不出现于响应体、服务端日志、MQS 消息；
5. 三平台 E2E（GitCode / GitHub / Gitee）可完成 签名 → 验签 → ECDH → 解密，且解密所得 token 经平台只读 API 实测有效；
6. 公钥指纹启动自检：配置公钥计算出的指纹与 `repo-token.fingerprint` 不一致时拒绝启动；
7. 全量单元测试与静态检查（checkstyle / spotbugs / pmd）门禁通过，PR CI（pre-commit / SCA）通过。
