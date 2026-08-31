# manual-version-scan-scheduled-scan — 技术设计

## 方案概述

`tbl_manual_version_scan` 加 `is_scheduled` 列；新增定时任务（cron 配置中心可配置，默认每天 00:00），捞取 `is_scheduled=1` 且 `is_version_scan=1` 的仓库，逐个经 `IntegrationApiServiceImpl.startVersionScan`（带队列类型参数）投递到新增的独立 scheduled 队列；新 listener `concurrency="1"` 串行消费，方法体复用现有 manual big/small 消费逻辑（`doScanV3` + 失败回写 + basicReject）。

## 架构决策

| 决策 | 理由 |
|------|------|
| 表加 `is_scheduled` TINYINT DEFAULT 0，additive changeset + preConditions onFail=MARK_RAN | 记录级配置，历史数据默认不定时，行为无变化 |
| cron 可配置：`@Scheduled(cron = "${job.cron.manual.version.scan:0 0 0 * * ?}")` | 对齐 `MindClusterLicenseSchedule`/`AutoBinaryLicenseSchedule` 的配置中心范式；支持不改代码调整触发时间；缺省值兜底每天 00:00 |
| 定时消息走独立 `version_scheduled_queue`（单一队列，`concurrency="1"` 串行） | 需求明确"必须串行执行"；独立队列避免凌晨批量投递挤占手动 big/small 队列资源 |
| 发送侧复用 `startVersionScan(versionScanPo, isManualScan)` 链路，新增第三个参数（或重载）区分 manual / scheduled 目标队列 | 保留 scanId 生成、`buildScanRequestVO`、`createScanRecord` 全链路；`isManualScan=true` 语义不变，下游 `doScanV3` / `updateManualVersionScanStatus` 状态回写完全复用 |
| listener 不做 HTTP size 探测 | 定时场景在凌晨批量投递，探测仓库 size 的 HTTP 往返拉长投递总时长且无分流价值（串行消费下大/小仓库都在同一队列排队）；超大仓库门禁不在本次范围 |
| 定时任务加 Redisson 分布式锁（key 带 env 后缀），范式对齐 `VersionScanSchedule` | 多实例部署时只跑一份；锁 key：`manual_version_scheduled_scan_<env>` |
| 投递前检查该仓库当前 `scan_status`，`SCANNING(0)` 状态跳过 | 防止前一天扫描未完成时重复投递同一仓库造成队列堆积 |
| 单仓失败不中断后续仓库，`try-catch` 包裹单仓投递 | 批量场景故障隔离，一个仓库异常不影响当天其他仓库投递 |
| 批量接口 `/batchUpdateScheduled`：body `{ids, isScheduled}`，空 ids 直接返回 0 不落 SQL | 对齐 `/save` 风格；service 层空集合防护 |

## 数据流

```
[每天凌晨（cron 可配置）] ManualVersionScanSchedule.triggerScheduledScan
  ├─ acquireLock("manual_version_scheduled_scan_<env>")  失败则跳过
  ├─ selectScheduledScanRepos(): is_scheduled=1 AND is_version_scan=1
  └─ for each repo:
       ├─ scan_status == SCANNING → skip（防止重复投递）
       └─ integrationApiService.startVersionScan(versionScanPo, true, SCHEDULED)
            ├─ generate scanId / buildScanRequestVO / createScanRecord（复用现有）
            ├─ convertAndSend("amq_version_scheduled_direct",
            │                 "version_scheduled_rout_key", msg)
            └─ return scanId
       └─ update tbl_manual_version_scan.scan_status = SCANNING

[消费端] IntegrationApiListener.receivedVersionScheduledMessage (concurrency="1")
  └─ doScanV3(scanRequestVO)   ← scanRequestVO.manualScan=true
       ├─ 成功: basicAck（doScanV3 内部回写 SCAN_SUCCESS）
       └─ 失败: updateManualVersionScanStatus(SCAN_FAILED) + tblScan.scanResult=-1
                + deleteVersionErrorFile + basicReject(false)
```

## 队列命名

沿用仓内 `amq_<biz>_<size>_direct` 风格，定时队列无 size 概念：

| 资源 | 值 |
|------|----|
| Exchange | `amq_version_scheduled_direct` |
| Queue | `version_scheduled_queue` |
| Routing Key | `version_scheduled_rout_key` |

