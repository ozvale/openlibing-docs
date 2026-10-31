# code-metrics-action 安全 issue 定性分析（20261027）

> 数据基线：主仓 `openlibing/code-metrics-action` upstream/master `5f76d6b`（src 布局迁移已完成，issue 中标注的 src 位置已逐一核对）。
> 流程：本文档为 Phase 1 定性产物，**所有定性待用户逐条确认后方可进入整改**（硬规则：先文档、后代码）。
> 跨仓先例引用：security-compilation-options-action（下称 sec-comp）、upload-sarif-action、pre-commit-action 已裁决结论。

## 0. 结论速览

| 分类 | Issue | 处理建议 |
|---|---|---|
| 真问题·等价加固（可直接做，均有跨仓先例） | #45 #66 #47 #60 #64 #51 #50 #42 #49 #57 #71 | 日志卫生组 + 进程执行组 + 上传器卫生组，见第 2 节 PR 计划 |
| 真问题·须用户评审（凭证传递通道 / 供应链固定） | #36 #46 #55 #59（同一问题 4 条）；#58 #69 #63（obsutil 下载完整性） | 方案见第 3 节，获批后才编码 |
| 非问题·建议归档 | #37 #38 #39 #40 #41 #43 #44 #62 #68 #70 | 信任模型同构 / 平台兜底 / 设计参数非凭证，见第 4 节 |
| 文档补全（非安全漏洞） | #67 | action.yml 补声明 config-file / min-lines，默认值与现行为一致 |
| 非安全需求（不在本流程范围） | #53 | feat(api-scan)：功能需求，转正常开发流程 |

## 1. 汇总表（open issue 全集 30 条）

| 分类 | Issue | 处置 |
|---|---|---|
| 等价加固·待实施 | #45 #66 #47 #60 #64 #51 #50 #42 #49 #57 #71 | 按 PR A/B/C 分组实施（第 2 节） |
| 须评审·待批准 | #36 #46 #55 #59；#58 #69 #63 | 第 3 节出方案，用户裁决后进 PR D/E |
| 非问题·待确认归档 | #37 #38 #39 #40 #41 #43 #44 #62 #68 #70 | 第 4 节，附结论关闭 |
| 文档补全 | #67 | 并入 PR C（契约文档化，无行为变化） |
| 功能需求 | #53 | 排除出安全整改范围 |

## 2. 等价加固组（可直接实施）

### 2.1 #45 + #66 —— gitUrl 凭据清洗仅覆盖 https（同一问题）

| 项 | 内容 |
|---|---|
| 位置 | `src/index.js:144`：`remoteUrl.replace(/https:\/\/[^@]+@/, 'https://')` |
| 核实 | 属实。`http://user:pass@host/`、`ssh://git@token@host/` 等形态不清洗，凭证明文进日志（`core.info('gitUrl: ...')`）与上报 payload |
| 整改 | 正则泛化为任意 scheme 的 userinfo 剔除，保留 `git@` 标准用户名（**与 sec-comp #38 已批准实施完全同款**）：`remoteUrl.replace(/([a-zA-Z][a-zA-Z0-9+.-]*:\/\/)(?!git@)[^@\/]+@/, '$1')` |
| 分类 | 等价加固（仅去除内嵌凭证，其余形态与原行为逐字一致） |

### 2.2 #47 —— obsutil 执行日志脱敏不完整泄露 AK

| 项 | 内容 |
|---|---|
| 位置 | `src/uploaders/CoderepoUploader.js:433`：`args.map(a => (a.startsWith('-k=') \|\| a.startsWith('-t=') ? ...` |
| 核实 | 属实。掩码只覆盖 `-k=`（SK）与 `-t=`（SecurityToken），`-i=`（AK/accessKeyId）明文打印 |
| 整改 | 掩码条件补上 `-i=`（单行改动） |
| 分类 | 等价加固（日志脱敏白名单第 1 类） |

### 2.3 #60 —— 日志输出本机绝对路径

| 项 | 内容 |
|---|---|
| 位置 | `src/index.js:237`（`Source directory: ${config.sourceDir}` 绝对路径）；`src/utils/fileCollector.js` 多处 `[WARN] 路径不存在: ${absolutePath}`；`src/detectors/DuplicationDetector.js` `[WARN] Failed to read file ${file}` 等 |
| 核实 | 属实。runner 机器绝对路径（含用户名/目录结构）落入 CI 日志 |
| 整改 | 与 sec-comp #36 同款：删除/降级 debug 级路径日志，info 级改 basename 或相对 sourceDir |
| 分类 | 等价加固（日志脱敏） |

### 2.4 #64 —— 日志注入

