# 资源运营看板能力增强 — 前端联调说明

## 1. 改动总览

| 页面/功能                       | 接口                                                              | 前端需要改动                                                                               |
| ------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 资源运营看板热力图/折线图下钻   | `POST /common/detail`                                             | 排队/运行任务请求传选中窗口的 `startTime/endTime`，不再传 `slotTime/slotGranularity`       |
| 流水线运行明细跳转              | `POST /common/detail`，`category=ops-pipeline-run-detail`         | 请求不变；读取记录中的 `repoUrl`、`platform`，结合 `runId` 按现有规则拼接跳转地址          |
| Nightly 看板跳转                | `POST /common/detail`，`category=nightly-dashboard`               | 请求不变；读取记录中的 `repoUrl`、`platform`、`pipelineId` 等字段拼接跳转地址              |
| 运行分析机器列表排序            | `POST /resource-operation/run-analysis`                           | 请求和响应结构不变；直接按后端返回顺序渲染 `allocServers`、`usageServers`                  |
| 项目 PR 平均排队与工程范围过滤  | `POST /common/detail`，`category=ops-project-resource-efficiency` | 新增展示 `prAvgQueueMinutes`；仅查工程能力运营看板范围时，请求增加 `engineeringScope=true` |
| 项目下钻流水线每日排队 P90 趋势 | `POST /common/chart`，`category=ops-pipeline-queue-p90`           | 新增多折线图，沿用平均消耗卡时趋势的筛选条件和 `xAxis + series` 渲染方式                   |
| 流水线分析单任务卡时汇总        | `POST /resource-operation/run-analysis`                           | 请求不变；读取新增顶层 `taskSummaries` 渲染任务汇总表，原两张热力图保持不变                |

## 2. 资源运营看板热力图/折线图下钻

### 2.1 下钻时间窗口

热力图和折线图仍使用原接口获取数据。点击格子或趋势点时：

- 前端根据选中项计算查询窗口，将开始、结束时间分别写入 `startTime/endTime`。
- 热力图下钻从 `servers[rowIndex].ip` 取得机器 IP，作为 `serverIp`；折线图无机器维度时不传。
- 当前行资源池需要限定时，将 `servers[rowIndex].poolId` 放入 `resourcePoolIds`。
- 页面已有的项目、平台等筛选条件继续透传。

### 2.2 下钻接口

排队任务和运行任务均调用：

```http
POST /common/detail
```

通过 `category` 区分：

| 下钻内容 | category                      |
| -------- | ----------------------------- |
| 排队任务 | `ops-npu-slot-queue-detail`   |
| 运行任务 | `ops-npu-slot-running-detail` |

时间及相关请求字段：

| 字段        | 类型   | 是否必传         | 说明                                         |
| ----------- | ------ | ---------------- | -------------------------------------------- |
| `startTime` | String | 是               | 查询窗口开始时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `endTime`   | String | 是               | 查询窗口结束时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `serverIp`  | String | 热力图按格子传入 | 取当前机器行的 `ip`；折线图无机器维度时不传  |

不再传 `slotTime/slotGranularity`。精确窗口使用 `startTime/endTime`，不要用 `startDate/endDate` 代替。

排队任务请求示例：

```json
{
  "category": "ops-npu-slot-queue-detail",
  "startTime": "2026-11-24 10:00:00",
  "endTime": "2026-11-24 11:00:00",
  "serverIp": "10.10.5.21",
  "projectId": 100,
  "resourcePoolIds": [1],
  "page": 1,
  "pageSize": 20
}
```

运行任务只需切换 `category`，其他参数保持一致：

```json
{
  "category": "ops-npu-slot-running-detail",
  "startTime": "2026-11-24 10:00:00",
  "endTime": "2026-11-24 11:00:00",
  "serverIp": "10.10.5.21",
  "projectId": 100,
  "resourcePoolIds": [1],
  "page": 1,
  "pageSize": 20
}
```

### 2.3 交互要求

