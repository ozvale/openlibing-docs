# Proposal: 修复版本级检查审核中数据出现负数

## 需求背景

`/codecheck/full/task/result/summary` 接口非常偶尔会出现返回的某条数据 `inReview`（审核中问题数）为负数，同时 `issue` 异常增加、`ignoreCount` 偏大。典型案例：原本 `issue=694, inReview=0, ignoreCount=0`，批量审核忽略后变成 `issue=794, inReview=-100, ignoreCount=1288`。重新执行版本级检查后数据恢复正常（因为全量重算绕过了增量更新的错误累积）。

## 根因

经代码追踪，确认有 4 个叠加 bug 共同导致：

### Bug 1（主因，确定性）：用请求数而非实际处理数更新 summary

`ProblemshieldDelegateImpl.updateDefect()`（审核通过）和 `shieldAudit()`（审核不通过）中，更新 summary 时使用 `auditModel.getDetailsId().size()`（请求数），而非 `getInReviewAndUpdateStatu()` 实际返回的 `defectVos.size()`（实际处理数）。

`getInReviewAndUpdateStatu()` 会过滤掉 `defectStatus==2`（已审核通过）和 `process==INPROCESS`（正在处理）的记录，实际返回数量可能小于请求数，导致 `inReview` 被多减。

### Bug 2（确定性）：审核通过时 issue 错误增加

`updateDefect()` 审核通过时执行 `issue += count`。审核通过的状态流转是 `inReview(3) → ignore(2)`，`issue` 不应该变化（提交屏蔽时已经 `issue -= count`）。

### Bug 3（概率性）：读-改-写无并发控制 + 伪锁

1. 所有对 `inReview` 的增减操作都是读-改-写模式：先 `getRepoSummary` 读当前值，内存计算，再 `updateSummaryData` 写回。无原子性保证，并发时丢失更新。
2. `ProblemShieldOperation.getInReviewAndUpdateStatu()` 中 `ReentrantLock lock = new ReentrantLock()` 是局部变量，每次调用都是新实例，无法跨线程互斥；`tryLock()` 返回值也未检查。`getShieldDetailByUserId()` 同样存在无效局部锁。

### Bug 4（中）：shieldAllAudit 批量审核通过时未更新 inReview

`shieldAllAudit()` 审核通过分支只调用 `updateDefectsDetail` + `updateDefectsSummary`，后者只更新 `ignoreCount`/`issueCount`（华为云字段），不更新 int 类型的 `inReview`/`ignore` 字段。

## 修复方案

1. **用实际处理数替代请求数**：`shieldAudit`/`updateDefect`/`commShieldRevoke`/`shieldSubmit` 中用 `defectVos.size()` 替代请求参数的 `size()`
2. **审核通过时不增加 issue**：`updateDefect` 删除 `issue += count` 逻辑
3. **用 MongoDB `$inc` 原子操作替代读-改-写**：在 `FullSummaryOperation` 新增 `incSummaryData(id, issueDelta, ignoreDelta, inReviewDelta)` 方法，所有 summary 增减改用此方法
4. **修复无效局部锁**：`ProblemShieldOperation.getInReviewAndUpdateStatu()` 改用 `findAndModify` 保证查询+更新原子性；`getShieldDetailByUserId()` 删除无效锁
5. **shieldAllAudit 补充 inReview 更新**：审核通过时累计每页实际处理数，循环结束后用 `$inc` 更新 `inReview`（减）和 `ignore`（增）

## 影响范围

- 仓库：`openlibing-codecheck`
- 模块：屏蔽审核（`ProblemshieldDelegateImpl`）、屏蔽操作（`ProblemShieldOperation`）、全量 summary 操作（`FullSummaryOperation`）
- 接口变化：无
- 数据模型变化：无（只改写入方式，不改 schema）

## 验收标准

1. 复现测试通过：审核通过后 `issue` 不再错误增加，`inReview` 不再变负
2. 并发场景测试通过：多线程并发审核时 `inReview` 不丢失更新
3. 现有相关单元测试全部通过
4. 项目构建成功

## 关联

- 业务 Issue: openlibing/openlibing-codecheck#128
