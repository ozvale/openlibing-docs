# 操作日志查询性能优化 — 详细设计

业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>

## 1. 方案设计

### 目标

消除五个日志查询接口（cicd / coderepo 的 list 与 filter-meta、framework 的 operation-logs/list）首查与重复查询的性能问题，同时保持权限校验与失败语义完全不变。

### 总体方案

分两个阶段，互相独立、可分别交付：

**阶段一 —— 查询侧缓存（openlibing-cicd + openlibing-coderepo）**

1. 白名单 TTL 本地缓存：`OperationLogWriteModules.listAllowed()` 增加进程内 TTL 缓存，默认 60s，Apollo 配置可调（`@Value`，与两仓既有配置注入风格一致）。
2. filter-meta 结果 TTL 缓存：`LoggingServiceImpl.queryFilterMeta` 在权限校验通过后按规范化 key 缓存最终 `filterMeta` 结果，默认 30s。

**阶段二 —— 存储侧覆盖索引（openlibing-framework）**

log_operation 表以「三合一替换」方式调整索引：删除既有 `idx_project_module_time`，新建一个覆盖索引（其前缀完整替代旧索引的全部查询能力），使 user_name / resource_name 维度的 GROUP BY 查询获得覆盖索引，消除回表，且索引总数保持 6 个不变：

- 删除 `idx_project_module_time (project_id, module_id, operation_end_time, id)`
- 新增 `idx_project_module_time_user_resource (project_id, module_id, operation_end_time, id, user_name, resource_name)`

冷启动开销（连接池懒建连、mapper 首解析、JIT、buffer pool）不做专项处理：阶段一缓存天然把首查后的重复查询挡在缓存层，阶段二索引缩小扫描面，两者叠加后冷启动剩余开销可接受。

### 关键决策

| 决策点                         | 结论                                                                            | 理由                                                                                                                                                                                                                              |
| ------------------------------ | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 缓存实现                       | 手写轻量 TTL 结构，不引入 Caffeine/Guava                                        | 两仓 pom 均无缓存框架依赖；改动最小、无新依赖风险                                                                                                                                                                                 |
| 白名单失败语义                 | 仅缓存「成功且非空」结果；失败/空列表不入缓存，当次请求照旧闭门失败             | 保持现有每请求可重试的失败恢复能力，避免把瞬时故障放大成 60s 全局闭门                                                                                                                                                             |
| filter-meta 缓存 key           | projectId + 维度集合 + 各维度规范化过滤值 + selectedValues + 时间区间按分钟取整 | 时间按分钟取整提升命中率；分钟级精度对「筛选候选值列表」这类元数据无业务影响                                                                                                                                                      |
| 权限校验与缓存顺序             | 校验先于缓存读写                                                                | 缓存命中仍要求当前用户是项目成员，行为与现状一致                                                                                                                                                                                  |
| 索引列顺序                     | project_id, module_id, operation_end_time, id, user_name, resource_name         | 前三列与既有 `idx_project_module_time` 前缀一致；`id` 紧跟 `operation_end_time` 保持 `ORDER BY operation_end_time DESC, id DESC` 的索引序免 filesort；user_name / resource_name 尾列使两维度 GROUP BY 免回表                      |
| 既有 `idx_project_module_time` | 删除（被新索引前缀完整替代）                                                    | 新索引前三列与其完全一致，任何命中旧索引的查询都可用新索引；删除后索引总数 6→6，日志写入（INSERT / updateFinish 回填 / 清理 DELETE）的索引维护成本零净增；若保留旧索引则 6→8，索引维护 +33%（方案评审时因写入放大顾虑改为三合一） |
| ip / log_result 维度           | 不建索引                                                                        | ip 与 log_result 过滤基数低；本期先上 user_name / resource_name 两个高频维度，观察收益后再定                                                                                                                                      |
| framework 白名单端             | 不做缓存                                                                        | 白名单查询 framework 侧走库内查询，瓶颈在调用频次而非单次耗时；调用方缓存已消除频次问题                                                                                                                                           |

