# 质量管理——关键问题统计 前端对接文档

> 服务：openlibing-platform-release
> 版本：v2（2026-11-26，新增需求交付率/病毒扫描/验签字段，明细改为按制品包分组，缓存 2 分钟）
> 通用说明：所有接口均为 `POST`，`Content-Type: application/json`；`userId`、`projectId` 通过 URL Query 传递（与其他业务接口一致）；响应统一为 `DataResult` 包装。

## 通用响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

| 字段    | 类型         | 说明                                      |
| ------- | ------------ | ----------------------------------------- |
| code    | int          | 200 成功；非 200 失败，message 为错误提示 |
| message | string       | 提示信息                                  |
| data    | array/object | 业务数据                                  |

---

## 1. 查询关键问题统计（列表数字展示）

发起评审后，前端用 `reviewId` 轮询/加载本接口，展示各代码仓的【缺陷关键问题数】【资料关键问题数】。达标判定：两个指标均为 0。

### 请求

```
POST /quality/queryCriticalIssuesSummary?userId={userId}&projectId={projectId}&reviewId={reviewId}
```

**Query 参数**

| 参数      | 类型   | 必填 | 说明        |
| --------- | ------ | ---- | ----------- |
| userId    | string | 是   | 当前用户 id |
| projectId | string | 是   | 项目 id     |
| reviewId  | int    | 是   | 评审单 id   |

**请求示例**（无请求体）

```bash
POST /quality/queryCriticalIssuesSummary?userId=zhangsan&projectId=p001&reviewId=123
```

### 响应

**data 元素字段**

| 字段                    | 类型   | 说明                                                                                                          |
| ----------------------- | ------ | ------------------------------------------------------------------------------------------------------------- |
| repoUrl                 | string | 代码仓地址                                                                                                    |
| repoName                | string | 仓库名称                                                                                                      |
| artifactName            | string | 制品包名称（制品包1、制品包2……按评审单内顺序编号）                                                            |
| defectCriticalCount     | int    | 缺陷关键问题数（未关闭 P0 缺陷类 issue 数量）                                                                 |
| docCriticalCount        | int    | 资料关键问题数（未关闭 P0 资料类 issue 数量）                                                                 |
| requirementDeliveryRate | int    | 需求交付率（百分比整数，100 表示全部需求已关闭）；评审单无制品信息时为 -1；有制品但需求 issue 总数为 0 时为 0 |
| virusScanStatus         | int    | 病毒扫描状态（随汇总接口透出）                                                                                |
| verifyResult            | string | 验签结果（随汇总接口透出）                                                                                    |
| countedAt               | string | 统计时间（ISO 格式，如 `2026-11-20T10:30:00`）                                                                |
| cacheExpireAt           | string | 缓存过期时间；缓存 2 分钟，过期后下次查询自动重算                                                             |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "repoUrl": "https://gitcode.com/openlibing/openlibing-anti-poison",
      "repoName": "openlibing-anti-poison",
      "artifactName": "制品包1",
      "defectCriticalCount": 1,
      "docCriticalCount": 0,
      "requirementDeliveryRate": 80,
      "virusScanStatus": 1,
      "verifyResult": "success",
      "countedAt": "2026-11-20T10:30:00",
      "cacheExpireAt": "2026-11-20T10:32:00"
    },
    {
      "repoUrl": "https://gitcode.com/openlibing/openlibing-platform-release",
      "repoName": "openlibing-platform-release",
      "artifactName": "制品包2",
      "defectCriticalCount": 0,
      "docCriticalCount": 0,
      "requirementDeliveryRate": 100,
      "virusScanStatus": 1,
      "verifyResult": "success",
      "countedAt": "2026-11-20T10:30:00",
      "cacheExpireAt": "2026-11-20T10:32:00"
    }
  ]
}
```

### 展示建议

- 每行展示：制品包名 + 仓库名 + 缺陷/资料数字 + 需求交付率（百分比展示，如 80%）+ 病毒扫描/验签结果。
- 数字大于 0 时标红（未达标），两个数字均为 0 且交付率 100% 标绿（达标）。
- 交付率为 -1 时展示"—"（无制品信息）；为 0 时展示 0%。
- 数字可点击 → 调接口 2 查明细。
- 统计在发起评审时后台异步触发，首次可能存在少量延迟（GitCode 拉取完成前查询返回的数字可能为 0）；可依据 `countedAt` 为空判断尚未完成统计。

---

## 2. 查询关键问题明细（点击数字展开）

点击统计数字后调用，返回该代码仓对应指标下的 issue 名称与链接列表。

### 请求

```
POST /quality/queryCriticalIssuesDetail?userId={userId}&projectId={projectId}
```

**Query 参数**

| 参数      | 类型   | 必填 | 说明        |
| --------- | ------ | ---- | ----------- |
| userId    | string | 是   | 当前用户 id |
| projectId | string | 是   | 项目 id     |

**Body 参数**

| 参数       | 类型   | 必填 | 说明                                                    |
| ---------- | ------ | ---- | ------------------------------------------------------- |
| reviewId   | int    | 是   | 评审单 id                                               |
| repoUrl    | string | 是   | 代码仓地址（必须属于该评审单，取接口 1 返回的 repoUrl） |
| metricType | string | 是   | 指标类型：`defect`=缺陷关键问题；`doc`=资料关键问题     |

**请求示例**

```bash
POST /quality/queryCriticalIssuesDetail?userId=zhangsan&projectId=p001
Content-Type: application/json

