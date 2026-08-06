# 流水线列表、详情接口优化并支持搜索条件缓存 - 实现步骤

## 任务清单

### P0 异常处理修复

- [x] 1. `PipelineServiceImpl.getPipelineList` 删除原 `catch (Exception e) { return DataResult.success(); }`
- [x] 2. 新增 `ConnectionException` 捕获，返回"网络连接超时"
- [x] 3. 新增 `RequestTimeoutException` 捕获，返回"响应超时，请稍后重试"
- [x] 4. 新增 `ServiceResponseException` 捕获，记录 HttpStatusCode/RequestId/ErrorCode/ErrorMsg，返回"获取流水线列表失败，请稍后重试"
- [x] 5. `Exception` 兜底捕获，返回"获取流水线列表异常，请稍后重试或联系管理员！"

### P1 CodeArtsPipelineClient 缓存

- [x] 6. 新增字段 `pipelineClientCache`（`Cache<String, Optional<CodeArtsPipelineClient>>`，TTL 30 分钟）
- [x] 7. 新增常量 `LOCAL_CACHE_TTL_MINUTES = 30L`
- [x] 8. 新增方法 `getPipelineClientCached(String projectId)`，使用 `Cache.get(key, loader)` 原子加载
- [x] 9. `getPipelineClientCached` 内 `ExecutionException` 降级直接构建
- [x] 10. `getPipelineList` 替换 `hwCloudClient.buildHuaweiCloudSdkClient` 为 `getPipelineClientCached`

### P2 HwProjectInfoEntity 缓存

- [x] 11. 新增字段 `hwProjectEntityCache`（`Cache<String, Optional<HwProjectInfoEntity>>`，TTL 30 分钟）
- [x] 12. 新增方法 `getHwProjectInfoEntityCached(String projectId)`，使用 `Cache.get(key, loader)` 原子加载
- [x] 13. `getHwProjectInfoEntityCached` 内 `ExecutionException` 降级直接查库
- [x] 14. `getPipelineClientCached` loader 内部调用 `getHwProjectInfoEntityCached`，避免重复查库
- [x] 15. `getPipelineList` 替换 `hwProjectInfoMapper.selectOne` 为 `getHwProjectInfoEntityCached`

### P3 白名单 Redis 缓存

- [x] 16. 新增依赖 `@Autowired private OpenlibingRedis openlibingRedis`
- [x] 17. 新增常量 `WHITELIST_CACHE_PREFIX = "pipeline:whitelist:"`
- [x] 18. 新增常量 `WHITELIST_CACHE_TTL_SECONDS = 30L`
- [x] 19. 新增方法 `getWhitelistPipelineIdSetCached(String projectId)`，Redis 读写 + DB 降级
- [x] 20. `getWhitelistPipelineIdSetCached` 读缓存命中时反序列化为 `Set<String>`
- [x] 21. `getWhitelistPipelineIdSetCached` miss 时查 DB（`pipeline_info` where `deleted=false`），写缓存（空集合也写，防穿透）
- [x] 22. `getWhitelistPipelineIdSetCached` Redis 读/写异常时降级，仅记 WARN 日志
- [x] 23. 拆分 `filterPipelineList`：DB 查询逻辑上移至 `getWhitelistPipelineIdSetCached`，`filterPipelineList` 仅负责过滤与分页
- [x] 24. `updateWhitelistStatus` 在 `doUpdateWhitelistStatus` 返回 `result.ok()` 后主动 `openlibingRedis.del(WHITELIST_CACHE_PREFIX + projectId)`
- [x] 25. `del` 失败时记 WARN 日志，不影响主流程（30s TTL 兜底）

### 测试

- [x] 26. `testGetPipelineList_Exception` 断言从 `assertTrue(result.ok())` 改为 `assertFalse(result.ok())` + `assertNull(result.getData())`
- [ ] 27. 补充 `OpenlibingRedis` mock 注入与 stub 配置（**P1 阻塞项**，需在合并前补齐）

## 关联 Issue

- openlibing/openlibing-cicd#185
- openlibing/openlibing-cicd#538（业务 PR）
