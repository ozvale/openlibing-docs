# 2026-06-10 分支管理代码质量指标详情任务清单

## 开发任务

### branches.vue 修改

- [x] `allColumns` 中 5 个 metrics 列添加 `metricType` 属性（代码规模=0, 平均代码行数=1, 平均圈复杂度=2, 总代码重复率=3, 总文件重复率=4）
- [x] 引入 MetricsDetailDialog 组件
- [x] 添加 `showMetricsDialog`、`metricsDialogProps`、`metricsDialogRef` 响应式状态
- [x] 添加 `metricsTitleMap` 和 `metricsDialogTitle` computed
- [x] 添加 `openMetricsDetail` 函数，设置参数并打开弹窗
- [x] 添加 `onMetricsDialogOpen` 函数，调用 `metricsDialogRef.value?.init()`
- [x] 模板中 metrics 列渲染为可点击链接（`.metrics-link`）
- [x] 模板中添加 el-dialog + MetricsDetailDialog
- [x] 添加 `.metrics-link` 样式

### MetricsDetailDialog.vue 新建

- [x] 创建组件，定义 props（repoId, repoName, branchName, pipelineRunId, metricType）
- [x] 添加 `metricsColumnMap` 按 metricType 映射列配置
- [x] 提取 `filePathColumn` 公共常量
- [x] 添加 `flattenedTableData` computed 展平 duplicatedFiles 数组
- [x] 添加 `mergeMethod` 合并单元格逻辑
- [x] 添加 `indexMethod` 序号列处理
- [x] 添加 `handleSortChange` 排序处理
- [x] 添加文件名称列模糊搜索（el-popover + el-input）
- [x] 添加信息展示区（代码仓、分支、流水线链接）
- [x] 流水线链接使用 `goToNotice` 安全跳转
- [x] 添加分页器组件
- [x] `defineExpose({ init: handleOpen })` 暴露初始化方法
- [x] 添加序号列

### index.vue 修改

- [x] 引入 MetricsDetailDialog 组件和 `useRoute`、`nextTick`
- [x] 添加 `showMetricsDetail`、`metricsDetailRef`、`metricsDetailProps` 状态
- [x] 添加 `metricsTitleMap` 和 `metricsDetailTitle` computed
- [x] 添加 `goMetricsDetail` 函数
- [x] 添加 `backToBranch` 函数（返回时清除 URL 参数）
- [x] 修改 `branchBack` 函数（同时关闭指标详情）
- [x] 修改 `goBranch` 函数（关闭指标详情）
- [x] 添加 `autoGoBranch` 函数（URL 参数自动跳转）
- [x] 修改面包屑为三级导航（仓库管理 / 分支管理 / 指标详情）
- [x] 添加条件渲染（showMetricsDetail 时显示 MetricsDetailDialog）
- [x] 添加 `.dbc-link` 面包屑链接样式

## 验证任务

### 功能验证

- [ ] 点击 5 个指标值打开对应详情弹窗
- [ ] 弹窗标题按 metricType 动态显示
- [ ] 文件名称模糊搜索功能
- [ ] 数值列排序功能（升序/降序/取消）
- [ ] metricType=4 合并单元格展示正确
- [ ] 序号列在合并场景下按原始行号显示
- [ ] 流水线链接跳转正确
- [ ] URL 参数自动跳转指标详情
- [ ] 返回分支管理时 URL 参数已清除
- [ ] 原有分支管理功能不受影响

### Code Review

- [ ] Reviewer 检查代码变更
- [ ] 解决 Review 反馈（如有）
- [ ] 获得 Approval
