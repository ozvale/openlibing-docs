# STRIDE + Abuse Cases — Threat Analysis

> This analysis uses the standard **STRIDE** methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) extended with **Abuse Cases** (business logic abuse, workflow manipulation, feature misuse). The "A" column in tables below represents Abuse — a supplementary category covering threats where legitimate features are misused for unintended purposes. This is distinct from Elevation of Privilege (E), which covers authorization bypass.

## Exploitability Tiers

Threats are classified into three exploitability tiers based on the prerequisites an attacker needs:

| Tier       | Label            | Prerequisites                                                                                                                 | Assignment Rule                                                                                                |
| ---------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Tier 1** | Direct Exposure  | `None`                                                                                                                        | Exploitable by unauthenticated external attacker with NO prior access. The prerequisite field MUST say `None`. |
| **Tier 2** | Conditional Risk | Single prerequisite: `Authenticated User`, `Privileged User`, `Internal Network`, or single `{Boundary} Access`               | Requires exactly ONE form of access. The prerequisite field has ONE item.                                      |
| **Tier 3** | Defense-in-Depth | `Host/OS Access`, `Admin Credentials`, `{Component} Compromise`, `Physical Access`, or MULTIPLE prerequisites joined with `+` | Requires significant prior breach, infrastructure access, or multiple combined prerequisites.                  |

## Summary

