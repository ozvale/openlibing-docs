# 模型调用审计日志 - Proposal

## 一、需求背景

当前 MaaS 网关已实现文件日志 + DB 异步批量写入的双写模式，但调用详情（requestBody/responseBody）未存储，无法满足模型调用的审计合规要求：

1. **调用详情未存储**：所有 `TracingLogHelper.writeLog` 调用点均未设置 `requestBody`/`responseBody`/`bodyStorageLocation`，DB 表 `workspace_maas_tracing_log` 的 `bodyStorageLocation` 字段始终为空
2. **无法按用户归档**：原 LTS 方案按时间分区转储，所有用户日志混杂在一个 gzip 文件中，无法按用户维度检索
3. **审计追溯困难**：无法快速定位"某用户的所有调用记录"，不满足合规审计要求
4. **不适合随机读取**：LTS 转储的是压缩 JSONL 批量文件，查单条记录需下载整个文件解压逐行扫描

本次改造将文件通道（maas-tracing.log → LTS → OBS 桶）替换为 OBS 直写通道，实现按用户归档的 JSONL 详情文件存储，同时保持 DB 通道作为查询安全网。这是模型调用审计日志能力的第一阶段，后续还将开发前端查询接口和数据下载功能。

## 二、改造范围

### 2.1 新增组件

| 组件 | 说明 |
|------|------|
| `ObsConfig` | OBS 客户端配置类，初始化 `ObsClient` Bean（`@ConditionalOnProperty` 按开关控制） |
| `TracingLogObsBuffer` | OBS 通道核心类：内存缓冲 + 定时 flush + 优雅关闭 + DB UPDATE 回调 + 恢复文件 |

### 2.2 修改组件

| 组件 | 改动 |
|------|------|
| `TracingLogHelper` | 去掉 `TRACING_LOG_LOGGER` 文件通道 + 增加 `saveToObsAsync` 调用 |
| `MaasTracingLogService` | 新增 `updateBodyStorageLocationBatch` 接口方法 |
| `MaasTracingLogServiceImpl` | 实现 `updateBodyStorageLocationBatch` |
| `MaasTracingLogMapper` | 新增 `updateBodyStorageLocationBatch` 方法 |
| `MaasTracingLogMapper.xml` | 新增 `updateBodyStorageLocationBatch` SQL + ON DUPLICATE KEY UPDATE 补充 `body_storage_location` |
| `ModelProxyServiceImpl` | 补全 requestBody/responseBody（3 处调用点） |
| `StreamingRequestHandler` | 补全 requestBody/responseBody（2 处调用点） |
| `ProxyErrorResponseWriter` | 补全 requestBody/responseBody（2 处调用点） |
| `pom.xml` | 添加 `esdk-obs-java-bundle` 依赖 |
| Apollo 配置 | OBS 连接信息（enabled、AK/SK、endpoint、bucket-name），不写入 application.yaml |

### 2.3 不改动的部分

- `TracingLogEntity` / `MaasTracingLog`：字段已预留，无需新增
- `workspace_maas_tracing_log` 表结构：`body_storage_location` 字段已存在
- DB 通道的 `ConcurrentLinkedQueue` + `@Scheduled` flush 模式：保持不变
- 前端检索 API（第 9 章）：本次不实现，后续独立 spec

## 三、核心设计决策

### 3.1 两阶段写入解决 bodyStorageLocation 时序问题

DB flush（1s 间隔）先于 OBS flush（3s 间隔）执行。`convertToDbEntity` 在 `writeLog` 时已将字段拷贝到新的 `MaasTracingLog` 对象，OBS 侧对 `TracingLogEntity` 的修改无法传递到 DB 侧。

**方案**：DB INSERT 时 `bodyStorageLocation = null`，OBS 上传成功后独立调用 `updateBodyStorageLocationBatch` 回填。

### 3.2 obsKey 稳定性

obsKey 在首次 flush 时生成并绑定到 `RetryableEntity`，重试时复用同一 key。保证审计时 key 稳定不变，不会产生孤儿文件。

### 3.3 DB UPDATE 失败兜底

