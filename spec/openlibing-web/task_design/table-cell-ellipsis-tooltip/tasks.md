# 任务清单

## Phase 1: 需求确认

- [x] 理解需求：表格超长文本单行省略 + tooltip 悬停显示完整内容，替代文字换行
- [x] 关联 Issue：openlibing/openlibing-web#283

## Phase 2: 设计与计划

- [x] 确定分层方案：myTable.vue 全局组件统一处理 time/link/text/header 四类场景；局部表格页面内同手法处理
- [x] 梳理 CSS 关键点：min-width: 0（flex 收缩）、display: block !important（覆盖 inline-flex 特异性）、图标 flex: none、popper 全局限宽
- [x] 创建 spec 文档（proposal.md、design.md、tasks.md）

## Phase 3: 编码实现

- [x] myTable.vue：四类 ellipsis 类 + el-tooltip；时间列禁用原生 show-overflow-tooltip
- [x] filterDropdown.vue：筛选下拉 label 省略 + title
- [x] cve/columns.js：相关列追加 `showToolTip: true`
- [x] 账号管理、反馈管理、检测中心页面处理
- [x] 发布管理（制品列表）、合法合规（规则表）处理
- [x] 工具管理、0-day 漏洞列表处理
- [x] 用户管理、角色管理处理（含 formatCreateTime 抽取）
- [x] 机器管理（账号/接口）处理（含 url-tooltip-popper 限宽）
- [x] 管理中心（公告板、用户看板、操作日志）处理
- [x] 提交代码到本地分支 `feat-table-tooltip-ellipsis-rel`

## Phase 4: PR 提交

- [x] 推送到 fork 仓 `dyy-1/openlibing-web_2708:feat-table-tooltip-ellipsis-rel`
- [x] 创建 [PR #797](https://gitcode.com/openlibing/openlibing-web/pull/797) 到 `openlibing/openlibing-web:release_20260923`
- [x] 补打 `ai-assisted` 标签，CI 通过，已合入（2026-09-22）

## Phase 5: 归档

- [x] 创建 spec 文档并提交到 openlibing-docs
