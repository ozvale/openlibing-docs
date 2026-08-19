# 重复代码抽屉优化（2026-08-19）— 实现任务

## 进度: 8/8 complete

- [x] 省略行命中块范围时，渲染左侧占位色条（DuplicationCodeDrawer）— commit `a868ac6c`
- [x] occurrence 页签切换时自动滚动选中项到可视区域（页签条 ref + scrollActiveOccTabIntoView）— commit `ab8f5a34`
- [x] 大文件渲染优化：高亮改 StateField + 共享 ViewPlugin 增量更新、行→块映射预计算、行号 Map 化、色条 DOM 刷新 — commit `0daebf78`
- [x] 修复性能优化后块高亮背景色消失（补加 highlightField 到 extensions，vitest 复现验证）— commit `1080e355`
- [x] 分支筛选输入框回车确认（@keyup.enter）— commit `c72b7b03`
- [x] 重复块色条宽度 5px → 3px — commit `f374bc60`
- [x] 移除未使用的 nanoid 直接依赖（CVE-2026-67213 业务侧）— commit `561a0e6e`
- [x] postcss 传递依赖 nanoid 3.3.17 → 3.3.18（overrides 更新 + lock 同步 + CJS 兼容验证）— commit `2957dc87`

## 说明

- 分支筛选回车与切项目缓存清空、autoGoBranch 修复包含在 commit `a868ac6c`（index.vue/branches.vue）。
- 依赖相关 commit 已在业务 PR #714 之后追加推送，属同批交付。
