# Security Findings

---

## Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 findings identified for this repository.* Per `0.1-architecture.md` Deployment Classification `LOCALHOST_DESKTOP`，Action 无 inbound 网络监听器、CI runner 单租户独占工作区，T1 在所有组件上禁止。

---

## Tier 2 — Conditional Risk (Authenticated / Single Prerequisite)

### FIND-04: `pull_request_target` 触发场景下 OIDC Token 以 Base 仓权限签发被 PR 作者间接盗用

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Important |
| CVSS 4.0 | 7.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N) |
| CWE | [CWE-863](https://cwe.mitre.org/data/definitions/863.html): Incorrect Authorization |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | Authenticated User (PR 作者通过 `pull_request_target` 触发) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | ActionEntryPoint |
| Related Threats | [T01.A](2-stride-analysis.md#actionentrypoint), [T02.A](2-stride-analysis.md#secoptionscanner) |

#### Description

`pull_request_target` 事件触发时，master 分支 YAML 声明的 `permissions: id-token: write` 会让 Action 以 base 仓权限向 runner 请求 OIDC ID Token；PR 作者可在其 PR 触发的 build step 中植入恶意代码（被 checkout 执行）来调用 Action，间接获得 base 仓权限的 OIDC token 流向。同时 `SecOptionScanner.scan()` 在 `options.upload || this.config.uploader?.enabled` 为 true 时（ActionEntryPoint 总是设置 `config.uploader.enabled=true`）会无条件上报扫描结果（含文件路径/产物名/开启率）到 OpenLibingAPIG，相当于自动外泄 PR 内私有产物元数据。

#### Evidence

**Prerequisite basis:** ActionEntryPoint 无 inbound 监听器，但 attack surface 是 workflow inputs（由 PRContributor 经 runner 注入）；按 `0.1-architecture.md` Component Exposure Table，PRContributor 的 Min Prerequisite 为 Authenticated User (T2)。

- `dist/index.js:54260` `const useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL;` — 仅检查 env 是否存在，不校验事件类型
- `dist/index.js:54328-54337` `if (cicdUrl) { config.uploader = { enabled: true, ... }; }` — 上报开关恒为 true，PR 触发场景无法关闭
- `action.yml:69-92` — `apig-app-key`/`apig-app-secret` 通过 `with` 传入，未声明 `id-token: write` 时使用 AK/SK，已声明时使用 OIDC（base 仓 OIDC 权限）
- 无 `GITHUB_EVENT_NAME`/`ATOMGIT_EVENT_NAME` 事件类型校验，无法识别 `pull_request_target` 触发场景

#### Remediation

在 `pull_request_target` 触发场景显式拒绝执行 OIDC 模式（或要求 `workflow_dispatch`/`schedule` 才允许 OIDC）：在 ActionEntryPoint 内校验 `ATOMGIT_EVENT_NAME`/`GITHUB_EVENT_NAME`，非 `pull_request_target` 时才启用 OIDC；或在 `pull_request_target` 场景默认禁用上报并要求 workflow 显式 opt-in；仅上报不含 `filePath` 的聚合统计。

#### Verification

提交一个 PR 到 base 仓触发 `pull_request_target` 事件，确认 Action 检测到事件类型后拒绝启用 OIDC 模式并打印明确告警；在另一仓通过 `workflow_dispatch` 触发，确认 OIDC 模式正常启用且上报成功。

---

### FIND-11: `pip install` 使用 `--trusted-host` 削弱 SSL 校验，存在供应链 MITM 风险

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Important |
| CVSS 4.0 | 7.0 (CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H) |
| CWE | [CWE-295](https://cwe.mitre.org/data/definitions/295.html): Improper Certificate Validation |
| OWASP | A02:2025 – Cryptographic Failures |
| Exploitation Prerequisites | Internal Network (MITM mirrors.aliyun.com) + Authenticated User (触发 pip install) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Internal Network) |
| Remediation Effort | Low |
| Mitigation Type | Standard Mitigation |
| Component | PyPIMirror |
| Related Threats | [T09.S](2-stride-analysis.md#pypimirror), [T09.D](2-stride-analysis.md#pypimirror) |

#### Description

ActionEntryPoint 通过 `execSync('python3 -m pip install --break-system-packages pyelftools -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com')` 安装依赖；`--trusted-host mirrors.aliyun.com` 标志会让 pip 在 SSL 校验失败时仍信任该 host（典型用于自签证书场景），攻击者若能在 self-hosted runner 与 mirrors.aliyun.com 之间实现 MITM（如 ARP 欺骗、DNS 劫持、HTTPS 中间人代理植入自签证书），可注入恶意 `pyelftools` 包，setup.py 在安装时执行任意 Python 代码 → 完全控制 runner 进程。此外 mirrors.aliyun.com 不可达或 pyelftools 包被下架时，pip install 抛错后 ActionEntryPoint 仅 `core.warning` 后继续，但 SecOptionScanScript import pyelftools 时抛 ImportError，action 在 `core.setFailed` 终止。

#### Evidence

**Prerequisite basis:** PyPIMirror 是外部 web 服务无认证；按 `0.1-architecture.md` Component Exposure Table，PyPIMirror 的 Min Prerequisite 在 LOCALHOST_DESKTOP 下被强制提升到 Internal Network (T2)（T1 禁止）。

- `dist/index.js:54288-54292` `pipInstallArgs = ['-m', 'pip', 'install', '--break-system-packages', 'pyelftools', '-i', 'https://mirrors.aliyun.com/pypi/simple/', '--trusted-host', 'mirrors.aliyun.com']`
- `dist/index.js:54293-54299` `try { ... execSync(...) } catch (e) { core.warning(...) }` — 安装失败仅 warning 后继续
- `dist/bin/sec_option_scan.py:22-24` `from elftools.common.exceptions import ELFError; from elftools.elf.elffile import ELFFile; from elftools.elf.enums import ENUM_ST_INFO_TYPE, ENUM_DT_FLAGS` — 失败则 ImportError

#### Remediation

移除 `--trusted-host mirrors.aliyun.com` 标志，让 pip 严格校验 SSL；或改用官方 PyPI `https://pypi.org/simple`（无需 trusted-host）；预安装 `pyelftools` 到 runner 镜像中（无需运行时 pip install）；增加 `--require-hashes` 锁定包哈希；pip install 失败时立即 `core.setFailed` 终止并明确提示。

#### Verification

`grep -n "trusted-host" dist/index.js` 不再命中；在 self-hosted runner 上抓包确认 pip 严格走 HTTPS+CA 校验；断网测试确认 pip install 失败后 Action 立即 setFailed 而非继续扫描。

---

### FIND-02: git remote URL 清洗正则不完整导致非标准格式的 Token 泄露到 CI 日志与上报 payload

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N) |
| CWE | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP | A09:2025 – Security Logging and Monitoring Failures |
| Exploitation Prerequisites | Authenticated User (PR 作者控制 workflow 配置非标准 git remote URL) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | ActionEntryPoint |
| Related Threats | [T01.I](2-stride-analysis.md#actionentrypoint), [T05.I](2-stride-analysis.md#cicduploader), [T06.I](2-stride-analysis.md#apigsigner) |

#### Description

`execSync('git remote get-url origin', ...)` 输出经 `remoteUrl.replace(/https:\/\/[^@]+@/, 'https://')` 清洗，但正则仅匹配 `https://<token>@` 形式；若 git remote URL 为 `https://username:password@gitcode.com/...`、`git@ssh://...` 或 `https://oauth2:<token>@` 等非标准格式，token 会原样进入 `gitUrl` 并被 `core.info(\`gitUrl: ${gitUrl}\`)` 打印到 CI 日志、且写入上报 payload。此外 `CicdUploader` 的 `console.log(\`[CicdUploader] Upload payload fields: gitUrl=${payload.gitUrl}, ...\`)` 把上报关键字段打印到 CI 日志；catch 块 `console.error(\`HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}\`)` 把整个 APIG 错误响应体打印到 CI 日志，可能含 AK 关联信息；`ApigSigner` 把 AK 直接写入 Authorization 头，若 axios 在 retry 时把 request headers 写入 error 对象被 JSON.stringify，AK 会随错误日志泄露。

#### Evidence

**Prerequisite basis:** ActionEntryPoint 无 inbound 监听器，attack surface 是 workflow 配置；按 Component Exposure Table，PRContributor 的 Min Prerequisite 为 Authenticated User (T2)。

- `dist/index.js:54271` `gitUrl = remoteUrl.replace(/https:\/\/[^@]+@/, 'https://');` — 仅匹配标准 `https://token@` 形式
- `dist/index.js:54343` `core.info(\`gitUrl: ${gitUrl || '(empty)'}\`);` — 打印到 CI 日志
- `dist/index.js:54382` `gitUrl: gitUrl,` — 写入上报 payload
- `dist/uploaders/CicdUploader.js:296` `console.log(\`[CicdUploader] Upload payload fields: gitUrl=${payload.gitUrl}, ...\`)`
- `dist/uploaders/CicdUploader.js:337` `console.error(\`HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}\`)`
- `dist/uploaders/CicdUploader.js:134` `headers['Authorization'] = \`SDK-HMAC-SHA256 Access=${this.ak}, ...\`` — AK 在 header 中

#### Remediation

改用 `new URL(remoteUrl).origin + pathname`（仅保留 origin+path，剔除 userinfo）；或在 regex 中加入 `git@`/`oauth2:` 等已知前缀；测试覆盖各类 git URL 格式；把 payload 调试日志改为 `core.debug`（仅在 `ACTIONS_STEP_DEBUG` 开启时输出）；对 error.response.data 做白名单字段提取（仅取 `code`、`msg`）并截断；在 CicdUploader catch 中过滤 `error.config.headers`、`error.request.headers` 字段。

#### Verification

单元测试覆盖 `https://user:pass@host`、`git@ssh://...`、`https://oauth2:token@host` 格式确认清洗后无凭证残留；CI 日志中 `grep -E "(token|password|AK|Bearer|eyJ)"` 无命中；`ACTIONS_STEP_DEBUG=false` 时无 payload 调试输出。

---

### FIND-03: 产物文件大小/解压比/递归深度无限制，存在资源耗尽 DoS 风险

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 6.5 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:H) |
| CWE | [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling |
| OWASP | A10:2025 – Mishandling of Exceptional Conditions |
| Exploitation Prerequisites | Authenticated User (PR 作者让 build step 产出超大文件/zip-bomb/深嵌套归档) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | ActionEntryPoint |
| Related Threats | [T01.D](2-stride-analysis.md#actionentrypoint), [T03.D](2-stride-analysis.md#secoptiondetector), [T04.D](2-stride-analysis.md#secoptionscanscript), [T10.D](2-stride-analysis.md#workspaceartifacts) |

#### Description

PR 作者可让 build step 产出超大单文件（数十 GB ELF）、爆炸性 zip-bomb（1 GB→100 GB）、或深嵌套归档（zip 内 tar 内 zip...），使 `artifact-path` 指向该文件 → pip install + Python 扫描耗尽 runner 磁盘/内存，workflow 卡死到 runner 超时。`SecOptionDetector._runPythonScript` 中 `spawn(pythonCmd, args, { stdio: ['ignore', 'pipe', 'pipe'] })` 未设置 `timeout` 选项，恶意 ELF（pyelftools 解析死循环、超大 section header）或归档递归死循环会让 Python 子进程永不退出，action 卡在 `await this._runPythonScript(...)` 直到 runner job 超时。`SecOptionScanScript._safe_extract_zip`/`_safe_extract_tar` 仅校验路径穿越，未限制解压比/总大小/递归深度。

#### Evidence

**Prerequisite basis:** ActionEntryPoint/SecOptionDetector/SecOptionScanScript 均无 inbound 监听器，attack surface 是 workflow inputs + WorkspaceArtifacts；按 Component Exposure Table，PRContributor 与 WorkspaceArtifacts 的 Min Prerequisite 均为 T2。

- `dist/index.js:54311-54312` `const resolvedArtifact = path.isAbsolute(line) ? line : path.resolve(process.cwd(), line); if (!fs.existsSync(resolvedArtifact))` — 仅校验存在性，无 `fs.statSync().size` 校验
- `dist/detectors/SecOptionDetector.js:78` `const proc = spawn(pythonCmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });` — 无 timeout 选项
- `dist/detectors/SecOptionDetector.js:93` `proc.on('close', (code) => {` — 之外无超时机制
- `dist/bin/sec_option_scan.py:190-220` `_safe_extract_zip`/`_safe_extract_tar` 仅校验路径穿越，无解压字节数累计、无递归深度上限
- `dist/bin/sec_option_scan.py:67-97` `scan_directory` 递归调用 `try_extract_archive` 处理嵌套包（.deb > data.tar.xz > .so）无 depth 参数

#### Remediation

在 ActionEntryPoint 中对 `artifact-path` 解析后 `fs.statSync` 校验大小阈值（如 1GB），超阈值 fail；在 `spawn` 后用 `setTimeout(() => proc.kill('SIGTERM'), 5*60*1000)` 设置硬超时；在 `_safe_extract_zip`/`_safe_extract_tar` 内累计解压字节数，超阈值（如 1GB）即 raise；`scan_directory` 加 `depth` 参数，超阈值（如 5）即 return；对 zip/tar 增加解压比（compressed:decompressed）上限（如 100:1）。

#### Verification

提交 5GB ELF 文件作为 `artifact-path`，确认 Action 在 stat 校验阶段 fail 而非尝试扫描；提交 zip-bomb（10MB→1GB）确认 `_safe_extract_zip` 在累计字节超阈值时 raise；提交深嵌套归档（5 层以上）确认 `scan_directory` 在 depth 超阈值时 return；提交死循环 ELF 确认 spawn 在 5 分钟后被 SIGTERM 终止。

---

### FIND-09: APIG 端点硬编码且无 TLS 证书指纹固定，存在 DNS 劫持与 MITM 风险

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 5.5 (CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N) |
| CWE | [CWE-547](https://cwe.mitre.org/data/definitions/547.html): Use of Hard-coded, Security-relevant Constants |
| OWASP | A02:2025 – Cryptographic Failures |
| Exploitation Prerequisites | Internal Network (DNS 劫持或 hosts 篡改) + Authenticated User (触发上报) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Internal Network) |
| Remediation Effort | High |
| Mitigation Type | Standard Mitigation |
| Component | OpenLibingAPIG |
| Related Threats | [T07.S](2-stride-analysis.md#openlibingapig), [T07.I](2-stride-analysis.md#openlibingapig) |

#### Description

APIG URL 硬编码在 `dist/index.js:54256` 为 `https://174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2.huaweicloudapis.com`；若 runner 的 DNS 被劫持（如 self-hosted runner 走 attacker-controlled DNS）或本机 hosts 文件被篡改，该域名可能解析到攻击者 IP；axios/SDK 默认信任系统 CA store，若攻击者在该 CA store 中植入自签名证书则可完成 MITM，捕获签名请求与扫描结果。同时 CicdUploader catch 块 `console.error(\`HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}\`)` 将 APIG 返回体整个打印到 CI 日志；若 APIG 因 4xx/5xx 返回含内部堆栈、SQL 片段、AK 关联、其他 tenant 数据（多租串扰）的 verbose 错误响应，会泄露到 CI 控制台与 workflow 日志归档。

#### Evidence

**Prerequisite basis:** OpenLibingAPIG 是外部服务，按 Component Exposure Table 的 Min Prerequisite 为 Authenticated User (T2)；DNS 劫持/CA 信任链攻击属于 Internal Network 攻击面（单一 prerequisite）。

- `dist/index.js:54256` `const cicdUrl = 'https://174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2.huaweicloudapis.com';`
- `dist/uploaders/CicdUploader.js:328` `const response = await axios.post(url, body, { headers, timeout: this.timeout });` — 默认信任系统 CA store，无证书指纹固定
- `dist/uploaders/CicdUploader.js:337` `console.error(\`HTTP ${error.response.status}: ${JSON.stringify(error.response.data)}\`)` — 完整打印响应体

#### Remediation

在 axios/SDK 中显式 pin APIG 证书指纹（pinned public key hash）；或固定 DNS 解析结果（启动时校验 `dns.lookup(host)` IP 在华为云已知网段内）；self-hosted runner 优先走平台 NAT/EGRESS 防火墙白名单；对 `error.response.data` 做白名单字段提取（仅取 `code`、`msg`），其余字段不打印或截断到 256 字符；告诉 OpenLibingAPIG 服务端团队对 4xx/5xx 返回标准 `{code,msg}` 而非堆栈。

#### Verification

在 self-hosted runner 上修改 hosts 文件指向攻击者 IP，确认 Action 因证书指纹校验失败而拒绝连接；构造 4xx 错误响应（含 verbose stack 字段）确认 CI 日志中仅打印 `code`/`msg` 字段。

---

### FIND-01: `artifact-path` 输入未校验路径穿越，可扫描 runner 工作区外文件并泄露到上报 payload

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N) |
| CWE | [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Improper Limitation of a Pathname to a Restricted Directory |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | Authenticated User (PR 作者通过 build step 输出控制 `artifact-path` 值) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Low |
| Mitigation Type | Custom Mitigation |
| Component | ActionEntryPoint |
| Related Threats | [T01.T](2-stride-analysis.md#actionentrypoint) |

#### Description

PR 作者通过 `pull_request_target` 触发的 build step 输出（`${{ steps.build.outputs.artifact-path }}`）控制 `artifact-path` 值，使其指向任意路径（含 `../` 穿越）→ action 扫描 runner 工作区外文件并将路径写入上报 payload。`path.isAbsolute(line) ? line : path.resolve(process.cwd(), line)` 接受绝对路径和相对路径，但无路径前缀校验，未限制必须位于 `process.cwd()` 子树内。

#### Evidence

**Prerequisite basis:** ActionEntryPoint 无 inbound 监听器，attack surface 是 workflow inputs；按 Component Exposure Table，PRContributor 的 Min Prerequisite 为 Authenticated User (T2)。

- `dist/index.js:54311` `const resolvedArtifact = path.isAbsolute(line) ? line : path.resolve(process.cwd(), line);` — 接受绝对路径，无 `..` 校验
- `dist/index.js:54312` `if (!fs.existsSync(resolvedArtifact))` — 仅校验存在性
- `dist/index.js:54315` `path: resolvedArtifact,` — 写入 scanTargets，后续会出现在 ScanResultFile 的 `filePath` 字段并被上报

#### Remediation

对 `artifact-path` 解析后校验路径必须位于 `process.cwd()` 子树内：`const rel = path.relative(process.cwd(), resolvedArtifact); if (rel.startsWith('..') || path.isAbsolute(rel)) throw new Error('artifact-path must be within workspace');`；拒绝绝对路径与 `..` 段。

#### Verification

提交 build step 输出 `artifact-path: ../../etc/passwd` 与 `/etc/passwd`，确认 Action 在路径校验阶段 fail 而非尝试扫描；提交合法相对路径 `./build/output/app.so` 确认正常扫描。

---

### FIND-14: 构建产物来源无完整性校验，PR 作者可投递恶意 ELF 或归档触发后续解析链路

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 5.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:H/VA:N) |
| CWE | [CWE-345](https://cwe.mitre.org/data/definitions/345.html): Insufficient Verification of Data Authenticity |
| OWASP | A08:2025 – Software and Data Integrity Failures |
| Exploitation Prerequisites | Authenticated User (PR 作者控制 PR 中的 build step 代码) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | WorkspaceArtifacts |
| Related Threats | [T10.T](2-stride-analysis.md#workspaceartifacts) |

#### Description

PR 作者控制 PR 中的 build step 代码（CMakeLists.txt/makefile/构建脚本），可让 build step 产出恶意 ELF 文件（含攻击载荷的 .so）、伪造的 .whl/.deb 归档、含 zip-slip 路径的 zip → 这些产物被 ActionEntryPoint 通过 `fs.existsSync` 校验后传给 SecOptionScanScript，触发后续解压/解析链路。ActionEntryPoint 仅校验文件存在性，不校验文件类型签名（magic bytes）合理性、不校验文件大小、不校验来源（commit SHA 或 build provenance）。

#### Evidence

**Prerequisite basis:** WorkspaceArtifacts 是文件系统数据存储，按 Component Exposure Table 的 Min Prerequisite 为 Local Process Access (T2)；PRContributor 通过 build step 写入产物，单一 prerequisite 为 Authenticated User (T2)。

- `dist/index.js:54311-54312` `if (!fs.existsSync(resolvedArtifact)) { throw new Error(...) }` — 仅校验存在性
- `dist/index.js:54314-54318` `scanTargets.push({ path: resolvedArtifact, packageName: ..., artifactName: path.basename(resolvedArtifact) })` — 直接传入 Scanner，无类型/大小校验
- `dist/bin/sec_option_scan.py:59-97` `scan_directory(scan_path, ...)` 递归扫描 + `try_extract_archive` 自动解压；恶意归档可触发后续解压/解析链路

#### Remediation

在 ActionEntryPoint 中校验 `artifact-path` 文件大小、类型签名（magic bytes）合理性；对 .so/.o 文件大小设上限（如 500MB）；扫描前对归档做完整性哈希校验；在 build step 完成后写入 `_artifact_provenance.json`（记录 commit SHA、build time、source hash），ActionEntryPoint 扫描时附带 provenance 上报。

#### Verification

提交 build step 产出 2GB ELF 文件，确认 Action 在大小校验阶段 fail；提交伪造 .whl 归档（非 ZIP magic bytes），确认类型签名校验拒绝；提交含 `_artifact_provenance.json` 的产物，确认上报 payload 中附带 provenance 字段。

---

### FIND-06: Python 子进程 stdout/stderr 未做控制字符过滤，存在日志注入与终端控制序列攻击

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 5.0 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:L/VA:L) |
| CWE | [CWE-117](https://cwe.mitre.org/data/definitions/117.html): Improper Output Neutralization for Logs |
| OWASP | A09:2025 – Security Logging and Monitoring Failures |
| Exploitation Prerequisites | Authenticated User (PR 作者让 build step 产出可触发 Python print 的恶意 ELF) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Low |
| Mitigation Type | Custom Mitigation |
| Component | SecOptionDetector |
| Related Threats | [T03.T](2-stride-analysis.md#secoptiondetector) |

#### Description

Python 子进程的 stdout/stderr 被原样捕获并通过 `this.logger.info(\`Python stdout: ${stdout.trim()}\`)` 写入 winston 日志（最终输出到 CI 控制台）；恶意 ELF 文件可触发 Python `print` 含 ANSI 转义序列/控制字符的输出，实现日志注入、终端控制序列攻击或掩盖真实错误行。`SecOptionScanScript` 的 `print(f"[sec-option-dbg] try_extract_archive: ...")` 等调试日志也是攻击面。

#### Evidence

**Prerequisite basis:** SecOptionDetector 无 inbound 监听器，attack surface 是 SecOptionScanScript 的 stdout/stderr；按 Component Exposure Table，PRContributor 的 Min Prerequisite 为 Authenticated User (T2)。

- `dist/detectors/SecOptionDetector.js:85-91` `proc.stdout.on('data', (data) => { stdout += data.toString(); }); proc.stderr.on('data', (data) => { stderr += data.toString(); });` — 原样捕获，无控制字符过滤
- `dist/detectors/SecOptionDetector.js:94-99` `if (stdout.trim()) { this.logger.info(\`Python stdout: ${stdout.trim()}\`); } if (stderr.trim()) { this.logger.warn(\`Python stderr: ${stderr.trim()}\`); }` — 直接写入日志
- `dist/bin/sec_option_scan.py:128-130` `print(f"[sec-option-dbg] try_extract_archive: {file_path} ...", file=sys.stderr)` — 调试日志包含 file_path

#### Remediation

对 Python stdout/stderr 做控制字符过滤（剥离 `\x1b[...` 等 CSI 序列与 NUL 字节）后再传给 logger；限制单次输出长度（如 64KB）防日志放大；对 file_path 在打印前做 sanitize（剥离控制字符）。

#### Verification

构造含 ANSI 转义序列的 ELF 文件名（如 `\x1b[2J\x1b[H`），确认日志中无 CSI 序列残留；构造超长 print 输出确认日志截断到 64KB。

---

### FIND-05: 扫描结果 `filePath` 绝对路径与错误 message 直接泄露到 CI 日志与上报 payload

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 4.3 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N) |
| CWE | [CWE-209](https://cwe.mitre.org/data/definitions/209.html): Generation of Error Message Containing Sensitive Information |
| OWASP | A09:2025 – Security Logging and Monitoring Failures |
| Exploitation Prerequisites | Authenticated User (PR 作者触发扫描失败或构造产物触发调试日志) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | SecOptionScanScript |
| Related Threats | [T04.I](2-stride-analysis.md#secoptionscanscript), [T10.I](2-stride-analysis.md#workspaceartifacts), [T02.I](2-stride-analysis.md#secoptionscanner) |

#### Description

`analyze_single` 在 result 中写入 `"filePath": os.path.normpath(file_path)`（绝对路径），并 `print(f"[sec-option-dbg] try_extract_archive: {file_path} ...")` 等调试日志到 stderr；filePath 经 ScanResultFile→SecOptionScanner→CicdUploader 上报到 OpenLibingAPIG，stderr 被 SecOptionDetector 捕获后写入 CI 日志 → 泄露 runner 文件系统结构、临时目录路径、产物命名约定。`SecOptionScanner` catch 块 `this.logger.error(\`Scan failed: ${error.message}\`)` 后调用 `this.uploader.upload({}, { ..., errorMessage: error.message, ... })`；若 `error.message` 包含绝对路径、用户名、stack trace，会被原样上报到 OpenLibingAPIG 并打印到 CI 日志。

#### Evidence

**Prerequisite basis:** SecOptionScanScript 无 inbound 监听器，attack surface 是产物文件与 SecOptionScanScript 的 stdout/stderr；按 Component Exposure Table，PRContributor 与 WorkspaceArtifacts 的 Min Prerequisite 均为 T2。

- `dist/bin/sec_option_scan.py` `analyze_single` 中 `result["filePath"] = os.path.normpath(file_path)` — 绝对路径
- `dist/bin/sec_option_scan.py:128-130` `print(f"[sec-option-dbg] try_extract_archive: {file_path} ...", file=sys.stderr)`
- `dist/scanner.js:108` `this.logger.error(\`Scan failed: ${error.message}\`);` — 错误 message 原样输出
- `dist/scanner.js:114-125` `this.uploader.upload({}, { ..., errorMessage: error.message, ... })` — error.message 原样上报
- `dist/uploaders/CicdUploader.js:269-279` payload 中 `gitUrl`、`packageName`、`artifactDownloadUrl`、`pipelineName` 等字段均原样上报

#### Remediation

在 Python 端 `result["filePath"]` 改为 `path.relpath(file_path, source_dir)`（仅保留相对路径）；调试日志加 `if os.environ.get('SEC_OPTION_DEBUG')` 开关默认关闭；对 `errorMessage` 做截断（如 max 200 字符）与路径/敏感字段过滤后再上报；本地保留完整 stack 用于排查；上报 payload 中 `artifactDownloadUrl` 仅传 OBS object key 而非完整 URL。

#### Verification

扫描含绝对路径的产物，确认上报 payload 中 `filePath` 为相对路径（如 `libfoo.so`）而非 `/home/runner/work/...`；触发 scan 异常，确认 `errorMessage` 截断到 200 字符且不含绝对路径/用户名；`SEC_OPTION_DEBUG` 未设置时 CI 日志无 `[sec-option-dbg]` 输出。

---

### FIND-07: Windows 平台硬编码短路径前缀 `D:\sec_option_tmp`/`C:\sec_option_tmp` 可被符号链接预植劫持

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 4.3 (CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:L) |
| CWE | [CWE-377](https://cwe.mitre.org/data/definitions/377.html): Insecure Temporary File |
| OWASP | A02:2025 – Cryptographic Failures |
| Exploitation Prerequisites | Authenticated User (PR 作者在 PR 触发的 build step 中预植符号链接) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User) |
| Remediation Effort | Low |
| Mitigation Type | Custom Mitigation |
| Component | SecOptionScanScript |
| Related Threats | [T04.A](2-stride-analysis.md#secoptionscanscript) |

#### Description

Windows 平台优先使用短路径前缀 `D:\sec_option_tmp` 或 `C:\sec_option_tmp`（`os.makedirs(short_base, exist_ok=True)` + `tempfile.mkdtemp(prefix='s_', dir=short_base)`）；这些短路径固定可预测，恶意 PR 作者若在 PR 触发的 build step 中预先 `mklink D:\sec_option_tmp\payload X` 创建符号链接，可让后续扫描的解压路径被劫持，将解压出的恶意 ELF 替换为攻击者控制的内容。

#### Evidence

**Prerequisite basis:** SecOptionScanScript 无 inbound 监听器，attack surface 是产物解压路径；按 Component Exposure Table，PRContributor 的 Min Prerequisite 为 Authenticated User (T2)，AV:L 因需在 runner 主机操作符号链接。

- `dist/bin/sec_option_scan.py:137-144` `if sys.platform == 'win32': for short_base in (r'D:\sec_option_tmp', r'C:\sec_option_tmp'): try: os.makedirs(short_base, exist_ok=True); tmp_dir = tempfile.mkdtemp(prefix='s_', dir=short_base); break except Exception: continue`

#### Remediation

改用 `tempfile.mkdtemp(prefix='sec_option_extract_')` 默认系统临时目录（路径随机）；或在 `os.makedirs` 后校验目录非符号链接（`os.path.islink(short_base)`）；解压前对 tmp_dir 做 `os.path.realpath` 校验，确认最终路径不指向符号链接目标。

#### Verification

在 Windows runner 上预植 `mklink D:\sec_option_tmp\payload C:\Windows\System32`，确认 Action 检测到符号链接后 fail；正常扫描场景确认临时目录使用 `%TEMP%\sec_option_extract_xxxxx` 而非固定短路径。

---

### FIND-12: ScanResultFile 存在 TOCTOU 窗口，本地进程可替换扫描结果篡改上报数据

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 4.0 (CVSS:4.0/AV:L/AC:H/AT:N/PR:L/UI:N/VC:N/VI:H/VA:N) |
| CWE | [CWE-367](https://cwe.mitre.org/data/definitions/367.html): Time-of-check Time-of-use Race Condition |
| OWASP | A08:2025 – Software and Data Integrity Failures |
| Exploitation Prerequisites | Local Process Access (self-hosted runner 多 job 并发或 PR 触发的恶意 job) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Local Process Access) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | ScanResultFile |
| Related Threats | [T11.T](2-stride-analysis.md#scanresultfile) |

#### Description

SecOptionScanScript 在 `analyze_single`/`compute_summary` 后通过 `json.dump` 写入 ScanResultFile；SecOptionDetector 在 `_readResult` 中 `fs.readFileSync` 后 `JSON.parse`。两个步骤之间存在 TOCTOU 窗口：若 attacker 在同一 runner 上有 Local Process Access（如 self-hosted runner 多 job 并发、或 PR 触发的恶意 job），可在 Python 写完后、Node 读前替换文件，注入伪造扫描结果（如把 `bindNow` 从 NO 改为 YES）→ 上报到 OpenLibingAPIG 的数据被篡改。

#### Evidence

**Prerequisite basis:** ScanResultFile 是文件系统数据存储，按 Component Exposure Table 的 Min Prerequisite 为 Local Process Access (T2)；AV:L + AC:H 因需精确时序窗口。

- `dist/bin/sec_option_scan.py:943` `with open(output_file, 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)` — Python 写入
- `dist/detectors/SecOptionDetector.js:125-126` `const content = fs.readFileSync(outputFile, 'utf8'); const result = JSON.parse(content);` — Node 读取，无签名校验
- 两步之间无原子替换、无签名校验、无文件锁

#### Remediation

Python 写入时附带文件签名（如 HMAC-SHA256(file_content, runner_secret)）写入 `_signature` 字段；Node 读取后校验签名；或用 `fs.openSync` 加 `O_EXCL` 写入临时文件再 `rename` 原子替换；runner 层面禁止多 job 并发共享工作区。

#### Verification

在 self-hosted runner 上构造并发 job A 写入正常结果、job B 在 TOCTOU 窗口替换文件，确认 SecOptionDetector 校验签名失败并 fail；正常单 job 场景确认扫描结果读取成功。

---

### FIND-08: OIDC `callApig` 调用未显式设置超时，STS endpoint 不可达时 action 长时间挂起

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 3.7 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L) |
| CWE | [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption |
| OWASP | A10:2025 – Mishandling of Exceptional Conditions |
| Exploitation Prerequisites | Authenticated User (触发 OIDC 模式上报) + Internal Network (STS endpoint 不可达) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User 触发 OIDC 模式) |
| Remediation Effort | Low |
| Mitigation Type | Custom Mitigation |
| Component | CicdUploader |
| Related Threats | [T05.D](2-stride-analysis.md#cicduploader), [T08.D](2-stride-analysis.md#huaweicloudoidc) |

#### Description

OIDC 模式 `await callApig('POST', url, headers, body)` 未显式设置超时，依赖 SDK 默认值；若 HuaweiCloudOIDC 端点 hang（如 TCP 连接建立但无响应），action 会卡在 await 直到 SDK 默认超时（可能数分钟），占用 runner 工作线程；axios path 有 `timeout: 30000`，但 OIDC path 不走 axios。STS endpoint（`sts.cn-southwest-2.huaweicloud.com` 等，SDK 内部决定）不可达时，OIDC 模式下 action 无法切换到 AK/SK 兜底（凭证未传），workflow 失败；攻击者无需直接攻击 OIDC，self-hosted runner 网络抖动即可触发。

#### Evidence

**Prerequisite basis:** CicdUploader 无 inbound 监听器，attack surface 是 OIDC 上报路径；按 Component Exposure Table，HuaweiCloudOIDC 与 CicdUploader 触发的 Min Prerequisite 均为 Authenticated User (T2)。

- `dist/uploaders/CicdUploader.js:305` `const res = await callApig('POST', url, { 'Content-Type': 'application/json' }, body);` — 无 timeout 参数
- `dist/uploaders/CicdUploader.js:328` `const response = await axios.post(url, body, { headers, timeout: this.timeout });` — axios path 有 timeout，OIDC path 无
- `package.json:16` `"@openlibing/huaweicloud-oidc-client": "0.0.5"` — 第三方 SDK 行为依赖审计

#### Remediation

用 `Promise.race([callApig(...), timeout(30000)])` 包装；超时后 `return { success:false, error:'OIDC call timeout' }`；或读 SDK 文档确认 `callApig` 是否接受 `timeout` 选项并传入；在 OIDC 失败时若 workflow 也提供了 `apig-app-key`/`apig-app-secret`，自动降级到 AK/SK 模式重试一次。

#### Verification

构造 STS endpoint 不可达场景（hosts 指向无响应 IP），确认 30s 内 OIDC 调用超时返回明确错误而非数分钟挂起；配置 AK/SK 凭证 + OIDC 失败场景，确认自动降级到 AK/SK 模式上报成功。

---

### FIND-10: APIG 网关不可用时 Action 直接 setFailed，无重试与降级策略

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 3.7 (CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L) |
| CWE | [CWE-754](https://cwe.mitre.org/data/definitions/754.html): Improper Check for Unusual or Exceptional Conditions |
| OWASP | A10:2025 – Mishandling of Exceptional Conditions |
| Exploitation Prerequisites | Authenticated User (触发上报) + APIG 持续不可用 (区域故障/限流 429/实例重启) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Authenticated User 触发上报) |
| Remediation Effort | Low |
| Mitigation Type | Custom Mitigation |
| Component | OpenLibingAPIG |
| Related Threats | [T07.D](2-stride-analysis.md#openlibingapig) |

#### Description

APIG 网关不可用（华为云区域故障、限流 429、APIG 实例重启）会让 OIDC/AK-SK 上报均失败；SecOptionScanner 的 catch 块会再次尝试 upload 兜底，但若 APIG 持续不可用，action 会以 `core.setFailed` 终止，workflow job 失败；攻击者无法直接攻击 APIG，但可通过触发大量 PR（每个 PR 触发一次扫描+上报）放大 APIG 负载。

#### Evidence

**Prerequisite basis:** OpenLibingAPIG 是外部服务，按 Component Exposure Table 的 Min Prerequisite 为 Authenticated User (T2)。

- `dist/index.js:54413-54415` `} catch (error) { core.setFailed(\`Action failed with error: ${error.message}\`); }` — 上报失败导致 setFailed
- `dist/uploaders/CicdUploader.js:330-344` catch 块直接 return `{ success: false, error: ... }`，无重试逻辑
- `dist/scanner.js:111-129` catch 块再次尝试 upload 兜底，但兜底上传也失败时仅 `logger.error` 后 throw

#### Remediation

在 CicdUploader 内对 429/503 做指数退避重试（最多 3 次，间隔 2/4/8 秒）；上报失败但扫描成功时不应 `core.setFailed`，改为 `core.warning` 让 workflow 继续；区分扫描失败与上报失败两类错误码。

#### Verification

构造 APIG 持续返回 503 场景，确认 CicdUploader 重试 3 次后才失败；上报失败但扫描成功的场景，确认 Action 以 `core.warning` 而非 `core.setFailed` 终止，workflow job 不失败。

---

### FIND-13: ScanResultFile 默认权限 0644，self-hosted runner 多租户场景存在信息泄露

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 3.1 (CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N) |
| CWE | [CWE-732](https://cwe.mitre.org/data/definitions/732.html): Incorrect Permission Assignment for Critical Resource |
| OWASP | A05:2025 – Security Misconfiguration |
| Exploitation Prerequisites | Local Process Access (self-hosted 或共享 runner 上其他 tenant/运维可读该文件) |
| Exploitability Tier | Tier 2 — Conditional Risk (single prerequisite: Local Process Access) |
| Remediation Effort | Low |
| Mitigation Type | Standard Mitigation |
| Component | ScanResultFile |
| Related Threats | [T11.I](2-stride-analysis.md#scanresultfile), [T10.I](2-stride-analysis.md#workspaceartifacts) |

#### Description

ScanResultFile 包含 `filePath`（绝对路径）、`options` 各项 YES/NO 计数、`summary.averageRate`；`fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf8')` 未显式设置文件权限（默认 umask，Linux 通常 0644 = world-readable）；在 self-hosted 或共享 runner 上，其他 tenant 或运维可读该文件，泄露扫描结果与文件路径。

#### Evidence

**Prerequisite basis:** ScanResultFile 是文件系统数据存储，按 Component Exposure Table 的 Min Prerequisite 为 Local Process Access (T2)。

- `dist/scanner.js:79` `fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf8');` — 未指定 mode
- `dist/detectors/SecOptionDetector.js:41` `fs.writeFileSync(outputFile, JSON.stringify(emptyResult, null, 2), 'utf8');` — 同样未指定 mode
- `dist/bin/sec_option_scan.py:943` `with open(output_file, 'w', encoding='utf-8') as f: json.dump(result, f, ensure_ascii=False, indent=2)` — Python 端默认 umask

#### Remediation

`fs.writeFileSync` 第三参数加 `{ mode: 0o600 }` 显式设置仅 owner 可读写；Python 端 `json.dump` 后 `os.chmod(output_path, 0o600)`。

#### Verification

在 Linux runner 上扫描完成后 `ls -la sec-option-result.json` 确认权限为 `-rw-------`（0600）而非 `-rw-r--r--`（0644）。

---

## Tier 3 — Defense-in-Depth (Prior Compromise / Host Access)

### FIND-22: `pyelftools` 依赖未锁定版本，存在 PyPI 供应链投毒风险

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Moderate |
| CVSS 4.0 | 5.0 (CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:H/VI:H/VA:H) |
| CWE | [CWE-494](https://cwe.mitre.org/data/definitions/494.html): Download of Code Without Integrity Verification |
| OWASP | A03:2025 – Software Supply Chain Failures |
| Exploitation Prerequisites | Host/OS Access + PyPI Compromise (攻陷上游 pyelftools 维护者账号或 PyPI 服务) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (multiple prerequisites joined with +) |
| Remediation Effort | Medium |
| Mitigation Type | Standard Mitigation |
| Component | PyPIMirror |
| Related Threats | [T09.A](2-stride-analysis.md#pypimirror) |

#### Description

`pyelftools` 包名是合法包，但供应链攻击者若短暂攻陷上游 `pyelftools` PyPI 包（如维护者账号被钓鱼、PyPI 服务被攻陷、CI 投毒），可发布含恶意 setup.py 的 0.0.x 版本；ActionEntryPoint 不锁定版本（`pip install pyelftools` 取最新），会立即中招；类似 event-stream 投毒事件。setup.py 在安装时执行任意 Python 代码 → 完全控制 runner 进程。

#### Evidence

**Prerequisite basis:** PyPIMirror 是外部服务无认证，按 Component Exposure Table 在 LOCALHOST_DESKTOP 下 Min Prerequisite 被强制提升到 Internal Network (T2)；但供应链投毒需 PyPI 服务端被攻陷（多 prerequisite），故为 Tier 3。

- `dist/index.js:54288-54292` `pipInstallArgs = ['-m', 'pip', 'install', '--break-system-packages', 'pyelftools', ...]` — 不指定版本，取最新
- `package.json:16` `"@openlibing/huaweicloud-oidc-client": "0.0.5"` — npm 依赖锁定版本，但 pip 依赖未锁定

#### Remediation

在 `pip install` 中固定版本（`pyelftools==0.31`）+ `--require-hashes` 锁定 SHA256；将 pyelftools 源码 vendoring 到 dist 中（无需运行时安装）；定期 audit pyelftools 上游发布历史；增加 PyPI 包下载完整性校验（比对已知哈希）。

#### Verification

`pip install` 命令包含 `==0.31` 版本固定与 `--require-hashes` 标志；`pip freeze` 显示 pyelftools 版本固定；`pip install --dry-run` 在哈希不匹配时报错。

---

### FIND-21: 第三方 OIDC SDK error 路径可能泄露 ID Token，未做依赖审计

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 3.1 (CVSS:4.0/AV:L/AC:L/AT:N/PR:H/UI:N/VC:H/VI:N/VA:N) |
| CWE | [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File |
| OWASP | A09:2025 – Security Logging and Monitoring Failures |
| Exploitation Prerequisites | Host/OS Access (runner 进程被攻陷或 SDK 行为异常) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (single prerequisite: Host/OS Access) |
| Remediation Effort | Medium |
| Mitigation Type | Standard Mitigation |
| Component | HuaweiCloudOIDC |
| Related Threats | [T08.I](2-stride-analysis.md#huaweicloudoidc) |

#### Description

OIDC ID Token 是敏感凭证（证明 workflow 身份与 repo scope），由 SDK 持有并发送给 STS；若 SDK 在 error path 中把 token 写入 error.message 或 error.config.headers，CicdUploader 的 catch 块 `console.error(\`Upload error: ${error.code || error.message}, URL: ${url}\`)` 会把 token 打印到 CI 日志；SDK 是 `@openlibing/huaweicloud-oidc-client@0.0.5` 第三方代码，行为需审计。

#### Evidence

**Prerequisite basis:** HuaweiCloudOIDC 是外部 STS 服务，按 Component Exposure Table 的 Min Prerequisite 为 Authenticated User (T2)；但 SDK error 路径泄露 token 需 runner 进程被攻陷或 SDK 本身有缺陷（Host/OS Access），故为 Tier 3。

- `package.json:16` `"@openlibing/huaweicloud-oidc-client": "0.0.5"` — 第三方 SDK，行为依赖审计
- `dist/uploaders/CicdUploader.js:305` `const res = await callApig('POST', url, headers, body);` — 调用 SDK，error 路径未明确处理
- `dist/uploaders/CicdUploader.js:339` `console.error(\`Upload error: ${error.code || error.message}, URL: ${url}\`)` — 直接打印 error.message

#### Remediation

对 `@openlibing/huaweicloud-oidc-client` SDK 做依赖审计（npm audit + 源码审查），确认 error 路径不泄漏 token；在 CicdUploader catch 中对 `error.message` 做关键词过滤（`Bearer `、`eyJ` JWT 前缀）；定期升级 SDK 版本并跟踪 changelog。

#### Verification

执行 `npm audit @openlibing/huaweicloud-oidc-client` 确认无已知漏洞；审查 SDK 源码确认 error 路径不引用 token；CI 日志中 `grep -E "(Bearer|eyJ)"` 无 JWT 残留。

---

### FIND-20: APIG 端点硬编码在客户端，跨仓扫描结果集中上报存在单点情报收集风险

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 2.7 (CVSS:4.0/AV:L/AC:L/AT:N/PR:H/UI:N/VC:H/VI:N/VA:N) |
| CWE | [CWE-1357](https://cwe.mitre.org/data/definitions/1357.html): Reliance on Insufficiently Trustworthy Component |
| OWASP | A03:2025 – Software Supply Chain Failures |
| Exploitation Prerequisites | OpenLibingAPIG Compromise (APIG 配置被恶意修改路由到 fake upstream) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (single prerequisite: OpenLibingAPIG Compromise) |
| Remediation Effort | High |
| Mitigation Type | Redesign |
| Component | OpenLibingAPIG |
| Related Threats | [T07.A](2-stride-analysis.md#openlibingapig) |

#### Description

APIG endpoint 硬编码在客户端，所有仓库的所有 workflow 都上报到同一后端；若该 endpoint 被短暂攻陷（如供应链攻击华为云 APIG 服务、APIG 配置被恶意修改路由到 fake upstream），攻击者可批量收集各仓扫描结果（含文件路径、产物名、构建元数据），形成跨仓情报。

#### Evidence

**Prerequisite basis:** OpenLibingAPIG 是外部 APIG 网关，按 Component Exposure Table 的 Min Prerequisite 为 Authenticated User (T2)；但批量情报收集需 APIG 服务端被攻陷（OpenLibingAPIG Compromise），故为 Tier 3。

- `dist/index.js:54256` `const cicdUrl = 'https://174e1b821a8446f38998a67186ba766e.apic.cn-southwest-2.huaweicloudapis.com';` — 全局硬编码
- `dist/uploaders/CicdUploader.js:300` `const url = this.baseUrl.replace(/\/+$/, '') + (this.useOidc ? OIDC_REPORT_PATH : AKSK_REPORT_PATH);` — 所有仓库上报到同一 endpoint

#### Remediation

客户端对返回的 `recordId` 做格式校验（如必须为数字/UUID），异常时告警；服务端签名响应体（mTLS 或响应签名头）让客户端可验证响应来源；考虑多 region endpoint 配置允许客户端选择就近上报点。

#### Verification

构造返回非数字 recordId 的 APIG 响应，确认客户端检测到异常并告警；启用响应签名后，篡改响应体确认客户端校验签名失败。

---

### FIND-23: `packageName` 输入未做 sanitize，多产物场景下可路径穿越写入工作区外文件

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 2.7 (CVSS:4.0/AV:L/AC:L/AT:N/PR:H/UI:N/VC:N/VI:H/VA:N) |
| CWE | [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Improper Limitation of a Pathname to a Restricted Directory |
| OWASP | A01:2025 – Broken Access Control |
| Exploitation Prerequisites | Host/OS Access + Authenticated User (PR 作者让 build step 产出含路径的产物名) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (multiple prerequisites joined with +) |
| Remediation Effort | Low |
| Mitigation Type | Custom Mitigation |
| Component | ScanResultFile |
| Related Threats | [T11.A](2-stride-analysis.md#scanresultfile) |

#### Description

多产物场景下 SecOptionScanner 为每个产物写 `sec-option-result-<packageName>.json`，`packageName` 来自 workflow input 或 `path.basename(resolvedArtifact)`；若 PR 作者让 build step 产出文件名为 `../../etc/cron.d/x.json` 这类含路径的产物名，则 `path.join(path.dirname(outputFile), \`sec-option-result-${target.packageName || i}.json\`)` 会写到工作区外（路径穿越写入）。

#### Evidence

**Prerequisite basis:** ScanResultFile 是文件系统数据存储，按 Component Exposure Table 的 Min Prerequisite 为 Local Process Access (T2)；但路径穿越写入工作区外需 Host/OS Access（self-hosted runner 持久化目录可被覆盖）+ Authenticated User（PR 作者控制 packageName），故为 Tier 3。

- `dist/index.js:54365` `const targetOutput = scanTargets.length > 1 ? path.join(path.dirname(outputFile), \`sec-option-result-${target.packageName || i}.json\`) : outputFile;`
- `dist/index.js:54316` `packageName: packageName || path.basename(resolvedArtifact),` — packageName 来自 workflow input 或 basename，未做 sanitize

#### Remediation

在 SecOptionScanner 中对 `target.packageName` 做 sanitize：剥离路径分隔符（`path.basename(target.packageName)`）、限制字符集（`/^[a-zA-Z0-9_.-]+$/`）；写文件前校验最终路径必须位于 `outputDir` 子树内。

#### Verification

提交 `packageName: ../../etc/cron.d/x` 的 workflow input，确认 SecOptionScanner sanitize 后实际输出路径仍位于 `outputDir` 子树内；正常 packageName（如 `app-1.0.tar.gz`）确认输出文件名为 `sec-option-result-app-1.0.tar.gz.json`。

---

### FIND-18: `_entry_path_unsafe` 未拒绝 NUL 字节与 Unicode 等价字符，存在归档路径校验绕过风险

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 2.5 (CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:L/VI:H/VA:N) |
| CWE | [CWE-182](https://cwe.mitre.org/data/definitions/182.html): Unsafe Decompression of a Compressed Archive |
| OWASP | A08:2025 – Software and Data Integrity Failures |
| Exploitation Prerequisites | Host/OS Access + Authenticated User (PR 作者构造含 Unicode 等价字符的归档) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (multiple prerequisites joined with +) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | SecOptionScanScript |
| Related Threats | [T04.T](2-stride-analysis.md#secoptionscanscript) |

#### Description

`_entry_path_unsafe` 校验绝对路径（`/`）、Windows 盘符（`name[1]==':'`）、`..` 段；但未显式拒绝 NUL 字节（`\x00`）与 Unicode 等价字符（如全角 `．．`、RTL 覆盖符 U+202E）。Python 3.6.2+ 的 zipfile 会 reject NUL，但 tarfile 与 ar 解析（`_extract_deb`）路径处理依赖 `os.path.join`，对边缘编码可能产生未预期路径。`_safe_extract_tar` 对 symlink linkname 校验 `_entry_path_unsafe`，但相对 symlink（如 `linkname = "../etc/passwd"`）已被覆盖；绝对 symlink 也被覆盖。剩余风险：构造 member.name 看似安全但 linkname 走 Unicode 规范化绕过。

#### Evidence

**Prerequisite basis:** SecOptionScanScript 无 inbound 监听器，attack surface 是归档条目路径；按 Component Exposure Table，PRContributor 的 Min Prerequisite 为 Authenticated User (T2)；但绕过 Unicode 等价字符需 PR 作者构造特殊归档 + runner 路径解析存在边缘 case（Host/OS Access 验证路径解析行为），故为 Tier 3。

- `dist/bin/sec_option_scan.py:173-187` `_entry_path_unsafe(name)`：仅校验 `name.startswith('/')`、`name[1]==':'`、`'..' in name.split('/')`
- `dist/bin/sec_option_scan.py:205-220` `_safe_extract_tar` 对 member.name 与 member.linkname 调用 `_entry_path_unsafe`

#### Remediation

在 `_entry_path_unsafe` 中追加：拒绝包含 `\x00` 的路径、对 name 做 `unicodedata.normalize('NFKC', name)` 后再校验（防全角/兼容等价字符绕过）；记录跳过条目数到审计日志。

#### Verification

构造含全角 `．．` 与 NUL 字节的归档条目，确认 `_entry_path_unsafe` 返回 True 并跳过；构造 Unicode RTL 覆盖符（U+202E）的 linkname，确认规范化后被识别为 `..`。

---

### FIND-19: ApigSigner HMAC 签名无 nonce/jti，存在签名重放风险

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 2.5 (CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:L/VI:L/VA:N) |
| CWE | [CWE-294](https://cwe.mitre.org/data/definitions/294.html): Authentication Bypass by Capture-replay |
| OWASP | A07:2025 – Identification and Authentication Failures |
| Exploitation Prerequisites | Host/OS Access + Authenticated User (截获合法签名请求) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (multiple prerequisites joined with +) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | ApigSigner |
| Related Threats | [T06.T](2-stride-analysis.md#apigsigner) |

#### Description

HMAC 签名包含 `X-Sdk-Date` 时间戳与 body SHA256，但无 nonce/jti；攻击者截获一个合法签名的 POST 请求（如通过 CI 日志泄露、网络抓包、APIG 服务端日志泄露），可在 APIG 时间容忍窗口内（通常 15 分钟）重放到 `/openlibing-cicd/build-artifact/sec-option/report`，伪造一次扫描结果上报。

#### Evidence

**Prerequisite basis:** ApigSigner 无 inbound 监听器，attack surface 是签名请求；按 Component Exposure Table，ApigSigner 的 Min Prerequisite 为 Host/OS Access (T3)；截获签名请求需 Host/OS Access + Authenticated User（触发合法签名请求）。

- `dist/uploaders/CicdUploader.js:60-63` `let datetime = ...; if (!datetime) { datetime = this._getDateTime(); headers['X-Sdk-Date'] = datetime; }` — 仅时间戳，无 nonce
- `dist/uploaders/CicdUploader.js:131-134` `const signature = this._hmacSha256Hex(this.sk, stringToSign); headers['Authorization'] = \`SDK-HMAC-SHA256 Access=${this.ak}, SignedHeaders=${signedHeadersStr}, Signature=${signature}\`;`

#### Remediation

在签名中追加 nonce（随机 16 字节 hex）并要求 APIG 服务端基于 `(ak, nonce)` 去重；或在 body 中嵌入 `pipelineRunId + runNumber + currentTime` 组合做幂等键。

#### Verification

构造两次相同 body 与时间的签名请求，确认 nonce 不同；APIG 服务端记录 nonce 后，重放第二次请求时返回 409 Conflict。

---

### FIND-15: Runner 环境变量可欺骗 OIDC 模式判定与 pipeline 元数据上报

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 2.0 (CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:L/VI:L/VA:L) |
| CWE | [CWE-349](https://cwe.mitre.org/data/definitions/349.html): Acceptance of Extraneous Untrusted Data with Untrusted Data Speculation |
| OWASP | A07:2025 – Identification and Authentication Failures |
| Exploitation Prerequisites | Host/OS Access (控制 runner 环境变量) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (single prerequisite: Host/OS Access) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | ActionEntryPoint |
| Related Threats | [T01.S](2-stride-analysis.md#actionentrypoint), [T05.A](2-stride-analysis.md#cicduploader), [T08.S](2-stride-analysis.md#huaweicloudoidc) |

#### Description

攻击者通过控制 runner 环境变量（`ACTIONS_ID_TOKEN_REQUEST_URL`、`ATOMGIT_RUN_ID`、`ATOMGIT_WORKFLOW` 等）欺骗 action 走 OIDC 模式或伪造 pipeline 元数据上报。`useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL` 仅检查 env 是否存在，不校验来源；若 runner 环境变量被错误配置（如 base 仓未声明 `permissions: id-token: write` 但 runner 仍注入了 ACTIONS_ID_TOKEN_REQUEST_URL，反之亦然），action 会走错认证模式与错上报接口 → 上报失败或认证错位。`ACTIONS_ID_TOKEN_REQUEST_URL` 由 runner 注入，SDK 据此向 runner 的 ID Token mint 服务发起请求；若 runner 进程被攻陷，攻击者可设置该 env 指向自己的 fake ID Token 服务。

#### Evidence

**Prerequisite basis:** ActionEntryPoint/CicdUploader/HuaweiCloudOIDC 均无 inbound 监听器；按 Component Exposure Table，三者的 Min Prerequisite 为 Host/OS Access (T3) 或 Authenticated User (T2 for external)；env 变量欺骗需 Host/OS Access（控制 runner 进程环境）。

- `dist/index.js:54260` `const useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL;` — 仅检查 env 是否存在
- `dist/index.js:54253` `const pipelineName = process.env['ATOMGIT_WORKFLOW'] || '';`
- `dist/index.js:54277-54278` `const pipelineRunId = process.env['ATOMGIT_RUN_ID'] || ''; const runNumber = process.env['ATOMGIT_RUN_NUMBER'] || '';`
- `dist/uploaders/CicdUploader.js:252` `this.useOidc = !!config.useOidc;` — 直接来自 env 判定结果

#### Remediation

对 `ATOMGIT_*` 关键元数据在 payload 中加签名校验或要求 OIDC token 内嵌 sub claims 与之匹配；在 ActionEntryPoint 增加 `permissions` 显式校验：若 `ATOMGIT_*` 上下文显示 workflow 声明了 `id-token: write` 但 `ACTIONS_ID_TOKEN_REQUEST_URL` 不存在（或反之），提前 fail 并提示配置不一致；客户端对 `ACTIONS_ID_TOKEN_REQUEST_URL` 做白名单校验（仅接受 runner 平台已知域名后缀）。

#### Verification

设置 `ACTIONS_ID_TOKEN_REQUEST_URL` 但 workflow 未声明 `id-token: write`，确认 Action 检测到配置不一致并 fail；篡改 `ATOMGIT_RUN_ID` 为非数字格式，确认 payload 校验失败。

---

### FIND-16: 缺少 invocation 审计日志，事后无法追溯扫描输入与上报来源

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 2.0 (CVSS:4.0/AV:L/AC:L/AT:N/PR:H/UI:N/VC:N/VI:N/VA:N) |
| CWE | [CWE-778](https://cwe.mitre.org/data/definitions/778.html): Insufficient Logging |
| OWASP | A09:2025 – Security Logging and Monitoring Failures |
| Exploitation Prerequisites | Host/OS Access (事后追溯需求方) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (single prerequisite: Host/OS Access) |
| Remediation Effort | Medium |
| Mitigation Type | Custom Mitigation |
| Component | ActionEntryPoint |
| Related Threats | [T01.R](2-stride-analysis.md#actionentrypoint), [T02.R](2-stride-analysis.md#secoptionscanner), [T10.R](2-stride-analysis.md#workspaceartifacts) |

#### Description

ActionEntryPoint 仅通过 `core.info` 输出执行轨迹，未记录 inputs 哈希、调用方身份、scan 选项到不可篡改的审计日志；事后无法证明某次扫描的输入与触发方。SecOptionScanner 未记录每次 `scan()`/`upload()` 调用的输入摘要与结果 recordId，事后无法追溯某次上报的来源。WorkspaceArtifacts 是文件落盘到 runner 工作区，无来源签名；无法事后证明某 .so 文件是哪个 commit/PR build 步骤产出的（build step 代码可被 PR 修改）。

#### Evidence

**Prerequisite basis:** ActionEntryPoint/SecOptionScanner 无 inbound 监听器；按 Component Exposure Table，二者的 Min Prerequisite 为 Host/OS Access (T3)。

- `dist/index.js:54343-54346` `core.info(\`gitUrl: ${gitUrl || '(empty)'}\`); core.info(\`pipelineName: ${pipelineName || '(empty)'}\`); core.info(\`pipelineRunId: ${pipelineRunId || '(empty)'}\`); core.info(\`scanOptions: ${scanOptions.length > 0 ? scanOptions.join(',') : '(all 14)'}\`);` — 仅 info 级日志，无审计落盘
- `dist/scanner.js:97-102` `if (uploadResult.success) { this.logger.info(\`Successfully uploaded sec-option report, recordId: ${uploadResult.recordId}\`); result.uploadInfo = { success: true, recordId: uploadResult.recordId }; }` — 仅内存中保留 recordId

#### Remediation

在 scan result JSON 中写入 `invocationContext: { event, actor, runId, inputsSha256 }` 字段并上报到 OpenLibingAPIG 留痕；至少本地落盘一份 invocation audit log；在 build step 完成后写入 `_artifact_provenance.json`（记录 commit SHA、build time、source hash），ActionEntryPoint 扫描时附带 provenance 上报。

#### Verification

扫描完成后确认 `sec-option-result.json` 中包含 `invocationContext` 字段；OpenLibingAPIG 服务端落库的 payload 中含 `inputsSha256` 与 `provenance`；本地 audit log 文件包含完整的 invocation 上下文。

---

### FIND-17: `scan-options` workflow input 接受任意 key 可触发 Python `sys.exit(1)` 中断扫描

| Attribute | Value |
|-----------|-------|
| SDL Bugbar Severity | Low |
| CVSS 4.0 | 1.8 (CVSS:4.0/AV:L/AC:L/AT:N/PR:H/UI:N/VC:N/VI:L/VA:N) |
| CWE | [CWE-20](https://cwe.mitre.org/data/definitions/20.html): Improper Input Validation |
| OWASP | A03:2025 – Software Supply Chain Failures |
| Exploitation Prerequisites | Host/OS Access (PR 作者修改 master YAML 中的 scan-options 值) |
| Exploitability Tier | Tier 3 — Defense-in-Depth (single prerequisite: Host/OS Access — 修改 master YAML 需仓库写权限) |
| Remediation Effort | Low |
| Mitigation Type | Custom Mitigation |
| Component | SecOptionDetector |
| Related Threats | [T03.A](2-stride-analysis.md#secoptiondetector) |

#### Description

`args.push(scanOptions.join(','))` 把 scanOptions 字符串数组拼成 CLI 第 3 参数；Python 端 `analyze_single` 会 `sys.exit(1)` 退出。攻击者若能影响 `scan-options` workflow input（如通过 PR 修改 master YAML），可传入非法 key 触发非零退出 → action 失败。

#### Evidence

**Prerequisite basis:** SecOptionDetector 无 inbound 监听器；按 Component Exposure Table，SecOptionDetector 的 Min Prerequisite 为 Host/OS Access (T3)；修改 master YAML 需仓库写权限（Privileged User），但 ActionEntryPoint 已有 ALL_OPTION_KEYS 列表可用于校验，未实施即视为 Host/OS Access 暴露面。

- `dist/detectors/SecOptionDetector.js:71-74` `const args = [this.scriptPath, sourceDir, outputFile]; if (scanOptions && scanOptions.length > 0) { args.push(scanOptions.join(',')); }` — 直接拼接，无 key 校验
- `dist/index.js:54281-54284` `const scanOptions = scanOptionsRaw.split(',').map(s => s.trim()).filter(s => s.length > 0);` — 仅过滤空白项，不校验 key 合法性
- `dist/index.js:54350-54351` `const ALL_OPTION_KEYS = ['bindNow', 'nx', 'pic', ...];` — 已有合法 key 列表但未用于校验

#### Remediation

在 JS 端先用 `scanOptions.filter(k => ALL_OPTION_KEYS.includes(k))` 过滤非法 key（ActionEntryPoint 已有 ALL_OPTION_KEYS 列表），非法 key 仅 warn 不退出；Python 端对未知 key 跳过而非 sys.exit(1)。

#### Verification

提交 `scan-options: invalidKey,bindNow` 的 workflow input，确认 Action 仅 warn 未知 key 但仍扫描 bindNow；Python 端对未知 key 跳过而非 sys.exit(1)。

---

## Threat Coverage Verification

| Threat ID | Finding ID | Status |
|-----------|------------|--------|
| T01.T | FIND-01 | ✅ Covered (FIND-01) |
| T01.I | FIND-02 | ✅ Covered (FIND-02) |
| T01.D | FIND-03 | ✅ Covered (FIND-03) |
| T01.A | FIND-04 | ✅ Covered (FIND-04) |
| T01.S | FIND-15 | ✅ Covered (FIND-15) |
| T01.R | FIND-16 | ✅ Covered (FIND-16) |
| T02.I | FIND-05 | ✅ Covered (FIND-05) |
| T02.A | FIND-04 | ✅ Covered (FIND-04) |
| T02.R | FIND-16 | ✅ Covered (FIND-16) |
| T03.T | FIND-06 | ✅ Covered (FIND-06) |
| T03.D | FIND-03 | ✅ Covered (FIND-03) |
| T03.A | FIND-17 | ✅ Covered (FIND-17) |
| T04.I | FIND-05 | ✅ Covered (FIND-05) |
| T04.D | FIND-03 | ✅ Covered (FIND-03) |
| T04.A | FIND-07 | ✅ Covered (FIND-07) |
| T04.T | FIND-18 | ✅ Covered (FIND-18) |
| T05.I | FIND-02 | ✅ Covered (FIND-02) |
| T05.D | FIND-08 | ✅ Covered (FIND-08) |
| T05.A | FIND-15 | ✅ Covered (FIND-15) |
| T06.I | FIND-02 | ✅ Covered (FIND-02) |
| T06.T | FIND-19 | ✅ Covered (FIND-19) |
| T07.S | FIND-09 | ✅ Covered (FIND-09) |
| T07.I | FIND-09 | ✅ Covered (FIND-09) |
| T07.D | FIND-10 | ✅ Covered (FIND-10) |
| T07.A | FIND-20 | ✅ Covered (FIND-20) |
| T08.D | FIND-08 | ✅ Covered (FIND-08) |
| T08.S | FIND-15 | ✅ Covered (FIND-15) |
| T08.I | FIND-21 | ✅ Covered (FIND-21) |
| T09.S | FIND-11 | ✅ Covered (FIND-11) |
| T09.D | FIND-11 | ✅ Covered (FIND-11) |
| T09.A | FIND-22 | ✅ Covered (FIND-22) |
| T10.T | FIND-14 | ✅ Covered (FIND-14) |
| T10.I | FIND-05 | ✅ Covered (FIND-05) |
| T10.D | FIND-03 | ✅ Covered (FIND-03) |
| T10.R | FIND-16 | ✅ Covered (FIND-16) |
| T11.T | FIND-12 | ✅ Covered (FIND-12) |
| T11.I | FIND-13 | ✅ Covered (FIND-13) |
| T11.A | FIND-23 | ✅ Covered (FIND-23) |
