# Tasks: 修复版本级检查审核中数据出现负数

## 进度: 10/10 complete

### Phase 3 实现任务

- [x] Task 1: 在 `FullSummaryOperation` 新增 `incSummaryData(String id, int issueDelta, int ignoreDelta, int inReviewDelta)` 方法，用 MongoDB `$inc` 原子更新 issue/ignore/inReview 三个字段
- [x] Task 2: 修复 `ProblemShieldOperation.getInReviewAndUpdateStatu()` —— 删除无效局部 `ReentrantLock`，改用 `findAndModify` 保证查询+更新 process 字段的原子性
- [x] Task 3: 修复 `ProblemShieldOperation.getShieldDetailByUserId()` —— 删除无效局部 `ReentrantLock`
- [x] Task 4: 修复 `ProblemshieldDelegateImpl.shieldAudit()` 审核不通过分支 —— count 用 `defectVos.size()`，改用 `incSummaryData(summaryId, +count, 0, -count)`
- [x] Task 5: 修复 `ProblemshieldDelegateImpl.updateDefect()` 审核通过分支 —— count 用 `defectVos.size()`，删除 `issue += count`，改用 `incSummaryData(summaryId, 0, +count, -count)`
- [x] Task 6: 修复 `ProblemshieldDelegateImpl.commShieldRevoke()` —— count 用 `defectVos.size()`，审核通过后撤销改用 `incSummaryData(summaryId, +count, -count, 0)`，审核前撤销改用 `incSummaryData(summaryId, +count, 0, -count)`
- [x] Task 7: 修复 `ProblemshieldDelegateImpl.shieldSubmit()` —— count 用 `unResolvedDefects.size()`，改用 `incSummaryData(summaryId, -count, 0, +count)`
- [x] Task 8: 修复 `ProblemshieldDelegateImpl.shieldAllAudit()` 审核通过分支 —— 累计每页 defectVos.size()，循环结束后用 `incSummaryData` 更新 inReview（减）。ignore/issue 已由 updateDefectsSummary 基于全表 count 重算覆盖，不再重复 $inc。

### 测试任务

- [x] Task 9: 编写复现测试 `ProblemshieldDelegateInReviewNegativeTest`，覆盖 Bug1/2/3 三个场景
- [x] Task 10: 运行相关单元测试 + 构建验证
  - 新增 3 个复现测试全部通过
  - 原有 ProblemshieldDelegateImplTest 30 个全部通过（同步修正 4 个 verify/stubbing 从 updateSummaryData 到 incSummaryData）
  - ProblemShieldOperationTest 4 个全部通过
  - 编译通过
