# trae运维数据转发

## 需求背景

实现 Trae AI 开发工具的运维数据转发能力，将 Trae 侧产生的运维数据通过本服务转发到下游存储或展示系统，支撑运营指标看板的数据采集需求。

## 功能描述

### 1. Trae 运维数据转发
- **API 转发接口**：在 AiDashboardController 中新增运维数据接收和转发接口
- **转发服务实现**：AiDashboardService 实现数据转发业务逻辑
- **请求参数封装**：定义 ApiForwardRequest 请求体，规范转发数据格式

### 2. API 配置管理
- **API 配置实体**：新增 ApiConfig 实体和 ApiConfigMapper，管理转发目标的 API 配置信息
- **多数据源支持**：通过 DataSource 注解和 DataSourceAspect 切面，支持转发到不同数据源

### 3. 数据源切换优化
- 优化 DataSource 注解和 DataSourceAspect 切面，增强多数据源切换的灵活性

### 4. 代码优化
- AiDashboardController 和 AiDashboardService 的代码优化调整

## 验收标准

- [ ] Trae 运维数据可通过转发接口成功接收并转发
- [ ] API 配置实体支持增删改查
- [ ] 数据源切换注解在多数据源场景下正确切换
- [ ] 转发接口返回格式与上游约定一致

## 影响范围

- `api/controller/AiDashboardController.java`
- `app/service/metric/AiDashboardService.java`
- `app/service/metric/req/ApiForwardRequest.java`
- `domain/repository/entity/ApiConfig.java`
- `domain/repository/repository/ApiConfigMapper.java`
- `infrastructure/aop/DataSource.java`
- `infrastructure/aop/DataSourceAspect.java`
- `infrastructure/entity/DynamicDataSource.java`（老代码优化）