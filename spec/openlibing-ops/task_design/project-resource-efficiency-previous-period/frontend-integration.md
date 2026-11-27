# 项目资源效率环比 — 前端对接文档

## 1. 改动范围

仅 `POST /common/detail` 中 `category = ops-project-resource-efficiency` 这一个请求：

- 请求新增可选开关 `includePreviousPeriod`；
- 响应每条记录新增 `previousPeriod`（上一期窗口 + 上一期原值 + **后端算好的增减值/增减率**）；
- 增减值（`Delta`）、增减率（`ChangeRate`）由后端计算并返回，**前端直接展示，不再自行计算**。

## 2. 请求改动

沿用现有请求，只新增一个参数：

| 字段                    | 类型    | 必填 | 默认    | 说明                                      |
| ----------------------- | ------- | ---- | ------- | ----------------------------------------- |
| `includePreviousPeriod` | boolean | 否   | `false` | `true` 时返回紧邻前一等长自然日周期的数据 |

```json
{
  "category": "ops-project-resource-efficiency",
  "startTime": "2026-11-20 00:00:00",
  "endTime": "2026-11-24 23:59:59",
  "engineeringScope": true,
  "includePreviousPeriod": true,
  "page": 1,
  "pageSize": 20
}
```

- 不传或传 `false`：响应不含上一期数据，`previousPeriod` 为 `null`，接口耗时与现在一致。
- 传 `true`：后端自动按“当前期天数”向前平移得到上一期窗口，前端**不要自己算上一期日期，也不要发第二次请求**。

## 3. 响应改动

每条记录的现有字段含义不变，`previousPeriod` 内包含三类字段：上一期窗口、上一期指标原值、增减值/增减率。

### 3.1 窗口与上一期原值

| 字段                                   | 类型           | 说明                                  |
| -------------------------------------- | -------------- | ------------------------------------- |
| `previousPeriod`                       | object \| null | 上一期数据；未开启环比时为 `null`     |
| `previousPeriod.startTime`             | string         | 上一期起始时间，`yyyy-MM-dd HH:mm:ss` |
| `previousPeriod.endTime`               | string         | 上一期结束时间，`yyyy-MM-dd HH:mm:ss` |
| `previousPeriod.queueP90`              | number \| null | 上一期 PR 排队时长 P90（分钟）        |
| `previousPeriod.prAvgQueueMinutes`     | number \| null | 上一期 PR 平均排队时长（分钟）        |
| `previousPeriod.npuAllocHours`         | number \| null | 上一期 PR NPU 分配（卡时）            |
| `previousPeriod.prAvgUsedHours`        | number \| null | 上一期单次 run 平均消耗（卡时）       |
| `previousPeriod.npuUsageRate`          | number \| null | 上一期 NPU 使用率（%，全部池）        |
| `previousPeriod.npuAllocRate`          | number \| null | 上一期 NPU 分配率（%，全部池）        |
| `previousPeriod.sharedNpuAllocRate`    | number \| null | 上一期共享池分配率（%）               |
| `previousPeriod.exclusiveNpuAllocRate` | number \| null | 上一期独占池分配率（%）               |
| `previousPeriod.sharedNpuUsageRate`    | number \| null | 上一期共享池使用率（%）               |
| `previousPeriod.exclusiveNpuUsageRate` | number \| null | 上一期独占池使用率（%）               |

### 3.2 增减值 / 增减率（后端已计算，前端直接读）

每个指标对应两个字段，命名规则为 `<指标名>Delta`（增减值）和 `<指标名>ChangeRate`（增减率）：