- 点击 `2026-11-24 10:00` 的小时格子，前端传 `startTime=2026-11-24 10:00:00`、`endTime=2026-11-24 11:00:00`。
- 排队/运行 Tab 切换时保留开始/结束时间、机器和页面筛选条件；分页参数按 Tab 独立维护或重置到第一页。
- 下钻响应结构没有变化，继续使用现有任务列表和申请卡数展示逻辑。

## 3. 流水线运行明细补充跳转信息

### 3.1 接口

```http
POST /common/detail
Content-Type: application/json
```

```json
{
  "category": "ops-pipeline-run-detail",
  "pipelineId": "pipeline-001",
  "pipelineType": "PR",
  "page": 1,
  "pageSize": 20
}
```

请求参数无新增要求，原有 `projectId`、`platform`、时间范围、排序和分页参数继续按现状传递。

### 3.2 记录新增/已有跳转字段

| 字段           | 类型   | 说明                                                 |
| -------------- | ------ | ---------------------------------------------------- |
| `repoUrl`      | String | **本次新增**，仓库地址；不是完整的流水线运行跳转地址 |
| `platform`     | String | 已有字段，平台：`codearts` / `gitcode` / `github`    |
| `runId`        | String | 已有字段，流水线运行 ID                              |
| `pipelineName` | String | 已有字段，流水线名称                                 |

记录字段示例：

```json
{
  "runId": "86231",
  "platform": "gitcode",
  "repoUrl": "https://gitcode.com/openlibing/openlibing-ops.git",
  "pipelineName": "pr-gate-ut",
  "status": "SUCCESS"
}
```

### 3.3 前端处理

- 使用 `repoUrl + platform + runId` 按前端已有的平台跳转规则拼接目标地址。
- `repoUrl` 为空或 `null` 时，不要拼接出无效地址；建议隐藏/禁用跳转入口或沿用现有无仓库信息时的兜底交互。
- 后端不返回完整跳转 URL，前端无需等待额外字段。

## 4. Nightly 看板补充跳转信息

### 4.1 接口

```http
POST /common/detail
Content-Type: application/json
```

```json
{
  "category": "nightly-dashboard",
  "startDate": "2026-11-01",
  "endDate": "2026-11-24",
  "page": 1,
  "pageSize": 20
}
```

请求参数无变化。

### 4.2 记录新增/已有跳转字段

| 字段           | 类型   | 说明                   |
| -------------- | ------ | ---------------------- |
| `repoUrl`      | String | **本次新增**，仓库地址 |
| `platform`     | String | 已有字段，托管平台     |
| `pipelineId`   | String | 已有字段，流水线 ID    |
| `projectId`    | Number | 已有字段，项目 ID      |
| `pipelineName` | String | 已有字段，流水线名称   |

记录字段示例：

```json
{
  "projectId": 100,
  "platform": "gitcode",
  "pipelineId": "pipeline-nightly-001",
  "repoUrl": "https://gitcode.com/openlibing/openlibing-ops.git",
  "pipelineName": "nightly-regression"
}
```

### 4.3 前端处理

- 使用 `repoUrl + platform + pipelineId` 按现有 Nightly 跳转规则拼接目标地址。
- `repoUrl` 为空或 `null` 时按无仓库信息处理，不生成无效链接。
- `repoUrl` 只用于页面跳转，不影响原有导出列。

## 5. 运行分析机器按资源池和 IP 排序

接口不变：

```http
POST /resource-operation/run-analysis
```

请求和响应字段结构均无变化。后端已对以下两个数组统一排序：

- `allocServers`
- `usageServers`

排序规则：

1. 有资源池名称的机器在前，按 `pool` 升序。
2. 同一资源池内按 `ip` 升序。
3. `pool` 为 `null`、空字符串或空白字符串的机器排在最后。

前端直接按接口返回顺序渲染即可，不要再用仅按 IP 的本地排序覆盖后端顺序。`labels`、`values`、`jobs` 等字段结构和含义不变。

