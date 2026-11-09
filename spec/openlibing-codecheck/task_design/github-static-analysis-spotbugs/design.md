# 静态代码分析 GitHub 接入方案与文档 · SpotBugs — 设计文档

## 1. 方案设计

### 1.1 需求背景与目标态

openLiBing 的代码检查链路当前主要面向 GitCode Actions：各静态分析工具产出 SARIF，经 `upload-sarif-action` 上传 OBS 并回调 openLiBing，最终在「开发管理 - 代码检查」页面展示。

「静态代码分析 GitHub 接入」FE 已由 clang-tidy 完成首个落地，沉淀了可复用的 GitHub 接入范式：平台来源枚举 `GITHUB_ACTION`、前端平台筛选与来源标签、`upload-sarif-action` / `pre-commit-action` 双插件的平台识别与 OIDC 免密换证。本 US 将该范式复制到 Java 字节码分析工具 **SpotBugs**，覆盖 Java 语言仓库的 GitHub 接入。

**目标态**：

1. 转测阶段在 GitHub 平台 `openlibing-test` 组织下准备可运行的 SpotBugs 流水线（工作流显式设置 `env_type: beta`），覆盖 workflow 全量扫描与 pre-commit 集成两种入口；
2. SpotBugs 基于编译产物分析，扫描结果通过 spotbugs-maven-plugin 原生 `sarifOutput` 生成 SARIF，上传 OBS 并回调 openLiBing；
3. 「代码检查」页面筛选 GitHub 平台后能看到 SpotBugs 问题列表与详情（前端零改动，复用 clang-tidy 已交付能力）；
4. 同步更新 GitCode `docs` 仓的 SpotBugs 用户文档（`2.7 GitHub Actions 配置（pre-commit 场景）`、`3.5 GitHub Actions 配置（workflow 全量扫描）` 与 `demos/github` 两套示例）；
5. 本设计文档归档到 `openlibing-docs` 仓。

本 US 以文档交付为主，暂不创建 GitHub demo 仓、不实跑流水线；SpotBugs 的 GitHub 链路验证在后续转测阶段完成。前端原型复用「静态代码分析 GitHub 接入」FE 已归档的 prototype.html，本 US 无前端改动、不单独出原型。

### 1.2 总体方案

沿用**单份代码、运行时识别平台**的方案，不为 GitHub 维护独立分支：

- 业务配置（`pom.xml` 中 spotbugs-maven-plugin 的规则过滤、分析强度、SARIF 输出、`.pre-commit-config.yaml` 钩子）在 GitCode 与 GitHub 完全复用，差异集中在 workflow 写法与插件引用；
- 两个 action 按 `GITHUB_ACTIONS` 识别运行平台，只读取对应平台的上下文变量（clang-tidy US 已交付，本 US 直接复用）；
- GitHub 侧使用 `GitHubActions` OIDC 身份提供商免密换证，OBS 桶按平台隔离；
- SpotBugs 分析 Java 字节码，扫描前必须先编译产出 `target/classes`：workflow 场景编译一次后执行 `spotbugs:spotbugs`，pre-commit 场景由钩子执行 `mvn compile spotbugs:check`；
- 产品侧零改动：来源枚举与前端标签沿用 clang-tidy 已上线能力；
- 文档在 GitCode `docs` 仓的 full-analysis 方案内扩展，不新增与 `full-analysis` 并列的目录。

### 1.3 关键选型与理由

| 决策点         | 选择                                                            | 理由                                                                                                     |
| -------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 认证方式       | OIDC 免密换证（`GitHubActions` 身份提供商）                     | 复用 clang-tidy 已打通的链路，不落任何长期 AK/SK                                                         |
| OBS 桶         | GitHub 使用 `openlibing-github-action`                          | 与 GitCode 桶隔离，便于权限与成本归集（复用既有桶，无新增）                                              |
| SARIF 产出     | spotbugs-maven-plugin 原生 `sarifOutput`（4.9.8.3）             | 插件直接输出 SARIF 2.1.0，**零转换器、零预置二进制**，较 clang-tidy 的 `clang-tidy-sarif` 显著简化供应链 |
| 编译前置       | workflow 执行 `mvn clean package -DskipTests` 后再扫描          | SpotBugs 分析 `.class` 字节码，`target/classes` 必须存在；先编译保证扫描结果完整                         |
| 失败语义       | pre-commit 用 `spotbugs:check`；workflow 用 `spotbugs:spotbugs` | `check` 发现缺陷非零退出以拦截提交；`spotbugs` 返回 0 只产出报告，避免全量扫描因存量问题阻断流水线       |
| 入口形态       | pre-commit 集成 + workflow 全量扫描并存                         | 分别覆盖提交前拦截与全量归档场景，共用同一份 pom 插件配置（pre-commit 仅在命令行覆盖 SARIF 输出目录）    |
| 产品侧改动范围 | 无                                                              | 来源枚举与前端标签已由 clang-tidy US 交付，本 US 仅验证复用                                              |

