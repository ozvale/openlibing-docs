# 静态代码分析 GitHub 接入方案与文档 · ESLint — 设计文档

## 1. 方案设计

### 1.1 需求背景与目标态

「静态代码分析 GitHub 接入」FE 需求的首个落地工具为 clang-tidy（C/C++，见 [github-static-analysis/design.md](../github-static-analysis/design.md)）。本 US 为第二个落地工具，面向 JavaScript/TypeScript 仓库，将 ESLint 接入 GitHub Actions，打通「扫描 → SARIF → 上传 → 回调 → 页面展示」全链路，并沉淀 JS/TS 语言栈的 GitHub 接入范式。

**目标态**：

1. 在 GitHub 平台 `openlibing-test` 组织下新建测试仓 `eslint-full-scan-demo`，覆盖 workflow 全量扫描与 pre-commit 集成两种入口；
2. 两条 GitHub Actions 工作流运行 success，SARIF 上传 OBS 并回调 openLiBing beta 环境；
3. 「代码检查」页面筛选 GitHub 平台后可查看 ESLint 问题列表与详情；
4. GitCode `docs` 仓在 full-analysis 方案内补充 ESLint 的 GitHub 接入用户文档（3.7 / 4.6 小节与 `demos/github` 示例）；
5. 本设计文档归档至 `openlibing-docs` 仓 `github-static-analysis` 分支。

### 1.2 总体方案

完全复用 clang-tidy 沉淀的接入范式，语言栈差异收敛到「扫描器 + 规则配置」两点：

- 插件层零改动：复用 `pre-commit-action` 与 `upload-sarif-action`，不修改插件代码；
- SARIF 产出利用 ESLint 原生能力（`@microsoft/eslint-formatter-sarif`），无需 clang-tidy 场景的预置转换二进制；
- 规则单一事实源：`eslint.config.mjs`（flat config）在本地、pre-commit、GitHub workflow 三处共用；
- 测试仓为新建仓（clang-tidy 的 demo 仓已存在，ESLint 需新建 `eslint-full-scan-demo`），含被扫示例代码与两条工作流。

### 1.3 关键选型与理由

| 决策点       | 选择                                                                      | 理由                                                                                                       |
| ------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| SARIF 转换   | `@microsoft/eslint-formatter-sarif`（npm 依赖，随 `npm ci` 安装）         | ESLint formatter 生态原生支持，免维护离线二进制；与 clang-tidy「随仓预置转换器」相比显著简化               |
| 规则配置     | `eslint.config.mjs`（flat config，ESLint 9.x）                            | 单一事实源，本地/pre-commit/流水线共用，避免规则漂移                                                       |
| 插件引用     | `upload-sarif-action@source-platform-detection`；`pre-commit-action@main` | upload 插件验证期间锁定平台改造分支，口径与 clang-tidy 一致；pre-commit 插件仅有 main 分支且已含双平台改造 |
| 上报来源     | `source=GITHUB_ACTION`（插件按 `GITHUB_ACTIONS` 自动判定）                | 与后端 `static-alarm-github-adapt` 改造的 source 推断逻辑对齐                                              |
| 测试数据     | 示例代码故意构造 32 条问题（覆盖 15 条规则）                              | 同时验证解析、上传、入库、页面展示全链路，问题条数可与本地扫描结果逐条比对                                 |
| 测试仓可见性 | 私有仓                                                                    | 与 `openlibing-test` 组织下插件仓可见性保持一致（公共仓无法引用私有仓 action）                             |

### 1.4 涉及文件与跨仓影响

| 仓库 / 模块                             | 涉及内容                                                                                                    | 是否改代码 |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------- |
| `openlibing-test/eslint-full-scan-demo` | 新建仓：示例代码、`eslint.config.mjs`、`.pre-commit-config.yaml`、`.github/workflows/` 两条工作流           | 新建       |
| `openlibing-test/upload-sarif-action`   | 仅引用其 `source-platform-detection` 分支，无代码改动                                                       | 否         |
| `openlibing-test/pre-commit-action`     | 仅引用 main 分支，无代码改动                                                                                | 否         |
| `docs`（GitCode）                       | `tools/eslint/README.md` 3.7 / 4.6 小节、`demos/github/` 两个示例                                           | 文档       |
| `openlibing-codecheck`                  | 无新增改动；依赖 `static-alarm-github-adapt` 已交付的后端能力（source 枚举、repoType 解析、OBS 双桶白名单） | 否         |
| `openlibing-docs`                       | 本设计文档归档                                                                                              | 文档       |

