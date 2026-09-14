# NPU 资源看板 — 技术设计

- 业务 Issue：https://gitcode.com/openlibing/openlibing-ops-web/issues/40
- 提案：`./proposal.md`

> 本文件为技术设计的**实现后回写版**：架构决策 D1–D13 均已按落地代码更新（对接真实后端接口、`chart-renderer` 抽取、三热力图、`project-heat-card` 合并卡、自绘网格热力图去 popover 化等），与当前实现保持一致。

## 方案概述

在 `src/views/dashboard/npu-resource/` 新建独立模块，采用「薄入口 view + 自治子组件」架构。数据对接真实后端接口（`/gateway/.../resource-operation/*`），**不依赖 `/mock`**（`mock/npu-resource.ts` 已注释停用）。下钻链路上下文（`projectId` / `projectName` / `projectRow` / `dateParams`）由入口 view 通过 provide/inject（`N_R_DETAIL_PARAMS_KEY`）下发，各图表/抽屉组件自行拉数。

三个服务器热力图用 ECharts `heatmap` + `visualMap` + `dataZoom`（各自独立实例，`FullscreenView` 全屏）；第三层运行分析的两个网格热力图是**自绘 DOM 网格**（非 ECharts），因为需要在格子上叠加任意定位的连线标记与文字胶囊，DOM 方案在定位精度与无障碍上都更优，标记数据统一由 `utils.buildMarker` 构造，组件内不再自建浮层（用原生 `:title` tooltip）。

## 架构决策

### D1: 目录布局

```
src/views/dashboard/npu-resource/
├── npu-resource-view.vue              # 薄入口，持有时间范围 + 刷新时间 + 抽屉开关 + provide 下钻上下文
├── style.less                          # 仅热力色阶/shimmer/动效降级/EP 覆盖，其余走 Tailwind
├── utils.ts                            # 纯函数：色阶分档、效率差值、热力/趋势 option 构造、运行分析视图转换
├── chart-renderer.ts                   # createChartRenderer：实例按 DOM 变化重置 + 渲染/全屏重绘
├── config/
│   ├── columns.ts                      # 3 组 ColumnProps 配置（项目/流水线/运行；机器列在 pool-detail-row 内联）
│   └── constants.ts                    # 色阶、趋势配色、时间快捷项、阈值、最小可选日期
├── components/
│   ├── npu-time-range-toolbar.vue      # 区块 1：共享 time-range-filter + 数据更新时间
│   ├── npu-kpi-cards.vue               # 区块 2（grid 容器 + 骨架）
│   ├── npu-kpi-card.vue                # 双行对比卡（base-card）
│   ├── npu-trend-chart.vue             # 区块 3：折线图 + 维度切换 + el-select-v2 分组筛选
│   ├── npu-heatmap-panel.vue           # 区块 4 容器（筛选 + 3 个热力图）
│   ├── npu-heatmap-filters.vue         # 三级联筛选（IP 可搜索确认）
│   ├── fullscreen-view.vue             # 全屏容器（useFullscreen + 图标按钮）
│   ├── project-efficiency-table.vue    # 区块 5
│   ├── pool-detail-drawer.vue          # 资源池明细抽屉（80%）
│   ├── pool-detail-row.vue             # 手风琴行 + 6 列机器原生表
│   ├── project-drill-drawer.vue        # 项目下钻抽屉（80%/min-width 880px）容器 + 面包屑切换
│   ├── project-summary-stats.vue       # 项目概要统计条
│   ├── project-heat-card.vue           # 单卡：资源申请/排队双线图 + 流水线分配热力（合并原两卡）
│   ├── pipeline-efficiency-table.vue   # 流水线效率表（5 列）
│   ├── run-analysis-panel.vue          # 第三层面板容器（面包屑 + 运行明细表 + 两网格热力）
│   └── run-marker-heatmap.vue          # 自绘 DOM 网格热力图（alloc/usage 复用）
└── __tests__/
    ├── columns.test.ts
    ├── utils.test.ts
    ├── npu-kpi-card.test.ts
    ├── npu-time-range-toolbar.test.ts
    └── pool-detail-row.test.ts
```

