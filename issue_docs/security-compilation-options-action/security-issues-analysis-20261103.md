# security-compilation-options-action 安全 issue 定性分析（2026-11-03）

> 分析基准：`upstream/master` HEAD `47da3ca`（2026-11-03），逐条对照源码核实，不按 issue 标题定性。
> 本批覆盖 open 的安全 issue：#44–#65（21 条 CVE）、#21、#24；功能类 #33（api-scan workflow）、#67（JS 插件构建流水线）不属于安全整改范围，排除。
> 关联威胁分析报告：`architecture_desgin/security-compilation-options-action/[security-compilation-options-action]安全威胁分析报告.md`。

## 汇总

| 分类 | Issue | 处理建议 |
| ---- | ----- | -------- |
| 真问题·等价加固（依赖升级），已整改 | #44–#65（21 条） | 全部为 `axios@1.17.0` 已知漏洞，已升级到 `1.21.0`（PR #38，commit `fd83b1f`），lock 重置、dist 重建、`npm test` 通过 |
| 非问题（2026-11-03 用户决策） | #21 | 信任边界是 CI job + 平台凭证，客户端自报哈希而后端不校验无实际防护效果；溯源增强转功能需求排期 |
| 已基本修复·残余非问题/观察项 | #24 | FIND-08 的主要点已由 Ref #35~#38 收敛；残余 SDK 声明打印、traceback 路径、结果文件权限，建议按非问题/观察项归档或做可选最小加固 |
| 非安全（功能 issue） | #33 #67 | 功能需求，不纳入安全整改 |

---

## 一、#44–#65 依赖 CVE（21 条，axios）

### 1.1 共性核实

