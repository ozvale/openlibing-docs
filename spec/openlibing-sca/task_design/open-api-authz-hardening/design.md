# open-api-authz-hardening — 技术设计

## 方案概述

不改动既有业务逻辑，只在数据出口与高危操作入口前置鉴权，分三类：

1. **仓库维度**（私仓数据）：复用门禁详情既有模式——公仓匿名放行；私仓未登录返回业务码 `4001`；
   已登录调用框架 `checkRepoUserNamePermission(userId, repoInfoEntity)` 判定仓库成员，非成员返回 `403`。
2. **项目维度**（列表聚合 / 增删改查 / 清理）：新增统一入口
   `CommonService.verifyProjectMemberPermission(userId, projectId)`，底层
   `UserRoleMapper.queryProjectMemberPermission`，失败抛 `PermissionException`（code=403），
   Controller 捕获后返回 403。
3. **对象归属**（导出下载）：把导出记录查询从"仅按文件名"改为"按文件名 + userId"，切断按文件名猜测下载他人导出的路径。

同时删除无法安全鉴权、且可被用于 userId 伪造的 committer 查询接口。

## 接口 → 校验方式 → 越权返回码

表中返回码取自代码里的业务码（`ResponseEntity.failure(code, msg)` 或 `ScaException` 的 `errorCode`）。
该 `ResponseEntity` 来自平台 SDK（`com.openlibing.common`），本仓不可见其实现，是否同时改写 HTTP
状态码**未验证**；前端应以响应体 code 判断。

| 接口                                      | 实现位置                                                                       | 校验方式                                                                                                           | 越权/未认证返回                                                               |
| ----------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| `GET /open/scan/find/committer`           | 原 `OpenScanController.findCommitter`                                          | 已删除                                                                                                             | 接口不存在（路由缺失）                                                        |
| `GET /open/scan/find/repoCommitter`       | 原 `OpenScanController.findRepocCmmitter`                                      | 已删除                                                                                                             | 接口不存在（路由缺失）                                                        |
| `GET /open/scan/getReposContents`         | `OpenScanServiceImpl.getReposContents`                                         | userId 为空 → 私仓判定 `prIsOpenSourceRepo(scanId)`；userId 非空 → `prDetailAuth` 调 `checkRepoUserNamePermission` | 私仓未登录 `4001 private repo, need login`；非成员 `403 no permission`        |
| `POST /open/scan/putExportXLS`            | `OpenScanServiceImpl.save`                                                     | 同 `getReposContents`（`prIsOpenSourceRepo` + `prDetailAuth`）                                                     | `4001`（私仓未登录）/ `403`（非成员）                                         |
| `POST /open/person/scan/query`            | `OpenPersonScanServiceImpl.selectScanByparam`                                  | 按 `RepoInfoEntity.visibility`：非 `REPO_EXTERNAL` 时要求 userId + `checkRepoUserNamePermission`                   | 私仓未登录 `4001`；非成员 `403`；仓库不存在 `403`                             |
| `GET /open/person/repos`                  | `OpenPersonScanServiceImpl.getPersonScanByCommunity`                           | `verifyProjectMemberPermission(userId, dto.projectId)`                                                             | `403 权限不足`                                                                |
| `GET /open/scan/repos`                    | `OpenScanServiceImpl.getScanByCommunity`                                       | `verifyProjectMemberPermission(userId, req.projectId)`                                                             | `403 权限不足`                                                                |
| `GET /open/scan/community`                | `OpenReposServiceImpl.getCommunity`                                            | `verifyProjectMemberPermission(req.userId, req.projectId)`                                                         | `403 权限不足`                                                                |
| `GET /open/scan/community/branch`         | `OpenReposServiceImpl.getCommunityByBranch`                                    | `verifyProjectMemberPermission(userId, projectId)`                                                                 | `403 权限不足`                                                                |
| `POST /review/file/review/history`        | `ConfirmReviewServceImpl.checkFileReviewHistoryPermission`                     | 公仓放行；私仓要求 userId + `checkRepoUserNamePermission`；repoId 解析失败/仓库不存在直接拒绝                      | 私仓未登录 `4001`；非成员或仓库不存在 `403`                                   |
| `GET /open/download/file`                 | `FileController.downloadFile` + `TblExportDataMapper.countByFileNameAndUserId` | `userId` 必填非空；`tbl_export_data` 按 `file_name + user_id` 计数                                                 | 空 userId → `failure("用户ID不得为空")`；非本人文件 → `failure("文件不存在")` |
| `POST /version/scan/save`                 | `ManualVersionScanServiceImpl.addRepo`                                         | 项目成员校验（按入参项目）                                                                                         | `403`                                                                         |
| `POST /version/scan/query`                | `ManualVersionScanServiceImpl.query`                                           | 项目成员校验（按查询条件项目）                                                                                     | `403`                                                                         |
| `POST /version/scan/startVersionScan`     | `ManualVersionScanServiceImpl.startScan`                                       | 整批逐条校验，任一越权整批拒绝                                                                                     | `403`                                                                         |
| `POST /version/scan/batchUpdateScheduled` | `ManualVersionScanServiceImpl.batchUpdateScheduled`                            | 同 startScan                                                                                                       | `403`                                                                         |
| `POST /version/scan/deleteByIds`          | `ManualVersionScanServiceImpl.deleteByIds`                                     | `selectByIds` 取记录后整批校验                                                                                     | `403`                                                                         |
| `GET /version/scan/repoBranchList`        | `ManualVersionScanServiceImpl.getRepoBranchSelect`                             | 项目成员校验                                                                                                       | `403`                                                                         |
| `POST /project/notice/scan/clear`         | `ProjectNoticeScanServiceImpl.clearScanData`                                   | `verifyCommunityPermission(userId, communityId)`：admin / platform_operater 或该项目 project_manager               | `403 权限不足`，且不提交清理任务                                              |

