# manual-version-scheduled-scan

## 需求背景

手动版本扫描（`tbl_manual_version_scan`）目前只能通过 `/version/scan/startVersionScan` 接口人工逐个触发。部分接入版本扫描的仓库需要每日自动执行扫描，人工触发效率低且容易遗漏。

## 功能描述

### 增量一：定时扫描（2026-08-20 已交付）

1. `tbl_manual_version_scan` 表新增"是否定时"字段 `is_scheduled`（TINYINT，0-否，1-是），默认 0（否）：
   - 通过现有 `/version/scan/save` 接口（addRepo）可设置该字段，新增与更新路径均持久化
   - `/version/scan/query` 查询结果透出该字段
2. 新增定时任务，每天 00:00（cron `0 0 0 * * ?`）触发：
   - 查询表中 `is_scheduled=1` 且 `is_version_scan=1` 的仓库
   - 逐个投递到新增的定时扫描队列
3. 新增 RabbitMQ 独立队列（`amq_version_scheduled_direct` / `version_scheduled_queue` / `version_scheduled_rout_key`），定时扫描消息**必须串行执行**（listener `concurrency="1"`），不与现有 big/small 队列混跑
4. 扫描状态沿用现有手动扫描状态流转：`SCANNING → 成功/失败`，由 `updateManualVersionScanStatus` 回写 `tbl_manual_version_scan.scan_status`

### 增量二：批量定时任务接口 + 创建人/修改人审计字段（2026-08-20）

1. 新增**批量设置定时任务接口** `/version/scan/batchUpdateScheduled`：按记录 id 集合批量更新 `is_scheduled` 字段（同时更新 `update_time` / `update_by`）
2. `tbl_manual_version_scan` 表新增 2 个审计字段：
   - `create_by`（创建人，VARCHAR）：`/version/scan/save` 新增记录时写入操作人
   - `update_by`（修改人，VARCHAR）：以下场景维护 `update_time` + `update_by`：
     - 批量更新定时标记（新接口，操作人）
     - 手动扫描触发（`/version/scan/startVersionScan` 新增 `userName` 参数，操作人）
     - 定时扫描触发与扫描完成回写（无操作人，记 `system`）
3. `/version/scan/query` 透出 `createBy` / `updateBy`

## 不做什么

- 不改变现有手动扫描（`/version/scan/startVersionScan`）与自动版本扫描（`/scan/version`）行为（仅新增可选 `userName` 参数）
- 不新增定时频率配置（固定每天一次）
- 不引入新的扫描状态枚举
- 删除（`/version/scan/deleteByIds`）保持物理删除，被删除行不维护修改人

## 验收标准

### 增量一：定时扫描（已交付）

- [x] `tbl_manual_version_scan` 新增 `is_scheduled` 列（默认 0），历史数据不受影响
- [x] `/version/scan/save` 接口可设置 `is_scheduled`，新增与更新路径均正确持久化
- [x] `/version/scan/query` 透出 `isScheduled` 字段
- [x] 定时任务每天 00:00 触发，仅投递 `is_scheduled=1` 且 `is_version_scan=1` 的仓库
- [x] 多实例部署时定时任务只有一个实例执行（分布式锁）
- [x] 定时扫描消息进入独立队列且串行消费（concurrency=1），扫描状态正确回写
- [x] 单元测试覆盖定时任务选仓逻辑、addRepo 持久化与队列路由逻辑，全量单测通过

### 增量二：批量定时任务接口 + 审计字段（2026-08-20 已交付）

- [x] `tbl_manual_version_scan` 新增 `create_by` / `update_by` 列（VARCHAR，可空），历史数据不受影响
- [x] 新增 `/version/scan/batchUpdateScheduled` 接口：按 id 批量更新 `is_scheduled`，同时维护 `update_time` / `update_by`（操作人）
- [x] `/version/scan/save`：新增记录写入 `create_by`；更新记录维护 `update_by`
- [x] `/version/scan/startVersionScan` 新增 `userName` 参数，手动扫描触发时维护 `update_by`（操作人）
- [x] 定时扫描触发与扫描完成回写维护 `update_by=system`（新增 `ProjectConstant.SYSTEM_OPERATOR`）
- [x] `/version/scan/query` 透出 `createBy` / `updateBy`
- [x] 删除保持物理删除，不做软删除
- [x] 单元测试覆盖批量更新接口、addRepo 审计字段写入、扫描触发 update_by 维护，全量单测通过（1292 tests, 0 failures）

## 影响范围

- openlibing-sca 仓：
  - Liquibase 变更（新增 changeset + include）
  - `TblManualVersionScan` 实体 / `TblManualVersionScanMapper`（接口 + XML）
  - `ManualVersionScanAddPo` / `ManualVersionScanVO` / `ManualVersionScanStatusUpdatePo` / 新增批量更新 PO
  - `ManualVersionScanService(Impl)`
  - `IntegrationApiServiceImpl`（scheduled 队列发送分支；扫描回写 update_by）
  - `IntegrationApiListener`（新增 scheduled 队列监听器）
  - 新增 `ManualVersionScanSchedule`（common/schedule）
  - `ManualVersionScanController`（新增批量接口；startVersionScan 加 userName）
