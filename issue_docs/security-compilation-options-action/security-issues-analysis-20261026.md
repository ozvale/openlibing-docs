# security-compilation-options-action 安全 Issue 批量定性分析（20261026）

> 本文取代 `security-issues-analysis-20261022.md`（该版保留作历史依据）。
> 重新生成原因：安全团队于 2026-10-26 重新整理了 issue——**删除** #29 #30 #32 #34（已被
> src 迁移/上报链路重构自然解决或合并），**新增** #38-#43（红线 7.1.11 + 威胁分析
> 20261026-0847 报告 6 条），并**改写** #25 #37（补充源码位置与范围）。本文按新 issue 集
> 重新核实并定性。

定性依据：argus / SenInfo / SENS / 红线落地 / 威胁分析（threat-model-20261026-0847）扫描 issue。
已比对跨仓知识库：`security-non-issue-catalog.md`（非问题判定库）、`security-remediation-playbook.md`（整改方案库）。

**代码基线（2026-10-26 核实）**：上游 master `90a63c8`（`!30 merge sync-plugin-src-layout`，
package.json version 1.0.2+）。**该基线已完成 src 迁移**：源码在 `src/`（`index.js`、
`scanner.js`、`bin/sec_option_scan.py`、`detectors/SecOptionDetector.js`、
`uploaders/CicdUploader.js`、`utils/logger.js`），产物为单 bundle `dist/index.js` +
`dist/sec_option_scan.py`（`dist/bin/` 副本已在 `fa78a5a` 删除）。本仓从此不再是
「dist 兼作源码」的结构性缺陷形态（20261022 版文档第 2 节问题 1/3/5 已消解）。

## 0. 结论速览

| 分类 | Issue | 处理建议 |
|---|---|---|
| 沿用已裁决方案（等价加固，可直接做，位置已更新到 src 布局） | #23 #24 #26 #31 #35 #36 #37 | 见 20261022 版分节 + 本文第 3 节位置映射（#35/#36 方案已收敛，见第 3 节）；#37 含本次复核新增的 ATOMGIT_OUTPUT 写入面 |
| 新增·真问题·等价加固（可直接做） | #39 | pip 安装在临时空目录执行，消除 Python 模块遮蔽（第 4.1 节） |
| 新增·已批准（2026-10-26） | #38 #42 | #38 契约变化·窄范围（4.2 节）；#42 新增输入拒绝（4.3 节）；均已获用户批准，待实施 |
| 新增·非问题（2026-10-27 全部落定：①随#27 ②风险接受 ③平台承接 ④随#19） | #40 | ①超时随 #27 改判；②ELF 解析预检改判非问题（既有失败语义受控 + 平台超时兜底，第 4.4 节）；③沙箱确认平台侧承接；④pyelftools 升级随 #19 归档 |
| 新增·非问题（已确认归档） | #25 #41 #43 | 信任模型同构于既有跨仓决策（第 5 节，2026-10-27 用户确认归档） |
| 合规/审计类·延期（后端联调） | #21 | 端到端签名属**合规/审计存证类平台能力需求**，非插件侧安全漏洞（第 4.5 节）；待后端联调排期，插件侧无动作 |
| 非问题（2026-10-27 改判归档） | #22 #27 #28 | #22：门禁语义前提不成立（第 4.6 节）；#27：出站请求已有超时 + 平台容器超时管理（第 4.7 节，#40① 随同）；#28：执行机不支持 Windows，win32 分支不可达（第 4.8 节，改为死代码删除） |
| 非问题（沿用 20261022 判定，2026-10-27 确认归档） | #17 #18 #19 #20 | 详述已并入本文第 5 节（原 20261022 版第 4 节，结论不变） |
| 已删除 issue（安全团队 2026-10-26 清理） | #29 #30 #32 #34 | #30/#32 已随 src 迁移自然解决；#29/#34 命中代码已随上报链路重构（axios + OIDC 客户端）消失，无需动作 |

## 1. 汇总表（当前 open 安全 issue 全集）

| 分类 | Issue | 处置 |
|---|---|---|
| 等价加固·待实施 | #23 #24 #26 #31 #35 #36 #37 #39 + #38 #42（已批准） | 按 20261022 版 PR 计划分组实施（#22 #27 #28 #40 移出；PR F 撤销、PR E 缩减为 #23、PR B 转为 #28 win32 死分支删除）+ #39 并入 PR A + #38（单行正则）+ #42（Python 扫描 symlink 校验） |
| 非问题·已确认归档 | #17 #18 #19 #20 #22 #25 #27 #28 #41 #43 | 2026-10-27 用户确认归档（#22 见 4.6 节、#27 见 4.7 节、#28 见 4.8 节，其余见第 5 节），待附结论关闭 issue |
| 延期·后端联调 | #21 | 合规/审计存证类平台能力需求（第 4.5 节，2026-10-27 定性改判）；待平台侧联调排期 |
| 功能需求 | #22（`fail-on-upload-error` 可选 input）#33 | #22 残余项转功能 issue 评估，不走安全整改流程 |

