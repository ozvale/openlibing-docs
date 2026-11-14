# 静态代码分析 GitHub 接入方案与文档 · clang-tidy - 交付归档

## 归档信息

| 项目         | 内容                                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------ |
| FE 需求名称  | 【openLiBing-coderepo】静态代码分析GitHub接入方案与文档-clang-tidy                                           |
| FE Issue     | https://gitcode.com/openlibing/code-metrics-action/issues/74                                                 |
| 设计归档 PR  | openlibing/openlibing-docs#1304（design.md + prototype.html，已合入）                                        |
| 交付归档 PR  | 本 PR（proposal.md + tasks.md + archive.md）                                                                 |
| 用户文档 PR  | openlibing/docs#59（clang-tidy GitHub 配置与 full-analysis 双平台样例，待合入 `main`）                       |
| 关联适配事项 | 后端 openlibing/openlibing-codecheck#391（已合入 `release_20261116_iter1`）；前端 openlibing-web 暂无对应 PR |
| 归档日期     | 2026-11-11                                                                                                   |

## 需求概述

以 clang-tidy 为样板，在 GitHub Actions 上打通「扫描 → SARIF → OBS → 回调 openLiBing」全链路，并沉淀可复用的 GitHub 接入范式。采用单份代码、运行时按 `GITHUB_ACTIONS` 识别平台的方案，不为 GitHub 维护独立插件分支。

## 交付清单

### GitHub 测试仓（openlibing-test，私有）

| 仓库                        | 说明                                                            |
| --------------------------- | --------------------------------------------------------------- |
| `clang-tidy-full-scan-demo` | 示例仓：被扫 C 代码、`.clang-tidy`、wrapper 脚本、两套 workflow |
| `pre-commit-action`         | GitHub 适配版 pre-commit 插件（`GITHUB_*` 上下文与输出）        |
| `upload-sarif-action`       | GitHub 适配版 SARIF 上传插件（OIDC、来源标记、桶隔离）          |

### upload-sarif-action 关键提交（`source-platform-detection` 分支）

| 提交      | 内容                                                 |
| --------- | ---------------------------------------------------- |
| `cd002be` | GitHub 场景切换 OIDC 认证，移除静态 AK/SK 依赖       |
| `0fd322c` | 依赖引用 GitHub OIDC SDK 分支                        |
| `ef86e5a` | 新增平台判定与 `GITHUB_ACTION` 来源标记              |
| `05d5ea9` | OIDC SDK 升级至 v0.0.7，`package-lock.json` 同步锁定 |

### demo 工作流

- `.github/workflows/clang-tidy-scan.yml`：workflow 全量扫描；
- `.github/workflows/clang-tidy-precommit.yml`：pre-commit 集成；
- 两者均声明 `permissions.id-token: write`，验证时引用 `openlibing-test/upload-sarif-action@source-platform-detection`（验证版本 `05d5ea9e9f9a76497022ccab322f6dc22d827820`）；demo 仓提交 `7dd349f` 完成该引用更新。生产接入应固定到上述 SHA，避免可变分支在持有 `id-token: write` 时执行未评审代码。

### 文档

- `openlibing-docs`：`design.md`、`prototype.html`（#1304 已合入）、`proposal.md` / `tasks.md` / `archive.md`（本 PR）；
- `docs`：clang-tidy README `3.6` / `4.7` GitHub Actions 配置、`demos/github/` 两套样例、full-analysis README 的 GitCode / GitHub 双平台样例（PR #59，待合入 `main`）。

## 验证证据

