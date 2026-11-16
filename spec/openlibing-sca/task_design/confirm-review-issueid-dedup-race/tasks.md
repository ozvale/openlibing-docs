# #102 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: `ConfirmReviewServceImpl` 新增 `MONGO_DUPLICATE_KEY_ERROR_CODE=11000` / `ISSUE_ID_FIELD="issueId"`，补充 `isIssueIdWritable`、`executeUpdate` 的 TOCTOU 与兜底语义 javadoc（`c9e685bf`）
- [x] Task 2: `executeUpdate` 失败分支解析 `MongoBulkWriteException.writeErrors`，冲突 op 走 `retryConflictUpdatesWithoutIssueId`（`stripIssueId` + 新建 UNORDERED bulk），非冲突失败保持原 error 日志（`c9e685bf`）
- [x] Task 3: 单测补充 E11000 降级重试、原生异常直抛、非冲突失败不重试，并交付 commit（`c9e685bf`）

## 交付记录

| commit     | 日期       | 标题                                                                                 | 关联       |
| ---------- | ---------- | ------------------------------------------------------------------------------------ | ---------- |
| `c9e685bf` | 2026-11-03 | fix(review): degrade issueId on Mongo unique-index conflict instead of losing update | Fixes #102 |

- 分支：`ms_scan`（`openlibing-sca`）
- 验证方式（代码内证据）：
  - `ConfirmReviewServceImplTest#executeUpdate_shouldRetryConflictUpdateWithoutIssueIdOnDuplicateKey`：仅冲突 op 进入重试，重试 `$set` 不含 `issueId`，`reviewStatus` 与 `committerType` 保留
  - `#executeUpdate_shouldRetryWhenWrappedDuplicateKeyExceptionThrownDirectly`：driver 原生 `MongoBulkWriteException` 直抛时同样重试
  - `#executeUpdate_shouldNotRetryWhenBulkFailsWithoutDuplicateKey`：连接类错误不新建 bulk，审核日志 `patchInsert` 仍被调用
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）
- 后续演进：`confirm-review-dual-write-consistency`（#95）将写出收敛到 `executeMongoUpdatesWithOutbox`，降级重试仍失败时改为落 Mongo 补偿表（Outbox）；对应新增用例 `executeUpdate_shouldSaveCompensationWhenDegradedRetryStillFails`、`replayMongoCompensations_shouldDegradeWithoutIssueIdOnDuplicateKey`