| 指标                  | 增减值字段                                  | 增减率字段                                       |
| --------------------- | ------------------------------------------- | ------------------------------------------------ |
| queueP90              | `previousPeriod.queueP90Delta`              | `previousPeriod.queueP90ChangeRate`              |
| prAvgQueueMinutes     | `previousPeriod.prAvgQueueMinutesDelta`     | `previousPeriod.prAvgQueueMinutesChangeRate`     |
| npuAllocHours         | `previousPeriod.npuAllocHoursDelta`         | `previousPeriod.npuAllocHoursChangeRate`         |
| prAvgUsedHours        | `previousPeriod.prAvgUsedHoursDelta`        | `previousPeriod.prAvgUsedHoursChangeRate`        |
| npuUsageRate          | `previousPeriod.npuUsageRateDelta`          | `previousPeriod.npuUsageRateChangeRate`          |
| npuAllocRate          | `previousPeriod.npuAllocRateDelta`          | `previousPeriod.npuAllocRateChangeRate`          |
| sharedNpuAllocRate    | `previousPeriod.sharedNpuAllocRateDelta`    | `previousPeriod.sharedNpuAllocRateChangeRate`    |
| exclusiveNpuAllocRate | `previousPeriod.exclusiveNpuAllocRateDelta` | `previousPeriod.exclusiveNpuAllocRateChangeRate` |
| sharedNpuUsageRate    | `previousPeriod.sharedNpuUsageRateDelta`    | `previousPeriod.sharedNpuUsageRateChangeRate`    |
| exclusiveNpuUsageRate | `previousPeriod.exclusiveNpuUsageRateDelta` | `previousPeriod.exclusiveNpuUsageRateChangeRate` |

取值约定（均为 `number | null`，保留两位小数）：

- **ChangeRate（增减率）已经是百分比数值**，如 `23.0` 表示 `+23.00%`、`-8.89` 表示 `-8.89%`，前端**不要再乘 100**，只需加正负号和 `%`。
- **Delta（增减值）= 当前期 − 上一期**：6 个百分比指标（`npuUsageRate`、`npuAllocRate`、`sharedNpuAllocRate`、`exclusiveNpuAllocRate`、`sharedNpuUsageRate`、`exclusiveNpuUsageRate`）单位是**百分点（pp）**；其余指标按原单位（分钟 / 卡时）。
- 空值规则（后端已处理，前端只需判 `null`）：
  - 任一期为 `null` → `Delta` 和 `ChangeRate` 都为 `null`；
  - 上一期为 `0` → `Delta` 仍返回（等于当前值），`ChangeRate` 为 `null`；
  - 两期相等 → `Delta = 0`、`ChangeRate = 0`。
- 开启环比但该项目上一期无数据时，`previousPeriod` **不为 `null`**，窗口正常返回，原值与 `Delta`/`ChangeRate` 均为 `null`。前端须区分“未开启”（对象为 null）与“上一期无数据”（字段为 null）。
- 列表顺序、总数、分页仍是当前期结果，前端保持现有排序分页逻辑，不要改动。

响应示例（省略部分字段）：

```json
{
  "code": "0",
  "data": {
    "total": 2,
    "page": 1,
    "pageSize": 20,
    "records": [
      {
        "projectId": 100,
        "projectName": "agent-core",
        "queueP90": 12.3,
        "npuUsageRate": 65.4,
        "npuAllocHours": 120.0,
        "resourcePools": ["共享-Pool-A"],
        "previousPeriod": {
          "startTime": "2026-11-15 00:00:00",
          "endTime": "2026-11-19 23:59:59",
          "queueP90": 10.0,
          "queueP90Delta": 2.3,
          "queueP90ChangeRate": 23.0,
          "npuUsageRate": 60.0,
          "npuUsageRateDelta": 5.4,
          "npuUsageRateChangeRate": 9.0,
          "npuAllocHours": 0,
          "npuAllocHoursDelta": 120.0,
          "npuAllocHoursChangeRate": null
        }
      }
    ]
  }
}
```

## 4. 前端读取方式

- 当前值：读记录原有字段（如 `record.queueP90`）。
- 上一期原值（Tooltip 用）：读 `record.previousPeriod.queueP90`。
- 增减值 / 增减率（趋势展示用）：直接读 `record.previousPeriod.queueP90Delta` / `record.previousPeriod.queueP90ChangeRate`，**无需任何计算**。
- 不要按数组下标对齐当前期与上一期，`previousPeriod` 已挂在同一条记录上。