## 2. src 迁移对旧结论的影响（位置映射）

| 旧位置（dist 布局，20261022 版引用） | 新位置（src 布局，2026-10-26 核实） | 备注 |
|---|---|---|
| `dist/index.js:53364`（OPENLIBING_APIG_KEY） | `src/index.js:92-93`（改为 `getInput('apig-app-key')`，凭证从 env 移到 action input） | #24 证据更新 |
| `dist/index.js:54394-54402`（pip install） | `src/index.js:116-128` | #19/#39 证据更新 |
| `dist/uploaders/CicdUploader.js:248` | `src/uploaders/CicdUploader.js:248`（`this.baseUrl = config.cicdUrl \|\| 'http://localhost:8080'` 仍在） | #26/#31 结论不变：`src/index.js:86` 传常量 `https://apig.openlibing.com:443`，fallback 不可达，删除即等价加固 |
| `dist/index.js:5642-5647`（mask 默认 6/4） | `src/index.js` OIDC 客户端内联段对应位置（bundle 重打包后行号以 dist 为准） | #24 结论不变 |
| `dist/sec_option_scan.py` 临时基目录 | `src/bin/sec_option_scan.py`（`D:\sec_option_tmp`/`C:\sec_option_tmp` + `mkdtemp` 仍在） | #28 结论不变 |
| `dist/index.js:54344`（run 入口） | `src/index.js`（run 主函数） | 各调用点结论不变 |
| `dist/bin/sec_option_scan.py` 重复副本 | **已删除**（`fa78a5a`），`SecOptionDetector.js:11` 改 `path.resolve(__dirname, '..', 'bin', 'sec_option_scan.py')`，ncc 打包改写为 dist 根 | #30 自然解决，issue 已删除 |

## 3. 沿用 20261022 已裁决的 issue（结论不变，仅更新位置）

以下 issue 的定性、方案选定（「一律选不影响业务逻辑的形态」）与 PR 分组**全部沿用
20261022 版文档**，本节不重复，仅列差异：

- **#35 #36 #37**（日志输出）：结论不变，**#35/#36 方案收敛（2026-10-27 用户裁决）**：
  - **#35 日志只走 detailLink/tip 单通道**——成功时入口仅输出 `detailLink`（无则 `tip`，两者为服务端契约内固定语义字段，天然无内部信息，`index.js:346-356` 现状已满足）；失败时删除 `CicdUploader.js:339` 的整段响应体 dump（`JSON.stringify(error.response.data)`），仅保留 `HTTP ${status}` 状态码一行；错误明细（msg/message）只随返回值进上报 payload 的 errorMessage 字段（后端定位契约，行为不变），不再落 CI 日志。
  - **#36 debug 级路径日志全删、info 级 basename 化**——debug 命中 4 行整行删除：`scanner.js:47`（Source directory）、`SecOptionDetector.js:23`（Python script path）、`:24`（Output file）、`:77`（Executing 命令行含绝对路径）；`SecOptionDetector.js:57`（Summary JSON）无路径保留。info 级 3 处改 `path.basename()`：`SecOptionDetector.js:22`（detector on）、`scanner.js:102`（Results saved to）、`index.js:80`（Using artifact-path）——扫描目标/结果文件基名是核对「扫了哪个包」的最小必需信息，basename 后不含用户名/盘符/目录结构。
  - `src/index.js:343-369` 写 `ATOMGIT_OUTPUT` 时，`detailLink`/`tip` 来自服务端响应、
    `packageName` 来自 input，未清洗换行/`=` 即拼接输出行——与日志注入同一 `sanitize()`
    方案覆盖（清洗仅作用于输出文本，不改上报契约），仍属等价加固；sanitize 同时覆盖
    detailLink/tip 两个输出通道字段（防换行注入）。
  - `src/bin/sec_option_scan.py:280-283,1238` 的 Python 侧输出点同前。
- **#24**：结论不变（只做 `mask()` 收紧，放弃 gitUrl 改动）。**注意**：#38 本轮以红线
  issue 形式重新提出 gitUrl 凭证清洗，见 4.2 节——两项裁决需一并对齐。
- **#26 #31**：结论不变（死 fallback 删除）。
- **#22 #23 #27 #28**：#23 结论不变（超预算只告警，风险接受声明见 4.7 节备注）；**#22 改判**（2026-10-27）——门禁语义前提不成立，转非问题 + 残余项转功能需求，见 4.6 节；**#27 改判**（2026-10-27）——出站请求已有超时 + 子进程由平台容器超时管理，转非问题（#40① 随同），见 4.7 节；**#28 改判**（2026-10-27）——执行机不支持 Windows，win32 固定基目录分支不可达，转非问题 + 死分支删除，见 4.8 节。
- **#21**：延期不变，定性改判记录见 4.5 节（2026-10-27 改判为合规/审计存证类平台能力需求）。
- **#17 #18 #19 #20**：非问题判定不变，2026-10-27 用户确认归档，详述已从 20261022 版并入本文第 5 节（可附结论关闭，操作同其他仓：评论 + close）。

