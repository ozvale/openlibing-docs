# 非问题判定知识库（人工鉴定归档）

人工鉴定的非问题判定库，供新一批扫描 issue 定性时**去重排除**复用。
与 [security-remediation-playbook.md](security-remediation-playbook.md)
（整改方案库）配套：一个管"怎么改"，一个管"为什么不用改"。

**收录边界**：只收录**跨仓可复用的模式级判定**（扫描器噪音、通用误报形态）；
与特定仓业务设计绑定的判定（桶 ACL 策略、静态 AK/SK 取舍等）**不进本库**，
保留在各仓定性文档（`issue_docs/<repo>/security-issues-analysis-*.md`）。

**使用规则**：
- 新一批扫描 issue 定性时先比对本库：命中同根因/同模式的直接复用结论排除，
  标注"非问题判定（catalog，决策日期）"
- 新的模式级判定经用户确认后按文末模板回写本库
- 维护流程见 `.agents/skills/gitcode-security-remediation/SKILL.md` Phase 3.1/3.2

---

## 扫描器噪音：依赖锁文件中的 registry/源 URL

- **识别特征**：gitleaks/SenInfo 命中 `package-lock.json` 等依赖锁文件中的
  npmmirror、taobao registry、公司内部源等 URL。
- **为什么不是问题**：属正常依赖安装源记录，非业务代码硬编码，不可改也不
  需改。
- **处置**：直接排除，不登记白名单注释（锁文件由工具生成，加注释会被
  重新生成覆盖）。

## 扫描器噪音：标准格式声明字段

- **识别特征**：命中 `json.schemastore.org`、SARIF 标准格式声明字段等
  schema/格式声明 URL。
- **为什么不是问题**：属数据格式的标准声明，非业务端点。
- **处置**：直接排除。

## 扫描器噪音：三方库自带文案 / CI 标准端点

- **识别特征**：三方依赖源码内自带的文档示例 URL；`token.actions.
  githubusercontent.com` 等 CI 平台标准 OIDC 端点。
- **为什么不是问题**：三方库自带内容不在整改范围；CI 平台标准端点是公开
  协议约定，无敏感性。
- **处置**：在 issue 定性文档标注噪音原因后排除。

## 门禁设计：pull_request_target 检出并执行外部 PR 代码

- **识别特征**：安全扫描报 workflow 使用 `pull_request_target` + 检出
  PR merge commit（或显式 `allow-unsafe-pr-checkout: true`），外部 PR
  代码在自托管执行机执行。
- **为什么不是问题**：针对开源仓外部人员 PR 的**有意门禁设计**（如
  pre-commit 门禁必须执行 PR 自带的 `.pre-commit-config.yaml`）。
  定性前须核实缓解因素：门禁 job 未传入凭证（ROBOT_TOKEN 等）、凭证与
  不可信代码不同 job；workflow 级权限收敛、长驻执行机隔离属平台侧
  整体加固范围，不在插件单仓整改。
- **处置**：核实缓解因素成立后按非问题归档（可回复说明设计意图后关闭）；
  缓解因素不成立（门禁 job 持有凭证）则升级为真问题。
- **适用范围**：使用自托管执行机 + 接收外部 PR 的插件仓。
- **案例**：pre-commit-action#20（2026-10-13 用户决策），详见
  `issue_docs/pre-commit-action/security-issues-analysis-20261012.md`。

## 自有门禁配置中的可变 tag 依赖

- **识别特征**：扫描报本仓自身门禁/CI 配置（如 `.pre-commit-config.yaml`
  钩子 `rev`、workflow `uses`）引用可变 tag（v6.0.0 / v8.30.1 等）而非
  commit SHA。
- **为什么不是问题**：本仓自身门禁配置，钩子/Action 来源可信可控，可变
  tag 不构成实际供应链风险。
- **处置**：非问题归档；如后续依赖升级可顺手固定 SHA，不作为安全整改项。
- **案例**：pre-commit-action#24（2026-10-13 用户决策），详见
  `issue_docs/pre-commit-action/security-issues-analysis-20261012.md`。
