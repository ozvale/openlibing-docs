# 测试策略 — issue_280_UT测试覆盖率插件支持GitHub

> **模板版本**: v3.10
> **对应规则**: AGENTS.md「规则 01 — 需求驱动的测试策略与设计」+「月度版本工作模式」

> 团队：软件实现&持续集成工具链团队 | 月度：202611 | 版本发布日期：20261116 | issue 编号：280 | issue 标题：UT测试覆盖率插件支持GitHub
> 文档状态：已定稿 | 创建日期：2026-11-11 | 负责人：测试（AI 辅助）

---

## 1. 测试策略

> 业务输入**唯一来源**为 gitcode issue 内的开发设计文档，AI/测试人员必须实际读取链接，禁止超出文档范围发散。

### 1.1 Issue 信息

| 字段 | 内容 |
|------|------|
| Issue编号 | 280 |
| Issue标题 | 【openLiBing-coderepo】UT测试覆盖率插件支持GitHub |
| 关联需求 | https://gitcode.com/openlibing/openlibing-coderepo/issues/280（设计文档 PR openlibing-docs#1317；代码 PR openlibing-coderepo#301、upload-ut-action#10） |
| 所属团队 | 软件实现&持续集成工具链团队 |
| 所属微服务 | upload-ut-action（Node.js Action）+ openlibing-coderepo（Java） |
| 所属模块 | UT 覆盖率上报插件 / OBS 下载白名单 / UT 覆盖率展示 |
| 负责人 | taohuoquan（开发）/ 测试（AI 辅助） |
| 创建日期 | 2026-11-11 |

### 1.2 需求摘要

详见 `测试过程数据/需求分析文档.md`：1.2 背景与目标、1.5 接口清单 API-01~API-03、1.6 功能点 `FP-01~FP-12`、1.7 业务规则 `BR-01~BR-15`、1.8 异常边界 `EX-01~EX-12`、1.11 澄清台账 `Q-01~Q-15`。

简述：插件单份代码在运行时识别 GitHub Actions / GitCode Actions，GitHub 侧只读 `GITHUB_*` 上下文并使用 GitHubActions OIDC 换证，覆盖率 JSON 上传隔离桶 `openlibing-github-action`，再由后端 `downloadToTempFile` 双桶白名单放行入库，最终在「代码仓管理 > 分支管理 > UT行覆盖率」展示。

### 1.3 测试目标

1. 验证平台判定与上下文映射的**黑盒可观测结果**：GitHub 运行日志显示平台为 GitHub Actions、上报归属分支与运行 ID 正确（对应 BR-01~BR-04 的可见结果，过程分支由开发单测覆盖）。
2. 验证 GitHub 侧 OIDC 换证使用 `GitHubActions` / `github-actions`，且未声明 `id-token: write` 时失败（FP-05、BR-13、EX-04）。
3. 验证 OBS 桶按平台隔离且对象 key 结构不变（FP-06、FP-07、BR-06~BR-08）。
4. 验证后端双桶白名单放行 GitHub 桶，并拒绝白名单外桶/前缀（FP-09、BR-09、BR-10、EX-07、EX-08）。
5. 验证 GitHub 仓库 UT 覆盖率经回调入库并在平台展示（FP-10）。
6. 验证产物一致性（版本 1.0.2、dist 已重建）与 step 输出兼容（FP-12、FP-08）。

### 1.4 测试范围