单文件均控制在 400 行内（仓库规范）。原设计的 `project-request-chart.vue` / `project-heatmap-chart.vue` 合并为单一 `project-heat-card.vue`（双线图 + 热力并列一卡）；`run-marker-popover.vue` 已移除（改为原生 `:title` tooltip）。

### D2: 数据来源（真实后端，非 mock）

全部数据来自真实后端，接口签名集中在 `src/api/dashboard/npu-resource.ts`：

| 函数                      | 端点                                                    | 用途                                             | 返回                       |
| ------------------------- | ------------------------------------------------------- | ------------------------------------------------ | -------------------------- |
| `getNpuSummary`           | `POST .../resource-operation/summary`                   | KPI 4 卡（双行）+ 总量按代际 tag                 | `NpuSummaryResp`           |
| `getNpuTrend`             | `POST .../resource-operation/trend`                     | 趋势图，按 `dim` 返回分组序列（pool/gen）        | `NpuTrendResp`             |
| `getNpuHeatmap`           | `POST .../resource-operation/heatmap`                   | 服务器热力全量（含筛选可选值），可传 `projectId` | `NpuHeatResp`              |
| `getNpuRunAnalysis`       | `POST .../resource-operation/run-analysis`              | 单次运行分配率/使用率分析序列                    | `NpuRunAnalysisResp`       |
| `getNpuProjectAllocTrend` | `POST .../resource-operation/project-alloc-trend`       | 项目资源申请次数 / 排队时长双线                  | `NpuProjectAllocTrendResp` |
| `getCommonDetail`         | `POST .../common/detail`（复用既有入口）                | 项目表 / 流水线表 / 运行明细表 / 资源池明细      | `PagerData<T>`             |
| `getRefreshTime`          | 既有接口（`modules: ['resource_operation_dashboard']`） | 工具条「数据更新于」时间戳                       | —                          |

`common/detail` 的 `category` 取值：`ops-project-efficiency` / `ops-pipeline-efficiency` / `ops-pipeline-run-detail` / `ops-resource-pool-detail`，复用 `getCommonDetail`，表格直接传给 `base-table` 的 `requestApi`。

时间范围参数统一为 `{ startDate, endDate }`（`YYYY-MM-DD`），由 `dateParams` computed 提供。运行分析窗口宽度由接口返回的 `timeLabels` 决定（非固定 4 小时）。

### D3: 图表选型

| 图                          | 实现                                                             | 理由                                                                                     |
| --------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| NPU 趋势图                  | ECharts `line`（已注册）                                         | 分组图例合并逻辑用 `buildTrendTooltip` + 自定义 tooltip 实现；实线分配 / 虚线使用        |
| 效率分析 / 分配率 / 使用率  | ECharts `heatmap` ×3（独立实例） + `visualMap` + `dataZoom`      | 3 个 `ChartsUI` 实例各自渲染；`dataZoom` 按容器尺寸自动决定是否出现滚动条                |
| 项目申请次数双线 + 分配热力 | ECharts `line` + `heatmap`（`project-heat-card` 内两个实例并列） | 实线 = 资源申请次数，警示色虚线 = 每小时总排队时长；热力为项目关联服务器 × 小时          |
| 运行分析双网格（第三层）    | **自绘 DOM 网格**（`run-marker-heatmap.vue`）                    | 需在格子上叠加任意百分比定位的连线 + 双端点 + 文字胶囊；DOM 方案在定位精度与无障碍上更优 |

`ECOption` 扩展的联合类型：`HeatmapSeriesOption`、`VisualMapComponentOption`、`GraphicComponentOption`。

### D4: 公共图表插件扩展（唯一对公共模块的改动）

`src/plugins/charts/echarts.ts` 纯追加：注册 `HeatmapChart` / `VisualMapComponent` / `GraphicComponent` 并追加 3 个联合类型。实现中 `GraphicComponent` **实际未使用**（三热力图方案不需要双栅格虚线分隔），注册仅保持类型完备。对既有图表零行为影响。

### D5: 状态管理

不引入 pinia store。跨组件共享的下钻上下文由入口 view `provide`（`N_R_DETAIL_PARAMS_KEY`），各组件 `inject`：

```ts
provide(N_R_DETAIL_PARAMS_KEY, {
  projectId, // ref<number>
  projectName, // ref<string>
  projectRow, // ref<NpuProjectEfficiencyItem | null>
  dateParams, // computed<{ startDate, endDate }>
});
```