| 项 | 内容 |
|---|---|
| 位置 | 注入面：`branchName`（ATOMGIT_REF_NAME 环境变量）、`gitUrl`（git remote）、`detailLink`/`tip`（服务端响应）经 `core.info`/`console.log` 与 `ATOMGIT_OUTPUT` 写出（`src/index.js:244-247, 268-296`）；服务端 `msg`/`adviceMsg` 直接进 `console.error`（`CoderepoUploader.js:655-658`） |
| 核实 | 属实。控制字符（CRLF）可伪造日志行/平台输出行 |
| 整改 | 与 sec-comp #37 同款：新增 `src/utils/sanitize.js`（`sanitize()` / `sanitizeProcessOutput()`），接入全部外部字符串输出点（含 ATOMGIT_OUTPUT 的 detailLink/tip 行） |
| 分类 | 等价加固（清洗仅作用于输出文本，不改上报契约） |

### 2.5 #51 —— 上报 baseUrl 明文 http fallback

| 项 | 内容 |
|---|---|
| 位置 | `src/uploaders/CoderepoUploader.js:263`：`this.baseUrl = config.coderepoUrl \|\| 'http://localhost:8080'` |
| 核实 | 属实且为**死 fallback**：调用点 `src/index.js:96` 恒传常量 `https://apig.openlibing.com:443`，fallback 不可达 |
| 整改 | 与 sec-comp #26/#31 同款：删除 fallback，直接 `this.baseUrl = config.coderepoUrl` |
| 分类 | 等价加固（不可达死代码删除） |

### 2.6 #50 + #42 —— 全量上报数据写临时目录未限权限 / 敏感数据落本地临时文件

| 项 | 内容 |
|---|---|
| 位置 | `src/uploaders/CoderepoUploader.js:377`：`fs.writeFileSync(tmpFile, JSON.stringify(fullPayload), 'utf-8')`，tmpFile 在 `os.tmpdir()`，默认权限（Linux umask 通常 644） |
| 核实 | 属实。全量上报文件含代码重复块内容（contentB64），同机其他账户/进程可读；文件名 `code-metrics-${Date.now()}.json` 毫秒时间戳可预测。finally 中已有 unlink 清理（#42 的清理诉求已满足），缺权限收紧 |
| 整改 | `writeFileSync(tmpFile, data, { encoding: 'utf8', mode: 0o600 })`；文件名补随机段（`crypto.randomUUID()`）——playbook「临时文件治理/可预测临时文件名」同款 |
| 分类 | 等价加固（不改文件用途与生命周期语义，仅收紧权限+去可预测性） |

### 2.7 #49 + #57 —— scc 命令拼接未经转义（同一问题）

| 项 | 内容 |
|---|---|
| 位置 | `src/detectors/SlocDetector.js:114-118`：`const cmd = \`"${this.sccPath}" ${args.join(' ')}\`; execSync(cmd, ...)` |
| 核实 | 属实。shell 字符串拼接执行；args 含 sources（当前为固定 `'./'`）与 `--include-ext`（来自 `allowed-extensions` input，workflow 配置方可控）。当前实际注入面窄（配置方受信），但属 playbook「shell 命令拼接注入」标准形态 |
| 整改 | `execSync(cmd)` → `execFileSync(this.sccPath, args, {...})`（参数数组直传，不经 shell），输出行为等价 |
| 分类 | 等价加固（playbook 第 5 类同款） |

### 2.8 #71 —— Python 模块遮蔽导致任意代码执行（pip/lizard）

| 项 | 内容 |
|---|---|
| 位置 | `src/index.js:247-260`：`execSync(['python3', ...pipInstallArgs].join(' '), { cwd: 未设置(继承工作区) })` |
| 核实 | 属实。`python3 -m pip` 会把 cwd 加入 sys.path 首位，被测仓库根目录的 `pip.py` 可遮蔽官方 pip 实现任意代码执行——**与 sec-comp #39 完全同款** |
| 整改 | 同款修复：`fs.mkdtempSync` 临时空目录作为 cwd 执行安装，finally 清理；顺带把字符串 join 改 execFile 参数数组（消除同类拼接面） |
| 分类 | 等价加固（仅改变执行 cwd 与调用方式，安装结果不变） |

### 2.9 #67 —— config-file 与 min-lines 输入未声明且未文档化

