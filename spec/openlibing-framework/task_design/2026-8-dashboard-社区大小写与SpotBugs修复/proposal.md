# Dashboard 社区大小写不敏感与 SpotBugs 安全编码修复

## 需求背景

特性运营看板（FeatureOpsDashboard）在 2026-08 迭代中暴露了三类问题：

1. **社区名称大小写不一致**：上游 `20260824_alter_*_community_cs` changeset 曾将 `feature_ops_dashboard_report` 与 `feature_ops_dashboard_community_feature` 两表的 `community` 列 collation 改为 `utf8mb4_0900_as_cs`（大小写敏感），导致同一社区以 `OpenLibing` / `openlibing` 等不同大小写上报时被拆成两条记录，看板聚合数据偏差。
2. **pv/uv 统计 URL 精确匹配过严**：`PvUvMapper.selectByOperationUrlsAndDateRange` 使用 `operation_url IN (...)` 精确匹配，而 metric 配置中的 `aggregationUrls` 通常只记录路径片段（如 `/api/v1/projects`），实际请求 URL 带有 query string 或前缀，导致聚合统计漏报。
3. **SpotBugs MALICIOUS_CODE 告警**：dashboard DTO 与配置类直接返回内部可变集合（`List`/`Map`），存在 EI_EXPOSE_REP / EI_EXPOSE_REP2 风险；`FeatureOpsDashboardServiceImpl#injectMetricsIntoReports` 中存在无意义的 `instanceof` 检查（BC_VACUOUS_INSTANCEOF），共 39 个 BugInstance。

## 功能描述

### 做什么

1. **社区列恢复大小写不敏感 collation**：新增 Liquibase changeset `feature_ops_dashboard_community_case_insensitive.xml`，将两张 dashboard 表的 `community` 列 collation 还原为 `utf8mb4_0900_ai_ci`，撤销 `20260824_alter_*_community_cs` 改动。Java/Mapper 层无需修改，case sensitivity 由 DB collation 决定。
2. **pv/uv 统计 URL 改为模糊匹配**：`PvUvMapper.selectByOperationUrlsAndDateRange` 的 SQL 由 `operation_url IN (...)` 改为 `operation_url LIKE CONCAT('%', #{url}, '%') OR ...`，使聚合 URL 作为子串命中实际请求 URL。
3. **SpotBugs 安全编码修复**：
   - dashboard DTO/配置类（`DashboardMatrixConfig`、`DashboardFeatureDetailData`、`DashboardMatrixData`、`DashboardMetricConfigData`、`DashboardMetricConfigRequestDTO`、`DashboardMetricUpdateRequestDTO`、`DashboardReportRequestDTO`）的 getter 返回 `Collections.unmodifiableList/Map`，setter/builder 对入参做防御性拷贝（`new LinkedHashMap/ArrayList`）。
   - 移除 `FeatureOpsDashboardServiceImpl#injectMetricsIntoReports` 中无意义的 `instanceof` 检查。
4. **DTO Spotless 单行格式化**：对防御性拷贝相关 setter/builder 进行 Spotless 单行格式化，无行为变化。

### 不做什么

- 不修改 `feature` 列 collation（保持原有大小写敏感）。
- 不调整 Dashboard 看板的查询 API 契约（请求/响应字段不变）。
- 不修改 metric 配置中 `aggregationUrls` 的存储格式（仍是 JSON 数组字符串）。
- 不重构 dashboard DTO 类结构，仅修改 getter/setter/builder 的防御性拷贝逻辑。
- 不为本次变更单独创建业务 Issue（用户确认走 PR-only 流程，PR !420 即为业务交付入口）。

## 验收标准

- [ ] `feature_ops_dashboard_report.community` 与 `feature_ops_dashboard_community_feature.community` 列 collation 为 `utf8mb4_0900_ai_ci`，`OpenLibing` 与 `openlibing` 视为同一社区。
- [ ] 数据上报与所有看板查询接口对社区名称大小写不敏感。
- [ ] `PvUvMapper.selectByOperationUrlsAndDateRange` 使用 LIKE 模糊匹配，记录的 `operation_url` 包含任一聚合 URL 作为子串即命中。
- [ ] dashboard DTO 的 getter 返回不可变视图，外部修改不影响内部状态。
- [ ] dashboard DTO 的 setter/builder 对入参做防御性拷贝，外部修改入参不影响内部状态。
- [ ] `FeatureOpsDashboardServiceImpl#injectMetricsIntoReports` 无 BC_VACUOUS_INSTANCEOF 告警。
- [ ] SpotBugs 全量扫描通过，BugInstance 数量由 39 降为 0。
- [ ] `FeatureOpsDashboardServiceImplTest` 通过，覆盖 LIKE 模糊匹配与社区大小写不敏感场景。
- [ ] pre-commit 钩子通过（Gitleaks + Maven All Checks: Spotless + CheckStyle + SpotBugs + PMD）。

## 影响范围

| 模块                | 影响 | 说明                                                                                                                              |
| ------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------- |
| 数据库 schema       | 修改 | `feature_ops_dashboard_report.community`、`feature_ops_dashboard_community_feature.community` 恢复 `utf8mb4_0900_ai_ci` collation |
| Liquibase changelog | 新增 | `v1.0.1/dashboard/feature_ops_dashboard_community_case_insensitive.xml`，注册到 `db.changelog.xml`                                |
| PvUvMapper          | 修改 | `selectByOperationUrlsAndDateRange` SQL 由 IN 改为 LIKE 模糊匹配                                                                  |
| Dashboard DTO       | 修改 | 7 个 DTO/Config 类的 getter/setter/builder 增加防御性拷贝与不可变视图                                                             |
| Dashboard Service   | 修改 | `FeatureOpsDashboardServiceImpl` 移除 instanceof 检查                                                                             |
| 单元测试            | 修改 | `FeatureOpsDashboardServiceImplTest` 补充模糊匹配与大小写不敏感测试用例                                                           |
| 业务仓 PR           | 关联 | openlibing-framework !420 「fix(dashboard): community case-insensitive and fix SpotBugs issues」                                  |
