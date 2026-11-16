# Proposal：【openLiBing】ICSL安全送检存量issue整改-coderepo

> 需求 Issue：[openlibing/openlibing-codecheck#401](https://gitcode.com/openlibing/openlibing-codecheck/issues/401)（FE 需求锚点）
>
> 目标分支：`release_20261116_iter1`
>
> 代码基线：`master`（`ac7ea8c5`）
>
> 设计文档：[design.md](./design.md)

## 1. 背景

ICSL 安全送检对 openlibing-coderepo 仓扫描出 5 个存量安全问题，覆盖三类链路：不可信输入进入出站 URL（路径段注入、Webhook 坐标未校验）、不可信输入进入查询语句/查询结构（SQL LIKE 通配符、GitHub GraphQL 字符串拼接）、生产环境调试端点暴露（Swagger）。

本需求对这 5 个问题进行集中整改，在不改变对外 HTTP 接口契约的前提下完成修复、单测覆盖与流水线验证，并为后续同类问题沉淀可复用的统一校验入口。

## 2. 问题清单

| 序号 | 问题                                | 子 Issue                                                              | 风险等级 | 整改方向                                                |
| ---- | ----------------------------------- | --------------------------------------------------------------------- | -------- | ------------------------------------------------------- |
| 1    | 三方 API 出站路径段注入（`.`/`..`） | [#282](https://gitcode.com/openlibing/openlibing-coderepo/issues/282) | 中       | 公共出口拒绝点段 + 各入口坐标白名单                     |
| 2    | 仓库/分支列表 LIKE 通配符未转义     | [#286](https://gitcode.com/openlibing/openlibing-coderepo/issues/286) | 低       | 统一 `SqlLikeUtil` 转义 + Mapper 显式 `ESCAPE`          |
| 3    | GitHub GraphQL 查询字符串拼接       | [#287](https://gitcode.com/openlibing/openlibing-coderepo/issues/287) | 低       | 查询/mutation 固定语句 + `variables`                    |
| 4    | Webhook 入口仓库坐标未校验          | [#288](https://gitcode.com/openlibing/openlibing-coderepo/issues/288) | 低       | 入口 `RepoUrlUtil.isLegalCoordinate` 校验，非法丢弃事件 |
| 5    | 生产环境 Swagger 调试端点暴露       | [#225](https://gitcode.com/openlibing/openlibing-coderepo/issues/225) | 中       | 关闭调试端点（最终调整为配置中心统一关闭，见归档说明）  |

## 3. 范围

**范围内**

- #282：`ApiUrlUtil` 公共出口拒绝 `.`/`..` 路径段；MergeRequest / SIG / token 探测等入口补齐坐标白名单；
- #286：仓库列表、项目分支列表、仓库下拉、分支列表等全部请求驱动的 LIKE 模糊过滤统一转义 `\`/`%`/`_`，Mapper 补 `ESCAPE '\\'`；
- #287：GitHub `reviewThreads` 查询与 `resolveReviewThread` mutation 改为 GraphQL variables；
- #288：PrSync / Notify / PrSyncPush 三个 webhook 入口在出站或下发 MQ 前校验仓库坐标；
- #225：关闭 Swagger 调试端点（最终方案调整为配置中心统一配置，代码仓不保留开关改动）。

**范围外**

- 其他仓库（codecheck / cicd / sbom 等）的存量问题由各自需求跟踪；
- 网关 `/manage` 路由策略调整：属于环境侧配置，作为部署验收项。

## 4. 验收标准

1. 4 个代码修复 PR（!306 / !309 / !310 / !311）合入 `release_20261116_iter1`，对应子 Issue 关闭；
2. 路径段/坐标非法时无平台请求、无 MQ 发送，入口 fail-closed；
3. LIKE 普通关键字查询结果不变，含 `%`/`_` 的输入按字面量匹配；
4. GraphQL 请求语句不包含外部取值，全部走 `variables`；
5. Swagger 调试端点在目标环境不可达（#225 以配置中心统一配置方式闭环，需部署实测 404）；
6. 相关单测、pre-commit 与流水线全部通过，对外 HTTP 契约无变化。
