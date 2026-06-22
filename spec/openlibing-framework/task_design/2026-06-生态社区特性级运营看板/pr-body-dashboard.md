## 变更说明

为 OpenLibing 平台实现运营看板后端接口，支持运营数据统一上报和自定义运营指标配置。解决运营数据上报格式不一致、指标定义分散的问题，为运营看板提供统一的数据接入能力。

## 变更内容

### 接口实现
- `POST /openlibing-framework/manage/feature-dashboard/report`：数据上报接口，支持自定义 userMetrics/businessMetrics
- `POST /openlibing-framework/manage/feature-dashboard/metrics`：指标配置接口，批量支持最多 50 条

### 核心模块
- **Controller**：`FeatureOpsDashboardController`（两个接口）
- **Service**：`FeatureOpsDashboardService` + Impl（业务逻辑、Community 推断、唯一性检查）
- **Mapper**：`FeatureOpsDashboardMapper` + XML（6 个方法）
- **Entity**：`FeatureOpsDashboardReportEntity`、`FeatureOpsDashboardMetricConfigEntity`
- **DTO**：请求/响应 DTO（参数校验注解）

### 数据库
- Liquibase XML 格式：`feature_ops_dashboard_report.xml`、`feature_ops_dashboard_metric_config.xml`
- 包含表结构、索引、唯一约束、回滚脚本

### 测试
- `FeatureOpsDashboardServiceImplTest`：Service 层（9 个测试场景）
- `FeatureOpsDashboardControllerTest`：Controller 层（4 个测试场景）
- `FeatureOpsDashboardMapperTest`：Mapper 层（7 个测试场景）

## 测试计划

- [x] 单元测试编写完成（Service + Controller + Mapper）
- [ ] Liquibase 数据库迁移脚本验证（需 DBA 审核）
- [ ] 本地启动应用验证接口响应
- [ ] 接口参数校验边界场景验证
- [ ] 认证权限集成（TODO：后续对接现有 RBAC）

## 技术要点

- **Community 推断**：从 repo 格式 `community/project` 自动推断
- **聚合类型**：支持 count（计数）和 rate（比率，需 numerator/denominator）
- **唯一约束**：(feature, metricKey) 防止重复配置
- **错误处理**：使用项目现有的 `DataResultFailException`，错误码 3001-3003

## 风险

- 数据库表结构变更需 DBA 审核
- 认证权限集成方式未确认（已标记 TODO）
- 时间段统计接口暂未实现（后续根据运营需求添加）

## 文件统计

- 新增文件：18 个（不含 skills）
- 新增代码：1948 行
- 修改文件：2 个（db.changelog.xml）