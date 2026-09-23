# Security Assessment

---

## Report Files

| File                                                       | Description                                                           |
| ---------------------------------------------------------- | --------------------------------------------------------------------- |
| [0-assessment.md](0-assessment.md)                         | This document — executive summary, risk rating, action plan, metadata |
| [0.1-architecture.md](0.1-architecture.md)                 | Architecture overview, components, scenarios, tech stack              |
| [1-threatmodel.md](1-threatmodel.md)                       | Threat model DFD diagram with element, flow, and boundary tables      |
| [1.1-threatmodel.mmd](1.1-threatmodel.mmd)                 | Pure Mermaid DFD source file                                          |
| [1.2-threatmodel-summary.mmd](1.2-threatmodel-summary.mmd) | Summary DFD for large systems                                         |
| [2-stride-analysis.md](2-stride-analysis.md)               | Full STRIDE-A analysis for all components                             |
| [3-findings.md](3-findings.md)                             | Prioritized security findings with remediation                        |
| [threat-inventory.json](threat-inventory.json)             | Machine-readable inventory of components, threats, and findings       |

---

## Executive Summary

openlibing-coderepo 是 OpenLibing 研发流程平台的代码仓管理微服务，基于 Java 21 + Spring Boot 3.4.4 构建为单一容器化进程（端口 8076），对接 GitCode/Gitee/GitHub 三大代码托管平台。该服务承担仓库元数据 CRUD、项目配置、分支同步、用户同步、代码度量采集与 Webhook 事件接入等核心能力，下游依赖 MySQL/MongoDB/Redis/RabbitMQ/Nacos/XXL-Job/华为云 OBS 等基础设施，经华为云 APIG 网关对外暴露 REST 与 Webhook 入口，所有入站流量由 APIG 代理并执行 IP 白名单与限流。

整体安全态势在容器化部署、AES 凭证加密、HMAC-SHA256 Webhook 签名、非 root 用户与 umask 0077 等基线上具备一定防护，但应用层存在多处可被已认证调用方利用的实质性缺陷：Webhook 签名比对使用 `String.equals`（非恒定时间）形成时序侧信道、GitHub 平台 token 校验硬编码返回 true、敏感 token 在 INFO 日志输出、仓库导出与代码度量查询存在 IDOR/路径遍历、Consumer 与 XXL-Job 缺乏限流与幂等等。这些问题在攻击者获得 APIG 入口访问权后即可触发，对仓库元数据机密性、PR 操作完整性与平台 API 配额构成实际威胁。

The analysis covers 20 system elements across 2 trust boundaries.

### Risk Rating: Elevated

风险评级为 **Elevated**：本仓库不存在任何 Tier 1（无需前置条件即可直接利用）的发现，外部攻击者无法在零先决条件下造成危害，整体暴露面经 APIG 收敛；但存在 1 个 Critical、20 个 Important 共 21 个中高危发现，其中 39 个 Tier 2 发现仅需"已认证用户"单一先决条件即可触发，攻击者一旦突破 APIG 网关鉴权或以合法研发人员身份调用即可批量利用。HMAC 时序攻击（FIND-01）、IDOR（FIND-09/19）、路径遍历（FIND-06）、SSRF（FIND-10）、NoSQL/SQL 注入潜在面（FIND-18/24）、GitHub token 校验硬编码绕过（FIND-20）等单点缺陷均可在已认证前提下直接导致仓库元数据泄露或被篡改，需在下一迭代前优先修复 Tier 2 中的 Critical 与 Important 项。

> **Note on threat counts:** This analysis identified 59 threats across 20 components. This count reflects comprehensive STRIDE-A coverage, not systemic insecurity. Of these, **0 are directly exploitable** without prerequisites (Tier 1). The remaining 59 represent conditional risks and defense-in-depth considerations.

---

## Action Summary