{
  "reviewId": 123,
  "repoUrl": "https://gitcode.com/openlibing/openlibing-anti-poison",
  "metricType": "defect"
}
```

### 响应

**data 元素字段**（按制品包分组，v2）

| 字段         | 类型   | 说明                                          |
| ------------ | ------ | --------------------------------------------- |
| artifactName | string | 制品包名称                                    |
| repoUrl      | string | 代码仓地址                                    |
| repoName     | string | 仓库名称                                      |
| issues       | array  | 该制品该仓该指标下的 issue 列表，元素字段如下 |

**issues 元素字段**

| 字段       | 类型     | 说明                                    |
| ---------- | -------- | --------------------------------------- |
| issueTitle | string   | issue 名称                              |
| issueUrl   | string   | issue 链接（可直接跳转 GitCode）        |
| priority   | string   | 优先级（致命/严重 等；取不到时为 null） |
| labels     | string[] | 标签列表                                |
| state      | string   | 状态                                    |
| repoUrl    | string   | 所属代码仓地址                          |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "artifactName": "制品包1",
      "repoUrl": "https://gitcode.com/openlibing/openlibing-anti-poison",
      "repoName": "openlibing-anti-poison",
      "issues": [
        {
          "issueTitle": "[缺陷]: 邮件外部参数未校验导致发送失败",
          "issueUrl": "https://gitcode.com/openlibing/openlibing-platform-release/issues/131",
          "priority": "严重",
          "labels": ["bug"],
          "state": "open",
          "repoUrl": "https://gitcode.com/openlibing/openlibing-anti-poison"
        }
      ]
    }
  ]
}
```

### 展示建议

- 弹窗/抽屉展示：issue 名称超链接 + 优先级 + 标签。
- 顶层 `data` 为空数组，或分组内 `issues` 为空数组表示无关键问题（数字与明细一致）。

---

## 错误场景

| 场景                         | 响应                                                   |
| ---------------------------- | ------------------------------------------------------ |
| 评审单不存在或不属于当前项目 | `code != 200`，message：`评审单不存在或不属于当前项目` |
| repoUrl 不属于该评审单       | `code != 200`，message：`代码仓不属于该评审单`         |
| metricType 非法              | `code != 200`，message：`指标类型仅支持defect或doc`    |
| 用户无项目权限               | 由 `@ProjectPermission` 拦截返回权限错误               |
| GitCode 查询异常             | 对应仓计数返回 0（不报错），可重试或等缓存过期重算     |

## 统计口径（后端逻辑，供前端理解展示）

| 指标           | 口径                                                                                                                                                                 |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 缺陷关键问题数 | issue 类型或 label 为 bug/缺陷，且优先级为 致命/严重（P0），且状态为 open                                                                                            |
| 资料关键问题数 | issue 类型为 资料，且优先级为 致命/严重（P0），且状态为 open                                                                                                         |
| 需求交付率     | issue 全量拉取（state=all）；需求类 = 类型或 label 命中 需求/requirement；交付率 = 已关闭需求 / 全部需求 × 100（百分比整数）；无制品信息返回 -1；需求总数为 0 返回 0 |
| 缓存           | Redis 评审单维度 2 分钟；发起评审时自动触发首次统计                                                                                                                  |
