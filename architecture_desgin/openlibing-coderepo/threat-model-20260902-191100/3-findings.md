# Security Findings

---

## Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 findings identified for this repository._

---

## Tier 2 — Conditional Risk (Authenticated / Single Prerequisite)

### FIND-01: Webhook HMAC-SHA256 签名比对使用非恒定时间 String.equals

| Attribute                  | Value                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Critical                                                                                  |
| CVSS 4.0                   | 7.4 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N)                     |
| CWE                        | [CWE-208](https://cwe.mitre.org/data/definitions/208.html): Observable Timing Discrepancy |
| OWASP                      | A02:2025 – Cryptographic Failures                                                         |
| Exploitation Prerequisites | Authenticated User                                                                        |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                           |
| Remediation Effort         | Low                                                                                       |
| Mitigation Type            | Standard Mitigation                                                                       |
| Component                  | WebHookEventController                                                                    |
| Related Threats            | [T01.1](2-stride-analysis.md#webhookeventcontroller)                                      |

#### Description

`WebhookAuthUtil.validateSignature` 使用 `hexString.toString().equals(signature)` 比对客户端传入的 HMAC-SHA256 签名与本地计算的签名。Java `String.equals` 在发现第一个不匹配字符时立即返回，导致比对耗时与匹配前缀长度线性相关。攻击者可在已获知 webhook 端点的前提下，通过逐字节篡改签名并测量响应时间，恢复出合法签名（时序侧信道）。一旦签名被恢复，攻击者可绕过 HMAC 校验直接投递伪造的 webhook 事件至 RabbitMQ，触发 PR 评论/标签等副作用操作。

#### Evidence

**Prerequisite basis:** Webhook 端点 `/apig/webhook/{platform}/repo` 经 APIG 对外暴露，Reachability=External，Min Prerequisite=Authenticated User（见 Component Exposure Table）。攻击者仅需能到达 APIG 即可触发签名校验流程。

`src/main/java/com/openlibing/coderepo/common/utils/WebhookAuthUtil.java:136`:

```java
return hexString.toString().equals(signature);
```

#### Remediation

将 `String.equals` 替换为 `java.security.MessageDigest.isEqual(byte[], byte[])` 进行恒定时间比对：

```java
return MessageDigest.isEqual(
    hexString.toString().getBytes(StandardCharsets.UTF_8),
    signature.getBytes(StandardCharsets.UTF_8));
```

#### Verification

1. 审查 `WebhookAuthUtil.validateSignature` 代码确认使用 `MessageDigest.isEqual`；2. 编写单元测试，构造不同前缀长度的错误签名，验证响应耗时无显著差异（统计偏差 < 5%）。

---

### FIND-02: Webhook 事件无重放保护

| Attribute                  | Value                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                 |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:L/VA:L/SC:N/SI:N/SA:N)                     |
| CWE                        | [CWE-294](https://cwe.mitre.org/data/definitions/294.html): Catching a Too-Late Exception |
| OWASP                      | A07:2025 – Identification and Authorization Failures                                      |
| Exploitation Prerequisites | Authenticated User                                                                        |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                           |
| Remediation Effort         | Medium                                                                                    |
| Mitigation Type            | Custom Mitigation                                                                         |
| Component                  | WebHookEventController                                                                    |
| Related Threats            | [T01.3](2-stride-analysis.md#webhookeventcontroller)                                      |

#### Description

`WebhookAuthController.apigGitCodeWebhookEvent` 在签名校验通过后直接将事件投递至 RabbitMQ，未对 `X-GitCode-Delivery`/`X-GitHub-Delivery` 等唯一事件 ID 做去重缓存。攻击者截获一次合法的 webhook 请求后，可短时间内多次重放该请求（签名仍校验通过），导致消费者侧触发重复的 PR 评论、标签、流水线记录等副作用操作，造成 PR 噪音与平台 API 配额浪费。该问题与 FIND-28（消费者侧幂等缺失）共同放大重放影响。

#### Evidence

**Prerequisite basis:** Webhook 端点经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User），截获合法 webhook 后即可重放。

`src/main/java/com/openlibing/coderepo/business/controller/WebHookEventController.java` 中 `apigGitCodeWebhookEvent`/`apigGiteeWebhookEvent`/`apigGithubWebhookEvent` 方法签名校验通过后直接 `rabbitTemplate.convertAndSend` 投递消息，未读取 `X-GitCode-Delivery`/`X-GitHub-Delivery` 头进行去重。

#### Remediation

在 Controller 投递前增加 Redis SET NX 去重缓存：以 `webhook:delivery:{platform}:{deliveryId}` 为 key 写入 TTL 5 分钟（与平台侧重发窗口对齐），写入失败视为重复事件直接返回 200 但不投递消息。

#### Verification

1. 审查 Controller 代码确认读取 delivery ID 并查询 Redis 去重；2. 集成测试：构造同一 delivery ID 的两次请求，验证第二次返回 200 但消息不重复投递至 RabbitMQ。

---

### FIND-03: 敏感平台 Token 在 INFO 日志中输出

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                    |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:H/SI:N/SA:N)                                        |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP                      | A09:2025 – Security Logging and Monitoring Failures                                                          |
| Exploitation Prerequisites | Authenticated User                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                              |
| Remediation Effort         | Low                                                                                                          |
| Mitigation Type            | Standard Mitigation                                                                                          |
| Component                  | WebHookEventController                                                                                       |
| Related Threats            | [T01.4](2-stride-analysis.md#webhookeventcontroller)                                                         |

#### Description

`WebHookEventController.apigGitCodeWebhookEvent` 等方法在签名校验失败、事件接收等流程中使用 `LOGGER.info` 输出请求头与请求体上下文，可能包含 `X-GitCode-Token`、`X-Gitee-Token`、`PRIVATE-TOKEN` 等敏感头部值。日志若被运维侧聚合（如 ELK）或被未授权人员读取，平台 access token 可被还原，攻击者据此可访问所有配置了该 token 的仓库元数据。仓库已有 `SensitiveDataConverter` 日志脱敏组件但未在 webhook 路径启用。

#### Evidence

**Prerequisite basis:** Webhook 流量经 APIG 对外暴露，签名校验过程中产生的日志包含外部可控的请求头（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/controller/WebHookEventController.java` 中 LOGGER.info 输出请求头与请求体上下文；`src/main/java/com/openlibing/coderepo/common/utils/SensitiveDataConverter.java` 提供日志脱敏能力但未在 webhook logger 链路启用。

#### Remediation

在 webhook logger 链路启用 `SensitiveDataConverter`，对 `X-GitCode-Token`/`X-Gitee-Token`/`PRIVATE-TOKEN`/`Authorization` 头部值脱敏为 `***`；将签名校验失败日志级别降为 WARN，仅记录失败原因不记录请求内容。

#### Verification

1. 配置 logback 使用 `SensitiveDataConverter` 包装 webhook logger；2. 触发一次 webhook 事件，grep 日志确认 token 头部值为 `***`；3. 单元测试 `SensitiveDataConverterTest` 覆盖敏感头列表。

---

### FIND-04: Webhook 端点应用层无限流导致 CPU/队列耗尽

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling |
| OWASP                      | A04:2025 – Untrusted Data Consumption                                                                            |
| Exploitation Prerequisites | Authenticated User                                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                  |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                                              |
| Component                  | WebHookEventController                                                                                           |
| Related Threats            | [T01.5](2-stride-analysis.md#webhookeventcontroller), [T01.6](2-stride-analysis.md#webhookeventcontroller)       |

#### Description

Webhook 端点在应用层未实现 IP 限流与 RabbitMQ 投递速率限制，仅依赖 APIG 网关层限流。一旦攻击者绕过 APIG（如内网直连 8076）或 APIG 限流策略被误配，攻击者可投递大量伪造签名的 webhook 请求：每次签名校验消耗 HMAC-SHA256 计算 CPU，且 RabbitMQ 投递无背压机制。后果是应用 CPU 被签名校验耗尽，或 RabbitMQ 队列堆积导致消费者 OOM。

#### Evidence

**Prerequisite basis:** Webhook 端点对外暴露（Reachability=External, Min Prerequisite=Authenticated User），APIG 限流为外部不可控假设。

`src/main/java/com/openlibing/coderepo/business/controller/WebHookEventController.java` 无 `@RateLimiter`/`RedisRateLimiter` 注解或拦截器；`src/main/java/com/openlibing/coderepo/common/config/RabbitMQConfig.java`（如存在）的 `webhook_event_queue_beta` 队列未配置 `x-max-length` 与死信策略。

#### Remediation

1. 在 Controller 增加基于 Redis 的令牌桶限流（单 IP/分钟 60 次）；2. RabbitMQ 队列配置 `x-max-length` 与 `x-dead-letter-exchange`，超限消息转死信；3. RabbitTemplate 投递失败时增加幂等去重 + 背压。

#### Verification

1. 压测脚本构造 1000 RPS 伪造签名请求，确认应用 CPU 与 RabbitMQ 队列长度被限流策略限制；2. 队列超长后确认消息转死信队列。

---

### FIND-05: Gitee Webhook 端点对外暴露但鉴权硬编码拒绝

| Attribute                  | Value                                                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                  |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)                                     |
| CWE                        | [CWE-1188](https://cwe.mitre.org/data/definitions/1188.html): Insecure Default Initialization of Resource |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                      |
| Exploitation Prerequisites | Authenticated User                                                                                        |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                           |
| Remediation Effort         | Low                                                                                                       |
| Mitigation Type            | Standard Mitigation                                                                                       |
| Component                  | WebHookEventController                                                                                    |
| Related Threats            | [T01.7](2-stride-analysis.md#webhookeventcontroller), [T14.1](2-stride-analysis.md#gitee)                 |

#### Description

`WebhookAuthUtil.webhookAuth` 对 Gitee 平台硬编码 `return false` 停用告警抑制扫描，但 `/apig/webhook/gitee/repo` 端点仍对外暴露。任何到达 APIG 的请求都会进入签名校验流程并直接返回失败响应，形成功能静默失效与无效端点暴露。攻击面虽不能直接造成数据泄露，但增加 APIG 与应用层无效请求处理负担，且未来若 Gitee 鉴权逻辑恢复（如 hotfix 改回 true）将形成静默绕过。

#### Evidence

**Prerequisite basis:** Webhook 端点对外暴露（Reachability=External, Min Prerequisite=Authenticated User），Gitee 端点路由由 APIG 暴露。

`src/main/java/com/openlibing/coderepo/common/utils/WebhookAuthUtil.java:62-65`:

```java
if ("gitee".equals(platform)) {
  LOGGER.warn("Gitee platform is no longer supported for suppression scan webhook auth");
  return false;
}
```

APIG 路由 `/apig/webhook/gitee/repo` 端点仍存在并转发至 `apigGiteeWebhookEvent` 方法。

#### Remediation

若 Gitee 已彻底停用，应在 APIG 路由层直接下线 `/apig/webhook/gitee/repo`，返回 404 而非进入应用层；若需保留代码以备恢复，应通过 Apollo 配置开关控制，且在开关关闭时 APIG 路由级返回 410 Gone。

#### Verification

1. 调用 `POST /apig/webhook/gitee/repo` 确认返回 404 或 410；2. 审查 APIG 路由配置确认 gitee webhook 路由已下线。

---

### FIND-06: 仓库导出文件路径未严格校验存在路径遍历

| Attribute                  | Value                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                             |
| CVSS 4.0                   | 6.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:H/VA:L/SC:H/SI:N/SA:N)                                                 |
| CWE                        | [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Improper Limitation of a Pathname to a Restricted Directory |
| OWASP                      | A01:2025 – Broken Access Control                                                                                      |
| Exploitation Prerequisites | Authenticated User                                                                                                    |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                       |
| Remediation Effort         | Medium                                                                                                                |
| Mitigation Type            | Custom Mitigation                                                                                                     |
| Component                  | RepoController                                                                                                        |
| Related Threats            | [T02.1](2-stride-analysis.md#repocontroller), [T18.1](2-stride-analysis.md#obs)                                       |

#### Description

仓库导出接口生成导出文件名时未对用户可控的文件名参数做白名单字符校验，直接拼接为 OBS 对象 key。攻击者可传入 `../../admin-export/secret.xlsx` 等路径作为导出文件名，覆盖他人项目下的导出产物，或跨 OBS 前缀读取敏感导出。OBS 端也存在相同问题（T18.1），二者共同构成跨项目越权覆盖风险。

#### Evidence

**Prerequisite basis:** 导出接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User），文件名参数由请求方传入。

`src/main/java/com/openlibing/coderepo/business/controller/RepoController.java` 的导出接口（如 `/export`）接收文件名参数；`src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java` 的导出方法将文件名拼接为 OBS 对象 key 前未做白名单校验。

#### Remediation

文件名仅允许 `[A-Za-z0-9_-]` 字符，拒绝 `..`、`/`、`\`；OBS 对象 key 强制以 `{projectId}/{userId}/{uuid}.{ext}` 模板生成，用户输入仅作为扩展名白名单。

#### Verification

1. 单元测试覆盖 `../`、绝对路径、特殊字符等攻击向量；2. 集成测试构造恶意文件名确认 OBS 拒绝写入异常前缀。

---

### FIND-07: 异常处理返回详细错误信息泄露仓库元数据

| Attribute                  | Value                                                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                                                 |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                                    |
| CWE                        | [CWE-209](https://cwe.mitre.org/data/definitions/209.html): Generation of Error Message Containing Sensitive Information |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                                     |
| Exploitation Prerequisites | Authenticated User                                                                                                       |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                          |
| Remediation Effort         | Low                                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                                      |
| Component                  | RepoController                                                                                                           |
| Related Threats            | [T02.2](2-stride-analysis.md#repocontroller)                                                                             |

#### Description

`GlobalExceptionHandler` 在捕获业务异常时可能将异常消息原文返回给调用方，部分异常消息包含仓库 URL、内部 ID、数据库错误码等内部信息。攻击者可据此探测内部仓库存在性、数据库表结构与配置，作为后续攻击的情报收集。仓库已有 `GlobalExceptionHandler` 与 `ErrorCode` 枚举，但未对所有业务异常做脱敏映射。

#### Evidence

**Prerequisite basis:** 仓库 CRUD 接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/common/exception/GlobalExceptionHandler.java` 的异常处理逻辑可能直接 `e.getMessage()` 返回调用方；`RepoServiceImpl` 的部分异常消息包含 `repoUrl`、`projectId` 等字段。

#### Remediation

`GlobalExceptionHandler` 仅返回 `ErrorCode` 枚举的错误码与简短提示，原始异常消息仅写入应用日志；新增 `SANITIZED_BUSINESS_ERROR` 错误码用于通用业务失败。

#### Verification

1. 触发已知会抛业务异常的接口（如录入重复仓库），确认响应体不含 `repoUrl` 或数据库错误；2. 审查 `GlobalExceptionHandler` 所有 `@ExceptionHandler` 分支确认无原文返回。

---

### FIND-08: 大规模仓库导出无并发限制造成资源耗尽

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling |
| OWASP                      | A04:2025 – Untrusted Data Consumption                                                                            |
| Exploitation Prerequisites | Authenticated User                                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                  |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                                              |
| Component                  | RepoController                                                                                                   |
| Related Threats            | [T02.3](2-stride-analysis.md#repocontroller)                                                                     |

#### Description

仓库导出接口对单用户的并发导出数量与单次导出的仓库规模未做限制。攻击者（或正常用户的大批量操作）可并发触发多个导出任务，每个任务序列化仓库元数据并上传 OBS，消耗应用内存、JDBC 连接池与 OBS 上传带宽。极端情况下导致 HikariCP 连接池耗尽，影响其他业务请求。

#### Evidence

**Prerequisite basis:** 导出接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/controller/RepoController.java` 的导出接口无并发限制注解；`src/main/java/com/openlibing/coderepo/common/config/DataSourceConfig.java` 的 HikariCP 默认 `maximumPoolSize=10`，单用户并发导出即可占满连接池。

#### Remediation

1. 单用户并发导出限制为 1（基于 Redisson 分布式锁）；2. 单次导出仓库数上限 100，超限要求分页；3. 导出任务异步化，通过 RabbitMQ 队列削峰后异步生成文件并预签名 URL 返回。

#### Verification

1. 压测脚本构造单用户并发 5 次导出请求，确认仅 1 次成功其余返回 429；2. 构造 500 仓库的批量导出，确认被分页限制拒绝。

---

### FIND-09: 仓库 CRUD 操作未校验用户对该仓库的归属权限存在 IDOR

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                    |
| CVSS 4.0                   | 6.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                        |
| CWE                        | [CWE-639](https://cwe.mitre.org/data/definitions/639.html): Authorization Bypass Through User-Controlled Key |
| OWASP                      | A01:2025 – Broken Access Control                                                                             |
| Exploitation Prerequisites | Authenticated User                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                              |
| Remediation Effort         | Medium                                                                                                       |
| Mitigation Type            | Custom Mitigation                                                                                            |
| Component                  | RepoController                                                                                               |
| Related Threats            | [T02.4](2-stride-analysis.md#repocontroller)                                                                 |

#### Description

`RepoController` 的仓库查询、更新、删除接口仅校验用户登录态，未校验用户对该仓库所属项目的角色权限。攻击者构造任意 `repoId` 调用 `/repo/{repoId}` 接口即可越权读取他人项目下的仓库元数据（含仓库 URL、平台、access token 是否存在的标记），甚至越权删除他人仓库记录。该问题与 FIND-19（代码度量 IDOR）属于同类越权访问缺陷。

#### Evidence

**Prerequisite basis:** 仓库 CRUD 接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/controller/RepoController.java` 的查询/删除接口签名仅含 `repoId`，无 `projectId` 或角色校验参数；`src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java` 直接按 `repoId` 查询数据库，无用户角色联合校验。

#### Remediation

在 `RepoServiceImpl` 的查询/删除方法增加 `userId` 参数，先查询仓库所属 `projectId`，再通过 `ProjectMemberService.getUserRole(projectId, userId)` 校验调用方角色，非项目成员或更低角色直接抛 `PermissionException`。

#### Verification

1. 集成测试：用户 A 创建项目 P1 与仓库 R1，用户 B 调用 `/repo/R1` 应返回 403；2. 审查 service 层所有按 `repoId` 单参查询的方法均增加角色校验。

---

### FIND-10: 仓库 URL 录入未校验内网地址导致 SSRF

| Attribute                  | Value                                                                                   |
| -------------------------- | --------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                               |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:H/SC:L/SI:L/SA:N)                   |
| CWE                        | [CWE-918](https://cwe.mitre.org/data/definitions/918.html): Server-Side Request Forgery |
| OWASP                      | A10:2025 – Server-Side Request Forgery                                                  |
| Exploitation Prerequisites | Authenticated User                                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                         |
| Remediation Effort         | Medium                                                                                  |
| Mitigation Type            | Custom Mitigation                                                                       |
| Component                  | RepoController                                                                          |
| Related Threats            | [T02.5](2-stride-analysis.md#repocontroller)                                            |

#### Description

仓库录入接口接受任意 URL 作为仓库地址，未校验是否为内网地址或 localhost。攻击者录入 `http://127.0.0.1:8848/nacos` 或 `http://169.254.169.254:80/latest/meta-data/` 等内网地址作为仓库 URL，后续 `XxlJobHandler` 或 `WebhookEventConsumer` 在分支刷新、PR 同步等流程中调用该 URL，触发 SSRF 探测内网服务（如 Nacos 控制台、云元数据接口），泄露内部凭证或配置。

#### Evidence

**Prerequisite basis:** 仓库录入接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User），URL 字段由用户传入。

`src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java` 的 `addRepo` 方法接收 `repoUrl` 后未做域名白名单校验；后续 `GitCode.getBranches`/`Gitee.getBranches`/`Github.getBranches` 等客户端基于 `repoUrl` 发起 HTTP 请求。

#### Remediation

`addRepo` 时校验 `repoUrl` 域名白名单（仅允许 `gitcode.com`、`gitee.com`、`github.com`），拒绝内网 IP（10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、127.0.0.0/8、169.254.0.0/16）与 localhost 主机名。

#### Verification

1. 单元测试覆盖 `http://127.0.0.1`、`http://169.254.169.254`、`http://10.0.0.1` 等内网地址应被拒绝；2. 集成测试录入 `http://gitcode.com/valid/repo` 应成功。

---

### FIND-11: SIG 扫描路径配置可指向恶意仓库注入恶意配置

| Attribute                  | Value                                                                                                                |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                            |
| CVSS 4.0                   | 6.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:L/VA:N/SC:L/SI:N/SA:N)                                                |
| CWE                        | [CWE-829](https://cwe.mitre.org/data/definitions/829.html): Inclusion of Functionality from Untrusted Control Sphere |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                                      |
| Exploitation Prerequisites | Privileged User                                                                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                      |
| Remediation Effort         | Medium                                                                                                               |
| Mitigation Type            | Custom Mitigation                                                                                                    |
| Component                  | ProjectConfigController                                                                                              |
| Related Threats            | [T03.1](2-stride-analysis.md#projectconfigcontroller)                                                                |

#### Description

`ProjectConfigController` 允许管理员配置全局 SIG 扫描路径（指向某 GitCode 仓库的 `sig-info.yaml` 路径），后续扫描任务拉取该 URL 的 yaml 并解析。若管理员被钓鱼或权限被滥用，可录入指向恶意仓库的路径，恶意 `sig-info.yaml` 可注入恶意字段（如引用其他恶意仓库、超长字段触发解析 OOM、注入命令模板字段），影响后续扫描任务执行。

#### Evidence

**Prerequisite basis:** ProjectConfigController 经 APIG 对外暴露但需 Privileged User 角色（见 Component Exposure Table, Min Prerequisite=Privileged User）。

`src/main/java/com/openlibing/coderepo/business/controller/ProjectConfigController.java` 的 SIG 路径配置接口接收任意 URL；`src/main/java/com/openlibing/coderepo/business/service/impl/ProjectConfigServiceImpl.java` 与 sig-info.yaml 解析逻辑未做 schema 校验。

#### Remediation

1. SIG 路径录入时校验域名白名单（仅允许 `gitcode.com` 内 `openlibing`/`openlibing-test` 组织）；2. `sig-info.yaml` 解析使用 strict schema 校验（字段类型、长度上限、URL 域名白名单）；3. 拒绝引用 sig-info 仓库外的路径。

#### Verification

1. 单元测试覆盖恶意 URL 与字段超长场景；2. 集成测试录入 `https://gitcode.com/evil/sig-info.yaml` 应被拒绝；3. 校验 schema 拒绝未知字段。

---

### FIND-12: 全局配置变更未强制记录操作者与变更前后值

| Attribute                  | Value                                                                            |
| -------------------------- | -------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                         |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)            |
| CWE                        | [CWE-778](https://cwe.mitre.org/data/definitions/778.html): Insufficient Logging |
| OWASP                      | A09:2025 – Security Logging and Monitoring Failures                              |
| Exploitation Prerequisites | Privileged User                                                                  |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                  |
| Remediation Effort         | Low                                                                              |
| Mitigation Type            | Custom Mitigation                                                                |
| Component                  | ProjectConfigController                                                          |
| Related Threats            | [T03.2](2-stride-analysis.md#projectconfigcontroller)                            |

#### Description

`ProjectConfigController` 的全局配置变更接口（如修改 `github.common.access_token`）若未通过 AOP 强制记录操作者身份与变更前后值，事后无法追溯谁在何时修改了哪些敏感配置。一旦发生凭证滥用（如 GitHub token 被恶意替换为攻击者控制 token），无法定位责任人与变更链路，也无法做回滚操作。

#### Evidence

**Prerequisite basis:** 配置变更接口经 APIG 暴露，需 Privileged User 角色（Min Prerequisite=Privileged User）。

`src/main/java/com/openlibing/coderepo/business/controller/ProjectConfigController.java` 的全局配置更新方法；`src/main/java/com/openlibing/coderepo/common/handler/SpaceUserLogHandler.java`（如存在）AOP 切面需确认是否覆盖配置变更方法。

#### Remediation

全局配置变更方法强制走 `SpaceUserLogHandler` AOP，记录字段名、旧值、新值、操作者 userId 与时间戳；敏感字段（access_token、secretKey）的旧值仅记录掩码。

#### Verification

1. 集成测试修改全局配置后查询 `space_user_log` 表确认有完整变更记录；2. 审查 AOP 切点覆盖所有配置变更方法。

---

### FIND-13: 项目级 Token 查询接口可能返回明文 Token

| Attribute                  | Value                                                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                              |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:N/VA:N/SC:H/SI:N/SA:N)                                                  |
| CWE                        | [CWE-200](https://cwe.mitre.org/data/definitions/200.html): Exposure of Sensitive Information to an Unauthorized Actor |
| OWASP                      | A01:2025 – Broken Access Control                                                                                       |
| Exploitation Prerequisites | Privileged User                                                                                                        |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                        |
| Remediation Effort         | Low                                                                                                                    |
| Mitigation Type            | Custom Mitigation                                                                                                      |
| Component                  | ProjectConfigController                                                                                                |
| Related Threats            | [T03.3](2-stride-analysis.md#projectconfigcontroller)                                                                  |

#### Description

项目级 Token 查询接口若直接返回数据库存储的加密 token 或调用 `SecurityUtil.decrypt` 解密后返回明文，越权调用（管理员账号被劫持或外部上游服务凭证泄露）可一次性获取项目下所有平台的 access token，进而访问所有配置了该 token 的仓库代码与元数据。即使接口需 Privileged User 角色，明文返回仍扩大了 token 暴露面。

#### Evidence

**Prerequisite basis:** Token 查询接口需 Privileged User 角色（Min Prerequisite=Privileged User）。

`src/main/java/com/openlibing/coderepo/business/controller/ProjectConfigController.java` 的 Token 查询接口；`src/main/java/com/openlibing/coderepo/business/service/impl/ProjectConfigServiceImpl.java` 是否调用 `SecurityUtil.decrypt` 后原样返回。

#### Remediation

Token 查询接口仅返回掩码（如 `ghp_****abcd`，保留前 4 后 4 字符）；明文 token 仅在内部服务调用链（如 `PrAccessTokenServiceImpl` 内部解密）传递，禁止经 REST 接口暴露。

#### Verification

1. 集成测试调用 Token 查询接口，确认响应为掩码格式；2. 审查 service 层确认无方法将明文 token 经 DTO 返回 Controller。

---

### FIND-14: 项目角色映射可被管理员篡改为高权限角色

| Attribute                  | Value                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                 |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                     |
| CWE                        | [CWE-269](https://cwe.mitre.org/data/definitions/269.html): Improper Privilege Management |
| OWASP                      | A01:2025 – Broken Access Control                                                          |
| Exploitation Prerequisites | Privileged User                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                           |
| Remediation Effort         | Medium                                                                                    |
| Mitigation Type            | Custom Mitigation                                                                         |
| Component                  | ProjectConfigController                                                                   |
| Related Threats            | [T03.4](2-stride-analysis.md#projectconfigcontroller)                                     |

#### Description

`GitCodeRoleMapping` 等角色映射表可被管理员直接修改，若将普通用户角色 ID 映射为 admin 角色，该用户即可获得全平台管理员权限。当前变更虽有日志记录（FIND-12 修复后），但单人修改即可生效，无审批双人复核或变更告警，存在内部滥用与权限提升风险。

#### Evidence

**Prerequisite basis:** 角色映射变更需 Privileged User 角色（Min Prerequisite=Privileged User）。

`src/main/java/com/openlibing/coderepo/business/controller/ProjectConfigController.java` 的角色映射更新接口；`src/main/java/com/openlibing/coderepo/business/service/impl/RoleMappingServiceImpl.java` 的更新方法直接 `UPDATE role_mapping SET role_id=...`。

#### Remediation

1. 角色映射变更为高风险角色（admin/superadmin）需双人审批：第一人提交进入待审状态，第二人审批通过后才生效；2. 变更生效后向安全运营告警群发送通知；3. 角色映射表保留 30 天变更历史供审计。

#### Verification

1. 集成测试单人提交 admin 角色映射变更应处于待审状态；2. 第二人审批后变更生效且告警群收到通知。

---

### FIND-15: 用户同步接口返回 PII 数据

| Attribute                  | Value                                                                                                |
| -------------------------- | ---------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                             |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                |
| CWE                        | [CWE-359](https://cwe.mitre.org/data/definitions/359.html): Exposure of Private Personal Information |
| OWASP                      | A01:2025 – Broken Access Control                                                                     |
| Exploitation Prerequisites | Authenticated User                                                                                   |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                      |
| Remediation Effort         | Low                                                                                                  |
| Mitigation Type            | Standard Mitigation                                                                                  |
| Component                  | SyncUserController                                                                                   |
| Related Threats            | [T04.1](2-stride-analysis.md#syncusercontroller)                                                     |

#### Description

`SyncUserController` 的用户列表查询接口可能返回邮箱、账号、姓名等 PII 字段，越权调用可批量获取组织内全部用户信息。攻击者据此可发起钓鱼邮件、撞库攻击或社会工程。该接口虽需 Authenticated User，但未按调用方角色分级脱敏。

#### Evidence

**Prerequisite basis:** 用户同步接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/controller/SyncUserController.java` 的用户列表查询接口直接返回 `UserBasicEntity` 全字段；`src/main/java/com/openlibing/coderepo/business/entity/space/UserBasicEntity.java` 含 `email`、`phone`、`account` 等字段。

#### Remediation

用户列表接口按调用方角色脱敏：非管理员仅返回 `userId`、`displayName`、`role` 必要字段；管理员才返回完整 PII；分页强制 pageSize 上限 100。

#### Verification

1. 集成测试普通用户调用接口确认响应不含 `email`/`phone`；2. 管理员调用返回完整字段；3. 单元测试覆盖角色脱敏逻辑。

---

### FIND-16: 批量用户同步无分页与并发限制

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling |
| OWASP                      | A04:2025 – Untrusted Data Consumption                                                                            |
| Exploitation Prerequisites | Authenticated User                                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                  |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                                              |
| Component                  | SyncUserController                                                                                               |
| Related Threats            | [T04.2](2-stride-analysis.md#syncusercontroller)                                                                 |

#### Description

批量用户同步接口接受任意规模的用户列表，无分页与单次同步上限。大组织（万级用户）一次性全量同步将造成 MySQL `user_basic` 表批量 UPSERT 锁竞争、HikariCP 连接池耗尽、Redisson 分布式锁等待超时，影响其他业务请求。

#### Evidence

**Prerequisite basis:** 同步接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/controller/SyncUserController.java` 的批量同步接口无分页参数；`src/main/java/com/openlibing/coderepo/business/service/impl/SyncUserServiceImpl.java` 的 `batchSync` 方法直接遍历 List 调用 `INSERT ON DUPLICATE KEY UPDATE`。

#### Remediation

1. 同步接口强制分页 `pageSize <= 200`；2. 单次同步上限 5000 用户，超限要求拆分；3. 大批量同步异步化，通过 `token_change_queue_beta` 削峰。

#### Verification

1. 单元测试覆盖 pageSize=201 被拒绝；2. 压测构造 5000 用户同步确认 MySQL 无连接超时。

---

### FIND-17: 用户同步接口可能接受外部 roleId 导致权限提升

| Attribute                  | Value                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                 |
| CVSS 4.0                   | 6.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                     |
| CWE                        | [CWE-269](https://cwe.mitre.org/data/definitions/269.html): Improper Privilege Management |
| OWASP                      | A01:2025 – Broken Access Control                                                          |
| Exploitation Prerequisites | Authenticated User                                                                        |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                           |
| Remediation Effort         | Medium                                                                                    |
| Mitigation Type            | Custom Mitigation                                                                         |
| Component                  | SyncUserController                                                                        |
| Related Threats            | [T04.3](2-stride-analysis.md#syncusercontroller)                                          |

#### Description

`SyncUserController` 的角色分配接口若直接接受请求体中的 `roleId` 并写入 `user_role_info` 表，未校验调用方权限是否高于目标角色，普通用户即可为自己或他人注入 admin 角色 ID 实现权限提升。

#### Evidence

**Prerequisite basis:** 同步接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/controller/SyncUserController.java` 的角色分配方法接收 `roleId` 参数；`src/main/java/com/openlibing/coderepo/business/service/impl/SyncUserServiceImpl.java` 直接将 `roleId` 写入 `user_role_info` 表，无调用方 vs 目标角色等级校验。

#### Remediation

角色分配时校验调用方角色等级严格高于目标角色（如调用方为 admin 才能分配 admin 角色，但禁止分配 superadmin）；禁止平级授权（admin 不能给另一用户授予 admin 角色）；超权授权尝试告警。

#### Verification

1. 集成测试普通用户尝试为自己分配 admin 角色应返回 403；2. admin 用户给普通用户分配 admin 角色应被拒绝；3. superadmin 才能分配 admin 角色。

---

### FIND-18: MongoDB 查询参数若字符串拼接存在 NoSQL 注入

| Attribute                  | Value                                                                                                                       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                   |
| CVSS 4.0                   | 6.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                                       |
| CWE                        | [CWE-943](https://cwe.mitre.org/data/definitions/943.html): Improper Neutralization of Special Elements in Data Query Logic |
| OWASP                      | A03:2025 – Injection                                                                                                        |
| Exploitation Prerequisites | Authenticated User                                                                                                          |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                             |
| Remediation Effort         | Medium                                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                                         |
| Component                  | CodeMetricsController                                                                                                       |
| Related Threats            | [T05.1](2-stride-analysis.md#codemetricscontroller), [T10.1](2-stride-analysis.md#mongodb)                                  |

#### Description

`CodeMetricsServiceImpl` 的 MongoDB 查询若将用户输入字符串拼接到查询 JSON（如 `{$where: "this.field == '" + userInput + "'"}` 或 `BasicDBObject.put("field", userInput)` 后 `JSON.parse`），存在 NoSQL 注入风险。攻击者构造 `{$ne: null}`、`{$gt: ""}` 等条件可绕过权限过滤读取全集合数据，或通过 `$where` 触发 JS 引擎执行造成 OOM。

#### Evidence

**Prerequisite basis:** 度量查询接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java` 的查询方法；`src/main/java/com/openlibing/coderepo/business/mapper/CodeMetricsMapper.java`（如有）的查询构建；需审查是否存在字符串拼接查询 JSON 的代码。

#### Remediation

使用 Spring Data MongoDB 的 `Query`/`Criteria` 类型安全构建器，禁止 `JSON.parseObject` 拼接查询；`$where` 操作符全量禁用；输入字段类型校验（如 `commitSha` 仅允许 `[0-9a-f]{40}`）。

#### Verification

1. 静态扫描（SpotBugs + findsecbugs）确认无 `JSON.parseObject` 拼接查询；2. 集成测试构造 `{$ne: null}` 注入应被类型校验拒绝。

---

### FIND-19: 代码度量与文件详情查询存在 IDOR 与源代码泄露

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                    |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N)                                        |
| CWE                        | [CWE-639](https://cwe.mitre.org/data/definitions/639.html): Authorization Bypass Through User-Controlled Key |
| OWASP                      | A01:2025 – Broken Access Control                                                                             |
| Exploitation Prerequisites | Authenticated User                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                              |
| Remediation Effort         | Medium                                                                                                       |
| Mitigation Type            | Custom Mitigation                                                                                            |
| Component                  | CodeMetricsController                                                                                        |
| Related Threats            | [T05.2](2-stride-analysis.md#codemetricscontroller), [T05.3](2-stride-analysis.md#codemetricscontroller)     |

#### Description

`CodeMetricsController` 的文件详情接口接收任意 `repoId`/`fileId` 参数返回源代码内容片段，但未校验调用方对该仓库的访问权限。攻击者构造任意 `repoId` 即可越权读取他人仓库的源代码片段（含算法实现、配置、注释中的密钥提示），同时也可越权查询他人仓库的度量数据（如重复块、复杂度热点），作为商业情报或后续攻击的情报收集。

#### Evidence

**Prerequisite basis:** 度量查询接口经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

`src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java` 的 `file-detail` 接口签名仅含 `fileId`/`repoId`；`src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java` 直接按 ID 查询 MongoDB `code_metrics_file_detail` 集合，无 projectId 联合校验。

#### Remediation

文件详情接口增加 `projectId` 参数，先校验调用方对该 `projectId` 的角色，非项目成员拒绝返回；源代码片段仅返回行号范围与度量值，不返回源码原文（如需展示源码，仅返回前 5 行 + 度量标注）。

#### Verification

1. 集成测试用户 A 调用用户 B 项目下的 `file-detail` 应返回 403；2. 审查接口响应 DTO 确认无 `sourceCode` 字段原文。

---

### FIND-20: GitHub Token 不校验有效性硬编码返回 true

| Attribute                  | Value                                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                  |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                      |
| CWE                        | [CWE-1189](https://cwe.mitre.org/data/definitions/1189.html): Improper Isolation of Inter-Process Resource |
| OWASP                      | A07:2025 – Identification and Authorization Failures                                                       |
| Exploitation Prerequisites | Authenticated User                                                                                         |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                            |
| Remediation Effort         | Low                                                                                                        |
| Mitigation Type            | Standard Mitigation                                                                                        |
| Component                  | PrAccessTokenServiceImpl                                                                                   |
| Related Threats            | [T06.1](2-stride-analysis.md#praccesstokenserviceimpl), [T15.1](2-stride-analysis.md#github)               |

#### Description

`PrAccessTokenServiceImpl.isTokenValid` 对 GitHub 平台硬编码 `if ("github".equals(platform)) return true;`，不调用 GitHub API 校验 token 有效性。失效、被撤销或权限被降级的 GitHub token 仍被使用，可能导致 PR 操作触发 GitHub 401 异常被 GitHub 侧告警为可疑账号活动，甚至触发 GitHub 自动封禁，影响业务连续性。注释称"GitHub 无 /api/v5/user 接口"，但 GitHub 实际有 `/user` 接口可用于校验。

#### Evidence

**Prerequisite basis:** PrAccessTokenServiceImpl 为内部服务（Reachability=No Listener, Min Prerequisite=Local Process Access），但调用方 WebhookEventConsumer 经 RabbitMQ 消费处理外部 webhook 事件，故调整为 Authenticated User。

`src/main/java/com/openlibing/coderepo/business/service/impl/PrAccessTokenServiceImpl.java:184-185`:

```java
if ("github".equals(platform)) {
  return true;
}
```

GitHub REST API 实际有 `/user` 接口（https://api.github.com/user）可校验 token。

#### Remediation

GitHub token 同样调用 `https://api.github.com/user` 校验，缓存结果到 Redis（key=`webhook:token:valid:github:{sha256(token)}`，TTL 10 分钟）；捕获 401 后标记 token 失效并告警。

#### Verification

1. 单元测试覆盖 GitHub token 校验调用 GitHub API；2. 集成测试用失效 token 调用确认返回 false 并告警。

---

### FIND-21: Token 缓存 key 使用 hashCode 存在碰撞绕过校验风险

| Attribute                  | Value                                                                                                                            |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                        |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                                            |
| CWE                        | [CWE-328](https://cwe.mitre.org/data/definitions/328.html): Use of Weak Hash                                                     |
| OWASP                      | A02:2025 – Cryptographic Failures                                                                                                |
| Exploitation Prerequisites | Authenticated User                                                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                                  |
| Remediation Effort         | Low                                                                                                                              |
| Mitigation Type            | Standard Mitigation                                                                                                              |
| Component                  | PrAccessTokenServiceImpl                                                                                                         |
| Related Threats            | [T06.2](2-stride-analysis.md#praccesstokenserviceimpl), [T11.1](2-stride-analysis.md#redis), [T11.2](2-stride-analysis.md#redis) |

#### Description

`PrAccessTokenServiceImpl.isTokenValid` 与 Redis 缓存 key 使用 `accessToken.hashCode()`，Java String `hashCode` 为 32 位整数且分布不均，存在碰撞风险。攻击者构造碰撞 token（仅前 32 位匹配）可继承合法 token 的"有效"缓存结果，绕过 token 有效性校验，使用伪造 token 调用 GitCode/Gitee/GitHub API 进行 PR 评论等操作。Redis 数据在内存中明文存储，配合 hashCode key 暴力枚举可放大攻击面。

#### Evidence

**Prerequisite basis:** PrAccessTokenServiceImpl 为内部服务（Reachability=No Listener, Min Prerequisite=Local Process Access），但经 WebhookEventConsumer 间接触发于外部 webhook 事件，故调整为 Authenticated User。

`src/main/java/com/openlibing/coderepo/business/service/impl/PrAccessTokenServiceImpl.java:188`:

```java
String cacheKey = TOKEN_VALID_CACHE_PREFIX + platform + ":" + accessToken.hashCode();
```

Java String.hashCode() 返回 int（32 位），约 4G 空间，存在已知碰撞算法。

#### Remediation

缓存 key 改用 `SHA-256(token)` 前 16 字节十六进制（128 位空间，碰撞概率可忽略）；缓存值仍为 `"1"/"0"` 不含明文 token；Redis 启用 ACL 区分读写权限（与 FIND-33 协同）。

#### Verification

1. 单元测试构造已知碰撞字符串验证新 key 不碰撞；2. 审查代码确认所有 token 缓存 key 使用 SHA-256；3. Redis 配置启用 ACL。

---

### FIND-22: Token 校验失败 WARN 日志可能泄露 Token 片段

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                                     |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                        |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP                      | A09:2025 – Security Logging and Monitoring Failures                                                          |
| Exploitation Prerequisites | Authenticated User                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                              |
| Remediation Effort         | Low                                                                                                          |
| Mitigation Type            | Standard Mitigation                                                                                          |
| Component                  | PrAccessTokenServiceImpl                                                                                     |
| Related Threats            | [T06.3](2-stride-analysis.md#praccesstokenserviceimpl)                                                       |

#### Description

`PrAccessTokenServiceImpl.isTokenValid` 在 token 校验失败时通过 `LOGGER.warn` 输出失败原因，若异常消息或参数包含 token 片段（如 `HTTP 401 for token ghp_xxxx...`），多次失败日志聚合可还原 token 模式。结合 FIND-03 的 webhook 路径日志问题，整体日志脱敏链路需统一加固。

#### Evidence

**Prerequisite basis:** PrAccessTokenServiceImpl 为内部服务（Reachability=No Listener, Min Prerequisite=Local Process Access），但调用方为处理外部 webhook 事件的 Consumer，故调整为 Authenticated User。

`src/main/java/com/openlibing/coderepo/business/service/impl/PrAccessTokenServiceImpl.java` 的 `LOGGER.warn` 调用可能包含异常消息（HTTP 响应体、URL 等）。

#### Remediation

token 在日志中一律脱敏为 `token:***` 或保留前 4 后 4 字符的掩码；仅记录校验结果（success/fail）与平台名；异常消息先经过 `SensitiveDataConverter` 过滤后再输出。

#### Verification

1. 触发 token 校验失败场景，grep 日志确认无 token 片段；2. 启用 `SensitiveDataConverter` 覆盖 PrAccessTokenServiceImpl 的 logger。

---

### FIND-23: Redis 不可用时 fallback 调用外部 API 可造成限流耗尽

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-754](https://cwe.mitre.org/data/definitions/754.html): Improper Check for Unusual or Exceptional Conditions |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                             |
| Exploitation Prerequisites | Authenticated User                                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                  |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Custom Mitigation                                                                                                |
| Component                  | PrAccessTokenServiceImpl                                                                                         |
| Related Threats            | [T06.4](2-stride-analysis.md#praccesstokenserviceimpl)                                                           |

#### Description

`PrAccessTokenServiceImpl.isTokenValid` 在 Redis 不可用时 fallback 直接调用 GitCode/Gitee API 校验 token，高频 webhook 事件可造成 GitCode/Gitee API 限流（429），导致后续合法 PR 操作失败。Redis 故障期间应用的降级策略应 fail-closed 而非 fail-open，避免单点故障引发下游平台 API 被打爆。

#### Evidence

**Prerequisite basis:** PrAccessTokenServiceImpl 为内部服务（Min Prerequisite=Local Process Access），但调用方为处理外部 webhook 事件的 Consumer，故调整为 Authenticated User。

`src/main/java/com/openlibing/coderepo/business/service/impl/PrAccessTokenServiceImpl.java` 的 `isTokenValid` 在 `openlibingRedis.get(cacheKey)` 抛异常或返回 null 时直接调用 GitCode/Gitee API。

#### Remediation

Redis 不可用时直接拒绝 webhook 处理（fail-closed）：抛 `TokenCacheUnavailableException`，Consumer 捕获后消息重入队列延迟消费，等待 Redis 恢复；同时 Redis 不可用事件告警运维。

#### Verification

1. 集成测试 mock Redis 不可用，确认 webhook 事件被延迟重消费而非直接调用 GitCode API；2. 监控告警确认 Redis 不可用事件触发告警。

---

### FIND-24: MyBatis Mapper 若使用 ${} 拼接存在 SQL 注入

| Attribute                  | Value                                                                                                                        |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                    |
| CVSS 4.0                   | 6.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                                        |
| CWE                        | [CWE-89](https://cwe.mitre.org/data/definitions/89.html): Improper Neutralization of Special Elements used in an SQL Command |
| OWASP                      | A03:2025 – Injection                                                                                                         |
| Exploitation Prerequisites | Internal Network                                                                                                             |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                              |
| Remediation Effort         | Medium                                                                                                                       |
| Mitigation Type            | Standard Mitigation                                                                                                          |
| Component                  | WebhookEventConsumer                                                                                                         |
| Related Threats            | [T07.1](2-stride-analysis.md#webhookeventconsumer), [T09.1](2-stride-analysis.md#mysql)                                      |

#### Description

`WebhookEventConsumer` 消费 webhook 事件后，事件 body 经 `JSON.parseObject` 解析的字段直接传入 MyBatis mapper 作为查询参数。若 mapper XML 存在 `${}` 拼接（如动态表名、ORDER BY 字段、LIKE 模式），攻击者通过 webhook body 字段注入 SQL 片段，造成数据泄露/篡改/删除。MySQL 端也存在同类问题（T09.1），需统一审计所有 mapper XML。

#### Evidence

**Prerequisite basis:** WebhookEventConsumer 从 RabbitMQ 队列消费（Reachability=Internal Only, Min Prerequisite=Internal Network），需内网访问 RabbitMQ 队列。

`src/main/java/com/openlibing/coderepo/business/handler/MergeRequestEventHandler.java` 等处理器将 webhook body 字段传入 mapper；`src/main/resources/mapper/*.xml` 需审查所有 `${}` 用法。

#### Remediation

1. 审计所有 mapper XML，`${}` 仅用于安全白名单字段（如表名、列名）并强制白名单校验；用户输入一律 `#{}` 参数化；2. webhook body 字段在传入 mapper 前做白名单校验（如 `repoUrl` 仅允许 `gitcode.com/gitee.com/github.com` 域名 + 字符长度上限）；3. 启用 MyBatis 的 `safeUpdates` 与 `sqlInjectionBlackList` 拦截器。

#### Verification

1. grep 所有 mapper XML 确认 `${}` 仅用于白名单字段；2. findsecbugs 静态扫描无 SQL 注入告警；3. 集成测试构造 webhook body 含 `' OR 1=1 --` 应被拒绝或参数化转义。

---

### FIND-25: Webhook 事件处理异常栈与 body 写入 MongoDB 日志

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                                     |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                        |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP                      | A09:2025 – Security Logging and Monitoring Failures                                                          |
| Exploitation Prerequisites | Internal Network                                                                                             |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                              |
| Remediation Effort         | Low                                                                                                          |
| Mitigation Type            | Standard Mitigation                                                                                          |
| Component                  | WebhookEventConsumer                                                                                         |
| Related Threats            | [T07.2](2-stride-analysis.md#webhookeventconsumer), [T10.2](2-stride-analysis.md#mongodb)                    |

#### Description

`WebhookEventConsumer` 处理 webhook 事件失败时将异常栈与 body 内容写入 MongoDB `operation_log` 集合，body 可能含仓库 URL、提交者账号、PR 标题、commit message 等敏感数据。MongoDB 单账号访问无行级权限控制（见 FIND-32），越权查询 MongoDB 日志集合即可批量获取敏感数据。

#### Evidence

**Prerequisite basis:** WebhookEventConsumer 从 RabbitMQ 队列消费（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/business/handler/*.java` 的异常处理 `LOGGER.error(e.getMessage(), e)` + body 内容；`src/main/java/com/openlibing/coderepo/business/service/impl/OperationLogServiceImpl.java` 将日志写入 MongoDB `operation_log` 集合。

#### Remediation

异常日志中 body 内容按字段白名单记录（仅记录 `eventType`、`deliveryId`、`repoUrl` 域名部分），其余字段（commitMessage、author、PR title）脱敏；异常栈仅记录类名与首行，不输出完整栈。

#### Verification

1. 集成测试触发异常，查询 MongoDB `operation_log` 确认 body 字段已脱敏；2. 单元测试覆盖字段白名单逻辑。

---

### FIND-26: Consumer 调用平台 PR API 无限流可触发 429 阻断合法操作

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling |
| OWASP                      | A04:2025 – Untrusted Data Consumption                                                                            |
| Exploitation Prerequisites | Internal Network                                                                                                 |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                  |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                                              |
| Component                  | WebhookEventConsumer                                                                                             |
| Related Threats            | [T07.3](2-stride-analysis.md#webhookeventconsumer), [T13.2](2-stride-analysis.md#gitcode)                        |

#### Description

`WebhookEventConsumer` 在处理 PR 事件时调用 GitCode/Gitee/Github PR API（如 `/repos/{owner}/{repo}/pulls/{number}/comments`）无应用层限流。高频 webhook 事件可触发平台 API 限流（429），导致后续合法 PR 评论/标签操作失败。GitCode 端也有同类问题（T13.2）。

#### Evidence

**Prerequisite basis:** WebhookEventConsumer 从 RabbitMQ 队列消费（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/business/handler/MergeRequestEventHandler.java` 调用 `GitCode.createPrComment`/`Gitee.createPrComment`/`Github.createPrComment` 无速率限制。

#### Remediation

消费者侧增加令牌桶限流（单平台每秒 10 次调用上限），429 时指数退避重试（最多 3 次），最终失败消息入死信队列；平台 API 调用增加幂等键避免重复评论。

#### Verification

1. 压测构造 100 PR 事件，确认 GitCode API 调用速率被令牌桶限制；2. mock 429 响应确认指数退避。

---

### FIND-27: Webhook body 反序列化无大小校验可造成 OOM

| Attribute                  | Value                                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                      |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                         |
| CWE                        | [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption |
| OWASP                      | A04:2025 – Untrusted Data Consumption                                                         |
| Exploitation Prerequisites | Internal Network                                                                              |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                               |
| Remediation Effort         | Low                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                           |
| Component                  | WebhookEventConsumer                                                                          |
| Related Threats            | [T07.4](2-stride-analysis.md#webhookeventconsumer)                                            |

#### Description

`WebhookEventConsumer` 消费 RabbitMQ 消息时，body 大小仅在 APIG 层限制（默认 16MB），消费者侧反序列化大 JSON 时无前置校验，可造成 JVM 堆 OOM。攻击者（或平台侧重发积累）投递大 body 消息，消费者 `JSON.parseObject(body)` 一次性加载到内存，触发 OOM 后整个 Consumer 进程崩溃。

#### Evidence

**Prerequisite basis:** WebhookEventConsumer 从 RabbitMQ 队列消费（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/business/consumer/WebhookEventConsumer.java` 的 `@RabbitListener` 方法直接 `JSON.parseObject(body)` 无大小校验；RabbitMQ `webhook_event_queue_beta` 队列无 `max-length` 配置。

#### Remediation

1. Consumer 侧前置 `body.length() > 1_000_000`（1MB）校验，超限直接死信；2. RabbitMQ 队列配置 `x-max-length: 10000` 与 `x-dead-letter-exchange`；3. `JSON.parseObject` 改为流式解析或限制最大字段数。

#### Verification

1. 集成测试投递 2MB body 消息确认被死信；2. 压测构造 1 万条消息确认队列超长后转死信。

---

### FIND-28: Consumer 事件处理无幂等去重造成 PR 噪音与配额浪费

| Attribute                  | Value                                                                                          |
| -------------------------- | ---------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                       |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:N/SI:L/SA:N)                          |
| CWE                        | [CWE-1290](https://cwe.mitre.org/data/definitions/1290.html): Inadequate Delivery Verification |
| OWASP                      | A04:2025 – Untrusted Data Consumption                                                          |
| Exploitation Prerequisites | Internal Network                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                |
| Remediation Effort         | Medium                                                                                         |
| Mitigation Type            | Custom Mitigation                                                                              |
| Component                  | WebhookEventConsumer                                                                           |
| Related Threats            | [T07.5](2-stride-analysis.md#webhookeventconsumer), [T12.3](2-stride-analysis.md#rabbitmq)     |

#### Description

`WebhookEventConsumer` 消费事件时未基于 `X-GitCode-Delivery`/`X-GitHub-Delivery` + 事件类型做幂等去重，RabbitMQ 消息重投（如消费失败重试、平台侧重发）可触发重复 PR 评论、重复标签、重复流水线记录，造成 PR 噪音与平台 API 配额浪费。该问题与 FIND-02（Controller 侧去重缺失）共同放大重放影响，与 FIND-34（RabbitMQ 未签名消息）共同放大伪造消息影响。

#### Evidence

**Prerequisite basis:** WebhookEventConsumer 从 RabbitMQ 队列消费（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/business/consumer/WebhookEventConsumer.java` 的 `@RabbitListener` 方法直接调用 handler，无 Redis SET NX 幂等校验。

#### Remediation

Consumer 入口基于 `deliveryId + eventType + action` 计算 SHA-256 作为幂等 key，Redis SET NX TTL 1 小时，写入失败视为重复事件直接 ACK 但不处理；PR 评论/标签操作前再次校验 `commentIdempotencyKey`（如 `pr:{repo}:{prNumber}:{action}`）。

#### Verification

1. 集成测试投递同一 delivery ID 两次，确认仅处理一次；2. mock PR 评论 API 调用次数确认幂等。

---

### FIND-29: XXL-Job 执行器与调度中心 token 泄露可触发任意任务

| Attribute                  | Value                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                        |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                            |
| CWE                        | [CWE-522](https://cwe.mitre.org/data/definitions/522.html): Insufficiently Protected Credentials |
| OWASP                      | A07:2025 – Identification and Authorization Failures                                             |
| Exploitation Prerequisites | Internal Network                                                                                 |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                  |
| Remediation Effort         | Medium                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                              |
| Component                  | XxlJobHandler                                                                                    |
| Related Threats            | [T08.1](2-stride-analysis.md#xxljobhandler), [T17.1](2-stride-analysis.md#xxljob)                |

#### Description

`XxlJobHandler` 通过 XXL-Job SDK 与调度中心通信，仅靠执行器 token 鉴权。token 泄露后攻击者可伪装为调度中心触发任意定时任务（如全量仓库同步、Token 轮换），在非调度时间执行同步任务造成 MySQL 与平台 API 压力，或触发 Token 轮换将 token 替换为攻击者控制值。XXLJob 端也存在同类问题（T17.1）。

#### Evidence

**Prerequisite basis:** XxlJobHandler 为内部执行器（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/common/config/XxlJobConfig.java` 的执行器 token 配置（来自 Apollo `xxl.job.access.token`）；XXL-Job SDK 默认无 mTLS。

#### Remediation

1. 执行器 token 定期轮换（30 天）；2. 执行器与调度中心双向 mTLS 认证（XXL-Job 3.x 支持 SSL）；3. 调度中心启用 IP 白名单仅允许执行器注册的 IP；4. 关键任务（Token 轮换）执行前再次校验调度来源签名。

#### Verification

1. 审查 XxlJobConfig 确认 token 来自环境变量而非配置文件明文；2. mTLS 配置生效；3. 集成测试用伪造 token 调用执行器应被拒绝。

---

### FIND-30: XXL-Job 任务参数未做白名单校验存在超范围数据同步

| Attribute                  | Value                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                           |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)               |
| CWE                        | [CWE-20](https://cwe.mitre.org/data/definitions/20.html): Improper Input Validation |
| OWASP                      | A03:2025 – Injection                                                                |
| Exploitation Prerequisites | Internal Network                                                                    |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                     |
| Remediation Effort         | Medium                                                                              |
| Mitigation Type            | Custom Mitigation                                                                   |
| Component                  | XxlJobHandler                                                                       |
| Related Threats            | [T08.2](2-stride-analysis.md#xxljobhandler), [T17.2](2-stride-analysis.md#xxljob)   |

#### Description

`XxlJobHandler` 接收调度中心下发的任务参数（JSON），若接受任意 `repoIdList` 或 `pageSize` 字段，恶意调度可注入超范围仓库 ID（同步他人项目仓库）或大分页参数（触发全量数据同步导致 MySQL 过载与数据泄露）。XXLJob 端也有同类问题（T17.2）。

#### Evidence

**Prerequisite basis:** XxlJobHandler 为内部执行器（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java` 的 `@XxlJob` 方法直接 `JSON.parseObject(param)` 取 `repoIdList` 与 `pageSize`，无白名单校验。

#### Remediation

1. 任务参数白名单校验：`repoIdList` 必须为应用所配置的项目下的仓库 ID；`pageSize` 上限 1000；2. 超范围仓库 ID 直接抛异常并告警；3. 全量同步任务（无 repoIdList）需 Apollo 开关显式开启才允许执行。

#### Verification

1. 集成测试注入他人项目仓库 ID 应被拒绝；2. `pageSize=1001` 应被拒绝；3. 全量同步任务在开关关闭时不应执行。

---

### FIND-31: 全量仓库同步任务无分页与并发限制

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling |
| OWASP                      | A04:2025 – Untrusted Data Consumption                                                                            |
| Exploitation Prerequisites | Internal Network                                                                                                 |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                  |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                                              |
| Component                  | XxlJobHandler                                                                                                    |
| Related Threats            | [T08.3](2-stride-analysis.md#xxljobhandler)                                                                      |

#### Description

`XxlJobHandler` 的全量仓库同步任务（分支刷新、Token 轮换）无分页与并发限制，大批量仓库（万级）一次性同步将造成 MySQL 批量 UPSERT 锁竞争、HikariCP 连接池耗尽、平台 API 限流。

#### Evidence

**Prerequisite basis:** XxlJobHandler 为内部执行器（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java` 的全量同步任务直接 `repoInfoMapper.selectAll()` 加载所有仓库到内存，循环调用 GitCode/Gitee/Github API。

#### Remediation

1. 同步任务强制分页（pageSize=200）；2. 单次同步上限 5000 仓库，超限拆分多个任务；3. 平台 API 调用限流（令牌桶，单平台每秒 10 次）。

#### Verification

1. 集成测试 mock 1 万仓库，确认任务分 50 页执行；2. 监控 MySQL 连接池与平台 API 调用速率。

---

### FIND-32: MySQL 单账号无行级权限控制存在越权读取风险

| Attribute                  | Value                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                 |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)                                    |
| CWE                        | [CWE-732](https://cwe.mitre.org/data/definitions/732.html): Incorrect Permission Assignment for Resource |
| OWASP                      | A01:2025 – Broken Access Control                                                                         |
| Exploitation Prerequisites | Internal Network                                                                                         |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                          |
| Remediation Effort         | High                                                                                                     |
| Mitigation Type            | Custom Mitigation                                                                                        |
| Component                  | MySQL                                                                                                    |
| Related Threats            | [T09.3](2-stride-analysis.md#mysql)                                                                      |

#### Description

MySQL 数据库为单账号访问，无行级权限控制（RLS），任何已认证应用请求可读取全表数据。若应用层 service 未强制 `projectId` + 用户角色过滤（见 FIND-09、FIND-19），数据库层无法兜底阻止越权读取。仓库元数据、用户 PII、Token 密文均暴露给任意应用层调用。

#### Evidence

**Prerequisite basis:** MySQL 为云数据库内网访问（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/common/config/DataSourceConfig.java` 配置单一数据库账号；MySQL 表无 `ROW LEVEL SECURITY` 或视图隔离。

#### Remediation

1. 应用层 service 强制 `projectId` + 用户角色过滤（覆盖所有查询方法）；2. 敏感表（`repo_info.access_token`、`user_basic.phone`）建立视图，应用账号仅授权视图；3. 长期方案：MySQL 8 企业版启用 RLS 或迁移到 PostgreSQL 启用 RLS。

#### Verification

1. 审查所有 service 查询方法确认 `projectId` 过滤；2. 数据库账号权限审计确认仅授权必要视图；3. 集成测试用普通用户 token 调用接口确认无越权返回。

---

### FIND-33: Redis 单密码认证无 ACL 可恶意释放分布式锁

| Attribute                  | Value                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                 |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)                                    |
| CWE                        | [CWE-732](https://cwe.mitre.org/data/definitions/732.html): Incorrect Permission Assignment for Resource |
| OWASP                      | A01:2025 – Broken Access Control                                                                         |
| Exploitation Prerequisites | Internal Network                                                                                         |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                          |
| Remediation Effort         | Medium                                                                                                   |
| Mitigation Type            | Standard Mitigation                                                                                      |
| Component                  | Redis                                                                                                    |
| Related Threats            | [T11.3](2-stride-analysis.md#redis)                                                                      |

#### Description

Redis 启用密码认证但无 ACL，任何获知密码的客户端可读写全部 key，包括 Redisson 分布式锁 key（如 `distributed:lock:syncJob:repoId123`）。攻击者恶意释放他人持有的分布式锁，可造成同步任务重复执行（多副本同时跑同一仓库同步），引发数据竞争与平台 API 重复调用。

#### Evidence

**Prerequisite basis:** Redis 为云缓存内网访问且启用 SSL 与密码认证（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/common/config/RedisConfig.java` 仅配置密码；Redisson 客户端默认无 ACL 隔离。

#### Remediation

Redis 6+ 启用 ACL：缓存 key（`webhook:token:valid:*`）使用 `cache_user` 账号（仅读写缓存 key 前缀），分布式锁 key（`distributed:lock:*`）使用 `lock_user` 账号（仅允许 lock/unlock 命令），应用按需切换连接。

#### Verification

1. Redis `ACL LIST` 确认多账号配置；2. 集成测试用 `cache_user` 尝试 `DEL distributed:lock:*` 应被拒绝；3. Redisson 配置确认按业务区分连接。

---

### FIND-34: RabbitMQ 消息未签名可伪造 webhook 事件投递

| Attribute                  | Value                                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                   |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:N/SI:L/SA:N)                                      |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                            |
| Exploitation Prerequisites | Internal Network                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                            |
| Remediation Effort         | Medium                                                                                                     |
| Mitigation Type            | Custom Mitigation                                                                                          |
| Component                  | RabbitMQ                                                                                                   |
| Related Threats            | [T12.1](2-stride-analysis.md#rabbitmq), [T12.2](2-stride-analysis.md#rabbitmq)                             |

#### Description

RabbitMQ 队列写权限未严格隔离（任何有 RabbitMQ 写权限的客户端均可投递），且消息体未签名。攻击者可绕过 Controller 直接向 `webhook_event_queue_beta` 投递伪造的 webhook 事件消息，Consumer 处理时触发 PR 评论/标签等副作用操作，绕过 Controller 的签名校验防线。配合 FIND-28（Consumer 无幂等）可放大伪造消息影响。队列无消息速率限制，恶意生产者可投递大量无效消息造成队列堆积与消费者 OOM（与 FIND-04、FIND-27 共同形成完整 DoS 链）。

#### Evidence

**Prerequisite basis:** RabbitMQ 为云消息队列内网访问（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/java/com/openlibing/coderepo/common/config/RabbitMQConfig.java` 队列配置无 `x-message-ttl`、`x-max-length`、`x-dead-letter-exchange`；消息体未增加签名头。

#### Remediation

1. 队列写权限仅授予 WebHookEventController 服务账号（RabbitMQ 端配置 `write` 权限限定 username）；2. 消息体增加 `X-Message-Signature` HMAC 头，Consumer 入口校验签名后才处理；3. 队列配置 `x-max-length: 10000` + `x-dead-letter-exchange: webhook.dlx`，超限消息转死信。

#### Verification

1. RabbitMQ `rabbitmqctl list_permissions` 确认队列写权限仅 controller 服务账号；2. 集成测试无签名消息应被 Consumer 拒绝；3. 压测投递 1.1 万消息确认超限转死信。

---

### FIND-35: 仓库导出产物 OBS Bucket 策略宽松未授权可读

| Attribute                  | Value                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:H/SI:N/SA:N)                                    |
| CWE                        | [CWE-732](https://cwe.mitre.org/data/definitions/732.html): Incorrect Permission Assignment for Resource |
| OWASP                      | A01:2025 – Broken Access Control                                                                         |
| Exploitation Prerequisites | Authenticated User                                                                                       |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                          |
| Remediation Effort         | Medium                                                                                                   |
| Mitigation Type            | Custom Mitigation                                                                                        |
| Component                  | OBS                                                                                                      |
| Related Threats            | [T18.2](2-stride-analysis.md#obs)                                                                        |

#### Description

仓库导出产物上传到 OBS bucket `openlibing-export-beta`，若 bucket 策略为公开读或预签名 URL TTL 过长（如 24 小时），未授权用户可枚举或猜测对象 key 读取他人导出文件（含仓库元数据、commit 信息、可能的源代码片段）。

#### Evidence

**Prerequisite basis:** OBS 经 HTTPS 对外暴露（Reachability=External, Min Prerequisite=Authenticated User），bucket 策略需审查。

`src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java` 的导出方法调用 OBS 上传后生成预签名 URL；OBS bucket `openlibing-export-beta` 策略需在华为云控制台审查。

#### Remediation

1. bucket 策略设为私有（拒绝公开读）；2. 预签名 URL TTL 缩短为 1 小时；3. 对象 key 含随机 UUID 防枚举（`{projectId}/{userId}/{uuid}.{ext}`）；4. 敏感导出文件下载前再次校验调用方权限。

#### Verification

1. 华为云 OBS 控制台确认 bucket 策略为私有；2. 集成测试生成预签名 URL 后 1.5 小时访问应返回 403；3. 枚举对象 key 应被随机 UUID 阻止。

---

### FIND-36: OBS AK/SK 与应用其他凭证同源存储

| Attribute                  | Value                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                        |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                            |
| CWE                        | [CWE-522](https://cwe.mitre.org/data/definitions/522.html): Insufficiently Protected Credentials |
| OWASP                      | A02:2025 – Cryptographic Failures                                                                |
| Exploitation Prerequisites | Authenticated User                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                  |
| Remediation Effort         | Medium                                                                                           |
| Mitigation Type            | Custom Mitigation                                                                                |
| Component                  | OBS                                                                                              |
| Related Threats            | [T18.3](2-stride-analysis.md#obs)                                                                |

#### Description

OBS AK/SK 若与应用其他凭证（数据库密码、Redis 密码、Webhook secret）同源存储于 Nacos/Apollo 配置中心，配置中心被入侵后 AK/SK 即被获取，攻击者可使用该 AK/SK 覆盖或删除他人导出产物，或批量读取 bucket 内全部对象。

#### Evidence

**Prerequisite basis:** OBS 经 HTTPS 对外暴露（Reachability=External, Min Prerequisite=Authenticated User），AK/SK 由应用持有。

`src/main/java/com/openlibing/coderepo/common/config/ObsConfig.java`（或 RestTemplate 配置）从 Apollo/Nacos 读取 AK/SK；与 FIND-40（凭证集中存储）相关。

#### Remediation

1. OBS AK/SK 使用最小权限 IAM 账号（仅允许 `PutObject` 到 `openlibing-export-beta/*` 前缀，拒绝 `DeleteObject`/`ListBucket`）；2. AK/SK 从环境变量或华为云 DEW 注入而非配置中心；3. 配置中心入侵演练验证 AK/SK 不在 Nacos 配置项中。

#### Verification

1. 华为云 IAM 控制台确认 OBS 账号为最小权限；2. 审查 Apollo 配置确认无 `obs.ak`/`obs.sk` 项；3. 集成测试用最小权限账号仅能上传不能删除。

---

### FIND-37: Nacos 服务注册无双向认证可被注册恶意实例

| Attribute                  | Value                                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                  |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                      |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                            |
| Exploitation Prerequisites | Internal Network                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                            |
| Remediation Effort         | Medium                                                                                                     |
| Mitigation Type            | Standard Mitigation                                                                                        |
| Component                  | Nacos                                                                                                      |
| Related Threats            | [T16.1](2-stride-analysis.md#nacos)                                                                        |

#### Description

Nacos 服务注册若未启用双向认证，攻击者可在内网注册同名恶意实例（IP 指向攻击者控制节点），网关与上游服务的流量被路由到恶意节点，可截获调用方凭证或返回恶意响应。

#### Evidence

**Prerequisite basis:** Nacos 为云服务内网访问（Reachability=Internal Only, Min Prerequisite=Internal Network）。

`src/main/resources/application.yaml` 的 Nacos 配置 `nacos.discovery.server-addr` 与 `nacos.config.server-addr`，需审查是否启用 `nacos.discovery.auth.enabled=true` 与服务注册域名白名单。

#### Remediation

1. Nacos 启用鉴权（`nacos.core.auth.enabled=true`）；2. 服务注册时校验实例 IP 是否在内网白名单（如仅允许 K8s 节点 IP 段）；3. 网关侧定期对账服务实例列表与 K8s Pod 列表，发现未授权实例告警。

#### Verification

1. Nacos 控制台确认鉴权已启用；2. 集成测试从非白名单 IP 注册实例应被拒绝；3. 监控告警覆盖未授权实例注册事件。

---

### FIND-38: Access Token 通过 PRIVATE-TOKEN HTTP 头部传输无 HSTS 强制

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                            |
| CWE                        | [CWE-319](https://cwe.mitre.org/data/definitions/319.html): Cleartext Transmission of Sensitive Information      |
| OWASP                      | A02:2025 – Cryptographic Failures                                                                                |
| Exploitation Prerequisites | Authenticated User                                                                                               |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                  |
| Remediation Effort         | Low                                                                                                              |
| Mitigation Type            | Standard Mitigation                                                                                              |
| Component                  | GitCode                                                                                                          |
| Related Threats            | [T13.1](2-stride-analysis.md#gitcode), [T14.2](2-stride-analysis.md#gitee), [T15.2](2-stride-analysis.md#github) |

#### Description

GitCode/Gitee/GitHub 三个平台的 access token 通过 `PRIVATE-TOKEN`/`Authorization` HTTP 头部传输。若 HTTPS 连接在中间网络被劫持（如企业代理、SSL 检查设备、内网劫持工具），token 可被截获。平台侧无 HSTS 强制时，连接可能被降级为 HTTP 明文传输。

#### Evidence

**Prerequisite basis:** GitCode/Gitee/GitHub 经 HTTPS 对外暴露（Reachability=External, Min Prerequisite=Authenticated User），token 由应用持有并经 HTTP 头发送。

`src/main/java/com/openlibing/coderepo/common/utils/GitCode.java`/`Gitee.java`/`Github.java` 的 HTTP 客户端调用使用 `setHeader("PRIVATE-TOKEN", token)` 或 `Authorization: Bearer token`；HTTP 客户端配置需审查是否禁用 HTTP fallback 与中间人证书。

#### Remediation

1. HTTP 客户端禁用 HTTP fallback（仅允许 HTTPS）；2. 启用 HSTS（如平台支持）；3. 连接池禁用中间人证书（仅信任平台官方 CA）；4. 内网部署若需 SSL 检查，token 头部经应用层加密包装后再传输。

#### Verification

1. 抓包确认 HTTP 客户端仅 HTTPS 调用；2. mock HTTP URL 应被拒绝；3. 审查 HTTP 客户端配置确认 CA 信任链。

---

### FIND-39: Gitee/GitHub 端点暴露但鉴权异常

| Attribute                  | Value                                                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                        |
| CVSS 4.0                   | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)                                                           |
| CWE                        | [CWE-1188](https://cwe.mitre.org/data/definitions/1188.html): Insecure Default Initialization of Resource                       |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                                            |
| Exploitation Prerequisites | Authenticated User                                                                                                              |
| Exploitability Tier        | Tier 2 — Conditional Risk (single prerequisite)                                                                                 |
| Remediation Effort         | Low                                                                                                                             |
| Mitigation Type            | Standard Mitigation                                                                                                             |
| Component                  | WebhookEventController                                                                                                          |
| Related Threats            | [T01.7](2-stride-analysis.md#webhookeventcontroller), [T14.1](2-stride-analysis.md#gitee), [T15.1](2-stride-analysis.md#github) |

#### Description

FIND-05 已覆盖 Gitee webhook 端点暴露问题。本 finding 聚焦于 GitHub 端 token 校验缺失（T15.1）与 Gitee 端鉴权硬编码（T14.1）形成的端点暴露+鉴权异常组合：Gitee 端点暴露但全部拒绝、GitHub token 不校验，二者共同构成"功能静默失效或鉴权缺失"的配置异常，需在 APIG 路由层与代码层同步治理。

#### Evidence

**Prerequisite basis:** Gitee/GitHub webhook 端点经 APIG 对外暴露（Reachability=External, Min Prerequisite=Authenticated User）。

详见 FIND-05（Gitee 端点暴露）与 FIND-20（GitHub token 不校验）的证据。

#### Remediation

详见 FIND-05 与 FIND-20 的修复措施；本 finding 主要用于将两个相关问题统一列入修复路线图。

#### Verification

详见 FIND-05 与 FIND-20 的验证步骤。

---

## Tier 3 — Defense-in-Depth (Prior Compromise / Host Access)

### FIND-40: 敏感凭证集中存储于 Nacos 未做环境变量或 Vault 隔离

| Attribute                  | Value                                                                                                                                                               |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                           |
| CVSS 4.0                   | 6.3 (CVSS:4.0/AV:N/AC:H/AT:N/PR:H/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                                                                               |
| CWE                        | [CWE-522](https://cwe.mitre.org/data/definitions/522.html): Insufficiently Protected Credentials                                                                    |
| OWASP                      | A02:2025 – Cryptographic Failures                                                                                                                                   |
| Exploitation Prerequisites | Admin Credentials                                                                                                                                                   |
| Exploitability Tier        | Tier 3 — Defense-in-Depth (multiple prerequisites or infrastructure access)                                                                                         |
| Remediation Effort         | High                                                                                                                                                                |
| Mitigation Type            | Redesign                                                                                                                                                            |
| Component                  | Nacos                                                                                                                                                               |
| Related Threats            | [T01.2](2-stride-analysis.md#webhookeventcontroller), [T09.2](2-stride-analysis.md#mysql), [T16.2](2-stride-analysis.md#nacos), [T16.3](2-stride-analysis.md#nacos) |

#### Description

Nacos 配置中心集中存储了所有敏感凭证：数据库密码、Redis 密码、Webhook secretKey、`security.part1` 工作密钥、OBS AK/SK、平台 access token 加密密钥等。`security.part1` 作为 AES 解密工作密钥与被解密的凭证同源存储于 Nacos，一旦 Nacos 管理员账号被入侵或 Nacos 配置被篡改，攻击者可一次性获取所有凭证并解密全部密文，形成"单点失陷=全部凭证泄露"的纵深风险。Nacos 配置被篡改后还可注入恶意 `security.part1`、`webhook.secretKey` 等，使应用使用攻击者控制的密钥与凭证，且应用启动时无校验配置来源合法性。

#### Evidence

**Prerequisite basis:** Nacos 管理员账号需 Admin Credentials 才能访问配置中心（Reachability=Internal Only, Min Prerequisite=Internal Network），且 `security.part1` 与凭证同源存储需获取管理员权限才能完成完整泄露，多重前置条件故为 Tier 3。

`src/main/java/com/openlibing/coderepo/common/utils/WebhookAuthUtil.java:34-38`:

```java
@Value("${security.part1}")
private String part1;
@Value("${webhook.secretKey}")
private String webhookSecretKey;
```

`src/main/java/com/openlibing/coderepo/common/config/DataSourceConfig.java`/`RedisConfig.java`/`MongoConfig.java` 均从 Apollo/Nacos 读取凭证后调用 `SecurityUtil.decrypt(password, part1)`；`src/main/resources/application.yaml` 的 Nacos 配置项 `nacos.config.server-addr`。

#### Remediation

1. `security.part1` 工作密钥从环境变量或华为云 DEW/Vault 注入，禁止从配置中心覆盖；2. 数据库密码、Redis 密码、Webhook secret、OBS AK/SK 改用 DEW 托管，应用启动时通过 SDK 拉取；3. Nacos 仅存非敏感配置（如连接池大小、限流阈值）；4. Nacos 启用独立管理员账号 + MFA + 配置变更审计告警；5. 应用启动时校验关键配置（`security.part1`）来源为环境变量，否则拒绝启动。

#### Verification

1. 审查 Apollo/Nacos 配置项确认无明文 `security.part1`/`webhook.secretKey`/数据库密码；2. 应用启动时确认 `security.part1` 来自环境变量；3. Nacos 控制台确认 MFA 与审计已启用；4. 配置变更演练确认告警触发。

---

## Threat Coverage Verification

| Threat ID | Finding ID | Status               |
| --------- | ---------- | -------------------- |
| T01.1     | FIND-01    | ✅ Covered (FIND-01) |
| T01.2     | FIND-40    | ✅ Covered (FIND-40) |
| T01.3     | FIND-02    | ✅ Covered (FIND-02) |
| T01.4     | FIND-03    | ✅ Covered (FIND-03) |
| T01.5     | FIND-04    | ✅ Covered (FIND-04) |
| T01.6     | FIND-04    | ✅ Covered (FIND-04) |
| T01.7     | FIND-05    | ✅ Covered (FIND-05) |
| T02.1     | FIND-06    | ✅ Covered (FIND-06) |
| T02.2     | FIND-07    | ✅ Covered (FIND-07) |
| T02.3     | FIND-08    | ✅ Covered (FIND-08) |
| T02.4     | FIND-09    | ✅ Covered (FIND-09) |
| T02.5     | FIND-10    | ✅ Covered (FIND-10) |
| T03.1     | FIND-11    | ✅ Covered (FIND-11) |
| T03.2     | FIND-12    | ✅ Covered (FIND-12) |
| T03.3     | FIND-13    | ✅ Covered (FIND-13) |
| T03.4     | FIND-14    | ✅ Covered (FIND-14) |
| T04.1     | FIND-15    | ✅ Covered (FIND-15) |
| T04.2     | FIND-16    | ✅ Covered (FIND-16) |
| T04.3     | FIND-17    | ✅ Covered (FIND-17) |
| T05.1     | FIND-18    | ✅ Covered (FIND-18) |
| T05.2     | FIND-19    | ✅ Covered (FIND-19) |
| T05.3     | FIND-19    | ✅ Covered (FIND-19) |
| T06.1     | FIND-20    | ✅ Covered (FIND-20) |
| T06.2     | FIND-21    | ✅ Covered (FIND-21) |
| T06.3     | FIND-22    | ✅ Covered (FIND-22) |
| T06.4     | FIND-23    | ✅ Covered (FIND-23) |
| T07.1     | FIND-24    | ✅ Covered (FIND-24) |
| T07.2     | FIND-25    | ✅ Covered (FIND-25) |
| T07.3     | FIND-26    | ✅ Covered (FIND-26) |
| T07.4     | FIND-27    | ✅ Covered (FIND-27) |
| T07.5     | FIND-28    | ✅ Covered (FIND-28) |
| T08.1     | FIND-29    | ✅ Covered (FIND-29) |
| T08.2     | FIND-30    | ✅ Covered (FIND-30) |
| T08.3     | FIND-31    | ✅ Covered (FIND-31) |
| T09.1     | FIND-24    | ✅ Covered (FIND-24) |
| T09.2     | FIND-40    | ✅ Covered (FIND-40) |
| T09.3     | FIND-32    | ✅ Covered (FIND-32) |
| T10.1     | FIND-18    | ✅ Covered (FIND-18) |
| T10.2     | FIND-25    | ✅ Covered (FIND-25) |
| T11.1     | FIND-21    | ✅ Covered (FIND-21) |
| T11.2     | FIND-21    | ✅ Covered (FIND-21) |
| T11.3     | FIND-33    | ✅ Covered (FIND-33) |
| T12.1     | FIND-34    | ✅ Covered (FIND-34) |
| T12.2     | FIND-34    | ✅ Covered (FIND-34) |
| T12.3     | FIND-28    | ✅ Covered (FIND-28) |
| T13.1     | FIND-38    | ✅ Covered (FIND-38) |
| T13.2     | FIND-26    | ✅ Covered (FIND-26) |
| T14.1     | FIND-05    | ✅ Covered (FIND-05) |
| T14.2     | FIND-38    | ✅ Covered (FIND-38) |
| T15.1     | FIND-20    | ✅ Covered (FIND-20) |
| T15.2     | FIND-38    | ✅ Covered (FIND-38) |
| T16.1     | FIND-37    | ✅ Covered (FIND-37) |
| T16.2     | FIND-40    | ✅ Covered (FIND-40) |
| T16.3     | FIND-40    | ✅ Covered (FIND-40) |
| T17.1     | FIND-29    | ✅ Covered (FIND-29) |
| T17.2     | FIND-30    | ✅ Covered (FIND-30) |
| T18.1     | FIND-06    | ✅ Covered (FIND-06) |
| T18.2     | FIND-35    | ✅ Covered (FIND-35) |
| T18.3     | FIND-36    | ✅ Covered (FIND-36) |
