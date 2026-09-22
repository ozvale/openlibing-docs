# 模型调用审计日志 - Design

注：该需求包含前端查询接口，本文档只做第一阶段后端存储日志设计。
## 一、架构设计

### 1.1 整体架构

```
请求完成后
   │
   ▼
TracingLogHelper.writeLog(entity)
   │
   ├── ① DB 通道（已有，不变）
   │   MaasTracingLogService.saveAsync(convertToDbEntity(entity))
   │       → ConcurrentLinkedQueue → @Scheduled 1s flush → MySQL
   │       → bodyStorageLocation 首次 INSERT 为 null
   │       → OBS 上传成功后 UPDATE 回填 bodyStorageLocation
   │
   └── ② OBS 通道（新增）
       TracingLogObsBuffer.add(entity)
           → ConcurrentLinkedQueue<RetryableEntity>
           → @Scheduled 3s flush
           → 按用户分组 → 聚合为 JSONL → 上传 OBS 详情桶
           → 上传成功后 callbackDbUpdate 回填 bodyStorageLocation
           → DB UPDATE 失败时写入 OBS 恢复文件（.recovery/）
           → 偶发失败放回缓冲区重试（obsKey 不变，最多 3 次）
           → 优雅关闭时 @PreDestroy 同步 flush
```

### 1.2 双通道职责

| 通道 | 存储 | 内容 | 用途 | 变更 |
|------|------|------|------|------|
| DB 通道 | MySQL | 核心查询字段 + `bodyStorageLocation` | 前端条件搜索、统计分析 | `bodyStorageLocation` 从 null → obsKey（两阶段写入） |
| OBS 通道 | OBS 详情桶 | 按用户归档的 JSONL 详情文件（含 body） | 前端查看调用详情、审计追溯 | **新增** |

### 1.3 两阶段写入时序

```
t=0s   writeLog(entity)
         ├─ OBS: buffer.add(new RetryableEntity(entity, 0, null))
         └─ DB:  saveAsync(convertToDbEntity(entity))  ← bodyStorageLocation = null

t=1s   DB flush → INSERT (bodyStorageLocation = null)   ← 首次写入

t=3s   OBS flush
         ├─ 生成 obsKey = "tracing-detail/user001/2026/06/08/batch-1717800003000.jsonl"
         ├─ 绑定 obsKey 到 RetryableEntity
         ├─ putObject() 成功
         └─ callbackDbUpdate()
              ├─ maasTracingLogService.updateBodyStorageLocationBatch(requestIds, obsKey)
              └─ DB UPDATE → bodyStorageLocation = obsKey              ← 二次回填
```

**根因**：`convertToDbEntity` 在 `writeLog` 时已将字段拷贝到新的 `MaasTracingLog` 对象，OBS 侧对 `TracingLogEntity` 的修改无法传递到 DB 侧。因此必须通过独立的 DB UPDATE 回填。

## 二、OBS 存储设计

### 2.1 存储路径

```
tracing-detail/{userId}/{yyyy}/{MM}/{dd}/batch-{timestamp}.jsonl
tracing-detail/.recovery/db-update-failures-{timestamp}.jsonl
```

| 设计点 | 说明 |
|--------|------|
| 按 userId 分目录 | 支持按用户维度检索，满足审计合规要求 |
| 按日期分目录 | 支持按时间范围清理过期数据 |
| batch-{timestamp} | 首次 flush 时的时间戳毫秒值；重试时复用，保证 key 稳定 |
| .recovery/ | DB UPDATE 失败时的恢复文件目录，90 天自动删除 |

### 2.2 JSONL 文件格式

```jsonl
{"requestId":"uuid-001","requestTimestamp":1717800000000,"userId":"user001","modelName":"qwen-72b","status":"success","latencyMs":2345,"requestBody":{...},"responseBody":{...}}
{"requestId":"uuid-002","requestTimestamp":1717800001000,"userId":"user001","modelName":"deepseek-v3","status":"fail","errorCode":"429","errorMessage":"rate limit","requestBody":{...},"responseBody":""}
```

### 2.3 恢复文件格式

```jsonl
{"requestId":"uuid-001","obsKey":"tracing-detail/user001/2026/06/08/batch-1717800003000.jsonl","failedAt":"2026-06-08T10:00:03","error":"Connection refused"}
```

### 2.4 OBS 桶配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 桶名 | Apollo 配置 | 独立桶，与其他业务桶隔离 |
| 存储类别 | 标准存储 | 热数据，前端需随机读取 |
| 加密 | SSE-OBS | 服务端加密 |
| 生命周期 | 30d→低频，180d→归档，365d→删除 | `tracing-detail/` 前缀；`.recovery/` 前缀 90d 删除 |
| 访问控制 | 桶策略限制仅 MaaS 服务账号可读写 | 最小权限原则 |

