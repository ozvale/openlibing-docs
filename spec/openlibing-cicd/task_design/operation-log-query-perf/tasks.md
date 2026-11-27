# 操作日志查询性能优化 — 实现任务

业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>

## 进度: 8/8 complete

- [x] Task 1: openlibing-cicd — `OperationLogWriteModules` 白名单 TTL 缓存（默认 60s，Apollo `openlibing.cicd.operation-log.whitelist-cache-ttl-seconds`；仅缓存成功非空结果）
- [x] Task 2: openlibing-cicd — 新增 `FilterMetaCache`（LRU 256 + TTL，默认 30s）并接入 `LoggingServiceImpl.queryFilterMeta`（权限校验先于缓存；key 含 projectId+维度+规范化过滤值+selectedValues+时间分钟取整）
- [x] Task 3: openlibing-cicd — 单元测试（缓存命中/过期/禁用/失败闭门/副本防污染）并运行相关验证
- [x] Task 4: openlibing-coderepo — 同构 Task 1（`openlibing.coderepo.operation-log.whitelist-cache-ttl-seconds`）
- [x] Task 5: openlibing-coderepo — 同构 Task 2/3（含单测）
- [x] Task 6: openlibing-framework — 新增 `db/changelog/v1.0.1/log_operation_filter_meta_index.xml`（三合一，先建后删：create `idx_project_module_time_user_resource (project_id, module_id, operation_end_time, id, user_name, resource_name)` → drop `idx_project_module_time`，幂等前置条件 + 双向 rollback；索引总数 6→6，写入零净增，任意时刻至少一个前缀索引可用）
- [x] Task 7: openlibing-framework — `db.changelog.xml` 注册 include；确认构建通过（`mvn -DskipTests compile` 通过，XML 良构校验通过，无 Java 改动故无覆盖率要求）
- [x] Task 8: 增量覆盖率实测（`python .agents/scripts/incremental_coverage.py`，cicd / coderepo ≥80%）+ Phase 3 自检（含接口变动检测：无 HTTP 接口签名变化）

> 覆盖率实测（2026-11-27）：两仓 CI 同口径（`--ignore-absent`，与 ut.yml diff-cover 一致）均为 **100% = 74/74（cicd）、72/72（coderepo）可测改动行全覆盖，未覆盖 0**；本地默认严口径（未采集行计入分母）为 43.02% / 42.60%，差异行均为导入、字段声明、括号等未进入 JaCoCo 报告的非可执行行。证据：`.temp/cicd-incr-cov-ci.json`、`.temp/coderepo-incr-cov-ci.json`。
