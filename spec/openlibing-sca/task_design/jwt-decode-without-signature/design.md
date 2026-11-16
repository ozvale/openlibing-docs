# 91 jwt-decode-without-signature — 技术设计

## 方案概述

采用"删除不可信身份链路"替代"补验签"。`5852b0d2` 一次性删除 `JwtUtils`、其全部调用点、依附在这些调用点上的权限过滤与死代码，并同步裁剪测试。删除后服务端不再读取请求 token 的任何 claim，"伪造 token → 冒充用户"在代码层没有落点。

## 架构决策

| 决策                    | 证据 / 理由                                                                                                                                                                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 删除而不是改成验签   | 提交说明明确 `as agreed`。该链路取出的 `login`/`sub` 是自签数据，从未与服务端会话绑定；补验签需新增密钥、算法白名单、过期策略与异常映射，灰发成本高于删除。授权能力由后续 #156 用显式 `userId` + `verifyProjectMemberPermission` 重建                          |
| D2 直接摘除权限过滤分支 | `MeasureServiceImpl` 删除 `extractLoginFromRequest` 与 `buildResultIfAuthorized` / `buildRepoResultIfAuthorized`；`OpenScanServiceImpl` 删除 `getLoginFromRequest`、`filterByPermission`，以及 `findCommitter` 中 `!"all".equals(type)` 时排除当前登录人的过滤 |
| D3 死代码一并删除       | `LoginService` / `LoginServiceImpl` 无上游调用方；`OpenScanDMService#scanPathConfirmParseV2` 无调用方（`validator.yml` 对应条目随之成为孤儿）；`ImportUserPermission` 仅被两个 `BinaryLicenseController` 导出接口使用                                          |
| D4 导出权限门接受移除   | `ImportUserPermission#versionImport` 依赖 JWT 登录态，链路删除后该门失效，提交说明将其列为 agreed 的行为变更                                                                                                                                                   |
| D5 测试裁剪而非重写     | `JwtUtilsTest`（256 行）、`ImportUserPermissionTest`（131 行）、`LoginServiceImplTest`（143 行）随被测代码删除；`MeasureServiceImplTest`、`OpenScanDMServiceImplTest` 去掉 token/角色相关 mock 与断言                                                          |
| D6 授权重建留给后续需求 | `6b300c27` 为 4 个 open 接口增加 `userId` + `projectId` 与 `verifyProjectMemberPermission`；`85b0706e` 删除无鉴权的 committer 查询接口。详见 `../open-api-authz-hardening/`                                                                                    |

## 涉及文件

| 文件                                                                                    | 操作 | 说明                                                                                                                                              |
| --------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/utils/JwtUtils.java`                         | 删除 | JWT 解析工具类（121 行）                                                                                                                          |
| `src/main/java/com/openlibing/sca/analysis/service/LoginService.java`                   | 删除 | 无上游调用方                                                                                                                                      |
| `src/main/java/com/openlibing/sca/analysis/service/impl/LoginServiceImpl.java`          | 删除 | 同上（65 行）                                                                                                                                     |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ImportUserPermission.java`      | 删除 | `versionImport` 权限门（130 行）                                                                                                                  |
| `src/main/java/com/openlibing/sca/analysis/controller/BinaryLicenseController.java`     | 修改 | 两个导出接口去掉 `versionImport` 判断与依赖注入                                                                                                   |
| `src/main/java/com/openlibing/sca/analysis/controller/LicenseController.java`           | 修改 | 去掉 `ImportUserPermission` 注入与 import                                                                                                         |
| `src/main/java/com/openlibing/sca/analysis/service/OpenScanService.java`                | 修改 | 删除 `getCookieToken` 声明                                                                                                                        |
| `src/main/java/com/openlibing/sca/analysis/service/impl/MeasureServiceImpl.java`        | 修改 | 删除 JWT 身份提取与两个授权结果构造方法                                                                                                           |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`       | 修改 | 删除 `getCookieToken` 实现、`getLoginFromRequest`、`filterByPermission`、`findCommitter` 的 login 过滤；`findCommunity` 直接 `sortAndDeduplicate` |
| `src/main/java/com/openlibing/sca/dm/service/OpenScanDMService.java`                    | 修改 | 删除 `scanPathConfirmParseV2` 声明                                                                                                                |
| `src/main/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImpl.java`           | 修改 | 删除 `scanPathConfirmParseV2` 实现（39 行）                                                                                                       |
| `src/main/resources/validator.yml`                                                      | 修改 | 删除 `scanPathConfirmParseV2` 校验条目                                                                                                            |
| `src/test/java/com/openlibing/sca/analysis/utils/JwtUtilsTest.java`                     | 删除 | -256 行                                                                                                                                           |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ImportUserPermissionTest.java`  | 删除 | -131 行                                                                                                                                           |
| `src/test/java/com/openlibing/sca/analysis/service/impl/LoginServiceImplTest.java`      | 删除 | -143 行                                                                                                                                           |
| `src/test/java/com/openlibing/sca/analysis/service/impl/MeasureServiceImplTest.java`    | 修改 | 去掉 token/角色 mock 与断言                                                                                                                       |
| `src/test/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImplTest.java`       | 修改 | 删除 `scanPathConfirmParseV2` 相关用例（-43 行）                                                                                                  |
| `src/test/java/com/openlibing/sca/analysis/controller/BinaryLicenseControllerTest.java` | 修改 | 去掉权限桩                                                                                                                                        |
| `src/test/java/com/openlibing/sca/analysis/controller/LicenseControllerTest.java`       | 修改 | 去掉 `ImportUserPermission` mock                                                                                                                  |

合计 19 个文件、+18 / -1316 行。

## 风险 & 缓解

| 风险                                                    | 缓解                                                                                                                                                                     |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 度量接口失去角色过滤，任何调用方可看到全量社区/仓库度量 | 本轮接受的取舍（提交说明 agreed）；当前 `MeasureController` 仍无 `userId`/权限校验，属残余未验证面，需由 #156 系列补齐                                                   |
| 二进制 license 导出失去 `versionImport` 权限门          | 同上；导出仍要求调用方传 `userId`，但未做服务端校验                                                                                                                      |
| 前端依赖"只见自己权限范围内仓库"的返回结果              | 返回集合变大，需前端/用例回归；本轮未验证                                                                                                                                |
| 误删仍在使用的代码                                      | `5852b0d2` 提交说明逐项标注"no upstream caller / no caller"，且当前全仓 grep 无 `JwtUtils` / `LoginService` / `ImportUserPermission` / `scanPathConfirmParseV2` 残留引用 |
| JWT 依赖残留（java-jwt / jjwt）                         | `JwtUtils` 删除后无 `com.auth0.jwt` 引用；依赖清理见 `../jjwt-dependency-removal/`                                                                                       |

## 跨仓影响

无代码级依赖。服务端不再读取 `authentication` 头/cookie 中的 token，网关或前端继续携带 token 也不会被本服务解析；调用方是否依赖被移除的 `versionImport` 403 语义未验证。
