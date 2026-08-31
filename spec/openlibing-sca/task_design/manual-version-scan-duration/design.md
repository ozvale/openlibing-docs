# manual-version-scan-duration — 技术设计

## 1. 数据模型变更

新增列（Liquibase changeset `20260824_add_tbl_manual_version_scan_finish_time`，文件 `mysql/20260824/add-tbl-manual-version-scan-finish-time.xml`）：

```sql
ALTER TABLE tbl_manual_version_scan ADD COLUMN finish_time DATETIME NULL COMMENT '扫描结束时间';
```

- 列语义：**最近一次扫描的结束时间**，仅终态回调写入；扫描触发（SCANNING）时**不**清空（终态必达，且保留上次值可容错中间态丢失）。
- 老数据 `finish_time = NULL` → `duration = null`，符合预期（见 proposal「不做什么」）。
- `preConditions onFail="MARK_RAN"` + `columnExists` 防重，与既有 `20260820` 两个 changeset 风格一致。

## 2. 字段流转

| 时机 | scan_time | finish_time | update_time | 触发代码 |
|------|-----------|-------------|-------------|----------|
| 手动扫描触发 | now | 不动 | 不动（由 update_by 分支整体不传 updateTime） | `ManualVersionScanServiceImpl.startSingleScan` |
| 定时扫描触发 | now | 不动 | 不动 | `startSingleScheduledScan` |
| 扫描成功/失败回调 | 不动 | now | now | `IntegrationApiServiceImpl.updateManualVersionScanStatus` |
| addRepo / batchUpdateScheduled | 不动 | 不动 | now | 既有审计逻辑 |

关键点：`updateManualVersionScanStatus` 的所有调用方（`IntegrationApiListener` 5 处异常分支、`doScanV3` 3 处异常分支、成功路径 2 处）传入的都是终态（SCAN_SUCCESS=2 / SCAN_FAILED=3），在该方法内统一写 `finishTime = now` 即可，无需区分调用方。

## 3. 代码改动设计

### 3.1 ManualVersionScanStatusUpdatePo

全参构造函数由 7 参扩为 8 参，`finishTime` 插在 `scanTime` 之后（时间语义：开始 → 结束 → 记录更新）：

```java
ManualVersionScanStatusUpdatePo(
    Integer repoId, Integer branchId, Integer scanStatus,
    Date scanTime, Date finishTime, Date updateTime,
    String branchName, String updateBy)
```

调用点适配（全仓仅 3 处）：
- `startSingleScan` / `startSingleScheduledScan`：`finishTime = null`（扫描刚开始）
- `updateManualVersionScanStatus`：`finishTime = now`（与 updateTime 同一时刻）

### 3.2 Mapper XML

- `resultMap` / `all_column` / `insert` 补 `finish_time`
- `updateScanStatusByRepoIdAndBranchId` 增加动态段：

```xml
<if test="updatePo.finishTime != null">
    finish_time = #{updatePo.finishTime},
</if>
```

### 3.3 query 耗时计算（ManualVersionScanServiceImpl）

```java
vo.setFinishTime(item.getFinishTime());
if (item.getFinishTime() != null
    && item.getScanTime() != null
    && item.getFinishTime().after(item.getScanTime())) {
  vo.setDuration(
      (item.getFinishTime().getTime() - item.getScanTime().getTime()) / 1000 + "s");
}
```

### 3.4 实体 / VO

`TblManualVersionScan` / `ManualVersionScanVO` 加 `finishTime`，沿用 `scanTime` 的防御性拷贝 getter/setter + `@JsonFormat(yyyy-MM-dd HH:mm:ss, GMT+8)` 风格。`TblManualVersionScan` 既有 13 参构造全仓无调用，不扩参。

## 4. 兼容性与风险

| 风险 | 评估 |
|------|------|
| 前端 | VO 加字段向后兼容；`duration` 对历史行变为 null（原来是被污染的虚高值，属修正而非回归） |
| DB | 加可空列，无锁表风险（表量级小）；Liquibase 启动自动执行 |
| 接口 | 无签名变化；`ManualVersionScanStatusUpdatePo` 构造为仓内类型，不影响外部 |
| 老分支 | 未部署 `fff2704d` 的环境执行本 changeset 后，finish_time 恒为 NULL，duration 为 null，无副作用 |

## 5. 测试策略

- `IntegrationApiServiceImplTest`：`updateManualVersionScanStatus_success` 增加断言 `finishTime != null`；新增用例验证 ScaException 分支不影响行为。
- `ManualVersionScanServiceImplTest`：
  - `query_success` / `query_withDurationCalculation`：改用 `finishTime` 设值，断言 duration。
  - `query_withoutDuration_whenScanTimeAfterUpdateTime` 改名/改语义：`finishTime` 早于 `scanTime` 或缺失 → duration 为 null。
  - 新增：`finishTime` 存在而 `updateTime` 晚于 `finishTime`（模拟扫描后改配置）→ duration 不受影响。
- 验证命令：`python scripts/run-mvn.py clean test`（全量）。
