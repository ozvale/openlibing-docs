# auto-confirm-committer-gate — 技术设计

## 方案概述

两层门禁替代"匿名机机接口"：

1. **身份层**：请求只携带 `prUrl` + `commentId`；服务端用 `commentId` 调平台评论 API 反查评论作者
   `user.login`，杜绝请求体伪造 `commentLogin`。
2. **授权层**：以反查出的登录名调用 openlibing-framework `/select/get-committer`，命中仓库 committer
   的 `gitcodeName` 集合才放行。两层任一步失败均 403，不降级。

门禁实现放在服务层 `ConfirmReviewServceImpl#checkCommitterPermission`，Controller 只做入参校验与
`ScaException` 透传，便于单测与复用。

## 数据流（修复后）

```
POST /open/review/auto-confirm { prUrl, commentId }
  └─ OpenConfirmReviewController#robotAutoConfirm
       ├─ prUrl 非空 / commentId 非空（否则 403）
       ├─ scanId = tblPersonScanDMMapper.findLatestIdByPrUrl(prUrl)（空 → "未找到该 PR 的扫描记录"）
       └─ ConfirmReviewServce.robotAutoConfirm(scanId, prUrl, commentId)
            ├─ scanId → repoId（为空 → ScaException 60000）
            ├─ commentLogin = PlatformCommentUtil.resolveCommentLogin(prUrl, commentId, repoId)
            │     ├─ repoId → RepoInfoEntity（缺 projectId → 403）
            │     ├─ prUrl 前缀判定平台（gitee / gitcode）→ 取该平台 token 与 API base
            │     ├─ GET {apiBase}/repos/{owner}/{repo}/issues/{pr}/comments/{commentId}
            │     ├─ 解析 user.login（空 → 403）
            │     └─ 任一步异常 → ScaException(403, "权限校验失败，评论身份获取失败", ...)
            ├─ checkCommitterPermission(repoId, commentLogin)
            │     ├─ repoInfo → projectInfo（缺失 → 403）
            │     ├─ feign getCommitter(commentLogin, projectId/repoId/productId)
            │     ├─ code != 200 / data == null → 403（服务异常）
            │     └─ gitcodeName 集合不含 commentLogin → 403（非 committer）
            └─ 建单/重绑待审单 → autoPathReview 机器人批复 → 统计 total/confirmed/remaining
```

## 架构决策

| 决策                                                                      | 理由                                                                                                                            |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| D1 以"评论人身份 + 仓库 committer 授权"替代机机签名                       | 不引入密钥分发与时间戳窗口，直接复用平台已有的评论归属与 framework committer 数据；调用方无需持凭据                             |
| D2 身份从平台评论 API 反查，而非信任请求体 `commentLogin`                 | 修复伪造：`commentLogin` 完全由调用方控制，任何校验都建立在不可信输入上；`commentId` 绑定在 PR 评论路径下，作者由平台返回       |
| D3 门禁下沉 Service（`ConfirmReviewServceImpl#checkCommitterPermission`） | Controller 不感知仓库/项目/framework 细节；复用 `robotAutoConfirm` 已查 `repo_id`，避免重复查询；403 经 `ScaException` 统一透传 |
| D4 fail-closed：任何取参/Feign/评论反查异常均 403                         | 权限服务不可用时宁可拒绝，不可降级放行，避免"异常即绕过"                                                                        |
| D5 `/select/get-committer` 的 `userId` 传评论人登录名                     | 与 framework 侧"排除操作人"逻辑解耦：该参数与平台 userId 不同空间，不会被误移除 committer                                       |
| D6 只校验 `gitcodeName` 集合                                              | 与 PR 评论触发场景的实际身份命名空间一致；`giteeName` 不参与判断                                                                |
| D7 Controller 保留 `FORBIDDEN_CODE = 403` 常量与 `ScaException` 三参透传  | 保持既有 `ResponseEntity.failure(code, msg, data)` 语义，前端/调用方可区分 403 与业务失败                                       |

## 涉及文件