### 1.4 涉及文件与跨仓影响

| 仓库 / 模块                               | 涉及内容                                                                                                                    | 是否改代码 |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `openlibing-test/spotbugs-full-scan-demo` | 后续转测新建：示例 Java 代码、`pom.xml`、`spotbugs-include.xml`、`.pre-commit-config.yaml`、`.github/workflows/` 两条工作流 | 新建       |
| `openlibing-test/upload-sarif-action`     | 固定到已验证的完整 commit SHA 引用（不跟踪可变 `main`），无代码改动                                                         | 否         |
| `openlibing-test/pre-commit-action`       | 固定到已验证的完整 commit SHA 引用（不跟踪可变 `main`），无代码改动                                                         | 否         |
| `docs`（GitCode）                         | `tools/spotbugs/README.md` 2.7 / 3.5 小节、`demos/github/` 两个示例、`full-analysis/README.md` 4.4 导航                     | 文档       |
| `openlibing-docs`                         | 本设计文档归档                                                                                                              | 文档       |
| `openlibing-codecheck`                    | 无改动；依赖 `static-alarm-github-adapt` 已交付的 source 枚举、repoType 解析、OBS 双桶白名单                                | 否         |
| `openlibing-web`                          | 无改动；平台筛选与来源标签复用 clang-tidy US 已交付能力                                                                     | 否         |

## 2. 实现逻辑设计

### 2.1 主流程

场景二（workflow 全量扫描）：

```text
GitHub 代码仓触发 workflow（手动 / push / 定时）
  → actions/checkout@v4
  → actions/setup-java@v4（Temurin JDK，cache: maven）
  → mvn -B clean package -DskipTests（产出 target/classes）
  → mvn -B spotbugs:spotbugs（复用 pom 插件配置，输出 target/reports/spotbugs.sarif）
  → upload-sarif-action：路径归一化 + 代码片段补齐
  → OIDC 申请 ID Token → 华为云 STS 换取临时凭证
  → 上传 OBS（openlibing-github-action）
  → APIG 回调 openLiBing（source=GITHUB_ACTION）
  → 解析入库 → 代码检查页面筛选 GitHub 查看结果
```

场景一（pre-commit 集成）：

```text
GitHub 代码仓触发 workflow
  → actions/checkout@v4 → actions/setup-python@v5 / actions/setup-java@v4
  → pre-commit-action 读取 .pre-commit-config.yaml 执行 mvn-spotbugs 钩子
  → 钩子执行 mvn compile spotbugs:check（发现缺陷非零退出，拦截提交）
  → 钩子通过 -DsarifOutputDirectory=/tmp/pre-commit-reports 覆盖 pom 默认目录，pre-commit-action 从 report-dir 收集并通过 sarif-files 输出
  → upload-sarif-action 读取 sarif-files 上传 OBS + 回调 openLiBing（category=pre-commit-report）
```

PR 事件下 `pre-commit-action` 按约定只做门禁检查，不生成/收集 SARIF；文档中的上传步骤以 `sarif-files` 非空为执行条件，避免空报告上传失败。

### 2.2 平台识别与上下文映射

复用 clang-tidy US 已交付的插件能力，本 US 无代码改动：

平台判定：`GITHUB_ACTIONS=true` 为 GitHub，其余按 GitCode 处理；判定结果在进程启动时固化。

| 回调字段        | GitHub 取值                                      | GitCode 取值                            |
| --------------- | ------------------------------------------------ | --------------------------------------- |
| `repoUrl`       | `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY`        | `ATOMGIT_REPOSITORY_URL`                |
| `pipelineId`    | `GITHUB_JOB`                                     | `ATOMGIT_PIPELINE_ID`                   |
| `pipelineName`  | `GITHUB_WORKFLOW`                                | `PIPELINE_NAME` / `ATOMGIT_WORKFLOW`    |
| `pipelineRunId` | `GITHUB_RUN_ID`                                  | `ATOMGIT_RUN_ID`                        |
| `branch`        | `GITHUB_BASE_REF`（PR）/ `GITHUB_REF_NAME`       | `ATOMGIT_HEAD_REF` / `ATOMGIT_REF_NAME` |
| `commitId`      | `GITHUB_SHA`                                     | `ATOMGIT_SHA`                           |
| `sourceRunUrl`  | 仓库地址 + `GITHUB_RUN_ID` 拼装的 Actions 运行页 | 仓库地址 + `ATOMGIT_RUN_ID`             |

