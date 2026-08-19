# 重复代码抽屉优化（2026-08-19）— 技术设计

## 方案概述

对重复代码抽屉（DuplicationCodeDrawer）做三项核心改造：CodeMirror 高亮从"每次整树重建"改为"StateField 增量更新"以解决大文件卡顿；occurrence 页签切换自动滚动到可视区域；省略行高亮范围同步渲染左侧占位色条。同时完成分支筛选交互增强、项目切换缓存清理、刷新跳转修复与 nanoid 依赖安全处理。

## 架构决策

### 1. 高亮渲染：StateField + 共享 ViewPlugin（替代 reconfigure）

- **原方案**：每次 `highlightCurrentBlock` 用 `StateEffect.reconfigure` 重建整棵扩展树，并新建临时 `ViewPlugin.fromClass`。编辑器越大，重建成本越高（gutter、行号、所有插件全量重装），且 markers 回调按"行 × 块"全量计算。
- **新方案**：
  - 高亮装饰集存入 `StateField<DecorationSet>`，切块时仅 `view.dispatch({ effects: setHighlightEffect })` 增量更新。
  - `highlightPlugin` 定义为模块级共享 ViewPlugin，其 `decorations` 提供者从 state 读取 field 值，`update` 时随 field 变化刷新。
  - 行→块映射（`buildRowLaneInfo`）在数据加载时预计算一次，markers 回调 O(1) 查表。
  - 色条颜色改为 DOM 级刷新（`refreshBlockStripeColors` 只更新视口内已渲染色条），marker 不再固化颜色。
  - 行号映射由每次线性查找改为 Map（`origToDocMap`）。

### 2. 关键回归教训：extensions 必须同时注册 StateField

- 本分支曾因 extensions 只加 `highlightPlugin` 而漏加 `highlightField`（StateField），导致 plugin 读取 `view.state.field(highlightField)` 抛 `RangeError: Field is not present in this state`，装饰永不渲染、背景色消失。
- **结论**：引入 StateField 时必须在 `EditorState.create({ extensions: [...] })` 中同时注册 field 与依赖它的 plugin，二者缺一不可。

### 3. occurrence 页签自动滚动

- 页签条容器加 `ref`，`selectOccurrence` 在 `nextTick` 后调用 `scrollActiveOccTabIntoView()`：以 `.active` 页签的 offsetLeft/offsetWidth 与容器 clientWidth/scrollLeft 比较，越界则滚动到目标位置。
- 切换上一个/下一个按钮同样复用该逻辑。

### 4. 分支筛选与项目切换

- `branches.vue` 筛选输入框绑定 `@keyup.enter="applyBranchFilter"`（焦点在输入框时回车即确定）。
- 项目切换 watch 中加入 `branchSearchCache.value = ''`，与 `showBranch` 等子页状态重置并列。
- autoGoBranch 判断由 `!oldValue` 改为 `!oldValue?.projectId`：空对象 `{}` 无 projectId，刷新后视为首次加载可跳转；切项目时 oldValue 带 projectId 不跳转。

### 5. 依赖安全（nanoid）

- 移除 `apps/web-openlibing/package.json` 中未使用的 `nanoid` 直接依赖（业务代码无引用）。
- `pnpm-workspace.yaml` overrides `nanoid@3` 由 3.3.17 升到 3.3.18。
- **为何不能升 4.x/5.x**：postcss 8.x 用 CJS `require('nanoid')`，nanoid 4/5 为 ESM-only（exports 无 require 条件），强升会构建崩溃。3.3.17 起已修复 CVE-2026-67213（NVD 受影响范围 `3.0.0 ≤ x < 3.3.17`），3.3.18 为 CJS 兼容范围内最新修复版。扫描器若仍报 3.3.17/3.3.18 属数据源宽范围误报。

## 涉及文件

| 文件 | 操作 | 说明 |
| ---- | ---- | ---- |
| `apps/web-openlibing/src/views/Repos/dialog/DuplicationCodeDrawer.vue` | 修改 | 高亮 StateField 化、省略行占位、页签自动滚动、性能优化、色条宽度、修复高亮回归 |
| `apps/web-openlibing/src/views/Repos/branches.vue` | 修改 | 筛选输入框回车确认 |
| `apps/web-openlibing/src/views/Repos/index.vue` | 修改 | 切项目清空 branchSearchCache、autoGoBranch 判断修复 |
| `apps/web-openlibing/package.json` | 修改 | 移除未使用的 nanoid 直接依赖 |
| `pnpm-workspace.yaml` | 修改 | overrides `nanoid@3` 3.3.17 → 3.3.18 |
| `pnpm-lock.yaml` | 修改 | 依赖解析更新 |

## 风险 & 缓解

| 风险 | 缓解 |
| ---- | ---- |
| StateField 漏注册导致高亮丢失（已发生过） | 扩展注册时 field 与 plugin 成对校验；本次已通过临时 vitest 复现并验证修复 |
| 切块后视口内色条颜色不刷新 | 统一走 `refreshBlockStripeColors()` 遍历已渲染 DOM，切块后立即调用 |
| postcss 构建受 nanoid 版本影响 | 用 3.3.18（CJS 兼容、3.x 修复版），node 实测 `require('postcss')` 成功、解析到 nanoid@3.3.18/index.cjs |
| 页签滚动测量不准确 | `nextTick` 后测量，确保 DOM 更新完成 |

## 跨仓影响

无。全部改动在 `openlibing-web`（前端）仓内，后端接口（`fileContent` / `duplicationBlockDetail`）与数据契约未变，仅前端渲染逻辑优化。

## 关联

- 业务 Issue：[https://gitcode.com/openlibing/openlibing-coderepo/issues/96](https://gitcode.com/openlibing/openlibing-coderepo/issues/96)（跨仓）
- 业务 PR：[openlibing/openlibing-web#714](https://gitcode.com/openlibing/openlibing-web/merge_requests/714)
