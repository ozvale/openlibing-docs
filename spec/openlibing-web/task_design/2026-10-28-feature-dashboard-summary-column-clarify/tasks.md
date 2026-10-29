# 2026-10-28 特性看板汇总列命名澄清与详情入口调整 - 任务清单

## 实现步骤

- [x] `StatusMatrix.vue`：矩阵最后一列 `label` 与表头文案"全部"→"汇总"
- [x] `StatusMatrix.vue`：新增列头说明图标 + tooltip（后按反馈移除，列头恢复纯文字）
- [x] `StatusMatrix.vue`：单元格 tooltip 改为"汇总视角 · 特性 · 状态"（后按反馈移除）
- [x] `StatusMatrix.vue`："已接入"单元格对勾状态圈替换为"详情"链接按钮，点击复用 `onCellClick` 打开汇总详情抽屉
- [x] `StatusMatrix.vue`：移除列头图标（`InfoFilled` 导入与 `__hint` 样式一并清理）
- [x] `StatusCell.vue`：`el-tooltip` 增加 `:disabled="!content"`，`content` 为空时不再弹出气泡
- [x] `DetailDrawer.vue`：社区下拉选项"全部"→"汇总"
- [x] `constants.ts`：指标配置弹窗 5 处"全部列"文案及相邻注释改为"汇总列/「汇总」"
- [x] `index.vue`："全部列"注释同步更名
- [x] 按用户规范分三次提交 commit（`5595d81b`/`eea755ca`/`a7b443e2`）

## 验证记录

| 场景                     | 结果                                  |
| ------------------------ | ------------------------------------- |
| 矩阵列头显示             | 纯文字"汇总"，无图标、无 tooltip      |
| 已接入单元格             | 显示"详情"按钮，点击打开汇总详情抽屉  |
| 插件明细子行（已接入）   | 同样显示"详情"按钮，行为一致          |
| 未接入/不涉及单元格      | 保留灰色状态图标，悬停无 tooltip      |
| 详情抽屉社区下拉         | 显示"汇总"选项，切换单社区明细正常    |
| 指标配置弹窗提示         | "全部列"文案已统一为"汇总列/「汇总」" |
| 社区列状态图标与 tooltip | 不受影响                              |
| ESLint / 单元测试        | 无错误；56 个用例全部通过             |
| pre-commit 钩子          | prettier/ESLint/secrets 等全部通过    |
