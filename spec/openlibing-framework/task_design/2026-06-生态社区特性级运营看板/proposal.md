# Proposal: 运营看板后端接口实现

## 需求背景

OpenLibing 平台需要为运营团队提供数据上报和自定义运营指标的能力，用于构建运营看板，监控各特性的运营效果。

当前痛点：
1. 运营数据上报缺乏统一接口，各特性自行实现，数据格式不一致
2. 运营指标定义分散，缺乏统一管理和配置能力
3. 无法灵活定义和聚合自定义运营指标

## 目标

实现两个核心后端接口：
1. **数据上报接口**：支持运营数据统一上报，包含用户指标和业务指标
2. **自定义运营指标接口**：支持运营人员灵活定义和配置运营指标

## 验收标准

### 功能验收

| 功能点 | 验收标准 |
|--------|---------|
| 数据上报接口 | POST `/openlibing-framework/manage/feature-dashboard/report` 可正常调用，返回 200 |
| 参数校验 | 必填字段缺失返回 400，错误信息清晰 |
| Community 推断 | 从 repo 正确推断 community（格式：community/project） |
| JSON 存储 | userMetrics/businessMetrics 正确序列化并存储到 MySQL |
| 指标配置接口 | POST `/openlibing-framework/manage/feature-dashboard/metrics` 可正常调用，返回 200 |
| 批量限制 | 批量指标超过 50 条返回 400，错误码 3004 |
| 唯一性约束 | 同一 (feature, metricKey) 重复定义返回 400，错误码 3003 |
| 聚合类型校验 | 非法 aggregationType 返回 400，错误码 3002 |

### 质量验收

| 质量指标 | 目标 |
|---------|------|
| 单元测试覆盖率 | ≥80% |
| 单元测试通过率 | 100% |
| 集成测试 | 端到端流程通过 |
| 代码规范 | 通过项目 lint 检查 |

### 非功能验收

| 指标 | 要求 |
|------|------|
| 接口响应时间 | ≤200ms（P95） |
| 数据一致性 | MySQL 两张表数据一致 |
| 错误处理 | 所有异常有明确的错误码和消息 |

## 影响范围

### 新增内容

| 类型 | 文件路径 | 说明 |
|------|---------|------|
| Controller | `src/main/java/com/openlibing/framework/business/controller/FeatureOpsDashboardController.java` | 新增控制器 |
| Service | `src/main/java/com/openlibing/framework/business/service/FeatureOpsDashboardService.java` | 新增服务接口 |
| Service Impl | `src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java` | 新增服务实现 |
| Mapper | `src/main/java/com/openlibing/framework/business/mapper/FeatureOpsDashboardMapper.java` | 新增 Mapper 接口 |
| Mapper XML | `src/main/resources/mapper/FeatureOpsDashboardMapper.xml` | 新增 Mapper XML |
| Entity | `src/main/java/com/openlibing/framework/business/entity/FeatureOpsDashboardReport.java` | 新增上报数据实体 |
| Entity | `src/main/java/com/openlibing/framework/business/entity/FeatureOpsDashboardMetricConfig.java` | 新增指标配置实体 |
| DTO | `src/main/java/com/openlibing/framework/business/dto/DashboardReportRequestDTO.java` | 新增上报请求 DTO |
| DTO | `src/main/java/com/openlibing/framework/business/dto/DashboardReportResponseDTO.java` | 新增上报响应 DTO |
| DTO | `src/main/java/com/openlibing/framework/business/dto/DashboardMetricConfigRequestDTO.java` | 新增指标配置请求 DTO |
| DTO | `src/main/java/com/openlibing/framework/business/dto/DashboardMetricConfigResponseDTO.java` | 新增指标配置响应 DTO |
| Exception | `src/main/java/com/openlibing/framework/common/exception/BusinessException.java` | 新增业务异常类 |
| Enum | `src/main/java/com/openlibing/framework/common/enums/ErrorCode.java` | 新增错误码枚举 |
| SQL | `src/main/resources/db/migration/V{version}__create_feature_ops_dashboard_tables.sql` | 新增建表脚本 |
| Test | `src/test/java/com/openlibing/framework/business/controller/FeatureOpsDashboardControllerTest.java` | 新增 Controller 测试 |
| Test | `src/test/java/com/openlibing/framework/business/service/FeatureOpsDashboardServiceTest.java` | 新增 Service 测试 |
| Test | `src/test/java/com/openlibing/framework/business/mapper/FeatureOpsDashboardMapperTest.java` | 新增 Mapper 测试 |

### 修改内容

| 类型 | 文件路径 | 修改说明 |
|------|---------|---------|
| 全局异常处理器 | `src/main/java/com/openlibing/framework/common/exception/GlobalExceptionHandler.java` | 新增 BusinessException 处理逻辑 |

### 依赖变更

无新增外部依赖，使用现有技术栈：
- Spring Boot 3.4.4
- MyBatis
- MySQL 8.0+
- JUnit 5 + Mockito

## 技术方案概要

采用标准 Spring Boot 分层架构：

```
Controller → Service → Mapper → MySQL
```

数据存储：
- `feature_ops_dashboard_report`：存储上报数据
- `feature_ops_dashboard_metric_config`：存储指标配置

认证权限：
- 利用现有 RBAC 权限体系验证 Token 和 Admin 角色（TODO）

时间段统计：
- 应用层聚合，暂不在数据库层做复杂统计

详细设计见 `design.md`。

## 风险与依赖

| 风险项 | 影响 | 缓解措施 |
|--------|------|---------|
| 数据库表结构变更 | 需要 DBA 审核 | 提前沟通，准备 SQL 脚本 |
| 认证权限集成 | 需要确认现有 RBAC 集成方式 | 标记 TODO，后续对接 |
| 测试覆盖率 | 需要达到 80% | 编写充分的单元测试 |

## 里程碑

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| Phase 1 | 头脑风暴与需求确认 | ✅ 已完成 |
| Phase 2 | 轻量设计与计划 | 待开始 |
| Phase 3 | AI 编码交付 | 待开始 |
| 用户自测 | 用户验收测试 | 待开始 |
| Phase 4 | 业务 PR 交付 | 待开始 |
| Phase 5 | 最终归档 | 用户触发 |

## 参考

- 接口规范文档：`openlibing-docs/temp_designs/dashboard-report-api-spec.md`
- 项目 README：`openlibing-framework/README.md`