## 4. 本轮新增 issue 详述

### 4.1 #39 —— Python 模块遮蔽导致任意代码执行（真问题·等价加固）

| 项 | 内容 |
|---|---|
| 位置 | `src/index.js:116-128`：`execSync([pythonCmd, '-m', 'pip', 'install', ...].join(' '), { stdio: 'inherit', timeout: 120000 })`，未设 `cwd`（继承工作区根）、未隔离 |
| 核实 | ✅ 真实。Python `-m` 把当前工作目录置于 `sys.path` 首位；被测仓提交 `pip/` 或 `pip.py` 即可遮蔽官方 pip，PR 流水线检出 PR 代码后在 runner 上获得任意代码执行。与 pre-commit 门禁「必须执行 PR 代码」不同，**此处执行的是插件自身的依赖安装步骤，PR 作者本无权介入**，属真实提权面 |
| 整改（等价加固） | pip 安装改在**临时空目录**执行：`execSync(cmd, { cwd: <os.tmpdir() 下新建空目录>, stdio: 'inherit', timeout: 120000 })`。工作区不再位于 `sys.path`，遮蔽面消除；安装内容/版本/镜像源/退出语义均不变（pip install 不依赖 cwd）。备选 `python -I -m pip`（隔离模式会同时忽略 PYTHON* 环境变量，行为面更大，不首选） |
| 分类 | 等价加固（执行目录安全化），不属硬规则 2。并入 PR A（日志与执行卫生同组） |

### 4.2 #38 —— git remote URL 凭据清洗仅覆盖 https（真问题·已批准·待实施）

**裁决（2026-10-26 用户批准）**：按拟议方案实施——正则泛化为任意 scheme 的 userinfo 剔除。

| 项 | 内容 |
|---|---|
| 位置 | `src/index.js:101`：`remoteUrl.replace(/https:\/\/[^@]+@/, 'https://')`；打印点 `src/index.js:186`（`core.info('gitUrl: ...')`）；外发点 `src/uploaders/CicdUploader.js:297`（payload 字段日志）+ payload body 随上报 POST |
| 核实 | ✅ 真实。`http://user:token@host/` 形式不清洗：① 完整凭证以 info 级落 CI 日志；② 随上报 JSON body 发往后端。红线 7.1.11 要求 |
| 治本 vs 兜底（2026-10-26 补充） | 内嵌凭证的真正来源是 **clone/checkout 阶段**把 token 拼进 remote URL。治本 = checkout 凭证传递改 GIT_ASKPASS / credential helper（token 不落 URL，gitUrl 天然干净）——但该控件在**平台内置 checkout 步骤**，不归本插件（本插件不执行 clone，仅 `git remote get-url origin` 读现成 URL；对照：pre-commit-action #22/#35 的 GIT_ASKPASS 整改可行是因为那个插件自己 clone）。插件侧正则清洗是**条件性兜底**：治本落地后正则无害空转，两层不冲突。建议同步给平台侧登记 checkout 凭证传递改造项 |
| 与 20261022 #24 裁决的关系 | 当时按「零业务影响」放弃了 gitUrl 改动（因其进上报体 = 契约变化）。本轮红线 issue 重新提出，需重新裁决 |
| 拟议方案 | `src/index.js:101` 正则改为**任意 scheme 的 userinfo 剔除**：`replace(/[a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^@\/]+@/, '$1://')` 形态（匹配 `http://`、`https://` 等全部内嵌凭证形式），单点修改同时覆盖日志与上报两个消费面。**ssh 形态注意**：`ssh://git@host` 的 `git@` 是标准用户名非凭证，泛化正则会误剔为 `ssh://host`（git 仍兼容，但语义有损）；如需保留 `git@`，正则排除 `git` 用户名（`(?<!git:)` 或先判 `user !== 'git'`）。验证用例需覆盖：http/https 内嵌凭证、无凭证、`ssh://git@host` |
| 业务逻辑影响评估 | ① 关联 issue：#38（波及 #24 残留项）。② 改动点：仅 `src/index.js:101` 一行正则。③ 分类：**契约变化（第 1 类，窄范围）**——仅当 remote URL 内嵌凭证时，上报的 gitUrl 值会剔除 userinfo；无凭证 URL（绝大多数场景）逐字节不变。④ 为什么绕不开：清洗点在源头，日志与上报共用该值，分开清洗会留半整改状态。⑤ 下游消费方：后端 gitUrl 字段（展示/溯源），消费的是仓库地址语义，剔除 userinfo 不损失语义。⑥ 验证：单测覆盖 http/https 内嵌凭证、无凭证、ssh 形式；`npm test` 全绿。⑦ 回滚：恢复原正则即可。 |
| 建议 | **建议批准**（上报体携带凭证本身即是泄露面，后端不应接收凭证；改动只影响病态输入） |

### 4.3 #42 —— 扫描目录跟随符号链接越界（真问题·已批准·待实施）