| 项 | 内容 |
|---|---|
| 位置 | `action.yml`（inputs 仅声明 exclude-dirs / allowed-extensions / output / apig-app-key / apig-app-secret / obs-ak / obs-sk）；`src/index.js` 实际读取 `config-file`、`min-lines` |
| 核实 | 属实。两个输入经 env 兜底逻辑实际生效但未在 action.yml 声明（平台表单不可见） |
| 整改 | action.yml 补声明：`config-file`（default ''，与现行为一致）、`min-lines`（default '10'，与代码默认一致）。纯契约文档化，无行为变化 |
| 分类 | 文档补全（非安全漏洞）；并入 PR C |

## 3. 须用户评审组（获批后才编码）

### 3.1 #36 + #46 + #55 + #59 —— OBS 凭证经 obsutil 命令行参数传递（同一问题，4 条重复 issue）

| 项 | 内容 |
|---|---|
| 位置 | `src/uploaders/CoderepoUploader.js:416-437`（uploadToOBS）：OIDC 模式 `-i=AK -k=SK -t=Token`、AK/SK 模式 `-i=AK -k=SK` 经 argv + `stdio:'inherit'` |
| 核实 | 属实。同机进程可经 `/proc/<pid>/cmdline` 读取凭证；CI 平台掩码只作用于日志，不覆盖进程表 |
| 部署事实（2026-10-27 补充） | 本仓自身 workflow 已声明 `permissions: id-token: write`（OIDC 模式），当前实际暴露的是 STS 临时凭证（短时效）；AK/SK 模式为存量兼容通道，静态凭证 argv 面仍在。两模式均需覆盖（硬规则 4：禁止半整改双通道并存） |
| 方案 A（**已批准，2026-10-27 用户裁决**） | **obsutil → esdk-obs-nodejs SDK 迁移**（upload-sarif-action PR #7 已验证的同款路径）：凭证全程内存传递（ObsClient 构造参数），消除 argv 暴露面。改动量中等（uploadToOBS 重写 + putObject + dist 重建），上传契约不变（同桶/同 key/私有对象）。一次性覆盖 OIDC（STS 三件套）与 AK/SK（静态）两个通道 |
| 分类 | 凭证传递加固（白名单第 7 类），鉴权协议与语义完全等价；但方案选择需用户裁决 |
| 合并建议 | 4 条 issue 同一代码段，**必须合并一个 PR**（硬规则 4） |

### 3.2 #58 + #69 + #63 —— obsutil 在线下载无校验直接解压执行（3 条重叠 issue）

**与 3.1 合并整改（2026-10-27 用户裁决）**：两组 issue 的根因同为「依赖 obsutil CLI 子进程」——3.1 是凭证经 argv 传给 obsutil，3.2 是 obsutil 本身运行时在线下载。3.1 已批准的方案 A（obsutil → esdk-obs-nodejs SDK 迁移）会整体删除 `ensureObsutil()` 下载链路，**3.2 的三条 issue 随迁移自动解决**（指控的下载/解压/执行行为不复存在，同 sec-comp #29/#34「命中代码已消失」形态），不单独出 PR，随 PR D 一并关闭。#63 的「scc」部分本就不成立——scc 为内置随插件分发（`dist/bin/scc` 提交在仓内），无运行时下载，归档评论中澄清。

## 4. 非问题组（建议附结论关闭，待用户逐条确认）

