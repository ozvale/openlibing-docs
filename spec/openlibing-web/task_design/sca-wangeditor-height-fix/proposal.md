# sca-wangeditor-height-fix

## 需求背景

Issue #303（[缺陷]: 项目合规-批量分析，分析说明输入过多内容无滚动条下拉，无法查看全部）：
项目合规批量分析场景下，分析说明 wangEditor 输入过多内容后无滚动条下拉，超出部分无法查看。

根因：`apps/web-openlibing/src/views/sca/component/wangEditor/index.vue` 在 `editor.create()` 之后
通过修改容器 DOM 高度设置编辑器高度。wangEditor v4（4.7.15）中，create 后再改
`.w-e-text-container` 容器高度不会同步 `.w-e-text` 的 min-height（保持默认 300px），
内容超出可视高度时被容器 `overflow:hidden` 静默裁切，且无法滚动回滚。

## 方案概要

高度设置时机从 create 后 DOM 操作改为 create 前配置：在 `editor.create()` 之前通过
`editor.config.height` 设置编辑区高度，对齐 `src/components/WangEditor.vue` 的既有正确实现。

## 验收标准

- [x] `editor.create()` 前通过 `editor.config.height` 设置高度，不再依赖 create 后容器 DOM 高度操作
- [x] 分析说明输入内容超出编辑区高度时，编辑区内部可滚动查看全部内容，不再被裁切
- [x] `minHeight` prop 行为保持不变（仍通过容器 style.minHeight 设置）
- [x] `height` 未传时编辑器保持默认高度，无回归
- [x] ESLint 检查无新增错误

## 关联

- 业务 Issue：openlibing/openlibing-web#303
- 业务 PR：https://gitcode.com/openlibing/openlibing-web/merge_requests/801（fix(sca): set wangEditor height via config before create）
- 业务分支：feature-sca-inspection → release_20260923
