# 操作日志查询性能优化 — 详细设计

业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>

## 1. 方案设计

### 目标

消除五个日志查询接口（cicd / coderepo 的 list 与 filter-meta、framework 的 operation-logs/list）重复查询的性能问题，并降低 filter-meta 首查中的白名单远程调用放大；首查执行计划与冷启动开销本期不优化（阶段二索引优化已撤销，见下）。权限校验与失败语义保持完全不变。

### 总体方案

原设计分两个阶段，互相独立、可分别交付；**阶段二已在 PR !560 检视后整体撤销，最终交付仅含阶段一**：

**阶段一 —— 查询侧缓存（openlibing-cicd + openlibing-coderepo）**

1. 白名单 TTL 本地缓存：`OperationLogWriteModules.listAllowed()` 增加进程内 TTL 缓存，默认 60s，Apollo 配置可调（`@Value`，与两仓既有配置注入风格一致）。
2. filter-meta 结果 TTL 缓存：`LoggingServiceImpl.queryFilterMeta` 在权限校验通过后按规范化 key 缓存最终 `filterMeta` 结果，默认 30s。

**阶段二 —— 存储侧覆盖索引（openlibing-framework）【已撤销，未交付】**

原方案：log_operation 表以「三合一替换」方式调整索引——删除既有 `idx_project_module_time`，新建覆盖索引 `idx_project_module_time_user_resource (project_id, module_id, operation_end_time, id, user_name, resource_name)`，使 user_name / resource_name 维度的 GROUP BY 获得覆盖索引，索引总数保持 6 个不变。

**撤销原因（PR !560 检视发现，openlibing-framework commit `9f347e43` 已撤销全部 DDL）**：

1. **索引键长超上限（P0，阻断性）**：`log_operation` 相关列（id / module_id / project_id / resource_id / resource_name / user_name）均为 `VARCHAR(255)` 且表已 `CONVERT TO CHARACTER SET utf8mb4`（每字符 4 字节，单列索引键 1020 字节），6 列索引键长 = 5×1020 + 5(DATETIME) = **5105 字节 > InnoDB 单索引 3072 字节上限**，`CREATE INDEX` 必报 ERROR 1071；changeSet 失败不写 DATABASECHANGELOG，随启动重放、每次阻断应用启动。反向佐证：现有 `idx_project_module_time`（3×1020+5=3065 字节）已贴上限，无追加任何列的余量。
2. **列序无法达成设计目标（P3）**：user_name / resource_name 位于范围谓词列 operation_end_time 之后，分组列不连续，GROUP BY 仍走 temporary/filesort，尾列仅提供覆盖扫描；而 5105 字节的超宽键使 16KB 页仅容纳约 3 条键，覆盖扫描收益存疑。
3. **写放大评估修正**：即便可行，覆盖扫描相对阶段一缓存叠加的边际收益，不足以补偿超宽索引对高频写入宽表（INSERT / updateFinish 回填 / 清理 DELETE）的维护成本。

结论：阶段二经检视否决，**性能优化仅交付阶段一**。列宽收缩（schema 变更）、窄索引（如 `(project_id, module_id, user_name)`，3060 字节贴上限且失去时间范围下推）等替代方向均存在明确代价，留待后续按 BETA 实测数据另行评估（不在本期范围）。

冷启动开销（连接池懒建连、mapper 首解析、JIT、buffer pool）不做专项处理：阶段一缓存把首查后的重复查询挡在缓存层，剩余冷启动开销可接受。

### 关键决策

| 决策点                                   | 结论                                                                            | 理由                                                                                                                                                                                                                               |
| ---------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 缓存实现                                 | 手写轻量 TTL 结构，不引入 Caffeine/Guava                                        | 两仓 pom 均无缓存框架依赖；改动最小、无新依赖风险                                                                                                                                                                                  |
| 白名单失败语义                           | 仅缓存「成功且非空」结果；失败/空列表不入缓存，当次请求照旧闭门失败             | 保持现有每请求可重试的失败恢复能力，避免把瞬时故障放大成 60s 全局闭门                                                                                                                                                              |
| filter-meta 缓存 key                     | projectId + 维度集合 + 各维度规范化过滤值 + selectedValues + 时间区间按分钟取整 | 时间按分钟取整提升命中率；分钟级精度对「筛选候选值列表」这类元数据无业务影响                                                                                                                                                       |
| 权限校验与缓存顺序                       | 校验先于缓存读写                                                                | 缓存命中仍要求当前用户是项目成员，行为与现状一致                                                                                                                                                                                   |
| 索引列顺序（已否决）                     | project_id, module_id, operation_end_time, id, user_name, resource_name         | 原设计意图：前三列与既有 `idx_project_module_time` 前缀一致、`id` 紧跟时间列保持索引序免 filesort、尾列使 GROUP BY 免回表；**经检视否决**：6 列键长 5105 字节超 InnoDB 3072 上限必建失败，且分组列位于范围列后本就无法免 temporary |
| 既有 `idx_project_module_time`（已否决） | 不删除（阶段二整体撤销）                                                        | 原方案「三合一替换」依赖覆盖索引建成；覆盖索引经检视否决后，替换失去前提，旧索引保留不动，索引总数维持 6 个                                                                                                                        |
| ip / log_result 维度                     | 不建索引                                                                        | ip 与 log_result 过滤基数低；原拟随阶段二先上 user_name / resource_name 两个高频维度，阶段二已整体撤销，本期不建任何 log_operation 索引，待列宽收缩评估后再定                                                                      |
| framework 白名单端                       | 不做缓存                                                                        | 白名单查询 framework 侧走库内查询，瓶颈在调用频次而非单次耗时；调用方缓存已消除频次问题                                                                                                                                            |

