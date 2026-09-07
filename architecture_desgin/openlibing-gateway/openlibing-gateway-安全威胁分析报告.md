# 安全威胁分析报告：openlibing-gateway

| 项 | 内容 |
|---|---|
| 仓库路径 | `D:\skill\skill收集\repo\openlibing-gateway` |
| 分析日期 | 2026-09-02 |
| 分析方法 | 静态代码审计（STRIDE-A 威胁建模 + 配置/依赖检查） |
| 报告语言 | 中文 |
| 部署分类 | 容器化微服务（K8s 集群内，端口 8073，响应式 WebFlux；平台**统一接入与安全网关**，依赖 Apollo/Nacos 拉取配置，直连 PostgreSQL/Redis/MongoDB/RabbitMQ） |

---

## 一、系统概述

### 1.1 用途与技术栈

OpenLiBing 平台的**统一接入网关**：多平台（Gitee/GitCode/GitHub/Uniportal/OpenUBMC）OAuth 登录与账号绑定、JWT 颁发与校验、RBAC 菜单权限、CSRF 防护、机机接口 HMAC 签名、Webhook 验签、Redis 漏桶限流、华为第三方 API 签名转发、隐私声明校验、中间件健康检查、PV/UV 上报。它是所有外部请求进入业务后端（openlibing-framework 等）的唯一入口。

- Java 21、Spring Boot 3.4.4（`web-application-type: reactive`）、Spring Cloud Gateway Server WebFlux 4.3.3、MyBatis + Liquibase（PostgreSQL 42.7.13）、Redis（Lettuce，**SSL**）、MongoDB、RabbitMQ、Apollo + Jasypt、auth0 JWT（HMAC256）、OkHttp 4.11.0、fastjson2（safeMode）+ Gson、spring-security-crypto、bouncycastle
- 容器：openeuler 24.03 + RASP，非 root
- 入口：`GatewayApplication.java`（`@EnableApolloConfig`、`@EnableEncryptableProperties`、MyBatis `@MapperScan`）

### 1.2 组件与信任边界

| 组件 ID | 锚点 | 职责 | 信任边界 |
|---|---|---|---|
| WebhookAuthFilter | `business/filter/WebhookAuthFilter.java:46` | Webhook 限流 + 验签（order=0），GitCode/GitHub 直接交 handler | 外部 → 网关 |
| AuthFilter | `business/filter/AuthFilter.java:58` | 核心认证鉴权（JWT、CSRF、会话、黑名单、豁免、RBAC），order=2 | 认证边界 |
| PrivacyProfileFilter | `business/filter/PrivacyProfileFilter.java` | 隐私声明签署校验/重签 token | 认证边界 |
| PermissionCheckFilter | `business/filter/PermissionCheckFilter.java` | `/openlibing-cicd/` 项目级横向权限 | 授权边界 |
| ApiGatewayFilter | `business/filter/ApiGatewayFilter.java:36` | 华为第三方 API 加签转发（X-HW-*） | 网关 → 外部 API |
| 限流 | `business/filter/ratelimit/RedisLeakyBucketRateLimiter.java` | Redis 漏桶限流 | 边界控制 |
| LoginController/Impl | `business/controller/LoginController.java:58`、`business/service/impl/LoginServiceImpl.java:81` | OAuth 发起/回调、绑定、JWT 颁发、登出 | 外部 ↔ 三方 OAuth 平台 |
| JwtHelper | `common/utils/JwtHelper.java` | HMAC256 签发/验签、Cookie 生成 | 认证边界 |
| SecurityHelper | `common/utils/SecurityHelper.java:21` | AES 加解密（密钥分片 `security.part1`） | 密钥边界 |
| UserAuthHelper | `common/utils/UserAuthHelper.java` | RBAC 菜单 URL 鉴权 + 黑名单 | 授权边界 |
| MachineInterfaceAuthHelper | `common/utils/MachineInterfaceAuthHelper.java` | 机机接口 HMAC-SHA256 签名验签 | 服务 ↔ 服务 |
| RedisHelper | `common/utils/redis/RedisHelper.java` | 会话/state/CSRF/限流/黑名单存储（异常静默） | 服务 → 存储 |
| MiddlewareHealthController | `business/controller/MiddlewareHealthController.java:23` | 用解密后凭据直连各中间件探活 | 服务 → 存储 |
| EndUser / 三方平台 | — | 请求来源 / OAuth 身份提供方 | 外部主体 |