顺序示例：

```text
pool-A / 10.10.5.22
pool-B / 10.10.5.21
空资源池 / 10.10.5.23
```

## 6. 项目资源效率新增 PR 平均排队时长与工程范围过滤

### 6.1 接口

```http
POST /common/detail
Content-Type: application/json
```

```json
{
  "category": "ops-project-resource-efficiency",
  "startDate": "2026-11-01",
  "endDate": "2026-11-24",
  "engineeringScope": true,
  "page": 1,
  "pageSize": 20
}
```

本次新增可选请求参数：

| 字段               | 类型    | 是否必传 | 说明                                                                                  |
| ------------------ | ------- | -------- | ------------------------------------------------------------------------------------- |
| `engineeringScope` | Boolean | 否       | 传 `true` 时仅查询工程能力运营看板仓库范围内的数据；不传或传 `false` 时保持原查询范围 |

启用后，项目列表和总数只保留至少包含一个工程能力运营仓的项目，PR 排队与 PR NPU 指标只统计运营仓 run。资源池指标没有仓库维度，仍返回入围项目的项目级资源池指标。`prAvgQueueMinutes` 未新增排序参数。

### 6.2 响应新增字段

| 字段                | 类型        | 单位 | 展示建议                             |
| ------------------- | ----------- | ---- | ------------------------------------ |
| `prAvgQueueMinutes` | Number/null | 分钟 | 列名建议为“PR 资源排队平均时长(min)” |

记录字段示例：

```json
{
  "projectId": 100,
  "projectName": "agent-core",
  "queueP90": 12.6,
  "prAvgQueueMinutes": 8.35
}
```

口径说明：每个 PR run 取其中排队时间最长的 job 作为该 run 的排队样本，再对所有 run 样本求平均，与 `queueP90` 使用相同样本集。

前端展示注意：

- 后端已按分钟返回并保留两位小数，不需要再除以 60。
- 该字段不是百分比，不需要乘以 100。
- 无样本时可能返回 `null`，建议显示 `--`，不要显示 `0`。

## 7. 项目下钻新增流水线每日排队 P90 趋势

### 7.1 接口与请求

在项目下钻页面新增“流水线每日排队时长 P90”趋势图，展示形式与现有“NPU 使用（占用）平均消耗卡时趋势”一致。保留现有“资源申请次数＋每小时总排队时长”双折线，不做替换。

```http
POST /common/chart
Content-Type: application/json
```

```json
{
  "category": "ops-pipeline-queue-p90",
  "projectId": 100,
  "pipelineType": "PR",
  "startDate": "2026-11-01",
  "endDate": "2026-11-24"
}
```

| 字段                    | 类型   | 是否必传 | 说明                                                           |
| ----------------------- | ------ | -------- | -------------------------------------------------------------- |
| `category`              | String | 是       | 固定为 `ops-pipeline-queue-p90`                                |
| `projectId`             | Number | 是       | 当前下钻项目 ID                                                |
| `pipelineType`          | String | 否       | `PR` / `Nightly`，跟随页面页签；不传或空字符串时默认 `Nightly` |
| `startDate` / `endDate` | String | 是       | 查询日期范围，格式 `yyyy-MM-dd`，最长 30 天                    |

### 7.2 响应与展示

```json
{
  "title": "流水线每日排队时长P90",
  "xAxis": ["2026-11-23", "2026-11-24"],
  "series": [
    {
      "name": "全部流水线",
      "data": [12.35, 0.0]
    },
    {
      "name": "pr-gate-ut",
      "data": [6.79, 8.2]
    }
  ]
}
```

