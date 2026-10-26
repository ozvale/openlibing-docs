# 安全合规评分看板 · 前端接口文档

> 版本：v1.2（2026-09-28 修订，接口 5 契约定稿 + 配置表驱动架构落地）
> 服务：openlibing-ops（本地联调默认 `https://localhost:8098`）
> 状态：**全部接口已实现并实测通过**（v1.2 起后端为配置表驱动 + 通用渲染引擎，见 8 节）。
> 口径细节见同目录 design.md；本文档自包含，前端无需阅读后端设计。
> v1.2 变更摘要（相对 v1.1，仅接口 5 变更，其余接口不变）：
>
> - **`startDate` 快照日过滤已在 5 组接口全部实测生效**（2026-09-28 修复后端 SQL 误读 `startTime` 的问题，契约本身不变，见 2.3）；空快照日各接口行为差异已补充（2.3 / 7 节 / 8.3）。
> - `indicator` 新增 `maxScore / scoreStatus / statusText / level` 字段：状态判定规则 = **满分(10)才 PASS**，`0≤score<10` 为 FAIL，`score=null + status=na/deferred` 为 NA/DEFERRED。
> - `summary / failItems / groups` 条目结构定稿（见 8.3 契约细节）：`summary` 增 `key/level`；`failItems` 为卡片结构（title/fields/reason/formula/deduct/searchText）；`groups` 为列定义 + 单元格结构（columns/columns[].type/cells/href/searchText）。
> - `raw` 字段保留透传，**前端不渲染**（仅排查用）。
> - 展示内容由 Doris 配置表 `dm_rd_efc_security_metric_detail_conf` 驱动（conf_json mini-DSL），前端为**哑渲染器**：改列名/文案/配色无需发版，UPDATE 配置 + 刷新缓存即可。
>   v1.1 变更摘要：
> - 接口 5 由"返回 HTML 片段 + v-html"改为**统一展示契约 JSON**（indicator/summary/failItems/groups + raw），前端 18 指标复用一个通用组件做数据驱动渲染，**禁止 v-html**。
> - 社区维度改为配置表驱动（`dm_rd_efc_security_community_conf`），接口 1 的 `communityId` 不再等于 project_id，取值见 3 节示例（1001~1005 / 1003）。
> - 接口 4.2 每行新增 `status` 三态字段：`scored`（有分）/ `na`（不适用）/ `deferred`（暂缓）。

---

## 1. 页面与接口映射

| 页面                               | 接口                                             | 说明                                   |
| ---------------------------------- | ------------------------------------------------ | -------------------------------------- |
| 社区汇总                           | 1. 社区汇总列表                                  | 5 个顶层社区；默认排序红→黄→绿         |
| 社区详情 · 开源项目层（仅 Ascend） | 2. 开源项目清单                                  | Ascend 下子社区列表                    |
| 代码仓清单                         | 3. 代码仓清单                                    | 应扫仓库全集，含 NA 行                 |
| 代码仓详情                         | 4.1 代码仓概要（头部 KPI）<br>4.2 代码仓指标明细 | 单仓得分 + 18 指标明细                 |
| 指标明细抽屉                       | 5. 指标达标明细（统一契约）                      | 数据驱动渲染，18 指标复用 1 个通用组件 |

页面跳转链路：`社区汇总 → (仅 Ascend) 开源项目清单 → 代码仓清单 → 代码仓详情 → 指标明细抽屉`。

---

## 2. 统一约定（所有接口）

### 2.1 请求

- 全部为 `POST`，`Content-Type: application/json`。
- 分页列表接口（1/2/3）统一走公共明细接口 `POST /common/detail`，通过 `category` 区分。
- 详情接口（4.1/4.2/5）为独立接口。

### 2.2 响应包装