## 三、核心类设计

### 3.1 ObsConfig

```java
@Slf4j
@Configuration
@ConditionalOnProperty(name = "maas.gateway.tracing-log.obs.enabled",
    havingValue = "true", matchIfMissing = false)
public class ObsConfig {
    @Value("${maas.gateway.tracing-log.obs.access-key-id}")
    private String accessKeyId;

    @Value("${maas.gateway.tracing-log.obs.secret-access-key}")
    private String secretAccessKey;

    @Value("${maas.gateway.tracing-log.obs.endpoint}")
    private String endpoint;

    @Value("${security.part1}")
    private String securityPart1;

    @Bean(destroyMethod = "close")
    public ObsClient obsClient() {
        String ak = SecurityUtil.decrypt(accessKeyId, securityPart1);
        String sk = SecurityUtil.decrypt(secretAccessKey, securityPart1);
        ObsConfiguration config = new ObsConfiguration();
        config.setEndPoint(endpoint);
        config.setConnectionTimeout(10000);
        config.setSocketTimeout(30000);
        log.info("ObsClient initialized, endpoint={}", endpoint);
        return new ObsClient(ak, sk, config);
    }
}
```

**设计要点**：
- `@ConditionalOnProperty`：`obs.enabled=false` 时不创建 Bean，OBS 通道自动降级
- `destroyMethod = "close"`：Spring 容器关闭时自动关闭 ObsClient 连接
- AK/SK 解密方式与 `RedisConfig`、`CryptoConfig` 一致

### 3.2 TracingLogObsBuffer

```java
@Slf4j
@Component
public class TracingLogObsBuffer {
    private static final DateTimeFormatter DATE_PATH_FMT =
        DateTimeFormatter.ofPattern("yyyy/MM/dd").withZone(ZoneId.of("Asia/Shanghai"));
    private static final String KEY_TEMPLATE = "tracing-detail/%s/%s/batch-%d.jsonl";
    private static final String RECOVERY_KEY_TEMPLATE =
        "tracing-detail/.recovery/db-update-failures-%s.jsonl";
    private static final int MAX_RETRY_COUNT = 3;

    private final ConcurrentLinkedQueue<RetryableEntity> buffer = new ConcurrentLinkedQueue<>();

    @Autowired(required = false)
    private ObsClient obsClient;

    @Autowired
    private MaasTracingLogService maasTracingLogService;

    @Value("${maas.gateway.tracing-log.obs.bucket-name:}")
    private String bucketName;

    @Value("${maas.gateway.tracing-log.obs.batch-size:200}")
    private int batchSize;

    @Value("${maas.gateway.tracing-log.obs.max-buffer-size:5000}")
    private int maxBufferSize;

    @Value("${maas.gateway.tracing-log.obs.enabled:false}")
    private boolean enabled;

    private final AtomicInteger consecutiveFailCount = new AtomicInteger(0);

    // add() → buffer.add(new RetryableEntity(entity, 0, null))
    // scheduledFlush() → @Scheduled 3s
    // shutdownFlush() → @PreDestroy synchronized
    // doFlush() → 按用户+日期分组（新实体）或按 obsKey 分组（重试实体）
    // uploadBatch() → 生成或复用 obsKey → putObject → callbackDbUpdate
    // callbackDbUpdate() → updateBodyStorageLocationBatch → 失败则 saveLocationRecoveryFile
    // saveLocationRecoveryFile() → 写入 .recovery/ 恢复文件

    private record RetryableEntity(TracingLogEntity entity, int retryCount, String obsKey) {}
}
```

**关键设计点**：

| 设计点 | 说明 |
|--------|------|
| `RetryableEntity.obsKey` | 首次 flush 时生成 obsKey 并绑定；重试时复用同一 key |
| 分组逻辑区分新旧 | 有 obsKey 按 obsKey 分组（重试）；无 obsKey 按用户+日期分组（新增） |
| `@Autowired(required = false)` | OBS 未启用时 obsClient 为 null，add() 直接跳过 |
| `callbackDbUpdate` | OBS 上传成功后独立调用 DB UPDATE，不依赖共享 entity 对象 |
| `saveLocationRecoveryFile` | DB UPDATE 失败时写恢复文件到 OBS（CCE 本地存储不可靠） |
| `consecutiveFailCount` | 连续失败计数器，成功时重置；≥3 时放弃重试 |

### 3.3 TracingLogHelper 修改

