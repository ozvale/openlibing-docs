# upload-sarif-action 新增安全 issue 分析（#10~#20，open 12 条）

> 分析基准：`fix-security-remediation` 分支（HEAD: ca837a0，已合 PR #12 / #13）。
> 分析日期：2026-10-12。结论仅作整改决策参考，暂不修改代码。
> 注：#18 与 #16 为同一根因（resolveSourceFile），合并分析。

## 汇总

| 分类 | Issue | 处理建议 |
|---|---|---|
| 已修复/重复，待合入后关闭 | #12 | 回复说明覆盖关系（PR #13），整改分支合入主线后关闭 |
| 已实施·集中配置化（2026-10-16，待自测） | #10 | 见第一节详述 |
| 已实施·边界校验（2026-10-16 用户批准，待自测） | #18 #16（同根因） | SARIF uri 读取限定 sourceRoots 边界，见第二节详述 |
| 已实施·等价加固（2026-10-16，待自测） | #20 | execCapture 改 execFileSync 数组传参，行为等价 |
| 真问题·需验证后修复 | #19 | 已实施（2026-10-16，sslVerify: true + obs_ssl_ca_file 可选输入）；需在自托管 runner 实测（企业代理/自签 CA 场景） |
| 平台/后端依赖·须评审 | #11（暂缓回退） #14（残留部分） | 默认 ACL 切 private / 回写行为调整依赖后端演进，插件侧无法单方面整改，待后端联动后统一实施 |
| 不是问题 | #13 #15 #17 | #13 业务功能需求（nightly 全量扫描）；#15 静态 AK/SK 直连是易用性设计取舍；#17 pwn request 属 CI 门禁固有形态——均见第六节详述 |

---

## 一、已部分修复（#10 集中配置化已实施，待自测）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #10 | 公网地址硬编码清单（长列表） | ✅ **已实施（2026-10-16，方案 B 集中配置化），待自测**：<br>① 已做（PR #12）：功能性/文档性公网 URL 加 `gitleaks:allow` 白名单注释；issue 正文大量条目为扫描器噪音（package-lock.json 的 npmmirror registry 属正常依赖源、`json.schemastore.org` 为 SARIF 标准格式声明字段、log4j 文档示例 URL 属三方库自带文案、`token.actions.githubusercontent.com` 属 GitHub OIDC 标准端点），不需处理。<br>② 已实施（fix-issue10-20-endpoints-exec 分支，commit 1178ec2，已合入 fix-security-remediation）：新建 `src/config/endpoints.js` 集中管理 5 项业务功能性端点（`OIDC_PROD_BASE`、`OIDC_BETA_BASE`、`OBS_BUCKET`、`OBS_READ_ENDPOINT`、CodeArts host 前缀/域名 `CODEARTS_HOST_PREFIX`/`CODEARTS_API_DOMAIN`），index.js 与 CodeArtsCheckApi.js 改从配置取值，保留同名环境变量覆盖；**默认值与原硬编码完全一致（等价变换）**，dist 已同步重建。<br>③ PR 归并：与 #20 按硬规则 4 合并到同一 PR 分支 fix-issue10-20-endpoints-exec；#19 另行走 fix-issue19-obs-tls-verify 分支。 |
| #11 | SENS-14：SARIF 临时目录残留 + public-read 上传 + 工作区回写 | ⏸ **暂缓回退（2026-10-15 用户决策）**：PR #13 中 #11 相关改动（convertOutDir exit 钩子清理、obs_acl 可配置、两处条件回写）已全部撤销并保留 #12 snippet 掩码（PR 分支 3f64ef5 + ab5e4a2，已同步 fix-security-remediation 86c4395）。原因：ACL 调整与回写行为需与后端 SarifParseServiceImpl 联动改造，插件侧暂时保持原有行为（桶私有 + 对象 public-read 既定设计），待后端支持带凭证下载后统一实施 |
| #12 | SENS-15：凭证类规则 snippet 明文留存 | ✅ 已修复：PR #13 实现 CREDENTIAL_RULE_RE 判定 + maskCredentialSnippet 掩码（index.js:409、518 附近），命中口令/密钥类规则时 snippet 中字符串字面量掩码后写入。**⚠️ 回归缺口 2（2026-10-26 流水线实测发现，已补齐 commit `8a74bd1`）**：掩码只覆盖 region.snippet / contextRegion.snippet，`result.message.text` 不在掩码范围——bandit 等把明文口令写进 message 的工具（B105 `comparison to "123456"`）SARIF 里仍保留明文。补齐：enrichRegionSnippet 循环中对 `r.message.text` 同样过 `maskText`（仅凭证类规则生效；窄范围契约变化，与 #11 snippet 掩码同性质取舍） |

