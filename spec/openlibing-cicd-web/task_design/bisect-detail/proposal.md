# Proposal: PR 问题二分定位功能（BisectDetail）

## 需求背景

当 Nightly 等通过 Branch 启动的流水线执行失败时，当前缺乏自动定位引入问题的 PR 的能力。用户需要手动排查时间窗口内合入的 PR，逐个触发流水线运行验证，效率低下且容易遗漏。需要提供二分定位功能，自动基于失败时间窗口内的 PR 列表，以二分法运行流水线，快速定位引入问题的 PR。

## 需求描述

1. 在流水线详情页新增"PR问题定位"入口，点击打开分析进度弹窗
2. 分析进度弹窗展示任务状态、问题 PR 链接、分析时长、时间窗口信息和进度列表表格
3. 进度列表展示每条 PR 的编号、标题、合入时间、分析流水线和分析结果
4. 支持手动触发分析（POST 请求）、刷新进度、重置失败/超时记录
5. 在流水线编辑弹窗新增"辅助功能"Tab，包含 PR 问题快速定位配置
6. 配置项包括开关、PR 筛选策略（当天零点 / 当前失败时间）和代码源选择

## 验收标准

- [ ] 流水线详情页页头子标题栏展示"PR问题定位：查看详情"入口（已执行流水线）
- [ ] 点击入口打开 BisectDetail 对话框，自动加载分析数据
- [ ] 对话框正确展示分析任务状态（进行中/成功/失败）、问题 PR 链接、分析时长
- [ ] 时间窗口信息正确展示（最近成功节点到失败节点之间的 PR 数量）
- [ ] 进度列表表格正确展示每条 PR 信息，PR 编号和标题可点击跳转
- [ ] 分析流水线列可点击跳转到流水线详情页
- [ ] 分析结果列展示正确状态图标和描述
- [ ] 重置按钮仅在 QUEUED/QUEUED_TIME_OUT/FAILED/RUN_FAILED 状态下可用
- [ ] 手动触发分析弹出确认框，确认后 POST 请求启动分析
- [ ] 流水线编辑弹窗"辅助功能"Tab 展示二分定位配置
- [ ] 批量编辑模式下隐藏"辅助功能"Tab
- [ ] 开关开启后，代码源下拉必填，仅 gitcode 类型可选
- [ ] PR 筛选策略支持 START_OF_DAY 和 START_OF_PIPELINE 两个选项
- [ ] 保存时 isBisectOn、bisectRepo、bisectStrategy 正确提交到后端

## 影响范围

- 前端：`openlibing-cicd-web` 仓
  - 新增：`BisectDetail.vue`、`BisectDetailLabel.vue`、`pipelineBisectDebug.vue`
  - 修改：`api.ts`、`url.ts`、`Detail.vue`、`pipelineEditDialog.vue`
- 后端：无变更（API 已有）

## 关联

- 业务仓 PR：openlibing/openlibing-cicd-web#70
- 目标分支：`release_20260630_iter2`
