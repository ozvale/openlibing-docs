# pipeline-run 列表接口增加 merge_id 展示与筛选

## 需求背景
当前 pipeline/pipeline-run/list 接口返回的流水线运行列表中，华为云 API 已在 `buildParams.mergeId` 字段返回 merge_id，但前端未展示，且接口不支持按 merge_id 筛选。前端需要在列表页展示 merge_id 并支持按其筛选。

## 功能描述
1. 华为云 `listPipelineRuns` API 已在响应的 `buildParams.mergeId` 字段中返回 merge_id，无需额外查询数据库
2. 在 PipelineRunReqDTO 中增加 `mergeId` 可选筛选参数，在应用层对华为云 API 返回结果按 `buildParams.mergeId` 进行过滤

不做：
- 不修改华为云 API 调用逻辑
- 不修改 pipeline-run/detail 接口
- 不修改数据库表结构
- 不从 `pipeline_run_info` 表查询 merge_id（该表由定时任务同步，非实时）

## 验收标准
- [ ] pipeline-run/list 接口响应中每条记录包含 `buildParams.mergeId` 字段（华为云 API 自带）
- [ ] pipeline-run/list 接口支持通过 `mergeId` 参数筛选（应用层过滤）
- [ ] 不传 `mergeId` 时接口行为与变更前完全一致
- [ ] 现有测试全部通过

## 影响范围
- 后端：`openlibing-cicd` 仓（PipelineRunReqDTO、PipelineServiceImpl）
- 前端：流水线运行列表页需新增 Merge ID 列和筛选输入框
