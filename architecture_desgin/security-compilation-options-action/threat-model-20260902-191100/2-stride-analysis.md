# STRIDE + Abuse Cases — Threat Analysis

> This analysis uses the standard **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) extended with **Abuse Cases** (business logic abuse, workflow manipulation, feature misuse). The "A" column in tables below represents Abuse — a supplementary category covering threats where legitimate features are misused for unintended purposes. This is distinct from Elevation of Privilege (E), which covers authorization bypass.

## Exploitability Tiers

Threats are classified into three exploitability tiers based on the prerequisites an attacker needs:

| Tier       | Label            | Prerequisites                                                                                                                 | Assignment Rule                                                                                                |
| ---------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Tier 1** | Direct Exposure  | `None`                                                                                                                        | Exploitable by unauthenticated external attacker with NO prior access. The prerequisite field MUST say `None`. |
| **Tier 2** | Conditional Risk | Single prerequisite: `Authenticated User`, `Privileged User`, `Internal Network`, or single `{Boundary} Access`               | Requires exactly ONE form of access. The prerequisite field has ONE item.                                      |
| **Tier 3** | Defense-in-Depth | `Host/OS Access`, `Admin Credentials`, `{Component} Compromise`, `Physical Access`, or MULTIPLE prerequisites joined with `+` | Requires significant prior breach, infrastructure access, or multiple combined prerequisites.                  |

> **Deployment context binding:** Per `0.1-architecture.md`, this Action's Deployment Classification is `LOCALHOST_DESKTOP` (single-process Node.js + Python subprocess, no inbound listeners, single-tenant CI runner). T1 is FORBIDDEN for all components; all threats are T2+ based on the Component Exposure Table floors.

## Summary

