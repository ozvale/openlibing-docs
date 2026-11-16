# #102 — 技术设计

## 方案概述

保留「exists 预检查 + 内存 claim」的原有去重逻辑，把唯一索引作为最终一致性兜底：`bulkOperations.execute()` 抛异常时解析 `MongoBulkWriteException.writeErrors`，对 `code=11000` 的操作从更新定义中剔除 `issueId` 后单独重试，其余字段照常写入；非 11000 失败维持原 error 日志路径。

## 数据流（修复后）

```
patchReview / autoPathReview (@Transactional)
  └─ prepareReviewUpdate（构造 updateList + mongoUpdates，1:1 同序）
       └─ executeUpdate
            ├─ MySQL: 分页 patchUpdate（PAGE_SIZE=1000）
            ├─ Mongo: bulkOperations.updateMulti(mongoUpdates).execute()
            │     ├─ 成功 → 继续
            │     └─ RuntimeException
            │           ├─ extractDuplicateKeyOpIndexes(异常链)
            │           │     ├─ 空 → LOGGER.error(reviewIds, error)（原路径）
            │           │     └─ 非空 → retryConflictUpdatesWithoutIssueId
            │           │            ├─ stripIssueId(update) → BasicUpdate
            │           │            └─ 新建 UNORDERED bulk 仅写冲突 op
            │           │                  ├─ 成功 → warn（issueId dropped, N docs）
            │           │                  └─ 失败 → error（含 queries，人工补偿）
            └─ MySQL: patchInsert 审核日志
```

## 架构决策

| 决策                                                                   | 理由                                                                                                                                               |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 仅对 E11000 降级，其他失败保持原 error 路径                         | 冲突有确定性修复手段（去 issueId）；超时/网络类失败不可安全重试，避免掩盖故障、制造重复写                                                          |
| D2 冲突文档「去 issueId 重写」而非放弃该文档                           | 若放弃，MySQL 已审核通过而 Mongo 停留待审，门禁待确认数（`reviewStatus=10`）与审核列表永久不一致                                                   |
| D3 保留冲突方原 `issueId`（让位语义）                                  | 与 `isIssueIdWritable` 同批内 claim 的语义一致：同一 `(scanId, issueId)` 只允许一条文档绑定，其余保持原值                                          |
| D4 只重试失败 op，不复用原 `BulkOperations`                            | 原 bulk 已被 `execute()` 消费；UNORDERED 模式下未冲突文档已落库，整批重放会重复执行                                                                |
| D5 从异常链而非顶层异常类型判断                                        | Spring 会把 `MongoBulkWriteException` 翻译成 `DuplicateKeyException`，原始异常挂在 cause 上；`writeErrors.index` 与 `updateMulti` 入参下标一一对应 |
| D6 `stripIssueId` 仅过滤 `$set` 等 Document 型字段，其他操作符原样保留 | 保持其余更新语义不变，避免误删操作符；返回 `BasicUpdate` 以承载构造出的 BSON 文档                                                                  |

## 涉及文件

| 文件                                                                                      | 操作 | 说明                                                                                                                                                                                                     |
| ----------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImpl.java`     | 修改 | 新增 E11000 常量与 `issueId` 常量；`executeUpdate` 失败分支解析冲突 op 并降级重试；新增 `retryConflictUpdatesWithoutIssueId` / `extractDuplicateKeyOpIndexes` / `stripIssueId`；补充 TOCTOU 相关 javadoc |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImplTest.java` | 修改 | 新增 E11000 冲突降级、原生异常直抛、非冲突失败不重试 3 个用例                                                                                                                                            |

## 风险 & 缓解

| 风险                                                   | 缓解                                                                                      |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| 降级重试丢失组件绑定（`issueId` 未写）                 | 只发生在冲突文档上，且该文档按让位语义本就不应抢占 issueId；其余文档不受影响              |
| 降级重试仍失败，审结状态依旧丢失                       | 输出包含查询条件的 error 日志便于定位；后续 #95 将冲突失败并入 Mongo 补偿表由定时任务重放 |
| 异常链解析不到 `MongoBulkWriteException`（被包装多层） | 循环遍历 `getCause()` 直到找到 bulk 异常；找不到则按原路径记录日志，不误判                |
| `writeErrors.index` 与 `mongoUpdates` 下标错位         | 降级方法先做边界检查，越界跳过并 `warn`；UNORDERED + 同序 `updateMulti` 保证下标对应      |
| 误将非唯一索引错误当作 11000                           | 仅比较 `writeError.getCode() == 11000`                                                    |

## 跨仓影响

无。仅 `openlibing-sca` 分析模块内部改动，无外部接口/契约变化；spec 文档归档 openlibing-docs 仓（本目录）。
