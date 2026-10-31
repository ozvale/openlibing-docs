# security-compilation-options-action 安全 Issue 批量定性分析（20261022）

定性依据：argus / SenInfo / SENS / 红线落地 / 威胁分析扫描 issue（openlibing/security-compilation-options-action open 安全类 #17-#37，共 18 条；#33 为功能需求，不在整改范围）。
已比对跨仓知识库：`security-non-issue-catalog.md`（非问题判定库）、`security-remediation-playbook.md`（整改方案库）。
整改方案引用 playbook 的类型标注为「playbook: <类型名>」。

**代码基线**：上游 master `f845b04`（package.json version 1.0.2）。

**本仓结构关键事实（影响整改落地方式）**

1. 本仓**无 src 目录**，`dist/` 同时是源码与产物（`git ls-files dist` 直接跟踪）。
2. `npm run package` = `ncc build dist/index.js -o dist`：ncc 以 `dist/index.js` 为入口，把 `dist/scanner.js`、`dist/uploaders/CicdUploader.js`、`dist/detectors/SecOptionDetector.js`、`dist/utils/logger.js` 内联进 `dist/index.js`。
3. **运行时只加载 `dist/index.js` 这一个 bundle**：bundle 内已无 `require('./scanner')` 等引用，兄弟模块文件（scanner.js / uploaders / detectors / utils）是遗留的非运行时副本。
   - 结论：整改必须**同时**改 bundle 与对应兄弟模块副本（bundle 是生效体，兄弟副本是语义一致性载体），否则会出现「改了没效果」或「下次重建被覆盖」的半整改状态。
4. `dist/sec_option_scan.py` 与 `dist/bin/sec_option_scan.py` 当前完全相同（59351 字节，SHA256 `A2FBC4D6…9EF1F32`）。运行时实际加载的是**根副本**：bundle `dist/index.js:22` 被 ncc 改写为 `__nccwpck_require2_.ab + "sec_option_scan.py"`，而 `ab = __dirname + "/"`（`dist/index.js:54275`）→ `dist/sec_option_scan.py`。
5. `dist/bin/` 与两种 Python 副本的来源是老路径约定（`detectors/SecOptionDetector.js:10` 用 `__dirname/../bin/`），与 bundle 现状不一致，是 #30 的真实成因。

## 汇总

| 分类 | Issue | 处理建议 |
|---|---|---|
| 真问题·等价加固（可直接做） | #28 #29 #30 #34 #35 #36 #37 | 全部在日志脱敏 / 临时文件治理 / 死代码移除 / 重复分发清理白名单内，行为不变；合并为 A/B/C 三个 PR |
| 真问题·低危可选 | #24 | 用户传入 AK/SK 无打印点 + 平台 mask 兜底；STS SK 无日志点。按「零业务影响」裁决：**只做 `mask()` 收紧（纯日志）**，放弃 `gitUrl` 改动（会改上报字段 = 契约变化）；不单独立 PR，并入 PR A |
| 真问题·已按「零业务影响」选定方案（可做） | #22 #23 #26 #27 #31 | 一律选运行期零差异的形态：删除不可达死代码（#26/#31）、超预算只告警不阻断（#23）、超时做成可选 input 默认关闭（#27）、新 input 默认 false（#22）；见分节 |
| 真问题·暂缓（后端联动） | #21 | 端到端签名需覆盖报告内容 + 后端发布验签公钥，单仓无法闭环 |
| 不是问题 | #17 #18 #19 #20 | 见分节详述（含 catalog 条目与既有跨仓决策引用） |

## PR 合并计划（Phase 2 预告）

| PR | Issue | 模块 | 性质 |
|---|---|---|---|
| A：fix-sec-log-hygiene | #35 #36 #37 #24 | dist/index.js（mask 收紧、Python 输出回显、日志路径）、CicdUploader.js、scanner.js、SecOptionDetector.js | 等价加固（日志脱敏 + mask 收紧）；不含 `gitUrl` 改动，无契约变化 |
| B：fix-sec-temp-and-dedup | #28 #30 | dist/sec_option_scan.py、删除 dist/bin/sec_option_scan.py、SecOptionDetector.js:10 路径同步 | 等价加固（临时文件治理 + 重复分发清理） |
| C：fix-sec-deadcode-tls-perm | #29 #34 | dist/index.js（TLS 旁路死分支、actions/io chmod 回退） | 等价加固（死代码移除 + 权限收紧） |
| D：fix-sec-remove-http-fallback | #26 #31 | CicdUploader.js（bundle 内联副本） | 等价加固（删除不可达死 fallback 与死 `if (cicdUrl)`；运行路径恒传常量，零行为差异） |
| E：fix-sec-budget-observe | #23 #27 | dist/index.js fetch/spawn、SecOptionDetector.js、sec_option_scan.py | 等价加固（超预算仅 warning 不阻断；超时/输出上限做成可选 input，默认关闭 = 现状） |
| F：fix-sec-gate-input | #22 | CicdUploader.js + action.yml + dist/index.js | 等价加固（新增 `fail-on-upload-error`，默认 `false`，默认路径逐字节不变） |
| 暂缓 | #21 | — | 后端联动后统一实施 |