- **案例**：pr-sync-action#15（2026-10-23 用户决策），命中
  `code-metrics-action@v1.0.3`、`pr-label-action@v1.0.0`、
  `pre-commit-action@v1.0.2`，均为本组织自有门禁组件，详见
  `issue_docs/pr-sync-action/security-issues-analysis-20261020.md`。

## OIDC 联邦必需的 id-token: write 权限

- **识别特征**：安全扫描报 workflow job 声明 `id-token: write`（OIDC
  token 权限）+ 引用可变 tag 的 action。
- **为什么不是问题**：`id-token: write` 是 OIDC 联邦身份认证上传云产物
  （如上传 SARIF/报告到云服务）的**必需权限**，属业务功能；引用的
  action 若为一方插件（自家仓），风险显著低于第三方。
- **处置**：确认权限有业务用途注释后按非问题归档；一方插件可变 tag 可低
  优先级处理，不作安全整改项。
- **案例**：pre-commit-action#30（2026-10-13 用户决策），详见
  `issue_docs/pre-commit-action/security-issues-analysis-20261012.md`。
- **案例**：security-compilation-options-action#18（2026-10-27 用户确认归档；
  `nightly-schedule-scan.yml`/`code-metrics-scan.yml` 的 `id-token: write` +
  自有 Action 可变 tag，`uses` 无第三方），详见
  `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
  5.2 节。

## 平台侧 workflow 配置优化项（非插件代码问题）

- **识别特征**：扫描报长期 PAT 暴露面（workflow 级 `permissions` 覆盖过宽、
  长期 ROBOT_TOKEN 等），指向 workflow/平台配置层。
- **为什么不是问题**：插件代码侧已核实缓解因素（如 token 与不可信代码非
  同作业）；剩余改进（permissions 按 job 收敛、换短期 token）属**平台侧
  配置优化**，超出插件单仓整改范围。
- **处置**：定性文档标注"平台侧配置优化"后排除，可在平台加固 issue 中
  统一跟进；不在插件仓开安全整改。
- **案例**：pre-commit-action#25（2026-10-13 用户决策），详见
  `issue_docs/pre-commit-action/security-issues-analysis-20261012.md`。

---

## workflow 配置方输入的路径穿越/越界读写

- **识别特征**：扫描报插件的路径类 input（`artifact-path`、`output`、
  `report-dir`、`sarif-file`、`package-name` 等）接受任意绝对路径或含
  `../` 的相对路径，可读写 runner 上工作区之外的文件。
- **为什么不是问题**：这些 input 由 **workflow 配置方**（有仓库写权限、
  能改 CI 的人）设定，非 PR 作者可控；配置方本就能在 workflow 里写
  `run: cat /etc/shadow` 直接读写任意路径并外传，插件侧路径穿越不构成
  新增提权面。属纵深防御建议而非漏洞。
- **处置**：非问题归档。可选强化（限制输入在工作区内，第 5 类新增输入
  拒绝）仅在用户明确要求时实施，须走业务逻辑影响评审。
- **适用范围**：所有以 workflow input 接收路径的扫描/上报类插件仓。
- **案例**：pre-commit-action#28（sarif-file/report-dir，2026-10-13 用户决策），
  详见 `issue_docs/pre-commit-action/security-issues-analysis-20261012.md`。
- **案例**：security-compilation-options-action#25（output/package-name 穿越）+
  #41（artifact-path 任意路径）（2026-10-27 用户确认归档），详见
  `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
  5.1 节。

---

## 环境变量作为 CI 信任边界（身份/配置类）

- **识别特征**：扫描报插件从环境变量直取 OIDC token、认证模式标识
  （`ACTIONS_ID_TOKEN_REQUEST_URL`、`HUAWEICLOUD_OIDC_TOKEN` 等）或
  未校验 OIDC 端点 URL，判定为「流水线身份可伪造」。
