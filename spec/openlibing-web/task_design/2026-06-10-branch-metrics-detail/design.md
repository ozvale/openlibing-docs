# 2026-06-10 分支管理代码质量指标详情技术设计

## 1. 技术方案

### 1.1 整体架构

指标详情功能采用两层组件结构：

- **branches.vue**：持有 el-dialog 外壳，控制弹窗开关和标题
- **MetricsDetailDialog.vue**：纯内容组件，负责数据请求、表格渲染、排序/搜索/分页

在 index.vue 中，指标详情作为分支管理的下一级视图，通过面包屑导航切换。

### 1.2 数据流

```
branches.vue (点击指标列)
  → openMetricsDetail(col, row)
    → 设置 metricsDialogProps (repoId, repoName, pipelineRunId, metricType, branchName)
    → 打开 el-dialog
    → MetricsDetailDialog.init() 触发 fetchData

index.vue (URL 参数跳转)
  → autoGoBranch(repoId)
    → queryRepo 查询仓库
    → goBranch(repo) + goMetricsDetail(params)
    → 显示指标详情视图
```

### 1.3 metricType 与列配置映射

| metricType | 标题 | 列配置 | 可排序列 |
|---|---|---|---|
| 0 | 代码规模详情 | 文件名称 + 行数 | 行数 |
| 1 | 平均代码行数详情 | 文件名称 + 函数名 + 函数行数 + 开始行 + 结束行 | 函数行数、开始行、结束行 |
| 2 | 平均圈复杂度详情 | 文件名称 + 平均圈复杂度 | 平均圈复杂度 |
| 3 | 总代码重复率详情 | 文件名称 + 重复率 + 重复行数 | 重复率、重复行数 |
| 4 | 总文件重复率详情 | 文件名称 + 重复文件 | 无 |

### 1.4 合并单元格方案（metricType=4）

`duplicatedFiles` 字段为数组，需要展平为多行并合并其他列单元格：

1. `flattenedTableData` computed：遍历原始数据，将 `duplicatedFiles` 数组展开为多行，每行添加 `_mergeIndex`、`_mergeCount`、`_originalIndex` 元数据
2. `mergeMethod`：对非 `duplicatedFile` 列，第一行 rowspan=_mergeCount，后续行 rowspan=0
3. `indexMethod`：metricType=4 时使用 `_originalIndex` 保持序号按原始行连续

### 1.5 接口调用

```
POST /metrics/code/file-detail
请求参数: { repoId, branchName, pipelineRunId, metricType, fileName, sortByField, sort, pageNum, pageSize }
响应数据: { fileDetails: [], total, runNumber, pipelineLink }
```

### 1.6 URL 参数跳转

路由 query 参数：`?repoId=xxx&branchName=xxx&pipelineRunId=xxx&metricType=0`

- 在 `projectInfo` watch 中检测 `route.query.repoId`，存在时调用 `autoGoBranch`
- `autoGoBranch` 查询仓库后自动打开分支管理 + 指标详情
- 返回分支管理时通过 `router.replace({ query: {} })` 清除参数

## 2. 变更详情

### 2.1 branches.vue 变更

| 变更类型 | 位置 | 说明 |
|---------|------|------|
| 新增 | `allColumns` | 5 个 metrics 列添加 `metricType` 属性（0-4） |
| 新增 | 模板 metrics 列 | 有值时渲染为 `.metrics-link` 可点击链接，点击调用 `openMetricsDetail` |
| 新增 | `showMetricsDialog`、`metricsDialogProps` | 弹窗状态和传参 |
| 新增 | `metricsTitleMap`、`metricsDialogTitle` | 弹窗标题动态映射 |
| 新增 | el-dialog + MetricsDetailDialog | 弹窗外壳 + 内容组件 |
| 新增 | `.metrics-link` 样式 | 蓝色可点击链接样式 |

### 2.2 MetricsDetailDialog.vue 变更

| 变更类型 | 位置 | 说明 |
|---------|------|------|
| 新增 | 整个文件 | 指标详情内容组件 |
| 新增 | `metricsColumnMap` | 按 metricType 映射列配置 |
| 新增 | `flattenedTableData` | metricType=4 时展平 duplicatedFiles 数组 |
| 新增 | `mergeMethod` | 合并单元格逻辑 |
| 新增 | `indexMethod` | 序号列在合并场景下按原始行号显示 |
| 新增 | `handleSortChange` | 自定义排序，传递 sortByField + sort 参数 |
| 新增 | 文件名称列筛选 | el-popover + el-input 模糊搜索 |
| 新增 | `goToNotice` | 流水线链接安全跳转 |
| 新增 | `defineExpose({ init })` | 暴露初始化方法供父组件调用 |

### 2.3 index.vue 变更

| 变更类型 | 位置 | 说明 |
|---------|------|------|
| 新增 | `showMetricsDetail`、`metricsDetailProps` | 指标详情视图状态 |
| 新增 | `goMetricsDetail`、`backToBranch` | 视图切换函数 |
| 新增 | `autoGoBranch` | URL 参数自动跳转 |
| 新增 | 面包屑三级导航 | 仓库管理 / 分支管理 / 指标详情 |
| 新增 | 条件渲染 | showMetricsDetail 时显示 MetricsDetailDialog |
| 修改 | `branchBack` | 返回时同时关闭指标详情 |
| 修改 | 返回箭头 | 指标详情时返回分支管理，分支管理时返回仓库列表 |

## 3. 影响范围

### 3.1 功能影响

- 新增指标详情查看能力，不影响原有分支列表功能
- URL 参数跳转仅在 `route.query.repoId` 存在时触发
- 返回分支管理时清除 URL 参数，避免刷新重复触发

### 3.2 测试建议

- 验证 5 种 metricType 的列配置和标题是否正确
- 验证排序功能（升序/降序/取消排序）
- 验证文件名称模糊搜索
- 验证 metricType=4 的合并单元格和序号显示
- 验证 URL 参数跳转和参数清除
- 验证流水线链接跳转
- 验证原有分支管理功能不受影响
