# 静态代码分析 GitHub 接入方案与文档 · clippy — 设计文档

## 1. 方案设计

### 1.1 需求背景与目标态

「静态代码分析 GitHub 接入」FE 已由 clang-tidy 完成首个落地并沉淀可复用范式（平台来源枚举 `GITHUB_ACTION`、前端平台筛选与来源标签、`upload-sarif-action` / `pre-commit-action` 双插件平台改造）；gosec US 验证了「替换扫描器 + SARIF 转换器 + 规则文件」的新工具接入模式。本 US 将该范式复制到 Rust 语言工具 **clippy**，验证编译型语言（无文件级增量、依赖构建工具链）场景下的接入形态。

GitCode 侧 `openlibing-test/rust-clippy-full-scan-demo` 已完成落地（`.gitcode/workflows/`：cargo-clippy 全量扫描与 pre-commit 集成，工具链 1.98.1、clippy-sarif 0.8.0）。本 US 将同一套扫描配置移植到 GitHub Actions。

**目标态**：

1. GitHub `openlibing-test` 组织下 demo 仓 `rust-clippy-full-scan-demo` 可运行，覆盖 workflow 全量扫描与 pre-commit 集成两种入口，并补充 **PR 门禁触发**场景；
2. `cargo clippy --message-format=json | clippy-sarif` 产出合法 SARIF，上传 OBS（`openlibing-github-action`）并回调 openLiBing；
3. 「代码检查」页面筛选 GitHub 平台可见 clippy 告警列表与详情（前端零改动）；
4. 本设计文档归档到 `openlibing-docs` 仓。

原型复用 FE 已归档的 prototype.html，本 US 无前端改动、不单独出原型。

### 1.2 总体方案

沿用「单份代码、运行时识别平台」方案，不为 GitHub 维护独立分支：

- 业务配置（`.pre-commit-config.yaml` clippy 钩子、Cargo 工程）在 GitCode 与 GitHub 完全复用，差异集中在 workflow 写法（`.github/workflows/`、官方 `actions/checkout@v4`、cron 5 位 POSIX、直连官方 rustup/crates.io 无需国内镜像）；
- 双插件按 `GITHUB_ACTIONS` 识别平台、OIDC 免密换证、OBS 桶按平台隔离（clang-tidy US 已交付，本 US 直接复用，插件零改动）；
- 产品侧零改动：来源枚举与前端标签复用既有能力。

### 1.3 关键选型与理由

| 决策点         | 选择                                                                             | 理由                                                                                                                                            |
| -------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 认证方式       | OIDC 免密换证（`GitHubActions` 身份提供商）                                      | 复用既有链路，不落任何长期 AK/SK                                                                                                                |
| OBS 桶         | GitHub 使用 `openlibing-github-action`                                           | 与 GitCode 桶隔离（复用既有桶，无新增）                                                                                                         |
| SARIF 转换     | `clippy-sarif`（cargo install 固定版本 `0.8.0 --locked`）                        | clippy 无原生 SARIF 输出；clippy-sarif 为 cargo 生态标准转换器，源码编译安装、无需随仓预置二进制                                                |
| 编译数据库     | 不需要                                                                           | cargo 自带构建编排，clippy 沿编译管线工作；但依赖 Rust 工具链（与 clang-tidy 需 `compile_commands.json` 的形态不同，与 gosec 直连源码也不同）   |
| 工具链固定     | `rustup toolchain install 1.98.1 --component clippy`                             | 与 GitCode 侧版本对齐，保证 CI 可复现                                                                                                           |
| PR 触发语义    | pre-commit 工作流开放 `pull_request`（纯门禁、跳过上传）；全量扫描不开放 PR 触发 | 华为云 IAM `GitHubActions` 信任策略仅放行 push 形 `sub`，`pull_request` 形 `sub` 换证必失败；「提交前拦截」与「结果归档」由不同触发事件分别承载 |
| 产品侧改动范围 | 无                                                                               | 复用 clang-tidy US 已交付能力                                                                                                                   |

### 1.4 涉及文件与跨仓影响

| 仓库 / 模块                            | 涉及内容                                                                                                                               |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `rust-clippy-full-scan-demo`（GitHub） | `.github/workflows/clippy-scan.yml`、`.github/workflows/clippy-precommit.yml`、README；删除 GitCode 侧 `.gitcode/workflows` 与测试残留 |
| `openlibing-docs`                      | 本设计文档归档                                                                                                                         |

`upload-sarif-action`、`pre-commit-action`、`openlibing-codecheck` 后端、`openlibing-web` 前端均无改动（复用 clang-tidy US 已交付成果）。

## 2. 实现逻辑设计

### 2.1 主流程

场景二（workflow 全量扫描，`clippy-scan.yml`）：