## 5. 展示格式化

后端只给数值，前端负责文案与正负号。建议两个纯函数统一处理：

```ts
type Nullable = number | null | undefined;

/** 增减率文案：后端已返回百分比数值（23.0 = +23%），null 显示 -- */
export function formatChangeRate(changeRate: Nullable): string {
  if (changeRate == null) return "--";
  const sign = changeRate > 0 ? "+" : "";
  return `${sign}${changeRate.toFixed(2)}%`;
}

/** 增减值文案：isPercent=true 时单位为百分点(pp)，否则按指标原单位 */
export function formatDelta(delta: Nullable, isPercent = false): string {
  if (delta == null) return "--";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(2)}${isPercent ? "pp" : ""}`;
}
```

| 场景                                       | ChangeRate | Delta  | 展示                              |
| ------------------------------------------ | ---------- | ------ | --------------------------------- |
| 两期都有值且上一期 ≠ 0                     | 数值       | 数值   | 当前值 + 增减率                   |
| 上一期 = 0                                 | `null`     | 数值   | 增减率 `--`，Tooltip 可显示增减值 |
| 任一期 `null`（含 previousPeriod 为 null） | `null`     | `null` | `--`，**不能当 0**                |
| 两期相等                                   | `0`        | `0`    | `0.00%`                           |

## 6. 展示建议

- 主展示：当前值 + 增减率（如 `12.30 (+23.00%)`）。
- Tooltip：上一期窗口 `previousPeriod.startTime ~ previousPeriod.endTime`、上一期原值、增减值；百分点指标提示“个百分点”。
- 趋势颜色按指标语义配置，不要只按数值正负统一红绿：排队时长类上升通常是变差，利用率/分配率类上升通常是变好。
- 本期不支持按 `Delta` / `ChangeRate` 排序，排序仍用后端 `sortField`。

计算样例（数值均由后端返回）：

| 指标       | 当前   | 上一期 | Delta   | ChangeRate | 展示               |
| ---------- | ------ | ------ | ------- | ---------- | ------------------ |
| 排队 P90   | 12.30  | 10.00  | +2.30   | 23.00      | `12.30 (+23.00%)`  |
| 平均排队   | 8.20   | 9.00   | -0.80   | -8.89      | `8.20 (-8.89%)`    |
| NPU 使用率 | 65.40  | 60.00  | +5.40pp | 9.00       | `65.40% (+5.40pp)` |
| 分配卡时   | 120.00 | 0      | +120.00 | null       | `120.00 (--)`      |
| 任意指标   | 12.30  | null   | null    | null       | `12.30 (--)`       |

## 7. 注意事项

1. 只在需要环比时传 `includePreviousPeriod=true`；不需要时保持不传，避免多一次查询。
2. 不要为了环比再调一次同接口，也不要前端自己减天数算上一期时间。
3. **不要前端再算 Delta / ChangeRate**，后端已返回；ChangeRate 已是百分比数值，不要再乘 100。
4. 上一期窗口仅供展示，不要用前端选择的时间替换。
5. 全部字段可能为 `null`，格式化函数必须兜底，不能输出 `NaN`、`Infinity`、`undefined`。

## 8. 前端自测清单

- [ ] 不传 `includePreviousPeriod`：页面与改造前完全一致，`previousPeriod` 为 `null` 时不渲染环比。
- [ ] 单日、跨月（2026-11-01～03）、跨年（2026-01-01～02）选择日期，Tooltip 中上一期窗口正确。
- [ ] 切换到第 2 页、切换排序、切换 `engineeringScope` 后，环比仍跟随当前页记录。
- [ ] 上一期为 0（ChangeRate=null）、上一期指标为 null、整个 previousPeriod 为 null 三种情况都显示 `--`。
- [ ] 6 个百分比指标 Delta 按百分点(pp)展示，其余按原单位展示；ChangeRate 直接加 `%`，未重复乘 100。
- [ ] 请求只在当前页数据返回后渲染环比，无第二次网络请求、无 N+1。
