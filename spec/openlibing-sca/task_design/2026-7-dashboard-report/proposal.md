# 每日凌晨1点定时上报运营看板数据到 openlibing-framework

## 需求背景

openlibing-framework 提供了运营看板数据上报接口 `manage/feature-dashboard/report`（接口规范见 [dashboard-report-api-spec.md](https://gitcode.com/openlibing/openlibing-docs/blob/master/spec/openlibing-framework/task_design/2026-06-生态社区特性级运营看板/dashboard-report-api-spec.md)），用于各开源社区每日上报推广数据。

openlibing-sca 作为 SCA 门禁工具，需要每日凌晨 1 点定时上报前一日的扫描运营数据，让运营看板能反映 SCA 在各社区的运行情况。

业务 Issue：https://gitcode.com/qq_39751731/openlibing-sca/issues/3

## 功能描述

新增定时任务 `DashboardReportSchedule`，每日凌晨 1 点（cron `0 0 1 * * ?`）执行：

1. 遍历所有社区（来自 `tblReposMapper.getCommunity(null)`）
2. 对每个社区，统计前一日（昨日 00:00:00 ~ 23:59:59）的如下 5 个指标：
   - **版本扫描次数**：`tbl_scan` 表中该社区前一日 `created` 的扫描记录数
   - **PR 扫描次数**：`tbl_person_scan` 表中该社区前一日 `created` 的扫描记录数
   - **版本扫描告警总数**：前一日版本扫描产生的告警数（MongoDB `ScanIssueVO` 中 `scanId` 属于昨日版本扫描且 `blockStatus != BLOCK`）
   - **社区扫描待处理告警总数**：前一日版本扫描产生的待处理告警数（MongoDB `ScanIssueVO` 中 `scanId` 属于昨日版本扫描且 `blockStatus != BLOCK` 且 `reviewStatus != 40`）
   - **PR 未通过数**：`tbl_person_scan` 表中该社区前一日 `created` 且 `scan_result != '1'` 的扫描记录数
3. 通过 Feign 调用 `OpenlibingFrameworkClient` 的 `manage/feature-dashboard/report` 接口上报，请求体：
   ```json
   {
     "community": "<社区名>",
     "feature": "门禁检查",
     "user_metrics": { "uv": 0, "pv": 0 },
     "business_metrics": {
       "version_scan_count": "<数字>",
       "pr_scan_count": "<数字>",
       "version_alert_total": "<数字>",
       "pending_alert_total": "<数字>",
       "pr_failed_count": "<数字>"
     },
     "timestamp": "<前一日 23:59:59 ISO 8601>"
   }
   ```

## 不做什么

- 不实现 Token 认证（沿用现有 `OpenlibingFrameworkClient` 内部可信调用方式，与 `checkRepoUserNamePermission` 一致）
- 不修改任何数据库 schema
- 不修改 `OpenlibingFrameworkClient` 现有方法
- 不引入新的 Feign 拦截器
- 不做指标历史持久化（指标只在内存计算后上报）

## 验收标准

- [ ] 每日凌晨 1 点自动触发（cron `0 0 1 * * ?`），无需人工干预
- [ ] 多实例部署时通过 `DistributedLockService` 保证只有一个实例执行
- [ ] 每个社区上报一次请求，5 个指标全部填充昨日计数
- [ ] 调用失败不影响其他社区上报（异常隔离）
- [ ] Feign 调用失败有日志告警，不中断整个任务
- [ ] 单元测试覆盖：时间窗口计算、请求体构建、Mapper 查询条件
- [ ] 业务仓 PR 关联本 Issue，PR 打 `ai-assisted` 标签

## 影响范围

**业务仓**：`openlibing-sca`
- 新增：`common/feign/OpenlibingFrameworkClient`（增加 1 个方法）、`common/schedule/DashboardReportSchedule`、`common/domain/DashboardReportRequest`（DTO）
- 修改：`analysis/dao/TblScanMapper`（增加昨日扫描计数查询）、`analysis/dao/TblPersonScanMapper`（增加昨日扫描计数 + 失败计数查询）
- 新增 Mapper XML：相应查询语句

**docs 仓**：`openlibing-docs`
- 新增：`spec/openlibing-sca/task_design/2026-7-dashboard-report/{proposal,design,tasks}.md`

**外部依赖**：openlibing-framework 的 `manage/feature-dashboard/report` 接口（已存在）
