# Design: sbom-prometheus-metrics

固定七章 + 验收。

## 1. 方案设计

采用 openlibing-ops MR #209 的通用契约模式，按 sbom 仓技术栈（JPA/Hibernate + PostgreSQL）适配：

- `TaskMetricsProvider` 通用接口：业务场景实现该接口即可接入 Prometheus；
- `PipelineMetricsService` 实现接口：基于 `raw_sbom` 与 Spring Batch 执行历史表提供 4 项指标；
- `TaskMetricsMeterBinder`（`MeterBinder`）：将所有 Provider 注册为带 `scenario` 标签的 Gauge；
- `spring-boot-starter-actuator` + `micrometer-registry-prometheus` 暴露 `/actuator/prometheus` 供 CCE 云原生监控插件抓取，经插件上报 AOM。

纯后端改造，仅 openlibing-sbom 单仓，前端/网关不涉及。

## 2. 实现逻辑设计

指标链路：Gauge（懒求值，抓取时执行查询）← Prometheus 抓取 `/actuator/prometheus` ← 云原生监控插件 ← AOM。

状态口径（与 `SbomServiceImpl#SCAN_STATUS_LABELS` 一致）：

| task_status            | 含义             | 归属            |
| ---------------------- | ---------------- | --------------- |
| WAIT                   | 等待解析         | queued          |
| RUNNING                | 解析中           | running         |
| FINISH_PARSE           | 解析中（中间态） | 不计入          |
| FINISH                 | 解析完成         | 成功率分子+分母 |
| FAILED / FAILED_FINISH | 解析失败（终态） | 成功率分母      |
| VUL_REFRESHING         | 漏洞信息刷新中   | 不计入          |

查询逻辑：

- running/queued：`count by taskStatus`（JPA 派生查询）；
- successRate：终态（FINISH/FAILED/FAILED_FINISH）按 `update_time` 倒序取最近 100 条（仅投影 task_status 列），成功率 = FINISH / 样本数；中间态不入样本；无终态样本返回 NaN（NaN=无数据，区别于 0 = 全部失败）；
- durationP99：JdbcTemplate SQL（终态与 LIMIT 由 `TERMINAL_STATUSES` / `RECENT_LIMIT` 常量驱动生成占位符并绑定参数，两指标口径结构性同源）：

```sql
SELECT EXTRACT(EPOCH FROM (e.end_time - e.start_time))
FROM sbom_batch_job_execution e
WHERE e.job_execution_id IN (
    SELECT r.job_execution_id FROM raw_sbom r
    WHERE r.task_status IN ('FINISH', 'FAILED', 'FAILED_FINISH')
    ORDER BY r.update_time DESC LIMIT 100)
AND e.start_time IS NOT NULL AND e.end_time IS NOT NULL
```

EXTRACT(EPOCH) 直接返回秒，Java 侧排序取 `index = ceil(0.99 * n) - 1`；无样本返回 NaN。
路径决策：Spring Batch 6 `JobRepository` API 无耗时聚合方法、无该表 JPA 实体，故按用户指定直查方案。

边界与异常：

- Provider 查询抛 RuntimeException：Binder 兜底 catch → error 日志（含 scenario）→ 返回 NaN，不阻断其他指标；
- 空表/无终态：running/queued=0，successRate=NaN；
- P99 无样本：NaN；终态任务缺失 job_execution_id 或起止时间的记录不入样本（数据完整性过滤，有效样本数可能少于成功率样本数，gamma 实证 100→97）；
- `update_time` 恒非空前提：由 Hibernate `@UpdateTimestamp` 在插入/更新时写入，gamma 库 652 行实证 0 条 NULL（DB 列本身允许 NULL，保证来自 ORM 层），`ORDER BY update_time DESC` 无需 NULLS LAST；若后续出现绕过 ORM 的数据修复路径，再评估 SQL 增加 `IS NOT NULL` / `NULLS LAST` 防御（见 archive 遗留）。

## 3. 类设计

均位于 sbom-web 模块：

| 类                       | 包                                       | 职责                                                                                                                                                                  |
| ------------------------ | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TaskMetricsProvider`    | `org.opensourceway.sbom.service.metrics` | 接口：`scenario()` / `runningTasks()` / `queuedTasks()` / `successRate()` / `durationP99Seconds()`                                                                    |
| `PipelineMetricsService` | 同上                                     | @Service 实现，scenario=sbom；依赖 `RawSbomRepository` + `JdbcTemplate`                                                                                               |
| `TaskMetricsMeterBinder` | `org.opensourceway.sbom.config`          | @Component 实现 `MeterBinder`，注册 4 Gauge（带 description/baseUnit）+ tag + safeValue 兜底；Provider 注入 `required=false` + 空列表默认值，无 Provider 时不阻断启动 |

`RawSbomRepository` 补充 2 个查询：

```java
long countByTaskStatus(String taskStatus);

