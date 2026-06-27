# 模型调用审计日志 - Tasks

## Phase 1：基础设施与依赖

### Task 1: OBS SDK 依赖引入

- [x] 1.1 在 `pom.xml` 中添加 `esdk-obs-java-bundle:3.24.12` 依赖
- [x] 1.2 执行 `mvn clean compile`，验证无依赖冲突

### Task 2: ObsConfig 配置类

- [x] 2.1 新建 `com.workspace.common.config.ObsConfig`
- [x] 2.2 添加 `@ConditionalOnProperty(name = "maas.gateway.tracing-log.obs.enabled", havingValue = "true", matchIfMissing = false)`
- [x] 2.3 注入 `accessKeyId`、`secretAccessKey`、`endpoint`、`securityPart1`
- [x] 2.4 实现 `obsClient()` Bean：AK/SK 通过 `SecurityUtil.decrypt` 解密，配置 connectionTimeout=10000、socketTimeout=30000
- [x] 2.5 Bean 声明 `destroyMethod = "close"`

### Task 3: Apollo 配置项

- [ ] 3.1 在 Apollo 配置中心添加 OBS 配置项：`maas.gateway.tracing-log.obs.enabled`（默认 false）、`maas.gateway.tracing-log.obs.access-key-id`、`maas.gateway.tracing-log.obs.secret-access-key`、`maas.gateway.tracing-log.obs.endpoint`、`maas.gateway.tracing-log.obs.bucket-name`
- [ ] 3.2 AK/SK 在 Apollo 中以加密方式存储，代码中通过 `@Value` 注入后 `SecurityUtil.decrypt` 解密
- [ ] 3.3 可调参数（flush-interval-ms、batch-size、max-buffer-size）不写入 Apollo，通过 `@Value` 默认值提供（3000、200、5000），需要调整时再在 Apollo 中覆盖
- [ ] 3.4 不在 `application.yaml` 中添加 OBS 配置项，全部走 Apollo + `@Value` 默认值

## Phase 2：DB 侧回填能力

### Task 4: MaasTracingLogService 接口扩展

- [x] 4.1 在 `MaasTracingLogService` 接口新增 `void updateBodyStorageLocationBatch(List<String> requestIds, String location)`
- [x] 4.2 在 `MaasTracingLogServiceImpl` 实现该方法：空列表直接返回，否则调用 mapper

### Task 5: MaasTracingLogMapper 扩展

- [x] 5.1 在 `MaasTracingLogMapper.java` 新增 `void updateBodyStorageLocationBatch(@Param("requestIds") List<String> requestIds, @Param("location") String location)`
- [x] 5.2 在 `MaasTracingLogMapper.xml` 新增 `updateBodyStorageLocationBatch` SQL：
  ```xml
  UPDATE workspace_maas_tracing_log
  SET body_storage_location = #{location}
  WHERE request_id IN (#{requestIds})
  ```

### Task 6: ON DUPLICATE KEY UPDATE 补充 body_storage_location

- [x] 6.1 在 `insertOnDuplicateKeyUpdate` 的 `ON DUPLICATE KEY UPDATE` 子句末尾追加 `body_storage_location = COALESCE(VALUES(body_storage_location), body_storage_location)`
- [x] 6.2 在 `batchInsertOnDuplicateKeyUpdate` 的 `ON DUPLICATE KEY UPDATE` 子句末尾追加 `body_storage_location = COALESCE(VALUES(body_storage_location), body_storage_location)`
- [x] 6.3 验证：INSERT 时 bodyStorageLocation=null 不覆盖已有值

## Phase 3：OBS 通道核心实现

### Task 7: TracingLogObsBuffer — 数据结构与基本操作

- [x] 7.1 新建 `com.workspace.business.service.maas.impl.TracingLogObsBuffer`
- [x] 7.2 定义 `RetryableEntity` record：`entity`、`retryCount`、`obsKey`
- [x] 7.3 定义常量：`DATE_PATH_FMT`、`KEY_TEMPLATE`、`RECOVERY_KEY_TEMPLATE`、`MAX_RETRY_COUNT=3`
- [x] 7.4 注入 `ObsClient`（`@Autowired(required = false)`）、`MaasTracingLogService`、各 `@Value` 配置
- [x] 7.5 实现 `add(TracingLogEntity entity)`：enabled/obsClient 判断 → `buffer.add(new RetryableEntity(entity, 0, null))` → maxBufferSize 紧急 flush

