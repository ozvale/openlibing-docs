# 安全整改方案知识库（Playbook）

跨仓共享的安全整改方案库，按**问题类型**组织。遇到同类问题时直接引用统一
方案，保证同类问题统一整改方式，避免每个仓临时发明方案。

**使用规则**：
- 定性/出整改建议前先查本库，命中类型直接引用模板
- 新类型方案经用户确认或实施验证后回写本库
- 方案被推翻（如整改回退）时同步标注"暂缓，待 <条件> 后实施"
- 维护流程见 `.agents/skills/gitcode-security-remediation/SKILL.md` Phase 3.3
- 本文件为共享主副本；skill 内置副本
  （`.agents/skills/gitcode-security-remediation/references/security-remediation-playbook.md`）
  随主副本同步更新

人工鉴定的**非问题判定**另见 skill 内置
[security-non-issue-catalog.md](../../.agents/skills/gitcode-security-remediation/references/security-non-issue-catalog.md)。

---

## 公网地址硬编码

- **识别特征**：扫描器（gitleaks/SenInfo 等）报公网 URL/域名硬编码；代码中
  直接写死 `https://xxx.com`、桶名、host 前缀等业务功能性地址。
  注意先区分扫描噪音（package-lock 依赖源 URL、标准格式声明字段、三方库
  自带文档文案、CI 标准 OIDC 端点等——这些直接按非问题排除）。
- **风险本质**：环境切换（prod/beta）需改源码并重新构建发版；地址变更分散
  在多处常量，易漏改。
- **整改方案（按项目形态分派）**：
  - **插件 / 前端项目**：提取到统一配置文件集中管理（如 `config/endpoints.json`
    或 `src/config/endpoints.js`），代码 require 引入读取；保留环境变量覆盖
    能力；环境切换只改配置不改源码。
  - **后端项目**：提取到**配置中心**统一管理（按后端实际使用的配置组件），
    代码从配置读取，支持不发版热切换。
  - **CLI / 脚本工具**：环境变量 / 配置文件注入，保留合理默认值。
- **等价性约束**：配置文件中的默认值必须与原硬编码值**完全一致**（等价变换，
  不改任何对外行为）；不改变输出契约；JS Action 仓需同步重建 dist。
- **实施要点**：待收敛地址先盘点成清单（常量名 + 当前值 + 所在文件:行），
  逐项迁入配置；跨多文件改动时按硬规则 4 与同文件的其他整改合并为一个 PR。
- **验证方式**：默认配置下行为与整改前一致（请求地址逐项比对）；切换配置
  能命中新环境。
- **实施案例**：upload-sarif-action#10（方案 B 已定待实施：OIDC_PROD_BASE、
  OIDC_BETA_BASE、OBS_BUCKET、OBS_READ_ENDPOINT、CodeArts host 共 5 项收敛），
  详见 `issue_docs/upload-sarif-action/security-issues-analysis-20261012.md`；
  upload-ut-action#2（PR #1，环境变量注入 + gitleaks:allow 白名单，2026-10）。

---

## 凭证类规则 snippet 明文留存

- **识别特征**：SARIF/扫描报告将命中凭证类规则（password/secret/token/
  api_key/硬编码口令等）的源码行及上下文窗口（snippet/contextRegion）原样
  上传或持久化，形成凭证多副本长期留存。
- **风险本质**：报告文件被下载/泄露时，明文凭证随 snippet 一并暴露。
- **整改方案**：报告生成/补齐环节对命中凭证类规则的问题行与上下文窗口中的
  字符串字面量做掩码（保留前 2 后 2 + `***`，长度 ≤6 整体掩码）。
- **等价性/取舍声明**：掩码后 snippet 与源码不再逐字一致，前端内容匹配高亮
  退化为按行号定位——安全优先属预期取舍，须评审确认。
- **实施案例**：upload-sarif-action#12（PR #13，maskCredentialSnippet，2026-10）。

---

## 临时文件残留（报告/产物目录）

- **识别特征**：流程将含敏感内容的中间产物写入 `os.tmpdir()` 等临时目录，
  全流程无清理代码，任务结束后跨任务残留。
- **风险本质**：含凭证/snippet 的中间文件长期留存于 runner 磁盘。
- **整改方案**：注册 `process.on('exit')` 钩子兜底清理（覆盖正常结束与
  `process.exit(1)` 失败退出全路径）；或 try/finally 清理。