| Component           | Link                         | S     | T     | R     | I     | D     | E     | A     | Total  | T1    | T2     | T3     | Risk     |
| ------------------- | ---------------------------- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ------ | ----- | ------ | ------ | -------- |
| ActionEntryPoint    | [Link](#actionentrypoint)    | 1     | 1     | 1     | 1     | 1     | 0     | 1     | 6      | 0     | 4      | 2      | Elevated |
| SecOptionScanner    | [Link](#secoptionscanner)    | 0     | 0     | 1     | 1     | 0     | 0     | 1     | 3      | 0     | 2      | 1      | Moderate |
| SecOptionDetector   | [Link](#secoptiondetector)   | 0     | 1     | 0     | 0     | 1     | 0     | 1     | 3      | 0     | 2      | 1      | Moderate |
| SecOptionScanScript | [Link](#secoptionscanscript) | 0     | 1     | 0     | 1     | 1     | 0     | 1     | 4      | 0     | 3      | 1      | Elevated |
| CicdUploader        | [Link](#cicduploader)        | 0     | 0     | 0     | 1     | 1     | 0     | 1     | 3      | 0     | 2      | 1      | Moderate |
| ApigSigner          | [Link](#apigsigner)          | 0     | 1     | 0     | 1     | 0     | 0     | 0     | 2      | 0     | 1      | 1      | Moderate |
| OpenLibingAPIG      | [Link](#openlibingapig)      | 1     | 0     | 0     | 1     | 1     | 0     | 1     | 4      | 0     | 3      | 1      | Moderate |
| HuaweiCloudOIDC     | [Link](#huaweicloudoidc)     | 1     | 0     | 0     | 1     | 1     | 0     | 0     | 3      | 0     | 1      | 2      | Moderate |
| PyPIMirror          | [Link](#pypimirror)          | 1     | 0     | 0     | 0     | 1     | 0     | 1     | 3      | 0     | 2      | 1      | Moderate |
| WorkspaceArtifacts  | [Link](#workspaceartifacts)  | 0     | 1     | 1     | 1     | 1     | 0     | 0     | 4      | 0     | 3      | 1      | Elevated |
| ScanResultFile      | [Link](#scanresultfile)      | 0     | 1     | 0     | 1     | 0     | 0     | 1     | 3      | 0     | 2      | 1      | Moderate |
| **Totals**          |                              | **4** | **6** | **3** | **9** | **8** | **0** | **8** | **38** | **0** | **25** | **13** |          |

---

## ActionEntryPoint

**Trust Boundary:** CIRunner
**Role:** `dist/index.js` `run()` 入口函数，读取 inputs、pip install、实例化 Scanner、聚合统计、设置 outputs
**Data Flows:** DF01, DF03, DF04, DF05
**Pod Co-location:** N/A (not K8s)

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ Action 由 GitCode runner 调用，无 inbound 监听器；按 LOCALHOST_DESKTOP 部署分类，T1 禁止。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                | Prerequisites      | Affected Flow    | Mitigation                                                                                                                                                                                                                                                 | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T01.T | Tampering              | PR 作者通过 `pull_request_target` 触发的 build step 输出（`${{ steps.build.outputs.artifact-path }}`）控制 `artifact-path` 值，使其指向任意路径（含 `../` 穿越）→ action 扫描 runner 工作区外文件并将路径写入上报 payload                                                                                                                                                             | Authenticated User | DF01, DF03       | 对 `artifact-path` 解析后校验路径必须位于 `process.cwd()` 子树内（`path.relative` 非 `..` 前缀）；拒绝绝对路径与 `..` 段                                                                                                                                   | Open   |
| T01.I | Information Disclosure | `execSync('git remote get-url origin', ...)` 输出经 `remoteUrl.replace(/https:\/\/[^@]+@/, 'https://')` 清洗，但正则仅匹配 `https://<token>@` 形式；若 git remote URL 为 `https://username:password@gitcode.com/...`、`git@ssh://...` 或 `https://oauth2:<token>@` 等非标准格式，token 会原样进入 `gitUrl` 并被 `core.info(\`gitUrl: ${gitUrl}\`)` 打印到 CI 日志、且写入上报 payload | Authenticated User | DF01             | 改用 `new URL(remoteUrl).origin + pathname`（仅保留 origin+path，剔除 userinfo）；或在 regex 中加入 `git@`/`oauth2:` 等已知前缀；测试覆盖各类 git URL 格式                                                                                                 | Open   |
| T01.D | Denial of Service      | PR 作者可让 build step 产出超大单文件（数十 GB ELF）、爆炸性 zip-bomb（1 GB→100 GB）、或深嵌套归档，使 `artifact-path` 指向该文件 → pip install + Python 扫描耗尽 runner 磁盘/内存，workflow 卡死到 runner 超时                                                                                                                                                                       | Authenticated User | DF01, DF03, DF05 | 限制 `artifact-path` 单文件大小（`fs.statSync` 校验）、归档解压总大小上限（解压累计字节数 vs 阈值）、递归深度上限；对 zip/tar 增加解压比（compressed:decompressed）上限（如 100:1）                                                                        | Open   |
| T01.A | Abuse                  | `pull_request_target` 触发时，master YAML 声明的 `permissions: id-token: write` 会让 action 以 base 仓权限签发 OIDC token；PR 作者可在其 PR 触发的 build step 中植入恶意代码（被 checkout 执行）来调用 action，间接获得 base 仓权限的 OIDC token 流向                                                                                                                                 | Authenticated User | DF01, DF05, DF08 | 在 `pull_request_target` 场景显式拒绝执行（或要求 `workflow_dispatch`/`schedule` 才允许 OIDC 模式）；在 ActionEntryPoint 内校验 `GITHUB_EVENT_NAME`/`ATOMGIT_EVENT_NAME` 非 `pull_request_target` 时才启用 OIDC；或要求 `permissions: id-token: none` 兜底 | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category    | Threat                                                                                                                                                      | Prerequisites  | Affected Flow    | Mitigation                                                                                                                                                    | Status |
| ----- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T01.S | Spoofing    | 攻击者通过控制 runner 环境变量（`ACTIONS_ID_TOKEN_REQUEST_URL`、`ATOMGIT_RUN_ID`、`ATOMGIT_WORKFLOW` 等）欺骗 action 走 OIDC 模式或伪造 pipeline 元数据上报 | Host/OS Access | DF01, DF05, DF08 | 对 `ATOMGIT_*` 关键元数据在 payload 中加签名校验或要求 OIDC token 内嵌 sub claims 与之匹配；runner 本身由平台托管，非 Action 可控                             | Open   |
| T01.R | Repudiation | ActionEntryPoint 仅通过 `core.info` 输出执行轨迹，未记录 inputs 哈希、调用方身份、scan 选项到不可篡改的审计日志；事后无法证明某次扫描的输入与触发方         | Host/OS Access | DF01, DF03, DF05 | 在 scan result JSON 中写入 `invocationContext: { event, actor, runId, inputsSha256 }` 字段并上报到 OpenLibingAPIG 留痕；至少本地落盘一份 invocation audit log | Open   |

#### Categories Not Applicable

| Category               | Justification                                               |
| ---------------------- | ----------------------------------------------------------- |
| Elevation of Privilege | Action 以 runner 单一用户身份运行，无内部权限边界可被提升。 |

---

## SecOptionScanner

**Trust Boundary:** CIRunner
**Role:** `dist/scanner.js` `SecOptionScanner` 类，编排 detect+upload、写入最终 JSON
**Data Flows:** DF06, DF07, DF08
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ 进程内类，无外部入口。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                           | Prerequisites      | Affected Flow                                                                                                                                                                                                               | Mitigation                                                                                          | Status     |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------- |
| T02.I | Information Disclosure | catch 块 `this.logger.error(\`Scan failed: ${error.message}\`)`后调用`this.uploader.upload({}, { ..., errorMessage: error.message, ... })`；若 `error.message` 包含绝对路径、用户名、stack trace，会被原样上报到 OpenLibingAPIG 并打印到 CI 日志 | Authenticated User | DF07, DF08                                                                                                                                                                                                                  | 对 `errorMessage` 做截断（如 max 200 字符）与路径/敏感字段过滤后再上报；本地保留完整 stack 用于排查 | Open       |
| T02.A | Abuse                  | `options.upload                                                                                                                                                                                                                                  |                    | this.config.uploader?.enabled`默认为 true（ActionEntryPoint 总是设置`config.uploader.enabled=true`），即使 PR 触发场景也会把扫描结果（含文件名/路径/开启率）无条件上报到 OpenLibingAPIG，相当于自动外泄 PR 内私有产物元数据 | Authenticated User                                                                                  | DF08, DF13 | 在 PR 触发场景（`ATOMGIT_EVENT_NAME=pull_request_target`）下默认禁用上传，要求 workflow 显式 opt-in；或仅上报不含 `filePath` 的聚合统计 | Open |

#### Tier 3 — Defense-in-Depth

| ID    | Category    | Threat                                                                                                    | Prerequisites  | Affected Flow    | Mitigation                                                                                                                        | Status |
| ----- | ----------- | --------------------------------------------------------------------------------------------------------- | -------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T02.R | Repudiation | SecOptionScanner 未记录每次 `scan()`/`upload()` 调用的输入摘要与结果 recordId，事后无法追溯某次上报的来源 | Host/OS Access | DF06, DF07, DF08 | 在 `result.uploadInfo` 中追加 `invocationContext`（pipelineRunId/runNumber/gitUrl 哈希），并在 ScanResultFile 中保留上传 ack 记录 | Open   |

#### Categories Not Applicable

| Category               | Justification                                                       |
| ---------------------- | ------------------------------------------------------------------- |
| Spoofing               | 进程内类，无独立认证面。                                            |
| Tampering              | 不接受外部输入直接修改 scanner 状态，输入委托给 SecOptionDetector。 |
| Denial of Service      | 编排类自身不持有资源；DoS 面在 detector/script/uploader。           |
| Elevation of Privilege | 单一 runner 用户，无权限边界。                                      |

---

## SecOptionDetector

**Trust Boundary:** CIRunner
**Role:** `dist/detectors/SecOptionDetector.js`：spawn Python 子进程、捕获 stdout/stderr、回读 JSON
**Data Flows:** DF06, DF09, DF11
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ 进程内类。

#### Tier 2 — Conditional Risk

| ID    | Category          | Threat                                                                                                                                                                                                                                                                                                          | Prerequisites      | Affected Flow | Mitigation                                                                                                                                            | Status |
| ----- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T03.T | Tampering         | Python 子进程的 stdout/stderr 被原样捕获并通过 `this.logger.info(\`Python stdout: ${stdout.trim()}\`)`写入 winston 日志（最终输出到 CI 控制台）；恶意 ELF 文件可触发 Python`print` 含 ANSI 转义序列/控制字符的输出，实现日志注入、终端控制序列攻击或掩盖真实错误行                                              | Authenticated User | DF09, DF11    | 对 Python stdout/stderr 做控制字符过滤（剥离 `\x1b[...` 等 CSI 序列与 NUL 字符）后再传给 logger；限制单次输出长度（如 64KB）防日志放大                | Open   |
| T03.D | Denial of Service | `const proc = spawn(pythonCmd, args, { stdio: ['ignore', 'pipe', 'pipe'] })` 未设置 `timeout` 选项；`proc.on('close')` 之外无超时机制；恶意 ELF（如 pyelftools 解析死循环、超大 section header）或归档递归死循环会让 Python 子进程永不退出，action 卡在 `await this._runPythonScript(...)` 直到 runner job 超时 | Authenticated User | DF09          | 在 `spawn` 后用 `setTimeout(() => proc.kill('SIGTERM'), 5*60*1000)` 设置硬超时；或用 `Promise.race` 与超时 promise 竞速；超时后清理 tmp_dir 并 reject | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                                                                  | Prerequisites  | Affected Flow | Mitigation                                                                                                                                        | Status |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T03.A | Abuse    | `args.push(scanOptions.join(','))` 把 scanOptions 字符串数组拼成 CLI 第 3 参数；Python 端 `analyze_single` 会 `sys.exit(1)` 退出。攻击者若能影响 `scan-options` workflow input（如通过 PR 修改 master YAML），可传入非法 key 触发非零退出 → action 失败 | Host/OS Access | DF09          | 在 JS 端先用 `set.intersection(scanOptions, ALL_OPTION_KEYS)` 过滤非法 key（ActionEntryPoint 已有 ALL_OPTION_KEYS 列表），非法 key 仅 warn 不退出 | Open   |

#### Categories Not Applicable

| Category               | Justification                               |
| ---------------------- | ------------------------------------------- |
| Spoofing               | 进程内类，无认证面。                        |
| Repudiation            | 由 SecOptionScanner 上层负责审计。          |
| Information Disclosure | 不处理敏感数据；仅传 sourceDir/outputFile。 |
| Elevation of Privilege | 单一 runner 用户。                          |

---

## SecOptionScanScript

**Trust Boundary:** CIRunner
**Role:** `dist/bin/sec_option_scan.py`：pyelftools 解析 ELF 14 项、自动解压 .deb/.whl/.jar/.tar.gz/.run
**Data Flows:** DF09, DF10, DF11
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ Python 子进程，由 SecOptionDetector spawn。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                                        | Prerequisites      | Affected Flow | Mitigation                                                                                                                                                                                      | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T04.I | Information Disclosure | `analyze_single` 在 result 中写入 `"filePath": os.path.normpath(file_path)`（绝对路径），并 `print(f"[sec-option-dbg] try_extract_archive: {file_path} ...")`、`print(f"[sec-option-dbg] run payload offset=...")` 等调试日志到 stderr；filePath 经 ScanResultFile→SecOptionScanner→CicdUploader 上报到 OpenLibingAPIG，stderr 被 SecOptionDetector 捕获后写入 CI 日志 → 泄露 runner 文件系统结构、临时目录路径、产物命名约定 | Authenticated User | DF10, DF11    | 在 `os.path.normpath` 后对绝对路径做相对化处理（如 `path.relpath(file_path, source_dir)` 仅保留相对路径）；调试日志加 `if os.environ.get('SEC_OPTION_DEBUG')` 开关默认关闭                      | Open   |
| T04.D | Denial of Service      | `_safe_extract_zip`/`_safe_extract_tar` 仅校验路径穿越，未限制解压比/总大小/递归深度；`scan_directory` 递归调用 `try_extract_archive` 处理嵌套包（.deb > data.tar.xz > .so）无深度上限；zip-bomb（1GB→100GB）或深嵌套归档可耗尽 runner 磁盘/栈/内存 → action 卡死                                                                                                                                                             | Authenticated User | DF10, DF11    | 在 `_safe_extract_zip`/`_safe_extract_tar` 内累计解压字节数，超阈值（如 1GB）即 raise；`scan_directory` 加 `depth` 参数，超阈值（如 5）即 return；单文件大小校验（`member.size` > 阈值则 skip） | Open   |
| T04.A | Abuse                  | Windows 平台优先使用短路径前缀 `D:\sec_option_tmp` 或 `C:\sec_option_tmp`（`os.makedirs(short_base, exist_ok=True)` + `tempfile.mkdtemp(prefix='s_', dir=short_base)`）；这些短路径固定可预测，恶意 PR 作者若在 PR 触发的 build step 中预先 `mklink D:\sec_option_tmp\payload X` 创建符号链接，可让后续扫描的解压路径被劫持                                                                                                   | Authenticated User | DF10, DF11    | 改用 `tempfile.mkdtemp(prefix='sec_option_extract_')` 默认系统临时目录（路径随机）；或在 `os.makedirs` 后校验目录非符号链接；解压前对 tmp_dir 做 `os.path.realpath` 校验                        | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category  | Threat                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Prerequisites                       | Affected Flow | Mitigation                                                                                                                                                             | Status |
| ----- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T04.T | Tampering | `_entry_path_unsafe` 校验绝对路径（`/`）、Windows 盘符（`name[1]==':'`）、`..` 段；但未显式拒绝 NUL 字节（`\x00`）与 Unicode 等价字符（如全角 `．．`、RTL 覆盖符 U+202E）。Python 3.6.2+ 的 zipfile 会 reject NUL，但 tarfile 与 ar 解析（`_extract_deb`）路径处理依赖 `os.path.join`，对边缘编码可能产生未预期路径。`_safe_extract_tar` 对 symlink linkname 校验 `_entry_path_unsafe`，但相对 symlink（如 `linkname = "../etc/passwd"`）已被覆盖；绝对 symlink 也被覆盖。剩余风险：构造 member.name 看似安全但 linkname 走 Unicode 规范化绕过 | Host/OS Access + Authenticated User | DF10, DF11    | 在 `_entry_path_unsafe` 中追加：拒绝包含 `\x00` 的路径、对 name 做 `unicodedata.normalize('NFKC', name)` 后再校验（防全角/兼容等价字符绕过）；记录跳过条目数到审计日志 | Open   |

#### Categories Not Applicable

| Category               | Justification                                                                       |
| ---------------------- | ----------------------------------------------------------------------------------- |
| Spoofing               | 子进程，无认证面。                                                                  |
| Repudiation            | stderr/stdout 输出即审计痕迹；上层 ActionEntryPoint/SecOptionScanner 负责正式审计。 |
| Elevation of Privilege | Python 以 runner 用户运行，无权限边界。                                             |

---

## CicdUploader

**Trust Boundary:** CIRunner
**Role:** `dist/uploaders/CicdUploader.js` `CicdUploader` 类，按 OIDC/AK-SK 双模式上报
**Data Flows:** DF08, DF12, DF13, DF14
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ 进程内类，仅发起 outbound HTTPS。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                              | Prerequisites      | Affected Flow                                                                                                                                                                                                                      | Mitigation                                                                                                                                                                        | Status     |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| T05.I | Information Disclosure | `console.log(\`[CicdUploader] Upload payload fields: gitUrl=${payload.gitUrl}, packageName=${payload.packageName}, pipelineRunId=${payload.pipelineRunId}, runNumber=${payload.runNumber}, pipelineName=${payload.pipelineName                                                      |                    | ''}, authMode=...\`)`把上报关键字段打印到 CI 日志；catch 块`console.error(\`HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}\`)` 把整个 APIG 错误响应体打印到 CI 日志，可能含内部错误细节、stack、AK 关联信息 | Authenticated User                                                                                                                                                                | DF13, DF14 | 把 payload 调试日志改为 `core.debug`（仅在 `ACTIONS_STEP_DEBUG` 开启时输出）；对 error.response.data 做 `JSON.stringify` 后截断（如 512 字符）并过滤已知敏感字段（`Authorization`、`X-Sdk-`、`X-Auth-`） | Open |
| T05.D | Denial of Service      | OIDC 模式 `await callApig('POST', url, headers, body)` 未显式设置超时，依赖 SDK 默认值；若 HuaweiCloudOIDC 端点 hang（如 TCP 连接建立但无响应），action 会卡在 await 直到 SDK 默认超时（可能数分钟），占用 runner 工作线程；axios path 有 `timeout: 30000`，但 OIDC path 不走 axios | Authenticated User | DF14                                                                                                                                                                                                                               | 用 `Promise.race([callApig(...), timeout(30000)])` 包装；超时后 `return { success:false, error:'OIDC call timeout' }`；或读 SDK 文档确认 `callApig` 是否接受 `timeout` 选项并传入 | Open       |

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                                                                                                                                                                 | Prerequisites  | Affected Flow | Mitigation                                                                                                                                                                                  | Status |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T05.A | Abuse    | `this.useOidc = !!config.useOidc` 取自 `process.env.ACTIONS_ID_TOKEN_REQUEST_URL`；若 runner 环境变量被错误配置（如 base 仓未声明 `permissions: id-token: write` 但 runner 仍注入了 ACTIONS_ID_TOKEN_REQUEST_URL，反之亦然），action 会走错认证模式与错上报接口 → 上报失败或认证错位；攻击者无需直接攻击 action，只需让 runner 误配 env 即触发模式混淆 | Host/OS Access | DF13, DF14    | 在 ActionEntryPoint 增加 `permissions` 显式校验：若 `ATOMGIT_*` 上下文显示 workflow 声明了 `id-token: write` 但 `ACTIONS_ID_TOKEN_REQUEST_URL` 不存在（或反之），提前 fail 并提示配置不一致 | Open   |

#### Categories Not Applicable

| Category               | Justification                        |
| ---------------------- | ------------------------------------ |
| Spoofing               | 客户端类，不对入站认证。             |
| Tampering              | 不接受网络输入修改自身状态。         |
| Repudiation            | 上报结果由 OpenLibingAPIG 落库留痕。 |
| Elevation of Privilege | 单一 runner 用户。                   |

---

## ApigSigner

**Trust Boundary:** CIRunner
**Role:** `dist/uploaders/CicdUploader.js` 内部 `ApigSigner` 类，实现 SDK-HMAC-SHA256 签名，持有 AK/SK
**Data Flows:** DF12
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ 进程内类，不暴露接口。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                      | Prerequisites | Affected Flow                                                                                                                                                               | Mitigation         | Status     |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ---------- |
| T06.I | Information Disclosure | `headers['Authorization'] = \`SDK-HMAC-SHA256 Access=${this.ak}, SignedHeaders=...\`` 把 AK 直接写入 Authorization 头；CicdUploader 的 catch 块 `console.error(\`Upload error: ${error.code |               | error.message}, URL: ${url}\`)` 不会打印 headers，但若 SDK 内部异常或 axios 在 retry 时把 request headers 写入 error 对象被 JSON.stringify，AK 会随错误日志泄露到 CI 控制台 | Authenticated User | DF12, DF13 | 在 CicdUploader catch 中过滤 error.config.headers、error.request.headers 等字段（delete 或 mask）；改用 `error.message` 而非 `JSON.stringify(error)`；axios 的 `error.toJSON()` 默认不含 headers，但自定义拦截器可能附加，需审计 | Open |

#### Tier 3 — Defense-in-Depth

| ID    | Category  | Threat                                                                                                                                                                                                                                                                             | Prerequisites                       | Affected Flow | Mitigation                                                                                                                                               | Status |
| ----- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T06.T | Tampering | HMAC 签名包含 `X-Sdk-Date` 时间戳与 body SHA256，但无 nonce/jti；攻击者截获一个合法签名的 POST 请求（如通过 CI 日志泄露、网络抓包、APIG 服务端日志泄露），可在 APIG 时间容忍窗口内（通常 15 分钟）重放到 `/openlibing-cicd/build-artifact/sec-option/report`，伪造一次扫描结果上报 | Host/OS Access + Authenticated User | DF12, DF13    | 在签名中追加 nonce（随机 16 字节 hex）并要求 APIG 服务端基于 `(ak, nonce)` 去重；或在 body 中嵌入 `pipelineRunId + runNumber + currentTime` 组合做幂等键 | Open   |

#### Categories Not Applicable

| Category               | Justification                               |
| ---------------------- | ------------------------------------------- |
| Spoofing               | 签名器不接收外部身份，只生成签名。          |
| Repudiation            | Authorization 头本身就是请求来源证明。      |
| Denial of Service      | 签名计算为 CPU 密集瞬时操作，无资源占用面。 |
| Elevation of Privilege | 单一 runner 用户。                          |
| Abuse                  | 无业务逻辑面。                              |

---

## OpenLibingAPIG

**Trust Boundary:** External
**Role:** openLiBing 后端 APIG 网关 `https://174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2.huaweicloudapis.com`，接收扫描结果上报
**Data Flows:** DF13, DF14
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ 部署分类 LOCALHOST_DESKTOP 禁止 T1。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                                                          | Prerequisites      | Affected Flow | Mitigation                                                                                                                                                                                           | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T07.S | Spoofing               | APIG URL 硬编码在 `dist/index.js:54257` 为 `https://174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2.huaweicloudapis.com`；若 runner 的 DNS 被劫持（如 self-hosted runner 走 attacker-controlled DNS）或本机 hosts 文件被篡改，`174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2.huaweicloudapis.com` 可能解析到攻击者 IP；axios/SDK 默认信任系统 CA store，若攻击者在该 CA store 中植入自签名证书则可完成 MITM，捕获签名请求与扫描结果 | Internal Network   | DF13, DF14    | 在 axios/SDK 中显式 pin APIG 证书指纹（pinned public key hash）；或固定 DNS 解析结果（如启动时校验 `dns.lookup(host)` IP 在华为云已知网段内）；self-hosted runner 优先走平台 NAT/EGRESS 防火墙白名单 | Open   |
| T07.I | Information Disclosure | CicdUploader catch 块 `console.error(\`HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}\`)` 将 APIG 返回体整个打印到 CI 日志；若 APIG 因 4xx/5xx 返回含内部堆栈、SQL 片段、AK 关联、其他 tenant 数据（多租串扰）的 verbose 错误响应，会泄露到 CI 控制台与 workflow 日志归档                                                                                                                                                | Authenticated User | DF13, DF14    | 对 `error.response.data` 做白名单字段提取（仅取 `code`、`msg`），其余字段不打印；或截断到 256 字符；告诉 OpenLibingAPIG 服务端团队对 4xx/5xx 返回标准 `{code,msg}` 而非堆栈                          | Open   |
| T07.D | Denial of Service      | APIG 网关不可用（华为云区域故障、限流 429、APIG 实例重启）会让 OIDC/AK-SK 上报均失败；SecOptionScanner 的 catch 块会再次尝试 upload 兜底，但若 APIG 持续不可用，action 会以 `core.setFailed` 终止，workflow job 失败；攻击者无法直接攻击 APIG，但可通过触发大量 PR（每个 PR 触发一次扫描+上报）放大 APIG 负载                                                                                                                                   | Authenticated User | DF13, DF14    | 在 CicdUploader 内对 429/503 做指数退避重试（最多 3 次，间隔 2/4/8 秒）；上报失败但扫描成功时不应 `core.setFailed`，改为 `core.warning` 让 workflow 继续                                             | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                                                                  | Prerequisites             | Affected Flow | Mitigation                                                                                                                         | Status |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T07.A | Abuse    | APIG endpoint 硬编码在客户端，所有仓库的所有 workflow 都上报到同一后端；若该 endpoint 被短暂攻陷（如供应链攻击华为云 APIG 服务、APIG 配置被恶意修改路由到 fake upstream），攻击者可批量收集各仓扫描结果（含文件路径、产物名、构建元数据），形成跨仓情报 | OpenLibingAPIG Compromise | DF13, DF14    | 客户端对返回的 `recordId` 做格式校验（如必须为数字/UUID），异常时告警；服务端签名响应体（mTLS 或响应签名头）让客户端可验证响应来源 | Open   |

#### Categories Not Applicable

| Category               | Justification                                       |
| ---------------------- | --------------------------------------------------- |
| Tampering              | Action 是 APIG 的客户端，不接受 APIG 主动推送数据。 |
| Repudiation            | APIG 端落库即为审计；客户端只关心响应状态。         |
| Elevation of Privilege | 外部服务，无 repo 内权限边界。                      |

---

## HuaweiCloudOIDC

**Trust Boundary:** External
**Role:** 华为云 STS 联邦认证服务（由 `@openlibing/huaweicloud-oidc-client@0.0.5` SDK 调用），ID Token→STS→V11 签名
**Data Flows:** DF14
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ 部署分类 LOCALHOST_DESKTOP 禁止 T1。

#### Tier 2 — Conditional Risk

| ID    | Category          | Threat                                                                                                                                                                                                                                                                         | Prerequisites      | Affected Flow | Mitigation                                                                                                                                                  | Status |
| ----- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T08.D | Denial of Service | STS endpoint（`sts.cn-southwest-2.huaweicloud.com` 等，SDK 内部决定）不可达时，`callApig('POST', url, headers, body)` 会 throw 或长时间挂起；OIDC 模式下 action 无法切换到 AK/SK 兜底（凭证未传），workflow 失败；攻击者无需直接攻击 OIDC，self-hosted runner 网络抖动即可触发 | Authenticated User | DF14          | 在 OIDC 失败时若 workflow 也提供了 `apig-app-key`/`apig-app-secret`，自动降级到 AK/SK 模式重试一次；或捕获 OIDC 错误并明确提示用户检查 workflow permissions | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                     | Prerequisites  | Affected Flow                                                                                                                      | Mitigation                                                                                                                                                      | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T08.S | Spoofing               | `ACTIONS_ID_TOKEN_REQUEST_URL` 由 runner 注入，SDK 据此向 runner 的 ID Token mint 服务发起请求；若 runner 进程被攻陷，攻击者可设置该 env 指向自己的 fake ID Token 服务，SDK 会拿到伪造的 ID Token 并向真实 STS 换凭证，被 STS 拒绝（签名不匹配），但若攻击者同时控制 STS endpoint 解析（DNS 劫持 huaweicloud 域名），可完成 fake OIDC 链路 | Host/OS Access | DF14                                                                                                                               | 客户端对 `ACTIONS_ID_TOKEN_REQUEST_URL` 做白名单校验（仅接受 runner 平台已知域名后缀）；SDK 应固定 STS 域名而非从 env 读取；self-hosted runner 必须有出网白名单 | Open   |
| T08.I | Information Disclosure | OIDC ID Token 是敏感凭证（证明 workflow 身份与 repo scope），由 SDK 持有并发送给 STS；若 SDK 在 error path 中把 token 写入 error.message 或 error.config.headers，CicdUploader 的 catch 块 `console.error(\`Upload error: ${error.code                                                                                                     |                | error.message}, URL: ${url}\`)`会把 token 打印到 CI 日志；SDK 是`@openlibing/huaweicloud-oidc-client@0.0.5` 第三方代码，行为需审计 | Host/OS Access                                                                                                                                                  | DF14   | 对 `@openlibing/huaweicloud-oidc-client` SDK 做依赖审计（npm audit + 源码审查），确认 error 路径不泄漏 token；在 CicdUploader catch 中对 error.message 做关键词过滤（`Bearer `、`eyJ` JWT 前缀） | Open |

#### Categories Not Applicable

| Category               | Justification                                  |
| ---------------------- | ---------------------------------------------- |
| Tampering              | 客户端模式，不接受 STS 主动推送。              |
| Repudiation            | STS 调用由华为云侧审计；客户端仅关心凭证可用。 |
| Elevation of Privilege | 外部服务。                                     |
| Abuse                  | 无业务逻辑面。                                 |

---

## PyPIMirror

**Trust Boundary:** External
**Role:** 阿里云 PyPI 镜像 `https://mirrors.aliyun.com/pypi/simple/`，pip install 自动安装 pyelftools
**Data Flows:** DF04
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ 部署分类 LOCALHOST_DESKTOP 禁止 T1；攻击者需 MITM 内网或控制 DNS 才能欺骗镜像。

#### Tier 2 — Conditional Risk

| ID    | Category          | Threat                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Prerequisites      | Affected Flow | Mitigation                                                                                                                                                                                                                             | Status |
| ----- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T09.S | Spoofing          | ActionEntryPoint 通过 `execSync('python3 -m pip install --break-system-packages pyelftools -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com')` 安装依赖；`--trusted-host mirrors.aliyun.com` 标志会让 pip 在 SSL 校验失败时仍信任该 host（典型用于自签证书场景）。攻击者若能在 self-hosted runner 与 mirrors.aliyun.com 之间实现 MITM（如 ARP 欺骗、DNS 劫持、HTTPS 中间人代理植入自签证书），可注入恶意 `pyelftools` 包，setup.py 在安装时执行任意 Python 代码 → 完全控制 runner 进程 | Internal Network   | DF04          | 移除 `--trusted-host mirrors.aliyun.com` 标志，让 pip 严格校验 SSL；或改用官方 PyPI `https://pypi.org/simple`（无需 trusted-host）；预安装 `pyelftools` 到 runner 镜像中（无需运行时 pip install）；增加 `--require-hashes` 锁定包哈希 | Open   |
| T09.D | Denial of Service | mirrors.aliyun.com 不可达或 pyelftools 包被下架时，pip install 抛错；ActionEntryPoint 仅 `core.warning(... The scan may fail if dependencies are missing)` 后继续，但 SecOptionScanScript 在 import pyelftools 时抛 ImportError，action 在 `core.setFailed` 终止                                                                                                                                                                                                                                                   | Authenticated User | DF04, DF09    | pip install 失败时 `core.setFailed` 立即终止并提示，避免误导用户扫描"成功"但无结果；预装 pyelftools 到 runner 镜像避免运行时依赖                                                                                                       | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                                                                                    | Prerequisites                    | Affected Flow | Mitigation                                                                                                                                                                       | Status |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T09.A | Abuse    | `pyelftools` 包名是合法包，但供应链攻击者若短暂攻陷上游 `pyelftools` PyPI 包（如维护者账号被钓鱼、PyPI 服务被攻陷、CI 投毒），可发布含恶意 setup.py 的 0.0.x 版本；ActionEntryPoint 不锁定版本（`pip install pyelftools` 取最新），会立即中招；类似 event-stream 投毒事件 | Host/OS Access + PyPI Compromise | DF04          | 在 `pip install` 中固定版本（`pyelftools==0.31`）+ `--require-hashes` 锁定 SHA256；将 pyelftools 源码 vendoring 到 dist 中（无需运行时安装）；定期 audit pyelftools 上游发布历史 | Open   |

#### Categories Not Applicable

| Category               | Justification                             |
| ---------------------- | ----------------------------------------- |
| Tampering              | 客户端只下载，不接受镜像主动推送。        |
| Repudiation            | pip 自身有日志；无需 action 侧审计。      |
| Information Disclosure | pip 不向 PyPI 发送敏感数据（包名+版本）。 |
| Elevation of Privilege | 外部服务。                                |

---

## WorkspaceArtifacts

**Trust Boundary:** CIRunner
**Role:** CI runner 工作区中的构建产物文件，由上游 build step 或 obs-download 落盘
**Data Flows:** DF02, DF03, DF10
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ LOCALHOST_DESKTOP 禁止 T1；产物写入需 PR/build 触发。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                        | Prerequisites      | Affected Flow    | Mitigation                                                                                                                                                                                   | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T10.T | Tampering              | PR 作者控制 PR 中的 build step 代码（CMakeLists.txt/makefile/构建脚本），可让 build step 产出恶意 ELF 文件（含攻击载荷的 .so）、伪造的 .whl/.deb 归档、含 zip-slip 路径的 zip → 这些产物被 ActionEntryPoint 通过 `fs.existsSync` 校验后传给 SecOptionScanScript，触发后续解压/解析链路                                        | Authenticated User | DF02, DF10, DF11 | 在 ActionEntryPoint 中校验 `artifact-path` 文件大小、类型签名（magic bytes）合理性；对 .so/.o 文件大小设上限（如 500MB）；扫描前对归档做完整性哈希校验                                       | Open   |
| T10.I | Information Disclosure | ScanResultFile 中 `filePath` 字段为 `os.path.normpath(file_path)` 绝对路径（如 `/home/runner/work/myrepo/myrepo/build/output/libfoo.so`），通过 CicdUploader 上报到 OpenLibingAPIG；上报 payload 中 `packageName`、`artifactDownloadUrl` 也泄露产物命名与 OBS/OBS 桶路径；多次扫描累积可重建 runner 文件系统结构与 build 布局 | Authenticated User | DF02, DF07, DF10 | 在 Python 端 `result["filePath"]` 改为 `path.relpath(file_path, source_dir)`（仅保留相对路径）；上报 payload 中 `artifactDownloadUrl` 仅传 OBS object key 而非完整 URL                       | Open   |
| T10.D | Denial of Service      | PR 作者可让 build step 产出超大单文件（GB 级别 ELF）或高嵌套归档（zip 内 tar 内 zip...），ActionEntryPoint `fs.existsSync` 通过后 SecOptionScanScript 尝试解压/解析 → 占满 runner 磁盘/CPU，workflow 超时                                                                                                                     | Authenticated User | DF02, DF03, DF10 | 在 ActionEntryPoint 中对 `artifact-path` 解析后 `fs.statSync` 校验大小阈值（如 1GB），超阈值 fail；SecOptionScanScript 在解压前对 `os.path.getsize(file_path)` 与归档成员 `member.size` 校验 | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category    | Threat                                                                                                                                             | Prerequisites  | Affected Flow    | Mitigation                                                                                                                                    | Status |
| ----- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T10.R | Repudiation | WorkspaceArtifacts 是文件落盘到 runner 工作区，无来源签名；无法事后证明某 .so 文件是哪个 commit/PR build 步骤产出的（build step 代码可被 PR 修改） | Host/OS Access | DF02, DF03, DF10 | 在 build step 完成后写入 `_artifact_provenance.json`（记录 commit SHA、build time、source hash），ActionEntryPoint 扫描时附带 provenance 上报 | Open   |

#### Categories Not Applicable

| Category               | Justification        |
| ---------------------- | -------------------- |
| Spoofing               | 文件系统无认证面。   |
| Elevation of Privilege | 文件系统无权限边界。 |
| Abuse                  | 无业务逻辑面。       |

---

## ScanResultFile

**Trust Boundary:** CIRunner
**Role:** 扫描结果 JSON 文件（默认 `sec-option-result.json`），由 Python 写、Node 读
**Data Flows:** DF07, DF09, DF11
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified._ LOCALHOST_DESKTOP 禁止 T1。

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                                                                                                                | Prerequisites        | Affected Flow    | Mitigation                                                                                                                                                                           | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| T11.T | Tampering              | SecOptionScanScript 在 `analyze_single`/`compute_summary` 后通过 `json.dump` 写入 ScanResultFile；SecOptionDetector 在 `_readResult` 中 `fs.readFileSync` 后 `JSON.parse`。两个步骤之间存在 TOCTOU 窗口：若 attacker 在同一 runner 上有 Local Process Access（如 self-hosted runner 多 job 并发、或 PR 触发的恶意 job），可在 Python 写完后、Node 读前替换文件，注入伪造扫描结果（如把 `bindNow` 从 NO 改为 YES）→ 上报到 OpenLibingAPIG 的数据被篡改 | Local Process Access | DF07, DF09, DF11 | Python 写入时附带文件签名（如 HMAC-SHA256(file_content, runner_secret)）写入 `_signature` 字段；Node 读取后校验签名；或用 `fs.openSync` 加 `O_EXCL` 写入临时文件再 `rename` 原子替换 | Open   |
| T11.I | Information Disclosure | ScanResultFile 包含 `filePath`（绝对路径）、`options` 各项 YES/NO 计数、`summary.averageRate`；`fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf8')` 未显式设置文件权限（默认 umask，Linux 通常 0644 = world-readable）；在 self-hosted 或共享 runner 上，其他 tenant 或运维可读该文件                                                                                                                                              | Local Process Access | DF07, DF11       | `fs.writeFileSync` 第三参数加 `{ mode: 0o600 }` 显式设置仅 owner 可读写；Python 端 `json.dump` 后 `os.chmod(output_path, 0o600)`                                                     | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                                                                                                                                         | Prerequisites | Affected Flow                              | Mitigation                          | Status     |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------- | ------------------------------------------ | ----------------------------------- | ---------- |
| T11.A | Abuse    | 多产物场景下 SecOptionScanner 为每个产物写 `sec-option-result-<packageName>.json`，`packageName` 来自 workflow input 或 `path.basename(resolvedArtifact)`；若 PR 作者让 build step 产出文件名为 `../../etc/cron.d/x.json` 这类含路径的产物名，则 `path.join(path.dirname(outputFile), \`sec-option-result-${target.packageName |               | i}.json\`)` 会写到工作区外（路径穿越写入） | Host/OS Access + Authenticated User | DF07, DF11 | 在 SecOptionScanner 中对 `target.packageName` 做 sanitize：剥离路径分隔符（`path.basename(target.packageName)`）、限制字符集（`/^[a-zA-Z0-9_.-]+$/`）；写文件前校验最终路径必须位于 `outputDir` 子树内 | Open |

#### Categories Not Applicable

| Category               | Justification          |
| ---------------------- | ---------------------- |
| Spoofing               | 文件无认证面。         |
| Repudiation            | 文件本身就是审计产物。 |
| Denial of Service      | 文件读写为瞬时操作。   |
| Elevation of Privilege | 文件系统无权限边界。   |
