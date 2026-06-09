# PR 门禁看板详情页增加列设置 + Issue 运营标签优化 + 测试仪表盘优化 — 归档

## 关联

- 业务 Issue: <https://gitcode.com/openlibing/openlibing-ops-web/issues/20>
- 业务 PR: <https://gitcode.com/openlibing/openlibing-ops-web/pull/55>（`feat/pr-info-detail-column-setting-temp` → `release_20260611_iter1`）
- 业务 PR commit 范围: `2937a67..ade23e5`（8 个 commit）
- 业务 Issue 状态: 交付完成，待用户在 PR 合入后关闭
- docs 仓归档分支: `spec/openlibing-ops-web/pr-info-detail-column-setting`

## 交付历程

- commit [`2937a67`](https://gitcode.com/openlibing/openlibing-ops-web/commit/2937a674a20cace0f6f31db641a650c2e41acaa2): `feat(pr-detail)` 重构 pr-info-detail 为 el-drawer 模式，迁移导出逻辑，集成列设置
- commit [`d95300c`](https://gitcode.com/openlibing/openlibing-ops-web/commit/d95300cbb21a9ec3ad1190fa1f75dba531c817bb): `fix(test-dashboard)` 调整 `getResultType` / `getResultLabel` 数字键映射
- commit [`3dce0f5`](https://gitcode.com/openlibing/openlibing-ops-web/commit/3dce0f5d303b179f360c535baac10be400b871c1): `feat(case-history)` 新增 `totalNpu` 卡片并优化指标布局
- commit [`9a0c426`](https://gitcode.com/openlibing/openlibing-ops-web/commit/9a0c426298f8a5eedf44d350cb1258ede4a5343a): `fix(case-history)` 5 个指标单行展示、通过率单位内联、空值显示 `--`
- commit [`7081c6e`](https://gitcode.com/openlibing/openlibing-ops-web/commit/7081c6e8008d78e046dbd1f2188f3acdb664b06f): `style(column-setting)` 优化树形布局（has-children 识别、统一 flex、节点宽度 162px）
- commit [`c18f366`](https://gitcode.com/openlibing/openlibing-ops-web/commit/c18f3661d0df8b1c250fbfe2b06b534e03f08565): `style` 通用布局微调
- commit [`eb3cbcf`](https://gitcode.com/openlibing/openlibing-ops-web/commit/eb3cbcfe16f9e7529c18aaf19abda64454cbe0fb): `fix(case-history)` 平均类指标 label 追加 `消耗` 后缀
- commit [`ade23e5`](https://gitcode.com/openlibing/openlibing-ops-web/commit/ade23e5a7dc1a98a3f20a391b76c9615d51d76f1): `feat(dashboard)` test-dashboard 路由参数新增 `uemId`

变更规模：10 文件，+238 / -110。

## 用户自测反馈

- 本次需求用户未提出反馈问题，8 个 commit 一次性通过 CI（PR #55 标签 `ci-pipeline-passed`）。

## 最终验证

- PR 流水线：`ci-pipeline-passed`（见 PR #55 标签）
- 构建验证：未在归档阶段单独跑 `npm run build`，构建结果以 PR CI 为准
- 手动验证项（来自 PR #55 测试计划）：
  - [ ] 打开 PR 详情抽屉，验证列设置开关可正常显隐列
  - [ ] 验证 case-history 卡片新增 totalNpu 数值正确
  - [ ] 验证平均指标 label 文案（包含 `消耗` 后缀）
  - [ ] 验证 test-dashboard 跳转携带 uemId 参数
  - [ ] 验证空值场景显示 `--` 占位

## 设计偏差与取舍

- **范围扩展**：本次需求 issue 描述仅涵盖「PR 详情页列设置」与「Issue 运营标签」两部分，最终实现额外延伸到 `test-dashboard` 结果映射、`case-history-view` 指标卡与 `column-setting` 布局统一。延伸部分在 proposal.md 中已显式列出并取得用户确认，不属于需求蔓延。
- **drawer vs page**：issue 原本要求 pr-info-detail 内层包裹 el-drawer，最终实现选择将整个组件外层包 drawer，让该组件成为自包含的弹窗入口，便于在其它页面复用 `column-setting`。
- **指标 label 命名**：`平均vCPU` / `平均NPU` 改名为 `平均vCPU消耗` / `平均NPU消耗`，与新增的 `总NPU消耗` 卡片在语义上保持一致。

## 可复用经验

- **el-drawer 复用模式**：当某个子页面需要被多处触发时，将组件顶层改用 `el-drawer` 包裹并以 `defineExpose` 暴露方法，比在父组件嵌套 drawer 维护成本更低。
- **列设置列定义集中管理**：`column-setting.vue` 通过 props 接收列描述数组，标题/字段/key 集中维护，根级与子节点统一 flex 布局，父节点加粗加底边可让用户一眼看到分组边界。
- **指标卡单位内联**：将单位写入数据后缀（如 `1.2 ms`）而不是 label 里，可让 label 文案更短、单位始终贴近数值；空值时统一显示 `--` 占位符，比 `0`/`null` 更友好。

## 归档日期

2026-06-09
