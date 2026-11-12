# 静态代码分析 GitHub 接入方案与文档 · clang-tidy — 设计文档

## 1. 方案设计

### 1.1 需求背景与目标态

openLiBing 的代码检查链路当前主要面向 GitCode Actions：各静态分析工具产出 SARIF，经 `upload-sarif-action` 上传 OBS 并回调 openLiBing，最终在「开发管理 - 代码检查」页面展示。

本 US 面向 C/C++ 仓库，是「静态代码分析 GitHub 接入」FE 的首个落地工具，目标是在 GitHub Actions 上打通 clang-tidy 全量检查，并沉淀可复用的 GitHub 接入范式。

**目标态**：

1. 在 GitHub 平台 `openlibing-test` 组织下准备可运行的 clang-tidy 流水线，覆盖 workflow 全量扫描与 pre-commit 集成两种入口；
2. 扫描结果能够生成合法 SARIF，上传 OBS 并回调 openLiBing beta 环境；
3. 「代码检查」页面筛选 GitHub 平台后能看到问题列表与详情；列表页支持 GitHub 平台与 GitHub Action 来源展示，详情页仅需适配两处 GitHub Action 标签（右侧「数据来源」、扫描记录来源），其余字段与交互沿用现有页面；
4. 满足以上条件即可转入测试流程；转测前，需求设计与原型等文档改动需合入 `openlibing-docs` 仓的 `github-static-analysis` 分支；
5. 同步更新 GitCode `docs` 仓的用户文档（在 full-analysis 方案内补充 GitHub 接入章节）。

前端目标态原型见 [prototype.html](./prototype.html)。

### 1.2 总体方案

采用**单份代码、运行时识别平台**的方案，不为 GitHub 维护独立分支：

- 业务脚本（`.clang-tidy`、`scripts/run-clang-tidy.py`、SARIF 转换）在 GitCode 与 GitHub 完全复用；
- 两个 action 按 `GITHUB_ACTIONS` 识别运行平台，只读取对应平台的上下文变量；
- GitHub 侧使用 `GitHubActions` OIDC 身份提供商免密换证，OBS 桶按平台隔离；
- 产品侧仅做最小适配：来源枚举新增 `GITHUB_ACTION`，前端列表页展示 GitHub 平台/来源，详情页展示两处 GitHub Action 标签；
- 文档在 GitCode `docs` 仓的 full-analysis 方案内扩展，不新增与 `full-analysis` 并列的目录。

### 1.3 关键选型与理由

| 决策点         | 选择                                         | 理由                                                               |
| -------------- | -------------------------------------------- | ------------------------------------------------------------------ |
| 认证方式       | OIDC 免密换证（`GitHubActions` 身份提供商）  | 不落任何长期 AK/SK，与 GitCode 链路一致；需华为云 IAM 信任策略配合 |
| OBS 桶         | GitHub 使用 `openlibing-github-action`       | 与 GitCode 桶隔离，便于权限与成本归集                              |
| SARIF 转换     | 继续使用 `clang-tidy-sarif` v0.8.0，随仓预置 | 执行机不依赖外网，产物与 GitCode 一致                              |
| 入口形态       | pre-commit 集成 + workflow 全量扫描并存      | 分别覆盖提交前拦截与全量归档场景，共用同一份规则                   |
| 产品侧改动范围 | 仅来源枚举 + 两处详情标签                    | 详情页现有结构已能承载 GitHub 数据，避免不必要的 UI 改造           |

### 1.4 涉及文件与跨仓影响

| 仓库 / 模块                 | 涉及内容                                                             |
| --------------------------- | -------------------------------------------------------------------- |
| `upload-sarif-action`       | 平台识别、OIDC 提供商切换、OBS 桶选择、移除 AK/SK 输入               |
| `pre-commit-action`         | GitHub 上下文适配、README 接入说明                                   |
| `clang-tidy-full-scan-demo` | `.github/workflows/` 两套 GitHub 工作流、预置二进制与示例代码        |
| `openlibing-codecheck`      | `StaticAlarmSourceEnum` 新增 `GITHUB_ACTION`                         |
| `openlibing-web`            | 来源选项/标签、列表页 GitHub 平台展示、详情页两处 GitHub Action 标签 |
| `openlibing-docs`           | 本设计文档与原型归档，合入 `github-static-analysis` 分支             |
| `docs`                      | full-analysis 方案内补充 GitHub 接入用户文档                         |

