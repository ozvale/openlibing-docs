# 运营看板数据自动上报

## 需求背景

SCA（软件成分分析）系统是开源合规门禁的核心服务，承载着多个社区（openEuler、PTA、MindIE 等）的版本扫描与 PR 扫描能力。当前缺乏对 SCA 运营指标的集中统计与可视化展示，管理层无法及时掌握各社区的扫描量、告警量和待处理量等关键运营数据。

需要在 openlibing-framework 运营看板中展示 SCA 系统的运营指标，因此需要 SCA 侧实现定时数据上报能力。

## 需求目标

1. **每日自动上报**：每日凌晨 1 点自动统计前一日各社区的 SCA 运营指标，通过 Feign 上报至 openlibing-framework 的 `/manage/feature-dashboard/report` 接口。
2. **历史数据补录**：提供 HTTP 接口支持对历史日期范围进行数据补录，确保运营看板数据完整。
3. **多实例互斥**：通过 Redis 分布式锁避免多实例重复执行上报任务。

## 4 项统计指标

| 指标 Key              | 指标含义                 | 数据来源                                                    |
| --------------------- | ------------------------ | ----------------------------------------------------------- |
| version_scan_count    | 版本扫描次数             | tbl_scan 表昨日 created 记录数                              |
| pr_scan_count         | PR 扫描次数              | tbl_person_scan 表昨日 created 且 scan_result='1'、un_confirmed_file_num 非空记录数 |
| version_alert_total   | 版本扫描告警总数         | 昨日版本扫描 scanIds 在 MongoDB ScanIssueVO 中 blockStatus != 'block' 的数量 |
| pending_alert_total   | 社区扫描待处理告警总数   | 在 version_alert_total 条件上叠加 reviewStatus != 40 的数量 |

## 验收标准

- [ ] 每日凌晨 1 点自动执行上报，遍历所有社区并逐社区调用 Feign 上报接口
- [ ] 分布式锁机制正常工作，同一环境下多个实例只有一个执行上报任务
- [ ] `/dashboard/backfill` 接口支持指定起始日期和结束日期的历史补录，异步执行并返回 taskId
- [ ] 补录接口仅超级管理员可调用，startDate 默认 2021-06-19，endDate 默认昨天
- [ ] 单社区上报失败不影响其他社区继续上报
- [ ] 上报时间戳固定为报表日 23:50:00，日期范围使用左闭右开区间避免边界问题
- [ ] 版本扫描记录按 repo_id + branch 去重取最新记录
- [ ] 单元测试覆盖定时任务主流程和边界场景

## 关联 PR

[openlibing/openlibing-sca#255](https://gitcode.com/openlibing/openlibing-sca/pull/255)
