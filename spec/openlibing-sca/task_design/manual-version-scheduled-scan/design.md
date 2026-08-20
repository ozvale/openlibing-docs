# manual-version-scheduled-scan — 技术设计

## 方案概述

`tbl_manual_version_scan` 加 `is_scheduled` 列；新增每天 00:00 的 `@Scheduled` 任务（分布式锁保证多实例单跑），把 `is_scheduled=1` 的仓库逐个经 `IntegrationApiServiceImpl.startVersionScan(po, true)` 走**新增的 scheduled 单一队列**发送；新 listener `concurrency="1"` 串行消费，方法体复用现有 manual big/small 消费逻辑（`doScanV3` + 失败回写 + basicReject）。

## 架构决策

| 决策 | 理由 |
|------|------|
| 定时消息走独立 `version_scheduled_queue`（单一队列，不按 size 分大小队列） | 需求明确"必须串行执行"；单一队列 + `concurrency="1"` 是 RabbitMQ 最直接的串行保证。若按 size 拆两个队列则两个 listener 各自并发，破坏串行语义 |
| 发送侧复用 `startVersionScan(versionScanPo, isManualScan)`，新增第三个参数 `queueType`（或重载）区分 manual / scheduled 目标队列 | 保留 `scanId` 生成、`buildScanRequestVO`、`createScanRecord` 全链路；`isManualScan=true` 语义不变（`ScanRequestVO.manualScan=true`），下游 `doScanV3` / `updateManualVersionScanStatus` 状态回写完全复用，无新增分支 |
| listener 不做 HTTP size 探测 | 定时场景在凌晨批量投递，探测仓库 size 的 HTTP 往返会拉长投递总时长且无分流价值（串行消费下大/小仓库都在同一队列排队） |
| 定时任务加 Redisson 分布式锁（key 带 env 后缀），范式对齐 `VersionScanSchedule` | 多实例部署时只跑一份；锁 key：`manual_version_scheduled_scan_<env>` |
| 投递前检查该仓库当前 `scan_status`，`SCANNING(0)` 状态跳过 | 防止前一天扫描未完成时重复投递同一仓库造成队列堆积 |
| `is_scheduled` 默认 0，additive changeset，`preConditions onFail=MARK_RAN` 防重复执行 | 历史数据全部视为"不定时"，行为无变化 |

## 数据流

```
[每天 00:00] ManualVersionScanSchedule.triggerScheduledScan
  ├─ acquireLock("manual_version_scheduled_scan_<env>")  失败则跳过
  ├─ selectScheduledScanRepos(): is_scheduled=1 AND is_version_scan=1
  └─ for each repo:
       ├─ scan_status == SCANNING → skip（防止重复投递）
       └─ integrationApiService.startVersionScan(versionScanPo, true, SCHEDULED)
            ├─ generate scanId / buildScanRequestVO / createScanRecord（复用现有）
            ├─ convertAndSend("amq_version_scheduled_direct",
            │                 "version_scheduled_rout_key", msg)   ← 不做 size 探测
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

命名与 manual big/small（`amq_version_manual_big_direct` 等）刻意区分，避免历史 broker 残留资源混淆。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `db/changelog/mysql/20260820/add-tbl-manual-version-scan-is-scheduled.xml` | 新增 | addColumn `is_scheduled` TINYINT DEFAULT 0 |
| `db/changelog/db.changelog.xml` | 修改 | include 新 changeset |
| `analysis/entity/TblManualVersionScan.java` | 修改 | 加 `isScheduled` 字段 |
| `analysis/entity/dto/ManualVersionScanAddPo.java` | 修改 | 加 `isScheduled` |
| `analysis/entity/vo/ManualVersionScanVO.java` | 修改 | 加 `isScheduled` 透出 |
| `dm/dao/TblManualVersionScanMapper.java` | 修改 | 新增 `selectScheduledScanRepos()` |
| `mapper/dm/TblManualVersionScanMapper.xml` | 修改 | 新增查询 SQL；insert/update 语句补 `is_scheduled` 列 |
| `dm/service/ManualVersionScanService.java` | 修改 | 新增 `startScheduledScan()` 接口方法 |
| `dm/service/impl/ManualVersionScanServiceImpl.java` | 修改 | addRepo 持久化 `isScheduled`；实现 `startScheduledScan` |
| `dm/service/IntegrationApiService.java` | 修改 | 新增带队列类型重载 |
| `dm/service/impl/IntegrationApiServiceImpl.java` | 修改 | scheduled 分支直发 scheduled 队列 |
| `common/config/rabbitmq/IntegrationApiListener.java` | 修改 | 新增 `receivedVersionScheduledMessage` |
| `common/schedule/ManualVersionScanSchedule.java` | 新增 | 每天 00:00 定时任务 + 分布式锁 |
| `src/test/java/...` | 修改/新增 | 定时任务、addRepo、队列路由单测 |

## 定时任务设计（关键代码结构）

```java
@EnableScheduling
@Component
public class ManualVersionScanSchedule {
  private static final String LOCK_KEY = "manual_version_scheduled_scan_";

  @Value("${spring.profiles.active}")
  private String env;

  @Resource private DistributedLockService lockService;
  @Autowired private ManualVersionScanService manualVersionScanService;

