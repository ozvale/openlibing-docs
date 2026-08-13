# 仿真运营数据上报 — 技术设计

## 方案概述

基于Spring Boot定时任务机制，实现仿真任务执行数据的自动化采集和上报。每天凌晨1点自动从OBS对象存储采集前一天的数据，按社区维度分组统计执行用例数量，并通过Feign客户端上报到openlibing-framework运营看板。

## 架构决策

### 关键决策及原因

| 决策点               | 方案                                    | 原因                                                          |
| -------------------- | --------------------------------------- | ------------------------------------------------------------- |
| **定时任务触发时间** | 每天凌晨1点（cron: `0 0 1 * * ?`）      | 避开业务高峰期，确保前一天数据已完整写入OBS                   |
| **数据采集方式**     | 递归列举OBS对象，统计包含"result"的文件 | OBS数据结构为层级目录，需递归遍历；result文件标识任务执行结果 |
| **数据统计维度**     | 按community分组统计                     | 运营看板按社区维度展示数据，需提前分组以提高上报效率          |
| **数据上报方式**     | Spring Cloud OpenFeign                  | 统一HTTP调用规范，支持负载均衡和熔断机制                      |
| **并发控制**         | 分布式锁（Redis实现）                   | 防止多实例重复执行，锁过期时间1小时确保任务执行完成           |
| **日志记录**         | SLF4J + 详细日志输出                    | 便于排查数据采集和上报问题，记录每个环节的详细信息            |

### 技术选型

- **定时任务**：Spring Boot `@Scheduled`注解，无需额外依赖，配置简单
- **OBS SDK**：华为云OBS Java SDK，官方支持，性能稳定
- **Feign客户端**：Spring Cloud OpenFeign，与Spring Boot集成良好
- **分布式锁**：项目已有的分布式锁服务（Redis实现），避免重复开发

## 涉及文件

| 文件                                        | 操作 | 说明                                                           |
| ------------------------------------------- | ---- | -------------------------------------------------------------- |
| `Application.java`                          | 修改 | 新增`@EnableFeignClients`注解，启用Feign客户端                 |
| `DashboardReportClient.java`                | 新增 | 运营看板数据上报Feign客户端接口                                |
| `ObsUtilClient.java`                        | 修改 | OBS客户端，新增初始化逻辑和`getObsClient()`方法                |
| `ScheduleTask.java`                         | 新增 | 定时任务调度类，每天凌晨1点触发数据采集                        |
| `ScheduleService.java`                      | 新增 | 数据采集和上报服务接口                                         |
| `ScheduleServiceImpl.java`                  | 新增 | 数据采集和上报服务实现，核心业务逻辑                           |
| `DashboardReportRequest.java`               | 新增 | 数据上报请求DTO，包含community、feature、businessMetrics等字段 |
| `DashboardReportResponse.java`              | 新增 | 数据上报响应DTO，包含reportId、status等字段                    |
| `Constans.java`                             | 修改 | 新增OBS路径常量`OBS_PATH_PREFIX`和桶名常量`BUCKET_NAME`        |
| `CmdConstants.java`                         | 修改 | 可能新增相关常量（根据实际需要）                               |
| `SimulationVerificationTaskBaseMapper.java` | 修改 | 新增查询方法`getTaskListByStatus`，获取包含community的任务列表 |
| `SimulationVerificationTaskBaseMapper.xml`  | 修改 | 新增SQL查询语句，查询任务列表                                  |
| `DateTimeUtils.java`                        | 修改 | 新增`getYesterdayDateString()`方法，获取昨天日期字符串         |
| `QemuTaskService.java`                      | 修改 | 可能新增相关方法（根据实际需要）                               |
| `QemuTaskServiceImpl.java`                  | 修改 | 可能新增相关方法实现（根据实际需要）                           |
| `application-beta.yaml`                     | 修改 | 新增运营看板配置`dashboard.report.url`                         |
| `application-gama.yaml`                     | 修改 | 新增运营看板配置`dashboard.report.url`                         |
| `application-prod.yaml`                     | 修改 | 新增运营看板配置`dashboard.report.url`                         |
| `pom.xml`                                   | 修改 | 新增Spring Cloud OpenFeign依赖                                 |

## 数据流程

### 完整流程图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           仿真运营数据上报完整流程                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  定时任务触发 │ (每天凌晨1点)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 获取分布式锁 │ (Redis, 过期时间1小时)
└──────┬───────┘
       │ 获取失败 → 跳过本次执行
       │ 获取成功 ↓
       ▼
┌──────────────┐
│ 查询任务列表 │ (从数据库查询包含community的任务)
└──────┬───────┘
       │ 任务列表为空 → 记录日志，跳过本次执行
       │ 任务列表不为空 ↓
       ▼
