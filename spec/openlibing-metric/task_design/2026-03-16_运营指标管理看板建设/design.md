# 运营指标管理看板建设 — 技术设计

## 方案概述

基于 Spring Boot + MyBatis Plus 构建运营指标管理后端服务，采用分层架构（api -> domain -> infrastructure），实现对指标、维度、领域、数据资产表的统一管理。

## 架构决策

| 决策 | 选择 | 原因 |
|------|------|------|
| ORM | MyBatis Plus | 与现有技术栈一致，支持灵活的自定义 SQL |
| 多数据源 | AOP 注解 + DataSourceAspect | 声明式切换，降低侵入性 |
| 逻辑删除 | 状态标记（status 字段） | 保留历史数据，支持审计 |
| 响应格式 | 统一 ResponseCodeEnum | 规范接口返回码 |

## 涉及文件

### 指标管理

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/controller/DigitalMetricInfoController.java` | 新增/修改 | 指标管理 REST 接口 |
| `api/controller/DigitalOperationDimensionController.java` | 新增 | 维度管理 REST 接口 |
| `api/controller/DigitalOperationDomainController.java` | 新增 | 领域管理 REST 接口 |
| `api/controller/req/MetricListQueryReq.java` | 新增 | 指标列表查询请求参数 |
| `api/controller/resp/MetricFilterOptionsResp.java` | 新增 | 筛选参数响应结构 |
| `domain/digital/entity/DigitalMetricInfo.java` | 新增 | 指标信息实体 |
| `domain/digital/entity/DigitalOperationDimension.java` | 新增 | 维度实体 |
| `domain/digital/entity/DigitalOperationDomain.java` | 新增 | 领域实体 |
| `domain/digital/repository/DigitalMetricInfoMapper.java` | 新增 | 指标 Mapper |
| `domain/digital/repository/DigitalOperationDimensionMapper.java` | 新增 | 维度 Mapper |
| `domain/digital/repository/DigitalOperationDomainMapper.java` | 新增 | 领域 Mapper |
| `domain/digital/service/` (3 interfaces) | 新增 | 指标/维度/领域 Service 接口 |
| `domain/digital/service/impl/` (3 impls) | 新增 | Service 实现 |
| `resources/mapper/DigitalMetricInfoMapper.xml` | 新增 | 105 行复杂查询 SQL |

### 数据资产管理

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/controller/DataAssetColumnInfoController.java` | 新增/修改 | 数据资产字段 REST 接口 |
| `api/controller/DataAssetTableRegistryController.java` | 新增/修改 | 表注册 REST 接口 |
| `api/controller/req/DataAssetColumnInfoUpdateReq.java` | 新增 | 字段更新请求 |
| `api/controller/req/DataAssetTableQueryReq.java` | 新增 | 表查询请求 |
| `api/controller/req/DataAssetTableUpdateReq.java` | 新增 | 表更新请求 |
| `domain/dataasset/entity/DataAssetColumnInfo.java` | 新增 | 字段实体 |
| `domain/dataasset/repository/DataAssetColumnInfoMapper.java` | 新增 | 字段 Mapper |
| `domain/dataasset/service/DataAssetColumnInfoService.java` | 新增 | 字段 Service |
| `domain/dataasset/service/impl/DataAssetColumnInfoServiceImpl.java` | 新增 | 字段 Service 实现 |
| `resources/mapper/DataAssetColumnInfoMapper.xml` | 新增 | 96 行字段 Mapper XML |

### 逻辑删除

| 文件 | 操作 |
|------|------|
| 3 个 Controller | 新增删除端点 |
| 3 个 Service 接口 | 新增删除方法 |
| 3 个 Service 实现 | 状态标记实现 |

### 基础设施

| 文件 | 操作 | 说明 |
|------|------|------|
| `infrastructure/aop/DataSource.java` | 新增 | 数据源切换注解 |
| `infrastructure/aop/DataSourceAspect.java` | 新增 | 数据源切换切面 |
| `infrastructure/response/ResponseCodeEnum.java` | 修改 | 补充响应码 |
| `api/controller/HealthController.java` | 修改 | 健康检查 |
| `api/controller/RefreshController.java` | 新增 | 刷新接口 |
| `application.yaml` | 修改 | 路径前缀 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 逻辑删除后查询需过滤 status | Mapper/Service 层统一添加过滤条件 |
| 多数据源事务一致性 | 数据源注解与 @Transactional 配合使用 |
| CodeCheck 修复量大可能引入回归 | UT 验证修复正确性 |

## 跨仓影响

无。