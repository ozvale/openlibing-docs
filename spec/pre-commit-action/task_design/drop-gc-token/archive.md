# archive：pre-commit-action 免凭证接入（复用 checkout 基线 ref）

## 结论

`pre-commit-action` 的 PR 增量基线已改为**优先复用 checkout（`fetch-depth: 0`）生成的 `origin/<baseRef>`**，命中时插件零 fetch、零凭证。`gc_token` 保留为可选兼容输入并标注已废弃，仅在基线 ref 缺失且存量调用方仍传参时走原 GIT_ASKPASS 认证 fetch。

业务 PR `openlibing/pre-commit-action#30` 已于 2026-11-16 合入 `master`（`action.yml` / `package.json` 版本 1.1.0，尚未打 tag 发布）；文中「已实现」指该分支合入时的代码状态，与 `master` 一致。

检查范围语义与改造前一致：PR 事件仍只检查变更文件，非 PR 事件仍为 `--all-files`。但**基线获取的前置条件有变化**：推荐路径要求 checkout 配置 `fetch-depth: 0`；未配置时若凭证不可用（GitCode 托管 checkout 默认不持久化凭证）会 fail-closed，不等价于改造前的隐式成功。

## 交付物

| 类型       | 内容                                                                                                                                           |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 业务 Issue | [openlibing/pre-commit-action#52](https://gitcode.com/openlibing/pre-commit-action/issues/52)                                                  |
| 业务 PR    | [openlibing/pre-commit-action#30](https://gitcode.com/openlibing/pre-commit-action/pulls/30)（`feat-drop-gc-token` → `master`，`ai-assisted`） |
| 已关闭 PR  | `openlibing/pre-commit-action#29`：早期「直接删除 `gc_token`」的不兼容方案，已被 #30 的兼容实现取代                                            |
| 代码改动   | `action.yml`、`package.json`、`index.js`、`dist/index.js`、`README.md`、`test/resolve-base-ref.test.js`                                        |
| Spec       | `proposal.md`、`design.md`、`tasks.md`、本 `archive.md`（[docs PR #1334](https://gitcode.com/openlibing/openlibing-docs/pulls/1334)）          |

## 关键实现

- `resolveBaseRef(baseRef)` 三级解析：
  1. `git rev-parse --verify --quiet origin/<baseRef>` 命中 → 直接返回，零 fetch、零凭证；
  2. 未命中且传入 `gc_token` → 打印 `[DEPRECATED]`，按原 GIT_ASKPASS 路径认证 fetch，返回 `FETCH_HEAD`；
  3. 未命中且未传 `gc_token` → 无凭证 fetch，失败则输出修复指引并 `exit(1)`（fail-closed）。
- 基线命中或 fetch 成功后执行 `warnIfShallowClone()`：`git rev-parse --is-shallow-repository` 为 `true` 时打印提示，不阻断，避免增量口径静默退化。
- `createGitAskpass` / `removeGitAskpass` 保留用于兼容路径：脚本写入系统临时目录（权限 0700），token 经 `PRE_COMMIT_GC_TOKEN` 环境变量传递，`finally` 中立即清理。
- `action.yml` 将 `gc_token` 改为 `required: false` 并标注已废弃；`package.json` / `action.yml` 版本 1.1.0。

## 验证证据

- 业务 PR #30 流水线：2026-11-16 最新 head 下 7 条检查全部通过（build、malicious-code-pr-scan、sca-pr-scan、ut、pre-commit 的 pr-label-running / pre-commit / pr-label-complete）。
- 单测：`npm test` 7 个用例通过（`origin/<baseRef>` 命中、回退 fetch、fetch 失败、浅克隆提示、`gc_token` 兼容路径）；本地 bare 仓模拟 origin，离线可跑。
- 静态检查：`npx eslint index.js test/` 0 error；`npx prettier@3.9.5 --check` 通过。
- 产物一致性：`dist/index.js` 由 `npm run package` 重建。
- 端到端：测试仓 `openlibing-test/openlibing-cicd-test` PR 事件不传 `gc_token`，日志命中 `origin/main`、无凭证报错，门禁通过。

## 遗留事项

1. **未打 tag**：版本 1.1.0 已合入 `master` 但未发布 tag，插件版本发布与下游版本引用统一整改待维护者触发。
2. **workflow 未改动**：本次不修改任何 `.gitcode/workflows/` 文件（含插件仓 `nightly-schedule-scan.yml` 与下游 `openlibing-cicd` 的 `pre-commit.yml`），统一整改后续单独进行。
3. **`gc_token` 下线顺序**：先发布新版本 → 下游补 `fetch-depth: 0` 并删除传参 → 再另起变更删除输入；顺序颠倒会导致未迁移的存量 workflow 直接失败。