**裁决（2026-10-26 用户批准）**：按 issue 修复建议实施——`follow_symlinks=False` + realpath 包含性校验。

**环节定位**：问题在**解压后的递归扫描**环节（`scan_directory`，`src/bin/sec_option_scan.py:102-119`）——`item.is_dir()` 默认跟随符号链接。解压侧 `_safe_extract_tar` 已有 linkname 越界校验（拦截归档内带出的恶意 symlink），但**树内扫描路径**（artifact-path 直接指向的目录）缺同层防护。

**行为影响确认（用户已确认）**：
- 正常产物（无 symlink 或 symlink 指向扫描根内，如 `libfoo.so -> libfoo.so.1.5`）：结果逐字节一致，零变化
- 病态输入（越界 symlink）：从「被扫描并上报」变「跳过 + 一行 warning」——第 5 类新增输入拒绝，已获批准
- 使用方式（artifact-path 格式、输出 JSON、上报接口、退出码）全部不变

| 项 | 内容 |
|---|---|
| 位置 | `src/bin/sec_option_scan.py:102-119`：`os.path.realpath` 仅做防环（visited 集合），`item.is_dir()` 默认跟随符号链接，无 scan_root 包含性校验 |
| 核实 | ✅ 真实，攻击路径成立：PR 作者控制构建产物内容 → tar 归档可含指向扫描根之外的符号链接（`tar xf` 保留 symlink；Python `zipfile.extractall` 不保留）→ 扫描递归进入外部目录，读取并上报 runner 上工作区外 ELF 的路径与编译选项。zip 系列归档不受影响 |
| 拟议方案 | ① `item.is_dir(follow_symlinks=False)`：符号链接目录不再当目录递归，按文件处理（非 ELF 即跳过）；② 对文件同样加 `realpath` 包含性校验：`os.path.realpath(file)` 必须位于当前扫描根（树内阶段 = scan_root，归档成员阶段 = 解压根）之内，越界跳过并打一行 warning |
| 业务逻辑影响评估 | ① 关联 issue：#42。② 分类：**新增输入拒绝（第 5 类）**——仅含越界符号链接的产物受影响（病态输入）；正常产物（无 symlink、或 symlink 指向包内）行为不变。③ 为什么绕不开：跟随语义在 `os.scandir`/`is_dir` 默认行为里，必须在遍历点拦。④ 下游消费方：扫描结果 JSON 与上报 payload（越界文件的条目将不再出现——这些条目本就不应出现）。⑤ 验证：构造含 `../` 越界 symlink 的 tar 测试包，断言跳过且 warning；正常 tar 扫描结果不变。⑥ 回滚：还原两处判断 |
| 建议 | 建议批准（攻击者 = PR 作者，防护收益明确；合法产物几乎不含目录级 symlink） |

### 4.4 #40 —— 不可信 ELF/归档解析无隔离与超时（非问题·2026-10-27 全部落定）

| 子项 | 定性 | 处置 |
|---|---|---|
| ① spawn 无超时/输出上限 | 非问题（2026-10-27 随 #27 改判） | 与 #27 属同一发现（同一 spawn 调用点）：出站请求已有超时（axios 60s），子进程 hang 由平台容器/job 级超时管理兜底（见 4.7 节）；原「并入 #27 可选 input」方案撤销 |
| ② ELF 解析预检（节数/符号数/字符串表长度上限） | 非问题（2026-10-27 改判·风险接受） | 三层论证：① 插件不挂 PR 流水线（schedule 全量扫描），解析失败无门禁影响、当晚数据次日 nightly 补齐；② 资源耗尽（CPU/内存）被平台 job 级超时兜底（用户确认 GitCode 侧管理）；③ **解析崩溃已是既有受控行为**——`sec_option_scan.py:594-603` 的 `except ELFError` / `except Exception` 将恶意 ELF 记入 failed_files（部分成功状态统计 + errorMessage 上报后端），单文件跳过不中断扫描，属健壮性设计而非安全漏洞。预检的收益仅是「崩溃→优雅跳过」，属健壮性/功能增强，不走安全整改。与 #23 边界：#23 的 zip bomb 横向影响整台 runner（写盘）故维持观测；本项仅耗本进程资源，被平台超时精确兜底，面更窄 |
| ③ 沙箱隔离（低权限用户/容器/namespace、CPU/内存上限） | 平台侧承接（2026-10-27 用户确认） | runner 隔离能力属平台基础设施，用户确认由 GitCode 侧统一处理，插件侧无动作（同 #17 残余风险归属）；登记平台侧，不计入本仓未修复数 |
| ④ pyelftools 版本跟踪升级 | 非问题（2026-10-27 确认，随 #19 归档） | 当前 `pyelftools==0.31` 已精确固定（#19 既有决策：精确版本固定即满足要求）；升级版本属功能演进，不走安全整改 |

### 4.5 #21 —— 上报数据无端到端签名（合规/审计类·延期后端联调）

