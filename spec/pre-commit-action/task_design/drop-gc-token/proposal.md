# proposal：pre-commit-action 去掉 gc_token 输入

- 仓库：`openlibing/pre-commit-action`
- 关联 Issue：`openlibing/pre-commit-action#52`
- 变更分支：`feat-drop-gc-token`
- 业务 PR：`openlibing/pre-commit-action#29`
- 流程模式：Standard

## 背景

插件在 PR 增量检查时需要 `git fetch origin <baseRef>` 取得比较基线，历史上要求调用方额外传入 `gc_token` 用于私有仓认证。由此产生的问题：

1. 每个接入仓都要单独维护并传入一个高权限 Token（多数直接复用 `secrets.ROBOT_TOKEN`），凭证暴露面随接入仓数量线性放大。
2. 插件内部为此维护 GIT_ASKPASS 临时脚本生成 / 环境变量传递 / 结束清理三套逻辑，属于纯凭证搬运代码。
3. checkout 步骤已持久化仓库凭证，并可按 `fetch-depth: 0` 生成远端基线 ref，插件再次自行认证 fetch 属重复实现。

## 目标

- 删除 `gc_token` 输入，插件不再接收、传递、落盘任何 Git 凭证。
- 增量基线优先复用 checkout 已生成的 `origin/<baseRef>`，缺失时回退 fetch 并复用 checkout 持久化凭证。
- 行为兼容：非 PR 事件仍为 `--all-files` 全量检查；PR 事件仍只检查变更文件。

## 非目标

- 不改动 pre-commit 版本固定、镜像源测速、SARIF 收集与兜底解析等既有能力。
- 不做版本号 bump 与发版（发版由维护者单独触发）。
- 不批量修改下游仓 workflow（在 PR 描述中提供迁移说明）。

## 验收标准

- [ ] `action.yml` 不再声明 `gc_token`；源码无 `gc_token` / `GIT_ASKPASS` / `PRE_COMMIT_GC_TOKEN` 残留（`.gitleaks.toml` 扫描规则关键字除外）
- [ ] PR 事件：`origin/<baseRef>` 存在时直接作为 `--from-ref`，不发起 fetch
- [ ] PR 事件：`origin/<baseRef>` 缺失时回退 `git fetch origin <baseRef>`，成功返回 `FETCH_HEAD`
- [ ] PR 事件：回退 fetch 失败时明确报错并 `exit(1)`，提示配置 `fetch-depth: 0`
- [ ] 非 PR 事件仍为 `--all-files`
- [ ] `dist/index.js` 由 `npm run package` 重建，与源码一致
- [ ] `npm test`（含新增 `resolveBaseRef` 用例）、eslint、prettier 全部通过

## 兼容性与迁移

- 下游 PR 场景建议 checkout 配置 `fetch-depth: 0`；未配置时走回退 fetch，行为与改造前一致（仅不再由插件注入 token）。
- 下游 workflow 若仍传 `gc_token`，平台按未知输入处理（提示忽略），不影响运行；建议同步删除该传参。
- 公共仓无需任何凭证即可完成回退 fetch；私有仓依赖 checkout 已持久化的凭证权限。
