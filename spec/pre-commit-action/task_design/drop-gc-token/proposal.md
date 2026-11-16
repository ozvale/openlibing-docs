# proposal：pre-commit-action 免凭证接入（复用 checkout 基线 ref，逐步废弃 gc_token）

- 仓库：`openlibing/pre-commit-action`
- 关联 Issue：`openlibing/pre-commit-action#52`
- 变更分支：`feat-drop-gc-token`
- 业务 PR：`openlibing/pre-commit-action#30`（兼容实现，待合入 `master`；此前的不兼容方案 #29 已关闭）
- docs PR：`openlibing/openlibing-docs#1334`
- 流程模式：Standard

## 背景

插件在 PR 增量检查时需要 `git fetch origin <baseRef>` 取得比较基线，历史上要求调用方额外传入 `gc_token` 用于私有仓认证。由此产生的问题：

1. 每个接入仓都要单独维护并传入一个高权限 Token（多数直接复用 `secrets.ROBOT_TOKEN`），凭证暴露面随接入仓数量线性放大。
2. 插件内部为此维护 GIT_ASKPASS 临时脚本生成 / 环境变量传递 / 结束清理三套逻辑，属于纯凭证搬运代码。
3. checkout 可按 `fetch-depth: 0` 生成远端基线 ref `origin/<baseRef>`；凭证是否可用取决于执行机类型，插件再次自行认证 fetch 属于重复实现。

## 目标

- 把「复用 checkout 生成的 `origin/<baseRef>`」作为默认路径：命中时插件零 fetch、零凭证。
- `gc_token` 保留为**可选**输入并标注已废弃，仅用于存量调用方在基线 ref 缺失时的兼容认证 fetch；不再作为新接入的推荐配置。
- 基线 ref 缺失且未传 `gc_token` 时，尝试无凭证 fetch；失败即 fail-closed 并给出 `fetch-depth: 0` 修复指引。
- 行为兼容：非 PR 事件仍为 `--all-files` 全量检查；PR 事件仍只检查变更文件。

## 非目标

- 本次不删除 `gc_token` 输入（直接删除会使未配置 `fetch-depth: 0` 且依赖 token 的存量 workflow 失败），下线动作待新版本发布并完成下游迁移后另起变更。
- 不改动 pre-commit 版本固定、镜像源测速、SARIF 收集与兜底解析等既有能力。
- 不批量修改下游仓 workflow（在 PR 描述中提供迁移说明）。

## 验收标准

- [x] `action.yml` 中 `gc_token` 为可选输入并标注「已废弃，仅兼容」；版本升至 1.1.0
- [x] PR 事件：`origin/<baseRef>` 存在时直接作为 `--from-ref`，不发起 fetch、不读取任何凭证
- [x] PR 事件：`origin/<baseRef>` 缺失且传入 `gc_token` 时，走 GIT_ASKPASS 认证 fetch 并打印 `[DEPRECATED]`
- [x] PR 事件：`origin/<baseRef>` 缺失且未传 `gc_token` 时，尝试无凭证 fetch；失败报错并 `exit(1)`，提示配置 `fetch-depth: 0`
- [x] 基线命中或 fetch 成功后执行浅克隆自检（`git rev-parse --is-shallow-repository`），浅历史时打印 `[WARN]` 但不阻断
- [x] 非 PR 事件仍为 `--all-files`
- [x] `dist/index.js` 由 `npm run package` 重建，与源码一致
- [x] `npm test`（7 个用例）、eslint、prettier 全部通过

## 兼容性与迁移

- **推荐配置**：PR 场景 checkout 配置 `fetch-depth: 0`，插件直接命中 `origin/<baseRef>`，无需任何凭证。
- **存量调用方**：继续传 `gc_token` 时，基线 ref 命中则走推荐路径；未命中则走与改造前等价的认证 fetch，行为不变（仅多一条 `[DEPRECATED]` 日志）。
- **未配置 `fetch-depth: 0` 且不传 `gc_token`**：GitCode 托管 checkout 默认不持久化凭证，无凭证 fetch 私有仓会失败并 fail-closed，**不等价于改造前的静默成功**，需按报错指引补 `fetch-depth: 0`。
- **迁移顺序约束**：必须先发布包含本变更的新版本并让下游完成 `fetch-depth: 0` 配置，才可后续删除 `gc_token` 输入，避免存量调用方直接断链。