@Query("SELECT rs.taskStatus FROM RawSbom rs WHERE rs.taskStatus IN :statuses "
    + "ORDER BY rs.updateTime DESC")
List<String> findRecentTaskStatuses(
    @Param("statuses") Collection<String> statuses, Pageable pageable);
```

状态常量复用 `SbomConstants.TASK_STATUS_*`；表前缀 `sbom_batch_` 与 `@EnableJdbcJobRepository(tablePrefix="sbom_batch_")` 配置一致（编译期常量）。

## 4. 数据模型设计

表结构无新增表/字段变更，仅一处索引变更：`raw_sbom` 新增 `idx_raw_sbom_update_time`（单列 `update_time`），支撑成功率/P99 的近 100 条排序查询，消除执行计划验证发现的全表扫描。落地：`RawSbom` 实体 `@Table` 注解声明 + 存量环境手工 DDL（本项目无迁移脚本机制，`ddl-auto=none`）：

```sql
CREATE INDEX CONCURRENTLY idx_raw_sbom_update_time ON raw_sbom (update_time);
```

指标读取仍全部来自既有表：`raw_sbom`（读 task_status/update_time/job_execution_id）与 `sbom_batch_job_execution`（Spring Batch 管理表，只读）；Micrometer 指标为内存态不落库。

## 5. 性能设计

- 查询触发频率 = Prometheus 抓取周期（15~30s），每次 4 个查询，频率低；
- 近 100 条排序查询由 `idx_raw_sbom_update_time`（update_time 单列索引）支撑，gamma 环境 EXPLAIN ANALYZE 验证走 Index Scan、亚毫秒级；`task_status` 计数查询当前全表扫描，`raw_sbom` 千级量级下成本可忽略，规模增长后再评估 `task_status` 索引/partial index；
- 近 100 条仅投影 task_status 单列，不触碰 value BYTEA 大字段；
- P99 样本量 ≤ raw_sbom 行数级，Java 排序 O(n log n) 无压力；
- 无缓存：成本低、实时性优先。

## 6. API 接口设计

业务 REST 接口无任何变化，前端无感。新增 Actuator 端点：

| 端点                   | 方法 | 说明                            |
| ---------------------- | ---- | ------------------------------- |
| `/actuator/prometheus` | GET  | Prometheus 文本格式指标（新增） |
| `/actuator/health`     | GET  | 健康检查                        |

配置（application.properties，全环境生效）：

```properties
management.endpoints.web.exposure.include=health,prometheus
management.endpoint.prometheus.enabled=true
management.metrics.tags.application=${spring.application.name}
```

输出样例：

```text
sbom_task_running{scenario="sbom",application="openlibing-sbom"} 3.0
sbom_task_queued{scenario="sbom",application="openlibing-sbom"} 1.0
sbom_task_success_rate{scenario="sbom",application="openlibing-sbom"} 0.95
sbom_task_duration_p99_seconds{scenario="sbom",application="openlibing-sbom"} 184.21
```

4 个 Gauge 均带 description（暴露为 HELP 文本）；`duration_p99` 声明 `baseUnit("seconds")` 故指标名带单位后缀。查询异常时指标值 NaN，端点不返回 5xx。

## 7. 安全设计

- 仅暴露 `health,prometheus`，不暴露 env/configprops/heapdump 等敏感端点；
- 管理端点默认与业务端口同监听（代码侧未配 `management.server.port`），代码侧访问收敛约定：`/actuator/prometheus` 仅允许集群内（云原生监控插件）抓取，禁止经外部 ingress/LB 暴露；**上线前置条件**为步骤②部署侧确认网关路由白名单不含 `/actuator`、集群内仅监控插件可达；如需端口级隔离，由步骤②启用独立 `management.server.port` 或 NetworkPolicy，代码侧不额外引入；
- 指标 SQL 全部为固定常量 SQL，无外部入参拼接，无注入风险；
- 不读取/输出任何凭证与敏感信息；
- micrometer 版本由 spring-boot-starter-parent 4.1.1 BOM 管理，随平台安全基线治理。

## 8. 验收标准

1. 单测覆盖 4 指标口径 + 边界 + Binder 注册/tag/异常 NaN，`mvn test` 通过；
2. 本地 `curl http://localhost:13331/actuator/prometheus | grep sbom_task` 可见 4 指标；
3. pre-commit 检测全部通过；
4. 测试环境部署后云原生监控插件可抓取（步骤②③④配合）。