---

## 分节详述

### #35 #36 #37 —— 日志输出（等价加固）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #35 | 异常处理泄密：上游响应体整体打印 | ✅ 真问题·等价加固（playbook: 日志脱敏）。`dist/uploaders/CicdUploader.js:338`（bundle 同处 `dist/index.js:670`）`console.error(\`HTTP ${status}: ${JSON.stringify(error.response.data)}\`)` 把整段响应体落日志。整改：仅输出 `status` + 后端 `error_code/message` 两个白名单字段，其余丢弃 |
| #36 | 信息泄露：日志输出本机绝对路径 | ✅ 真问题·等价加固。**默认（info 级）实际打印绝对路径的点**：`dist/index.js:33`（`Running sec-option detector on: <绝对路径>`）、`:257`（`Results saved to: <绝对路径>`）、`dist/scanner.js:102`、`:54440`（`Scan target: <绝对路径>`）。`dist/index.js:202`、`scanner.js:47` 为 debug 级，而 action.yml 未暴露 `verbose`/`debug` 输入、`Logger` 仅 `config.verbose` 为真才输出 → 默认不打印。整改：info 级改 `path.basename()`/`path.relative(process.cwd(), p)`；debug 级一并改为相对路径（防将来开启 verbose 时泄露） |
| #37 | 日志注入：外部字符串未清洗换行 | ✅ 真问题·等价加固（playbook: 日志注入清洗）。3 处命中：① `CicdUploader.js:297` payload 字段（`gitUrl`、`pipelineName`、`pipelineRunId`、`packageName` 均源自 `core.getInput` / `GITHUB_REPOSITORY` 等外部值，`packageName` 可含换行）② `dist/index.js:54464-54466`（同字段）③ 子进程输出 `dist/index.js:107/110`、`SecOptionDetector.js:95/98` 原样回显 Python stdout/stderr。整改：统一 `sanitize()`（去 `\r\n` 与控制字符 + 截断）后再拼接；Python 输出按尾部 64KB 截断 |

### #24 —— 凭证与内部路径写入日志（低危可选 + 部分非问题）

**结论（2026-10-22 用户裁决，按「不影响业务逻辑」取舍）**：降为**低危可选**，不单独立 PR，并入 PR A。#24 的子项中「子进程输出」归 #37、「内部路径」归 #36、「Token 声明」为非问题。两个可选改动**只做第 1 项**：

| 可选改动 | 定位 | 影响面 | 是否实施 |
|---|---|---|---|
| `mask()` 默认 `head/tail` 由 6/4 收紧为 2/2 | `dist/index.js:5642-5647` | **纯日志**：11 处调用全在日志链路（5395/5397/5376/5390/5466/5486/5504/5509/5661/5672/5683），不进 payload/outputs/ATOMGIT_OUTPUT，不改退出码 | ✅ 做 |
| `gitUrl` 额外剔除含冒号的 userinfo | `dist/index.js:54379` | **非纯日志**：`gitUrl` 同时上报后端（`:54516`），属窄范围契约变化 | ❌ 不做（按零业务影响原则放弃） |

**未实施项说明**：`gitUrl` 若含内嵌凭证，仍会随上报请求体发往平台（HTTPS 通道内），属既有行为；若后续需要，需单独评审契约变化。

**风险等级下调依据**：用户传入的 `apig-app-key`/`apig-app-secret` 全仓无日志点，且平台 masking 对 secrets 原文做子串替换可兜底；STS 临时 SK 无任何日志点；STS 临时 AK 仅信息级打印片段且不可用于签名。残余风险只到「指纹级 + URL 内嵌凭证」。

