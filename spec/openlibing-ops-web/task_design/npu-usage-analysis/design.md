# Design — npu-usage-analysis

## 总体方案

路由 `/dashboard/npu-resource` 挂载页签容器 `npu-dashboard-view.vue`（`base-tabs` + `KeepAlive`，激活页签用 `useLocalStorage` 持久化）。tab1「资源总览」为原 `npu-resource-view.vue` 内容（原样保留）；tab2「使用率分析」挂载 `usage-analysis/usage-analysis-view.vue` 容器。

v2 页面所有组件放在 `src/views/dashboard/npu-resource/usage-analysis/`（页面级组件规范）；图表统一走项目 `ChartsUI` + `useCharts`（ECharts），页签 / 抽屉 / 表格用 Element Plus 与既有公共组件（`base-tabs`、`base-table`、`base-select-filter`）。

## 关键决策

| #   | 决策                                                                                                                                                  | 理由                                                                                             |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | 数据流：容器 `usage-analysis-view.vue` 持有 `usageFilter` 单一状态，props 下发、emit 上抛（`open-slot` / `open-daily`）                               | 容器持状态 + 子组件自请求；状态集中可直观、可测试                                                |
| 2   | 时间筛选（`time-range.ts` 纯函数）：`el-date-picker type="datetimerange"` 小时粒度（隐藏分钟列）、跨度钳制 1~72h、不含当天                            | 接口窗口上限 72h、后端 5 分钟桶粒度；小时粒度满足分析需求且避免分钟误选                          |
| 3   | 热力图用 ECharts heatmap（复用 `npu-resource/utils.ts` 的 `getHeatmapOption` / `getHeatmapInitialZoom`），仅暴露 IP 筛选（`visible-levels="['ip']"`） | 与既有热力图同栈同风格；接口按机器×切片返回；dataZoom 横向滚动 + 鼠标滚轮缩放                    |
| 4   | 使用率颜色分级用 `heatLevelForPct` + `HEAT_COLORS`（标准 7 档色阶），不用 5 档                                                                        | 与既有 NPU 看板统一口径；进度条最低档从 `heat-1` 起（0% 不渲染深色）                             |
| 5   | 每日区块日期固定最近 7 日，仅项目 / 资源池跟随全局筛选                                                                                                | 设计稿明确「最近 7 日」副文案；减少无效请求                                                      |
| 6   | 任务明细抽屉按资源池分组展示（接口 `getCommonDetail` 返回 `NpuSlotDetailGroup[]`），表格无分页（组内平铺）                                            | 接口按资源池分组返回；组内条数有限无需分页                                                       |
| 7   | 每日汇总抽屉两级展示平台 → 流水线；流水线「任务数」可再下钻任务明细抽屉（`dayParams` 传 `startDate/endDate/pipelineId`）                              | 接口只到流水线级，无任务级明细；按日期 + 流水线下钻任务明细闭环链路                              |
| 8   | 抽屉 tab 用 `base-tabs`；表格统一用 `base-table`，排队 / 运行时长列开启前端排序（`elProps.sortable`）                                                 | 复用既有组件；前端本地排序免额外请求                                                             |
| 9   | 新增 API 追加到 `src/api/dashboard/npu-resource.ts` + 类型追加到 `src/types/npu-resource.ts`                                                          | 遵循目录规范，避免文件膨胀                                                                       |
| 10  | 项目 / 资源池下拉选项来自真实接口 `getNpuUsageFilters`（不再静态兜底），资源池随项目级联                                                              | 接口提供 `projects[].resourcePoolIds`，级联收敛选项                                              |
| 11  | 使用率 KPI 卡点击复用既有 `pool-detail-drawer.vue`（`show-usage=false`，只看资源池明细）                                                              | 避免重复实现抽屉                                                                                 |
| 12  | 趋势图 / 热力图点击下钻由容器统一接 `open-slot` 事件，写 `slotContext` 后打开 `task-drawer`                                                           | 下钻上下文（slotTime / serverIp / resourcePoolName / resourcePoolIds）在容器侧组装，组件只发事件 |

## 数据流

