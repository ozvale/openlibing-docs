# manual-version-scheduled-scan — 实现任务

## 增量一：定时扫描（已交付，commit 8ee7f8b5）

- [x] Task 1: Liquibase 新增 `is_scheduled` 列（`20260820/add-tbl-manual-version-scan-is-scheduled.xml`）+ include 到 `db.changelog.xml`
- [x] Task 2: `TblManualVersionScan` 实体 / `ManualVersionScanAddPo` / `ManualVersionScanVO` 加 `isScheduled` 字段
- [x] Task 3: `TblManualVersionScanMapper` 接口 + XML：新增 `selectScheduledScanRepos`；insert / updateByRepoIdAndBranchId 补 `is_scheduled` 列
- [x] Task 4: `ManualVersionScanServiceImpl.addRepo` 持久化 `isScheduled`（新增 + 更新路径）；`query` 透出
- [x] Task 5: `IntegrationApiService(Impl)` 新增 scheduled 队列发送分支（直发 `amq_version_scheduled_direct`，不做 size 探测）
- [x] Task 6: `IntegrationApiListener` 新增 `receivedVersionScheduledMessage`（`concurrency="1"`，复用 doScanV3 + 失败回写逻辑）
- [x] Task 7: 新增 `ManualVersionScanSchedule`（cron `0 0 0 * * ?` + 分布式锁）+ `ManualVersionScanService.startScheduledScan`（SCANNING 跳过、单仓失败不中断）
- [x] Task 8: 单元测试（schedule 选仓/跳过逻辑、addRepo 持久化、scheduled 队列路由）+ `python scripts/run-mvn.py clean test` 全量通过

## 增量二：批量定时任务接口 + 审计字段（已交付，commit fff2704d）

- [x] Task 9: Liquibase 新增 `create_by` / `update_by` 列（`20260820/add-tbl-manual-version-scan-audit-by.xml`）+ include 到 `db.changelog.xml`
- [x] Task 10: `TblManualVersionScan` 实体 / `ManualVersionScanVO` 加 `createBy` / `updateBy`；新增 `ManualVersionScanScheduledBatchPo`；`ManualVersionScanStatusUpdatePo` 加 `updateBy`
- [x] Task 11: `TblManualVersionScanMapper` 接口 + XML：新增 `batchUpdateScheduledByIds`；resultMap / all_column / insert / update 语句补审计列
- [x] Task 12: `ManualVersionScanService(Impl)`：实现 `batchUpdateScheduled`；`addRepo` 写 createBy/updateBy；`startScan` 加 userName 参数；scheduled 路径 updateBy=system；`IntegrationApiServiceImpl.updateManualVersionScanStatus` 回写 updateBy=system
- [x] Task 13: `ManualVersionScanController`：新增 `/version/scan/batchUpdateScheduled`；`/startVersionScan` 加 userName
- [x] Task 14: 单元测试（批量接口、审计字段写入、startScan 签名适配）+ `python scripts/run-mvn.py clean test` 全量通过（1292 tests, 0 failures）

> 实现偏差：系统操作人常量未复用 `ProjectConstant.RoleType.SYSTEM`（语义为角色分类），新增顶层常量 `ProjectConstant.SYSTEM_OPERATOR`（值 "system"）。
> 待部署验证：Liquibase 变更执行后历史数据 `create_by` / `update_by` 为 NULL 不影响现有逻辑；`/startVersionScan` 前端需同步传 `userName`。
