# STRIDE + Abuse Cases — Threat Analysis

> This analysis uses the standard **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) extended with **Abuse Cases** (business logic abuse, workflow manipulation, feature misuse). The "A" column in tables below represents Abuse — a supplementary category covering threats where legitimate features are misused for unintended purposes. This is distinct from Elevation of Privilege (E), which covers authorization bypass.

## Exploitability Tiers

Threats are classified into three exploitability tiers based on the prerequisites an attacker needs:

| Tier | Label | Prerequisites | Assignment Rule |
|------|-------|---------------|----------------|
| **Tier 1** | Direct Exposure | `None` | Exploitable by unauthenticated external attacker with NO prior access. The prerequisite field MUST say `None`. |
| **Tier 2** | Conditional Risk | Single prerequisite: `Authenticated User`, `Privileged User`, `Internal Network`, or single `{Boundary} Access` | Requires exactly ONE form of access. The prerequisite field has ONE item. |
| **Tier 3** | Defense-in-Depth | `Host/OS Access`, `Admin Credentials`, `{Component} Compromise`, `Physical Access`, or MULTIPLE prerequisites joined with `+` | Requires significant prior breach, infrastructure access, or multiple combined prerequisites. |

## Summary

| Component | Link | S | T | R | I | D | E | A | Total | T1 | T2 | T3 | Risk |
|-----------|------|---|---|---|---|---|---|---|-------|----|----|----|------|
| APIGateway | [Link](#apigateway) | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 3 | 3 | 0 | 0 | Medium |
| GitCode | [Link](#gitcode) | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | Medium |
| Gitee | [Link](#gitee) | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | High |
| HuaweiCloud | [Link](#huaweicloud) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | Medium |
| Nacos | [Link](#nacos) | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 3 | 0 | 1 | 2 | Medium |
| XxlJobAdmin | [Link](#xxljobadmin) | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | Medium |
| RabbitMQ | [Link](#rabbitmq) | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 3 | 0 | 3 | 0 | Medium |
| MySQL | [Link](#mysql) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | Medium |
| Redis | [Link](#redis) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 1 | 1 | Medium |
| PipelineControllerV2 | [Link](#pipelinecontrollerv2) | 1 | 0 | 0 | 1 | 0 | 1 | 0 | 3 | 0 | 3 | 0 | Medium |
| AuthInterceptor | [Link](#authinterceptor) | 1 | 2 | 0 | 1 | 1 | 0 | 0 | 5 | 1 | 4 | 0 | High |
| ApigWebhookController | [Link](#apigwebhookcontroller) | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | Medium |
| WebHookEventController | [Link](#webhookeventcontroller) | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 3 | 3 | 0 | 0 | High |
| CrossRegionController | [Link](#crossregioncontroller) | 1 | 1 | 0 | 1 | 0 | 0 | 1 | 4 | 4 | 0 | 0 | Critical |
| InternalPipelineController | [Link](#internalpipelinecontroller) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 0 | 2 | 0 | Medium |
| MachineInterfaceAuthUtil | [Link](#machineinterfaceauthutil) | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 3 | 2 | 0 | 1 | Medium |
| WebHookEventConsumer | [Link](#webhookeventconsumer) | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 3 | 0 | 3 | 0 | Medium |
| PipelineEventConsumer | [Link](#pipelineeventconsumer) | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | Low |
| PipelineStatusUpdateConsumer | [Link](#pipelinestatusupdateconsumer) | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 3 | 0 | 2 | 1 | Medium |
| PrOpEventConsumer | [Link](#propeventconsumer) | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | Low |
| PipelineFailEmailConsumer | [Link](#pipelinefailemailconsumer) | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | Medium |
| XxlJobHandler | [Link](#xxljobhandler) | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | Medium |
| PipelineStatusThirdPartyApiClient | [Link](#pipelinestatusthirdpartyapiclient) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | Medium |
| HwCloudClient | [Link](#hwcloudclient) | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 3 | 0 | 3 | 0 | Medium |
| ObsBucketServiceImpl | [Link](#obsbucketserviceimpl) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | Medium |
| **Totals** | | **8** | **22** | **2** | **14** | **6** | **3** | **9** | **64** | **19** | **36** | **9** | |

---

## APIGateway

**Trust Boundary:** External
**Role:** 华为云 API 网关，承担平台用户认证与流量接入；信任边界，所有入站流量经此进入服务。
**Data Flows:** DF01, DF02, DF03, DF04
**Pod Co-location:** N/A（外部托管服务）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T01.S | Spoofing | 网关平台会话认证若被绕过（弱口令/会话固定/令牌窃取），攻击者可冒充合法平台用户身份访问业务接口 | None | DF01 | 依赖华为云 APIG 平台认证能力；建议启用二次认证与令牌短期有效 | Platform |
| T01.D | Denial of Service | 业务接口无应用层速率限制，网关流量控制不覆盖单接口维度，攻击者可对 webhook/批量接口发起洪泛 | None | DF02 | 依赖 APIG 流量控制（QPS 配额）；服务侧建议对 webhook 增加幂等与限流 | Platform |
| T01.E | Elevation of Privilege | 网关将 `/internal/**`、`/cross-region/**` 等未鉴权端点透传至内网服务，若路由配置过宽，外部攻击者可触达内部接口 | None | DF03, DF04 | 服务侧内部接口无鉴权（见 InternalPipelineController），应在网关层收紧路由与鉴权策略 | Open |

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Tampering | 网关为旁路转发组件，不存储业务数据，无篡改面 |
| Repudiation | 网关访问日志由华为云平台托管，属平台责任 |
| Information Disclosure | 网关不保存业务敏感数据，仅透传 |
| Abuse | 网关无业务逻辑可供滥用，仅做流量接入 |

---

## GitCode

**Trust Boundary:** External
**Role:** 外部代码托管平台，发送 Webhook 事件、提供 REST API（PR/标签/评论/commit status）。
**Data Flows:** DF05, DF07, DF09, DF18, DF35
**Pod Co-location:** N/A（外部托管平台）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T02.R | Repudiation | 机机接口调用审计不完整：`machineInterfaceLog` 不记录验签结果且 `requestStatus="unknown"`，无法追溯是谁/何时触发了 webhook 操作 | None | DF05, DF07 | 需在审计日志中记录验签结果、签名与处理结果，实现不可抵赖 | Open |
| T02.T | Tampering | 依赖 GitCode 平台返回的 PR/标签/仓库数据完整性；若 GitCode 平台账号失陷或 API 响应被篡改，将影响 PR 自动化与门禁判断 | None | DF18, DF35 | 平台侧控制；本服务应校验关键响应字段并做幂等 | Platform |

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 面向本服务的 webhook 入口已做 HMAC 验签，平台身份由 GitCode 平台保证 |
| Information Disclosure | 本服务未向 GitCode 暴露敏感数据，仅做 API 调用方 |
| Denial of Service | 本服务不依赖 GitCode 作为唯一可用性来源，且有延迟重试机制 |
| Elevation of Privilege | GitCode 为外部平台，无本服务权限提升面 |
| Abuse | GitCode 平台功能由平台方治理，本服务仅消费其 API |

---

## Gitee

**Trust Boundary:** External
**Role:** 外部代码托管平台，发送 Webhook 事件、提供 REST API。
**Data Flows:** DF06, DF08, DF10, DF19
**Pod Co-location:** N/A（外部托管平台）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T03.S | Spoofing | Gitee webhook 验签算法弱（仅 timestamp+secret HMAC，不覆盖请求体、无时间窗），攻击者可伪造/重放 Gitee 事件 | None | DF06 | 应覆盖请求体参与签名，并校验 timestamp 时间窗（见 MachineInterfaceAuthUtil） | Open |
| T03.T | Tampering | 遗留 `WebHookEventController` 的 gitee 端点无服务内验签，事件体可被任意篡改后触发流水线操作 | None | DF08 | 服务内补验签或统一收敛到 `/apig/webhook` 验签入口 | Open |

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | Gitee 为外部平台，事件签名可作为一定程度溯源，不作为审计主体 |
| Information Disclosure | 本服务未向 Gitee 暴露敏感数据 |
| Denial of Service | 依赖 Gitee API 可用性，但本服务有延迟重试机制 |
| Elevation of Privilege | 外部平台无本服务权限提升面 |
| Abuse | Gitee 平台功能由平台方治理 |

---

## HuaweiCloud

**Trust Boundary:** External
**Role:** 华为云后端（OBS 对象存储、SWR 镜像仓、CodeCheck、构建服务），承载构建产物与流水线数据。
**Data Flows:** DF20, DF21
**Pod Co-location:** N/A（外部云服务）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T04.I | Information Disclosure | 若 OBS 桶 ACL/生命周期策略配置不当，或 AK/SK 泄露，构建日志与产物可被未授权读取 | AK/SK Compromise | DF21 | 遵循最小权限、桶私有化 + 临时签名 URL，定期轮换 AK/SK | Open |
| T04.T | Tampering | 若 AK/SK 泄露，攻击者可篡改/删除 OBS 对象与构建产物，影响构建完整性 | AK/SK Compromise | DF21 | 启用桶版本控制与防篡改策略，监控异常访问 | Open |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 云服务身份由 AK/SK 签名保证 |
| Repudiation | 云侧操作有云审计日志 |
| Denial of Service | 云服务由华为云 SLA 保障 |
| Elevation of Privilege | 外部云服务无本服务权限提升面 |
| Abuse | 云服务功能由云平台治理 |

---

## Nacos

**Trust Boundary:** External
**Role:** 配置中心与注册中心，托管数据库/Redis/RabbitMQ/密钥（含 AES part1、OBS AK/SK、webhook secret）等敏感配置。
**Data Flows:** DF33, DF34
**Pod Co-location:** N/A（集群内部部署）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T05.D | Denial of Service | Nacos 不可用会导致服务启动/配置刷新失败，进而影响全服务可用性 | Internal Network | DF33 | Nacos 集群高可用 + 配置本地缓存兜底 | Mitigated |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T05.I | Information Disclosure | Nacos 集中托管全部敏感配置与 AES 解密密钥（`security.part1`、DB/Redis/MQ/OBS 凭据），一旦配置中心失陷，所有凭据可被解密 | Nacos Compromise | DF33, DF34 | 拆分密钥托管、Nacos 访问控制、密钥定期轮换、网络隔离 | Open |
| T05.T | Tampering | 若攻击者可写 Nacos 配置，可篡改验签密钥/开关/端点，导致验签失效或配置误导 | Nacos Compromise | DF33, DF34 | Nacos 写权限最小化 + 配置变更审计 + 敏感配置加解密校验 | Open |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | Nacos 客户端连接使用 accessToken 鉴权 |
| Repudiation | 配置变更由 Nacos 审计日志记录 |
| Elevation of Privilege | Nacos 为外部基础设施，不直接参与业务授权 |
| Abuse | Nacos 无业务逻辑可供滥用 |

---

## XxlJobAdmin

**Trust Boundary:** External
**Role:** XXL-Job 调度中心，触发本服务 14 个定时任务。
**Data Flows:** DF32
**Pod Co-location:** N/A（集群内部部署）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T06.T | Tampering | 定时任务 `jobParam` 作为可信输入直接参与业务（webhook 批量刷新可携带 `customOrgs` 自定义 token、批量投递 MQ），恶意参数可造成批量误操作 | Internal Network | DF32 | 对 jobParam 做白名单/校验，敏感参数加密存储，禁止直接在任务参数中传递 token | Open |
| T06.A | Abuse | 调度任务可被反复触发（批量投递/刷新/邀请），造成资源放大与重复操作 | Internal Network | DF32 | 任务幂等 + 触发频率限制 + 操作审计 | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 调度中心与本服务使用 accessToken 鉴权 |
| Repudiation | 任务执行有 XXL-Job 执行日志 |
| Information Disclosure | 调度中心不持有业务敏感数据 |
| Denial of Service | 调度触发由平台治理，非业务攻击面 |
| Elevation of Privilege | 调度中心不参与业务授权 |

---

## RabbitMQ

**Trust Boundary:** External
**Role:** 消息中间件，承载 Webhook 事件与流水线内部事件队列；消息含加密 accessToken 等敏感字段。
**Data Flows:** DF11, DF12, DF13, DF14, DF15, DF16, DF17
**Pod Co-location:** N/A（集群内部部署）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T07.T | Tampering | 内部队列消息可被注入/篡改（若 MQ 凭据泄露或网络被中间人），可伪造 webhook/流水线事件触发任意操作 | Internal Network | DF13-D17 | 生产环境启用 TLS + MQ 凭据最小化 + 消息校验 | Open |
| T07.I | Information Disclosure | 非 prod 环境 RabbitMQ 为明文 TCP，消息中的加密 accessToken 与事件数据可被内部窃听 | Internal Network | DF11-D17 | prod 已启用 TLS；非 prod 建议启用 TLS 或网络隔离 | Open |
| T07.D | Denial of Service | 消费者处理慢/毒消息导致队列堆积，或消息风暴导致消费者过载 | Internal Network | DF13-D17 | 死信队列 + 延迟重试 + 消费并发控制（已实现） | Mitigated |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | MQ 连接使用用户名/密码认证 |
| Repudiation | 消息生产/消费由 MQ 追踪 |
| Elevation of Privilege | MQ 不直接参与业务授权 |
| Abuse | MQ 无业务逻辑可供滥用 |

---

## MySQL

**Trust Boundary:** External
**Role:** 业务数据库（流水线信息、PR 信息、机机账号、权限、加密 accessToken/webhook secret）。
**Data Flows:** DF22, DF23, DF24, DF25, DF26, DF27, DF28
**Pod Co-location:** N/A（集群内部部署）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T08.I | Information Disclosure | 数据库表含加密 accessToken、webhook secret、机机账号；若 DB 被攻破且解密密钥（part1）可得，可批量解密凭据 | Database Compromise | DF22-D28 | 凭据加密存储 + 密钥与数据分离 + 数据库访问最小化 | Open |
| T08.T | Tampering | 若可写 DB，攻击者可篡改权限表/流水线状态/公开仓可见性，实现越权与门禁绕过 | Database Compromise | DF22-D28 | 数据库写权限最小化 + 审计 + 关键数据防篡改 | Open |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | DB 连接使用账号密码认证 |
| Repudiation | DB 操作有 binlog/审计日志 |
| Denial of Service | 由基础设施高可用保障 |
| Elevation of Privilege | DB 不直接参与业务授权决策 |
| Abuse | DB 无业务逻辑可供滥用 |

---

## Redis

**Trust Boundary:** External
**Role:** 缓存（公开仓判定、权限缓存、分布式锁、幂等）。
**Data Flows:** DF29, DF30, DF31
**Pod Co-location:** N/A（集群内部部署）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T09.I | Information Disclosure | 非 prod 环境 Redis 为明文 TCP，公开仓判定/权限缓存可被内部窃听 | Internal Network | DF29 | prod 使用 `rediss://` TLS；非 prod 建议启用 TLS 或网络隔离 | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T09.T | Tampering | 若可写 Redis，攻击者可篡改公开仓判定缓存（`projectId+pipelineId` 值），导致匿名越权或误拒绝 | Redis Access | DF29 | 缓存写权限最小化 + 缓存值来源校验 + 短 TTL | Open |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | Redis 连接使用密码认证 |
| Repudiation | 缓存非审计主体 |
| Denial of Service | 缓存不可用有降级路径（回源查询） |
| Elevation of Privilege | 缓存不直接参与授权决策 |
| Abuse | 缓存无业务逻辑可供滥用 |

---

## PipelineControllerV2

**Trust Boundary:** Application
**Role:** 流水线主 REST 控制器（启动/停止/重试/白名单/导出等），`@CheckPermission`/`@ProjectAuth` 注解鉴权。
**Data Flows:** DF02, DF23, DF30, DF33
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T10.S | Spoofing | userId 从客户端请求参数/请求体提取（非服务端会话），攻击者可指定他人 userId 冒用身份执行权限校验 | Authenticated User | DF02 | 由网关/平台注入可信身份，服务端禁止信任客户端 userId（见 AuthInterceptor） | Open |
| T10.E | Elevation of Privilege | 通过构造越权 projectId/pipelineId 访问/操作他人流水线（启动/停止/导出/白名单），实现水平越权 | Authenticated User | DF02 | 权限校验与资源归属强绑定，导出等接口校验资源所有者 | Open |
| T10.I | Information Disclosure | 构建日志导出接口基于 jobId/buildNo 生成 OBS 临时签名 URL，若对象 key 归属校验缺失，可越权下载他人构建日志 | Authenticated User | DF02 | 导出前校验对象与流水线/用户的归属关系（见 ObsBucketServiceImpl） | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | 操作有操作日志与审计记录 |
| Denial of Service | 高频操作有 MQ 异步化与幂等保护 |
| Abuse | 滥用行为已通过启动/停止等操作频率受限；由管理员治理 |

---

## AuthInterceptor

**Trust Boundary:** Application
**Role:** 授权拦截器，基于客户端传入 userId/projectId 调 `UserRoleMapper.hasPermission`，处理匿名公开仓放行与本地缓存。
**Data Flows:** DF22, DF29
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T11.T | Tampering | 匿名公开仓判定中，流水线 `sources` 为空时直接放行（`PipelineDetailVO.getSources()` 为空即视为开放流水线），配置缺失的流水线可被匿名访问 | None | DF22 | 空 sources 不应默认放行，应返回未配置状态或要求显式公开标记 | Open |

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T11.S | Spoofing | 身份提取完全依赖客户端参数/请求体（`extractPermissionContext`），配合 JWT 不验签（JwtUtils.decode），可冒用任意 userId | Authenticated User | DF22 | 身份来自可信来源（网关注入），禁止信任客户端 userId | Open |
| T11.T2 | Tampering | Redis 公开仓缓存 key 由 `projectId + pipelineId` 无分隔符拼接（`openlibingRedis.hasKey(projectId + pipelineId)`），存在碰撞风险，私有流水线可能被误判为公开 | Authenticated User | DF29 | key 使用分隔符或哈希，避免碰撞 | Open |
| T11.I | Information Disclosure | 权限校验错误码区分 `REPO_NOT_FOUND`/`REPO_VISIBILITY_EMPTY`/`ANONYMOUS_ACCESS_DENIED` 等，可被用于探测仓库存在性与可见性 | Authenticated User | DF22 | 统一错误响应，避免信息泄露 | Mitigated |
| T11.D | Denial of Service | 权限校验异步缓存刷新线程池满或被拒绝，以及并发权限查询放大，可能导致权限校验失败/延迟 | Authenticated User | DF22 | 缓存 + 线程池隔离（已实现），建议增加熔断与降级 | Mitigated |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | 权限判定由操作日志记录，非本组件主要风险 |
| Elevation of Privilege | 授权绕过已通过 Spoofing/Tampering 维度覆盖 |
| Abuse | 权限校验逻辑无业务功能可供滥用 |

---

## ApigWebhookController

**Trust Boundary:** Application
**Role:** APIG 统一 Webhook 入口（`/apig/webhook/**`），7 个端点服务内 HMAC 验签后投递 MQ。
**Data Flows:** DF05, DF06, DF11
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T12.T | Tampering | GitCode 端点 HMAC 覆盖请求体（已缓解）；但 Gitee 端点签名不覆盖请求体，攻击者可在持有效 token 的情况下篡改事件体 | None | DF06 | Gitee 验签覆盖请求体（见 MachineInterfaceAuthUtil） | Open |
| T12.D | Denial of Service | Webhook 高并发直投 MQ，无应用层限流与幂等，可造成队列洪泛与重复处理 | None | DF11 | 增加幂等键（X-GitCode-Delivery/messageId）与限流 | Open |

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 入口对 GitCode/Gitee 均有验签（HMAC/token），未验签通过的请求被拒绝 |
| Repudiation | 机机调用有审计日志（machineInterfaceLog） |
| Information Disclosure | 入口不返回敏感业务数据 |
| Elevation of Privilege | 入口仅做验签与投递，无授权决策 |
| Abuse | 事件语义由下游 handler 处理，入口无业务滥用面 |

---

## WebHookEventController

**Trust Boundary:** Application
**Role:** 遗留 Webhook 入口（`/webhookEvent/hooks/**`），gitcode 端点服务内验签，gitee 端点依赖网关。
**Data Flows:** DF07, DF08, DF12
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T13.S | Spoofing | `giteeWebHookEvent` 无服务内验签（注释明确"鉴权放在 gateway 层"），任意调用者可伪造 Gitee 事件 | None | DF08 | 服务内补验签或下线遗留入口，统一收敛到 `/apig/webhook` | Open |
| T13.T | Tampering | Gitee 事件体可被任意篡改，触发伪造的流水线启动/停止/PR 操作 | None | DF08 | 服务内验签 + 事件字段校验 | Open |
| T13.A | Abuse | 伪造事件可反复触发构建/PR 自动化，消耗构建资源与配额 | None | DF08 | 幂等 + 频率限制 + 事件来源可信 | Open |

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | 需在补验签后补充审计（当前缺失，见 FIND-13） |
| Information Disclosure | 入口不返回敏感业务数据 |
| Denial of Service | 滥用已通过 Abuse 维度覆盖 |
| Elevation of Privilege | 入口无授权决策，伪造事件即达成越权（已覆盖） |

---

## CrossRegionController

**Trust Boundary:** Application
**Role:** 跨区域/黄蓝协同入口（`/cross-region/**`），gitcode hooks 验签，gitee hooks 与状态回写端点无服务内验签。
**Data Flows:** DF04, DF09, DF10
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T14.S | Spoofing | `updatePipelineStatus`/`getPipelineInfo`/`compileTrigger`/`getPrDetailProjectId`/`updatePrLinkUrl` 等端点无鉴权，任意调用者可伪造黄区/外部调用方 | None | DF04 | 为状态回写与查询接口增加服务内鉴权或签名 | Open |
| T14.T | Tampering | `updatePipelineStatus` 可篡改流水线门禁状态与 PR 门禁结果 | None | DF04 | 状态回写接口需校验来源 + 签名 + 幂等 | Open |
| T14.I | Information Disclosure | `getPipelineInfo` 根据 org/repo/pr 返回流水线状态，未授权者可枚举查询他人流水线状态 | None | DF04 | 查询接口增加鉴权与访问控制 | Open |
| T14.A | Abuse | `compileTrigger` 可被任意调用触发编译脚本，`handleGiteeHooks*` 可创建跳转评论，造成资源滥用与骚扰评论 | None | DF10 | 服务内验签 + 频率限制 + 调用方白名单 | Open |

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | 需在补鉴权后补充审计（当前缺失） |
| Denial of Service | 滥用已通过 Abuse 维度覆盖 |

---

## InternalPipelineController

**Trust Boundary:** Application
**Role:** 微服务间内部接口（`/internal/**`），调用 `PipelineStartEventHandler.startPipeline` 启动流水线，无服务内鉴权。
**Data Flows:** DF03
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T15.S | Spoofing | `/internal/prStartPipeline` 无服务内鉴权，内部网络调用者可伪装为内部服务触发任意流水线启动 | Internal Network | DF03 | 机机接口增加服务间鉴权（token/签名） | Open |
| T15.E | Elevation of Privilege | 直接调用 handler 绕过 `AuthInterceptor` 权限校验，实现对任意流水线的启动控制 | Internal Network | DF03 | 内部接口同样需要鉴权与来源校验 | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Tampering | 请求体为 `PrStartPipelineVo`，启动参数直接影响行为（已通过 Spoofing/E 覆盖） |
| Repudiation | 需补充内部调用审计 |
| Information Disclosure | 接口不返回敏感业务数据 |
| Denial of Service | 触发构建可消耗资源（已通过 E 维度覆盖滥用） |
| Abuse | 触发构建即滥用（已通过 E 维度覆盖） |

---

## MachineInterfaceAuthUtil

**Trust Boundary:** Application
**Role:** Webhook 签名校验核心（GitCode HMAC-SHA256、Gitee token+timestamp）与机机接口审计日志。
**Data Flows:** DF05, DF06
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T16.T | Tampering | Gitee 验签 `message = timestamp + "\n" + secretKey`，不包含请求体且无时间窗校验，可被重放或配合 token 泄露篡改事件 | None | DF06 | 请求体参与签名 + 时间窗校验 + 抗重放 nonce | Open |
| T16.R | Repudiation | `machineInterfaceLog` 不记录验签结果与调用结果（`requestStatus="unknown"`），无法审计恶意 webhook | None | DF05 | 审计日志记录验签结果、签名摘要与处理结果 | Open |

#### Tier 2 — Conditional Risk

*No Tier 2 threats identified.*

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T16.S | Spoofing | 签名比对使用字符串 `equals`（非常量时间比较），理论上存在时序侧信道；HTTPS 下实际利用难度极高，属防御纵深 | Network Access | DF06 | 使用 `MessageDigest.isEqual` 常量时间比较 | Open |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Information Disclosure | 验签组件不直接暴露敏感数据（密钥解密结果仅内存使用） |
| Denial of Service | 验签为纯计算，无独立 DoS 面 |
| Elevation of Privilege | 验签通过即放行，伪造即达成（已通过 Tampering 覆盖） |
| Abuse | 验签逻辑无业务功能可供滥用 |

---

## WebHookEventConsumer

**Trust Boundary:** Application
**Role:** Webhook 事件 MQ 消费者，分发到各 handler（启动/停止/重试/PR 事件）并触发副作用。
**Data Flows:** DF13, DF24, DF31
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T17.T | Tampering | 消费的消息若被篡改/伪造（MQ 凭据泄露），可触发任意 webhook 事件 handler 副作用（启动/停止/PR 自动化） | Internal Network | DF13 | MQ 访问控制 + 消息来源校验 + prod TLS | Open |
| T17.D | Denial of Service | 100 并发消费 + 异常重试，若 handler 持续失败或消息风暴，可造成消息重入队放大与队列堆积 | Internal Network | DF13 | 重试次数上限 + 死信队列（已实现）+ 熔断 | Mitigated |
| T17.I | Information Disclosure | 日志打印消息体前 500 字符预览（`previewBody`），事件内容可能含仓库/PR 等敏感信息 | Internal Network | DF13 | 日志脱敏（部分已用 `maskSensitiveFields`），预览需裁剪敏感字段 | Mitigated |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 消息来源由 MQ 与上层验签保证 |
| Repudiation | 消费处理有日志 |
| Elevation of Privilege | 消费者无授权决策，伪造消息即达成越权（已通过 Tampering 覆盖） |
| Abuse | 事件语义由 handler 处理，滥用已通过 Tampering 覆盖 |

---

## PipelineEventConsumer

**Trust Boundary:** Application
**Role:** 流水线业务事件消费者（bisect/下载/构建分析/详情/排队时间/自动建 Issue）。
**Data Flows:** DF14, DF26
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T18.T | Tampering | 内部事件消息若被篡改，可触发下载/构建分析/自动建 Issue 等副作用 | Internal Network | DF14 | MQ 访问控制 + prod TLS | Open |
| T18.A | Abuse | 事件风暴（重复 bisect/分析/自动建 Issue）可造成资源消耗与噪音 | Internal Network | DF14 | 幂等 + 频率限制 + 去重 | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 消息来源由 MQ 保证 |
| Repudiation | 消费处理有日志 |
| Information Disclosure | 消费事件数据有脱敏（`maskSensitiveFields`） |
| Denial of Service | 滥用已通过 Abuse 维度覆盖 |
| Elevation of Privilege | 消费者无授权决策 |

---

## PipelineStatusUpdateConsumer

**Trust Boundary:** Application
**Role:** 流水线状态更新消费者，解密 token 后回写华为云/第三方并更新 DB。
**Data Flows:** DF15, DF25, DF35
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T19.T | Tampering | 状态更新消息含加密 accessToken，若消息被篡改/伪造，可让服务以错误身份更新 PR 标签/门禁/commit status | Internal Network | DF15, DF35 | MQ 访问控制 + 消息完整性 + prod TLS | Open |
| T19.A | Abuse | 伪造终态状态消息（COMPLETED/FAILED）可提前结束流水线或操纵门禁结果 | Internal Network | DF15 | 状态迁移校验 + 消息来源可信 | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T19.I | Information Disclosure | accessToken 解密于内存并写入 DB（加密），日志已用 `maskSensitiveFields` 脱敏；但若 DB 与解密密钥同时失陷，token 可被解密 | Database Compromise | DF25 | 凭据加密 + 密钥分离 + 日志脱敏（已实现） | Open |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 消息来源由 MQ 保证 |
| Repudiation | 状态更新有日志与 DB 记录 |
| Denial of Service | 异常路由延迟队列重试（已实现） |
| Elevation of Privilege | 消费者无授权决策，伪造消息即越权（已通过 Tampering 覆盖） |

---

## PrOpEventConsumer

**Trust Boundary:** Application
**Role:** PR 异步操作消费者（更新标签、刷新评论、推送 commit status）。
**Data Flows:** DF16, DF27
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T20.T | Tampering | PR 操作消息若被篡改，可对任意 PR 更新标签/评论/commit status，造成 PR 状态污染 | Internal Network | DF16 | MQ 访问控制 + prod TLS + 操作归属校验 | Open |
| T20.A | Abuse | 重复消费/伪造消息可造成重复评论、标签错乱 | Internal Network | DF16 | 幂等 + 去重（延迟队列已实现） | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 消息来源由 MQ 保证 |
| Repudiation | 操作有日志 |
| Information Disclosure | 消费数据有脱敏 |
| Denial of Service | 滥用已通过 Abuse 维度覆盖 |
| Elevation of Privilege | 消费者无授权决策 |

---

## PipelineFailEmailConsumer

**Trust Boundary:** Application
**Role:** 流水线失败邮件消费者，读仓库 `.notification.yaml` 解析收件人并发邮件。
**Data Flows:** DF17, DF28
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T21.I | Information Disclosure | 收件人解析自仓库 `.notification.yaml`，若该文件可被攻击者控制，可收集/篡改收件人列表，导致邮件泄露给未授权邮箱或钓鱼 | Internal Network | DF28 | 校验通知文件来源与格式，收件人白名单 | Open |
| T21.A | Abuse | 流水线失败事件可被触发邮件轰炸（每次失败发邮件） | Internal Network | DF17 | 邮件频率限制 + 事件去重 | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 消息来源由 MQ 保证 |
| Tampering | 邮件内容为系统生成，篡改面低 |
| Repudiation | 邮件发送有日志 |
| Denial of Service | 邮件轰炸已通过 Abuse 维度覆盖 |
| Elevation of Privilege | 消费者无授权决策 |

---

## XxlJobHandler

**Trust Boundary:** Application
**Role:** XXL-Job 定时任务（14 个），含批量投递 MQ、接受项目邀请、刷新 Webhook 等。
**Data Flows:** DF32
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T22.T | Tampering | 任务 `jobParam` 直接作为可信输入（webhook 刷新 `customOrgs` 携带自定义 token、批量投递），恶意参数可造成批量误操作 | Internal Network | DF32 | jobParam 白名单校验 + 敏感参数加密，禁止明文 token 传参 | Open |
| T22.A | Abuse | 定时任务被恶意/重复触发可放大批量投递与刷新操作 | Internal Network | DF32 | 任务幂等 + 触发频率控制 + 操作审计 | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 任务触发由 XXL-Job 与 accessToken 保证 |
| Repudiation | 任务执行有 XXL-Job 日志 |
| Information Disclosure | 任务日志需脱敏（部分敏感 token） |
| Denial of Service | 滥用已通过 Abuse 维度覆盖 |
| Elevation of Privilege | 任务执行权限由调度中心控制 |

---

## PipelineStatusThirdPartyApiClient

**Trust Boundary:** Application
**Role:** GitCode/Gitee 三方 API 客户端（PR 标签/评论/commit status/执行日志），PRIVATE-TOKEN 认证。
**Data Flows:** DF18, DF19
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T23.I | Information Disclosure | 携带 PRIVATE-TOKEN 调用三方 API，若 token 被日志记录或在传输中泄露（配合凭据失陷），可冒用身份操作他人仓库 | Internal Network | DF18, DF19 | token 加密存储 + 日志脱敏 + HTTPS + token 最小权限 | Open |
| T23.T | Tampering | 依赖三方 API 返回数据更新本地状态，若响应被篡改（配合链路失陷）可污染流水线/PR 状态 | Internal Network | DF18 | 响应字段校验 + 三方数据仅作参考 | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 对三方使用 PRIVATE-TOKEN 认证 |
| Repudiation | 调用有三方 API 日志 |
| Denial of Service | 三方超时/限流有延迟重试（已实现） |
| Elevation of Privilege | 客户端无授权决策 |
| Abuse | 客户端无业务功能可供滥用 |

---

## HwCloudClient

**Trust Boundary:** Application
**Role:** 华为云客户端（OBS/SWR/CodeCheck/APIGateway SDK），AK/SK 解密后调用，部分链路关闭 SSL 校验。
**Data Flows:** DF20, DF34
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T24.T | Tampering | `getDataResultFromHWCloudHttpApi` 使用 `buildPipelineSslHttpsClient(false)` 关闭 SSL 证书校验，中间人可截获/篡改带 AK/SK 签名的请求与响应 | Internal Network | DF20 | 启用证书校验，至少对生产链路强制 verify | Open |
| T24.I | Information Disclosure | AK/SK 解密后用于构造请求，若解密结果进入日志或请求异常信息，可能泄露华为云凭据 | Internal Network | DF20 | 日志脱敏 + 异常信息不包含凭据 | Open |
| T24.A | Abuse | 部分调用使用无超时客户端（`buildPipelineSslHttpsClient`），远端无响应时可造成线程阻塞放大 | Internal Network | DF20 | 统一使用带超时客户端（WithTimeout 变体已提供） | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 对华为云使用 AK/SK 签名认证 |
| Repudiation | 调用有云侧审计日志 |
| Denial of Service | 超时/线程阻塞已通过 Abuse 维度覆盖 |
| Elevation of Privilege | 客户端无授权决策 |

---

## ObsBucketServiceImpl

**Trust Boundary:** Application
**Role:** OBS 对象存储服务，AK/SK 解密创建客户端，生成临时签名下载 URL。
**Data Flows:** DF21
**Pod Co-location:** N/A（单进程）

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified.*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T25.I | Information Disclosure | `getSignedUrl` 为任意 objectKey 生成 OBS 临时 GET 签名 URL，若 objectKey 由用户可控的 jobId/buildNo 拼接且未校验归属，可越权下载他人构建日志 | Authenticated User | DF21 | 生成签名 URL 前校验对象与流水线/用户归属 | Open |
| T25.T | Tampering | AK/SK 解密创建 ObsClient 且实例缓存于字段（`obsClient` 懒加载非线程安全），并发初始化或实例被替换可能造成凭据/请求异常 | Internal Network | DF21 | 单例安全初始化（volatile/双重检查）或每次创建 | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 对 OBS 使用 AK/SK 签名认证 |
| Repudiation | OBS 操作有云侧审计日志 |
| Denial of Service | 对象下载为正常功能，滥用已通过 Information Disclosure 维度覆盖 |
| Elevation of Privilege | 服务无授权决策 |
| Abuse | 签名 URL 生成无业务滥用面（下载为正常功能） |
