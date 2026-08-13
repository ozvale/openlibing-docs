# 定时同步流水线信息需增加超时机制 - 实现步骤

## 任务清单

- [x] 1. SSLCipherSuiteUtil 新增 createHttpClientWithTimeout 方法
- [x] 2. HwCloudClient 新增 buildPipelineSslHttpsClientWithTimeout 方法
- [x] 3. HwCloudClient 新增 getDataResultFromHWCloudHttpApiWithTimeout 方法
- [x] 4. HwCloudClient OBJECT_MAPPER 复用优化（FAIL_ON_UNKNOWN_PROPERTIES=false）
- [x] 5. PipelineServiceImpl 新增 getCodeArtsPipelineClientByProjectIdWithTimeout 方法
- [x] 6. PipelineServiceImpl 新增 fetchPipelineDetailWithTimeout 方法
- [x] 7. PipelineServiceImpl.fetchPipelineDetailFromRemote 改用带超时版本
- [x] 8. ScheduleTaskImpl 注释掉 @Scheduled 注解，标注迁移
- [x] 9. XxlJobHandler 新增 syncPipelineConfigInfoHandler
- [ ] 10. xxl-job 管理后台新增 syncPipelineConfigInfoHandler 任务（需运维配合）
- [ ] 11. 重启服务释放卡死的 scheduling-1 线程（需运维配合）

## 关联 Issue

- openlibing/openlibing-cicd#180