## 2. 实现逻辑设计

### 2.1 主流程

```text
GitHub 代码仓触发 workflow / 本地 pre-commit
  → checkout / 安装 clang-tidy + cmake
  → 生成 compile_commands.json
  → scripts/run-clang-tidy.py 全量扫描（编译数据库去重 + 实时 tee）
  → clang-tidy-sarif 转换为 SARIF v2.1.0
  → upload-sarif-action：路径归一化 + 代码片段补齐
  → OIDC 申请 ID Token → 华为云 STS 换取临时凭证
  → 上传 OBS（openlibing-github-action）
  → APIG 回调 openLiBing beta
  → 解析入库 → 代码检查页面筛选 GitHub 查看结果
```

### 2.2 平台识别与上下文映射

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

1. 平台为 GitHub 时，在调用 `getCredentials()` 之前执行 `configure({ oidcProviderName: 'GitHubActions' })`；
2. 通过 `ACTIONS_ID_TOKEN_REQUEST_URL/TOKEN` 申请 OIDC ID Token，调用华为云 STS `AssumeAgencyWithOIDC` 换取临时 AK/SK/SecurityToken；
3. OBS 桶按平台选择：GitHub 为 `openlibing-github-action`，GitCode 为 `openlibing-gitcode-action`；
4. 上传对象保持现有公共读策略，对象 key 结构不变；
5. 上传与回调沿用指数退避重试（默认 3 次）；回调失败仅告警，以 OBS 上传成功为准。

### 2.4 前端展示逻辑

- **列表页**：平台筛选支持 GitHub；数据来源展示为 `GitHub Action`。
- **详情页右侧「数据来源」**：沿用 `formatStaticAlarmSource(source)` 渲染 pill，新增 `GITHUB_ACTION → GitHub Action` 映射。
- **详情页「扫描记录」**：时间线内 `sourceLabel` 标签同样由该映射生成，展示 `GitHub Action`。
- 详情页其余结构、字段和交互不变。
- 发布顺序：先上线后端 `GITHUB_ACTION` 枚举与前端映射，再让上传插件上报 `GITHUB_ACTION`，避免非法来源被拒绝。

### 2.5 边界与异常处理

| 场景                            | 处理                                                            |
| ------------------------------- | --------------------------------------------------------------- |
| 华为云 IAM 未放行仓库 OIDC 换证 | STS 返回 403 / `STS5.1001`，插件输出 iss/aud/sub 诊断信息并失败 |
| 未生成 SARIF 文件               | 上传步骤失败并提示检查扫描步骤                                  |
| OBS 上传失败                    | 指数退避重试 3 次，仍失败则 job 失败                            |
| APIG 回调失败                   | 仅输出 WARN，不改变 OBS 上传成功的结果                          |
| PR 事件执行 pre-commit          | 只做门禁检查，不生成/上传报告                                   |
| 执行机无法访问外网              | `clang-tidy-sarif` 随仓预置，禁止运行时下载                     |

### 2.6 验证情况

| 验证项                   | 结果                                                                |
| ------------------------ | ------------------------------------------------------------------- |
| GitHub workflow（AK/SK） | 历史验证运行成功，扫描 → SARIF → OBS → beta 回调全链路通过          |
| GitHub workflow（OIDC）  | `openlibing-test` 仓库已发起运行，换证被 IAM 拒绝（STS5.1001）      |
| 前端列表/详情原型        | 平台筛选、来源展示、详情两处 GitHub Action 标签均已验证             |
| 待完成项                 | 华为云 IAM 为 `gitcode-actions` 委托补充 GitHub OIDC 信任策略后复跑 |

## 3. 类设计

