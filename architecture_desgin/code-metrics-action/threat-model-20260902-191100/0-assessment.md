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

---

## Executive Summary

`code-metrics-action` is an OpenLibing platform GitCode CI/CD plugin (GitHub Action form) that runs on a GitCode runner and statically scans code in the workflow-owned repo for code metrics (scc for code size, lizard for function complexity, custom duplication detection). Scan results are assembled into a full JSON report, uploaded to Huawei Cloud OBS for transit storage, and metadata + OBS download links are reported to the openLiBing backend via APIG. Authentication supports two modes: OIDC federated auth with STS temporary credentials (new mode), and legacy AK/SK static credentials (compatibility mode for存量 scripts).

The system's security posture has two critical supply-chain exposures (FIND-01, FIND-02) at Tier 1 — the `obsutil` binary download from a public HTTPS mirror and the `pip install lizard --trusted-host` invocation both skip integrity verification, allowing a network-position attacker to inject malicious binaries/packages that execute with runner process privileges. Below this, 62 Tier 2 threats cover the authenticated-user attack surface (command injection, path traversal, source code disclosure, DoS) across detectors, uploaders, and configuration loaders. Twelve Tier 3 threats cover defense-in-depth scenarios requiring host/OS access or component compromise (AK/SK leakage, OIDC URL spoofing, supply-chain compromise of bundled scc). The system's existing security controls (execFileSync parameter arrays for obsutil, Base64 encoding for snapshotData, git remote URL token redaction, pre-commit gitleaks/detect-private-key hooks) mitigate some risks but leave the two supply-chain paths and several command injection paths open.

The analysis covers 19 system elements across 2 trust boundaries.

### Risk Rating: Elevated

The system has two directly-exploitable supply-chain vulnerabilities (CVSS 9.3 each) that allow unauthenticated external attackers to inject malicious code via the obsutil download mirror or the aliyun PyPI mirror, both of which disable or weaken TLS verification. Beyond these, the AK/SK legacy authentication path (FIND-16) creates a long-lived credential leakage risk that enables forged APIG signatures and arbitrary bucket access. The OIDC mode mitigates this risk but coexists with the legacy path for存量 compatibility. The risk rating is Elevated rather than Critical because the Tier 1 exposures are confined to two specific download paths (mitigatable with hash pinning or SDK replacement), and the Tier 2 exposures require authenticated access (PR submission) which the GitCode platform already throttles.

> **Note on threat counts:** This analysis identified 78 threats across 17 of 19 components (2 external interactors — GitCodeRunner and WorkflowConfig — are declared in the DFD and components inventory but excluded from STRIDE enumeration per skill convention). This count reflects comprehensive STRIDE-A coverage, not systemic insecurity. Of these, **4 are directly exploitable** without prerequisites (Tier 1). The remaining 74 represent conditional risks and defense-in-depth considerations.

---

## Action Summary