```
usage-analysis-view.vue（容器）
  ├─ usageFilter: NpuUsageFilter        ← usage-filter-bar v-model 写入
  ├─ :filter="usageFilter"             → KPI / 趋势 / 热力图（watch 自请求，含完整时间+项目+资源池）
  ├─ :filter="usageFilter"             → 每日区块（仅 watch projectId / resourcePoolIds，日期固定最近 7 日）
  ├─ @open-slot="ctx"                  → slotContext + slotDrawerVisible → task-drawer（:context + :filter）
  └─ @open-daily="date"                → dailyDate + dailyDrawerVisible → daily-drill-drawer（:date + :filter）
      └─ daily-drill-drawer 内流水线任务数点击 → 再开 task-drawer（dayParams: {startDate, endDate, pipelineId}）
```

各组件自持 loading / empty 状态，`to()` 包装请求，不向父组件回传业务数据（仅下钻事件）。

## 时间范围规则（time-range.ts，含单测）

- 默认范围：`trailingHoursRange(24)` = 昨天 00:00 ~ 23:00；快捷项「最近三天」（72h）/「昨天」（24h）
- `alignRange`：起止对齐整点；跨度钳制 1~72h；end 最晚为昨天 23 点（不含当天及未来）；超限自动调整并 `ElMessage.warning` 提示原因
- `isDisabledRangeDate`：禁用今天及未来；已选 start 后，两端日期间隔 > 48h（72h − 24h）禁用
- `toApiTimeRange`：`endTime = endHour + 1h − 5min`（`YYYY-MM-DD HH:mm:ss`），与后端 5 分钟桶形成闭区间（00:00 代表 00:00~00:59 数据）
- 小时粒度通过 `el-date-picker` 的 `time-format="HH"` + popper 样式隐藏分钟列实现

## 数据契约（以 `src/types/npu-resource.ts` / `src/api/dashboard/npu-resource.ts` 为准）

通用方法：`src/api/dashboard/common.ts` 的 `getCommonCard` / `getCommonChart` / `getCommonDetail`；新增方法挂 `src/api/dashboard/npu-resource.ts`。

| 区块     | 接口                                                                                                     | 入参要点                                                                               | 响应要点                                                                                                                                 |
| -------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 筛选选项 | `getNpuUsageFilters`（GET `/npu-usage/filters`）                                                         | 无                                                                                     | `projects[{projectId, projectName, resourcePoolIds}]` + `resourcePools[{resourcePoolId, resourcePoolName}]`                              |
| KPI      | `getCommonCard` category `ops-npu-usage-summary`                                                         | `NpuUsageCommonReq = NpuUsageFilter + category`                                        | `cards[]`，metric ∈ `queueTask / usageRate / usedCardHours / freeCardHours`，按 `resourcePoolId` 分组渲染                                |
| 趋势     | `getCommonChart` category `ops-npu-usage-trend`                                                          | 同全局筛选                                                                             | `xAxis`（5 分钟时刻）+ `series[0]` 使用率(%) + `series[1]` 排队任务数                                                                    |
| 热力图   | `getNpuUsageHeatmap`（POST `/npu-usage/heatmap`）                                                        | `{startTime, endTime, projectId?, resourcePoolIds?, generation?}`                      | `labels[]`（5 分钟刻度）+ `servers[{ip, pool, gen, usage[], alloc[]}]`                                                                   |
| 每日排队 | `getCommonChart` category `ops-npu-daily-queue` + `getCommonCard` category `ops-npu-daily-queue-summary` | `NpuUsageDailyChartReq`：`startDate/endDate` = 最近 7 日 + `projectId/resourcePoolIds` | 图：平均排队 / P90 排队 / 任务总数；卡：`avgQueueMinutes / p90QueueMinutes / taskCount`                                                  |
| 每日卡时 | `getCommonChart` category `ops-npu-daily-card-hours` / `ops-npu-daily-pipeline-card-hours`               | 同上                                                                                   | 每图：主系列 + P90 虚线系列                                                                                                              |
| 任务明细 | `getCommonDetail` category `ops-npu-slot-queue-detail` / `ops-npu-slot-running-detail`                   | `NpuSlotDetailReq`：全局时间 + `slotTime?/serverIp?/resourcePoolIds?/dayParams`        | `records: NpuSlotDetailGroup[]`（按资源池分组，组内 `NpuSlotTaskRecord[]`）                                                              |
| 每日汇总 | `getNpuUsageDailyDrill`（POST `/npu-usage/daily-drill`）                                                 | `{date, projectId?, resourcePoolIds?}`                                                 | 顶层 `totalTasks / avgQueueMinutes / p90QueueMinutes` + `platforms[{platform, taskCount, avgQueueMinutes, totalCardHours, pipelines[]}]` |

