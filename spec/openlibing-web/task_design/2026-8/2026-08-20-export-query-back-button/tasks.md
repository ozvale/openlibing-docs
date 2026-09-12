## 1. stores/app.ts 状态与生命周期

- [x] 1.1 新增 `scaExportFrom` 状态（导出来源上下文：routeName、isDetail、detail、projectId）
- [x] 1.2 新增 `scaPendingRestore` 状态（返回后待恢复详情快照：routeName、isDetail、detail）
- [x] 1.3 新增 `setScaExportFrom` / `clearScaExportFrom` / `setScaPendingRestore` / `clearScaPendingRestore` 方法
- [x] 1.4 注册 `router.afterEach` 钩子：离开 `queryExportRecord` 时清空 `scaExportFrom`
- [x] 1.5 `projectInfo` watcher：projectId 变化时清空 `scaExportFrom` 与 `scaPendingRestore`

## 2. queryExportRecord/index.vue 返回按钮与样式

- [x] 2.1 新增「返回」按钮，位于列表内容上方左对齐（`back-bar` 容器）
- [x] 2.2 新增 `inDialog` prop（默认 `false`），`isPageMode` computed 返回 `!this.inDialog`
- [x] 2.3 模板 `v-if="isPageMode"` 控制返回按钮栏渲染
- [x] 2.4 `.moudle-content` 动态绑定 `is-page-mode` class，仅 `is-page-mode` 时设置白色背景与 20px 内边距
- [x] 2.5 实现 `handleBack()` 方法：
  - 有效来源（routeName 为 componentAnalysis/PRComponentAnalysis、projectId 匹配当前项目）→ 迁移详情快照到 `scaPendingRestore`，`router.push` 到来源路由
  - 无效来源 → 清空 `scaExportFrom`，`router.push` 到 `componentAnalysis`
- [x] 2.6 返回按钮样式：icon+文字 4px 间距，默认色 #191919，hover 色 #409eff

## 3. exportTipComponent.vue 来源上下文捕获

- [x] 3.1 `inject` 父级提供的导出上下文 getter
- [x] 3.2 `jumpToQueryRec()` 调用 getter 获取快照，写入 `scaExportFrom`（含 routeName、isDetail、detail、projectId）
- [x] 3.3 跳转 `queryExportRecord` 前完成 `scaExportFrom` 设置

## 4. componentAnalysis/index.vue 版本扫描上下文

- [x] 4.1 `provide` 暴露导出上下文 getter（返回 routeName、isDetail、detail 快照）
- [x] 4.2 `mounted` 消费 `scaPendingRestore`，若需恢复详情则调用 `restoreScaDetail`
- [x] 4.3 实现 `restoreScaDetail` 方法：根据快照恢复版本扫描详情状态
- [x] 4.4 消费后调用 `clearScaPendingRestore`

## 5. PRComponentAnalysis/index.vue PR 扫描路由级恢复

- [x] 5.1 `created` 检测 `scaPendingRestore`，若需恢复 PR 详情则预置 `isDetail = true`（避免列表→详情闪烁）
- [x] 5.2 `mounted` 兜底清理 `scaPendingRestore`（防止子组件未消费时残留）

## 6. openSourceCompliance/index.vue PR 扫描详情恢复

- [x] 6.1 `provide` 暴露导出上下文 getter（返回 routeName、isDetail、detail 快照）
- [x] 6.2 `mounted` 消费 `scaPendingRestore`，若需恢复 PR 详情则调用 `getDetail`
- [x] 6.3 `getDetail` 中记录 `lastPrDetail`（最近一次进入详情的参数）
- [x] 6.4 `getDetail` 参数顺序调整：先设 `checkedProp`，再设 `chooseGitObject`（避免 watch 触发时 chooseProp 为旧值）
- [x] 6.5 消费后调用 `clearScaPendingRestore`
- [x] 6.6 修复重复 `mounted()` 钩子问题（删除覆盖消费逻辑的空 `mounted() {}`）

## 7. layout/index.vue 弹窗内嵌区分

- [x] 7.1 弹窗内 `<queryExportRecord :in-dialog="true" />`，确保弹窗内不显示返回按钮与白色背景样式

## 8. 手动验收

- [ ] 8.1 从版本扫描列表点击导出 → 查看导出记录 → 点击返回按钮 → 回到版本扫描列表
- [ ] 8.2 从版本扫描详情点击导出 → 查看导出记录 → 点击返回按钮 → 回到版本扫描详情，详情参数（git 仓库、扫描状态等）恢复正确
- [ ] 8.3 从 PR 扫描列表点击导出 → 查看导出记录 → 点击返回按钮 → 回到 PR 扫描列表
- [ ] 8.4 从 PR 扫描详情点击导出 → 查看导出记录 → 点击返回按钮 → 回到 PR 扫描详情，PR 列表数据正常加载（无空数据问题）
- [ ] 8.5 在导出查询页切换项目 → 点击返回按钮 → 回到合法合规默认列表
- [ ] 8.6 在导出查询页刷新浏览器 → 点击返回按钮 → 回到合法合规默认列表
- [ ] 8.7 在导出查询页切换到其他菜单 → 再回到导出查询页 → 点击返回按钮 → 回到合法合规默认列表
- [ ] 8.8 在任意页面（包括导出查询页本身）通过弹窗打开导出记录查询 → 弹窗内不显示返回按钮，样式与原有弹窗一致
- [ ] 8.9 点击合法合规左侧导航栏 → 直接打开合法合规列表
- [ ] 8.10 返回按钮样式：icon 与「返回」文字间距 4px，默认色 #191919，hover 色 #409eff
- [ ] 8.11 独立路由页面 `.moudle-content` 白色背景与 20px 内边距生效，弹窗内嵌样式不变
- [ ] 8.12 从 PR 扫描详情返回后，再切换到其他菜单，再回到 PR 扫描菜单 → 应显示列表而非详情（`scaPendingRestore` 已清理）
