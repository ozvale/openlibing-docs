# Security Findings

---

## Tier 1 — Direct Exposure (No Prerequisites)

### FIND-01: Gitee Webhook 遗留端点无服务内验签，可伪造事件触发流水线

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Critical |
| CVSS 4.0 | 9.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N) |
| CWE | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | None |
| Exploitability Tier | Tier 1 — Direct exposure, no prerequisites |
| Remediation Effort | Medium |
| Mitigation Type | Redesign |
| Component | WebHookEventController |
| Related Threats | [T13.S](2-stride-analysis.md#webhookeventcontroller), [T13.T](2-stride-analysis.md#webhookeventcontroller), [T13.A](2-stride-analysis.md#webhookeventcontroller) |

#### Description

`WebHookEventController.giteeWebHookEvent`（`POST /webhookEvent/hooks/gitee/{pipelineId}`）未做任何服务内验签，代码注释明确"鉴权放在 gateway 层"。一旦网关侧未对该路径实施严格认证（或网关认证被绕过），任意外部调用者均可伪造 Gitee 事件，触发流水线启动/停止、PR 自动化等副作用。同类的遗留 `CrossRegionController` gitee 端点（`handleGiteeHooks` 等）同样无服务内验签。该问题与 FIND-03 叠加后，攻击面进一步放大到 `ApigWebhookController` 的 Gitee 入口（见 T12.T）。

#### Evidence

**Prerequisite basis:** `WebHookEventController.java:87-106` — `giteeWebHookEvent` 无任何 `MachineInterfaceAuthUtil` 调用，直接组装 `WebHookRequestDTO` 投递业务处理；组件暴露表将该控制器标记为 External / 无前置条件（T1）。`CrossRegionController.java:58-66` — `handleGiteeHooks` 无验签直接调用 `crossRegionService`。

#### Remediation

1. 为所有 Gitee webhook 入口统一启用服务内验签（`giteeWebhookMachineInterfacePermissionAuth`）。
2. 下线或收敛遗留 `/webhookEvent/hooks/**` 与 `/cross-region/hooks/**` 入口，统一指向 `/apig/webhook/**` 验签入口。
3. 为事件处理增加幂等键（`X-Gitee-Event` + 事件 ID）与频率限制，防止重放放大。

#### Verification

- 构造无 `X-Gitee-Token`/`X-Gitee-Timestamp` 头的 Gitee 事件请求，确认被 401 拒绝。
- 使用错误签名请求 `/apig/webhook/gitee/**`，确认返回"校验失败"。
- 回归：合法 Gitee webhook 事件仍能正常触发流水线。

---

### FIND-02: CrossRegion 对外接口缺少鉴权，可篡改门禁状态并泄露流水线信息

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Important |
| CVSS 4.0 | 8.6 (CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:H/VA:L/SC:N/SI:N/SA:N) |
| CWE | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | None |
| Exploitability Tier | Tier 1 — Direct exposure, no prerequisites |
| Remediation Effort | Medium |
| Mitigation Type | Redesign |
| Component | CrossRegionController |
| Related Threats | [T14.S](2-stride-analysis.md#crossregioncontroller), [T14.T](2-stride-analysis.md#crossregioncontroller), [T14.I](2-stride-analysis.md#crossregioncontroller), [T14.A](2-stride-analysis.md#crossregioncontroller) |

#### Description

`CrossRegionController` 的多个对外端点无服务内鉴权：`updatePipelineStatus`（`PUT /cross-region/pipeline-status`）可篡改流水线/PR 门禁结果；`getPipelineInfo`（`POST /cross-region/pipelineInfo`）可根据 org/repo/pr 返回他人流水线状态；`compileTrigger`、`getPrDetailProjectId`、`updatePrLinkUrl` 均可被任意调用。攻击者无需任何凭据即可完成状态操纵与信息收集，直接影响发布门禁的可信度。

#### Evidence

**Prerequisite basis:** `CrossRegionController.java:215-219` — `updatePipelineStatus(@RequestBody String requestBody)` 无鉴权注解、无验签；`:227-231` — `getPipelineInfo` 注释"鉴权由 API 网关统一处理"但服务内无校验；`:203-206` — `compileTrigger` 无鉴权。组件暴露表将该控制器标记为 External / T1。

#### Remediation

1. 对状态回写类接口（`updatePipelineStatus`）增加服务内签名/HMAC 验签与调用方白名单。
2. 对查询类接口（`getPipelineInfo`）增加认证与基于组织的访问控制。
3. 对 `compileTrigger`、`updatePrLinkUrl` 等增加鉴权与频率限制。

#### Verification

- 无凭据直接调用 `PUT /cross-region/pipeline-status`，确认被拒绝。
- 无凭据调用 `POST /cross-region/pipelineInfo`，确认被拒绝或要求认证。
- 回归：黄区合法回调仍能正常更新状态。

---

### FIND-03: Gitee 验签不覆盖请求体且无时间窗，可重放/篡改事件

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Important |
| CVSS 4.0 | 8.2 (CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity |
| OWASP | A07:2025 – Identification and Authentication Failures |
| Exploitation Prerequisites | None |
| Exploitability Tier | Tier 1 — Direct exposure, no prerequisites |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | MachineInterfaceAuthUtil |
| Related Threats | [T16.T](2-stride-analysis.md#machineinterfaceauthutil), [T12.T](2-stride-analysis.md#apigwebhookcontroller) |

#### Description

`MachineInterfaceAuthUtil.giteeWebhookMachineInterfacePermissionAuth` 的签名消息为 `timestamp + "\n" + secretKey`，**不包含请求体内容**，且**无 timestamp 时间窗校验**。持有有效签名（或能窃取/重放历史签名）的攻击者可篡改事件体或重放旧事件；`ApigWebhookController` 的 Gitee 入口亦复用该校验，篡改面扩展至所有 Gitee 事件。

#### Evidence

**Prerequisite basis:** `MachineInterfaceAuthUtil.java:97-120` — `message = timestamp + "\n" + secretKeyDecrypt`，仅对 timestamp 签名不覆盖 body；`getBase64HmacSHA256(secretKeyDecrypt, message)` 与 `verifySign.equals(sign)` 无时间窗检查。组件暴露表将该工具类标记为 External / T1。

#### Remediation

1. 将完整请求体纳入签名计算。
2. 增加 timestamp 时间窗校验（如 ±5 分钟）与一次性 nonce 防重放。
3. 使用恒定时间比较（`MessageDigest.isEqual`，见 FIND-14）。

#### Verification

- 用旧请求的合法签名 + 修改后的请求体重放，确认验签失败。
- 使用过期 timestamp 的合法签名，确认被拒绝。
- 回归：正常 Gitee 事件验签通过。

---

### FIND-04: 匿名访问判定在流水线无资源配置时默认放行

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 7.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | None |
| Exploitability Tier | Tier 1 — Direct exposure, no prerequisites |
| Remediation Effort | Low |
| Mitigation Type | Standard Mitigation |
| Component | AuthInterceptor |
| Related Threats | [T11.T](2-stride-analysis.md#authinterceptor) |

#### Description

`AuthInterceptor.checkAnonymousAccess` 在 `pipelineDetailVO.getSources()` 为空时直接放行并缓存为"允许访问"。任何未配置代码仓资源的流水线均可被匿名访问其业务接口，绕过权限校验，形成隐藏的公开面。该行为与设计意图（仅公开仓匿名放行）相悖，属于 fail-open 默认值。

#### Evidence

**Prerequisite basis:** `AuthInterceptor.java:374-379` — `if (CollectionUtils.isEmpty(sources)) { ... cacheToLocal(..., AccessCacheResult.success()); return; }`，空 sources 即匿名放行。组件暴露表将 AuthInterceptor 标记为 External，但该匿名分支使空资源配置流水线达到无前置条件（T1）暴露。

#### Remediation

- 空 sources 视为"配置不完整"，返回未配置状态而非匿名放行。
- 匿名访问仅对显式标记为 `public` 的仓库放行。

#### Verification

- 为一条无 sources 的流水线发起匿名请求，确认被拒绝而非放行。
- 公开仓匿名访问回归通过。

---

## Tier 2 — Conditional Risk (Authenticated / Single Prerequisite)

### FIND-05: JWT 仅解码不验签且 userId 客户端可控，可冒用身份越权

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Important |
| CVSS 4.0 | 8.1 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-287](https://cwe.mitre.org/data/definitions/287.html): Improper Authentication |
| OWASP | A07:2025 – Identification and Authentication Failures |
| Exploitation Prerequisites | Authenticated User |
| Exploitability Tier | Tier 2 — Conditional risk, requires one prerequisite |
| Remediation Effort | High |
| Mitigation Type | Redesign |
| Component | AuthInterceptor / PipelineControllerV2 |
| Related Threats | [T11.S](2-stride-analysis.md#authinterceptor), [T10.S](2-stride-analysis.md#pipelinecontrollerv2), [T10.E](2-stride-analysis.md#pipelinecontrollerv2) |

#### Description

`JwtUtils.getClaimByName` 使用 `JWT.decode(token)` **仅解码不验签**（无 HMAC/RSA 校验、无过期校验），Cookie token 中的 userId 与三方 access token claim 未经签名验证即被信任；同时 `AuthInterceptor.extractPermissionContext` 直接从客户端请求参数/请求体提取 `userId`/`projectId`（非服务端会话）。两个问题叠加后，任意能触达业务接口的调用者均可通过伪造 JWT 或指定他人 userId 冒用身份，实现水平/垂直越权（启动他人流水线、导出日志、操作白名单）。

#### Evidence

**Prerequisite basis:** `JwtUtils.java:30-32` — `JWT.decode(token).getClaim(name)` 无 `JWTVerifier`/`withIssuer`/`withExpiresAt`；`AuthInterceptor.java:281-306` — `extractPermissionContext` 从 `request.getParameter`/请求体 JSON 提取 `userId`/`projectId`。组件暴露表将 AuthInterceptor / PipelineControllerV2 标记为需认证（T2），故该漏洞的实际利用需先获得任一平台登录身份。

#### Remediation

1. 由网关/平台在可信边界注入身份（如可信请求头），服务端禁止信任客户端传入的 userId。
2. 若保留 JWT，须验证签名、issuer、exp 并绑定服务端会话。
3. 权限校验强绑定资源归属（projectId/pipelineId 与用户关系），而非仅校验参数。

#### Verification

- 以用户 A 登录，构造 userId=B 的请求访问 B 的流水线接口，确认被拒绝。
- 使用伪造签名/过期 JWT 请求，确认被拒绝。
- 回归：正常登录用户操作通过。

---

### FIND-06: 华为云客户端部分链路关闭 SSL 证书校验

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Important |
| CVSS 4.0 | 7.3 (CVSS:4.0/AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-295](https://cwe.mitre.org/data/definitions/295.html): Improper Certificate Validation |
| OWASP | A02:2025 – Cryptographic Failures |
| Exploitation Prerequisites | Internal Network |
| Exploitability Tier | Tier 2 — Conditional risk, requires one prerequisite |
| Remediation Effort | Medium |
| Mitigation Type | Standard Mitigation |
| Component | HwCloudClient |
| Related Threats | [T24.T](2-stride-analysis.md#hwcloudclient), [T24.A](2-stride-analysis.md#hwcloudclient) |

#### Description

`HwCloudClient.getDataResultFromHWCloudHttpApi` 调用 `buildPipelineSslHttpsClient(false)` 创建**关闭证书校验**的 HTTPS 客户端（`false` 即不校验），用于携带 AK/SK 签名的华为云 API 请求。中间人可对请求/响应进行截获、篡改甚至重放，破坏华为云链路的数据机密性与完整性。另有部分调用使用无超时客户端（`buildPipelineSslHttpsClient`），远端无响应时会造成线程阻塞放大。

#### Evidence

**Prerequisite basis:** `HwCloudClient.java:116-122` — `buildPipelineSslHttpsClient(boolean verify)` 当 `verify=false` 时调用 `SSLCipherSuiteUtil.createHttpClient(...)`（不校验证书）；`:180` — `getDataResultFromHWCloudHttpApi` 以 `false` 构造客户端执行 AK/SK 签名请求。

#### Remediation

- 生产链路一律使用 `verify=true` 的客户端，明确受信 CA 与主机名校验。
- 统一使用带超时的客户端（`buildPipelineSslHttpsClientWithTimeout`），防止线程阻塞。
- 若历史兼容原因必须关闭校验，限制在测试环境并显式告警。

#### Verification

- 使用自签证书的模拟华为云端点调用，确认校验开启后被拒绝、关闭后被放行（验证配置生效）。
- 回归：真实华为云调用正常。

---

### FIND-07: 内部机机接口无服务内鉴权，内部网络者可触发任意流水线

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Important |
| CVSS 4.0 | 6.3 (CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | Internal Network |
| Exploitability Tier | Tier 2 — Conditional risk, requires one prerequisite |
| Remediation Effort | Medium |
| Mitigation Type | Redesign |
| Component | InternalPipelineController |
| Related Threats | [T15.S](2-stride-analysis.md#internalpipelinecontroller), [T15.E](2-stride-analysis.md#internalpipelinecontroller), [T01.E](2-stride-analysis.md#apigateway) |

#### Description

`InternalPipelineController.prStartPipeline`（`POST /internal/prStartPipeline`）直接调用 `PipelineStartEventHandler.startPipeline(vo)`，无服务内鉴权。任何能访问内部网络或经由网关路由到达该路径的调用者，均可伪装内部服务触发任意流水线启动，且绕过 `AuthInterceptor` 的业务权限校验。若 APIG 网关对该路径的路由配置过宽（见 T01.E），攻击面将从内部扩展到外部。

#### Evidence

**Prerequisite basis:** `InternalPipelineController.java:33-36` — `prStartPipeline(@RequestBody PrStartPipelineVo vo)` 无鉴权注解、无验签，直接 `pipelineStartEventHandler.startPipeline(vo)`。组件暴露表将其标记为 Internal Only / T2，故利用需内部网络访问。

#### Remediation

- 为内部接口增加服务间鉴权（mTLS、共享 token 或签名）。
- 在网关侧收紧 `/internal/**` 路由，禁止外部可达。
- 增加来源校验与调用审计。

#### Verification

- 从内部网络直接调用 `/internal/prStartPipeline`，确认未鉴权被拒绝。
- 确认 `/internal/**` 在网关路由中不可外部访问。

---

### FIND-08: RabbitMQ/Redis 非 prod 环境明文传输敏感数据

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 6.9 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-319](https://cwe.mitre.org/data/definitions/319.html): Cleartext Transmission of Sensitive Information |
| OWASP | A02:2025 – Cryptographic Failures |
| Exploitation Prerequisites | Internal Network |
| Exploitability Tier | Tier 2 — Conditional risk, requires one prerequisite |
| Remediation Effort | Medium |
| Mitigation Type | Standard Mitigation |
| Component | RabbitMQ / Redis |
| Related Threats | [T07.I](2-stride-analysis.md#rabbitmq), [T09.I](2-stride-analysis.md#redis), [T07.T](2-stride-analysis.md#rabbitmq), [T17.T](2-stride-analysis.md#webhookeventconsumer), [T19.T](2-stride-analysis.md#pipelinestatusupdateconsumer), [T20.T](2-stride-analysis.md#propeventconsumer) |

#### Description

生产环境（prod）RabbitMQ 与 Redis 启用了 TLS/SSL（`rediss://`），但非 prod 环境为明文 TCP。消息与缓存中包含加密的 accessToken、事件数据、权限判定结果等敏感信息；内部网络窃听者可在链路上读取/注入数据，且消息完整性未受保护（配合 FIND-01/05 可扩大事件伪造面）。

#### Evidence

**Prerequisite basis:** `application-prod.yaml` 配置 MQ/Redis 生产队列与命名空间；Redis 配置文档（Security Infrastructure Inventory）注明"prod 用 `rediss://` TLS，非 prod 明文"；Rabbit 配置注明"仅 prod 启用 SSL"。组件暴露表将 RabbitMQ/Redis 标记为 Internal Only / T2。

#### Remediation

- 非 prod 环境统一启用 TLS（RabbitMQ `ssl.enabled`、Redis `rediss://`）。
- 通过集群网络策略限制 MQ/Redis 仅白名单服务可达。
- 消息与缓存数据敏感字段加密 + 完整性校验。

#### Verification

- 非 prod 环境抓包确认 MQ/Redis 链路为 TLS 密文。
- 回归：所有消费者/缓存读写正常。

---

### FIND-09: XXL-Job 任务参数作为可信输入，可被恶意调度滥用

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 6.9 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-284](https://cwe.mitre.org/data/definitions/284.html): Improper Access Control |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | Privileged User |
| Exploitability Tier | Tier 2 — Conditional risk, requires one prerequisite |
| Remediation Effort | Medium |
| Mitigation Type | Standard Mitigation |
| Component | XxlJobHandler |
| Related Threats | [T22.T](2-stride-analysis.md#xxljobhandler), [T22.A](2-stride-analysis.md#xxljobhandler), [T06.T](2-stride-analysis.md#xxljobadmin), [T06.A](2-stride-analysis.md#xxljobadmin) |

#### Description

`XxlJobHandler` 的 14 个定时任务直接使用 `XxlJobContext.getXxlJobContext().getJobParam()` 作为可信输入：如 `refreshWebhookHandler` 可携带 `customOrgs` 自定义 token 批量改写 GitCode/Gitee 代码仓 Webhook 回调 URL，`bisectTaskHandler` 等以 jobParam 作为查询条件。拥有 XXL-Job 管理权限者可构造恶意参数造成批量误操作（改回调 URL、批量投递、接受邀请），且存在明文 token 经任务参数传递的泄露风险。

#### Evidence

**Prerequisite basis:** `XxlJobHandler.java:138-147` — `String jobParam = XxlJobContext.getXxlJobContext().getJobParam(); ... wrapper.eq(..., jobParam)` 直接作为 SQL 条件；webhook 刷新任务以 jobParam 携带自定义 token。组件暴露表将 XxlJobHandler 标记为 Internal Only / T2（触发需 XXL-Job accessToken）。

#### Remediation

- 对 jobParam 做白名单/格式校验，禁止敏感参数（token）明文传递。
- 敏感凭据改为加密存储或引用 ID，任务仅传引用。
- 关键任务（webhook 刷新）增加二次确认/回滚开关与审计。

#### Verification

- 构造含非法/超长 jobParam 触发任务，确认被拒绝或无害化。
- 确认任务日志中不出现明文 token。

---

### FIND-10: OBS 导出签名 URL 的 objectKey 归属校验缺失（待验证）

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-639](https://cwe.mitre.org/data/definitions/639.html): Authorization Bypass Through User-Controlled Key |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | Authenticated User |
| Exploitability Tier | Tier 2 — Conditional risk, requires one prerequisite |
| Remediation Effort | Medium |
| Mitigation Type | Standard Mitigation |
| Component | ObsBucketServiceImpl |
| Related Threats | [T25.I](2-stride-analysis.md#obsbucketserviceimpl), [T10.I](2-stride-analysis.md#pipelinecontrollerv2) |

#### Description

`PipelineControllerV2.exportBuildLog` 依据用户传入的 projectId/taskName/jobId/buildNo 触发日志导出，`ObsBucketServiceImpl.getSignedUrl` 为指定 objectKey 生成 OBS 临时 GET 签名 URL。若 objectKey 由用户可控参数拼接且未与流水线/用户归属做绑定校验，认证用户可构造他人 jobId/buildNo 获取其构建日志的下载 URL，造成跨流水线对象越权访问。该问题与 FIND-05 的 userId 冒用叠加时危害进一步放大。

#### Evidence

**Prerequisite basis:** `PipelineControllerV2.java` `exportBuildLog` 接收 `jobId`/`buildNo` 等用户输入（仅校验非空）；`ObsBucketServiceImpl.java:192-206` — `getSignedUrl(objectKey, ...)` 对任意 objectKey 生成签名 URL，未体现对象归属校验；`getObsClient()` 以解密 AK/SK 创建（`:208-215`）。需要进一步确认 objectKey 拼接是否绑定 pipeline 归属（见 0-assessment.md Needs Verification）。

#### Remediation

- 导出前校验 objectKey 前缀与 job/pipeline 归属关系，禁止跨流水线拼接。
- 对签名 URL 设置短有效期，并限定可下载对象。
- 参数（jobId/buildNo）与 DB 中实际流水线运行记录强绑定。

#### Verification

- 以用户 A 身份用用户 B 的 jobId/buildNo 发起导出，确认被拒绝。
- 回归：本人流水线日志导出正常。

---

### FIND-11: Redis 公开仓缓存 key 无分隔符拼接存在碰撞，可致匿名越权

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 5.6 (CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-639](https://cwe.mitre.org/data/definitions/639.html): Authorization Bypass Through User-Controlled Key |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | Authenticated User |
| Exploitability Tier | Tier 2 — Conditional risk, requires one prerequisite |
| Remediation Effort | Low |
| Mitigation Type | Standard Mitigation |
| Component | AuthInterceptor |
| Related Threats | [T11.T2](2-stride-analysis.md#authinterceptor), [T09.T](2-stride-analysis.md#redis) |

#### Description

`AuthInterceptor.isGitUrlPublic` 使用 `openlibingRedis.hasKey(projectId + pipelineId)` 与 `openlibingRedis.set(projectId + pipelineId, ...)`，key 由 `projectId` 与 `pipelineId` **无分隔符直接拼接**。当存在 `(projectId=1, pipelineId=23)` 与 `(projectId=12, pipelineId=3)` 这类碰撞对时，二者共享同一缓存值；若其中一个为公开仓，另一个私有流水线会被误判为公开，从而通过匿名访问绕过权限校验。

#### Evidence

**Prerequisite basis:** `AuthInterceptor.java:456-480` — `openlibingRedis.hasKey(projectId + pipelineId)` / `openlibingRedis.set(projectId + pipelineId, ...)` 无分隔符拼接；缓存值 `"true"/"false"` 决定 `isGitUrlPublic` 分支是否执行权限查询（`:165-169`）。

#### Remediation

- key 使用分隔符或哈希（如 `access:{projectId}:{pipelineId}` 或对拼接值做摘要）。
- 为缓存值增加归属校验（如同时缓存 projectId 供回读比对）。

#### Verification

- 构造碰撞对（如 1+23 与 12+3），验证缓存隔离。
- 回归：公开仓判定不受影响。

---

## Tier 3 — Defense-in-Depth (Prior Compromise / Host Access)

### FIND-12: Nacos 集中托管全部凭据与解密密钥，单点失陷风险高

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 7.1 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N) |
| CWE | [CWE-522](https://cwe.mitre.org/data/definitions/522.html): Insufficiently Protected Credentials |
| OWASP | A07:2025 – Identification and Authentication Failures |
| Exploitation Prerequisites | Nacos Compromise |
| Exploitability Tier | Tier 3 — Defense-in-depth, requires prior compromise |
| Remediation Effort | High |
| Mitigation Type | Redesign |
| Component | Nacos |
| Related Threats | [T05.I](2-stride-analysis.md#nacos), [T05.T](2-stride-analysis.md#nacos), [T08.I](2-stride-analysis.md#mysql), [T19.I](2-stride-analysis.md#pipelinestatusupdateconsumer), [T04.I](2-stride-analysis.md#huaweicloud), [T23.I](2-stride-analysis.md#pipelinestatusthirdpartyapiclient), [T24.I](2-stride-analysis.md#hwcloudclient) |

#### Description

Nacos 集中托管数据库/Redis/RabbitMQ/OBS/华为云 AK/SK 等敏感配置，且本服务的 AES 解密密钥 `security.part1` 亦由 Nacos 下发（`SecurityUtil.decrypt(value, part1)`）。配置中心一旦失陷，攻击者不仅可读取全部凭据，还能利用 `part1` 解密 DB 中的加密 accessToken 与 webhook secret（配合 FIND-05/06 完成全链路凭据接管）。密钥与数据共置形成单点失效。

#### Evidence

**Prerequisite basis:** `application-prod.yaml:2-19` — 从 Nacos 导入 `application/framework/cicd/xxl-job` 配置；`SecurityUtil`/`DataSourceConfig` 以 `@Value("${security.part1}")` + Jasypt 统一解密凭据；`ObsBucketServiceImpl.java:53-54`、`HwCloudClient.java:49-50`、`MachineInterfaceAuthUtil.java:44-45` 均依赖 `security.part1`。组件暴露表将 Nacos 标记为 Internal Only / T2，实际利用需先攻破 Nacos（T3）。

#### Remediation

- 引入独立密钥管理服务（KMS/HSM），`part1` 改为托管密钥引用，密钥与配置分离。
- Nacos 开启访问控制、网络隔离与配置变更审计。
- 密钥/凭据定期轮换，降低单点失陷影响半径。

#### Verification

- 确认 `security.part1` 不再以明文配置存储于 Nacos。
- 模拟 Nacos 失陷场景验证无法仅凭配置解密 DB 凭据。

---

### FIND-13: 机机接口审计日志不完整，无法追溯恶意调用

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 3.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-778](https://cwe.mitre.org/data/definitions/778.html): Insufficient Logging |
| OWASP | A09:2025 – Security Logging and Monitoring Failures |
| Exploitation Prerequisites | None |
| Exploitability Tier | Tier 3 — Defense-in-depth (audit deficiency, not directly exploitable) |
| Remediation Effort | Low |
| Mitigation Type | Standard Mitigation |
| Component | MachineInterfaceAuthUtil |
| Related Threats | [T16.R](2-stride-analysis.md#machineinterfaceauthutil), [T02.R](2-stride-analysis.md#gitcode) |

#### Description

`MachineInterfaceAuthUtil.machineInterfaceLog` 写入机机调用审计时，`requestStatus` 固定为 `"unknown"`（拿不到调用结果），且不记录验签是否通过、签名摘要与响应状态。当 webhook 被伪造/重放（FIND-01/03）时，审计日志无法区分合法与恶意调用，无法支持事后溯源与问责，削弱了 Repudiation（不可抵赖）防线。

#### Evidence

**Prerequisite basis:** `MachineInterfaceAuthUtil.java:156-184` — `logEntity.setRequestStatus("unknown"); // 拿不到调用结果`；仅记录 `requestIp`/URL/账号，不记录验签结果与处理结果。

#### Remediation

- 审计日志记录验签结果（成功/失败/缺失）、签名摘要、timestamp 与处理结果。
- 对验签失败事件单独告警并保留原始请求（脱敏后）。
- 审计日志接入集中日志平台，设置保留期与告警规则。

#### Verification

- 触发一次验签失败请求，确认审计日志中可见失败标记与告警。
- 回归：合法 webhook 审计记录完整。

---

### FIND-14: 签名比对使用非常量时间字符串比较

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 3.1 (CVSS:4.0/AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N) |
| CWE | [CWE-208](https://cwe.mitre.org/data/definitions/208.html): Observable Timing Discrepancy |
| OWASP | A07:2025 – Identification and Authentication Failures |
| Exploitation Prerequisites | Network Access |
| Exploitability Tier | Tier 3 — Defense-in-depth (requires precise timing + on-path) |
| Remediation Effort | Low |
| Mitigation Type | Standard Mitigation |
| Component | MachineInterfaceAuthUtil |
| Related Threats | [T16.S](2-stride-analysis.md#machineinterfaceauthutil) |

#### Description

`MachineInterfaceAuthUtil.validateSignature` 使用 `hexString.toString().equals(signature)` 进行签名比对，`String.equals` 非恒定时间比较，理论上存在基于响应时间的签名逐字节爆破侧信道。在 HTTPS 链路上实际利用难度极高，属于防御纵深问题；但作为机机验签核心，应使用恒定时间比较消除该理论面。

#### Evidence

**Prerequisite basis:** `MachineInterfaceAuthUtil.java:130-154` — `return hexString.toString().equals(signature);` 非常量时间比较；Gitee 路径 `verifySign.equals(sign)`（`:114`）同理。

#### Remediation

- 使用 `MessageDigest.isEqual(byte[], byte[])` 做恒定时间比较。
- 统一签名比较工具，覆盖 GitCode 与 Gitee 两条路径。

#### Verification

- 对极短/极长签名分别调用，确认响应时间差异不可观测（无回归风险）。

---

## Threat Coverage Verification

| Threat ID | Finding ID | Status |
|-----------|------------|--------|
| T01.S | — | 🔄 Mitigated by Platform |
| T01.D | — | 🔄 Mitigated by Platform |
| T01.E | FIND-07 | ✅ Covered (FIND-07) |
| T02.R | FIND-13 | ✅ Covered (FIND-13) |
| T02.T | — | 🔄 Mitigated by Platform |
| T03.S | FIND-03 | ✅ Covered (FIND-03) |
| T03.T | FIND-01 | ✅ Covered (FIND-01) |
| T04.I | FIND-12 | ✅ Covered (FIND-12) |
| T04.T | FIND-12 | ✅ Covered (FIND-12) |
| T05.D | FIND-12 | ✅ Mitigated (FIND-12) |
| T05.I | FIND-12 | ✅ Covered (FIND-12) |
| T05.T | FIND-12 | ✅ Covered (FIND-12) |
| T06.T | FIND-09 | ✅ Covered (FIND-09) |
| T06.A | FIND-09 | ✅ Covered (FIND-09) |
| T07.T | FIND-08 | ✅ Covered (FIND-08) |
| T07.I | FIND-08 | ✅ Covered (FIND-08) |
| T07.D | FIND-08 | ✅ Mitigated (FIND-08) |
| T08.I | FIND-12 | ✅ Covered (FIND-12) |
| T08.T | FIND-12 | ✅ Covered (FIND-12) |
| T09.I | FIND-08 | ✅ Covered (FIND-08) |
| T09.T | FIND-11 | ✅ Covered (FIND-11) |
| T10.S | FIND-05 | ✅ Covered (FIND-05) |
| T10.E | FIND-05 | ✅ Covered (FIND-05) |
| T10.I | FIND-10 | ✅ Covered (FIND-10) |
| T11.T | FIND-04 | ✅ Covered (FIND-04) |
| T11.S | FIND-05 | ✅ Covered (FIND-05) |
| T11.T2 | FIND-11 | ✅ Covered (FIND-11) |
| T11.I | FIND-05 | ✅ Mitigated (FIND-05) |
| T11.D | FIND-05 | ✅ Mitigated (FIND-05) |
| T12.T | FIND-03 | ✅ Covered (FIND-03) |
| T12.D | FIND-01 | ✅ Covered (FIND-01) |
| T13.S | FIND-01 | ✅ Covered (FIND-01) |
| T13.T | FIND-01 | ✅ Covered (FIND-01) |
| T13.A | FIND-01 | ✅ Covered (FIND-01) |
| T14.S | FIND-02 | ✅ Covered (FIND-02) |
| T14.T | FIND-02 | ✅ Covered (FIND-02) |
| T14.I | FIND-02 | ✅ Covered (FIND-02) |
| T14.A | FIND-02 | ✅ Covered (FIND-02) |
| T15.S | FIND-07 | ✅ Covered (FIND-07) |
| T15.E | FIND-07 | ✅ Covered (FIND-07) |
| T16.T | FIND-03 | ✅ Covered (FIND-03) |
| T16.R | FIND-13 | ✅ Covered (FIND-13) |
| T16.S | FIND-14 | ✅ Covered (FIND-14) |
| T17.T | FIND-08 | ✅ Covered (FIND-08) |
| T17.D | FIND-08 | ✅ Mitigated (FIND-08) |
| T17.I | FIND-13 | ✅ Mitigated (FIND-13) |
| T18.T | FIND-08 | ✅ Covered (FIND-08) |
| T18.A | FIND-08 | ✅ Covered (FIND-08) |
| T19.T | FIND-08 | ✅ Covered (FIND-08) |
| T19.A | FIND-08 | ✅ Covered (FIND-08) |
| T19.I | FIND-12 | ✅ Covered (FIND-12) |
| T20.T | FIND-08 | ✅ Covered (FIND-08) |
| T20.A | FIND-08 | ✅ Covered (FIND-08) |
| T21.I | FIND-08 | ✅ Covered (FIND-08) |
| T21.A | FIND-08 | ✅ Covered (FIND-08) |
| T22.T | FIND-09 | ✅ Covered (FIND-09) |
| T22.A | FIND-09 | ✅ Covered (FIND-09) |
| T23.I | FIND-12 | ✅ Covered (FIND-12) |
| T23.T | FIND-12 | ✅ Covered (FIND-12) |
| T24.T | FIND-06 | ✅ Covered (FIND-06) |
| T24.I | FIND-12 | ✅ Covered (FIND-12) |
| T24.A | FIND-06 | ✅ Covered (FIND-06) |
| T25.I | FIND-10 | ✅ Covered (FIND-10) |
| T25.T | FIND-10 | ✅ Covered (FIND-10) |
