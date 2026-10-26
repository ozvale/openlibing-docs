# 安全合规评分看板 · 前端开发交接文档

> 版本：v1.0（2026-09-28，接口契约 v1.2 定稿）
> 读者：前端开发同学
> 接口文档（唯一权威入口，自包含）：同目录 [frontend-api.md](frontend-api.md)
> 本文是速览 + 交接要点，**字段级定义一律以 frontend-api.md 为准**；口径争议时备查 [design.md](design.md)。

---

## 1. 接口总览（5 组，全部 POST + JSON）

| #   | 接口           | 路径                                                           | 用途                          |
| --- | -------------- | -------------------------------------------------------------- | ----------------------------- |
| 1   | 社区汇总列表   | `POST /common/detail`（`category=security-community-summary`） | 5 个顶层社区                  |
| 2   | 开源项目清单   | `POST /common/detail`（`category=security-project-list`）      | Ascend 子项目                 |
| 3   | 代码仓清单     | `POST /common/detail`（`category=security-repo-list`）         | 应扫仓库全集（含 NA 行）      |
| 4.1 | 代码仓概要     | `POST /security/repo-summary`                                  | 详情页头部 KPI                |
| 4.2 | 代码仓指标明细 | `POST /security/repo-metric-detail`                            | 18 指标三态清单               |
| 5   | 指标达标明细   | `POST /security/metric-detail`                                 | 指标抽屉（统一展示契约 v1.2） |

- 分页接口（1/2/3）走公共明细接口，`category` 区分；详情接口（4.1/4.2/5）为 security 独立接口。
- 响应统一包装：`{code, messageCn, messageEn, data}`；`code=200` 成功，非 200 按 `messageCn` 提示。
- 分页 `data` 固定为 `{records[], total, page, pageSize}`。

## 2. 页面与交互链路

```
社区汇总 → (仅 Ascend 可下钻) 开源项目清单 → 代码仓清单 → 仓库详情页 → 指标明细抽屉
```

- 顶层统一放**快照日期筛选器**（可选，空 = 最新），全链路下钻透传 `startDate`，日期变化当前层级自动重查。
- 面包屑支持逐级回跳（社区 → 项目 → 仓库清单 → 仓库）。
- 页面原型：`docs/0912/明细数据设计freemarker模版/`（21 个 mi-*.html）。

## 3. 前端最关键的 4 个契约点（易踩坑）

1. **三态判定直接用后端字段**：`score=10` 才 PASS；`0≤score<10` 为 FAIL；`score=null` 且 `status=na/deferred` 为 NA/暂缓。渲染以接口 5 返回的 `indicator.scoreStatus / statusText / level` 为准，**不要前端按分数自己算**。
2. **接口 5 是数据驱动**：`summary / failItems / groups` 的 label、文案、配色规则、跳转链接全部由后端配置表下发，前端只做**哑渲染**（循环 + 按 `level` 上色 + searchText 检索 + href 跳转）。**禁止 v-html，禁止按指标硬编码分支**。改文案/列名/配色是后端配置表操作，与前端无关。
3. **null 语义**：列表接口 NA 行的得分/灯为 null → 显示 "—"/灰灯；接口 5 `data=null` → 抽屉显示空态；空 `groups`、空 `failItems` 均为正常返回，需兜底样式。
4. **`raw` 字段透传但不渲染**，仅联调排查用。

## 4. 联调环境

- 后端已实现并实测通过。本地联调：`https://localhost:8098`（HTTPS 自签证书，建议走 Vite proxy；本地直连**不带** `/openlibing-ops` 网关前缀；beta 及以上环境带前缀）。
- 环境差异与启动方式详见 frontend-api.md 第 9 节「联调注意」。

## 5. 实测数据参考（对拍用）

| 场景          | 仓库/参数                              | 预期                                            |
| ------------- | -------------------------------------- | ----------------------------------------------- |
| 社区汇总      | 默认（不传 startDate）                 | Ascend 红 7.31                                  |
| 快照日筛选    | `startDate=2026-09-01`                 | 全社区灰、得分 "—"（早于首批扫描）              |
| CI_TESTS FAIL | `repoId=401429, metricCode=CI_TESTS`   | FAIL 2.33，30 行 PR 明细 + 失败卡               |
| VULNS FAIL    | `repoId=401281, metricCode=VULNS`      | FAIL，22 条超期漏洞分档统计 + 明细 + issue 链接 |
| 满分指标      | `repoId=401281, metricCode=MAINTAINED` | PASS 10，summary 232/780                        |
| NA 态         | `repoId=401009, metricCode=VULNS`      | NA（DB 无数据）                                 |
| 暂缓态        | `metricCode=PINNED_DEP`                | DEFERRED                                        |

接口 5 完整响应样例见 frontend-api.md 8.2 节。

## 6. 参考实现

`openlibing-ops-web` 仓 `feat-security-score-dashboard` 分支已有完整可跑实现（4 层页面 + 通用指标抽屉 + 快照日期筛选），前端正式开发时可作对拍参考：

```
src/views/dashboard/security-score/
├── security-score-view.vue          # 顶层路由 + 面包屑 + 快照日期筛选 + provide/inject 导航上下文
├── types.ts                         # 契约类型定义
└── components/
    ├── community-summary-page.vue   # 接口 1
    ├── project-list-page.vue        # 接口 2
    ├── repo-list-page.vue           # 接口 3
    ├── repo-detail-page.vue         # 接口 4.1 + 4.2
    ├── metric-detail-drawer.vue     # 接口 5（通用哑渲染抽屉）
    └── repo-summary-cards.vue       # KPI 卡片
src/api/dashboard/security-score.ts  # API 层
```

## 7. 阅读建议

按序通读 frontend-api.md 的四个关键节，其余按需查阅：

1. **2.3 时间入参** —— startDate 快照日语义
2. **2.5 值语义** —— null/三态判定
3. **8.3 契约细节** —— 接口 5 条目结构定稿
4. **9 联调注意** —— 环境差异 + 常见坑
