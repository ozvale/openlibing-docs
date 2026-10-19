# Proposal — NPU 使用率分析（npu-usage-analysis）

- 关联 Issue：https://gitcode.com/openlibing/openlibing-ops/issues/121
- 业务仓：`openlibing-ops-web`
- 流程模式：Full（跨 8 区块、新增页面级组件 8 个、对接 3 个新接口 + 复用通用接口）

> 本文档为实现后回写版，功能描述与验收标准均已按落地代码更新，与当前实现保持一致。

## 背景与目标

NPU 资源看板（`src/views/dashboard/npu-resource`）原为单页线性布局。需要：

1. 主入口页签化：新增页签容器「资源总览」（原页面内容原样保留）+「使用率分析」（新增页面）
2. 使用率分析页包含：筛选栏、KPI 概览（排队 + 使用率）、双 Y 轴趋势图、机器×切片热力图、每日排队分析、每日卡时双图、切片任务明细抽屉、每日分层汇总抽屉

## 验收标准

- [ ] `/dashboard/npu-resource` 路由下两个页签（资源总览 / 使用率分析）可切换，页签激活态持久化（localStorage），「资源总览」内容与改造前一致（无回归）
- [ ] 筛选栏：时间范围小时粒度（不可选分钟）、跨度 ≤ 72h、不含当天及未来日期；快捷项「最近三天 / 昨天」；项目单选、资源池多选（随项目级联），选项来自真实接口 `getNpuUsageFilters`
- [ ] 筛选联动：KPI、趋势、热力图跟随时间 + 项目 + 资源池刷新；每日区块（每日排队 / 每日卡时）固定最近 7 日，仅跟随项目 / 资源池
- [ ] 下钻链路：趋势点 / 热力格 / 热力行 / KPI 排队卡 → 任务明细抽屉（排队 / 运行 tab，按资源池分组）；每日排队图点 → 每日汇总抽屉（平台 → 流水线），流水线任务数可继续下钻任务明细抽屉
- [ ] 使用率 KPI 卡点击复用既有 `pool-detail-drawer` 查看资源池明细
- [ ] 排队任务数不做告警（无红色阈值）；使用率颜色分级使用 `heatLevelForPct` 标准 7 档色阶（与既有热力图一致）
- [ ] 空 / loading / error 边界：loading 骨架屏、空数据「暂无数据」占位、数值缺失显示 `--`
- [ ] `npm run lint` / `npm run format` / `npm run test:unit` / `npm run type-check` 通过

## 组件树

```
npu-dashboard-view.vue（页签容器：BaseTabs + KeepAlive，激活页签存 localStorage）
├── tab1 资源总览：npu-resource-view.vue（原有内容原样保留）
└── tab2 使用率分析：usage-analysis/usage-analysis-view.vue（容器：持有 usageFilter，props 下发 / emit 上抛）
    ├── usage-filter-bar.vue      时间 / 项目 / 资源池筛选（v-model 写回 usageFilter）
    ├── usage-kpi-panel.vue       排队任务 + 使用率 KPI 卡组
    ├── usage-trend-chart.vue     双 Y 轴趋势图（点击下钻）
    ├── usage-heatmap.vue         使用率热力图（IP 筛选，点击下钻）
    ├── daily-queue-panel.vue     每日排队任务分析（3 KPI + 柱线混合图）
    ├── daily-card-hours.vue      每日卡时双图（总卡时 / 平均卡时）
    ├── task-drawer.vue           任务明细抽屉（排队 / 运行 tab，按资源池分组）
    └── daily-drill-drawer.vue    当日任务汇总抽屉（平台 → 流水线，可再下钻）
```

配套文件：`usage-analysis/constants.ts`（图表配色、`USAGE_MAX_SPAN_HOURS`）、`usage-analysis/time-range.ts`（时间对齐 / 钳制 / API 转换纯函数，含单测）、`usage-analysis/utils.ts`（ECharts option 纯函数）。
