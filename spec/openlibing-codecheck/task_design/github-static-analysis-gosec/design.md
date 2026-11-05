# 静态代码分析 GitHub 接入方案与文档 · gosec — 设计文档

## 1. 方案设计

### 1.1 需求背景与目标态

openLiBing 的代码检查链路当前主要面向 GitCode Actions：各静态分析工具产出 SARIF，经 `upload-sarif-action` 上传 OBS 并回调 openLiBing，最终在「开发管理 - 代码检查」页面展示。

「静态代码分析 GitHub 接入」FE 已由 clang-tidy 完成首个落地，并沉淀了可复用的 GitHub 接入范式：平台来源枚举（`GITHUB_ACTION`）、前端平台筛选与来源标签、`upload-sarif-action` / `pre-commit-action` 双插件的平台识别与 OIDC 免密换证改造均已交付。本 US 将该范式复制到 Go 语言工具 **gosec**，验证「替换扫描器 + SARIF 转换器 + 规则文件」即可接入新工具的可行性。

**目标态**：

1. 在 GitHub 平台 `openlibing-test` 组织下准备可运行的 gosec 流水线，覆盖 workflow 全量扫描与 pre-commit 集成两种入口；
2. 扫描结果能够生成合法 SARIF（gosec 原生 `-fmt sarif` 直出），上传 OBS 并回调 openLiBing；
3. 「代码检查」页面筛选 GitHub 平台后能看到问题列表与详情（前端零改动，复用 clang-tidy 已交付能力）；
4. 同步更新 GitCode `docs` 仓的 gosec 用户文档（GitHub 差异速查表 + `demos/github` 两套示例）；
5. 本设计文档归档到 `openlibing-docs` 仓。

前端原型复用「静态代码分析 GitHub 接入」FE 已归档的 prototype.html（平台筛选、GitHub Action 来源标签），本 US 无前端改动、不单独出原型。

### 1.2 总体方案

沿用**单份代码、运行时识别平台**的方案，不为 GitHub 维护独立分支：

- 业务配置（`gosec.json` 规则、扫描命令、pre-commit 钩子）在 GitCode 与 GitHub 完全复用，差异集中在 workflow 写法与插件引用；
- 两个 action 按 `GITHUB_ACTIONS` 识别运行平台，只读取对应平台的上下文变量（clang-tidy US 已交付，本 US 直接复用）；
- GitHub 侧使用 `GitHubActions` OIDC 身份提供商免密换证，OBS 桶按平台隔离；
- 产品侧零改动：来源枚举与前端标签沿用 clang-tidy 已上线能力；
- 文档在 GitCode `docs` 仓的 full-analysis 方案内扩展（gosec README 增加平台差异速查表，demos 按平台拆分目录），不新增与 `full-analysis` 并列的目录。

### 1.3 关键选型与理由

| 决策点         | 选择                                                | 理由                                                                                       |
| -------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 认证方式       | OIDC 免密换证（`GitHubActions` 身份提供商）         | 复用 clang-tidy 已打通的链路，不落任何长期 AK/SK                                            |
| OBS 桶         | GitHub 使用 `openlibing-github-action`              | 与 GitCode 桶隔离，便于权限与成本归集（复用既有桶，无新增）                                 |
| SARIF 转换     | gosec 原生 `-fmt sarif` 直出                        | **零转换器、零预置二进制**，较 clang-tidy 需随仓预置 `clang-tidy-sarif` 显著简化供应链       |
| 编译数据库     | 不需要                                              | gosec 直接解析 Go 源码（依赖 `go.mod` 定位模块），无需 `compile_commands.json`，扫描分钟级   |
| 入口形态       | pre-commit 集成 + workflow 全量扫描并存             | 分别覆盖提交前拦截与全量归档场景，共用同一份 `gosec.json` 规则                              |
| 产品侧改动范围 | 无                                                  | 来源枚举与前端标签已由 clang-tidy US 交付，本 US 仅验证复用                                 |

### 1.4 涉及文件与跨仓影响