| 项目 | 核实结论 |
| ---- | -------- |
| 漏洞组件 | 全部为 `axios`，报出 `1.17.0`（21 条逐一确认：`漏洞归属组件：axios` / `漏洞归属的版本：1.17.0`） |
| 依赖声明 | [package.json](file:///e:/work/huawei/fork/security-compilation-options-action/package.json) `"axios": "^1.6.0"`；lock 中 `node_modules/axios` 解析为 `1.17.0`（唯一 axios 条目） |
| 使用点 | [CicdUploader.js:329](file:///e:/work/huawei/fork/security-compilation-options-action/src/uploaders/CicdUploader.js#L329) 仅一处 `axios.post(url, body, { headers, timeout })`（AK/SK 模式上报；OIDC 模式走 SDK 的 `callApig`） |
| 修复版本 | CVE-2026-67320 修复于 `1.18.0`；CVE-2026-101908 修复于 `1.20.0`；其余条目的修复版本均 ≤ 1.20.0。取 `>=1.20.0` 全覆盖 |
| 可用版本 | npm registry 当前最新为 `1.21.0` |

### 1.2 风险与可利用性

- 多条为 prototype-pollution 读侧 gadget / proxy 与 headers 继承类问题，需要应用内已存在原型污染原语才可利用；本插件无动态拼接对象/无 `Object.assign` 合并外部配置的路径，实际可利用面很低。
- 但 SCA 扫描直接以 lock 版本判定，升级到修复版本即为标准整改方式，且 axios 在本仓只用于一次 POST，1.x 内升级 API 完全兼容。

### 1.3 整改方案（建议）

1. `package.json`：`"axios": "^1.6.0"` → `"^1.21.0"`（或 `^1.20.0`，按用户偏好；1.21.0 为当前最新）。
2. `npm install` 重置 `package-lock.json`（确认 `node_modules/axios` 版本、integrity 同步）。
3. `npm run package` 重建 `dist/`（axios 由 ncc 内联进产物，禁止手改 dist）。
4. `npm test`（上游已引入 node test framework，`node --test`）。
5. 单 PR 覆盖全部 21 条 CVE（同一根因、同一依赖、同一行改动），commit body 逐个 `Refs #44` … `Refs #65`；PR 描述标注关联 issue 清单。

### 1.4 分类与影响声明

- 分类：**依赖升级（CVE 整改）**，不属业务逻辑改动 —— 请求方法/路径/头/body/超时与返回值结构均不变，OIDC 路径不经过 axios。
- 需注意：依赖升级不在硬规则 1 白名单的「依赖固定（版本不变）」条目内，按「拿不准归入须评审」口径，**编码前需用户批准本方案**。

### 1.5 实施记录（2026-11-03）

- 已按方案实施：`package.json` `axios` → `^1.21.0`；`package-lock.json` 重置（axios 1.21.0、form-data 4.0.6）；`dist/index.js` 由 `npm run package` 重建（产物内 axios `VERSION = "1.21.0"`）。
- 验证：`npm test` 1/1 通过。
- 交付：commit `fd83b1f`，PR [#38](https://gitcode.com/openlibing/security-compilation-options-action/merge_requests/38)（已打 `ai-assisted`），已同步统一测试分支 `fix-security-remediation`（HEAD `cd20510`）。
- 业务逻辑影响声明：**本改动未触及业务逻辑**。

---

## 二、#21 合规结果端到端可篡改【高危，FIND-05】

### 2.1 现状核实（`upstream/master`）

| 原问题点 | 现状 | 结论 |
| -------- | ---- | ---- |
| 产物仅存在性检查，无内容校验 | [scanner.js:96-102](file:///e:/work/huawei/fork/security-compilation-options-action/src/scanner.js#L96-L102) 仍只做 `existsSync` 后进入扫描，无产物哈希/大小校验 | 未修复 |
| 结果写盘后重读 | 扫描结果写入 `outputFile` 后再读取上报，路径可由 `output` 输入指定 | 未修复 |
| 上报体只签 body，无溯源绑定 | [CicdUploader.js:270-300](file:///e:/work/huawei/fork/security-compilation-options-action/src/uploaders/CicdUploader.js#L270-L300) payload 含 gitUrl/packageName/pipelineRunId/runNumber/pipelineName 等，**无产物 SHA256、无产物大小、无构建任务 ID** | 未修复 |

### 2.2 定性结论：非问题（2026-11-03 用户决策）

- **信任边界**：本插件的信任边界是 CI job + 平台凭证（OIDC token / AK-SK）。扫描与上报在同一 action step 内完成，签名只保证 body 在传输中未被改。
- **哈希绑定挡不住真实威胁**：若攻击者能在同一 job 内篡改结果 JSON，他同样持有该 job 的凭证，可直接伪造上报，客户端哈希绑定无济于事。
- **后端无法独立验证**：后端只解析上报 JSON，不重新扫描、也不单独持有构建产物；客户端自报 SHA256/大小而后端不校验 = 无安全增益（自证循环）。
- **真正意义的端到端校验**：需要后端自行拉取产物重算哈希或重新扫描，并与构建记录比对，属跨仓功能演进，不是插件侧安全整改。
- **衍生决策**：「上报体带产物 SHA256/大小/构建任务 ID」作为**可选溯源增强**，走功能需求排期，将来后端具备校验能力后再实施，不作为本轮安全整改项。
- 残余说明：PR 作者提交「干净产物过门禁、发布另一份产物」属构建/发布链路问题，不在本插件的防护范围。
- 知识库归档：2026-11-03 用户决策**暂不归档**至 playbook / ai_memory，结论仅保留在本定性文档。

---

## 三、#24 凭证与内部路径写入 CI 日志/工作区【中危，FIND-08】

### 3.1 逐点核实（对照报告 FIND-08 证据）

| 原问题点 | 现状（`upstream/master`） | 结论 |
| -------- | ------------------------- | ---- |
| OIDC 客户端 error 级打印 Token 声明（iss/aud/azp/sub），`mask()` 仅保留首六尾四 | 来自 `@openlibing/huaweicloud-oidc-client@0.0.5`，被 ncc 内联进 `dist/index.js`；仍存在 `_printTokenClaims(claims, error)` 与 `mask(head=6, tail=4)`。核对了 SDK `0.0.6`（最新）：**同样保留该行为**，且新增 `engines.node >=18`、依赖 undici 5.x | 属上游 SDK 侧问题，本仓无法通过改源码消除；声明字段非凭证，SK 不落日志（既有结论）→ 观察项/非问题 |
| `gitUrl` 仅去除 HTTPS userinfo | [index.js](file:///e:/work/huawei/fork/security-compilation-options-action/src/index.js) 已泛化为任意 scheme 的 userinfo 剔除（Ref #38），保留 `ssh://git@host` 标准用户名 | 已修复 |
| 子进程 stdout/stderr 原样回显 | [SecOptionDetector.js:94-109](file:///e:/work/huawei/fork/security-compilation-options-action/src/detectors/SecOptionDetector.js#L94-L109) 已改为 `sanitizeProcessOutput`（控制字符折叠 + 尾部 64KB 截断），Ref #37 | 已修复（日志注入面） |
| Python `traceback.print_exc` 打印完整异常栈 | `src/bin/sec_option_scan.py` 仍保留 `traceback.print_exc(file=sys.stderr)`；但 JS 侧已统一清洗换行/控制字符并截断，**不再能伪造日志行**；traceback 文本仍包含 runner 临时目录绝对路径 | 部分残余（内部路径可见），低危 |
| 结果 JSON 默认权限写入工作区 | `scanner.js` 未指定 `mode`，按 umask 默认写盘 | 未加固 |

### 3.2 建议定性

- **主结论：已基本修复**。报告 FIND-08 的核心风险（日志注入、凭证/URL 内嵌凭证落日志、子进程输出原样回显）已由 Ref #35~#38 系列改动收敛。
- 残余三项按低危处理：
  1. SDK 声明打印：上游 SDK 问题，需 SDK 仓单独整改后再升级（本仓无法改 dist）；
  2. traceback 内部路径：默认环境为 runner 临时目录，运维可读性依赖它；如需收敛可改为只输出异常类型+消息（会降低排查效率）；
  3. 结果文件权限：可 `fs.writeFileSync(..., { mode: 0o600 })` 收紧（Windows 无效，不影响 Linux 正常读取，属「临时文件治理/权限收紧」白名单）。

### 3.3 实施记录（2026-11-03，用户裁决：不影响业务逻辑前提下加固）

| 加固点 | 改动 | 分类 |
| ------ | ---- | ---- |
| traceback 内部路径 | `src/bin/sec_option_scan.py` 解压失败分支删除 `traceback.print_exc`，改为输出 `Warning: failed to extract <basename>: <sanitized msg>` + `Extraction error type: <ExceptionType>`；同时移除 `import traceback` | 等价加固（仅日志文本） |
| 结果文件权限 | `src/scanner.js` 写盘后追加 `fs.chmodSync(outputFile, 0o600)`（try/catch 包裹，Windows 下 chmod 受限时不阻断）；因结果文件由 Python 检测器预先创建，`writeFileSync` 的 `mode` 不生效，必须后置 chmod 修正 | 等价加固（临时文件/产物权限收紧） |

- 未加固项：OIDC SDK 的 token 声明打印（上游 `@openlibing/huaweicloud-oidc-client` 问题，`0.0.6` 仍存在，需 SDK 仓整改）。
- 验证：本地用截断 15 字节的真实 tar.gz 触发解压异常 → 输出仅含 `Extraction error type: EOFError`，无 `Traceback`、无 runner 绝对路径，exit=0；`node dist/index.js` 全链路跑通（结果文件正常生成、上报失败不阻断）；`npm test` 1/1 通过；dist 由 `npm run package` 重建（产物内含 `chmodSync(outputFile, 0o600)`）。
- 交付：commit `5025af9`（traceback + mode）+ `b8e8613`（chmod 后置修正），PR [#39](https://gitcode.com/openlibing/security-compilation-options-action/merge_requests/39)（base `fix-sec-axios-cve`，已打 `ai-assisted`），已同步统一测试分支 `fix-security-remediation`（HEAD `d1da60c`）。
- 端到端验证：`openlibing-cicd-test` PR #280 挂载 `security-compilation-options-action@fix-sec-log-hardening`，新增 job 断言结果文件 `stat -c '%a'` = `600`；2026-11-03 16:39 流水线全绿（`ci-pipeline-passed`），确认加固生效且原有 pre-commit 门禁未受影响。
- 业务逻辑影响声明：**本改动未触及业务逻辑**（仅日志文本与结果文件权限；扫描逻辑、上报 payload、输出契约、退出码均不变；结果文件仍由同一进程同一用户读写）。

---

## 四、待用户裁决项

1. **CVE 批次**：已裁决并实施（2026-11-03）——`axios ^1.21.0`，单 PR #38 覆盖 #44–#65。
2. **#21**：已裁决（2026-11-03）——**非问题**，溯源增强转功能需求排期，不再作为安全整改项。
3. **#24**：已裁决（2026-11-03）——在不影响业务逻辑前提下做等价加固（traceback 收敛 + 结果文件 `0600`），已实施见 3.3；待端到端验证通过后再决定是否评论/关闭 issue。
4. **PR 拆分**：CVE 批次 1 个 PR（#38），#24 加固 1 个 PR（#39，base 为 `fix-sec-axios-cve`，待 #38 合入后自动归并到 master）。

## 五、环境说明

- 本地 `security-compilation-options-action` 当前在 `fix-sec-symlink-and-budget` 分支，落后 `upstream/master` 15 个提交（该分支改动已通过 `!34` 合入 master）；工作区显示为 modified 的文件经 `git diff --ignore-cr-at-eol` 核对为**纯 CRLF 差异**，无内容改动，整改将基于 `upstream/master` 新建分支，不动该分支。
