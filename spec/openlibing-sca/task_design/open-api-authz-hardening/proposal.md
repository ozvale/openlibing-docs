# open-api-authz-hardening — open 接口鉴权与返回面收口（#156）

## 需求背景

业务 Issue：[openlibing/openlibing-sca#156](https://gitcode.com/openlibing/openlibing-sca/issues/156)
（【数据安全】openlibing-sca 多个接口存在无认证或返回数据不合理，通过接口返回数据的利用可下载在
OpenLibing 经过扫描的任意代码仓代码（包括私仓））。

- 类型：数据安全 / 越权访问（broken access control），无 CVE 编号；issue 未标注 CWE，可归类 CWE-862（缺少授权）与 CWE-639（IDOR）。
- 攻击链（issue 原文）：
  1. `/gateway/openlibing-sca/open/person/repos` 可获取某社区全部代码仓（含私仓）及 `repoId`；
  2. 用 `repoId` 调 `/gateway/openlibing-sca/open/person/scan/query` 拿到该仓库在 OpenLibing 上的所有扫描记录 `scanId`；
  3. 用 `scanId` 直接调 `/gateway/openlibing-sca/open/scan/getReposContents` 读取该仓库源码内容。
- 风险与影响：未登录用户可越权读取任意社区（含私仓）的源码，等同于"下载社区机密私仓代码"；
  同时 `find/committer` 系列接口无鉴权返回 committer 的 userId/userName，可被用于伪造 userId 绕过仓库权限校验。
- 关联批次：同批次的 `ManualVersionScanController` 鉴权改造与公告扫描清理接口鉴权分别提交时标注
  `Refs #160`，本轮按批次口径归入本 issue 一并归档。

## 功能描述

**做什么**：

1. 删除无鉴权的 committer 查询接口：`GET /open/scan/find/committer`、`GET /open/scan/find/repoCommitter`
   （连同 Service 方法、实现与单测）。
2. 对私仓数据读取类接口按"仓库可见性 + 仓库成员身份"两段校验：公仓匿名可读，私仓未登录返回业务码 4001，
   已登录但非仓库成员返回业务码 403。
3. 对列表聚合类接口按"项目成员身份"校验：`CommonService.verifyProjectMemberPermission`，
   admin / platform_operater 全局放行，其余要求 `user_role_info` 中存在当前项目（`perm_group_id=0`）任意项目级角色。
4. 导出任务与下载接口绑定调用者：导出保存前鉴权，下载时按 `fileName + userId` 校验文件归属。
5. 审核历史、公告扫描清理等读/清理接口补充权限校验。
6. 接口契约调整：相关接口新增 `userId`（部分可选）与 `projectId` 参数；`projectId` 由独立
   `@RequestParam` 收敛进 `ScanCommunityReq` / `ScanCommunityDto`。

**不做什么**：

- 不引入统一网关级鉴权拦截器或 Spring Security 全局过滤器（仍由各 Controller 显式校验）。
- 不改动仓库权限判定服务（`openlibingFrameworkClient.checkRepoUserNamePermission`）的实现。
- 不改变公开数据的匿名可读能力（公仓仍允许未登录访问）。
- 不逐一复核未被 issue 点名的其它 `/open/**` 接口（见验收标准"本轮未覆盖"项）。

## 验收标准

- [x] `/open/scan/find/committer`、`/open/scan/find/repoCommitter` 已删除（Controller/Service/Impl/Test 共 -194 行，`85b0706e`）
- [x] `/open/scan/getReposContents`：私仓未传 userId → 4001；userId 非仓库成员 → 403（`f6c677ca`）
- [x] `/open/scan/putExportXLS`：私仓未传 userId → 4001；userId 非仓库成员 → 403（`07b063af`）
- [x] `/open/person/scan/query`：公仓直接访问；私仓未传 userId → 4001；非成员 → 403；仓库不存在 → 403（`1d0c0642`）
- [x] `/open/person/repos`、`/open/scan/repos`、`/open/scan/community`、`/open/scan/community/branch`：
      项目成员校验失败 → 403（`6b300c27`）
- [x] `/review/file/review/history`：公仓匿名可读；私仓未登录 → 4001；非成员 → 403；
      repoId 缺失/非法/仓库不存在 → 403（fail-closed，`a8e8a5eb`）
- [x] `/open/download/file`：`userId` 必填；文件名与 userId 绑定查询 `tbl_export_data`，无法下载他人导出（`b48b09d6`）
- [x] `/version/scan/*` 六个接口（save/query/startVersionScan/batchUpdateScheduled/deleteByIds/repoBranchList）：
      项目成员校验失败 → 403；批量接口任一记录越权整批拒绝（`53c32a60`，提交标注 `Refs #160`）
- [x] `/project/notice/scan/clear`：复用 `verifyCommunityPermission`（admin / platform_operater 或指定项目
      project_manager），越权 → 403（`449cc555`，提交标注 `Refs #160`）
- [x] 单测覆盖主要拒绝/放行路径（新增用例见 tasks.md）
- [ ] 全量回归：仅 `53c32a60` 在 commit message 中记录 `mvn test 70/70 通过`，其余 commit 未记录整体测试结果，**未验证**
- [ ] 前端 / 网关适配新增必填 `userId`：跨仓，**未验证**
- [ ] 其它 `/open/**` 接口的认证矩阵全量复核（issue 修复建议第 1 条）：本轮仅覆盖上述接口，**未覆盖**
- [ ] 接口返回字段最小化（issue 修复建议第 2 条）：本轮以删除 committer 接口与鉴权为主，未系统性裁剪返回字段，**部分覆盖**

## 影响范围

- 仓库：`openlibing-sca`（analysis 模块 controller/service/dao/mapper 与 dm 模块）。
- 接口契约变化（调用方需同步适配）：
  - 新增必填 `userId`：`/open/scan/community`、`/open/scan/repos`、`/open/scan/community/branch`、
    `/open/person/repos`、`/open/download/file`、`/version/scan/{save,query,startVersionScan,batchUpdateScheduled,deleteByIds,repoBranchList}`、
    `/project/notice/scan/clear`（另加必填 `communityId`）。
  - 新增可选 `userId`：`/open/scan/getReposContents`、`/open/person/scan/query`、`/review/file/review/history`。
  - 删除接口：`/open/scan/find/committer`、`/open/scan/find/repoCommitter`。
  - `projectId` 由 `@RequestParam` 移入 `ScanCommunityReq` / `ScanCommunityDto`（查询参数形态不变）。
- 配置：无变化。
- Schema：无数据库结构变化（仅新增查询语句 `queryProjectMemberPermission`、`selectByIds`）。
- 跨仓：前端页面与网关需透传 `userId`。
