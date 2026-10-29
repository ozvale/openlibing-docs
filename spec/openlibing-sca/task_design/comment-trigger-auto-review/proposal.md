# 评论触发 PR 自动评审开放接口（OpenConfirmReviewController）

## 需求背景

sca-action 支持通过 PR 评论触发 bot 评审，但该链路此前从未真正生效：

- 门禁阻塞的 issue 属于"未提审"状态——既有自动链路（`autoSubmitConfirmV2` + `autoPathReview`）只对 license/copyright 匹配的 issue 自动提审，门禁拦截的恰恰是未被提审、无审核单的那部分。
- 因此按 `reviewStatus=00` + `reviewId` 过滤查不到数据，重新扫描也无法解除门禁阻塞，评论触发的 bot 评审始终无效。

需要为 sca-action 提供一个机机（服务间）开放接口：按 PR 定位最近一次扫描，将全部未确认问题强制提审并经机器人账号批量批复，使批复状态经既有传播机制同步，门禁得以通过。

## 功能描述

- 新增 `OpenConfirmReviewController`，暴露 `POST /open/review/auto-confirm` 机机接口（无需登录态鉴权，审核人由服务端固定为机器人账号，不信任外部身份）。
- 入参 `AutoConfirmPo`：`prUrl`（必填）+ `commentLogin`（触发评论的用户登录名，仅审计留痕）。
- 服务端按 `prUrl` 定位最近一次扫描成功（`scan_result='1'`）的扫描记录，避免选中进行中/失败的扫描。
- 合并原有三个机器接口为单一自动确认接口 `ConfirmReviewServce.robotAutoConfirm(scanId, commentLogin)`：
  - 仅处理未提审（空/00）与审核中（10）的文档；转审（20）、审核拒绝（30）的文档不重新提审，避免把人工结论刷成批复状态。
  - 强制提审：不做 license/copyright 匹配过滤，为无审核单的文档建单或重绑既有待审单（`scanConfirmParseV3`）。
  - 机器人批量批复（`autoPathReview`）：仅批复审核人为机器人的审核单；审核人非机器人的待审单不越权处理，计入返回的 `remaining`。
- 附带性能修复：`scanConfirmParseV3` 提审链路由循环内逐条 `selectByParam`（N+1 查询）改为批量预查仓库全部待审核(10)审核单后按文件路径分组匹配（`selectPendingByRepoId` + `matchPendingReviews`）。
- 附带小修复：`ScanossShiledMapper` 屏蔽查询兼容 `repository = CONCAT(#{repository}, '_gitcode')` 命名变体。

## 验收标准

- [x] `POST /open/review/auto-confirm`：`prUrl` 为空时返回失败提示；无对应扫描记录时返回失败提示。
- [x] 定位扫描时仅取 `scan_result='1'` 的记录，进行中/失败的扫描不会被选中。
- [x] 门禁阻塞（无审核单）的未确认问题能被强制提审并批复通过。
- [x] `repo_id` 未回填时中止流程并返回可重试错误（不跨仓库批复、不以 null repo_id 落库）。
- [x] 转审（20）/审核拒绝（30）的文档不被重新提审。
- [x] 审核人非机器人的待审单不被越权批复，计入 `remaining` 返回。
- [x] 单元测试通过（`OpenConfirmReviewControllerTest`、`ConfirmReviewServceImplTest`）。
- [x] CI 流水线通过（PR 标签 `ci-pipeline-passed`）。

## 影响范围

- 仅 `openlibing-sca` 仓：新增 controller/DTO 各 1 个，扩展 `ConfirmReviewServce`/`ConfirmReviewServceImpl`、`TblConfirmReviewMapper`、`TblPersonScanDMMapper`、`ProcessScanIssueDto`，补充 2 个单测。
- 新增对外机机接口 `POST /open/review/auto-confirm`（外部接口变化，调用方为 sca-action）。
- `autoPathReview` 返回值由 `void` 改为 `int`（门禁扫描返回批复后未确认数，其他扫描类型返回 -1），属内部接口变化。
- 无 DB schema 变化、无部署链路变化。

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/355（`ms_review` → `release_20261029`，+491/−36，12 files）
