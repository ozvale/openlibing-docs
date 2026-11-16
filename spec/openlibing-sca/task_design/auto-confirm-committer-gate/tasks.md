# auto-confirm-committer-gate — 实现任务

## 进度: 4/4 complete

- [x] Task 1: Controller 层新增 committer 权限门禁（`33a7188f`）
  - `OpenConfirmReviewController#checkCommitterPermission`：scanId→repo_id→project_id→product_id 取参，
    调 `OpenlibingFrameworkClient#getCommitter`，校验 `gitcodeName` 集合；异常/非 committer 均 403
  - 新增 `CommitterUserInfoDto`、`QueryCommitterInputDto`，扩展 `OpenlibingFrameworkClient`
  - 新增 `OpenConfirmReviewControllerTest` 门禁用例
- [x] Task 2: 门禁下沉服务层，消除重复 repo_id 查询（`d5b3feea`）
  - `ConfirmReviewServceImpl#checkCommitterPermission` 承接取参与校验，`robotAutoConfirm` 内调用
  - Controller 瘦身，改为 `ScaException(403, ...)` 透传
  - 测试从 Controller 迁移到 `ConfirmReviewServceImplTest`（`testRobotAutoConfirm_NotCommitter_ThrowsForbidden` 等）
- [x] Task 3: 修复 `commentLogin` 伪造，身份改由平台评论 API 反查（`ce9b188e`）
  - `AutoConfirmPo` 字段 `commentLogin` → `commentId`；Service 接口改为
    `robotAutoConfirm(scanId, prUrl, commentId)`
  - 新增 `PlatformCommentUtil#resolveCommentLogin`：按 `prUrl` 判定 gitee/gitcode，取平台 token，
    调 `/repos/{owner}/{repo}/issues/{pr}/comments/{commentId}` 解析 `user.login`，失败 fail-closed 403
  - 新增 `PlatformCommentUtilTest`（6 用例）；更新 Controller/Service 测试
- [x] Task 4: 交付与静态核验
  - 静态核验：`AutoConfirmPo` 已无 `commentLogin` 字段；`robotAutoConfirm` 先 `resolveCommentLogin`
    再 `checkCommitterPermission`；403 分支覆盖非 committer、信息缺失、framework 异常、评论反查失败

## 交付记录

| commit     | 日期       | 摘要                                                                     | 关联                                    |
| ---------- | ---------- | ------------------------------------------------------------------------ | --------------------------------------- |
| `33a7188f` | 2026-11-05 | feat(analysis): gate auto-confirm with committer permission check        | 提交信息写 `Refs #152`（非 #146，见下） |
| `d5b3feea` | 2026-11-05 | refactor(analysis): move committer gate from controller to service layer | 提交信息写 `Refs #152`                  |
| `ce9b188e` | 2026-11-12 | fix(analysis): resolve PR comment identity via platform comment API      | 无 Refs                                 |

- 分支：`ms_scan`（三个 commit 均为 HEAD 祖先）
- 关联说明：三个 commit 的 message 未引用 `#146`，前两个引用 `#152`；issue 正文与验收项对应
  `#146`，映射关系由批次清单指定，issue 与 commit 的显式关联缺失。
- 验证方式：本轮为回溯文档，仅做静态核验与 diff 复核，**未执行 `mvn test`**（运行测试会写入
  `target/`，超出只读约束）。
- 测试覆盖（代码中已存在）：
  - `OpenConfirmReviewControllerTest`：7 个用例（含 `testRobotAutoConfirmBlankCommentId`、
    `testRobotAutoConfirmForbiddenByService`）
  - `ConfirmReviewServceImplTest`：72 个用例，新增门禁桩 `mockCommitterGate` / `mockCommentAuthor`
    与 `testRobotAutoConfirm_NotCommitter_ThrowsForbidden`、
    `testRobotAutoConfirm_FrameworkInvalidResponse_ThrowsForbidden`、
    `testRobotAutoConfirm_FrameworkError_ThrowsForbidden`、
    `testRobotAutoConfirm_RepoInfoMissing_ThrowsForbidden`
  - `PlatformCommentUtilTest`：6 个用例（gitcode/gitee 成功、仓库缺失、空响应、非法 PR 编号、API 异常）
- 未覆盖项：`prUrl` 频控/幂等去重、批量条数上限、触发人身份落库（Issue P1），未验证自动确认
  调用方是否已适配 `commentId` 新契约。
