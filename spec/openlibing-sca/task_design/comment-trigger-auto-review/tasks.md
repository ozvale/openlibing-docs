# 评论触发 PR 自动评审开放接口 — 实现任务

## 进度: 5/5 complete

- [x] 新增 `AutoConfirmPo` DTO（prUrl + commentLogin）与 `OpenConfirmReviewController`（`POST /open/review/auto-confirm` 机机接口）
- [x] `TblPersonScanDMMapper` 新增 `findLatestIdByPrUrl`（仅取 `scan_result='1'` 的最新扫描）
- [x] `ConfirmReviewServce`/`ConfirmReviewServceImpl` 新增 `robotAutoConfirm`：过滤可自动处理状态 → 强制提审（`scanConfirmParseV3`）→ 机器人批复（`autoPathReview`）；`autoPathReview` 返回值改为 `int` 以复用查询结果统计 remaining
- [x] N+1 修复：`TblConfirmReviewMapper` 新增 `selectPendingByRepoId`，`scanConfirmParseV3` 改为批量预查 + `matchPendingReviews` 按路径/hash 匹配；`ProcessScanIssueDto` 携带批量预查结果（防御性拷贝）
- [x] 创建 PR #355（`ms_review` → `release_20261029`），CI 流水线通过（标签 `ci-pipeline-passed`），补打 `ai-assisted` 标签

## 后续（可选）

- [ ] sca-action 侧切换调用新接口，并确认调用来源网络限制（机机接口无登录态鉴权）
- [ ] 评估为 `/open/review/auto-confirm` 增加内部 token 校验（参考 `internal-auth-request-interceptor` 方案）

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/355
- 分支: `ms_review` → `release_20261029`
