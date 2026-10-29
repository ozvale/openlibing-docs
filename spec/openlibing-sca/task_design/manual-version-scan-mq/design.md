# 设计文档：手动版本扫描走独立 MQ 队列（按 size 分大小队列）

## 1. 整体方案

保留 `ManualVersionScanServiceImpl.startScan → startSingleScan` 的同步入口与逐条处理流程不变，仅在 `IntegrationApiServiceImpl.startVersionScan(versionScanPo, isManualScan)` 内部按 `isManualScan` 标志分流：

- `isManualScan=true`：调用新增 `sendManualScanToMqBasedOnRepoSize`，按 `MANUAL_REPO_SIZE=10MB` 阈值路由到新增的 `amq_version_manual_big_direct` / `amq_version_manual_small_direct` 交换机
- `isManualScan=false`：维持现有 `sendToMqBasedOnRepoSize` 行为，按 `REPO_SIZE=5MB` 走 `version_big_queue` / `version_small_queue`

`IntegrationApiListener` 新增 `receivedVersionManualBigMessage` / `receivedVersionManualSmallMessage` 监听器消费手动大/小队列，方法体与 `receivedVersionBigMessage` / `receivedVersionSmallMessage` 完全一致：调用 `doScanV3`，失败时执行 `updateManualVersionScanStatus(SCAN_FAILED)` + `tblScan.scanResult=-1` + 删除文件 + `basicReject(false)`。原单一 `receivedVersionManualMessage` listener 删除。

## 2. 队列命名

沿用既有 `amq_version_<size>_direct` / `<size>_queue` / `<size>_rout_key` 约定，以 `manual_big` / `manual_small` 作为区分标识：

| 资源类型    | 大队列                          | 小队列                            |
| ----------- | ------------------------------- | --------------------------------- |
| Exchange    | `amq_version_manual_big_direct` | `amq_version_manual_small_direct` |
| Queue       | `version_manual_big_queue`      | `version_manual_small_queue`      |
| Routing Key | `version_manual_big_rout_key`   | `version_manual_small_rout_key`   |

命名与已回退的 `amq_manual_version_scan_dispatch_direct`（commit `f2f46590`）以及第一版单一 `amq_version_manual_direct` / `version_manual_queue` 都刻意不同，避免历史 broker 上残留同名资源造成混淆。

阈值常量：

```java
// 自动扫描（/scan/version 接口）阈值，保持不变
private static final long REPO_SIZE = 5_000_000L;

// 手动扫描阈值，本次新增
private static final long MANUAL_REPO_SIZE = 10_000_000L;
```

## 3. 关键改动点

### 3.1 `IntegrationApiServiceImpl.startVersionScan`

```java
@Override
public String startVersionScan(VersionScanPo versionScanPo, boolean isManualScan) {
  String repoUrl = versionScanPo.getRepoUrl();
  LOGGER.info("repoUrl============={}", LogSanitizer.sanitizeForLog(repoUrl));
  validateRepoUrl(repoUrl);
  if (!repoUrl.endsWith(".git")) {
    repoUrl = repoUrl + ".git";
  }
  String scanId = UUID.randomUUID().toString();
  ScanRequestVO scanRequestVO = buildScanRequestVO(versionScanPo, repoUrl, scanId);
  scanRequestVO.setManualScan(isManualScan);
  createScanRecord(versionScanPo, scanId, scanRequestVO, repoUrl);
  String msg = JSONObject.toJSONString(scanRequestVO);
  RepoInfoEntity repoInfoEntity = repoInfoMapper.queryById(scanRequestVO.getReposId());
  if (isManualScan) {
    // 手动版本扫描走独立大小队列，不与 /scan/version 接口共享 big/small 队列
    sendManualScanToMqBasedOnRepoSize(versionScanPo, scanRequestVO, repoInfoEntity, msg);
  } else {
    sendToMqBasedOnRepoSize(versionScanPo, scanRequestVO, repoInfoEntity, msg);
  }
  LOGGER.info("scanId================={}", scanId);
  return scanId;
}
```

要点：

- `scanId` 生成、`buildScanRequestVO`、`createScanRecord` 全部保留
- `repoInfoEntity` 查询提到 `if` 之前，因为 manual 路径也需要 token 取仓库 size
- `manualScan` 标志已透传到 `ScanRequestVO`，下游 `doScanV3` 无需感知队列来源

### 3.2 `IntegrationApiServiceImpl.sendManualScanToMqBasedOnRepoSize` / `checkManualRepoSizeAndSendToMq`

新增方法镜像现有 `sendToMqBasedOnRepoSize` / `checkRepoSizeAndSendToMq`，区别：

- 阈值用 `MANUAL_REPO_SIZE`（10 MB）而非 `REPO_SIZE`（5 MB）
- 路由到 `amq_version_manual_big_direct` / `amq_version_manual_small_direct`
- 异常 / 非 200 兜底走 `amq_version_manual_big_direct`（与自动扫描侧兜底策略一致）

`buildRepoSizeCheckUrl` 复用现有方法，不新增——只是构建查询仓库 size 的 URL，与队列无关。

### 3.3 `IntegrationApiListener.receivedVersionManualBigMessage` / `receivedVersionManualSmallMessage`

```java
@RabbitListener(
    bindings =
        @QueueBinding(
            exchange = @Exchange("amq_version_manual_big_direct"),
            key = "version_manual_big_rout_key",
            value = @Queue("version_manual_big_queue")))
public void receivedVersionManualBigMessage(
    Message message, Channel channel, CorrelationData correlationData) throws IOException {
  // 方法体与 receivedVersionBigMessage 完全一致
  ...
}

@RabbitListener(
    bindings =
        @QueueBinding(
            exchange = @Exchange("amq_version_manual_small_direct"),
            key = "version_manual_small_rout_key",
            value = @Queue("version_manual_small_queue")))
public void receivedVersionManualSmallMessage(
    Message message, Channel channel, CorrelationData correlationData) throws IOException {
  // 方法体与 receivedVersionSmallMessage 完全一致
  ...
}
```

