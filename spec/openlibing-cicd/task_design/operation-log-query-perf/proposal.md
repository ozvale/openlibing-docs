# 操作日志查询性能优化（operation-log-query-perf）

## 需求背景

五个操作日志查询接口在首次查询或服务刚部署后特别慢，第一次查询完成后后续明显变快：

- `/openlibing-cicd/logging/pipelineLog/list`
- `/openlibing-cicd/logging/filter-meta`
- `/openlibing-coderepo/logging/list`
- `/openlibing-coderepo/logging/filter-meta`
- `/openlibing-framework/manage/operation-logs/list`

根因（已核实）：

1. `selectFilterMetaGroupBy` 对 module_id / user_name / resource_name / ip / log_result 五个维度分别执行 GROUP BY + COUNT，WHERE 走 `idx_project_module_time(project_id, module_id, operation_end_time)`，聚合列不在索引内，执行计划退化为回表 + temporary + filesort。
2. cicd / coderepo 两仓 `OperationLogWriteModules.listAllowed()` 每次请求通过 Feign 远程拉取白名单，无缓存；一次 filter-meta 请求内多维度循环会放大远程调用次数。
3. 冷启动开销（连接池懒建连、mapper 首解析、JIT、buffer pool 冷页）解释「首查慢、后续快」。

业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>

## 功能描述

- 阶段一（openlibing-cicd + openlibing-coderepo）：
  - 白名单 TTL 本地缓存（默认 60s，Apollo 可配，失败闭门语义不变）；
  - filter-meta 查询结果 TTL 缓存（默认 30s，key = projectId + 规范化过滤条件 + 时间区间分钟取整），权限校验保持在缓存之前。
- 阶段二（openlibing-framework）：
  - Liquibase 新增 2 个覆盖索引 `(project_id, module_id, operation_end_time, user_name)` 与 `(project_id, module_id, operation_end_time, resource_name)`，幂等可回滚。
- 不做（本期明确排除）：ip / log_result 维度索引（基数低，观察后再定）、framework 白名单端缓存、预热 / 并行 / JOIN 改写。

## 验收标准

- [ ] filter-meta 各维度查询执行计划不再出现 temporary / filesort（EXPLAIN 验证）
- [ ] 白名单远程拉取频次降为每 TTL 窗口一次
- [ ] 接口首查耗时明显下降
- [ ] 权限校验行为不变（校验先于缓存生效）
- [ ] 新增索引幂等可回滚，不影响既有写入链路
- [ ] cicd / coderepo 改动行增量覆盖率 ≥80%

## 影响范围

- openlibing-cicd：`common/operationlog/OperationLogWriteModules.java`、`business/service/impl/LoggingServiceImpl.java`（queryFilterMeta 缓存）、新增缓存组件与单测
- openlibing-coderepo：同名类与同链路改动
- openlibing-framework：`db/changelog/v1.0.1/log_operation_filter_meta_index.xml`（新增）、`db/changelog.xml`（include 注册）
