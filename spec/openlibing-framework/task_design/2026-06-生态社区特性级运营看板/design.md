# Design: 运营看板后端接口实现

## 技术选型

| 技术 | 版本 | 说明 |
|------|------|------|
| Java | 21 | 项目统一版本 |
| Spring Boot | 3.4.4 | 项目统一版本 |
| MyBatis | - | 数据持久层 |
| MySQL | 8.0+ | 数据存储 |
| Redis | 6.0+ | 缓存（暂不使用） |
| JUnit 5 | - | 单元测试框架 |
| Mockito | - | Mock 框架 |

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Controller 层                         │
│  FeatureOpsDashboardController                          │
│  - POST /openlibing-framework/manage/feature-dashboard/report │
│  - POST /openlibing-framework/manage/feature-dashboard/metrics │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Service 层                            │
│  FeatureOpsDashboardService (接口)                      │
│  FeatureOpsDashboardServiceImpl (实现)                  │
│  - reportData()                                         │
│  - defineMetrics()                                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    Mapper 层                             │
│  FeatureOpsDashboardMapper                              │
│  - insertReport()                                       │
│  - selectByFeature()                                    │
│  - insertMetricConfig()                                 │
│  - selectByFeatureAndKey()                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    MySQL 数据库                          │
│  - feature_ops_dashboard_report                         │
│  - feature_ops_dashboard_metric_config                  │
└─────────────────────────────────────────────────────────┘
```

### 模块结构

```
src/main/java/com/openlibing/framework/
├── business/
│   ├── controller/
│   │   └── FeatureOpsDashboardController.java
│   ├── service/
│   │   ├── FeatureOpsDashboardService.java
│   │   └── impl/
│   │       └── FeatureOpsDashboardServiceImpl.java
│   ├── mapper/
│   │   └── FeatureOpsDashboardMapper.java
│   ├── entity/
│   │   ├── FeatureOpsDashboardReport.java
│   │   └── FeatureOpsDashboardMetricConfig.java
│   └── dto/
│       ├── DashboardReportRequestDTO.java
│       ├── DashboardReportResponseDTO.java
│       ├── DashboardMetricConfigRequestDTO.java
│       └── DashboardMetricConfigResponseDTO.java
├── common/
│   ├── exception/
│   │   ├── BusinessException.java
│   │   └── GlobalExceptionHandler.java (修改)
│   └── enums/
│       └── ErrorCode.java
└── resources/
    ├── mapper/
    │   └── FeatureOpsDashboardMapper.xml
    └── db/migration/
        └── V{version}__create_feature_ops_dashboard_tables.sql