```text
GitHub workflow 触发（手动 / push / 定时 02:00 UTC）
  → actions/checkout@v4
  → rustup toolchain install 1.98.1 --component clippy（GitHub runner 自带 rustup，直连官方源）
  → cargo install clippy-sarif --version 0.8.0 --locked（源码编译安装，直连 crates.io）
  → cargo clippy --message-format=json | clippy-sarif > /tmp/clippy-result/clippy-results.sarif
  → upload-sarif-action@source-platform-detection：路径归一化 + 代码片段补齐
  → OIDC ID Token → 华为云 STS 换临时凭证 → 上传 OBS（openlibing-github-action）→ APIG 回调
  → 解析入库 → 代码检查页面筛选 GitHub 查看结果
```

场景一（pre-commit 集成，`clippy-precommit.yml`）：

```text
GitHub workflow 触发（手动 / push / PR）
  → actions/checkout@v4 → actions/setup-python@v5 → rust 工具链 + clippy-sarif
  → pre-commit-action@main 读取 .pre-commit-config.yaml 执行 cargo-clippy local hook
    （pass_filenames: false，钩子内 cargo clippy | clippy-sarif 输出到 report-dir）
  → push / 手动：upload-sarif-action 收集 sarif-files 输出，上传 OBS + 回调（归档语义）
  → PR：跳过上传步骤（门禁语义，见 2.4）
```

### 2.2 平台识别与上下文映射

复用 clang-tidy US 已交付的插件能力，本 US 无代码改动。平台判定 `GITHUB_ACTIONS=true`；回调字段映射（`repoUrl`/`pipelineId=GITHUB_JOB`/`pipelineName=GITHUB_WORKFLOW`/`pipelineRunId=GITHUB_RUN_ID`/`commitId=GITHUB_SHA` 等）与 gosec US 一致，不再赘述。

### 2.4 触发事件与门禁/归档语义

| 触发                         | pre-commit 工作流                                                                                                                                                                                                                                          | 全量扫描工作流                    |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| `workflow_dispatch` / `push` | 钩子检查 + SARIF 上传回调（归档）                                                                                                                                                                                                                          | 全量扫描 + 上传回调               |
| `pull_request`               | **纯门禁**：钩子命中告警 → exit 1 拦截合并；上传步骤以 `if: always() && github.event_name != 'pull_request'` 跳过（信任策略不放行 PR 形 `sub`，且 PR 场景无归档语义）。门禁运行环境必须为 GitHub 托管一次性 runner（任意代码执行隔离约束见第 7 章第 3 条） | 不开放 PR 触发                    |
| `schedule`                   | 不配置                                                                                                                                                                                                                                                     | 每日 02:00 UTC（cron 5 位 POSIX） |

### 2.5 clippy 工具特性与影响

| 特性                   | 影响                                                                                                                                                                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 无文件级增量扫描       | clippy 是编译器 lint pass，必须对完整 crate 语义分析，`pass_filenames: false` 为唯一可行形态；「增量」仅来自 cargo 编译缓存（crate 粒度）                                                                                           |
| 告警严重级别语义       | 默认 warning 级只报告不失败（clippy 退出码 0）；仅 `deny` 级（如 `#[deny(clippy::needless_return)]`）使退出码非 0，经钩子 `set -o pipefail` 传递实现门禁拦截。SARIF 包含全部 warning 级告警用于归档展示，门禁拦截与否只取决于退出码 |
| `--all-targets`        | bin 与 test 两个 target 各编译一次同一 crate，诊断重复上报（SARIF 中同一告警出现两条、日志 warning 计数翻倍），已知行为                                                                                                             |
| SARIF 转换             | clippy-sarif 将全部 JSON diagnostic（含 warning）转为 SARIF results；路径相对化由 upload-sarif-action 处理                                                                                                                          |
| 新增告警过滤（演进项） | 全量扫描天然包含历史告警；「仅归档新增告警」可在上传前按 PR 变更文件过滤（无状态）或由平台侧按上一次 run 对比标记新增/存量（正解，涉及后端迭代），本 US 未实现，记录为演进项                                                        |

### 2.6 验证情况

| 验证项               | 结果                                                                                                                            |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| main 全量扫描        | `cargo-upload-sarif` run=3 success（OIDC 换证 → OBS `openlibing-github-action` → APIG 回调）                                    |
| main pre-commit 归档 | `pre-commit_gate` run=4 success（含 `upload sarif reports` 步骤）                                                               |
| PR 门禁放行          | PR #1（78db7fb，无 deny 违例）`pre-commit_gate` success，上传步骤 skipped                                                       |
| PR 门禁拦截          | PR #1（8f023a7，`#[deny(clippy::needless_return)]` 违例）`pre-commit_gate` failure，clippy 退出码 101 经 pipefail 传递，PR 变红 |
| 本地预验证           | 本地 cargo clippy 对 deny 违例报 error 并退出 101，与 CI 行为一致                                                               |

## 3. 类设计

本 US 无后端 / 前端代码改动，涉及文件集中在 demo 仓：