- `series[0]` 固定为“全部流水线”，直接由全部 run 样本计算 P90；其余每项为一条流水线折线，按流水线名称排序。
- `data` 与 `xAxis` 按下标一一对应，单位为**分钟**，后端已保留两位小数，前端不需要再除以 60。
- 每个 run 取排队时间最长的 job 作为样本，按该 run 在窗口内最早申请时间归属日期；当日无样本时返回 `0`。
- PR/Nightly 切换时重新请求本接口，项目和时间范围与其他下钻图表保持一致。
- 前端直接按 `xAxis + series` 渲染多折线，不要对各流水线 P90 再次求和或平均。

## 8. 流水线分析新增单任务卡时汇总

### 8.1 接口兼容性

仍调用原接口，请求参数不变：

```http
POST /resource-operation/run-analysis
Content-Type: application/json
```

```json
{
  "runId": "86231",
  "projectId": 100
}
```

响应新增顶层 `taskSummaries`。原 `labels`、`allocServers`、`usageServers` 以及其中的 `jobs[]` 字段和统计口径均不变，现有“NPU 使用（占用）率分析”和“NPU 利用率分析”继续使用原字段渲染。

### 8.2 新增字段

| 字段                        | 类型            | 说明                                              |
| --------------------------- | --------------- | ------------------------------------------------- |
| `taskSummaries`             | Array           | 按任务汇总，每个 `jobId` 仅一条；无任务时为空数组 |
| `taskSummaries[].jobId`     | String          | 任务 ID                                           |
| `taskSummaries[].taskName`  | String          | 任务名称                                          |
| `taskSummaries[].npuHours`  | Number          | 该任务跨所有机器的累计 NPU 卡时，保留两位小数     |
| `taskSummaries[].serverIps` | Array\<String\> | 该任务涉及的机器 IP，去重后升序                   |

新增字段示例：

```json
{
  "taskSummaries": [
    {
      "jobId": "job-001",
      "taskName": "unit-test",
      "npuHours": 1.01,
      "serverIps": ["10.10.5.21", "10.10.5.22"]
    }
  ]
}
```

前端可在两张热力图旁新增“任务卡时消耗”汇总表，建议列为“任务名称、卡时消耗（卡时）、执行机器”。直接使用 `taskSummaries[].npuHours`，不要从两张热力图的 `jobs[]` 重复累加，也不要对单机器卡时四舍五入后再求和。任务名称可能为空，建议显示 `--`。

## 9. 前端自测清单

- [ ] 热力图和折线图可以打开排队/运行任务下钻，请求只传选中窗口的 `startTime/endTime`，不带 `slotTime/slotGranularity`。
- [ ] 下钻的机器、时间窗口、项目、资源池等条件与选中项一致，翻页和 Tab 切换不丢失条件。
- [ ] 排队/运行任务列表与申请卡数使用相同的 `startTime/endTime` 查询窗口。
- [ ] 运行明细能读取 `repoUrl`，并按 `platform`、`runId` 正确跳转；无 `repoUrl` 时无无效链接。
- [ ] Nightly 能读取 `repoUrl`，并按 `platform`、`pipelineId` 正确跳转；无 `repoUrl` 时无无效链接。
- [ ] 运行分析两张热力图均按资源池、IP 顺序展示，空资源池在最后。
- [ ] 项目资源效率展示 `prAvgQueueMinutes`，单位为分钟，`null` 显示为 `--`。
- [ ] 传 `engineeringScope=true` 时项目列表、总数和 PR 指标均限定为工程能力运营看板范围；不传或传 `false` 时结果与原有一致。
- [ ] 项目下钻新增每日排队 P90 多折线图，首条为“全部流水线”，各流水线独立展示，PR/Nightly 和时间筛选联动正确。
- [ ] 排队 P90 按分钟展示，缺样本日期为 `0`，`series.data` 与 `xAxis` 长度一致；原资源申请双折线仍保留。
- [ ] 流水线分析直接展示 `taskSummaries` 的任务名称、跨机器累计卡时和机器列表；同一任务跨机器不重复显示。
- [ ] 原 NPU 使用（占用）率、NPU 利用率热力图及任务状态连线保持原展示和交互，不使用 `taskSummaries` 重算原指标。
