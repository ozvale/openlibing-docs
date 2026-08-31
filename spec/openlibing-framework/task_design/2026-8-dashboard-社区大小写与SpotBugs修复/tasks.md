# Dashboard 社区大小写不敏感与 SpotBugs 安全编码修复 — 实现任务

## 进度: 4/4 complete

### Phase 1: pv/uv 统计 URL 模糊匹配

- [x] `PvUvMapper.xml`：`selectByOperationUrlsAndDateRange` SQL 由 `operation_url IN (...)` 改为 `operation_url LIKE CONCAT('%', #{url}, '%') OR ...`
- [x] `PvUvMapper.java`：同步更新方法 Javadoc，说明改用 LIKE 模糊匹配
- [x] `FeatureOpsDashboardServiceImpl.java`：调整调用上下文以适配新签名
- [x] `FeatureOpsDashboardServiceImplTest.java`：补充 LIKE 模糊匹配测试用例
- [x] Commit `515536c7` 提交并验证

### Phase 2: 社区列 collation 恢复

- [x] 新增 `src/main/resources/db/changelog/v1.0.1/dashboard/feature_ops_dashboard_community_case_insensitive.xml`
- [x] `changeSet 20260831_alter_feature_ops_dashboard_report_community_ci`：恢复 `feature_ops_dashboard_report.community` 为 `utf8mb4_0900_ai_ci`
- [x] `changeSet 20260831_alter_feature_ops_dashboard_community_feature_ci`：恢复 `feature_ops_dashboard_community_feature.community` 为 `utf8mb4_0900_ai_ci`
- [x] 在 `db.changelog.xml` 末尾按依赖顺序注册新 changeset
- [x] 保留 `rollback` 块，可回滚为 `utf8mb4_0900_as_cs`
- [x] Commit `499a8c65` 提交并验证

### Phase 3: SpotBugs 安全编码修复

- [x] `DashboardMatrixConfig`：`getCommunities`/`getFeatures` 返回 `Collections.unmodifiableList`
- [x] `DashboardFeatureDetailData`：getter 不可变视图 + setter/builder 防御性拷贝
- [x] `DashboardMatrixData`：同上
- [x] `DashboardMetricConfigData`：同上
- [x] `DashboardMetricConfigRequestDTO`：同上
- [x] `DashboardMetricUpdateRequestDTO`：同上
- [x] `DashboardReportRequestDTO`：同上
- [x] `FeatureOpsDashboardServiceImpl#injectMetricsIntoReports`：移除 BC_VACUOUS_INSTANCEOF
- [x] `FeatureOpsDashboardServiceImplTest`：DTO 测试改用 setter
- [x] SpotBugs 全量扫描通过，BugInstance 由 39 降为 0
- [x] Commit `d5529b82` 提交并验证

### Phase 4: DTO Spotless 单行格式化

- [x] `DashboardFeatureDetailData`：setter/builder 防御性拷贝表达式合并为单行
- [x] `DashboardMatrixData`：matrix 字段 Javadoc 合并为单行
- [x] `DashboardMetricConfigData`：builder aggregationUrls 合并为单行
- [x] `DashboardReportRequestDTO`：setBusinessMetrics 合并为单行
- [x] pre-commit 钩子通过（Gitleaks + Maven All Checks）
- [x] Commit `2f64997a` 提交并验证

### 业务 PR

- [x] openlibing-framework !420「fix(dashboard): community case-insensitive and fix SpotBugs issues」已创建（open 状态，标签 `ai-assisted`）

### 待用户触发（Phase 5 归档）

- [ ] 业务 PR !420 合入后，由用户触发 Phase 5 创建 `archive.md` 沉淀经验
