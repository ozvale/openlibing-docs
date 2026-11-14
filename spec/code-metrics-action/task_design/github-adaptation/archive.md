# 代码度量指标插件支持 GitHub — 归档

## 关联

- 业务 Issue：https://gitcode.com/openlibing/code-metrics-action/issues/74
- 业务 PR：[!44](https://gitcode.com/openlibing/code-metrics-action/pull/44)（主功能，已合入）
- 配套 PR：[!46](https://gitcode.com/openlibing/code-metrics-action/pull/46)（UT 流水线调整）、[!47](https://gitcode.com/openlibing/code-metrics-action/pull/47)（安全加固）
- docs PR：[#1303](https://gitcode.com/openlibing/openlibing-docs/pull/1303)（design.md + prototype.html）
- Release tag：`v1.0.4` → commit [09292c3](https://gitcode.com/openlibing/code-metrics-action/commit/09292c367a283b0b0f3d119a9e11bc00db8f9d27)

## 交付历程

- commit `fe8674f`：合入 !44 GitHub Actions 适配（平台识别、OIDC、摘要、OBS 桶隔离）
- commit `e6f351b`：修复 GitHub PR 事件游离 HEAD 时 `branchName` 上报为 `HEAD`
- commit `b689e8d`：治理 gitleaks 对打包产物与 action 输入名的误报
- commit `95e8f72`：glob 规则容错与摘要链接转义安全加固
- commit `09292c3`：版本升至 1.0.4 并重建 `dist`，创建附注 tag `v1.0.4`

## 用户自测反馈

- 检视意见：PR 事件下 `branchName` 取到 `HEAD` → 新增 `resolveBranchName` 回落目标分支（`e6f351b`）
- 检视意见：新增的 `summary.js` / `ciContext.js` 逻辑缺少单测，且覆盖率只统计已加载文件 → 抽取纯函数、补 12 个测试文件 64 个用例、新增 `.c8rc.json` 统一口径
- 流水线问题：pre-commit 的 gitleaks 对 `dist` 打包产物与 action 输入名误报 → allowlist + 行内放行（`b689e8d`）
- GitHub 生产镜像仓首跑：STS 403 `STS5.1001`，根因为仓库创建于 2026-07-15 之后，OIDC `sub` 使用不可变 ID 新格式，IAM 信任策略未覆盖；信任策略已修正，待复验

## 最终验证

- 单测：`node --test`，v1.0.4 共 66 个用例全部通过（!44 合入时 64 个，!47 在 `fileCollector.test.js` 与 `summary.test.js` 各补 1 个）
- 覆盖率：`.c8rc.json` 按 `src` 全量统计（排除入口与二进制资产），增量覆盖率 98%
- 静态检查：pre-commit（prettier / eslint / gitleaks）全量通过
- GitHub 验证仓：`openlibing-test/code-metrics-action` run `42987841974` 扫描、摘要、上报通过
- GitHub 生产镜像仓：run `42990956297` 扫描与摘要成功；上报因 IAM 信任策略 `sub` 格式不匹配失败，策略修正后待复验
- GitCode 回归：`v1.0.4` 的 `code-metrics-scan` run #105 在初始化步骤失败，未进入插件步骤，待平台侧排查

## 设计偏差与取舍

- `action.yml` 保持 `runs.using: node16`：GitCode runner 仅支持 node16；GitHub 会将 node16 动作强制按 node20 运行，因此 GitHub 侧实际运行时不处于 EOL 状态，GitCode 侧仍运行 node16。Node 16 已停止安全支持，本项作为已知风险由插件维护人跟踪：GitCode runner 支持 node20 后立即切换 `runs.using: node20` 并重建 `dist`，目标为 GitCode runner 升级后的首个插件版本；暂未单独立项，跟踪入口为本归档与插件仓后续版本计划
- 设计未包含的测试与覆盖率治理（`.c8rc.json`、新增 12 个测试文件；v1.0.4 共 66 个用例）为评审阶段补充，不改变运行时行为
- IAM 信任策略需同时覆盖 GitHub 旧格式与不可变 ID 新格式 `sub`，该要求已写入设计 §7 安全设计

## 可复用经验

- GitHub 2026-07-15 起新建/转移的仓库，OIDC `sub` 为 `repo:<org>@<orgID>/<repo>@<repoID>:<限定类型>:<限定值>`；信任策略只写 `repo:<org>/*` 无法匹配，需同时覆盖新旧两种格式，且 owner 大小写必须与仓库实际登录名一致
- GitHub Actions 没有 GitCode 式输出面板，富文本只能写 `GITHUB_STEP_SUMMARY`；GitCode 的 `ATOMGIT_OUTPUT` 在 GitHub 无对应能力
- c8 默认只统计运行期加载的文件，需 `--all --src=src` 并显式排除入口与二进制资产，否则覆盖率虚高

## 归档日期

2026-11-11
