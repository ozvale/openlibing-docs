## Why

合法合规菜单下存在多处导出功能入口（版本扫描列表/详情、PR 扫描列表/详情），用户点击导出后会弹出 `exportTipComponent` 提示「Excel导出提交成功」，弹窗内提供「查看导出记录」按钮跳转到导出查询页 `queryExportRecord` 查看导出状态与下载文件。

当前导出查询页**缺少返回路径**：用户查看完导出记录后只能通过左侧菜单或浏览器后退返回，无法一键回到刚才导出的来源页面（列表或详情）。尤其当用户从 PR 详情进入导出查询页后，希望返回的是 PR 详情而非列表，现有交互无法满足。

此外，由于合法合规列表与详情共用 `componentAnalysis` / `PRComponentAnalysis` 路由（通过组件内 `isDetail` 状态切换列表/详情视图），返回到详情需要恢复进入详情时的上下文参数（如选中的 git 仓库、PR 通过/未通过状态等），现有机制未保存此上下文。

## What Changes

- `queryExportRecord/index.vue` 新增「返回」按钮，位于列表内容上方左对齐
  - 点击返回到上一次点击导出的来源页面（版本扫描列表/版本扫描详情/PR扫描列表/PR扫描详情）
  - 来源页面是详情时，恢复进入详情时的上下文参数（git 仓库、PR 状态等）
- `queryExportRecord/index.vue` 新增 `inDialog` prop，仅独立路由页面渲染时显示返回按钮，弹窗内嵌时不显示
- `queryExportRecord/index.vue` 独立路由页面增加白色背景与 20px 内边距
- `stores/app.ts` 新增 `scaExportFrom`（导出来源上下文）与 `scaPendingRestore`（返回后待恢复详情快照）两个内存态状态
- `stores/app.ts` 注册 `router.afterEach` 钩子：离开导出查询页时清空 `scaExportFrom`，确保从其他菜单再回到导出查询页时不会误用旧来源
- `stores/app.ts` 项目切换时清理 `scaExportFrom` 与 `scaPendingRestore`
- `exportTipComponent.vue` 通过 `inject` 捕获父级提供的导出上下文（路由名、是否详情、详情参数），在跳转导出查询页前写入 `scaExportFrom`
- `componentAnalysis/index.vue` 与 `PRComponentAnalysis/components/openSourceCompliance/index.vue` 通过 `provide` 暴露当前页面上下文 getter，并在 `mounted` 消费 `scaPendingRestore` 恢复详情状态
- `PRComponentAnalysis/index.vue` 在 `created` 预置 `isDetail`（避免列表→详情闪烁），`mounted` 兜底清理 `scaPendingRestore`

## Capabilities

### New Capabilities

- `export-query-back-navigation`: 导出查询页返回按钮能力，支持从导出查询页一键返回到上一次导出的来源页面（列表或详情），并在返回详情时恢复详情上下文参数；在切换项目、刷新浏览器、切换其他菜单后等无效来源场景下回退到合法合规默认列表

### Modified Capabilities

（无现有 openspec spec 需修改。本次为新增前端导航能力，不改变既有 spec 级行为契约。）

## Impact

- **前端文件**
  - `apps/web-openlibing/src/stores/app.ts` — 新增 `scaExportFrom` / `scaPendingRestore` 状态、getter/setter/clear 方法、`router.afterEach` 钩子、项目切换 watcher 清理
  - `apps/web-openlibing/src/views/sca/queryExportRecord/index.vue` — 新增返回按钮、`handleBack` 方法、`inDialog` prop、`isPageMode` computed、白色背景与内边距样式
  - `apps/web-openlibing/src/views/sca/component/exportTipComponent.vue` — `inject` 父级上下文、`jumpToQueryRec` 捕获来源写入 `scaExportFrom`
  - `apps/web-openlibing/src/views/sca/componentAnalysis/index.vue` — `provide` 上下文 getter、`mounted` 消费 `scaPendingRestore` 恢复详情、新增 `restoreScaDetail` 方法
  - `apps/web-openlibing/src/views/sca/PRComponentAnalysis/index.vue` — `created` 预置 `isDetail`、`mounted` 兜底清理 `scaPendingRestore`
  - `apps/web-openlibing/src/views/sca/PRComponentAnalysis/components/openSourceCompliance/index.vue` — `provide` 上下文 getter、`mounted` 消费 `scaPendingRestore`、`lastPrDetail` 捕获、`getDetail` 参数顺序调整
  - `apps/web-openlibing/src/views/sca/layout/index.vue` — 弹窗内 `<queryExportRecord :in-dialog="true" />`
- **路由** — 无新增路由，复用 `componentAnalysis` / `PRComponentAnalysis` / `queryExportRecord` 三个既有路由
- **后端 / API** — 无变更
- **状态管理** — `app` store 新增两个内存态字段，不持久化（刷新即丢失，符合「刷新后回退到默认列表」的产品约束）
- **tabbar** — 本次不修改 tabbar 持久化机制；已知遗留问题：从其他菜单刷新浏览器后点击 tabbar「合法合规」可能跳到导出查询页（因 sca 子路由 meta.title 相同导致 tab key 冲突），不在本次范围
