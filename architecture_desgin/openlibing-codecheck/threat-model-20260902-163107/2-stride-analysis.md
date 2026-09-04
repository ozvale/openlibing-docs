# STRIDE + Abuse Cases — Threat Analysis

> This analysis uses the standard **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) extended with **Abuse Cases** (business logic abuse, workflow manipulation, feature misuse). The "A" column in tables below represents Abuse — a supplementary category covering threats where legitimate features are misused for unintended purposes. This is distinct from Elevation of Privilege (E), which covers authorization bypass.

## Exploitability Tiers

Threats are classified into three exploitability tiers based on the prerequisites an attacker needs:

| Tier       | Label            | Prerequisites                                                                                                                 | Assignment Rule                                                                                                |
| ---------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Tier 1** | Direct Exposure  | `None`                                                                                                                        | Exploitable by unauthenticated external attacker with NO prior access. The prerequisite field MUST say `None`. |
| **Tier 2** | Conditional Risk | Single prerequisite: `Authenticated User`, `Privileged User`, `Internal Network`, or single `{Boundary} Access`               | Requires exactly ONE form of access. The prerequisite field has ONE item.                                      |
| **Tier 3** | Defense-in-Depth | `Host/OS Access`, `Admin Credentials`, `{Component} Compromise`, `Physical Access`, or MULTIPLE prerequisites joined with `+` | Requires significant prior breach, infrastructure access, or multiple combined prerequisites.                  |

> **Deployment context:** The service is `K8S_SERVICE` (single pod, ClusterIP on 0.0.0.0:8091). Per the Component Exposure Table in `0.1-architecture.md`, every application component has a prerequisite floor of `Internal Network` (T2) or `Authenticated User` (T2) — no component is directly reachable by an unauthenticated external attacker because external M2M traffic is fronted by the Huawei APIG gateway and portal/internal paths are reachable only from inside the cluster. Consequently **no Tier 1 threats exist** in this analysis; all threats are Tier 2 or Tier 3.

## Summary