### Task 8: TracingLogObsBuffer — 定时 flush 与优雅关闭

- [x] 8.1 实现 `scheduledFlush()`：`@Scheduled(fixedRateString = "...")`，enabled/obsClient 判断 → `doFlush()`
- [x] 8.2 实现 `shutdownFlush()`：`@PreDestroy synchronized`，记录日志 → `doFlush()`
- [x] 8.3 实现 `doFlush()`：`synchronized`，poll 全部 → 按分组逻辑分组 → 按 batchSize 分批 → `uploadBatch()`

### Task 9: TracingLogObsBuffer — 分组逻辑

- [x] 9.1 分组逻辑：有 `obsKey` 的 RetryableEntity 按 obsKey 分组（重试实体）；无 obsKey 的按 `userId + "/" + datePath` 分组（新增实体）
- [x] 9.2 验证：重试实体与新增实体不会混入同一批次

### Task 10: TracingLogObsBuffer — 上传逻辑

- [x] 10.1 实现 `uploadBatch(String groupKey, List<RetryableEntity> retryableEntities)`
- [x] 10.2 obsKey 生成/复用：`retryableEntities.get(0).obsKey()`，为 null 时生成新 key（`String.format(KEY_TEMPLATE, userId, datePath, System.currentTimeMillis())`）
- [x] 10.3 聚合 JSONL：遍历 entities，`JSON.toJSONString(entity) + '\n'`
- [x] 10.4 OBS 上传：设置 `ObjectMetadata`（contentType=application/x-ndjson, contentLength）→ `obsClient.putObject()`
- [x] 10.5 上传成功：重置 `consecutiveFailCount` → 调用 `callbackDbUpdate()`
- [x] 10.6 上传失败：`consecutiveFailCount.incrementAndGet()` → 重试（retryCount < 3 且 consecutiveFailCount < 3）→ 放回 buffer（携带 obsKey）→ 放弃（记录 error 日志）

### Task 11: TracingLogObsBuffer — DB UPDATE 回调

- [x] 11.1 实现 `callbackDbUpdate(List<TracingLogEntity> entities, String obsKey, List<RetryableEntity> retryableEntities)`
- [x] 11.2 提取 requestIds → `maasTracingLogService.updateBodyStorageLocationBatch(requestIds, obsKey)`
- [x] 11.3 成功：记录 debug 日志
- [x] 11.4 失败：记录 error 日志 → 调用 `saveLocationRecoveryFile()`

### Task 12: TracingLogObsBuffer — 恢复文件

- [x] 12.1 实现 `saveLocationRecoveryFile(List<TracingLogEntity> entities, String obsKey, String error)`
- [x] 12.2 构建恢复记录 JSONL：每行包含 `requestId`、`obsKey`、`failedAt`、`error`
- [x] 12.3 上传到 OBS：key = `String.format(RECOVERY_KEY_TEMPLATE, System.currentTimeMillis())`
- [x] 12.4 恢复文件上传本身失败：仅记录 error 日志，不再重试（避免递归）

## Phase 4：TracingLogHelper 改造

### Task 13: 去掉文件通道 + 增加 OBS 通道

- [x] 13.1 删除 `TRACING_LOG_LOGGER` 字段及 `TRACING_LOG_LOGGER.info(...)` 调用
- [x] 13.2 在 `writeLog()` 中增加 `saveToObsAsync(entity)` 调用（在 `saveToDatabaseAsync` 之前）
- [x] 13.3 实现 `saveToObsAsync(TracingLogEntity entity)`：`SpringContextHolder.getBean(TracingLogObsBuffer.class)` → `buffer.add(entity)`，try-catch 静默降级
- [x] 13.4 `convertToDbEntity` 中 `bodyStorageLocation` 保持传入（此时为 null，由 OBS 回填）

## Phase 5：requestBody / responseBody 补全

### Task 16: ProxyContext 扩展