┌──────────────┐
│ 按community分组 │ (Map<community, List<Task>>)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────┐
│ 对每个community进行数据采集和上报 │ (循环处理)
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────┐
│ 采集OBS数据 │
│ ┌────────────────────────────────┐ │
│ │ 获取昨天日期字符串             │ │
│ │ 构建OBS路径：simulation/case/ │ │
│ │   matrixsvr/{taskId}/{date}/  │ │
│ └────────────────────────────────┘ │
│ ┌────────────────────────────────┐ │
│ │ 递归列举OBS对象                │ │
│ │ - 列举当前目录下的文件         │ │
│ │ - 递归列举子目录               │ │
│ │ - 统计包含"result"的文件数量   │ │
│ └────────────────────────────────┘ │
└──────┬───────┘
       │ OBS路径不存在 → 记录错误日志，跳过该任务
       │ OBS路径存在 ↓
       ▼
┌──────────────┐
│ 统计executeCaseCount │ (统计result文件数量)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 构建上报请求 │
│ ┌────────────────────────────────┐ │
│ │ DashboardReportRequest         │ │
│ │ - community: 社区名称          │ │
│ │ - feature: 测试管理            │ │
│ │ - businessMetrics:             │ │
│ │   zhanlu_execute_case_count: N │ │
│ │ - timestamp: 当前时间          │ │
│ └────────────────────────────────┘ │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 调用运营看板接口 │ (Feign客户端)
│ POST /openlibing-framework/     │
│   manage/feature-dashboard/report│
└──────┬───────┘
       │ 上报成功 → 记录成功日志
       │ 上报失败 → 记录错误日志，不影响其他社区
       │
       ▼
┌──────────────┐
│ 释放分布式锁 │ (finally块确保锁释放)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 任务执行完成 │
└──────────────┘
```

### OBS数据结构

**OBS路径格式：** `simulation/case/matrixsvr/{taskId}/{date}/`

**示例：**

```
simulation/case/matrixsvr/1001/2026-07-08/
  ├── result_1.log
  ├── result_2.log
  ├── config.json
  └── subtask/
      ├── result_3.log
      └── logs/
          ├── result_4.log
```

**统计逻辑：** 递归列举所有文件，统计文件名包含"result"的文件数量作为executeCaseCount。

## 关键技术实现

### 1. OBS递归列举对象

**实现代码：** `ScheduleServiceImpl.listObjects()` 和 `listObjectsByPrefix()`

**关键逻辑：**

```java
private void listObjects(ListObjectsRequest request, int[] counts) {
    ObjectListing result;
    do {
        result = obsClient.listObjects(request);
        for (ObsObject obsObject : result.getObjects()) {
            log.info("\t" + obsObject.getObjectKey());
            if (obsObject.getObjectKey().contains("result")) {
                counts[0]++; // executeCaseCount累加
            }
        }
        request.setMarker(result.getNextMarker());
        listObjectsByPrefix(result, counts); // 递归列举子目录
    } while (result.isTruncated());
}
```

**注意事项：**

- 设置`delimiter="/"`，只列举当前目录内容
- 设置`maxKeys=100000`，避免分页过多
- 递归处理子目录（`listObjectsByPrefix()`）

### 2. 按社区分组统计

**实现代码：** `ScheduleServiceImpl.collectPushCaseInfo()`

**关键逻辑：**

```java
// 按community分组
Map<String, List<SimulationVerificationTaskBaseEntity>> communityTaskMap =
    taskList.stream()
        .filter(item -> StringUtils.isNotEmpty(item.getCommunity()))
        .collect(Collectors.groupingBy(Task::getCommunity));

// 为每个community分别统计和上报
for (Map.Entry<String, List<Task>> entry : communityTaskMap.entrySet()) {
    oneCommunityDataReport(entry, dateString);
}
```

### 3. 分布式锁保证

**实现代码：** `ScheduleTask.collectObsData()`

**关键逻辑：**

```java
String lockResult = distributedLockService.acquireLock(LOCK_NAME, LOCK_EXPIRE_SECONDS);
if (lockResult == null || lockResult.isEmpty()) {
    logger.info("Failed to acquire lock, skip execution");
    return;
}

