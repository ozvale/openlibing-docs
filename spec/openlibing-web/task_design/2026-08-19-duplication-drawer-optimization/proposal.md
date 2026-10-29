# 重复代码抽屉优化（2026-08-19）

## 需求背景

在 `duplicate-code-metrics-enhance`（重复代码抽屉 DuplicationCodeDrawer）上线后的自测与使用过程中，发现以下问题：

1. **省略行缺少占位色条**：高亮范围包含省略行（`.dup-ellipsis-line`）时，左侧占位条（stripe）没有跟随高亮，视觉上高亮范围不连续。
2. **occurrence 页签无法自动滚动**：occurrence 数量较多时，页签条出现横向滚动条，切换上一个/下一个时选中页签可能被挤出可视区域，需要手动拖动滚动条。
3. **大文件渲染卡顿**：文件行数较多、重复块较多时，切换块/滚动明显卡顿。根因是每次切块都 `StateEffect.reconfigure` 重建整棵编辑器扩展树，导致装饰计算随行数线性恶化。
4. **性能优化引入回归**：将高亮改为 StateField 方案时，漏加 `highlightField`（StateField）到 extensions，导致插件崩溃、块高亮背景色消失（CodeMirror 仅打印 console 错误，不中断其它功能，表现隐蔽）。
5. **分支筛选缺少回车确认**：筛选弹层需点击"确定"按钮，键盘操作不友好。
6. **切换项目时分支筛选缓存残留**：切换项目回到代码仓管理页时，分支搜索缓存（内存 ref）未清空。
7. **刷新后 autoGoBranch 不触发**：watch 首次触发时 `oldValue` 为空对象（truthy），`!oldValue` 恒为 false，刷新页面后无法自动跳转到仓库分支页。
8. **色条宽度偏宽**：重叠块色条宽度 5px 与间隔 3px 不一致，视觉偏粗。
9. **依赖安全**：nanoid 3.3.17 被安全扫描标记 CVE-2026-67213（HIGH）。

## 功能描述

### 重复代码抽屉（DuplicationCodeDrawer）

- 省略行命中块范围时，左侧色条占位也跟随高亮渲染。
- occurrence 页签切换（上/下一个或点击页签）时，自动滚动页签条，将选中页签滚入可视区域。
- 大文件渲染优化：高亮改为 StateField + 共享 ViewPlugin 增量更新，行→块映射预计算，色条颜色 DOM 级刷新。
- 修复性能优化引入的高亮丢失回归（补加 highlightField 到 extensions）。
- 重复块色条宽度由 5px 收窄至 3px（与间隔一致）。

### 分支管理（branches / index）

- 分支筛选输入框绑定 `keyup.enter`，回车即触发"确定"。
- 切换项目时清空分支筛选缓存 `branchSearchCache`。
- 修复刷新后 autoGoBranch 不触发：`!oldValue` 改为 `!oldValue?.projectId` 判断。

### 依赖安全

- 移除未使用的 nanoid 直接依赖（业务代码无引用）。
- postcss 的 nanoid 传递依赖由 3.3.17 升级到 3.3.18（3.x 分支 CVE-2026-67213 修复版，CJS 兼容约束下最新）。

## 验收标准

- [ ] 高亮范围包含省略行时，省略行左侧也显示占位色条
- [ ] occurrence 页签有横向滚动条时，切换自动滚动选中项到可视区域
- [ ] 大文件（数千行 + 多块）下切换块、滚动流畅，无明显卡顿
- [ ] 块高亮背景色（黄色/当前块深黄/省略行灰色）正常显示，无丢失
- [ ] 重复块色条宽度为 3px，与间隔一致
- [ ] 分支筛选弹层输入框按回车触发"确定"
- [ ] 切换项目后重新进入分支页，搜索框为空（缓存已清空）
- [ ] 刷新代码仓管理页后自动跳转到仓库分支页
- [ ] 依赖树中无业务直接引用 nanoid，postcss 传递依赖为 nanoid@3.3.18（CJS 兼容、含 67213 修复）
- [ ] 构建通过

## 影响范围

| 文件                                                                   | 仓库           | 变更类型 |
| ---------------------------------------------------------------------- | -------------- | -------- |
| `apps/web-openlibing/src/views/Repos/dialog/DuplicationCodeDrawer.vue` | openlibing-web | 修改     |
| `apps/web-openlibing/src/views/Repos/branches.vue`                     | openlibing-web | 修改     |
| `apps/web-openlibing/src/views/Repos/index.vue`                        | openlibing-web | 修改     |
| `apps/web-openlibing/package.json`                                     | openlibing-web | 修改     |
| `pnpm-workspace.yaml`                                                  | openlibing-web | 修改     |
| `pnpm-lock.yaml`                                                       | openlibing-web | 修改     |