字段约定：数值缺失 / null 显示 `--`（`EMPTY_VALUE` / `formatValue`），不显示 "null" / "undefined"。

## 样式与约束（用户指定）

- 样式统一 Tailwind 原子类（base-card、gap-5、p-5 等）；图表栅格 / 缩放条复用既有热力图常量（`HEATMAP_LEFT/RIGHT/TOP_OFFSET/BOTTOM_OFFSET`、`HEAT_DATA_ZOOM_*`、`HEAT_CELL_WIDTH`）；仅日期选择器隐藏分钟列等 Tailwind 无法覆盖处用少量 scoped style
- 不使用 `<section>` 元素（区块一律 `<div>`）
- 仅语义明确的按钮用 `<button>`；下钻触发点（热力格 / 机器行标签、趋势图数据点、KPI 迷你卡、流水线任务数）一律 `<div>`/`<span>` + click
- 排队任务数不做红色告警
- 图表配色统一 `usage-analysis/constants.ts` 的 `USAGE_TREND_COLORS`（使用率紫 `#7c3aed`、排队橙 `#f97316`、总卡时蓝 `#3b82f6`、P90 橙）

## 复用清单

| 复用件                                                                    | 来源                                            | 用于                                                |
| ------------------------------------------------------------------------- | ----------------------------------------------- | --------------------------------------------------- |
| `getCommonCard / getCommonChart / getCommonDetail`                        | `src/api/dashboard/common.ts`                   | KPI / 趋势 / 每日排队 / 每日卡时 / 任务明细数据请求 |
| `getHeatmapOption` / `getHeatmapInitialZoom` / `toHourLabel` / 热力图常量 | `npu-resource/utils.ts` + `config/constants.ts` | 趋势图 / 热力图图表 option 与缩放                   |
| `ChartsUI` + `useCharts`                                                  | `src/plugins/charts`                            | 趋势图 / 热力图 / 每日排队 / 每日卡时图表渲染       |
| `base-tabs` / `base-table` / `base-select-filter`                         | `src/components`                                | 页签、表格、资源池多选                              |
| `pool-detail-drawer.vue`                                                  | `npu-resource/components`                       | 使用率卡点击查看资源池明细                          |
| `NpuHeatmapFilters`（`visible-levels` prop）                              | `npu-resource/components`                       | 使用率热力图仅 IP 筛选                              |
| `heatLevelForPct` / `HEAT_COLORS`                                         | `npu-resource/utils.ts` + `config/constants.ts` | 使用率进度条色阶                                    |
| `formatValue` / `formatFloat` / `isValueEmpty` / `EMPTY_VALUE` / `to()`   | `src/utils` / `src/constants`                   | 数值格式化与错误包装                                |

不复用：`TimeRangeFilter`（仅支持天粒度），筛选栏用 `el-date-picker type="datetimerange"` 小时粒度实现。

## 影响范围

- 修改：`npu-dashboard-view.vue`（新增页签容器，路由改指此文件）、`src/api/dashboard/npu-resource.ts`（+3 方法）、`src/types/npu-resource.ts`（+NpuUsage* 类型）
- 新增：`usage-analysis/` 目录（容器 + 8 组件 + `constants.ts` / `time-range.ts` / `utils.ts` + `__tests__/time-range.test.ts`）
- 不影响：tab1 各组件、既有路由参数、全局 store

## 风险

- 后端接口未就绪时页面空态——按接口契约实现，空态 / 错误态兜底
- 72h × 5 分钟粒度数据量较大——趋势图 / 热力图用 dataZoom 局部渲染 + 横向滚动，前端不做虚拟化
