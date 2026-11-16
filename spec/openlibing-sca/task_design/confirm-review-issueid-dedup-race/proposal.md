# #102 — ConfirmReview issueId 去重预检查 TOCTOU 竞态（scan_issue 唯一索引 E11000 导致更新丢失）

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/102
（【安全】【Argus】审核确认模块 issueId 去重预检查非原子：并发批复批次可触发 scan_issue 唯一索引冲突导致写入丢失，当前状态 closed）

来源：Argus 安全扫描报告 `argus-openlibingsca-20260928173548-018`，严重程度低危，漏洞类型「业务竞态/去重 TOCTOU」，CWE-362。

漏洞位置：`src/main/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImpl.java:669`（`isIssueIdWritable`）。

根因：`isIssueIdWritable` 用两层**非原子**手段判断 `(scanId, issueId)` 是否可写——批次方法内局部 `claimedIssueKeys`（不跨批次/线程共享）+ `mongoTemplate.exists(...)` 预检查；真正写入发生在稍后的 `executeUpdate` 的 `bulkOperations.updateMulti + execute()`。预检查与 bulk 写入之间没有条件更新、upsert 或扫描级锁，形成 TOCTOU 窗口：并发批次（机器人 `autoPathReview` 与人工批量确认重叠，或多人并发批复同一 scan）可同时读到 `exists=false`，后写方触发 MongoDB `scan_issue` 集合 `(scanId, issueId)` 唯一索引 E11000。

影响：`executeUpdate` 原 `catch (RuntimeException)` 仅记录日志，UNORDERED 批量下冲突文档的 `reviewStatus` / `committerType` / `issueId` 更新整体丢失，而 MySQL `tbl_confirm_review` 已提交为审核通过，导致：

1. Mongo 侧审结状态永久停留旧值，审核列表与扫描结果不一致；
2. 门禁待确认风险统计（按 `reviewStatus=10` 计数）虚高；
3. 需人工按日志 reviewIds 逐条补偿，长期破坏审计一致性。

## 功能描述

**做什么**：

1. `executeUpdate` 捕获 bulk 失败后，沿异常链解析 `MongoBulkWriteException.getWriteErrors()`，筛出 `code == 11000` 的操作下标（`extractDuplicateKeyOpIndexes`）；
2. 对冲突操作**只做降级重试**：新建一个 UNORDERED `BulkOperations`，把这些操作的更新定义去掉 `issueId` 字段后重写（`retryConflictUpdatesWithoutIssueId` + `stripIssueId`），使 `reviewStatus` / `committerType` / `reviewTime` 等其余字段仍落库，与 `isIssueIdWritable` 的「让位语义」保持一致（冲突方保留原 issueId）；
3. 非 E11000 失败（超时、网络、副本集故障等）保持原有 error 日志路径，输出 reviewIds 便于定位，不触发降级重试；
4. 新增常量 `MONGO_DUPLICATE_KEY_ERROR_CODE = 11000`、`ISSUE_ID_FIELD = "issueId"`；`isIssueIdWritable` 与 `executeUpdate` javadoc 补充 TOCTOU 窗口与唯一索引兜底说明。

**不做什么**：

- 不改动去重预检查本身：不引入 `findAndModify` / `$setOnInsert` upsert / 扫描级分布式锁，也不把 `claimedIssueKeys` 提升为跨批次共享结构；
- 不改变 MySQL 侧「已提交审核通过」的语义，不回滚 MySQL 审核结果；
- 不新增重试队列/补偿表（该能力由后续 `confirm-review-dual-write-consistency` 的 Outbox 补偿承接，见兄弟目录）；
- 不处理 `patchRevoke` / `reviewReferral` 的同类冲突（后续由共享写出口统一覆盖）。

## 验收标准

- [x] E11000 冲突时仅对冲突操作降级重试，重试载荷去掉 `issueId` 且保留 `reviewStatus` / `committerType`（`ConfirmReviewServceImplTest#executeUpdate_shouldRetryConflictUpdateWithoutIssueIdOnDuplicateKey`）
- [x] 未包装的原生 `MongoBulkWriteException` 直接抛出时同样触发降级重试（`#executeUpdate_shouldRetryWhenWrappedDuplicateKeyExceptionThrownDirectly`）
- [x] 非 E11000 失败不新建 bulk、不降级重试，审核日志仍正常插入（`#executeUpdate_shouldNotRetryWhenBulkFailsWithoutDuplicateKey`）
- [x] 冲突操作下标越界/非法时跳过并 `warn`，不影响其余冲突操作
- [x] 降级重试本身失败时输出含查询条件的 error 日志，不静默吞掉
- [ ] 真实 MongoDB 环境 E11000 并发复现/压测（本轮未覆盖，仅单测 mock 异常链）
- [ ] `mvn test` 全量与 checkstyle/pmd/spotbugs 结果（本轮为回溯补写文档，未执行，未验证）

> 后续演进：`confirm-review-dual-write-consistency`（#95）把 bulk 写出收敛为 `executeMongoUpdatesWithOutbox`，`Pair` 改为 `MongoUpdateOp`（`query()` / `update()`），并新增「冲突降级仍失败 → 落 Mongo 补偿表由定时任务重放」；降级重试方法 `retryConflictUpdatesWithoutIssueId` 仍保留（当前位于 `ConfirmReviewServceImpl.java:1574`）。

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `ConfirmReviewServceImpl`（`executeUpdate` / `isIssueIdWritable` 链路）及其单测
- 接口 / 契约：无变化（`POST /review/patch/review`、`autoPathReview` 入参与返回不变）
- 配置 / schema：无变化，无数据迁移
- 行为变化：并发冲突文档由「整条更新丢失 + error 日志」变为「去 issueId 重写，审结字段落库 + warn 日志」
