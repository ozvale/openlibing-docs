# 每日凌晨1点定时上报运营看板数据 — 技术设计

## 方案概述

新增 `DashboardReportSchedule` 定时任务，每日凌晨 1 点通过 Feign 调用 `OpenlibingFrameworkClient.reportDashboard()` 上报各社区前一日 SCA 运营指标。任务复用现有 `DistributedLockService` 防止多实例重复执行，复用 `MongoTemplate` 查询告警数据，复用 `TblReposMapper/TblScanMapper/TblPersonScanMapper` 查询扫描计数。

## 架构决策

### 1. 时间窗口计算
- **昨日 00:00:00 ~ 23:59:59**（按服务器本地时区，Spring Boot 默认 GMT+8）
- 使用 `LocalDate.now().minusDays(1).atStartOfDay()` 和 `LocalDate.now().minusDays(1).atTime(LocalTime.MAX)` 计算
- 转换为 `java.util.Date` 传给 Mapper

### 2. 指标数据源
| 指标 | 数据源 | 查询条件 |
|------|--------|---------|
| 版本扫描次数 | MySQL `tbl_scan` JOIN `tbl_repo` | `r.community = ?` AND `s.created BETWEEN ? AND ?` |
| PR 扫描次数 | MySQL `tbl_person_scan` JOIN `tbl_repo` | `r.community = ?` AND `s.created BETWEEN ? AND ?` |
| 版本扫描告警总数 | MongoDB `ScanIssueVO` | `scanId IN (昨日版本扫描IDs)` AND `blockStatus != BLOCK` |
| 社区扫描待处理告警总数 | MongoDB `ScanIssueVO` | `scanId IN (昨日版本扫描IDs)` AND `blockStatus != BLOCK` AND `reviewStatus != 40` |
| PR 未通过数 | MySQL `tbl_person_scan` JOIN `tbl_repo` | `r.community = ?` AND `s.created BETWEEN ? AND ?` AND `s.scan_result != '1'` |

> **注**：版本扫描告警总数和待处理告警总数按用户决策"5 个全部用昨日计数"——即只统计昨日版本扫描产生的告警，而非当前快照。这与 `PendingCountSchedule` 的 Redis 缓存口径不同，需独立查询。

### 3. Feign 调用
- `OpenlibingFrameworkClient` 现有 `@FeignClient(name = "https://openlibing-framework")` 配置直接复用
- 新增方法 `reportDashboard(@RequestBody DashboardReportRequest request)`
- **不携带 Authorization 头**（用户决策：沿用现有内部可信调用方式）
- 路径：`/openlibing-framework/manage/feature-dashboard/report`（按规范文档实际路径，注意 `dashboard` 拼写）

### 4. 异常隔离
- 每个社区独立 try-catch，单个社区失败不影响其他社区
- Feign 调用失败记录 WARN 日志，不抛出
- 整个任务外层有 `DistributedLockService` 保护

### 5. community 字段大小写
- `tblReposMapper.getCommunity(null)` 返回的 `community` 字段在数据库中可能大小写不一致
- 上报时直接用数据库原值（规范 enum 接受 "MindIE", "PTA", "MindSpeed", "openEuler", "HPCkit", "UBS Core", "openUBMC", "CANN", "openLiBing"），不做 toLowerCase 转换

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `common/feign/OpenlibingFrameworkClient.java` | 修改 | 新增 `reportDashboard` 方法 |
| `common/domain/DashboardReportRequest.java` | 新增 | 上报请求 DTO（含 user_metrics、business_metrics 嵌套结构） |
| `common/schedule/DashboardReportSchedule.java` | 新增 | 定时任务主类 |
| `analysis/dao/TblScanMapper.java` | 修改 | 新增 `countByCommunityAndCreatedBetween` 方法 |
| `analysis/dao/TblPersonScanMapper.java` | 修改 | 新增 `countByCommunityAndCreatedBetween` 和 `countFailedByCommunityAndCreatedBetween` 方法 |
| `resources/mapper/analysis/TblScanMapper.xml` | 修改 | 新增昨日扫描计数 SQL |
| `resources/mapper/analysis/TblPersonScanMapper.xml` | 修改 | 新增昨日扫描计数 + 失败计数 SQL |
| `test/.../DashboardReportScheduleTest.java` | 新增 | 单元测试 |

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| Feign 调用超时导致整个任务卡住 | 配置 Feign 超时；每社区独立 try-catch |
| 社区数量多导致串行上报慢 | 上报是 IO 密集型，但每日只跑一次且凌晨低峰，串行可接受；后续可改 `@Async` |
| MongoDB 查询慢（scanIds 列表过长） | 昨日版本扫描数量有限，IN 查询可接受；必要时加 scanId 索引 |
| 时区问题 | 使用服务器本地时区（GMT+8），与现有 `PendingCountSchedule` 一致 |
| 数据库 community 大小写与规范 enum 不匹配 | 上报时用数据库原值；若 framework 返回 400 再降级处理 |

## 跨仓影响

- **openlibing-framework**：仅作为调用方，不修改其代码。依赖其 `manage/feature-dashboard/report` 接口可用。
- **openlibing-docs**：本 spec 文档落盘到 `spec/openlibing-sca/task_design/2026-7-dashboard-report/`。
