# 定时同步流水线信息需增加超时机制 - 技术方案

## 修改范围

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `SSLCipherSuiteUtil.java` | 新增方法 | `createHttpClientWithTimeout(protocol, connectTimeoutMs, socketTimeoutMs)` |
| `HwCloudClient.java` | 新增方法 + 优化 | 新增 `buildPipelineSslHttpsClientWithTimeout`、`getDataResultFromHWCloudHttpApiWithTimeout`；`OBJECT_MAPPER` 复用优化 |
| `PipelineServiceImpl.java` | 修改方法 + 新增方法 | `fetchPipelineDetailFromRemote` 改用带超时版本；新增 `getCodeArtsPipelineClientByProjectIdWithTimeout`、`fetchPipelineDetailWithTimeout` |
| `ScheduleTaskImpl.java` | 注释注解 | `@Scheduled` 注释掉，标注已迁移 |
| `XxlJobHandler.java` | 新增方法 | `@XxlJob("syncPipelineConfigInfoHandler")` |

## 技术方案

### 1. SSL HTTP Client 超时

在 `SSLCipherSuiteUtil` 中新增 `createHttpClientWithTimeout` 方法，通过 `RequestConfig` 设置：

- `setConnectTimeout(connectTimeoutMs)` — TCP 建连超时
- `setSocketTimeout(socketTimeoutMs)` — socket 读取超时
- `setConnectionRequestTimeout(connectTimeoutMs)` — 从连接池获取连接的超时

与 `createHttpClient` 的区别：
- 不覆盖 static `httpClient` 字段，避免资源泄漏
- 每次调用创建新客户端实例（超时客户端用完即关）

### 2. 华为云 SDK 客户端超时

已有 `buildHuaweiCloudSdkClientWithTimeout` 方法，使用 `HttpConfig` 配置：

```java
HttpConfig httpConfig = HttpConfig.getDefaultHttpConfig()
    .withConnectionTimeout(ThirdPartyApiConstants.CONNECT_TIMEOUT_SECONDS)  // 10s
    .withReadTimeout(ThirdPartyApiConstants.READ_TIMEOUT_SECONDS);          // 20s
```

新增 `getCodeArtsPipelineClientByProjectIdWithTimeout` 调用此方法。

### 3. fetchPipelineDetailFromRemote 改造

原调用链：
```
fetchPipelineDetailFromRemote
  → getCodeArtsPipelineClientByProjectId        // 无超时
  → fetchPipelineDetail
    → getDataResultFromHWCloudHttpApi            // 无超时
```

改造后：
```
fetchPipelineDetailFromRemote
  → getCodeArtsPipelineClientByProjectIdWithTimeout  // 带超时 SDK
  → fetchPipelineDetailWithTimeout
    → getDataResultFromHWCloudHttpApiWithTimeout      // 带超时 HTTP
```

原有的无超时方法保留，其他非定时任务调用路径不受影响。

### 4. @Scheduled → xxl-job 迁移

| 对比项 | @Scheduled | xxl-job |
|--------|-----------|---------|
| 调度线程 | Spring 单线程（scheduling-1） | xxl-job 独立线程池 |
| 阻塞影响 | 一个卡死全部停摆 | 仅影响当前任务 |
| 手动触发 | 不支持 | 支持控制台手动执行 |
| 监控告警 | 无 | 内置执行日志和失败告警 |
| 超时控制 | 无 | 支持配置任务超时时间 |

handler 名称：`syncPipelineConfigInfoHandler`
调度建议：`0 0 0,12 * * ?`（每天 0 点、12 点）

### 5. 超时参数

统一使用 `ThirdPartyApiConstants`：

| 参数 | 值 | 说明 |
|------|---|------|
| `CONNECT_TIMEOUT_SECONDS` | 10s | TCP 建连超时 |
| `READ_TIMEOUT_SECONDS` | 20s | socket 读取超时 |

### 6. 附带优化

- `HwCloudClient.OBJECT_MAPPER` 静态初始化时配置 `FAIL_ON_UNKNOWN_PROPERTIES=false`，原 `getDataResultFromHWCloudHttpApi` 中 `new ObjectMapper()` 替换为复用单例，减少 GC 压力。

## 影响分析

- **对现有功能无破坏**：所有新增方法为独立新增，原有无超时方法保留
- **向后兼容**：`fetchPipelineDetailFromRemote` 的签名和返回值不变
- **部署注意**：需要在 xxl-job 管理后台新增 `syncPipelineConfigInfoHandler` 任务

## 关联 Issue

- openlibing/openlibing-cicd#180