**日志分级事实（判断泄露面的前提）**：本仓两套日志都有级别门控，默认只打 info/error，debug 全关——
- OIDC SDK：`debug()` 仅在 `cfg.debug` 为真时输出，`cfg.debug` 默认 `false`（`dist/index.js:5217`），只有程序化 `configure({ debug: true })` 才开，action 入口从未调用（`openlibing.configure` 仅出现在注释文档里）。
- 扫描器/CicdUploader：winston `Logger` 的 `debug()` 仅 `config.verbose` 为真才输出（`dist/utils/logger.js:5,24`），而 action.yml 未暴露 `verbose` 输入。
- 因此「CI 日志把所有日志都打印」在本仓对 **info/error** 成立，对 **debug** 不成立。

| 子项 | 定位 | 结论 |
|---|---|---|
| **临时 AK（唯一默认落日志的凭证类值）** | `dist/index.js:5395` `info(... AK ${mask(cred.access_key_id)} ...)` | ⚠️ info 级、每次必打。AK 为 20 位，`mask` 默认 6/4 → 露前 6 + 后 4。AK 是标识不是密钥，单独不可用于签名，属关联指纹级泄露 |
| 临时 SK（`secret_access_key`） | 全仓检索 | ⚪ 不落日志：仅进入内存 result 与签名计算 |
| 临时 SecurityToken | `:5397` debug `mask(cred.security_token, 10, 10)` | ⚪ 默认不打印（debug 门控）；若将来开 debug，露前 10 + 后 10 |
| `Authorization` / `x-security-token` 等请求头 | `:5466` debug `maskHeaders(headers)` | ⚪ 默认不打印（debug 门控）；开启后按 `SENSITIVE_KEYS` 掩码，但仍是 `mask` 6/4 |
| STS 请求体（含 OIDC `id_token` JWT） | `:5468` debug `_describeBody` → `maskBody`（JWT `mask(20,10)`） | ⚪ 默认不打印（debug 门控） |
| `apig-app-key` / `apig-app-secret` 输入 | `:54370-54371` 读取，仅用于 V11 签名 | ⚪ 无任何日志语句，不落日志 |
| 掩码过宽：`head=6 tail=4` | `dist/index.js:5642-5647` | ✅ 等价加固（playbook: 日志「snippet 掩码」，保留前 2 后 2 + 长度）。改为 `head=2, tail=2`；短值分支 `s.slice(0,2)+'***'+s.slice(-2)` 同步收紧为 `slice(0,1)+'***'+slice(-1)` |
| 失败路径打印 Token 声明（iss/aud/azp/sub） | `dist/index.js:5378` + `_printTokenClaims`（`:5319-5331`） | ⚪ 不是问题：只打 iss/aud/azp/sub 四个声明，非凭证，是 STS 403 信任策略比对所必需（代码注释已说明设计意图） |
| `gitUrl` 仅清洗 `https://user:pass@` | `dist/index.js:54379` `replace(/https:\/\/[^@]+@/, 'https://')` + `:54464` info 打印 | ✅ 等价加固，且是**唯一可能整段凭证落日志的路径**：remote URL 若为 `http://oauth2:<token>@host/...`，正则不匹配 → 完整 token 会以 info 级打印。整改：改为任意 `scheme://userinfo@` 的 userinfo 剔除 |
| 子进程输出原样回显 | `dist/index.js:107/110` | ✅ 与 #37 第③点合并处理 |
| 内部路径写入日志 | 同 #36 | ✅ 与 #36 合并处理 |
| 凭证写入工作区文件 | 全仓检索 | ⚪ 未发现：扫描临时目录与结果 JSON 均不含 AK/SK 或 token；临时目录随 job 结束回收 |

**平台遮罩不能兜底**：平台 secret masking 只替换 workflow 里 `${{ secrets.X }}` 的原文，对拼接/截断/派生值（如 `mask()` 输出的片段、`Bearer xxx` 拼接串）无效，因此上述掩码逻辑不能依赖平台兜底。