| Issue | 内容 | 非问题理由 | 同构先例 |
|---|---|---|---|
| #37 | 跨租户 OBS object-key 混淆（owner/repo 取自 git remote） | 信任模型同构：能改 workflow / 仓库 remote 的是配置方（有仓库写权限），本就能控制扫描与上报内容；写入统一桶需平台 OBS 凭证（OIDC STS / obs-ak），key 前缀只影响自身数据归属；后端按 objectKey 下载有固定前缀约束 | sec-comp #40③、upload-sarif #41（artifact-path 受信） |
| #38 | YAML 解析资源耗尽 | config-file 为 workflow 配置方受信输入（信任模型同构）；js-yaml 4.x `yaml.load` 默认 DEFAULT_SCHEMA（安全 schema，无自定义标签 RCE 面）；别名爆炸防御属资源限制增强非安全整改（可随 #39 同口径处理） | upload-sarif #25（配置方受信输入） |
| #39 | 无界资源消耗 + 上报无重试 | 资源面：平台对容器/job 有超时管理（用户已确认 GitCode 侧管理，多仓既定裁决），本插件 schedule/push master 触发（非 PR 门禁），最坏损失=当晚数据次日重扫补齐；上报面：**已有设计兜底**——OBS 先落盘 + report 失败走「平台保底定时任务（入参 objectKey）补导入」（`CoderepoUploader.js:346-355` 注释明确）；资源阈值/重试属健壮性增强 | sec-comp #40②（风险接受）、#27（平台超时兜底） |
| #40 | 上报归属信任本地 git/env 元数据 | 环境变量与 git 元数据即 Actions 信任边界：能写这些的主体（runner/workflow 配置方）本就具备改 workflow、在 runner 执行任意代码的能力，「伪造归属」零增量收益 | upload-sarif #20（同构裁决） |
| #41 | config/input 可覆盖并关闭检测器 | config-file / exclude-dirs / allowed-extensions 均为 workflow 配置方输入；关闭检测器=配置方对自家仓库扫描口径的合法选择，非攻击面 | sec-comp #25（输出/配置受信） |
| #43 | 不可信 PR 代码在自托管执行机执行（pwn-request） | `pre-commit.yml` 的 `pull_request_target` + 检出 merge commit + `allow-unsafe-pr-checkout: true` 是自有门禁的有意设计（始终读默认分支最新门禁配置、必须执行 PR 代码才能检查它）；ROBOT_TOKEN 仅注入 label job，与执行 PR 代码的 pre-commit job 隔离 | **项目记忆既有裁决**（pre-commit-action 同形态，多仓已归档） |
| #44 | CI 工作流第三方 Action 可变 tag 引用 | `uses` 全部为自家 Action（openlibing/code-metrics-action@v1.0.3 / pr-label-action@v1.0.0 / pre-commit-action@v1.0.2）或平台内置（checkout/setup-node/setup-go），无第三方；自家可变 tag 不构成实际供应链风险；可选低优先级强化：改 commit SHA（须随发版维护） | sec-comp #18（同构裁决） |
| #62 | 重复代码检测使用 MD5 弱哈希作为文件指纹 | MD5 在此为**内容匹配指纹非安全控制**：用途是识别相同代码块（非对抗场景），碰撞只影响度量精度且无攻击收益（攻击者伪造碰撞只会让自己的重复率数字失真）；换 SHA256 属算法升级，无安全增益 | ——（本仓特性，机制说明） |
| #68 | oidc-client 依赖内置华为云账号 ID | `accountId: '4d29a984c4fe4e6eb5d404a853d0084e'`（dist/index.js:3671 内联）是 IAM **标识符非凭证**——构造 `iam::${accountId}:agency:${agencyName}` URN 换取 STS 临时凭证的必需设计参数，泄露无安全后果（账号 ID 非秘密）；且属第三方 SDK（@openlibing/huaweicloud-oidc-client）内联产物，硬规则 6 第 3 类 | sec-comp #24 分析中同 SDK 已核（SK 无日志落点） |
| #70 | fileCollector 收集 CI 配置目录内容随重复块明文外发 | `.gitcode` 纳入扫描是**有意的功能修复**（commit cbc3f95：按「. 开头」一刀切剪枝导致本地收集范围 < scc 全量范围，重复率被系统性低估）；扫描+上传本仓代码内容（重复块快照）是度量下钻页的**产品核心功能**；触发仅 push master + workflow_dispatch（非 PR 代码）；上传走 OIDC + 私有桶 | ——（本仓产品定义） |

## 5. PR 分组计划

| PR | 分支名 | Issue | 内容 |
|---|---|---|---|
| PR A | fix-sec-log-hygiene | #45 #66 #60 #64 | gitUrl 正则泛化 + 路径脱敏 + sanitize 统一清洗（#47 移入 PR D，见第 7 节） |
| PR B | fix-sec-scc-exec | #49 #57 #71 **#29** | scc execFileSync 数组化（SlocDetector + DuplicationDetector 两处调用点）+ pip 临时空目录 + execFile 数组化 |
| PR C | fix-sec-uploader-hygiene | #51 #50 #42 #67 **#22** | 死 fallback 删除 + 临时文件 0600/随机名 + action.yml 补声明 + 公网地址收敛/白名单登记 |
| PR D（**已批准方案 A**，2026-10-27） | fix-sec-obs-sdk-migrate | #36 #46 #55 #59 **#58 #69 #63** **#23 #24 #33 #47** | obsutil → esdk-obs-nodejs SDK 迁移：凭证内存传递消除 argv 暴露 + ensureObsutil 下载链路整体删除（3.2 三条 + #33 随迁移解决；#47 的 obsutil 掩码日志随 uploadToOBS 重写消失，同「命中代码已消失」形态） |
| 归档 | —— | #37 #38 #39 #40 #41 #43 #44 #62 #68 #70 **#30 #31 #32 #34** | 附结论关闭（第 4 节 + 第 7 节理由） |

## 6. 裁决状态