| 仓库 / 模块          | 涉及内容                                                                       |
| -------------------- | ------------------------------------------------------------------------------ |
| `gosec-full-scan-demo` | `.github/workflows/` 两套 GitHub 工作流、`gosec.json`、`.pre-commit-config.yaml` |
| `openlibing-docs`    | 本设计文档归档                                                                 |
| `docs`               | gosec README 增加 GitCode / GitHub 差异速查表，demos 拆分 `gitcode/` 与 `github/` 目录 |

`upload-sarif-action`、`pre-commit-action`、`openlibing-codecheck` 后端、`openlibing-web` 前端均无改动（复用 clang-tidy US 已交付成果）。

## 2. 实现逻辑设计

### 2.1 主流程

场景二（workflow 全量扫描）：

```text
GitHub 代码仓触发 workflow（手动 / push / PR / 定时）
  → checkout → setup-go（go-version 按 go.mod 调整）
  → go install gosec@v2.22.4 并扫描（同一步执行，PATH 修改不跨 step 继承）
  → gosec -no-fail -conf gosec.json -fmt sarif -out reports/gosec.sarif ./...
  → upload-sarif-action：路径归一化 + 代码片段补齐
  → OIDC 申请 ID Token → 华为云 STS 换取临时凭证
  → 上传 OBS（openlibing-github-action）
  → APIG 回调 openLiBing
  → 解析入库 → 代码检查页面筛选 GitHub 查看结果
```

场景一（pre-commit 集成）：

```text
GitHub 代码仓触发 workflow
  → checkout → setup-python / setup-go
  → go install gosec 到 .github/bin/（hook entry 固定路径）
  → pre-commit-action 读取 .pre-commit-config.yaml 执行 gosec 钩子
  → 钩子 -fmt sarif -out /tmp/pre-commit-reports/gosec.sarif
  → pre-commit-action 收集 SARIF → upload-sarif-action 上传 OBS + 回调 openLiBing
```

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
4. 上传对象保持现有公共读策略，对象 key 结构不变；
5. 上传与回调沿用指数退避重试（默认 3 次）；回调失败仅告警，以 OBS 上传成功为准。

### 2.4 前端展示逻辑

**无前端改动**。列表页 GitHub 平台筛选、数据来源 `GitHub Action` 标签、详情页两处来源标签均已由 clang-tidy US 交付上线，本 US 的 gosec 数据按 `source=GITHUB_ACTION` 上报后自动进入既有展示链路。

### 2.5 边界与异常处理

| 场景                                 | 处理                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------ |
| gosec 钩子按文件列表扫描             | pre-commit 钩子必须 `pass_filenames: false` 并传 `./...`（gosec 以包/模块为单位分析）；否则 SARIF 可能 results 为空但上传成功，openLiBing 无告警 |
| vendor / 生成代码                    | 扫描命令 `-exclude-dir=vendor -exclude-generated`，`gosec.json` 的 `exclude-rules` 按路径排除 |
| GitHub PR 事件                       | 场景二使用 `pull_request`（GitHub 默认只读 token，无 fork 篡改风险；GitCode 侧用 `pull_request_target` 的差异已在用户文档速查表标注） |
| gosec 安装与扫描拆分到不同 step      | `go install` 的 PATH 修改无法跨 step 继承，安装与扫描放同一步            |
| pre-commit 产物路径                  | gosec 输出路径固定，upload 直接引用 `/tmp/pre-commit-reports/gosec.sarif`，不依赖 `sarif-files` output（可能为空） |
| 华为云 IAM 未放行仓库 OIDC 换证      | STS 返回 403 / `STS5.1001`，插件输出 iss/aud/sub 诊断信息并失败          |
| 未生成 SARIF 文件                    | 上传步骤失败并提示检查扫描步骤                                           |
| OBS 上传失败 / APIG 回调失败         | 沿用指数退避重试 3 次；回调失败仅 WARN，不改变 OBS 上传成功的结果        |
| Go 模块拉取超时                      | GitCode 执行机需配置 `GOPROXY` 国内代理；GitHub `ubuntu-latest` 一般直连默认代理即可 |

### 2.6 验证情况

| 验证项                 | 结果                                                                       |
| ---------------------- | -------------------------------------------------------------------------- |
| docs 用户文档          | gosec README 已含 GitCode / GitHub 差异速查表与实操清单，`demos/github/` 两套工作流示例已提交（`docs` 仓 `github-static-analysis-gosec` 分支） |
| GitHub 侧 gosec 流水线 | 待验证：demo 仓工作流推送、两条工作流运行、OIDC 换证、OBS 上传、回调与前端展示全链路核对 |