**定性改判（2026-10-27 用户裁决）**：从「真问题·暂缓」改判为**合规/审计存证类平台能力需求**，非插件侧安全漏洞；延期至后端联调排期，插件侧无动作。

| 项 | 内容 |
|---|---|
| 原始指控 | 上报数据无端到端签名，签名不覆盖关键字段 |
| 核实 | OIDC（V11-HMAC-SHA256）/ AK-SK（HMAC）签名绑定的是「所交付 body」，服务端按 body 验签——**传输完整性与请求来源认证已有**；原 issue「签名不覆盖关键字段」表述不准确（签名覆盖整个 body） |
| 为什么不是安全问题 | ① **无未受信攻击者路径**：结果 JSON 在 job 内生成、job 内上传，能介入该窗口的主体 = runner / workflow 配置方，已在 Actions 信任边界内（同 #20/#41 信任模型），不存在可利用的攻击链；② 缺的是「报告级内容签名 + 可信时间戳 + 存证」——防事后篡改/防抵赖，消费方是**审计/合规流程**而非攻击面防护；③ 插件侧无法单方面提供可信时间戳/取证锚点（锚点必须由受信第三方/后端持有） |
| 实施主体与形态 | **平台侧（后端）**：发布验签公钥 + 报告内容签名 + 存证机制；插件侧届时配合透传签名字段（属接口契约变化，须届时评审） |
| 处置 | 延期整改，登记到平台侧联调排期；本仓安全整改批次不含 #21，不计入未修复数（同非问题口径：非插件仓可整改项） |

### 4.6 #22 —— 合规门禁可被绕过（非问题·2026-10-27 改判）

**定性改判（2026-10-27 用户裁决）**：从「真问题·等价加固（PR F）」改判为**非问题**——「门禁可被绕过」的指控前提不成立；20261022 版选择的 `fail-on-upload-error` 整改**撤销**（PR F 取消），残余可观测性诉求转功能需求。

| 项 | 内容 |
|---|---|
| 原始指控 | 上报失败不使 step 失败（fail-open）、扫描环境准备失败仅 warning、无「必需」语义 → 合规门禁可被绕过 |
| 指控前提拆解 | 「门禁被绕过」隐含前提：**插件承担 PR 流水线门禁（阻断合入）语义**。该前提不成立 |
| 事实核实 | 本仓 workflow 触发器仅 `schedule`（每日凌晨 3 点 cron）+ `workflow_dispatch`（手动）——`nightly-schedule-scan.yml:3-6`，**无任何 `pull_request`/`push` 触发器**。插件定位 = 全量代码扫描 + 报告上报，与同仓 #9/#10/#25 定性中反复确认的部署事实一致（不挂 PR 流程） |
| 为什么不是安全问题 | ① **无门禁语义可绕过**：无 PR 触发 → 插件失败/成功均不影响任何合入决策，「必需扫描」与门禁判定由平台侧（后端数据对账）承载（20261022 版定性已写明该归属）；② **无攻击者路径**：上报失败源于网络/服务端故障，非攻击者可控收益面；③ **fail-open 是上报类工具的合理默认**：nightly 场景下中断整个流程 vs 漏一次可重扫的数据，前者代价更高（次日定时自动重扫补齐） |
| 残余项（非安全） | 运维可观测性：上报失败仅 info/error 日志，平台侧若不做数据对账则漏报无人察觉。可选功能增强：`fail-on-upload-error` input（默认 false）、失败告警计数——**转功能 issue 评估**，不走安全整改流程 |
| 处置 | 撤销 20261022 版 PR F（fix-sec-gate-input）；#22 按非问题归档（待附结论关闭），与 #33 同类处置；后续新扫描同形态问题参照本节 + catalog「上报类插件的 fail-open 默认」判定 |

### 4.7 #27 —— 出站请求无超时、子进程输出无上限（非问题·2026-10-27 改判）

**定性改判（2026-10-27 用户裁决）**：从「真问题·等价加固（可选 input 默认关闭）」改判为**非问题**；20261022 版选择的 `request-timeout-ms` / spawn 超时可选 input 方案**撤销**（PR E 中 #27 部分取消，PR E 仅保留 #23）。#40①（spawn 无超时/输出上限）与 #27 属同一发现，随同改判非问题（4.4 节已更新）。

