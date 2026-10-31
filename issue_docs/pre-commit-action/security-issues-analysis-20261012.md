# pre-commit-action 新增安全 issue 分析（#20~#37）

> 分析基准：`fix-security-remediation` 分支（HEAD: 9359c93），对照整改后代码逐条核实。
> 分析日期：2026-10-12。结论仅作整改决策参考，暂不修改代码。

## 汇总

| 分类 | Issue | 处理建议 |
|---|---|---|
| 已修复/重复，待合入后关闭 | #22 #35 #36 | 回复说明覆盖关系，整改分支合入主线后关闭 |
| 高危·须用户评审修复方向 | — | （#34 已定性为非问题，高危项已清空） |
| 已评审批准，待实施 | #23 #31 | #23 固定 pre-commit 版本（不做 require-hashes）；#31 删除 `GONOSUMDB=*`（无私有 Go 模块，公共模块全走 sumdb 校验）。2026-10-13 评审通过 |
| 低危·等价加固，可直接做 | #26 #37 #32 | 按最小改动原则整改 |
| 基本不是问题 | #28 #33 #30 #25 #21 #27 #20 #24 #29 #34 | 回复说明 / 降级 / 平台侧配置优化 / 使用方配置控制 / 有意设计 / 业务逻辑与配置端决定 |

---

## 一、已被现有整改覆盖（重复 issue，可回复关闭）

| Issue | 内容 | 核实结论 |
|---|---|---|
| #22 | gc_token 明文写入 `.git/config`（index.js:167-175 拼入 remote URL） | ✅ 已修复：PR #13 改用 GIT_ASKPASS，token 不落盘、不进 argv |
| #35 | token 持久化未清理 + 进程参数可见 | ✅ 已修复：同 PR #13，askpass 脚本 0o700 权限、finally 中即时删除 |
| #36 | remoteUrl 未编码拼入 bash 命令（index.js:169-173） | ✅ 问题代码已整体移除（index.js 无任何 `remote get-url/set-url` 调用残留） |

---

## 二、真问题（建议整改，属行为变化，须先评审）

### #31 `go env -w GONOSUMDB=*` 关闭 Go 校验【中危】

- **位置**：`index.js:700`（仍存在）
- **核实**：真实，runner 全局关闭 Go 模块校验和
- **已决策（2026-10-13 用户评审）**：**直接删除 `GONOSUMDB=*` 这一行**。理由：本平台仓不使用私有 Go 模块，公共模块全部走 sum.golang.org 校验最干净，无需豁免清单。属行为变化（删除全局校验豁免），已经用户评审批准，可进入实施。验证方式：跑一个含 Go 钩子的仓确认模块拉取正常（公共模块校验不应失败）。

### #23 pip 安装 pre-commit 无版本固定 + 动态选源【中危】

- **位置**：`index.js:550,577`
- **核实**：真实，供应链投毒面
- **已决策（2026-10-13 用户评审）**：采用**固定版本**方案——pip 安装改为 `pre-commit==X.Y.Z`（锁定当前实际使用的版本），不做 `--require-hashes`（不维护哈希清单）。理由：固定版本即可免疫"新版本投毒"这一最主要攻击面；哈希清单维护成本高，暂不引入。升级策略：随安全 issue 整改节奏定期更新版本号（属手动升级，升级时机由维护者控制）。属升级策略变化（硬规则 2 第 2 类），已经用户评审批准，可进入实施。

---

## 三、真问题但低危（等价加固类，可直接做）

| Issue | 内容 | 备注 |
|---|---|---|
| #26 | `execCapture` 用 `shell:'/bin/bash'` 字符串拼接（index.js:88,95,173） | 改 execFile 数组传参。残留调用点（curl 测速/go version）插值均来自环境变量/常量，无不可信输入，风险低 |
| #37 | README 输入参数表缺 `gc_token` 说明 | 纯文档补齐，零风险 |
| #32 | bump-version.js 正则要求带引号，action.yml 当前 `version: 1.0.41` 无引号 → 必然匹配失败 | 小 bug，顺手修 |

---

## 四、基本不是问题（建议降级 / 回复说明）