- [x] 等价加固组 PR A/B/C 方案确认（2026-10-28 用户裁决「有先例就采取先例的解决方案」——11 条整改手法全部与 sec-comp/pre-commit/upload-sarif 已裁决先例同款或同构，按先例直接实施）
- [x] PR D 方案裁决：**方案 A（SDK 迁移）**，3.1（4 条）+ 3.2（3 条）合并整改（2026-10-27 用户裁决）
- [x] PR E：**取消**——3.2 三条随 PR D 的 SDK 迁移自动解决，无需独立 PR
- [x] 非问题组 10 条逐条确认归档（2026-10-28 用户确认，已全部附结论评论并关闭：#37 #38 #39 #40 #41 #43 #44 #62 #68 #70）
- [x] #53 移交功能需求流程确认（2026-10-28 用户确认，已附移交说明并关闭）
- [x] 20261028 新增 8 条（#22 #23 #24 #29 #30 #31 #32 #33 #34）定性确认（2026-10-28 用户裁决同规则：4 条并入既有 PR、4 条非问题归档，见第 7 节）

## 7. 20261028 新增 issue 定性（安全团队重发批次）

> 2026-10-28 发现 open issue 中有一批定性文档基线（10-27）之后重发/新增的 issue。按用户裁决规则「有先例 → 采用先例方案；无先例 → 报评审」逐条核实，8 条全部有先例，无需单独评审。

### 7.1 与已裁决项同款、并入既有 PR（5 条）

| Issue | 指控 | 核实 | 归宿 |
|---|---|---|---|
| #23 #24 | obsutil 以命令行参数传递 STS 临时凭证 / 静态 AK-SK | 与 #36 #46 #55 #59 同一问题（OIDC/AK-SK 两模式拆条重发），位置同为 `CoderepoUploader.js` uploadToOBS 的 argv 传递 | 并入 PR D（SDK 迁移一次性消除两通道） |
| #29 | OS 命令注入（shell 拼接，allowed-extensions 可控） | 与 #49 #57 同款（指控描述一致），且漏了第二处调用点：`DuplicationDetector.js:315` 的 scc recount 同为 execSync 字符串拼接 | 并入 PR B（两处调用点统一 execFileSync 数组化） |
| #33 | 运行时下载并执行 obsutil 无完整性校验 | 与 #58 #69 #63 同款（ensureObsutil 下载链路） | 随 PR D 迁移自动解决（下载行为消失） |
| #47（原 PR A） | obsutil 执行日志脱敏不完整泄露 AK | 掩码只覆盖 `-k=`/`-t=`，`-i=`（AK）明文。PR D 重写 uploadToOBS 后 obsutil 执行及其掩码日志整体消失（命中代码已消失形态，同 sec-comp #29/#34） | 移入 PR D |

### 7.2 非问题归档（4 条）

| Issue | 指控 | 非问题理由 | 先例 |
|---|---|---|---|
| #22 | dist/index.js 等硬编码公网地址 | **部分成立，小整改**：① PyPI 华为镜像 → 环境变量注入（默认值不变，pre-commit #12 同款）；② APIG 网关地址 = 自家平台部署固定端点、PyPI 官方源 = 功能必需 → 白名单登记（gitleaks:allow）；③ GitHub OIDC 颁发者 URL 位于第三方 SDK（oidc-client）内联产物且为文档性说明文案，不可改无需改 | pre-commit-action #12；sec-comp #24 同 SDK 已核 |
| #30 | output 路径遍历任意文件写入 | `output` 为 workflow 配置方 input，能写 workflow 的主体本就能在 runner 执行任意代码，零增量收益 | 已归档 #41（config/input 受信）、#40 同构 |
| #31 | 源码正文外泄至共享 OBS 桶 | 与已归档 #70（重复块上报 = 产品核心功能）+ #37（统一桶 + key 前缀约束）完全同构；补充诉求（桶加密/生命周期/访问日志）属 OBS 运维配置，登记平台侧 | #70、#37；sec-comp #17/#40③（平台侧承接） |
| #32 | 运行时 pip install lizard 无哈希校验 | 代码已固定 `lizard==1.24.0`（精确版本固定即满足要求，不做 --require-hashes） | sec-comp #19、pre-commit #23 既有裁决 |
| #34 | 内置 scc 二进制无完整性校验 + PATH 回退 | scc 随仓分发（git commit SHA 即完整性来源）；PATH 回退前有 `command -v` 探测、最终回退本地统计非盲执行；能篡改 runner 文件系统的主体已在信任边界内 | #40 信任边界；pre-commit gitleaks wrapper（执行机预装二进制可接受） |

> 注：7.2 表中 #22 实为「小整改 + 白名单登记」，实施归入 PR C（与镜像收敛同文件）；其余 4 条（#30 #31 #32 #34）附结论关闭。
