# 流水线列表、详情接口优化并支持搜索条件缓存 - 归档

## 归档信息

| 项目 | 内容 |
|------|------|
| FE 需求名称 | 【openLiBing-cicd】流水线列表、详情接口优化并支持搜索条件缓存 |
| 业务仓 Issue | openlibing/openlibing-cicd#185 |
| 业务仓 PR | openlibing/openlibing-cicd#538 |
| 业务仓开发分支 | `pipeline_cache` → `release_20260813_iter1` |
| docs 仓 Issue | openlibing/openlibing-docs#125 |
| docs 仓 PR | openlibing/openlibing-docs#728 |
| docs 仓归档分支 | `spec-openlibing-cicd-pipeline-list-cache-optimization` |
| 归档日期 | 2026-08-05 |

## 实现总结

### 功能概述

本次改造对 `PipelineServiceImpl` 的流水线列表接口进行了性能优化与异常处理修复。核心改动包括：引入 Guava 本地缓存和 Redis 缓存减少重复的 DB 查询与 SDK 客户端构建开销；修复 `getPipelineList` 通用异常捕获时错误返回 `DataResult.success()` 的 P0 缺陷；白名单变更后主动失效 Redis 缓存以保证一致性。

### 核心改动

1. **Guava 本地缓存（P1 + P2）**：新增 `pipelineClientCache` 与 `hwProjectEntityCache` 两个 `Cache<String, Optional<T>>` 本地缓存，TTL 30 分钟，通过 `Cache.get(key, loader)` 实现原子加载，避免每次请求重复解密 AK/SK 与查询数据库；`Optional` 包装支持缓存"查不到"的结果以防止缓存穿透。
2. **白名单 Redis 缓存（P3）**：新增 `getWhitelistPipelineIdSetCached` 方法，将白名单流水线 ID 集合按 `projectId` 缓存到 Redis（TTL 30 秒兜底）；在 `updateWhitelistStatus` 中白名单变更成功后调用 `openlibingRedis.del` 主动删缓存，实现全局零延迟生效；Redis 读/写/删异常时均降级回源数据库。
3. **P0 异常处理修复**：将原来的 `catch (Exception e) { return DataResult.success(); }` 改为返回 `DataResult.failureMessage(...)`，并新增对 `ConnectionException`、`RequestTimeoutException`、`ServiceResponseException` 的精细化捕获，分别返回"网络连接超时""响应超时""获取流水线列表失败"等中文错误提示。
4. **新增私有方法**：`getHwProjectInfoEntityCached` 与 `getPipelineClientCached` 封装带本地缓存的查询逻辑，两者均在 Guava `ExecutionException` 时降级直接查库/直接构建；`getWhitelistPipelineIdSetCached` 封装带 Redis 缓存的白名单查询。
5. **单元测试断言修正**：`testGetPipelineList_Exception` 中 `assertTrue(result.ok())` 改为 `assertFalse(result.ok())`，与 P0 修复保持一致——异常场景下不应伪装成功。

### 缓存设计

| 缓存对象 | 缓存层 | TTL | 隔离维度 | 失效方式 |
|---------|-------|-----|---------|---------|
| `CodeArtsPipelineClient` | Guava 本地缓存 | 30 分钟 | `projectId` | TTL 兜底，AK/SK 轮转后 30 分钟内自动重建 |
| `HwProjectInfoEntity` | Guava 本地缓存 | 30 分钟 | `projectId` | TTL 兜底 |
| 白名单流水线 ID 集合 | Redis | 30 秒 | `projectId` | 主动 `del` + TTL 兜底 |

### 容错设计

- Guava `Cache.get` loader 抛 `ExecutionException` 时捕获后直接查库 / 直接构建 client，记 WARN 日志；
- Redis 读失败时降级回源 DB，记 WARN 日志；
- Redis 写失败时跳过缓存写入，仅记 WARN 日志，下次 miss 再写；
- Redis 主动删失败时主流程已成功，走 30s TTL 兜底最终一致；
- 异常分支均打印 ERROR 日志（含 projectId、请求体、华为云错误详情），便于问题定位。

### 关联 spec

- 完整设计文档：`spec/openlibing-cicd/task_design/pipeline-list-cache-optimization/design.md`
- 需求背景与验收标准：`spec/openlibing-cicd/task_design/pipeline-list-cache-optimization/proposal.md`
- 实现步骤清单：`spec/openlibing-cicd/task_design/pipeline-list-cache-optimization/tasks.md`

## 待办事项

- 测试类 `PipelineServiceImplTest` 需补充 `@Mock private OpenlibingRedis openlibingRedis` 字段声明与 `setField` 注入，并为 `openlibingRedis.get()` / `set()` / `del()` 设置适当的 Mockito stub，避免到达 `filterPipelineList` 或 `updateWhitelistStatus` 成功路径的测试用例抛 NPE（详见 PR #538 行内评论）。
