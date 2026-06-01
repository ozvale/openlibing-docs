# pipeline-run 列表接口增加 merge_id 展示与筛选 — 实现任务

## 进度: 2/2 complete

- [x] Task 1: PipelineRunReqDTO 增加 `mergeId` 筛选字段
- [x] Task 2: PipelineServiceImpl.getPipelineRunList 中支持按 mergeId 参数筛选（应用层过滤，直接比较华为云 API 响应中的 `buildParams.mergeId`）

### 已废弃的任务（实现过程中发现华为云 API 已自带 merge_id，无需数据库查询）
- ~~Task: PipelineRunInfoMapper 增加 `selectByPipelineRunIds` 和 `selectPipelineRunIdsByPrId` 方法及 SQL~~ — 已删除，不再需要
- ~~Task: PipelineServiceImpl.getPipelineRunList 中 enrich merge_id 到响应 buildParams.mergeId 字段~~ — 已删除，华为云 API 已自带