## 3. 类设计

本 US 无后端 / 前端代码改动，涉及文件集中在 demo 仓与文档仓：

| 模块 / 文件                                   | 职责                              | 本次变化                                             |
| --------------------------------------------- | --------------------------------- | ---------------------------------------------------- |
| `.github/workflows/gosec-scan.yml`            | workflow 全量扫描                 | 新增：checkout → setup-go → 安装并扫描 → 上传       |
| `.github/workflows/gosec-precommit.yml`       | pre-commit 集成                   | 新增：checkout → setup-python/go → 装到 `.github/bin` → 双插件两步 |
| `.pre-commit-config.yaml`                     | gosec local hook                  | 新增：`entry: .github/bin/gosec`、`pass_filenames: false` |
| `gosec.json`                                  | 规则单一事实源                    | 新增：两场景共享，含 G101 熵值、G301/G302/G306/G307 权限位等 |
| `upload-sarif-action`（`source-platform-detection` 分支） | SARIF 上传 OBS + APIG 回调 | 复用，不改                                           |
| `pre-commit-action`（`main` 分支）            | 执行钩子并收集 SARIF              | 复用，不改                                           |

## 4. 数据模型设计

**不适用（无新增/变更表结构）**，原因：来源枚举 `GITHUB_ACTION` 与相关存储已由 clang-tidy US 交付，本 US 仅新增 gosec 扫描数据，沿用现有表结构与字段。

补充说明：

- gosec 上报的告警沿用 `issue_id + category` 唯一键，不会与 clang-tidy 存量数据冲突；
- OBS 对象 key 结构不变，仅桶名按平台切换；
- 无存量数据迁移。

## 5. 性能设计

**无新增性能敏感路径**，原因：复用现有 SARIF 上传链路，扫描器为工具自身能力。

补充说明：

- gosec 直接解析 Go 源码、无需编译数据库，全量扫描为分钟级（优于需要 `compile_commands.json` 的 C/C++ 工具链小时级）；
- `setup-go` 开启 `cache: true` 缓存 Go 模块；
- GitHub 工作流提供 `concurrency`，同分支仅保留最新一次扫描；
- pre-commit 场景沿用 10 分钟时限，超预算的工具应移出 pre-commit。

## 6. API接口设计

**不适用（无新增/变更对外 HTTP 接口）**，原因：结果回传复用现有回调接口，前端复用现有查询接口。

| 项       | 说明                                                                  |
| -------- | --------------------------------------------------------------------- |
| 回调接口 | `POST /action-api/codescan/v1/result/receive`，沿用现有入参与签名方式 |
| 认证     | OIDC 临时凭证 + V11-HMAC-SHA256 签名                                  |
| 前端接口 | 无契约变化；来源筛选项沿用 `GITHUB_ACTION` 枚举值                     |
| 错误码   | 沿用现有回调错误码；OIDC 换证失败按插件失败处理                       |

## 7. 安全设计

1. **免密优先**：GitHub 链路使用 OIDC 临时凭证，不在仓库或 Secrets 中保存长期 AK/SK；
2. **信任边界**：华为云 IAM `GitHubActions` 提供商信任策略通过 `iss` / `aud` / `sub` 限定到目标组织、仓库与分支（复用 clang-tidy US 已配置的信任策略）；
3. **最小权限**：工作流仅声明 `contents: read` + `id-token: write`；OIDC 委托仅授予 OBS 上传与 APIG 回调所需权限；
4. **对象存储隔离**：GitHub 与 GitCode 使用不同 OBS 桶，避免跨平台对象混用；
5. **供应链简化**：gosec 原生 `-fmt sarif` 直出，无需预置第三方转换二进制（较 clang-tidy 少一个二进制供应链风险面）；`go install` 固定版本 `v2.22.4`；
6. **规则自检**：`gosec.json` 的 G101 规则（关键词 + 熵值）用于检测业务仓自身硬编码凭证；
7. **输入与日志**：外部可控字段（仓库名、分支名等）写入日志前做净化，不上送凭证。
