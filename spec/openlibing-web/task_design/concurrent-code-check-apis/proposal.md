# 并发化代码门禁与版本检查列表及静态报告接口请求

## 需求背景

代码门禁（GatingCheck）和版本检查（StaticCheck）页面在切换项目时，需要先调用 `getSelect` 接口获取仓库/分支下拉选项，拿到响应后清空分支/仓库条件，再触发列表查询 `getIncCheckList`/`getCheckList`。这种方式将列表查询完全串行依赖在下拉选项接口之后，导致首屏加载延迟。

代码检查看板（StaticDetail）fulltask 模式下的 `getTrend`（趋势图）与 `getReport`（严重等级/敏感词报告）也是串行执行，且 `getTrend` 被重复调用了两次（flag='1' 和 flag='2' 各调一次），而 `getTrend` 接口本身不区分 flag，存在不必要的重复请求。

## 功能描述

将上述 3 个页面的接口调用从串行改为并发，减少首屏等待时间。

- **GatingCheck**：`handleSelectPro` 中 `getIncCheckList` 与 `getSelect` 并发执行
- **StaticCheck**：`handleSelectPro` 中 `getCheckList` 与 `getSelect` 并发执行
- **StaticDetail**：fulltask 模式下 `getReport('1')`、`getReport('2')`、`fillTrend()` 三者并发；`getTrend` 只发一次请求

同时修复 immediate watch 首次触发时子组件 refs 未挂载导致列表查询丢失的问题。

## 验收标准

- [ ] GatingCheck 切换项目时列表立即刷新，不再等待下拉选项接口返回
- [ ] StaticCheck 切换项目时列表立即刷新，不再等待下拉选项接口返回
- [ ] StaticDetail fulltask 首屏三个接口并发加载，`getTrend` 只发一次请求
- [ ] 首次进入页面（immediate watch）时列表能正常加载
- [ ] 下拉选项（仓库/分支）在各接口返回后正常填充
- [ ] 任一下拉接口失败时不影响主列表展示

## 影响范围

| 文件                                                                        | 仓库           |
| --------------------------------------------------------------------------- | -------------- |
| `apps/web-openlibing/src/views/CodeCheckPages/GatingCheck/GatingCheck.vue`  | openlibing-web |
| `apps/web-openlibing/src/views/CodeCheckDashboard/StaticDetail.vue`         | openlibing-web |
| `apps/web-openlibing/src/views/CodeCheckPages/VersionCheck/StaticCheck.vue` | openlibing-web |
