# 手动版本扫描走独立 MQ 队列（按 size 分大小队列）

## 需求背景

`ManualVersionScanServiceImpl.startSingleScan` 当前通过 `integrationApiService.startVersionScan(versionScanPo, true)` 触发扫描，内部沿用 `/scan/version` 接口的 `sendToMqBasedOnRepoSize` 逻辑，根据仓库大小将消息发往 `version_big_queue` 或 `version_small_queue`。

手动版本扫描与接口触发的版本扫描共享同一套队列，存在以下问题：

- 两类业务在峰值期互相阻塞，无法独立伸缩
- 手动扫描与接口扫描的并发 / 限流策略无法分别配置
- 故障隔离粒度过粗，一类扫描堆积会影响另一类
- 手动扫描的批次与 `/scan/version` 接口共享消费者 `concurrency`，难以独立调优

`ms_20260818` 分支上曾尝试过 `amq_manual_version_scan_dispatch_direct` 方案（commit `f2f46590`），把整个 `startScan` 批次包到 MQ 里异步派发，已被回退。第一版方案采用精细做法：保留 `startScan` 同步入口与逐条 `startSingleScan` 流程，仅在 `startSingleScan` 内部把消息发往**单一**专用队列 `version_manual_queue`。

## 本次迭代背景

第一版单一队列方案已落地代码，但运行中发现：

- 手动扫描的批次里同时存在小仓库（< 10 MB）和大仓库（≥ 10 MB），小仓库扫描快、大仓库扫描慢，挤在同一队列时小仓库被大仓库阻塞
- 自动扫描侧已有 5 MB 分大小队列设计，手动扫描侧缺乏对应分流，难以针对大仓库单独配置 `prefetch` / `concurrency`

本次迭代在第一版"独立队列隔离手动与自动"基础上，进一步对手动队列按仓库 size 分大/小队列，阈值 **10 MB**（与自动扫描侧 5 MB 区分，反映手动扫描通常面对整仓而非单 MR、平均体积更大的实际分布）。

## 需求目标

1. 手动版本扫描消息走**独立**的 RabbitMQ 队列族，不再与 `/scan/version` 接口共享 `version_big_queue` / `version_small_queue`
2. 手动队列内部按仓库 size 分流：**> 10 MB 走 `version_manual_big_queue`，≤ 10 MB 走 `version_manual_small_queue`**
3. 队列消费者行为与现有 `receivedVersionBigMessage` / `receivedVersionSmallMessage` 完全一致：成功 `basicAck`，失败时 `updateManualVersionScanStatus(SCAN_FAILED)` + `tblScan.scanResult=-1` + 删除文件 + `basicReject(false)`
4. `ManualVersionScanServiceImpl#L214` 调用签名保持不变（仍调用 `integrationApiService.startVersionScan(versionScanPo, true)`），由 `IntegrationApiServiceImpl` 内部按 `isManualScan` 标志路由到独立大/小队列
5. 旧的单一 `version_manual_queue` 不保留 listener，部署时由运维 drain 残留消息后清理（应用启动时 RabbitMQ 自动声明保留新队列、不再声明旧队列的 listener 绑定）

## 验收标准

- [ ] 新增独立常量 `MANUAL_REPO_SIZE = 10_000_000L`（10 MB），与 `REPO_SIZE`（5 MB）解耦
- [ ] 新增 RabbitMQ 资源：
  - 大队列：exchange=`amq_version_manual_big_direct`、queue=`version_manual_big_queue`、routingKey=`version_manual_big_rout_key`
  - 小队列：exchange=`amq_version_manual_small_direct`、queue=`version_manual_small_queue`、routingKey=`version_manual_small_rout_key`
- [ ] `IntegrationApiServiceImpl.startVersionScan(versionScanPo, isManualScan)`：
  - `isManualScan=true` 时调用新增 `sendManualScanToMqBasedOnRepoSize`，按 `MANUAL_REPO_SIZE` 阈值路由到 manual_big / manual_small
  - `isManualScan=false` 时维持现有 `sendToMqBasedOnRepoSize` 行为不变（阈值仍是 `REPO_SIZE=5MB`）
- [ ] `IntegrationApiListener`：
  - 删除 `receivedVersionManualMessage`（单一 manual queue listener）
  - 新增 `receivedVersionManualBigMessage` 监听 `version_manual_big_queue`
  - 新增 `receivedVersionManualSmallMessage` 监听 `version_manual_small_queue`
  - 三个 listener 方法体与 `receivedVersionBigMessage` / `receivedVersionSmallMessage` 完全一致（仅 `@QueueBinding` 不同）
- [ ] `ManualVersionScanServiceImpl#L214` 调用签名不变
- [ ] 测试更新：
  - 修改 `IntegrationApiServiceImplTest` 中针对 `isManualScan=true` 的断言：从"直接 `convertAndSend` 到 `amq_version_manual_direct`"改为"调用 `sendManualScanToMqBasedOnRepoSize`，且不调用 `sendToMqBasedOnRepoSize`"
  - 修改 `IntegrationApiListenerTest` 中 `receivedVersionManualMessage` 测试为 `receivedVersionManualBigMessage` + `receivedVersionManualSmallMessage` 两个测试
  - 新增 `checkManualRepoSizeAndSendToMq_big` / `_small` / `_exception_fallback_big` 测试覆盖新增的分流方法
- [ ] `mvn test` 全量通过；pre-commit（Spotless/CheckStyle/SpotBugs/PMD）通过

## 影响范围

- 业务仓：`openlibing-sca`（2 个主代码文件 + 2 个测试文件，约 100 行）
- spec 仓：`openlibing-docs/spec/openlibing-sca/task_design/manual-version-scan-mq/`（更新已有 spec）
- 部署：
  - RabbitMQ 上新增 2 个 exchange + 2 个 queue（Spring `@QueueBinding` 自动声明）
  - 旧 `version_manual_queue` 变孤儿：部署前需 drain 残留消息，运维清理后从 broker 删除
  - HTTP 探测：手动扫描现在也要先打一次仓库 metadata 接口探 size，与自动扫描行为对齐；仓库 metadata 接口慢时手动扫描响应时延会轻微增加
- 数据模型：无变化
- 安全影响：无
- 接口契约：无外部接口变化（`IntegrationApiService` 接口签名不变）

## 关联 Issue

[openlibing/openlibing-sca#64](https://gitcode.com/openlibing/openlibing-sca/issues/64)
