# 并发化代码门禁与版本检查列表及静态报告接口请求 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: GatingCheck 切换项目时列表查询与 getSelect 并发 (commit 61de617f)
  - 将 `triggerFormInlineChange()` 提前到 `handleSelectPro` 入口，与 `getSelect` 并发
  - 去掉 `.then` 中的冗余清空（watch 的 resetFormInline 已处理）
  - 去掉 `.then` 中的重复 `triggerFormInlineChange` 调用
  - 新增 `triggerIncCheckList()` 辅助方法，immediate watch 首次触发时用 `$nextTick` 兜底 refs 未挂载
  - 移除废弃的 `goPath` 方法和 `Stamp` 图标引用

- [x] Task 2: StaticDetail fulltask 下 getTrend 与 getReport 并发 (commit 61de617f)
  - `getReport('1')`、`getReport('2')`、`fillTrend()` 用 `Promise.all` 并发执行
  - `getTrendRes(flag)` 重构为 `fillTrend()`，移除 flag 参数和对 getReport 的调用
  - `getTrend` 只发一次请求（原代码两个 flag 各发一次，浪费）
  - `fillTrend` 失败时静默，不影响主报告展示

- [x] Task 3: StaticCheck 切换项目时列表查询与 getSelect 并发 (commit c48495da)
  - 将 `triggerFormInlineChange()` 提前到 `handleSelectPro` 入口，与 `getSelect` 并发
  - 去掉 `try/catch` 包裹（无会抛异常的语句）
  - 去掉 `.then` 中的冗余清空和重复调用
  - 新增 `triggerStaticCheckList()` 辅助方法，immediate watch 首次触发时用 `$nextTick` 兜底 refs 未挂载

## 验证方式
- 人工验证：切换项目时观察列表是否立即刷新（不等下拉）；首次进入页面列表是否正常加载
- 人工验证：StaticDetail fulltask 首屏三个图表是否正常展示
- 无单元测试（纯页面交互逻辑，行为变化通过人工验证）