所有接口统一返回：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {}
}
```

`code = 200` 为成功，非 200 按 `messageCn` 提示。分页接口的 `data` 结构固定为：

```json
{
  "records": [],
  "total": 0,
  "page": 1,
  "pageSize": 10
}
```

### 2.3 时间入参（重要）

| 规则      | 说明                                                                                                                                                                                             |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 字段      | 统一用 `startDate`，格式 `yyyy-MM-dd`（如 `"2026-09-18"`）                                                                                                                                       |
| 语义      | **快照日**："查 09-18" = 展示 09-18 这一天的状态快照，不是"09-18 当天发生的扫描"                                                                                                                 |
| 不传      | 返回表内**最新**数据（默认行为，页面初始加载不传即可）                                                                                                                                           |
| ⚠️ 禁止传 | `endDate` / `startTime` / `endTime` / `isAllDay` 一律不要传（本看板无区间语义，传了无效果但易造成误解）                                                                                          |
| 无数据    | 所查日期无快照/该仓从未扫过 → 相关字段返回 `null`（见 2.5）。各接口差异：1/2/3 行保留仅得分 null；4.1 仓库基础信息保留、得分 null；**4.2 返回空数组 `[]`**；**5 返回 `data = null`**（均已实测） |

### 2.4 分页与排序（仅接口 1/2/3）

| 字段        | 默认值  | 说明                                                                     |
| ----------- | ------- | ------------------------------------------------------------------------ |
| `page`      | 1       | 页码                                                                     |
| `pageSize`  | 10      | 每页条数                                                                 |
| `sortField` | `light` | 可选：`light`（亮灯）/ `scoreRule`（规则项得分）/ `scoreAll`（全部得分） |
| `sortRule`  | `desc`  | 仅允许 `asc` / `desc`（后端校验，传错报"排序规则填写错误"）              |
| 默认排序    | -       | `light DESC, scoreRule DESC`：红(3)→黄(2)→绿(1)→null，同灯色按分数降序   |

### 2.5 值语义（重要）

| 值                                      | 含义                                                                                 | 前端展示                  |
| --------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------- |
| `light = 1`                             | 绿灯                                                                                 | 绿                        |
| `light = 2`                             | 黄灯                                                                                 | 黄                        |
| `light = 3`                             | 红灯                                                                                 | 红                        |
| `light = null`                          | 该日无快照 / 该仓未扫 / 整仓无分                                                     | **置灰**（无灯态）        |
| `score = null` 且 `status = "na"`       | NA（指标不适用：未扫/无 workflow 覆盖等）                                            | **NA**                    |
| `score = null` 且 `status = "deferred"` | 指标暂缓（配置 `status=deferred` 的 3 项：PINNED_DEP / BRANCH_PROTECTION / FUZZING） | **暂缓**（不是 NA）       |
| `score = 0`                             | 有效得分 0 分                                                                        | **正常显示 0**（不是 NA） |

> `status` 字段仅接口 4.2 / 5 返回；列表类接口（1/2/3）无此字段，`score = null` 一律按 NA 展示（社区/项目级不存在暂缓态的单独展示需求）。

得分范围 `0 ~ 10`，DECIMAL 两位小数。亮灯规则（后端算好，仅供前端理解）：得分率 ≥80% 绿、≥50% 黄、<50% 红。

---

## 3. 接口 1 · 社区汇总列表

`POST /common/detail`

### 请求

```json
{
  "category": "security-community-summary",
  "startDate": "2026-09-18",
  "communityName": "",
  "page": 1,
  "pageSize": 10,
  "sortField": "light",
  "sortRule": "desc"
}
```

| 字段                                   | 类型   | 必填 | 说明                              |
| -------------------------------------- | ------ | ---- | --------------------------------- |
| category                               | String | 是   | 固定 `security-community-summary` |
| startDate                              | String | 否   | 快照日，不传 = 最新               |
| communityName                          | String | 否   | 社区名模糊查询（大小写不敏感）    |
| page / pageSize / sortField / sortRule | -      | 否   | 见 2.4                            |

### 响应 `data.records[]`

```json
{
  "records": [
    {
      "communityId": 1003,
      "communityName": "Ascend",
      "hasSubCommunity": 1,
      "light": 3,
      "scoreRule": 6.3,
      "scoreAll": 5.9,
      "repoCount": 59,
      "nullRepoCount": 2
    },
    {
      "communityId": 1001,
      "communityName": "openEuler",
      "hasSubCommunity": 0,
      "light": null,
      "scoreRule": null,
      "scoreAll": null,
      "repoCount": 0,
      "nullRepoCount": 0
    }
  ],
  "total": 5,
  "page": 1,
  "pageSize": 10
}
```

| 字段            | 类型       | 说明                                                                                                  |
| --------------- | ---------- | ----------------------------------------------------------------------------------------------------- |
| communityId     | Integer    | 社区 ID（配置表 `community_id`，1001~~1005 顶层 / 1010~~1017 Ascend 子层），**下钻接口 2/3 传这个值** |
| communityName   | String     | 社区展示名                                                                                            |
| hasSubCommunity | Integer    | 1=有子社区（仅 Ascend，行可下钻到接口 2）                                                             |
| light           | Integer    | 1/2/3，null=无快照置灰                                                                                |
| scoreRule       | BigDecimal | 规则项得分（0-10），看板主分数                                                                        |
| scoreAll        | BigDecimal | 全部得分（仅展示备用）                                                                                |
| repoCount       | Integer    | 应扫仓库数（含无分仓），页脚"仓库合计"用                                                              |
| nullRepoCount   | Integer    | 其中无分仓数                                                                                          |

> 社区 = 配置表顶层节点。Ascend 分数为其子项目按有分仓数加权汇总，亮灯取子项目最差灯；openEuler/openGauss 当前无仓库数据，返回 null 行（置灰）属预期。

---

## 4. 接口 2 · 开源项目清单（仅 Ascend）

`POST /common/detail`

### 请求

```json
{
  "category": "security-project-list",
  "communityId": 1003,
  "startDate": "2026-09-18",
  "projectName": "",
  "page": 1,
  "pageSize": 10
}
```

| 字段        | 类型    | 必填 | 说明                                                              |
| ----------- | ------- | ---- | ----------------------------------------------------------------- |
| category    | String  | 是   | 固定 `security-project-list`                                      |
| communityId | Integer | 是   | 父社区 ID，取接口 1 的 `communityId`（当前仅 Ascend=1003 有此层） |
| startDate   | String  | 否   | 同上                                                              |
| projectName | String  | 否   | 项目名模糊查询                                                    |

### 响应 `data.records[]`

```json
{
  "records": [
    {
      "communityId": 1010,
      "projectId": 300033,
      "projectName": "CANN",
      "light": 3,
      "scoreRule": 7.75,
      "scoreAll": 7.4,
      "repoCount": 59,
      "nullRepoCount": 0
    }
  ],
  "total": 8,
  "page": 1,
  "pageSize": 10
}
```

| 字段        | 类型    | 说明                                                     |
| ----------- | ------- | -------------------------------------------------------- |
| communityId | Integer | 子社区配置 ID（1010~1017）                               |
| projectId   | Integer | 关联项目 ID，**下钻接口 3 传这个值**（`projectId` 筛选） |
| projectName | String  | 子社区展示名                                             |
| 其余字段    | -       | 同接口 1（无 hasSubCommunity）                           |

---

## 5. 接口 3 · 代码仓清单

`POST /common/detail`

### 请求

```json
{
  "category": "security-repo-list",
  "startDate": "2026-09-18",
  "communityId": 1003,
  "repoName": "",
  "light": null,
  "page": 1,
  "pageSize": 10,
  "sortField": "light",
  "sortRule": "desc"
}
```

| 字段                 | 类型    | 必填   | 说明                                                                         |
| -------------------- | ------- | ------ | ---------------------------------------------------------------------------- |
| category             | String  | 是     | 固定 `security-repo-list`                                                    |
| startDate            | String  | 否     | 快照日。注意：每仓展示其 ≤ 该日**最近一次**扫描结果（scanTime 各仓不同）     |
| communityId          | Integer | 二选一 | 社区筛选（接口 1 的 communityId；传 Ascend=1003 时自动包含其全部子社区仓库） |
| projectId            | Integer | 二选一 | 项目筛选（接口 2 的 projectId）                                              |
| repoName             | String  | 否     | 仓库名/URL 模糊查询                                                          |
| light                | Integer | 否     | 亮灯筛选：1/2/3，不传=全部                                                   |
| sortField / sortRule | -       | 否     | `light` / `scoreRule` / `scoreAll`，默认 `light desc`                        |
| page / pageSize      | -       | 否     | 分页                                                                         |

### 响应 `data.records[]`

```json
{
  "records": [
    {
      "repoId": 100234,
      "repoName": "MindIE-LLM",
      "repoUrl": "https://gitcode.com/ascend/MindIE-LLM",
      "scoreRule": 5.5,
      "scoreAll": 5.2,
      "light": 3,
      "scanTime": "2026-09-18 02:00:00"
    },
    {
      "repoId": 100235,
      "repoName": "xxx-repo",
      "repoUrl": "https://gitcode.com/xxx/xxx-repo",
      "scoreRule": null,
      "scoreAll": null,
      "light": null,
      "scanTime": null
    }
  ],
  "total": 44,
  "page": 1,
  "pageSize": 10
}
```

| 字段               | 类型       | 说明                                                                                                                  |
| ------------------ | ---------- | --------------------------------------------------------------------------------------------------------------------- |
| repoId             | Long       | 仓库 ID，**下钻接口 4.1/4.2/5 传这个值**                                                                              |
| repoName / repoUrl | String     | 仓库基础信息                                                                                                          |
| scoreRule          | BigDecimal | 规则项得分；null=未扫/无分 → 显示 NA                                                                                  |
| scoreAll           | BigDecimal | 全部得分；null 同上                                                                                                   |
| light              | Integer    | 1/2/3；null → 置灰                                                                                                    |
| scanTime           | String     | 该仓实际批次时间 `yyyy-MM-dd HH:mm:ss`（**各仓不同**，如 09-18 查询时有的仓显示 09-10，属正常——展示该仓最近一次 run） |

> 清单为**应扫全集**：当天没扫到 / 从未扫过的仓库也会以 null 行出现，用于与社区层 `repoCount` 数字对账。

---

## 6. 接口 4.1 · 代码仓概要（详情页头部 KPI）

`POST /security/repo-summary`

### 请求

```json
{
  "repoId": 100234,
  "startDate": "2026-09-18"
}
```

| 字段      | 类型   | 必填 | 说明                |
| --------- | ------ | ---- | ------------------- |
| repoId    | Long   | 是   | 取接口 3 的 repoId  |
| startDate | String | 否   | 不传 = 该仓最新一次 |

### 响应 `data`（单对象）

```json
{
  "repoId": 100234,
  "repoName": "MindIE-LLM",
  "repoUrl": "https://gitcode.com/ascend/MindIE-LLM",
  "scoreRule": 5.5,
  "scoreAll": 5.2,
  "light": 3,
  "scanTime": "2026-09-18 02:00:00"
}
```

字段含义同接口 3 单行。该仓所查日期无扫描记录时 `data` 中得分/亮灯/scanTime 为 null（仓库基础信息仍有值）。

---

## 7. 接口 4.2 · 代码仓指标明细

`POST /security/repo-metric-detail`

### 请求

```json
{
  "repoId": 100234,
  "startDate": "2026-09-18",
  "metricType": null
}
```

| 字段       | 类型   | 必填 | 说明                                                    |
| ---------- | ------ | ---- | ------------------------------------------------------- |
| repoId     | Long   | 是   |                                                         |
| startDate  | String | 否   | 不传 = 该仓最新一次                                     |
| metricType | String | 否   | 筛选：`rule`（规则类）/ `advice`（建议类），不传 = 全部 |

### 响应 `data`（数组，18 行，按配置顺序）

```json
[
  {
    "metricCode": "VULNS",
    "metricName": "已知漏洞",
    "metricType": "rule",
    "weight": 7.5,
    "score": 0.0,
    "status": "scored",
    "scanTime": "2026-09-18 02:00:00",
    "contribution": null
  },
  {
    "metricCode": "BRANCH_PROTECTION",
    "metricName": "分支保护",
    "metricType": "rule",
    "weight": 3.0,
    "score": null,
    "status": "deferred",
    "scanTime": "2026-09-18 02:00:00",
    "contribution": null
  }
]
```

| 字段         | 类型       | 说明                                                                                                  |
| ------------ | ---------- | ----------------------------------------------------------------------------------------------------- |
| metricCode   | String     | 指标码（以 metric_conf 配置 18 项为准），**下钻接口 5 传这个值**                                      |
| metricName   | String     | 指标中文名                                                                                            |
| metricType   | String     | `rule` 规则类 / `advice` 建议类（前端可分组展示）                                                     |
| weight       | BigDecimal | 该指标权重                                                                                            |
| score        | BigDecimal | 得分；null 时看 `status` 区分 NA / 暂缓                                                               |
| status       | String     | `scored` 有分 / `na` 不适用（未扫/无覆盖，NA 不参与该仓得分计算）/ `deferred` 暂缓（配置暂缓的 3 项） |
| scanTime     | String     | 该仓批次时间（同一批次的行值相同）                                                                    |
| contribution | BigDecimal | 对满分贡献，**计算逻辑后置，本期恒 null**，前端可先不展示或占位                                       |

> 该仓所查日期**无扫描记录**时（含传了无快照的 `startDate`）返回空数组 `[]`，前端按空清单渲染（不渲染 18 行占位）。

---

## 8. 接口 5 · 指标达标明细（统一展示契约 v1.2，抽屉）

`POST /security/metric-detail`

### 8.1 请求

```json
{
  "metricCode": "VULNS",
  "repoId": 100234,
  "startDate": "2026-09-18"
}
```

| 字段       | 类型   | 必填 | 说明                     |
| ---------- | ------ | ---- | ------------------------ |
| metricCode | String | 是   | 取接口 4.2 的 metricCode |
| repoId     | Long   | 是   |                          |
| startDate  | String | 否   | 不传 = 该仓最新一次      |

### 8.2 响应 `data`（单对象，统一展示契约 v1.2 实测样例）

```json
{
  "indicator": {
    "metricCode": "CI_TESTS",
    "metricName": "CI测试",
    "metricType": "rule",
    "weight": 2.5,
    "maxScore": 10,
    "score": 2.33,
    "status": "scored",
    "scoreStatus": "FAIL",
    "statusText": "不满足",
    "level": "error",
    "naReason": null,
    "scanTime": "2026-09-27 15:56:56"
  },
  "repo": {
    "repoId": 401429,
    "repoName": "xxx-repo",
    "repoUrl": "https://gitcode.com/xxx/xxx-repo"
  },
  "summary": [
    { "key": "total", "label": "纳入统计 PR", "value": "30", "level": null },
    { "key": "ci", "label": "已跑 CI", "value": "7", "level": "success" },
    { "key": "noci", "label": "未跑 CI", "value": "23", "level": "error" }
  ],
  "failNote": "未达标原因说明文案（FAIL 时非空，PASS/NA 为空串）",
  "failItems": [
    {
      "title": "PR #157 未跑 CI",
      "fields": [
        { "label": "PR", "value": "#157", "level": null },
        { "label": "CI 状态", "value": "未跑 CI", "level": "error" }
      ],
      "reason": "未满足：PR #157 已合入但未匹配到流水线执行记录",
      "formula": "—",
      "deduct": "—",
      "searchText": "157 未跑 CI"
    }
  ],
  "groups": [
    {
      "key": "pr",
      "label": "PR 明细",
      "columns": [
        { "key": "num", "label": "PR", "type": "text" },
        { "key": "ci", "label": "CI 状态", "type": "text" }
      ],
      "rows": [
        {
          "cells": [
            { "text": "#157" },
            { "text": "未跑 CI", "level": "error" }
          ],
          "level": null,
          "searchText": "157"
        }
      ]
    }
  ],
  "raw": { "（该指标 dwi 表 detail_json 原文透传，前端不渲染）": "..." }
}
```

### 8.3 契约细节（v1.2 定稿）

**indicator（指标头，抽屉顶部）**：

| 字段                                          | 类型       | 说明                                                                                              |
| --------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------- |
| metricCode / metricName / metricType / weight | -          | 同接口 4.2                                                                                        |
| maxScore                                      | Integer    | 恒为 10，前端进度条分母用                                                                         |
| score                                         | BigDecimal | 得分，null 时为 NA/DEFERRED 态                                                                    |
| status                                        | String     | 数据态：`scored` / `na` / `deferred`（同接口 4.2）                                                |
| scoreStatus                                   | String     | **展示判定态（前端以这个为准）**：`PASS` 满分达标 / `FAIL` 未达标 / `NA` 不适用 / `DEFERRED` 暂缓 |
| statusText                                    | String     | scoreStatus 对应中文：`满足` / `不满足` / `不适用` / `暂缓`                                       |
| level                                         | String     | 配色：`success`（PASS）/ `error`（FAIL）/ `na`（NA/DEFERRED）                                     |
| naReason                                      | String     | NA/DEFERRED 时的原因文案（如"该仓库本期未扫描"），可能为 null                                     |
| scanTime                                      | String     | 该仓批次时间                                                                                      |

> 判定规则（后端算好，前端直接用 scoreStatus）：**score=10 → PASS**；0≤score<10 → FAIL；score=null+status=na → NA；score=null+status=deferred → DEFERRED。

**summary（摘要条目数组）**：

| 字段  | 类型   | 说明                                                                         |
| ----- | ------ | ---------------------------------------------------------------------------- |
| key   | String | 条目键（可 null，仅标识用）                                                  |
| label | String | 文案（如"已跑 CI"），**由后端配置驱动，不同指标不同**，前端不感知内容        |
| value | String | 预格式化字符串（如 `"7"`、`"80%"`、`"232"`），**直接展示，前端不做数值加工** |
| level | String | 配色：`success` / `warning` / `error` / null（默认色）                       |

**failItems（未达标卡片数组）**：

| 字段       | 类型   | 说明                                                            |
| ---------- | ------ | --------------------------------------------------------------- |
| title      | String | 卡片标题（如"高危漏洞 4 个"、"PR #157 未跑 CI"）                |
| fields     | Array  | 卡片内键值对，每项 `{label, value, level}`，结构同 summary 条目 |
| reason     | String | 未满足原因文案（"未满足：……"）                                  |
| formula    | String | 计分公式说明，`"—"` 为无                                        |
| deduct     | String | 扣分值（如 `"-20"`），`"—"` 为无                                |
| searchText | String | 搜索匹配串（后端拼好小写），前端搜索框对它做包含匹配            |

**groups（分组明细数组，每组一张表格）**：

| 字段                 | 类型   | 说明                                                                                                     |
| -------------------- | ------ | -------------------------------------------------------------------------------------------------------- |
| key                  | String | 组键                                                                                                     |
| label                | String | 组标题（表格上方文案 / tab 名）                                                                          |
| columns              | Array  | 列定义：`{key, label, type}`，`type`: `text` / `number`（number 列前端可按数值排序）                     |
| rows[].cells         | Array  | 单元格数组，与 columns 一一对应：`{text, level?, href?, hrefText?}`                                      |
| rows[].cells[].text  | String | 单元格文本（预格式化，如 `"2025-06-24 15:17:13"`、`"—"`）                                                |
| rows[].cells[].level | String | 单元格配色：`success` / `warning` / `error` / 缺省                                                       |
| rows[].cells[].href  | String | GitCode 链接（**后端白名单校验过的 https://gitcode.com/ 域**），有值时该单元格渲染为超链接，缺省则纯文本 |
| rows[].level         | String | 整行配色（行级告警），缺省为 null                                                                        |
| rows[].searchText    | String | 行搜索匹配串（后端拼好小写），前端搜索框对它做包含匹配并高亮                                             |

**空态语义**：

| 场景                                 | 表现                                                           | 前端处理                                         |
| ------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------ |
| `data = null`                        | 该仓该指标所查日期**无任何数据**（如传了无快照的 `startDate`） | 抽屉整体空态                                     |
| `groups = []`                        | 该指标无逐条明细数据                                           | 显示占位提示（如"该指标无逐条数据"），不显示表格 |
| `failItems = []` 且 scoreStatus=FAIL | 无独立失败卡（失败信息在 failNote / 表格中）                   | 正常，不额外处理                                 |
| scoreStatus=NA / DEFERRED            | summary/failItems/groups 可能为空                              | 展示 naReason 文案 + 空态                        |
| `raw`                                | 始终透传                                                       | **前端不渲染此字段**（仅接口排查用）             |

### 8.4 配置表驱动机制（前端须知）

- 展示内容（summary 文案、列名、失败卡、配色规则、href 模板）由 Doris 配置表 `dm_rd_efc_security_metric_detail_conf` 的 `conf_json`（mini-DSL）驱动，后端通用引擎（MetricDetailConfigEngine）渲染，**前端是哑渲染器**——循环渲染契约字段即可，不感知任何指标特有逻辑。
- 配置修改（列名/文案/配色/扣分单价）走 `UPDATE` 配置表 + 缓存刷新（5 分钟 TTL），**无需发版、前端无需改动**。
- 渲染顺序固定：`indicator → summary → failNote → failItems → groups`，**禁止 v-html**。

---

## 9. 联调注意

1. **后端接口已全部实现并实测通过（v1.2）**，重点验证态覆盖——
   - `score = null + status=na → NA`、`score = null + status=deferred → 暂缓`、`score = 0 → 正常 0`、`light = null → 置灰` 四态；
   - 不传 `startDate`（默认最新）与传历史日期两种入口；
   - 接口 3 的 `scanTime` 各仓不一致的场景（列表中混排不同批次时间）；
   - 接口 5 的空态：`summary/failItems/groups` 为空数组时的渲染，以及 `scoreStatus=NA` 时展示 `naReason`。
2. **传参纪律**：时间只传 `startDate`；`sortRule` 只传 `asc/desc`（有后端校验）；`category` 必传且值区分大小写，按本文档原样传。
3. **下钻链路的 ID 传递**：`communityId`（接口1）→ `projectId`（接口2）/`communityId`（接口3）→ `repoId`（接口3）→ `repoId+metricCode`（接口4.2 → 接口5）。ID 全部来自上游响应，前端不要自行拼接。
4. 分页响应的 `total` 为筛选后的总数；接口 1/2 数据量很小（5/4 行），分页参数可默认传 1/10 即可。
5. 字段名均为 camelCase，与后端实体一致；本文档若有与实际联调不一致处，以 design.md 口径为准并及时反馈后端修正。
6. **接口 5 的 `value/text` 均为后端预格式化字符串**（含 `%`、`—`、日期等），前端直接展示，不要二次加工；配色一律用 `level` 字段，不要前端自行判断数值大小。
7. **搜索与排序**：行搜索用 `rows[].searchText` / 卡片搜索用 `failItems[].searchText`（后端拼好的小写串），前端做小写包含匹配；数值排序仅对 `columns[].type = "number"` 的列生效。
