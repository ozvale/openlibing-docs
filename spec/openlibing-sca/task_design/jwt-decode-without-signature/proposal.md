# 91 jwt-decode-without-signature — 移除仅解码不验签的 JWT 身份链路

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/91
（【安全】【安全威胁】JWT 仅解码未验证签名，攻击者可伪造 token 冒充任意用户）

`JwtUtils#getClaimByName`（原 `src/main/java/com/openlibing/sca/analysis/utils/JwtUtils.java`）对请求携带的 token 只执行 `JWT.decode()`：不校验签名、不校验 `exp`、不限制 `alg`。`JwtUtils#getAccessToken` / `#getLogin` 及调用方 `OpenScanServiceImpl`、`MeasureServiceImpl` 又把解码出的 `login` / `sub` / `email` / `access_token` 直接当作身份与权限依据，攻击者可自签任意 token 冒充他人调用扫描、度量、导出、审核类接口。

归类：CWE-347（Improper Verification of Cryptographic Signature）。风险等级：高（身份仿冒 / 越权 / 提权）。

实际处置方式与 issue 修复建议不同：本轮不是"补验签"，而是**删除整条不可信身份链路**（提交说明标注 `as agreed`）。

## 功能描述

**做什么**：

1. 删除 `JwtUtils`（`getClaimByName` / `getAccessToken` / `getLogin` / `getCookieToken` 等）及其单测 `JwtUtilsTest`（-256 行）。
2. 摘除所有调用点的 token 解析与基于 `login`/`sub` 的权限过滤：
   - `MeasureServiceImpl#getCommMeasure` / `#getRepoMeasure`：删除 `extractLoginFromRequest`，以及 `buildResultIfAuthorized` / `buildRepoResultIfAuthorized`（CommunityManager、`roleId==4`、超管判定与 gitcode 平台分支）；
   - `OpenScanServiceImpl`：删除 `findCommitter` 内的 token 解析与"排除当前登录人"过滤、`findCommunity` 的 `getLoginFromRequest` + `filterByPermission`（超管 / `openeuler`、`src-openeuler` 公共社区 / 角色仓库交集逻辑）；
   - `OpenScanService#getCookieToken` 接口方法与其实现一并删除（已无引用）。
3. 删除无上游调用方的死代码：`LoginService` / `LoginServiceImpl`、`ImportUserPermission`（`versionImport` 门）、`OpenScanDMService#scanPathConfirmParseV2`，以及 `validator.yml` 中对应的孤儿校验条目。
4. `BinaryLicenseController` 两个导出接口去掉 `ImportUserPermission#versionImport` 前置权限判断。
5. 同步裁剪测试：`MeasureServiceImplTest`、`OpenScanDMServiceImplTest` 去掉相关 mock/断言；删除 `ImportUserPermissionTest`、`LoginServiceImplTest`；`BinaryLicenseControllerTest`、`LicenseControllerTest` 去掉对应桩。

**不做什么**：

- 不实现 issue 修复建议 1（`JWT.require(<Algorithm>).build().verify(token).getClaim(name)` + 算法白名单 + `exp` 校验）：`getClaimByName` 已删除，"验签"无落点；
- 不实现建议 2（统一验签入口、验签失败统一业务异常 + 审计日志）；
- 不实现建议 3（`access_token` 移出 JWT 载荷）：服务端已不再读取任何 claim；
- 不重建等价授权能力：由后续 `#156`（`manual-version-scan-auth` / `open-api-authz-hardening`）以显式 `userId` + `verifyProjectMemberPermission` 承担，不在本 issue 范围。

## 验收标准

- [x] 代码中不再存在绕过验签的 `JWT.decode` 身份解析路径：删除后全仓 grep `com.auth0.jwt` / `JWT.decode` / `io.jsonwebtoken` 均无命中
- [x] 伪造签名、`alg: none`、篡改 claim 的攻击场景失效：服务端不再从请求 token 推导身份（路径被删除，而非"验签失败"）
- [ ] `getClaimByName` 验签生效并拒绝伪造 / `alg: none` / 篡改 / 过期 token（本轮未覆盖：改为删除方法与调用点）
- [ ] 验签失败返回统一业务异常、日志不含 token 明文（本轮未覆盖：无验签与异常分支）
- [ ] 合法 token 全链路回归无破坏（本轮未覆盖：`JwtUtilsTest` 等已删除；接口行为按提交说明变更为"不再区分用户"）
- [ ] 相关单元测试通过、覆盖率达标（本次回溯未重新执行 `mvn test`，见 `tasks.md`）

## 影响范围

- 仓库：`openlibing-sca`（`analysis` 模块为主，`dm` 模块删除死方法）。
- 接口：无路由增删，但行为变化明显——社区/仓库度量接口返回全量数据、不再按角色过滤；二进制 license 的两个导出接口不再校验 `versionImport`；`findCommunity` 不再按 login 收窄。后续 `85b0706e` 直接删除 `/open/scan/find/committer`、`/open/scan/find/repoCommitter` 两个无鉴权接口（见 `../open-api-authz-hardening/`）。
- 配置：`src/main/resources/validator.yml` 删除 `scanPathConfirmParseV2` 条目。
- schema / 部署：无。
