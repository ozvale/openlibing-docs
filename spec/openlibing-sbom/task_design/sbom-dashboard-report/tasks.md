# 【openlibing-sbom】数据看板上报 — 实现任务

## 进度: 6/6 complete

- [x] Task 1: 新增 `FrameworkClient` Feign 接口 — `POST /manage/feature-dashboard/report`，返回 `DataResult<Map>`，参数 `DashboardReportRequest` DTO
- [x] Task 2: 新增 `ProductStatisticsRepository.countByProductType()` — `COUNT(DISTINCT product_id)` JOIN product 按 `attribute ->> 'productType'` 过滤
- [x] Task 3: 新增 `SbomDashboardReportService` — 遍历激活社区、统计 `product_statistics`、0 则跳过、调用 Feign 上报、单社区异常隔离
- [x] Task 4: 新增 `SbomDashboardReportJob` Quartz 定时任务 — 凌晨 1 点（UTC 17:00），分布式锁过期时间可配置
- [x] Task 5: 修改 `ScheduleBatchJobConfig` — 注册 `sbomDashboardReportJobDetail` + `sbomDashboardReportJobTrigger`
- [x] Task 6: 修改 `SbomController` — 新增 `GET /sbom-api/reportDashboard` 手动触发端点 + `application.properties` 配置
- [x] Task 7: 重构 `QuartzLockManager` — `acquireLock` 按 `lockName` 全量查询 + `FOR UPDATE`，支持 `expireMinutes` 参数，删除 `renewLock` 死代码