### 2.3 认证与上传逻辑

全部复用 clang-tidy US 已交付链路：

1. GitHub 平台使用 `GitHubActions` OIDC 身份提供商，SDK（≥ v0.0.7）按 `GITHUB_ACTIONS` 自动选择，不手写 `configure`；
2. 通过 `ACTIONS_ID_TOKEN_REQUEST_URL/TOKEN` 申请 OIDC ID Token，调用华为云 STS `AssumeAgencyWithOIDC` 换取临时 AK/SK/SecurityToken；
3. OBS 桶按平台选择：GitHub 为 `openlibing-github-action`，GitCode 为 `openlibing-gitcode-action`；
4. 上传对象保持现有公共读策略，对象 key 结构不变；key 由仓库/分支/commit 等可推导信息拼装且 SARIF 含补齐的源码片段，公共读存在跨租户信息暴露面——禁用公共列举只能降低批量枚举风险，无法阻止已知 key 的定向匿名下载，残留风险与访问控制结论见第 7 章第 7 条；
5. 上传与回调沿用指数退避重试（默认 3 次）；回调失败仅告警，以 OBS 上传成功为准；
6. 结果回传环境由 `env_type` 控制：`beta`（测试环境）/ `prod`（正式环境，默认值）；demo/转测工作流必须显式设置 `env_type: beta`，否则会默认写入正式环境。

### 2.4 前端展示逻辑

**无前端改动**。列表页 GitHub 平台筛选、数据来源 `GitHub Action` 标签、详情页两处来源标签均已由 clang-tidy US 交付上线，本 US 的 SpotBugs 数据按 `source=GITHUB_ACTION` 上报后自动进入既有展示链路。

### 2.5 边界与异常处理

| 场景                              | 处理                                                                                                                                                                                                                                                                                                                                                     |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SpotBugs 分析字节码               | 必须先编译产出 `target/classes`；workflow 先执行 `mvn clean package -DskipTests`，pre-commit 钩子执行 `mvn compile spotbugs:check`。缺少编译产物会导致扫描结果为空                                                                                                                                                                                       |
| pre-commit 钩子按文件列表扫描     | 钩子必须 `pass_filenames: false`，由 Maven 插件按项目整体分析；否则 pre-commit 传入的文件列表对 SpotBugs 无意义                                                                                                                                                                                                                                          |
| 拦截语义                          | `spotbugs:check` 发现缺陷非零退出，用于 pre-commit 拦截；`spotbugs:spotbugs` 发现缺陷返回 0，用于 workflow 只产出报告                                                                                                                                                                                                                                    |
| SARIF 输出路径                    | 必须在 pom `<configuration>` 配置 `sarifOutput` / `sarifOutputDirectory` / `sarifOutputFilename` 三件套；未配置时默认输出到 `target/spotbugsSarif.json`，上传路径需与之对应。workflow 使用 pom 默认目录 `target/reports`；pre-commit 钩子通过 `-DsarifOutputDirectory=/tmp/pre-commit-reports` 覆盖，保证与 pre-commit-action 的 report-dir 采集目录一致 |
| GitHub PR 事件（pre-commit 场景） | `pull_request` 触发时 `pre-commit-action` 只做增量门禁，不生成/收集 SARIF；上传步骤以 `steps.pre-commit.outputs.sarif-files != ''` 为条件跳过                                                                                                                                                                                                            |
| PR 触发（含 fork / 同仓）         | IAM 信任策略仅放行 `push` 形 `sub`，`pull_request` 形 `sub` 一律被拒绝，PR 触发的 workflow 不要执行上传换证；测试与验证必须使用 `push` 或手动触发                                                                                                                                                                                                        |
| GitHub 托管 runner Maven          | `ubuntu-latest` 已预装 Maven，`setup-java` 仅负责 JDK 与依赖缓存；业务仓要求固定 Maven 版本时，提交 Maven Wrapper 并将命令改为 `./mvnw`                                                                                                                                                                                                                  |
| Maven 依赖下载慢                  | `actions/setup-java@v4` 开启 `cache: maven`；企业内网可提交 `settings.xml` 配置镜像源                                                                                                                                                                                                                                                                    |
| 大仓库分析耗时/内存               | SpotBugs `effort=Max` 与全覆盖分析耗时较高，按需调整 `onlyAnalyze`、`maxHeap`（默认 512 MB）或降级 `effort`；耗时超预算的工具应移出 pre-commit                                                                                                                                                                                                           |
| 华为云 IAM 未放行仓库 OIDC 换证   | STS 返回 403 / `STS5.1001`，插件输出 iss/aud/sub 诊断信息并失败                                                                                                                                                                                                                                                                                          |
| 未生成 SARIF 文件                 | 上传步骤失败并提示检查编译与扫描步骤                                                                                                                                                                                                                                                                                                                     |
| OBS 上传失败 / APIG 回调失败      | 沿用指数退避重试 3 次；回调失败仅 WARN，不改变 OBS 上传成功的结果                                                                                                                                                                                                                                                                                        |