| 文件                                                                                        | 操作 | 说明                                                                                                                              |
| ------------------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenConfirmReviewController.java`     | 修改 | 入参校验 `commentId`；`robotAutoConfirm(scanId, prUrl, commentId)`；`ScaException` 三参透传；删除本地权限校验逻辑                 |
| `src/main/java/com/openlibing/sca/analysis/entity/dto/AutoConfirmPo.java`                   | 修改 | `commentLogin` → `commentId`                                                                                                      |
| `src/main/java/com/openlibing/sca/analysis/service/ConfirmReviewServce.java`                | 修改 | 接口签名 `robotAutoConfirm(String scanId, String prUrl, String commentId)`                                                        |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImpl.java`       | 修改 | 新增 `checkCommitterPermission`；`robotAutoConfirm` 内先反查身份再校验 committer                                                  |
| `src/main/java/com/openlibing/sca/analysis/entity/open/CommitterUserInfoDto.java`           | 新增 | framework committer 返回体（userId/userName/giteeName/gitcodeName/unboundPlatform/unboundEmail）                                  |
| `src/main/java/com/openlibing/sca/analysis/entity/open/QueryCommitterInputDto.java`         | 新增 | get-committer 请求体（userId/repoId/projectId/productId）                                                                         |
| `src/main/java/com/openlibing/sca/common/feign/OpenlibingFrameworkClient.java`              | 修改 | 新增 `getCommitter(@RequestParam userId, @RequestBody QueryCommitterInputDto)`，`POST /select/get-committer`                      |
| `src/main/java/com/openlibing/sca/common/utils/PlatformCommentUtil.java`                    | 新增 | `resolveCommentLogin(prUrl, commentId, repoId)`：平台判定、owner/repo/PR 编号解析、评论 API 调用、`user.login` 解析，失败统一 403 |
| `src/test/java/com/openlibing/sca/analysis/controller/OpenConfirmReviewControllerTest.java` | 修改 | 7 个用例，覆盖成功、空 prUrl、空 commentId(403)、无扫描记录、服务层 403、ScaException、未知异常                                   |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImplTest.java`   | 修改 | 新增 `mockCommitterGate` / `mockCommentAuthor` 桩与 4 个门禁失败用例                                                              |
| `src/test/java/com/openlibing/sca/common/utils/PlatformCommentUtilTest.java`                | 新增 | 6 个用例：gitcode/gitee 成功、仓库缺失、空响应、非法 PR 编号、API 异常                                                            |

## 风险 & 缓解

| 风险                                                                            | 缓解                                                                                                        |
| ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 平台评论 API 或 framework 不可用导致自动确认整体不可用                          | fail-closed 是安全取向；接口返回 403 + "权限校验服务异常，请稍后重试"，调用方可重试                         |
| `commentId` 本身不是调用方凭据：知道某条 committer 评论 ID 的第三方仍可重放触发 | 本轮未做频控/幂等（Issue P1 未覆盖）；实际暴露面受内网可达性约束，需后续补频控                              |
| 请求体字段改名导致存量调用方 400/拒绝                                           | 契约变更需调用方同步；本仓无法验证 sca-action 是否已改造（未验证）                                          |
| 仓库/项目元数据缺失（`projectId`/`productId` 为空）误伤合法请求                 | 403 文案明确"仓库或项目信息缺失"并记 ERROR 日志，便于运维定位                                               |
| 反查依赖 `prUrl` 格式（最后一段必须是 PR 编号）                                 | `parsePrNumber` 失败即 403 并记日志；`parseOwnerAndRepo` 校验 owner/repo 非空                               |
| gitcode/gitee 双平台 token 读取错误导致反查失败                                 | 平台由 `prUrl` 前缀判定，token 走 `PlatformUtil.getPlatformToken` 按 project 维度取；两平台均有成功用例覆盖 |

## 跨仓影响

- `openlibing-framework`：依赖 `POST /select/get-committer`（请求/响应结构由本仓 DTO 映射），
  该接口未在本批次修改，行为按既有契约假设。
- 调用方（sca-action / PR 评论触发链路）：请求体字段 `commentLogin` → `commentId` 为破坏性变更，
  改造仓库与状态未验证。
- `openlibing-sca` 与文档仓之外无其他改动。
