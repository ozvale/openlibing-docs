# Proposal: sbom-prometheus-metrics

- 仓名：openlibing-sbom
- 需求名：CCE 云原生监控插件接入 · 步骤① 服务生成 Prometheus 自定义监控指标并暴露采集点
- 参考实现：openlibing-ops MR #209
- 日期：2026-10-26

## 需求背景

CCE 提供云原生监控插件，支持使用 Prometheus 监控自定义指标并上报 AOM。服务接入共 4 步：

1. 服务生成 Prometheus 自定义监控指标，暴露访问点（**本需求范围，代码侧**）；
2. 服务负载（deployment）增加 prometheus 访问地址、访问形式（http/https）等配置（部署侧）；
3. K8S 集群安装云原生监控插件（运维侧）；
4. 数据上报 AOM（平台侧）。

openlibing-sbom 服务目前无任何 `/actuator` 管理端点与 Micrometer 集成，需要按步骤①完成指标生成与暴露。

## 需求范围

在 openlibing-sbom 仓（sbom-web 模块）内：

1. `sbom-web/pom.xml` 增加 `spring-boot-starter-actuator` 与 `micrometer-registry-prometheus` 依赖（版本由 spring-boot-starter-parent 4.1.1 BOM 管理）；
2. `application.properties` 暴露 `health,prometheus` 端点，配置全局 `application` 指标标签；
3. 新增 `TaskMetricsProvider` 通用指标契约接口（对齐参考 MR，多一个 P99 耗时方法）；
4. 新增 `PipelineMetricsService` 实现，提供 4 项指标查询（基于 `raw_sbom` 表 + `sbom_batch_job_execution` 直查）；
5. 新增 `TaskMetricsMeterBinder` 将 Provider 注册为 Micrometer Gauge；
6. `raw_sbom` 新增 `update_time` 单列索引（实体注解声明 + 存量环境手工 DDL），消除近 100 条排序查询的全表扫描；
7. 补充单测。

### 指标口径（用户确认）

| 指标名                   | 口径                                                                                                                                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `sbom_task_running`      | `raw_sbom` 中 `task_status='RUNNING'` 记录数                                                                                                                                                                             |
| `sbom_task_queued`       | `raw_sbom` 中 `task_status='WAIT'` 记录数                                                                                                                                                                                |
| `sbom_task_success_rate` | 终态任务（FINISH/FAILED/FAILED_FINISH）按 update_time 倒序取近 100 条，`FINISH / 样本数`，值域 0~1；无终态样本返回 NaN（区别于 0 = 全部失败）                                                                            |
| `sbom_task_duration_p99` | 任务耗时 P99（秒）：与成功率同口径的近 100 条**终态**任务，取 `sbom_batch_job_execution` 的 `end_time - start_time`，Java 侧计算；注册时声明 baseUnit seconds，暴露名为 `sbom_task_duration_p99_seconds`；无样本返回 NaN |

排队阈值告警由 AOM 侧配置，代码只输出指标。

## 验收标准

1. 新增单测覆盖 4 项指标口径与边界（空表、无终态、无 P99 样本）及 Binder 注册/tag/异常 NaN，`mvn test` 通过；
2. 本地启动后 `curl http://localhost:13331/actuator/prometheus | grep sbom_task` 可见 4 个指标；
3. pre-commit 对改动文件检测全部通过；
4. 测试环境部署后云原生监控插件可抓取 `sbom_task_*` 指标（步骤②③④配合，非本仓代码范围）。

## 设计文档

- spec：`openlibing-docs/spec/openlibing-sbom/task_design/sbom-prometheus-metrics/`（本目录）
