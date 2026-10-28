# manual-version-scan-scheduled-scan — 实现任务

## 进度: 0/8 complete

- [ ] Task 1: Liquibase 新增 `is_scheduled` 列（`20260831/add-tbl-manual-version-scan-is-scheduled.xml`，TINYINT DEFAULT 0，preConditions + rollback）+ include 到 `db.changelog.xml`
- [ ] Task 2: `TblManualVersionScan` 实体 / `ManualVersionScanAddPo` / `ManualVersionScanVO` 加 `isScheduled` 字段；新增 `ManualVersionScanScheduledBatchPo`（`{ids, isScheduled}`）
- [ ] Task 3: `TblManualVersionScanMapper` 接口 + XML：resultMap / all_column / insert / `updateByRepoIdAndBranchId` 补 `is_scheduled` 列；新增 `selectScheduledScanRepos()` 与 `batchUpdateScheduledByIds()`
- [ ] Task 4: `ManualVersionScanServiceImpl`：`addRepo` 持久化 `isScheduled`（新增 + 更新路径）；`query` 透出；实现 `startScheduledScan`（SCANNING 跳过、单仓失败不中断）与 `batchUpdateScheduled`（空 ids 返回 0）
- [ ] Task 5: `IntegrationApiService(Impl)` 新增 scheduled 队列发送分支（直发 `amq_version_scheduled_direct`）
- [ ] Task 6: `IntegrationApiListener` 新增 `receivedVersionScheduledMessage`（`concurrency="1"`，复用 doScanV3 + 失败回写）
- [ ] Task 7: 新增 `ManualVersionScanSchedule`（cron `${job.cron.manual.version.scan:0 0 0 * * ?}` + 分布式锁）；`ManualVersionScanController` 新增 `/batchUpdateScheduled`
- [ ] Task 8: 单元测试（schedule 选仓/跳过逻辑、addRepo 持久化、批量接口、scheduled 队列路由）+ 相关验证通过
