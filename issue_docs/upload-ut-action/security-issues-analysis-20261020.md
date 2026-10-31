# upload-ut-action 安全 Issue 批量定性分析（20261020）

定性依据：argus / SenInfo / SENS / 红线落地扫描 issue 清单（openlibing/upload-ut-action#1-#23）。
已比对跨仓知识库：`security-non-issue-catalog.md`（非问题判定库）、`security-remediation-playbook.md`（整改方案库）。
整改方案引用 playbook 的类型标注为「playbook: <类型名>」。

## 汇总

| 分类 | Issue | 处理建议 |
|---|---|---|
| 已修复待自测（PR #1） | #2 #4 | #2 URL 环境变量注入 + gitleaks:allow；#4 obs_acl 可配置（默认 public-read 不变）。PR openlibing/upload-ut-action#1（分支 fix-issue1-2-obs-url），已合入统一测试分支 fix-security-remediation |
| 同根因·待后端联动暂缓 | #1 #15 #18 #21 | public-read 匿名可读与 #4 同根因；默认 ACL 切 private 依赖后端支持带凭证下载（同 upload-sarif-action#11 暂缓模式），待后端联动后统一切 private |
| 真问题·等价加固（可直接做） | #5 #11 #16 #20 | 见分节详述；按同文件/同根因合并 2 个 PR |
| 真问题·需验证 | #8 #14 | 同根因（esdk-obs-nodejs sslVerify 默认 false）；传 sslVerify: true 需在自托管 runner + 企业自签 CA 场景实测 |
| 同根因重复（随 #8/#14） | #24 | 【计算生态型应用TOP问题】不安全协议/加密套件，命中点 ObsUploader.js:117-124 ObsClient 构造未设 sslVerify，与 #8/#14 同一处代码；PR #4 已显式 `sslVerify: true`（:123），不新增改动，随 #8/#14 环境验证后一并关闭 |
| 真问题·低危（攻击面受限） | #9 | 惰性正则 O(n²) 已复现（k=16000 约 0.7s，叠加无闭合长尾可达 9s 级）；jacoco.xml 非 PR 可控 + pre-commit 拦截 + 插件不挂 PR 流程 → 当前部署不可利用；2026-10-22 已附实测证据按「当前不可利用」关闭 |
| 真问题·产物入库需清理 | #23 | upload-ut-action.zip 为 build 构建产物（zip.js:16 生成），已被入库；`.gitignore:3` 的 `.zip` 规则只能匹配名为 `.zip` 的文件，实际未忽略该产物（`git check-ignore` 验证不命中）。已从版本库删除并修正为 `*.zip` |
| 不是问题 | #3 #10 #12 #13 #17 #19 #22 #25 | 见非问题详述（含 catalog 条目引用）；#10 与 #9 同属「jacoco.xml 非 PR 可控输入」前提不成立；#25 日志注入需平台侧异常或仓库写权限才能触发 |
| 已关闭（重复） | #6 | 与 #3 同一问题独立发现，2026-10-12 已关闭 |

## PR 合并计划（Phase 2 预告）

| PR | Issue | 模块 | 性质 |
|---|---|---|---|
| PR #1（已存在，待自测） | #2 #4（+#1/#15/#18/#21 同根因声明） | ObsUploader + action.yml | 等价加固 |
| PR #3：fix-issue16-20-workspace-injection（已创建，待自测） | #16 #20 | index.js（find 子进程改 fs 递归，同代码段 resolveRepoRoot） | 等价加固 |
| PR #4：fix-issue5-8-11-14-obs-uploader（已创建，待自测） | #5 #11 #8 #14 #24 | ObsUploader.js（临时文件名、runId 清洗、sslVerify） | 等价加固 + 需验证 |
| PR #5：fix-issue23-remove-zip-artifact（已创建，待自测） | #23 | 删除入库的 upload-ut-action.zip + `.gitignore` 修正为 `*.zip` | 产物清理 |

## 分节详述