> 说明：`/open/scan/getReposContents` 在未传 userId 且 `scanId` 无法解析出仓库时，
> `prIsOpenSourceRepo` 返回 false，同样以 `4001` 拒绝（fail-closed）。

## 架构决策

| 决策                                                                                                                        | 理由                                                                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| D1：新增 `UserRoleMapper.queryProjectMemberPermission` + `CommonService.verifyProjectMemberPermission` 作为唯一项目鉴权入口 | 避免每个 Service 重复写用户/角色查询；SQL 集中在 Mapper XML，便于审计                                                                           |
| D2：项目成员口径 = admin / platform_operater 全局放行，或 `project_id = 当前项目 AND perm_group_id = 0` 的任意项目级角色    | 与既有 `queryCommunityPermission` 的"默认权限组"口径一致，避免引入第二套权限语义                                                                |
| D3：仓库维度校验复用 `getTree` 既有两段式（`prIsOpenSourceRepo` + `prDetailAuth`）                                          | 门禁详情接口已有成熟实现与单测，复用可保证同类接口行为一致（`f6c677ca`、`07b063af` 明确"same permission validation as getTree"）                |
| D4：审核历史 fail-closed（repoId 缺失/非法/仓库不存在一律 403）                                                             | 该接口无 scanId 可推导仓库，无法安全放行；宁可拒绝也不降级为匿名可读（`a8e8a5eb`）                                                              |
| D5：直接删除 committer 查询接口，而不是补鉴权                                                                               | 该接口返回 userId/userName 列表，是 userId 伪造的输入源；业务上无必须保留的证据，删除比"加鉴权后仍暴露名单"更彻底（`85b0706e`）                 |
| D6：导出下载绑定 `fileName + userId`                                                                                        | 导出文件名可被枚举/猜测，仅校验"文件存在"不能阻止他人下载；归属绑定使越权请求表现为"文件不存在"，不泄露存在性（`b48b09d6`）                     |
| D7：批量接口整批校验、任一越权整批拒绝                                                                                      | 避免"部分成功"造成的越权写入与状态不一致；`selectByIds` 一次取全量记录后统一校验（`53c32a60`）                                                  |
| D8：`projectId` 从独立 `@RequestParam` 收敛进 `ScanCommunityReq` / `ScanCommunityDto`                                       | 四个接口原本已接收整个查询对象，独立参数与对象字段重复；收敛后 DTO 一处携带，`exportCommunityCount` 内部调用链也只需在 DTO 上设置（`76f4733a`） |
| D9：鉴权失败统一抛 `PermissionException`（code=403）或 `ScaException(4001/403, ...)`，由 Controller 转成业务响应            | 与仓库既有错误返回风格一致，前端可按 code 区分"需登录"与"无权限"                                                                                |

