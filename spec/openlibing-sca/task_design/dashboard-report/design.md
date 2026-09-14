# 运营看板 - 技术设计

## 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                    openlibing-sca                         │
│                                                          │
│  ┌─────────────────────┐   ┌──────────────────────────┐  │
│  │ DashboardReportController│  │ DashboardReportSchedule  │  │
│  │ POST /dashboard/backfill │  │ cron: 0 0 1 * * ?        │  │
│  │   (补录入口)           │  │   (每日定时上报)          │  │
│  └──────────┬──────────┘   └────────────┬─────────────┘  │
│             │                           │                 │
│  ┌──────────▼───────────────────────────▼─────────────┐  │
│  │            DashboardBackfillService                  │  │
│  │  异步补录: 按日期升序遍历 [startDate, endDate]       │  │
│  │  逐日调用 reportForDate(date, null)                  │  │
│  └────────────────────────┬───────────────────────────┘  │
│                           │                               │
│  ┌────────────────────────▼───────────────────────────┐  │
│  │            DashboardReportSchedule                   │  │
│  │  reportForDate(date, communities):                   │  │
│  │    1. 获取社区列表                                   │  │
│  │    2. 逐社区 buildRequest → Feign 上报               │  │
│  │    3. buildRequest 内部计算 4 项指标                 │  │
│  └────┬───────┬──────────┬─────────────┬──────────────┘  │
│       │       │          │             │                  │
│  ┌────▼──┐┌───▼────┐┌───▼──────┐┌────▼──────────┐       │
│  │MySQL  ││MySQL   ││MySQL     ││MongoDB        │       │
│  │tbl_scan│tbl_person│tbl_repos ││ScanIssueVO    │       │
│  │      ││_scan   ││          ││               │       │
│  └───────┘└────────┘└──────────┘└───────────────┘       │
│                                                          │
└──────────────────────────┬───────────────────────────────┘
                           │ Feign
┌──────────────────────────▼───────────────────────────────┐
│                 openlibing-framework                      │
│  POST /manage/feature-dashboard/report                   │
│  接收 DashboardReportRequest 并持久化                     │
└──────────────────────────────────────────────────────────┘
```

## 模块设计

### 1. 新增文件清单

| 文件                               | 类型         | 职责                               |
| ---------------------------------- | ------------ | ---------------------------------- |
| `DashboardReportController.java`   | Controller   | 补录接口入口，鉴权与参数校验       |
| `DashboardReportSchedule.java`     | Component    | 定时任务，核心计算与上报逻辑       |
| `DashboardBackfillService.java`    | Service      | 补录任务管理（创建/查询/异步执行） |
| `DashboardReportRequest.java`      | Domain       | 上报请求体（含手写 Builder）       |
| `DashboardBackfillRequest.java`    | Domain       | 补录请求体                         |
| `DashboardBackfillTaskStatus.java` | Domain       | 补录任务状态（内存存储）           |
| `OpenlibingFrameworkClient.java`   | Feign Client | 新增 reportDashboard 方法          |
| `DashboardReportScheduleTest.java` | Test         | 单元测试                           |

### 2. DashboardReportSchedule 核心逻辑

#### 2.1 定时任务 doJob()

```
doJob():
  1. 获取 Redis 分布式锁 (lockKey = "dashboard_report_work_{env}")
     ↓ 获取失败 → 跳过执行
  2. 调用 doJobWork()
  3. 释放锁（finally）
```

#### 2.2 doJobWork() / reportForDate()

```
reportForDate(date, communities):
  1. 计算时间窗口:
     startTime = date 00:00:00
     endTime   = date+1 00:00:00  (左闭右开)
     timestamp = date 23:50:00     (上报时间戳)
  2. 获取社区列表:
     communities 为空 → tblReposMapper.getAllDistinctCommunities()
     communities 非空 → 使用传入列表
  3. 逐社区循环:
     3.1 buildRequest(community, startTime, endTime, timestamp)
     3.2 openlibingFrameworkClient.reportDashboard(request)
     3.3 单社区失败不阻断后续 → 记录日志 + failCount++
```

#### 2.3 buildRequest() 4 项指标计算

```
buildRequest(community, startTime, endTime, timestamp):
  reportDate = formatDateTime(endTime)    // 次日 00:00:00

  // 指标1: 版本扫描次数
  versionScanCount = tblScanMapper
    .countByCommunityAndCreatedBetween(community, startTime, endTime)

  // 版本扫描 ID 列表（按 repo_id + branch 取最新）
  scanIds = tblScanMapper
    .findIdsByCommunityAndCreatedBetween(community, reportDate)

  // 指标2: PR 扫描次数
  prScanCount = tblPersonScanMapper
    .countPrByCommunityAndCreatedBetween(community, startTime, endTime)

  // 指标3: 版本扫描告警总数 (blockStatus != 'block')
  versionAlertTotal = countAlerts(scanIds, pendingOnly=false)

  // 指标4: 待处理告警总数 (叠加 reviewStatus != 40)
  pendingAlertTotal = countAlerts(scanIds, pendingOnly=true)

  return DashboardReportRequest{...}
```

#### 2.4 countAlerts - MongoDB 告警数统计

```
countAlerts(scanIds, pendingOnly):
  if scanIds 为空 → return 0
  构建 MongoDB Query:
    criteria: scanId in scanIds
              AND blockStatus != 'block'
    if pendingOnly: criteria AND reviewStatus != '40'
  return mongoTemplate.count(query, ScanIssueVO.class)
