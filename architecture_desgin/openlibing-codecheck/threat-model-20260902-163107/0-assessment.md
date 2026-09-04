# Security Assessment

---

## Report Files

| File                                                       | Description                                                           |
| ---------------------------------------------------------- | --------------------------------------------------------------------- |
| [0-assessment.md](0-assessment.md)                         | This document — executive summary, risk rating, action plan, metadata |
| [0.1-architecture.md](0.1-architecture.md)                 | Architecture overview, components, scenarios, tech stack              |
| [1-threatmodel.md](1-threatmodel.md)                       | Threat model DFD diagram with element, flow, and boundary tables      |
| [1.1-threatmodel.mmd](1.1-threatmodel.mmd)                 | Pure Mermaid DFD source file                                          |
| [2-stride-analysis.md](2-stride-analysis.md)               | Full STRIDE-A analysis for all components                             |
| [3-findings.md](3-findings.md)                             | Prioritized security findings with remediation                        |
| [1.2-threatmodel-summary.mmd](1.2-threatmodel-summary.mmd) | Summary DFD for large systems                                         |

---

## Executive Summary

openlibing-codecheck is the code-inspection microservice of the OpenLibing R&D workflow platform. It orchestrates Huawei Cloud CodeCheck scans (daily full scans and incremental PR gate checks), ingests and parses static-alarm SARIF results from the CICD service, manages rule sets and defect shielding, and exposes board/summary queries and Excel exports to the CI portal. It is a Spring Boot application deployed as a single Kubernetes workload (port 8091, non-root container, RASP agent) with three distinct trust surfaces: cluster-internal service-to-service endpoints, portal endpoints proxied by the ci-portal backend, and M2M `/apig/v1/**` APIs fronted by the Huawei APIG gateway.

The analysis identified **59 threats** across **38 components** and consolidated them into **35 actionable findings**. The system has **no Tier 1 (directly exploitable) findings**: every externally reachable surface is gated by an upstream boundary (Huawei APIG gateway for M2M APIs, the ci-portal backend proxy for portal APIs), and the internal endpoints require cluster-network access. However, the risk is **concentrated in the authentication and authorization layer** — the application performs almost no in-code authentication, and several authorization decisions consume client-supplied identity (`userId`), enabling impersonation, unauthorized task triggers, SSRF, and NoSQL injection once any in-cluster or gateway-authorized actor exists. The most severe finding (FIND-04, Critical) is an authorization bypass through user-controlled keys.

Positive controls were verified and documented: the webhook path applies a field whitelist (`WebhookInputValidator`), several portal endpoints call `AuthUtils.checkPermission`, Redis and RabbitMQ use TLS in production, MongoDB transport uses TLS, the container runs as a non-root user with an RASP agent, and the XXL-Job executor and Redisson locks are configured. The dominant risk direction is that the platform's security currently depends on boundary controls (gateway auth, network segmentation, Nacos ACL) that live largely outside this repository and cannot be verified from source alone — several key assumptions are recorded in `Analysis Context & Assumptions → Needs Verification`.

The analysis covers **38 system elements across 3 trust boundaries**.

### Risk Rating: Elevated

The risk is rated Elevated rather than Critical because zero findings are directly exploitable without a prerequisite (Tier 1 = 0). Every exploit path requires either cluster-network access (Tier 2, 26 findings) or prior compromise/administrative access (Tier 3, 9 findings). However, the tier is elevated by the presence of one Critical and twelve Important findings that, when reachable (e.g., by a compromised sibling pod, a malicious in-cluster actor, or a misconfigured APIG gateway), enable full read/write over scan results, defect data, and task workflows — including the ability to impersonate any platform user via client-supplied `userId` (FIND-04) and to trigger arbitrary scans and parses (FIND-02, FIND-10). The security posture is therefore only as strong as the external boundary controls, which cannot be validated from this repository's source.

> **Note on threat counts:** This analysis identified 59 threats across 38 components. This count reflects comprehensive STRIDE-A coverage, not systemic insecurity. Of these, **0 are directly exploitable** without prerequisites (Tier 1). The remaining 59 represent conditional risks (46) and defense-in-depth considerations (13).