| 测试类型 | 是否覆盖 | 说明 |
|----------|----------|------|
| UI功能测试 | 是（限定） | 仅展示核对：`开发管理 > 代码仓管理 > 分支管理` 的「UT行覆盖率」列与 `UtCoverageDetailDialog`（FP-10）。本需求无新页面、无前端改动，不做交互型 UI 用例 |
| API接口测试 | 是 | 主维度：`POST /action-api/ut/coverage/report` 入库（API-01）、GitHub Actions 端到端触发与 OBS 对象校验（API-02）、展示侧 `POST /ut/coverage/file-detail`（API-03）。黑盒覆盖 FP-01、FP-02、FP-03、FP-06、FP-07、FP-09、FP-10；FP-04（双标志冲突）为进程内分支，由开发单测覆盖 |
| DFX测试 | 否 | 无新增性能指标；OBS 上传重试（3 次）与回调降级仅作为异常路径断言（EX-05、EX-06），不出独立性能用例 |
| 安全测试 | 是（限定） | 6 维度：① 认证校验 **覆盖**（OIDC 换证成功/缺失 `id-token: write` 失败，EX-04）；② 横向越权 **覆盖**（后端白名单外桶/前缀拒绝，EX-07/EX-08）；③ 纵向越权 不覆盖（无角色面变更）；④ 传输安全 不覆盖（沿用 APIG/IAM 既有链路）；⑤ CSRF 不覆盖（机机接口、无浏览器会话态）；⑥ 敏感信息防护 **覆盖**（日志不打印 AK/SK/SecurityToken，设计 7 章） |

> 维度组合定稿（v3.23 + 用户修订 Q-16）：**API + 安全为主，UI 仅展示核对，DFX 不覆盖；测试侧只做黑盒，不重复开发自测**。
> 备选与权衡：A「含插件上下文层（本地纯函数断言）」——与开发自测 `test/platform-context.test.js` 重复，用户判定属开发自测内容（Q-16），剔除；B「仅端到端」——无法覆盖桶白名单拒绝等后端口径；C「三层全量 + GitCode 回归」——用户明确不做 GitCode 回归（Q-11）。最终：**端到端层 + 后端白名单层 + 页面展示核对**，纯函数分支以「由开发单测覆盖」登记豁免并引用 PR#10 的 `npm test` 63/63 证据。

### 1.5 测试策略

- **执行顺序（用户确认 Q-17）**：**先做端到端功能验证**（push / PR 两条完整链路，一次运行贯穿换证 → 上传 GitHub 桶 → 回调入库 → 平台可见），端到端跑通后再补分段用例（失败面、白名单拒绝、降级）用于定位与加固。
- **端到端层（自动化，真实 GitHub Actions）**：在 `theWoodlc/ldf` 上以 Python + coverage.py 生成 `coverage.json`，push(main) 与 pull_request 各跑一次；单次运行内断言运行日志平台标识与 OBS 桶、OIDC 提供商/委托、对象 key 结构、回调成功，并回看平台「UT行覆盖率」列（FP-01、FP-02、FP-03、FP-05、FP-06、FP-07、FP-10）。
- **后端白名单层（自动化）**：验证 `downloadToTempFile` 对 GitHub 平台的放行与非白名单桶/前缀的拒绝（FP-09、BR-09、BR-10、EX-07、EX-08）。优先通过 beta 上可构造的入库入口做黑盒验证；若机机接口签名不可得，则以「PR#301 diff + 现有单测断言」为等价证据并登记未覆盖，不伪造通过。
- **豁免（由开发自测覆盖，不重复设计用例）**：平台判定全分支、双标志冲突、`ATOMGIT_*` 映射、`GITHUB_EVENT_PATH` 缺失/非法、`GITHUB_SERVER_URL` 尾斜杠、`unknown-repo`/`manual` 兜底、`setOutput` 双文件缺失告警等进程内分支，均由 `test/platform-context.test.js`、`test/obs-uploader.test.js` 覆盖；证据引用 PR#10 记录的 `npm test` 63/63 通过（Q-04、Q-16）。
- **插件引用**：先用 `uses: openlibing-test/upload-ut-action@v1.0.2`；若跨 owner 私有 action 被拒，回退为 workflow 内 clone 源码 + `uses: ./upload-ut-action`（Q-07）。
- **对照基线**：`openlibing-test/ut-coverage-demo` 已有成功运行（2026-11-10 workflow_dispatch success），用于区分「插件能力问题」与「ldf 集成问题」。
- **优先级**：P0 = 端到端 push 全链路（含平台日志与桶）、PR 事件目标分支归属、平台展示核对、后端 GitHub 桶放行；P1 = OIDC 提供商日志、`id-token` 缺失失败、白名单拒绝、产物版本与 dist 内联、敏感信息；P2 = 手动触发、回调降级、空报告、`obs_acl` 非法值、对象归属已知边界。
- **脚本位置**：后端/API 类 `src/automation/software-cicd/api/development_management/code_repository_management/beta/`；UI 展示核对 `src/automation/software-cicd/ui/development_management/code_repository_management/beta/`；GitHub 侧 workflow 与示例项目落 `theWoodlc/ldf`（不落本仓）。