- [x] 16.1 `ProxyContext` record 新增 `requestBody` 字段
- [x] 16.2 `ModelProxyServiceImpl.chat()` 中将 `forwardedBody` 存入 `ProxyRequest` → `ProxyContext`
- [x] 16.3 `DegradationExhaustedParams` 新增 `requestBody` 字段，从 `ProxyContext` 传入

### Task 17: ModelProxyServiceImpl 补全（3 处）

- [x] 17.1 `handleBlockingSuccess`：`.requestBody(ctx.requestBody())` `.responseBody(responseBody)`
- [x] 17.2 `logBlockingFailure`：`.requestBody(ctx.requestBody())` `.responseBody("")`
- [x] 17.3 `executeRetryBlockingRequest` 内成功/失败：`.requestBody(retryForwardedBody)` `.responseBody(响应/空)`

### Task 18: StreamingRequestHandler 补全（2 处）

- [x] 18.1 `handleStreamComplete`：`.requestBody(ctx.requestBody())` `.responseBody(state.getFullResponseBodyAsString())`
- [x] 18.2 `handleStreamError`：`.requestBody(ctx.requestBody())` `.responseBody(state.getFullResponseBodyAsString())`

### Task 19: ProxyErrorResponseWriter 补全（2 处）

- [x] 19.1 `handleRateLimitError`：方法签名新增 `requestBody` 参数，`.requestBody(requestBody)` `.responseBody("")`
- [x] 19.2 `handleDegradationExhausted`：从 `DegradationExhaustedParams.requestBody` 获取，`.requestBody(params.requestBody())` `.responseBody("")`

### Task 20: 调用链路适配

- [x] 20.1 `handleRateLimitError` 的所有调用处补充 `requestBody` 参数传入
- [x] 20.2 `handleDegradationExhausted` 的所有调用处补充 `params.requestBody()` 传入
- [x] 20.3 编译验证：所有调用点参数匹配

## Phase 6：验证

### Task 21: 编译与单元测试

- [x] 21.1 `mvn clean compile` 通过
- [x] 21.2 全量单元测试通过
- [x] 21.3 新增 `TracingLogObsBuffer` 单元测试：
  - [x] 21.3.1 `add()` 正常入队
  - [x] 21.3.2 `add()` enabled=false 时跳过
  - [x] 21.3.3 `add()` obsClient=null 时跳过
  - [x] 21.3.4 `doFlush()` 按用户+日期分组
  - [x] 21.3.5 `doFlush()` 重试实体按 obsKey 分组
  - [x] 21.3.6 `uploadBatch()` 成功后调用 `callbackDbUpdate`
  - [x] 21.3.7 `uploadBatch()` 失败后放回 buffer（携带 obsKey）
  - [x] 21.3.8 `uploadBatch()` 连续失败 ≥ 3 次后放弃
  - [x] 21.3.9 `callbackDbUpdate()` DB UPDATE 失败后调用 `saveLocationRecoveryFile`
  - [x] 21.3.10 obsKey 首次生成后重试时复用

### Task 22: ObsConfig 条件装配验证

- [ ] 22.1 `obs.enabled=true` 时 `ObsClient` Bean 正常创建
- [ ] 22.2 `obs.enabled=false` 时 `ObsClient` Bean 不创建，`TracingLogObsBuffer.add()` 静默跳过
- [ ] 22.3 `TracingLogObsBuffer` 在 obsClient=null 时不抛异常

### Task 23: 集成验证（需 OBS 测试环境）

- [ ] 23.1 配置 OBS 测试环境 AK/SK/endpoint/bucket
- [ ] 23.2 发起非流式请求 → 验证 OBS JSONL 文件包含 requestBody/responseBody
- [ ] 23.3 发起流式请求 → 验证 OBS JSONL 文件包含完整 responseBody
- [ ] 23.4 验证 DB `bodyStorageLocation` 被正确回填
- [ ] 23.5 验证 OBS 存储路径按用户+日期分目录
- [ ] 23.6 模拟 OBS 上传失败 → 验证重试机制（obsKey 不变）
- [ ] 23.7 模拟 DB UPDATE 失败 → 验证恢复文件写入 `.recovery/`
- [ ] 23.8 验证 `obs.enabled=false` 时 DB 通道正常工作
- [ ] 23.9 验证文件通道（maas-tracing.log）已移除
