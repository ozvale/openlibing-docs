# 91 jwt-decode-without-signature — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 删除 `JwtUtils` 与 `JwtUtilsTest`（`5852b0d2`）
- [x] Task 2: 摘除 `MeasureServiceImpl` / `OpenScanServiceImpl` / `OpenScanService` 中的 token 解析与 login 过滤（`5852b0d2`）
- [x] Task 3: 删除死代码 `LoginService` / `LoginServiceImpl` / `ImportUserPermission` / `scanPathConfirmParseV2` 与 `validator.yml` 条目，去掉 `BinaryLicenseController` / `LicenseController` 的权限门（`5852b0d2`）
- [x] Task 4: 裁剪相关单测（`MeasureServiceImplTest`、`OpenScanDMServiceImplTest`、`BinaryLicenseControllerTest`、`LicenseControllerTest`，删除 3 个测试类）（`5852b0d2`）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                           | 关联                                                  |
| ---------- | -------------------------------------------------------------- | ----------------------------------------------------- |
| `5852b0d2` | refactor(auth): remove JwtUtils and JWT-based permission logic | 提交 message 未写 `Refs #91`（按 issue 主题回溯关联） |

关键 diff：

- `JwtUtils.java` 整文件删除（121 行），`JwtUtilsTest.java`（256 行）删除。
- `MeasureServiceImpl`：删除 `extractLoginFromRequest`、`buildResultIfAuthorized`、`buildRepoResultIfAuthorized`，两个查询方法直接返回 `list` + `total`。
- `OpenScanServiceImpl`：删除 `getCookieToken` 实现、`getLoginFromRequest`、`filterByPermission`；`findCommunity` 改为 `sortAndDeduplicate(communityNewList)` 后直接分组。
- `OpenScanDMServiceImpl`：删除 `scanPathConfirmParseV2(IssuePathPo, HttpServletRequest)`（39 行）；`validator.yml` 删除同名校验条目。
- `BinaryLicenseController`：两个导出接口删除 `importUserPermission.versionImport(...)` 判断与字段注入。

验证方式：

- 静态核实：全仓 grep `com.auth0.jwt` / `JWT.decode` / `JwtUtils` / `LoginService` / `ImportUserPermission` / `scanPathConfirmParseV2` 均无残留引用（仅 `#108` 的 `io.jsonwebtoken` 链路在下一提交清除）。
- 单测：本地 UT 日志（`5_ut.log`，2026-11-14）显示 `MeasureServiceImplTest` 18 个用例、`OpenScanServiceImplTest` 27 个用例全部通过；本次回溯未重新执行 `mvn test`。
- 覆盖率：未验证。

## 备注：与 issue 修复建议的差异

issue 要求"验签后取 claim + 算法白名单 + exp 校验 + 统一业务异常"。实际落地为删除整条身份链路（提交说明 `as agreed`），因此上述四项均不适用；服务端不再从 token 推导身份，相关授权改由后续 #156（`../open-api-authz-hardening/`）以显式 `userId` 参数 + `verifyProjectMemberPermission` 承担。
