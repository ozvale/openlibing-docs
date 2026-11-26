# 资源运营看板能力增强 — 实现任务

## 进度：16/16 complete

- [x] Task 1：为现有 NPU 切片任务下钻增加 `slotGranularity=HOUR`，同步任务与申请卡数 SQL，并补充小时窗口测试。
- [x] Task 2：为 `ops-pipeline-run-detail` 增加 `repoUrl`，预聚合仓库关系并补充字段透传测试。
- [x] Task 3：为 `nightly-dashboard` 的 ResultMap、Model、Response 和 SQL CTE 增加 `repoUrl`，补充映射测试。
- [x] Task 4：统一 `run-analysis` 两类服务器列表的资源池/IP 排序，补充乱序和空池名测试。
- [x] Task 5：在现有 run 级排队样本聚合中增加 `prAvgQueueMinutes`，完成 DTO、SQL、rounding 和测试。
- [x] Task 6：运行相关单元测试与 Maven 编译，检查变更范围并交付用户自测；不提交代码。
- [x] Task 7：为 `engineeringScope=true/false/缺省` 增加动态 SQL 测试，先确认新增断言失败。
- [x] Task 8：新增请求参数，在项目列表/count 和 PR 排队、NPU 聚合中实现同口径运营仓过滤。
- [x] Task 9：运行相关测试与 Spotless，更新前端联调说明并检查变更范围；不提交代码。
- [x] Task 10：先更新动态 SQL 测试，再移除下钻请求的 `slotTime/slotGranularity` 及两处附加时间过滤。
- [x] Task 11：运行相关测试与 Spotless，更新前端联调说明并检查变更范围；不提交代码。
- [x] Task 12：先在 `ResourceEfficiencyServiceTest`、`ResourceEfficiencyMapperXmlTest` 增加每日排队 P90 趋势失败测试，覆盖全部/单流水线、缺日补零、PR/Nightly 和全量样本独立聚合。
- [x] Task 13：新增 `ops-pipeline-queue-p90` 请求、枚举和 ChartService，在 `ResourceEfficiencyMapper(.java/.xml)` 与 `ResourceEfficiencyService` 实现单次申请表扫描、run 级样本和多折线组装。
- [x] Task 14：先在 `ResourceOperationServiceTest` 增加跨机器任务卡时汇总测试，再扩展 `OpsPipelineRunAnalysisResp` 和 `ResourceOperationService`，复用 `queryRunSlots` 生成 `taskSummaries` 且保持旧返回不变。
- [x] Task 15：更新 `frontend-integration.md`，补充排队 P90 趋势和任务卡时汇总接口契约、示例及前端自测清单。
- [x] Task 16：运行相关单元测试、Maven 编译与 Spotless，检查只修改本轮指定文件和文档；不提交代码。
