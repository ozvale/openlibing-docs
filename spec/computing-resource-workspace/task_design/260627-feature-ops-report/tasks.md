# 260627-feature-ops-report — 实现任务

## 第一期（已完成，6/27）：6/6 complete

- [x] Task 1: 在 `FrameworkClient` 新增 `reportFeatureOps` 方法（参数用 `Map<String, Object>`，响应用 `DataResult<Map<String, Object>>`）
- [x] Task 2: 在 `EnvRecordMapper` 新增 `countByCreatedTimeRange` / `countDistinctUserIdByCreatedTimeRange` 两个聚合查询方法
- [x] Task 3: 新增 `FeatureOpsReportService`，组装 2 个用户指标（page_view/unique_visitor）+ 业务指标留 TODO + timestamp 用统计日 23:59:59 + 异常降级（DB 用 DataAccessException，Feign 用 FeignException）
- [x] Task 4: 新增 `FeatureOpsReportScheduler`，cron 来自 Apollo 配置，开关默认关闭
- [x] Task 5: 在 `application.yaml` 新增 `feature-ops.report.*` 配置项（含 enabled/cron/community/feature/stat-day-offset，带默认值）
- [x] Task 6: 编译通过（`mvn compile`），AI 自检对照生成前约束清单逐条勾选

## 本期（6/29 业务指标扩展）：5/5 complete

- [x] Task 7: 在 `EnvRecordMapper` 新增 4 个业务指标聚合查询方法
  - `avgApplyWaitMinutes(startTime, endTime)` → `Double`，按 `grant_time` 归属
  - `countGrantedByApplyTimeRange(startTime, endTime)` → `long`，按 `apply_time` 归属，`grant_time` 非空
  - `countByApplyTimeRange(startTime, endTime)` → `long`，按 `apply_time` 归属，全部记录
  - `avgUsageMinutesByTaskType(taskType, startTime, endTime)` → `Double`，按 `release_time` 归属 + `task_type`
  - SQL 见 design.md §3.2
- [x] Task 8: 扩展 `FeatureOpsReportService`，新增 `buildBusinessMetrics` 方法
  - 移除原 TODO 注释
  - 组装 4 个业务指标到 `businessMetrics`
  - `apply_wait_mins` / `exclusive_usage_mins` / `task_usage_mins`：AVG 为 null 时不上报该 key
  - `apply_success_rate`：始终上报 `{numerator, denominator}`（分母为 0 时传 `{0,0}`）
  - task_type 常量：`01`=独占式、`02`=任务式
  - DB 查询与用户指标共用同一个 try-catch，任一失败整体不上报
- [x] Task 9: 编译通过（`mvn compile`，exit 0）
- [x] Task 10: AI 自检对照生成前约束清单逐条勾选
  - [x] 只改 workspace 仓 + spec 目录（EnvRecordMapper / FeatureOpsReportService + spec 三件套）
  - [x] 遵循目标仓既有风格（@Select 注解、@Value 注入、Slf4j 日志、DataAccessException/FeignException 分类捕获）
  - [x] 无硬编码凭证、无敏感信息
  - [x] 无新增测试（Standard 模式不强制）
  - [x] 无无关重构（仅扩展，不动第一期已有方法）
  - [x] 无行为变化测试缺口（Mapper 是纯查询、Service 是定时任务，Standard 模式说明后跳过）
- [x] Task 11: 提醒用户在前端看板录入 4 个业务指标 metricKey（`apply_wait_mins` / `apply_success_rate` / `exclusive_usage_mins` / `task_usage_mins`），并提醒 `apply_success_rate` 配 `aggregationType=rate`，其余配 `count`

## 6/30 调整：IDE 不区分社区：1/1 complete

- [x] Task 12: 移除上报请求中的 `community` 字段
  - 删除 `FeatureOpsReportService` 中的 `@Value("${feature-ops.report.community:openLiBing}") private String community;` 注入
  - 删除 `request.put("community", community);` 一行
  - 不动 `feature-ops.report.feature` / `feature-ops.report.stat-day-offset` 配置项
  - commit: `cf1b8b3`

## 6/30 调整：unique_visitor 口径变更（全表累计 UV）：1/1 complete

- [x] Task 13: `unique_visitor` 指标从"当日时间窗去重"改为"全表累计去重"
  - 指标 key 保持 `unique_visitor` 不变（framework 端无需重新注册 metric_config）
  - `EnvRecordMapper`：删除 `countDistinctUserIdByCreatedTimeRange(start, end)`，新增 `countDistinctUserIdAll()`，SQL 为 `SELECT COUNT(DISTINCT user_id) FROM workspace_env_record`（无 WHERE）
  - `FeatureOpsReportService.buildUserMetrics`：调用改为 `envRecordMapper.countDistinctUserIdAll()`
  - 同步更新 JavaDoc（Service 类注释 + Mapper 方法注释）
  - 编译通过（`mvn compile`，exit 0）
  - commit: `148e29a`
  - PR: #13（关联 Issue #7，已打 `ai-assisted` 标签）