入口 view 持有：`dateRange`（`ref<[string, string] | null>`）、`refreshTime`、`poolDrawerVisible`、`projectDrawerVisible` + 项目三元组。各图表/抽屉组件 `inject` 到 `dateParams` 后自行 `watch` 拉数。热力筛选状态在 `npu-heatmap-panel.vue` / `project-heat-card.vue` 内部持有（`Record<值, boolean>` ×3：pool/gen/ip）。抽屉用 `defineModel` 双向绑定可见性。项目下钻抽屉在打开/关闭时维护 `activePipeline`（关闭即置空）。

### D6: 时间范围模型与校验

- 复用共享组件 `time-range-filter.vue`（`v-model: [string, string] | null`），quick options 为 `NPU_TIME_QUICK_OPTIONS`（`昨日` value `'1'` / `最近一周` value `'7'`，均以昨日收尾，不含当天）
- `min-date` 传 `NPU_MIN_SELECTABLE_DATE = '2026-08-20'`，`clearable=false`
- `disabled-date` 三重禁用：今天及未来、早于最小可选日期、与已选起点跨度 > `MAX_TIME_SPAN_DAYS - 1`（7 天，含首尾）
- **无独立「应用」按钮与 4 档校验文案**（原设计 `validateTimeSpan` 已废弃，改为 disabled-date 直接禁止非法选择）
- 数据首次拉取由 `time-range-filter` 检测到空 `dateRange` 时触发（默认「最近一周」写回）
- 工具条右侧「数据更新于」来自 `getRefreshTime`

### D7: 热力色阶与阈值

`config/constants.ts`：

```ts
export const HEAT_COLORS = [
  "#f4f7fc",
  "#dbe7f8",
  "#a8c8ef",
  "#f5d9b8",
  "#f0a84a",
  "#e8682a",
  "#c92a1f",
];
export const TREND_PALETTE = [
  "#2563eb",
  "#dc2626",
  "#16a34a",
  "#d97706",
  "#7c3aed",
  "#0891b2",
  "#db2777",
  "#65a30d",
  "#ea580c",
  "#0d9488",
  "#4f46e5",
  "#b91c1c",
];
export const NPU_TIME_QUICK_OPTIONS = [
  { label: "昨日", value: "1" },
  { label: "最近一周", value: "7" },
];
export const QUEUE_WARN_THRESHOLD = 10;
export const MAX_TIME_SPAN_DAYS = 7;
export const NPU_MIN_SELECTABLE_DATE = "2026-08-20";
```

- 趋势分组配色由 `TREND_PALETTE`（12 色）按 index 循环取色（`colorizeTrendGroups`），非按 pool/gen 两套固定色
- `QUEUE_WARN_THRESHOLD = 10`（min）已声明但**未应用于表格警示色**（见 proposal「不做什么」）
- `utils.ts` 的 `heatLevelForPct(pct): 0|1|2|3|4|5|6`：分档 `0–10 / 11–25 / 26–45 / 46–60 / 61–75 / 76–90 / ≥91`
- 效率差值 `resolveHeatValue(alloc, usage) = Number(Math.abs(alloc - usage).toFixed(2))` —— **取绝对值**，非 `max(0, …)`
- 语义色沿用仓库 `--el-color-*` / Tailwind slate/blue/amber 令牌，不引入设计稿 `--npu-*` 私有变量集

### D8: 三级联筛选

筛选状态 `Record<string, boolean>` ×3（`pool` / `gen` / `ip`），放 `npu-heatmap-filters.vue` 内部。级联收敛纯函数在 `utils.ts`：

```ts
function reconcileHeatFilters(
  servers,
  filter,
): { poolOptions: string[]; genOptions: string[]; ipOptions: string[] };
function filterServers(servers, filter): NpuHeatServer[]; // pool+gen+ip 均 !== false 才保留
```

- `pool` 可选值 = 全量去重；`gen` = 已选 pool 下存在的代际；`ip` = 匹配已选 pool+gen 的机器
- **不可用选项直接从列表收敛移除**（不渲染 `{值} (无)` 禁用态）；IP 选项数 ≤5 时隐藏搜索框，>5 时需输入确认选择
- `重置` 把三个 map 全部置空对象，三个热力图由同一 `filteredServers` computed 派生，天然同步