命名与 manual big/small（`amq_version_big_direct` / `amq_version_small_direct`）刻意区分，避免历史 broker 残留资源混淆。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `db/changelog/mysql/20260831/add-tbl-manual-version-scan-is-scheduled.xml` | 新增 | addColumn `is_scheduled` TINYINT DEFAULT 0 |
| `db/changelog/db.changelog.xml` | 修改 | include 新 changeset |
| `analysis/entity/TblManualVersionScan.java` | 修改 | 加 `isScheduled` 字段 |
| `analysis/entity/dto/ManualVersionScanAddPo.java` | 修改 | 加 `isScheduled` |
| `analysis/entity/dto/ManualVersionScanScheduledBatchPo.java` | 新增 | `{ids: List\<String>, isScheduled: Integer}` |
| `analysis/entity/vo/ManualVersionScanVO.java` | 修改 | 加 `isScheduled` 透出 |
| `dm/dao/TblManualVersionScanMapper.java` | 修改 | 新增 `selectScheduledScanRepos()`、`batchUpdateScheduledByIds()` |
| `mapper/dm/TblManualVersionScanMapper.xml` | 修改 | resultMap / all_column / insert / update 语句补 `is_scheduled`；新增查询与批量 update SQL |
| `dm/service/ManualVersionScanService.java` | 修改 | 新增 `startScheduledScan()`、`batchUpdateScheduled()` 接口方法 |
| `dm/service/impl/ManualVersionScanServiceImpl.java` | 修改 | addRepo 持久化 `isScheduled`；实现 `startScheduledScan`（SCANNING 跳过、单仓失败不中断）；实现批量更新 |
| `dm/service/IntegrationApiService.java` | 修改 | 新增带队列类型重载 |
| `dm/service/impl/IntegrationApiServiceImpl.java` | 修改 | scheduled 分支直发 scheduled 队列 |
| `common/config/rabbitmq/IntegrationApiListener.java` | 修改 | 新增 `receivedVersionScheduledMessage` |
| `common/schedule/ManualVersionScanSchedule.java` | 新增 | cron 可配置定时任务 + 分布式锁 |
| `dm/controller/ManualVersionScanController.java` | 修改 | 新增 `/batchUpdateScheduled` |
| `src/test/java/...` | 修改/新增 | 定时任务、addRepo、批量接口、队列路由单测 |

## 定时任务设计（关键代码结构）

```java
@Component
public class ManualVersionScanSchedule {
  private static final String LOCK_KEY = "manual_version_scheduled_scan_";

  @Value("${spring.profiles.active}")
  private String env;

  @Resource private DistributedLockService lockService;
  @Autowired private ManualVersionScanService manualVersionScanService;

  /** 每天凌晨触发定时版本扫描，cron 可通过配置中心调整 */
  @Scheduled(cron = "${job.cron.manual.version.scan:0 0 0 * * ?}")
  public void triggerScheduledScan() {
    String lockKey = LOCK_KEY + env;
    try {
      if (!lockService.acquireLock(lockKey, 5)) {
        LOGGER.info("un get lock, skip execute: {}", lockKey);
        return;
      }
      manualVersionScanService.startScheduledScan();
    } catch (Exception e) {
      LOGGER.error("triggerScheduledScan error: {}", e.getMessage());
    } finally {
      lockService.releaseLock(lockKey);
    }
  }
}
```

`startScheduledScan()`：查 `selectScheduledScanRepos()`（`is_scheduled=1 AND is_version_scan=1`），逐条复用 `startSingleScan` 的校验与投递逻辑，`SCANNING` 状态跳过，单仓失败不影响后续仓库。

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 定时任务与用户手动触发同一仓库并发扫描 | 投递前检查 `scan_status=SCANNING` 跳过；极端窗口期（投递瞬间用户触发）由队列串行消费兜底，后到消息仍会执行但状态回写幂等 |
| broker 未声明新 exchange/queue 导致首次发送失败 | `@QueueBinding` 注解随应用启动自动声明（与 big/small 一致） |
| cron 配置错误导致定时任务异常 | `@Scheduled` 配置中心注入，非法 cron 会启动失败并暴露日志；默认值兜底；任务体 try-catch 包裹，锁 finally 释放 |
| 凌晨批量投递 + 串行消费，仓库多时当天跑不完 | 串行是需求硬约束；当前接入规模（十级）可接受，后续如超限再引入分片/优先级 |
| 定时任务异常导致锁未释放 | `finally` 中 releaseLock，范式与 `VersionScanSchedule` 一致 |
| 历史数据 `is_scheduled` 全 0 | 符合预期，默认不定时，行为无变化 |

## 跨仓影响

无。仅 openlibing-sca 仓内改动；`/version/scan/save` 仅新增可选字段，`/version/scan/query` 仅新增透出字段，均不破坏现有契约。
