# manual-version-scan-duration — 实现任务

- [x] Task 1: Liquibase 新增 `finish_time` 列（`20260824/add-tbl-manual-version-scan-finish-time.xml`）+ include 到 `db.changelog.xml`
- [x] Task 2: `TblManualVersionScan` 实体加 `finishTime`（防御性拷贝 getter/setter + JsonFormat）；`ManualVersionScanVO` 加 `finishTime`
- [x] Task 3: `ManualVersionScanStatusUpdatePo` 全参构造扩为 8 参（scanTime 后插 finishTime）+ 防御性拷贝 getter/setter
- [x] Task 4: `TblManualVersionScanMapper.xml`：resultMap / all_column / insert / `updateScanStatusByRepoIdAndBranchId` 补 `finish_time` 动态更新段
- [x] Task 5: `IntegrationApiServiceImpl.updateManualVersionScanStatus` 终态回调写 `finishTime = now`
- [x] Task 6: `ManualVersionScanServiceImpl`：`startSingleScan` / `startSingleScheduledScan` 构造调用适配（finishTime=null）；`query` 耗时改用 `finishTime - scanTime` 并透出 `finishTime`
- [x] Task 7: 单测更新（query 耗时用例改 finishTime、终态回写断言 finishTime、扫描后改配置不影响 duration）+ `python scripts/run-mvn.py clean test` 全量通过（1299 tests, 0 failures）
- [x] Task 8: 业务仓 commit（`9126061a fix(dm): compute manual version scan duration from finish_time`）
