# 仿真运营数据上报

## 需求背景

提升数据流转效率，实现仿真任务执行数据的自动化上报，统一数据口径，为运营看板提供准确、及时的数据支撑。

**当前问题：**

- 仿真任务执行数据分散在OBS对象存储中，缺乏统一的数据采集机制
- 数据上报依赖人工统计，效率低且易出错
- 不同社区的数据口径不一致，难以横向对比

**价值：**

- 自动化数据采集，提升数据流转效率
- 统一上报至openlibing-framework运营看板，实现数据可视化展示
- 统一数据口径，支持多社区数据的横向对比和分析

## 功能描述

### 做什么

实现仿真任务执行数据的自动化采集和上报功能：

1. **定时数据采集**
   - 每天凌晨1点自动触发数据采集任务
   - 从OBS对象存储采集仿真任务执行结果数据
   - 采集路径：`simulation/case/matrixsvr/{taskId}/{date}/`
   - 统计指标：执行用例数量（executeCaseCount，统计包含"result"的文件）

2. **按社区分组统计**
   - 从数据库查询包含`community`字段的仿真任务列表
   - 按社区维度分组统计执行用例数量
   - 每个社区独立上报数据

3. **数据上报到运营看板**
   - 通过Feign客户端调用openlibing-framework运营看板接口
   - 上报接口：`POST /openlibing-framework/manage/feature-dashboard/report`
   - 上报内容：
     - `community`：社区名称
     - `feature`：测试管理
     - `businessMetrics`：`zhanlu_execute_case_count`（执行用例数量）

4. **分布式锁保证**
   - 使用分布式锁防止多实例重复执行
   - 锁过期时间：1小时
   - 异常情况下自动释放锁

### 不做什么

- 不修改现有仿真任务管理功能
- 不修改OBS对象存储的数据结构
- 不实现实时数据上报（仅定时上报）
- 不实现数据校验和纠错功能
- 不实现上报失败的数据重试机制（仅记录失败日志）

## 验收标准

- [ ] 定时任务每天凌晨1点自动触发执行
- [ ] 能够正确从OBS对象存储采集仿真任务执行数据
- [ ] 能够按社区维度分组统计数据
- [ ] 能够成功上报数据到openlibing-framework运营看板
- [ ] 分布式锁能够防止重复执行
- [ ] 上报成功后，运营看板能够正确显示仿真任务执行用例数量
- [ ] 日志记录清晰，包含采集、分组、上报各环节的详细信息

## 影响范围

### 新增组件

- `DashboardReportClient`：运营看板数据上报Feign客户端
- `ObsUtilClient`：OBS对象存储客户端（已存在，本次新增初始化逻辑）
- `ScheduleTask`：定时任务调度类
- `ScheduleService`：数据采集和上报服务接口
- `ScheduleServiceImpl`：数据采集和上报服务实现
- `DashboardReportRequest`：数据上报请求DTO
- `DashboardReportResponse`：数据上报响应DTO

### 修改组件

- `Application.java`：新增`@EnableFeignClients`注解，启用Feign客户端
- `Constans.java`：新增OBS路径常量`OBS_PATH_PREFIX`和桶名常量`BUCKET_NAME`
- `SimulationVerificationTaskBaseMapper`：新增查询方法`getTaskListByStatus`
- `SimulationVerificationTaskBaseMapper.xml`：新增SQL查询语句
- `DateTimeUtils`：新增获取昨天日期字符串的方法
- `application-{env}.yaml`：新增运营看板配置`dashboard.report.url`

### 外部依赖

- **OBS对象存储**：华为云OBS服务，存储仿真任务执行结果数据
- **openlibing-framework**：运营看板服务，提供数据上报接口
- **分布式锁服务**：已存在的分布式锁服务（Redis实现）

### 数据影响

- **查询数据**：`t_simulation_verification_task_base`表（任务基础信息表）
- **不上报数据**：不修改任何数据库表数据，仅查询和上报

## 参考方案

### 技术实现

- **定时任务**：使用Spring Boot的`@Scheduled`注解，cron表达式：`0 0 1 * * ?`
- **OBS数据采集**：使用华为云OBS Java SDK，递归列举对象
- **数据上报**：使用Spring Cloud OpenFeign，HTTP POST请求
- **分布式锁**：使用项目已有的分布式锁服务（Redis实现）
- **日志记录**：使用SLF4J，记录采集、分组、上报各环节的详细信息

### 数据流程

```
定时任务触发 → 获取分布式锁 → 查询任务列表 → 按community分组 →
采集OBS数据（递归列举） → 统计executeCaseCount → 构建上报请求 →
调用运营看板接口 → 释放分布式锁
```

## 边界条件

- **OBS路径不存在**：记录错误日志，跳过该任务
- **运营看板接口不可用**：记录错误日志，不影响下一次执行
- **分布式锁获取失败**：跳过本次执行，避免重复执行
- **任务列表为空**：记录日志，跳过本次执行
- **单个社区数据采集失败**：记录错误日志，不影响其他社区的数据上报