```

## 数据库设计

### 表一：feature_ops_dashboard_report（数据上报表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| report_id | VARCHAR(36) | UNIQUE, NOT NULL | 上报 ID（UUID） |
| community | VARCHAR(100) | INDEX | 社区名称 |
| feature | VARCHAR(100) | NOT NULL, INDEX | 特性名称 |
| user_metrics | JSON | NOT NULL | 用户指标（JSON） |
| business_metrics | JSON | NOT NULL | 业务指标（JSON） |
| reported_at | DATETIME | NOT NULL | 上报时间 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- PRIMARY KEY (id)
- UNIQUE KEY uk_report_id (report_id)
- INDEX idx_community (community)
- INDEX idx_feature (feature)
- INDEX idx_reported_at (reported_at)

### 表二：feature_ops_dashboard_metric_config（指标配置表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| metric_id | VARCHAR(36) | UNIQUE, NOT NULL | 指标 ID（UUID） |
| feature | VARCHAR(100) | NOT NULL, INDEX | 特性名称 |
| metric_type | VARCHAR(20) | NOT NULL | 指标类型（user_metric/business_metric） |
| metric_name | VARCHAR(50) | NOT NULL | 指标名称 |
| metric_key | VARCHAR(50) | NOT NULL | 指标标识 |
| aggregation_type | VARCHAR(20) | NOT NULL | 统计方式（count/rate） |
| target_value | TEXT | NOT NULL | 目标值（JSON 字符串） |
| description | VARCHAR(500) | | 指标说明 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- PRIMARY KEY (id)
- UNIQUE KEY uk_metric_id (metric_id)
- UNIQUE KEY uk_feature_metric_key (feature, metric_key)
- INDEX idx_feature (feature)
- INDEX idx_metric_type (metric_type)

### SQL 脚本

```sql
-- 创建数据上报表
CREATE TABLE feature_ops_dashboard_report (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    report_id VARCHAR(36) NOT NULL COMMENT '上报 ID（UUID）',
    community VARCHAR(100) COMMENT '社区名称',
    feature VARCHAR(100) NOT NULL COMMENT '特性名称',
    user_metrics JSON NOT NULL COMMENT '用户指标（JSON）',
    business_metrics JSON NOT NULL COMMENT '业务指标（JSON）',
    reported_at DATETIME NOT NULL COMMENT '上报时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_report_id (report_id),
    INDEX idx_community (community),
    INDEX idx_feature (feature),
    INDEX idx_reported_at (reported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运营看板数据上报表';

-- 创建指标配置表
CREATE TABLE feature_ops_dashboard_metric_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    metric_id VARCHAR(36) NOT NULL COMMENT '指标 ID（UUID）',
    feature VARCHAR(100) NOT NULL COMMENT '特性名称',
    metric_type VARCHAR(20) NOT NULL COMMENT '指标类型（user_metric/business_metric）',
    metric_name VARCHAR(50) NOT NULL COMMENT '指标名称',
    metric_key VARCHAR(50) NOT NULL COMMENT '指标标识',
    aggregation_type VARCHAR(20) NOT NULL COMMENT '统计方式（count/rate）',
    target_value TEXT NOT NULL COMMENT '目标值（JSON 字符串）',
    description VARCHAR(500) COMMENT '指标说明',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_metric_id (metric_id),
    UNIQUE KEY uk_feature_metric_key (feature, metric_key),
    INDEX idx_feature (feature),
    INDEX idx_metric_type (metric_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运营看板指标配置表';
```

## 接口设计

### 接口一：数据上报接口

**接口路径：** `POST /openlibing-framework/manage/feature-dashboard/report`

**请求示例：**

```json
{
  "community": "communityA",
  "repo": "communityA/projectB",
  "feature": "feature-dashboard",
  "userMetrics": {
    "active_users": 150,
    "new_users": 30
  },
  "businessMetrics": {
    "total_requests": 1000,
    "success_rate": 0.95
  },
  "timestamp": "2025-06-15T10:30:00Z"
}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "数据上报成功",
  "data": {
    "reportId": "uuid-xxx-xxx",
    "community": "communityA",
    "feature": "feature-dashboard",
    "receivedAt": "2025-06-15T10:30:05Z"
  }
}
```

### 接口二：自定义运营指标接口

**接口路径：** `POST /openlibing-framework/manage/feature-dashboard/metrics`

**请求示例：**

```json
{
  "metrics": [
    {
      "feature": "feature-dashboard",
      "metricType": "user_metric",
      "metricName": "活跃用户数",
      "metricKey": "active_users",
      "aggregationType": "count",
      "targetValue": "200",
      "description": "每日活跃用户数"
    },
    {
      "feature": "feature-dashboard",
      "metricType": "business_metric",
      "metricName": "成功率",
      "metricKey": "success_rate",
      "aggregationType": "rate",
      "targetValue": "0.98",
      "description": "接口成功率"
    }
  ]
}
```

**响应示例：**

```json
{
  "code": 200,
  "message": "运营指标定义成功",
  "data": {
    "batchId": "batch-uuid-xxx",
    "totalMetrics": 2,
    "createdMetrics": [
      {
        "metricId": "metric-uuid-1",
        "feature": "feature-dashboard",
        "metricType": "user_metric",
        "metricName": "活跃用户数",
        "metricKey": "active_users",
        "aggregationType": "count",
        "targetValue": "200",
        "description": "每日活跃用户数",
        "createdAt": "2025-06-15T10:30:00Z"
      },
      {
        "metricId": "metric-uuid-2",
        "feature": "feature-dashboard",
        "metricType": "business_metric",
        "metricName": "成功率",
        "metricKey": "success_rate",
        "aggregationType": "rate",
        "targetValue": "0.98",
        "description": "接口成功率",
        "createdAt": "2025-06-15T10:30:00Z"
      }
    ]
  }
}
```

## Service 层核心逻辑

### 1. 数据上报 Service

**核心逻辑：**

```java
@Service
public class FeatureOpsDashboardServiceImpl implements FeatureOpsDashboardService {
    
    @Override
    public DashboardReportResponseDTO reportData(DashboardReportRequestDTO request) {
        // 1. 参数校验与预处理
        validateRequest(request);
        
        // 2. Community 推断逻辑
        String community = inferCommunity(request.getCommunity(), request.getRepo());
        
        // 3. 数据存储
        String reportId = UUID.randomUUID().toString();
        FeatureOpsDashboardReport report = new FeatureOpsDashboardReport();
        report.setReportId(reportId);
        report.setCommunity(community);
        report.setFeature(request.getFeature());
        report.setUserMetrics(toJsonString(request.getUserMetrics()));
        report.setBusinessMetrics(toJsonString(request.getBusinessMetrics()));
        report.setReportedAt(parseTimestamp(request.getTimestamp()));
        
        mapper.insertReport(report);
        
        // 4. 构建响应
        return buildResponse(report);
    }
    
    private String inferCommunity(String community, String repo) {
        if (StringUtils.hasText(community)) {
            return community;
        }
        if (StringUtils.hasText(repo) && repo.contains("/")) {
            return repo.split("/")[0];
        }
        return null;
    }
}
```

### 2. 指标配置 Service

**核心逻辑：**

```java
@Service
public class FeatureOpsDashboardServiceImpl implements FeatureOpsDashboardService {
    
    @Override
    @Transactional
    public DashboardMetricConfigResponseDTO defineMetrics(DashboardMetricConfigRequestDTO request) {
        // 1. 参数校验
        validateMetrics(request.getMetrics());
        
        // 2. 批量处理指标配置
        String batchId = UUID.randomUUID().toString();
        List<MetricItemDTO> createdMetrics = new ArrayList<>();
        
        for (MetricDTO metric : request.getMetrics()) {
            // 检查唯一性
            if (mapper.selectByFeatureAndKey(metric.getFeature(), metric.getMetricKey()) != null) {
                throw new BusinessException(ErrorCode.METRIC_ALREADY_EXISTS);
            }
            
            // 插入配置
            String metricId = UUID.randomUUID().toString();
            FeatureOpsDashboardMetricConfig config = new FeatureOpsDashboardMetricConfig();
            config.setMetricId(metricId);
            config.setFeature(metric.getFeature());
            config.setMetricType(metric.getMetricType());
            config.setMetricName(metric.getMetricName());
            config.setMetricKey(metric.getMetricKey());
            config.setAggregationType(metric.getAggregationType());
            config.setTargetValue(metric.getTargetValue());
            config.setDescription(metric.getDescription());
            
            mapper.insertMetricConfig(config);
            createdMetrics.add(buildMetricItemDTO(config));
        }
        
        // 3. 构建响应
        return buildResponse(batchId, createdMetrics);
    }
}
```

### 3. 时间段统计逻辑（应用层聚合）

**统计实现：**

```java
public Map<String, Object> aggregateMetrics(String feature, String startTime, String endTime) {
    // 1. 查询时间段内的上报数据
    List<FeatureOpsDashboardReport> reports = mapper.selectByFeatureAndTimeRange(
        feature, startTime, endTime
    );
    
    // 2. 查询指标配置
    List<FeatureOpsDashboardMetricConfig> configs = mapper.selectByFeature(feature);
    
    // 3. 应用层聚合
    Map<String, Object> result = new HashMap<>();
    for (FeatureOpsDashboardMetricConfig config : configs) {
        Object value = aggregateByType(reports, config);
        result.put(config.getMetricKey(), value);
    }
    
    return result;
}

private Object aggregateByType(List<FeatureOpsDashboardReport> reports, 
                                FeatureOpsDashboardMetricConfig config) {
    if ("count".equals(config.getAggregationType())) {
        // count 类型：求和
        return reports.stream()
            .mapToDouble(r -> getMetricValue(r, config.getMetricKey()))
            .sum();
    } else if ("rate".equals(config.getAggregationType())) {
        // rate 类型：计算比率
        double numerator = reports.stream()
            .mapToDouble(r -> getNestedValue(r, config.getMetricKey(), "numerator"))
            .sum();
        double denominator = reports.stream()
            .mapToDouble(r -> getNestedValue(r, config.getMetricKey(), "denominator"))
            .sum();
        return denominator > 0 ? numerator / denominator : 0;
    }
    return null;
}
```

## 错误处理设计

### 错误码定义

```java
public enum ErrorCode {
    // 通用错误 (1000-1999)
    INVALID_PARAMETER(1001, "参数校验失败"),
    INVALID_JSON_FORMAT(1002, "JSON 格式错误"),
    
    // 数据上报错误 (2000-2999)
    REPORT_FEATURE_EMPTY(2001, "feature 不能为空"),
    REPORT_USER_METRICS_EMPTY(2002, "userMetrics 不能为空"),
    REPORT_BUSINESS_METRICS_EMPTY(2003, "businessMetrics 不能为空"),
    
    // 指标配置错误 (3000-3999)
    METRIC_TYPE_INVALID(3001, "metricType 不合法，仅支持 user_metric 或 business_metric"),
    AGGREGATION_TYPE_INVALID(3002, "aggregationType 不合法，仅支持 count 或 rate"),
    METRIC_ALREADY_EXISTS(3003, "指标配置已存在"),
    METRIC_BATCH_EXCEEDED(3004, "批量指标数量超过限制，最多 50 条"),
    
    // 系统错误 (5000-5999)
    DATABASE_ERROR(5001, "数据库操作失败"),
    INTERNAL_ERROR(5000, "系统内部错误");
    
    private final Integer code;
    private final String message;
}
```

### 异常处理

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponseDTO> handleValidationException(
        MethodArgumentNotValidException ex
    ) {
        List<FieldError> errors = ex.getBindingResult().getFieldErrors().stream()
            .map(e -> new FieldError(e.getField(), e.getDefaultMessage()))
            .collect(Collectors.toList());
        
        return ResponseEntity.badRequest().body(
            new ErrorResponseDTO(1001, "参数校验失败", errors)
        );
    }
    
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorResponseDTO> handleBusinessException(
        BusinessException ex
    ) {
        return ResponseEntity.badRequest().body(
            new ErrorResponseDTO(ex.getCode(), ex.getMessage(), null)
        );
    }
    
    @ExceptionHandler(DataAccessException.class)
    public ResponseEntity<ErrorResponseDTO> handleDataAccessException(
        DataAccessException ex
    ) {
        return ResponseEntity.status(500).body(
            new ErrorResponseDTO(5001, "数据库操作失败", null)
        );
    }
}
```

## 测试策略

### 测试覆盖率目标

**≥80%**

### 测试范围

| 测试层级 | 测试类 | 覆盖内容 |
|---------|--------|---------|
| Controller | FeatureOpsDashboardControllerTest | 接口调用、参数校验、响应格式 |
| Service | FeatureOpsDashboardServiceTest | 业务逻辑、异常处理、边界情况 |
| Mapper | FeatureOpsDashboardMapperTest | 数据库操作、唯一约束、查询逻辑 |
| Integration | FeatureOpsDashboardIntegrationTest | 端到端流程 |

### 关键测试用例

**Controller 层：**
- 所有字段完整上报 → 200
- 仅必填字段上报 → 200
- feature 为空 → 400 (2001)
- userMetrics 为空 → 400 (2002)
- 从 repo 推断 community → 200
- 单个指标配置 → 200
- 批量指标配置（50 条）→ 200
- 批量指标超过 50 条 → 400 (3004)
- metricType 不合法 → 400 (3001)
- aggregationType 不合法 → 400 (3002)
- 重复 metricKey → 400 (3003)

**Service 层：**
- 数据上报成功，验证 Mapper 调用
- Community 推断逻辑正确
- timestamp 为空时使用当前时间
- 指标配置成功
- 重复 metricKey 抛出异常
- JSON 序列化成功

**Mapper 层：**
- 插入上报数据成功
- 按 feature 查询上报数据
- 按时间范围查询上报数据
- 插入指标配置成功
- 按 feature 和 metricKey 查询
- 唯一约束冲突

### 测试执行命令

```bash
# 运行所有测试
mvn test

# 运行单个测试类
mvn test -Dtest=FeatureOpsDashboardControllerTest

# 生成覆盖率报告
mvn test jacoco:report
```

## 部署与配置

### 数据库变更

执行 SQL 脚本创建两张表：
- `feature_ops_dashboard_report`
- `feature_ops_dashboard_metric_config`

### 配置项

暂无新增配置项，使用项目现有配置。

### 认证权限

利用现有 RBAC 权限体系验证 Token 和 Admin 角色（TODO：后续对接）。

## 性能与扩展

### 当前方案

- 小数据量场景，应用层聚合可接受
- 暂不使用 Redis 缓存
- 暂不做分库分表

### 未来扩展

- 数据量增大后，考虑数据库层聚合（存储过程 / 物化视图）
- 高频查询场景，引入 Redis 缓存
- 大数据量场景，考虑分库分表或时序数据库

## 待办事项（TODO）

| TODO | 说明 | 优先级 |
|------|------|--------|
| 认证权限集成 | 确认现有 RBAC 集成方式，验证 Token 和 Admin 角色 | 高 |
| 代码仓映射 | 集成到现有配置表（repo → community 映射） | 中 |
| 时间段统计接口 | 暂未实现，后续根据运营需求添加 | 中 |
| 监控告警 | 添加接口调用监控和异常告警 | 低 |