# pipeline-run 列表接口增加 merge_id 展示与筛选 — 实现任务

## 进度: 4/4 complete

- [x] Task 1: PipelineRunReqDTO 增加 `mergeId` 筛选字段
- [x] Task 2: PipelineRunInfoMapper 增加 `selectByPipelineRunIds` 和 `selectPipelineRunIdsByPrId` 方法及 SQL
- [x] Task 3: PipelineServiceImpl.getPipelineRunList 中 enrich merge_id 到响应 buildParams.mergeId 字段
- [x] Task 4: PipelineServiceImpl.getPipelineRunList 中支持按 mergeId 参数筛选（应用层过滤）