OBS 上传成功但 DB UPDATE 失败时，将 requestId→obsKey 映射写入 OBS `.recovery/` 恢复文件，支持人工补录。写入 OBS 而非本地文件是因为 CCE 容器本地存储是临时的。

### 3.4 去掉文件通道

OBS 通道已覆盖文件通道的所有功能，LTS 路径不适合按用户检索，去掉文件通道减少 I/O 和运维负担。

## 四、验收标准

### 功能验收

- [ ] OBS 通道开启时（`obs.enabled=true`），调用日志详情（含 requestBody/responseBody）写入 OBS 详情桶
- [ ] OBS 存储路径按用户+日期分目录：`tracing-detail/{userId}/{yyyy}/{MM}/{dd}/batch-{timestamp}.jsonl`
- [ ] JSONL 文件每行一条完整 JSON 记录，包含所有字段（含 requestBody 和 responseBody）
- [ ] DB 中 `bodyStorageLocation` 字段在 OBS 上传成功后被正确回填
- [ ] 非流式请求成功：requestBody 和 responseBody 均有值
- [ ] 流式请求成功：requestBody 和 responseBody 均有值（responseBody 为流式拼接结果）
- [ ] 请求失败：requestBody 有值，responseBody 为空或部分内容
- [ ] 降级成功：modelName 为降级后的模型，errorMessage 包含降级信息
- [ ] 限流拒绝：requestBody 有值，responseBody 为空
- [ ] 降级耗尽：requestBody 有值，responseBody 为空

### 降级与容错验收

- [ ] OBS 通道关闭时（`obs.enabled=false`），DB 通道正常工作，核心字段不丢失
- [ ] OBS 偶发上传失败：数据放回缓冲区重试（最多 3 次），obsKey 不变
- [ ] OBS 连续失败 ≥ 3 次：放弃该批数据，记录 error 日志
- [ ] OBS 上传成功但 DB UPDATE 失败：映射关系写入 OBS `.recovery/` 恢复文件
- [ ] 缓冲区超过 maxBufferSize：触发紧急 flush
- [ ] Pod 优雅关闭：`@PreDestroy` 同步 flush 缓冲区数据

### 非功能验收

- [ ] OBS 通道 add 操作不阻塞主请求（同步入队，<0.1ms）
- [ ] 正常情况下缓冲区内存占用 < 10MB（100 QPS × 3s 间隔）
- [ ] `ObsClient` Bean 在 `obs.enabled=false` 时不创建
- [ ] AK/SK 通过 `SecurityUtil.decrypt` 解密，与现有 RedisConfig 一致
- [ ] 全量单元测试通过
- [ ] 文件通道（`TRACING_LOG_LOGGER`）已移除

### 安全验收

- [ ] OBS 桶访问控制限制仅 MaaS 服务账号可读写
- [ ] AK/SK 不硬编码，通过 Apollo 加密配置注入
- [ ] 恢复文件（`.recovery/`）不含 requestBody/responseBody 内容，仅含 requestId→obsKey 映射

## 五、约束

- 不修改 `workspace_maas_tracing_log` 表结构（字段已预留）
- 不修改 DB 通道的 flush 机制（保持 `ConcurrentLinkedQueue` + `@Scheduled` 1s）
- 不引入 Kafka（后续服务拆分时再接入）
- 前端检索 API 不在本次实现（后续独立 spec）
- 不修改 `TracingLogEntity` / `MaasTracingLog` 的字段定义
- OBS SDK 版本使用 `esdk-obs-java-bundle:3.24.12`

## 六、关联文档

- [MaaS调用日志OBS入湖方案](../../md/AI作业平台/MaaS服务/MaaS调用日志OBS入湖方案.md)（完整设计文档）
- [MAAS调用日志入湖设计文档](../../md/AI作业平台/MaaS服务/MAAS调用日志入湖设计文档.md)（原 LTS 方案，已废弃）
- [MaaS调用详情存储与前端检索方案](../../md/AI作业平台/MaaS服务/MaaS调用详情存储与前端检索方案.md)（前端检索，后续实现）