| 模块 / 文件                                               | 职责                                      | 本次变化                                                                                              |
| --------------------------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `.github/workflows/clippy-scan.yml`                       | workflow 全量扫描                         | 新增：checkout → rust 工具链 → clippy-sarif → 扫描 → 上传                                             |
| `.github/workflows/clippy-precommit.yml`                  | pre-commit 集成（含 PR 门禁）             | 新增：checkout → python/rust → pre-commit-action（收集 SARIF）→ 非 PR 事件串 upload-sarif-action 上传 |
| `.pre-commit-config.yaml`                                 | clippy local hook（规则单一事实源）       | 复用 GitCode 侧，不改                                                                                 |
| `README.md`                                               | GitHub 侧使用说明                         | 重写：工作流矩阵、触发方式、平台差异、结果查看                                                        |
| `upload-sarif-action`（`source-platform-detection` 分支） | SARIF 上传 OBS + APIG 回调                | 复用，不改                                                                                            |
| `pre-commit-action`（`main` 分支）                        | 执行钩子 + 生成/收集 SARIF（report-only） | 复用，不改                                                                                            |

## 4. 数据模型设计

**不适用（无新增/变更表结构）**：来源枚举 `GITHUB_ACTION` 与相关存储已由 clang-tidy US 交付。clippy 告警沿用 `issue_id + category` 唯一键，与既有数据不冲突；OBS 对象 key 结构不变，仅桶名按平台切换；无存量数据迁移。

## 5. 性能设计

**无新增性能敏感路径**。补充说明：

- clippy 全量扫描为 crate 级编译检查，demo 仓分钟级；耗时大头为 `cargo install clippy-sarif` 源码编译（每次运行重复，约 1~2 分钟）——可用 `Swatinem/rust-cache` 缓存 `target/` 与 `~/.cargo` 优化，本 US 未引入，记录为演进项；
- 无编译数据库生成步骤（优于 C/C++ 工具链）；全量工作流提供 `workflow_dispatch` + `schedule`，同分支 push 触发自然去重；
- pre-commit 场景沿用插件 10 分钟时限约束，超预算工具应移出 pre-commit。

## 6. API接口设计

**不适用（无新增/变更对外 HTTP 接口）**。结果回传复用 `POST /action-api/codescan/v1/result/receive`（OIDC 临时凭证 + V11-HMAC-SHA256 签名），前端复用既有查询接口，来源筛选项沿用 `GITHUB_ACTION` 枚举值。

## 7. 安全设计

1. **免密优先**：GitHub 链路使用 OIDC 临时凭证，仓库与 Secrets 不保存长期 AK/SK（GitCode 侧残留的 `OBS_AK`/`OBS_SK` 输入不带入 GitHub 侧工作流）；
2. **信任边界**：华为云 IAM `GitHubActions` 信任策略通过 `iss`/`aud`/`sub` 限定目标组织、仓库与分支，仅放行 push 形 `sub`（`repo:<org>/<repo>:ref:refs/heads/<branch>`）、拒绝 `pull_request` 形 `sub`（`repo:<org>/<repo>:pull_request`，不含分支）——fork PR 换证直接失败；pre-commit 工作流的 PR 触发为纯门禁，不依赖 OIDC 换证，上传步骤显式跳过以避免误导性失败；如需 PR 触发归档，须先经 GitHub Environment 保护与审批后单独放行；
3. **最小权限**：两条工作流仅声明 `contents: read` + `id-token: write`；`pull_request` 事件下 `GITHUB_TOKEN` 只读，不构成本链路安全边界（第 2 条 `sub` 约束兜底）。注意 PR 门禁场景下 `cargo clippy` 会对完整 crate 编译，必然执行 PR head 中的 `build.rs` 与过程宏（runner 上任意代码执行，且 `sub` 约束与 token 只读均不能消除该面）；其风险可控的前提是运行环境为 GitHub 托管的一次性 runner（`ubuntu-latest`，任务结束即销毁）。接入内网/自托管等常驻 runner 时，不得开放 `pull_request` 触发，或必须先经 Environment 保护、审批与网络隔离加固后再单独评估放行；
4. **供应链**：`clippy-sarif 0.8.0 --locked` 固定版本安装，工具链固定 `1.98.1`，与 GitCode 侧版本对齐；不随仓预置二进制（较 clang-tidy 少一个二进制供应链面）；测试验证用的 PAT 仅会话内使用，未落盘仓库、Secrets 或文档。已知缺口：workflow 中 action 引用为验证期分支（`upload-sarif-action@source-platform-detection`、`pre-commit-action@main`），属可变引用且相关步骤持有 `id-token: write`，分支被重推即等于执行新代码；约束为**验证期允许分支引用联调，接入范式定稿/复制到其他仓前必须固定为 tag 或 commit SHA**，本 US 记录为演进项；
5. **规则来源**：clippy lint 级别由源码属性（`#[deny(...)]`）与工具链默认集定义，`.pre-commit-config.yaml` 为扫描命令单一事实源，pre-commit 与全量扫描不重复定义规则；
6. **输入与日志**：外部可控字段（仓库名、分支名等）写入日志前由插件净化，不上送凭证。