### #1 #15 #18 #21 —— OBS public-read 匿名可读（同根因，待后端联动）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #1 | SENS-14 覆盖率数据 public-read 上传共享桶长期留存 | ⏸ 暂缓（后端依赖）：ObsUploader.js:46 `OBS_BUCKET='openlibing-gitcode-action'`，uploadJson ACL 默认 `public-read`（:96, :113）。后端 coderepo UtCoverageController 依赖匿名 HTTP GET 下载 obsUrl（回调 payload 只传 obsUrl，无凭证）。整改与 #4 一致：PR #1 已提供 `obs_acl` input（默认 public-read 行为不变），切 private 须后端支持带凭证下载后统一实施。#15/#18/#21 为同一根因的重复发现，随 #4 一并处理 |
| #15 | 覆盖率报告 public-read 匿名可读上传公网桶 | 同 #1 |
| #18 | 权限最小化：OBS 对象 ACL public-read 匿名可读 | 同 #1 |
| #21 | public-read 明文可读且无大小上限 | 同 #1；"无大小上限"部分：覆盖率 JSON 为流水线自身产物，平台侧对象大小治理超出插件单仓范围 |

### #5 —— 临时文件名可预测（等价加固）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #5 | 信息泄露：临时文件名可预测且未限制权限 | ✅ 真问题·等价加固（playbook: 临时文件残留，扩展形态）。定位 ObsUploader.js:102 `ut-coverage-${Date.now()}.json`（os.tmpdir 下时间戳可预测）。整改：保留时间戳并追加随机后缀 `ut-coverage-${Date.now()}-${crypto.randomUUID()}.json`（保留 `Date.now()` 便于按时间排查，`randomUUID` 消除可预测性）。行为等价（文件用途/生命周期不变）；清理已有（:118-122 finally unlink）。覆盖率 JSON 非凭证文件，风险低 |

### #8 #14 —— OBS TLS 证书校验（需验证）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #8 | ObsClient 未开启 TLS 证书校验（ssl_verify 缺省 false） | ✅ 真问题·需验证。ObsUploader.js:100-107 ObsClient 构造未传 sslVerify，esdk-obs-nodejs dist 内默认 `sslVerify=false` → `rejectUnauthorized: false`（dist/index.js:11952）。整改：构造参数加 `sslVerify: true`。**需验证**：自托管 runner + 企业自签 CA/MITM 代理场景可能握手失败，须实测后定案（同 upload-sarif-action 整改先验证模式） |
| #14 | OBS 上传客户端未启用 TLS 证书校验 | 同 #8 根因，合并处理 |
| #24 | 【计算生态型应用TOP问题】不安全协议/加密套件（ObsUploader.js:104-109 未设 sslVerify） | 同 #8/#14 同一处代码（现位于 ObsUploader.js:117-124 ObsClient 构造），属重复发现。不新增改动，随 #8/#14 完成自托管 runner + 企业自签 CA 环境验证后一并关闭 |

> **⚠️ 回归缺口补记（2026-10-27，commit `aafeebd`）**：前轮整改写入的键名 `sslVerify`（驼峰）被 esdk-obs-nodejs **静默忽略**——SDK 构造链路为 `new ObsClient(param)` → `initFactory(..., param.ssl_verify, ...)`（dist/index.js:4044），内部 `rejectUnauthorized: this.sslVerify || false`（:11978），即 #8/#14/#24 实际一直未生效（TLS 校验仍关闭）。本轮已修正为 SDK 原生键名 `ssl_verify: true`（ObsUploader.js:123），并由单测断言构造参数键名（test/obs-acl.test.js）。**后续自测验证须基于 `aafeebd` 之后版本**，此前「sslVerify: true 已显式设置」的验证结论作废。

