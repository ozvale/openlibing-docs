# review-mongo-compensation — 技术设计

## 方案概述

Outbox 补偿模式：Mongo bulk 写失败时同步重试（3 次），穷尽后将本批 Mongo 更新载荷（扩展 JSON 快照）
与 reviewIds 落入 MySQL 补偿表（与审核状态同事务提交）；定时任务每分钟取 PENDING 行，按 mong_id 幂等重放
`updateFirst` 直至成功；重放前比对 MySQL 当前审核状态做 stale 保护。

## 数据流（修复后）

```
patchReview/autoPathReview (@Transactional)
  └─ updateIssueData ─ prepareReviewUpdate（构造 updateList + mongoUpdates，1:1 同序）
       └─ executeUpdate
            ├─ MySQL: 分页 patchUpdate（事务内，未提交）
            ├─ Mongo: executeMongoBulkWithRetry（最多 3 次，间隔 200ms）
            │     ├─ 成功 → 继续
            │     └─ 穷尽失败 → ReviewMongoCompensationService.persistCompensations
            │           （补偿行与 MySQL 审核状态同事务提交；若落表本身失败则整体回滚，两侧一致）
            └─ MySQL: patchInsert 审核日志
ReviewMongoCompensationSchedule（每分钟，分布式锁）
  ├─ sweep: PENDING 且 retry_count ≥ 10 → FAILED + ERROR 日志
  └─ replay: 取 PENDING 且 next_retry_time ≤ now 的行（限 200）
        ├─ review 不存在 / review_status ≠ payload.reviewStatus → markDone + WARN（stale，MySQL 为准）
        └─ mongoTemplate.updateFirst(_id=mongId, Update.fromDocument(payload))
              ├─ 成功 → markDone
              └─ 失败 → incrementRetry（指数退避 2^n 分钟，封顶 30 分钟）
```

## 架构决策

| 决策                                                    | 理由                                                                                                                                                      |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 补偿表（Outbox）而非 MQ 异步                            | 与审核状态同事务提交，天然"不丢批次"；不引入 MQ 依赖与消费语义复杂度                                                                                      |
| 保留"先 MySQL 后 Mongo"顺序 + 补偿，而非顺序反转        | UNORDERED bulk 部分成功时顺序反转会产生反向不一致；补偿重放按 _id set 幂等可安全收敛                                                                      |
| 载荷存扩展 JSON 快照（`updateObject.toJson()` RELAXED） | 忠实还原审核时刻的派生值（issueId/component/version/confirmType 等），重放不经二次推导；`Document.parse` 往返保类型（Date→`$date`、Integer→`$numberInt`） |
| 重放逐行 `updateFirst` 而非整批 bulk                    | 单行失败不影响其他行，逐行 markDone，部分进度可保留                                                                                                       |
| stale guard（重放前比对 review_status）                 | 防止补偿期间发生撤回/转审等后续状态变化时，旧载荷覆盖新状态                                                                                               |
| 同步重试 3 次作为第一道防线                             | 吸收秒级瞬时抖动，减少补偿表写入频率                                                                                                                      |
| 复用 `DistributedLockService` 分布式锁                  | 多实例部署下防重复执行，沿用 `PendingCountSchedule` 既有模式                                                                                              |

## 表设计 `tbl_review_mongo_compensation`

| 列                        | 类型                   | 说明                                              |
| ------------------------- | ---------------------- | ------------------------------------------------- |
| id                        | VARCHAR(64) PK         | UUID                                              |
| review_id                 | VARCHAR(64) NOT NULL   | tbl_confirm_review.id                             |
| mong_id                   | VARCHAR(64) NOT NULL   | scan_issue._id                                    |
| payload                   | TEXT NOT NULL          | Mongo update 文档扩展 JSON（如 `{"$set":{...}}`） |
| status                    | VARCHAR(16) NOT NULL   | PENDING / DONE / FAILED                           |
| retry_count               | INT NOT NULL DEFAULT 0 | 重放失败次数，≥10 转 FAILED                       |
| next_retry_time           | DATETIME NOT NULL      | 退避控制，任务只取 `≤ NOW()` 的行                 |
| last_error                | TEXT                   | 最近一次重放失败原因                              |
| create_time / update_time | DATETIME               |                                                   |

