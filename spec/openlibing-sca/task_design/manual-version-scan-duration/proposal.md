# manual-version-scan-duration

## 需求背景

手动版本扫描（`tbl_manual_version_scan`）的 `/version/scan/query` 接口会返回扫描耗时 `duration`，当前实现为 `updateTime - scanTime`（[ManualVersionScanServiceImpl.query](https://gitcode.com/openlibing/openlibing-sca/blob/master/src/main/java/com/openlibing/sca/dm/service/impl/ManualVersionScanServiceImpl.java) L150-L158）。

该计算成立的前提是 `update_time` 只在"扫描完成回调"（`updateManualVersionScanStatus`）时被更新，即 `update_time ≈ 扫描结束时间`。

`fff2704d`（批量定时接口 + 审计字段，2026-08-20）之后，`update_time` 语义变为**通用记录修改时间**，以下操作都会刷新它：

| 操作 | 触发点 |
|------|--------|
| 切换接入/定时状态 | `addRepo`（`updateByRepoIdAndBranchId`） |
| 批量设置定时 | `batchUpdateScheduledByIds` |
| 手动/定时扫描触发 | `updateScanStatusByRepoIdAndBranchId`（SCANNING） |
| 扫描完成回写 | `updateManualVersionScanStatus` |

因此"扫描结束后用户修改配置"也会刷新 `update_time`，导致耗时虚高（例如扫描完成 1 小时后切换定时开关，duration 会多出 3600s）。

## 功能描述

1. `tbl_manual_version_scan` 表新增 `finish_time` 列（DATETIME，可空）：**扫描结束时间**，仅在扫描成功/失败终态回调（`updateManualVersionScanStatus`）时写入。
2. `/version/scan/query` 透出 `finishTime` 字段，`duration` 计算改为 `finishTime - scanTime`。
3. `duration` 仅在 `finishTime` 与 `scanTime` 均非空且 `finishTime > scanTime` 时返回，否则为 null。

## 不做什么

- 不回填历史数据（历史行的 `update_time` 已被审计操作污染，无法可靠区分"扫描完成时间"；历史行 `finish_time` 为 NULL，`duration` 自然为空）
- 不改变 `scan_time` 语义（仍为扫描开始时间，扫描触发时写入）
- 不改变 `update_time` 语义（保持通用审计字段）
- 不改变 duration 输出格式（仍为秒，`<n>s`）
- 不新增/修改扫描状态枚举与接口签名（VO 加字段向后兼容）

## 验收标准

- [ ] `tbl_manual_version_scan` 新增 `finish_time` 列（DATETIME，可空），历史数据不受影响
- [ ] 扫描开始（手动/定时触发）不写 `finish_time`；扫描成功/失败终态回调写入 `finish_time = 回调时间`
- [ ] `/version/scan/query` 透出 `finishTime`
- [ ] `duration = finishTime - scanTime`（秒），仅当两者非空且 `finishTime > scanTime`；否则为 null
- [ ] 扫描结束后修改配置（addRepo / batchUpdateScheduled）不影响已记录的 `duration`
- [ ] 单元测试覆盖：终态回写 finishTime、query 耗时计算、finishTime 缺失/早于 scanTime 时 duration 为空；全量单测通过

## 影响范围

- openlibing-sca 仓：
  - Liquibase 变更（新增 changeset + include）
  - `TblManualVersionScan` 实体 / `ManualVersionScanStatusUpdatePo` / `ManualVersionScanVO`
  - `TblManualVersionScanMapper.xml`（resultMap / all_column / insert / updateScanStatusByRepoIdAndBranchId）
  - `ManualVersionScanServiceImpl`（query 耗时计算；两个扫描触发调用点适配新构造参数）
  - `IntegrationApiServiceImpl.updateManualVersionScanStatus`（终态回调写 finishTime）
  - 单测：`ManualVersionScanServiceImplTest` / `IntegrationApiServiceImplTest`