### #9 —— JacocoParser 惰性正则二次方复杂度（真问题·攻击面受限）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #9 | JacocoParser 惰性正则二次方复杂度致恶意 jacoco.xml DoS | ✅ 真问题·低危（缺陷成立，当前部署不可利用）。定位 JacocoParser.js:70-80 `/<package...>([\s\S]*?)<\/package>/g` 与嵌套 sourcefile 正则。① **已复现**（仓库真实 parseContent，Node 20.20/24.14）：无闭合 `<package name="a">` 重复 k 次，k=4000 约 46ms、8000 约 179ms、16000 约 651-711ms（翻倍约 4 倍，O(n²)）；叠加 2MB 无闭合长尾时 16000 个开标签达 9.3s，与 argus PoC（196/737/3183ms）曲线一致。action 运行时为 node16（action.yml:61），老 V8 只会更慢。② **攻击面受限**：jacoco.xml 由 jacoco 工具链生成，非 PR 可控输入；手工构造的病态文件属代码变更，会在 pre-commit 门禁环节被拦截；本插件用于全量代码扫描，不挂在 PR 流程上 → 当前部署下不可利用。③ 整改（低优先级，可选）：parseContent 改 indexOf 游标线性切片 + parseFile 增加文件大小上限，输出对合法报告完全一致 |

### #10 —— 覆盖率百分比边界（非问题）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #10 | 覆盖率百分比缺乏 0-100 边界校验可上报越界数据 | ❌ 非问题（与 #9 同构：攻击面前提不成立）。coverageUtil.js:20-24 `pct` 已防护非数字、`t<=0`（除零）、`t<0`，剩余未防护项仅为 `covered > total`（输出 >100）与 `covered < 0`（输出负数）。这两个值只能来自 JacocoParser 对 XML 属性 `parseInt` 直信，而 jacoco 工具链不会产出此类数据；病态 XML 属代码变更会被 pre-commit 拦截，插件用于全量扫描不挂 PR 流程 → 不可利用，无需安全整改。**如后续出现工具侧异常数据，按功能需求处理**（在功能 issue 中评估 clamp，不作为安全整改） |

### #11 —— OBS 对象键清洗与组织维度（拆分处理）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #11 | OBS 对象键缺组织维度且 runId 未清洗致跨租户数据覆盖 | ✅ 拆两半：① runId 未清洗 = 等价加固（buildObsKey ObsUploader.js:84 `${runId || 'manual'}` 原样拼入，repoName 有清洗而 runId 没有；runId 源 ATOMGIT_RUN_ID 平台生成，正常输入清洗前后等价）→ 随 PR B 实施；② 对象键增加组织维度 = 后端依赖（键格式变化影响后端检索/清理逻辑）→ 暂缓，与 ACL 切 private 一并待后端联动。跨租户覆盖实际前提：同 repoName + 同时间桶 + runId 冲突，平台 runId 全局唯一，风险低 |

### #16 #20 —— WORKSPACE/find 拼接 shell 命令（等价加固）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #16 | 红线：WORKSPACE 未校验拼入 bash 命令 | ✅ 真问题·等价加固。定位 index.js:57-65 execCapture（shell:'/bin/bash'）+ :77 `find ${workspace} -maxdepth 3 -name ".git"`。WORKSPACE 源自平台环境变量，含空格/特殊字符即命令注入面。整改：以 Node fs 递归查找 .git 替代 find 子进程，删除 shell 执行路径；查找结果语义一致 |
| #20 | 命令注入：find 拼接 workspace 未转义 | 同 #16 同一代码段，合并一个 PR |

### #2 #4 —— 已修复待自测（PR #1）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #2 | SecInfo 硬编码公网地址（OIDC 业务 API 等） | ✅ 已修复（playbook: 公网地址硬编码）。PR #1：OIDC_PROD_BASE/OIDC_BETA_BASE 支持 OPENLIBING_APIG_PROD_BASE/OPENLIBING_APIG_BETA_BASE 环境变量注入，默认值与原硬编码逐字一致，gitleaks:allow 白名单登记合规例外 |
| #4 | OBS 对象硬编码 public-read ACL | ✅ 已修复（等价加固：新增可选参数）。action.yml 新增 `obs_acl` input，默认 public-read 保持原行为；后端切带凭证下载后配 private（Ref #1） |

