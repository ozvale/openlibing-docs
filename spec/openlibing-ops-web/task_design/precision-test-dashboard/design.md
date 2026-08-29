# 精准测试看板 — 技术设计

## 方案概述

在 `openlibing-ops-web` 新增 `precision-test` 子模块，实现精准测试看板 Vue 页面。遵循现有 dashboard 模块的目录结构：入口 view → 分区子组件 → mock 数据 → utils → style.less。

图表统一使用项目 `@/plugins/charts` 封装的 `ChartsUI` + `useCharts`；表格使用原生 `<table>` + Tailwind 类（原型即为原生表格，无需引入 `base-table` 的接口能力）；数据使用静态 mock（`mock-data.ts` 内置 `communityData`，与原型一致）。

## 架构决策

### D1: 目录布局

```
src/views/dashboard/precision-test/
├── precision-test-view.vue   # 入口 view：状态（社区/子组织/日期）+ 视图切换 + 图表实例管理
├── mock-data.ts              # communityData + generateProjects / generateLineData / 类型定义
├── utils.ts                  # 格式化、阈值着色、指标展示工具
├── style.less                # 模块公共样式（滚动条、表格 hover、sticky 列阴影）
└── components/
    ├── page-header.vue       # 面包屑 + 快捷时间区间 + 起止日期
    ├── kpi-cards.vue         # KPI 卡片组（组织/详情复用，props: items）
    ├── line-chart-card.vue   # 行覆盖率折线图（props: series、dates、yDomain）
    ├── bar-chart-card.vue    # PR 测试时长降幅柱状图（props: categories、values）
    ├── org-table.vue         # 社区/子组织列表（emit: select-suborg）
    └── project-table.vue     # 子组织项目明细列表（props: rows）
```

理由：单文件 <400 行的项目硬约束；与 `test-dashboard` / `code-check` 组件划分方式一致；两个图表在组织视图与详情视图复用，抽为共享组件。

### D2: 数据来源（**静态 mock**）

- `mock-data.ts` 内置 4 个社区（Ascend / CANN / Kunpeng / MindSpore）+ 各自子组织 + 项目列表。
- 随机生成函数（`generateProjects` / `generateLineData`）与原型保持一致，保证页面每次进入有动态视觉效果。
- 接口替换预留：`mock-data.ts` 对外只暴露 `communityData` 与类型，后续接真实接口时仅需替换该文件与 view 中的数据获取逻辑。

### D3: 视图与交互状态

`precision-test-view.vue` 集中管理以下状态：

| 状态 | 说明 |
|------|------|
| `currentCommunity` / `currentSubOrg` | 当前下钻位置；均为空 = 组织总览 |
| `startDate` / `endDate` / `dateRangeDays` | 日期区间（快捷按钮 0/7/30/90 天） |
| `detailLineData` / `detailBarData` | 详情视图图表数据（选中子组织后计算） |

- 点击子组织行 → 设置 currentCommunity/currentSubOrg → 显示详情视图
- 面包屑"组织" / 社区 → 逐级返回
- 日期区间变化 → 重算各图表日期轴与数据

### D4: 图表选型

| 分区 | ECharts 类型 | 备注 |
|------|-------------|------|
| 行覆盖率（组织总览） | line（smooth，多 series） | 4 社区 × 日期轴；y 轴 0.75-1.0 百分比 |
| 行覆盖率（子组织详情） | line（smooth，单 series + 渐变 area） | y 域基于子组织基线动态计算 |
| PR 测试时长降幅（组织总览） | bar | 4 社区柱状，按索引着色 |
| PR 测试时长降幅（子组织详情） | bar | 项目维度，按数值阈值着色 |

图表使用 `ChartsUI` 容器 + `useCharts` 的 `renderCharts`；切换子组织时先 `resetInstance` 再重建，避免残留实例。

### D5: 表格与阈值着色

- 百分比阈值着色函数在 `utils.ts`：
  - `getCoverageClass`：行/分支/函数/文件覆盖率（≥80 绿 / ≥70 黄 / <70 红）
  - `getReductionClass`：时长降幅（≥80 绿 / ≥70 黄 / <70 橙）
- 首列"社区"跨行合并（rowspan），子组织列 sticky + 点击下钻。

### D6: 样式

- 页面容器：`bg-[#f8fafc]` 灰底，卡片白底圆角。
- 模块级 scrollbar 定制与表格 hover 态放 `style.less`（非 scoped，跟随其他 dashboard 模块约定）。
- 日期输入、快捷按钮交互沿用原型（Tailwind 类 + 少量 scoped 样式）。

### D7: 类型

所有 Props 用 TS `interface` 定义（如 `KpiItem`、`LineSeriesItem`、`SubOrgRow`、`ProjectRow`）；ECharts option 使用 `ECOption` 类型；随机生成函数返回类型显式声明。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/router/routes/modules/dashboard.ts` | 修改 | 追加子路由 `precision-test` |
| `src/views/dashboard/precision-test/precision-test-view.vue` | 新增 | 入口 view |
| `src/views/dashboard/precision-test/components/page-header.vue` | 新增 | 顶部工具栏 |
| `src/views/dashboard/precision-test/components/kpi-cards.vue` | 新增 | KPI 卡片组 |
| `src/views/dashboard/precision-test/components/line-chart-card.vue` | 新增 | 行覆盖率折线图 |
| `src/views/dashboard/precision-test/components/bar-chart-card.vue` | 新增 | 时长降幅柱状图 |
| `src/views/dashboard/precision-test/components/org-table.vue` | 新增 | 社区/子组织列表 |
| `src/views/dashboard/precision-test/components/project-table.vue` | 新增 | 项目明细列表 |
| `src/views/dashboard/precision-test/mock-data.ts` | 新增 | mock 数据 + 生成函数 + 类型 |
| `src/views/dashboard/precision-test/utils.ts` | 新增 | 格式化 + 着色工具 |
| `src/views/dashboard/precision-test/style.less` | 新增 | 模块公共样式 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 单文件超 400 行 | 分区拆组件，view 层仅做状态与组装 |
| 图表实例残留导致旧数据闪烁 | 切换时 `resetInstance` + `renderCharts(option, true)` |
| Tailwind 动态类名被 purge | 阈值着色类全部是完整字符串（如 `bg-green-50 text-green-600`），非动态拼接 |
| mock 随机数据导致测试不稳定 | 工具函数单测用固定输入，不测随机生成结果 |

## 跨仓影响

无。仅 `openlibing-ops-web` 前端页面变更。

## 关联

- Issue: https://gitcode.com/openlibing/openlibing-ops-web/issues/42
- Proposal: [proposal.md](./proposal.md)
