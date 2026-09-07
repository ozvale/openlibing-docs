# 安全威胁分析报告：openlibing-common

| 项 | 内容 |
|---|---|
| 仓库路径 | `D:\skill\skill收集\repo\openlibing-common` |
| 分析日期 | 2026-09-02 |
| 分析方法 | 静态代码审计（STRIDE-A 威胁建模 + 依赖/配置检查） |
| 报告语言 | 中文 |
| 部署分类 | **类库（jar）**——被各业务微服务依赖，其中 `@Component`（过滤器/拦截器/AOP）随业务服务 Spring 上下文自动装配；风险会被所有下游服务继承 |

---

## 一、系统概述

### 1.1 用途与技术栈

openlibing 各微服务共享的**基础安全 SDK**：内部服务鉴权过滤器、Feign 出站拦截器、JWT 工具、AES/HMAC/PBKDF2 加解密、安全命令执行器、外链校验、OBS/SMN/KMS 封装、日志 AOP 等。平台大量安全决策（认证、加密、命令执行）集中于此，其缺陷具有**全平台放大效应**。

- Java 21、Spring Boot 3.5.14 / Spring 6.2.19、Nacos、MyBatis-Plus、Redis/Jedis/Redisson、Feign、java-jwt 3.19.1、fastjson2、jasypt-spring-boot、华为云 SDK、commons-exec、hutool
- 自动装配入口：`filter/InternalAuthFilter.java:47`（`@Component @Order(HIGHEST_PRECEDENCE)`）、`interceptor/InternalAuthRequestInterceptor.java:20`、`config/ConfigContextInitializer.java:17`

### 1.2 组件与信任边界

| 组件 ID | 锚点 | 职责 | 信任边界 |
|---|---|---|---|
| InternalAuthFilter | `filter/InternalAuthFilter.java:47` | `/internal-server/**` 静态 token 入站校验 | 外部/集群内 → 业务服务 |
| InternalAuthRequestInterceptor | `interceptor/InternalAuthRequestInterceptor.java:20` | Feign 出站加 `X-Internal-Token` | 服务 → 服务 |
| JwtUtils | `utils/JwtUtils.java:36` | HMAC256 签发/校验、Cookie 生成 | 认证边界 |
| SecurityUtil / AESCipher / AESUtil / HmacUtil | `security/security/`、`security/cipher/` | 加解密、签名 | 加密边界 |
| KeyComponentUtil / ReadFileUtils | `security/KeyComponentUtil.java:24`、`security/cipher/ReadFileUtils.java:19` | 三段式根密钥生成与 `.ks` 文件读取 | 密钥管理边界 |
| SecureCmdExecutor | `security/SecureCmdExecutor.java:68` | 白名单命令执行 + 超时 + 沙箱 | 服务 → OS |
| CmdValidator / CsvValidator | `validator/` | 命令参数/CSV 校验 | 服务内 |
| ExternalLinkCheckUtils | `utils/ExternalLinkCheckUtils.java:22` | markdown 外链图片白名单 | 内容渲染边界 |
| LoggerAspect | `aspect/logapi/` | 日志 AOP | 日志边界 |

**关键信任边界**：① 集群内任意工作负载 → 内部接口（`/internal-server/**`）；② 配置中心（Nacos/Apollo）下发的开关与 token → 鉴权决策（配置缺失时的默认行为是关键风险点）；③ 密钥文件（`.ks`）→ 工作密钥还原。

---

## 二、STRIDE-A 威胁分析汇总

| STRIDE 类别 | 威胁数 | 代表性威胁 |
|---|---|---|
| S 仿冒 | 2 | 内部过滤器 fail-open 放行；路径 contains 匹配可被构造绕过 |
| T 篡改 | 1 | 密钥加载路径受环境变量影响 |
| R 抵赖 | 1 | JWT verifyToken 失败仅 log 返回 null，依赖调用方判空 |
| I 信息泄露 | 2 | JWT 对称密钥泄露即可伪造任意用户；Cookie 缺 SameSite |
| D 拒绝服务 | 1 | 路径误匹配导致静态资源被要求鉴权（可用性） |
| E 权限提升 | 3 | fail-open 内部接口匿名访问；contains 绕过内部接口鉴权；CSRF 结合 Cookie |
| A 业务滥用 | 1 | 内部接口被集群内滥用（无审计区分） |

### 关键威胁场景

**场景 1（E，fail-open）**：Nacos/Apollo 中 `internal.auth.token` 未配置或被置空、或 `internal.auth.enabled=false` → `InternalAuthFilter` 打印 warn 后 `filterChain.doFilter()` 放行（`:86-98`）→ `/internal-server/**` 高权限内部接口匿名可达 → 配置遗漏即静默失权，且该过滤器被所有业务服务继承。

