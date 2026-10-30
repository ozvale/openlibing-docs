# fix-checkboard-repo-visibility-auth

## 需求背景

看板详情、全量趋势、Excel 导出/下载等接口在网关侧配置为**可免登录访问**（`userId` 可为空）。改造前，部分入口未在业务层校验关联代码仓是否**公开/开源**，或未校验已登录用户是否具备**仓读权限**，存在通过 summaryId / taskId / uuid 窥探私有仓检查结果的风险。

本 PR 将原先散落在 `CheckboardDelegateImpl` 内的仓可见性与 Feign 读权限逻辑抽到 `CheckboardRepoAccessHelper`，并在此前缺少校验的看板统计、趋势、导出链路上统一调用。

## 功能描述

1. **新增 `CheckboardRepoAccessHelper`**：封装全量 summary / task、门禁 MR（uuid）两类维度的鉴权。
2. **免登录（`userId` 为空）**：仅当关联仓为对外可见时放行——全量仓 `visibility == public`；门禁仓 `visibility == REPO_EXTERNAL`（`ProjectConstant.RepoVisibility`）。
3. **已登录（`userId` 非空）**：通过 `OpenlibingFrameworkClient.checkRepoUserNamePermission(userId, repoInfo)` 校验仓读权限；失败返回 `403` / `no permission`。
4. **参数缺失**：summaryId / taskId / uuid 为空返回 `50001`。
5. **私有仓 + 免登录**：返回 `4001` / `private repo, no permission`。
6. **看板入口补校验**：
   - `getDetailNum` 增加可选 `userId`，按 type 走全量 summary 或 MR uuid 校验；
   - `getFullTaskTrend` 增加可选 `userId`，走 `assertFullTaskAccess`；
   - `getTaskResultDetails` 在查询前走 `assertFullSummaryAccess`（Delegate 内 auth 方法委托 Helper）。
7. **导出链路**：
   - `CheckboardRepoAccessService` 门面供 Excel/文件下载使用；
   - `FileDownLoadController` 提交导出任务、文件导出前调用 `assertExportAccess` / `assertExportAccessByRecordKey`；
   - `ExcelReportImpl.getExcelStatus` 增加 `userId` 参数并做同样校验；
   - `ExportDetailRequestDTO` 增加 `userId` 字段供 POST 导出使用。
8. **仓库解析**：优先 `parentTaskId` / `repoBranchInfo` 查 `repo_info`；缺失时用 `RepoInfoCoordinateResolver.resolveByUrl(gitUrl)` 兜底。

## 不做什么

- 不改变需 `projectId` + 菜单 URL 的**项目管理类**接口鉴权方式（仍走 `AuthUtils.checkPermission`）。
- 不调整网关免登录白名单本身，仅在 codecheck 业务层补仓级校验。

## 验收标准

- [x] 免登录访问私有仓看板统计、全量趋势、导出相关接口返回 `4001`
- [x] 已登录无仓读权限返回 `403`
- [x] 公开/开源仓免登录仍可访问
- [x] `CheckboardRepoAccessHelperTest` 覆盖 MR/全量/导出分流等分支
- [x] Controller / Delegate / Excel 相关单测已适配 `userId` 入参
- [x] 编译通过，相关单测通过

## 影响范围

### 业务仓 `openlibing-codecheck`（PR !381，13 files，约 +871 / -290）

| 文件                                                | 操作    | 说明                                                 |
| --------------------------------------------------- | ------- | ---------------------------------------------------- |
| `business/service/CheckboardRepoAccessHelper.java`  | 新增    | 仓可见性 + Feign 读权限                              |
| `business/service/CheckboardRepoAccessService.java` | 新增    | 导出链路门面                                         |
| `business/impl/CheckboardDelegateImpl.java`         | 修改    | 注入 Helper；趋势/详情数/任务详情等入口校验          |
| `business/controller/CheckboardController.java`     | 修改    | `getDetailNum`、`getFullTaskTrend` 增加可选 `userId` |
| `business/controller/FileDownLoadController.java`   | 修改    | 导出任务、状态、文件导出前校验                       |
| `business/delegate/CheckboardDelegate.java`         | 修改    | 接口签名增加 `userId`                                |
| `business/entity/dto/ExportDetailRequestDTO.java`   | 修改    | 新增 `userId`                                        |
| `business/impl/ExcelReportImpl.java`                | 修改    | `getExcelStatus` 鉴权                                |
| 相关 `*Test.java`                                   | 新增/改 | 单测                                                 |

### docs 仓

| 文件                                                                                    | 操作 |
| --------------------------------------------------------------------------------------- | ---- |
| `spec/openlibing-codecheck/task_design/fix-checkboard-repo-visibility-auth/proposal.md` | 新增 |
| `spec/openlibing-codecheck/task_design/fix-checkboard-repo-visibility-auth/design.md`   | 新增 |
| `spec/openlibing-codecheck/task_design/fix-checkboard-repo-visibility-auth/tasks.md`    | 新增 |

## 关联 PR

- https://gitcode.com/openlibing/openlibing-codecheck/pull/381（分支 `fix-checkboard-repo-visibility-auth-2` → `release_20261029_iter2`，已合入）

## 说明

后续 PR !382 在同一 release 上再次调整看板鉴权并**移除**本 PR 新增的 Helper/Service；本 spec 描述 **!381 合入时** 的代码形态。