try {
    scheduleService.collectPushCaseInfo();
} finally {
    distributedLockService.releaseLock(LOCK_NAME);
}
```

**注意事项：**

- 锁过期时间1小时，确保任务执行完成
- 使用try-finally确保锁释放
- 获取失败直接跳过，避免重复执行

## 风险 & 缓解

| 风险                   | 影响                             | 缓解措施                                                  |
| ---------------------- | -------------------------------- | --------------------------------------------------------- |
| **OBS服务不可用**      | 无法采集数据，任务失败           | 记录错误日志，不影响下一次执行；OBS服务有SLA保证          |
| **运营看板接口不可用** | 无法上报数据，任务失败           | 记录错误日志，不影响下一次执行；运营看板服务有SLA保证     |
| **分布式锁获取失败**   | 多实例重复执行                   | 锁过期时间1小时，确保任务执行完成；获取失败直接跳过       |
| **OBS路径不存在**      | 采集数据为空                     | 记录错误日志，跳过该任务；不影响其他社区的数据上报        |
| **数据量过大**         | 采集耗时过长，可能超过锁过期时间 | 设置OBS列举maxKeys=100000，避免分页过多；监控执行时间     |
| **数据库查询慢**       | 查询任务列表耗时过长             | 添加查询条件，只查询包含community的任务；添加索引优化     |
| **Feign调用失败**      | 上报失败                         | 记录错误日志，不影响其他社区的数据上报；使用Feign熔断机制 |

## 跨仓影响

### openlibing-framework运营看板

**接口契约：**

- **接口路径：** `POST /openlibing-framework/manage/feature-dashboard/report`
- **请求参数：** `DashboardReportRequest`
  - `community`: 社区名称（可选）
  - `feature`: 特性名称（必填，固定值"测试管理"）
  - `businessMetrics`: 业务指标（必填，包含`zhanlu_execute_case_count`）
  - `timestamp`: 数据采集时间（可选，默认当前时间）
- **响应参数：** `DashboardReportResponse`
  - `code`: 响应状态码（200=成功）
  - `message`: 响应消息
  - `data.reportId`: 本次上报的唯一ID
  - `data.status`: 状态

**注意事项：**

- 需要配置运营看板服务URL：`dashboard.report.url`
- 需要确保运营看板服务正常运行
- 需要确保数据格式符合运营看板接口规范

### openlibing-docs文档仓

**新增文档：**

- `spec/openlibing-simulation/task_design/simulation-obs-data-report/proposal.md`
- `spec/openlibing-simulation/task_design/simulation-obs-data-report/design.md`
- `spec/openlibing-simulation/task_design/simulation-obs-data-report/tasks.md`

**文档要求：**

- 文档必须提交到docs仓，通过PR合入
- PR标题：`docs(spec/openlibing-simulation): simulation-obs-data-report`
- PR描述：关联业务仓Issue #10
- 必须加`ai-assisted`标签

## 性能考虑

| 场景             | 性能指标         | 优化措施                                                    |
| ---------------- | ---------------- | ----------------------------------------------------------- |
| **OBS列举对象**  | 单次列举耗时     | 设置maxKeys=100000，减少分页次数；使用delimiter避免深度递归 |
| **数据库查询**   | 查询任务列表耗时 | 只查询包含community的任务；添加索引优化                     |
| **Feign调用**    | 单次上报耗时     | 使用Feign连接池；设置合理的超时时间                         |
| **整体执行时间** | 任务执行总耗时   | 监控执行时间，确保不超过锁过期时间（1小时）                 |

## 配置说明

### application-{env}.yaml配置

```yaml
# 运营看板配置
dashboard:
  report:
    url: http://openlibing-framework-service:8080

# OBS配置（已存在）
obs:
  endpoint: https://obs.cn-north-4.myhuaweicloud.com
  access-key-id: ${OBS_ACCESS_KEY_ID}
  secret-access-key: ${OBS_SECRET_ACCESS_KEY}

# 分布式锁配置（已存在）
distributed:
  lock:
    redis:
      host: ${REDIS_HOST}
      port: ${REDIS_PORT}
```

### pom.xml依赖

```xml
<!-- Spring Cloud OpenFeign -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
```

## 测试策略

### 单元测试

- **ScheduleServiceImplTest**: 测试数据采集和上报逻辑
  - 测试按community分组
  - 测试OBS数据采集（Mock ObsClient）
  - 测试数据上报（Mock DashboardReportClient）

### 集成测试

- **ScheduleTaskTest**: 测试定时任务执行
  - 测试分布式锁获取和释放
  - 测试完整流程执行
  - 测试异常情况处理

### 性能测试

- 测试OBS列举对象性能（大数据量场景）
- 测试整体执行时间（确保不超过锁过期时间）

## 监控与日志

### 关键监控指标

- **定时任务执行次数**: 每天凌晨1点执行一次
- **数据采集成功率**: 统计成功采集的社区数量
- **数据上报成功率**: 统计成功上报的社区数量
- **执行耗时**: 监控任务执行总耗时

### 日志输出

**关键日志点：**

- 定时任务触发
- 分布式锁获取/释放
- 任务列表查询结果
- 按社区分组结果
- OBS数据采集开始/结束
- 执行用例数量统计
- 数据上报请求/响应
- 异常情况处理

**日志级别：**

- INFO: 正常流程日志
- WARN: 警告日志（如上报失败）
- ERROR: 错误日志（如OBS路径不存在）
