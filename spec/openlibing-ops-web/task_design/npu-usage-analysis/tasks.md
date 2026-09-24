# Tasks — npu-usage-analysis

关联 Issue：https://gitcode.com/openlibing/openlibing-ops/issues/121

> 实现任务清单（全部已完成），与当前代码保持一致。执行顺序自上而下。

## L0 页签容器

- [x] 任务 1：新增 `npu-dashboard-view.vue` 页签容器（`base-tabs` + `KeepAlive`，激活页签 `useLocalStorage` 持久化），tab1 挂原 `npu-resource-view.vue`、tab2 挂 `usage-analysis-view.vue`；路由 `/dashboard/npu-resource` 改指 `npu-dashboard-view.vue`｜验证：`npm run lint` + 浏览器切换页签无回归

## L1 基础设施

- [x] 任务 2：类型与 API——`src/types/npu-resource.ts` 追加 `NpuUsage*` 类型（`NpuUsageFilter` / `NpuUsageKpiCard` / `NpuUsageChartResp` / `NpuUsageFiltersResp` / `NpuUsageDailyChartReq` / `NpuUsageDailyDrill*` / `NpuSlotDetailReq` / `NpuSlotDetailGroup` / `NpuSlotTaskRecord` / `NpuUsageSlotContext`）；`src/api/dashboard/npu-resource.ts` 追加 `getNpuUsageFilters` / `getNpuUsageHeatmap` / `getNpuUsageDailyDrill`｜验证：`npm run type-check`
- [x] 任务 3：常量与工具——`usage-analysis/constants.ts`（`USAGE_TREND_COLORS`、`USAGE_MAX_SPAN_HOURS=72`）、`usage-analysis/time-range.ts`（`trailingHoursRange` / `alignRange` / `isDisabledRangeDate` / `toApiTimeRange`，小时粒度对齐、跨度钳制、不含当天、endTime +1h−5min）+ `__tests__/time-range.test.ts` 单测、`usage-analysis/utils.ts`（`buildUsageTrendOption` / `buildDailyQueueOption` / `buildDailyCardHoursOption` / `buildUsageSlotHeatmapOption` / `dailyRange` / `EMPTY_CHART_RESP`）｜验证：`npm run test:unit`（time-range 用例通过）

## L2 组件

- [x] 任务 4：`usage-filter-bar.vue`——`el-date-picker` datetimerange 小时粒度（隐藏分钟列）、快捷项「最近三天 / 昨天」、禁用今天及未来、跨度 ≤72h 自动钳制并提示；项目单选 / 资源池多选（`base-select-filter`，随项目级联），选项来自 `getNpuUsageFilters`；`defineModel` 写回 `usageFilter`｜验证：`npm run lint`
- [x] 任务 5：`usage-kpi-panel.vue`——两列卡组：排队任务（每池迷你卡，点击 emit `open-slot`）+ 使用率（每池进度条，色阶 `heatLevelForPct` + `HEAT_COLORS`，点击打开复用 `pool-detail-drawer`，`show-usage=false`）；数据来自 `getCommonCard`（`ops-npu-usage-summary`）按 `resourcePoolId` 分组｜验证：`npm run lint`
- [x] 任务 6：`usage-trend-chart.vue`——双 Y 轴折线（使用率左轴 / 排队任务右轴），dataZoom（slider + inside）按数据量条件展示、`minSpan` 约束；点击图表（zr click + `convertFromPixel`，`Math.floor` 定位切片）emit `open-slot`；数据来自 `getCommonChart`（`ops-npu-usage-trend`）｜验证：`npm run lint`
- [x] 任务 7：`usage-heatmap.vue`——ECharts heatmap（复用 `getHeatmapOption` / `getHeatmapInitialZoom`），仅 IP 筛选（`NpuHeatmapFilters` `visible-levels=['ip']`）；点击热力格 emit `open-slot`（slotTime + serverIp）、点击机器行标签 emit `open-slot`（serverIp）；数据来自 `getNpuUsageHeatmap`｜验证：`npm run lint`
- [x] 任务 8：`daily-queue-panel.vue`——3 KPI 卡（平均排队 / P90 排队 / 任务总数，`ops-npu-daily-queue-summary`）+ 柱线混合图（平均 / P90 折线 + 任务总数柱，`ops-npu-daily-queue`）；日期固定最近 7 日，仅 watch 项目 / 资源池；点击图点 emit `open-daily`｜验证：`npm run lint`
- [x] 任务 9：`daily-card-hours.vue`——双图（每日消耗总卡时 / 每日使用 NPU 流水线平均卡时），各含主系列 + P90 虚线系列；`Promise.all` 并发请求 `ops-npu-daily-card-hours` / `ops-npu-daily-pipeline-card-hours`｜验证：`npm run lint`
- [x] 任务 10：`task-drawer.vue`——排队 / 运行双 tab（`base-tabs`），按资源池分组展示（`NpuSlotDetailGroup[]`，`base-table` 无分页），排队 / 运行时长列前端排序；任务名超链接（`el-link`，`jobUrl`）；数据来自 `getCommonDetail`（`ops-npu-slot-queue-detail` / `ops-npu-slot-running-detail`），入参含 `slotTime` / `serverIp` / `resourcePoolIds` / `dayParams`｜验证：`npm run lint`
- [x] 任务 11：`daily-drill-drawer.vue`——头部 3 个总览徽章（任务总数 / 平均排队 / P90 排队），平台 → 流水线两级卡片；流水线「任务数」点击再开 `task-drawer`（`dayParams` 传 `startDate/endDate/pipelineId`）；数据来自 `getNpuUsageDailyDrill`｜验证：`npm run lint`

## L3 容器组装

- [x] 任务 12：`usage-analysis-view.vue` 容器——持有 `usageFilter` / `slotContext` / `dailyDate` / 两个抽屉可见性；`usage-filter-bar` v-model 写回 `usageFilter`；KPI / 趋势 / 热力图 / 每日区块 props 下发 `filter`；接 `open-slot` / `open-daily` 事件打开对应抽屉｜验证：`npm run lint`

## L4 验证

- [x] 任务 13：`npm run lint` / `npm run format` / `npm run test:unit` / `npm run type-check` 全部通过；对照验收标准逐条自检；交付用户自测通过
