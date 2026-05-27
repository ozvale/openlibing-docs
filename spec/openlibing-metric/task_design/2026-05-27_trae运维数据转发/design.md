# trae运维数据转发 — 技术设计

## 方案概述

在现有运营指标看板服务基础上，新增 Trae 运维数据转发能力。通过新增 API 配置实体管理转发目标，利用已有的数据源切换 AOP 机制支持多数据源转发。

## 架构决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 转发方式 | AiDashboardService 同步转发 | 与现有看板服务架构一致，便于统一管理和监控 |
| API 配置存储 | 新增 ApiConfig 实体 + ApiConfigMapper | 支持持久化配置，便于运行时管理转发目标 |
| 数据源切换 | 复用 DataSource AOP 注解 | 已有成熟方案，避免重复开发 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/controller/AiDashboardController.java` | 修改 | 新增运维数据转发接口 |
| `app/service/metric/AiDashboardService.java` | 修改 | 转发业务逻辑实现 |
| `app/service/metric/req/ApiForwardRequest.java` | 新增 | 转发请求参数体 |
| `domain/repository/entity/ApiConfig.java` | 新增 | API 配置实体（目标地址、认证信息等） |
| `domain/repository/repository/ApiConfigMapper.java` | 新增 | API 配置 Mapper |
| `infrastructure/aop/DataSource.java` | 新增/修改 | 数据源切换注解 |
| `infrastructure/aop/DataSourceAspect.java` | 新增/修改 | 数据源切换切面 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 转发接口超时可能阻塞调用方 | 考虑异步处理或设置超时配置 |
| 多数据源配置管理复杂 | ApiConfig 实体统一管理配置信息 |

## 跨仓影响

无。