| Tier                                                                                | Description                   | Threats | Findings | Priority         |
| ----------------------------------------------------------------------------------- | ----------------------------- | ------- | -------- | ---------------- |
| [Tier 1](3-findings.md#tier-1--direct-exposure-no-prerequisites)                    | Directly exploitable          | 4       | 2        | 🔴 Critical Risk |
| [Tier 2](3-findings.md#tier-2--conditional-risk-authenticated--single-prerequisite) | Requires authenticated access | 62      | 19       | 🟠 Elevated Risk |
| [Tier 3](3-findings.md#tier-3--defense-in-depth-prior-compromise--host-access)      | Requires prior compromise     | 12      | 5        | 🟡 Moderate Risk |
| **Total**                                                                           |                               | **78**  | **26**   |                  |

### Priority by Tier and CVSS Score (Top 10)

| Finding                                                                                                | Tier | CVSS Score | SDL Severity | Title                                                                 |
| ------------------------------------------------------------------------------------------------------ | ---- | ---------- | ------------ | --------------------------------------------------------------------- |
| [FIND-01](3-findings.md#find-01-supply-chain-attack-via-untrusted-obsutil-binary-download)             | T1   | 9.3        | Critical     | Supply Chain Attack via Untrusted obsutil Binary Download             |
| [FIND-02](3-findings.md#find-02-supply-chain-attack-via-pip-install-lizard-with---trusted-host)        | T1   | 9.3        | Critical     | Supply Chain Attack via pip install lizard with --trusted-host        |
| [FIND-03](3-findings.md#find-03-command-injection-via-shell-metacharacters-in-detector-execsync-calls) | T2   | 8.8        | Critical     | Command Injection via Shell Metacharacters in Detector execSync Calls |
| [FIND-04](3-findings.md#find-04-path-traversal-via-malicious-giturl-in-extractownerrepo)               | T2   | 7.5        | Important    | Path Traversal via Malicious gitUrl in extractOwnerRepo               |
| [FIND-05](3-findings.md#find-05-arbitrary-file-read-via-untrusted-lizard-output)                       | T2   | 7.5        | Important    | Arbitrary File Read via Untrusted lizard Output                       |
| [FIND-15](3-findings.md#find-15-dns-spoofing-and-mitm-of-external-endpoints)                           | T2   | 7.5        | Important    | DNS Spoofing and MitM of External Endpoints                           |
| [FIND-09](3-findings.md#find-09-output-path-traversal-via-unvalidated-output-parameter)                | T2   | 6.5        | Important    | Output Path Traversal via Unvalidated output Parameter                |
| [FIND-11](3-findings.md#find-11-input-environment-variable-override-of-security-inputs)                | T2   | 6.5        | Important    | Input Environment Variable Override of Security Inputs                |
| [FIND-13](3-findings.md#find-13-scc-binary-path-spoofing)                                              | T2   | 6.5        | Important    | scc Binary Path Spoofing                                              |
| [FIND-17](3-findings.md#find-17-apig-signer-input-validation-missing)                                  | T2   | 6.5        | Important    | APIG Signer Input Validation Missing                                  |

### Quick Wins

| Finding                                                                                                | Title                                                                 | Why Quick                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [FIND-03](3-findings.md#find-03-command-injection-via-shell-metacharacters-in-detector-execsync-calls) | Command Injection via Shell Metacharacters in Detector execSync Calls | Replace `execSync(cmdString, { shell })` with `execFileSync(binary, argsArray, { shell: false })` — purely mechanical change with no API surface impact. |
| [FIND-08](3-findings.md#find-08-missing-timeouts-on-external-network-calls)                            | Missing Timeouts on External Network Calls                            | Add `timeout: 60000` to `execFileSync`/`axios.post` calls — single-line change per call site, prevents indefinite hangs.                                 |
| [FIND-09](3-findings.md#find-09-output-path-traversal-via-unvalidated-output-parameter)                | Output Path Traversal via Unvalidated output Parameter                | Add `path.resolve` + `path.relative` prefix check in `FileUtils.writeJsonFile` — 3-line validation block, prevents arbitrary file writes.                |
| [FIND-11](3-findings.md#find-11-input-environment-variable-override-of-security-inputs)                | Input Environment Variable Override of Security Inputs                | Add workflow-YAML convention check for security-critical inputs — documentation + simple `getInput` source validation.                                   |
| [FIND-13](3-findings.md#find-13-scc-binary-path-spoofing)                                              | scc Binary Path Spoofing                                              | Restrict `getSccPath()` to single canonical `path.join(bundleRoot, 'bin', 'scc')` — removes ancestor directory candidates, single-line fix.              |
| [FIND-17](3-findings.md#find-17-apig-signer-input-validation-missing)                                  | APIG Signer Input Validation Missing                                  | Add `if (!ak                                                                                                                                             |     | !sk) throw` constructor check + URL length cap — straightforward input validation pattern. |
| [FIND-22](3-findings.md#find-22-redos-via-user-supplied-glob-patterns)                                 | ReDoS via User-Supplied Glob Patterns                                 | Install `safe-regex` package and pre-check compiled RegExp — single library call before regex use.                                                       |

---

## Analysis Context & Assumptions

### Analysis Scope

| Constraint  | Description                                                                                                                                                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Scope       | Single analysis of `code-metrics-action` repository at commit `1ae6958` on branch `code-metrics-oidc-auth`. Covers all `dist/` ncc-bundled source code, `action.yml`, `package.json`, and `.gitcode/workflows/*.yml`.                 |
| Excluded    | `node_modules/`, `.git/`, `dist/bin/scc` binary contents (treated as opaque), `metrics.json` example file. The OIDC SDK (`@openlibing/huaweicloud-oidc-client@0.0.5`) is treated as a black-box external dependency.                  |
| Focus Areas | Supply chain risks (obsutil download, pip install), command injection paths (execSync string concatenation), path traversal (extractOwnerRepo, output parameter), credential handling (AK/SK vs OIDC), CI runner deployment boundary. |

### Infrastructure Context

| Category                 | Discovered from Codebase                                                                      | Findings Affected                                                                                                                              |
| ------------------------ | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| CI_RUNNER Deployment     | `0.1-architecture.md` Deployment Classification section; `action.yml` `using: node16`         | FIND-03, FIND-06, FIND-07, FIND-08, FIND-09, FIND-10, FIND-11, FIND-12, FIND-13, FIND-14, FIND-17, FIND-18, FIND-19, FIND-20, FIND-21, FIND-22 |
| External HTTPS endpoints | `0.1-architecture.md` Component Exposure Table; OBS/APIG/OIDC/mirror endpoints                | FIND-01, FIND-02, FIND-08, FIND-15, FIND-16, FIND-23, FIND-26                                                                                  |
| OIDC + AK/SK dual auth   | `0.1-architecture.md` Scenario 1 + Scenario 2; `dist/index.js:62363` `useOidc` presence check | FIND-16, FIND-23, FIND-26                                                                                                                      |
| ncc-bundled binaries     | `0.1-architecture.md` Technology Stack; `dist/bin/scc`                                        | FIND-13, FIND-24, FIND-25                                                                                                                      |

### Needs Verification

| Item                                                 | Question                                                                                                                | What to Check                                                                                                              | Why Uncertain                                                                                                                                                          |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitCode platform env var injection policy            | Does GitCode CI allow PR-comment or branch-name values to flow into `INPUT_*` env vars for workflow steps?              | GitCode CI platform documentation; empirical test by submitting a PR with crafted branch name and inspecting `env` context | The threat model assumes GitHub Actions convention applies; GitCode may differ in env var scoping for PR-triggered runs.                                               |
| `huaweicloud-oidc-client@0.0.5` SDK security posture | Does the SDK perform issuer validation, nonce checking, and timestamp window enforcement on V11-HMAC-SHA256 signatures? | SDK source code (not included in this analysis); SDK changelog and security advisories                                     | The SDK is treated as a black box; vulnerabilities would surface as Tier 3 abuse threats (T14.A, T15.A, T26).                                                          |
| APIG endpoint IP allow-list and replay protection    | Is the APIG `/metrics/code/report` endpoint configured with IP allow-list and 5-minute timestamp window?                | APIG gateway configuration (not in repo)                                                                                   | FIND-16 and FIND-26 remediation depends on APIG-side controls that cannot be verified from the plugin code.                                                            |
| Runner image hardening                               | Are GitCode-hosted runners ephemeral (single-use) or reused across workflows? Is `os.tmpdir()` cleaned between runs?    | GitCode runner documentation; runner image build scripts                                                                   | FIND-10 and FIND-12 assume `os.tmpdir()` is shared across workflow steps on the same runner; if runners are ephemeral and per-job, the race condition risk is reduced. |
| OBS bucket ACL                                       | Is the `openlibing-gitcode-action` bucket configured with public-read or owner-only ACL?                                | OBS bucket policy (not in repo)                                                                                            | FIND-19 assumes the bucket is private; if the bucket is misconfigured as public-read, source code snippets would leak to the internet.                                 |

### Finding Overrides

| Finding ID | Original Severity | Override | Justification                                           | New Status |
| ---------- | ----------------- | -------- | ------------------------------------------------------- | ---------- |
| —          | —                 | —        | No overrides applied. Update this section after review. | —          |

### Additional Notes

No additional notes.

---

## References Consulted

### Security Standards

| Standard                      | URL                                                                                   | How Used                                                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Microsoft SDL Bug Bar         | https://www.microsoft.com/en-us/msrc/sdlbugbar                                        | Severity classification                                                                                         |
| OWASP Top 10:2025             | https://owasp.org/Top10/2025/                                                         | Threat categorization                                                                                           |
| CVSS 4.0                      | https://www.first.org/cvss/v4.0/specification-document                                | Risk scoring                                                                                                    |
| CWE                           | https://cwe.mitre.org/                                                                | Weakness classification                                                                                         |
| STRIDE                        | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats | Threat enumeration                                                                                              |
| GitHub Actions Security Guide | https://docs.github.com/en/actions/security-guides                                    | CI runner security best practices for `INPUT_*` env var convention and `ACTIONS_ID_TOKEN_REQUEST_URL` OIDC flow |
| PEP 668                       | https://peps.python.org/pep-0668/                                                     | `--break-system-packages` risk context (externally-managed environment protection)                              |

### Component Documentation

| Component                                 | Documentation URL                                                 | Relevant Section                                                |
| ----------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------- |
| `@openlibing/huaweicloud-oidc-client` SDK | https://www.npmjs.com/package/@openlibing/huaweicloud-oidc-client | OIDC federated auth flow, V11-HMAC-SHA256 signing               |
| Huawei Cloud OBS                          | https://www.huaweicloud.com/intl/en-us/product/obs.html           | OBS bucket ACL, STS temporary credentials, obsutil CLI          |
| Huawei Cloud APIG                         | https://www.huaweicloud.com/intl/en-us/product/apig.html          | APIG SDK-HMAC-SHA256 signing, IP allow-list, replay protection  |
| `@vercel/ncc`                             | https://github.com/vercel/ncc                                     | ncc packaging process, dist bundling, supply chain implications |
| `scc` (Sloc Cloc and Code)                | https://github.com/boyter/scc                                     | scc binary distribution, SBOM/provenance                        |
| `lizard`                                  | https://github.com/terryyin/lizard                                | lizard package distribution, PyPI mirror trust                  |
| GitCode Actions                           | https://gitcode.com/docs/actions                                  | GitCode CI runner env var injection, OIDC token provider        |

---

## Report Metadata

| Field              | Value                                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Source Location    | `d:\Develop\Java\code-metrics-action`                                                                                                                  |
| Git Repository     | `https://gitcode.com/openlibing/code-metrics-action.git`                                                                                               |
| Git Branch         | `code-metrics-oidc-auth`                                                                                                                               |
| Git Commit         | `1ae6958` (`2026-09-02`)                                                                                                                               |
| Model              | `GLM-5.2`                                                                                                                                              |
| Machine Name       | `DESKTOP-1L0N2MM`                                                                                                                                      |
| Analysis Started   | `2026-09-02T03:00:00Z`                                                                                                                                 |
| Analysis Completed | `2026-09-02T11:11:13Z`                                                                                                                                 |
| Duration           | `8h 11m 13s`                                                                                                                                           |
| Output Folder      | `d:\Develop\Java\openlibing-docs\architecture_desgin\threat-models\code-metrics-action`                                                                |
| Prompt             | `你是一名 Threat Model Analyst 专家。请对 Node.js 仓库 d:\Develop\Java\code-metrics-action 执行完整的 STRIDE-A 威胁建模分析（Single Analysis Mode）。` |

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
