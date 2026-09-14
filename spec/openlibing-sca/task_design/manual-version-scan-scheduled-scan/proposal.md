# manual-version-scan-scheduled-scan

## 需求背景

手动版本扫描（`tbl_manual_version_scan`）目前只能通过 `/version/scan/startVersionScan` 接口人工逐个触发。部分接入版本扫描的仓库需要每日自动执行扫描，人工触发效率低且容易遗漏。此前 Issue #66（旧版，固定 00:00）已关闭，本次重新设计：定时触发时间可配置化，并新增批量设置定时标记接口。

## 功能描述

### 做

1. `tbl_manual_version_scan` 新增记录级开关字段 `is_scheduled`（TINYINT，0-不定时，1-定时，默认 0）：
   - 通过现有 `/version/scan/save` 接口（addRepo）可设置该字段，新增与更新路径均持久化
   - `/version/scan/query` 查询结果透出该字段
2. 新增定时任务 `ManualVersionScanSchedule`，触发 cron **可配置**（配置中心，默认每天凌晨 00:00）：
   - 查询表中 `is_scheduled=1` 且 `is_version_scan=1` 的仓库
   - 逐个投递到新增的独立定时扫描队列
   - 多实例部署时只有一个实例执行（分布式锁）
3. 新增 RabbitMQ 独立队列（`amq_version_scheduled_direct` / `version_scheduled_queue` / `version_scheduled_rout_key`），定时扫描消息**串行执行**（listener concurrency=1），不与现有 big/small 队列混跑
4. 新增批量设置定时标记接口 `/version/scan/batchUpdateScheduled`：按记录 id 集合批量更新 `is_scheduled`
5. 扫描状态沿用现有手动扫描状态流转：SCANNING → 成功/失败，回写 `tbl_manual_version_scan.scan_status`

### 不做

- 不改动现有手动扫描（`/version/scan/startVersionScan`）与自动版本扫描（`/scan/version`）行为
- 不新增审计字段（create_by/update_by）与超大仓库体积门禁（is_oversize）
- 不新增频率多档配置，仅提供单个 cron 配置项

## 验收标准

- [ ] `tbl_manual_version_scan` 新增 `is_scheduled` 列（默认 0），历史数据不受影响
- [ ] `/version/scan/save` 接口可设置 `is_scheduled`，新增与更新路径均正确持久化
- [ ] `/version/scan/query` 透出 `isScheduled` 字段
- [ ] 定时任务按配置中心 cron 触发（默认每天 00:00），仅投递 `is_scheduled=1` 且 `is_version_scan=1` 的仓库
- [ ] 多实例部署时定时任务只有一个实例执行（分布式锁）
- [ ] 定时扫描消息进入独立队列且串行消费（concurrency=1），扫描状态正确回写
- [ ] 新增 `/version/scan/batchUpdateScheduled` 接口：按 id 批量更新 `is_scheduled`
- [ ] 单元测试覆盖定时任务选仓/跳过逻辑、addRepo 持久化、批量接口与队列路由逻辑，全量单测通过

## 影响范围

- openlibing-sca 仓：
  - Liquibase 变更（新增 changeset + include）
  - `TblManualVersionScan` 实体 / `ManualVersionScanAddPo` / `ManualVersionScanVO` / 新增批量更新 PO
  - `TblManualVersionScanMapper`（接口 + XML）
  - `ManualVersionScanService(Impl)`
  - `IntegrationApiService(Impl)`（scheduled 队列发送分支）
  - `IntegrationApiListener`（新增 scheduled 队列监听器）
  - 新增 `ManualVersionScanSchedule`（common/schedule）
  - `ManualVersionScanController`（新增批量接口）

## 关联

- 业务 Issue: https://gitcode.com/qq_39751731/openlibing-sca/issues/6
- 旧版参考 Issue: https://gitcode.com/openlibing/openlibing-sca/issues/66（已关闭，固定 00:00 版）