### #28 #30 —— 临时目录与重复分发（等价加固）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #28 | Windows 可预测临时基目录 | ✅ 真问题·等价加固（playbook: 可预测临时文件名 / 临时文件残留）。`dist/sec_option_scan.py` 中 `for short_base in (r'D:\sec_option_tmp', r'C:\sec_option_tmp')` 固定基目录 + `tempfile.mkdtemp(prefix='s_')`。风险：基目录可被同机其他作业预先创建为 junction/symlink，或已存在低权限可读目录。整改（严格等价，不改业务逻辑）：① **首选（零行为变化）**保留现有 `D:\sec_option_tmp`/`C:\sec_option_tmp` 基目录，`os.makedirs(exist_ok=True)` 后仅增加 `os.path.islink(short_base)` 与 `FILE_ATTRIBUTE_REPARSE_POINT` 校验——正常机器上判断恒为假，路径/盘符/长度/清理与现状逐字节一致，仅在目录被 junction 劫持时才跳过该基目录并回退 `gettempdir()` + `mkdtemp` 随机名 + 一行 warning；② 可选优化（**非严格等价，需评审**）：改用 `tempfile.gettempdir()` 的 8.3 短路径（ctypes `GetShortPathNameW`），彻底去掉固定名，但引入两个环境依赖——卷上禁用 8.3 时短名不生效导致 MAX_PATH 问题复发、临时目录换盘可能因容量不足解压失败；③ **不要依赖 `os.chmod(0o700)`**——Windows 下 Python 的 `os.chmod` 只切换只读位、不改 ACL，防护实际来自 `mkdtemp` 自身 0700 叶子目录 + ①。**输出不受影响**：结果路径均经 `_relativize_file_path` 且 `scan_root` 重置为解压根，临时目录前缀不进结果 JSON。
| #30 | 分发两份重复扫描脚本且无完整性校验 | ✅ 部分等价加固 / 部分不是问题。重复部分：两份 SHA256 完全一致（见基线事实 4/5），运行时只用根副本 → **删除 `dist/bin/sec_option_scan.py`**，并把 `detectors/SecOptionDetector.js:10` 的路径改为 `__dirname/../sec_option_scan.py`，保证「单一副本 + 单一引用」。完整性校验部分：⚪ 不是问题（catalog: 平台分发完整性）——zip 由平台 artifact 分发与校验，插件内自校验无信任根（校验清单与 zip 同源），无实际收益 |

### #29 #34 —— 不可达死代码（等价加固）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #29 | 打包内 TLS 校验旁路 + 可变 `fetch` | ✅ 部分等价加固 / 部分不是问题。TLS 旁路：`dist/index.js:3245` 与 `:3269`（`usingSsl && this._ignoreSslError` → `rejectUnauthorized:false`，两处 HttpsProxyAgent 构造分支），核实 `CicdUploader` 构造 `HttpsProxyAgent` 时从未传 `_ignoreSslError`，也无 input 暴露该开关 → 不可达死分支，**删除**（等价加固：无行为变化）。`fetch` 动态选取（`:5473`）⚪ 不是问题：为 Node16（`engines: >=16`）保留的兼容降级，`typeof fetch === 'function'` 在 Node18+ 恒真，非攻击者可控 |
| #34 | 捆绑 @actions/io 回退路径 `chmod 0666` | ✅ 真问题·等价加固。`dist/index.js:3933`（io.cp 的 EPERM 回退）。核实：全仓无 `io.cp(` 调用（仅定义与导出）→ 本包不可达；但打包产物仍带该宽松逻辑。整改：`0666` → `0600`（等价加固：唯一效果是权限更严，且调用面为 0）。升级依赖不可行：`@actions/io` 最新 3.0.2 为 `type: module`（ESM-only），而 `@actions/exec` 1.1.x 为 CJS `require('@actions/io')`，升级属破坏性变更（需改调用方 + ncc 打包），超出等价加固范围 |

### #26 #31 —— 上报 baseUrl 明文 HTTP fallback（已按零业务影响裁决）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #26 | 明文 HTTP 默认值 + 无证书固定 | ✅ 真问题·等价加固（**方案 C：删除死代码**）。`dist/uploaders/CicdUploader.js:248`（bundle `dist/index.js:~580`）`this.baseUrl = config.cicdUrl \|\| 'http://localhost:8080'`。核实 fallback **不可达**：① 运行入口 `run()`（`dist/index.js:54344`）唯一构造点传常量 `cicdUrl = 'https://apig.openlibing.com:443'`（`:54364/54452`），且 `:54449` 的 `if (cicdUrl)` 恒真；② bundle 内 `Scanner` 类虽定义了第二构造点（`:182`），但全文无 `new Scanner`，`package.json.main` 为 `dist/index.js` 且无 `exports`，无外部消费方。故整改为 `this.baseUrl = config.cicdUrl` 并删除死 `if (cicdUrl)` 分支——运行期零差异（比方案 A 改 https / 方案 B 置空报错更彻底且不引入语义变化）。证书固定不做（内网自签 CA 场景会破坏现网可用性，属平台侧能力） |
| #31 | 上报 baseUrl 明文 http fallback | 同 #26（同一行代码的重复发现，合并一个 PR） |

