# Tasks: 运营看板后端接口实现

## 任务清单

### 1. 数据库准备

- [ ] 创建数据库迁移脚本 `V{version}__create_feature_ops_dashboard_tables.sql`
- [ ] 创建 `feature_ops_dashboard_report` 表
- [ ] 创建 `feature_ops_dashboard_metric_config` 表
- [ ] 验证表结构和索引

### 2. Entity 层

- [ ] 创建 `FeatureOpsDashboardReport.java` 实体类
- [ ] 创建 `FeatureOpsDashboardMetricConfig.java` 实体类
- [ ] 添加字段注解（@TableName, @TableId, @TableField）

### 3. DTO 层

- [ ] 创建 `DashboardReportRequestDTO.java` 数据上报请求 DTO
- [ ] 创建 `DashboardReportResponseDTO.java` 数据上报响应 DTO
- [ ] 创建 `DashboardMetricConfigRequestDTO.java` 指标配置请求 DTO
- [ ] 创建 `DashboardMetricConfigResponseDTO.java` 指标配置响应 DTO
- [ ] 添加参数校验注解（@NotBlank, @NotNull, @Size, @Pattern）

### 4. Mapper 层

- [ ] 创建 `FeatureOpsDashboardMapper.java` 接口
- [ ] 创建 `FeatureOpsDashboardMapper.xml` 映射文件
- [ ] 实现 `insertReport()` 方法
- [ ] 实现 `selectByFeature()` 方法
- [ ] 实现 `selectByFeatureAndTimeRange()` 方法
- [ ] 实现 `insertMetricConfig()` 方法
- [ ] 实现 `selectByFeatureAndKey()` 方法
- [ ] 实现 `selectByFeature()` 方法（指标配置）

### 5. Service 层

- [ ] 创建 `FeatureOpsDashboardService.java` 接口
- [ ] 创建 `FeatureOpsDashboardServiceImpl.java` 实现类
- [ ] 实现 `reportData()` 方法
  - [ ] 参数校验与预处理
  - [ ] Community 推断逻辑
  - [ ] 数据存储
  - [ ] 响应构建
- [ ] 实现 `defineMetrics()` 方法
  - [ ] 参数校验
  - [ ] 批量处理指标配置
  - [ ] 唯一性检查
  - [ ] 响应构建
- [ ] 实现 JSON 序列化工具方法
- [ ] 实现时间戳解析工具方法

### 6. 异常处理

- [ ] 创建 `BusinessException.java` 业务异常类
- [ ] 扩展 `ErrorCode.java` 错误码枚举
- [ ] 修改 `GlobalExceptionHandler.java` 添加异常处理
- [ ] 创建 `ErrorResponseDTO.java` 错误响应 DTO

### 7. Controller 层

- [ ] 创建 `FeatureOpsDashboardController.java` 控制器
- [ ] 实现 `POST /openlibing-framework/manage/feature-dashboard/report` 接口
- [ ] 实现 `POST /openlibing-framework/manage/feature-dashboard/metrics` 接口
- [ ] 添加参数校验注解（@Valid）
- [ ] 添加接口文档注解（@Operation, @ApiResponse）

### 8. 单元测试

- [ ] 创建 `FeatureOpsDashboardControllerTest.java`
  - [ ] 测试数据上报接口：所有字段完整上报 → 200
  - [ ] 测试数据上报接口：仅必填字段上报 → 200
  - [ ] 测试数据上报接口：feature 为空 → 400
  - [ ] 测试数据上报接口：userMetrics 为空 → 400
  - [ ] 测试数据上报接口：从 repo 推断 community → 200
  - [ ] 测试指标配置接口：单个指标配置 → 200
  - [ ] 测试指标配置接口：批量指标配置（50 条）→ 200
  - [ ] 测试指标配置接口：批量指标超过 50 条 → 400
  - [ ] 测试指标配置接口：metricType 不合法 → 400
  - [ ] 测试指标配置接口：aggregationType 不合法 → 400
  - [ ] 测试指标配置接口：重复 metricKey → 400