| Tier                                                                                | Description                   | Threats | Findings | Priority         |
| ----------------------------------------------------------------------------------- | ----------------------------- | ------- | -------- | ---------------- |
| [Tier 1](3-findings.md#tier-1--direct-exposure-no-prerequisites)                    | Directly exploitable          | 0       | 0        | 🔴 Critical Risk |
| [Tier 2](3-findings.md#tier-2--conditional-risk-authenticated--single-prerequisite) | Requires authenticated access | 55      | 39       | 🟠 Elevated Risk |
| [Tier 3](3-findings.md#tier-3--defense-in-depth-prior-compromise--host-access)      | Requires prior compromise     | 4       | 1        | 🟡 Moderate Risk |
| **Total**                                                                           |                               | **59**  | **40**   |                  |

### Priority by Tier and CVSS Score (Top 10)

| Finding                                                                                  | Tier | CVSS Score | SDL Severity | Title                                                    |
| ---------------------------------------------------------------------------------------- | ---- | ---------- | ------------ | -------------------------------------------------------- |
| [FIND-01](3-findings.md#find-01-webhook-hmac-sha256-签名比对使用非恒定时间-stringequals) | T2   | 7.4        | Critical     | Webhook HMAC-SHA256 签名比对使用非恒定时间 String.equals |
| [FIND-06](3-findings.md#find-06-仓库导出文件路径未严格校验存在路径遍历)                  | T2   | 6.8        | Important    | 仓库导出文件路径未严格校验存在路径遍历                   |
| [FIND-09](3-findings.md#find-09-仓库-crud-操作未校验用户对该仓库的归属权限存在-idor)     | T2   | 6.8        | Important    | 仓库 CRUD 操作未校验用户对该仓库的归属权限存在 IDOR      |
| [FIND-11](3-findings.md#find-11-sig-扫描路径配置可指向恶意仓库注入恶意配置)              | T2   | 6.8        | Important    | SIG 扫描路径配置可指向恶意仓库注入恶意配置               |
| [FIND-17](3-findings.md#find-17-用户同步接口可能接受外部-roleid-导致权限提升)            | T2   | 6.8        | Important    | 用户同步接口可能接受外部 roleId 导致权限提升             |
| [FIND-18](3-findings.md#find-18-mongodb-查询参数若字符串拼接存在-nosql-注入)             | T2   | 6.8        | Important    | MongoDB 查询参数若字符串拼接存在 NoSQL 注入              |
| [FIND-24](3-findings.md#find-24-mybatis-mapper-若使用-拼接存在-sql-注入)                 | T2   | 6.8        | Important    | MyBatis Mapper 若使用 ${} 拼接存在 SQL 注入              |
| [FIND-03](3-findings.md#find-03-敏感平台-token-在-info-日志中输出)                       | T2   | 6.5        | Important    | 敏感平台 Token 在 INFO 日志中输出                        |
| [FIND-10](3-findings.md#find-10-仓库-url-录入未校验内网地址导致-ssrf)                    | T2   | 6.5        | Important    | 仓库 URL 录入未校验内网地址导致 SSRF                     |
| [FIND-13](3-findings.md#find-13-项目级-token-查询接口可能返回明文-token)                 | T2   | 6.5        | Important    | 项目级 Token 查询接口可能返回明文 Token                  |

### Quick Wins

| Finding                                                                                  | Title                                                    | Why Quick                                                                                                           |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| [FIND-01](3-findings.md#find-01-webhook-hmac-sha256-签名比对使用非恒定时间-stringequals) | Webhook HMAC-SHA256 签名比对使用非恒定时间 String.equals | 替换为 `MessageDigest.isEqual` 一行代码即可完成恒定时间比对，修复成本极低且为唯一 Critical 风险                     |
| [FIND-03](3-findings.md#find-03-敏感平台-token-在-info-日志中输出)                       | 敏感平台 Token 在 INFO 日志中输出                        | 仓库已提供 `SensitiveDataConverter`，仅需在 webhook logger 链路启用并配置敏感头列表，无需新增组件                   |
| [FIND-13](3-findings.md#find-13-项目级-token-查询接口可能返回明文-token)                 | 项目级 Token 查询接口可能返回明文 Token                  | 返回前显式将 token 字段置为 `***` 即可，无需改库表结构                                                              |
| [FIND-20](3-findings.md#find-20-github-token-不校验有效性硬编码返回-true)                | GitHub Token 不校验有效性硬编码返回 true                 | 移除硬编码 `return true` 并复用 GitCode/Gitee 的 HTTPS 校验分支，改动局限于 `PrAccessTokenServiceImpl.isTokenValid` |
| [FIND-21](3-findings.md#find-21-token-缓存-key-使用-hashcode-存在碰撞绕过校验风险)       | Token 缓存 key 使用 hashCode 存在碰撞绕过校验风险        | 改用 SHA-256 摘要或完整 token 字符串作为 Redis key，改动局限于缓存键生成方法                                        |

---

## Analysis Context & Assumptions

### Analysis Scope

| Constraint  | Description                                                                                                                                                                   |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scope       | `d:\Develop\Java\openlibing-coderepo-fork` 仓库 `src/main/java`、`src/main/resources`、`Dockerfile`、`pom.xml` 等源码与配置；分支 `sig-path-dir-recursion`，commit `1dfaefe5` |
| Excluded    | `node_modules`、`.git`、`dist`、`build`、`target`、测试 fixture 数据文件、第三方 jar 源码、`openlibing-common`/`openlibing-test` 等外部依赖包源码                             |
| Focus Areas | Webhook 入口签名校验、仓库/项目配置 CRUD、PR access token 加解密与缓存、Webhook 消费者幂等与限流、XXL-Job 定时任务参数校验、OBS/RabbitMQ/Redis 等下游服务的鉴权与传输安全     |

### Infrastructure Context

| Category     | Discovered from Codebase                                                                                            | Findings Affected                                                                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 凭证加密     | `WebhookAuthUtil`、`SecurityUtil`、`AESCipher`、`AESUtil`（openlibing-common）；`security.part1` 工作密钥来自 Nacos | [FIND-01](3-findings.md#find-01-webhook-hmac-sha256-签名比对使用非恒定时间-stringequals), [FIND-36](3-findings.md#find-36-obs-aksk-与应用其他凭证同源存储), [FIND-40](3-findings.md#find-40-敏感凭证集中存储于-nacos-未做环境变量或-vault-隔离)      |
| 网关与边界   | 华为云 APIG 前置 IP 白名单 + 限流；应用 `0.0.0.0:8076` 仅经 APIG 暴露                                               | [FIND-04](3-findings.md#find-04-webhook-端点应用层无限流导致-cpu队列耗尽), [FIND-05](3-findings.md#find-05-gitee-webhook-端点对外暴露但鉴权硬编码拒绝), [FIND-39](3-findings.md#find-39-giteegithub-端点暴露但鉴权异常)                              |
| 缓存与锁     | Redis 3.x（`useSsl()` 非 local 启用）、Redisson 分布式锁；token 缓存 TTL 10 分钟                                    | [FIND-21](3-findings.md#find-21-token-缓存-key-使用-hashcode-存在碰撞绕过校验风险), [FIND-23](3-findings.md#find-23-redis-不可用时-fallback-调用外部-api-可造成限流耗尽), [FIND-33](3-findings.md#find-33-redis-单密码认证无-acl-可恶意释放分布式锁) |
| 容器与运行时 | `openeuler/openeuler:24.03-lts-sp1`、非 root 用户 `openlibing`、umask 0077、RASP 集成                               | [FIND-32](3-findings.md#find-32-mysql-单账号无行级权限控制存在越权读取风险), [FIND-40](3-findings.md#find-40-敏感凭证集中存储于-nacos-未做环境变量或-vault-隔离)                                                                                     |
| 静态质量门禁 | Spotless/Checkstyle/PMD/SpotBugs/findsecbugs 在 pre-commit 与 CI 强制                                               | [FIND-01](3-findings.md#find-01-webhook-hmac-sha256-签名比对使用非恒定时间-stringequals), [FIND-24](3-findings.md#find-24-mybatis-mapper-若使用-拼接存在-sql-注入)                                                                                   |

### Needs Verification

| Item                 | Question                                                                | What to Check                                                          | Why Uncertain                                              |
| -------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- |
| OBS Bucket 策略      | `openlibing-export-beta` 是否对未授权请求开放读权限                     | 在 OBS 控制台或华为云 CLI 查询 bucket policy 与 ACL                    | 仓库源码仅体现上传侧，bucket 策略不在代码仓内              |
| Nacos 双向认证       | Nacos 是否启用 `nacos.core.auth.server.identity.*` 与 mTLS              | 检查 `application.yaml` 的 `nacos.config.secure` 与部署侧 nacos 配置   | `secure: true` 仅声明 HTTPS，不等于启用双向认证            |
| APIG IP 白名单       | APIG 是否真的仅放行 GitCode/Gitee/GitHub 平台源 IP                      | 检查 APIG 实例的访问控制策略                                           | APIG 配置不在代码仓内，需在华为云控制台核对                |
| XXL-Job 执行器 token | XXL-Job 调度中心与执行器之间的 token 是否与 Access Token 不同源且足够强 | 检查 `XxlJobConfig` 与 Apollo `xxl.job.accessToken` 配置项             | token 值本身不在代码中，仅看到引用键名                     |
| MongoDB 连接 TLS     | MongoDB 客户端是否启用 TLS 与证书校验                                   | 检查 `MongoClientSettings` 与 `application.yaml` 的 `mongodb.uri` 参数 | 配置可能依赖 spring data mongodb auto-config，需运行时验证 |

### Finding Overrides

| Finding ID | Original Severity | Override | Justification                                           | New Status |
| ---------- | ----------------- | -------- | ------------------------------------------------------- | ---------- |
| —          | —                 | —        | No overrides applied. Update this section after review. | —          |

### Additional Notes

本分析未对 `openlibing-common`/`openlibing-test` 等公共依赖包源码做逐行审查，仅以 `import` 与调用方使用方式推断其安全性。涉及 `SecurityUtil.decrypt`、`AESCipher.getWorkKey`、`SensitiveDataConverter` 等公共组件的实现细节建议在公共包独立威胁模型中确认。本报告仅以本次代码仓内调用点为评估基础。

---

## References Consulted

### Security Standards

| Standard                       | URL                                                                                   | How Used                  |
| ------------------------------ | ------------------------------------------------------------------------------------- | ------------------------- |
| Microsoft SDL Bug Bar          | https://www.microsoft.com/en-us/msrc/sdlbugbar                                        | Severity classification   |
| OWASP Top 10:2025              | https://owasp.org/Top10/2025/                                                         | Threat categorization     |
| CVSS 4.0                       | https://www.first.org/cvss/v4.0/specification-document                                | Risk scoring              |
| CWE                            | https://cwe.mitre.org/                                                                | Weakness classification   |
| STRIDE                         | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats | Threat enumeration        |
| Spring Security Best Practices | https://docs.spring.io/spring-security/reference/                                     | Web 安全控制参考          |
| Redis Security Checklist       | https://redis.io/docs/management/security/                                            | Redis 凭证与 ACL 评估依据 |

### Component Documentation

| Component           | Documentation URL                                               | Relevant Section           |
| ------------------- | --------------------------------------------------------------- | -------------------------- |
| Spring AMQP         | https://docs.spring.io/spring-amqp/docs/current/reference/html/ | RabbitMQ 消费者幂等与限流  |
| Spring Data MongoDB | https://docs.spring.io/spring-data/mongodb/reference/           | NoSQL 注入防护与查询构造   |
| MyBatis             | https://mybatis.org/mybatis-3/sqlmap-xml.html                   | `${}` vs `#{}` 拼接差异    |
| XXL-Job             | https://www.xuxueli.com/xxl-job/                                | 执行器鉴权与任务参数校验   |
| 华为云 OBS          | https://support.huaweicloud.com/obs/                            | bucket policy 与预签名 URL |
| 华为云 CSE Nacos    | https://support.huaweicloud.com/cse/                            | 配置中心与服务注册安全     |

---

## Report Metadata

| Field              | Value                                                                                                                                                                |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source Location    | `d:\Develop\Java\openlibing-coderepo-fork`                                                                                                                           |
| Git Repository     | `https://gitcode.com/yanzhaohong/openlibing-coderepo.git`                                                                                                            |
| Git Branch         | `sig-path-dir-recursion`                                                                                                                                             |
| Git Commit         | `1dfaefe5` (`2026-09-02 18:51:56 +0800`)                                                                                                                             |
| Model              | `GLM-5.2`                                                                                                                                                            |
| Machine Name       | `DESKTOP-1L0N2MM`                                                                                                                                                    |
| Analysis Started   | `2026-09-02 11:02:48Z`                                                                                                                                               |
| Analysis Completed | `2026-09-02 11:12:09Z`                                                                                                                                               |
| Duration           | `00:09:21`                                                                                                                                                           |
| Output Folder      | `d:\Develop\Java\openlibing-docs\architecture_desgin\threat-models\openlibing-coderepo-fork`                                                                         |
| Prompt             | `你是一名 Threat Model Analyst 专家。请对 Java Spring Boot 仓库 d:\Develop\Java\openlibing-coderepo-fork 执行完整的 STRIDE-A 威胁建模分析（Single Analysis Mode）。` |

---

## Classification Reference

| Classification           | Values                                                                                                                                                                      |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Exploitability Tiers** | **T1** Direct Exposure (no prerequisites) · **T2** Conditional Risk (single prerequisite) · **T3** Defense-in-Depth (multiple prerequisites or infrastructure access)       |
| **STRIDE + Abuse**       | **S** Spoofing · **T** Tampering · **R** Repudiation · **I** Information Disclosure · **D** Denial of Service · **E** Elevation of Privilege · **A** Abuse (feature misuse) |
| **SDL Severity**         | `Critical` · `Important` · `Moderate` · `Low`                                                                                                                               |
| **Remediation Effort**   | `Low` · `Medium` · `High`                                                                                                                                                   |
| **Mitigation Type**      | `Redesign` · `Standard Mitigation` · `Custom Mitigation` · `Existing Control` · `Accept Risk` · `Transfer Risk`                                                             |
| **Threat Status**        | `Open` · `Mitigated` · `Platform`                                                                                                                                           |
| **Incremental Tags**     | `[Existing]` · `[Fixed]` · `[Partial]` · `[New]` · `[Removed]` (incremental reports only)                                                                                   |
| **CVSS**                 | CVSS 4.0 vector with `CVSS:4.0/` prefix                                                                                                                                     |
| **CWE**                  | Hyperlinked CWE ID (e.g., [CWE-306](https://cwe.mitre.org/data/definitions/306.html))                                                                                       |
| **OWASP**                | OWASP Top 10:2025 mapping (e.g., A01:2025 – Broken Access Control)                                                                                                          |
