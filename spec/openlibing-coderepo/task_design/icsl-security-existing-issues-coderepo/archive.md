# Archive：【openLiBing】ICSL安全送检存量issue整改-coderepo

> 归档日期：2026-11-16
>
> 目标分支：`release_20261116_iter1`
>
> 代码基线：`master`（`ac7ea8c5`）

## 1. 关联 Issue

| 类型          | 链接                                                                                                  |
| ------------- | ----------------------------------------------------------------------------------------------------- |
| FE 需求锚点   | [openlibing/openlibing-codecheck#401](https://gitcode.com/openlibing/openlibing-codecheck/issues/401) |
| 子 Issue #282 | [openlibing/openlibing-coderepo#282](https://gitcode.com/openlibing/openlibing-coderepo/issues/282)   |
| 子 Issue #286 | [openlibing/openlibing-coderepo#286](https://gitcode.com/openlibing/openlibing-coderepo/issues/286)   |
| 子 Issue #287 | [openlibing/openlibing-coderepo#287](https://gitcode.com/openlibing/openlibing-coderepo/issues/287)   |
| 子 Issue #288 | [openlibing/openlibing-coderepo#288](https://gitcode.com/openlibing/openlibing-coderepo/issues/288)   |
| 子 Issue #225 | [openlibing/openlibing-coderepo#225](https://gitcode.com/openlibing/openlibing-coderepo/issues/225)   |
| 设计文档 PR   | [openlibing/openlibing-docs!1327](https://gitcode.com/openlibing/openlibing-docs/merge_requests/1327) |

## 2. 交付清单

| 序号 | 问题                                | 子 Issue | 修复 PR                                                                       | 状态                            |
| ---- | ----------------------------------- | -------- | ----------------------------------------------------------------------------- | ------------------------------- |
| 1    | 三方 API 出站路径段注入（`.`/`..`） | #282     | [!306](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/306) | 已合入 `release_20261116_iter1` |
| 2    | 仓库/分支列表 LIKE 通配符未转义     | #286     | [!309](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/309) | 已合入 `release_20261116_iter1` |
| 3    | GitHub GraphQL 查询字符串拼接       | #287     | [!310](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/310) | 已合入 `release_20261116_iter1` |
| 4    | Webhook 入口仓库坐标未校验          | #288     | [!311](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/311) | 已合入 `release_20261116_iter1` |
| 5    | 生产环境 Swagger 调试端点暴露       | #225     | [!303](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/303) | 已关闭，改配置中心方案闭环      |

补充说明：

- 4 个代码修复同时已合入 `develop_202611_iter1`，便于 BETA 环境提前验证；
- 5 个子 Issue 均已关闭；
- #225 最终未在代码仓保留开关改动，改为在配置中心（Nacos）`application` 配置集统一关闭接口文档，Issue #225 以该方案闭环。

## 3. 验收口径与实际结论

| 验收标准                                               | 结论                                                                                         |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| 4 个代码修复 PR 合入目标分支，对应子 Issue 关闭        | 达成：!306 / !309 / !310 / !311 已合入 `release_20261116_iter1`，#282/#286/#287/#288 已关闭  |
| 路径段/坐标非法时无平台请求、无 MQ 发送（fail-closed） | 达成：公共出口拒绝点段；PrSync / Notify / PrSyncPush 入口非法坐标直接丢弃，单测覆盖          |
| LIKE 普通关键字结果不变，含通配符输入按字面量匹配      | 达成：统一 `SqlLikeUtil` 转义，20 处 LIKE 补 `ESCAPE '\\'`，普通关键字行为不变               |
| GraphQL 请求语句不含外部取值                           | 达成：`reviewThreads` / `resolveReviewThread` 全部走 `variables`，单测断言语句无外部取值     |
| Swagger 调试端点不可达                                 | 方案调整为配置中心统一关闭，部署后需在目标环境实测 `/v3/api-docs`、`/swagger-ui/**` 返回 404 |
| 单测、pre-commit、流水线通过，对外 HTTP 契约无变化     | 达成：各 PR 相关单测全部通过，pre-commit 全部 Passed，流水线 `ci-pipeline-passed`            |

## 4. 验证记录

- **!306**：ApiUrlUtil、SigInfoClient、SigDefaultParamBuilder、TokenPermissionEvaluator、RepoServiceImpl、MergeRequestEventHandler 等单测全部通过（合计 370 例）
- **!309**：`SqlLikeUtilTest`（3 例）+ `RepoServiceImplLikeEscapeTest`（5 例）通过；RepoServiceImpl / Mapper 回归 312 例通过
- **!310**：`MergeRequestEventHandlerGraphqlTest` 3 例通过（变量传参 / endCursor 翻页 / mutation threadId）
- **!311**：`RepoUrlUtilTest`、`PrSyncEventHandlerTest`、`NotifyConfigEventHandlerTest`、`PrSyncPushEventHandlerTest` 等 19 例通过；相关入口回归 325 例通过
- 各 PR pre-commit（Spotless / CheckStyle / SpotBugs / PMD / Gitleaks 等）全部 Passed

## 5. 遗留与待回填

- **#225 部署验收**：配置中心统一关闭后需在目标环境实测调试端点返回 404，并在 Issue #225 补充实测结论；
- **统一入口收敛已落地**：`RepoUrlUtil.isLegalSegment` / `isLegalOwner` 已直接委托 `SigInfoClient`，`WebhookUrlUtil`、`RepoServiceImpl` 复用 `RepoUrlUtil`，路径段白名单为单一实现；
- 其他仓库（codecheck / cicd / sbom 等）的同类存量问题由各自需求跟踪，不在本需求范围。
