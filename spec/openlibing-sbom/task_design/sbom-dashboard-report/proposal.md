# 【openlibing-sbom】数据看板上报

## 需求背景

openlibing 已提供运营数据看板（feature-dashboard），需要接入 sbom 相关运营数据。当前 sbom 服务已积累各社区的 SBOM 解析任务数据，但未向看板上报，运营看板缺少 sbom 维度的运营指标。

## 功能描述

- **做什么**：为每个激活的社区（ProductType），统计已走完全流程（`product_statistics` 表有记录）的制品数量，通过 Feign 调用 framework 的 `/manage/feature-dashboard/report` 接口上报到运营看板
- **不做什么**：不修改 framework 端看板接口、不修改 SBOM 解析流程、不上报用户 UV/PV 指标（sbom 服务不追踪用户行为）

## 验收标准

- [x] 定时任务每日凌晨 1 点自动执行（Quartz Job + 分布式锁），遍历所有激活的 ProductType，上报各社区已扫描制品包数量
- [x] 提供手动触发 Controller 端点（`GET /sbom-api/reportDashboard`），支持运维按需立即上报
- [x] 单社区上报失败不影响其他社区的上报（独立 try-catch + 日志记录）
- [x] Feign 调用 framework 接口 feature="SBOM"，业务指标 key="involved_product_count"，aggregationType="last_value"，值传 Long 数字
- [x] framework 返回非成功时记录日志，不抛异常中断整体流程
- [x] 统计数为 0 的社区跳过上报

## 影响范围

| 模块 | 文件 | 操作 |
|------|------|------|
| sbom-web/feign | FrameworkClient.java | 新增（返回 `com.openlibing.common.pojo.response.DataResult`） |
| sbom-web/service | SbomDashboardReportServiceImpl.java | 新增 |
| interface/api | SbomDashboardReportService.java | 新增（接口定义） |
| model/pojo | DashboardReportRequest.java | 新增（请求 DTO，对齐 framework 字段） |
| quartz/jobs | SbomDashboardReportJob.java | 新增（含分布式锁 + 可配置过期时间） |
| quartz/config | ScheduleBatchJobConfig.java | 修改（注册 Job，cron: UTC 17:00 = 北京 1:00） |
| sbom-web/controller | SbomController.java | 修改（新增 `/reportDashboard` 端点） |
| dao | ProductStatisticsRepository.java | 修改（新增 `countByProductType()`） |
| sbom-web/resources | application.properties | 修改（新增 `feign.framework.name`） |
| dao | QuartzLockRepository.java | 修改（`queryLockByLockName` + `FOR UPDATE`，`acquireLock` 支持过期时间参数） |
| clients | QuartzLockManagerImpl.java | 修改（`acquireLock` 按 `lockName` 全量查，删除 `renewLock`） |
| interface/api | QuartzLockManager.java | 修改（`acquireLock` 加 `expireMinutes`，删除 `renewLock`） |
| quartz/jobs | FetchMajunCveJob.java | 修改（适配新 `acquireLock` 签名，删除 `renewLock` 死代码） |

## 设计决策

- 统计口径：`product_statistics` 表（`CollectStatisticsStep` 写入），统计按 `COUNT(DISTINCT product_id)`，不依赖 `raw_sbom.task_status`
- 上报格式：`businessMetrics` 的 `involved_product_count` 传 Long 数字（last_value 类型接受 bare number）
- 分布式锁：`acquireLock` 按 `lockName` 全量查询 + `FOR UPDATE`，`SbomDashboardReportJob` 默认锁过期 60 分钟（可配置 `sbom.dashboard.report.lock.expire-minutes`）
- Feign：通过 Eureka 服务发现调用 `openlibing-framework`，不直连 URL