## 2. 实现逻辑设计

### 2.1 白名单缓存（cicd / coderepo，两仓同构）

`OperationLogWriteModules.listAllowed()` 流程调整为：

```
listAllowed()
  ├─ 读内存快照（cachedAllowed, expireAtMs），未过期 → 直接返回快照（拷贝）
  └─ 已过期/无快照 → synchronized
       ├─ 锁内二次检查：快照未过期（已被并发线程刷新）→ 直接返回快照
       ├─ 仍过期 → 拉取 Feign，成功且非空 → 写快照 + expireAtMs = now + ttl，返回
       └─ 失败/空 → 不写快照（保留锁外快照的重试能力），返回 emptyList（闭门失败，语义与现状一致）
```

- 双重检查保证 TTL 到期瞬间并发线程只触发 1 次远程调用，其余线程复用刷新后的快照（两仓单测均含并发双检用例：主线程持锁刷新期间并发线程进入锁后直接命中二次检查，断言远程调用仅 1 次）。

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

### 2.3 覆盖索引 changeSet（framework）【已撤销】

原设计为新增 `db/changelog/v1.0.1/log_operation_filter_meta_index.xml`（两个 changeSet，先 create 新索引、后 drop 旧索引，幂等前置条件 + 双向 rollback），并在 `db.changelog.xml` 注册 include。

**处置**：PR !560 检视发现 6 列覆盖索引键长 5105 字节超 InnoDB 3072 字节上限（详见 §1 阶段二撤销原因），该 changeSet 一旦合入将随服务启动重复失败并阻断启动。已按方案 A **整体撤销阶段二**：删除 changeSet 文件与 include 注册（framework commit `9f347e43`，pre-commit 全部通过），framework 侧不再包含任何 DDL 变更。

## 3. 类设计

| 仓                   | 类                                            | 改动                                                                      |
| -------------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| openlibing-cicd      | `OperationLogWriteModules`                    | 增加缓存字段、TTL `@Value` 配置、`listAllowed()` 缓存逻辑                 |
| openlibing-cicd      | `common/operationlog/FilterMetaCache`（新增） | LRU+TTL 缓存组件：put/get/容量上限                                        |
| openlibing-cicd      | `LoggingServiceImpl`                          | `queryFilterMeta` 接入缓存（key 构建 + 读写副本）                         |
| openlibing-coderepo  | 同名三个类                                    | 同构改动（coderepo 的 `listAllowed` 无 mirror_detail 排除逻辑，其余一致） |
| openlibing-framework | 无 Java 类改动                                | 无任何改动（原阶段二 Liquibase changeSet 经检视撤销）                     |

两仓类结构互为镜像（既有代码即如此：`OperationLogWriteModules` 在两仓各自存在），本次沿用该组织方式，不抽公共库（跨仓共享需走 common SDK 发版，超出本期范围）。

## 4. 数据模型设计

log_operation 表**无任何变化**：无列变更、无索引增删，二级索引总数维持既有 6 个（`idx_operation_time` / `idx_module_time` / `idx_project_module_time` / `idx_project_resource_time` / `idx_user_time` / `idx_account_time`）。

原阶段二「三合一替换」索引方案经 PR !560 检视否决后撤销（撤销理由与证据链见 §1）：核心阻断点是覆盖索引键长 5105 字节超 InnoDB 3072 字节上限；既有 `idx_project_module_time` 本身已达 3065 字节、贴上限无追加余量，说明在当前 VARCHAR(255) × utf8mb4 列宽下该表**不存在可行的超集覆盖索引**，任何索引增强都需先做列宽收缩（schema 变更）并另行评估。

ip / log_result 维度不建索引的结论不变（基数低）。

## 5. 性能设计

- 白名单：每请求 1~N 次 Feign 调用 → 每 TTL 窗口（默认 60s）至多 1 次，P99 时延直接削掉一次远程 RTT。
- filter-meta：同参数组合 30s 窗口内重复查询由 5 次维度 GROUP BY（每次 temporary+filesort）降为 0 次 DB 访问。
- 冷启动：阶段一缓存使首查后的重复查询不再依赖冷路径；不单独做预热。
- filter-meta 各维度执行计划（temporary / filesort）本期**不变**：索引优化经检视否决（§1），同参数重复查询的性能收益由 30s 缓存承担，首查仍走原执行计划。
- 验证方式：本地单测（缓存命中/过期/禁用/失败闭门）+ BETA 环境接口时延对比。

## 6. API接口设计

不涉及。五个 HTTP 接口的路径、入参、出参、权限语义均不变；改动均为服务内部实现与进程内缓存，不涉及任何数据库 DDL / 索引变更。前端无需适配。

## 7. 安全设计

### 鉴权

不变：`checkProjectMember`（cicd 经 `isProjectMember`、coderepo 经 `userRoleMapper.isProjectMember`）仍先于缓存读写执行；缓存命中不绕过校验。缓存内容按 projectId 隔离，key 含 projectId，不存在跨项目数据串扰。

### 敏感信息

不涉及：filter-meta 缓存的仅是维度候选值与计数（筛选元数据），不含 old_data / new_data / ex_message 等敏感正文；白名单缓存仅含 module identification 列表。明细链路的 `OperationLogSensitiveMasker` 脱敏逻辑不动。

### 硬编码

无凭证与敏感常量；TTL 默认值（60s / 30s）走 `@Value` 配置键 + 默认值，可经 Apollo 运行期调整。

### 审计日志

不涉及：查询链路本无审计写入；新增缓存不改变操作日志写入链路（写入链路不调用 `OperationLogWriteModules`）。