## 2. 实现逻辑设计

### 2.1 白名单缓存（cicd / coderepo，两仓同构）

`OperationLogWriteModules.listAllowed()` 流程调整为：

```
listAllowed()
  ├─ 读内存快照（cachedAllowed, expireAtMs），未过期 → 直接返回快照
  └─ 已过期/无快照 → synchronized 重新拉取 Feign
       ├─ 成功且非空 → 写快照 + expireAtMs = now + ttl，返回
       └─ 失败/空 → 不写快照，返回 emptyList（闭门失败，语义与现状一致）
```

- TTL 配置键（Apollo，`@Value`，支持运行期热更）：cicd 仓 `openlibing.cicd.operation-log.whitelist-cache-ttl-seconds`（默认 60）；coderepo 仓 `openlibing.coderepo.operation-log.whitelist-cache-ttl-seconds`（默认 60）。TTL ≤ 0 视为禁用缓存。
- 快照为不可变 List（拷贝返回），防止调用方污染缓存。

### 2.2 filter-meta 结果缓存（cicd / coderepo，两仓同构）

`LoggingServiceImpl.queryFilterMeta` 流程调整为：

```
queryFilterMeta(query, userId)
  ├─ 参数与权限校验（不变，先于缓存）
  ├─ dimensions 为空 → 原样返回空 map（不进缓存）
  ├─ 时间区间校验（不变）
  ├─ 构建 cacheKey：
  │    projectId + 排序后的 dimensions
  │    + 排序后的 moduleId / logResult / userName / resourceName / ip 过滤值
  │    + 各维度排序后的 selectedValues
  │    + startTime / endTime 按分钟取整（floor/ceil 至分钟边界）
  ├─ 缓存命中（未过期）→ 返回缓存副本
  └─ 未命中 → 走原有多维度循环查询 → 写入缓存 → 返回
```

- 缓存组件：进程内 LRU + TTL，容量上限 256 条（防止异常多的过滤组合撑爆内存），TTL 默认 30s，Apollo 配置键 `openlibing.cicd.operation-log.filter-meta-cache-ttl-seconds` / `openlibing.coderepo.operation-log.filter-meta-cache-ttl-seconds`。TTL ≤ 0 视为禁用。
- 缓存值为 filterMeta map 的深拷贝快照（返回副本），防止调用方/序列化侧改动污染缓存。
- 失败路径（异常返回 failure）不写缓存。
- 敏感信息脱敏（OperationLogSensitiveMasker）发生在明细查询链路，filter-meta 仅含维度候选值与计数，不涉及脱敏逻辑变化。

### 2.3 覆盖索引 changeSet（framework）

新增 `db/changelog/v1.0.1/log_operation_filter_meta_index.xml`，两个 changeSet（**先 create 新索引、后 drop 旧索引**：构建新索引期间旧索引继续服务全部查询，任意时刻至少存在一个 `(project_id, module_id, operation_end_time)` 前缀索引，消除查询裸奔窗口），参照 `iam_account_query_perf_index.xml` 既有风格：

- drop changeSet：`tableExists + indexExists` 双前置条件，`onFail="MARK_RAN"` 幂等；rollback 为重建 `idx_project_module_time`；
- create changeSet：`tableExists + not indexExists` 前置条件，`onFail="MARK_RAN"` 幂等；rollback 为 `dropIndex`；
- 在 `db.changelog.xml` 末尾追加 include 注册。

索引在 BETA 环境由 Liquibase 随服务启动自动执行；上线前用 EXPLAIN 验证 filter-meta 各维度执行计划。

## 3. 类设计

