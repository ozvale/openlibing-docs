# static-alarm-snapshot-count 技术方案

## 方案概述

扫描结束时对 issue 表按仓库维度（repo_type + owner + repo + branch，与 `resolveDisappearedIssues` 维度一致）执行一次聚合，得到 status × severity 组合计数，客户端按状态维度、级别维度分别求和推导出 7 个快照值，随 scanRun 更新一并写入 MongoDB。

## 核心设计

### 聚合管道（StaticAlarmOperation.aggregateSnapshot）

```
$match:  repo_type + owner + repo + branch 等值匹配（复用 resolveDisappearedIssues 维度）
$project: status, severity（排除 _id）
$group:  { _id: { status, severity }, count: { $sum: 1 } }
```

- status / severity 全部命中 `idx_issue_branch_status` 索引，走覆盖索引扫描不产生 FETCH，`$group` 内存占用与 issue 数量无关。
- 聚合结果为 status × severity 组合计数（最多 3 × 4 = 12 个文档），客户端按两个维度分别累加：
  - 状态维度：OPEN → issue、RESOLVED → solve、IGNORED → ignore
  - 级别维度（全量计数，不限定 status）：CRITICAL → critical、HIGH → major、MEDIUM → minor、LOW → suggestion

### 0 计数与失败语义

| 场景                   | 快照字段值                                              | snapshot_computed |
| ---------------------- | ------------------------------------------------------- | ----------------- |
| 聚合成功，计数 > 0     | 实际计数                                                | true              |
| 聚合成功，某维度未命中 | 0（$group 不为 0 计数组合产出文档，未命中字段统一填 0） | true              |
| 聚合异常（catch）      | null（failed() 标记实例）                               | false             |

失败路径不抛出、不阻塞 scanRun 入库，仅 warn 日志；下游入湖消费方按 `snapshot_computed=false` 区分处理。

### 写入路径（SarifParseServiceImpl）

`updateScanRunSuccess` / `updateScanRunPartialSuccess` 两个私有方法先调用 `aggregateSnapshot`，再把 8 个字段（7 快照 + 标记）加入原 Update 一并提交。

### 字段变更（StaticAlarmScanRunEntity）

| 变更     | 字段                                                                                              | 说明                            |
| -------- | ------------------------------------------------------------------------------------------------- | ------------------------------- |
| 删除     | new_issue_count / resolved_issue_count                                                            | 增量死字段，从未有效写入        |
| 语义调整 | issue_count                                                                                       | 明确为 SARIF 解析总数（非存量） |
| 新增     | issue_snapshot / solve_snapshot / ignore_snapshot                                                 | 状态维度存量                    |
| 新增     | critical_count_snapshot / major_count_snapshot / minor_count_snapshot / suggestion_count_snapshot | 级别维度存量                    |
| 新增     | snapshot_computed                                                                                 | 快照计算成功标记                |

新增 model `StaticAlarmSnapshotCount` 承载聚合结果（非数据库实体），含 `failed()` 静态工厂。

## 影响范围

| 文件                          | 改动                                            |
| ----------------------------- | ----------------------------------------------- |
| StaticAlarmScanRunEntity.java | 字段增删（+32 行）                              |
| StaticAlarmSnapshotCount.java | 新增聚合结果 model（+44 行）                    |
| StaticAlarmOperation.java     | 新增 aggregateSnapshot + addNullSafe（+105 行） |
| SarifParseServiceImpl.java    | 成功/部分成功两路径写入快照（+37 行）           |

- 数据模型：MongoDB 集合字段变更，无迁移（字段缺省即 null，下游按标记兼容）。
- 接口：无 HTTP 接口变更。
- 兼容性：删除的两个死字段确认无读取方；旧 scanRun 记录缺新字段，读取侧按 null 容忍。