| 项 | 内容 |
|---|---|
| 原始指控 | ① 出站请求无超时、`res.text()` 无长度上限；② SecOptionDetector spawn 无 `timeout`/`maxBuffer` |
| 核实（src 布局，2026-10-27） | ① **出站请求已有超时**：axios 上报带 `timeout`（`CicdUploader.js:329`），入口显式传 60000ms（`index.js:175`，经 `scanner.js:30` 透传），超时有明确错误反馈（`CicdUploader.js:334`）；② `pip install` 的 execSync 带 `timeout: 120000`（`index.js:124`）；③ 确无超时的仅剩两处：Python 扫描子进程 spawn（`SecOptionDetector.js:79`）与 `git remote get-url` execSync（`index.js:100`，瞬时命令） |
| 为什么不是安全问题 | ① **网络面已有控件**：唯一的外发请求（上报）已带 60s 超时与失败反馈，指控的网络 hang 面不成立；② **子进程面由平台兜底**（用户裁决依据）：GitCode 平台对容器/子进程有 job 级超时管理，扫描子进程最坏被平台超时终止——与 #40③（沙箱）、#17（执行机隔离）同一「平台侧承载」归属模式；③ 残余代价可接受：子进程 hang 最坏损失 = 当晚扫描数据，次日 nightly 自动补齐（同 #22 恢复路径），无数据泄露、无提权 |
| 残余风险接受 | 观测/超时粒度粗（平台 job 级超时远大于插件级），属效率损耗而非安全风险；如后续业务需要更细的失败定位，可作为功能需求评估（非安全整改） |
| 处置 | 撤销 20261022 版 PR E 中 #27 部分（可选超时 input）；#27 按非问题归档（待附结论关闭），#40① 随同；不计入本仓未修复数 |

**备注（#23 风险接受声明，2026-10-27 用户确认维持观测方案）**：#23 的「只观测不阻断」同样属风险接受——zip bomb 写盘/深嵌套 hang 的实际损失不变，接受理由为 nightly 单次 DoS 代价低（一晚延迟 + 磁盘清理）、攻击者无数据收益、残余风险由 #40③ 平台侧沙箱最终兜底；硬预算须业务方确认合法大包场景后另行评审。

### 4.8 #28 —— Windows 可预测临时基目录（非问题·2026-10-27 改判 + 死分支删除）

**定性改判（2026-10-27 用户裁决）**：从「真问题·等价加固（junction 校验）」改判为**非问题（环境不达）**——本插件执行机不支持 Windows 系统，指控的固定基目录劫持面在本仓部署中不可达；`win32` 分支作为**死代码移除**（20261022 版方案① islink/reparse 校验不再需要）。