| Component                      | Link                                    | S     | T     | R     | I      | D     | E     | A     | Total  | T1    | T2     | T3     | Risk   |
| ------------------------------ | --------------------------------------- | ----- | ----- | ----- | ------ | ----- | ----- | ----- | ------ | ----- | ------ | ------ | ------ |
| OpenlibingCodecheckApplication | [Link](#openlibingcodecheckapplication) | 1     | 0     | 0     | 1      | 0     | 0     | 0     | 2      | 0     | 0      | 2      | Low    |
| HwApigController               | [Link](#hwapigcontroller)               | 0     | 0     | 0     | 1      | 0     | 1     | 1     | 3      | 0     | 3      | 0      | High   |
| WebhookController              | [Link](#webhookcontroller)              | 0     | 0     | 0     | 2      | 0     | 0     | 0     | 2      | 0     | 2      | 0      | Medium |
| InternalController             | [Link](#internalcontroller)             | 0     | 0     | 0     | 1      | 0     | 1     | 1     | 3      | 0     | 2      | 1      | High   |
| StaticAlarmReceiveController   | [Link](#staticalarmreceivecontroller)   | 1     | 1     | 0     | 1      | 0     | 0     | 1     | 4      | 0     | 4      | 0      | High   |
| InternalCodeFullController     | [Link](#internalcodefullcontroller)     | 0     | 0     | 0     | 1      | 0     | 1     | 0     | 2      | 0     | 2      | 0      | High   |
| InternalCodeIncController      | [Link](#internalcodeinccontroller)      | 0     | 1     | 0     | 0      | 1     | 1     | 0     | 3      | 0     | 3      | 0      | High   |
| FileDownLoadController         | [Link](#filedownloadcontroller)         | 1     | 0     | 0     | 1      | 0     | 1     | 0     | 3      | 0     | 3      | 0      | High   |
| CheckboardController           | [Link](#checkboardcontroller)           | 0     | 0     | 0     | 2      | 0     | 1     | 0     | 3      | 0     | 3      | 0      | High   |
| AuthUtils                      | [Link](#authutils)                      | 1     | 0     | 0     | 0      | 0     | 1     | 0     | 2      | 0     | 2      | 0      | High   |
| RuleSetScheduleTask            | [Link](#rulesetscheduletask)            | 0     | 0     | 0     | 1      | 0     | 0     | 1     | 2      | 0     | 2      | 0      | Medium |
| SaveFullTaskResult             | [Link](#savefulltaskresult)             | 0     | 0     | 0     | 2      | 0     | 0     | 0     | 2      | 0     | 2      | 0      | Medium |
| SaveIncTaskResult              | [Link](#saveinctaskresult)              | 0     | 0     | 0     | 1      | 0     | 0     | 1     | 2      | 0     | 2      | 0      | Medium |
| CodeCheckEventConsumer         | [Link](#codecheckeventconsumer)         | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Low    |
| StaticAlarmEventConsumer       | [Link](#staticalarmeventconsumer)       | 0     | 0     | 0     | 0      | 1     | 0     | 1     | 2      | 0     | 2      | 0      | Medium |
| ShieldAllConsumer              | [Link](#shieldallconsumer)              | 0     | 0     | 0     | 1      | 0     | 0     | 1     | 2      | 0     | 2      | 0      | Medium |
| StaticAlarmExportConsumer      | [Link](#staticalarmexportconsumer)      | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Low    |
| SarifParseServiceImpl          | [Link](#sarifparseserviceimpl)          | 0     | 0     | 0     | 1      | 1     | 0     | 0     | 2      | 0     | 2      | 0      | High   |
| ObsBucketServiceImpl           | [Link](#obsbucketserviceimpl)           | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Low    |
| MongoDB                        | [Link](#mongodb)                        | 0     | 1     | 0     | 0      | 0     | 1     | 0     | 2      | 0     | 1      | 1      | High   |
| MySQL                          | [Link](#mysql)                          | 0     | 1     | 0     | 0      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Medium |
| Redis                          | [Link](#redis)                          | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 0      | 1      | Medium |
| RabbitMQ                       | [Link](#rabbitmq)                       | 0     | 1     | 0     | 0      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | High   |
| OpenlibingCicd                 | [Link](#openlibingcicd)                 | 0     | 1     | 0     | 0      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Medium |
| OpenlibingFramework            | [Link](#openlibingframework)            | 1     | 0     | 0     | 0      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Medium |
| OpenlibingCoderepo             | [Link](#openlibingcoderepo)             | 1     | 0     | 0     | 0      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Medium |
| XxlJob                         | [Link](#xxljob)                         | 1     | 0     | 0     | 0      | 0     | 0     | 0     | 1      | 0     | 1      | 0      | Medium |
| Nacos                          | [Link](#nacos)                          | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 0      | 1      | Medium |
| HuaweiOBS                      | [Link](#huaweiobs)                      | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 0      | 1      | Medium |
| HuaweiApiG                     | [Link](#huaweiapig)                     | 0     | 0     | 0     | 0      | 0     | 1     | 0     | 1      | 0     | 0      | 1      | Medium |
| HuaweiCodeCheck                | [Link](#huaweicodecheck)                | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 0      | 1      | Low    |
| GitCode                        | [Link](#gitcode)                        | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 0      | 1      | Medium |
| Gitee                          | [Link](#gitee)                          | 0     | 0     | 0     | 1      | 0     | 0     | 0     | 1      | 0     | 0      | 1      | Medium |
| Github                         | [Link](#github)                         | 0     | 0     | 0     | 0      | 0     | 0     | 1     | 1      | 0     | 0      | 1      | Low    |
| SmtpServer                     | [Link](#smtpserver)                     | 0     | 1     | 0     | 0      | 0     | 0     | 0     | 1      | 0     | 0      | 1      | Medium |
| **Totals**                     |                                         | **7** | **7** | **0** | **25** | **3** | **9** | **8** | **59** | **0** | **46** | **13** |        |

---

## OpenlibingCodecheckApplication

**Trust Boundary:** CodecheckService
**Role:** Spring Boot bootstrap: Nacos config loading, credential decryption (DataSourceConfig/MongoConfig/RedisConfig), RASP agent host
**Data Flows:** DF52, DF53
**Pod Co-location:** RASP agent (co-located in the same pod)

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                          | Prerequisites    | Affected Flow | Mitigation                                                                                                                                                            | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T01.1 | Spoofing               | Nacos configuration spoofing: `security.part1`, datasource/Redis/Mongo/RabbitMQ credentials, and all account tokens are injected from the Nacos config center; an attacker able to publish config (or poison discovery) can inject attacker-controlled credentials and endpoints, steering the application to hostile services. | Nacos Compromise | DF52          | Restrict Nacos write/read access to trusted operators; use Nacos ACL/namespace isolation; validate config source integrity; separate discovery from sensitive config. | Open   |
| T01.2 | Information Disclosure | Key/ciphertext co-location: the AES key `security.part1` and the encrypted secrets it decrypts are stored in the same Nacos namespace and same config group (`OPENLIBING`), so one config compromise reveals both the key and the ciphertexts it protects, negating encryption isolation.                                       | Nacos Compromise | DF52          | Move the key to a dedicated secrets manager with independent access control and rotation; avoid co-locating key and ciphertext in the same config artifact.           | Open   |

#### Categories Not Applicable

| Category               | Justification                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Tampering              | The bootstrap component performs no mutable data operations beyond reading config and decryption; no user-writable state. |
| Repudiation            | No user-facing action originates from the bootstrap process.                                                              |
| Denial of Service      | Unavailability of Nacos is an availability dependency, not an attacker-controlled DoS of this component.                  |
| Elevation of Privilege | The bootstrap runs as the same non-root `openlibing` user as the rest of the pod; no privilege boundary to cross.         |
| Abuse                  | Bootstrap has no business feature to misuse.                                                                              |

---

## HwApigController

**Trust Boundary:** CodecheckService
**Role:** M2M API endpoints under `/apig/v1/**` fronted by Huawei APIG gateway (full task trigger, inc task trigger, task status, full result summary)
**Data Flows:** DF06, DF07
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                         | Prerequisites      | Affected Flow | Mitigation                                                                                                                            | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T02.1 | Elevation of Privilege | No code-level authentication: all four `/apig/v1/**` endpoints rely entirely on the Huawei APIG gateway for auth (javadoc lines 29-31). A gateway misconfiguration, weak AppCode, or gateway bypass exposes unauthenticated task-trigger and status-read APIs. | Authenticated User | DF07          | Enforce a second in-code auth barrier (HMAC/API-key/signature validation) on `/apig/v1/**`; do not single-source auth to the gateway. | Open   |
| T02.2 | Information Disclosure | Full request bodies logged at INFO on every endpoint (lines 72, 94, 113, 135: `logger.info("apig startFullTaskForApig entry, params={}", params)`), including repoUrl, task params, and caller-supplied fields; sensitive data lands in log pipelines.         | Internal Network   | DF06, DF07    | Redact or truncate request payloads before logging; log only non-sensitive identifiers (taskId, uuid); review log retention/access.   | Open   |
| T02.3 | Abuse                  | Any authenticated (gateway-authorized) machine caller can submit arbitrary full/inc scan tasks for arbitrary repo URLs without quota or ownership checks, consuming Huawei CodeCheck scan quota and compute cost.                                              | Authenticated User | DF06, DF07    | Add per-caller rate/quota limits and repo-ownership validation in code; bind machine callers to registered projects.                  | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category          | Justification                                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Spoofing          | Machine callers are authenticated by the gateway; in-code there is no identity to spoof, so the exposure is covered by T02.1 (Elevation of Privilege). |
| Tampering         | The controller performs no data mutation itself (delegates to downstream services).                                                                    |
| Repudiation       | No per-caller audit trail exists at the controller; gateway audit is external (Platform).                                                              |
| Denial of Service | Rate limiting is delegated to the gateway (Platform); no in-code DoS surface beyond normal endpoint handling.                                          |

---

## WebhookController

**Trust Boundary:** CodecheckService
**Role:** Webhook MongoDB query endpoint `/ci-portal/webhook/codecheck/v1/find/by/mongoDB` with WebhookInputValidator whitelisting
**Data Flows:** DF01, DF20
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                              | Prerequisites    | Affected Flow | Mitigation                                                                                                                          | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T03.1 | Information Disclosure | Unauthenticated MongoDB read access: any in-cluster caller can query 17 whitelisted collections (TASK_INC, TASK_RESULT_DETAILS, STATIC_ALARM_ISSUE, etc.) with whitelisted fields; the endpoint performs no authentication, so task/defect/alarm data is readable without permission.                                               | Internal Network | DF01, DF20    | Add an authentication/authorization barrier for this endpoint; scope queryable collections per-caller; audit reads.                 | Open   |
| T03.2 | Information Disclosure | NoSQL injection via whitelist gaps: `WebhookInputValidator` blocks non-whitelisted table/field names and Map/Iterable operator values in the reachable `readMongoDB` path, but `insertData` validates only `tableName` and leaves nested `queryData`/`mongoData` unvalidated; injection surface persists on future reachable paths. | Internal Network | DF20          | Extend `validateFieldName`/`validateValue` to all write/insert paths; unit-test validator against operator objects and array types. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Spoofing               | No identity is claimed or checked in-code; the exposure is an authorization gap (covered under Information Disclosure). |
| Tampering              | The reachable path performs read-only MongoDB queries; no data mutation.                                                |
| Repudiation            | No write/state-change operation on this controller to repudiate.                                                        |
| Denial of Service      | No unbounded input or expensive computation beyond a bounded whitelisted query.                                         |
| Elevation of Privilege | The exposure is horizontal data read (Information Disclosure), not privilege escalation.                                |
| Abuse                  | Query abuse is bounded by the whitelist; treated under T03.1.                                                           |

---

## InternalController

**Trust Boundary:** CodecheckService
**Role:** Service-to-service endpoints under `/internal/**` (pre-commit pipeline trigger, rule-set recompute, full task invoke for openlibing-coderepo)
**Data Flows:** DF11, DF54, DF55
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                         | Prerequisites    | Affected Flow | Mitigation                                                                                                                                                          | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T04.1 | Elevation of Privilege | Unauthenticated internal endpoints: `/internal/**` relies on "service-to-service trust" with no credential (javadoc lines 76-79). Any in-cluster pod can invoke `/internal/pre-commit` (triggers a local auto-fix process and a CICD pipeline), `/internal/rule-set/recompute-used`, and `/internal/full/invoke/task?branchId=` (triggers a full Huawei scan). | Internal Network | DF11, DF54    | Enforce mutual authentication (mTLS/API token) for `/internal/**`; verify caller identity (service account) before acting; restrict to the actual sibling services. | Open   |
| T04.2 | Abuse                  | Option injection into the auto-fix process: `CommandArgSanitizer.sanitizeBranchName` allows a leading `-` and `..` sequences; a branch like `--flag` or `-c <value>` is accepted and passed as an option value to `auto-fix.sh -b`, enabling option/argument injection into the shell script.                                                                  | Internal Network | DF11          | Reject branch names starting with `-`; strengthen `sanitizeBranchName` regex; pass branch via environment or stdin rather than argv.                                | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                           | Prerequisites  | Affected Flow | Mitigation                                                                                                                         | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T04.3 | Information Disclosure | Decrypted repo access tokens passed as process command-line arguments: `PipelineDelegateImpl.preMergeAndFix` runs `timeout ... /opt/app/openlibing/auto-fix.sh -a <repo> ... -d <targetToken> -l <sourceToken>` (lines 166-194); the decrypted tokens are visible in the host process list (`ps`/`/proc`) to any local observer. | Host/OS Access | DF11          | Pass tokens via environment variables or a temp file with 0600 permissions; use `ProcessBuilder` with env; avoid argv for secrets. | Open   |

#### Categories Not Applicable

| Category          | Justification                                                                                   |
| ----------------- | ----------------------------------------------------------------------------------------------- |
| Spoofing          | In-cluster callers are not identified; the gap is authorization (T04.1), not identity spoofing. |
| Tampering         | No request-body data is mutated by the controller itself (delegates to delegates/services).     |
| Repudiation       | No per-caller audit log exists; pre-commit records are persisted but not caller-authenticated.  |
| Denial of Service | Endpoints are lightweight; heavy work (full scan) is delegated and rate-limited downstream.     |

---

## StaticAlarmReceiveController

**Trust Boundary:** CodecheckService
**Role:** Scan result ingestion endpoint `/codescan/v1/result/receive` receiving OBS URLs and pipeline context from the CICD service
**Data Flows:** DF12, DF15
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                       | Prerequisites    | Affected Flow | Mitigation                                                                                                     | Status |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | -------------------------------------------------------------------------------------------------------------- | ------ |
| T05.1 | Spoofing               | Unauthenticated result ingestion lets any in-cluster service spoof the CICD source: `POST /codescan/v1/result/receive` (also `/internal/codescan/v1/result/receive`, documented as bypassing gateway auth) accepts scan results from any caller, enabling injection of forged scan-run records and triggering SARIF parsing. | Internal Network | DF12          | Authenticate the CICD caller (mTLS/service token); verify pipeline context integrity; audit ingestion.         | Open   |
| T05.2 | Tampering              | Unvalidated `obsUrl`: the DTO field has only `@NotEmpty` — no scheme, host, or domain whitelist (StaticAlarmReceiveDTO lines 37-39; StringOrListDeserializer). Arbitrary URLs are persisted and later fetched server-side by SarifParseServiceImpl, enabling SSRF and malicious-content parsing.                             | Internal Network | DF12          | Validate obsUrl against an allowed OBS host/scheme allowlist; reject private/internal IP ranges and redirects. | Open   |
| T05.3 | Information Disclosure | Full DTO logged at INFO (`LOGGER.info("Static alarm receive called, dto: {}", dto)` line 52, plus lines 56-57, 63-65, 68-74, 88-92) including obsUrl, repoUrl, and pipeline context; sensitive pipeline and repository data lands in logs.                                                                                   | Internal Network | DF12          | Log only scanRecordId and non-sensitive identifiers; redact URLs.                                              | Open   |
| T05.4 | Abuse                  | Arbitrary obsUrl + resource consumption: an in-cluster caller can submit unbounded parse events that cause repeated outbound OBS downloads and parsing work (no per-source quota/rate limit).                                                                                                                                | Internal Network | DF12, DF15    | Rate-limit ingestion per source; cap concurrent parse work; validate URL before enqueue.                       | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                                                         |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Repudiation            | Ingestion records are persisted to MongoDB (`scan_run`), providing an audit trail.                                    |
| Denial of Service      | Direct DoS of the endpoint is bounded by in-cluster access; the resource-exhaustion path is covered by T05.4 (Abuse). |
| Elevation of Privilege | The exposure is spoofing/forgery of data source, not privilege escalation.                                            |

---

## InternalCodeFullController

**Trust Boundary:** CodecheckService
**Role:** Full-scan task endpoints under `/ci-portal/webhook/codecheck/full/**` (start full task)
**Data Flows:** DF04, DF08, DF13, DF26, DF27
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                  | Prerequisites    | Affected Flow | Mitigation                                                                                                       | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| T06.1 | Elevation of Privilege | No authentication/authorization on full-task trigger: `POST /ci-portal/webhook/codecheck/full/task` performs only a repoUrl blank-check (lines 50-53) with no format whitelisting (unlike `/internal/pre-commit` which uses CommandArgSanitizer). Any in-cluster caller can trigger full scans for arbitrary repo URLs. | Internal Network | DF08, DF27    | Enforce caller authentication and repo-ownership validation; apply repoUrl format whitelisting on this path too. | Open   |
| T06.2 | Information Disclosure | Full request params logged at INFO (`logger.info("startFullTask entry, params={}", params)` line 49) including repoUrl and project/branch; sensitive repository identifiers land in logs.                                                                                                                               | Internal Network | DF08          | Log only taskId after creation; redact request payloads.                                                         | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category          | Justification                                                                                            |
| ----------------- | -------------------------------------------------------------------------------------------------------- |
| Spoofing          | Callers are not identified in-code; the gap is authorization (T06.1).                                    |
| Tampering         | No mutation of request data; delegates to downstream services.                                           |
| Repudiation       | Caller identity is not authenticated, so no reliable audit source.                                       |
| Denial of Service | Task trigger is a single DB+API operation; downstream scan is rate-limited by Huawei.                    |
| Abuse             | Resource/scan-quota abuse is the intent of T06.1 (Elevation of Privilege); no separate abuse row needed. |

---

## InternalCodeIncController

**Trust Boundary:** CodecheckService
**Role:** Incremental gate-check endpoints under `/ci-portal/webhook/codecheck/v1/**` (create task, query gate status by uuid)
**Data Flows:** DF05, DF09, DF14, DF28, DF29
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                    | Prerequisites    | Affected Flow | Mitigation                                                                                                      | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | --------------------------------------------------------------------------------------------------------------- | ------ |
| T07.1 | Elevation of Privilege | Gate status exposed by capability value: `POST /ci-portal/webhook/codecheck/v1/task/status` returns gate results for any `uuid` (MongoDB lookup by uuid, IncTaskOperation lines 73-79) with no authentication; the uuid (MD5 of UUID+timestamp+id, TokenUtil lines 50-54) acts as a bearer credential, so a leaked/guessed uuid exposes and can manipulate gate outcomes. | Internal Network | DF09, DF28    | Bind status queries to authenticated callers; require an additional auth factor; rotate/shorten token exposure. | Open   |
| T07.2 | Tampering              | Unencoded concatenation of client-supplied values into URLs: `InternalCodeIncDelegateImpl.handleFinishedTask` builds `openlibingDomain + "/apps/entryCheckDashCode/" + taskId + "/" + uuid + "?projectName=" + openlibingProjectName` (lines 254-273) with unencoded taskId/uuid, allowing parameter injection into the returned result URL.                              | Internal Network | DF09          | URL-encode path/query components; validate taskId/uuid format before concatenation.                             | Open   |
| T07.3 | Denial of Service      | Malformed `pr_url` triggers exception churn: `pr_url.split("/")` requires ≥5 segments then indexes up to `prStrings[6]` (InternalCodeIncDelegateImpl line 163), throwing ArrayIndexOutOfBoundsException for 5-6 segment URLs (caught by generic catch line 136); repeated malformed calls cause repeated error-handling and 500s.                                         | Internal Network | DF09          | Validate PR-URL segment count and format up front; return 4xx for malformed input.                              | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------- |
| Spoofing               | No identity is claimed in-code; the gap is authorization (T07.1).                     |
| Repudiation            | Caller identity not authenticated, so no reliable audit.                              |
| Information Disclosure | Status data exposure is covered by T07.1 (Elevation of Privilege); no separate I row. |
| Abuse                  | Gate-status manipulation is the intent of T07.1.                                      |

---

## FileDownLoadController

**Trust Boundary:** CodecheckService
**Role:** Excel export endpoints under `/ci-portal/excel/v1/**` (export task, status, rule/rule-set export, download log)
**Data Flows:** DF03, DF24, DF25
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                              | Prerequisites    | Affected Flow | Mitigation                                                                                                              | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------- | ------ |
| T08.1 | Elevation of Privilege | Missing permission checks on 6 of 8 export endpoints: only `/rule/set` (lines 129-133) and `/rule/set/export` (lines 155-161) call `AuthUtils.checkPermission`. `/download/log` (fetches Huawei task logs via `RestCodeCheckUtil.showTaskLog`) and the summary/rule export endpoints expose task logs and rule data to any in-cluster caller without authorization. | Internal Network | DF03, DF24    | Add permission checks to all export endpoints, especially `/download/log`; apply a consistent authorization filter.     | Open   |
| T08.2 | Spoofing               | Client-supplied identity: `userId` is a `@RequestParam` on the permission-checked endpoints (lines 128, 153), so any caller can impersonate another user by passing their userId to satisfy `AuthUtils.checkPermission`.                                                                                                                                            | Internal Network | DF03          | Derive the user identity from an authenticated session/token, never from a client-supplied parameter.                   | Open   |
| T08.3 | Information Disclosure | Unvalidated filename concatenation: `tableName + ".xlsx"`, `fileName + ".log"`, `projectName + "规则集.xlsx"` (lines 109, 140, 173, 193, 211) build Content-Disposition filenames from unvalidated request parameters, enabling header/response injection and misleading filenames.                                                                                 | Internal Network | DF03          | Sanitize/whitelist filename components; use Content-Disposition with safe encoding; validate tableName/fileName format. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category          | Justification                                                |
| ----------------- | ------------------------------------------------------------ |
| Tampering         | No request-data mutation; exports are read-only.             |
| Repudiation       | Export activity is not caller-authenticated.                 |
| Denial of Service | Export endpoints are bounded; async export is queue-limited. |
| Abuse             | Data exfiltration via missing auth is covered by T08.1.      |

---

## CheckboardController

**Trust Boundary:** CodecheckService
**Role:** Portal board/summary query endpoints under `/ci-portal/v1/**` with per-endpoint permission checks
**Data Flows:** DF02, DF21, DF22, DF23
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                      | Prerequisites    | Affected Flow | Mitigation                                                                                                   | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------ | ------ |
| T09.1 | Elevation of Privilege | Client-supplied identity on state-changing ops: `POST /codecheck/inc/task/shield-all-result` (lines 235-247) performs bulk defect shielding (a state-changing audit operation) with `userId` taken from the request (line 239); the delegate's `isReviewer(revision, userId)` check (ProblemshieldDelegateImpl lines 526-540) compares against the spoofable client value, allowing unauthorized shielding. | Internal Network | DF02          | Derive userId from an authenticated session; require server-side reviewer identity; audit shield operations. | Open   |
| T09.2 | Information Disclosure | Unauthenticated summary/detail reads: the 13 query endpoints under `/ci-portal/v1/**` have no controller-level auth; board summaries, defect details, task file contents, and full/inc metrics are readable by any in-cluster caller.                                                                                                                                                                       | Internal Network | DF02, DF21    | Add consistent authorization for all read endpoints; enforce repo-level permission checks.                   | Open   |
| T09.3 | Information Disclosure | NoSQL query injection via unvalidated query models: `QueryDetailModel`, `QueryTaskFileContentModel`, and `IgnoredExtendDTO` lack `@Valid` and whitelisting (only `QuerySummaryModel` bodies are `@Valid`, lines 121, 181, 193), so query criteria fields flow into MongoDB queries unsanitized.                                                                                                             | Internal Network | DF21          | Add `@Valid` + field whitelisting to all query DTOs; centralize NoSQL query construction.                    | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category          | Justification                                                                                            |
| ----------------- | -------------------------------------------------------------------------------------------------------- |
| Spoofing          | Identity spoofing is subsumed by T09.1 (Elevation of Privilege).                                         |
| Tampering         | Query endpoints are read-only except shield-all (covered by T09.1).                                      |
| Repudiation       | Shield-all is recorded in Mongo (`message_apply`/`message_notice`) but not authenticated to a real user. |
| Denial of Service | No unbounded query or computation on this controller.                                                    |
| Abuse             | Feature misuse (bulk shielding) is the intent of T09.1.                                                  |

---

## AuthUtils

**Trust Boundary:** CodecheckService
**Role:** Horizontal/vertical permission decision component (repo permission, menu-role checks against MySQL, public-repo assertions)
**Data Flows:** DF30, DF31
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                            | Prerequisites      | Affected Flow | Mitigation                                                                                                               | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------------ | ------ |
| T10.1 | Elevation of Privilege | Over-broad authorization bypasses in `checkPermission`: returns `true` unconditionally for roles `admin`/`platform_operator` regardless of project (lines 371-377), for any menu with identification `general_config` (lines 357-359), and `assertAuthFromSummary` returns `true` for any `"public"` repo without a per-user check (lines 155-168); these widen the authorization surface beyond least privilege. | Authenticated User | DF30          | Restrict admin bypasses to explicit project scopes; validate `general_config` handling; tighten public-repo assumptions. | Open   |
| T10.2 | Spoofing               | Permission decisions consume client-supplied `userId` (FileDownLoadController lines 128, 153; CheckboardController shield-all line 239) rather than a server-authenticated identity, so horizontal privilege escalation is trivial by spoofing another user's id.                                                                                                                                                 | Internal Network   | DF30          | Replace client-supplied userId with session/token-derived identity at all checkPermission call sites.                    | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                      |
| ---------------------- | ------------------------------------------------------------------ |
| Tampering              | AuthUtils only reads role/permission data; no mutation.            |
| Repudiation            | Permission decisions are not audited (no authz audit log).         |
| Information Disclosure | No direct data disclosure; decisions gate other components' data.  |
| Denial of Service      | No unbounded computation; DB lookups are indexed.                  |
| Abuse                  | Business misuse is handled by the two authorization threats above. |

---

## RuleSetScheduleTask

**Trust Boundary:** CodecheckService
**Role:** Scheduled tenant rule-set sync with Redisson locks, Redis queues, AK/SK credentials
**Data Flows:** DF37, DF38, DF39
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                             | Prerequisites    | Affected Flow | Mitigation                                                                                                                                                 | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T11.1 | Information Disclosure | Credential material in Redis and logs: `syncRule()` serializes `{region, akSkVo}` (ciphertext AK/SK) into Redis queue `rule_set:languages_severity_rule_set_task_queue` (lines 319-331), and error paths log the map/JSON containing the AkSkVo ciphertext (`logger.error("Parameter serialization failed: {}", paramMap, e)` line 327; line 354). | Internal Network | DF37          | Do not persist AK/SK (even ciphertext) in task queues; redact credential fields from log messages; cache decrypted credentials in-memory with TTL instead. | Open   |
| T11.2 | Abuse                  | Dequeue/consume phase runs outside the Redisson lock: for `getAllAccountRule`/`syncRule`/`getProjectRuleSets` only queue initialization is locked; if the lock is not acquired, consumers still process stale queue content (lines 143, 295, 473), enabling duplicate or inconsistent rule-set sync.                                               | Internal Network | DF37          | Move the consume phase inside the lock or use idempotent consumption keys; clear queues on lock failure.                                                   | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                   |
| ---------------------- | ------------------------------------------------------------------------------- |
| Spoofing               | Scheduled task has no external identity surface.                                |
| Tampering              | Rule-set data comes from Huawei API (AK/SK signed); no local mutation of input. |
| Repudiation            | No user-facing action.                                                          |
| Denial of Service      | Scheduled work is bounded by cron and locks.                                    |
| Elevation of Privilege | Runs as the standard non-root app user; no privilege boundary.                  |

---

## SaveFullTaskResult

**Trust Boundary:** CodecheckService
**Role:** Scheduled job polling full-scan results from HuaweiCodeCheck, MongoDB writes, email notifications
**Data Flows:** DF40, DF41, DF42
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                           | Prerequisites    | Affected Flow | Mitigation                                                                                       | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------ | ------ |
| T12.1 | Information Disclosure | HTML injection in notification emails: `executionDurationJudgment` builds an HTML body by concatenating `taskVo.getRepoName()`, `getGitUrl()`, `getBranch()`, and triggerTime without escaping (lines 294-299), and EmailUtil sends it as `text/html` (line 165); attacker-influenced task metadata can inject HTML/phishing content into recipients' mail clients.              | Internal Network | DF42          | HTML-escape all interpolated fields; use a templating engine; send text/plain or sanitized HTML. | Open   |
| T12.2 | Information Disclosure | Unsanitized persisted data: Huawei CodeCheck API responses (summary/details) are written to MongoDB (`fullSummaryOperation.saveInfo`, `fullDetailsOperation.saveInfo`) with only status/emptiness checks — no field-level sanitization of `filePath`/`defectContent` (lines 873-914), allowing stored XSS/injection content to flow into downstream board rendering and exports. | Internal Network | DF40          | Sanitize/normalize persisted defect fields; escape at render time.                               | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                             |
| ---------------------- | ------------------------------------------------------------------------- |
| Spoofing               | Polling job has no inbound identity surface.                              |
| Tampering              | Data source is the AK/SK-signed Huawei API.                               |
| Repudiation            | No user-facing action.                                                    |
| Denial of Service      | Polling is CAS-guarded (compareAndSetProcessing line 163); single-runner. |
| Elevation of Privilege | Runs as the standard non-root app user.                                   |
| Abuse                  | No feature misuse beyond covered data-integrity issues.                   |

---

## SaveIncTaskResult

**Trust Boundary:** CodecheckService
**Role:** Scheduled job polling incremental gate results, decrypting account tokens, git platform operations, saving results, email notifications
**Data Flows:** DF43, DF44, DF45, DF46, DF47, DF48
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                        | Prerequisites    | Affected Flow    | Mitigation                                                                                                   | Status |
| ----- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------- | ------------------------------------------------------------------------------------------------------------ | ------ |
| T13.1 | Information Disclosure | HTML injection in gate-notification emails: `sendExceedThresholdEmail` interpolates `taskIncEntity.getId()`, `getMrUrl()`, triggerTime (lines 268-285) and `executionDurationJudgment` concatenates projectName/mrUrl/triggerTime (lines 444-448) into unsanitized HTML bodies; attacker-influenced MR data can inject HTML/phishing content. | Internal Network | DF48             | HTML-escape interpolated fields; use a templating engine.                                                    | Open   |
| T13.2 | Abuse                  | Token-based repo operations on spoofable task data: decrypted account tokens (`SecurityHelper.decrypt(restCodeCheckUtil.getAccountToken(gitUrl, accountInfo))`, lines 307-320) drive git platform operations for task-supplied git URLs; tampered task records could redirect token use or trigger unwanted platform calls.                   | Internal Network | DF45, DF46, DF47 | Validate git URL against registered repos before using tokens; bind token use to authenticated task origins. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| Spoofing               | Polling job has no inbound identity surface.                                                                 |
| Tampering              | Result data from AK/SK-signed Huawei API; details are fragment-encrypted before insert (FragmentCryptoUtil). |
| Repudiation            | No user-facing action.                                                                                       |
| Denial of Service      | CAS-guarded (compareAndSetProcessing line 334); single-runner.                                               |
| Elevation of Privilege | Runs as the standard non-root app user.                                                                      |

---

## CodeCheckEventConsumer

**Trust Boundary:** CodecheckService
**Role:** RabbitMQ consumer for full/inc code-check events
**Data Flows:** DF16
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                    | Prerequisites    | Affected Flow | Mitigation                                             | Status |
| ----- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------ | ------ |
| T14.1 | Information Disclosure | Raw dead-letter content logged: `handleDeadLetterEvent` logs the raw dead-letter message (lines 124-127); if task records or sensitive payloads enter the dead-letter queue, their content lands in logs. | Internal Network | DF16          | Truncate/sanitize dead-letter payloads before logging. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                          |
| ---------------------- | -------------------------------------------------------------------------------------- |
| Spoofing               | Message IDs are plain strings looked up in MongoDB; no identity claim.                 |
| Tampering              | No message-body deserialization (plain String record IDs); CAS guards task processing. |
| Repudiation            | No user-facing action.                                                                 |
| Denial of Service      | Concurrency bounded (5); CAS prevents duplicate processing; Redis rate-limit on 429.   |
| Elevation of Privilege | Runs as the standard non-root app user.                                                |
| Abuse                  | No feature misuse beyond covered logging issue.                                        |

---

## StaticAlarmEventConsumer

**Trust Boundary:** CodecheckService
**Role:** RabbitMQ consumer for static-alarm parse events
**Data Flows:** DF17
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category          | Threat                                                                                                                                                                                                                                                                                        | Prerequisites    | Affected Flow | Mitigation                                                                                                               | Status |
| ----- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------ | ------ |
| T15.1 | Denial of Service | Unbounded SARIF download: SarifParseServiceImpl downloads the persisted `obsUrl` via `URI.create(obsUrl).toURL().openStream()` (line 160) with no content-length cap, no byte limit, and no connect/read timeout; a malicious or oversized URL causes memory exhaustion in the Jackson parse. | Internal Network | DF17          | Enforce max download size and timeouts; stream with a bounded reader; validate URL against an allowlist before download. | Open   |
| T15.2 | Abuse             | No duplicate-parse protection: the consumer runs with concurrency 1-3 and takes no Redisson lock; duplicate parse events cause repeated OBS downloads, re-parses, and repeated MongoDB upserts, inflating cost and state churn.                                                               | Internal Network | DF17          | Add idempotency/lock keyed on scanRunId; skip already-parsed runs.                                                       | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                                                     |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Spoofing               | No identity claim; source is the persisted scan-run record.                                                       |
| Tampering              | SARIF parsed into fixed `SarifSchema210` class (no autotype); tool whitelist applied.                             |
| Repudiation            | No user-facing action.                                                                                            |
| Information Disclosure | SSRF/data exposure path is covered under SarifParseServiceImpl (T18.1); consumer itself only reads the record ID. |
| Elevation of Privilege | Runs as the standard non-root app user.                                                                           |

---

## ShieldAllConsumer

**Trust Boundary:** CodecheckService
**Role:** RabbitMQ consumer for bulk defect shielding
**Data Flows:** DF18
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                   | Prerequisites    | Affected Flow | Mitigation                                                                                                                                        | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T16.1 | Abuse                  | Message-trusted identity for bulk state changes: `ShieldAllMessage` carries `userId`/`op`/`type`/scope (entity lines 20-39) published by CheckboardController from client-supplied values; the consumer performs mass defect shielding and notifies users, so a forged/forged-userId message within the broker causes unauthorized bulk shielding and notification spam. | Internal Network | DF18          | Re-validate the operator identity and permission at consume time; bind messages to authenticated callers; verify count/scope against source data. | Open   |
| T16.2 | Information Disclosure | HTML injection in shield notification email: `sendEmail` builds body as `"<html>...详情可见：" + detailUrl + "</body></html>"` (lines 1566-1567) without escaping `detailUrl`, enabling HTML injection into recipient mail clients.                                                                                                                                      | Internal Network | DF18          | HTML-escape detailUrl and all interpolated fields.                                                                                                | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------------------------- |
| Spoofing               | Identity spoofing is the mechanism of T16.1 (Abuse).                                                      |
| Tampering              | Jackson class-based deserialization (no autotype); scope validation at enqueue (lines 2147-2172).         |
| Repudiation            | Shield actions recorded in `message_apply`/`message_notice` but not bound to real authenticated identity. |
| Denial of Service      | Redisson running-lock prevents duplicate concurrent runs (lines 2064-2071).                               |
| Elevation of Privilege | Bulk shielding impact is covered by T16.1 (Abuse).                                                        |

---

## StaticAlarmExportConsumer

**Trust Boundary:** CodecheckService
**Role:** RabbitMQ consumer for alarm export tasks and file delivery via OpenlibingFramework
**Data Flows:** DF19, DF35, DF36
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                         | Prerequisites    | Affected Flow | Mitigation                                                                                                                    | Status |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| T17.1 | Information Disclosure | Stored query-DTO tampering alters export scope: `StaticAlarmServiceImpl.processExport` deserializes the stored export query `StaticAlarmQueryDTO` from the framework `obs_file` record (lines 1211-1217) and exports matching defects; tampering with the stored DTO or the originating record changes which defect data is exported to files. | Internal Network | DF35          | Verify the export query/scope against the requesting user's permissions before export; authenticate the export record origin. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| Spoofing               | Message is an integer record ID; no identity claim.                                       |
| Tampering              | Class-based Jackson deserialization (no autotype); CAS transitions via framework service. |
| Repudiation            | Export status transitions are framework-CAS tracked.                                      |
| Denial of Service      | Concurrency bounded (5); temp files auto-deleted.                                         |
| Elevation of Privilege | Runs as the standard non-root app user.                                                   |
| Abuse                  | Export-scope manipulation is the intent of T17.1.                                         |

---

## SarifParseServiceImpl

**Trust Boundary:** CodecheckService
**Role:** SARIF parsing service (CodeQL parser), OBS download, MongoDB writes
**Data Flows:** DF49, DF50
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | Prerequisites    | Affected Flow | Mitigation                                                                                                                          | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T18.1 | Information Disclosure | SSRF via server-side URL fetch: `downloadAndParse` executes `URI.create(obsUrl).toURL().openStream()` (line 160) where `obsUrl` originates from the request bodies of the unauthenticated receive endpoints (StaticAlarmReceiveController /internal/codescan + /codescan), with no scheme/host allowlist, no redirect policy, and no timeout; an in-cluster caller can make the service fetch arbitrary internal endpoints (metadata, internal services) and parse the response. | Internal Network | DF49          | Validate obsUrl against an allowed OBS domain allowlist; block private/internal IP ranges and redirects; add connect/read timeouts. | Open   |
| T18.2 | Denial of Service      | Unbounded download/parse: no content-length or byte cap on the SARIF InputStream fed to Jackson (lines 160-161) and no result/message size bounds in CodeQlSarifParser (only per-result threadFlow locations capped at 30, lines 57, 321-331); oversized SARIF causes memory exhaustion.                                                                                                                                                                                         | Internal Network | DF49          | Enforce max download size, max parse elements, and timeouts; stream with a bounded reader.                                          | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------- |
| Spoofing               | No identity claim; input is the persisted scan-run record.                                                    |
| Tampering              | Jackson fixed-class deserialization (no autotype); tool whitelist via `parserFactory.isSupported` (line 142). |
| Repudiation            | No user-facing action.                                                                                        |
| Elevation of Privilege | Runs as the standard non-root app user.                                                                       |
| Abuse                  | URL-fetch misuse is the intent of T18.1 (Information Disclosure/SSRF).                                        |

---

## ObsBucketServiceImpl

**Trust Boundary:** CodecheckService
**Role:** Huawei OBS bucket file service (file create/query/update)
**Data Flows:** DF51
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                                      | Prerequisites    | Affected Flow | Mitigation                                                                                | Status |
| ----- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ----------------------------------------------------------------------------------------- | ------ |
| T19.1 | Information Disclosure | Missing object-key validation: `uploadFile`/`deleteObject`/`getObject` pass the caller-supplied `objectKey` straight to the OBS SDK with no key-format or scope validation (lines 88-129), so any caller with service access could address any object in the single configured bucket; current in-repo callers generate keys server-side (date+UUID, StaticAlarmServiceImpl lines 1020-1021), making this defense-in-depth. | Internal Network | DF51          | Enforce an object-key namespace/pattern allowlist; scope operations to the export prefix. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                    |
| ---------------------- | -------------------------------------------------------------------------------- |
| Spoofing               | No identity surface.                                                             |
| Tampering              | No mutation of request data beyond OBS object content it is authorized to write. |
| Repudiation            | No user-facing action.                                                           |
| Denial of Service      | No unbounded operation; AK/SK decrypted at construction only.                    |
| Elevation of Privilege | Runs as the standard non-root app user.                                          |
| Abuse                  | Object-key misuse is the intent of T19.1.                                        |

---

## MongoDB

**Trust Boundary:** ClusterServices
**Role:** Document store for check summaries, details, alarms, webhook events, logs
**Data Flows:** DF20, DF21, DF24, DF26, DF28, DF31-DF35, DF40, DF43, DF50
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category  | Threat                                                                                                                                                                                                                                                                                                                                                     | Prerequisites    | Affected Flow | Mitigation                                                                                                 | Status |
| ----- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ---------------------------------------------------------------------------------------------------------- | ------ |
| T20.1 | Tampering | TLS hostname verification disabled: `MongoConfig` sets `builder.enabled(true)` (SSL on) but also `builder.invalidHostNameAllowed(true)` (lines 66-70) with an inline comment "not recommended for production"; the client does not verify the MongoDB server hostname, enabling MITM/eavesdropping on the MongoDB connection within the cluster (CWE-295). | Internal Network | DF20-DF50     | Set `invalidHostNameAllowed(false)`; pin the MongoDB server certificate/CA; enforce hostname verification. | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                   | Prerequisites      | Affected Flow | Mitigation                                                                                                | Status |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | --------------------------------------------------------------------------------------------------------- | ------ |
| T20.2 | Elevation of Privilege | Single shared account, no least privilege: the application uses one decrypted MongoDB credential for all collections and operations; any application compromise or DB account leak grants full read/write over all scan/defect/alarm data with no per-collection or per-role separation. | MongoDB Compromise | DF20-DF50     | Use separate MongoDB roles/users per function; enable MongoDB RBAC; scope credentials to least privilege. | Open   |

#### Categories Not Applicable

| Category               | Justification                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| Spoofing               | Auth is via decrypted credentials at connection time; no per-session identity surface.                 |
| Repudiation            | No user-facing action; Mongo ops are application-driven.                                               |
| Information Disclosure | Data exposure paths are covered under the controllers that query it (e.g., T09.2).                     |
| Denial of Service      | No attacker-controlled unbounded query reaching the datastore beyond controller paths already covered. |
| Abuse                  | No business feature directly on the datastore.                                                         |

---

## MySQL

**Trust Boundary:** ClusterServices
**Role:** Relational store for users, roles, permissions, projects, repos, branches, pre-commit records
**Data Flows:** DF22, DF30, DF38
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category  | Threat                                                                                                                                                                                                                                                                                                                               | Prerequisites    | Affected Flow | Mitigation                                                                                         | Status |
| ----- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- | ------------- | -------------------------------------------------------------------------------------------------- | ------ |
| T21.1 | Tampering | Transport encryption depends on config: `DataSourceConfig` decrypts the password (line 73) but configures no TLS in code — the JDBC URL (`spring.datasource.url`) comes from the config center; if the URL does not enforce `useSSL`/TLS, MySQL traffic (including queries over roles/permissions) travels plaintext in the cluster. | Internal Network | DF30, DF38    | Enforce TLS/SSL in the JDBC URL (`useSSL=true&requireSSL=true`); verify via config and connection. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                                                                |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Spoofing               | Auth via decrypted credentials at connection time.                                                                           |
| Repudiation            | No user-facing action.                                                                                                       |
| Information Disclosure | Role/permission data disclosure paths are covered under controllers/AuthUtils.                                               |
| Denial of Service      | No attacker-controlled unbounded query.                                                                                      |
| Elevation of Privilege | Single Hikari pool account for all app data; least-privilege separation is a platform concern (documented in T20.2 pattern). |
| Abuse                  | No business feature directly on the datastore.                                                                               |

---

## Redis

**Trust Boundary:** ClusterServices
**Role:** Cache, Redisson locks, Excel task state, rule-set queues, AK/SK cache
**Data Flows:** DF25, DF37
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                    | Prerequisites    | Affected Flow | Mitigation                                                                                                                                              | Status |
| ----- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T22.1 | Information Disclosure | Credential ciphertext at rest in Redis queues: `RuleSetScheduleTask` persists `{region, akSkVo}` (ciphertext AK/SK) in Redis list `rule_set:languages_severity_rule_set_task_queue` (lines 319-331) and task status markers are set; SSL is enabled for Jedis (`useSsl()`, lines 67-73) and Redisson (`rediss://`, line 102), but a Redis compromise exposes encrypted credential material and task data. | Redis Compromise | DF37          | Avoid persisting credential material in Redis; if needed, use short TTLs and encrypt at a separate layer; restrict Redis access via ACL/network policy. | Open   |

#### Categories Not Applicable

| Category               | Justification                                                                                                         |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Spoofing               | No inbound identity surface.                                                                                          |
| Tampering              | No attacker-controlled writes reach Redis directly; app-driven keys.                                                  |
| Repudiation            | No user-facing action.                                                                                                |
| Denial of Service      | No attacker-controlled unbounded operation; RedisHelper bounds key patterns (`del` rejects wildcards, lines 194-197). |
| Elevation of Privilege | Runs as the standard non-root app user.                                                                               |
| Abuse                  | No business feature directly on the datastore.                                                                        |

---

## RabbitMQ

**Trust Boundary:** ClusterServices
**Role:** Message broker for full/inc code-check tasks, static alarm parse/export, shield-all batch ops
**Data Flows:** DF13-DF19
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category  | Threat                                                                                                                                                                                                                                                                                                                                                 | Prerequisites    | Affected Flow | Mitigation                                                                                                     | Status |
| ----- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- | ------------- | -------------------------------------------------------------------------------------------------------------- | ------ |
| T23.1 | Tampering | Plaintext AMQP outside prod: `RabbitConnectionFactoryConfig` enables SSL only when `spring.profiles.active == "prod"` (`useSslProtocol()`, lines 57-60); beta/gama/icsl profiles inherit port 5672 and connect without TLS, so task/alarm messages travel in cleartext across the cluster and can be read or tampered with by any in-cluster observer. | Internal Network | DF13-DF19     | Enable AMQPS (TLS) for all non-local profiles; enforce TLS via config; consider message signing for integrity. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                     |
| ---------------------- | --------------------------------------------------------------------------------- |
| Spoofing               | Broker auth via decrypted credentials; message source is app producers.           |
| Repudiation            | No user-facing action.                                                            |
| Information Disclosure | Message content exposure is a consequence of T23.1 (Tampering/cleartext).         |
| Denial of Service      | No attacker-controlled unbounded publish path beyond controllers already covered. |
| Elevation of Privilege | Runs as the standard non-root app user.                                           |
| Abuse                  | Message-driven misuse is covered under consumers (e.g., T16.1).                   |

---

## OpenlibingCicd

**Trust Boundary:** ClusterServices
**Role:** CI/CD microservice (Feign HTTPS); delivers static-alarm scan results to `/codescan/v1/result/receive`
**Data Flows:** DF12, DF54
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category  | Threat                                                                                                                                                                                                                                                                                          | Prerequisites    | Affected Flow | Mitigation                                                                                        | Status |
| ----- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------- | ------ |
| T24.1 | Tampering | Scan results delivered without integrity verification: the CICD service posts scan results to `/codescan/v1/result/receive` over plain service-to-service HTTP with no signature or mutual auth, so tampered scan results (altered SARIF/obsUrl) would be accepted and parsed as authoritative. | Internal Network | DF12          | Add message signature/HMAC or mTLS between CICD and codecheck; verify pipeline context integrity. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                |
| ---------------------- | ---------------------------------------------------------------------------- |
| Spoofing               | Source is a fixed sibling service; identity not verified (covered by T24.1). |
| Repudiation            | No user-facing action.                                                       |
| Information Disclosure | No data disclosure from this component.                                      |
| Denial of Service      | No attacker-controlled unbounded interaction.                                |
| Elevation of Privilege | External service, managed by another team.                                   |
| Abuse                  | No business feature directly exposed.                                        |

---

## OpenlibingFramework

**Trust Boundary:** ClusterServices
**Role:** Framework microservice (Feign HTTPS); export file delivery and export-task state
**Data Flows:** DF36
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category | Threat                                                                                                                                                                                                                                        | Prerequisites    | Affected Flow | Mitigation                                                         | Status |
| ----- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------ | ------ |
| T25.1 | Spoofing | No mutual auth on Feign calls: `openlibingFrameworkClient` calls are HTTPS but not mutually authenticated; an in-cluster actor could impersonate the framework service and return forged export-task state, altering the CAS export workflow. | Internal Network | DF36          | Enable mTLS/service-account identity verification for Feign calls. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                        |
| ---------------------- | ---------------------------------------------------- |
| Tampering              | No data mutation by this client beyond export state. |
| Repudiation            | No user-facing action.                               |
| Information Disclosure | No data disclosure from this component.              |
| Denial of Service      | No attacker-controlled unbounded interaction.        |
| Elevation of Privilege | External service, managed by another team.           |
| Abuse                  | No business feature directly exposed.                |

---

## OpenlibingCoderepo

**Trust Boundary:** ClusterServices
**Role:** Code-repo microservice (metrics Feign); calls back `/internal/**` endpoints
**Data Flows:** DF11, DF23
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category | Threat                                                                                                                                                                                                                                               | Prerequisites    | Affected Flow | Mitigation                                                                                             | Status |
| ----- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------ | ------ |
| T26.1 | Spoofing | Internal callbacks unauthenticated: `openlibing-coderepo` calls `/internal/**` (rule-set recompute, full task invoke) with no credential, so the trust relationship can be impersonated by any in-cluster actor to trigger recompute/full-scan work. | Internal Network | DF11          | Authenticate sibling-service callbacks (mTLS/service token); verify caller identity in `/internal/**`. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                |
| ---------------------- | ------------------------------------------------------------ |
| Tampering              | No data mutation by this client beyond triggered callbacks.  |
| Repudiation            | No user-facing action.                                       |
| Information Disclosure | Metrics data disclosure is covered under controllers (DF23). |
| Denial of Service      | No attacker-controlled unbounded interaction.                |
| Elevation of Privilege | External service, managed by another team.                   |
| Abuse                  | No business feature directly exposed.                        |

---

## XxlJob

**Trust Boundary:** ClusterServices
**Role:** Distributed job scheduler for scheduled task dispatch
**Data Flows:** DF53
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

| ID    | Category | Threat                                                                                                                                                                                                                                                                                                                                | Prerequisites    | Affected Flow | Mitigation                                                                                              | Status |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------- | ------------------------------------------------------------------------------------------------------- | ------ |
| T27.1 | Spoofing | Weak/absent executor accessToken: `xxl.job.admin.accessToken` is injected from config (`XxlJobConfig` lines 27-28, set on the executor line 58); if the token is empty or weak, an in-cluster actor can register a spoofed executor or dispatch forged jobs (e.g., `lintRunnerChecksHandler`, rule-sync handlers) to the application. | Internal Network | DF53          | Enforce a strong, rotated accessToken for executor registration; restrict xxl-job admin network access. | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified._

#### Categories Not Applicable

| Category               | Justification                                                                     |
| ---------------------- | --------------------------------------------------------------------------------- |
| Tampering              | Job params are sanitized (CommandArgSanitizer) before reaching command execution. |
| Repudiation            | No user-facing action.                                                            |
| Information Disclosure | No data disclosure from this component.                                           |
| Denial of Service      | No attacker-controlled unbounded interaction.                                     |
| Elevation of Privilege | External service, managed by another team.                                        |
| Abuse                  | Job-trigger misuse is the intent of T27.1 (Spoofing).                             |

---

## Nacos

**Trust Boundary:** ExternalServices
**Role:** Huawei CSE Nacos config/discovery server (holds `security.part1` key and all encrypted credentials)
**Data Flows:** DF10, DF52
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                      | Prerequisites     | Affected Flow | Mitigation                                                                                                                                                            | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T28.1 | Information Disclosure | Key/ciphertext co-location: the AES key `security.part1` and every encrypted secret (datasource, mongo, redis, rabbitmq, git tokens, AK/SK) reside in the same Nacos group/namespace (OPENLIBING); one Nacos read compromise yields both key and ciphertexts, defeating encryption at rest. | Admin Credentials | DF10, DF52    | Store the key in a dedicated secrets manager with independent ACLs and rotation; split sensitive config from application config; enable Nacos ACL/encryption-at-rest. | Open   |

#### Categories Not Applicable

| Category               | Justification                                                           |
| ---------------------- | ----------------------------------------------------------------------- |
| Spoofing               | Config poisoning is covered under OpenlibingCodecheckApplication T01.1. |
| Tampering              | Config tampering impact is covered under T01.1.                         |
| Repudiation            | No user-facing action.                                                  |
| Denial of Service      | Nacos availability is an external dependency.                           |
| Elevation of Privilege | External managed service (Huawei CSE).                                  |
| Abuse                  | No business feature directly exposed.                                   |

---

## HuaweiOBS

**Trust Boundary:** ExternalServices
**Role:** Huawei Cloud Object Storage holding SARIF scan results and export files
**Data Flows:** DF49, DF51
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                          | Prerequisites     | Affected Flow | Mitigation                                                                                     | Status |
| ----- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- | ---------------------------------------------------------------------------------------------- | ------ |
| T29.1 | Information Disclosure | OBS AK/SK from config: bucket access uses `${obs.access-key-id}`/`${obs.secret-access-key}` decrypted from config (ObsBucketServiceImpl lines 42-52, 164-165); a config/credential leak exposes all SARIF scan artifacts and export files in the single bucket. | Admin Credentials | DF49, DF51    | Rotate OBS AK/SK; use STS short-lived credentials; restrict bucket ACL to the service account. | Open   |

#### Categories Not Applicable

| Category               | Justification                                            |
| ---------------------- | -------------------------------------------------------- |
| Spoofing               | External managed service.                                |
| Tampering              | Object writes are app-driven with server-generated keys. |
| Repudiation            | No user-facing action.                                   |
| Denial of Service      | External managed service.                                |
| Elevation of Privilege | External managed service.                                |
| Abuse                  | No business feature directly exposed.                    |

---

## HuaweiApiG

**Trust Boundary:** ExternalServices
**Role:** Huawei Cloud API Gateway fronting `/apig/v1/**` with gateway auth, rate limiting, audit
**Data Flows:** DF06, DF07
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                              | Prerequisites     | Affected Flow | Mitigation                                                                                | Status |
| ----- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- | ----------------------------------------------------------------------------------------- | ------ |
| T30.1 | Elevation of Privilege | Single point of auth: the entire `/apig/v1/**` boundary trusts the APIG gateway for authentication/rate limiting/audit; a gateway misconfiguration, AppCode leak, or bypass would expose unauthenticated M2M endpoints (task trigger, status read). | Admin Credentials | DF06, DF07    | Add an in-code secondary auth barrier; monitor gateway config; restrict AppCode rotation. | Open   |

#### Categories Not Applicable

| Category               | Justification                                                                      |
| ---------------------- | ---------------------------------------------------------------------------------- |
| Spoofing               | Gateway authentication is external (Platform); spoofing is the mechanism of T30.1. |
| Tampering              | Gateway-managed traffic.                                                           |
| Repudiation            | Gateway provides caller audit (Platform).                                          |
| Information Disclosure | Gateway traffic confidentiality is external (Platform).                            |
| Denial of Service      | Rate limiting is gateway-provided (Platform).                                      |
| Abuse                  | API misuse is the intent of T30.1.                                                 |

---

## HuaweiCodeCheck

**Trust Boundary:** ExternalServices
**Role:** Huawei Cloud CodeCheck service executing actual code scans; accessed via APIG SDK with AK/SK signing
**Data Flows:** DF27, DF29, DF39, DF41, DF44
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                                          | Prerequisites     | Affected Flow                | Mitigation                                                                                                                                                                                              | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T31.1 | Information Disclosure | AK/SK dependency: scan delegation, rule sync, and result polling use tenant AK/SK (`CodeCheckOrganization`, decrypted at signing in `RestCodeCheckUtil` lines 525-526); an AK/SK leak grants control of scan creation, rule-set sync, and full result readback for all tenants. | Admin Credentials | DF27, DF29, DF39, DF41, DF44 | Rotate AK/SK; enforce per-tenant scoping; avoid logging credential-bearing request objects (`logger.error("...result : {}", request.get())` lines 167, 209, 751, 797-800, 838, 1001, 1080, 1193, 1356). | Open   |

#### Categories Not Applicable

| Category               | Justification                                              |
| ---------------------- | ---------------------------------------------------------- |
| Spoofing               | Requests are AK/SK-signed (Mitigated by request signing).  |
| Tampering              | Signed requests prevent tampering (Platform/API SDK).      |
| Repudiation            | API audit is provider-side (Platform).                     |
| Denial of Service      | Provider-side rate limits (Platform).                      |
| Elevation of Privilege | External managed service.                                  |
| Abuse                  | Scan-quota misuse via leaked AK/SK is the intent of T31.1. |

---

## GitCode

**Trust Boundary:** ExternalServices
**Role:** GitCode platform API (account tokens; PR info, comments)
**Data Flows:** DF45, DF55
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                        | Prerequisites     | Affected Flow | Mitigation                                                                                          | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- | --------------------------------------------------------------------------------------------------- | ------ |
| T32.1 | Information Disclosure | Access tokens in URL query parameters: GitCodeHelper appends `?access_token=<decrypted token>` to API URLs (lines 89-93, 135, 222-223); tokens can leak via proxy/access logs, browser history, or Referer headers (CWE-598). | Admin Credentials | DF45, DF55    | Send tokens via Authorization header instead of query params; ensure HTTP client does not log URLs. | Open   |

#### Categories Not Applicable

| Category               | Justification                                            |
| ---------------------- | -------------------------------------------------------- |
| Spoofing               | Token-based auth to the platform is standard (Platform). |
| Tampering              | Platform-managed.                                        |
| Repudiation            | Platform-managed audit.                                  |
| Denial of Service      | Platform-managed.                                        |
| Elevation of Privilege | Token scope is platform-managed.                         |
| Abuse                  | Token misuse via leakage is the intent of T32.1.         |

---

## Gitee

**Trust Boundary:** ExternalServices
**Role:** Gitee platform API (account tokens; role data drives AuthUtils)
**Data Flows:** DF46
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                            | Prerequisites     | Affected Flow | Mitigation                                                     | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- | -------------------------------------------------------------- | ------ |
| T33.1 | Information Disclosure | Access tokens in URL query parameters: GiteeHelper appends `?access_token=<decrypted token>` to API URLs (lines 70-71, 145-150); tokens can leak via logs, browser history, or Referer (CWE-598). | Admin Credentials | DF46          | Send tokens via Authorization header; avoid logging full URLs. | Open   |

#### Categories Not Applicable

| Category               | Justification                                     |
| ---------------------- | ------------------------------------------------- |
| Spoofing               | Token-based auth is platform-standard (Platform). |
| Tampering              | Platform-managed.                                 |
| Repudiation            | Platform-managed audit.                           |
| Denial of Service      | Platform-managed.                                 |
| Elevation of Privilege | Token scope is platform-managed.                  |
| Abuse                  | Token misuse via leakage is the intent of T33.1.  |

---

## Github

**Trust Boundary:** ExternalServices
**Role:** GitHub platform API (account tokens)
**Data Flows:** DF47
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                                                                                                                                                                                                   | Prerequisites     | Affected Flow | Mitigation                                                                                                                    | Status |
| ----- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| T34.1 | Abuse    | Inconsistent GitHub token handling: `GithubPlate.getAccessToken` returns `accountInfo.getGithubAccessToken()` without `SecurityHelper.decrypt` (lines 60-63), and `getAccountInfo` never populates the github token (CodeCheckOrganization lines 148-153), so GitHub flows may use an un-decrypted/empty token, causing functional mis-credential usage and masking the real auth state. | Admin Credentials | DF47          | Align GitHub token decryption with other platforms; populate/persist github token consistently; fail closed on missing token. | Open   |

#### Categories Not Applicable

| Category               | Justification                                                 |
| ---------------------- | ------------------------------------------------------------- |
| Spoofing               | Token-based auth is platform-standard (Platform).             |
| Tampering              | Platform-managed.                                             |
| Repudiation            | Platform-managed audit.                                       |
| Information Disclosure | No token-in-URL pattern in GithubHelper (no HTTP operations). |
| Denial of Service      | Platform-managed.                                             |
| Elevation of Privilege | Token scope is platform-managed.                              |

---

## SmtpServer

**Trust Boundary:** ExternalServices
**Role:** SMTP email server for task result and audit notifications
**Data Flows:** DF42, DF48
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._

#### Tier 2 — Conditional Risk

_No Tier 2 threats identified._

#### Tier 3 — Defense-in-Depth

| ID    | Category  | Threat                                                                                                                                                                                                                                                         | Prerequisites     | Affected Flow | Mitigation                                                                                                                   | Status |
| ----- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------ |
| T35.1 | Tampering | SMTP without TLS: `EmailUtil.sendEmail` configures only `mail.smtp.auth=true` with no STARTTLS/TLS property (lines 67-71), so the sender password (decrypted config `commom.email.password`) and email bodies are transmitted to the mail server in plaintext. | Admin Credentials | DF42, DF48    | Enable STARTTLS/TLS (`mail.smtp.starttls.enable=true` / `mail.smtp.ssl.enable=true`); enforce server certificate validation. | Open   |

#### Categories Not Applicable

| Category               | Justification                                                                  |
| ---------------------- | ------------------------------------------------------------------------------ |
| Spoofing               | External managed service.                                                      |
| Repudiation            | No user-facing action beyond email delivery.                                   |
| Information Disclosure | Email content confidentiality is a consequence of T35.1 (plaintext transport). |
| Denial of Service      | External managed service.                                                      |
| Elevation of Privilege | External managed service.                                                      |
| Abuse                  | No business feature directly exposed.                                          |
