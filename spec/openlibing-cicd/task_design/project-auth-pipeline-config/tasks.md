# project-auth-pipeline-config — 实现任务

## 进度: 6/6 complete

- [x] Task 1: 新增 `@ProjectAuth` 注解（`common/auth/ProjectAuth.java`），定义 `projectIdKey` 和 `userIdKey` 属性
- [x] Task 2: 扩展 `AuthInterceptor`，在 `preHandle` 中增加 `@ProjectAuth` 处理分支，始终校验 `hasPermission`，不判断仓库公开性
- [x] Task 3: 修改 `PipelineControllerV2`：`updatePipelineConfig`/`batchUpdatePipelineConfig`/`cancelPipelineQueue` 改用 `@ProjectAuth` 并新增 `userId` 参数；`updateDetailInfo` 标注 `@Deprecated`
- [x] Task 4: 修改 `PipelineDetailController`：`getPipelineJobTypes` 新增 `@ProjectAuth` + `projectId`/`userId` 参数
- [x] Task 5: `PipelineService` 和 `PipelineServiceImpl` 中 `updatePipelineDetailInfo` 标注 `@Deprecated`
- [x] Task 6: 补充测试用例（`AuthInterceptorTest` 4 个 `@ProjectAuth` 测试 + Controller 测试适配参数变更）