### D9: 表格策略

4 张表全部用 `base-table`，列配置集中在 `config/columns.ts`：

| 表                   | 列数 | 关键处理                                                                                                                                            |
| -------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npuProjectColumns`  | 4    | 项目名称（可点击下钻）/ PR 资源排队时长[P90](min) / PR NPU 分配(卡时) / NPU 使用率(%)；分页 small                                                   |
| `npuPipelineColumns` | 5    | 流水线名称 / 类型（PR·Nightly 徽标）/ 资源排队时长[P90](min) / 分配卡时 / 运行次数；操作列「查看运行明细」                                          |
| `npuRunColumns`      | 7    | 运行 ID / 流水线名称 / 运行结束时间 / 测试任务资源最大排队时长 / 累计排队时长 / NPU 分配 / 状态；分页 small，默认每页 20                            |
| 机器列（内联）       | 6    | 资源池抽屉展开区。`machineColumns` 定义在 `pool-detail-row.vue` 内部（非 `columns.ts`），用 `base-table`（`pager-show=false` + `border=false`）渲染 |

资源池明细抽屉用 `getCommonDetail({ category: 'ops-resource-pool-detail', ...dateParams })` 一次性拉取，由 `pool-detail-row.vue` 手风琴展开区渲染 6 列机器表（机器 IP / 总卡时 / 分配卡时 / 使用卡时 / 分配率 / 使用率），后两列为数值 + 迷你占比条。

### D10: 抽屉实现

两个抽屉都用 `el-drawer`，`direction="rtl"`：

| 抽屉       | size                        | 触发                     | 内部结构                                                        |
| ---------- | --------------------------- | ------------------------ | --------------------------------------------------------------- |
| 资源池明细 | `80%`                       | KPI 卡「查看资源池明细」 | 头部 + 副标题 + 3 个手风琴行（`pool-detail-row`，首个默认展开） |
| 项目下钻   | `80%`（`min-width: 880px`） | 项目表点击项目名         | 头部 + 面包屑；body 双态：概要+热力卡+流水线表 / 运行分析面板   |

项目下钻抽屉的双态切换：`v-show="!activePipeline"` 渲染概要视图（`ProjectSummaryStats` + `ProjectHeatCard` + `PipelineEfficiencyTable`），`v-if="activePipeline"` 渲染 `RunAnalysisPanel`；面包屑「项目效率 › {项目} › {流水线} 运行分析」，点「项目效率」置空 `activePipeline` 返回。图表 resize 由 `chart-renderer` 按 DOM 变化重置实例（全屏/抽屉展开动画后自动处理），不再依赖 `@opened` + `setTimeout`。

### D11: 自绘网格热力图（第三层）

`run-marker-heatmap.vue`，props：`{ title, runId?, mode: 'alloc' | 'usage', timeLabels, rows }`（`rows: NpuRunHeatRow[]`，由 `utils.toRunAnalysisView` 构造）。

- 网格 `display: grid; grid-template-columns: 180px repeat(n, 1fr)`，列数由 `timeLabels.length` 决定（1 小时/格，非固定 4 小时）
- 每台机器一行数值格（7 级色阶背景 + 百分比文字）；无运行记录的机器整行 `opacity: .5`
- 每个测试任务一行标记行：连线 + 起止双端点 + 文字胶囊，`left: calc(...)` 按 `startPct` / `endPct` 百分比定位（跨午夜窗口已处理，`secondsBetween` 对负差 +24h）
- `alloc` 用警示色（空心起点 = 申请开始，实心终点 = 分配成功）；`usage` 用主色（双实心端点）
- 文字胶囊 `:title` 原生 tooltip（任务名 · 时长 min · 起止），**不引入 teleport 浮层**（原设计 `run-marker-popover.vue` 已移除）
- 标记数据由 `utils.buildMarker`（按 mode 决定时长/起止字段）统一构造，组件内不再内联计算
- 图例两套文案：分配 `申请开始 / 分配成功 / 等待区间`；使用 `使用开始 / 使用结束 / 使用区间`

### D12: 样式策略（Tailwind 优先）与骨架加载态

按 `ai_memory.md` 严格执行 **Tailwind utility classes 优先**，`<style>` 块降到最小。判定规则：

| 样式类型                                                                   | 归属                                                              |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 布局（grid / flex / gap / padding / 尺寸）、字号、字重、颜色、圆角、边框   | Tailwind utility，直接写在模板 `class` 上                         |
| 响应式断点（>1100 / 768–1100 / <768）                                      | Tailwind `md:` `xl:` 或 `max-[1100px]:` 任意断点                  |
| 表格数字对齐                                                               | Tailwind `text-right` + `[font-variant-numeric:tabular-nums]`     |
| `base-card` 及其修饰类                                                     | 复用 `src/assets/style/card.less` 既有类，不重写                  |
| 7 级热力色阶（同一组类被上百个格子复用）                                   | `style.less` 定义 `.npu-heat-0` … `.npu-heat-6`（色阶需集中维护） |
| shimmer 关键帧动画 / `prefers-reduced-motion` 全模块降级                   | `style.less`（`@keyframes` / 通配选择器无法用 utility 表达）      |
| Element Plus 深度覆盖（`el-select`、`el-segmented`、`el-drawer` 内边距等） | `style.less`（需 `:deep()` / 后代选择器）                         |

**动态值处理**：迷你占比条宽度、连线标记百分比定位属于数据驱动，通过 `:style` 绑定 CSS 自定义属性（如 `:style="{ '--npu-bar-w': pct + '%' }"`），实际 `width: var(--npu-bar-w)` 写在 class 里。

**骨架加载态**：`.npu-skeleton` 定义在 `style.less`，尺寸/圆角/间距用 Tailwind；各卡片 `v-if="loading"` 渲染等高骨架，避免布局跳动。

### D12.1: 注释约束

按 `ai_memory.md` 严格执行「代码中不写任何注释」：本次新增的 `.ts` / `.vue` / `.less` 文件**不写任何注释**（含 JSDoc、`//`、`/* */`、`<!-- -->`）。既有文件（`echarts.ts`、`dashboard.ts` 路由等）的原有注释保留不动，只做追加。命名必须自解释（`heatLevelForPct` / `buildMarker` 等）；单测用中文 `describe`/`it` 名称承担「这段逻辑要满足什么」的表达职责。

