# Tasks：【openLiBing】ICSL安全送检存量issue整改-coderepo

> 需求 Issue：[openlibing/openlibing-codecheck#401](https://gitcode.com/openlibing/openlibing-codecheck/issues/401)
>
> 目标分支：`release_20261116_iter1`
>
> 状态：全部任务已完成或已闭环（2026-11-16）

## 1. 通用准备

- [x] 核对 5 个问题在 `master` 上的实际状态与影响面，确认修复必要性
- [x] 确认代码基线 `master`（`ac7ea8c5`）与目标分支 `release_20261116_iter1`
- [x] 为每个问题创建独立修复分支与子 Issue，标题统一为「【安全】【参数注入问题】具体问题」
- [x] 5 个 PR 均关联子 Issue 与需求锚点 `openlibing-codecheck#401`

## 2. #282 三方 API 出站路径段注入（!306）

- [x] `ApiUrlUtil` 公共出口拒绝 `.` / `..` 路径段，不再交给 OkHttp 做相对路径规范化
- [x] `MergeRequestEventHandler`、`SigDefaultParamBuilder`、`TokenPermissionEvaluator`、`RepoServiceImpl`（sig 同步 / token 探测）等入口补齐坐标白名单
- [x] `SigInfoClient.isLegalSegment` 统一下沉拒绝 `.` 与 `..`，新增 `isLegalOwner` 兼容嵌套分组
- [x] sig 同步非法坐标计入失败，阻止基于残缺集合的硬删除
- [x] 补充单测（ApiUrlUtil / SigInfoClient / SigDefaultParamBuilder / TokenPermissionEvaluator / RepoServiceImpl）
- [x] PR !306 合入 `release_20261116_iter1`

## 3. #286 LIKE 通配符未转义（!309）

- [x] 新增 `SqlLikeUtil`，统一转义 `\`、`%`、`_`，作为唯一转义入口
- [x] `buildRepoQueryEntity` 对 `repoNameLike` / `repoUrlLike` / `repoOwnerLike` / `platformCreateBy` / `createBy` / `updateBy` 先转义
- [x] 两个 `buildProjectBranchQueryEntity` 重载对 `repoUrlLike` / `branchNameLike` 先转义
- [x] `queryRepoBranchInfo` 的 `branchName`、`getRepoSelect` 的 `repoName` 先转义（含计数查询同口径）
- [x] `RepoCoordinateResolverImpl` 复用 `SqlLikeUtil`，删除重复私有实现
- [x] `RepoInfoMapper` / `RepoBranchInfoMapper` 共 20 处 LIKE 子句补 `ESCAPE '\\'`
- [x] 补充 `SqlLikeUtilTest`、`RepoServiceImplLikeEscapeTest`（覆盖各组装点转义）
- [x] PR !309 合入 `release_20261116_iter1`

## 4. #287 GitHub GraphQL 字符串拼接（!310）

- [x] `reviewThreads` 查询改为固定语句，`owner` / `repo` / `prNumber` / `pageSize` / `after` 走 `variables`
- [x] `resolveReviewThread` mutation 改为固定语句，`threadId` 走 `variables`
- [x] 保留分页游标与最大页数逻辑，首次分页 `after` 为 null
- [x] 新增 `MergeRequestEventHandlerGraphqlTest`（变量传参 / endCursor 翻页 / mutation threadId）
- [x] PR !310 合入 `release_20261116_iter1`

## 5. #288 Webhook 入口坐标未校验（!311）

- [x] 新增 `RepoUrlUtil.isLegalCoordinate` / `isLegalOwner` / `isLegalSegment`，统一路径段白名单
- [x] `PrSyncEventHandler` 在去重与 token 反查前校验坐标，非法记 `[SECURITY]` 并丢弃事件
- [x] `NotifyConfigEventHandler` 在读取 YAML 前校验坐标，非法记 `[SECURITY]` 并丢弃事件
- [x] `PrSyncPushEventHandler` 在构建并下发 MQ 消息前校验坐标，非法记录并丢弃事件
- [x] `WebhookUrlUtil`、`RepoServiceImpl` 收敛为复用 `RepoUrlUtil.isLegalSegment`，`RepoUrlUtil` 最终直接委托 `SigInfoClient`
- [x] 补充 `RepoUrlUtilTest`、`PrSyncEventHandlerTest`、`NotifyConfigEventHandlerTest`、`PrSyncPushEventHandlerTest`
- [x] PR !311 合入 `release_20261116_iter1`

## 6. #225 Swagger 调试端点暴露（!303 关闭，改配置中心闭环）

- [x] 评估代码仓关闭方案（所有环境 `springdoc` 开关置 false），提交 PR !303
- [x] 方案调整：改为在配置中心（Nacos）`application` 配置集统一关闭接口文档，代码仓不保留开关改动
- [x] PR !303 关闭，Issue #225 以配置中心方案闭环
- [x] 部署验收项：目标环境 `/v3/api-docs`、`/swagger-ui/**` 返回 404（环境侧实测）

## 7. 文档与归档

- [x] 编写需求设计文档 `design.md`（7 固定章节）
- [x] SPEC 设计文档归档至 `openlibing-docs`（PR !1327 已合入 `master`）
- [x] 补齐 `proposal.md` / `tasks.md` / `archive.md` / `demo.html` 并归档至同一路径
