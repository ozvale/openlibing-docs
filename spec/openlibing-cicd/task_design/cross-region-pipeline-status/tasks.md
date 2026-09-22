# cross-region-pipeline-status — 实现任务

## 进度: 0/8 complete

- [ ] Task 1: 新增 `dto/cross_region/ExternalPipelineInfoReqDTO.java`：owner（`@NotNull`）、repo（`@NotNull`）、platform（`@NotNull`）、prNumber（`@NotNull Integer`）
- [ ] Task 2: 新增 `vo/YellowPipelineStatusVO.java`：status、pipelineStatus、yellowUrl、startTime、endTime、failReason、duration（implements Serializable）
- [ ] Task 3: 修改 `mapper/YelloRegionPipelineMapper.java` + `mapper/YellowRegionPipelineMapper.xml`：新增 `queryLatestPipelineByPlatform` 四维联合查询（orgName/repoName/number/platform），按 start_time DESC LIMIT 1
- [ ] Task 4: 修改 `service/CrossRegionService.java` + `service/impl/CrossRegionServiceImpl.java`：新增 `getPipelineStatus` 方法，实现查询→VO组装→耗时计算
- [ ] Task 5: 修改 `controller/CrossRegionController.java`：新增 `POST /pipelineInfo` 端点
- [ ] Task 6: 修改 `enums/YellowPipelineStatusEnum.java`：新增 `ALREADY_RUNNING("ALREADY_RUNNING", "已有流水线在运行中，当前实例启动失败", "A pipeline is already running, current instance failed to start")`
- [ ] Task 7: 修改 `enums/PipelineStartErrorEnums.java`：`CONCURRENCY_LIMIT` 关键词从 "最大并发" 改为 "排队"；修改 `controller/PipelineControllerV2.java`：`getPipelineRunSummary` 标记 `@Deprecated` 并添加 `LOGGER.warn`；修改 `start.sh`：新增 `-Dapollo.cache.file.enable=false`
- [ ] Task 8: 编译验证 + 全量测试通过

## 验证方式
- Phase 1：编译通过（`mvn compile -pl . -am`）
- Phase 2：调用 `POST /pipelineInfo` 验证返回正确状态 VO
- Phase 3：全量测试通过

## 生成前约束检查
- [x] 只修改 `openlibing-cicd` 业务仓
- [x] 遵循既有代码风格（华为版权头、Javadoc、SLF4J 日志、MyBatis XML 风格）
- [x] 避免无关重构、无关格式化
- [x] 无硬编码凭证、敏感信息