- **为什么不是问题**：环境变量即 Actions 的信任边界——关键变量仅由
  runner（workflow 声明 `permissions: id-token: write` 时）或 workflow
  配置方注入，PR 作者不可设；能写这些环境变量的主体本就具备修改
  workflow / 在 runner 执行任意代码的能力，「伪造身份」零增量收益。
  OIDC 端点 host 白名单属「新增输入拒绝」，会破坏私有云/自建平台兼容性。
- **处置**：非问题归档。若平台侧要求收紧，走评审并在 action.yml 暴露
  可配置白名单；runner 隔离缺陷（PR 可控值透传进 env）归平台侧。
- **案例**：security-compilation-options-action#20（2026-10-27 用户确认归档，
  2026-10-27 复核 src 布局代码证据），详见
  `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
  5.4 节。

---

## 已标注废弃的静态凭证兼容通道

- **识别特征**：扫描报插件保留静态 AK/SK（或长期凭证）直连通道，
  且「未强制 OIDC、无 OIDC 即失败」被作为整改建议提出。
- **为什么不是问题**：静态凭证通道是**已标注废弃的兼容通道**（README
  注明），保留为存量脚本兼容的易用性取舍；OIDC 为默认路径（检测到
  `ACTIONS_ID_TOKEN_REQUEST_URL` 即走 OIDC）。「无 OIDC 直接失败」=
  默认行为反转（fail-open → fail-closed，硬规则 2 第 4 类），影响存量
  使用方，不作为安全整改实施。
- **处置**：非问题归档。可选等价加固：AK/SK 分支入口加一行
  deprecation warning 日志（不改变行为）。
- **案例**：upload-sarif-action#15（2026-10-13 用户决策），详见
  `issue_docs/upload-sarif-action/` 定性文档。
- **案例**：security-compilation-options-action#43（2026-10-27 用户确认归档），
  详见 `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
  5.1 节。

---

## pip 安装精确版本固定 + 固定镜像源（无 --require-hashes）

- **识别特征**：扫描报 CI 内 `pip install <pkg>==<精确版本>` 未使用
  `--require-hashes`，且使用固定公网镜像源（如阿里云 PyPI）。
- **为什么不是问题**：版本已精确固定（无浮动 tag），命令为静态参数
  数组、无用户输入参与——精确版本固定即满足供应链要求，不引入
  `--require-hashes`（哈希清单维护成本与发版节奏冲突）；固定镜像源
  地址非动态/外部可控值。
- **处置**：非问题归档。注意与「执行目录安全化」（pip 安装 cwd 脱离
  工作区，防 Python 模块遮蔽）区分——后者是真问题整改项，互不影响
  定性。
- **案例**：pre-commit-action#23（2026-10-13 评审决策），详见
  `issue_docs/pre-commit-action/security-issues-analysis-20261012.md`。
- **案例**：security-compilation-options-action#19（pip pyelftools==0.31，
  2026-10-27 用户确认归档；执行目录安全化归同仓 #39 整改），详见
  `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
  5.3 节。

---

## 子进程/请求超时缺失（已有请求超时 + 平台 job 级超时兜底）

- **识别特征**：扫描报插件 spawn/execSync 子进程无 `timeout`/`maxBuffer`、
  请求无超时等，判定为 hang/DoS 风险。
- **为什么不是问题**：须分两面核实——① **网络面**：出站请求（上报）若已带
  超时与失败反馈（如 axios timeout），指控的网络 hang 面不成立；② **子进程面**：
  CI 平台对容器/job 有超时管理，子进程最坏被平台超时终止，损失 = 本次任务
  数据（定时任务次日补齐）——属「平台侧承载」归属（同沙箱隔离/执行机隔离），
  插件侧再加超时属冗余防御，且粒度更细仅提升失败定位效率（运维收益），
  非安全收益。
- **处置**：非问题归档。前提核实清单：唯一外发请求已带超时？任务属定时/
  可重跑类（非 PR 门禁，失败无合入影响）？若插件实际挂 PR 流水线（子进程
  hang 会卡合入），则改判真问题。更细的超时/失败定位作为功能需求评估。
- **适用范围**：定时全量扫描类插件仓（schedule/workflow_dispatch 触发）。
- **案例**：security-compilation-options-action#27 + #40①（2026-10-27 用户
  裁决改判非问题，axios 60s 超时已存在 + GitCode 平台容器子进程超时管理），
  详见 `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
  4.7 节。
