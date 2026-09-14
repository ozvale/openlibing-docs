# 重复代码抽屉优化（2026-08-19）— 实现任务

## 进度: 9/9 complete

- [x] 省略行命中块范围时，渲染左侧占位色条；occurrence 编辑器改用 segments 渲染并保留省略行（DuplicationCodeDrawer）— commit `a868ac6c`
- [x] 切换项目时清空分支筛选缓存 + 修复刷新后 autoGoBranch 不触发（index.vue，`oldValue?.projectId` 判断）— commit `a868ac6c`
- [x] occurrence 页签切换时自动滚动选中项到可视区域（页签条 ref + scrollActiveOccTabIntoView）— commit `ab8f5a34`
- [x] 大文件渲染优化：高亮改 StateField + 共享 ViewPlugin 增量更新、行→块映射预计算、行号 Map 化、色条 DOM 刷新 — commit `0daebf78`
- [x] 修复性能优化后块高亮背景色消失（补加 highlightField 到 extensions，vitest 复现验证）— commit `1080e355`
- [x] 分支筛选输入框回车确认（@keyup.enter，branches.vue）— commit `c72b7b03`
- [x] 重复块色条宽度 5px → 3px — commit `f374bc60`
- [x] 移除未使用的 nanoid 直接依赖（CVE-2026-67213 业务侧）— commit `561a0e6e`
- [x] postcss 传递依赖 nanoid 3.3.17 → 3.3.18（overrides 更新 + lock 同步 + CJS 兼容验证）— commit `2957dc87`

## 说明

- commit `a868ac6c` 同时包含 DuplicationCodeDrawer（省略行占位 + segments 渲染）与 index.vue（切项目缓存清空 + autoGoBranch 修复）两类改动，涉及两个组件/文件，已在任务清单中拆为第 1、2 项分别标注。
- 分支筛选回车确认独立于 `c72b7b03`（仅改动 branches.vue），与 `a868ac6c` 无关联。
- 依赖相关 commit（`561a0e6e`、`2957dc87`）已在业务 PR #714 之后追加推送，属同批交付。
