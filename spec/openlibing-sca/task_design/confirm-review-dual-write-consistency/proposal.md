# ConfirmReview 双写一致性收敛（#95 第二轮）

## 需求背景

Issue [#95](https://gitcode.com/openlibing/openlibing-sca/issues/95)（Argus 中危 CWE-703）：ConfirmReview 审核结果 MySQL/Mongo 双写不一致。第一轮已落地批复方向 outbox 补偿（commit `5a2f3670`：同事务原子、幂等重放、E11000 冲突降级、FAILED 转人工），批 7 评审确认该方向设计正确。

本轮处理批 7 评审遗留问题（评审原文见 Issue #95 讨论区 / 用户反馈）：

- **P1-1 replay 陈旧回冲**：补偿载荷固化，重放前不校验 MySQL 当前状态——补偿等待期内发生撤销/转审，replay 会把旧值冲回 Mongo 且 DONE 无痕。
- **P1-2 转审/撤销未补偿**：`reviewReferral`（无事务）、`patchRevoke`（Mongo 先行 MySQL 后写，反向漂移）、`propagateRevokeToInheritScans`（吞异常）。
- **P2-1 混合错误 bulk 丢更新**：非 11000 失败 op 静默丢弃。
- **P2-2 autoPathReview 多批回滚漂移**：多批同事务回滚时 Mongo 已生效的写不回滚。

## 功能描述

**做**：

1. 补偿载荷每个 op 打来源审核单标记；replay 时按 MySQL 当前 `reviewStatus`/`reviewUserId` 校验载荷新鲜度，陈旧 op 跳过并留痕。
2. `patchRevoke` / `reviewReferral` / 撤销继承传播纳入同一 outbox 机制；写序统一为 MySQL 先行 → 日志 → Mongo bulk 最后。
3. Mongo bulk 混合错误（11000 + 非 11000）分区处理：非冲突失败 op 单独落补偿，不再静默丢。
4. `autoPathReview` 每 100 条批次独立事务（REQUIRES_NEW）；`robotAutoConfirm` 同步调整；`executeUpdate` 日志提前到 Mongo 之前。

**不做**：

- 不新增数据库 schema（补偿表 `tbl_confirm_review_mongo_compensation` 已于 20261103 changeset 落地，发布前提已满足）。
- 不改动批复方向（patchReview 主链路）既有 outbox 语义与 `appendInheritScanPropagation` 的 best-effort 读容错。
- 不处理存量漂移数据修复（人工/对账脚本范畴）。

## 验收标准

- [ ] 补偿等待期内撤销：replay 不回冲旧值，Mongo 保持撤销状态，补偿记录 DONE 且日志留痕（批 7 用例集 3.2）。
- [ ] 转审载荷陈旧（审核人已变更）：replay 跳过对应 op。
- [ ] `patchRevoke` 写序为 MySQL 先行；Mongo bulk 失败时落补偿记录（含撤销 + 继承传播操作），事务不回滚已写 MySQL。
- [ ] `reviewReferral` 具备事务；Mongo 失败落补偿。
- [ ] 撤销继承传播的 Mongo 写失败走 outbox；范围解析读失败时撤销整体回滚（fail-closed，两侧一致）。
- [ ] 混合 bulk 错误：非 11000 失败 op 落补偿（仅失败子集）；11000 走降级重试，降级失败并入补偿。
- [ ] `autoPathReview` 批次 N 失败仅回滚批次 N，前序批次一致性提交。
- [ ] 既有 61 个单测全部通过 + 新增用例通过；`mvn compile` 通过。

## 影响范围

- `openlibing-sca`：`ConfirmReviewServceImpl.java`（核心）、`ConfirmReviewServceImplTest.java`
- 无接口契约变化（`ConfirmReviewServce` 接口签名不变）、无 schema 变化、无部署链路变化
