# auto-confirm-committer-gate — /open/review/auto-confirm 权限门禁与评论人身份反查（#146）

## 需求背景

安全 Issue：[openlibing/openlibing-sca#146](https://gitcode.com/openlibing/openlibing-sca/issues/146)
（安全 / 缺失授权，CWE-862，高危；来源 Argus 批次 `openlibingsca-20261103130601-010`，已验证且可实际利用）。

`POST /open/review/auto-confirm` 是特权写操作，修复前完全匿名可达：

- 类 javadoc 自述"机机接口，无需鉴权"，全库无 Filter/Interceptor/WebMvcConfigurer 鉴权实现；
- 入参 `AutoConfirmPo` 仅有 `prUrl` + `commentLogin`，无任何凭据字段；`commentLogin` 只写运行时日志；
- `patchReview` 的 `selectByIdAndUser` 校验的是服务端解密的机器人账号归属，与调用方无关，不构成授权；
- 任意可达调用方可按 `prUrl` 定位任意 PR 最近一次扫描，将未确认问题批量置为 `reviewStatus=40` 并刷新
  `un_confirmed_file_num`，使 PR 门禁计数归零放行。

修复前的二次缺陷：即使加上"`commentLogin` 必须是仓库 committer"的判断，`commentLogin` 仍来自请求体，
调用方可直接填入 committer 登录名冒充，门禁依旧可被绕过。

## 功能描述

**做什么**：

1. committer 权限门禁：按 `scanId → repo_id → project_id → product_id` 链路取齐参数，调用
   openlibing-framework `POST /select/get-committer`，校验评论人登录名在返回的 `gitcodeName` 集合中；
   非 committer、入参缺失、framework 返回异常或调用异常一律 403（fail-closed，不降级放行）。
   已知错配：gitee 平台反查出的是 gitee 登录名，与本轮仅比对的 `gitcodeName` 集合不同命名空间
   （见 design.md D6 与风险表）。
2. 门禁下沉到服务层：`ConfirmReviewServceImpl#checkCommitterPermission(repoId, commentLogin)`
   在 `robotAutoConfirm` 内执行，复用已查询的 `repo_id`，Controller 只保留入参校验，403 语义经
   `ScaException(403, ...)` 透传。
3. 评论人身份反查（修复 `commentLogin` 伪造）：请求体字段由 `commentLogin` 改为 `commentId`；服务端经
   平台评论 API（`/repos/{owner}/{repo}/issues/{prNumber}/comments/{commentId}`）取 `user.login` 作为
   真实评论人，再进入 committer 校验；评论反查失败、作者为空、`prUrl`/`commentId` 非法均 403。

**不做什么**：

- 未实现机机签名 / token + 时间戳防重放的白名单机制（Issue P0 第 1 条的另一种路线）；
  本轮以"评论人真实身份 + 仓库 committer 授权"作为等价门禁。
- 未实现同一 `prUrl` 的频控/幂等去重与批量条数上限（Issue P1，本轮未覆盖）。
- 未新增独立操作日志表；`@LogApi` 已由 API 访问审计批次（`a7e7bc1b`）从 Controller 移除，
  触发人身份仅在应用日志留痕。

## 验收标准

- [ ] 匿名/无凭据调用被拒绝（部分满足）：请求体缺失 `commentId` 直接 403（`commentId不能为空`）；
      `commentId` 无法反查到有效评论作者时 403，不产生审核数据变更（`PlatformCommentUtil.resolveCommentLogin`
      fail-closed，`OpenConfirmReviewControllerTest#testRobotAutoConfirmBlankCommentId`）。但门禁不校验
      调用方身份、无防重放：`commentId` 为平台可枚举整数，任何匿名可达方取得某条 committer 评论的
      `commentId` 即可重放触发（见 design.md 风险表）；issue #146 P0 的机机认证（签名/token + 时间戳
      防重放）诉求未达成
- [x] 非仓库 committer 的评论作者被拒绝：`checkCommitterPermission` 未命中 `gitcodeName` 集合抛
      `ScaException(403, "当前用户无权触发自动确认，仅仓库committer可操作", ...)`
      （`ConfirmReviewServceImplTest#testRobotAutoConfirm_NotCommitter_ThrowsForbidden`）；
      注：门禁仅比对 `gitcodeName`，gitee 场景命名空间错配为遗留项（见 design.md D6）
- [x] 权限校验服务异常时拒绝而非放行：framework 响应非法 / 调用抛异常 / 仓库项目信息缺失均 403
      （`testRobotAutoConfirm_FrameworkInvalidResponse_ThrowsForbidden`、
      `testRobotAutoConfirm_FrameworkError_ThrowsForbidden`、
      `testRobotAutoConfirm_RepoInfoMissing_ThrowsForbidden`）
- [x] 评论人身份不可由调用方伪造：入参不再接收 `commentLogin`，身份以平台评论 API 返回的
      `user.login` 为准（`AutoConfirmPo#commentId`；`PlatformCommentUtilTest` 覆盖 gitcode/gitee 反查与失败分支）。
      注：评论作者身份不可伪造 ≠ 调用方身份已认证，无凭据重放仍可借 committer 评论触发（见上一条）
- [ ] 同一 `prUrl` 重复触发被拦截或幂等去重；批量条数超限被拒绝（本轮未覆盖，无对应实现）
- [ ] 批复留痕含触发人身份（部分满足）：`robotAutoConfirm` 以 INFO 记录反查后的 `commentLogin`；
      审核流转日志仍记录服务端机器人操作人，未落"触发人"字段（本轮未覆盖）
- [x] 门禁改动不影响既有自动确认/审核链路：`ConfirmReviewServceImplTest` 全类 72 个用例保留，新增门禁桩
      （`mockCommitterGate` / `mockCommentAuthor`）

## 影响范围

- 业务仓：`openlibing-sca`（`analysis` 模块：Controller / Service / ServiceImpl / DTO；`common` 模块：Feign 客户端、新增 `PlatformCommentUtil`）
- 接口契约：`POST /open/review/auto-confirm` 请求体由 `commentLogin` 改为 `commentId`（**破坏性变更**，
  调用方 sca-action / PR 评论触发链路需同步改造；调用方仓库不在本仓，改造状态未验证）
- 外部依赖：openlibing-framework `POST /select/get-committer`；平台评论 API（gitee / gitcode v5）
- 配置：`PlatformCommentUtil` 读取既有配置键 `gitee.url`、`gitcode.url`、`gitee.api.url`、
  `gitcode.api.url`、`sca.majun.gitee.token`、`sca.gitcode.token`（无新增配置项）
- 数据库 schema：无变化