## 2. 实现逻辑设计

### 2.1 主流程

```text
GitHub 代码仓触发 workflow / pre-commit
  → actions/checkout@v4
  → actions/setup-node@v4（node 20，cache: npm）
  → npm ci（含 @microsoft/eslint-formatter-sarif）
  → npx eslint "src/**/*.{js,ts}" -f @microsoft/eslint-formatter-sarif -o sarif.eslint.json
  → pre-commit 场景：pre-commit-action 收集钩子产出 SARIF
  → upload-sarif-action（@source-platform-detection）
     → OIDC 申请 ID Token → 华为云 STS 换取临时凭证
     → 上传 OBS（openlibing-github-action）
     → APIG 回调 openLiBing beta（source=GITHUB_ACTION，env_type=beta）
  → 解析入库 → 代码检查页面筛选 GitHub 查看结果
```

### 2.2 平台识别与上下文映射

平台判定由 upload-sarif-action 内部完成（`GITHUB_ACTIONS=true`），工作流侧无需任何平台参数。上报字段映射：

| 回调字段        | GitHub 取值                               | 说明                                                                     |
| --------------- | ----------------------------------------- | ------------------------------------------------------------------------ |
| `repoUrl`       | `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` | 形如 `https://github.com/owner/repo.git`，后端据此解析 `repoType=github` |
| `pipelineId`    | `GITHUB_JOB`                              | 工作流内 job 标识                                                        |
| `pipelineName`  | `GITHUB_WORKFLOW`                         | workflow 文件 `name`                                                     |
| `pipelineRunId` | `GITHUB_RUN_ID`                           | 运行 ID，用于 OBS 对象 key 与溯源                                        |
| `branch`        | `GITHUB_REF_NAME`                         | 触发分支                                                                 |
| `commitId`      | `GITHUB_SHA`                              | 触发 commit                                                              |

### 2.3 认证与上传逻辑

- OIDC 免密换证：workflow 声明 `permissions: id-token: write`，身份提供商 `GitHubActions`、信任委托 `github-actions`（与 GitCode 的 `gitcode-actions` 隔离）；
- OBS 桶按平台自动切换为 `openlibing-github-action`，对象 key 结构与 GitCode 保持一致（beta 实测形如 `eslint-results/{repo}/{轮次}/{runId}/eslint.sarif`，与 §2.6 实测记录一致）；
- 回调 `source=GITHUB_ACTION`、`env_type=beta`；AK/SK 输入已从插件移除，全链路无静态凭证。

### 2.4 前端展示逻辑

- 列表页：平台筛选出现 `github`（filter-options 数据驱动），来源标签显示「GitHub Action」；
- 详情页：右侧「数据来源」与扫描记录来源展示 GitHub Action 标签，其余字段沿用现有页面；
- 前端适配依赖 `static-alarm-github-adapt` 的前端清单（`STATIC_ALARM_SOURCE_OPTIONS` 补充 `GITHUB_ACTION` 映射、`platformIcon()` 增加 github 分支），本 US 不重复设计。

### 2.5 边界与异常处理

| 场景                              | 行为                                                                                                                                        |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 未提交 `package-lock.json`        | `setup-node` 的 `cache: npm` 前置条件不满足，工作流启动即失败；lock 文件必须随仓提交（实测首跑踩坑）                                        |
| pre-commit 场景 ESLint 退出非零   | 预期行为（存在违规即非零）；upload 步骤声明 `if: always()`，由 pre-commit-action 兜底收集已生成的 SARIF 继续上传                            |
| workflow 全量扫描 ESLint 退出非零 | 同为预期行为；`eslint-scan.yml` 的 upload 步骤同样声明 `if: always()`，ESLint 违规不阻断 SARIF 上传（实测 32 条违规场景两工作流均 success） |
| fork PR 触发                      | GitHub 不下发 `ACTIONS_ID_TOKEN_REQUEST_URL`，OIDC 换证失败；测试与验证必须使用同仓分支                                                     |
| 插件分支不可达                    | `Unable to resolve action` 直接失败；`source-platform-detection` 为验证期临时分支，稳定后收敛为 tag                                         |
| 代码无违规                        | ESLint 退出码 0，SARIF 仍生成（runs 为空数组），链路正常入库、页面 0 条                                                                     |

### 2.6 验证情况

以下均为 2026-11-06 在 beta 环境的实测结果：

