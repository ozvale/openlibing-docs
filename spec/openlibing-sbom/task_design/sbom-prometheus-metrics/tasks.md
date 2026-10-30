# Tasks: sbom-prometheus-metrics

特性分支：`feat-sbom-prometheus-metrics`（最终基线 `prod/release_20261029_iter2`，即 PR 目标分支；PR #167）

## 编码

- [x] 1. `sbom-web/pom.xml`：+`spring-boot-starter-actuator`、+`micrometer-registry-prometheus`
- [x] 2. `sbom-web/src/main/resources/application.properties`：management 端点暴露 + 全局 application 标签
- [x] 3. 新增 `service/metrics/TaskMetricsProvider.java` 通用契约接口
- [x] 4. `dao/RawSbomRepository.java`：+`countByTaskStatus`、+`findRecentTaskStatuses(statuses, Pageable)`
- [x] 5. 新增 `service/metrics/PipelineMetricsService.java`（4 指标查询实现）
- [x] 6. 新增 `config/TaskMetricsMeterBinder.java`（4 Gauge 注册 + 异常 NaN 兜底）
- [x] 7. 新增 `PipelineMetricsServiceTest`（口径 + 边界单测）
- [x] 8. 新增 `TaskMetricsMeterBinderTest`（注册/tag/异常 NaN 单测）

## 口径迭代（用户反馈循环）

- [x] 9. P99 改近 100 条（与成功率同口径）+ 单位改秒（`cac4ee6d`）
- [x] 10. 样本过滤终态 + `raw_sbom` 加 `update_time` 索引（`60d083ae`）

## 检视修复

- [x] 11. ozvale 2 条：成功率空样本 NaN、duration_p99 baseUnit seconds（`573237a1`）
- [x] 12. atomgit-bot 7 条 P3：5 采纳 / 1 部分采纳 / 1 暂缓（`291e31d4`）

## 验证与交付

- [x] 13. `mvn test` 相关单测通过（14 个：口径 + 边界 + Binder + SQL 契约）
- [x] 14. pre-commit 对改动文件检测全部通过
- [x] 15. 合入 sbom-dev 测试环境分支 + 部署验证（`/actuator/prometheus` 输出 4 指标，数值与库内计算一致）
- [x] 16. gamma 库 EXPLAIN ANALYZE 验证索引生效，4 条 SQL 亚毫秒级
- [x] 17. fork 推送 + issue #165 + PR #167
- [x] 18. spec 归档 docs PR（Phase 9）