- [ ] 创建 `FeatureOpsDashboardServiceTest.java`
  - [ ] 测试数据上报成功，验证 Mapper 调用
  - [ ] 测试 Community 推断逻辑
  - [ ] 测试 timestamp 为空时使用当前时间
  - [ ] 测试指标配置成功
  - [ ] 测试重复 metricKey 抛出异常
  - [ ] 测试 JSON 序列化
- [ ] 创建 `FeatureOpsDashboardMapperTest.java`
  - [ ] 测试插入上报数据
  - [ ] 测试按 feature 查询
  - [ ] 测试按时间范围查询
  - [ ] 测试插入指标配置
  - [ ] 测试按 feature 和 metricKey 查询
  - [ ] 测试唯一约束冲突

### 9. 集成测试（可选）

- [ ] 创建 `FeatureOpsDashboardIntegrationTest.java`
  - [ ] 测试端到端数据上报流程
  - [ ] 测试端到端指标配置流程

### 10. 验证与文档

- [ ] 运行所有单元测试，确保通过
- [ ] 运行覆盖率报告，确保 ≥80%
- [ ] 检查代码规范（lint）
- [ ] 更新 README 或 API 文档（如需要）

## 修改文件清单

### 新增文件（18 个）

| 序号 | 文件路径 | 说明 |
|------|---------|------|
| 1 | `src/main/resources/db/migration/V{version}__create_feature_ops_dashboard_tables.sql` | 数据库迁移脚本 |
| 2 | `src/main/java/com/openlibing/framework/business/entity/FeatureOpsDashboardReport.java` | 数据上报实体 |
| 3 | `src/main/java/com/openlibing/framework/business/entity/FeatureOpsDashboardMetricConfig.java` | 指标配置实体 |
| 4 | `src/main/java/com/openlibing/framework/business/dto/DashboardReportRequestDTO.java` | 数据上报请求 DTO |
| 5 | `src/main/java/com/openlibing/framework/business/dto/DashboardReportResponseDTO.java` | 数据上报响应 DTO |
| 6 | `src/main/java/com/openlibing/framework/business/dto/DashboardMetricConfigRequestDTO.java` | 指标配置请求 DTO |
| 7 | `src/main/java/com/openlibing/framework/business/dto/DashboardMetricConfigResponseDTO.java` | 指标配置响应 DTO |
| 8 | `src/main/java/com/openlibing/framework/business/dto/ErrorResponseDTO.java` | 错误响应 DTO |
| 9 | `src/main/java/com/openlibing/framework/business/mapper/FeatureOpsDashboardMapper.java` | Mapper 接口 |
| 10 | `src/main/resources/mapper/FeatureOpsDashboardMapper.xml` | Mapper XML |
| 11 | `src/main/java/com/openlibing/framework/business/service/FeatureOpsDashboardService.java` | Service 接口 |
| 12 | `src/main/java/com/openlibing/framework/business/service/impl/FeatureOpsDashboardServiceImpl.java` | Service 实现 |
| 13 | `src/main/java/com/openlibing/framework/business/controller/FeatureOpsDashboardController.java` | Controller |
| 14 | `src/main/java/com/openlibing/framework/common/exception/BusinessException.java` | 业务异常类 |
| 15 | `src/main/java/com/openlibing/framework/common/enums/ErrorCode.java` | 错误码枚举（新增错误码） |
| 16 | `src/test/java/com/openlibing/framework/business/controller/FeatureOpsDashboardControllerTest.java` | Controller 测试 |
| 17 | `src/test/java/com/openlibing/framework/business/service/FeatureOpsDashboardServiceTest.java` | Service 测试 |
| 18 | `src/test/java/com/openlibing/framework/business/mapper/FeatureOpsDashboardMapperTest.java` | Mapper 测试 |