---

## Action Summary

| Tier                                                                                | Description                   | Threats | Findings | Priority         |
| ----------------------------------------------------------------------------------- | ----------------------------- | ------- | -------- | ---------------- |
| [Tier 1](3-findings.md#tier-1--direct-exposure-no-prerequisites)                    | Directly exploitable          | 0       | 0        | 🔴 Critical Risk |
| [Tier 2](3-findings.md#tier-2--conditional-risk-authenticated--single-prerequisite) | Requires authenticated access | 46      | 26       | 🟠 Elevated Risk |
| [Tier 3](3-findings.md#tier-3--defense-in-depth-prior-compromise--host-access)      | Requires prior compromise     | 13      | 9        | 🟡 Moderate Risk |
| **Total**                                                                           |                               | **59**  | **35**   |                  |

### Priority by Tier and CVSS Score (Top 10)

| Finding                                                                                                       | Tier | CVSS Score | SDL Severity | Title                                                                         |
| ------------------------------------------------------------------------------------------------------------- | ---- | ---------- | ------------ | ----------------------------------------------------------------------------- |
| [FIND-04](3-findings.md#find-04-client-supplied-identity-enables-authorization-bypass)                        | T2   | 8.7        | Critical     | Client-supplied identity enables authorization bypass                         |
| [FIND-06](3-findings.md#find-06-nosql-injection-via-insufficient-input-validation)                            | T2   | 8.1        | Important    | NoSQL injection via insufficient input validation                             |
| [FIND-02](3-findings.md#find-02-unauthenticated-internal--machine-endpoints-allow-unauthorized-task-triggers) | T2   | 8.0        | Important    | Unauthenticated internal & machine endpoints allow unauthorized task triggers |
| [FIND-01](3-findings.md#find-01-missing-code-level-authentication-on-m2m-apigv1-endpoints)                    | T2   | 7.8        | Important    | Missing code-level authentication on M2M `/apig/v1/**` endpoints              |
| [FIND-05](3-findings.md#find-05-ssrf-via-sarif-obsurl-server-side-fetch)                                      | T2   | 7.5        | Important    | SSRF via SARIF obsUrl server-side fetch                                       |
| [FIND-09](3-findings.md#find-09-unbounded-sarif-downloadparse-causes-resource-exhaustion)                     | T2   | 7.5        | Important    | Unbounded SARIF download/parse causes resource exhaustion                     |
| [FIND-19](3-findings.md#find-19-mongodb-tls-hostname-verification-disabled)                                   | T2   | 7.4        | Important    | MongoDB TLS hostname verification disabled                                    |
| [FIND-03](3-findings.md#find-03-missing-authorization-on-portalboardwebhook-read-endpoints)                   | T2   | 7.2        | Important    | Missing authorization on portal/board/webhook read endpoints                  |
| [FIND-14](3-findings.md#find-14-aksk-ciphertext-in-redis-queues-and-error-logs)                               | T2   | 7.0        | Important    | AK/SK ciphertext in Redis queues and error logs                               |
| [FIND-21](3-findings.md#find-21-scan-results-delivered-without-integrity-verification)                        | T2   | 7.0        | Important    | Scan results delivered without integrity verification                         |

### Quick Wins

_No Tier 1 findings exist for this repository, so there are no zero-prerequisite quick wins. The lowest-effort Tier 2 remediations are Low-effort fixes that remove broad weaknesses with small changes: [FIND-07](3-findings.md#find-07-sensitive-data-logged-at-info-across-controllers) (log redaction), [FIND-13](3-findings.md#find-13-malformed-pr-url-causes-exception-churn) (PR URL validation), [FIND-19](3-findings.md#find-19-mongodb-tls-hostname-verification-disabled) (enable MongoDB hostname verification), and [FIND-25](3-findings.md#find-25-obs-object-key-validation-absent-defense-in-depth) (OBS object-key allowlist)._

---

## Analysis Context & Assumptions

### Analysis Scope

| Constraint  | Description                                                                                                                                                                                                                                                         |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scope       | Full source analysis of the `openlibing-codecheck` repository (Spring Boot microservice, K8s deployment)                                                                                                                                                            |
| Excluded    | Internal implementation of external services (Nacos, HuaweiOBS, HuaweiApiG, HuaweiCodeCheck, GitCode/Gitee/Github, SMTP); internal code of sibling services (openlibing-cicd, openlibing-framework, openlibing-coderepo); ci-portal frontend/backend implementation |
| Focus Areas | Authentication & authorization (AuthUtils, APIG gateway dependency), injection (NoSQL/command/HTML), SSRF, cryptographic & credential handling, log leakage, message-queue security, transport security (TLS), resource consumption, business-logic abuse           |

### Infrastructure Context

| Category           | Discovered from Codebase                                                                                                                                     | Findings Affected                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------- |
| Deployment         | Single K8s workload, non-root container, RASP agent, port 8091; three trust boundaries (pod / cluster / external)                                            | FIND-27, FIND-28                            |
| Authentication     | No unified in-code auth layer; M2M APIs delegate to Huawei APIG; internal endpoints rely on service-to-service trust; `AuthUtils` manual per-endpoint checks | FIND-01, FIND-02, FIND-03, FIND-04, FIND-24 |
| Secrets & Config   | Nacos config center holds `security.part1` AES key co-located with all encrypted secrets; `SecurityHelper.decrypt` used at connect time                      | FIND-27, FIND-30, FIND-35                   |
| Transport          | MongoDB TLS with `invalidHostNameAllowed(true)`; RabbitMQ TLS only for `prod` profile; MySQL TLS depends on JDBC URL; Feign HTTPS without mTLS               | FIND-19, FIND-20, FIND-22                   |
| Messaging & Queues | RabbitMQ consumers (concurrency 1-3), Redisson locks, AK/SK ciphertext persisted in Redis task queues                                                        | FIND-14, FIND-15, FIND-17, FIND-30          |
| Logging            | INFO-level full request/DTO logging across controllers; credential-bearing `Request` objects logged on error paths                                           | FIND-07, FIND-14, FIND-35                   |

### Needs Verification

| Item                        | Question                                                                                            | What to Check                                  | Why Uncertain                                                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| APIG gateway enforcement    | Does HuaweiApiG actually enforce authentication, rate limiting, and caller audit for `/apig/v1/**`? | Gateway configuration/policy, AppCode issuance | Gateway behavior is outside this repo; FIND-01/FIND-10 assume the gateway is the only barrier                  |
| ci-portal userId proxy      | Does the ci-portal backend validate or override the client-supplied `userId` before forwarding?     | ci-portal source, ingress/filter configuration | If the backend replaces `userId` server-side, the prerequisite for FIND-04 is raised                           |
| MySQL TLS                   | Does the config-center JDBC URL enforce `useSSL`/`requireSSL`?                                      | Nacos datasource config                        | `DataSourceConfig` configures no TLS in code; transport security is config-dependent (FIND-20)                 |
| XXL-Job accessToken         | Is the `xxl.job.admin.accessToken` strong, non-empty, and rotated?                                  | Nacos config value                             | Token strength cannot be verified from source (FIND-23)                                                        |
| SMTP STARTTLS               | Does the mail server accept/enforce STARTTLS and reject plaintext?                                  | SMTP server policy                             | `EmailUtil` sets no TLS property; server may still enforce it (FIND-33)                                        |
| Nacos ACL                   | Are Nacos ACLs enabled and is the `security.part1` key isolated from application config?            | Nacos auth/config-group policy                 | The key and ciphertexts co-reside in the same group; isolation is deployment-dependent (FIND-27)               |
| Network segmentation        | Are cluster NetworkPolicies / mTLS enforced between pods and backing services?                      | K8s NetworkPolicy, service mesh config         | Internal endpoints assume service-to-service trust; segmentation would raise prerequisites for FIND-02/FIND-03 |
| MongoDB certificate pinning | Can `invalidHostNameAllowed(false)` be safely enabled without breaking the current cert setup?      | MongoDB server cert/CA chain                   | Current setting is a deliberate workaround (FIND-19)                                                           |

### Finding Overrides

| Finding ID | Original Severity | Override | Justification                                           | New Status |
| ---------- | ----------------- | -------- | ------------------------------------------------------- | ---------- |
| —          | —                 | —        | No overrides applied. Update this section after review. | —          |

### Additional Notes

Deployment classification: K8s cluster service with mixed exposure — the `/apig/v1/**` surface is externally reachable only via the Huawei APIG gateway (treated as a platform trust boundary), portal endpoints are reachable only via the ci-portal backend proxy, and `/internal/**`, machine, webhook, and board endpoints are cluster-internal. This classification yields zero Tier 1 findings because every listener has at least one upstream barrier, and it sets the prerequisite floor (Internal Network or Authenticated User) used throughout the STRIDE-A analysis and findings. If network segmentation is later removed (e.g., endpoints exposed to a broader network), several Tier 2 findings would escalate to Tier 1.

---

## References Consulted

### Security Standards

| Standard              | URL                                                                                   | How Used                |
| --------------------- | ------------------------------------------------------------------------------------- | ----------------------- |
| Microsoft SDL Bug Bar | https://www.microsoft.com/en-us/msrc/sdlbugbar                                        | Severity classification |
| OWASP Top 10:2025     | https://owasp.org/Top10/2025/                                                         | Threat categorization   |
| CVSS 4.0              | https://www.first.org/cvss/v4.0/specification-document                                | Risk scoring            |
| CWE                   | https://cwe.mitre.org/                                                                | Weakness classification |
| STRIDE                | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats | Threat enumeration      |

### Component Documentation

| Component                  | Documentation URL                                                       | Relevant Section                                |
| -------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------- |
| Spring Boot                | https://spring.io/projects/spring-boot                                  | MVC controllers, scheduled tasks, configuration |
| Spring Data MongoDB        | https://docs.spring.io/spring-data/mongodb/docs/current/reference/html/ | MongoTemplate query construction                |
| Redisson                   | https://redisson.org/                                                   | Distributed locks, Redis queue operations       |
| Jedis                      | https://github.com/redis/jedis                                          | Redis client (TLS)                              |
| RabbitMQ Java Client       | https://www.rabbitmq.com/clients/java-api-client                        | Message consumers, dead-letter handling         |
| Huawei Cloud OBS SDK       | https://support.huaweicloud.com/sdk-java-devg-obs/                      | Object storage file operations                  |
| Huawei Cloud CodeCheck API | https://support.huaweicloud.com/api-codecheck/                          | Scan task creation and result polling           |
| XXL-Job                    | https://github.com/xuxueli/xxl-job                                      | Executor registration, scheduled handlers       |

---

## Report Metadata

| Field              | Value                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Source Location    | `d:\code\openlibing-new\openlibing-codecheck`                                                                                         |
| Git Repository     | `https://gitcode.com/openlibing/openlibing-codecheck.git`                                                                             |
| Git Branch         | `master`                                                                                                                              |
| Git Commit         | `d7c7af22` (`2026-09-02 09:26:04 +0800`)                                                                                              |
| Model              | `DeepSeek-V4-Flash`                                                                                                                   |
| Machine Name       | `DESKTOP-MO1I5FG`                                                                                                                     |
| Analysis Started   | `2026-09-02 16:31:07 (+08:00)`                                                                                                        |
| Analysis Completed | `2026-09-03 09:24:33 (+08:00)`                                                                                                        |
| Duration           | `16h 53m (multi-session, includes idle time between sessions)`                                                                        |
| Output Folder      | `threat-model-20260902-163107`                                                                                                        |
| Prompt             | `使用 threat-model-analyst skill，对 codecheck 仓进行安全威胁分析，分析报告放在 docs 仓的 architecture_desgin 目录下，先不要提交代码` |

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
