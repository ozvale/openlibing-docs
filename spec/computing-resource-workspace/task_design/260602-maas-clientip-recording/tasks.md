# MaaS 调用记录 clientIp - Tasks

## Phase 1：IP 提取与记录能力

### Task 1: MaasAuthInterceptor 新增 resolveClientIp

- [x] 1.1 实现 `resolveClientIp(request)` 方法，IP 提取优先级：X-Real-IP → RemoteAddr → 0.0.0.0
- [x] 1.2 在 `preHandle()` 中 API Key 验证通过后调用 `resolveClientIp()`，将 IP 存入 `MaasAuthContext`

### Task 2: MaasAuthContext 新增 clientIp 字段

- [x] 2.1 `MaasAuthInfo` 新增 `clientIp` 字段
- [x] 2.2 `MaasAuthContext` 新增 `getClientIp()` 方法，返回 `Optional<String>`

### Task 3: TracingLog 数据模型新增 clientIp

- [x] 3.1 `TracingLogEntity` 新增 `clientIp` 字段
- [x] 3.2 `MaasTracingLog` 新增 `clientIp` 字段
- [x] 3.3 `maas-tables.xml` 新增 `client_ip` 列定义

### Task 4: Mapper 与写入链路

- [x] 4.1 `MaasTracingLogMapper.xml` INSERT 语句包含 `client_ip`
- [x] 4.2 `ModelProxyServiceImpl` 所有 `TracingLogEntity.builder()` 添加 `.clientIp(MaasAuthContext.getClientIp().orElse(null))`
- [x] 4.3 `StreamingRequestHandler` 所有 `TracingLogEntity.builder()` 添加 `.clientIp(MaasAuthContext.getClientIp().orElse(null))`
- [x] 4.4 `ProxyErrorResponseWriter` 所有 `TracingLogEntity.builder()` 添加 `.clientIp(MaasAuthContext.getClientIp().orElse(null))`

### Task 5: 验证

- [x] 5.1 编译通过
- [x] 5.2 全量测试通过

---

## Phase 2：修复 clientIp 实际未记录的问题

> 上线验证后发现 `client_ip` 字段仍为空，排查发现流式请求中 ThreadLocal 丢失以及 Mapper ON DUPLICATE KEY UPDATE 缺失 client_ip。

### Task 6: IP 固化到上下文对象（解决 ThreadLocal 丢失）

- [x] 6.1 `ProxyRequest` record 新增 `clientIp` 字段
- [x] 6.2 `ProxyContext` 新增 `clientIp` 字段、构造参数、accessor
- [x] 6.3 `DegradationExhaustedParams` 新增 `clientIp` 字段
- [x] 6.4 `ModelProxyServiceImpl.chat()` 中提前获取 `MaasAuthContext.getClientIp()` 并传入 `ProxyRequest`
- [x] 6.5 `executeProxyLoop` 中 `ProxyRequest.clientIp` → `ProxyContext.clientIp`
- [x] 6.6 降级耗尽路径 `ProxyRequest.clientIp` → `DegradationExhaustedParams.clientIp`
- [x] 6.7 重试路径 `ProxyContext.clientIp` → 新 `ProxyContext.clientIp`
- [x] 6.8 `ModelProxyServiceImpl` 3 处 `MaasAuthContext.getClientIp()` → `ctx.clientIp()` / `retryCtx.clientIp()`
- [x] 6.9 `StreamingRequestHandler` 2 处 `MaasAuthContext.getClientIp()` → `ctx.clientIp()`
- [x] 6.10 `ProxyErrorResponseWriter` 2 处 `MaasAuthContext.getClientIp()` → `ctx.clientIp()` / `params.clientIp()`

### Task 7: Mapper ON DUPLICATE KEY UPDATE 补全

- [x] 7.1 `insertOnDuplicateKeyUpdate` 的 `ON DUPLICATE KEY UPDATE` 补充 `client_ip = VALUES(client_ip)`
- [x] 7.2 `batchInsertOnDuplicateKeyUpdate` 的 `ON DUPLICATE KEY UPDATE` 补充 `client_ip = VALUES(client_ip)`

### Task 8: 验证

- [x] 8.1 `mvn clean compile test` 全量通过（590 tests, 0 failures）
