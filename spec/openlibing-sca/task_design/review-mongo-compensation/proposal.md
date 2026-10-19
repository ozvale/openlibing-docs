# review-mongo-compensation — ConfirmReview 审核结果 MySQL/Mongo 双写补偿机制

## 需求背景

安全审计报告 M-0024（`argus-openlibingsca-20260928173548-029.md`，中危，CWE-703）指出：
`ConfirmReviewServceImpl.executeUpdate`（L706-734）将 MySQL 与 Mongo 双写放在非原子顺序执行中——
先分页 `patchUpdate` 提交 MySQL 审核状态，随后 `bulkOperations.updateMulti + execute()` 更新 Mongo
`scan_issue`。Mongo 批量写失败（超时、网络抖动、E11000、副本集故障）时 `catch(RuntimeException)` 仅记日志，
无重试、无补偿、无对账，导致：

1. MySQL 已置"审核通过(40)/拒绝(30)"而 Mongo `reviewStatus` 永久停留旧值（10），两侧 UI 矛盾；
2. 门禁待确认风险计数（`reviewStatus in "10"`）虚高；
3. 下次同文件扫描 `createNewReview` 重复建单，审计轨迹失真。

## 功能描述

**做什么**：为 Mongo 批量写失败建立自动补偿机制（方案 A：Outbox 补偿表 + 定时重放）：

1. `executeUpdate` 同步重试 Mongo bulk 写入（吸收瞬时抖动）；
2. 重试穷尽仍失败时，将本批 reviewIds + Mongo 更新载荷落补偿表 `tbl_review_mongo_compensation`
   （与 MySQL 审核状态**同事务**提交，失败批次不丢 reviewIds）；
3. 新增定时任务按 mong_id 幂等重放补偿行，直至 `scan_issue` 与 MySQL 对齐；
4. 重放前比对 MySQL 当前审核状态，防止过期补偿覆盖更新状态（stale guard）。

**不做什么**：

- 不实现 P1 全量历史对账任务（扫描全量 40/30 与 Mongo 差异）与监控告警平台接入（后续单独需求）；
- 不重构 `patchRevoke` / `reviewReferral` 等其他 MySQL+Mongo 联动路径（报告 P2 架构层治理项）；
- 不改变"审核成功"语义（补偿落库后接口仍返回成功，由任务保证最终一致）。

## 验收标准

- [ ] 静态核验：`executeUpdate` 区域可检索到重试/补偿调用（报告 P0 验收第 1 条）
- [ ] 单测：mock `bulkOperations.execute()` 恒抛 RuntimeException 时，补偿行被写入且含 reviewIds/mongId/payload，
      审核日志 insert 不受影响（报告 P0 验收第 2 条，对应新增用例 `executeUpdate_MongoFailureTriggersCompensation`）
- [ ] 单测：Mongo 第 N 次重试成功时不落补偿行；成功路径零补偿行为
- [ ] 单测：补偿重放按 _id set 幂等，同 payload 重放两次不产生脏写（对应 `compensationRetryIdempotent`）
- [ ] 单测：stale guard——review 状态已变化时跳过 Mongo 重放并标记 DONE
- [ ] 单测：分页边界——updateList 超过 PAGE_SIZE=1000 时逐页 patchUpdate，补偿覆盖全部页
- [ ] 现有测试全量通过（mvn test），无回归
- [ ] checkstyle / pmd / spotbugs 无新增告警

## 影响范围

- 业务仓 `openlibing-sca`：analysis 模块（ConfirmReview 双写路径）+ common 模块（新增定时任务）
- 新增 MySQL 表 `tbl_review_mongo_compensation`（Liquibase 迁移）
- 无外部接口/契约变化；无跨仓影响