**场景 2（E，路径绕过）**：内部路径判定使用 `requestUri.contains(pathPrefix)`（`:130-143`）而非规范化后的段边界匹配 → 分号矩阵参数、`//`、URL 编码、`/x/internal-server/../y` 等在网关与服务间的路径解释差异可能使真正的内部接口未命中前缀而放行。

**场景 3（S/E，JWT）**：JWT 使用 HMAC256 对称密钥（`JwtUtils.java:87,112,161`），密钥来自配置解密；一旦密钥泄露（密钥文件烘焙镜像，见各服务 Dockerfile 发现）即可伪造任意用户 token；Cookie 未设 SameSite（`:125-131`），存在 CSRF 面。

---

## 三、安全发现明细

### 高危

#### FIND-01：内部鉴权过滤器 fail-open（未配置 token / 开关关闭即匿名放行）

| 属性 | 内容 |
|---|---|
| STRIDE | E（权限提升） |
| CWE | [CWE-306](https://cwe.mitre.org/data/definitions/306.html) 缺失认证；[CWE-636](https://cwe.mitre.org/data/definitions/636.html) 安全机制失效时未 fail-close |
| OWASP | A01:2025 – Broken Access Control；A05:2025 – Security Misconfiguration |
| 利用前提 | 能访问到业务服务（集群内/SSRF/网关绕过），且配置缺失或开关被关 |
| 证据 | `filter/InternalAuthFilter.java:86-90` `if (!isAuthEnabled) { filterChain.doFilter(...); return; }`；`:92-98` `if (StringUtils.isBlank(expectedToken)) { LOGGER.warn("...degraded mode..."); filterChain.doFilter(...); return; }` |
| 风险 | `/internal-server/**` 高权限内部接口在配置遗漏/置空时**匿名放行**，仅 warn 日志。该过滤器随所有业务服务自动装配，一个配置错误影响全平台内部接口。 |
| 修复建议 | 安全默认 fail-close：token 缺失时拒绝请求并使应用启动失败（`@Conditional` 强制要求配置）；`enabled=false` 仅允许非 prod profile 生效并启动告警；对接配置中心健康检查，token 为空时熔断。 |
| 修复成本 | 低 |

#### FIND-02：内部路径判定使用 `contains` 子串匹配，无路径规范化

| 属性 | 内容 |
|---|---|
| STRIDE | E / S |
| CWE | [CWE-863](https://cwe.mitre.org/data/definitions/863.html) 授权判定不正确；[CWE-184](https://cwe.mitre.org/data/definitions/184.html) 不完整黑名单 |
| OWASP | A01:2025 – Broken Access Control |
| 证据 | `InternalAuthFilter.java:130-143` `if (requestUri.contains(pathPrefix)) { return true; }`；默认前缀 `/internal-server`（:53）；未基于 `getServletPath()` 做归一化 |
| 风险 | ① `contains` 不锚定边界，公开路径中含该串会被误判（DoS/误拦）；② Spring 对分号矩阵参数、`//`、URL 编码（`%2f`）的归一化差异可能使真正内部接口以未命中前缀形态放行（鉴权绕过）。 |
| 修复建议 | 使用 `request.getServletPath()`（容器已归一化）后 `startsWith(prefix + "/")` 精确匹配；增加路径规范化单元测试（分号、`../`、双斜杠、编码）；前缀集合按"精确路径 + 方法"维护。 |
| 修复成本 | 低 |

### 中危

#### FIND-03：JWT Cookie 缺少 SameSite，且使用对称密钥

| 属性 | 内容 |
|---|---|
| STRIDE | E / I |
| CWE | [CWE-352](https://cwe.mitre.org/data/definitions/352.html) CSRF；[CWE-320](https://cwe.mitre.org/data/definitions/320.html) 密钥管理不当 |
| OWASP | A01:2025；A02:2025 – Cryptographic Failures |
| 证据 | `utils/JwtUtils.java:125-131` `ResponseCookie.from("token", jwtToken).domain(domain).httpOnly(true).secure(true).path("/").maxAge(maxAge).build()`（无 sameSite）；签名 `Algorithm.HMAC256(decryptSecret)`（:87,112,161）；`verifyToken` 失败仅 log 返回 null（:163-167） |
| 风险 | ① 无 SameSite，跨站请求携带 Cookie，结合未设防 POST 接口存在 CSRF；② HMAC 对称密钥一旦泄露即可伪造任意用户 token；③ verifyToken 返回 null 依赖调用方判空，存在调用方遗漏导致未认证访问的风险。 |
| 修复建议 | `.sameSite("Lax")`（严格场景 Strict）；考虑非对称算法 RS256 或 KMS 托管密钥；对 verifyToken 结果做统一封装（null 即拒绝），避免业务代码裸用。 |
| 修复成本 | 中 |

#### FIND-04：密钥文件加载路径受环境变量控制，无完整性/归属校验

- STRIDE：I / T ｜ CWE：[CWE-73](https://cwe.mitre.org/data/definitions/73.html) 外部控制文件路径；[CWE-522](https://cwe.mitre.org/data/definitions/522.html) ｜ OWASP：A07:2025
- 证据：`security/cipher/ReadFileUtils.java:61-72` `PROJECT_NAME` 环境变量决定密钥根路径，随后读 `<path>/keys/tcpFile.ks` 等（:26-53）。
- 风险：环境变量被篡改或路径可写时，可诱导加载攻击者提供的 `.ks`，进而解密/伪造工作密钥；密钥文件随各服务镜像分发（见各服务 Dockerfile COPY `.ks`）。
- 建议：密钥路径固定/白名单；文件权限 600 且属主为运行用户；优先从 KMS/挂载 Secret 获取而非镜像内文件。
- 修复成本：中

### 低危 / 信息

#### FIND-05：springdoc-openapi 与 actuator 被引入所有业务服务，缺安全默认值

- STRIDE：I ｜ CWE：[CWE-1059](https://cwe.mitre.org/data/definitions/1059.html)、[CWE-1188](https://cwe.mitre.org/data/definitions/1188.html) ｜ OWASP：A05:2025
- 证据：`pom.xml:562-565` 引入 `springdoc-openapi-starter-webmvc-ui` 到所有业务服务；`:121-127` 引入 actuator，暴露策略由各服务 yaml 决定（已在 anti-poison/platform-release 发现 shutdown 暴露）。
- 风险：Swagger 接口文档生产暴露；actuator 危险端点依赖各服务自行收敛，已出现实际偏差。
- 建议：在 common 层提供安全自动配置默认值（默认只暴露 health、shutdown 关闭、生产关闭 swagger-ui），下游服务默认继承安全基线。
- 修复成本：低

#### FIND-06：正面安全实践（供参考与推广）

- `SecureCmdExecutor.java`：L1 命令白名单（`:864`）、L2 参数 NFKC 归一化 + 正则黑名单、L3 超时 + 优雅销毁（SIGTERM→SIGKILL）、环境变量黑名单（含 `LD_PRELOAD`）、工作目录禁根/禁系统目录（`:704`）、数组形式 ProcessBuilder 不经 shell（`:607-615`）。**建议 anti-poison/platform-release 的 curl/git/python/clamscan 调用全部迁移到该组件**。
- `InternalAuthFilter.isTokenValid:154-161` 使用 `MessageDigest.isEqual` 常量时间比较，防时序攻击。
- `ExternalLinkCheckUtils.java:64-74` 外链 host 精确匹配 + `.domain` 后缀白名单，逻辑正确。
- 依赖版本整体较新（Spring 6.2.19/Boot 3.5.14/fastjson2 2.0.56/jackson 2.21.4/log4j 2.25.4），未发现 shiro、fastjson1、旧 log4j 等高危组件；hutool 5.8.40、redisson 3.45.1、java-jwt 3.19.1（已修 CVE-2022-23529，建议跟进 4.x）。

---

## 四、行动摘要（整改优先级）

### Quick Wins（低成本快速修复）

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-01 | InternalAuthFilter 改 fail-close，token 缺失即拒绝/启动失败 | 低 |
| FIND-02 | 路径匹配改用 getServletPath + 段边界 startsWith，补规范化测试 | 低 |
| FIND-05 | common 层提供 actuator/springdoc 安全默认自动配置 | 低 |

### 需专项处理

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-03 | JWT Cookie 加 SameSite；评估 RS256/KMS 托管；verifyToken 统一封装 | 中 |
| FIND-04 | 密钥加载路径固定化、权限收敛、迁移 KMS/Secret 挂载 | 中 |
| 推广 | 将各服务 `Runtime.exec("/bin/sh","-c",...)` 统一迁移到 SecureCmdExecutor | 中（跨仓） |

---

## 五、分析假设与需验证项

1. 本仓为类库，实际行为取决于下游服务的配置（Nacos/Apollo 下发的 `internal.auth.*`、`security.part1` 等）；fail-open 的实际暴露需结合运行配置核验。
2. `JwtUtils` 的签名/过期/算法校验细节（是否拒绝 `alg=none`、密钥强度）建议结合配置值做专项验证——多个下游服务（framework、gateway、vulnerability）直接"读取 claim"认定用户，验签严格性由此类决定。
3. 建议将本 SDK 作为独立审计对象生成 SBOM，并对其版本（各服务依赖 1.0.19.5~1.0.20.5 不一致）做统一收敛。

## 六、参考标准

- STRIDE-A 威胁建模；OWASP Top 10:2025；CWE/MITRE；OWASP Cheat Sheet（认证、JWT、CSRF、密钥管理）。