- **注意**：upload-sarif-action#11 该方案**暂缓回退**——随 ACL 调整一并
  依赖后端联动，待后端支持带凭证下载后统一实施。引用前确认最新状态
  （见 `issue_docs/upload-sarif-action/security-issues-analysis-20261012.md`）。

---

## shell 命令拼接注入（workspace/输入路径进 shell）

- **识别特征**：扫描报 `execSync`/`spawn`（`shell: true` 或默认 shell）+
  模板字符串拼接 workspace、输入参数等外部路径，如
  `` execSync(`find ${workspace} -maxdepth 3 ...`) ``。
- **风险本质**：外部输入含空格或 shell 元字符（`$(...)`、`;`、反引号）时
  形成命令注入面。
- **整改方案（JS/Node 项目）**：用 Node 原生 API 重写等价逻辑，彻底删除
  `child_process` 依赖——`find` 查目录 → `fs.readdirSync(dir,
  { withFileTypes: true })` BFS 递归（深度语义对齐 `find -maxdepth N`，
  注意 N 层 = 距根 N 跳的目录，测试用例层级易写错）；grep/sed 类需求优先
  找 Node 等价物，不保留任何 shell 出口。
- **等价性约束**：查找范围、首个命中语义、日志输出、兜底行为（如无 .git
  兜底 workspace 本身）均不变；补充命中/超深/兜底三类测试用例。
- **验证方式**：全量既有测试 + 新增边界用例（一级命中/嵌套命中/超出深度/
  无命中兜底）；JS Action 仓同步重建 dist。
- **实施案例**：upload-ut-action#16/#20（PR #3，findGitDir BFS 替代 find
  管道，2026-10）。

---

## 可预测临时文件名（抢注/预读面）

- **识别特征**：扫描报临时文件名仅由时间戳/自增序号构成，如
  `ut-coverage-${Date.now()}.json`，写入共享 tmpdir。
- **风险本质**：文件名可预测，同机并发任务或低权限进程可抢注（先创建占位）
  或预读敏感内容；与"残留"不同，本类风险在文件**存续期内**即成立。
- **整改方案**：文件名追加密码学随机后缀
  `path.join(tmpDir, `name-${Date.now()}-${crypto.randomUUID()}.json`)`；
  文件用途、生命周期、清理逻辑（try/finally unlink 等）均不变。
- **等价性约束**：纯等价变换，无输出契约变化。
- **实施案例**：upload-ut-action#5（PR #4，2026-10）。

---

## 对象存储 Key 段未清洗（runId/文件名等动态段）

- **识别特征**：扫描报 OBS/S3 对象 Key 的某个动态段（runId、分支名、文件名）
  直接拼入 Key，未做字符白名单清洗；同 Key 其他段已清洗而该段遗漏（半清洗
  状态常见）。
- **风险本质**：动态段含 `/`、`..`、`?` 等字符时可穿越目录层级或注入
  非预期对象路径，污染/覆盖其他前缀下对象。
- **整改方案**：抽出统一的 Key 段清洗函数（仅保留 `[a-zA-Z0-9._-]`，
  其余折叠为单连字符，trim 首尾连字符，空结果回退默认值如 `manual`），
  所有动态段（含已清洗段）统一走该函数，消除半清洗状态。
- **等价性约束**：Key 结构、固定常量段（前缀/对象名）、下载 URL 格式均
  不变；合法输入（字母数字段）清洗前后逐字节一致。
- **注意**：若扫描同时报"Key 缺组织/租户维度"类结构化问题，属后端检索
  契约，拆为"后端依赖暂缓"，与字符清洗分离，勿混在同一改动。
- **实施案例**：upload-ut-action#11（PR #4，sanitizeKeySegment，2026-10）。

---

## 第三方 SDK 不安全默认值（TLS 证书校验关闭）

- **识别特征**：扫描报云 SDK 客户端构造未显式传安全相关选项，而 SDK 默认
  值不安全。典型：esdk-obs-nodejs（华为云 OBS）`sslVerify` 默认 `false`，
  构造 ObsClient 不传该参数即关闭 TLS 证书校验。
- **风险本质**：中间人可伪造服务端证书截获 AK/SK 与上传数据。
- **整改方案**：构造参数显式传入 `sslVerify: true` 恢复校验。
- **分类**：真问题·需验证——自托管 runner + 企业自签 CA / TLS 解密代理
  场景下，开启校验后可能报证书错误。