| 检查点           | 结果                                                                                                |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| 两条工作流       | 均 success（scan 与 pre-commit 场景）                                                               |
| SARIF 条数一致性 | 本地 32 条（31 error + 1 warning，15 规则）与上传日志 `SARIF 规范化: eslint.sarif (32 条问题)` 一致 |
| OIDC 换证        | 提供商 `GitHubActions`、委托 `github-actions`，日志未出现 `gitcode-actions`                         |
| OBS 上传         | `obs://openlibing-github-action/eslint-results/eslint-full-scan-demo/{轮次}/{runId}/eslint.sarif`   |
| 平台回调         | `/codescan/v1/result/receive` 返回 `{"code":200,"msg":"success"}`，两次运行均受理并返回记录 ID      |
| 上下文映射       | `pipelineId`（GITHUB_JOB）、`pipelineRunId`（GITHUB_RUN_ID）、`commitId`（GITHUB_SHA）均正确        |

**已知平台侧依赖（非本 US 缺陷）**：测试仓未在 beta `repo_info` 注册时，回调入库记录的 `project_ids` 为空数组，「代码检查」页面按项目维度查询（`project_ids $in [projectId]`）无法命中，表现为页面无数据。处置方式：在 beta `repo_info` 注册 `github.com/openlibing-test/eslint-full-scan-demo` 并挂接项目，存量记录等待对账任务回填或手动补齐。该行为与 `static-alarm-github-adapt` 设计 2.1 节 `resolveProjectIds` 的定义一致。

## 3. 类设计

无后端/插件代码改动，不涉及类变更。测试仓组件清单：

| 组件                                                                           | 说明                                                                                                                    |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `.github/workflows/eslint-scan.yml`                                            | workflow 全量扫描（push + workflow_dispatch + 定时）                                                                    |
| `.github/workflows/eslint-precommit.yml`                                       | pre-commit 集成场景                                                                                                     |
| `.pre-commit-config.yaml`                                                      | eslint local hook，输出 SARIF 到固定路径                                                                                |
| `eslint.config.mjs`                                                            | flat config：`js.configs.recommended` + `typescript-eslint` + 显式开启 `eqeqeq` / `no-var` / `prefer-const` / `no-eval` |
| `package.json` / `package-lock.json`                                           | 声明 eslint 9.10.0、typescript-eslint、SARIF formatter；lock 文件必须提交                                               |
| `src/`（index.js、utils.js、types.ts、bad-practices.js、insecure-patterns.js） | 含 32 条故意违规的示例代码，覆盖 no-eval、no-dupe-keys、no-const-assign、no-fallthrough、eqeqeq 等 15 条规则            |

## 4. 数据模型设计

无数据库结构变更。数据落存量集合，新增取值：

- `static_alarm_scan_run`：`repo_type=github`、`source=GITHUB_ACTION`、`category=full` / `pre-commit-report`、`language=javascript/typescript`；
- 问题与实例数据沿用 SARIF 通用解析路径，与 GitCode 侧数据结构完全一致。

## 5. 性能设计

- ESLint 扫描为秒级（示例仓 5 个源文件），SARIF 32 条量级，上传与回调耗时与 clang-tidy 链路持平；
- 无新增后端查询维度，列表/计数接口沿用 `repo_type` / `source` 现有索引。

## 6. API 接口设计

无新增/变更接口。上报契约复用 `POST /codescan/v1/result/receive`（`StaticAlarmReceiveDTO`）：

- `repoUrl` 传 GitHub 地址（后端解析 `repoType=github`）；`source` 传 `GITHUB_ACTION`（不传时后端按 repoUrl 推断并记 WARN）；
- `obsUrl` 主机需在后端 OBS 白名单内（默认双桶已含 `openlibing-github-action`）；
- `sourceRunUrl` 透传 GitHub Actions 运行详情页链接，用于页面跳转。

## 7. 安全设计

1. **认证**：OIDC 免密换证，全程无 AK/SK；GitHub token 仅用于本次建仓/推送验证，任务完成后应撤销；
2. **测试数据隔离**：示例代码中的「故意违规」均为质量类问题（eval、松散比较、重复 key 等），不含真实凭证、内网地址或可利用漏洞代码，不触发敏感信息检查；
3. **上传链路**：复用后端 OBS 白名单强校验与 `repoType` 一致性防绕过（见 `static-alarm-github-adapt` 设计第 7 节），本 US 无新增安全面；
4. **权限最小化**：workflow 仅声明 `contents: read` + `id-token: write`，不授予 GitHub 侧任何写权限。