| 验证项            | 结果                                                                                                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 全量扫描工作流    | [run 41803721358](https://github.com/openlibing-test/clang-tidy-full-scan-demo/actions/runs/41803721358) success                                                              |
| pre-commit 工作流 | [run 41803725788](https://github.com/openlibing-test/clang-tidy-full-scan-demo/actions/runs/41803725788) success                                                              |
| 来源标记          | 日志输出 `[INFO] 来源标记: GITHUB_ACTION`                                                                                                                                     |
| OIDC 换证         | 提供商 `GitHubActions`、委托 `github-actions`，STS 换证成功                                                                                                                   |
| OBS 上传          | 桶 `openlibing-github-action`，key 含 `{owner}/{repo}/{runId}`                                                                                                                |
| 平台回调          | APIG 返回 `{"code":200,"msg":"success"}`（验证环境 beta，后端版本与来源枚举支持情况未在本次核对范围）                                                                         |
| 结果入库          | beta `static_alarm_scan_run` 存在 `category=business` / `pre-commit-report` 记录；后端来源枚举已支持 `GITHUB_ACTION`（#391，待随 `release_20261116_iter1` 发布）              |
| GitCode 链路回归  | 本次未执行（改造后未运行 GitCode 工作流），列为发布前待验证项                                                                                                                 |
| 质量门禁          | `upload-sarif-action`：`npm test` 79 项通过、`pre-commit` 全绿、`dist` 已重建；`pre-commit-action` 无独立单测，通过 `clang-tidy-precommit` demo 工作流（run 41803725788）验证 |

## 关键技术决策

| 决策                        | 理由                                                             |
| --------------------------- | ---------------------------------------------------------------- |
| 单份代码运行时识别平台      | 避免 GitCode/GitHub 双分支漂移，降低维护成本                     |
| OIDC 免密换证               | 不落长期 AK/SK；SDK 0.0.7 起按平台自动选择提供商与委托           |
| OBS 桶按平台隔离            | 便于权限、成本与对象归集，后端按桶白名单识别                     |
| 插件内显式上报来源          | 由 `GITHUB_ACTIONS` 判定生成 `GITHUB_ACTION`，避免后端猜测平台   |
| `clang-tidy-sarif` 随仓预置 | 执行机不依赖外网，产物与 GitCode 链路一致                        |
| 文档不新增并列目录          | GitHub 作为 full-analysis 方案内的平台维度扩展，保持信息架构稳定 |

## 遗留与后续

1. **GitCode 侧回归与 AK/SK 迁移**：本次验证仅覆盖 GitHub 侧；`upload-sarif-action` 已移除 `obs-ak` / `obs-sk` / `obs-region` 输入，存量 GitCode 工作流需删除对应参数并依赖 OIDC 换证，发布前需补做 GitCode 上传/回调回归验证。
2. **后端来源枚举**：`StaticAlarmSourceEnum` 已新增 `GITHUB_ACTION` / `GITEE_ACTION`，并补充平台推断、仓库域名关键字配置与 OBS 桶白名单（openlibing-codecheck#391），已合入 `release_20261116_iter1`，待随版本发布。
3. **前端展示适配**：来源选项/标签与列表页 GitHub 平台展示仍未完成，openlibing-web 暂无对应 PR，需补充实现并建单跟踪；发布顺序仍为「先前后端、后插件上报」。
4. **用户文档合入**：openlibing/docs#59 已提交但尚未合入 `main`，合入后验收标准第 7 条才全部满足。
5. **转测**：完成上述适配并部署 beta 后，按验收标准执行测试流程。
6. **其他工具接入**：Bandit、ESLint、gosec、SpotBugs、cargo-clippy、gitleaks 等按各自 US 复用本范式，用户文档已在 `docs` 仓提供对应 GitHub 章节。
7. **api.md 不适用**：本需求无新增/变更对外 HTTP 接口，结果回传复用 `/action-api/codescan/v1/result/receive`，前端复用现有查询接口。

## 结论

GitHub 侧 clang-tidy 接入链路已在 `openlibing-test` 组织内完成端到端验证，插件改造、工作流样例已交付；后端来源枚举已合入 `release_20261116_iter1` 待发布，前端展示适配、GitCode 侧回归、用户文档 PR #59 合入与转测仍待完成，详见遗留项。