> **⚠️ 回归缺口补记（2026-10-27，commit `aafeebd`）**：前轮 #4 整改存在两处闭环缺口，流水线实测暴露：① **P0** index.js:200 解构 `{ envType, obsAcl }`，但全文件从未声明 `obsAcl`（未读 `obs_acl` input），所有升级到该分支的流水线在「扫描/解析成功之后」必然抛 `obsAcl is not defined` → result=failed → exit 1，OBS 无对象、无回调；② **P1** ObsUploader.uploadJson 接收 `acl` 形参但 putObject 写死 `ACL: 'public-read'`，即使补上 obsAcl 读取，`obs_acl=private` 也不生效。本轮闭环：index.js 补 `obs_acl` 读取 + public-read/private 白名单（非法值提前抛错，默认 public-read 与后端匿名下载行为一致）+ putObject 改为透传 `acl`；新增 test/obs-acl.test.js 覆盖白名单/透传/缺省等价（47 用例全绿），dist 已重建同步。

### #23 —— 构建产物 zip 入库（真问题·需清理）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #23 | 安装包残留-zip 打包产物入库 | ✅ 真问题（产物入库），已整改。`upload-ut-action.zip` 由 zip.js:16 在 `npm run build` 时生成，属构建产物，却被提交进版本库（提交 064d5c8 "chore: rebuild dist artifacts"）。根因不止「文件已被跟踪」：`.gitignore:3` 写的是 `.zip`，该模式只能匹配名为 `.zip` 的文件，对 `upload-ut-action.zip` 不生效（`git check-ignore -v upload-ut-action.zip` 无输出、`git status` 仍显示为未跟踪文件）。整改（分支 `fix-issue23-remove-zip-artifact`，commit d80a427）：`git rm --cached` 移除版本库中的 zip + 忽略规则修正为 `*.zip`（修正后 `git check-ignore` 正常命中）。本地构建时仍会重新生成，不影响 Action 使用 |

### #25 —— 日志注入（非问题）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #25 | 【计算生态型应用TOP问题】日志注入：外部可控输入未清洗直接拼入日志，可 CRLF 伪造日志行 | ❌ 非问题（判定逻辑与 #9/#10 同构：注入源前提不成立）。命中点 index.js:146 的两个值均不可被外部构造：`branchName` 来自 ATOMGIT_HEAD_REF/ATOMGIT_REF_NAME（git ref，`check-ref-format` 禁止控制字符含 `\r\n`，PR 作者起不出带换行的分支/标签）；`gitUrl` 来自 ATOMGIT_REPOSITORY_URL（平台生成的规范化地址，owner/repo 段不含换行）。要让这一处注入 CRLF，只能是平台自身把异常字符串写入环境变量（平台缺陷或被攻破），正常 PR 贡献者无法触发。其余日志点（index.js:163/:170/:179 的 `r.file` 文件路径、`e.message`）虽理论上可用含换行的目录名污染（git 仅禁 NUL 与 `/`），但需向被扫描仓库提交代码，而本插件用于全量代码扫描、不挂 PR 流程 → 注入者已具备该仓写权限，收益仅限伪造本仓 CI 日志行，不改变上传数据与退出码。**如后续平台侧环境变量出现异常字符串，按功能需求处理**（在功能 issue 中评估日志清洗，不作为安全整改） |

## 非问题详述（人工鉴定清单，待用户逐条确认）

