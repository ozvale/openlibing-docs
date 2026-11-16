# open-api-authz-hardening — 实现任务

## 进度: 10/10 complete

- [x] Task 1: 删除无鉴权 committer 查询接口（`85b0706e`）—— `OpenScanController` / `OpenScanService` /
      `OpenScanServiceImpl` / `OpenScanControllerTest` 共 4 文件 -194 行；`/open/scan/find/committer`、
      `/open/scan/find/repoCommitter` 及其单测全部移除
- [x] Task 2: `getReposContents` 私仓鉴权（`f6c677ca`）—— 5 文件 +108/-31；新增用例
      `getReposContents_privateRepoWithoutUserRejected`、`getReposContents_userWithoutPermissionRejected`、
      `getReposContents_openSourceRepoWithoutUserAllowed`
- [x] Task 3: `putExportXLS` 导出保存鉴权（`07b063af`）—— 2 文件 +63；新增用例
      `save_privateRepoWithoutUserRejected`、`save_userWithoutPermissionRejected`、
      `save_userWithPermissionProceedsToRepoLookup`
- [x] Task 4: 手动版本扫描六接口项目成员鉴权（`53c32a60`，提交标注 `Refs #160`）—— 11 文件 +475/-123；
      `UserRoleMapper.queryProjectMemberPermission` + `CommonService.verifyProjectMemberPermission`；
      新增用例 `addRepo_noPermission_throwsPermissionException`、`query_noPermission_throwsPermissionException`、
      `startScan_noPermission_rejectsWholeBatch`、`deleteByIds_noPermission_rejectsWholeBatch`、
      `batchUpdateScheduled_noPermission_rejectsWholeBatch`、`getRepoBranchSelect_noPermission_throwsPermissionException`
      及 Controller 层 `addRepo_permissionException`、`repoBranchList_permissionException`；`mvn test` 70/70 通过
- [x] Task 5: 公告扫描清理接口社区权限（`449cc555`，提交标注 `Refs #160`）—— 5 文件 +78/-16；
      `ProjectNoticeScanServiceImpl.clearScanData` 前置 `verifyCommunityPermission`，拒绝时不提交后台任务；
      新增 `clearScanData_permissionException`、`clearScanData_noPermission_throwsPermissionException`
- [x] Task 6: `/open/person/scan/query` 仓库可见性鉴权（`1d0c0642`）—— 5 文件 +95/-4；
      `PersonScanQueryVO` 增加 userId；新增用例 `testSelectScanByparam_PrivateRepoNoUserId`、
      `testSelectScanByparam_PrivateRepoNotMember`、`testSelectScanByparam_PrivateRepoMember`、
      `testSelectScanByparam_RepoNotFound`
- [x] Task 7: `/review/file/review/history` 审核历史鉴权（`a8e8a5eb`）—— 5 文件 +123/-7；
      新增 `checkFileReviewHistoryPermission`（fail-closed）；新增用例 `testFileReviewHistory_PrivateRepoNoUserId`、
      `testFileReviewHistory_PrivateRepoNotMember`、`testFileReviewHistory_PrivateRepoMember`、
      `testFileReviewHistory_RepoNotFound`
- [x] Task 8: 导出文件下载归属校验（`b48b09d6`）—— 7 文件 +69/-15；`countByFileName` →
      `countByFileNameAndUserId`，SQL 增加 `user_id` 条件；新增用例
      `testDownloadFile_shouldRejectBlankUserIdBeforeLookup`、`testDownloadFile_shouldRejectFileOwnedByAnotherUser`、
      `countExportDataByFileName_returnsTrueForMatchingUser`、`countExportDataByFileName_returnsFalseWithoutMatchingUserRecord`
- [x] Task 9: 四个 open 列表接口项目成员鉴权（`6b300c27`）—— 8 文件 +92/-17；覆盖
      `/open/scan/community`、`/open/scan/community/branch`、`/open/scan/repos`、`/open/person/repos`；
      `exportCommunityCount` 内部调用链向下透传 userId
- [x] Task 10: `projectId` 收敛进 DTO（`76f4733a`）—— 8 文件 +20/-34；`ScanCommunityReq`、`ScanCommunityDto`
      新增 `projectId` 字段，Controller/Service 不再接收独立 `projectId` 参数

## 交付记录

| commit     | 摘要                                                                        | 变更规模          | 关联                            |
| ---------- | --------------------------------------------------------------------------- | ----------------- | ------------------------------- |
| `85b0706e` | fix(analysis): remove unauthenticated committer query endpoints             | 4 文件 +0/-194    | 无 Refs                         |
| `f6c677ca` | fix(analysis): add repo permission check to getReposContents                | 5 文件 +108/-31   | 无 Refs                         |
| `07b063af` | fix(analysis): add repo permission check to putExportXLS export             | 2 文件 +63/-0     | 无 Refs                         |
| `53c32a60` | feat(dm): enforce project-member permission on manual version scan apis     | 11 文件 +475/-123 | `Refs #160`                     |
| `449cc555` | feat(notice-scan): add community permission check to clear api              | 5 文件 +78/-16    | `Refs #160`                     |
| `1d0c0642` | feat(analysis): enforce repo visibility permission on scan query api        | 5 文件 +95/-4     | 无 Refs                         |
| `a8e8a5eb` | feat(analysis): add repo visibility check to file review history            | 5 文件 +123/-7    | 无 Refs                         |
| `b48b09d6` | fix(analysis): enforce export file ownership on download                    | 7 文件 +69/-15    | `Refs #156`                     |
| `6b300c27` | fix(analysis): add verifyProjectMemberPermission to 4 open scan/person APIs | 8 文件 +92/-17    | `Refs manual-version-scan-auth` |
| `76f4733a` | refactor(analysis): move projectId from method param into DTO fields        | 8 文件 +20/-34    | `Refs manual-version-scan-auth` |

- 分支：`ms_scan`（业务仓 `openlibing-sca`）
- 关联 Issue：`openlibing/openlibing-sca#156`
  - 仅 `b48b09d6` 显式写 `Refs #156`；`53c32a60`、`449cc555` 写 `Refs #160`，
    `6b300c27`、`76f4733a` 写 `Refs manual-version-scan-auth`。映射关系见本 spec 任务表。
- 验证方式：
  - `53c32a60`：commit message 记录 `mvn test 70/70 通过`（dm 模块相关用例）。
  - 其余 commit：仅记录新增/适配用例，未记录整体测试输出，**未验证**。
  - `6b300c27`、`76f4733a` 未新增单测；`OpenReposServiceImplTest` 既有
    `testGetCommunity_VersionScan` / `testGetCommunity_PersonScan` / `testGetCommunity_All` /
    `testGetCommunityByBranch` 未随本次改造新增拒绝用例。
  - 安全复核：建议在 PR 阶段对 design.md"接口 → 校验方式 → 越权返回码"表中的接口逐一验证
    "公仓匿名 / 私仓匿名 / 私仓非成员 / 私仓成员"四种组合，本轮未提供执行记录。