```

### 3. DashboardBackfillService 补录服务

#### 3.1 任务状态模型

```
DashboardBackfillTaskStatus (存 ConcurrentHashMap):
  State: PENDING → RUNNING → SUCCESS / PARTIAL / FAILED
  字段: taskId, state, startDate, endDate, totalDays,
        processedDays, successCount, failCount,
        currentDay, errorMessage, startTime, endTime
```

#### 3.2 补录执行流程

```
runBackfill(taskId, request):
  1. 获取 taskStatus，校验非空
  2. synchronized(status) 防并发:
     if state == RUNNING → return (已运行)
     state = RUNNING
  3. 按日期升序遍历:
     current = startDate, end = endDate
     while current <= end:
       int[] result = reportForDate(current, null)
       // null 表示自动获取全量社区
       更新 progress/successCount/failCount
       current.plusDays(1)
  4. 设定终态: SUCCESS / PARTIAL / FAILED
  5. 记录 endTime (finally)
```

### 4. 接口设计

#### POST `/dashboard/backfill`

- 鉴权：仅超级管理员
- 请求体 `DashboardBackfillRequest`:
  - `userId` (String, 必填)
  - `startDate` (LocalDate, 默认 2021-06-19)
  - `endDate` (LocalDate, 默认昨天)
- 响应：`{"taskId": "uuid"}`

### 5. Feign 接口

```
OpenlibingFrameworkClient.reportDashboard():
  POST /manage/feature-dashboard/report
  Body: DashboardReportRequest {
    community: "openEuler",
    feature: "开源合规",
    repo: "https://gitcode.com/openlibing/openlibing-sca",
    businessMetrics: {
      "version_scan_count": "5",
      "pr_scan_count": "10",
      "version_alert_total": "20",
      "pending_alert_total": "15"
    },
    userMetrics: {},
    timestamp: "2026-07-15 23:50:00"
  }
```

### 6. SQL 关键查询

#### getAllDistinctCommunities

```sql
-- 版本扫描社区
SELECT DISTINCT p.project_name AS community
FROM tbl_scan s
  INNER JOIN repo_info r ON s.repo_id = r.repo_id
  INNER JOIN project_info p ON p.project_id = r.project_id
WHERE r.has_repo = '1' AND p.project_name IS NOT NULL AND p.project_name != ''
UNION
-- PR 扫描社区
SELECT DISTINCT s.community
FROM tbl_person_scan s
  INNER JOIN repo_info r ON s.repo_id = r.repo_id
WHERE r.has_repo = '1' AND s.community IS NOT NULL AND s.community != ''
```

#### findIdsByCommunityAndCreatedBetween（取每仓库每分支最新扫描记录）

```sql
SELECT t.id FROM (
  SELECT s.id,
    ROW_NUMBER() OVER (PARTITION BY s.repo_id, s.branch ORDER BY s.modified DESC) AS rn
  FROM tbl_scan s
    INNER JOIN repo_info r ON s.repo_id = r.repo_id
    INNER JOIN project_info p ON p.project_id = r.project_id
  WHERE p.project_name = #{community}
    AND s.created < #{reportDate}
    AND r.has_repo = '1'
    AND s.scan_result = 1
) t WHERE t.rn = 1
```

### 7. 关键设计决策

| 决策点                  | 方案                                             | 原因                                                   |
| ----------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| 上报时间戳              | 固定报表日 23:50:00                              | 规避 MySQL DATETIME 对 23:59:59.x 的四舍五入越界风险   |
| scanIds 查询上界        | 使用 endTime（次日 00:00:00）                    | 与 versionScanCount 窗口一致，避免最后一刻扫描漏算告警 |
| 日期窗口                | 左闭右开 [startTime, endTime)                    | SQL 用 `>=` 和 `<` 确保不重不漏                        |
| 扫描去重                | ROW_NUMBER() OVER (PARTITION BY repo_id, branch) | 多分支仓库只取最新扫描                                 |
| 分布式锁                | Redisson tryLock(5s, -1) + 看门狗                | 防任务执行中锁释放；多实例互斥                         |
| 补录任务状态            | 内存 ConcurrentHashMap                           | 低频运维场景，重启丢失可接受                           |
| 补录任务并发控制        | synchronized(status 对象)                        | 同一 taskId 的 status 是同一引用，天然唯一锁           |
| 单社区异常处理          | catch 日志 + 继续                                | 单社区失败不影响其他社区                               |
| SpotBugs EI_EXPOSE_REP2 | 手写 Builder + 防御性拷贝                        | 替换 Lombok @Builder，避免可变 Map 引用泄露            |

## 影响范围

- **MySQL 表**: tbl_scan, tbl_person_scan, tbl_repos, project_info, repo_info（只读查询）
- **MongoDB 集合**: ScanIssueVO（只读查询）
- **Redis**: 分布式锁（key: `dashboard_report_work_{env}`）
- **外部依赖**: openlibing-framework `/manage/feature-dashboard/report` 接口
- **新增配置**: `${job.cron.dashboard.report.task}`（cron 表达式，默认 `0 0 1 * * ?`）
- **无需新建 MySQL 表**: 所有数据来自已有表