### D13: 无 `<section>` 与 `base-card` 约束落地

- 所有区块容器一律 `<div class="base-card">`；语义分组用 `role="group"` + `aria-label` 补偿
- 抽屉外层用 `el-drawer`（内部渲染为 `<div>`），头部用 `<div>` / `<header>` 内嵌，不用 `<section>`
- 卡片阴影/抬升按需追加 `base-card--hover-shadow` / `base-card--hover-lift`

## 涉及文件

- **新增**：`src/views/dashboard/npu-resource/`（见 D1 目录）、`src/api/dashboard/npu-resource.ts`、`src/types/npu-resource.ts`、路由 `src/router/routes/modules/dashboard.ts`
- **修改（公共模块）**：`src/plugins/charts/echarts.ts`（纯追加注册）
- **删除/停用**：`mock/npu-resource.ts`（已注释停用，gitignored）

## 测试策略

- `utils.test.ts`：`heatLevelForPct` 7 档边界、`resolveHeatValue`（`Math.abs` 口径）、`reconcileHeatFilters` 级联收敛、`filterServers`、`buildTrendOption` / `buildHeatTooltip`、`toRunAnalysisView` / `buildMarker`（alloc/usage 模式、跨午夜）、`colorizeTrendGroups`
- `columns.test.ts`：4 组列配置契约断言（列数、`prop`、`label`、`sortable`、`unit`）
- `npu-kpi-card.test.ts`：双行渲染、`base-card` 类、空值 `--` 降级、`view-pool-detail` emit
- `npu-time-range-toolbar.test.ts`：快捷项 / 禁用日期逻辑（今日及未来、早于最小日期、超 7 天跨度）
- `pool-detail-row.test.ts`：折叠/展开切换、`aria-expanded` 同步、6 列表头、占比条宽度
- 质量门禁：`npm run lint` / `npm run format` / `npm run test:unit` / `npm run type-check` 全部通过后提交