| 模块 / 类                        | 职责                              | 本次变化                                                                  |
| -------------------------------- | --------------------------------- | ------------------------------------------------------------------------- |
| `upload-sarif-action/index.js`   | SARIF 收集、OBS 上传、APIG 回调   | 新增 `IS_GITHUB` 平台判定、`GitHubActions` OIDC 提供商、按平台选择 OBS 桶 |
| `upload-sarif-action/action.yml` | action 输入定义                   | 移除 `obs-ak` / `obs-sk` / `obs-region` 输入                              |
| `pre-commit-action/index.js`     | 执行 pre-commit 钩子并收集 SARIF  | 适配 `GITHUB_*` 上下文与 `GITHUB_OUTPUT`                                  |
| `.github/workflows/*.yml`        | GitHub 侧扫描与 pre-commit 流水线 | 新增 `id-token: write`，引用 `openlibing-test` 下的 action                |
| `StaticAlarmSourceEnum`          | 后端来源枚举                      | 新增 `GITHUB_ACTION`                                                      |
| `staticAlarmMultiSource.ts`      | 来源选项与标签格式化              | 新增 `{ label: 'GitHub Action', value: 'GITHUB_ACTION' }`                 |
| `StaticAlarm/index.vue`          | 代码检查列表页                    | 平台筛选/图标支持 GitHub                                                  |
| `StaticAlarm/detail.vue`         | 代码检查详情页                    | 无结构改动，右侧「数据来源」与扫描记录自动展示新标签                      |

## 4. 数据模型设计

**不适用（无新增/变更表结构）**，原因：本 US 只扩展现有来源枚举取值，不新增表、字段、索引或迁移。

补充说明：

- 来源取值由 `GITCODE_ACTION` 扩展为 `GITHUB_ACTION`，存储位置与字段长度沿用现状；
- 告警实例唯一键保持 `issue_id + category` 不变，来源变化不会产生重复记录；
- OBS 对象 key 结构不变，仅桶名按平台切换；
- 存量 `GITCODE_ACTION` 数据不迁移。

## 5. 性能设计

**不适用（无新增性能敏感路径）**，原因：GitHub 链路复用现有 clang-tidy 扫描与 SARIF 上传链路，仅替换平台上下文与认证方式。

补充说明：

- 全量扫描耗时主要由 clang-tidy 与编译数据库规模决定，原则上控制在小时级；
- pre-commit 场景沿用 10 分钟时限，超预算的工具应移出 pre-commit；
- OIDC/STS 每次运行只换证一次，SDK 内部缓存并做并发去重；
- OBS 上传与回调内置指数退避重试，不额外增加平台请求；
- GitHub 工作流提供 `concurrency`，同分支仅保留最新一次扫描。

## 6. API接口设计

**不适用（无新增/变更对外 HTTP 接口）**，原因：结果回传复用现有回调接口，前端复用现有查询接口。

| 项       | 说明                                                                  |
| -------- | --------------------------------------------------------------------- |
| 回调接口 | `POST /action-api/codescan/v1/result/receive`，沿用现有入参与签名方式 |
| 认证     | OIDC 临时凭证 + V11-HMAC-SHA256 签名                                  |
| 前端接口 | 无契约变化；来源筛选项新增 `GITHUB_ACTION` 枚举值                     |
| 错误码   | 沿用现有回调错误码；OIDC 换证失败按插件失败处理                       |

## 7. 安全设计

1. **免密优先**：GitHub 链路使用 OIDC 临时凭证，不在仓库或 Secrets 中保存长期 AK/SK；
2. **信任边界**：华为云 IAM 为 `gitcode-actions` 委托配置 `GitHubActions` 提供商，信任策略通过 `iss` / `aud` / `sub` 限定到目标组织、仓库与分支；
3. **最小权限**：OIDC 委托仅授予 OBS 上传与 APIG 回调所需权限；
4. **对象存储隔离**：GitHub 与 GitCode 使用不同 OBS 桶，避免跨平台对象混用；
5. **输入与日志**：外部可控字段（仓库名、分支名等）写入日志前做净化，不上送凭证；
6. **依赖安全**：`clang-tidy-sarif` 随仓预置并保留 MIT License，执行机不访问外网；
7. **发布顺序**：先上线后端来源枚举，再让插件上报 `GITHUB_ACTION`，避免非法来源被拒绝。
