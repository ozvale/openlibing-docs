# 运营看板 - 实现任务清单

## 实现步骤

### 1. 数据模型层

- [x] 新建 `DashboardReportRequest.java`
  - 字段: community, feature, repo, businessMetrics, userMetrics, timestamp
  - 手写 Builder 内部类（替换 Lombok @Builder，修复 EI_EXPOSE_REP2）
  - getter 返回 Collections.unmodifiableMap（修复 EI_EXPOSE_REP）
  - setter 做防御性拷贝 LinkedHashMap
- [x] 新建 `DashboardBackfillRequest.java`
  - 字段: userId, startDate, endDate
  - startDate 默认 2021-06-19，endDate 默认昨天
- [x] 新建 `DashboardBackfillTaskStatus.java`
  - State 枚举: PENDING, RUNNING, SUCCESS, PARTIAL, FAILED
  - 字段: taskId, state, startDate, endDate, totalDays, processedDays, successCount, failCount, currentDay, errorMessage, startTime, endTime

### 2. Mapper 层（复用已有 DAO，无需新增）

- [x] `TblReposMapper.getAllDistinctCommunities()` - 获取全量社区列表
- [x] `TblScanMapper.countByCommunityAndCreatedBetween()` - 版本扫描次数
- [x] `TblScanMapper.findIdsByCommunityAndCreatedBetween()` - 按分支取最新扫描 ID
- [x] `TblPersonScanMapper.countPrByCommunityAndCreatedBetween()` - PR 扫描次数

### 3. Feign Client 扩展

- [x] 在 `OpenlibingFrameworkClient.java` 新增 `reportDashboard()` 方法
  - `POST /manage/feature-dashboard/report`
  - 入参 `DashboardReportRequest`，返回 `Object`

### 4. 核心定时任务

- [x] 新建 `DashboardReportSchedule.java`
  - `@Scheduled(cron = "${job.cron.dashboard.report.task:0 0 1 * * ?}")` 每日凌晨 1 点
  - `doJob()`: 分布式锁 → doJobWork() → 释放锁
  - `doJobWork()`: 计算昨日时间窗口 → 获取社区列表 → reportForDate()
  - `reportForDate(date, communities)`: 遍历社区 → buildRequest() → Feign 上报
  - `buildRequest(community, startTime, endTime, timestamp)`: 计算 4 项指标
  - `countAlerts(scanIds, pendingOnly)`: MongoDB 告警数统计
  - 配置 `@Value("${spring.profiles.active}")` 注入 env

### 5. 补录功能

- [x] 新建 `DashboardBackfillService.java`
  - `createTask(request)`: 生成 taskId + 创建任务状态 → 存入 ConcurrentHashMap
  - `getTask(taskId)`: 查询任务状态
  - `runBackfill(taskId, request)`: `@Async` 异步执行，按日升序遍历 → 调用 reportForDate()
  - synchronized 防止同一任务并发执行
- [x] 新建 `DashboardReportController.java`
  - `POST /dashboard/backfill`: 参数校验 → createTask + runBackfill → 返回 taskId
  - 日期校验: startDate ≤ endDate, endDate ≤ 今天
  - 鉴权: 仅超级管理员可调用

### 6. 单元测试

- [x] `DashboardReportScheduleTest.java`（11 个用例）
  - `testDoJob_LockNotAcquired`: 锁未获取，跳过执行
  - `testDoJob_LockAcquired_NoCommunity`: 无社区，不调用 Feign
  - `testDoJob_LockServiceThrowsException`: 锁服务异常，正常释放锁
  - `testDoJob_NullCommunity`: null 社区跳过
  - `testDoJob_EmptyCommunity`: 空字符串社区跳过
  - `testDoJobWork_SingleCommunity_Success`: 单社区成功上报
  - `testDoJobWork_MultiCommunities_PartialFailure`: 多社区部分失败，成功的不受影响
  - `testDoJobWork_EmptyScanIds`: scanIds 为空时不查询 MongoDB
  - `testBuildRequest_AllMetricsPopulated`: 4 项指标计算正确，验证 reportDate 解耦
  - `testBuildRequest_EmptyScanIds`: 无扫描记录时指标全为 0
  - `testBuildRequest_FourMetricsKeysPresent`: 4 个 key 完整性验证

## 关键技术点

1. **日期窗口左闭右开**：`startTime = date 00:00:00`, `endTime = date+1 00:00:00`，SQL 用 `>=` 和 `<`
2. **scanIds 上界解耦**：scanIds 查询用 `endTime` 格式化值（次日 00:00:00），不与 timestamp 复用，防止最后一刻漏算
3. **上报时间戳**：固定 23:50:00，规避 MySQL DATETIME 四舍五入越界
4. **扫描去重**：`ROW_NUMBER() OVER (PARTITION BY repo_id, branch ORDER BY modified DESC)` 取 rn=1
5. **分布式锁**：`Redisson.tryLock(5s, -1, SECONDS)`，leaseTime=-1 启用看门狗自动续期
6. **SpotBugs**：手工 Builder + 防御性拷贝替换 Lombok @Builder/@AllArgsConstructor