**关键信任边界**：① 终端用户/插件 → 网关过滤链（认证鉴权核心）；② 网关 → 5 个 OAuth 平台（授权码换 token、拉用户信息）；③ 网关 → 后端业务服务（身份以 query 参数注入转发，依赖网络隔离）；④ 网关 → 各中间件（健康检查直连）。

---

## 二、STRIDE-A 威胁分析汇总

| STRIDE 类别 | 威胁数 | 代表性威胁 |
|---|---|---|
| S 仿冒 | 2 | 机机/Webhook 签名依赖可伪造 IP 白名单；`use-insecure-trust-manager` 下后端可被中间人仿冒 |
| T 篡改 | 3 | 网关转发信任所有 TLS 证书（MITM 篡改）；MongoDB 禁用主机名校验；白名单 `contains` 子串匹配可被路径构造绕过 |
| R 抵赖 | 1 | 鉴权/限流基于可伪造的 XFF 与可降级的 Redis，审计归属可被误导 |
| I 信息泄露 | 3 | GitHub 回调 500 回显 `e.getMessage()`；access_token 放 URL query；中间件健康检查/Swagger 暴露面 |
| D 拒绝服务 | 2 | Redis 故障时限流/会话 fail-open 或异常；无统一请求体大小约束（网关层） |
| E 权限提升 | 3 | 豁免/转发/CSRF 白名单 `contains` 绕过认证；开放重定向挟持绑定回调；身份以 query 参数转发后端 |
| A 业务滥用 | 2 | 开放重定向钓鱼；白名单绕过后无鉴权调用敏感接口 |

### 关键威胁场景

**场景 1（T/E，TLS 校验全局关闭）**：网关配置 `spring.cloud.gateway.server.webflux.httpclient.ssl.use-insecure-trust-manager: true`（`application.yaml:29`），网关向后端/外部转发时**信任任意证书**。在内网东西向流量被劫持（ARP/DNS/代理被攻陷）时，攻击者可中间人窃听/篡改转发请求（含注入的 userId、token、业务数据），且无证书告警。

**场景 2（E，白名单子串匹配绕过认证）**：`AuthFilter` 的豁免路径、CSRF 信任列表、转发信任列表、公开接口、插件 token 路径全部使用 `path.contains(trustUrl)` 子串匹配（`AuthFilter.java:809,861,883,900,929,950`）。若白名单条目为较短片段（如 `/login`、`/public`），攻击者可构造 `/anything/<trust片段>/../sensitive` 或把可信片段作为路径段/参数，使本应鉴权的接口命中 `shouldExemptAuth` 直接放行（`AuthFilter.java:125-127`），从而**完全绕过认证与 CSRF 校验**。

**场景 3（E/A，开放重定向挟持授权回调）**：账号绑定发起接口 `/platform/account/bind/{platform}` 接受用户可控的 `redirect` 参数，仅做 `SPLIT_STR→&` 替换后原样写入 Redis（`LoginController.java:361-370` 等 5 处），回调成功后直接作为 `Location` 头 302（`LoginServiceImpl.java:624,709`），**无同源/白名单校验**。攻击者可构造 `redirect=https://evil.com` 诱导受害者完成三方授权后跳转到钓鱼站点，窃取授权码/令牌或进行钓鱼。

---

## 三、安全发现明细

### 高危

#### FIND-01：网关转发全局信任所有 TLS 证书（禁用证书校验）