- **验证与兼容预案**：统一测试分支实测上传链路；遇自签 CA 报错时，方案是
  `NODE_EXTRA_CA_CERTS` 环境变量注入企业根证书，**禁止回退关闭校验**。
- **等价性约束**：鉴权协议、上传语义完全不变。
- **实施案例**：upload-ut-action#8/#14（PR #4，2026-10，待统一自测验证）。

---

## 第三方 HTTP 依赖存在已知漏洞（如 undici 5.x）

- **识别特征**：SCA / 依赖扫描报 Node 侧 HTTP 客户端库旧版漏洞（undici、axios、
  node-fetch 等）。典型代码形态是「Node 18+ 用内置 fetch，node16 回退到
  `require('undici').fetch`」，该回退分支把旧版库引入依赖树，ncc 打包时整库
  内联进 Action 产物。
- **风险本质**：兜底依赖带入已知漏洞的 HTTP 实现，且被内联进发布产物。
- **整改方案（按项目形态分派）**：
  - **Node SDK / 库（优先，零第三方依赖）**：删除旧版 HTTP 库依赖，用 Node 内置
    `http`/`https` 实现最小 fetch 兼容层，只覆盖项目实际用到的能力
    （method/headers/body 发送；status/headers.forEach/text 读取），超时对齐原库
    默认值（undici fetch 为 300s）；Node 18+ 仍优先走内置 fetch。
  - **Action 仓**：先判定 dist 中命中的来源——来自本仓 SDK 直接内联 → 用上面的
    零依赖方案；来自 `@actions/http-client` 等官方 SDK 传递依赖 → 改源码无法
    消除，按「第三方库内联产物」非问题归档，或单独立项替换 `@actions/core`，
    不与 SDK 整改混在同一 PR。
- **反模式**：为消漏洞直接升大版本（undici 5 → 6）会连带要求 Node >= 18，
  node16 Action 需改 `using: node20`，取决于平台支持程度，属硬规则 2 须评审；
  能用零依赖等价回退时优先选回退。
- **等价性约束**：请求方法/头/体与返回结构不变；有内置 fetch 的运行时执行路径
  不变；`action.yml` 的 `using` 无需调整；dist 必须重新构建，禁止手改。
- **验证方式**：单测临时移除 `globalThis.fetch` 走回退分支（本地 http server 断言
  状态码/响应头/请求方法/请求体），并断言 lock 文件中该依赖条目清零、dist 中
  不再出现该库源码。
- **实施案例**：openlibing/huaweicloud-oidc-sdk-nodejs#19（分支
  `fix-undici-fetch-fallback`，commit `69091ff`，2026-10-26）。

---

## 解析器类 issue 复核要点（ReDoS 定级 / 数值越界入口审计）

处理"解析器 DoS""数值越界"类扫描 issue 时，先做两项复核再定性，避免
高估风险或全局乱改：

1. **正则回溯定级**：逐个检查被报正则是否为真·catastrophic backtracking。
   「前缀锚定 + 惰性量词 + 字面闭合标签」（如
   `/<package[^>]*>([\s\S]*?)<\/package>/g`）**不含嵌套量词歧义**，最坏
   O(n²) 线性回溯而非指数爆炸——秒级延迟不构成进程级 DoS，定级低危；
   真正风险常是超大文件一次性读入内存。首选整改是**文件大小上限拒绝**
   （`fs.statSync` 超限抛 WARN 并跳过），属"新增输入拒绝"须评审；正则
   重写收益低可放弃，让用户裁决取舍。
2. **数值越界入口审计**：对"覆盖率/百分比无边界校验"类 issue，先证明
   `pct(covered, total)` 类函数在 `covered/total` 均来自 `\d+` 正则或
   非负整数时数学上不可能 >100——**唯一真实越界入口是直接透传外部
   预计算百分比字段**（如 coverage.py JSON 的 `totals.percent_covered`
   除以 100）。整改只需在透传入口 clamp（`Math.min(100, Math.max(0, v))`），
   不动全局 pct 签名，避免防御面扩大引入无谓行为变化。
- **实施案例**：upload-ut-action#9/#10（2026-10，影响评估待用户裁决，
  见 `issue_docs/upload-ut-action/blia-issue9-10-20261020.md`）。