原单一 `receivedVersionManualMessage` 监听器删除，旧 `version_manual_queue` 不保留 listener，部署时由运维 drain 残留消息后清理。

### 3.4 `ManualVersionScanServiceImpl#L214`

不修改，保持原调用：

```java
String scanId = integrationApiService.startVersionScan(versionScanPo, true);
```

## 4. 数据流

```
ManualVersionScanController.startScan
  └─ ManualVersionScanService.startScan (同步循环)
       └─ startSingleScan
            ├─ validate / lookup repoInfo
            ├─ build VersionScanPo
            ├─ integrationApiService.startVersionScan(versionScanPo, true)   ← L214 不变
            │    ├─ generate scanId (UUID)
            │    ├─ buildScanRequestVO + createScanRecord
            │    ├─ query repoInfoEntity (for token / repo size URL)
            │    ├─ [NEW] isManualScan=true → sendManualScanToMqBasedOnRepoSize
            │    │    └─ checkManualRepoSizeAndSendToMq
            │    │         ├─ length > 10MB → amq_version_manual_big_direct
            │    │         └─ length ≤ 10MB → amq_version_manual_small_direct
            │    │           (异常 / 非 200 兜底 → manual_big)
            │    └─ return scanId
            ├─ update tbl_manual_version_scan.scan_status = SCANNING
            └─ return scanId

[消费端]
IntegrationApiListener.receivedVersionManualBigMessage
  └─ doScanV3(scanRequestVO)
       └─ on success: basicAck
       └─ on failure: updateManualVersionScanStatus(SCAN_FAILED) + tblScan.scanResult=-1 + delete files + basicReject(false)

IntegrationApiListener.receivedVersionManualSmallMessage  (行为同上)
```

## 5. 兼容性与回滚

- 旧的 `version_big_queue` / `version_small_queue` 行为完全不变，`/scan/version` 接口路径无感知
- 旧的单一 `version_manual_queue`：listener 删除后该队列变孤儿。部署前运维需 drain 残留消息（若有）后从 broker 删除；不 drain 也不会影响新队列消费
- 若需快速回滚：恢复 `IntegrationApiServiceImpl.startVersionScan` 中 `isManualScan` 分支为第一版的"直接 `convertAndSend` 到 `amq_version_manual_direct`"即可，并恢复 `receivedVersionManualMessage` listener

## 6. 风险与缓解

| 风险                                                                                      | 缓解                                                                                                                  |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| RabbitMQ broker 上未声明新 exchange/queue 导致首次发送失败                                | Spring `@QueueBinding` 注解自动声明，与应用启动同步                                                                   |
| 消费者 `concurrency` 未指定，默认与 `receivedVersionBigMessage` 不同                      | 不显式指定 `concurrency`，使用 Spring AMQP 默认值（与 `version_big_queue` 一致）                                      |
| 历史 broker 上残留 `amq_version_manual_direct` / `version_manual_queue`（第一版单一队列） | 新命名 `amq_version_manual_big_direct` / `amq_version_manual_small_direct` 与第一版刻意不同，无冲突；旧队列由运维清理 |
| HTTP 探测仓库 size 接口慢导致手动扫描响应时延增加                                         | 与自动扫描侧行为对齐，无可避免的额外 HTTP 一次往返；后续可考虑缓存 repo size                                          |
| 仓库 metadata 接口非 200 或异常时全部兜底到 manual_big，可能让小仓库也被丢到大队列        | 与自动扫描侧兜底策略一致，先求稳再优化；后续可加更精细的兜底（如重试）                                                |

## 7. 测试策略

- **单元测试**：
  - `IntegrationApiServiceImplTest`：
    - 原 `testStartVersionScan_ManualScanTrue_RoutesToManualQueue` 改为 `testStartVersionScan_ManualScanTrue_CallsSendManualScanToMqBasedOnRepoSize`：验证 `isManualScan=true` 时调用 `sendManualScanToMqBasedOnRepoSize`，且不调用 `sendToMqBasedOnRepoSize`
    - 新增 `testCheckManualRepoSizeAndSendToMq_Big`：response body length > 10MB → 路由到 `amq_version_manual_big_direct`
    - 新增 `testCheckManualRepoSizeAndSendToMq_Small`：response body length ≤ 10MB → 路由到 `amq_version_manual_small_direct`
    - 新增 `testCheckManualRepoSizeAndSendToMq_ExceptionFallbackBig`：HTTP 异常时兜底 `amq_version_manual_big_direct`
  - `IntegrationApiListenerTest`：
    - 原 `receivedVersionManualMessage_Success` / `_Failure` 替换为 `receivedVersionManualBigMessage_Success` / `_Failure` + `receivedVersionManualSmallMessage_Success` / `_Failure`（共 4 个测试，mock 结构复用现有 big/small 队列测试）
- **回归测试**：`mvn test` 全量通过；`ManualVersionScanServiceImplTest.startScan_success` 继续通过（mock `integrationApiService.startVersionScan` 返回 "scan-001" 不变）
- **集成自测**（用户负责）：启动应用，调用 `POST /version/scan/startVersionScan`，观察 RabbitMQ 控制台出现 `version_manual_big_queue` / `version_manual_small_queue` 且消息按仓库 size 被消费到对应队列，`tbl_manual_version_scan.scan_status` 流转 `SCANNING → 成功/失败` 正常
