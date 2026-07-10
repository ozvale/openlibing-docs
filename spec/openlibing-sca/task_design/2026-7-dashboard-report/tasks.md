# 每日凌晨1点定时上报运营看板数据 — 实现任务

## 进度: 0/7 complete

- [ ] Task 1: 新增 `DashboardReportRequest` DTO（含 UserMetrics、BusinessMetrics 嵌套类）
- [ ] Task 2: `OpenlibingFrameworkClient` 新增 `reportDashboard` 方法
- [ ] Task 3: `TblScanMapper` + XML 新增昨日版本扫描计数查询
- [ ] Task 4: `TblPersonScanMapper` + XML 新增昨日 PR 扫描计数 + 失败计数查询
- [ ] Task 5: 新增 `DashboardReportSchedule` 定时任务类（含时间窗口计算、MongoDB 告警查询、Feign 上报、异常隔离）
- [ ] Task 6: 编写单元测试（时间窗口、请求体构建、Mapper 调用验证）
- [ ] Task 7: 本地编译验证 + commit