---

## 二、高危·已评审并实施（#18/#16 边界校验，待自测）

### #18 / #16 SARIF uri 驱动的任意文件读取（同根因，合并处理）【高危】

- **状态**：✅ **已实施（2026-10-16，用户批准边界校验方案），待自测**（fix-issue18-16-uri-boundary 分支，commit 6988409，已合入 fix-security-remediation）
- **位置**：`resolveSourceFile`，[index.js:470-504](file:///e:/work/huawei/fork/upload-sarif-action/index.js#L470-L504)
- **核实**：真实。修复前三条读取路径均无 workspace 边界校验：
  1. `file://` 前缀 → `decodeURIComponent` 后直接 `fs.existsSync` 读取
  2. 绝对路径（盘符或 `/` 开头）→ 直接读取
  3. 相对路径 `path.join(root, p)`——`p` 含 `../` 可越出 sourceRoot
  4. 兜底 `find` 按文件名递归查找，范围仅限 sourceRoots
- **攻击链**：SARIF 由扫描工具对 PR 代码运行产生，恶意 PR 代码（依赖包 install 脚本等）可影响 SARIF uri 内容 → `resolveSourceFile` 读任意文件 → `enrichRegionSnippet` 将文件内容写入 snippet → 随 SARIF 上传 public-read OBS 匿名可读（CWE-22 → CWE-538 组合）
- **实施内容（硬规则 2 第 5 类：对先前接受的输入增加拒绝，用户已批准）**：
  - 边界定义：`sourceRoots`（`source_path` 输入 + workspace 兜底）的 `path.resolve` 结果即合法读取边界
  - 新增 `isWithinRoots` 前缀校验（`resolved === root || resolved.startsWith(root + path.sep)`，防 `/workspace-evil` 前缀误判）
  - `file://` 路径：decode 后统一 resolve（含 Windows 盘符形式 `file:///e:/xxx` 归一化），越界拒绝
  - 绝对路径：resolve 后越界拒绝
  - 相对路径：`path.resolve(root, p)` 归一化折叠 `../`，越出该根即拒绝
  - 兜底 find：本就限定在 sourceRoots 内，无需改动
  - 越界 uri 解析为 null → snippet 缺失但上传不中断（降级而非报错）
- **验证**：9 场景边界验证脚本（相对路径命中 / `./` 前缀 / `../` 越界拒绝 / `file://` 内可读 / `file://` 越界拒绝 / 绝对路径内可读 / 绝对路径越界拒绝 / basename 兜底 / 不存在返回 null）——8 passed, 1 skipped（basename 兜底依赖 GNU find，Windows 本地不可测，Linux runner 上生效）
- **业务逻辑影响**：SARIF uri 指向 sourceRoots 之外的合法场景（此前能读）现在会降级为 snippet 缺失。经评估，业务中 SARIF 由扫描工具对 workspace 内代码产出，uri 合法指向均在 workspace / source_path 之内，无已知合法越界场景

**⚠️ 回归缺口 1（2026-10-26 流水线实测发现，已补齐 commit `8a74bd1`）**：上轮词法前缀校验
只比对路径字符串，挡不住「路径在界内、目标在界外」的**符号链接**（`fs.statSync`/
`readFileSync` 跟随链接）——界内 symlink 指向工作区外文件，内容仍被读入 snippet 并上传
（已用测试专用假标记在流水线证实）。补齐：全部解析分支（file://、绝对、相对、find 兜底）
统一经 `confirmWithinRootsRealpath`（`realpathSync` + 二次 `isWithinRoots`）终裁，越界
symlink 返回 null；界内 symlink 与正常文件解析不受影响（等价加固）。
单测 `test/symlink-message-mask.test.js`（Windows 无 symlink 权限 2 例 skip，Linux runner 全跑）。

---

## 三、真问题·等价加固（可直接做）

### #20 execSync + escapeShellArg 单点转义防护【低】

- **状态**：✅ **已实施（2026-10-16），待自测**（fix-issue10-20-endpoints-exec 分支，commit 1178ec2，已合入 fix-security-remediation）
- **位置**：原 `execCapture`（shell 字符串执行）+ 4 处 `find "${escapeShellArg(...)}"` 调用点
- **实施内容**：新增 `findFirst` 助手，4 处 find 调用点全部改为 `execFileSync('find', args)` 数组传参，零 shell 解析；删除 `execCapture` 与 `escapeShellArg`；find 对个别子目录无权限退出非零时通过 `e.stdout` 保留部分结果，与原 `2>/dev/null | head -1` 管道行为等价；dist 已同步重建
- **附带收益**：若 #18/#16 修复后 base 已限定在 workspace 内，本条为纯防御纵深

---

## 四、真问题·需验证后修复

### #19 esdk-obs-nodejs 默认 sslVerify=false（TLS 证书校验未启用）【中】

- **状态**：✅ **已实施（2026-10-16），待真实 runner 实测**（fix-issue19-obs-tls-verify 分支，commit 7f18d16，已合入 fix-security-remediation）
- **位置**：`new ObsClient({...})` 原未传 sslVerify；SDK 内部默认 `this.sslVerify = false`，实际效果 `rejectUnauthorized: false`
- **实施内容**：构造时传 `sslVerify: obsSslCaFile || true`（默认严格校验）；新增 `obs_ssl_ca_file` 可选输入（action.yml 已注册），自托管 runner 经企业自签 TLS 代理出网时配置企业 CA 证书文件路径即可（SDK 支持传路径，内部读取为 ca 选项），无需关闭校验；dist 已同步重建
- **实测要点**：在真实自托管 runner 上验证上传链路——① 默认场景（证书链正常）应直接通过；② 企业自签代理场景需配置 `obs_ssl_ca_file` 指向企业 CA。注意后端 SarifParseServiceImpl 匿名下载链路不受本改动影响（校验仅作用于插件侧上传连接）

---

## 五、平台/后端依赖·须评审（插件侧无法单方面整改）

| Issue | 内容 | 说明 |
|---|---|---|
| #14（残留） | SARIF public-read 上传 + 源码 snippet 匿名可下载 | 已覆盖部分：ACL 可配置、凭证类 snippet 掩码。残留：默认仍 public-read，因后端 SarifParseServiceImpl 依赖匿名 HTTP GET 下载（代码注释已明确）。彻底修复 = 后端改带凭证下载/预签名 URL + workflow 切 `obs_acl: private`，属跨团队契约变化（硬规则 2 第 1 类），须后端排期评审 |

---

## 六、不是问题

| Issue | 内容 | 结论 |
|---|---|---|
| #13 | 版本级全量代码检查使用开源工具试点 | 业务功能需求（nightly 全量扫描 + SARIF 归档验收），非安全漏洞，不走安全整改流程。按常规需求流程处理 |
| #15 | CodeArts API 优先使用静态 IAM AK/SK（CWE-798） | **非问题（2026-10-13 用户决策）**。静态 AK/SK 直连 CodeArts API 是**易用性设计取舍**：配置一次即可用，无 OIDC 临时凭证的前置编排；且 defects-detail 接口暂不支持 OIDC（代码注释已明确），插件侧单方面切换会导致功能不可用。属后端能力成熟度问题，不属插件侧安全整改项。可回复说明后关闭 |
| #17 | pre-commit 工作流特权上下文执行不可信 PR 代码（pwn request） | **非问题（2026-10-13 用户决策）**。`pull_request_target` + `pull_request_comment` 触发 + 检出 merge_commit_sha + 执行 pre-commit 钩子 + 自托管 runner + `pr: write`。与 pre-commit-action #20 同类，**该工作流模式是平台 CI 门禁的业务设计确定**——PR 门禁必须在特权上下文对 PR 合并结果执行检查，属门禁系统的固有形态；且 pre-commit job 未传入 ROBOT_TOKEN，凭证与不可信代码已隔离（无凭证泄露路径）；issue 引用的 `allow-unsafe-pr-checkout: true` 在当前工作流中也不存在。插件侧无可整改项，可回复说明后关闭 |

---

## 七、2026-10-29 现状复核（基准 upstream/main HEAD）

PR !18 合入后，逐条对照 `upstream/main` 代码复核全部 open issue（不按标题定性），结论：

| Issue | 复核结论 | 证据（main） | 处置 |
|---|---|---|---|
| #10 公网地址 | 已整改 | `src/config/endpoints.js` 集中配置；`index.js:39-41` 统一 require；剩余命中为 vendor 内联产物与 schema 声明 | ✅ 已评论并按证据关闭（2026-10-29） |
| #12 SENS-15 snippet 明文 | 已整改 | `index.js:415-439` mask*，`569-598` 覆盖 snippet/contextRegion/message | ✅ 已评论并关闭 |
| #16 / #18 uri 任意路径读取 | 已整改 | `index.js:467-485` `isWithinRoots` + `confirmWithinRootsRealpath`；`497-535` 全分支校验 | ✅ 已评论并关闭 |
| #20 execSync 拼 find | 已整改 | `index.js:95` `execFileSync('find', args)`；残留 `index.js:116` `sleep` 为整型常量，无外部输入 | ✅ 已评论并关闭 |
| #30 不安全协议 | 已整改 | `index.js:934-944` `sslVerify: obsSslCaFile \|\| true` | ✅ 已评论并关闭 |
| #11 SENS-14 | 部分整改 | 掩码已做；`convertOutDir`（`index.js:802-804`）无清理；`ACL: 'public-read'`（`index.js:964`）未改 | 已评论说明：tmp 拆到 #27，ACL 暂缓，保持 open |
| #25 读取+公读泄露链 | 部分整改 | 前两跳已斩断（边界校验 + 掩码）；第三跳 ACL 依赖后端 | 已评论说明，保持 open |
| #27 临时文件不清理 | **未整改** | `convertOutDir` 仅 `mkdirSync`，全仓无 `rm/unlink` | 待提 PR（等价加固：`finally` 清理） |
| #31 日志注入 | **未整改** | `sanitizePath` 仅脱敏 IP；`CodeArtsCheckApi.js:178-183` 直接拼 `resp.body`；parser warnings 输出报告原文 | 待提 PR（日志清洗 CRLF/控制字符） |
| #28 zip 产物入库 | **未整改** | `openlibing-upload-sarif.zip` 仍被跟踪；`.gitignore` 已有 `*.zip` 但对已跟踪文件无效；zip 仅 `zip.js` 生成、源码不消费 | 待提 PR（`git rm --cached`，最小改动） |
| #26 上传约束缺失 | **未整改** | 目录扫描仅过滤 `.sarif`；显式文件路径不校验扩展名；`putObject` 无大小上限 | 待评审（新增输入拒绝 + 阈值，硬规则 2 第 5/6 类） |
| #29 SSRF（region 拼 host） | **未整改** | `resolveRegion()` 无格式/白名单校验，region 直接进 `codecheck-ext.{region}.myhuaweicloud.com` | 待评审（新增输入拒绝） |
| #24 workflow pwn request | **未整改，且与 #17 结论冲突** | `.gitcode/workflows/pre-commit.yml:45-48` 仍为 `pull_request_target` + 检出 PR head + `allow-unsafe-pr-checkout: true` + `npm install` | 需复判：第六节 #17 判定"`allow-unsafe-pr-checkout` 不存在"已与当前代码不符，须重新对齐结论 |

### 待办 PR 计划

| 批次 | 覆盖 issue | 性质 | 前置条件 |
|---|---|---|---|
| PR-A | #27 + #31 | 等价加固（临时文件治理 / 日志脱敏），同一 index.js 日志与临时目录链路，合并一 PR | 无 |
| PR-B | #28 | 产物治理（`git rm --cached` + 确认 `.gitignore`） | 无 |
| PR-C | #26 | 输入拒绝 + 资源阈值 | 《业务逻辑影响评估》经用户批准 |
| PR-D | #29 | region 白名单/格式校验 | 《业务逻辑影响评估》经用户批准 |
| PR-E | #24 | 工作流结构（secrets 隔离） | 与 #17 结论对齐后定方案 |

ACL 私有化（#11/#25 残留）：维持 `public-read`，标注暂缓，待后端支持带凭证/签名 URL 下载后统一实施（2026-10-29 用户决策）。