### 修改文件（1 个）

| 序号 | 文件路径 | 修改说明 |
|------|---------|---------|
| 1 | `src/main/java/com/openlibing/framework/common/exception/GlobalExceptionHandler.java` | 新增 BusinessException 处理逻辑 |

## 验证方式

### 1. 单元测试验证

```bash
# 运行所有测试
mvn test

# 运行单个测试类
mvn test -Dtest=FeatureOpsDashboardControllerTest
mvn test -Dtest=FeatureOpsDashboardServiceTest
mvn test -Dtest=FeatureOpsDashboardMapperTest

# 生成覆盖率报告
mvn test jacoco:report
```

### 2. 代码规范验证

```bash
# 运行 lint 检查（根据项目配置）
mvn checkstyle:check
# 或
mvn spotless:check
```

### 3. 接口验证（可选）

```bash
# 启动应用
mvn spring-boot:run

# 测试数据上报接口
curl -X POST http://localhost:8080/openlibing-framework/manage/feature-dashboard/report \
  -H "Content-Type: application/json" \
  -d '{
    "community": "communityA",
    "feature": "feature-dashboard",
    "userMetrics": {"active_users": 150},
    "businessMetrics": {"total_requests": 1000}
  }'

# 测试指标配置接口
curl -X POST http://localhost:8080/openlibing-framework/manage/feature-dashboard/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": [{
      "feature": "feature-dashboard",
      "metricType": "user_metric",
      "metricName": "活跃用户数",
      "metricKey": "active_users",
      "aggregationType": "count",
      "targetValue": "200"
    }]
  }'
```

## 生成前约束检查

在开始编码前，确认以下约束：

- [ ] **范围约束**：只修改 `openlibing-framework` 仓和允许的 `openlibing-docs` 仓
- [ ] **架构约束**：遵循现有 Spring Boot 分层架构（Controller → Service → Mapper）
- [ ] **命名约束**：遵循现有命名风格（参考 `src/main/java/com/openlibing/framework/business/` 下现有代码）
- [ ] **错误处理约束**：使用统一的错误码枚举和全局异常处理器
- [ ] **安全约束**：无硬编码凭证、无敏感信息泄露
- [ ] **测试约束**：有行为变化时必须补充测试，覆盖率 ≥80%
- [ ] **格式约束**：避免无关格式化和元数据 churn

## 预估工作量

| 任务 | 预估时间 | 复杂度 |
|------|---------|--------|
| 数据库准备 | 0.5 小时 | 低 |
| Entity + DTO 层 | 1 小时 | 低 |
| Mapper 层 | 1 小时 | 中 |
| Service 层 | 2 小时 | 中 |
| 异常处理 | 0.5 小时 | 低 |
| Controller 层 | 1 小时 | 低 |
| 单元测试 | 3 小时 | 中 |
| 集成测试 | 1 小时 | 低 |
| 验证与文档 | 0.5 小时 | 低 |
| **总计** | **10.5 小时** | - |

## 风险与依赖

| 风险项 | 缓解措施 | 负责人 |
|--------|---------|--------|
| 数据库表结构变更需要 DBA 审核 | 提前准备 SQL 脚本，与 DBA 沟通 | 开发 |
| 认证权限集成方式未确认 | 标记 TODO，后续对接 | 开发 |
| 测试覆盖率可能不足 | 编写充分的单元测试 | 开发 |

## 里程碑

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | 头脑风暴与需求确认 | ✅ 已完成 |
| Phase 2 | 轻量设计与计划 | ✅ 已完成 |
| Phase 3 | AI 编码交付 | ✅ 已完成 |
| 用户自测 | 用户验收测试 | 🔄 进行中 |
| Phase 4 | 业务 PR 交付 | 待开始 |
| Phase 5 | 最终归档 | 用户触发 |