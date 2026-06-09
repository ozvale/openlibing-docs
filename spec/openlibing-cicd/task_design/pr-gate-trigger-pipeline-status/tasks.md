# PR 合入门禁触发与 pipeline_status 回调 — 实现任务

## 进度: 12/12 complete

- [x] Task 1: 创建 CompileTriggerReqDTO（compile 接口请求 DTO）
- [x] Task 2: CrossRegionController 新增 POST /compile 和 PUT /pipeline-status 端点
- [x] Task 3: CrossRegionService 接口声明 compileTrigger 和 updatePipelineStatus
- [x] Task 4: CrossRegionServiceImpl 实现 compileTrigger（MQS 发送 + pipeline 记录 + 标签）
- [x] Task 5: CrossRegionServiceImpl 实现 updatePipelineStatus（JSON 解析 + pipeline_status 提取 + 状态更新，不打标签）
- [x] Task 6: CrossRegionStartReqDTO 新增 actionType、executeSchemeName 字段
- [x] Task 7: BlueYellowPipeline Entity 新增对应字段
- [x] Task 8: BlueYellowPipelineServiceImpl MQS payload 加入两个新字段
- [x] Task 9: BlueYellowPipelineMapper.xml resultMap + queryByBlueRecord 补充映射
- [x] Task 10: db.changelog.xml 数据库迁移（扩 parameter 列 + 加两个字段）
- [x] Task 11: CrossRegionServiceImplTest 新增 7 个测试方法
- [x] Task 12: 64 测试全部通过（3 个 @Disabled 需 Spring 集成环境）