| Component             | Link                           | S     | T      | R     | I      | D      | E      | A      | Total  | T1    | T2     | T3     | Risk   |
| --------------------- | ------------------------------ | ----- | ------ | ----- | ------ | ------ | ------ | ------ | ------ | ----- | ------ | ------ | ------ |
| CodeMetricsAction     | [Link](#codemetricsaction)     | 0     | 1      | 1     | 1      | 1      | 1      | 1      | 6      | 0     | 5      | 1      | Medium |
| MetricsScanner        | [Link](#metricsscanner)        | 0     | 0      | 1     | 1      | 1      | 0      | 0      | 3      | 0     | 3      | 0      | Low    |
| SlocDetector          | [Link](#slocdetector)          | 1     | 1      | 0     | 1      | 1      | 1      | 1      | 6      | 0     | 4      | 2      | Medium |
| LizardDetector        | [Link](#lizarddetector)        | 1     | 1      | 0     | 1      | 1      | 1      | 1      | 6      | 0     | 5      | 1      | Medium |
| DuplicationDetector   | [Link](#duplicationdetector)   | 0     | 0      | 0     | 1      | 1      | 0      | 1      | 3      | 0     | 3      | 0      | Low    |
| ConfigLoader          | [Link](#configloader)          | 0     | 1      | 0     | 0      | 1      | 1      | 0      | 3      | 0     | 3      | 0      | Low    |
| FileCollector         | [Link](#filecollector)         | 0     | 1      | 0     | 1      | 1      | 0      | 0      | 3      | 0     | 3      | 0      | Low    |
| CoderepoUploader      | [Link](#coderepouploader)      | 0     | 1      | 1     | 1      | 1      | 1      | 1      | 6      | 0     | 5      | 1      | High   |
| ApigSigner            | [Link](#apigsigner)            | 0     | 1      | 0     | 1      | 1      | 1      | 1      | 5      | 0     | 4      | 1      | Medium |
| WorkspaceRepo         | [Link](#workspacerepo)         | 0     | 0      | 0     | 1      | 1      | 0      | 1      | 3      | 0     | 3      | 0      | Medium |
| MetricsOutputFile     | [Link](#metricsoutputfile)     | 0     | 1      | 0     | 1      | 1      | 0      | 1      | 4      | 0     | 4      | 0      | Low    |
| TempFiles             | [Link](#tempfiles)             | 0     | 1      | 0     | 1      | 1      | 0      | 1      | 4      | 0     | 4      | 0      | Low    |
| OBS                   | [Link](#obs)                   | 1     | 1      | 0     | 1      | 0      | 1      | 1      | 5      | 0     | 4      | 1      | Medium |
| APIG                  | [Link](#apig)                  | 1     | 1      | 0     | 1      | 0      | 1      | 1      | 5      | 0     | 3      | 2      | Medium |
| HuaweiCloudOIDC       | [Link](#huaweicloudoidc)       | 1     | 1      | 0     | 1      | 0      | 1      | 1      | 5      | 0     | 2      | 3      | High   |
| ObsutilDownloadMirror | [Link](#obsutildownloadmirror) | 1     | 1      | 0     | 1      | 1      | 0      | 1      | 5      | 2     | 3      | 0      | Medium |
| PyPIMirror            | [Link](#pypimirror)            | 1     | 1      | 0     | 1      | 1      | 1      | 1      | 6      | 2     | 4      | 0      | High   |
| **Totals**            |                                | **7** | **14** | **3** | **16** | **14** | **10** | **14** | **78** | **4** | **62** | **12** |        |

---

## CodeMetricsAction

**Trust Boundary:** GitCode Runner
**Role:** Action 入口 `run()`，读取 env/inputs、调用 git/python3、构造 config 启动扫描（`dist/index.js:62337-62519`）
**Data Flows:** DF01, DF02, DF03, DF04, DF05, DF06
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER deployment classification forbids T1 — runner 是 GitCode 平台调度的 ephemeral 容器，外部攻击者需先经 GitCode 认证并具备提交代码/配置 workflow 权限才能影响此组件的执行。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                    | Prerequisites      | Affected Flow                                                                                                                                | Mitigation                                                                                                                     | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------ |
| T01.T | Tampering              | `getInput()` 同时支持连字符与下划线形式的 `INPUT_<NAME>` 环境变量（`dist/index.js:62331-62334`），CI 平台 env 块若允许 PR 评论/分支名注入环境变量，恶意用户可构造 `INPUT_APIG_APP_KEY` 覆盖 secret 输入                                   | Authenticated User | DF01                                                                                                                                         | 对安全相关输入（apig-app-key/secret、obs-ak/sk）显式校验来源 workflow 是否信任；或要求 secrets 仅经 `secrets.*` 注入而非裸 env | Open   |
| T01.R | Repudiation            | scan 失败时仅 `core.warning` 输出（`dist/index.js:62394, 62406, 62410`），无结构化审计日志留痕，事后无法追溯是谁触发了失败/异常                                                                                                           | Authenticated User | DF06                                                                                                                                         | 增加 audit log 上报到独立端点（含 pipelineRunId + commitId + 失败原因），与 metrics 上报解耦                                   | Open   |
| T01.I | Information Disclosure | `core.info` 输出 `gitUrl/branchName/pipelineRunId/commitId` 到控制台日志（`dist/index.js:62483-62486`），若 gitUrl 含 token（已被 `dist/index.js:62399` 清洗），但 commitId 可关联到具体开发者身份，被恶意 workflow step 读取后做行为追踪 | Authenticated User | DF06                                                                                                                                         | 仅输出脱敏后的 pipelineRunId，commitId 与 gitUrl 移至 debug 级别（verbose=true 才输出）                                        | Open   |
| T01.D | Denial of Service      | `pip install --break-system-packages lizard` 120s 超时（`dist/index.js:62474`）+ `stdio:'inherit'` 阻塞输出，恶意构造的 PyPI 镜像响应慢或返回超长包可耗尽 runner 资源                                                                     | Authenticated User | DF05                                                                                                                                         | 改用 `execFileSync` + `--no-input` + `--require-hashes`；timeout 降低到 60s；失败时不阻断扫描（已部分实现，line 62476-62478）  | Open   |
| T01.A | Abuse                  | `pipelineRunId = process.env['ATOMGIT_RUN_ID']                                                                                                                                                                                            |                    | process.env['PIPELINE_RUN_ID']`（`dist/index.js:62420`），用户可设置 `PIPELINE_RUN_ID` 环境变量覆盖真正的运行 ID，导致上报数据归属错误流水线 | Authenticated User                                                                                                             | DF02   | 优先用 runner 注入的 ATOMGIT_RUN_ID；若必须支持 PIPELINE_RUN_ID fallback，加白名单校验或允许 workflow 关闭 fallback | Open |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                            | Prerequisites  | Affected Flow | Mitigation                                                                                                               | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------ | ------ |
| T01.E | Elevation of Privilege | `useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL`（`dist/index.js:62363`）仅靠 env var 存在性判定，攻击者控制 runner env（如恶意 self-hosted runner 配置）可注入伪造 URL，使插件走 OIDC 路径调用攻击者控制的"OIDC provider"换取伪造 STS 凭证 | Host/OS Access | DF02, DF20    | 校验 `ACTIONS_ID_TOKEN_REQUEST_URL` 必须以 `https://` 开头且 host 属于 GitCode 平台白名单；OIDC SDK 内部应做 issuer 验证 | Open   |

#### Categories Not Applicable

| Category | Justification                                                                                           |
| -------- | ------------------------------------------------------------------------------------------------------- |
| Spoofing | CodeMetricsAction 是 runner 进程内的入口模块，无监听端口、不接受外部身份凭证，spoofing surface 不适用。 |

## MetricsScanner

**Trust Boundary:** GitCode Runner
**Role:** 扫描编排器，调度三 detector + calculator + uploader（`dist/scanner.js:25-227`）
**Data Flows:** DF06, DF07, DF08, DF09, DF10, DF11
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署，无外部攻击面。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                               | Prerequisites      | Affected Flow | Mitigation                                                                                                                     | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------ |
| T02.R | Repudiation            | catch 块（`dist/scanner.js:197-225`）失败时仅 logger.error + 重发 upload，logger 是 winston console transport，无审计落盘                                                                                                            | Authenticated User | DF10, DF11    | 失败兜底 upload 时附带 `errorMessage` 已实现（line 217）；增加结构化 errorReport 字段含 stack 头部 12 行（line 201）但未持久化 | Open   |
| T02.I | Information Disclosure | `logger.info` 输出 `Local output size approx: ${JSON.stringify(compactResult).length} bytes`（`dist/scanner.js:170`）+ `Result scale: fileDetails=..., snapshotDataTotal=... bytes`（line 137），泄露文件规模信息                    | Authenticated User | DF11          | 文件规模非敏感，但应避免在 verbose=false 时输出，减少日志噪音                                                                  | Open   |
| T02.D | Denial of Service      | 超大代码库 + 高重复率可触发 `JSON.stringify(compactResult)` 超 V8 单字符串上限（`Invalid string length`），代码已部分缓解（line 144-167 剥离 snapshotData + clipOversizeContent 15KB），但 compactResult 仍含全量 fileDetails 可触顶 | Authenticated User | DF11          | 对 fileDetails 也做分批裁剪或流式写入；监控 JSON.stringify 异常并降级为分片写文件                                              | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. MetricsScanner 是进程内编排器，无独立基础设施访问，无多重 prerequisite 触发的威胁。_

#### Categories Not Applicable

| Category               | Justification                                                                                   |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| Spoofing               | 进程内编排器，无身份验证表面。                                                                  |
| Tampering              | scanner.js 内部状态由各 detector 返回值填充，外部攻击者无法直接篡改（需先经 detector 攻击面）。 |
| Elevation of Privilege | 不做授权决策，权限由调用方（CodeMetricsAction）决定。                                           |
| Abuse                  | scanner.js 行为是固定编排流程，无业务逻辑可被滥用。                                             |

## SlocDetector

**Trust Boundary:** GitCode Runner
**Role:** 调用内置 scc 二进制统计代码行（`dist/detectors/SlocDetector.js`）
**Data Flows:** DF07, DF12
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署，scc 二进制由插件打包，无外部监听。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                             | Prerequisites      | Affected Flow | Mitigation                                                                                                 | Status |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ---------------------------------------------------------------------------------------------------------- | ------ |
| T03.S | Spoofing               | `getSccPath()` 探测顺序含 `path.join(__dirname, 'bin', 'scc')` 等多个候选（`dist/detectors/SlocDetector.js:22-28`），若 runner 工作区被恶意 checkout 注入同名 `scc` 二进制到 `__dirname` 上溯目录，可优先被选中执行                | Authenticated User | DF12          | 严格使用 `path.join(bundleRoot, 'bin', 'scc')` 单一来源；候选路径不包含上溯目录                            | Open   |
| T03.T | Tampering              | `runScc()` 用 `const cmd = '"${this.sccPath}" ${args.join(" ")}'` + `execSync(cmd)` 字符串拼接（`dist/detectors/SlocDetector.js:111-118`），若 `this.sccPath` 或 `sources` 路径含 shell 元字符（`$(...)`、`; rm`），可触发命令注入 | Authenticated User | DF12          | 改用 `execFileSync(this.sccPath, args, ...)` 参数数组，不经 shell；sources 路径用 `fs.realpathSync` 归一化 | Open   |
| T03.I | Information Disclosure | `console.log` 输出 scc 命令行 + 文件路径（`dist/detectors/SlocDetector.js:40, 158, 192`），恶意构造的 filePath 含敏感路径（如 `/etc/secrets/...`）可进日志                                                                         | Authenticated User | DF12          | 文件路径仅输出相对于扫描根的相对路径，不输出绝对路径                                                       | Open   |
| T03.D | Denial of Service      | `execSync` `maxBuffer: 100 * 1024 * 1024` + `timeout: 300000`（`dist/detectors/SlocDetector.js:114-117`），恶意构造超多文件触发 scc 输出超 100MB 可抛错（已 catch 回退到逐文件统计，但 fallback 仍遍历全部文件）                   | Authenticated User | DF12          | 增加文件总数硬上限（如 100k）；超过时拒绝扫描并提示用户拆分仓库                                            | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                            | Prerequisites                                | Affected Flow | Mitigation                                                                                 | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------ | ------ |
| T03.E | Elevation of Privilege | 内置 scc 二进制 `dist/bin/scc` 在 Linux 上首次运行 `fs.chmodSync(candidate, 0o755)`（`dist/detectors/SlocDetector.js:33-38`），若 dist 打包过程被入侵（供应链攻击）注入恶意 scc，可获 runner 进程权限执行任意代码 | CoderepoUploader Compromise + Host/OS Access | DF12          | 对 scc 二进制做 SBOM 校验或哈希签名；CI 构建时记录 sha256 并在运行时验证                   | Open   |
| T03.A | Abuse                  | `toRelativePath()`（`dist/detectors/SlocDetector.js:259-271`）用 `sources` 做前缀剥除，恶意构造 `sources=[ '/tmp' ]` 可让绝对路径前缀匹配 `/tmp/secret.txt` 被剥成 `secret.txt` 上报，绕过"工作区相对路径"语义    | Host/OS Access                               | DF12          | 限定 sources 必须在 workspace 范围内（`path.resolve(this.workingDir, src)`）后再做前缀剥除 | Open   |

#### Categories Not Applicable

| Category    | Justification                                                              |
| ----------- | -------------------------------------------------------------------------- |
| Repudiation | scc 执行结果直接进 slocResult，由 MetricsCalculator 处理，无独立审计需求。 |

## LizardDetector

**Trust Boundary:** GitCode Runner
**Role:** 调用 python3 -m lizard 计算函数复杂度（`dist/detectors/LizardDetector.js`）
**Data Flows:** DF08, DF13, DF14
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                                            | Prerequisites      | Affected Flow | Mitigation                                                                                                                               | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T04.S | Spoofing               | `tempJsonFile = './lizard_output.json'` 默认写到工作区根（`dist/detectors/LizardDetector.js:11`），恶意仓库可预置同名文件， lizard 输出会被代码先 `unlinkSync` 删除（line 81-83）但恶意预置文件仍可在 `runLizard` 失败时被读取（line 124-135 兜底解析）                                                                                                           | Authenticated User | DF13, DF14    | tempJsonFile 改写到 `os.tmpdir()`（与 `writeInputFile` 一致，line 71-73），避免工作区污染                                                | Open   |
| T04.T | Tampering              | `execSync('python3 -m lizard ' + args.join(' '))` 字符串拼接（`dist/detectors/LizardDetector.js:89`），args 由 `tempInputPath` 与 `tempJsonPath` 组成；`tempInputPath = path.join(os.tmpdir(), 'lizard_input_${Date.now()}.txt')`，若攻击者控制 `TMPDIR` env var，可注入含 shell 元字符的路径                                                                     | Authenticated User | DF13          | 改用 `execFileSync('python3', ['-m', 'lizard', '-f', tempInputPath, '-o', tempJsonPath], ...)` 参数数组；校验 `os.tmpdir()` 不含特殊字符 | Open   |
| T04.I | Information Disclosure | `parseTextOutput` 用正则 `^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+?)@(\d+)-(\d+)@(.+)$`（`dist/detectors/LizardDetector.js:155`），捕获组 9 是 `filePath`，恶意 lizard 输出可让 `filePath` 指向敏感文件，触发 `fs.readFileSync(filePath, 'utf8')`（line 168）读取后存入 `functions[].filename`，最终经 `aggregateFileDetails` 进 metrics.json 与 OBS 上报 | Authenticated User | DF13          | 校验 `filePath` 必须在 `sources`/workspace 范围内，否则跳过该函数；或对 lizard 输出做来源签名校验                                        | Open   |
| T04.D | Denial of Service      | `execSync` `maxBuffer: 50 * 1024 * 1024` + `timeout: 300000`（`dist/detectors/LizardDetector.js:90-93`），恶意仓库含超多函数（如生成代码模板）可触发 lizard 输出超 50MB                                                                                                                                                                                           | Authenticated User | DF13          | 文件分批喂给 lizard（每批 N 个文件）；或监控输出大小，超阈值降级采样                                                                     | Open   |
| T04.E | Elevation of Privilege | `runLizard` 内的 `fs.readFileSync(filePath, 'utf8')` + `fs.readFileSync(func.filename, 'utf8')`（`dist/detectors/LizardDetector.js:168, 269`）允许读取 runner 进程可读的任意文件，恶意 lizard 输出可让 `func.filename = '/etc/passwd'` 被读取后内容进入 `calculateBodyNloc` 计算流程（虽最终不直接写入 metrics，但内容被读入内存可能被后续异常日志泄露）          | Authenticated User | DF13          | 同 T04.I 缓解：校验 `func.filename` 必须在 workspace 范围内                                                                              | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                           | Prerequisites  | Affected Flow | Mitigation                                                                                                         | Status |
| ----- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------ | ------ |
| T04.A | Abuse    | `pip install lizard` 在 `CodeMetricsAction` 中执行 `--break-system-packages`（`dist/index.js:62468`）系统级安装，若 runner 上其他 workflow step 也用 python3，会被污染为本次安装的 lizard 版本，影响后续步骤行为 | Host/OS Access | DF13          | 改用 venv 隔离（`python3 -m venv /tmp/lizard-venv && source /tmp/lizard-venv/bin/activate && pip install lizard`） | Open   |

#### Categories Not Applicable

| Category    | Justification                                    |
| ----------- | ------------------------------------------------ |
| Repudiation | lizard 输出直接进 lizardResult，无独立审计需求。 |

## DuplicationDetector

**Trust Boundary:** GitCode Runner
**Role:** 进程内逐文件读取做跨文件行级匹配（`dist/detectors/DuplicationDetector.js`）
**Data Flows:** DF09, DF15
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                       | Prerequisites                                                                                                                  | Affected Flow      | Mitigation                                                                                                                                                                            | Status                                                                                          |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| T05.I | Information Disclosure | `fs.readFileSync(file, 'utf8')` 读取全部源文件内容（`dist/detectors/DuplicationDetector.js:82`），`buildContextSegments` 构建重复块 ±5 行上下文片段（snapshotData）含明文代码，最终经 CoderepoUploader.encodeOccurrences Base64 编码后上报到 OBS（私有对象） | Authenticated User                                                                                                             | DF15               | 已通过 Base64 编码 + OBS 私有对象缓解；但若被扫描仓库源码含密钥/PII，密钥会经此链路上报。建议上游 gitleaks/detect-private-key 钩子拦截；可选：snapshotData 上报前对疑似密钥做正则遮蔽 | Open                                                                                            |
| T05.D | Denial of Service      | 跨文件 union-find 滑动窗口匹配（`detectWithLineLevel`）算法复杂度可能 O(n²) 或更高（n=文件总行数），恶意构造超多重复块可触发 CPU 耗尽                                                                                                                        | Authenticated User                                                                                                             | DF15               | 增加单文件最大行数硬上限（如 100k 行）；超限时跳过该文件的重复检测并 warning                                                                                                          | Open                                                                                            |
| T05.A | Abuse                  | `buildObjectKey` 用 `ownerRepo` 拼 objectKey（`dist/uploaders/CoderepoUploader.js:475-480`），但 `extractOwnerRepo` 用正则 `(?:git@[^:]+:                                                                                                                    | https?://[^/]+/)(.+)$`（line 490）提取，恶意 `gitUrl`含`../` 可让 ownerRepo 含路径穿越段，使 objectKey 写到其他 owner 的目录下 | Authenticated User | DF09                                                                                                                                                                                  | `extractOwnerRepo` 对结果做 `replace(/\\.\\./g, '')` 与 `/` 计数限制；或后端按 owner 鉴权后下载 | Open |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 进程内计算，无外部基础设施访问。_

#### Categories Not Applicable

| Category               | Justification                                                         |
| ---------------------- | --------------------------------------------------------------------- |
| Spoofing               | 进程内检测器，无身份验证表面。                                        |
| Tampering              | 内部状态由 fs.readFileSync 读取，恶意文件内容影响结果但不篡改二进制。 |
| Repudiation            | 输出由 MetricsCalculator 处理，无独立审计需求。                       |
| Elevation of Privilege | 不做授权决策。                                                        |

## ConfigLoader

**Trust Boundary:** GitCode Runner
**Role:** 加载并合并 YAML/JSON config-file（`dist/config/loader.js`）
**Data Flows:** DF03
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                       | Prerequisites      | Affected Flow | Mitigation                                                                                                       | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ------------- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| T06.T | Tampering              | `yaml.load(fileContent)` 使用 `js-yaml ^4.1.0`（`dist/config/loader.js:46`），默认 SAFE_SCHEMA 不支持 `!!js/function` 等不安全类型；但若用户 config-file 含恶意 YAML 锚点/别名循环引用可触发栈溢出                                                           | Authenticated User | DF03          | 升级到 js-yaml 最新版；或对 config-file 大小限制（如 < 1MB）；加载时设置 `schema: yaml.DEFAULT_SAFE_SCHEMA` 显式 | Open   |
| T06.D | Denial of Service      | 超大 config 文件可耗尽 runner 内存（无 max size 限制）                                                                                                                                                                                                       | Authenticated User | DF03          | 加载前 `fs.statSync` 校验文件大小（如 < 1MB），超限拒绝                                                          | Open   |
| T06.E | Elevation of Privilege | `mergeConfig` 递归合并（`dist/config/loader.js:62-85`），用户可在 config-file 中覆盖 `detectors.duplication.enabled=false` 或 `uploader.coderepoUrl` 等安全相关字段（虽然 `dist/index.js:62450-62461` 中 coderepoUrl 硬编码会覆盖，但 enabled 字段可被关闭） | Authenticated User | DF03          | 对安全相关字段（enabled、url、credentials）做白名单合并；或加载后校验关键字段未被 userConfig 修改                | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 静态配置加载器。_

#### Categories Not Applicable

| Category               | Justification                                            |
| ---------------------- | -------------------------------------------------------- |
| Spoofing               | 不接受身份凭证。                                         |
| Repudiation            | 配置加载失败已 console.warn（line 55），无独立审计需求。 |
| Information Disclosure | 配置文件内容不输出到日志。                               |
| Abuse                  | 无业务逻辑可被滥用。                                     |

## FileCollector

**Trust Boundary:** GitCode Runner
**Role:** 按 exclude-dirs/allowed-extensions 递归遍历工作区（`dist/utils/fileCollector.js`）
**Data Flows:** DF16
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                         | Prerequisites      | Affected Flow | Mitigation                                                             | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ---------------------------------------------------------------------- | ------ |
| T07.T | Tampering              | `globToRegExp(glob)` 将用户 exclude-dirs 模式转为正则（`dist/utils/fileCollector.js:127-180`），恶意构造的 glob 模式（如 `(a+)+` 等回溯模式）可触发 ReDoS，导致 _walkDir 阻塞                                  | Authenticated User | DF16          | 用 `safe-regex` 库预校验 glob 转换后的正则；或对单次 _walkDir 设硬超时 | Open   |
| T07.I | Information Disclosure | `console.warn('[WARN] 路径不存在: ${absolutePath}')` 与 `console.warn('[WARN] 文件扩展名不在允许列表中: ${absolutePath}')`（`dist/utils/fileCollector.js:199, 219`）输出绝对路径，可能泄露 runner 文件系统结构 | Authenticated User | DF16          | 输出相对路径（相对 `this.workingDir`）而非绝对路径                     | Open   |
| T07.D | Denial of Service      | 超深目录递归（如恶意构造 1000 层嵌套目录）可触发栈溢出；`_walkDir` 递归调用无深度限制                                                                                                                          | Authenticated User | DF16          | 增加 maxDepth 参数（如 32），超限跳过子目录                            | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 静态工具类。_

#### Categories Not Applicable

| Category               | Justification                                  |
| ---------------------- | ---------------------------------------------- |
| Spoofing               | 不接受身份凭证。                               |
| Repudiation            | 输出文件列表供 detector 使用，无独立审计需求。 |
| Elevation of Privilege | 不做授权决策。                                 |
| Abuse                  | 行为是固定遍历逻辑，无业务可滥用。             |

## CoderepoUploader

**Trust Boundary:** GitCode Runner
**Role:** OBS 上传 + APIG /report 调用，OIDC/AK-SK 双模式（`dist/uploaders/CoderepoUploader.js`）
**Data Flows:** DF10, DF17, DF18, DF19, DF20, DF22
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署，runner 是平台调度。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                                                                                                                                               | Prerequisites      | Affected Flow | Mitigation                                                                                                   | Status |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ------------------------------------------------------------------------------------------------------------ | ------ |
| T08.T | Tampering              | `ensureObsutil()` 用 `execSync('wget -q "${downloadUrl}" -O "${tarball}" 2>/dev/null \|\| curl -sL "${downloadUrl}" -o "${tarball}"', { shell: '/bin/bash' })`（`dist/uploaders/CoderepoUploader.js:446-450`），downloadUrl 硬编码但 `tarball`/`extractedDir` 含 `os.tmpdir()` 路径，若 `TMPDIR` 被攻击者控制为含 shell 元字符的路径，可触发命令注入 | Authenticated User | DF22          | 改用 `execFileSync('wget', ['-q', downloadUrl, '-O', tarball])` 参数数组；或用 Node.js 内置 `https.get` 下载 | Open   |
| T08.R | Repudiation            | `report()` 失败时 `console.error('Upload error: ${error.code \|\| error.message}, URL: ${url}')`（`dist/uploaders/CoderepoUploader.js:657`）输出到 stdout，无结构化审计                                                                                                                                                                              | Authenticated User | DF19          | 增加结构化 errorReport 上报（含 pipelineRunId + commitId + 失败原因 + 时间戳）到独立端点                     | Open   |
| T08.I | Information Disclosure | `console.log('[upload] exec obsutil ${maskedArgs.join(" ")}')`（`dist/uploaders/CoderepoUploader.js:425`）输出命令行，`-k=***`/`-t=***` 已脱敏；但 `-i=STS_AK`/`-i=OBS_AK` 未脱敏，accessKeyId（临时或永久 AK）会进日志                                                                                                                              | Authenticated User | DF18          | 对 `-i=` 也做脱敏（只显示前 4 位 + `***`）；或完全不输出 obsutil 命令行，仅输出 obsutil version + 结果       | Open   |
| T08.D | Denial of Service      | `execFileSync(obsutil, args, { stdio: 'inherit' })`（`dist/uploaders/CoderepoUploader.js:426`）无 timeout，OBS 端响应慢或网络故障可无限阻塞                                                                                                                                                                                                          | Authenticated User | DF18          | 增加 `timeout: 60000`（60s）；超时后清理 tmpFile 并返回失败                                                  | Open   |
| T08.A | Abuse                  | `buildObjectKey` 用 `extractOwnerRepo(options.gitUrl)` 拼 objectKey（`dist/uploaders/CoderepoUploader.js:475-480`），恶意 `gitUrl` 含 `../` 可让 ownerRepo 路径穿越，使 OBS objectKey 写到其他 owner 的目录下；后端按 objectKey 下载解析时可能读到攻击者构造的恶意数据                                                                               | Authenticated User | DF10, DF18    | `extractOwnerRepo` 校验 ownerRepo 不含 `..`、`//` 等；或后端按 owner 鉴权后下载                              | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                                                 | Prerequisites  | Affected Flow | Mitigation                                                                       | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- | ------------- | -------------------------------------------------------------------------------- | ------ |
| T08.E | Elevation of Privilege | AK/SK 模式下 `ApigSigner(this.apigAppKey, this.apigAppSecret)`（`dist/uploaders/CoderepoUploader.js:627`），若 SK 泄露（如日志、tmp 文件、git 历史），攻击者可伪造签名直接调用 `/openlibing-coderepo/metrics/code/report` 上报伪造数据（覆盖真实指标） | Host/OS Access | DF19, DF21    | 强制 OIDC 模式（deprecate AK/SK）；或对 AK/SK 做 IP 白名单限制；监控异常上报来源 | Open   |

#### Categories Not Applicable

| Category | Justification                                       |
| -------- | --------------------------------------------------- |
| Spoofing | CoderepoUploader 是出站调用方，不接受外部身份凭证。 |

## ApigSigner

**Trust Boundary:** GitCode Runner
**Role:** SDK-HMAC-SHA256 签名构造（`dist/uploaders/CoderepoUploader.js:20-248` 内嵌类）
**Data Flows:** DF21
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. CI_RUNNER 部署。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                               | Prerequisites      | Affected Flow | Mitigation                                                                                                                                                     | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| T09.T | Tampering              | `sign()` 解析 URL（`new URL(url)`，`dist/uploaders/CoderepoUploader.js:32`）+ 解码 query string（line 38-54），恶意构造的 URL 含超长 query 或特殊字符可触发 `decodeURIComponent` 异常或 `URIError`（line 224），导致签名失败         | Authenticated User | DF21          | 对 URL 长度做上限校验（如 < 8KB）；decodeURIComponent 用 try/catch 包裹（line 224 已有但仅 throw）                                                             | Open   |
| T09.I | Information Disclosure | `headers['Authorization'] = 'SDK-HMAC-SHA256 Access=${this.ak}, SignedHeaders=..., Signature=...'`（`dist/uploaders/CoderepoUploader.js:138`），ak（access key ID）明文进 Authorization 头；若调用方将 headers 输出到日志，ak 会泄露 | Authenticated User | DF21          | 调用方（CoderepoUploader.report）已用 axios 不输出 headers；但 console.error 输出 URL（line 619, 657）不含 headers，OK。建议在 sign() 内部对调试日志做 ak 脱敏 | Open   |
| T09.D | Denial of Service      | `_canonicalUri`/`_canonicalQueryString`/`_urlEncode` 均为字符串处理（`dist/uploaders/CoderepoUploader.js:147-233`），超长 URL 或超多 query 参数可触发 CPU 耗尽                                                                       | Authenticated User | DF21          | 对 URL 长度与 query 参数数量做上限校验                                                                                                                         | Open   |
| T09.E | Elevation of Privilege | `ApigSigner` 构造函数不校验 ak/sk 非空（`dist/uploaders/CoderepoUploader.js:21-24`），若调用方传入空字符串，sign() 会输出 `Access=, SignedHeaders=..., Signature=...`，可能被 APIG 当作匿名请求处理（取决于网关配置）                | Authenticated User | DF21          | 构造函数校验 `if (!ak \|\| !sk) throw new Error('ApigSigner requires ak/sk')`；CoderepoUploader.report 已有 AK/SK 模式校验（line 624-626）                     | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category | Threat                                                                                                                                                                                                | Prerequisites  | Affected Flow | Mitigation                                                                           | Status |
| ----- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------- | ------------------------------------------------------------------------------------ | ------ |
| T09.A | Abuse    | `_canonicalUri(uri)` 末尾强制补 `/`（`dist/uploaders/CoderepoUploader.js:153-156`），与官方 SDK 行为对齐；但若某些 APIG 路由对末尾 `/` 敏感（如重定向到不同 handler），可被构造的 path 触发非预期路由 | Host/OS Access | DF21          | 仅用于已知 APIG 路由（/metrics/code/report），路由列表白名单；非白名单 path 拒绝签名 | Open   |

#### Categories Not Applicable

| Category    | Justification                                                       |
| ----------- | ------------------------------------------------------------------- |
| Spoofing    | 签名器是辅助类，不做身份验证决策。                                  |
| Repudiation | 签名包含 X-Sdk-Date 时间戳，本身具备防重放审计能力（APIG 侧校验）。 |

## WorkspaceRepo

**Trust Boundary:** GitCode Runner
**Role:** runner 工作区被扫描的仓库内容（不可信源码 + .git 元数据）
**Data Flows:** DF04, DF12, DF13, DF15, DF16
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. WorkspaceRepo 在 runner 进程内访问，外部攻击者需先经 GitCode 认证并提交 PR 才能 influence 内容。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                       | Prerequisites      | Affected Flow          | Mitigation                                                                                                                | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ---------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------ |
| T10.I | Information Disclosure | WorkspaceRepo 含被扫描仓库的所有源码（含可能的密钥/PII），经 SlocDetector/LizardDetector/DuplicationDetector 读取后，fileDetails 与 duplicationOccurrences 内容会进 metrics.json 与 OBS 上传 | Authenticated User | DF12, DF13, DF15       | 上游 gitleaks + detect-private-key 钩子已配置（`.pre-commit-config.yaml`）；可选：上报前对 fileDetails 内容做密钥正则遮蔽 | Open   |
| T10.D | Denial of Service      | 恶意构造超多文件（如 1M 个空文件）或超大文件可耗尽 runner 资源（磁盘/内存/CPU）                                                                                                              | Authenticated User | DF12, DF13, DF15, DF16 | 增加文件总数与单文件大小硬上限；超限拒绝扫描                                                                              | Open   |
| T10.A | Abuse                  | 攻击者构造高重复率文件（如 1000 个 10 行相同代码块）可触发上报链路大数据量，虽 OBS 中转缓解了 APIG 12MB 限制，但 OBS 上传成本与后端入库压力可被滥用                                          | Authenticated User | DF15                   | 对 duplicationOccurrences 数量做上限（如 1000）；超限时裁剪并 warning                                                     | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 静态文件系统数据存储。_

#### Categories Not Applicable

| Category               | Justification                                                                   |
| ---------------------- | ------------------------------------------------------------------------------- |
| Spoofing               | 静态文件系统无身份验证表面。                                                    |
| Tampering              | 文件内容由 git 管理，runner 内进程间无篡改威胁（git 元数据完整性由 git 保证）。 |
| Repudiation            | git log 自带审计能力。                                                          |
| Elevation of Privilege | 不做授权决策。                                                                  |

## MetricsOutputFile

**Trust Boundary:** GitCode Runner
**Role:** 本地 metrics.json 输出文件（`output` 参数指定）
**Data Flows:** DF11
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. 文件系统数据存储，runner 进程内访问。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                               | Prerequisites        | Affected Flow | Mitigation                                                                                  | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------- | ------------- | ------------------------------------------------------------------------------------------- | ------ |
| T11.T | Tampering              | `output` 参数可被构造为任意路径（如 `/etc/cron.d/malicious`），`FileUtils.writeJsonFile` 会 `fs.mkdirSync(dir, { recursive: true })`（`dist/utils/fileUtils.js:7-9`）创建目录并写入文件，可能覆盖 runner 上其他 workflow step 的输出 | Local Process Access | DF11          | 校验 `output` 路径必须在 `${workspace}/` 范围内；默认值 `metrics.json` 已是相对路径         | Open   |
| T11.I | Information Disclosure | metrics.json 内容含 fileDetails（filePath + 行数 + 复杂度 + 重复率）+ duplicationOccurrences 元数据（groupId/startLine/endLine/content 裁剪后），不含完整源码但仍泄露仓库结构                                                        | Local Process Access | DF11          | 默认 output 写到 workspace 内的私有路径；或对敏感字段（如 filePath）做相对路径化            | Open   |
| T11.D | Denial of Service      | 超大 metrics.json 可触发 V8 Invalid string length（已通过 `clipOversizeContent` 15KB 裁剪 duplicationOccurrences 缓解，`dist/scanner.js:158-166`），但 fileDetails 列表本身可超长                                                    | Local Process Access | DF11          | 对 fileDetails 也做分批或裁剪；或用流式写入（`fs.createWriteStream` + JSON.stringify 替代） | Open   |
| T11.A | Abuse                  | `output` 路径可被构造为 runner 上其他 workflow step 的输入文件（如 `.gitcode/workflows/pre-commit.yml` 引用的文件），覆盖之影响后续 step 行为                                                                                        | Local Process Access | DF11          | 同 T11.T：校验 output 路径必须在 workspace 子目录内                                         | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 静态文件系统数据存储。_

#### Categories Not Applicable

| Category               | Justification            |
| ---------------------- | ------------------------ |
| Spoofing               | 静态文件无身份验证表面。 |
| Repudiation            | 文件写入即审计痕迹。     |
| Elevation of Privilege | 不做授权决策。           |

## TempFiles

**Trust Boundary:** GitCode Runner
**Role:** `os.tmpdir()` 临时文件（lizard I/O、上报全量 payload、obsutil 解压）
**Data Flows:** DF14, DF17
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. 临时目录在 runner 进程内访问。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                                         | Prerequisites        | Affected Flow | Mitigation                                                                                                       | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------- | ------ |
| T12.T | Tampering              | `os.tmpdir()` 共享给 runner 上所有 workflow step（`/tmp`），恶意 step 可预置 `code-metrics-*.json` 或 `lizard_input_*.txt` 文件污染下一次运行（race condition）                                                                | Local Process Access | DF14, DF17    | tmp 文件用 `mkstemp` 或 `fs.mkdtempSync` 创建独占目录；文件名加随机后缀（已用 `Date.now()`，但 ms 粒度可被预测） | Open   |
| T12.I | Information Disclosure | tmp 全量 payload 文件含 fileDetails 全量明细 + duplicationOccurrences 明文 content（已 Base64 编码，但解码即明文），若 `fs.unlinkSync` 清理失败（`dist/uploaders/CoderepoUploader.js:380-384` 已 try/catch），可残留到下次运行 | Local Process Access | DF17          | unlink 失败时 warning；上传完成后立即清理；可选：tmp 文件用 0600 权限创建                                        | Open   |
| T12.D | Denial of Service      | tmpdir 空间可被恶意 workflow step 耗尽（写满 /tmp），导致 tmp 文件写入失败                                                                                                                                                     | Local Process Access | DF14, DF17    | 写入前检查 `fs.statSync(os.tmpdir())` 可用空间；不足时降级到 workspace 内 .tmp 目录                              | Open   |
| T12.A | Abuse                  | `TMPDIR` 环境变量可被恶意 workflow 设置重定向到攻击者控制目录（如 `/home/attacker/tmp`），tmp 文件会写到攻击者可读位置                                                                                                         | Local Process Access | DF14, DF17    | 不信任 `TMPDIR` env var；硬编码使用 `/tmp`（Linux）或 `os.tmpdir()` 默认值                                       | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 临时文件系统数据存储。_

#### Categories Not Applicable

| Category               | Justification                                  |
| ---------------------- | ---------------------------------------------- |
| Spoofing               | 临时文件无身份验证表面。                       |
| Repudiation            | tmp 文件用完即删（`finally` 块），无审计需求。 |
| Elevation of Privilege | 不做授权决策。                                 |

## OBS

**Trust Boundary:** External
**Role:** 华为云对象存储（`obs.cn-southwest-2.myhuaweicloud.com`，桶 `openlibing-gitcode-action`）
**Data Flows:** DF18
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. OBS 端点需凭证（STS 或 AK/SK）才能写入，公开 HTTPS 仅校验证书，无匿名写入路径。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                             | Prerequisites      | Affected Flow | Mitigation                                                                       | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ------------- | -------------------------------------------------------------------------------- | ------ |
| T13.S | Spoofing               | 攻击者控制 DNS 或网络 MitM 可伪造 `obs.cn-southwest-2.myhuaweicloud.com` 端点，接收上传的 payload 数据（含仓库源码片段）                                                                                           | Internal Network   | DF18          | 强制 HTTPS + 证书 pinning（obsutil 已支持）；或对 OBS endpoint 做哈希校验        | Open   |
| T13.T | Tampering              | 上传内容若被 MitM 篡改，后端按 objectKey 下载会拿到错误数据（伪造的 metrics）                                                                                                                                      | Internal Network   | DF18          | OBS 服务端校验 ETag/MD5；上传后回读校验 hash                                     | Open   |
| T13.I | Information Disclosure | 私有对象，但 objectKey 含 `ownerRepo/pipelineRunId`（`dist/uploaders/CoderepoUploader.js:475-480`），可被推测；攻击者控制 ownerRepo 可构造 objectKey 路径穿越                                                      | Authenticated User | DF18          | objectKey 不含敏感信息（仅元数据 + 仓库 owner）；后端按 owner 鉴权下载           | Open   |
| T13.A | Abuse                  | `buildObjectKey` 拼 `code-metrics-action/${ownerRepo}/${pipelineRunId}/${ts}-metrics.json`（`dist/uploaders/CoderepoUploader.js:475-480`），攻击者控制 `ownerRepo` 含 `../` 可让 objectKey 写到其他 owner 的目录下 | Authenticated User | DF18          | `extractOwnerRepo` 校验 ownerRepo 不含 `..`、`//`、空段；或后端按 owner 鉴权下载 | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                             | Prerequisites  | Affected Flow | Mitigation                                                           | Status |
| ----- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------- | -------------------------------------------------------------------- | ------ |
| T13.E | Elevation of Privilege | AK/SK 模式下 `obs-ak/obs-sk` 静态凭证（永久有效），若泄露攻击者可任意读写 `openlibing-gitcode-action` 桶（覆盖真实 metrics 或读取其他 owner 数据） | Host/OS Access | DF18          | 强制 OIDC + STS 临时凭证模式；或对 AK/SK 做 IP 白名单；桶级 ACL 限制 | Open   |

#### Categories Not Applicable

| Category          | Justification                                |
| ----------------- | -------------------------------------------- |
| Repudiation       | OBS 侧访问日志属华为云平台，由平台维护审计。 |
| Denial of Service | OBS 服务端有容量与请求限流，非本系统职责。   |

## APIG

**Trust Boundary:** External
**Role:** 华为云 APIG 网关（`174e1b821...apic.cn-southwest-2.huaweicloudapis.com`）
**Data Flows:** DF19
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. APIG 端点需签名（HMAC 或 OIDC）才能调用 /metrics/code/report。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                          | Prerequisites      | Affected Flow | Mitigation                                                 | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ---------------------------------------------------------- | ------ |
| T14.S | Spoofing               | 攻击者控制 DNS 或网络 MitM 可伪造 APIG 端点（coderepoUrl 硬编码在 `dist/index.js:62359`），接收带签名的上报请求（含元数据 + obsUrl）                                            | Internal Network   | DF19          | 强制 HTTPS + 证书 pinning；axios 已校验 TLS 证书           | Open   |
| T14.T | Tampering              | 响应可被 MitM 篡改，但代码已校验 `resData?.code !== 200`（`dist/uploaders/CoderepoUploader.js:639`）；recordId 提取逻辑宽松（line 648-652，多种字段尝试），可能被构造的响应误导 | Internal Network   | DF19          | 严格校验响应 schema；recordId 必须是数字字符串且长度合理   | Open   |
| T14.I | Information Disclosure | 失败响应可能含敏感 error message（`resData?.msg \|\| resData?.message`，`dist/uploaders/CoderepoUploader.js:644, 660`），输出到 `console.error`（line 642, 657）                | Authenticated User | DF19          | 对失败响应做脱敏（不输出原始 msg，仅输出 code 与简短描述） | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                     | Prerequisites              | Affected Flow | Mitigation                                                               | Status |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------------- | ------------------------------------------------------------------------ | ------ |
| T14.E | Elevation of Privilege | AK/SK 模式下 SK 泄露后，攻击者可伪造 SDK-HMAC-SHA256 签名直接调用 `/openlibing-coderepo/metrics/code/report` 上报伪造数据（覆盖真实 metrics 或污染历史趋势）                                               | Host/OS Access             | DF19          | 强制 OIDC 模式；APIG 端配置 IP 白名单；监控异常上报频率与来源            | Open   |
| T14.A | Abuse                  | V11-HMAC-SHA256 签名（OIDC 模式）由 `@openlibing/huaweicloud-oidc-client` SDK 0.0.5 处理（`dist/uploaders/CoderepoUploader.js:3, 613`），若 SDK 实现有缺陷（如重放攻击窗口未限制），可被滥用绕过 APIG 鉴权 | HuaweiCloudOIDC Compromise | DF19, DF20    | 升级 SDK 到最新版；SDK 内部应做 nonce + timestamp 校验；监控异常签名请求 | Open   |

#### Categories Not Applicable

| Category          | Justification                     |
| ----------------- | --------------------------------- |
| Repudiation       | APIG 侧访问日志属华为云平台。     |
| Denial of Service | APIG 服务端有限流，非本系统职责。 |

## HuaweiCloudOIDC

**Trust Boundary:** External
**Role:** 华为云 OIDC 联邦认证端点（由 SDK 通过 `ACTIONS_ID_TOKEN_REQUEST_URL` 调用）
**Data Flows:** DF20
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

_No Tier 1 threats identified for this component. OIDC 端点需 runner 上下文（`ACTIONS_ID_TOKEN_REQUEST_URL` + 平台 token）才能换证。_

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                                           | Prerequisites      | Affected Flow | Mitigation                                                                          | Status |
| ----- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ----------------------------------------------------------------------------------- | ------ |
| T15.T | Tampering              | STS 凭证响应可被 MitM 篡改（替换 accessKeyId/secretAccessKey 为攻击者凭证）                                                                                                                                      | Internal Network   | DF20          | SDK 内部用 HTTPS + 证书校验；STS 凭证使用后立即过期（短时效）                       | Open   |
| T15.I | Information Disclosure | STS 凭证（`cred.accessKeyId/secretAccessKey/securityToken`）经 `-i/-k/-t` 命令行参数传 obsutil（`dist/uploaders/CoderepoUploader.js:418`），可能在 `ps` 输出中可见（CI 平台对 secrets 自动掩码，但本地 ps 可见） | Authenticated User | DF18, DF20    | obsutil 支持 `-i`/`-k`/`-t` 从环境变量读取（避免命令行参数）；或用 obsutil 配置文件 | Open   |

#### Tier 3 — Defense-in-Depth

| ID    | Category               | Threat                                                                                                                                                                                                                          | Prerequisites              | Affected Flow | Mitigation                                                                                                        | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------- | ------ |
| T15.S | Spoofing               | 攻击者控制 runner env（如恶意 self-hosted runner 配置）可注入伪造 `ACTIONS_ID_TOKEN_REQUEST_URL`，使 `callApig`/`getCredentials` 调用攻击者控制的"OIDC provider"，拿到伪造 STS 凭证后写入攻击者控制的 OBS 桶                    | Host/OS Access             | DF20          | 校验 `ACTIONS_ID_TOKEN_REQUEST_URL` 必须以 `https://` 开头且 host 属于 GitCode 平台白名单；SDK 内部做 issuer 验证 | Open   |
| T15.E | Elevation of Privilege | `ACTIONS_ID_TOKEN_REQUEST_URL` 是 runner 注入的 env var（`dist/index.js:62363`），仅靠存在性判定 `useOidc`，恶意 workflow 可声明 `permissions: id-token: write` 但同时注入伪造 URL，使插件走 OIDC 路径调用攻击者控制的 endpoint | Host/OS Access             | DF02, DF20    | 同 T15.S：校验 URL 必须属于 GitCode 平台白名单                                                                    | Open   |
| T15.A | Abuse                  | `@openlibing/huaweicloud-oidc-client` SDK 0.0.5 版本固定（`package.json:15`），未做版本升级与依赖漏洞扫描；若该版本有已知漏洞（如 OIDC nonce 校验缺失），可被滥用绕过认证                                                       | HuaweiCloudOIDC Compromise | DF20          | 升级 SDK 到最新版；接入 dependabot/renovate 做依赖漏洞监控                                                        | Open   |

#### Categories Not Applicable

| Category          | Justification                               |
| ----------------- | ------------------------------------------- |
| Repudiation       | OIDC token 自带 jti + exp，平台侧维护审计。 |
| Denial of Service | OIDC 端点属华为云平台，限流由平台负责。     |

## ObsutilDownloadMirror

**Trust Boundary:** External
**Role:** obsutil 二进制下载源（`obs-community.obs.cn-north-1.myhuaweicloud.com`）
**Data Flows:** DF22
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID    | Category  | Threat                                                                                                                                                 | Prerequisites | Affected Flow | Mitigation                                                                  | Status |
| ----- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------- | ------------- | --------------------------------------------------------------------------- | ------ |
| T16.S | Spoofing  | 公开 HTTPS 下载源，攻击者无认证即可发起请求；若控制 DNS 可伪造端点返回恶意 obsutil 二进制                                                              | None          | DF22          | HTTPS 证书校验已缓解；可选：对下载的 obsutil 做 sha256 校验（已知官方哈希） | Open   |
| T16.T | Tampering | 下载的 tar.gz 可被 MitM 篡改为恶意 obsutil（HTTPS 缓解，但 CA 信任链外风险）；解压后 `chmod 755` + `execFileSync` 执行，恶意二进制可获 runner 进程权限 | None          | DF22          | 对下载文件做 sha256 校验；或改用 OBS SDK（Node.js 内置）替代 obsutil 二进制 | Open   |

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                    | Prerequisites      | Affected Flow | Mitigation                                                                                             | Status |
| ----- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ------------------------------------------------------------------------------------------------------ | ------ |
| T16.I | Information Disclosure | 下载 URL + tarball/extractedDir 路径输出到日志（`dist/uploaders/CoderepoUploader.js:446-450`），泄露 runner 文件系统结构                  | Authenticated User | DF22          | 输出相对路径或脱敏 tmpdir 路径                                                                         | Open   |
| T16.D | Denial of Service      | 下载失败回退系统 obsutil（`dist/uploaders/CoderepoUploader.js:456-466`），若系统 obsutil 不存在则抛错；恶意构造网络抖动可触发下载超时阻塞 | Authenticated User | DF22          | 设置下载 timeout（如 60s）；失败时不阻塞，降级到 OBS SDK 直接上传                                      | Open   |
| T16.A | Abuse                  | `downloadUrl` 硬编码（`dist/uploaders/CoderepoUploader.js:438-439`），用户无法配置；下载的 obsutil 无 SBOM 校验，存在供应链风险           | Authenticated User | DF22          | 改用 OBS Node.js SDK（`@huaweicloud/huaweicloud-obs`）替代外部 obsutil；或对下载的二进制做哈希签名验证 | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 公开镜像源，无基础设施级攻击面。_

#### Categories Not Applicable

| Category               | Justification                      |
| ---------------------- | ---------------------------------- |
| Repudiation            | 下载行为属一次性操作，无审计需求。 |
| Elevation of Privilege | 不做授权决策。                     |

## PyPIMirror

**Trust Boundary:** External
**Role:** Python 包镜像（`mirrors.aliyun.com/pypi/simple/`），用于 `pip install lizard`
**Data Flows:** DF05
**Pod Co-location:** N/A

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

| ID    | Category  | Threat                                                                                                                                                           | Prerequisites | Affected Flow | Mitigation                                                                             | Status |
| ----- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------------- | -------------------------------------------------------------------------------------- | ------ |
| T17.S | Spoofing  | 公开 HTTPS PyPI 镜像，攻击者无认证即可上传 lizard 包（需 mirrors.aliyun.com 账号）；若镜像被入侵可注入恶意 lizard 包                                             | None          | DF05          | pip 已启用 `--trusted-host` 但跳过证书校验（弱化 TLS）；改用官方 PyPI + 不跳过证书校验 | Open   |
| T17.T | Tampering | 下载的 lizard 包可被 MitM 篡改（`--trusted-host mirrors.aliyun.com` 跳过证书校验，`dist/index.js:62470`），恶意 lizard 可执行任意 Python 代码（runner 进程权限） | None          | DF05          | 移除 `--trusted-host`；用 `--require-hashes` + lizard 包哈希白名单；或用 venv 隔离     | Open   |

#### Tier 2 — Conditional Risk

| ID    | Category               | Threat                                                                                                                                                                                      | Prerequisites      | Affected Flow | Mitigation                                                                               | Status |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ------------- | ---------------------------------------------------------------------------------------- | ------ |
| T17.I | Information Disclosure | `pip install` 命令 `stdio: 'inherit'`（`dist/index.js:62474`）输出到控制台，可能泄露包名、版本、下载 URL                                                                                    | Authenticated User | DF05          | 改用 `stdio: 'pipe'` + 仅在失败时输出错误；成功时仅输出简短摘要                          | Open   |
| T17.D | Denial of Service      | `pip install` timeout 120s（`dist/index.js:62474`），恶意镜像响应慢可阻塞；失败时仅 warning（line 62476-62478）不阻断扫描，但 lizard 缺失会导致 LizardDetector 失败                         | Authenticated User | DF05          | timeout 降低到 60s；失败时明确告知用户 lizard 不可用 + 跳过 lizard 检测                  | Open   |
| T17.A | Abuse                  | `--break-system-packages`（`dist/index.js:62468`）系统级安装，污染 runner 上后续 workflow step 的 python3 环境                                                                              | Authenticated User | DF05          | 改用 venv 隔离（`python3 -m venv /tmp/lizard-venv && source ... && pip install lizard`） | Open   |
| T17.E | Elevation of Privilege | `--trusted-host mirrors.aliyun.com` 跳过 TLS 证书校验（`dist/index.js:62470`），网络位置的攻击者可发起 MitM 注入恶意 lizard 包，导致任意代码执行（runner 进程权限，可能进一步访问 secrets） | Internal Network   | DF05          | 移除 `--trusted-host`；用 HTTPS + 证书校验；或对接华为云内部 PyPI 镜像（VPC 内可信）     | Open   |

#### Tier 3 — Defense-in-Depth

_No Tier 3 threats identified for this component. 公开 PyPI 镜像，无基础设施级攻击面。_

#### Categories Not Applicable

| Category    | Justification                              |
| ----------- | ------------------------------------------ |
| Repudiation | pip install 行为属一次性操作，无审计需求。 |