| 仓                   | 类                                            | 改动                                                                      |
| -------------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| openlibing-cicd      | `OperationLogWriteModules`                    | 增加缓存字段、TTL `@Value` 配置、`listAllowed()` 缓存逻辑                 |
| openlibing-cicd      | `common/operationlog/FilterMetaCache`（新增） | LRU+TTL 缓存组件：put/get/容量上限                                        |
| openlibing-cicd      | `LoggingServiceImpl`                          | `queryFilterMeta` 接入缓存（key 构建 + 读写副本）                         |
| openlibing-coderepo  | 同名三个类                                    | 同构改动（coderepo 的 `listAllowed` 无 mirror_detail 排除逻辑，其余一致） |
| openlibing-framework | 无 Java 类改动                                | 仅 Liquibase changeSet 文件 + include 注册                                |

两仓类结构互为镜像（既有代码即如此：`OperationLogWriteModules` 在两仓各自存在），本次沿用该组织方式，不抽公共库（跨仓共享需走 common SDK 发版，超出本期范围）。

## 4. 数据模型设计

log_operation 表无列变化，索引数保持 6 个：删除 1 个、新增 1 个：

| 索引名                                  | 动作 | 列                                                                      |
| --------------------------------------- | ---- | ----------------------------------------------------------------------- |
| `idx_project_module_time`               | 删除 | project_id, module_id, operation_end_time, id                           |
| `idx_project_module_time_user_resource` | 新增 | project_id, module_id, operation_end_time, id, user_name, resource_name |

写放大权衡：log_operation 为写入高频宽表（异步 INSERT、`updateFinish` 回填 operation_end_time、清理 DELETE 三条写路径都要维护全部二级索引）。原方案新增 2 个索引会使索引维护成本 +33%；三合一替换后索引数不变、写入零净增，同时 user_name / resource_name 查询消除回表 + temporary 开销。代价是新索引较宽（多两条 varchar 尾列、树页密度略降），可接受。ip / log_result 维度基数低，不建索引。

## 5. 性能设计

- 白名单：每请求 1~N 次 Feign 调用 → 每 TTL 窗口（默认 60s）至多 1 次，P99 时延直接削掉一次远程 RTT。
- filter-meta：同参数组合 30s 窗口内重复查询由 5 次维度 GROUP BY（每次 temporary+filesort）降为 0 次 DB 访问。
- 覆盖索引：user_name / resource_name 维度 GROUP BY 免回表；moduleId / logResult 维度维持现状（前者本就命中新索引的 `(project_id, module_id, operation_end_time)` 前缀，后者基数 3）；列表查询 `ORDER BY operation_end_time DESC, id DESC` 继续走索引序免 filesort（`id` 紧跟 `operation_end_time`）。
- 冷启动：阶段一缓存使首查后的查询不再依赖冷路径，阶段二降低首查扫描量；不单独做预热。
- 验证方式：本地单测（缓存命中/过期/禁用/失败闭门）+ BETA 环境 EXPLAIN 与接口时延对比。

## 6. API接口设计

不涉及。五个 HTTP 接口的路径、入参、出参、权限语义均不变；改动均为服务内部实现与数据库索引。前端无需适配。

## 7. 安全设计

### 鉴权

不变：`checkProjectMember`（cicd 经 `isProjectMember`、coderepo 经 `userRoleMapper.isProjectMember`）仍先于缓存读写执行；缓存命中不绕过校验。缓存内容按 projectId 隔离，key 含 projectId，不存在跨项目数据串扰。

### 敏感信息

不涉及：filter-meta 缓存的仅是维度候选值与计数（筛选元数据），不含 old_data / new_data / ex_message 等敏感正文；白名单缓存仅含 module identification 列表。明细链路的 `OperationLogSensitiveMasker` 脱敏逻辑不动。

### 硬编码

无凭证与敏感常量；TTL 默认值（60s / 30s）走 `@Value` 配置键 + 默认值，可经 Apollo 运行期调整。

### 审计日志

不涉及：查询链路本无审计写入；新增缓存不改变操作日志写入链路（写入链路不调用 `OperationLogWriteModules`）。
