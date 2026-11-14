# archive：pre-commit-action 免凭证接入（drop gc_token）

## 结论

`pre-commit-action` 已移除 `gc_token` 输入及全部凭证搬运逻辑，PR 增量检查基线改为优先复用 checkout（`fetch-depth: 0`）已生成的 `origin/<baseRef>`，插件侧不再接收、传递、落盘任何 Git 凭证。功能行为与改造前一致：PR 事件仍只检查变更文件，非 PR 事件仍为 `--all-files`。

## 交付物

| 类型       | 内容                                                                                     |
| ---------- | ---------------------------------------------------------------------------------------- |
| 业务 Issue | `openlibing/pre-commit-action#52`（【需求】pre-commit 插件去掉 gc_token 输入）           |
| 业务 PR    | `openlibing/pre-commit-action#29`（`feat-drop-gc-token` → `master`，已打 `ai-assisted`） |
| 代码改动   | `action.yml`、`index.js`、`dist/index.js`、`README.md`、`test/resolve-base-ref.test.js`  |
| Spec       | `proposal.md`、`design.md`（7 章节）、`tasks.md`、本 `archive.md`                        |

## 关键实现

- `resolveBaseRef(baseRef)`：`git rev-parse --verify --quiet origin/<baseRef>` 命中即返回（零 fetch、零凭证）；未命中回退 `git fetch origin <baseRef>`（复用 checkout 持久化凭证）；仍失败则报错并 `exit(1)`。
- 删除 `createGitAskpass` / `removeGitAskpass` 与 `os` 依赖，`execFile` 移除 `env` 覆盖能力。
- `action.yml` 删除 `gc_token` 输入；README 补充 `fetch-depth: 0` 硬前提。

## 验证证据

- 测试仓 `openlibing-test/openlibing-cicd-test` PR #286：不传 `gc_token`，日志命中 `origin/main`，无 `git fetch`、无凭证报错，门禁通过并打上 `ci-pipeline-passed`。
- 多执行机矩阵：codearts-hosted 托管机、SGRunner 自建 euler 执行机均通过。
- 本地：`npm test`（含 `resolveBaseRef` 三条路径）、eslint、prettier 通过；`dist/index.js` 由 `npm run package` 重建。

## 遗留事项

1. **未打 tag**：插件版本发布与下游版本引用统一整改待维护者触发。
2. **workflow 未改动**：按用户要求，本次不修改任何 `.gitcode/workflows/` 文件（含插件仓 `nightly-schedule-scan.yml` 与下游 `openlibing-cicd` 的 `pre-commit.yml`），统一整改后续单独进行。
3. 下游迁移：checkout 增加 `fetch-depth: 0`，删除 `gc_token` 传参；残留传参按未知输入忽略，不阻断运行。
