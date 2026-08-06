# 流水线列表、详情接口优化并支持搜索条件缓存

## 需求背景

用户在前端流水线列表页面查看所属项目下的流水线时，每次访问触发后端 `getPipelineList` 接口。该接口存在两类问题：

1. **性能问题**：每次请求重复执行 AK/SK 解密与 SDK 客户端构建、重复查询 `hw_project_info` 与 `pipeline_info` 表，CPU 与 DB 开销不可忽略；
2. **正确性 P0 缺陷**：`getPipelineList` 的 `catch (Exception e)` 直接返回 `DataResult.success()`，导致上游调用方无法识别失败，前端拿到空数据无法提示用户。

## 问题分析

### 性能瓶颈

| 调用点 | 重复开销 | 频率 |
|--------|---------|------|
| `hwCloudClient.buildHuaweiCloudSdkClient` | AK/SK 非对称解密 + SSL 客户端初始化 | 每次请求 |
| `hwProjectInfoMapper.selectOne` | DB 查询项目映射 | 每次请求 |
| `pipelineInfoMapper.selectList`（白名单过滤） | DB 查询白名单流水线 | 每次请求 |

### P0 异常处理缺陷

原实现：

```java
try {
  ListPipelinesResponse response = client.listPipelines(request);
  filterPipelineList(...);
  return DataResult.successData(response);
} catch (Exception e) {
  return DataResult.success();  // 异常伪装成功，前端无法识别失败
}
```

## 优化清单

| 优先级 | 项 | 类型 | 缓存方式 | 业务感知 |
|--------|---|------|---------|---------|
| P0 | 修复 `getPipelineList` 异常处理（参考 `getPipelineRunDetail` 模板） | 正确性 bug | — | 无（修复后明确报错而非伪装成功） |
| P1 | 缓存 `CodeArtsPipelineClient` | 性能 | Guava `CacheBuilder`（30min TTL + 原子加载） | 无 |
| P2 | 缓存 `HwProjectInfoEntity` | 性能 | Guava `CacheBuilder`（30min TTL + 原子加载） | 无 |
| P3 | 白名单缓存 30s + 主动失效 | 性能 | Redis（`StringRedisTemplate` + JSON） | 无（主动失效保证零延迟） |

## 缓存实现选型

### P1 / P2：Guava CacheBuilder（本地，带 TTL + 原子加载）

| 维度 | 旧方案（ConcurrentHashMap） | 新方案（Guava CacheBuilder） |
|------|---------------------------|---------------------------|
| TTL | 无，重启才生效 | 30min `expireAfterWrite` |
| 竞态 | check-then-act，多线程重复构建 | `Cache.get(key, Callable)` 原子加载，同 key 互斥 |
| AK/SK 轮转 | 旧凭据永久有效至重启（安全审计隐患） | 最多 30min 自动失效重建 |
| null 处理 | 不缓存 null，可能穿透 | `Optional` 包装，缓存负查询结果 |
| 异常降级 | 无 | `ExecutionException` 时 fallback 直接查库/构建 |
| 参考实现 | `ImageServiceImpl` | `AuthInterceptor` |

### P3：Redis（StringRedisTemplate + JSON，主动失效）

选型理由：

1. **多实例全局一致**：白名单变更后所有实例立即生效（本地缓存只能当前实例立即生效，其他实例靠 TTL）；
2. **主动失效全局生效**：符合用户"改完立即看到"预期；
3. **与 `CrossRegionServiceImpl` 既有模式一致**。

可用性保障：

- 读缓存：try-catch Redis 异常，降级回源 DB，避免 Redis 故障导致接口全量失败；
- 写缓存：try-catch Redis 异常，仅 warn 日志，不影响主流程，下次 miss 再写；
- 主动失效：`updateWhitelistStatus` 中 `del` 缓存独立 try-catch，失败靠 30s TTL 兜底最终一致。

## 不做的事项（YAGNI 检查）

| 候选增加项 | 是否需要 | 原因 |
|-----------|---------|------|
| 缓存流水线运行状态数据 | 否 | 5 秒轮询要求实时性，缓存破窗读语义 |
| 缓存运行实例详情（终态缓存） | 否 | 回看频率不高，命中率低，收益有限 |
| TTL 配置化（Apollo） | 否 | 业务已确认无需调整，写死常量更简单 |
| 引入 Caffeine 本地缓存框架 | 否 | 项目已有 Guava（`AuthInterceptor` 在用） |
| P3 加 Guava 二级本地缓存 | 否 | 当前 Redis 压力可忽略，二级缓存增加一致性复杂度 |
| 管理接口主动清缓存 | 否 | 30min TTL 已覆盖 AK/SK 轮转场景 |
| DB 变更通知（binlog/事件） | 否 | 复杂度过高，AK/SK 轮转极低频 |
| 优化华为云 300 条拉取 | 否 | 外部依赖 + 白名单架构必要，代码层面无优化空间 |

## 验收标准

- [x] `getPipelineList` 异常分支返回 `DataResult.failureMessage(...)`，不再伪装成功
- [x] `getPipelineList` 按 SDK 异常类型分层捕获（`ConnectionException` / `RequestTimeoutException` / `ServiceResponseException` / `Exception`）
- [x] `CodeArtsPipelineClient` 按 `projectId` 本地缓存，TTL 30 分钟
- [x] `HwProjectInfoEntity` 按 `projectId` 本地缓存，TTL 30 分钟
- [x] 白名单流水线 ID 集合按 `projectId` 缓存到 Redis，TTL 30 秒
- [x] `updateWhitelistStatus` 成功后主动 `del` Redis 缓存
- [x] Guava `ExecutionException` 时降级直接查库/构建
- [x] Redis 读/写/删异常时降级，不影响主流程
- [x] 单元测试 `testGetPipelineList_Exception` 断言修正为 `assertFalse(result.ok())`

## 关联 Issue

- openlibing/openlibing-cicd#185
- openlibing/openlibing-cicd#538（业务 PR）
