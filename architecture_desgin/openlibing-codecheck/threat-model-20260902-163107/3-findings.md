# Security Findings

---

## Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 findings identified for this repository._

---

## Tier 2 — Conditional Risk (Authenticated / Single Prerequisite)

### FIND-01: Missing code-level authentication on M2M `/apig/v1/**` endpoints

| Attribute                  | Value                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                |
| CVSS 4.0                   | 7.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N)                                    |
| CWE                        | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                    |
| Exploitation Prerequisites | Authenticated User (Huawei APIG gateway credential)                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                |
| Remediation Effort         | Medium                                                                                                   |
| Mitigation Type            | Custom Mitigation                                                                                        |
| Component                  | HwApigController                                                                                         |
| Related Threats            | [T02.1](2-stride-analysis.md#hwapigcontroller), [T30.1](2-stride-analysis.md#huaweiapig)                 |

#### Description

All four `/apig/v1/**` endpoints (`full/task/result/summary`, `full/task`, `v1/task/status`, `v1/task`) perform no in-code authentication; authentication is delegated entirely to the Huawei APIG gateway (javadoc lines 29-31). A gateway misconfiguration, weak AppCode, or gateway bypass exposes unauthenticated task-trigger and status-read capabilities.

#### Evidence

**Prerequisite basis:** `HwApigController` reachability is `External (via HuaweiApiG)` with `Auth Required = No` in the Component Exposure Table; the gateway is the only barrier, so the prerequisite is `Authenticated User` (T2).

`HwApigController.java` lines 69-141: no `AuthUtils`/token/interceptor on any endpoint; `QueryTaskSummaryMachineApiModel` (lines 36-98) has zero validation annotations; javadoc lines 29-31 state "由华为云 APIG 网关统一鉴权、限流、调用方审计".

#### Remediation

- Add a secondary in-code auth barrier (HMAC request signing, API-key, or token validation) on every `/apig/v1/**` endpoint.
- Bind machine callers to registered projects and validate ownership before acting.
- Audit gateway AppCode issuance and rotation.

#### Verification

- Send a request to `/apig/v1/**` without a gateway credential and confirm it is rejected by code (not just the gateway).
- Confirm every endpoint validates an app-level credential.

---

### FIND-02: Unauthenticated internal & machine endpoints allow unauthorized task triggers

| Attribute                  | Value                                                                                                                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                                                                             |
| CVSS 4.0                   | 8.0 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N)                                                                                                                                                 |
| CWE                        | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function                                                                                                              |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                                                                                                                                 |
| Exploitation Prerequisites | Internal Network                                                                                                                                                                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                                                                                                             |
| Remediation Effort         | Medium                                                                                                                                                                                                                |
| Mitigation Type            | Custom Mitigation                                                                                                                                                                                                     |
| Component                  | InternalController                                                                                                                                                                                                    |
| Related Threats            | [T04.1](2-stride-analysis.md#internalcontroller), [T06.1](2-stride-analysis.md#internalcodefullcontroller), [T07.1](2-stride-analysis.md#internalcodeinccontroller), [T26.1](2-stride-analysis.md#openlibingcoderepo) |

#### Description

The `/internal/**`, `/ci-portal/webhook/codecheck/full/**`, and `/ci-portal/webhook/codecheck/v1/**` endpoints rely on "service-to-service trust" with no credential. Any in-cluster pod can trigger full scans, incremental gate tasks, and pre-commit pipeline runs for arbitrary repo URLs, and can read gate status by `uuid` (a capability value).

#### Evidence

**Prerequisite basis:** All three controllers have `Reachability = Internal Only` and `Auth Required = No` in the Component Exposure Table → prerequisite `Internal Network` (T2).

`InternalController.java` lines 76-79 (javadoc: "本内部端点走服务间信任...不重复鉴权"); `InternalCodeFullController.java` lines 47-55 (blank-check only, no format whitelist); `InternalCodeIncController.java` lines 60-89; `IncTaskOperation.java` lines 73-79 (status lookup by uuid with no auth).

#### Remediation

- Enforce mutual authentication (mTLS or service token) on all `/internal/**` and machine endpoints.
- Bind task creation and status queries to authenticated, repo-scoped callers; do not treat `uuid` as the sole credential.

#### Verification

- Attempt to call `/internal/full/invoke/task`, `/ci-portal/webhook/codecheck/full/task`, and `/ci-portal/webhook/codecheck/v1/task/status` without any credential and confirm rejection.

---

### FIND-03: Missing authorization on portal/board/webhook read endpoints

| Attribute                  | Value                                                                                                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                 |
| CVSS 4.0                   | 7.2 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N)                                                                                     |
| CWE                        | [CWE-862](https://cwe.mitre.org/data/definitions/862.html): Missing Authorization                                                                         |
| OWASP                      | A01:2025 – Broken Access Control                                                                                                                          |
| Exploitation Prerequisites | Internal Network                                                                                                                                          |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                                                 |
| Remediation Effort         | Medium                                                                                                                                                    |
| Mitigation Type            | Custom Mitigation                                                                                                                                         |
| Component                  | CheckboardController                                                                                                                                      |
| Related Threats            | [T03.1](2-stride-analysis.md#webhookcontroller), [T08.1](2-stride-analysis.md#filedownloadcontroller), [T09.2](2-stride-analysis.md#checkboardcontroller) |

#### Description

Of 8 FileDownLoadController export endpoints, only `/rule/set` and `/rule/set/export` call `AuthUtils.checkPermission`; `/download/log` (which fetches Huawei task logs) and the summary/rule export endpoints have no check. The WebhookController MongoDB query endpoint and the 13 CheckboardController read endpoints also perform no authorization. In-cluster callers can read task results, defect data, and rule data without permission.

#### Evidence

**Prerequisite basis:** Controllers have `Reachability = Internal Only`, `Auth Required = No` (or per-endpoint) in the Component Exposure Table → `Internal Network` (T2).

`FileDownLoadController.java` lines 129-133 (only `/rule/set` guarded) and lines 155-161; `/download/log` lines 184-194 unguarded → `RestCodeCheckUtil.showTaskLog` (FileDownloadDelegateImpl lines 713-719). `WebhookController.java` lines 36-39. `CheckboardController.java` lines 46-249 (no controller-level auth).

#### Remediation

- Add a consistent authorization filter/interceptor covering all portal and webhook endpoints.
- Require repo-level permission checks before serving task logs, defect details, and rule sets.

#### Verification

- Call `/ci-portal/excel/v1/download/log`, `/ci-portal/v1/codecheck/getDetailNum`, and the webhook query endpoint without any permission and confirm rejection.

---

### FIND-04: Client-supplied identity enables authorization bypass

| Attribute                  | Value                                                                                                                                                                                              |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Critical                                                                                                                                                                                           |
| CVSS 4.0                   | 8.7 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N)                                                                                                                              |
| CWE                        | [CWE-639](https://cwe.mitre.org/data/definitions/639.html): Authorization Bypass Through User-Controlled Key                                                                                       |
| OWASP                      | A01:2025 – Broken Access Control                                                                                                                                                                   |
| Exploitation Prerequisites | Internal Network                                                                                                                                                                                   |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                                                                                          |
| Remediation Effort         | Medium                                                                                                                                                                                             |
| Mitigation Type            | Redesign                                                                                                                                                                                           |
| Component                  | AuthUtils                                                                                                                                                                                          |
| Related Threats            | [T08.2](2-stride-analysis.md#filedownloadcontroller), [T09.1](2-stride-analysis.md#checkboardcontroller), [T10.2](2-stride-analysis.md#authutils), [T16.1](2-stride-analysis.md#shieldallconsumer) |

#### Description

Authorization decisions consume a `userId` supplied directly by the client as a request parameter (e.g., `@RequestParam("userId")` on FileDownLoadController lines 128, 153; CheckboardController shield-all line 239; ShieldAllMessage carries userId). There is no server-side session identity, so any in-cluster caller can impersonate any user (including reviewers) to pass permission checks, approve shield operations, or trigger bulk defect shielding.

#### Evidence

**Prerequisite basis:** Endpoints are reachable from `Internal Network`; the spoofing vector requires no additional privilege → T2.

`FileDownLoadController.java` lines 128, 153; `CheckboardController.java` line 239; `ProblemshieldDelegateImpl.java` lines 526-540 (`isReviewer(revision, userId)` compares against client value); `ShieldAllMessage.java` lines 20-39; `AuthUtils.checkPermission` lines 349-389 consumes caller-supplied userId.

#### Remediation

- Derive user identity from an authenticated session/token (SSO) server-side; never trust client-supplied userId.
- Enforce server-side reviewer identity for shield-all operations and audit every state-changing action.

#### Verification

- Submit a request with another user's userId and confirm the operation is rejected based on the session identity.

---

### FIND-05: SSRF via SARIF obsUrl server-side fetch

| Attribute                  | Value                                                                                                           |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                       |
| CVSS 4.0                   | 7.5 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N)                                           |
| CWE                        | [CWE-918](https://cwe.mitre.org/data/definitions/918.html): Server-Side Request Forgery                         |
| OWASP                      | A06:2025 – Insecure Design                                                                                      |
| Exploitation Prerequisites | Internal Network                                                                                                |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                       |
| Remediation Effort         | Medium                                                                                                          |
| Mitigation Type            | Custom Mitigation                                                                                               |
| Component                  | SarifParseServiceImpl                                                                                           |
| Related Threats            | [T18.1](2-stride-analysis.md#sarifparseserviceimpl), [T05.2](2-stride-analysis.md#staticalarmreceivecontroller) |

#### Description

`SarifParseServiceImpl.downloadAndParse` fetches `URI.create(obsUrl).toURL().openStream()` (line 160) where `obsUrl` originates from the unauthenticated `POST /codescan/v1/result/receive` and `/internal/codescan/v1/result/receive` request bodies. There is no scheme/host allowlist, no redirect policy, and no timeout, so an in-cluster caller can make the service fetch arbitrary internal endpoints (cloud metadata, internal services) and parse the returned content.

#### Evidence

**Prerequisite basis:** obsUrl is accepted on internal-reachability endpoints → `Internal Network` (T2).

`SarifParseServiceImpl.java` lines 159-168; `StaticAlarmReceiveDTO.java` lines 37-39 (obsUrl has only `@NotEmpty`, no URL validation); `StaticAlarmInternalController.java` lines 28, 42-44 (javadoc: "/internal/ 前缀不走网关鉴权"); method javadoc line 153 acknowledges no OBS auth.

#### Remediation

- Validate obsUrl against an allowed OBS domain allowlist; reject private/internal IP ranges and redirects.
- Add connect/read timeouts and size limits on the fetch.

#### Verification

- Submit a scan-run record with an obsUrl pointing to an internal service/metadata endpoint and confirm the fetch is rejected.

---

### FIND-06: NoSQL injection via insufficient input validation

| Attribute                  | Value                                                                                                                       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                   |
| CVSS 4.0                   | 8.1 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N)                                                       |
| CWE                        | [CWE-943](https://cwe.mitre.org/data/definitions/943.html): Improper Neutralization of Special Elements in Data Query Logic |
| OWASP                      | A05:2025 – Injection                                                                                                        |
| Exploitation Prerequisites | Internal Network                                                                                                            |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                   |
| Remediation Effort         | Medium                                                                                                                      |
| Mitigation Type            | Custom Mitigation                                                                                                           |
| Component                  | CheckboardController                                                                                                        |
| Related Threats            | [T09.3](2-stride-analysis.md#checkboardcontroller), [T03.2](2-stride-analysis.md#webhookcontroller)                         |

#### Description

`QueryDetailModel`, `QueryTaskFileContentModel`, and `IgnoredExtendDTO` are not `@Valid`-annotated and are not run through a field whitelist (only `QuerySummaryModel` bodies are validated at CheckboardController lines 121, 181, 193), so query criteria fields flow unsanitized into MongoDB queries. The Webhook path validates table/field names via `WebhookInputValidator` but `insertData` validates only `tableName` and leaves nested values unvalidated.

#### Evidence

**Prerequisite basis:** Both controllers are reachable from `Internal Network` (T2).

`CheckboardController.java` lines 205-249 (unvalidated models); `WebhookDelegateImpl.java` lines 43-87 (`insertData` validates only tableName at line 76; nested `queryData`/`mongoData` unvalidated vs `readMongoDB` lines 136-153 which validates via `getCriteria` lines 193-195).

#### Remediation

- Add `@Valid` and a field/operator whitelist to all query DTOs; centralize NoSQL query construction.
- Apply `validateFieldName`/`validateValue` to all webhook write paths.

#### Verification

- Send a query containing `$ne`-style operator objects or non-whitelisted fields to the board and webhook endpoints and confirm they are rejected.

---

### FIND-07: Sensitive data logged at INFO across controllers

| Attribute                  | Value                                                                                                                                                                                                                      |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                                                                                                   |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)                                                                                                                                                      |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File                                                                                                               |
| OWASP                      | A09:2025 – Security Logging and Monitoring Failures                                                                                                                                                                        |
| Exploitation Prerequisites | Internal Network                                                                                                                                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                                                                                                                  |
| Remediation Effort         | Low                                                                                                                                                                                                                        |
| Mitigation Type            | Custom Mitigation                                                                                                                                                                                                          |
| Component                  | HwApigController                                                                                                                                                                                                           |
| Related Threats            | [T02.2](2-stride-analysis.md#hwapigcontroller), [T05.3](2-stride-analysis.md#staticalarmreceivecontroller), [T06.2](2-stride-analysis.md#internalcodefullcontroller), [T14.1](2-stride-analysis.md#codecheckeventconsumer) |

#### Description

Several controllers log full request bodies or DTOs at INFO level: HwApigController lines 72, 94, 113, 135; StaticAlarmReceiveServiceImpl line 52 (full DTO incl. obsUrl/repoUrl); InternalCodeFullController line 49; InternalCodeIncController lines 62, 82. CodeCheckEventConsumer logs raw dead-letter message content (lines 124-127). Repository URLs, pipeline context, and caller-supplied fields land in log pipelines.

#### Evidence

**Prerequisite basis:** Logs are accessible to in-cluster log readers → `Internal Network` (T2).

`HwApigController.java` line 94 (`logger.info("apig startFullTaskForApig entry, params={}", params)`); `StaticAlarmReceiveServiceImpl.java` line 52; `InternalCodeFullController.java` line 49; `InternalCodeIncController.java` lines 62, 82; `CodeCheckEventConsumer.java` lines 124-127.

#### Remediation

- Redact or truncate request payloads before logging; log only non-sensitive identifiers.
- Sanitize dead-letter payloads before writing them to logs.

#### Verification

- Inspect log output for a sample request and confirm no full request bodies or URLs appear.

---

### FIND-08: HTML injection in notification emails

| Attribute                  | Value                                                                                                                                              |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                           |
| CVSS 4.0                   | 5.4 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:N/SC:L/SI:L/SA:N)                                                                              |
| CWE                        | [CWE-79](https://cwe.mitre.org/data/definitions/79.html): Improper Neutralization of Input During Web Page Generation                              |
| OWASP                      | A05:2025 – Injection                                                                                                                               |
| Exploitation Prerequisites | Internal Network                                                                                                                                   |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                                          |
| Remediation Effort         | Low                                                                                                                                                |
| Mitigation Type            | Custom Mitigation                                                                                                                                  |
| Component                  | SaveFullTaskResult                                                                                                                                 |
| Related Threats            | [T12.1](2-stride-analysis.md#savefulltaskresult), [T13.1](2-stride-analysis.md#saveinctaskresult), [T16.2](2-stride-analysis.md#shieldallconsumer) |

#### Description

Notification emails are built by string concatenation and sent as raw `text/html` (EmailUtil line 165): SaveFullTaskResult interpolates repoName/gitUrl/branch unescaped (lines 294-299); SaveIncTaskResult interpolates id/mrUrl/projectName (lines 268-285, 444-448); ShieldAllConsumer concatenates `detailUrl` (lines 1566-1567). Attacker-influenced task metadata can inject HTML/phishing content into recipients' mail clients.

#### Evidence

**Prerequisite basis:** Task metadata is influenced by internal-network callers (T2).

`EmailUtil.java` line 165 (`setContent(..., "text/html;charset=UTF-8")`); `SaveFullTaskResult.java` lines 294-299; `SaveIncTaskResult.java` lines 268-285, 444-448; `ProblemshieldDelegateImpl.java` lines 1566-1567.

#### Remediation

- HTML-escape all interpolated fields; use a templating engine or send text/plain.
- Sanitize persisted task metadata before display.

#### Verification

- Create a task whose repo/branch metadata contains HTML tags and confirm the email body renders them inert.

---

### FIND-09: Unbounded SARIF download/parse causes resource exhaustion

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                        |
| CVSS 4.0                   | 7.5 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling |
| OWASP                      | A06:2025 – Insecure Design                                                                                       |
| Exploitation Prerequisites | Internal Network                                                                                                 |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                        |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Custom Mitigation                                                                                                |
| Component                  | SarifParseServiceImpl                                                                                            |
| Related Threats            | [T15.1](2-stride-analysis.md#staticalarmeventconsumer), [T18.2](2-stride-analysis.md#sarifparseserviceimpl)      |

#### Description

The SARIF download feeds the InputStream directly into Jackson with no content-length cap, byte limit, or connect/read timeout (`SarifParseServiceImpl` lines 160-161), and `CodeQlSarifParser` bounds only per-result threadFlow locations (lines 57, 321-331). A malicious or oversized SARIF causes memory exhaustion in the parser.

#### Evidence

**Prerequisite basis:** Parse is triggered by internal-network callers via the receive endpoints → T2.

`SarifParseServiceImpl.java` lines 159-168; `CodeQlSarifParser.java` lines 57, 321-331.

#### Remediation

- Enforce max download size, max parse elements, and timeouts; stream with a bounded reader.
- Reject oversized SARIF before parsing.

#### Verification

- Submit a scan-run pointing at a very large/never-ending URL and confirm the parser aborts within limits.

---

### FIND-10: Scan/parse resource abuse via arbitrary tasking

| Attribute                  | Value                                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                   |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                      |
| CWE                        | [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption              |
| OWASP                      | A06:2025 – Insecure Design                                                                                 |
| Exploitation Prerequisites | Internal Network                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                  |
| Remediation Effort         | Medium                                                                                                     |
| Mitigation Type            | Custom Mitigation                                                                                          |
| Component                  | HwApigController                                                                                           |
| Related Threats            | [T02.3](2-stride-analysis.md#hwapigcontroller), [T05.4](2-stride-analysis.md#staticalarmreceivecontroller) |

#### Description

Authenticated (gateway) machine callers and in-cluster callers can submit arbitrary full/inc scan tasks and parse events for arbitrary repo URLs without per-caller quotas or repo-ownership checks, consuming Huawei CodeCheck scan quota and compute cost.

#### Evidence

**Prerequisite basis:** Tasking surfaces are reachable from `Internal Network` or via gateway `Authenticated User` (T2).

`HwApigController.java` lines 91-141 (no quota/ownership checks); `InternalCodeFullDelegateImpl.startFullTask` lines 75-143 (validates repo existence but not caller ownership); `StaticAlarmReceiveServiceImpl` lines 51-66.

#### Remediation

- Add per-caller rate/quota limits and repo-ownership validation in code.
- Bound concurrent parse work and scan task submissions.

#### Verification

- Confirm a caller cannot exceed configured per-project scan/parse quotas.

---

### FIND-11: Command/option injection into auto-fix script via branch name

| Attribute                  | Value                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                              |
| CVSS 4.0                   | 6.0 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:L/SC:N/SI:N/SA:N)                                                 |
| CWE                        | [CWE-88](https://cwe.mitre.org/data/definitions/88.html): Improper Neutralization of Argument Delimiters in a Command |
| OWASP                      | A05:2025 – Injection                                                                                                  |
| Exploitation Prerequisites | Internal Network                                                                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                             |
| Remediation Effort         | Low                                                                                                                   |
| Mitigation Type            | Custom Mitigation                                                                                                     |
| Component                  | InternalController                                                                                                    |
| Related Threats            | [T04.2](2-stride-analysis.md#internalcontroller)                                                                      |

#### Description

`CommandArgSanitizer.sanitizeBranchName` (regex `^[a-zA-Z0-9._/-]+$`, line 41) permits a leading `-` and `..`; a branch such as `--flag` is accepted and passed as an option value to `auto-fix.sh -b`, enabling option/argument injection into the script. `sanitizeRepoUrl` (regex line 38) also explicitly allows `@` (basic-auth in URL).

#### Evidence

**Prerequisite basis:** `/internal/pre-commit` is reachable from `Internal Network` (T2).

`CommandArgSanitizer.java` lines 37-41, 62-71, 80-89; `PipelineDelegateImpl.preMergeAndFix` lines 147-197 (ProcessBuilder list-form, branch passed at line 179).

#### Remediation

- Reject branch names starting with `-`; tighten `sanitizeBranchName`.
- Pass branch via environment/stdin rather than argv; validate repoUrl userinfo.

#### Verification

- Submit a pre-commit request with a branch like `--help` and confirm it is rejected.

---

### FIND-12: Injection via unencoded URL/filename concatenation

| Attribute                  | Value                                                                                                         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                      |
| CVSS 4.0                   | 5.5 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N)                                         |
| CWE                        | [CWE-93](https://cwe.mitre.org/data/definitions/93.html): Improper Neutralization of CRLF Sequences           |
| OWASP                      | A05:2025 – Injection                                                                                          |
| Exploitation Prerequisites | Internal Network                                                                                              |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                     |
| Remediation Effort         | Low                                                                                                           |
| Mitigation Type            | Custom Mitigation                                                                                             |
| Component                  | InternalCodeIncController                                                                                     |
| Related Threats            | [T07.2](2-stride-analysis.md#internalcodeinccontroller), [T08.3](2-stride-analysis.md#filedownloadcontroller) |

#### Description

Client-supplied values are concatenated unencoded into URLs and download filenames: `handleFinishedTask` builds `openlibingDomain + "/apps/entryCheckDashCode/" + taskId + "/" + uuid + "?projectName=..."` (lines 254-273), and FileDownLoadController builds Content-Disposition names from unvalidated `tableName`/`fileName` (`tableName + ".xlsx"`, `fileName + ".log"`, lines 109, 193). This enables parameter/CRLF injection into response URLs and headers.

#### Evidence

**Prerequisite basis:** Both controllers reachable from `Internal Network` (T2).

`InternalCodeIncDelegateImpl.java` lines 254-273; `FileDownLoadController.java` lines 109, 140, 173, 193, 211.

#### Remediation

- URL-encode all path/query components; validate taskId/uuid/tableName/filename format before use.
- Use Content-Disposition with safe encoding and validate names.

#### Verification

- Submit values containing `?`, `#`, `%0d%0a`, or `/` and confirm they are encoded or rejected.

---

### FIND-13: Malformed PR URL causes exception churn

| Attribute                  | Value                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Low                                                                                 |
| CVSS 4.0                   | 3.5 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)               |
| CWE                        | [CWE-20](https://cwe.mitre.org/data/definitions/20.html): Improper Input Validation |
| OWASP                      | A10:2025 – Mishandling of Exceptional Conditions                                    |
| Exploitation Prerequisites | Internal Network                                                                    |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                           |
| Remediation Effort         | Low                                                                                 |
| Mitigation Type            | Custom Mitigation                                                                   |
| Component                  | InternalCodeIncController                                                           |
| Related Threats            | [T07.3](2-stride-analysis.md#internalcodeinccontroller)                             |

#### Description

`pr_url.split("/")` requires ≥5 segments but indexes up to `prStrings[6]` (InternalCodeIncDelegateImpl line 163), throwing `ArrayIndexOutOfBoundsException` for 5-6 segment URLs (caught by the generic catch at line 136); repeated malformed calls cause repeated error handling and 500 responses.

#### Evidence

**Prerequisite basis:** `/ci-portal/webhook/codecheck/v1/task` reachable from `Internal Network` (T2).

`InternalCodeIncDelegateImpl.java` lines 94-97, 136, 163.

#### Remediation

- Validate PR-URL segment count/format up front; return a 4xx for malformed input.

#### Verification

- Submit PR URLs with 5-6 segments and confirm a clean 4xx instead of an exception.

---

### FIND-14: AK/SK ciphertext in Redis queues and error logs

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                    |
| CVSS 4.0                   | 7.0 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N)                                        |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                            |
| Exploitation Prerequisites | Internal Network                                                                                             |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                    |
| Remediation Effort         | Medium                                                                                                       |
| Mitigation Type            | Custom Mitigation                                                                                            |
| Component                  | RuleSetScheduleTask                                                                                          |
| Related Threats            | [T11.1](2-stride-analysis.md#rulesetscheduletask)                                                            |

#### Description

`syncRule()` serializes `{region, akSkVo}` (ciphertext AK/SK) into Redis queue `rule_set:languages_severity_rule_set_task_queue` (lines 319-331), and error paths log the map/JSON containing the AkSkVo ciphertext (`logger.error("Parameter serialization failed: {}", paramMap, e)` line 327; line 354). Credential material is persisted in task queues and appears in logs.

#### Evidence

**Prerequisite basis:** Redis and logs are reachable/readable from `Internal Network` (T2).

`RuleSetScheduleTask.java` lines 319-331, 327, 354.

#### Remediation

- Do not persist AK/SK (even ciphertext) in task queues; cache decrypted credentials in-memory with TTL.
- Redact credential fields from log messages.

#### Verification

- Inspect Redis queue contents and log output and confirm no AK/SK material is present.

---

### FIND-15: Rule-set sync consume phase runs outside lock

| Attribute                  | Value                                                                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                                                             |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:L/SC:N/SI:N/SA:N)                                                                |
| CWE                        | [CWE-362](https://cwe.mitre.org/data/definitions/362.html): Concurrent Execution using Shared Resource with Improper Synchronization |
| OWASP                      | A06:2025 – Insecure Design                                                                                                           |
| Exploitation Prerequisites | Internal Network                                                                                                                     |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                                            |
| Remediation Effort         | Low                                                                                                                                  |
| Mitigation Type            | Custom Mitigation                                                                                                                    |
| Component                  | RuleSetScheduleTask                                                                                                                  |
| Related Threats            | [T11.2](2-stride-analysis.md#rulesetscheduletask)                                                                                    |

#### Description

For `getAllAccountRule`/`syncRule`/`getProjectRuleSets` only the queue-initialization block is under the Redisson lock; the dequeue/consume phase runs outside the lock (lines 143, 295, 473). If the lock is not acquired, consumers still process stale queue content, enabling duplicate or inconsistent rule-set sync.

#### Evidence

**Prerequisite basis:** Scheduled task operates on internal Redis queues (T2).

`RuleSetScheduleTask.java` lines 66-77 (locks), 143, 295, 473, 653-657.

#### Remediation

- Move the consume phase inside the lock or use idempotent consumption keys; clear queues on lock failure.

#### Verification

- Simulate lock failure and confirm consumers do not process stale queue content.

---

### FIND-16: Unsanitized persisted defect data enables stored injection

| Attribute                  | Value                                                                                               |
| -------------------------- | --------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                            |
| CVSS 4.0                   | 5.4 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:N/SC:L/SI:L/SA:N)                               |
| CWE                        | [CWE-116](https://cwe.mitre.org/data/definitions/116.html): Improper Encoding or Escaping of Output |
| OWASP                      | A05:2025 – Injection                                                                                |
| Exploitation Prerequisites | Internal Network                                                                                    |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                           |
| Remediation Effort         | Medium                                                                                              |
| Mitigation Type            | Custom Mitigation                                                                                   |
| Component                  | SaveFullTaskResult                                                                                  |
| Related Threats            | [T12.2](2-stride-analysis.md#savefulltaskresult)                                                    |

#### Description

Huawei CodeCheck API responses (summary/details) are written to MongoDB (`fullSummaryOperation.saveInfo`, `fullDetailsOperation.saveInfo`) with only status/emptiness checks — no field-level sanitization of `filePath`/`defectContent` (lines 873-914), allowing stored injection content to flow into downstream board rendering and exports.

#### Evidence

**Prerequisite basis:** Persisted data is rendered to internal-network viewers (T2).

`SaveFullTaskResult.java` lines 873-914; `FullSummaryOperation.java` line 448; `FullDetailsOperation.java` line 447.

#### Remediation

- Sanitize/normalize persisted defect fields; escape at render time; treat defect content as untrusted.

#### Verification

- Confirm defect content containing HTML/script is stored inert and rendered escaped.

---

### FIND-17: Duplicate static-alarm parsing without idempotency

| Attribute                  | Value                                                                                                 |
| -------------------------- | ----------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Low                                                                                                   |
| CVSS 4.0                   | 3.8 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N)                                 |
| CWE                        | [CWE-799](https://cwe.mitre.org/data/definitions/799.html): Improper Control of Interaction Frequency |
| OWASP                      | A06:2025 – Insecure Design                                                                            |
| Exploitation Prerequisites | Internal Network                                                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                             |
| Remediation Effort         | Low                                                                                                   |
| Mitigation Type            | Custom Mitigation                                                                                     |
| Component                  | StaticAlarmEventConsumer                                                                              |
| Related Threats            | [T15.2](2-stride-analysis.md#staticalarmeventconsumer)                                                |

#### Description

The static-alarm parse consumer runs with concurrency 1-3 and takes no Redisson lock; duplicate parse events cause repeated OBS downloads, re-parses, and repeated MongoDB upserts, inflating cost and state churn.

#### Evidence

**Prerequisite basis:** Parse triggered by internal-network callers (T2).

`StaticAlarmEventConsumer.java` lines 34-44 (concurrency 1-3, no lock); `SarifParseServiceImpl.java` lines 159-168.

#### Remediation

- Add idempotency/lock keyed on scanRunId; skip already-parsed runs.

#### Verification

- Publish a duplicate parse event and confirm the second is skipped.

---

### FIND-18: Stored export DTO tampering alters export scope

| Attribute                  | Value                                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                   |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)                                      |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                            |
| Exploitation Prerequisites | Internal Network                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                  |
| Remediation Effort         | Medium                                                                                                     |
| Mitigation Type            | Custom Mitigation                                                                                          |
| Component                  | StaticAlarmExportConsumer                                                                                  |
| Related Threats            | [T17.1](2-stride-analysis.md#staticalarmexportconsumer)                                                    |

#### Description

`StaticAlarmServiceImpl.processExport` deserializes the stored export query `StaticAlarmQueryDTO` from the framework `obs_file` record (lines 1211-1217) and exports matching defects; tampering with the stored DTO or the originating record changes which defect data is exported to files.

#### Evidence

**Prerequisite basis:** Export records originate from internal-network callers (T2).

`StaticAlarmServiceImpl.java` lines 1211-1217, 956-1043.

#### Remediation

- Verify the export query/scope against the requesting user's permissions before export; authenticate the export record origin.

#### Verification

- Confirm a tampered stored export query cannot widen the export scope.

---

### FIND-19: MongoDB TLS hostname verification disabled

| Attribute                  | Value                                                                                       |
| -------------------------- | ------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                   |
| CVSS 4.0                   | 7.4 (CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N)                       |
| CWE                        | [CWE-295](https://cwe.mitre.org/data/definitions/295.html): Improper Certificate Validation |
| OWASP                      | A04:2025 – Cryptographic Failures                                                           |
| Exploitation Prerequisites | Internal Network                                                                            |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                   |
| Remediation Effort         | Low                                                                                         |
| Mitigation Type            | Standard Mitigation                                                                         |
| Component                  | MongoDB                                                                                     |
| Related Threats            | [T20.1](2-stride-analysis.md#mongodb)                                                       |

#### Description

`MongoConfig` enables SSL but also sets `builder.invalidHostNameAllowed(true)` (lines 66-70) with an inline comment "not recommended for production"; the client does not verify the MongoDB server hostname, enabling MITM/eavesdropping on the MongoDB connection within the cluster.

#### Evidence

**Prerequisite basis:** MongoDB is reachable from `Internal Network`; TLS is enabled but hostname verification is disabled (T2).

`MongoConfig.java` lines 66-70; URI decrypted at lines 54-62.

#### Remediation

- Set `invalidHostNameAllowed(false)`; pin the MongoDB server certificate/CA; enforce hostname verification.

#### Verification

- Confirm the MongoDB client rejects a mismatched server certificate.

---

### FIND-20: Datastore transport encryption gaps (MySQL, RabbitMQ)

| Attribute                  | Value                                                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                    |
| CVSS 4.0                   | 5.9 (CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)                                       |
| CWE                        | [CWE-319](https://cwe.mitre.org/data/definitions/319.html): Cleartext Transmission of Sensitive Information |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                           |
| Exploitation Prerequisites | Internal Network                                                                                            |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                   |
| Remediation Effort         | Medium                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                         |
| Component                  | RabbitMQ                                                                                                    |
| Related Threats            | [T21.1](2-stride-analysis.md#mysql), [T23.1](2-stride-analysis.md#rabbitmq)                                 |

#### Description

MySQL transport security depends entirely on the config-center JDBC URL (`DataSourceConfig` configures no TLS in code, line 73); if `useSSL`/`requireSSL` is not enforced, role/permission queries travel plaintext. RabbitMQ enables TLS only for the `prod` profile (`RabbitConnectionFactoryConfig` lines 57-60); beta/gama/icsl inherit port 5672 and connect without TLS, so task/alarm messages travel in cleartext across the cluster.

#### Evidence

**Prerequisite basis:** Both datastores are reachable from `Internal Network`; credentials are decrypted at connect time (T2).

`DataSourceConfig.java` line 73 (password decrypt only, no TLS config); `RabbitConnectionFactoryConfig.java` lines 57-60; `application-prod.yaml` line 22 (port 5671) vs `application-beta.yaml` (no port override → 5672).

#### Remediation

- Enforce TLS in the JDBC URL (`useSSL=true&requireSSL=true`) and verify via config.
- Enable AMQPS for all non-local profiles; enforce TLS via config.

#### Verification

- Confirm MySQL and RabbitMQ connections use TLS in beta/gama/icsl environments.

---

### FIND-21: Scan results delivered without integrity verification

| Attribute                  | Value                                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                  |
| CVSS 4.0                   | 7.0 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N)                                      |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                            |
| Exploitation Prerequisites | Internal Network                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                  |
| Remediation Effort         | Medium                                                                                                     |
| Mitigation Type            | Custom Mitigation                                                                                          |
| Component                  | StaticAlarmReceiveController                                                                               |
| Related Threats            | [T24.1](2-stride-analysis.md#openlibingcicd), [T05.1](2-stride-analysis.md#staticalarmreceivecontroller)   |

#### Description

The CICD service posts scan results to `/codescan/v1/result/receive` (and `/internal/codescan/v1/result/receive`) over plain service-to-service HTTP with no signature or mutual auth; tampered scan results (altered SARIF/obsUrl) are accepted and parsed as authoritative, and any in-cluster actor can spoof the CICD source.

#### Evidence

**Prerequisite basis:** Receive endpoints are reachable from `Internal Network` with no auth (T2).

`StaticAlarmReceiveController.java` lines 37-40; `StaticAlarmInternalController.java` lines 28, 42-44 (javadoc: "/internal/ 前缀不走网关鉴权"); `StaticAlarmReceiveServiceImpl.java` lines 51-66.

#### Remediation

- Authenticate the CICD caller (mTLS/service token); add message signature/HMAC; verify pipeline context integrity.

#### Verification

- Confirm a request without a valid CICD credential/signature is rejected.

---

### FIND-22: Feign service calls without mutual authentication

| Attribute                  | Value                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                 |
| CVSS 4.0                   | 5.6 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N)                                    |
| CWE                        | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                    |
| Exploitation Prerequisites | Internal Network                                                                                         |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                |
| Remediation Effort         | High                                                                                                     |
| Mitigation Type            | Standard Mitigation                                                                                      |
| Component                  | OpenlibingFramework                                                                                      |
| Related Threats            | [T25.1](2-stride-analysis.md#openlibingframework)                                                        |

#### Description

Feign calls to sibling microservices (`openlibing-framework`, `openlibing-cicd`, `openlibing-coderepo`) are HTTPS but not mutually authenticated; an in-cluster actor could impersonate a sibling service and return forged responses (e.g., export-task state) to alter workflows.

#### Evidence

**Prerequisite basis:** Sibling services are reachable from `Internal Network` (T2).

Feign clients under `business/delegate/` (e.g., `openlibingFrameworkClient`); `StaticAlarmExportConsumer.java` lines 963-1042 (CAS via framework service).

#### Remediation

- Enable mTLS/service-account identity verification for Feign calls across sibling services.

#### Verification

- Confirm Feign calls reject an impersonated server certificate.

---

### FIND-23: XXL-Job executor registration token may be weak or absent

| Attribute                  | Value                                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                 |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:N/VI:L/VA:L/SC:N/SI:N/SA:N)                                    |
| CWE                        | [CWE-306](https://cwe.mitre.org/data/definitions/306.html): Missing Authentication for Critical Function |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                    |
| Exploitation Prerequisites | Internal Network                                                                                         |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                |
| Remediation Effort         | Low                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                      |
| Component                  | XxlJob                                                                                                   |
| Related Threats            | [T27.1](2-stride-analysis.md#xxljob)                                                                     |

#### Description

`xxl.job.admin.accessToken` is injected from config and set on the executor (XxlJobConfig lines 27-28, 58); if the token is empty or weak, an in-cluster actor can register a spoofed executor or dispatch forged jobs (e.g., `lintRunnerChecksHandler`, rule-sync handlers) to the application.

#### Evidence

**Prerequisite basis:** XXL-Job admin is reachable from `Internal Network` (T2).

`XxlJobConfig.java` lines 27-28, 58; `XxlJobHandler.java` lines 89-109 (`lintRunnerChecksHandler`).

#### Remediation

- Enforce a strong, rotated accessToken for executor registration; restrict xxl-job admin network access.

#### Verification

- Confirm executor registration fails without the correct accessToken.

---

### FIND-24: Over-broad authorization bypasses in AuthUtils

| Attribute                  | Value                                                                             |
| -------------------------- | --------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                          |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)             |
| CWE                        | [CWE-862](https://cwe.mitre.org/data/definitions/862.html): Missing Authorization |
| OWASP                      | A01:2025 – Broken Access Control                                                  |
| Exploitation Prerequisites | Authenticated User                                                                |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                         |
| Remediation Effort         | Medium                                                                            |
| Mitigation Type            | Custom Mitigation                                                                 |
| Component                  | AuthUtils                                                                         |
| Related Threats            | [T10.1](2-stride-analysis.md#authutils)                                           |

#### Description

`AuthUtils.checkPermission` returns `true` unconditionally for roles `admin`/`platform_operator` regardless of project (lines 371-377) and for any menu with identification `general_config` (lines 357-359); `assertAuthFromSummary` returns `true` for any `"public"` repo without a per-user check (lines 155-168). These widen authorization beyond least privilege.

#### Evidence

**Prerequisite basis:** Permission checks run for authenticated users of the portal (T2).

`AuthUtils.java` lines 155-168, 357-359, 371-377; `checkPermission` consumed at FileDownLoadController lines 130, 156 and 34 call sites in RuleSetListImpl/RuleDelegateImpl/SensitiveDelegateImpl.

#### Remediation

- Restrict admin bypasses to explicit project scopes; validate `general_config` handling; tighten public-repo assumptions.

#### Verification

- Confirm admin/platform_operator roles are scoped to the projects they manage.

---

### FIND-25: OBS object-key validation absent (defense-in-depth)

| Attribute                  | Value                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Low                                                                                 |
| CVSS 4.0                   | 3.7 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)               |
| CWE                        | [CWE-284](https://cwe.mitre.org/data/definitions/284.html): Improper Access Control |
| OWASP                      | A01:2025 – Broken Access Control                                                    |
| Exploitation Prerequisites | Internal Network                                                                    |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                           |
| Remediation Effort         | Low                                                                                 |
| Mitigation Type            | Custom Mitigation                                                                   |
| Component                  | ObsBucketServiceImpl                                                                |
| Related Threats            | [T19.1](2-stride-analysis.md#obsbucketserviceimpl)                                  |

#### Description

`uploadFile`/`deleteObject`/`getObject` pass the caller-supplied `objectKey` straight to the OBS SDK with no key-format or scope validation (lines 88-129), so any caller with service access could address any object in the single configured bucket. Current in-repo callers generate keys server-side (date+UUID, StaticAlarmServiceImpl lines 1020-1021), making this defense-in-depth.

#### Evidence

**Prerequisite basis:** ObsBucketServiceImpl has no listener; invoked from internal-network services (T2).

`ObsBucketServiceImpl.java` lines 88-129; `StaticAlarmServiceImpl.java` lines 1020-1021.

#### Remediation

- Enforce an object-key namespace/pattern allowlist; scope operations to the export prefix.

#### Verification

- Confirm an out-of-prefix objectKey is rejected.

---

### FIND-26: Token use redirectable via tampered task git URL

| Attribute                  | Value                                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                   |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)                                      |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                            |
| Exploitation Prerequisites | Internal Network                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk                                                                                  |
| Remediation Effort         | Medium                                                                                                     |
| Mitigation Type            | Custom Mitigation                                                                                          |
| Component                  | SaveIncTaskResult                                                                                          |
| Related Threats            | [T13.2](2-stride-analysis.md#saveinctaskresult)                                                            |

#### Description

`SaveIncTaskResult` decrypts account tokens and uses them for git platform operations based on the task-supplied `gitUrl` (`SecurityHelper.decrypt(restCodeCheckUtil.getAccountToken(gitUrl, accountInfo))`, lines 307-320); tampered task records could redirect token use or trigger unwanted platform calls.

#### Evidence

**Prerequisite basis:** Task records are created by internal-network callers (T2).

`SaveIncTaskResult.java` lines 307-320; `CodePlateHelper.getCodePlate` lines 117-133 (platform selection by URL host substring).

#### Remediation

- Validate git URLs against registered repos before using tokens; bind token use to authenticated task origins.

#### Verification

- Confirm a task with an unregistered/malicious git URL does not trigger token use.

---

## Tier 3 — Defense-in-Depth (Prior Compromise / Host Access)

### FIND-27: Nacos key/ciphertext co-location and config spoofing

| Attribute                  | Value                                                                                                                                                           |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                       |
| CVSS 4.0                   | 8.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N)                                                                                           |
| CWE                        | [CWE-321](https://cwe.mitre.org/data/definitions/321.html): Use of Hard-coded Cryptographic Key                                                                 |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                                                                               |
| Exploitation Prerequisites | Admin Credentials                                                                                                                                               |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                                                                                       |
| Remediation Effort         | High                                                                                                                                                            |
| Mitigation Type            | Redesign                                                                                                                                                        |
| Component                  | Nacos                                                                                                                                                           |
| Related Threats            | [T01.1](2-stride-analysis.md#openlibingcodecheckapplication), [T01.2](2-stride-analysis.md#openlibingcodecheckapplication), [T28.1](2-stride-analysis.md#nacos) |

#### Description

The AES key `security.part1` and every encrypted secret (datasource, mongo, redis, rabbitmq, git tokens, AK/SK) reside in the same Nacos group/namespace (OPENLIBING). One Nacos read compromise yields both the key and the ciphertexts it protects, defeating encryption at rest; an attacker able to publish config can also inject attacker-controlled credentials and endpoints.

#### Evidence

**Prerequisite basis:** Nacos has `Min Prerequisite = Admin Credentials` in the Component Exposure Table (T3).

`SecurityHelper.java` lines 27-38 (key from `${security.part1}`); `application-prod.yaml` lines 3-20 (all credentials + part1 in Nacos group OPENLIBING); `application-beta.yaml` lines 3-19.

#### Remediation

- Store the key in a dedicated secrets manager with independent ACLs and rotation; split sensitive config from application config; enable Nacos ACL/encryption-at-rest.

#### Verification

- Confirm the key and ciphertexts are stored under separate access-control domains.

---

### FIND-28: Decrypted repo tokens exposed in process argv

| Attribute                  | Value                                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                     |
| CVSS 4.0                   | 6.8 (CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N)                         |
| CWE                        | [CWE-200](https://cwe.mitre.org/data/definitions/200.html): Exposure of Sensitive Information |
| OWASP                      | A04:2025 – Cryptographic Failures                                                             |
| Exploitation Prerequisites | Host/OS Access                                                                                |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                     |
| Remediation Effort         | Medium                                                                                        |
| Mitigation Type            | Custom Mitigation                                                                             |
| Component                  | InternalController                                                                            |
| Related Threats            | [T04.3](2-stride-analysis.md#internalcontroller)                                              |

#### Description

`PipelineDelegateImpl.preMergeAndFix` runs `timeout ... /opt/app/openlibing/auto-fix.sh -a <repo> ... -d <targetToken> -l <sourceToken>` (lines 166-194); the decrypted repo access tokens are passed as process command-line arguments and are visible in the host process list (`ps`/`/proc`) to any local observer.

#### Evidence

**Prerequisite basis:** Token exposure requires host process-list access → `Host/OS Access` (T3).

`PipelineDelegateImpl.java` lines 147-197 (tokens at lines 179, 187); tokens fetched via `gitCodeHelper.getAutoFormatRepoAccessToken` lines 154, 160.

#### Remediation

- Pass tokens via environment variables or a 0600 temp file; use `ProcessBuilder` env; avoid argv for secrets.

#### Verification

- Inspect the running process list during auto-fix and confirm no tokens appear in argv.

---

### FIND-29: Single shared MongoDB credential, no least privilege

| Attribute                  | Value                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                          |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:L/AC:L/AT:N/PR:H/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)                             |
| CWE                        | [CWE-250](https://cwe.mitre.org/data/definitions/250.html): Execution with Unnecessary Privileges |
| OWASP                      | A01:2025 – Broken Access Control                                                                  |
| Exploitation Prerequisites | MongoDB Compromise                                                                                |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                         |
| Remediation Effort         | High                                                                                              |
| Mitigation Type            | Redesign                                                                                          |
| Component                  | MongoDB                                                                                           |
| Related Threats            | [T20.2](2-stride-analysis.md#mongodb)                                                             |

#### Description

The application uses one decrypted MongoDB credential for all collections and operations (MongoConfig lines 54-73); any application compromise or DB account leak grants full read/write over all scan/defect/alarm data with no per-collection or per-role separation.

#### Evidence

**Prerequisite basis:** Exploitation requires prior MongoDB/app compromise → `MongoDB Compromise` (T3).

`MongoConfig.java` lines 54-73 (single decrypted URI); single credential used by all MongoTemplate operations.

#### Remediation

- Use separate MongoDB roles/users per function; enable MongoDB RBAC; scope credentials to least privilege.

#### Verification

- Confirm different functions use different MongoDB roles with minimal privileges.

---

### FIND-30: AK/SK ciphertext at rest in Redis

| Attribute                  | Value                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                               |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:L/AC:L/AT:N/PR:H/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)                                  |
| CWE                        | [CWE-312](https://cwe.mitre.org/data/definitions/312.html): Cleartext Storage of Sensitive Information |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                      |
| Exploitation Prerequisites | Redis Compromise                                                                                       |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                              |
| Remediation Effort         | Medium                                                                                                 |
| Mitigation Type            | Custom Mitigation                                                                                      |
| Component                  | Redis                                                                                                  |
| Related Threats            | [T22.1](2-stride-analysis.md#redis)                                                                    |

#### Description

`RuleSetScheduleTask` persists `{region, akSkVo}` (ciphertext AK/SK) in Redis list `rule_set:languages_severity_rule_set_task_queue` (lines 319-331). Redis is TLS-enabled (Jedis `useSsl()`, lines 67-73; Redisson `rediss://`, line 102), but a Redis compromise exposes encrypted credential material and task data.

#### Evidence

**Prerequisite basis:** Exploitation requires prior Redis compromise → `Redis Compromise` (T3).

`RuleSetScheduleTask.java` lines 319-331; `RedisConfig.java` lines 67-73, 102.

#### Remediation

- Avoid persisting credential material in Redis; if needed, use short TTLs and encrypt at a separate layer; restrict Redis access via ACL/network policy.

#### Verification

- Confirm no credential material exists in Redis keys.

---

### FIND-31: Access tokens transmitted in URL query parameters

| Attribute                  | Value                                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                          |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N)                                              |
| CWE                        | [CWE-598](https://cwe.mitre.org/data/definitions/598.html): Use of GET Request Method With Sensitive Query Strings |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                                  |
| Exploitation Prerequisites | Admin Credentials                                                                                                  |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                                          |
| Remediation Effort         | Medium                                                                                                             |
| Mitigation Type            | Custom Mitigation                                                                                                  |
| Component                  | GitCode                                                                                                            |
| Related Threats            | [T32.1](2-stride-analysis.md#gitcode), [T33.1](2-stride-analysis.md#gitee)                                         |

#### Description

GitCodeHelper and GiteeHelper append decrypted access tokens to API URLs as query parameters (`?access_token=<token>`, GitCodeHelper lines 89-93, 135, 222-223; GiteeHelper lines 70-71, 145-150). Tokens can leak via proxy/access logs, browser history, or Referer headers.

#### Evidence

**Prerequisite basis:** Token leakage requires access to logs/infrastructure → `Admin Credentials` (T3).

`GitCodeHelper.java` lines 89-93, 135, 222-223; `GiteeHelper.java` lines 70-71, 145-150.

#### Remediation

- Send tokens via the Authorization header instead of query params; ensure the HTTP client does not log URLs.

#### Verification

- Confirm outbound platform requests carry tokens in headers, not URLs.

---

### FIND-32: Inconsistent GitHub token handling

| Attribute                  | Value                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Low                                                                                  |
| CVSS 4.0                   | 3.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N)                |
| CWE                        | [CWE-696](https://cwe.mitre.org/data/definitions/696.html): Incorrect Behavior Order |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                |
| Exploitation Prerequisites | Admin Credentials                                                                    |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                            |
| Remediation Effort         | Low                                                                                  |
| Mitigation Type            | Custom Mitigation                                                                    |
| Component                  | Github                                                                               |
| Related Threats            | [T34.1](2-stride-analysis.md#github)                                                 |

#### Description

`GithubPlate.getAccessToken` returns `accountInfo.getGithubAccessToken()` without `SecurityHelper.decrypt` (lines 60-63), and `getAccountInfo` never populates the github token (CodeCheckOrganization lines 148-153); GitHub flows may use an un-decrypted/empty token, causing functional mis-credential usage and masking the real auth state.

#### Evidence

**Prerequisite basis:** GitHub token path is config/credential-administered (T3).

`GithubPlate.java` lines 59-64; `CodeCheckOrganization.java` lines 141-157.

#### Remediation

- Align GitHub token decryption with other platforms; populate/persist the github token consistently; fail closed on missing token.

#### Verification

- Confirm GitHub API calls use a correctly decrypted token.

---

### FIND-33: SMTP without TLS

| Attribute                  | Value                                                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                    |
| CVSS 4.0                   | 5.9 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)                                       |
| CWE                        | [CWE-319](https://cwe.mitre.org/data/definitions/319.html): Cleartext Transmission of Sensitive Information |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                           |
| Exploitation Prerequisites | Admin Credentials                                                                                           |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                                   |
| Remediation Effort         | Low                                                                                                         |
| Mitigation Type            | Standard Mitigation                                                                                         |
| Component                  | SmtpServer                                                                                                  |
| Related Threats            | [T35.1](2-stride-analysis.md#smtpserver)                                                                    |

#### Description

`EmailUtil.sendEmail` configures only `mail.smtp.auth=true` with no STARTTLS/TLS property (lines 67-71), so the sender password (decrypted config `commom.email.password`) and email bodies are transmitted to the mail server in plaintext.

#### Evidence

**Prerequisite basis:** SMTP server access is externally administered (T3).

`EmailUtil.java` lines 67-71, 84; `EmailAccount.java` lines 44-51.

#### Remediation

- Enable STARTTLS/TLS (`mail.smtp.starttls.enable=true` / `mail.smtp.ssl.enable=true`); enforce server certificate validation.

#### Verification

- Confirm SMTP connections negotiate TLS.

---

### FIND-34: OBS credential dependency

| Attribute                  | Value                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                         |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)                            |
| CWE                        | [CWE-522](https://cwe.mitre.org/data/definitions/522.html): Insufficiently Protected Credentials |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                |
| Exploitation Prerequisites | Admin Credentials                                                                                |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                        |
| Remediation Effort         | Medium                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                              |
| Component                  | HuaweiOBS                                                                                        |
| Related Threats            | [T29.1](2-stride-analysis.md#huaweiobs)                                                          |

#### Description

OBS bucket access uses `${obs.access-key-id}`/`${obs.secret-access-key}` decrypted from config (ObsBucketServiceImpl lines 42-52, 164-165); a config/credential leak exposes all SARIF scan artifacts and export files in the single bucket.

#### Evidence

**Prerequisite basis:** OBS is externally administered (T3).

`ObsBucketServiceImpl.java` lines 42-52, 158-171.

#### Remediation

- Rotate OBS AK/SK; use STS short-lived credentials; restrict bucket ACL to the service account.

#### Verification

- Confirm OBS credentials are rotated and scoped to the export bucket only.

---

### FIND-35: HuaweiCodeCheck AK/SK handling and request-object logging

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                                     |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N)                                        |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP                      | A04:2025 – Cryptographic Failures                                                                            |
| Exploitation Prerequisites | Admin Credentials                                                                                            |
| Exploitability Tier        | Tier 3 — Defense-in-Depth                                                                                    |
| Remediation Effort         | Medium                                                                                                       |
| Mitigation Type            | Custom Mitigation                                                                                            |
| Component                  | HuaweiCodeCheck                                                                                              |
| Related Threats            | [T31.1](2-stride-analysis.md#huaweicodecheck)                                                                |

#### Description

Scan delegation, rule sync, and result polling use tenant AK/SK (decrypted at signing in `RestCodeCheckUtil` lines 525-526). Several error paths log the whole APIG `Request` object (which holds the decrypted key/secret set at lines 525-526): lines 167, 209, 751, 797-800, 838, 1001, 1080, 1193, 1356. An AK/SK leak grants control of scan creation, rule-set sync, and full result readback.

#### Evidence

**Prerequisite basis:** AK/SK are credential-administered (T3).

`RestCodeCheckUtil.java` lines 525-526, 167, 209, 751, 797-800, 838, 1001, 1080, 1193, 1356; `CodeCheckOrganization.java` lines 50-60.

#### Remediation

- Rotate AK/SK; enforce per-tenant scoping; never log the `Request` object — log only safe identifiers.

#### Verification

- Inspect log output and confirm no credential-bearing Request objects are serialized.

---

## Threat Coverage Verification

| Threat ID | Finding ID | Status               |
| --------- | ---------- | -------------------- |
| T01.1     | FIND-27    | ✅ Covered (FIND-27) |
| T01.2     | FIND-27    | ✅ Covered (FIND-27) |
| T02.1     | FIND-01    | ✅ Covered (FIND-01) |
| T02.2     | FIND-07    | ✅ Covered (FIND-07) |
| T02.3     | FIND-10    | ✅ Covered (FIND-10) |
| T03.1     | FIND-03    | ✅ Covered (FIND-03) |
| T03.2     | FIND-06    | ✅ Covered (FIND-06) |
| T04.1     | FIND-02    | ✅ Covered (FIND-02) |
| T04.2     | FIND-11    | ✅ Covered (FIND-11) |
| T04.3     | FIND-28    | ✅ Covered (FIND-28) |
| T05.1     | FIND-21    | ✅ Covered (FIND-21) |
| T05.2     | FIND-05    | ✅ Covered (FIND-05) |
| T05.3     | FIND-07    | ✅ Covered (FIND-07) |
| T05.4     | FIND-10    | ✅ Covered (FIND-10) |
| T06.1     | FIND-02    | ✅ Covered (FIND-02) |
| T06.2     | FIND-07    | ✅ Covered (FIND-07) |
| T07.1     | FIND-02    | ✅ Covered (FIND-02) |
| T07.2     | FIND-12    | ✅ Covered (FIND-12) |
| T07.3     | FIND-13    | ✅ Covered (FIND-13) |
| T08.1     | FIND-03    | ✅ Covered (FIND-03) |
| T08.2     | FIND-04    | ✅ Covered (FIND-04) |
| T08.3     | FIND-12    | ✅ Covered (FIND-12) |
| T09.1     | FIND-04    | ✅ Covered (FIND-04) |
| T09.2     | FIND-03    | ✅ Covered (FIND-03) |
| T09.3     | FIND-06    | ✅ Covered (FIND-06) |
| T10.1     | FIND-24    | ✅ Covered (FIND-24) |
| T10.2     | FIND-04    | ✅ Covered (FIND-04) |
| T11.1     | FIND-14    | ✅ Covered (FIND-14) |
| T11.2     | FIND-15    | ✅ Covered (FIND-15) |
| T12.1     | FIND-08    | ✅ Covered (FIND-08) |
| T12.2     | FIND-16    | ✅ Covered (FIND-16) |
| T13.1     | FIND-08    | ✅ Covered (FIND-08) |
| T13.2     | FIND-26    | ✅ Covered (FIND-26) |
| T14.1     | FIND-07    | ✅ Covered (FIND-07) |
| T15.1     | FIND-09    | ✅ Covered (FIND-09) |
| T15.2     | FIND-17    | ✅ Covered (FIND-17) |
| T16.1     | FIND-04    | ✅ Covered (FIND-04) |
| T16.2     | FIND-08    | ✅ Covered (FIND-08) |
| T17.1     | FIND-18    | ✅ Covered (FIND-18) |
| T18.1     | FIND-05    | ✅ Covered (FIND-05) |
| T18.2     | FIND-09    | ✅ Covered (FIND-09) |
| T19.1     | FIND-25    | ✅ Covered (FIND-25) |
| T20.1     | FIND-19    | ✅ Covered (FIND-19) |
| T20.2     | FIND-29    | ✅ Covered (FIND-29) |
| T21.1     | FIND-20    | ✅ Covered (FIND-20) |
| T22.1     | FIND-30    | ✅ Covered (FIND-30) |
| T23.1     | FIND-20    | ✅ Covered (FIND-20) |
| T24.1     | FIND-21    | ✅ Covered (FIND-21) |
| T25.1     | FIND-22    | ✅ Covered (FIND-22) |
| T26.1     | FIND-02    | ✅ Covered (FIND-02) |
| T27.1     | FIND-23    | ✅ Covered (FIND-23) |
| T28.1     | FIND-27    | ✅ Covered (FIND-27) |
| T29.1     | FIND-34    | ✅ Covered (FIND-34) |
| T30.1     | FIND-01    | ✅ Covered (FIND-01) |
| T31.1     | FIND-35    | ✅ Covered (FIND-35) |
| T32.1     | FIND-31    | ✅ Covered (FIND-31) |
| T33.1     | FIND-31    | ✅ Covered (FIND-31) |
| T34.1     | FIND-32    | ✅ Covered (FIND-32) |
| T35.1     | FIND-33    | ✅ Covered (FIND-33) |
