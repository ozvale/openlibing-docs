# Security Findings

---

## Tier 1 — Direct Exposure (No Prerequisites)

### FIND-01: Supply Chain Attack via Untrusted obsutil Binary Download

| Attribute                  | Value                                                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Critical                                                                                                                        |
| CVSS 4.0                   | 9.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N)                                                           |
| CWE                        | [CWE-494](https://cwe.mitre.org/data/definitions/494.html): Download of Code Without Integrity                                  |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                                                 |
| Exploitation Prerequisites | None                                                                                                                            |
| Exploitability Tier        | Tier 1 — Direct Exposure (no prerequisites); the obsutil download mirror is a public HTTPS endpoint requiring no authentication |
| Remediation Effort         | Medium                                                                                                                          |
| Mitigation Type            | Standard Mitigation                                                                                                             |
| Component                  | ObsutilDownloadMirror                                                                                                           |
| Related Threats            | [T16.S](2-stride-analysis.md#obsutildownloadmirror), [T16.T](2-stride-analysis.md#obsutildownloadmirror)                        |

#### Description

`CoderepoUploader.ensureObsutil()` downloads the obsutil binary tarball from a public HTTPS mirror (`obs-community.obs.cn-north-1.myhuaweicloud.com`) using shell-based `wget`/`curl` commands without verifying the artifact's integrity (no SHA256 hash check, no signature verification). After download, the tarball is extracted with `tar -xzf`, the binary is `chmod 755`'d, and then executed via `execFileSync` to upload metrics to OBS. An attacker who controls the mirror endpoint — via DNS spoofing, network MitM at the egress, or compromise of the public mirror — can replace the obsutil binary with a malicious payload that runs with the runner process privileges immediately after extraction.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table in `0.1-architecture.md`, `ObsutilDownloadMirror` listens on `obs-community.obs.cn-north-1.myhuaweicloud.com:443`, requires No auth, Reachability = External, Min Prerequisite = None, Derived Tier = T1. The download URL is hardcoded and the runner has no built-in trust anchor for verifying the binary.

- `dist/uploaders/CoderepoUploader.js:438-450` — hardcoded `downloadUrl` and shell-based `execSync('wget -q "${downloadUrl}" -O "${tarball}" 2>/dev/null || curl -sL "${downloadUrl}" -o "${tarball}"', { shell: '/bin/bash' })`
- `dist/uploaders/CoderepoUploader.js:451-466` — `tar -xzf` extraction + `fs.chmodSync(candidate, 0o755)` + `execFileSync` execution

#### Remediation

- Pin the SHA256 hash of the official obsutil release; verify the downloaded tarball against this hash before extraction, aborting on mismatch.
- Prefer the official `@huaweicloud/huaweicloud-obs` Node.js SDK over the external obsutil binary, eliminating the binary download path entirely.
- Configure HTTPS certificate pinning for the download endpoint; do not silently fall back to system obsutil without verification.

#### Verification

- Confirm `ensureObsutil()` contains a SHA256 verification step before `chmod`/`execFileSync`.
- Run a unit test with a tampered tarball and confirm the verification rejects the modified artifact.
- Verify no `--no-check-certificate` or trust-bypassing flags are present in download commands.

### FIND-02: Supply Chain Attack via pip install lizard with --trusted-host

| Attribute                  | Value                                                                                                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Critical                                                                                                                                                  |
| CVSS 4.0                   | 9.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N)                                                                                     |
| CWE                        | [CWE-494](https://cwe.mitre.org/data/definitions/494.html): Download of Code Without Integrity                                                            |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                                                                           |
| Exploitation Prerequisites | None                                                                                                                                                      |
| Exploitability Tier        | Tier 1 — Direct Exposure (no prerequisites); the PyPI mirror is a public HTTPS endpoint and lizard package uploads require no authentication to influence |
| Remediation Effort         | Medium                                                                                                                                                    |
| Mitigation Type            | Standard Mitigation                                                                                                                                       |
| Component                  | PyPIMirror                                                                                                                                                |
| Related Threats            | [T17.S](2-stride-analysis.md#pypimirror), [T17.T](2-stride-analysis.md#pypimirror), [T17.E](2-stride-analysis.md#pypimirror)                              |

#### Description

`CodeMetricsAction.run()` invokes `pip install --break-system-packages --trusted-host mirrors.aliyun.com lizard` with `stdio: 'inherit'` and a 120-second timeout. The `--trusted-host` flag explicitly disables TLS certificate verification against the aliyun mirror, allowing any network-position attacker to inject a malicious `lizard` package that executes arbitrary Python code with runner process privileges. Because the aliyun PyPI mirror accepts package uploads from any authenticated account holder (a low bar), an attacker need not even compromise the mirror — they can register a similarly-named package or typosquat the canonical `lizard` package to win a dependency confusion race.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table in `0.1-architecture.md`, `PyPIMirror` listens on `mirrors.aliyun.com:443`, requires No auth, Reachability = External, Min Prerequisite = None, Derived Tier = T1. The pip command line opts out of TLS verification entirely.

- `dist/index.js:62468-62478` — `pip install --break-system-packages --trusted-host mirrors.aliyun.com lizard` invoked via `execSync` with `stdio: 'inherit'`, `timeout: 120000`
- `package.json:15` — direct dependency on lizard as runtime tool, no pinned hash

#### Remediation

- Remove `--trusted-host mirrors.aliyun.com`; let pip verify TLS certificates against the system CA bundle.
- Pin lizard to a specific version and add `--require-hashes` with a verified hash in a constraints file (`lizard==1.17.9 --hash=sha256:...`).
- Run `pip install` inside a `python3 -m venv /tmp/lizard-venv` to isolate the install from the runner's system Python.
- Reduce timeout to 60s and surface a clear warning if the install fails (don't silently warn and continue).

#### Verification

- Confirm `pip install` invocation no longer includes `--trusted-host` and the constraints file contains pinned hashes.
- Run a test with a typosquatted package name to verify pip refuses to install it.
- Verify `python3 -m venv` invocation precedes `pip install` and the venv is removed after scan.

---

## Tier 2 — Conditional Risk (Authenticated / Single Prerequisite)

### FIND-03: Command Injection via Shell Metacharacters in Detector execSync Calls

| Attribute                  | Value                                                                                                                                    |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Critical                                                                                                                                 |
| CVSS 4.0                   | 8.8 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N)                                                                    |
| CWE                        | [CWE-78](https://cwe.mitre.org/data/definitions/78.html): OS Command Injection                                                           |
| OWASP                      | A03:2025 – Injection                                                                                                                     |
| Exploitation Prerequisites | Authenticated User                                                                                                                       |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can submit a malicious repo/PR triggering the detectors)                                   |
| Remediation Effort         | Low                                                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                                                      |
| Component                  | SlocDetector, LizardDetector, CoderepoUploader                                                                                           |
| Related Threats            | [T03.T](2-stride-analysis.md#slocdetector), [T04.T](2-stride-analysis.md#lizarddetector), [T08.T](2-stride-analysis.md#coderepouploader) |

#### Description

Three detector/uploader paths construct shell command strings by concatenating file paths and arguments, then pass them to `execSync(cmd, { shell: '/bin/bash' })` instead of using parameter-array forms like `execFileSync`. If any concatenated segment contains shell metacharacters (`$()`, `` ` ``, `;`, `&&`, `|`) and an attacker can control that segment — for example by manipulating the `TMPDIR` environment variable, by injecting a malicious `gitUrl` with crafted owner/repo, or by supplying a `sources` path containing special characters — the resulting shell command will execute unintended commands with runner process privileges. The risk is amplified because all three detectors run synchronously and inherit stdio, so a successful injection has full pipeline access.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, the detectors run on the GitCode Runner with Reachability = No Listener, Min Prerequisite = Authenticated User (the attacker must submit a PR or workflow config that influences the concatenated segments). The runner is platform-scheduled (CI_RUNNER deployment classification), so external unauthenticated attackers cannot reach these components directly.

- `dist/detectors/SlocDetector.js:111-118` — `const cmd = '"${this.sccPath}" ${args.join(" ")}'; execSync(cmd)` (string concatenation + shell)
- `dist/detectors/LizardDetector.js:89` — `execSync('python3 -m lizard ' + args.join(' '))` (string concatenation, no shell specified but Node defaults to /bin/sh)
- `dist/uploaders/CoderepoUploader.js:446-450` — `execSync('wget -q "${downloadUrl}" -O "${tarball}" 2>/dev/null || curl -sL "${downloadUrl}" -o "${tarball}"', { shell: '/bin/bash' })` (TMPDIR-controlled `tarball` segment)

#### Remediation

- Replace `execSync(cmdString, { shell })` with `execFileSync(binary, argsArray, { shell: false })` so arguments bypass the shell entirely.
- For `SlocDetector.runScc()`: `execFileSync(this.sccPath, args, { maxBuffer: 100*1024*1024, timeout: 300000 })`.
- For `LizardDetector.runLizard()`: `execFileSync('python3', ['-m', 'lizard', '-f', tempInputPath, '-o', tempJsonPath], { maxBuffer, timeout })`.
- For `CoderepoUploader.ensureObsutil()`: use Node.js built-in `https.get` or `execFileSync('wget', ['-q', downloadUrl, '-O', tarball])`.
- Validate that `os.tmpdir()` does not contain shell metacharacters before constructing paths.

#### Verification

- Inspect each detector's exec call to confirm `shell: false` and argument-array form is used.
- Run a test with a `TMPDIR` containing `; touch /tmp/pwn` and confirm no file is created.
- Verify `node --check dist/detectors/SlocDetector.js` and equivalent for other detectors pass.

### FIND-04: Path Traversal via Malicious gitUrl in extractOwnerRepo

| Attribute                  | Value                                                                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                                            |
| CVSS 4.0                   | 7.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:H/SI:N/SA:N)                                                                |
| CWE                        | [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Path Traversal                                                             |
| OWASP                      | A01:2025 – Broken Access Control                                                                                                     |
| Exploitation Prerequisites | Authenticated User                                                                                                                   |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can set `gitUrl` action input to a malicious value)                                    |
| Remediation Effort         | Low                                                                                                                                  |
| Mitigation Type            | Standard Mitigation                                                                                                                  |
| Component                  | DuplicationDetector, CoderepoUploader, OBS                                                                                           |
| Related Threats            | [T05.A](2-stride-analysis.md#duplicationdetector), [T08.A](2-stride-analysis.md#coderepouploader), [T13.A](2-stride-analysis.md#obs) |

#### Description

`CoderepoUploader.extractOwnerRepo()` parses the user-supplied `gitUrl` with a permissive regex (`(?:git@[^:]+:|https?://[^/]+/)(.+)$`) and uses the captured `ownerRepo` substring to construct the OBS objectKey (`code-metrics-action/${ownerRepo}/${pipelineRunId}/${ts}-metrics.json`). The function does not normalize `..` segments, strip leading slashes, or enforce a strict `owner/repo` format. An attacker who supplies a `gitUrl` like `https://gitcode.com/foo/../../other-owner/repo` can cause the resulting objectKey to escape the intended per-owner namespace, writing metrics to another owner's directory or tricking the backend into reading attacker-controlled data when it later fetches by objectKey.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `CoderepoUploader` is on the GitCode Runner (CI_RUNNER deployment). The `gitUrl` is read from action inputs (`dist/index.js:62399` cleans embedded tokens but does not normalize path segments). The attacker must be authenticated to submit a workflow config or PR that overrides the `gitUrl` input.

- `dist/uploaders/CoderepoUploader.js:475-480` — `buildObjectKey` concatenates `${ownerRepo}/${pipelineRunId}/${ts}-metrics.json` without sanitization
- `dist/uploaders/CoderepoUploader.js:488-495` — `extractOwnerRepo` regex captures the remainder of the URL path verbatim into `ownerRepo`
- `dist/uploaders/CoderepoUploader.js:535` — `buildObjectKey` is also called from the upload path; same objectKey is later downloaded by the backend

#### Remediation

- After regex capture, normalize `ownerRepo`: reject if it contains `..`, `//`, leading/trailing slashes, or empty segments.
- Enforce strict `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` on the captured `ownerRepo`; on mismatch, fall back to a hash of the URL or abort the upload with a clear error.
- On the backend, when fetching by objectKey, verify the requesting principal owns the `ownerRepo` segment before serving metrics data.

#### Verification

- Unit test `extractOwnerRepo` with `https://gitcode.com/foo/../../other/repo` and confirm rejection or normalization.
- Confirm objectKey does not contain `..` for any well-formed `gitUrl`.
- Backend: integration test that an authenticated user cannot read another owner's objectKey.

### FIND-05: Arbitrary File Read via Untrusted lizard Output

| Attribute                  | Value                                                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                   |
| CVSS 4.0                   | 7.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:L/SI:N/SA:N)                                       |
| CWE                        | [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Path Traversal                                    |
| OWASP                      | A01:2025 – Broken Access Control                                                                            |
| Exploitation Prerequisites | Authenticated User                                                                                          |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can submit a repo that produces a crafted lizard JSON output) |
| Remediation Effort         | Medium                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                         |
| Component                  | LizardDetector                                                                                              |
| Related Threats            | [T04.I](2-stride-analysis.md#lizarddetector), [T04.E](2-stride-analysis.md#lizarddetector)                  |

#### Description

`LizardDetector.parseTextOutput()` parses lizard's text output with a regex that captures a `filePath` group (group 9), and the code immediately passes this `filePath` to `fs.readFileSync(filePath, 'utf8')` to compute body NLOC. Because lizard's output reflects whatever file paths it scanned — and an attacker can construct a repo with symlinks or path-traversal segments in source file names — the captured `filePath` may point to an arbitrary runner-readable file (`/etc/passwd`, `~/.ssh/id_rsa`, GitHub-style `/etc/secrets/*`). The file's content is then loaded into the runner process memory and may leak via subsequent error logging or aggregated fileDetails fields.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `LizardDetector` is on the GitCode Runner (CI_RUNNER deployment), Reachability = No Listener, Min Prerequisite = Authenticated User. An authenticated user submits a repo whose file paths influence lizard's text output.

- `dist/detectors/LizardDetector.js:155` — regex `^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+?)@(\d+)-(\d+)@(.+)$` captures `filePath` verbatim
- `dist/detectors/LizardDetector.js:168` — `fs.readFileSync(filePath, 'utf8')` reads the file content unconditionally
- `dist/detectors/LizardDetector.js:269` — `fs.readFileSync(func.filename, 'utf8')` repeats the same pattern in `aggregateFileDetails`

#### Remediation

- Before calling `fs.readFileSync`, verify `filePath` resolves to a location within the configured `sources` array (use `path.resolve` + prefix check).
- Reject or skip any `filePath` that is an absolute path outside workspace, contains `..` segments after normalization, or is a symlink pointing outside workspace.
- Consider switching to lizard's JSON output (`-f json`) and parsing structured fields rather than text regex, reducing the surface for path injection.

#### Verification

- Unit test with a synthetic lizard output containing `filePath=/etc/passwd` and confirm the function skips the entry.
- Symlink test: create a symlink `evil.txt -> /etc/passwd` in workspace, run lizard, confirm the target file is not read.
- Run lizard with `-f json` and verify no `readFileSync` of untrusted paths occurs.

### FIND-06: Sensitive Data Leakage in Console Logs

| Attribute                  | Value                                                                                                                                                                                                                                                                                                                                                                                                                |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                                                                                                                                                                                                                                                                                             |
| CVSS 4.0                   | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                                                                                                                                                                                                                                                                                                                                |
| CWE                        | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File                                                                                                                                                                                                                                                                                                         |
| OWASP                      | A09:2025 – Security Logging and Monitoring Failures                                                                                                                                                                                                                                                                                                                                                                  |
| Exploitation Prerequisites | Authenticated User                                                                                                                                                                                                                                                                                                                                                                                                   |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can submit inputs that influence logged content; logs are visible to the workflow run, downstream steps, and CI platform UI)                                                                                                                                                                                                                                           |
| Remediation Effort         | Low                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Mitigation Type            | Standard Mitigation                                                                                                                                                                                                                                                                                                                                                                                                  |
| Component                  | CodeMetricsAction, SlocDetector, FileCollector, CoderepoUploader, ApigSigner, APIG, HuaweiCloudOIDC, ObsutilDownloadMirror, PyPIMirror                                                                                                                                                                                                                                                                               |
| Related Threats            | [T01.I](2-stride-analysis.md#codemetricsaction), [T03.I](2-stride-analysis.md#slocdetector), [T07.I](2-stride-analysis.md#filecollector), [T08.I](2-stride-analysis.md#coderepouploader), [T09.I](2-stride-analysis.md#apigsigner), [T14.I](2-stride-analysis.md#apig), [T15.I](2-stride-analysis.md#huaweicloudoidc), [T16.I](2-stride-analysis.md#obsutildownloadmirror), [T17.I](2-stride-analysis.md#pypimirror) |

#### Description

Numerous `console.log`/`console.error`/`core.info` calls across the codebase output absolute file paths, AK identifiers, command lines, and error response messages to the CI runner's stdout/stderr. CI platforms persist this output with the workflow run and surface it to anyone with read access on the repo, including PR contributors who do not have repo admin privileges. The most impactful leakage is in `CoderepoUploader.execObsutil` which prints the full obsutil command line including `-i=STS_AK`/`-i=OBS_AK` (the unmasked access key ID), allowing a PR author to harvest AKs from a single failed-upload log. The `ApigSigner` Authorization header includes the AK in cleartext, and the `CodeMetricsAction` entry point logs `commitId` and `gitUrl` which can be cross-referenced to track individual developer behavior across pipelines.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, all affected components run on the GitCode Runner (CI_RUNNER deployment) with Min Prerequisite = Authenticated User. The authenticated user must be able to view the workflow run logs (default for PR contributors).

- `dist/index.js:62483-62486` — `core.info` outputs `gitUrl`, `branchName`, `pipelineRunId`, `commitId`
- `dist/detectors/SlocDetector.js:40, 158, 192` — `console.log` outputs scc command line + absolute file paths
- `dist/utils/fileCollector.js:199, 219` — `console.warn` outputs `[WARN] 路径不存在: ${absolutePath}` and `[WARN] 文件扩展名不在允许列表中: ${absolutePath}`
- `dist/uploaders/CoderepoUploader.js:425` — `console.log('[upload] exec obsutil ${maskedArgs.join(" ")}')` — `-k=***`/`-t=***` are masked but `-i=STS_AK`/`-i=OBS_AK` are NOT masked
- `dist/uploaders/CoderepoUploader.js:138` — Authorization header `SDK-HMAC-SHA256 Access=${this.ak}, SignedHeaders=..., Signature=...` exposes ak
- `dist/uploaders/CoderepoUploader.js:642, 657` — `console.error` outputs `resData?.msg || resData?.message` from APIG responses
- `dist/index.js:62474` — `pip install` uses `stdio: 'inherit'` exposing package names/versions/download URLs

#### Remediation

- In `CoderepoUploader.execObsutil`, mask all three credential arguments (`-i=`, `-k=`, `-t=`) to `***` (only first 4 chars + `***` if debugging is needed).
- Replace all `console.log`/`core.info` of absolute paths with relative paths computed against `this.workingDir`.
- Move `commitId` and `gitUrl` to `core.debug` (only emitted when `verbose=true`); keep `pipelineRunId` as the only identity signal in `core.info`.
- Wrap `console.error` of APIG responses with a sanitizer that emits only `code` and a short canned message; never the raw `msg`.
- Change `pip install` to `stdio: 'pipe'` and emit a short summary on success, full stderr only on failure.

#### Verification

- Search the codebase for `console.log`, `console.error`, `core.info` and confirm none output absolute paths, AKs, or raw response msgs.
- Run a workflow with `ACTIONS_STEP_DEBUG=false` and confirm `commitId`/`gitUrl` are absent from logs.
- Run a workflow with a forced upload failure and confirm the log contains no `STS_AK`/`OBS_AK` substring.

### FIND-07: Resource Exhaustion DoS via Large Inputs

| Attribute                  | Value                                                                                                                                                                                                                                                                                                                                                                       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                                                                                                                                                                                                                                   |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N)                                                                                                                                                                                                                                                                                                       |
| CWE                        | [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption                                                                                                                                                                                                                                                                               |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                                                                                                                                                                                                                                                                                        |
| Exploitation Prerequisites | Authenticated User                                                                                                                                                                                                                                                                                                                                                          |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can submit a repo with a large file count or pathological structure)                                                                                                                                                                                                                                                          |
| Remediation Effort         | Medium                                                                                                                                                                                                                                                                                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                                                                                                                                                                                                                                                                                         |
| Component                  | SlocDetector, LizardDetector, DuplicationDetector, ConfigLoader, FileCollector, WorkspaceRepo, MetricsOutputFile, TempFiles                                                                                                                                                                                                                                                 |
| Related Threats            | [T03.D](2-stride-analysis.md#slocdetector), [T04.D](2-stride-analysis.md#lizarddetector), [T05.D](2-stride-analysis.md#duplicationdetector), [T06.D](2-stride-analysis.md#configloader), [T07.D](2-stride-analysis.md#filecollector), [T10.D](2-stride-analysis.md#workspacerepo), [T11.D](2-stride-analysis.md#metricsoutputfile), [T12.D](2-stride-analysis.md#tempfiles) |

#### Description

The detectors and supporting utilities lack hard upper bounds on input size and recursion depth. `SlocDetector.runScc()` allocates a 100MB maxBuffer; `LizardDetector.runLizard()` uses 50MB; `DuplicationDetector.detectWithLineLevel()` performs cross-file union-find matching that can degrade to O(n²) on adversarial input; `FileCollector._walkDir()` recurses directories without a depth cap; `ConfigLoader.load()` does not bound the config file size before parsing. An authenticated user can submit a repo with one million empty files, a single 5 GB generated source file, or a 1000-deep directory tree, causing the runner to OOM, exceed V8's string length limit, or hit a stack overflow — failing the workflow and consuming runner resources that other workflows on the same runner share.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, all affected components are on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker must be able to submit a PR with adversarial repo content.

- `dist/detectors/SlocDetector.js:114-117` — `execSync` with `maxBuffer: 100 * 1024 * 1024`, `timeout: 300000`; fallback iterates all files individually
- `dist/detectors/LizardDetector.js:90-93` — `execSync` with `maxBuffer: 50 * 1024 * 1024`, `timeout: 300000`
- `dist/detectors/DuplicationDetector.js` — `detectWithLineLevel` cross-file matching has no row/file cap
- `dist/utils/fileCollector.js` — `_walkDir` recursion has no `maxDepth` parameter
- `dist/config/loader.js:46` — `yaml.load(fileContent)` after `fs.readFileSync` without size check
- `dist/scanner.js:144-167` — `clipOversizeContent` 15KB cap exists for `duplicationOccurrences` but `fileDetails` is uncapped
- `dist/scanner.js:170` — `logger.info` of `JSON.stringify(compactResult).length` indicates whole-result serialization

#### Remediation

- Add a `maxFileCount` cap (e.g., 100000) and `maxFileSize` cap (e.g., 10MB per file) in `FileCollector.collect()`; abort scan with a clear warning if either is exceeded.
- Cap `maxDepth` in `_walkDir` (e.g., 32) and skip deeper entries with a warning.
- Cap `lizard` input by batching files into chunks of N (e.g., 500 per invocation) to bound maxBuffer pressure.
- Cap `duplicationOccurrences` count (e.g., 1000) and truncate with a warning when exceeded.
- Pre-check `fs.statSync(configFile).size` against a 1MB limit before `yaml.load`.
- For `MetricsOutputFile`: switch to streaming `fs.createWriteStream` + JSON.stringify chunked writes to avoid V8 string-length limit.

#### Verification

- Unit test with a synthetic 100k-file workspace and confirm the cap triggers an abort before OOM.
- Run `lizard` against a 100k-function repo and confirm no `Invalid string length` error.
- Verify config loader rejects files larger than 1MB with a clear error message.

### FIND-08: Missing Timeouts on External Network Calls

| Attribute                  | Value                                                                                                                                                                                                                                    |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                                                                                                                 |
| CVSS 4.0                   | 4.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N)                                                                                                                                                                    |
| CWE                        | [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption                                                                                                                                            |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                                                                                                                                                     |
| Exploitation Prerequisites | Authenticated User                                                                                                                                                                                                                       |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can trigger external network calls; an attacker-controlled or stalled endpoint can hang the runner)                                                                                        |
| Remediation Effort         | Low                                                                                                                                                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                                                                                                                                                      |
| Component                  | CodeMetricsAction, CoderepoUploader, ApigSigner, ObsutilDownloadMirror, PyPIMirror                                                                                                                                                       |
| Related Threats            | [T01.D](2-stride-analysis.md#codemetricsaction), [T08.D](2-stride-analysis.md#coderepouploader), [T09.D](2-stride-analysis.md#apigsigner), [T16.D](2-stride-analysis.md#obsutildownloadmirror), [T17.D](2-stride-analysis.md#pypimirror) |

#### Description

Multiple external-network invocations either omit the `timeout` option entirely or set it so high that a stalled endpoint can pin runner resources for minutes. `CoderepoUploader.execObsutil` calls `execFileSync(obsutil, args, { stdio: 'inherit' })` with no timeout, so a slow OBS endpoint will hang the workflow indefinitely. The `pip install lizard` 120s timeout is generous enough that a slow aliyun mirror can stall the workflow for 2 minutes per run. The `obsutil` download path uses `execSync` for the `wget`/`curl` fallback without a timeout. None of these paths implement a circuit breaker or retry cap, so a single stalled endpoint stalls the entire workflow.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, all five components are on the GitCode Runner (CI_RUNNER deployment) and reach External endpoints (OBS, APIG, aliyun PyPI, huaweicloud obsutil mirror). Min Prerequisite = Authenticated User (the attacker must trigger a workflow run).

- `dist/uploaders/CoderepoUploader.js:426` — `execFileSync(obsutil, args, { stdio: 'inherit' })` with no `timeout`
- `dist/uploaders/CoderepoUploader.js:446-450` — `execSync('wget ... || curl ...', { shell: '/bin/bash' })` with no `timeout`
- `dist/index.js:62474` — `execSync` of `pip install` with `timeout: 120000` (overly generous)
- `dist/uploaders/CoderepoUploader.js:613-660` — `axios.post` to APIG without explicit `timeout` (axios default is 0 = no timeout)

#### Remediation

- Add `timeout: 60000` (60s) to `execFileSync(obsutil, ...)` and clean up tmpFile in a `finally` block on timeout.
- Add `timeout: 30000` (30s) to the `wget`/`curl` download; on timeout, fall back to Node.js `https.get` with its own timeout.
- Reduce `pip install` timeout to 60s; on failure, emit a clear warning and skip LizardDetector rather than blocking the scan.
- Pass `timeout: 30000` to `axios.post` for the APIG /report call; on timeout, log a sanitized error and return a failure result.

#### Verification

- Confirm each external call has a `timeout` option set.
- Test with a mock OBS endpoint that stalls (e.g., `nc -l 8888`) and verify the workflow aborts within 60s.
- Verify the `finally` block removes tmpFile after a timeout.

### FIND-09: Output Path Traversal via Unvalidated output Parameter

| Attribute                  | Value                                                                                                                                                             |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                         |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:L/SC:L/SI:N/SA:N)                                                                                             |
| CWE                        | [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Path Traversal                                                                                          |
| OWASP                      | A01:2025 – Broken Access Control                                                                                                                                  |
| Exploitation Prerequisites | Local Process Access                                                                                                                                              |
| Exploitability Tier        | Tier 2 — Conditional Risk (Local Process Access to set the `output` action input; CI_RUNNER deployment means the attacker must already control the workflow YAML) |
| Remediation Effort         | Low                                                                                                                                                               |
| Mitigation Type            | Standard Mitigation                                                                                                                                               |
| Component                  | MetricsOutputFile                                                                                                                                                 |
| Related Threats            | [T11.T](2-stride-analysis.md#metricsoutputfile), [T11.A](2-stride-analysis.md#metricsoutputfile), [T11.I](2-stride-analysis.md#metricsoutputfile)                 |

#### Description

The `output` action input is consumed verbatim by `FileUtils.writeJsonFile()` which calls `fs.mkdirSync(dir, { recursive: true })` before writing the metrics JSON. Because there is no validation that `output` stays within the workspace, a malicious workflow YAML can set `output: /etc/cron.d/malicious` or `output: ../rival-workflow/.gitcode/steps.yml` and have the metrics file written there, overwriting another workflow step's inputs or a system file. The metrics.json itself contains `fileDetails` (filePath, line counts, complexity, duplication rate) and metadata that may leak the scanned repo's structure to anyone reading the overwritten file.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `MetricsOutputFile` is on the GitCode Runner (CI_RUNNER deployment), Reachability = No Listener, Min Prerequisite = Local Process Access (the attacker must control the workflow YAML or have runner filesystem write access). External unauthenticated attackers cannot reach this component.

- `dist/utils/fileUtils.js:7-9` — `fs.mkdirSync(dir, { recursive: true })` creates arbitrary directory paths
- `dist/utils/fileUtils.js:11-13` — `fs.writeFileSync(filePath, jsonContent)` writes to the unvalidated path
- `dist/index.js:62451-62452` — `output` input read verbatim with no path validation

#### Remediation

- Resolve `output` against the workspace root with `path.resolve(this.workingDir, output)`.
- Verify the resolved path is within `this.workingDir` using `path.relative` + leading-`..` check; reject otherwise.
- Default `output` to `${this.workingDir}/metrics.json` if not specified.

#### Verification

- Unit test with `output: /etc/cron.d/evil` and confirm the write is rejected.
- Confirm `path.relative(this.workingDir, resolved)` returns a non-`..` path for valid `output` values.

### FIND-10: Temp File Race Condition and TMPDIR Hijack

| Attribute                  | Value                                                                                                                     |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                  |
| CVSS 4.0                   | 5.5 (CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:L/SC:L/SI:N/SA:N)                                                     |
| CWE                        | [CWE-377](https://cwe.mitre.org/data/definitions/377.html): Insecure Temporary File                                       |
| OWASP                      | A01:2025 – Broken Access Control                                                                                          |
| Exploitation Prerequisites | Local Process Access                                                                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk (Local Process Access to pre-create files in `os.tmpdir()` or set `TMPDIR` env var)             |
| Remediation Effort         | Low                                                                                                                       |
| Mitigation Type            | Standard Mitigation                                                                                                       |
| Component                  | TempFiles                                                                                                                 |
| Related Threats            | [T12.T](2-stride-analysis.md#tempfiles), [T12.A](2-stride-analysis.md#tempfiles), [T12.I](2-stride-analysis.md#tempfiles) |

#### Description

`TempFiles` writes lizard input, full-upload payload, and obsutil-extracted artifacts into `os.tmpdir()` shared by all workflow steps on the same runner. Filenames use `Date.now()` millisecond granularity, which is predictable; an attacker who can pre-create a file with the same name can win a race condition to have the plugin's `unlinkSync` delete the attacker's file (clearing an audit trail) or have the plugin's `writeFileSync` fail. The `TMPDIR` environment variable is honored by Node without validation, so a malicious workflow step can redirect temp files to an attacker-readable location. The cleanup path uses `fs.unlinkSync` in a `try/catch` that swallows errors, so a failed cleanup leaves the full metrics payload (containing source code snippets) on disk for the next workflow to read.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `TempFiles` is on the GitCode Runner (CI_RUNNER deployment), Reachability = No Listener, Min Prerequisite = Local Process Access. External attackers cannot reach temp files directly.

- `dist/uploaders/CoderepoUploader.js:380-384` — `fs.unlinkSync(tmpFile)` in `try/catch` that warns on failure but does not escalate
- `dist/detectors/LizardDetector.js:11, 71-73` — `tempJsonFile = './lizard_output.json'` and `tempInputPath = path.join(os.tmpdir(), 'lizard_input_${Date.now()}.txt')` (predictable ms granularity)
- `dist/uploaders/CoderepoUploader.js:396-415` — full payload written to `os.tmpdir()` before obsutil upload
- `process.env.TMPDIR` honored by Node without validation; can be set by any workflow step

#### Remediation

- Use `fs.mkdtempSync(path.join(os.tmpdir(), 'code-metrics-'))` to create an exclusive temp directory per workflow run.
- Set file permissions to 0600 on tmp files: `fs.writeFileSync(path, content, { mode: 0o600 })`.
- Do not honor `TMPDIR`; use the OS default tmpdir (Linux `/tmp`, Windows `%TEMP%`) directly.
- On `unlinkSync` failure, escalate to `core.setFailed` to prevent silent residue.

#### Verification

- Confirm `mkdtempSync` is used and each run uses a unique subdir.
- Run two concurrent scans and verify no tmp file collisions.
- Set `TMPDIR=/tmp/attacker` and confirm the plugin ignores it (uses `/tmp` directly).

### FIND-11: Input Environment Variable Override of Security Inputs

| Attribute                  | Value                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Important                                                                                                    |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:L/SC:L/SI:N/SA:N)                                        |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity   |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                        |
| Exploitation Prerequisites | Authenticated User                                                                                           |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can set workflow env vars that override secret-derived inputs) |
| Remediation Effort         | Low                                                                                                          |
| Mitigation Type            | Standard Mitigation                                                                                          |
| Component                  | CodeMetricsAction                                                                                            |
| Related Threats            | [T01.T](2-stride-analysis.md#codemetricsaction), [T01.A](2-stride-analysis.md#codemetricsaction)             |

#### Description

`CodeMetricsAction.run()` reads inputs via `getInput()`, which (per the GitHub Actions convention) reads `INPUT_<NAME>` environment variables and additionally tolerates both hyphen and underscore forms. If a CI platform's env block allows PR-comment or branch-name values to flow into env vars (or if a workflow explicitly sets `INPUT_APIG_APP_KEY` outside the secrets context), a malicious workflow can override the secret-derived inputs with attacker-controlled values, redirecting uploads to an attacker-controlled APIG endpoint. The `pipelineRunId` resolution `process.env['ATOMGIT_RUN_ID'] || process.env['PIPELINE_RUN_ID']` allows an attacker to set `PIPELINE_RUN_ID` to attribute the metrics to another pipeline, polluting trend data.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `CodeMetricsAction` is on the GitCode Runner (CI_RUNNER deployment), Reachability = No Listener, Min Prerequisite = Authenticated User. The attacker must be able to influence env vars or workflow YAML.

- `dist/index.js:62331-62334` — `getInput` tolerates both `INPUT_APIG-APP-KEY` and `INPUT_APIG_APP_KEY`
- `dist/index.js:62420` — `pipelineRunId = process.env['ATOMGIT_RUN_ID'] || process.env['PIPELINE_RUN_ID']` (fallback allows override)
- `dist/index.js:62363` — `useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL` (env var presence check)

#### Remediation

- For security-critical inputs (`apig-app-key`, `apig-app-secret`, `obs-ak`, `obs-sk`), explicitly verify the input source is `${{ secrets.* }}` by inspecting the workflow YAML convention; refuse to run if the input was set via a non-secret env var.
- For `pipelineRunId`, prefer `ATOMGIT_RUN_ID` only; if `PIPELINE_RUN_ID` must remain as fallback, add a workflow opt-out flag and validate the value is a known pipeline ID via a backend lookup.
- For `ACTIONS_ID_TOKEN_REQUEST_URL`, validate the URL host matches a GitCode platform whitelist before consuming.

#### Verification

- Confirm `getInput` for security-critical inputs raises an error if the input was set via env var rather than secrets context.
- Test `pipelineRunId` with `PIPELINE_RUN_ID=evil` and confirm rejection.

### FIND-12: Missing Audit Logging of Scan Failures

| Attribute                  | Value                                                                                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                      |
| CVSS 4.0                   | 4.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:N/SC:L/SI:N/SA:N)                                                                         |
| CWE                        | [CWE-778](https://cwe.mitre.org/data/definitions/778.html): Insufficient Logging                                                              |
| OWASP                      | A09:2025 – Security Logging and Monitoring Failures                                                                                           |
| Exploitation Prerequisites | Authenticated User                                                                                                                            |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can trigger scan failures that go un-audited)                                                   |
| Remediation Effort         | Low                                                                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                                                                           |
| Component                  | CodeMetricsAction, MetricsScanner, CoderepoUploader                                                                                           |
| Related Threats            | [T01.R](2-stride-analysis.md#codemetricsaction), [T08.R](2-stride-analysis.md#coderepouploader), [T02.R](2-stride-analysis.md#metricsscanner) |

#### Description

Failure paths across the scan pipeline emit `core.warning`/`console.error` to stdout but do not persist structured audit records to a tamper-evident sink. When `CodeMetricsAction` aborts scan, `MetricsScanner` catch block retries upload with an `errorMessage` field (already in body, `dist/scanner.js:217`), and `CoderepoUploader.report()` fails the APIG call, no record survives linking `pipelineRunId + commitId + failureReason + timestamp` to a backend that an SRE can later query. This breaks forensic reconstruction of an attacker who repeatedly triggers failures to mask data exfiltration, and prevents detection of a slow-loris style attack that exhausts the runner over many runs.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, all three components are on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker must be able to trigger scan failures via PR submission.

- `dist/index.js:62394, 62406, 62410` — `core.warning` outputs to console only
- `dist/scanner.js:197-225` — `catch` block retries upload with `errorMessage` in body but no separate audit endpoint
- `dist/uploaders/CoderepoUploader.js:657` — `console.error` of upload failure, no structured log

#### Remediation

- Add a separate audit endpoint (`/openlibing-coderepo/metrics/code/audit`) that accepts `{ pipelineRunId, commitId, stage, failureReason, timestamp }` and persists to an append-only store.
- Call the audit endpoint in `CodeMetricsAction` catch, `MetricsScanner` catch, and `CoderepoUploader.report` catch — independent of the metrics upload path.
- Use the OIDC/STS token for authentication; do not rely on the AK/SK path that may itself be compromised.

#### Verification

- Trigger each of the three failure paths and confirm an audit record appears in the audit store.
- Confirm the audit endpoint requires OIDC authentication.

### FIND-13: scc Binary Path Spoofing

| Attribute                  | Value                                                                                                                                   |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                               |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:L/SC:L/SI:N/SA:N)                                                                   |
| CWE                        | [CWE-426](https://cwe.mitre.org/data/definitions/426.html): Untrusted Search Path                                                       |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                                                         |
| Exploitation Prerequisites | Authenticated User                                                                                                                      |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can place a malicious `scc` binary in a candidate search path via the workspace checkout) |
| Remediation Effort         | Low                                                                                                                                     |
| Mitigation Type            | Standard Mitigation                                                                                                                     |
| Component                  | SlocDetector                                                                                                                            |
| Related Threats            | [T03.S](2-stride-analysis.md#slocdetector)                                                                                              |

#### Description

`SlocDetector.getSccPath()` probes a list of candidate paths including `path.join(__dirname, 'bin', 'scc')` and several ancestor directories of `__dirname`. If a malicious checkout injects a same-named `scc` binary into one of the higher-priority candidate paths (e.g., via a crafted npm dependency that lands in an ancestor directory), the attacker's binary executes in place of the bundled scc, returning crafted output or directly executing arbitrary commands via the subsequent `execSync` call.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `SlocDetector` is on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker must be able to influence the workspace contents or `__dirname` ancestors.

- `dist/detectors/SlocDetector.js:22-28` — `getSccPath()` iterates candidate paths including ancestor directories of `__dirname`
- `dist/detectors/SlocDetector.js:33-38` — `fs.chmodSync(candidate, 0o755)` and use the first existing candidate

#### Remediation

- Use a single canonical path: `path.join(bundleRoot, 'bin', 'scc')` where `bundleRoot` is the resolved plugin root directory.
- Do not include ancestor directories of `__dirname` in the candidate list.
- Compute the SHA256 of the bundled scc binary at startup; refuse to execute if the on-disk hash differs.

#### Verification

- Confirm `getSccPath` returns only the single canonical path.
- Inject a malicious `scc` in an ancestor directory and confirm it is not picked up.
- Verify hash check rejects a modified binary.

### FIND-14: Lizard Temp Output File Spoofing

| Attribute                  | Value                                                                                                 |
| -------------------------- | ----------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                              |
| CVSS 4.0                   | 4.5 (CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:L/SI:N/SA:N)                                 |
| CWE                        | [CWE-377](https://cwe.mitre.org/data/definitions/377.html): Insecure Temporary File                   |
| OWASP                      | A01:2025 – Broken Access Control                                                                      |
| Exploitation Prerequisites | Authenticated User                                                                                    |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can pre-create `./lizard_output.json` in the workspace) |
| Remediation Effort         | Low                                                                                                   |
| Mitigation Type            | Standard Mitigation                                                                                   |
| Component                  | LizardDetector                                                                                        |
| Related Threats            | [T04.S](2-stride-analysis.md#lizarddetector)                                                          |

#### Description

`LizardDetector` writes its temp JSON output to `./lizard_output.json` in the workspace root (not `os.tmpdir()`). A malicious repo can pre-create a same-named file with crafted content; while the code does `unlinkSync` before invoking lizard, if `runLizard` itself fails (e.g., python3 not installed), the fallback `parseTextOutput`/`parseJsonOutput` path reads the pre-existing file and trusts its contents, allowing the attacker to inject arbitrary `filePath` values that flow into the arbitrary-file-read vulnerability (FIND-05).

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `LizardDetector` is on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker must be able to commit a `lizard_output.json` to the repo root.

- `dist/detectors/LizardDetector.js:11` — `tempJsonFile = './lizard_output.json'` (workspace-relative, not tmpdir)
- `dist/detectors/LizardDetector.js:81-83` — `unlinkSync` of pre-existing file (best-effort)
- `dist/detectors/LizardDetector.js:124-135` — fallback parse path reads the file even if lizard failed

#### Remediation

- Write `tempJsonFile` to `os.tmpdir()` (or an `mkdtempSync` subdir, per FIND-10) with a unique name.
- Verify the file was created by the current lizard invocation (e.g., compare mtime to invocation start time, or write a sentinel first and check it).
- On lizard invocation failure, do NOT read the temp file at all — surface a clear error and skip LizardDetector.

#### Verification

- Pre-create `./lizard_output.json` with malicious content; cause lizard to fail; confirm the fallback does not read the file.
- Verify `tempJsonFile` is in `os.tmpdir()` with a unique name.

### FIND-15: DNS Spoofing and MitM of External Endpoints

| Attribute                  | Value                                                                                                                                                                                       |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                                                   |
| CVSS 4.0                   | 7.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:H/SI:N/SA:N)                                                                                                                       |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity                                                                                  |
| OWASP                      | A02:2025 – Cryptographic Failures                                                                                                                                                           |
| Exploitation Prerequisites | Internal Network                                                                                                                                                                            |
| Exploitability Tier        | Tier 2 — Conditional Risk (Internal Network access to manipulate DNS or route traffic to a forged endpoint)                                                                                 |
| Remediation Effort         | Medium                                                                                                                                                                                      |
| Mitigation Type            | Standard Mitigation                                                                                                                                                                         |
| Component                  | OBS, APIG, HuaweiCloudOIDC                                                                                                                                                                  |
| Related Threats            | [T13.S](2-stride-analysis.md#obs), [T13.T](2-stride-analysis.md#obs), [T14.S](2-stride-analysis.md#apig), [T14.T](2-stride-analysis.md#apig), [T15.T](2-stride-analysis.md#huaweicloudoidc) |

#### Description

The external endpoints `obs.cn-southwest-2.myhuaweicloud.com` (OBS), `174e1b821...apic.cn-southwest-2.huaweicloudapis.com` (APIG), and the OIDC provider (via `ACTIONS_ID_TOKEN_REQUEST_URL`) are all reached via plain HTTPS without certificate pinning. An attacker with internal network position — e.g., a compromised runner host, a malicious self-hosted runner, or BGP/DNS hijack at the egress — can resolve these hostnames to attacker-controlled IPs and present a valid (but attacker-issued) TLS certificate that the standard CA bundle trusts. The forged OBS endpoint would receive the full metrics payload (including source code snippets), the forged APIG endpoint would receive signed report requests (including obsUrl), and the forged OIDC endpoint would exchange forged STS credentials for runner-supplied OIDC tokens, allowing the attacker to redirect OBS uploads to attacker-controlled buckets.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `OBS`, `APIG`, and `HuaweiCloudOIDC` are all External (Reachability = External) endpoints reached via HTTPS from the GitCode Runner. The Min Prerequisite for each is Authenticated User (someone must trigger a workflow), but the spoofing attack itself requires Internal Network position to manipulate DNS/routes.

- `dist/uploaders/CoderepoUploader.js:438-450` — obsutil download URL hardcoded; no cert pinning
- `dist/uploaders/CoderepoUploader.js:613-660` — axios call to APIG endpoint; uses default CA validation
- `dist/index.js:62363` — `ACTIONS_ID_TOKEN_REQUEST_URL` consumed by SDK without issuer/host validation

#### Remediation

- Configure certificate pinning for the OBS, APIG, and OIDC endpoints (pin the huaweicloudapis.com leaf cert or intermediate CA public key).
- For `ACTIONS_ID_TOKEN_REQUEST_URL`, validate that the host matches a GitCode platform whitelist (`*.gitcode.com`, `*.huaweicloud.com`) before invoking the SDK.
- Validate the STS credentials returned by OIDC have the expected account ID and short expiry (≤ 1h) before passing them to obsutil.

#### Verification

- Confirm certificate pinning is configured for the three endpoints.
- Test with a forged cert (e.g., mitmproxy with a trusted CA) and confirm the call is rejected.
- Verify `ACTIONS_ID_TOKEN_REQUEST_URL` host whitelist enforcement.

### FIND-16: AK/SK Static Credential Risk in Legacy Authentication Mode

| Attribute                  | Value                                                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                     |
| CVSS 4.0                   | 7.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:H/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N)                                                         |
| CWE                        | [CWE-798](https://cwe.mitre.org/data/definitions/798.html): Use of Hard-coded Credentials                                     |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                                         |
| Exploitation Prerequisites | Host/OS Access                                                                                                                |
| Exploitability Tier        | Tier 3 — Defense-in-Depth (Host/OS Access needed to harvest the SK from runner env or tmp files; multiple prerequisite paths) |
| Remediation Effort         | High                                                                                                                          |
| Mitigation Type            | Redesign                                                                                                                      |
| Component                  | CoderepoUploader, OBS, APIG                                                                                                   |
| Related Threats            | [T08.E](2-stride-analysis.md#coderepouploader), [T13.E](2-stride-analysis.md#obs), [T14.E](2-stride-analysis.md#apig)         |

#### Description

The legacy authentication path uses static AK/SK credentials (`obs-ak`, `obs-sk`, `apig-app-key`, `apig-app-secret`) supplied as workflow secrets. These credentials are long-lived (no expiry), have full write access to the `openlibing-gitcode-action` OBS bucket and full call access to the APIG `/metrics/code/report` endpoint. If any of these credentials leak — via runner env captured to a log, tmp file residue, GitHub Actions cache poisoning, or a malicious workflow step that reads `process.env` — an attacker can forge SDK-HMAC-SHA256 signatures and submit fabricated metrics (overwriting real data or polluting trend history) or read/overwrite any object in the OBS bucket. The OIDC mode (newly added) mitigates this by using short-lived STS credentials, but the AK/SK path remains as a fallback.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `CoderepoUploader`, `OBS`, and `APIG` are reached from the GitCode Runner. The AK/SK is supplied via workflow secrets, but a Host/OS compromise (runner env access, tmp file access, or AK/SK in git history) is required to harvest the SK. Multiple prerequisites are needed for full exploit.

- `dist/uploaders/CoderepoUploader.js:627` — `ApigSigner(this.apigAppKey, this.apigAppSecret)` constructs signer with static credentials
- `dist/uploaders/CoderepoUploader.js:418` — obsutil invoked with `-i=${ak} -k=${sk} -t=${token}` (or static AK/SK without `-t`)
- `dist/uploaders/CoderepoUploader.js:624-626` — AK/SK mode active when `!useOidc`

#### Remediation

- Deprecate the AK/SK path: emit a deprecation warning when `useOidc === false`; track usage and remove the path once all callers have migrated.
- For过渡期: enforce IP allow-list on the AK/SK at APIG and OBS bucket policy side, so a leaked SK is only useful from the GitCode runner IP range.
- Add anomaly detection on the APIG `/metrics/code/report` endpoint: alert on unusual upload frequency, unusual source IPs, or unusual ownerRepo values.

#### Verification

- Confirm deprecation warning fires when `useOidc === false`.
- Verify APIG IP allow-list is configured for the AK/SK credential.
- Confirm anomaly detection alerts on synthetic unusual upload patterns.

### FIND-17: APIG Signer Input Validation Missing

| Attribute                  | Value                                                                                                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                                              |
| CVSS 4.0                   | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:L/SI:N/SA:N)                                                                                                  |
| CWE                        | [CWE-20](https://cwe.mitre.org/data/definitions/20.html): Improper Input Validation                                                                                    |
| OWASP                      | A03:2025 – Injection                                                                                                                                                   |
| Exploitation Prerequisites | Authenticated User                                                                                                                                                     |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can influence coderepoUrl and report payload size)                                                                       |
| Remediation Effort         | Low                                                                                                                                                                    |
| Mitigation Type            | Standard Mitigation                                                                                                                                                    |
| Component                  | ApigSigner                                                                                                                                                             |
| Related Threats            | [T09.T](2-stride-analysis.md#apigsigner), [T09.D](2-stride-analysis.md#apigsigner), [T09.E](2-stride-analysis.md#apigsigner), [T09.A](2-stride-analysis.md#apigsigner) |

#### Description

`ApigSigner.sign()` parses arbitrary URL strings with `new URL(url)`, decodes query strings via `decodeURIComponent` (which can throw `URIError` on malformed input), and constructs canonical strings without bounds. The constructor does not validate that `ak` and `sk` are non-empty before signing, so an empty credential produces a `SDK-HMAC-SHA256 Access=, SignedHeaders=..., Signature=...` header that may be interpreted as an anonymous request by APIG (depending on gateway configuration). The `_canonicalUri` always appends a trailing `/`, which can route to unintended handlers on path-sensitive APIG configurations. An attacker who can influence `coderepoUrl` (e.g., via the action input) can construct URLs that crash the signer (DoS) or produce signatures for unintended routes.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `ApigSigner` is on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker must influence `coderepoUrl` or the report payload.

- `dist/uploaders/CoderepoUploader.js:21-24` — constructor does not validate ak/sk non-empty
- `dist/uploaders/CoderepoUploader.js:32` — `new URL(url)` parses arbitrary URL
- `dist/uploaders/CoderepoUploader.js:38-54` — `decodeURIComponent` can throw `URIError` on malformed input
- `dist/uploaders/CoderepoUploader.js:153-156` — `_canonicalUri` always appends trailing `/`
- `dist/uploaders/CoderepoUploader.js:147-233` — no URL length or query parameter count limits

#### Remediation

- Validate `ak` and `sk` are non-empty in the constructor; throw `Error('ApigSigner requires ak/sk')` if either is missing.
- Add URL length cap (e.g., < 8KB) and query parameter count cap (e.g., < 100) at the start of `sign()`.
- Wrap `decodeURIComponent` in try/catch and treat malformed input as a signing failure, not a crash.
- Restrict `_canonicalUri` to a known route whitelist (`/metrics/code/report`); reject unknown paths.

#### Verification

- Confirm constructor rejects empty ak/sk with a clear error.
- Unit test with an over-long URL and a malformed query string; confirm signing fails gracefully.

### FIND-18: pip install System Pollution via --break-system-packages

| Attribute                  | Value                                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                                           |
| CVSS 4.0                   | 5.5 (CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:L/SI:N/SA:N)                                              |
| CWE                        | [CWE-732](https://cwe.mitre.org/data/definitions/732.html): Incorrect Permission Assignment for Critical Resource  |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                               |
| Exploitation Prerequisites | Authenticated User                                                                                                 |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User triggers a workflow that runs `pip install --break-system-packages`) |
| Remediation Effort         | Low                                                                                                                |
| Mitigation Type            | Standard Mitigation                                                                                                |
| Component                  | LizardDetector, PyPIMirror                                                                                         |
| Related Threats            | [T04.A](2-stride-analysis.md#lizarddetector), [T17.A](2-stride-analysis.md#pypimirror)                             |

#### Description

`pip install --break-system-packages lizard` installs lizard at the system Python level on the runner. If the runner is shared by multiple workflow steps (typical on GitCode-hosted runners), subsequent steps that use `python3` will see the installed `lizard` package in their import path. A malicious lizard package (per FIND-02 supply chain risk) would thus persist across workflow steps, and a benign but version-pinned lizard would shadow any caller's expected version. The `--break-system-packages` flag was added in PEP 668 to bypass the externally-managed-environment protection that distributions like Debian/Ubuntu add precisely to prevent this class of pollution.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `LizardDetector` and `PyPIMirror` are on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker must trigger a workflow that installs lizard.

- `dist/index.js:62468` — `--break-system-packages` flag explicitly bypasses PEP 668 protection
- `dist/index.js:62470` — `--trusted-host mirrors.aliyun.com` (per FIND-02)
- Runner shares system Python across all workflow steps in the same job

#### Remediation

- Replace `pip install --break-system-packages` with a virtualenv: `python3 -m venv /tmp/lizard-venv && /tmp/lizard-venv/bin/pip install lizard`.
- Invoke lizard via `/tmp/lizard-venv/bin/python3 -m lizard` so the system Python is untouched.
- Remove the venv in a `finally` block to prevent residue.

#### Verification

- Confirm `python3 -m venv` is invoked before `pip install`.
- Verify system Python's `pip list` does not include lizard after the workflow.
- Confirm `lizard` is invoked via the venv's `python3`.

### FIND-19: Source Code Disclosure via Metrics Pipeline

| Attribute                  | Value                                                                                                                                       |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                    |
| CVSS 4.0                   | 4.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                                                       |
| CWE                        | [CWE-200](https://cwe.mitre.org/data/definitions/200.html): Exposure of Sensitive Information to an Unauthorized Actor                      |
| OWASP                      | A02:2025 – Cryptographic Failures                                                                                                           |
| Exploitation Prerequisites | Authenticated User                                                                                                                          |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can submit a repo with secrets/PII in source; metrics pipeline uploads to OBS)                |
| Remediation Effort         | High                                                                                                                                        |
| Mitigation Type            | Custom Mitigation                                                                                                                           |
| Component                  | DuplicationDetector, WorkspaceRepo, CoderepoUploader                                                                                        |
| Related Threats            | [T05.I](2-stride-analysis.md#duplicationdetector), [T10.I](2-stride-analysis.md#workspacerepo), [T10.A](2-stride-analysis.md#workspacerepo) |

#### Description

`DuplicationDetector.buildContextSegments()` reads full source file content via `fs.readFileSync(file, 'utf8')` and constructs ±5-line context segments around each duplicated block. These segments (snapshotData) are Base64-encoded and uploaded to OBS as part of the metrics payload. If the scanned repo contains secrets, PII, or proprietary algorithms in source files that happen to contain duplication (a common case for boilerplate-heavy codebases), the secrets transit the entire metrics pipeline and land in the OBS bucket — readable by anyone with bucket read access (per FIND-16, the AK/SK has full bucket access). The same risk applies to `fileDetails` (file paths + line counts) and `duplicationOccurrences` (start/end lines), which together let an attacker reconstruct a partial map of the scanned repo's structure even without the snapshotData.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `DuplicationDetector`, `WorkspaceRepo`, and `CoderepoUploader` are all on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker submits a repo with sensitive content.

- `dist/detectors/DuplicationDetector.js:82` — `fs.readFileSync(file, 'utf8')` reads full source
- `dist/detectors/DuplicationDetector.js` — `buildContextSegments` constructs ±5 line context per duplicate
- `dist/uploaders/CoderepoUploader.js:475-480` — `buildObjectKey` writes to OBS

#### Remediation

- Add an upstream gitleaks / detect-private-key pre-commit hook in the workflow; abort the metrics scan if secrets are detected.
- Optionally scrub snapshotData before upload with a secret-detection regex that masks patterns resembling AWS keys, private keys, JWTs, and connection strings.
- Consider not uploading snapshotData at all — the backend can fetch duplication metadata without the source context, recomputing context on-demand from the cloned repo (which the backend already has access to).
- Document the data flow to the OBS bucket in the plugin README so users can make an informed decision.

#### Verification

- Confirm pre-commit hook rejects a repo containing `AWS_SECRET_ACCESS_KEY=...`.
- Verify a regex-scrubbed snapshotData does not contain `AKIA...` patterns.
- Confirm the plugin README documents the OBS upload path.

### FIND-20: Config File Override of Security-Critical Fields

| Attribute                  | Value                                                                                                                              |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                           |
| CVSS 4.0                   | 5.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:L/SC:L/SI:N/SA:N)                                                              |
| CWE                        | [CWE-639](https://cwe.mitre.org/data/definitions/639.html): Authorization Bypass Through User-Controlled Key                       |
| OWASP                      | A01:2025 – Broken Access Control                                                                                                   |
| Exploitation Prerequisites | Authenticated User                                                                                                                 |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can supply a `config-file` that overrides security-critical fields)                  |
| Remediation Effort         | Low                                                                                                                                |
| Mitigation Type            | Standard Mitigation                                                                                                                |
| Component                  | ConfigLoader                                                                                                                       |
| Related Threats            | [T06.T](2-stride-analysis.md#configloader), [T06.D](2-stride-analysis.md#configloader), [T06.E](2-stride-analysis.md#configloader) |

#### Description

`ConfigLoader.mergeConfig()` recursively merges the user-supplied `config-file` over the default config, allowing the user to override any field including security-critical ones like `detectors.duplication.enabled`, `uploader.coderepoUrl`, or `uploader.obsEndpoint`. While `dist/index.js:62450-62461` does hardcode some fields (coderepoUrl), the `enabled` flag for detectors is not protected, allowing a user to disable the duplication detector (masking exfiltration via duplication patterns) or reconfigure the uploader endpoint. The `js-yaml` parser uses SAFE_SCHEMA by default but does not bound the config file size, allowing a 1GB YAML with deeply nested anchors to trigger memory exhaustion.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `ConfigLoader` is on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker supplies a `config-file` via the action input.

- `dist/config/loader.js:46` — `yaml.load(fileContent)` with no size check
- `dist/config/loader.js:62-85` — `mergeConfig` recursively merges user config over defaults with no field whitelist
- `dist/index.js:62450-62461` — coderepoUrl is hardcoded after merge (good), but `enabled` flags are not protected

#### Remediation

- Define a whitelist of user-overridable fields; reject any other field in the user config with a clear error.
- Pre-check `fs.statSync(configFile).size` against a 1MB limit before `yaml.load`.
- Explicitly set `schema: yaml.DEFAULT_SAFE_SCHEMA` in the `yaml.load` call.
- For security-critical fields (`enabled`, `coderepoUrl`, `obsEndpoint`, `apig*`), always reset to defaults after merge and emit a warning if the user tried to override them.

#### Verification

- Confirm `mergeConfig` rejects unknown fields with a clear error.
- Test a 2MB config file and confirm rejection.
- Verify `detectors.duplication.enabled=false` in user config is reset to `true` after merge.

### FIND-21: JSON.stringify DoS via Oversized compactResult

| Attribute                  | Value                                                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                  |
| CVSS 4.0                   | 4.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:L/SI:N/SA:N)                                     |
| CWE                        | [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption             |
| OWASP                      | A05:2025 – Security Misconfiguration                                                                      |
| Exploitation Prerequisites | Authenticated User                                                                                        |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User can submit a repo that produces an oversized compactResult) |
| Remediation Effort         | Medium                                                                                                    |
| Mitigation Type            | Standard Mitigation                                                                                       |
| Component                  | MetricsScanner                                                                                            |
| Related Threats            | [T02.D](2-stride-analysis.md#metricsscanner)                                                              |

#### Description

`MetricsScanner` calls `JSON.stringify(compactResult)` to compute the local output size estimate and to write the metrics.json file. The `compactResult` includes the full `fileDetails` array (uncapped) plus `duplicationOccurrences` (capped at 15KB per content via `clipOversizeContent`). For a large repo (e.g., 100k files with high complexity), the `fileDetails` array alone can exceed V8's `Invalid string length` limit (~512MB on 64-bit, but practically lower due to memory pressure), causing `JSON.stringify` to throw. The `catch` block in `scanner.js:197-225` catches the error but the workflow still fails, blocking the pipeline.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `MetricsScanner` is on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker submits a large repo.

- `dist/scanner.js:137` — `logger.info('Result scale: fileDetails=..., snapshotDataTotal=... bytes')` indicates uncapped arrays
- `dist/scanner.js:144-167` — `clipOversizeContent` caps `duplicationOccurrences` content at 15KB but does not cap `fileDetails`
- `dist/scanner.js:170` — `JSON.stringify(compactResult).length` can throw `Invalid string length`

#### Remediation

- Cap `fileDetails` count (e.g., top N=10000 files by complexity, with the rest aggregated into a summary).
- Replace `JSON.stringify(fullResult)` with a streaming serializer (`fs.createWriteStream` + manual JSON token writer) to avoid the V8 string-length limit.
- Wrap `JSON.stringify` in try/catch and on `RangeError`, fall back to writing a truncated result with a warning.

#### Verification

- Test with a 100k-file synthetic repo and confirm no `Invalid string length` error.
- Verify `fileDetails` is capped to 10000 entries with a summary of the rest.
- Confirm streaming writer produces a valid JSON file.

### FIND-22: ReDoS via User-Supplied Glob Patterns

| Attribute                  | Value                                                                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| SDL Bugbar Severity        | Moderate                                                                                                                             |
| CVSS 4.0                   | 4.0 (CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:L/SI:N/SA:N)                                                                |
| CWE                        | [CWE-1333](https://cwe.mitre.org/data/definitions/1333.html): Inefficient Regular Expression Complexity                              |
| OWASP                      | A03:2025 – Injection                                                                                                                 |
| Exploitation Prerequisites | Authenticated User                                                                                                                   |
| Exploitability Tier        | Tier 2 — Conditional Risk (Authenticated User supplies exclude-dirs glob patterns that compile to catastrophic backtracking regexes) |
| Remediation Effort         | Low                                                                                                                                  |
| Mitigation Type            | Standard Mitigation                                                                                                                  |
| Component                  | FileCollector                                                                                                                        |
| Related Threats            | [T07.T](2-stride-analysis.md#filecollector)                                                                                          |

#### Description

`FileCollector.globToRegExp(glob)` converts user-supplied glob patterns (e.g., from the `exclude-dirs` action input) to JavaScript RegExp objects without checking for catastrophic backtracking patterns. A crafted glob like `(a+)+` or `(a|a)*b` compiles to a regex that, when matched against a long path string, exhibits exponential backtracking — blocking the event loop for minutes on a single match. An attacker who can set `exclude-dirs` to such a pattern can stall the entire file collection phase, blocking the workflow.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `FileCollector` is on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User. The attacker supplies `exclude-dirs` via the action input or config file.

- `dist/utils/fileCollector.js:127-180` — `globToRegExp(glob)` converts glob to RegExp without ReDoS check
- `dist/utils/fileCollector.js` — regex used in `_walkDir` against every file path

#### Remediation

- Add a `safe-regex` (or `re2`) pre-check on the compiled RegExp before using it; reject patterns flagged as potentially catastrophic.
- Alternatively, use `re2` (Google's RE2 engine) which has linear-time guarantees and is available as an npm package.
- Add a per-`_walkDir` invocation timeout (e.g., 30s) that aborts if exceeded.

#### Verification

- Confirm `safe-regex` is installed and used to pre-check globs.
- Test with `(a+)+b` glob and confirm rejection.
- Verify `re2` is used if chosen as the alternative.

---

## Tier 3 — Defense-in-Depth (Prior Compromise / Host Access)

### FIND-23: OIDC URL Validation Missing for ACTIONS_ID_TOKEN_REQUEST_URL

| Attribute                  | Value                                                                                                                                           |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Important                                                                                                                                       |
| CVSS 4.0                   | 7.0 (CVSS:4.0/AV:N/AC:H/AT:N/PR:H/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N)                                                                           |
| CWE                        | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity                                      |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                                                           |
| Exploitation Prerequisites | Host/OS Access                                                                                                                                  |
| Exploitability Tier        | Tier 3 — Defense-in-Depth (Host/OS Access to runner env or malicious self-hosted runner required to inject forged ACTIONS_ID_TOKEN_REQUEST_URL) |
| Remediation Effort         | Low                                                                                                                                             |
| Mitigation Type            | Standard Mitigation                                                                                                                             |
| Component                  | CodeMetricsAction, HuaweiCloudOIDC                                                                                                              |
| Related Threats            | [T01.E](2-stride-analysis.md#codemetricsaction), [T15.S](2-stride-analysis.md#huaweicloudoidc), [T15.E](2-stride-analysis.md#huaweicloudoidc)   |

#### Description

`CodeMetricsAction` determines whether to use OIDC mode via `useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL` — checking only for the env var's existence, not its content. An attacker with Host/OS access to the runner (e.g., via a malicious self-hosted runner configuration, runner image compromise, or compromise of the CI platform's env injection) can set `ACTIONS_ID_TOKEN_REQUEST_URL` to an attacker-controlled URL. The plugin then calls this forged "OIDC provider" via the huaweicloud-oidc-client SDK, which receives a forged OIDC token, exchanges it for forged STS credentials (with attacker-controlled accessKeyId/secretAccessKey/securityToken), and passes those credentials to obsutil — directing the OBS upload to an attacker-controlled bucket while the workflow believes it's uploading to the legitimate `openlibing-gitcode-action` bucket.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `CodeMetricsAction` and `HuaweiCloudOIDC` are on the GitCode Runner (CI_RUNNER deployment). The `ACTIONS_ID_TOKEN_REQUEST_URL` is platform-injected; spoofing it requires Host/OS Access (Tier 3) — an attacker must compromise the runner image, the CI platform's env injection, or substitute a self-hosted runner.

- `dist/index.js:62363` — `useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL` (presence check only)
- `dist/uploaders/CoderepoUploader.js:613` — `getCredentials()` invoked with the unvalidated URL via the SDK
- `package.json:15` — `@openlibing/huaweicloud-oidc-client` 0.0.5 SDK

#### Remediation

- Validate that `ACTIONS_ID_TOKEN_REQUEST_URL` starts with `https://` and its host matches a GitCode platform whitelist (`*.gitcode.com`, `*.atomgit.com`, or whatever the platform's official OIDC host is).
- In the SDK call, enable issuer validation against the expected OIDC discovery document; reject if the issuer doesn't match.
- Validate the returned STS credentials' account ID matches the expected huaweicloud account before passing to obsutil.

#### Verification

- Confirm URL host whitelist is enforced before SDK invocation.
- Test with a forged `ACTIONS_ID_TOKEN_REQUEST_URL=http://attacker.example.com` and confirm rejection.
- Verify the SDK call passes `issuer` validation option.

### FIND-24: scc Binary SBOM and Integrity Verification Missing

| Attribute                  | Value                                                                                                                                   |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                |
| CVSS 4.0                   | 4.5 (CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:L/VI:L/VA:L/SC:N/SI:N/SA:N)                                                                   |
| CWE                        | [CWE-494](https://cwe.mitre.org/data/definitions/494.html): Download of Code Without Integrity                                          |
| OWASP                      | A08:2025 – Software and Data Integrity Failures                                                                                         |
| Exploitation Prerequisites | CoderepoUploader Compromise + Host/OS Access                                                                                            |
| Exploitability Tier        | Tier 3 — Defense-in-Depth (requires supply chain compromise of the dist packaging pipeline AND host/OS access to substitute the binary) |
| Remediation Effort         | Medium                                                                                                                                  |
| Mitigation Type            | Standard Mitigation                                                                                                                     |
| Component                  | SlocDetector                                                                                                                            |
| Related Threats            | [T03.E](2-stride-analysis.md#slocdetector)                                                                                              |

#### Description

The scc binary is bundled into `dist/bin/scc` via the ncc packaging process. There is no SBOM, hash signature, or runtime integrity check for this binary. If the ncc build pipeline is compromised (e.g., a malicious npm dependency slips a modified scc into the bundle, or the CI builder is compromised), the bundled scc executes with runner process privileges on every workflow that uses the plugin. Because scc is invoked via `execSync`/`execFileSync` and reads every file in the workspace, a malicious scc can exfiltrate source code, plant backdoors in the metrics output, or establish persistence on the runner.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `SlocDetector` is on the GitCode Runner (CI_RUNNER deployment). The bundled scc binary is shipped with the plugin; compromising it requires supply-chain compromise of the ncc build (CoderepoUploader Compromise in the threat model) AND host/OS access to substitute the binary at rest.

- `dist/detectors/SlocDetector.js:22-28` — `getSccPath()` returns the bundled binary path
- `dist/detectors/SlocDetector.js:33-38` — `fs.chmodSync(candidate, 0o755)` before execution
- No hash verification step before `execSync`/`execFileSync` invocation

#### Remediation

- At plugin build time, compute and embed the SHA256 of the bundled scc binary into a `dist/bin/scc.sha256` file.
- At runtime, before first invocation, compute the on-disk scc SHA256 and compare to the embedded value; abort on mismatch.
- Generate and publish a CycloneDX SBOM for the plugin release, including the bundled scc binary's hash, version, and provenance.

#### Verification

- Confirm `scc.sha256` file exists in `dist/bin/`.
- Test with a tampered scc binary and confirm the runtime check aborts invocation.
- Verify the SBOM is published with the release.

### FIND-25: scc toRelativePath Prefix剥除 Abuse via Workspace-Escaping sources

| Attribute                  | Value                                                                                                                                     |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                                                  |
| CVSS 4.0                   | 4.5 (CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:L/VI:N/VA:N/SC:L/SI:N/SA:N)                                                                     |
| CWE                        | [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Path Traversal                                                                  |
| OWASP                      | A01:2025 – Broken Access Control                                                                                                          |
| Exploitation Prerequisites | Host/OS Access                                                                                                                            |
| Exploitability Tier        | Tier 3 — Defense-in-Depth (Host/OS Access required to inject `sources=['/tmp']` or similar absolute path via workflow YAML or runner env) |
| Remediation Effort         | Low                                                                                                                                       |
| Mitigation Type            | Standard Mitigation                                                                                                                       |
| Component                  | SlocDetector                                                                                                                              |
| Related Threats            | [T03.A](2-stride-analysis.md#slocdetector)                                                                                                |

#### Description

`SlocDetector.toRelativePath()` strips a `sources` prefix from absolute file paths to produce workspace-relative paths in the metrics output. If an attacker can set `sources=['/tmp']` (via the action input or config file), then any file path under `/tmp` (e.g., `/tmp/secret.txt`) gets stripped to `secret.txt` and reported as if it were a workspace file. This bypasses the "workspace-relative paths only" semantic and can leak the existence (and via `fileDetails`, the size/complexity) of files outside the workspace into the metrics output, which then transits to OBS.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `SlocDetector` is on the GitCode Runner (CI_RUNNER deployment), Min Prerequisite = Authenticated User for the action input path. The Tier 3 framing (Host/OS Access) reflects the worst case where the attacker has full control of the runner env to inject arbitrary `sources` values that escape the workspace.

- `dist/detectors/SlocDetector.js:259-271` — `toRelativePath()` strips `sources` prefix without verifying `sources` is within `workingDir`
- The `sources` value is read from action input or config file

#### Remediation

- In `SlocDetector` constructor, validate each entry in `sources` resolves to a path within `this.workingDir` via `path.resolve(this.workingDir, src)` + prefix check; reject absolute paths outside workspace.
- On rejection, surface a clear error and abort the scan.

#### Verification

- Confirm `sources=['/tmp']` is rejected.
- Verify `sources=['./src']` (a valid relative path) is accepted and resolves to workspace.

### FIND-26: OIDC/HMAC SDK Replay Attack and Version Pin Risk

| Attribute                  | Value                                                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| SDL Bugbar Severity        | Moderate                                                                                                         |
| CVSS 4.0                   | 4.5 (CVSS:4.0/AV:N/AC:H/AT:N/PR:H/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N)                                            |
| CWE                        | [CWE-294](https://cwe.mitre.org/data/definitions/294.html): Authentication Bypass by Capture-replay              |
| OWASP                      | A07:2025 – Identification and Authentication Failures                                                            |
| Exploitation Prerequisites | HuaweiCloudOIDC Compromise                                                                                       |
| Exploitability Tier        | Tier 3 — Defense-in-Depth (requires HuaweiCloudOIDC provider compromise or SDK vulnerability with known exploit) |
| Remediation Effort         | Medium                                                                                                           |
| Mitigation Type            | Standard Mitigation                                                                                              |
| Component                  | APIG, HuaweiCloudOIDC                                                                                            |
| Related Threats            | [T14.A](2-stride-analysis.md#apig), [T15.A](2-stride-analysis.md#huaweicloudoidc)                                |

#### Description

The V11-HMAC-SHA256 signing flow (OIDC mode) is handled entirely by `@openlibing/huaweicloud-oidc-client` SDK version 0.0.5, which is pinned in `package.json:15` without version upgrade tracking or vulnerability scanning. If 0.0.5 has a known vulnerability (e.g., missing nonce validation, insufficient timestamp window enforcement, or replay-attack-vulnerable signature scheme), the entire OIDC authentication can be bypassed — an attacker who captures a signed request can replay it to APIG with modified payload, or forge signatures for arbitrary requests. The SDK also lacks a SBOM and has no dependabot/renovate integration, so vulnerabilities in transitive dependencies are not surfaced.

#### Evidence

**Prerequisite basis:** Per the Component Exposure Table, `APIG` and `HuaweiCloudOIDC` are External endpoints. The Tier 3 framing reflects the worst case where the huaweicloud-oidc-client SDK itself has a vulnerability (HuaweiCloudOIDC Compromise) that allows replay or forgery.

- `package.json:15` — `"@openlibing/huaweicloud-oidc-client": "0.0.5"` (pinned, no caret/tilde)
- `dist/uploaders/CoderepoUploader.js:3, 613` — SDK imported and `getCredentials()`/`callApig()` invoked
- No `dependabot.yml` or `renovate.json` in repo for dependency vulnerability monitoring

#### Remediation

- Upgrade `@openlibing/huaweicloud-oidc-client` to the latest version on each release; track security advisories for the SDK and its transitive dependencies.
- Add a `dependabot.yml` or `renovate.json` to automatically surface dependency vulnerabilities.
- At the APIG side, enforce a 5-minute timestamp window and reject any request with a duplicate `X-Sdk-Date` + nonce combination (server-side replay protection).
- Generate and publish a CycloneDX SBOM for the plugin, including the OIDC SDK and its transitive dependencies.

#### Verification

- Confirm `package.json` has the latest SDK version or a caret range that allows patch updates.
- Verify `dependabot.yml` is configured for npm.
- Confirm APIG has a 5-minute timestamp window enforcement.

---

## Threat Coverage Verification

| Threat ID | Finding ID | Status               |
| --------- | ---------- | -------------------- |
| T01.T     | FIND-11    | ✅ Covered (FIND-11) |
| T01.R     | FIND-12    | ✅ Covered (FIND-12) |
| T01.I     | FIND-06    | ✅ Covered (FIND-06) |
| T01.D     | FIND-08    | ✅ Covered (FIND-08) |
| T01.A     | FIND-11    | ✅ Covered (FIND-11) |
| T01.E     | FIND-23    | ✅ Covered (FIND-23) |
| T02.R     | FIND-12    | ✅ Covered (FIND-12) |
| T02.I     | FIND-06    | ✅ Covered (FIND-06) |
| T02.D     | FIND-21    | ✅ Covered (FIND-21) |
| T03.S     | FIND-13    | ✅ Covered (FIND-13) |
| T03.T     | FIND-03    | ✅ Covered (FIND-03) |
| T03.I     | FIND-06    | ✅ Covered (FIND-06) |
| T03.D     | FIND-07    | ✅ Covered (FIND-07) |
| T03.E     | FIND-24    | ✅ Covered (FIND-24) |
| T03.A     | FIND-25    | ✅ Covered (FIND-25) |
| T04.S     | FIND-14    | ✅ Covered (FIND-14) |
| T04.T     | FIND-03    | ✅ Covered (FIND-03) |
| T04.I     | FIND-05    | ✅ Covered (FIND-05) |
| T04.D     | FIND-07    | ✅ Covered (FIND-07) |
| T04.E     | FIND-05    | ✅ Covered (FIND-05) |
| T04.A     | FIND-18    | ✅ Covered (FIND-18) |
| T05.I     | FIND-19    | ✅ Covered (FIND-19) |
| T05.D     | FIND-07    | ✅ Covered (FIND-07) |
| T05.A     | FIND-04    | ✅ Covered (FIND-04) |
| T06.T     | FIND-20    | ✅ Covered (FIND-20) |
| T06.D     | FIND-07    | ✅ Covered (FIND-07) |
| T06.E     | FIND-20    | ✅ Covered (FIND-20) |
| T07.T     | FIND-22    | ✅ Covered (FIND-22) |
| T07.I     | FIND-06    | ✅ Covered (FIND-06) |
| T07.D     | FIND-07    | ✅ Covered (FIND-07) |
| T08.T     | FIND-03    | ✅ Covered (FIND-03) |
| T08.R     | FIND-12    | ✅ Covered (FIND-12) |
| T08.I     | FIND-06    | ✅ Covered (FIND-06) |
| T08.D     | FIND-08    | ✅ Covered (FIND-08) |
| T08.A     | FIND-04    | ✅ Covered (FIND-04) |
| T08.E     | FIND-16    | ✅ Covered (FIND-16) |
| T09.T     | FIND-17    | ✅ Covered (FIND-17) |
| T09.I     | FIND-06    | ✅ Covered (FIND-06) |
| T09.D     | FIND-17    | ✅ Covered (FIND-17) |
| T09.E     | FIND-17    | ✅ Covered (FIND-17) |
| T09.A     | FIND-17    | ✅ Covered (FIND-17) |
| T10.I     | FIND-19    | ✅ Covered (FIND-19) |
| T10.D     | FIND-07    | ✅ Covered (FIND-07) |
| T10.A     | FIND-19    | ✅ Covered (FIND-19) |
| T11.T     | FIND-09    | ✅ Covered (FIND-09) |
| T11.I     | FIND-09    | ✅ Covered (FIND-09) |
| T11.D     | FIND-07    | ✅ Covered (FIND-07) |
| T11.A     | FIND-09    | ✅ Covered (FIND-09) |
| T12.T     | FIND-10    | ✅ Covered (FIND-10) |
| T12.I     | FIND-10    | ✅ Covered (FIND-10) |
| T12.D     | FIND-07    | ✅ Covered (FIND-07) |
| T12.A     | FIND-10    | ✅ Covered (FIND-10) |
| T13.S     | FIND-15    | ✅ Covered (FIND-15) |
| T13.T     | FIND-15    | ✅ Covered (FIND-15) |
| T13.I     | FIND-06    | ✅ Covered (FIND-06) |
| T13.A     | FIND-04    | ✅ Covered (FIND-04) |
| T13.E     | FIND-16    | ✅ Covered (FIND-16) |
| T14.S     | FIND-15    | ✅ Covered (FIND-15) |
| T14.T     | FIND-15    | ✅ Covered (FIND-15) |
| T14.I     | FIND-06    | ✅ Covered (FIND-06) |
| T14.E     | FIND-16    | ✅ Covered (FIND-16) |
| T14.A     | FIND-26    | ✅ Covered (FIND-26) |
| T15.S     | FIND-23    | ✅ Covered (FIND-23) |
| T15.T     | FIND-15    | ✅ Covered (FIND-15) |
| T15.I     | FIND-06    | ✅ Covered (FIND-06) |
| T15.E     | FIND-23    | ✅ Covered (FIND-23) |
| T15.A     | FIND-26    | ✅ Covered (FIND-26) |
| T16.S     | FIND-01    | ✅ Covered (FIND-01) |
| T16.T     | FIND-01    | ✅ Covered (FIND-01) |
| T16.I     | FIND-06    | ✅ Covered (FIND-06) |
| T16.D     | FIND-08    | ✅ Covered (FIND-08) |
| T16.A     | FIND-04    | ✅ Covered (FIND-04) |
| T17.S     | FIND-02    | ✅ Covered (FIND-02) |
| T17.T     | FIND-02    | ✅ Covered (FIND-02) |
| T17.I     | FIND-06    | ✅ Covered (FIND-06) |
| T17.D     | FIND-08    | ✅ Covered (FIND-08) |
| T17.A     | FIND-18    | ✅ Covered (FIND-18) |
| T17.E     | FIND-02    | ✅ Covered (FIND-02) |