  /** 每天凌晨 00:00 触发定时版本扫描 */
  @Scheduled(cron = "0 0 0 * * ?")
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
| broker 未声明新 exchange/queue 导致首次发送失败 | `@QueueBinding` 注解随应用启动自动声明（与 manual big/small 一致） |
| 凌晨批量投递 + 串行消费，仓库多时当天跑不完 | 串行是需求硬约束；先按当前接入规模（十级）评估可接受，后续如超限再引入分片/优先级 |
| 定时任务异常导致锁未释放 | `finally` 中 releaseLock，范式与 `VersionScanSchedule` 一致 |
| 历史数据 `is_scheduled` 全 0 | 符合预期，默认不定时，行为无变化 |

## 跨仓影响

无。仅 openlibing-sca 仓内改动，不涉及对外接口契约变化（`/version/scan/save` 仅新增可选字段）。

---

# 增量二：批量定时任务接口 + 创建人/修改人审计字段

## 方案概述

`tbl_manual_version_scan` 加 `create_by` / `update_by` 两列（VARCHAR(64) 可空，additive changeset）；新增 `/version/scan/batchUpdateScheduled` 接口按 id 集合批量更新 `is_scheduled` 并维护 `update_time` / `update_by`；手动扫描接口 `/startVersionScan` 加 `userName` 参数记录操作人；无操作人场景（定时扫描触发、扫描完成回写）统一记 `ProjectConstant.SYSTEM_OPERATOR`（"system"，实现时新增的顶层常量——原计划复用 `ProjectConstant.SYSTEM`，但该常量实际位于 `RoleType` 内部类且语义为角色分类，故新增语义正确的顶层常量）。

## 架构决策

| 决策 | 理由 |
|------|------|
| 批量接口用独立 POST `/version/scan/batchUpdateScheduled`，body 为 `{ids, isScheduled}`，操作人走 `@RequestParam userName` | 对齐 `/save`、`/deleteByIds` 既有风格（userName 用 query param、业务数据用 body） |
| `create_by` / `update_by` VARCHAR(64) 可空 + `preConditions onFail=MARK_RAN` + rollback | 与 `is_scheduled` 变更同一范式；历史数据为 NULL 不影响现有逻辑 |
| 手动扫描 `/startVersionScan` 加 `userName` 参数（对齐 `/save` 的必填 query param） | 需求明确记录扫描操作人；前端同步改造，缺参即时报错反馈 |
| 定时扫描触发、扫描完成回写 `update_by = system`（新增 `ProjectConstant.SYSTEM_OPERATOR`） | 这两处无用户上下文；`ProjectConstant` 原无此常量（`RoleType.SYSTEM` 语义为角色分类），新增顶层常量复用 |
| 删除保持物理 DELETE，不维护修改人 | 行已删除无从更新；用户确认不做软删除 |
| `ManualVersionScanStatusUpdatePo` 构造器扩为 7 参（尾部加 `updateBy`） | 全部 3 个调用点集中在本仓两文件，随签名一并更新 |
| insert 时同时写 `create_by` 和 `update_by` | 与 insert 同时写 `create_time` / `update_time` 的既有行为对齐 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `db/changelog/mysql/20260820/add-tbl-manual-version-scan-audit-by.xml` | 新增 | addColumn `create_by` / `update_by` VARCHAR(64) |
| `db/changelog/db.changelog.xml` | 修改 | include 新 changeset |
| `analysis/entity/TblManualVersionScan.java` | 修改 | 加 `createBy` / `updateBy` 字段 |
| `analysis/entity/dto/ManualVersionScanScheduledBatchPo.java` | 新增 | `{ids: List<String>, isScheduled: Integer}` |
| `analysis/entity/dto/ManualVersionScanStatusUpdatePo.java` | 修改 | 加 `updateBy`（构造器扩 7 参） |
| `analysis/entity/vo/ManualVersionScanVO.java` | 修改 | 加 `createBy` / `updateBy` 透出 |
| `dm/dao/TblManualVersionScanMapper.java` | 修改 | 新增 `batchUpdateScheduledByIds` |
| `mapper/dm/TblManualVersionScanMapper.xml` | 修改 | resultMap / all_column / insert / 两条 update 补审计列；新增批量 update SQL |
| `dm/service/ManualVersionScanService.java` | 修改 | 新增 `batchUpdateScheduled`；`startScan` 加 userName 参数 |
| `dm/service/impl/ManualVersionScanServiceImpl.java` | 修改 | addRepo 写 createBy/updateBy；startScan 传操作人；scheduled 路径记 system；实现批量更新 |
| `dm/service/impl/IntegrationApiServiceImpl.java` | 修改 | `updateManualVersionScanStatus` 回写 updateBy=system |
| `dm/controller/ManualVersionScanController.java` | 修改 | 新增 `/batchUpdateScheduled`；`/startVersionScan` 加 userName |
| `src/test/java/...` | 修改 | 批量接口、审计字段、startScan 签名相关单测 |

## 关键 SQL

```sql
-- 批量更新定时标记
UPDATE tbl_manual_version_scan
SET is_scheduled = #{isScheduled}, update_time = #{updateTime}, update_by = #{updateBy}
WHERE id IN (...)
```

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| `/startVersionScan` 加必填参数导致旧前端调用报错 | 前端同步改造；接口缺参即时报错属预期反馈 |
| 扫描完成回写将 update_by 覆盖为 system，掩盖用户此前操作 | 符合"扫描即修改"语义；最后一次扫描完成即最后修改 |
| ids 为空集合生成非法 SQL | service 层空集合直接返回 0，不落 SQL |