| Issue | 内容 | 结论 |
|---|---|---|
| #28 | sarif-file / report-dir 任意路径进入 `sarif-files` | 输入由 workflow 配置方（有仓库写权限者）控制，非 PR 攻击者可控——能改 workflow 的人本就能读任意文件。属纵深防御建议，非实际漏洞 |
| #33 | 输入/健壮性控制覆盖有限 | workspace 来自平台 `WORKSPACE` 环境变量，非攻击者可控；`sanitizePath` 已覆盖主要输出路径。无实际攻击路径 |
| #30 | 第三方 action 可变 tag + OIDC `id-token: write` | **非问题（2026-10-13 用户决策）**。`code-metrics-scan.yml` 的 `id-token: write` 是 OIDC 联邦上传**必需**（有注释说明），不是问题；第三方 action 可变 tag 一项，引用的 `pr-label-action`/`pre-commit-action` 均为一方插件，风险显著低于第三方，可低优先级处理 |
| #25 | 长期 PAT 暴露面（workflow 级 `pr: write` + 长期 ROBOT_TOKEN） | **非问题（2026-10-13 用户决策）**。报告自己已复核"token 与不可信代码非同作业"。剩余改进（permissions 按 job 收敛、换短期 token）是平台侧配置优化，非插件代码问题 |
| #21 | extra_args 白名单可绕过任意 `--` 长选项（index.js:39） | **非问题**。① extra_args 走 execFile 数组传参（index.js:358-359），无 shell 解析，无注入面；② pre-commit 自身 argparse 会拒绝未知选项，任意 `--xxx` 直接报错退出；③ 能改变扫描行为的合法选项（`--config`/`--hook-stage`/`--files` 等）均要求 workflow 配置方权限，而该方本就能直接编辑 `.pre-commit-config.yaml`，无权限提升。附注：extra_args 会整体覆盖 PR 模式自动增量参数（index.js:749-751），属配置方显式选择。建议保留非 `--` token 的 exit(1) 拦截作为防御纵深 |
| #27 | pre-commit 日志原样写入 SARIF（tool-parsers.js:273） | **非问题（2026-10-13 用户决策：交由使用方配置控制，插件侧不做进一步处理）**。gitleaks 自带 `--redact` 选项，在 `.pre-commit-config.yaml` 的 args 中显式开启后 Secret/Match 字段输出 `***`，属配置层、零代码的第一道防线；建议在组织的标准 pre-commit 配置模板中统一加 `args: [--redact]`。插件侧已合入的 `redactGitleaksOutput` 掩码保留为兜底（不再扩展其他工具格式的掩码）；用户自备 `*.sarif` 原样上传属业务资产契约，插件不二次加工 |
| #20 | 不可信 PR 代码在特权自托管执行机执行（pre-commit.yml `pull_request_target` + 检出 merge_commit_sha） | **非问题（2026-10-13 用户决策：有意设计）**。`pull_request_target` + 检出 PR merge commit + 执行 PR 内 `.pre-commit-config.yaml` 是**针对开源仓外部人员 PR 的有意门禁设计**（issue 引用的 `allow-unsafe-pr-checkout: true` 即该场景的显式开关）。缓解因素已核实：pre-commit job 未传入 ROBOT_TOKEN（gc_token 未配置），凭证与不可信代码不同 job。残余风险（workflow 级 `pr: write` 作用到门禁 job、长驻自托管执行机）属平台侧整体加固范围，不在插件单仓整改。可回复说明设计意图后关闭 |
| #24 | `.pre-commit-config.yaml` 钩子 `rev` 用可变 tag（v6.0.0 / v8.30.1） | **非问题（2026-10-13 用户决策）**。本仓自身门禁配置，钩子来源可信可控，可变 tag 不构成实际供应链风险；如后续需要可在依赖升级时顺手固定 SHA，不作为安全整改项 |
| #29 | spawn 无超时 / 输出无上限（index.js:199-242） | **暂定非问题（2026-10-13 用户决策）**。① 执行对象与参数由插件自身控制，程序可控；② 大型项目 pre-commit 子进程执行时长不可预估——部分依赖首次下载受网络波动影响很慢，设置 timeout 会误杀合法任务；③ 扫描结果需要完整输出，设 maxBuffer 截断会把大项目误判为环境失败（当初不设上限即有意为之，见 index.js 注释）。维持现状，不整改 |
| #34 | 配置缺失 fail-open 绕过门禁（index.js:755-758，配置不存在时退出码 0） | **非问题（2026-10-13 用户决策）**。配置缺失时静默通过是**业务逻辑确定的既有行为**，且 `.pre-commit-config.yaml` 是否存在、门禁如何断言均属**配置端/使用方**的职责范围，插件按契约执行即可，不属插件侧安全整改项。可回复说明后关闭 |
