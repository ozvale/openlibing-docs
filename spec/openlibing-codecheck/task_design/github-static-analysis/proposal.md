# 静态代码分析 GitHub 接入方案与文档 · clang-tidy

## 需求背景

openLiBing 的代码检查链路此前主要面向 GitCode Actions：各静态分析工具产出 SARIF，经 `upload-sarif-action` 上传 OBS 并回调 openLiBing，最终在「开发管理 - 代码检查」页面展示。随着业务仓迁移到 GitHub，需要在 GitHub Actions 上复用同一套扫描、转换与上报链路，避免为每个平台维护独立的插件分支。

本 US 是「静态代码分析 GitHub 接入」FE 的首个落地工具，以 **clang-tidy** 为样板，打通 GitHub 全量扫描与 pre-commit 两种入口，并沉淀可复用的平台适配方案与用户文档，供后续工具按同一范式接入。

## 需求目标

1. 在 GitHub `openlibing-test` 组织下准备可运行的 clang-tidy 流水线，覆盖 workflow 全量扫描与 pre-commit 集成两种入口；
2. 扫描结果生成合法 SARIF，上传 OBS 并回调 openLiBing beta 环境；
3. 「代码检查」页面筛选 GitHub 平台后能看到问题列表与详情，来源展示为 GitHub Action；
4. 沉淀 GitHub 接入用户文档与可复用范式，其他静态分析工具可按同一结构接入；
5. 满足以上条件后转入测试流程。

## 需求范围

### 涉及仓库 / 模块

| 仓库 / 模块                 | 涉及内容                                                             |
| --------------------------- | -------------------------------------------------------------------- |
| `upload-sarif-action`       | 平台识别、OIDC 提供商切换、OBS 桶选择、来源标记、移除 AK/SK 输入     |
| `pre-commit-action`         | GitHub 上下文适配（`GITHUB_*`、`GITHUB_OUTPUT`）与 README 接入说明   |
| `clang-tidy-full-scan-demo` | `.github/workflows/` 两套 GitHub 工作流、预置二进制与示例代码        |
| `openlibing-codecheck`      | `StaticAlarmSourceEnum` 新增 `GITHUB_ACTION`（由 #397 跟踪）         |
| `openlibing-web`            | 来源选项/标签、列表页 GitHub 平台展示、详情页两处 GitHub Action 标签 |
| `openlibing-docs`           | 设计文档、需求原型与交付归档                                         |
| `docs`                      | full-analysis 方案内补充 GitHub 接入用户文档                         |

### 包含

- GitHub OIDC 免密换证（`GitHubActions` 身份提供商）与 OBS 桶按平台隔离；
- GitCode 与 GitHub 均使用 OIDC 免密换证；`upload-sarif-action` 不再声明 `obs-ak` / `obs-sk` / `obs-region` 输入，存量工作流需删除对应 `with` 参数，由 OIDC 自动获取凭证；
- `upload-sarif-action` / `pre-commit-action` 单份代码运行时识别平台，不维护独立分支；
- clang-tidy 全量扫描与 pre-commit 集成两套 GitHub workflow 示例；
- GitHub 接入用户文档（工具配置、平台差异、字段映射与排错）；
- 设计文档、需求原型与交付归档。

### 不包含

- 其他静态分析工具（Bandit、ESLint、gosec、SpotBugs、cargo-clippy、gitleaks 等）的具体接入，按各自 US 推进；
- GitHub 账号映射、PR 文件获取、详情页其他 GitHub 交互；
- 存量 `GITCODE_ACTION` 数据迁移。

## 验收标准

1. GitHub 全量扫描与 pre-commit 两条工作流均可成功执行；
2. 运行日志显示来源标记为 `GITHUB_ACTION`，OBS 对象写入 `openlibing-github-action` 桶；
3. APIG 回调 beta 返回 `{"code":200,"msg":"success"}`，扫描记录正常入库；
4. 「代码检查」页面筛选 GitHub 平台后可见结果，列表与详情来源展示 GitHub Action；
5. 存量 GitCode 工作流在移除 `obs-ak` / `obs-sk` 入参并切换 OIDC 后仍可正常上传；
6. GitCode 原有扫描、上报与展示链路回归不受影响；
7. 用户文档与设计/交付归档分别合入 `docs` 仓与 `openlibing-docs` 仓主干。

## 关联 Issue

- FE 唯一 Issue：https://gitcode.com/openlibing/code-metrics-action/issues/74
- 后端来源枚举与前端展示适配：openlibing/openlibing-codecheck#397

## 交付物

- 设计文档：`design.md`（7 章节）
- 需求原型：`prototype.html`
- 交付归档：`proposal.md`、`tasks.md`、`archive.md`
- 代码交付：GitHub `openlibing-test` 下三个仓及两套 demo 工作流
- 用户文档：`docs` 仓 `static-code-analysis/solutions/full-analysis/`（工具章节 + workflow 示例）