- **案例**：security-compilation-options-action#40②（恶意 ELF 解析崩溃/资源
  耗尽，2026-10-27 用户裁决改判非问题——非 PR 门禁 + 平台超时兜底 +
  `except ELFError` 记 failed_files 属既有受控失败语义，解析器预检属健壮性
  增强非安全整改），详见同文档 4.4 节。

---

## 上报类插件的 fail-open 默认（无 PR 门禁语义）

- **识别特征**：扫描报「上报失败不使 step 失败」「扫描环境准备失败仅 warning」
  「无必需语义」等 fail-open 形态，并判定为「合规门禁可被绕过」。
- **为什么不是问题**：指控隐含前提是插件承担 PR 流水线门禁（阻断合入）语义。
  须核实 workflow 触发器：仅 `schedule` / `workflow_dispatch`（全量扫描上报类
  插件）则前提不成立——插件成败不影响任何合入决策，门禁判定由平台侧数据
  对账承载；fail-open 是上报类工具的合理默认（漏一次数据可由下次定时扫描
  补齐，中断流程代价更高）。上报失败源于网络/服务端故障，无攻击者路径。
- **处置**：非问题归档。须先确认触发器不含 `pull_request`/`push`——若插件
  实际挂 PR 流水线（失败应阻断合入），则 fail-open 升级为真问题。残余的
  运维可观测性诉求（`fail-on-upload-error` 可选 input、失败告警）转功能
  需求评估，不走安全整改。
- **适用范围**：nightly/定时全量扫描 + 报告上报类插件仓。
- **案例**：security-compilation-options-action#22（2026-10-27 用户裁决改判
  非问题并撤销原整改 PR F），详见
  `issue_docs/security-compilation-options-action/security-issues-analysis-20261026.md`
  4.6 节。

---

## 构建产物：dist 内第三方库被内联（`@actions/http-client` → undici）

- **识别特征**：SCA 在 JS Action 仓报 undici 5.x 漏洞，但本仓 `package.json`
  未声明 undici，`dist/index.js` 中能搜到 `undici` 源码与 `class UndiciError`
  等片段。
- **为什么不是问题**（指"改本仓源码可消除"这一诉求不成立）：undici 来自
  `@actions/core` → `@actions/http-client@2.2.3` 的传递依赖（`undici ^5.25.4`），
  由 ncc 整库内联进产物；本仓源码无 `require('undici')`，改源码无法消除。
  它常被误认为来自本仓 OIDC SDK 的 node16 fetch 回退——需先查 lock 文件的
  依赖归属再定性。
- **处置**：先区分来源——本仓 SDK 直接依赖 → 走 playbook「第三方 HTTP 依赖
  存在已知漏洞」的零依赖回退；仅为 `@actions/http-client` 传递依赖 → 按
  非问题归档（写明来源与不可达/无调用方证据），或在独立 issue 中用原生实现
  替换 `@actions/core`，不与 SDK 整改混在同一 PR。
- **适用范围**：所有使用 `@actions/core` ≥1.10 的 Node Action 仓（跨仓通用）。
- **案例**：huaweicloud-oidc-sdk-nodejs#19 整改中确认（3 个测试 Action 的
  dist 残留 undici 属此类，SDK 侧直接依赖已移除，2026-10-26），详见
  `issue_docs/huaweicloud-oidc-sdk-nodejs/security-issues-analysis-20261026.md`
  4.2 节。

---

## 条目模板（新增判定时套用）

```markdown
## <模式名>

- **识别特征**：<扫描器如何命中、典型形态>
- **为什么不是问题**：<设计意图/易用性取舍的具体机制>
- **处置**：<排除 / 加白名单注释 / 仅记录>
- **适用范围**：<跨仓通用 / 仅 XX 类项目>
- **案例**：<repo>#<n>（<决策日期>），详见 <定性文档路径>
```