## 涉及文件

| 文件                                                                                        | 操作 | 说明                                                                                                                                             |
| ------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenScanController.java`              | 修改 | 删除 committer 两个接口；`getReposContents` 增加可选 userId；`/community`、`/community/branch`、`/repos` 增加 userId 与 PermissionException 处理 |
| `src/main/java/com/openlibing/sca/analysis/service/OpenScanService.java`                    | 修改 | 删除 committer 方法；`getReposContents`、`countExportDataByFileName` 签名调整；`getScanByCommunity` 增加 userId                                  |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`           | 修改 | `getReposContents`、`save` 前置鉴权；`getScanByCommunity` 前置项目校验；`countExportDataByFileName` 绑定 userId                                  |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenPersonScanController.java`        | 修改 | `/repos` 增加 userId 与 PermissionException 处理；`/scan/query` 透传 userId                                                                      |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenPersonScanServiceImpl.java`     | 修改 | `selectScanByparam` 可见性校验；`getPersonScanByCommunity` 项目成员校验                                                                          |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenReposServiceImpl.java`          | 修改 | `getCommunity`、`getCommunityByBranch` 项目成员校验                                                                                              |
| `src/main/java/com/openlibing/sca/analysis/service/CommonService.java`                      | 修改 | 新增 `verifyProjectMemberPermission`                                                                                                             |
| `src/main/java/com/openlibing/sca/analysis/service/impl/CommonServiceImpl.java`             | 修改 | 实现：空 userId → PermissionException；查询计数为 0 → PermissionException                                                                        |
| `src/main/java/com/openlibing/sca/analysis/dao/UserRoleMapper.java`                         | 修改 | 新增 `queryProjectMemberPermission`                                                                                                              |
| `src/main/resources/mapper/analysis/UserRoleMapper.xml`                                     | 修改 | 新增权限查询 SQL                                                                                                                                 |
| `src/main/java/com/openlibing/sca/analysis/controller/ConfirmReviewController.java`         | 修改 | `/file/review/history` 增加可选 userId                                                                                                           |
| `src/main/java/com/openlibing/sca/analysis/service/ConfirmReviewServce.java`                | 修改 | `fileReviewHistory(reviewPo, userId)`                                                                                                            |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImpl.java`       | 修改 | 新增 `checkFileReviewHistoryPermission`（fail-closed）                                                                                           |
| `src/main/java/com/openlibing/sca/analysis/controller/FileController.java`                  | 修改 | 下载增加必填 userId，空白拒绝                                                                                                                    |
| `src/main/java/com/openlibing/sca/analysis/dao/TblExportDataMapper.java`                    | 修改 | `countByFileName` → `countByFileNameAndUserId`                                                                                                   |
| `src/main/resources/mapper/analysis/TblExportDataMapper.xml`                                | 修改 | 查询条件增加 `user_id`                                                                                                                           |
| `src/main/java/com/openlibing/sca/common/domain/ScanCommunityReq.java`                      | 修改 | 新增 `projectId` 字段                                                                                                                            |
| `src/main/java/com/openlibing/sca/common/domain/ScanCommunityDto.java`                      | 修改 | 新增 `projectId` 字段                                                                                                                            |
| `src/main/java/com/openlibing/sca/dm/controller/ManualVersionScanController.java`           | 修改 | 六个接口增加 userId 与 PermissionException 处理                                                                                                  |
| `src/main/java/com/openlibing/sca/dm/service/ManualVersionScanService.java`                 | 修改 | 六个方法签名增加 userId                                                                                                                          |
| `src/main/java/com/openlibing/sca/dm/service/impl/ManualVersionScanServiceImpl.java`        | 修改 | 前置项目成员校验；批量接口整批校验                                                                                                               |
| `src/main/java/com/openlibing/sca/dm/dao/TblManualVersionScanMapper.java`                   | 修改 | 新增 `selectByIds`                                                                                                                               |
| `src/main/resources/mapper/dm/TblManualVersionScanMapper.xml`                               | 修改 | 新增 `selectByIds` 查询                                                                                                                          |
| `src/main/java/com/openlibing/sca/dm/controller/ProjectNoticeScanController.java`           | 修改 | `/clear` 增加 userId、communityId 与 PermissionException 处理                                                                                    |
| `src/main/java/com/openlibing/sca/dm/service/ProjectNoticeScanService.java`                 | 修改 | `clearScanData` 签名增加 userId、communityId                                                                                                     |
| `src/main/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanServiceImpl.java`        | 修改 | 提交清理任务前 `verifyCommunityPermission`                                                                                                       |
| `src/test/java/com/openlibing/sca/analysis/controller/OpenScanControllerTest.java`          | 修改 | 删除 committer 用例；适配 getReposContents 参数                                                                                                  |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImplTest.java`       | 修改 | getReposContents / save 鉴权与文件归属用例                                                                                                       |
| `src/test/java/com/openlibing/sca/analysis/controller/OpenPersonScanControllerTest.java`    | 修改 | `/repos` 适配 userId                                                                                                                             |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenPersonScanServiceImplTest.java` | 修改 | scan/query 私仓拒绝与成员放行用例                                                                                                                |
| `src/test/java/com/openlibing/sca/analysis/controller/ConfirmReviewControllerTest.java`     | 修改 | `/file/review/history` 适配 userId                                                                                                               |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImplTest.java`   | 修改 | 审核历史权限用例                                                                                                                                 |
| `src/test/java/com/openlibing/sca/analysis/controller/FileControllerTest.java`              | 修改 | 空 userId、他人文件用例                                                                                                                          |
| `src/test/java/com/openlibing/sca/dm/controller/ManualVersionScanControllerTest.java`       | 修改 | 六接口适配 + PermissionException 用例                                                                                                            |
| `src/test/java/com/openlibing/sca/dm/service/impl/ManualVersionScanServiceImplTest.java`    | 修改 | 越权拒绝与整批拒绝用例                                                                                                                           |
| `src/test/java/com/openlibing/sca/dm/controller/ProjectNoticeScanControllerTest.java`       | 修改 | clear 越权用例                                                                                                                                   |
| `src/test/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanServiceImplTest.java`    | 修改 | clearScanData 权限用例                                                                                                                           |

## 风险 & 缓解

| 风险                                                           | 缓解                                                                                             |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 前端未透传新增的必填 `userId` 导致接口调用失败                 | 属预期契约收紧；proposal 中列出全部受影响接口，跨仓适配需前端/网关同步（本轮未验证）             |
| `checkRepoUserNamePermission` 依赖框架服务，异常时无法判定权限 | 现有 `getTree` 同样依赖该调用；本轮未新增降级逻辑，异常按既有异常处理路径返回（未验证具体表现）  |
| 项目成员口径过宽（任意项目级角色即视为成员）                   | 与既有 `queryCommunityPermission` 口径保持一致；如需更细粒度（如仅 project_manager）应单独提需求 |
| 公仓匿名可读被误判为漏洞未修复                                 | 公仓源码本身可公开访问，保留匿名可读是产品要求；私仓路径已全部要求登录 + 成员                    |
| 删除 `find/committer` 影响既有调用方                           | 该接口为无鉴权内部查询；commit 删除同时清理 Service/Impl/Test，未保留兼容层（调用方适配未验证）  |
| 批量接口整批拒绝影响可用性                                     | 仅在有越权记录时拒绝；同项目批量操作不受影响                                                     |
| 下载错误提示暴露文件是否存在                                   | 统一返回"文件不存在"，不区分"无权限"与"不存在"                                                   |

## 跨仓影响

- 前端页面：`/open/scan/community`、`/open/scan/repos`、`/open/scan/community/branch`、`/open/person/repos`、
  `/open/download/file`、`/version/scan/*`、`/project/notice/scan/clear` 需透传 `userId`；
  私仓场景需透传登录态 userId。**未验证**
- 网关：`/gateway/openlibing-sca/**` 需保证 `userId` 查询参数透传。**未验证**
- 平台框架服务：依赖 `checkRepoUserNamePermission` 仓库成员判定结果。
- spec 文档归档 openlibing-docs 仓（本目录）；`/version/scan/*` 与 `/project/notice/scan/clear`
  的鉴权改造同属本批次（提交分别标注 `Refs #160`）。