| 项 | 内容 |
|---|---|
| 原始指控 | `D:\sec_option_tmp`/`C:\sec_option_tmp` 固定基目录可被同机其他作业预先创建为 junction/symlink 劫持解压写入 |
| 核实 | 代码属实（`src/bin/sec_option_scan.py:250-257`，`sys.platform == 'win32'` 分支内）。但**部署事实**：本仓全部 workflow `runs-on: ["self-hosted", "region=cn"/"region=overseas"]`，执行机均为 Linux（用户确认不支持 Windows）→ 分支恒不执行，`D:\`/`C:\` 基目录路径在 Linux 上也无意义 |
| 为什么不是安全问题 | ① **攻击面不可达**：junction/symlink 劫持需要插件跑在 Windows runner 上，本部署不存在该环境；② 原分支的存在动机（Windows MAX_PATH 260 限制）也仅 Windows 特有，Linux 无路径长度限制 |
| 整改形态 | **死代码删除**（等价加固，同 20261022 版 #29/#34 形态）：删除 `if sys.platform == 'win32':` 整个分支（含固定基目录循环），保留 `tmp_dir = tempfile.mkdtemp(prefix='sec_option_extract_')` 单一路径——Linux 上该行本就是实际执行路径，删除后行为逐字节一致 |
| 边界说明 | 该分支是为「分发到 Windows runner 使用」预留的兼容代码；删除意味着**明确放弃 Windows runner 支持**。如未来需要支持 Windows，恢复分支并按 20261022 版方案①（islink + reparse 校验）实施，不得裸恢复 |
| 处置 | 归入原 PR B（fix-sec-temp-and-dedup；#30 死副本已被上游 `fa78a5a` 删除，PR B 实际内容 = 本项死分支删除）；`src/bin/sec_option_scan.py` 与 `dist/sec_option_scan.py` 同步；#28 按非问题归档，不计入本仓未修复数 |


## 5. 非问题归档（2026-10-27 用户确认）

> 判定依据：**信任模型同构**——相关 issue 的「外部输入」实际都由 workflow 配置方
> （有仓库写权限、能改 CI 的人）控制，非 PR 作者可控。#17-#20 沿用 20261022 版
> 判定（详述自该版第 4 节并入，代码位置已随 src 迁移更新）；#25 #41 #43 为本轮
> 新增，同构于既有跨仓决策；#22 #27 #28 为 2026-10-27 改判（门禁语义前提不成立 /
> 出站请求已有超时 + 平台超时兜底 / 执行机不支持 Windows 分支不可达，详述见
> 4.6 / 4.7 / 4.8 节）。全部经用户 2026-10-27 确认归档，后续新扫描同形态问题按
> `security-non-issue-catalog.md` 对应条目去重排除。

### 5.1 #25 #41 #43 —— 本轮新增（信任模型同构）

| Issue | 内容 | 非问题理由 | 同构先例 |
|---|---|---|---|
| #41 | artifact-path 接受任意绝对路径 → 越权扫描 runner 任意路径 | `artifact-path` 由 workflow 配置方设定（`src/index.js:144` 仅做存在性校验）；能改 workflow 的人本就能在 runner 上读写任意路径并自行外传，扫描上报不构成新增提权面。属纵深防御建议 | pre-commit-action #28（sarif-file/report-dir 任意路径，2026-10-13 用户决策非问题）。可选强化（须评审）：限制在工作区内（第 5 类新增输入拒绝），仅用户要求时实施 |
| #43 | 静态 AK/SK 兼容通道长期有效 | AK/SK 为**已标注废弃的兼容通道**（README:235-236），OIDC 为默认路径（`src/index.js:90`：有 `ACTIONS_ID_TOKEN_REQUEST_URL` 即走 OIDC）；保留是为存量脚本兼容（易用性取舍）。报告建议的「无 OIDC 直接失败」= 默认行为反转（fail-closed，硬规则 2 第 4 类），不实施。可选等价加固：AK/SK 分支入口加一行 deprecation warning 日志 | upload-sarif-action #15（静态 AK/SK 直连是易用性设计取舍，2026-10-13 用户决策非问题） |
| #25 | output 越界写 / 下载 URL 未校验转发 / package-name 拼接穿越 / artifact-download-url 持久化 | ① `output`、`package-name`、`artifact-download-url` 均为 workflow 配置方输入（`src/index.js:70-72`），配置方本就有 runner 写权限，`../` 穿越不构成提权；② `artifact-download-url` 原样持久化上报属**产物溯源业务契约**（后端按此下载产物），插件不二次加工；③ OBS 预签名 URL 的有效期/留存策略属平台数据治理 | pre-commit-action #28（路径输入受信）+ #27（用户自备资产原样上传属业务契约，2026-10-13 用户决策） |

### 5.2 #17 #18 —— CI workflow（沿用 20261022 判定）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #17 | PR 代码在自托管执行机执行（pwn-request） | ⚪ 非问题（catalog: 自建门禁 workflow 设计）。`pre-commit.yml:8` 用 `pull_request_target` 是为**始终读取 master 的最新门禁配置**，`checkout` 显式检出 `merge_commit_sha` 并按设计「检查 PR 合并后代码」（门禁必须执行 PR 代码才能检查它）。`ROBOT_TOKEN` 只注入 `initiate`/`post` 两个 label job（`pre-commit.yml:31/84`），与执行 PR 代码的 `pre-commit` job 不同 job，无凭证可达。workflow 级 `permissions: repository: read, pr: write`（`:17-19`）对执行 job 偏宽，属平台侧 job 级 permissions 能力缺口，登记为配置优化项 |
| #18 | CI 供应链可变引用 + 超范围 OIDC 授权 | ⚪ 非问题（catalog: OIDC 联邦必需 + 自有仓可变 tag）。`id-token: write`（`nightly-schedule-scan.yml:10`、`code-metrics-scan.yml:11`）是华为云 OIDC 联邦换临时凭证的必需权限，无法收敛；`uses` 全部为自家门禁 Action（`openlibing/pre-commit-action@v1.0.2`、`openlibing/upload-sarif-action@v1.0.0`、`openlibing/code-metrics-action@v1.0.3`、`openlibing/pr-label-action@v1.0.0`）或平台内置 `checkout/setup-node/setup-go`，无第三方 Action。可选强化：自家 Action 改 commit SHA（低优先级，需随发版维护） |

### 5.3 #19 —— PyPI 镜像无哈希安装（沿用 20261022 判定）

| 内容 | 核实结论 |
|---|---|
| `pip install pyelftools==0.31` 无 `--require-hashes`，源为公网阿里云镜像 | ⚪ 非问题（沿用 2026-10-13 pre-commit-action#23 评审决策：**精确版本固定即满足要求，不引入 `--require-hashes`**）。本仓核实：`src/index.js:116-128` 用静态参数数组 + `execSync`，无用户输入参与，版本已精确固定，已满足该决策标准。`-i https://mirrors.aliyun.com/pypi/simple/` 为**固定**地址、非动态/外部可控值，不属安全问题（已裁决 2026-10-22）。注：执行目录安全化归 #39 整改，与本条定 性无关 |

### 5.4 #20 —— 流水线身份可伪造（沿用 20261022 判定，2026-10-27 复核）

| 内容 | 核实结论 |
|---|---|
| OIDC 身份取自环境变量/未校验 OIDC URL | ⚪ 非问题。核实（src 布局）：`src/index.js:90` `useOidc = !!process.env.ACTIONS_ID_TOKEN_REQUEST_URL`（仅 runner 在 workflow 声明 `permissions: id-token: write` 时注入，PR 作者不可设）；OIDC 令牌获取在 `@openlibing/huaweicloud-oidc-client` 内部（`HUAWEICLOUD_OIDC_TOKEN` 环境变量优先直取，见 `node_modules/@openlibing/huaweicloud-oidc-client/src/oidc.js:27`）。**环境变量即 Actions 的信任边界**：能写这些环境变量的主体（runner / workflow 配置方）本就具备修改 workflow、在 runner 上执行任意代码的能力，「伪造身份上报」零增量收益，不构成新增提权面。OIDC 端点 URL 强制 host 白名单属「新增输入拒绝」，会破坏私有云/自建 GitCode 平台兼容性，不实施；若平台侧要求，须走评审并在 action.yml 暴露可配置白名单。与 #41/#43 信任模型同构（外部输入实为受信配置方控制） |