索引：`idx_rmc_status_next_retry(status, next_retry_time)`、`idx_rmc_review_id(review_id)`。

Liquibase：`db/changelog/mysql/20261012/create-tbl-review-mongo-compensation.xml`，
`preConditions` 表不存在才建，含 rollback，include 进 `db.changelog.xml`。

## 涉及文件

| 文件                                                                   | 操作 | 说明                                                                                         |
| ---------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------- |
| `db/changelog/mysql/20261012/create-tbl-review-mongo-compensation.xml` | 新增 | 建表迁移                                                                                     |
| `db/changelog/db.changelog.xml`                                        | 修改 | include 新迁移                                                                               |
| `analysis/entity/TblReviewMongoCompensation.java`                      | 新增 | 补偿表实体（@Data）                                                                          |
| `analysis/dao/TblReviewMongoCompensationMapper.java`                   | 新增 | patchInsert / selectPendingBatch / markDone / incrementRetry / markFailedWhereRetryExhausted |
| `resources/mapper/analysis/TblReviewMongoCompensationMapper.xml`       | 新增 | 对应 XML                                                                                     |
| `analysis/service/ReviewMongoCompensationService.java`                 | 新增 | persistCompensations / replayPendingBatch 接口                                               |
| `analysis/service/impl/ReviewMongoCompensationServiceImpl.java`        | 新增 | 载荷序列化/反序列化、stale guard、退避计算                                                   |
| `analysis/service/impl/ConfirmReviewServceImpl.java`                   | 修改 | updateIssueData 去掉外部 bulkOperations；executeUpdate 同步重试 + 失败落补偿；注入新 service |
| `common/schedule/ReviewMongoCompensationSchedule.java`                 | 新增 | @Scheduled cron 可配置（默认每分钟）+ 分布式锁薄壳                                           |
| `test/.../ConfirmReviewServceImplTest.java`                            | 修改 | 新增失败补偿/重试成功/分页边界用例                                                           |
| `test/.../ReviewMongoCompensationServiceImplTest.java`                 | 新增 | 重放成功/失败退避/stale/幂等/载荷 round-trip 用例                                            |
| `test/.../ReviewMongoCompensationScheduleTest.java`                    | 新增 | 锁与委托薄壳用例                                                                             |

## 安全设计约束（映射生成前约束检查）

- 补偿表仅内部写入，无外部输入面；payload 为服务端派生数据，不回注用户输入。
- 新增 Mapper 全部参数化 SQL，无拼接注入风险。
- 不涉及鉴权/权限/凭证变化；不新增敏感信息落盘。
- 任务日志输出 reviewIds/mongId 与错误摘要，不含敏感用户数据。

## 风险 & 缓解

| 风险                                         | 缓解                                                                  |
| -------------------------------------------- | --------------------------------------------------------------------- |
| 补偿行重放时 review 已被撤回/转审            | stale guard：比对 review_status 不一致则跳过并 markDone               |
| markDone 在 Mongo 写成功后失败，行被重复重放 | 重放按 _id set 幂等，重复执行结果一致                                 |
| 补偿落表自身失败（DB 故障）                  | 异常向上传播 → 整个事务回滚 → 两侧保持旧状态一致，用户重试即补偿      |
| 定时任务多实例并发                           | DistributedLockService 锁 + env 后缀                                  |
| 长期 Mongo 故障导致 PENDING 堆积             | retry_count ≥ 10 转 FAILED + ERROR 日志，人工复位即可续跑；批次不丢失 |
| payload 类型漂移（Date/Integer）             | 扩展 JSON RELAXED round-trip；单测覆盖 round-trip 类型断言            |

## 跨仓影响

无。spec 文档归档 openlibing-docs 仓（本目录），业务改动仅 `openlibing-sca`。

## 明确不在范围

- `patchRevoke` / `reviewReferral` 的同类双写补偿（报告 P2，后续架构层治理）
- P1 全量历史对账任务与告警平台接入
