# 操作日志查询性能优化（operation-log-query-perf）

## 需求背景

五个操作日志查询接口在首次查询或服务刚部署后特别慢，第一次查询完成后后续明显变快：

- `/openlibing-cicd/logging/pipelineLog/list`
- `/openlibing-cicd/logging/filter-meta`
- `/openlibing-coderepo/logging/list`
- `/openlibing-coderepo/logging/filter-meta`
- `/openlibing-framework/manage/operation-logs/list`

根因（已核实）：

1. `selectFilterMetaGroupBy` 对 module_id / user_name / resource_name / ip / log_result 五个维度分别执行 GROUP BY + COUNT，WHERE 走 `idx_project_module_time(project_id, module_id, operation_end_time, id)`，聚合列不在索引内，执行计划退化为回表 + temporary + filesort。
2. cicd / coderepo 两仓 `OperationLogWriteModules.listAllowed()` 每次请求通过 Feign 远程拉取白名单，无缓存；一次 filter-meta 请求内多维度循环会放大远程调用次数。
3. 冷启动开销（连接池懒建连、mapper 首解析、JIT、buffer pool 冷页）解释「首查慢、后续快」。

业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>

## 功能描述

- 阶段一（openlibing-cicd + openlibing-coderepo）：
  - 白名单 TTL 本地缓存（默认 60s，Apollo 可配，失败闭门语义不变）；
  - filter-meta 查询结果 TTL 缓存（默认 30s，key = projectId + 规范化过滤条件 + 时间区间分钟取整），权限校验保持在缓存之前。
- 阶段二（openlibing-framework）【已撤销，未交付】：
  - 原方案为 Liquibase「三合一替换」覆盖索引（先建后删）：新建 `idx_project_module_time_user_resource (project_id, module_id, operation_end_time, id, user_name, resource_name)`，新索引就绪后删除 `idx_project_module_time`（该方案此前已因写放大 +33% 否决过「新增 2 个独立索引」方案）。
  - **撤销原因（PR !560 检视发现）**：6 列索引键长 5105 字节（5×VARCHAR(255) utf8mb4 单列 1020 + DATETIME 5）超 InnoDB 3072 字节上限，CREATE INDEX 必报 ERROR 1071，changeSet 随启动重放阻断应用启动；且分组列位于范围列之后，GROUP BY 无法免 temporary/filesort。方案级否决详见 design.md §1。
- 不做（本期明确排除）：ip / log_result 维度索引（基数低，观察后再定）、framework 白名单端缓存、预热 / 并行 / JOIN 改写；以及任何 log_operation 索引/列宽变更（既有 `idx_project_module_time` 已达 3065 字节贴 InnoDB 上限，当前列宽下不存在可行的覆盖索引，后续如需优化须先评估列宽收缩）。

## 验收标准

- [ ] filter-meta 同参数重复查询在 TTL 窗口内命中缓存、不触达 DB（阶段二索引优化已否决，重复查询收益由缓存承担；首查执行计划不变）
- [ ] 白名单远程拉取频次降为每 TTL 窗口一次
- [ ] 接口首查耗时明显下降
- [ ] 权限校验行为不变（校验先于缓存生效）
- [ ] log_operation 表无任何 DDL 变更：二级索引总数维持 6 个、无列变更（openlibing-framework PR !560 检视后已撤销阶段二，commit `9f347e43`）
- [ ] cicd / coderepo 改动行增量覆盖率 ≥80%

## 影响范围

- openlibing-cicd：`common/operationlog/OperationLogWriteModules.java`、`business/service/impl/LoggingServiceImpl.java`（queryFilterMeta 缓存）、新增缓存组件与单测
- openlibing-coderepo：同名类与同链路改动
- openlibing-framework：无改动（原 changeSet 文件 log_operation_filter_meta_index.xml 与 include 注册已随阶段二整体撤销，commit `9f347e43`）