## 6. 已删除 issue 说明（安全团队 2026-10-26 清理）

| Issue | 原内容 | 删除原因（核实） |
|---|---|---|
| #30 | 分发两份重复扫描脚本 | **已随 src 迁移自然解决**：`dist/bin/sec_option_scan.py` 已删（`fa78a5a`），`SecOptionDetector.js:11` 单一引用 |
| #32 | 打包无源码↔dist 一致性校验 | **已随 src 迁移自然解决**：源码在 `src/`、`ncc build` 从 `src/index.js` 构建，一致性由构建流程保证 |
| #29 | 打包内 TLS 校验旁路死分支 + 可变 fetch | 命中代码位于旧 `@actions/http-client` 内联段；上报链路重构为 axios（AK/SK）+ OIDC 客户端（OIDC 模式）后该依赖已不在 bundle，命中消失 |
| #34 | 捆绑 @actions/io 回退路径 chmod 0666 | 同上，`@actions/io` 已不在新 bundle 中 |

## 7. PR 分组计划（在 20261022 版 A-F 基础上增量）

| PR | Issue | 增量内容 |
|---|---|---|
| PR A：fix-sec-log-hygiene | #35 #36 #37 #24（+#39 新增） | + pip 安装改临时空目录执行（#39）；+ ATOMGIT_OUTPUT 写入清洗（#37 补充范围） |
| PR B：fix-sec-temp-dedup | #28（改判后形态） | **缩减（2026-10-27）**：#28 改判非问题 + win32 死分支删除（#30 死副本已被上游删除，PR B 内容 = 删除 `sec_option_scan.py` 的 win32 分支 + dist 同步） |
| PR C/D | 同 20261022 版 | 无变化（#26/#31/#24 各自方案沿用） |
| ~~PR F：fix-sec-gate-input~~ | ~~#22~~ | **撤销（2026-10-27）**：#22 改判非问题（第 4.6 节），`fail-on-upload-error` 转功能需求 |
| 待实施（已批准） | #38 → 并入 PR A 或单独小 PR（单行正则 + 单测）；#42 → `src/bin/sec_option_scan.py` + 测试 tar 包用例 |
| 延期 | #21（后端联调，合规/审计类） | #40②③ 已落定（②非问题·风险接受、③平台侧承接），不再暂缓 |

## 8. 裁决状态

| 裁决项 | 状态 |
|---|---|
| #38 gitUrl 任意 scheme userinfo 剔除 | ✅ **已批准（2026-10-26）**，按 4.2 拟议方案实施 |
| #42 符号链接越界拒绝 | ✅ **已批准（2026-10-26）**，按 4.3 拟议方案实施（issue 修复建议） |
| #25 #41 #43 非问题归档 | ✅ **已确认（2026-10-27）**，归档至本文第 5.1 节，待附结论关闭 issue |
| #17 #18 #19 #20 非问题关单 | ✅ **已确认（2026-10-27）**，详述并入本文第 5.2-5.4 节，待附结论关闭 issue |
| #21 定性改判 + 延期 | ✅ **已裁决（2026-10-27）**：改判为合规/审计存证类平台能力需求（非插件侧安全漏洞），延期至后端联调排期（第 4.5 节），不计入本仓未修复数 |
| #22 定性改判 + PR F 撤销 | ✅ **已裁决（2026-10-27）**：改判非问题——门禁语义前提不成立（插件仅 schedule/workflow_dispatch 全量扫描，无 PR 触发，第 4.6 节）；PR F 撤销，`fail-on-upload-error` 转功能需求，不计入本仓未修复数 |
| #27 定性改判 + #40① 随同 | ✅ **已裁决（2026-10-27）**：改判非问题——出站请求已有超时（axios 60s + 失败反馈）、子进程由平台容器/job 级超时管理兜底（第 4.7 节）；PR E 中 #27 部分撤销（仅保留 #23），#40① 随同改判非问题，不计入本仓未修复数 |
| #28 定性改判 + 死分支删除 | ✅ **已裁决（2026-10-27）**：改判非问题（环境不达）——执行机不支持 Windows，win32 固定基目录劫持面不可达（第 4.8 节）；PR B 缩减为 win32 死分支删除，原 junction 校验方案撤销，不计入本仓未修复数 |
| #23 维持观测方案 | ✅ **已确认（2026-10-27）**：维持「只观测不阻断」，风险明示接受（第 4.7 节备注），硬预算待业务方确认合法大包场景后另行评审 |
| #40 ②ELF 预检立项 / ③沙箱暂缓 | ⏳ 待用户确认（①超时已随 #27 改判非问题、④pyelftools 升级已随 #19 确认为非问题） |