### 1.6 复用检查（强制）

| 检索范围 | 可复用用例 | 复用结论 |
|-----------|-----------|----------|
| 特性树（本团队 01~04） | `01_系统测试/开发管理/代码检查(beta)/TC-ISSUE205-003_度量指标帮助文档链接验证.md`（仅涉及度量指标文案） | **无 UT 覆盖率上报/展示类存量用例**，仅可参考其代码度量页面操作路径；本需求用例需新建 |
| 易用性通用库 | 无（本需求无界面交互变更） | 不适用 |
| API 测试目录 | `02_API测试/开发管理/代码仓管理/` 无 UT 覆盖率接口用例 | 需新建 |
| 页面对象 | `src/automation/software-cicd/ui/development_management/code_repository_management/` 已有仓库/分支管理相关页面对象 | **部分复用**：分支管理页定位器（`span.metrics-link`）与筛选弹层可复用并扩展「UT行覆盖率」断言 |

### 1.7 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| `openlibing-test/upload-ut-action` 为私有仓库，跨 owner 引用可能被 GitHub 拒绝 | 层③ 无法启动 | 按 Q-07 预置 clone 回退；先跑一次判定 |
| IAM `sub` 未授权仓库不可构造 | EX-11（未授权换证失败）不可测 | 本次登记未覆盖（Q-14），由开发确认后单独补测 |
| 平台机机接口需 IAM 签名 | 层② 黑盒不可直接调用 | 优先走真实端到端入库；不可行则以 PR#301 diff 与单测断言为等价证据并登记未覆盖 |
| ldf 当前无 UT 覆盖率数据、GitHub 行「操作」disabled | 展示核对只能看列值，明细弹窗可能打不开 | 以上报成功后的「UT行覆盖率」列非 `--` 为主要通过判据，弹窗作为补充 |
| 对象 key 中 `yyyyMMdd.HH` 时区口径未明确 | 断言可能误判 | 仅校验 `\d{8}\.\d{2}` 结构与其余路径段，不锁定时区（P-02） |
| GitHub Actions 在用户仓库的权限策略未知 | `id-token: write` 可能被组织策略禁用 | 首跑即验证，失败则记录为阻塞并反馈 |
| 用户明确不复跑开发单测、不做 GitCode 回归 | 两仓单测结论与 GitCode 等价性不由我方独立取证 | 报告中引用 PR 记录并标注「未独立复跑/未回归」 |
| 层① 剔除后进程内分支（双标志冲突、事件文件缺失等）无测试侧独立证据 | 这些分支仅由开发单测覆盖 | 设计中的豁免 TP 明确引用 `test/platform-context.test.js` 与 PR#10 的 `npm test` 63/63；审核闸门确认接受该依赖 |

### 1.8 依赖与前置条件

- 环境：BETA `https://beta.openlibing.com`，已部署 `openlibing-coderepo` PR#301（用户确认 Q-01）。
- 平台：`theWoodlc/ldf` 已接入项目 3（仓库别名 `ldf`，GitHub 平台，Python 语言）；UT 覆盖率展示入口为「代码仓管理 > 分支管理 > UT行覆盖率」。
- GitHub：仓库 `theWoodlc/ldf`（public，默认分支 main，现有 workflow `pr-sync.yml`）；令牌具备 `repo` + `workflow` 权限，仅存 `.env.local` 的 `ISSUE280_*`，禁止提交。
- 华为云：IAM 已注册 `GitHubActions` 提供商与 `github-actions` 委托；后端 OBS 凭证对 `openlibing-github-action` 有 GetObject 权限（用户确认 Q-01）。
- 测试数据：Python 最小示例项目 + `coverage.json`（由 `coverage run -m pytest` + `coverage json` 生成）；对照仓 `openlibing-test/ut-coverage-demo` 已有成功基线。
- 账号：平台侧使用 GitCode 会话（liudongfang，仓库责任人为刘东方）。
