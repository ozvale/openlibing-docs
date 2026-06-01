# pipeline-run 列表接口增加 merge_id 展示与筛选

## 需求背景
当前 pipeline/pipeline-run/list 接口返回的流水线运行列表不包含 merge_id 字段，必须点进某条流水线历史记录的 detail 里才能看到 merge_id。前端需要在列表页直接展示并支持按 merge_id 筛选。

## 功能描述
1. 在 pipeline-run/list 接口响应中，每条记录的 `buildParams.mergeId` 字段会被填充（从本地 `pipeline_run_info` 表的 `pr_id` 字段获取）
2. 在 PipelineRunReqDTO 中增加 `mergeId` 可选筛选参数，支持按 MR/PR ID 筛选流水线运行记录

不做：
- 不修改华为云 API 调用逻辑
- 不修改 pipeline-run/detail 接口
- 不修改数据库表结构

## 验收标准
- [ ] pipeline-run/list 接口响应中每条记录包含 `buildParams.mergeId` 字段
- [ ] pipeline-run/list 接口支持通过 `mergeId` 参数筛选
- [ ] 不传 `mergeId` 时接口行为与变更前完全一致
- [ ] 现有测试全部通过

## 影响范围
- 后端：`openlibing-cicd` 仓（PipelineRunReqDTO、PipelineServiceImpl、PipelineRunInfoMapper）
- 前端：流水线运行列表页需新增 Merge ID 列和筛选输入框
