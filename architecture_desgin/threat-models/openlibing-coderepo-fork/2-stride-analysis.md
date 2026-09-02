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
| WebHookEventController | [Link](#webhookeventcontroller) | 2 | 1 | 0 | 1 | 2 | 0 | 1 | 7 | 0 | 6 | 1 | High |
| RepoController | [Link](#repocontroller) | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 5 | 0 | 5 | 0 | Medium |
| ProjectConfigController | [Link](#projectconfigcontroller) | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 4 | 0 | 4 | 0 | High |
| SyncUserController | [Link](#syncusercontroller) | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 3 | 0 | 3 | 0 | Medium |
| CodeMetricsController | [Link](#codemetricscontroller) | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 3 | 0 | 3 | 0 | Medium |
| PrAccessTokenServiceImpl | [Link](#praccesstokenserviceimpl) | 1 | 0 | 0 | 2 | 1 | 0 | 0 | 4 | 0 | 4 | 0 | High |
| WebhookEventConsumer | [Link](#webhookeventconsumer) | 0 | 1 | 0 | 1 | 2 | 0 | 1 | 5 | 0 | 5 | 0 | High |
| XxlJobHandler | [Link](#xxljobhandler) | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 3 | 0 | 3 | 0 | Medium |
| MySQL | [Link](#mysql) | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 3 | 0 | 2 | 1 | Medium |
| MongoDB | [Link](#mongodb) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | Low |
| Redis | [Link](#redis) | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 3 | 0 | 3 | 0 | Medium |
| RabbitMQ | [Link](#rabbitmq) | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 3 | 0 | 3 | 0 | Medium |
| GitCode | [Link](#gitcode) | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 | 0 | 2 | 0 | Low |
| Gitee | [Link](#gitee) | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | Low |
| Github | [Link](#github) | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | Low |
| Nacos | [Link](#nacos) | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 3 | 0 | 1 | 2 | High |
| XXLJob | [Link](#xxljob) | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 0 | 2 | 0 | Low |
| OBS | [Link](#obs) | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 3 | 0 | 3 | 0 | Medium |
| **Totals** | | **8** | **11** | **1** | **16** | **11** | **8** | **4** | **59** | **0** | **55** | **4** | |

---

## WebHookEventController

**Trust Boundary:** Application
**Role:** 接收 GitCode/Gitee/GitHub 三大平台 Webhook 事件的 REST 控制器，HMAC-SHA256 签名校验后投递 RabbitMQ
**Data Flows:** DF05, DF06, DF07, DF08, DF26
**Pod Co-location:** N/A (非 K8s Sidecar 部署)

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. 所有入站流量经华为云 APIG IP 白名单与限流，应用层 HMAC 签名校验构成双重屏障，无前置条件的直接暴露面被关闭。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T01.1 | Spoofing | HMAC-SHA256 签名比对使用 `String.equals()`（非恒定时间），存在时序侧信道攻击风险，攻击者可通过测量响应时间逐字节推断正确签名 | Authenticated User | DF05, DF06, DF07 | 改用 `MessageDigest.isEqual()` 或 `java.security.MessageDigest.isEqual()` 进行恒定时间签名比对 | Open |
| T01.3 | Tampering | Webhook 事件无时间戳/nonce 重放保护，攻击者截获合法事件后可重放触发重复处理 | Authenticated User | DF05, DF06, DF07 | 增加 `X-GitCode-Delivery`/`X-GitHub-Delivery` 去重缓存（Redis TTL 窗口内拒绝重复 delivery ID） | Open |
| T01.4 | Information Disclosure | `X-GitCode-Token` 等敏感头部在 INFO 日志中输出，日志泄露可暴露平台 token | Authenticated User | DF05 | 降低日志级别或脱敏 `X-GitCode-Token`/`X-Gitee-Token` 头部值 | Open |
| T01.5 | Denial of Service | 应用层无限流（依赖 APIG），签名校验本身消耗 CPU，大量伪造签名请求可造成 CPU 耗尽 | Authenticated User | DF05, DF06, DF07 | 在应用层增加 IP 级别限流或签名校验前的前置过滤 | Open |
| T01.6 | Denial of Service | RabbitMQ 投递失败时仅返回失败不重试，平台侧重发可形成消息洪泛 | Authenticated User | DF08 | 增加幂等去重 + 背压机制，限制单平台并发投递速率 | Open |
| T01.7 | Abuse | Gitee 平台 webhook 鉴权硬编码返回 false（停用告警抑制扫描），合法 Gitee 事件被全部拒绝，造成 Gitee 仓库告警抑制功能失效 | Authenticated User | DF06 | 如需停用 Gitee，应在 APIG 层路由级禁用而非应用层硬编码拒绝，避免功能静默失效 | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T01.2 | Spoofing | Webhook 密钥 `webhook.secretKey` 存储于 Apollo/Nacos 配置，配置中心被入侵或 `security.part1` 工作密钥泄露后，攻击者可解密获取 webhook 密钥，伪造任意平台事件 | Admin Credentials | DF05, DF06, DF07, DF26 | 配置中心启用独立账号 + MFA，`security.part1` 从环境变量或 Vault 注入而非配置文件 | Open |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | Webhook 事件携带 `X-GitCode-Delivery`/`X-GitHub-Delivery` 唯一 ID，且 LOGGER.info 记录事件起始与投递结果，具备不可否认性基础 |
| Elevation of Privilege | Webhook 接入仅做事件投递，不涉及用户身份或权限提升逻辑 |

---

## RepoController

**Trust Boundary:** Application
**Role:** 仓库元数据 CRUD REST 控制器，处理仓库录入/查询/批量删除/导出等接口
**Data Flows:** DF02, DF10, DF24
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. REST 接口经 APIG 网关用户 token 鉴权，无未认证直接暴露面。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T02.1 | Tampering | 仓库导出文件路径未严格校验，可能存在路径遍历风险（如 `../` 跨目录写入 OBS） | Authenticated User | DF24 | 对导出文件名做白名单字符校验，拒绝 `..` 与绝对路径 |
| T02.2 | Information Disclosure | 异常处理返回详细错误信息（含仓库 URL、内部 ID），可泄露仓库元数据 | Authenticated User | DF02 | 异常响应统一脱敏，仅返回错误码与简短提示 |
| T02.3 | Denial of Service | 大规模仓库导出请求无并发限制，OBS 上传与序列化消耗内存与带宽 | Authenticated User | DF24 | 限制单用户并发导出数量，导出任务异步化 + 队列削峰 |
| T02.4 | Elevation of Privilege | 仓库操作仅校验用户登录态，未校验用户对该仓库的归属权限，存在 IDOR（越权访问他人项目下仓库） | Authenticated User | DF10 | 在仓库查询/删除接口增加 `projectId` 与用户角色的联合校验 |
| T02.5 | Abuse | 仓库 URL 录入未校验内网地址，攻击者可录入 `http://127.0.0.1:xxx` 或内网服务 URL，后续同步任务触发 SSRF | Authenticated User | DF10 | 仓库 URL 录入时校验域名白名单（仅允许 gitcode.com/gitee.com/github.com），拒绝内网 IP 与 localhost |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 用户身份由 APIG 网关 token 校验保障，应用层不直接处理身份伪造 |
| Repudiation | `RepoLogHandler` AOP 切面记录仓库操作日志，操作行为可追溯 |

---

## ProjectConfigController

**Trust Boundary:** Application
**Role:** 项目配置与全局配置管理 REST 控制器，管理项目级 Token、SIG 路径、全局开关
**Data Flows:** DF01, DF11
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. 管理接口经 APIG 网关鉴权 + 角色权限校验。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T03.1 | Tampering | SIG 扫描路径配置可指向恶意仓库 URL，后续扫描任务拉取恶意 sig-info.yaml 注入恶意配置 | Privileged User | DF11 | SIG 路径录入校验域名白名单，sig-info.yaml 解析增加 schema 校验 |
| T03.2 | Repudiation | 全局配置（如 `github.common.access_token`）修改若未记录操作者身份与变更前后值，事后无法追溯 | Privileged User | DF11 | 全局配置变更强制走 `SpaceUserLogHandler` AOP 记录操作者、字段、旧值新值 |
| T03.3 | Information Disclosure | 项目级 Token 查询接口若返回明文或可解密 token，造成凭证泄露 | Privileged User | DF11 | Token 查询接口仅返回掩码（如 `ghp_****xxxx`），明文 token 仅在内部服务调用链传递 |
| T03.4 | Elevation of Privilege | 项目角色映射（GitCodeRoleMapping）可被管理员篡改为高权限角色，实现权限提升 | Privileged User | DF11 | 角色映射变更需双人审批或操作日志告警 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 管理员身份由网关鉴权保障，应用层不处理身份伪造 |
| Denial of Service | 配置接口为低频管理操作，无高频并发场景 |
| Abuse | 配置管理为标准 CRUD，无业务逻辑可被滥用 |

---

## SyncUserController

**Trust Boundary:** Application
**Role:** 用户与权限同步 REST 控制器，对接 IAM 与 openubmc 同步用户与角色权限
**Data Flows:** DF04, DF12
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. 同步接口经 APIG 鉴权。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T04.1 | Information Disclosure | 用户同步接口返回用户列表可能包含邮箱、账号等 PII，越权调用可批量获取用户信息 | Authenticated User | DF12 | 用户列表接口按调用方角色脱敏，非管理员仅返回必要字段 |
| T04.2 | Denial of Service | 批量用户同步无分页与并发限制，大组织全量同步可造成 MySQL 写入压力与连接池耗尽 | Authenticated User | DF12 | 同步接口强制分页，单次同步上限 + 异步队列削峰 |
| T04.3 | Elevation of Privilege | 同步接口若接受外部传入的 `roleId`，攻击者可注入高权限角色 ID 实现权限提升 | Authenticated User | DF12 | 角色分配需校验调用方权限是否高于目标角色，禁止平级或越级授权 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 用户身份由网关鉴权保障 |
| Tampering | 用户数据写入经 MyBatis 参数化查询，无直接篡改风险 |
| Repudiation | `SpaceUserLogHandler` AOP 记录用户同步操作 |
| Abuse | 同步为标准 CRUD，无业务逻辑可被滥用 |

---

## CodeMetricsController

**Trust Boundary:** Application
**Role:** 代码度量查询 REST 控制器，提供 cloc/重复块/文件详情等度量查询接口
**Data Flows:** DF03, DF13
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. 查询接口经 APIG 鉴权。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T05.1 | Tampering | MongoDB 查询参数若拼接为查询 JSON，存在 NoSQL 注入风险（如 `{$ne: null}` 条件注入） | Authenticated User | DF13 | 使用 Spring Data MongoDB 的类型安全查询构建器，禁止字符串拼接查询 |
| T05.2 | Information Disclosure | 文件详情接口返回源代码内容片段，越权调用可读取他人仓库代码 | Authenticated User | DF13 | 文件内容查询校验用户对该仓库的访问权限，非授权仓库拒绝返回内容 |
| T05.3 | Elevation of Privilege | 度量查询仅校验登录态，未校验仓库归属，存在 IDOR（越权查询他人仓库度量） | Authenticated User | DF13 | 度量查询接口增加 `projectId` + 用户角色联合校验 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 用户身份由网关鉴权保障 |
| Repudiation | 度量查询为只读操作，无审计需求 |
| Denial of Service | 查询接口可由 APIG 限流保护 |
| Abuse | 查询为标准只读操作 |

---

## PrAccessTokenServiceImpl

**Trust Boundary:** Application
**Role:** PR 场景 access token 获取服务，负责仓库/项目级 token 解密、校验与缓存
**Data Flows:** DF20, DF21, DF22, DF23
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. 该服务为内部 Service，无独立监听端口，仅被 Controller/Consumer 调用。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T06.1 | Spoofing | GitHub 平台 token 不校验有效性（`if ("github".equals(platform)) return true;`），失效或被撤销的 GitHub token 仍被使用，可能触发 401 暴露或被 GitHub 侧告警 | Authenticated User | DF19 | GitHub token 同样调用 `/user` 接口校验，或至少捕获 401 后标记失效 |
| T06.2 | Information Disclosure | token 有效性缓存 key 为 `webhook:token:valid:{platform}:{token.hashCode()}`，`hashCode()` 可碰撞且为 32 位整数，存在缓存碰撞导致无效 token 被判为有效的风险 | Authenticated User | DF22 | 缓存 key 改用 token 的 SHA-256 摘要（非 hashCode），降低碰撞概率 |
| T06.3 | Information Disclosure | token 校验失败的 WARN 日志可能包含 token 片段或平台信息，多次失败日志聚合可泄露 token 模式 | Authenticated User | DF20, DF21 | 日志中 token 一律脱敏，仅记录 `token:***` 与校验结果 |
| T06.4 | Denial of Service | Redis 不可用时 fallback 调用外部 API 校验 token，高频 webhook 事件可造成 GitCode/Gitee API 限流耗尽 | Authenticated User | DF20, DF21, DF22 | Redis 不可用时直接拒绝 webhook 处理（fail-closed）而非 fallback 到外部 API |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Tampering | token 解密使用 `SecurityUtil.decrypt`，密文来自数据库，应用层不直接篡改 |
| Repudiation | token 获取为内部服务调用，无独立审计需求 |
| Elevation of Privilege | token 获取按"仓库私有 → 项目级 → 公共"优先级，无权限提升路径 |
| Abuse | token 获取为标准内部逻辑 |

---

## WebhookEventConsumer

**Trust Boundary:** Application
**Role:** RabbitMQ 异步消费者，消费 webhook 事件并分发至 MergeRequestEventHandler 等处理器
**Data Flows:** DF09, DF14, DF15, DF17, DF18, DF19
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. 消费者从 RabbitMQ 队列消费，需 Internal Network 访问消息队列。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T07.1 | Tampering | Webhook 事件 body 经 `JSON.parseObject` 解析后直接用于数据库查询参数，若 MyBatis mapper 使用 `${}` 拼接，存在 SQL 注入风险 | Internal Network | DF09, DF14 | 审计所有 mapper XML，确保使用 `#{}` 参数化；对 webhook body 字段做白名单校验 |
| T07.2 | Information Disclosure | 事件处理异常栈与 body 内容可能写入 MongoDB 日志集合，含仓库 URL、提交者信息等敏感数据 | Internal Network | DF15 | 异常日志脱敏，body 内容按字段白名单记录 |
| T07.3 | Denial of Service | 消费者调用 GitCode/Gitee/Github PR API 无限流，高频 webhook 事件可触发平台 API 限流（429），导致后续合法 PR 操作失败 | Internal Network | DF17, DF18, DF19 | 消费者侧增加平台 API 调用限流（令牌桶），429 时指数退避重试 |
| T07.4 | Denial of Service | Webhook body 大小仅在 APIG 层限制（16MB），消费者反序列化大 JSON 可造成 OOM | Internal Network | DF09 | 消费者侧增加 body 大小校验，超限消息直接死信队列 |
| T07.5 | Abuse | 事件消费无幂等去重，重复投递的 webhook 事件可触发重复 PR 评论/标签，造成 PR 噪音与平台 API 配额浪费 | Internal Network | DF09 | 消费者基于 `X-GitCode-Delivery` + 事件类型做幂等去重（Redis SET NX TTL） |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 消费者从 RabbitMQ 队列消费，消息源身份由队列鉴权保障 |
| Repudiation | 消费处理结果写入 MongoDB 日志，可追溯 |
| Elevation of Privilege | 消费者使用 PrAccessTokenServiceImpl 获取 token，无权限提升路径 |

---

## XxlJobHandler

**Trust Boundary:** Application
**Role:** XXL-Job 定时任务执行器，执行仓库同步、分支刷新、Token 轮换等周期任务
**Data Flows:** DF16, DF25, DF27, DF28, DF29
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. 执行器通过 XXL-Job SDK 与调度中心通信，需 Internal Network 访问调度中心。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T08.1 | Spoofing | XXL-Job 执行器 token 泄露后，攻击者可伪装为调度中心触发任意任务执行 | Internal Network | DF25 | 执行器 token 定期轮换，调度中心与执行器双向 mTLS 认证 |
| T08.2 | Tampering | 定时任务参数（如仓库 ID 列表、同步范围）若来自调度中心且未校验，恶意调度可注入超范围参数 | Internal Network | DF16, DF25 | 任务参数做白名单校验，拒绝超范围仓库 ID 与异常分页大小 |
| T08.3 | Denial of Service | 全量仓库同步任务无分页与并发限制，大批量仓库同步可造成 MySQL 读写压力与平台 API 限流 | Internal Network | DF16, DF27, DF28, DF29 | 同步任务强制分页，单次同步上限 + 平台 API 调用限流 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | XXL-Job 调度中心记录任务触发与执行结果日志 |
| Information Disclosure | 定时任务不直接返回数据给外部，无泄露面 |
| Elevation of Privilege | 任务执行使用应用自身权限，无用户身份提升 |
| Abuse | 定时任务为标准同步逻辑 |

---

## MySQL

**Trust Boundary:** External
**Role:** 关系型数据库，存储项目/仓库/用户/角色/Token 配置
**Data Flows:** DF10, DF11, DF12, DF14, DF16, DF23
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. MySQL 为云数据库内网访问，需 Internal Network。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T09.1 | Tampering | MyBatis mapper XML 若存在 `${}` 拼接（如动态表名、排序字段），可被 SQL 注入 | Internal Network | DF10, DF11, DF14 | 审计所有 mapper XML，`${}` 仅用于安全白名单字段（如表名），用户输入一律 `#{}` |
| T09.3 | Elevation of Privilege | 数据库为单账号访问，无行级权限控制（RLS），任何已认证应用请求可读取全表数据，存在越权读取风险 | Internal Network | DF10, DF11 | 应用层在 service 层强制 `projectId` + 用户角色过滤，避免全表查询暴露 |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T09.2 | Information Disclosure | 数据库密码经 `SecurityUtil.decrypt(password, part1)` 解密，`security.part1` 工作密钥也存储于 Nacos/Apollo 配置，配置中心被入侵后数据库密码可被解密 | Admin Credentials | DF10 | `security.part1` 从环境变量或 Vault 注入，不与密码同源存储；数据库账号使用最小权限 |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 数据库为外部托管服务，身份由连接字符串与凭证保障 |
| Repudiation | 数据库操作由应用 AOP 日志记录，非数据库职责 |
| Denial of Service | 云数据库由华为云保障可用性，应用层 HikariCP 连接池限流 |
| Abuse | 数据库为标准存储，无业务逻辑可被滥用 |

---

## MongoDB

**Trust Boundary:** External
**Role:** 文档型数据库，存储操作日志、代码度量记录、PR 流水线记录
**Data Flows:** DF13, DF15
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. MongoDB 为云数据库内网访问，需 Internal Network。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T10.1 | Tampering | MongoDB 查询若使用字符串拼接构建查询 JSON，存在 NoSQL 注入风险（如 `{$where: "..."}`） | Internal Network | DF13 | 使用 Spring Data MongoDB 类型安全查询构建器，禁止字符串拼接 |
| T10.2 | Information Disclosure | MongoDB 存储操作日志与 PR 流水线记录，可能包含仓库 URL、提交者账号、PR 标题等敏感数据，越权查询可批量获取 | Internal Network | DF15 | 日志集合按项目隔离，查询强制 `projectId` 过滤；敏感字段脱敏后写入 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | MongoDB 为外部托管服务，身份由凭证保障 |
| Repudiation | 日志写入由应用控制，非数据库职责 |
| Denial of Service | 云数据库由华为云保障可用性 |
| Elevation of Privilege | MongoDB 单账号访问，无权限提升路径 |
| Abuse | 数据库为标准存储 |

---

## Redis

**Trust Boundary:** External
**Role:** 缓存与分布式锁，缓存 token 有效性校验结果（TTL 10 分钟），Redisson 分布式锁
**Data Flows:** DF22
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. Redis 为云缓存内网访问且启用 SSL 与密码认证，需 Internal Network。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T11.1 | Tampering | token 有效性缓存 key 使用 `token.hashCode()`，Java String hashCode 为 32 位且可碰撞，攻击者构造碰撞 token 可继承有效 token 的缓存结果，绕过校验 | Internal Network | DF22 | 缓存 key 改用 token 的 SHA-256 摘要前 16 字节十六进制，降低碰撞 |
| T11.2 | Information Disclosure | token 有效性缓存值为 `"1"/"0"`，虽不直接存储明文 token，但 key 含 hashCode 可被暴力枚举；Redis 数据在内存中明文存储 | Internal Network | DF22 | 缓存 key 与值均不含明文 token，Redis 启用 ACL 区分读写权限 |
| T11.3 | Elevation of Privilege | Redis 单密码认证无 ACL，任何获知密码的客户端可读写全部 key，包括分布式锁 key，可恶意释放锁造成任务重复执行 | Internal Network | DF22 | Redis 6+ 启用 ACL，分布式锁 key 与缓存 key 分属不同权限账号 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | Redis 为外部托管服务，身份由凭证保障 |
| Repudiation | 缓存操作无审计需求 |
| Denial of Service | 云 Redis 由华为云保障可用性，连接池限制并发 |
| Abuse | Redis 为标准缓存 |

---

## RabbitMQ

**Trust Boundary:** External
**Role:** 消息队列，承载 webhook/notify/metrics/token 四类队列
**Data Flows:** DF08, DF09
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. RabbitMQ 为云消息队列内网访问，需 Internal Network。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T12.1 | Tampering | RabbitMQ 消息未签名，任何有队列写权限的客户端可伪造 webhook 事件消息投递到 `webhook_event_queue_beta`，触发消费者处理伪造事件 | Internal Network | DF08, DF09 | 队列写权限仅授予 WebHookEventController 服务账号；消息体增加 HMAC 签名头由消费者校验 |
| T12.2 | Denial of Service | 队列无消息速率限制，恶意生产者可投递大量无效消息造成队列堆积与消费者 OOM | Internal Network | DF08 | 队列配置最大长度（max-length）与死信队列，超限消息转入死信 |
| T12.3 | Abuse | 伪造的 webhook 事件消息可触发 PR 评论/标签等副作用操作，造成 PR 噪音与平台 API 配额浪费 | Internal Network | DF09 | 消费者校验消息来源（如生产者 ID 或签名），拒绝未授权生产者消息 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | RabbitMQ 为外部托管服务，身份由凭证保障 |
| Repudiation | 消息投递由 RabbitMQ 持久化日志记录 |
| Information Disclosure | 队列内容为业务事件，不含明文凭证 |
| Elevation of Privilege | 队列权限由 RabbitMQ 账号控制，无应用层提升路径 |

---

## GitCode

**Trust Boundary:** External
**Role:** GitCode 代码托管平台，既是 Webhook 事件来源，也是 PR 操作的 API 调用目标
**Data Flows:** DF05, DF17, DF20, DF27
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. GitCode 为外部第三方平台，从本系统视角为外部服务，攻击面由平台侧保障。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T13.1 | Information Disclosure | access token 通过 `PRIVATE-TOKEN` 请求头传输，若 HTTPS 连接在中间网络被劫持（如企业代理），token 可被截获 | Authenticated User | DF17, DF20, DF27 | 强制 HTTPS 并启用 HSTS，禁用 HTTP fallback；连接池禁用中间人证书 |
| T13.2 | Denial of Service | 高频 PR 操作与 token 校验调用可触发 GitCode API 限流（429），导致合法 PR 评论失败 | Authenticated User | DF17, DF20 | 应用侧令牌桶限流，429 时指数退避重试，失败消息入死信队列 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | 平台身份由 HTTPS 证书保障，本系统不校验平台身份 |
| Tampering | API 请求为标准 REST，数据完整性由 HTTPS 保障 |
| Repudiation | PR 操作由 GitCode 平台侧记录审计日志 |
| Elevation of Privilege | token 权限由 GitCode 平台侧控制 |
| Abuse | 平台 API 为标准 REST，滥用由平台侧限流 |

---

## Gitee

**Trust Boundary:** External
**Role:** Gitee 代码托管平台，Webhook 事件来源与 API 调用目标（已停用告警抑制扫描）
**Data Flows:** DF06, DF18, DF21, DF28
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. Gitee 为外部第三方平台。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T14.1 | Spoofing | Gitee webhook 鉴权硬编码返回 false（停用告警抑制扫描），但 `/apig/webhook/gitee/repo` 端点仍对外开放，任何能到达 APIG 的请求都会触发签名校验失败流程，存在功能滥用面 | Authenticated User | DF06 | 若 Gitee 已停用，应在 APIG 路由层直接下线 `/apig/webhook/gitee/repo`，避免无效端点暴露 |
| T14.2 | Information Disclosure | access token 通过 `PRIVATE-TOKEN` 请求头传输至 Gitee API，存在与 GitCode 相同的传输截获风险 | Authenticated User | DF18, DF21, DF28 | 强制 HTTPS 与 HSTS |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Tampering | API 请求为标准 REST，数据完整性由 HTTPS 保障 |
| Repudiation | PR 操作由 Gitee 平台侧记录审计日志 |
| Denial of Service | 平台 API 限流由 Gitee 侧控制 |
| Elevation of Privilege | token 权限由 Gitee 平台侧控制 |
| Abuse | 平台 API 为标准 REST |

---

## Github

**Trust Boundary:** External
**Role:** GitHub 代码托管平台，Webhook 事件来源与 API 调用目标
**Data Flows:** DF07, DF19, DF29
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. Github 为外部第三方平台。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T15.1 | Spoofing | GitHub token 在 `PrAccessTokenServiceImpl.isTokenValid` 中硬编码 `return true` 不校验有效性，失效或被撤销的 token 仍被使用，可能触发 GitHub 401 告警或账户异常检测 | Authenticated User | DF19 | GitHub token 同样调用 `/user` 接口校验，或至少捕获 401 后标记失效并告警 |
| T15.2 | Information Disclosure | access token 通过 `PRIVATE-TOKEN` 请求头传输至 GitHub API，存在传输截获风险 | Authenticated User | DF19, DF29 | 强制 HTTPS 与 HSTS |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Tampering | API 请求为标准 REST，数据完整性由 HTTPS 保障 |
| Repudiation | PR 操作由 GitHub 平台侧记录审计日志 |
| Denial of Service | 平台 API 限流由 GitHub 侧控制 |
| Elevation of Privilege | token 权限由 GitHub 平台侧控制 |
| Abuse | 平台 API 为标准 REST |

---

## Nacos

**Trust Boundary:** External
**Role:** 华为云 CSE Nacos 配置中心与服务注册发现
**Data Flows:** DF26
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. Nacos 为云服务内网访问，需 Internal Network。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T16.1 | Spoofing | 服务注册无双向认证时，攻击者可注册同名恶意实例，流量被路由到恶意节点 | Internal Network | DF26 | Nacos 启用鉴权 + 服务注册域名白名单，禁止未授权实例注册 |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T16.2 | Tampering | Nacos 配置被入侵或篡改后，可注入恶意 `security.part1`、`webhook.secretKey`、数据库密码等配置，导致应用使用攻击者控制的密钥与凭证 | Admin Credentials | DF26 | Nacos 启用配置变更审计与告警；关键配置（`security.part1`）从环境变量注入，禁止从配置中心覆盖 |
| T16.3 | Information Disclosure | Nacos 配置集中存储所有敏感凭证（数据库密码、Redis 密码、webhook secret、`security.part1`），Nacos 账号泄露即等同全部凭证泄露 | Admin Credentials | DF26 | Nacos 启用独立管理员账号 + MFA；敏感凭证改用 Vault 或华为云 DEW 托管，Nacos 仅存非敏感配置 |

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Repudiation | Nacos 配置变更由平台侧审计 |
| Denial of Service | 云 Nacos 由华为云保障可用性 |
| Elevation of Privilege | Nacos 权限由平台侧控制 |
| Abuse | Nacos 为标准配置中心 |

---

## XXLJob

**Trust Boundary:** External
**Role:** XXL-Job 调度中心，下发定时任务到本服务执行
**Data Flows:** DF25
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. XXLJob 调度中心为内网访问，需 Internal Network。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T17.1 | Spoofing | XXL-Job 调度中心 token 泄露后，攻击者可伪装为调度中心触发任意定时任务，在非调度时间执行同步任务 | Internal Network | DF25 | 调度中心 token 定期轮换，执行器与调度中心双向 mTLS 认证 |
| T17.2 | Elevation of Privilege | XXL-Job 调度参数若接受任意 JSON，恶意调度可注入超范围仓库 ID 或大分页参数，触发全量数据同步导致数据泄露或 DB 过载 | Internal Network | DF25 | 执行器侧对任务参数做白名单校验，拒绝超范围仓库 ID 与异常分页大小 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Tampering | 任务调度参数由调度中心控制，执行器不修改 |
| Repudiation | 任务执行结果由调度中心记录 |
| Information Disclosure | 定时任务不直接返回数据给外部 |
| Denial of Service | 调度中心由独立部署保障可用性 |
| Abuse | 定时任务为标准调度逻辑 |

---

## OBS

**Trust Boundary:** External
**Role:** 华为云对象存储 OBS，存放仓库导出产物（bucket: openlibing-export-beta）
**Data Flows:** DF24
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified. OBS 为云对象存储，访问需 AK/SK 签名认证。*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| T18.1 | Tampering | 导出文件上传路径未严格校验，可能存在路径遍历（如 `../` 跨前缀覆盖他人导出文件） | Authenticated User | DF24 | 导出文件名做白名单字符校验，按项目 + 用户隔离前缀 |
| T18.2 | Information Disclosure | 导出产物若通过公开 URL 或宽松 bucket 策略访问，未授权用户可读取他人导出文件（含仓库元数据） | Authenticated User | DF24 | 导出文件使用预签名 URL（短期有效），bucket 策略设为私有 |
| T18.3 | Elevation of Privilege | OBS AK/SK 若与应用其他凭证同源存储（Nacos），配置中心被入侵后可获取 OBS 写权限，覆盖或删除导出产物 | Authenticated User | DF24 | OBS AK/SK 使用最小权限 IAM 账号，仅允许写指定 bucket 前缀 |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified for this repository.*

#### Categories Not Applicable

| Category | Justification |
|----------|---------------|
| Spoofing | OBS 为外部托管服务，身份由 AK/SK 签名保障 |
| Repudiation | OBS 操作日志由华为云云审计服务（CTS）记录 |
| Denial of Service | 云 OBS 由华为云保障可用性 |
| Abuse | OBS 为标准对象存储 |