### 2.6 验证情况

| 验证项                  | 结果                                                                                                                                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| docs 用户文档           | 已完成：SpotBugs README 新增 2.7 / 3.5 两个 GitHub 章节与 `demos/github/` 两套工作流示例，`full-analysis/README.md` 4.4 补充 SpotBugs 导航（`docs` 仓 `github-static-analysis-spotbugs` 分支） |
| 文档校验                | 链接检查 1109/1109 通过；敏感信息扫描未发现敏感信息                                                                                                                                            |
| GitHub 侧 SpotBugs 链路 | 待验证：本次不创建 demo 仓，demo 仓工作流、OIDC 换证、OBS 上传、回调与前端展示留待转测阶段核对                                                                                                 |
| 配置样例可信度          | 平台写法（workflow 目录、OIDC 权限、插件引用、字段映射）复用 clang-tidy / gosec / ESLint 已验证范式；SpotBugs 自身的编译前置、SARIF 输出与拦截语义基于 spotbugs-maven-plugin 官方配置，未实跑  |

## 3. 类设计

本 US 无后端 / 前端 / 插件代码改动，涉及文件集中在后续 demo 仓与文档仓：

| 模块 / 文件                                | 职责                                                  | 本次变化                                                                                                              |
| ------------------------------------------ | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `.github/workflows/spotbugs-java.yml`      | workflow 全量扫描                                     | 后续新建：checkout → setup-java → 编译 → 扫描 → 上传                                                                  |
| `.github/workflows/spotbugs-precommit.yml` | pre-commit 集成                                       | 后续新建：checkout → setup-python / setup-java → pre-commit-action → upload-sarif-action                              |
| `.pre-commit-config.yaml`                  | `mvn-spotbugs` local hook                             | 后续新建：`entry: mvn compile spotbugs:check -DsarifOutputDirectory=/tmp/pre-commit-reports`、`pass_filenames: false` |
| `pom.xml`                                  | spotbugs-maven-plugin 与 SARIF 输出配置（单一事实源） | 后续新建：版本、filter、effort、SARIF 三件套                                                                          |
| `spotbugs-include.xml`                     | 规则过滤（白名单）                                    | 后续新建：按安全/质量规则范围筛选                                                                                     |
| `upload-sarif-action`（固定 commit SHA）   | SARIF 上传 OBS + APIG 回调                            | 复用，不改                                                                                                            |
| `pre-commit-action`（固定 commit SHA）     | 执行钩子 + 收集 SARIF（不负责上传）                   | 复用，不改                                                                                                            |
| `docs/tools/spotbugs/README.md`            | 用户文档                                              | 新增 2.7 / 3.5 GitHub 章节、FAQ 与平台差异速查                                                                        |
| `docs/tools/spotbugs/demos/github/`        | GitHub workflow 示例                                  | 新增两套 yml                                                                                                          |

## 4. 数据模型设计

**不适用（无新增/变更表结构）**，原因：来源枚举 `GITHUB_ACTION`、`repo_type=github` 与相关存储已由 clang-tidy US 交付，本 US 仅新增 SpotBugs 扫描数据，沿用现有表结构与字段。

补充说明：

- SpotBugs 上报的告警沿用 `issue_id + category` 唯一键，不会与 clang-tidy / gosec / ESLint 存量数据冲突；
- 扫描记录新增取值为 `tool=spotbugs`、`category=business`（workflow）/ `pre-commit-report`（pre-commit）；
- OBS 对象 key 结构不变，仅桶名按平台切换；
- 无存量数据迁移。

## 5. 性能设计

**无新增性能敏感路径**，原因：复用现有 SARIF 上传链路，扫描器性能由 SpotBugs 与 Maven 构建自身决定。