| Issue | 内容 | 非问题理由 | 决策 |
|---|---|---|---|
| #3 | pull_request_target + allow-unsafe-pr-checkout 自托管执行 fork PR 代码（RCE） | 非问题判定（catalog：门禁设计，同 pre-commit-action#20 模式）。缓解因素核实：ROBOT_TOKEN 仅注入 initiate/post 的 label job（pre-commit.yml:33/:83），与检出 PR 代码的 pre-commit job（:42，无 secrets）不同 job；npm lifecycle/本地 hook 执行不可信代码是 pre-commit 门禁的固有形态（必须执行 PR 自带 .pre-commit-config.yaml）；runner 隔离属平台侧整体加固 | 2026-10-22 用户决策：非问题，已附结论关闭 GitCode #3 |
| #19 | 执行不可信代码-workflow 检出 PR 代码执行钩子 | 与 #3 同根因重复发现，随 #3 归档 | 2026-10-22 用户决策：非问题，已附结论关闭 GitCode #19 |
| #12 | CI Action 以可变 tag 引用未按 SHA 固定 | 非问题判定（catalog：自有门禁配置中的可变 tag 依赖）。uses 均为一方插件（openlibing/pr-label-action@v1.0.0、pre-commit-action@v1.0.2）或平台标准 action | 2026-10-22 用户决策：非问题，已附结论关闭 GitCode #12 |
| #13 | CI 运行期联网拉取未入 lockfile 的 prettier | prettier 已 `--save-exact prettier@3.9.5` 精确 pin（pre-commit.yml:63），无版本漂移；npm install 在 PR 检出树执行 lifecycle 脚本的风险属 #3 门禁设计同根因，已随 #3 定性 | 2026-10-22 用户决策：非问题，已附结论关闭 GitCode #13 |
| #17 | （标题为 feat(api-scan) workflow） | 非安全 issue：扫描误将功能 PR/issue 标题计入安全清单 | 2026-10-22 用户决策：非问题（扫描噪音），已附结论关闭 GitCode #17 |
| #10 | 覆盖率百分比缺乏 0-100 边界校验 | 非问题判定：`pct` 已防护非数字/除零/负总数，剩余 `covered > total`、`covered < 0` 只能来自 jacoco 工具链不会产出的病态 XML，攻击面同 #9 评估（非 PR 可控、pre-commit 拦截、插件不挂 PR 流程）。如后续出现工具侧异常数据，按功能需求处理，不作为安全整改 | 2026-10-22 用户决策：非问题，已附结论关闭 GitCode #10 |
| #22 | 输入校验缺失-report_dir 无白名单 | report_dir 为仓管理员在流水线配置中设置的受信输入（INPUT_REPORT_DIR），非外部不可信输入；白名单会破坏多语言报告路径的通用性（业务设计固有取舍） | 2026-10-22 用户决策：非问题，已附结论关闭 GitCode #22 |
| #25 | 日志注入（TOP问题）：gitUrl/branchName 直接拼入日志 | 非问题判定：注入源不可外部构造（分支名为 git ref 禁止控制字符、仓库 URL 平台生成），需平台侧异常才可能触发；文件路径类日志需仓库写权限且仅影响 CI 日志。如后续平台侧环境变量出现异常字符串，按功能需求处理 | 2026-10-22 用户决策：非问题，已附结论关闭 GitCode #25 |

## 备注

- 2026-10-22 新到扫描【计算生态型应用TOP问题】2 条，已补入本定性：#24（不安全协议/加密套件，与 #8/#14 同根因重复）、#25（日志注入，2026-10-22 用户决策改判非问题）。
- #6（pwn request，closed）为 #3 的 argus 独立发现，报告原文注明"修复任一即可关闭两者"，2026-10-12 已关闭。
- 2026-10-22 复验（统一测试分支 fix-security-remediation，commit 45fa322）：`npm test` 38/38 通过；4 个整改 PR（#1/#3/#4/#5）均已合入该分支；PR #4 分支 src 与 dist 一致（dist/index.js:25744 `sslVerify: true`、:25750 `randomUUID` 临时文件名）。
- 2026-10-22 TLS 校验可用性预验证：本机 node 默认 CA 直连 `https://obs.cn-southwest-2.myhuaweicloud.com` 握手成功（HTTP 403，未带凭证），说明 `sslVerify: true` 对公网 CA 链路无影响；企业自签 CA/MITM 场景仍须在自托管 runner 实测。
- 2026-10-27 回归缺口修复（统一测试分支 fix-security-remediation，commit `aafeebd`）：静态分析 + 流水线实测暴露前轮三处缺陷——P0 `obsAcl` 未声明（上报阶段必失败）、P1 putObject 写死 ACL 忽略入参、P1 TLS 键名误写 `sslVerify` 被 SDK 忽略（#8/#14/#24 实际未生效）。三项已全部修复并补 9 个针对性单测（合计 47 用例全绿），dist 重建同步；上两条 2026-10-22 的复验/预验证结论中涉及 `sslVerify: true` 的部分以本条为准（键名修正为 `ssl_verify` 后需重新实测）。
- 当前仓库状态：fix-security-remediation 分支含 PR #1 整改 commit（7016e30）；PR #1 页面显示 +0/-0 为对比基准显示问题，实际 diff main...fix-issue1-2-obs-url 为 5 files +400/-380（主要 dist）。