### #23 #27 —— 资源与超时预算（已按零业务影响裁决）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #27 | 出站请求无超时、子进程输出无上限 | ✅ 真问题·等价加固（**改为可选开关，默认关闭 = 现状**）。① `dist/index.js:5473-5490` `fetchImpl(url, {...})` 无 `signal`、`res.text()` 无长度上限；修复：新增可选 input（如 `request-timeout-ms`，默认 `0` = 不超时，与现状一致），仅当 >0 时才挂 `AbortSignal.timeout`；② `SecOptionDetector.js` spawn 无 `timeout`/`maxBuffer`：新增可选 input（默认 `0`）后才设 `timeout`，`maxBuffer` 仅在用户显式设置时收紧；③ 响应体/子进程输出的**日志截断**（尾部 64KB）只作用于 `sanitize/truncate` 输出，不改 payload、不改 outputs、不改退出码（与 #36/#37 共用同一函数） |
| #23 | 解压/递归扫描无资源预算 | ✅ 真问题·等价加固（**只观测、不阻断**）。`dist/sec_option_scan.py` 的 `_safe_extract_zip/_safe_extract_tar` 已有 zip-slip/tar-slip 校验，但无总量预算。整改：统计解压字节/条目数/嵌套深度/单归档耗时，超参考阈值（2GB / 200000 / 8 层 / 300s）**只打一行 warning 并继续扫描**，不跳过归档、不改成功/失败语义、不改扫描结果。硬预算（超限跳过）需业务方确认合法大包场景后再另行评审 |

### #22 —— 合规门禁可被绕过（已按零业务影响裁决）

| 内容 | 核实结论 |
|---|---|
| 上报失败不使 step 失败；扫描环境准备失败仅 warning；无「必需」语义 | ✅ 真问题·等价加固（**新增可选 input，默认 `false` = 现状**）。核实：① 上传分支仅 `info`/`error` 日志，**未 `setFailed`**；② `pip install` 失败仅 `core.warning('Python dependency installation failed…')`（`dist/index.js:54405`），该步 fail-open；③ 产物缺失会 `throw` → 顶层 `setFailed`（`:54656`），阻断能力已存在。整改：新增 `fail-on-upload-error`（默认 `false`），默认路径不进入 `setFailed` 分支 → 运行期零差异；README/action.yml 同步说明。「必需扫描」与门禁判定由平台侧承载，插件不自行反转默认语义 |

### #21 —— 合规结果端到端可篡改（暂缓·后端联动）

| 内容 | 核实结论 |
|---|---|
| 上报数据无端到端签名，签名不覆盖关键字段 | ⏸ 暂缓（后端依赖）。核实：OIDC/SK 签名绑定的是「所交付 body」，服务端按 body 验签，属传输完整性设计而非报告不可篡改证明；结果 JSON 在 job 内生成、job 内上传，插件侧无法提供可信时间戳/取证锚点。整改需平台侧（后端发布验签公钥 + 报告内容签名 + 存证），单仓无法闭环 |

### #17 #18 —— CI workflow（不是问题）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #17 | PR 代码在自托管执行机执行（pwn-request） | ⚪ 不是问题（catalog: 自建门禁 workflow 设计）。`pre-commit.yml:8` 用 `pull_request_target` 是为**始终读取 master 的最新门禁配置**，`checkout` 显式检出 `merge_commit_sha` 并按设计「检查 PR 合并后代码」（门禁必须执行 PR 代码才能检查它）。`ROBOT_TOKEN` 只注入 `initiate`/`post` 两个 label job（`pre-commit.yml:31/84`），与执行 PR 代码的 `pre-commit` job 不同 job，无凭证可达。workflow 级 `permissions: repository: read, pr: write`（`:17-19`）对执行 job 偏宽，属平台侧 job 级 permissions 能力缺口，登记为配置优化项 |
| #18 | CI 供应链可变引用 + 超范围 OIDC 授权 | ⚪ 不是问题（catalog: OIDC 联邦必需 + 自有仓可变 tag）。`id-token: write`（`nightly-schedule-scan.yml:10`、`code-metrics-scan.yml:11`）是华为云 OIDC 联邦换临时凭证的必需权限，无法收敛；`uses` 全部为自家门禁 Action（`openlibing/pre-commit-action@v1.0.2`、`openlibing/upload-sarif-action@v1.0.0`、`openlibing/code-metrics-action@v1.0.3`、`openlibing/pr-label-action@v1.0.0`）或平台内置 `checkout/setup-node/setup-go`，无第三方 Action。可选强化：自家 Action 改 commit SHA（低优先级，需随发版维护） |