补充说明：

- SpotBugs 分析字节码，耗时由「Maven 编译 + 字节码分析」两部分组成；`effort=Max` 与全量分析耗时较高，大仓库建议按模块拆分或使用 `onlyAnalyze` 限定包范围；
- `actions/setup-java@v4` 开启 `cache: maven` 缓存 `~/.m2/repository`，减少重复下载；
- GitHub 工作流提供 `concurrency`，同分支仅保留最新一次扫描；
- pre-commit 场景沿用 10 分钟时限，超预算的仓库应仅保留 workflow 全量扫描；
- OIDC/STS 每次运行只换证一次，SDK 内部缓存并做并发去重；OBS 上传与回调内置指数退避重试，不额外增加平台请求。

## 6. API接口设计

**不适用（无新增/变更对外 HTTP 接口）**，原因：结果回传复用现有回调接口，前端复用现有查询接口。

| 项       | 说明                                                                  |
| -------- | --------------------------------------------------------------------- |
| 回调接口 | `POST /action-api/codescan/v1/result/receive`，沿用现有入参与签名方式 |
| 认证     | OIDC 临时凭证 + V11-HMAC-SHA256 签名                                  |
| 前端接口 | 无契约变化；来源筛选项沿用 `GITHUB_ACTION` 枚举值                     |
| 错误码   | 沿用现有回调错误码；OIDC 换证失败按插件失败处理                       |

## 7. 安全设计

1. **鉴权**：GitHub 链路使用 OIDC 临时凭证，不在仓库或 Secrets 中保存长期 AK/SK；`upload-sarif-action` 通过 `id-token: write` 申请 ID Token 并换取 STS 临时凭证；
2. **信任边界**：华为云 IAM `GitHubActions` 提供商信任策略通过 `iss` / `aud` / `sub` 限定到目标组织、仓库与分支。`sub` 对 `push` 事件形如 `repo:<org>/<repo>:ref:refs/heads/<branch>`（可限定分支），对 `pull_request` 事件形如 `repo:<org>/<repo>:pull_request`（不含分支）——信任策略仅放行 `push` 形 `sub`、拒绝 `pull_request` 形 `sub`，任何 PR（含同仓与 fork）均无法完成换证；如确需 PR 触发上报，先经 GitHub Environment 保护与审批再单独放行；
3. **最小权限**：工作流仅声明 `contents: read` + `id-token: write`；OIDC 委托仅授予 OBS 上传与 APIG 回调所需权限。`GITHUB_TOKEN` 只读权限不构成本链路的安全边界，平台间隔离以第 2 条的 `sub` 约束与 OBS 桶隔离为准；
4. **敏感信息**：示例代码与配置不包含真实凭证、内网地址或可利用漏洞代码；SpotBugs 的 `findsecbugs-plugin` 可检测业务代码中的硬编码凭证，文档示例仅使用占位形式；
5. **硬编码**：插件版本（spotbugs-maven-plugin 4.9.8.3、spotbugs 4.10.2、findsecbugs-plugin 1.14.0）在 pom properties 中集中声明；OBS 桶名、OIDC 提供商等由插件按平台自动选择，不在工作流中硬编码密钥；
6. **审计日志**：上传插件输出平台来源标记、OIDC 提供商、OBS 桶名与回调结果，便于从 Actions 日志追溯；外部可控字段（仓库名、分支名等）写入日志前做净化，不上送凭证；扫描结果按 `source=GITHUB_ACTION` 入库，来源可追溯；
7. **OBS 对象访问控制与公共读残留风险**：SARIF 对象 key 由仓库/分支/commit 等公开可推导信息拼装，且内容含补齐的源码片段；公共读策略下禁用公共列举只能降低批量枚举风险，无法阻止已知 key 的定向匿名下载，仍存在跨租户源码泄露面。缓解措施：优先将桶收敛为私有读并由后端使用服务端凭证读取（`openlibing-codecheck` 已支持 `downloadToTempFile` 的 AK/SK 读取）；过渡期可在 key 中加入不可预测随机段、按对象设置 ACL 与留存期，上线前由安全与运维共同确认桶策略；
8. **供应链引用固定**：消费方工作流引用 `upload-sarif-action` / `pre-commit-action` 及第三方 actions 时必须固定到完整 commit SHA（或不可移动 tag），禁止跟踪可变 `main` 或 `@v4` 等 major 标签，避免上游被劫持后借已授权的 `id-token: write` 换取 STS 凭证；`id-token: write` 仅授予执行上传换证的 job，不扩散到其他 job。