```java
public static void writeLog(TracingLogEntity entity) {
    // 文件通道已去掉，不再写 maas-tracing.log
    saveToObsAsync(entity);      // OBS 通道
    saveToDatabaseAsync(entity); // DB 通道
}

private static void saveToObsAsync(TracingLogEntity entity) {
    try {
        TracingLogObsBuffer buffer = SpringContextHolder.getBean(TracingLogObsBuffer.class);
        buffer.add(entity);
    } catch (Exception e) {
        // OBS 通道降级：Bean 不存在或未启用时静默跳过
    }
}
```

**注意**：`convertToDbEntity` 中 `bodyStorageLocation` 在 INSERT 时始终为 null，由 OBS 上传成功后的 `callbackDbUpdate` 独立回填。

### 3.4 MaasTracingLogMapper 新增

```xml
<update id="updateBodyStorageLocationBatch">
    UPDATE workspace_maas_tracing_log
    SET body_storage_location = #{location}
    WHERE request_id IN
    <foreach collection="requestIds" item="id" open="(" separator="," close=")">
        #{id}
    </foreach>
</update>
```

### 3.5 ON DUPLICATE KEY UPDATE 补充

现有 `batchInsertOnDuplicateKeyUpdate` 的 `ON DUPLICATE KEY UPDATE` 子句未包含 `body_storage_location`，需补充：

```xml
body_storage_location = COALESCE(VALUES(body_storage_location), body_storage_location)
```

使用 `COALESCE` 确保 INSERT 时为 null 不覆盖已有值。

## 四、requestBody / responseBody 补全设计

### 4.1 调用点清单

| # | 文件 | 方法 | requestBody 来源 | responseBody 来源 | 当前状态 |
|---|------|------|-----------------|-----------------|---------|
| 1 | ModelProxyServiceImpl | `handleBlockingSuccess` | `forwardedBody` | `responseBody` | 需补全 |
| 2 | ModelProxyServiceImpl | `logBlockingFailure` | 需从 ctx 传入 | 空字符串 | 需补全 |
| 3 | ModelProxyServiceImpl | `executeRetryBlockingRequest` 内成功/失败 | `retryForwardedBody` | 响应/空 | 需补全 |
| 4 | StreamingRequestHandler | `handleStreamComplete` | 需从 ctx 传入 | `state.getFullResponseBodyAsString()` | 需补全 |
| 5 | StreamingRequestHandler | `handleStreamError` | 需从 ctx 传入 | `state.getFullResponseBodyAsString()` | 需补全 |
| 6 | ProxyErrorResponseWriter | `handleRateLimitError` | 需传入 | 空字符串 | 需补全 |
| 7 | ProxyErrorResponseWriter | `handleDegradationExhausted` | 需传入 | 空字符串 | 需补全 |

### 4.2 requestBody 传递方案

部分调用点当前无法直接获取 requestBody，需通过 `ProxyContext` 或方法参数传递：

- **ProxyContext**：新增 `requestBody` 字段，在 `chat()` 入口处将 `forwardedBody` 存入 ctx
- **DegradationExhaustedParams**：新增 `requestBody` 字段，从 ctx 传入
- **ProxyErrorResponseWriter**：方法签名新增 `requestBody` 参数

### 4.3 降级场景的日志行为

经代码确认，`requestId` 在 `chat()` 入口处生成一次，整个降级/重试循环共用同一个 `requestId`。无论经过多少次降级/重试，每个用户请求只产生一条日志记录。

| 场景 | writeLog 调用次数 | modelName | errorMessage |
|------|-----------------|-----------|-------------|
| 正常成功 | 1 次 | 请求的模型 | 无 |
| 降级成功 | 1 次 | 降级后的模型 | `[降级] originalModel -> actualModel: ...` |
| 降级失败 | 1 次 | 原始请求模型 | 降级耗尽信息 |
| 重试成功 | 1 次 | 重试的模型 | 无 |

## 五、配置设计

所有 OBS 配置通过 Apollo + `@Value` 默认值注入，**不写入 `application.yaml`**。

| 配置项 | 来源 | 默认值 | 说明 |
|--------|------|--------|------|
| `obs.enabled` | Apollo | `false` | OBS 通道开关，需在 Apollo 中显式开启 |
| `obs.access-key-id` | Apollo（加密） | - | OBS AK，Apollo 加密存储，`SecurityUtil.decrypt` 解密 |
| `obs.secret-access-key` | Apollo（加密） | - | OBS SK，Apollo 加密存储，`SecurityUtil.decrypt` 解密 |
| `obs.endpoint` | Apollo | - | OBS endpoint，如 `obs.cn-southwest-2.myhuaweicloud.com` |
| `obs.bucket-name` | Apollo | - | 详情桶名称 |
| `obs.flush-interval-ms` | `@Value` 默认值 | `3000` | 缓冲 flush 间隔（毫秒），需要调整时在 Apollo 覆盖 |
| `obs.batch-size` | `@Value` 默认值 | `200` | 单次 flush 最大聚合条数，需要调整时在 Apollo 覆盖 |
| `obs.max-buffer-size` | `@Value` 默认值 | `5000` | 缓冲区最大容量，需要调整时在 Apollo 覆盖 |