| 属性 | 内容 |
|---|---|
| STRIDE | T（篡改）/ S（仿冒） |
| CWE | [CWE-295](https://cwe.mitre.org/data/definitions/295.html) 证书校验不当 |
| OWASP | A02:2025 – Cryptographic Failures；A05:2025 – Security Misconfiguration |
| 利用前提 | 处于网关到后端/外部的网络路径上（内网中间人、被攻陷代理/DNS） |
| 证据 | `src/main/resources/application.yaml:27-29` `httpclient.ssl.use-insecure-trust-manager: true`（全局生效于网关转发 HttpClient） |
| 风险 | 网关转发的所有请求（含注入的 userId/accountId、会话、业务数据、华为 API 加签请求）在 TLS 层不校验对端证书，可被中间人窃听/篡改而不告警。这是网关作为统一入口最严重的传输层缺陷。 |
| 修复建议 | 移除 `use-insecure-trust-manager: true`（默认即严格校验）；若后端为自签证书，通过受信 CA/信任库（仓内已有 `cacerts`）显式导入，而非全局关闭校验；区分"出站到外部三方"与"内网转发"分别配置。 |
| 修复成本 | 低（配置项）；中（需梳理自签后端证书） |

#### FIND-02：认证/CSRF/转发/豁免白名单普遍使用 `String.contains` 子串匹配，可被路径构造绕过

| 属性 | 内容 |
|---|---|
| STRIDE | E（权限提升）/ T（绕过控制） |
| CWE | [CWE-807](https://cwe.mitre.org/data/definitions/807.html) 安全决策依赖不可靠输入；[CWE-285](https://cwe.mitre.org/data/definitions/285.html) 授权不当；[CWE-184](https://cwe.mitre.org/data/definitions/184.html) 不完整白名单 |
| OWASP | A01:2025 – Broken Access Control |
| 利用前提 | 能向网关发送请求；白名单中存在较短/可作为子串出现的条目 |
| 证据 | `AuthFilter.java:900`（`shouldExemptAuth` 豁免认证）、`:809`（CSRF 信任列表 `checkCsrfAttack`）、`:950`（失效凭证白名单）、`:861`（`isForwardRequest` 转发白名单，命中后跳过 RBAC `:195-197`）、`:883`（插件 token 头路径）、`:929`（公开接口）均为 `path.contains(trustUrl)`；`WebhookAuthFilter.java:96,108` webhook 路径也用 `contains` |
| 风险 | 子串匹配不锚定路径边界。攻击者可构造包含可信片段的路径（如 `/x?next=<exempt片段>`、`/<exempt片段>/../<敏感接口>`、把片段放在路径段内）命中豁免/转发/CSRF 白名单，使敏感接口**跳过认证、跳过 CSRF、跳过 RBAC**。`isForwardRequest` 命中后直接 `chain.filter(exchange)` 且不注入/不校验用户，风险最高。 |
| 修复建议 | 白名单匹配改为**前缀匹配 + 路径边界**（`path.equals(x)` 或 `path.startsWith(x + "/")`），或使用 Spring `AntPathMatcher`/`PathPattern` 精确匹配；匹配前对路径做规范化（`normalize()` 去除 `../`）；白名单条目避免过短片段；对 `forward.trust.list` 命中的转发额外强制认证。 |
| 修复成本 | 低 |

### 中危

#### FIND-03：账号绑定回调存在开放重定向（`redirect` 参数无同源校验）

| 属性 | 内容 |
|---|---|
| STRIDE | E / A（钓鱼、授权流程挟持） |
| CWE | [CWE-601](https://cwe.mitre.org/data/definitions/601.html) 开放重定向 |
| OWASP | A01:2025 |
| 利用前提 | 诱导已登录受害者点击构造的绑定授权链接（含 `redirect=https://evil.com`） |
| 证据 | 发起：`LoginController.java:361-370`（uniportal）、`:471-478`（openubmc）、`:521-528`（gitee）、`:571-578`（gitcode）、`:620-626`（github）`redirect = request.getQueryParams().getFirst("redirect")` → `replace(SPLIT_STR,"&")` → `redisHelper.set(userId+":"+platform+":redirect", redirect, 30, MINUTES)`；回调：`LoginServiceImpl.java:624` 与 `:709` `response.getHeaders().add("location", prManageRedirectUrl)` 原样 302 |
| 风险 | `redirect` 用户完全可控、无协议/主机白名单/同源校验。受害者完成三方账号绑定授权后被 302 到攻击者站点，可用于钓鱼、窃取授权码/令牌（若三方回调带 code）、或借平台可信域名信誉实施跳转钓鱼。 |
| 修复建议 | 对 `redirect` 做白名单校验（仅允许 `domain.name` 同源或预置相对路径/可信主机列表）；拒绝绝对 URL 中的外域；仅允许 `https`；回调取用时再次校验。 |
| 修复成本 | 低 |

#### FIND-04：Redis 异常静默吞掉，鉴权/限流/黑名单存在 fail-open 降级面

| 属性 | 内容 |
|---|---|
| STRIDE | D / E / T |
| CWE | [CWE-755](https://cwe.mitre.org/data/definitions/755.html) 异常处理不当；[CWE-636](https://cwe.mitre.org/data/definitions/636.html) 安全决策依赖未失败即安全 |
| OWASP | A05:2025 – Security Misconfiguration |
| 证据 | `RedisHelper.hasKey` 在异常/返回 null 时 `return false`（`RedisHelper.java:65-73`，注意 `stringRedisTemplate.hasKey` 抛 `RedisConnectionFailureException` 时会向上传播，但大量 `set/hset/lSet` 等 catch 后 `return false`：`:119-121,143-145,168-170,...`）；会话校验 `AuthFilter.java:743` `if (!redisHelper.hasKey(userTokenKey))` 判失效；限流 `RedisLeakyBucketRateLimiter`、黑名单 `UserAuthHelper`、CSRF `AuthFilter.java:832` 均依赖 Redis |
| 风险 | Redis 故障/超时时，写类操作静默失败、读类判断可能返回"不存在"。不同分支语义不一致：会话 `hasKey=false` 会拒绝（fail-closed，偏安全但造成可用性问题），而限流计数/黑名单/权限缓存若异常被吞可能**降级放行或不限流**。整体安全姿态在依赖故障时行为不确定。 |
| 修复建议 | 统一安全关键路径的故障策略：认证/黑名单默认 **fail-closed**，限流可按业务明确选择并记录；不要吞掉 `RedisConnectionFailureException`，应向上传播或返回显式错误并打点告警；区分"key 不存在"与"Redis 不可用"。 |
| 修复成本 | 中 |

#### FIND-05：MongoDB 健康检查禁用 SSL 主机名校验

| 属性 | 内容 |
|---|---|
| STRIDE | T / S |
| CWE | [CWE-297](https://cwe.mitre.org/data/definitions/297.html) 主机名证书校验不当；[CWE-295](https://cwe.mitre.org/data/definitions/295.html) |
| OWASP | A02:2025 |
| 证据 | `business/service/impl/MiddlewareHealthServiceImpl.java:192-196` `applyToSslSettings(builder -> { builder.enabled(true); builder.invalidHostNameAllowed(true); })`（代码注释自述"不推荐用于生产环境"） |
| 风险 | 健康检查直连 MongoDB 时不校验证书主机名，连接串含解密后的生产凭据，中间人可仿冒 MongoDB 端点截获凭据/数据。虽为探活路径，但携带真实凭据。 |
| 修复建议 | 移除 `invalidHostNameAllowed(true)`；确保证书 CN/SAN 与连接主机匹配；探活使用低权限只读账号。 |
| 修复成本 | 低 |

#### FIND-06：Cookie 未设置 `SameSite`，CSRF 防护完全依赖自定义 token 机制

| 属性 | 内容 |
|---|---|
| STRIDE | E / T |
| CWE | [CWE-1275](https://cwe.mitre.org/data/definitions/1275.html) 敏感 Cookie 无 SameSite；[CWE-352](https://cwe.mitre.org/data/definitions/352.html) CSRF |
| OWASP | A01:2025；A07:2025 |
| 证据 | `JwtHelper.generateCookie`（`common/utils/JwtHelper.java:151-168`）仅设置 `httpOnly(true)`、`secure(true)`、`path("/")`、`domain(...)`，**未设置 `SameSite`**；CSRF 靠 `Csrf-Token-Open-Li-Bing` 头/Redis 双重校验（`AuthFilter.java:805-850`） |
| 风险 | 缺少浏览器层 SameSite 防线，一旦自定义 CSRF 校验逻辑出现疏漏（如 FIND-02 的 `csrf.trust.list` contains 绕过、Referer 校验 `referer.contains(domainName)` 子串匹配 `AuthFilter.java:816` 可被 `domainName.evil.com` 绕过），即形成 CSRF。 |
| 修复建议 | 为会话 Cookie 增加 `SameSite=Lax`（或 `Strict`）；Referer/Origin 校验改为**主机名精确匹配**（解析 URL 后比 host，而非 `contains`）；保留现有 token 校验作为纵深防御。 |
| 修复成本 | 低 |

#### FIND-07：GitHub 回调 500 响应回显异常消息 `e.getMessage()`

| 属性 | 内容 |
|---|---|
| STRIDE | I（信息泄露） |
| CWE | [CWE-209](https://cwe.mitre.org/data/definitions/209.html) 错误信息含敏感内容；[CWE-200](https://cwe.mitre.org/data/definitions/200.html) |
| OWASP | A05:2025 – Security Misconfiguration |
| 证据 | `LoginController.java:929-937` catch `RedisConnectionFailureException` 后 `response.writeWith(... ("Internal Server Error" + e.getMessage()) ...)`；对比其他平台回调仅回固定 `"Internal Server Error"`（`:776,862,1017,1096`） |
| 风险 | Redis 连接异常消息可能包含内网主机、端口、连接串片段等基础设施细节，回显给外部访问者有助于探测内网拓扑。 |
| 修复建议 | 响应体统一返回固定 `"Internal Server Error"`，异常细节仅写服务端日志；与其他 4 个回调保持一致。 |
| 修复成本 | 低 |

### 低危 / 信息

#### FIND-08：鉴权身份以 query 参数注入转发后端，依赖网络隔离

- STRIDE：E / T ｜ CWE：[CWE-306](https://cwe.mitre.org/data/definitions/306.html)（后端若独立可访问则关键功能缺认证）｜ OWASP：A01:2025
- 证据：`AuthFilter` 认证通过后把 `userId/userName/accountId/accountPlatform` 放入 query 参数转发（`getNewServerWebExchange`/`addParamIfNotNull`，`AuthFilter.java:700-705` 及注入逻辑）；后端服务据此识别用户。
- 风险：若后端业务服务（framework 等）可被绕过网关直接访问（K8s NetworkPolicy 缺失/容器网段可达），攻击者可直接在请求里伪造 `userId` 等参数冒充任意用户。
- 建议：网络层强制后端仅接受网关来源（NetworkPolicy/监听绑定）；后端对敏感操作二次校验；身份信息改用签名后的内部头（如 JWT 断言）而非裸 query 参数。
- 修复成本：中

#### FIND-09：access_token 经 URL query 调用三方接口

- STRIDE：I ｜ CWE：[CWE-598](https://cwe.mitre.org/data/definitions/598.html) 敏感信息进查询串 ｜ OWASP：A07:2025
- 证据：`common/utils/ThreePartyHelper.java:109,132` `giteeUserInfoUrl + "?access_token=" + accessToken`（OkHttp GET）；accessToken 源自解密后的 JWT claim。
- 风险：token 经 URL query 易被出站访问日志、代理日志、Referer 泄露。缓解：URL 基础段为配置常量、OkHttp 未发现 TrustAll，SSRF 面低。
- 建议：三方支持时改用 `Authorization: Bearer`/请求头；对出站 URL 保持主机白名单。
- 修复成本：低

#### FIND-10：`verifyToken.hashCode() == 401` 冗余/误导判断

- STRIDE：T（逻辑健壮性）｜ CWE：[CWE-1164](https://cwe.mitre.org/data/definitions/1164.html) 无关代码 ｜ OWASP：A05:2025
- 证据：`AuthFilter.java:717` `if (verifyToken == null || verifyToken.hashCode() == 401)`、`:843` `if (verifyToken != null && verifyToken.hashCode() != 401)`。`DecodedJWT.hashCode()` 不可能恒等于 401，该条件恒为 false/true，属无效判断。
- 风险：当前实际靠 null 判断，功能未失效；但误导维护者以为存在"401 语义"，后续修改易引入鉴权绕过。
- 建议：删除 `hashCode()==401` 判断，验签失败统一以 null/异常表达。
- 修复成本：低

#### FIND-11：`/login/gitee/account` 账密登录端点处理明文口令

- STRIDE：I / S ｜ CWE：[CWE-522](https://cwe.mitre.org/data/definitions/522.html) 凭据保护不足 ｜ OWASP：A07:2025
- 证据：`LoginController.java:1191-1199` `POST /login/gitee/account` 请求体含 gitee `username`/`password`。
- 风险：依赖 HTTPS 传输；需确保口令不落日志、不进 Redis/URL、服务端不缓存。与 OAuth 授权码模式并存，口令模式风险更高。
- 建议：优先废弃账密直通、改走 OAuth；若保留，确保全链路不记录口令、仅用于一次性换 token。
- 修复成本：中

#### FIND-12：中间件健康检查 / Swagger UI / 调试端点暴露面待收敛

- STRIDE：I / D ｜ CWE：[CWE-200](https://cwe.mitre.org/data/definitions/200.html) ｜ OWASP：A05:2025
- 证据：`MiddlewareHealthController.java:32` `GET /middleware/healthCheckByType?type=` 使用**解密后的生产凭据**直连 MySQL/Redis/PostgreSQL/MongoDB/RabbitMQ/Doris 探活；`springdoc-openapi-starter-webflux-ui 2.8.10`（pom）默认暴露 Swagger UI；`/health-check` 无认证。
- 风险：若这些路径在 `exempt.paths` 白名单或被外网可达，健康检查会泄露中间件拓扑/连接状态/版本，Swagger 暴露全部接口结构。
- 建议：生产环境禁用/收敛 springdoc（`springdoc.swagger-ui.enabled=false` 或仅内网）；健康检查端点加入内网/运维网段访问控制并确认不在免认证外网暴露面；actuator `management.endpoints.web.exposure` 收敛为 `health`。
- 修复成本：低

#### FIND-13：反射改写 `sslInfo` 脆弱、XFF 取最后一跳

- STRIDE：T / R ｜ CWE：[CWE-470](https://cwe.mitre.org/data/definitions/470.html) 反射依赖实现细节；[CWE-348](https://cwe.mitre.org/data/definitions/348.html) 信任不可靠来源 ｜ OWASP：A05:2025 / A01:2025
- 证据：`AuthFilter.setSslInfo`（约 `:536-551`）用反射写 `ServerHttpRequest.Builder` 内部 `delegate.sslInfo`，随 Spring 版本升级可能失效；`HttpRequestUtil.getUserIpAddress` 取 `X-Forwarded-For` **最后一个** IP（`HttpRequestUtil.java:217-221`），机机接口 IP 白名单/限流依赖该值。
- 风险：反射在框架升级后可能静默失效；XFF 末跳可信依赖前置代理行为，若代理未强制覆写 XFF，IP 白名单/限流归属可被影响。
- 建议：避免反射改内部对象，改用公开 API；XFF 仅在受信代理后解析并按受信跳数取值，或直接用 `getRemoteAddress()`；网关入口统一覆写 XFF。
- 修复成本：低/中

### 正面安全实践（已核实）

- **OAuth state 防回调绕过**：5 平台发起登录/插件/绑定时均生成 state 写入 Redis（登录态 TTL 30s、绑定态 30min），回调先 `redisHelper.hasKey(state)` 校验（`LoginController` 各回调、Issue #115/PR #168）；state 用 `SecureRandom.getInstanceStrong()`（`SecureRandomUtil.java`）。
- **JWT 规范**：HMAC256 对称签名，密钥经 Apollo + Jasypt 密文下发、运行时 `SecurityUtil.decrypt`（`JwtConfig.java:30-32`）；`getClaimByName` 先验签再取 claim，验签失败抛 `CustomSecurityException`（`JwtHelper.java:183-195`）；access 30min / user 8h / refresh 30d；敏感 claim（三方 access_token）写入前 AES 加密。
- **Cookie 安全标志**：`httpOnly(true)` + `secure(true)`（`JwtHelper.java:163-164`），会话服务端存 Redis（30min 滑动续期），登出后 token/csrf 加入失效名单。
- **Redis 强制 SSL**（`RedisConfig.java` `.useSsl()`），DB/Redis/Mongo/RabbitMQ/机机密钥均 `SecurityUtil.decrypt` 解密，未发现硬编码密钥；`SecurityHelper` 启动校验 `security.part1` 非空（`SecurityHelper.java:31-44`）。
- **机机接口/Webhook**：HMAC-SHA256 动态加签 + 时间戳防重放 + 失败次数限制 + IP 白名单 + 账号-接口权限校验（`MachineInterfaceAuthHelper.java`）。
- **SQL 注入面低**：MyBatis XML 全量 `#{}` 参数绑定，未发现 `${}` 拼接；fastjson2 开启 safeMode（防 autoType RCE）。
- **限流**：路由级 Redis 漏桶（`RedisLeakyBucketRateLimiter` Lua 原子扣减）+ Webhook 令牌桶；未发现 `TrustAllCerts/NoopHostnameVerifier` 出现在 OkHttp 出站调用（出站三方 URL 均来自配置）。

---

## 四、行动摘要（整改优先级）

### Quick Wins（低成本快速修复）

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-01 | 移除 `use-insecure-trust-manager: true`，自签证书走受信信任库 | 低/中 |
| FIND-02 | 白名单 `contains` 改前缀/`PathPattern` 精确匹配 + 路径规范化 | 低 |
| FIND-03 | 绑定 `redirect` 参数加同源/白名单校验 | 低 |
| FIND-05 | 移除 MongoDB `invalidHostNameAllowed(true)` | 低 |
| FIND-06 | Cookie 增加 `SameSite=Lax`；Referer 改主机名精确匹配 | 低 |
| FIND-07 | GitHub 回调去掉 `e.getMessage()` 回显 | 低 |
| FIND-10 | 删除 `hashCode()==401` 冗余判断 | 低 |
| FIND-12 | 生产关闭 Swagger、收敛健康检查/actuator 暴露面 | 低 |

### 需专项处理

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-04 | Redis 故障安全策略统一（认证 fail-closed、异常不吞、告警） | 中 |
| FIND-08 | 后端仅接受网关来源（NetworkPolicy），身份改签名内部头 | 中 |
| FIND-11 | 评估废弃 gitee 账密直通，全链路不记录口令 | 中 |
| FIND-13 | 去除反射改 sslInfo；XFF 按受信跳数解析 | 低/中 |
| FIND-09 | 三方 access_token 改请求头，出站主机白名单 | 低 |

---

## 五、分析假设与需验证项

1. 白名单实际条目值（`exempt.paths`、`csrf.trust.list`、`forward.trust.list`、`no.authentication.accessible.paths`、`token.header.paths`）由 Apollo/Nacos 下发、不在仓内。FIND-02 的可利用性取决于条目是否为短片段/可作为子串出现，需在运行环境拉取实际配置验证，并据此构造绕过用例复测。
2. `use-insecure-trust-manager`（FIND-01）是否在环境配置（Apollo/Nacos）中被覆盖为 false，需在生产配置核验；仓内 `application.yaml` 默认值为 true。
3. `/middleware/healthCheckByType`、Swagger UI、actuator 是否在 `exempt.paths` 且对外网暴露，需结合部署 Ingress/NetworkPolicy 与白名单配置确认。
4. 网关到后端是否强制 mTLS/网络隔离、后端是否独立可达，决定 FIND-08 的实际可利用性。
5. `openlibing-common:1.0.20.1` SDK 提供 `SecurityUtil`/`HmacUtil`/fastjson2 safeMode 等，AES 模式/强度、HMAC 实现细节需结合 openlibing-common 报告最终确认。

## 六、参考标准

- STRIDE-A 威胁建模；OWASP Top 10:2025；CWE/MITRE；CIS Docker/K8s 基线；OWASP Cheat Sheet（认证、传输层保护、CSRF/ SameSite、开放重定向、服务端请求）。