### #19 —— PyPI 镜像无哈希安装（不是问题，沿用既有跨仓决策）

| 内容 | 核实结论 |
|---|---|
| `pip install pyelftools==0.31` 无 `--require-hashes`，源为公网阿里云镜像 | ⚪ 不是问题（沿用 2026-10-13 pre-commit-action#23 评审决策：**精确版本固定即满足要求，不引入 `--require-hashes`**）。同形态已落地可对照：`pre-commit-action/index.js:710-712` → `pip install pre-commit==${PRE_COMMIT_VERSION}`，注释明确「不做 --require-hashes」。本仓核实：`dist/index.js:54394-54402` 用静态参数数组 + `execSync`，无用户输入参与，版本已精确固定，已满足该决策标准。`-i https://mirrors.aliyun.com/pypi/simple/` 为**固定**地址、非动态/外部可控值，不属安全问题，本次不处理（已裁决 2026-10-22） |

### #20 —— 流水线身份可伪造（不是问题）

| 内容 | 核实结论 |
|---|---|
| OIDC 身份取自环境变量/未校验 OIDC URL | ⚪ 不是问题。核实：`process.env.HUAWEICLOUD_OIDC_TOKEN` 优先直取（`dist/index.js` OIDC 客户端段）——环境变量即 Actions 的信任边界，能写环境变量的主体已具备修改 workflow / 直接在 runner 执行代码的能力，不构成新增提权面；OIDC 端点 URL 若强制 host 白名单，属「新增输入拒绝」，会破坏私有云/自建 GitCode 平台兼容性，不建议实施。若平台侧要求，须走评审并在 action.yml 暴露可配置白名单 |

---

## 方案选定（原则：一律选不影响业务逻辑的形态）

| 项 | 选定方案 | 零业务影响依据 |
|---|---|---|
| #26/#31 | **删除不可达死 fallback + 死 `if (cicdUrl)`**（不是 A 也不是 B） | 唯一运行构造点传常量 `https://apig.openlibing.com:443`，`new Scanner` 不存在 → fallback 永不执行；删除后运行期无差异，且不引入失败语义/默认值变化 |
| #23 | **只统计并打 warning，不跳过、不阻断** | 硬预算会拒绝合法大包（行为变化）；告警型只增一行日志 |
| #27 | **新增可选 input，默认 `0`/关闭 = 现状**；日志截断只作用于日志文本 | 默认路径不加 `signal`、不加 `timeout`、不改 payload/outputs/退出码 |
| #22 | **新增 `fail-on-upload-error`，默认 `false`** | 默认不进入 `setFailed` 分支，与现状逐字节一致 |
| #24 | **只做 `mask()` 收紧（纯日志），放弃 `gitUrl` 改动** | `gitUrl` 会进入上报体（契约变化），按原则不做 |
| #28 | **保留原短路径基目录 + reparse/junction 校验 + 回退** | 正常机器校验恒为假，路径/盘符/清理全部不变 |
| #29 #30 #34 | **照做**（死分支删除 / 删重复副本 / `0666`→`0600`） | 三处调用面均为 0，运行期不可达 |

> 已裁决（2026-10-22）：#19 维持「精确版本固定、不做 require-hashes」的既有跨仓决策；固定阿里云镜像源不属安全问题，不做改动。

## 一致性说明（跨仓）

- 本仓 `dist/index.js` 内的 `@actions/io` `chmod 0666` 与 code-metrics-action、pr-sync-action、oidc-client 为同一捆绑依赖问题，建议四仓按同一形态（`0600`）统一处理，避免各仓形态不一。
- 日志清洗（`sanitize`）与 snippet 掩码（前 2 后 2）应与 upload-ut-action / upload-sarif-action 已整改形态保持一致。