**配置分类**：

| 类别 | 配置项 | 理由 |
|------|--------|------|
| 必须在 Apollo | enabled、access-key-id、secret-access-key、endpoint、bucket-name | 环境相关 + 敏感信息，不同环境值不同 |
| `@Value` 默认值即可 | flush-interval-ms、batch-size、max-buffer-size | 调优参数，默认值适用于绝大多数场景，需要调整时再在 Apollo 覆盖 |

## 六、极端情况分析

| 场景 | 影响 | 保障 |
|------|------|------|
| OBS 偶发上传失败 | 放回缓冲区重试（obsKey 不变，最多 3 次） | 重试成功后 DB UPDATE 回填 |
| OBS 连续失败 ≥ 3 次 | 放弃该批数据，body 详情丢失 | DB 核心字段可通过 requestId 追溯 |
| OBS 成功但 DB UPDATE 失败 | DB 中 bodyStorageLocation 为空 | 恢复文件写入 OBS `.recovery/`，支持人工补录 |
| Pod 强制杀（OOMKilled） | 内存缓冲区数据丢失 | DB 有 requestId 可追溯 |
| OBS 服务不可用 | 所有上传失败 | DB 通道不受影响 |
| 缓冲区积压 | maxBufferSize 触发紧急 flush | 紧急 flush 在写入线程同步执行 |

## 七、内存占用评估

| 指标 | 估算 |
|------|------|
| 单条日志大小（含 body） | ~5-30 KB |
| 100 QPS × 3s 间隔 | 缓冲区峰值 ~300 条 |
| 缓冲区内存占用 | 300 × 15KB ≈ 4.5 MB |
| maxBufferSize=5000 极端 | 5000 × 30KB ≈ 150 MB |

## 八、涉及文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **新增** | `pom.xml` | 添加 `esdk-obs-java-bundle:3.24.12` 依赖 |
| **新增** | `common/config/ObsConfig.java` | ObsClient Bean 配置 |
| **新增** | `business/service/maas/impl/TracingLogObsBuffer.java` | OBS 缓冲+定时 flush+DB 回调+恢复文件 |
| **修改** | `common/utils/TracingLogHelper.java` | 去掉文件通道 + 增加 saveToObsAsync |
| **修改** | `business/service/maas/MaasTracingLogService.java` | 新增 updateBodyStorageLocationBatch 接口 |
| **修改** | `business/service/maas/impl/MaasTracingLogServiceImpl.java` | 实现 updateBodyStorageLocationBatch |
| **修改** | `business/mapper/MaasTracingLogMapper.java` | 新增 updateBodyStorageLocationBatch 方法 |
| **修改** | `resources/mapper/MaasTracingLogMapper.xml` | 新增 SQL + ON DUPLICATE KEY UPDATE 补充 |
| **修改** | `business/service/maas/impl/ModelProxyServiceImpl.java` | 补全 requestBody/responseBody（3 处） |
| **修改** | `business/service/maas/impl/StreamingRequestHandler.java` | 补全 requestBody/responseBody（2 处） |
| **修改** | `business/service/maas/impl/ProxyErrorResponseWriter.java` | 补全 requestBody/responseBody（2 处） |
| **修改** | Apollo 配置 | OBS 连接信息（enabled、AK/SK、endpoint、bucket-name） |

## 九、风险点

| 风险 | 应对 |
|------|------|
| OBS SDK 与现有依赖冲突 | `esdk-obs-java-bundle` 是 shade 包，冲突概率低；引入后需验证编译和启动 |
| requestBody 传递需改方法签名 | 通过 ProxyContext 传递，影响范围可控 |
| 两阶段写入导致短暂 location 为空 | 前端查询时 location 为空表示"尚未上传完成"，可接受 |
| DB UPDATE 与 INSERT 并发 | `updateBodyStorageLocationBatch` 按 requestId 更新，无并发冲突 |
| 敏感信息存储到 OBS | 需与安全团队确认桶豁免扫描方案 |
| 恢复文件堆积 | `.recovery/` 前缀设置 90 天自动删除生命周期 |
