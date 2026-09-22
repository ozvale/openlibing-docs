# 代码检查运营看板 — 技术设计

## 方案概述

在 `openlibing-ops-web` 新增 `code-check` 子模块，遵循现有 `test-dashboard` / `engineering-capability` 的目录结构和组件划分方式：入口 view → 分区子组件 → config 常量 → style.less 模块公共样式。图表统一使用项目 `@/plugins/charts` 封装的 `ChartsUI` 组件；表格使用 `@/components/base-table`；KPI 卡片新增本模块专用组件（不与 engineering-capability 的 kpi-card 强耦合，避免过度抽象）。

数据走真实接口：`getCommonDetail`（`category` 字段路由到 `codeCheck*` 系列 handler）、`getKpiSummary`、`getTrend`、`getRepoList`。

## 架构决策

### D1: 目录布局

采用**分区子组件**方式：view 是薄薄的入口，每个大分区（KPI 组、趋势图、Top10 分支、Top10 重复模块、重复率对比、告警玫瑰、明细表）拆成独立组件。理由：

- 单文件 <400 行的项目硬约束
- 与 `test-dashboard` / `engineering-capability` 的现有模式一致，降低团队认知成本
- 便于后续按分区替换 loading/empty state

### D2: 数据来源（**真实接口**）

通过 `getCommonDetail<T,U>(data)`（`src/api/index.ts`）按 `category` 路由：

| category | 用途 |
|----------|------|
| `codeCheckKpi` | KPI 汇总（8 个卡片） |
| `codeCheckTrend` | 趋势接口（含 `trendMain` / `topBranch` / `topDuplication` / `duplicationDistribution` / `severityBuckets` / `totalSeverityCount`） |
| `codeCheckRepo` | 代码仓明细表（支持 `filterKey: 'repoIds'`） |

辅以：
- `getKpiSummary({ projectId, checkDate })`：单独 KPI 汇总
- `getTrend({ projectId, checkDate })`：单次返回整个趋势聚合
- `getRepoList({ projectId })`：代码仓候选列表（注入到明细表表头 `updateFilterList('repoName', repoList)`）

**接口拆分原则**：每个图表 / 区块对应一个独立的接口函数，互不聚合。理由：

- 后端天然按分区微服务化，各分区数据源不同
- 前端各分区可独立 loading / 独立错误处理 / 独立刷新
- 后续按分区替换 mock/real 时改造成本最低

### D3: 图表选型

| 分区 | ECharts 类型 | 备注 |
|------|-------------|------|
| 12 周增长趋势 | line（smooth，多 series） | 支持 legend scroll |
| Top10 分支数 | bar（横向） | yAxis 反转；`buildOption` 内 `[...items].reverse()` 修柱图顺序 |
| Top10 高重复率代码仓 | **不用 ECharts**，用 CSS 进度条 | 排行榜更适合 HTML 表现 |
| 重复率分布 | bar（分组柱状） | 双系列 + markLine (20% 警戒线) |
| 告警严重等级 | pie（roseType='radius'） | 玫瑰图 + 右侧图例列表；`total` 内部从 `data` 累加 |

ECharts 6 grid 配置：使用 `outerBoundsMode: 'same'` + `outerBoundsContain: 'axisLabel'`，不再用 `containLabel: true`（已在 6.x 弃用）。

### D4: 组件复用策略

- **KPI 卡片**：本模块内新建 `kpi-card.vue`，样式**严格对齐设计稿**：
  - 白底 `#fff` + `1px solid #e2e8f0` + `border-radius: 12px` + `padding: 20px`
  - 顶行：左 label（`12px / #64748b`）+ 右图标方块（4 组预设色板，定义在 `utils.ts` `KPI_ICON_PALETTE`）
  - 底行：值 + 单位
  - hover 略微提升（阴影 + `translateY(-2px)`）
  - engineering-capability 的 kpi-card 使用渐变卡背景，本页不采用；两者不复用。
- **图标语义色映射**（`KPI_ICON_PALETTE` 4 组，循环使用）：

  | idx | bg | color | 用途 |
  |-----|-----|-------|------|
  | 0 | `#dbeafe` | `#2563eb` | 代码仓 / 分支数 |
  | 1 | `#e0f2fe` | `#0ea5e9` | 代码规模 / 平均函数行数 |
  | 2 | `#fee2e2` | `#ef4444` | 静态告警数 / 代码重复率 |
  | 3 | `#fef3c7` | `#b45309` | 未确认开源片段 / 文件重复率 |

- **表格**：直接用 `@/components/base-table`。
- **顶部工具栏**：日期选择 + 刷新按钮（**不**含搜索代码仓与导出）。

### D5: 骨架加载态

沿用 test-dashboard 的做法：数据未加载时 chart-card 内显示 shimmer 占位。骨架样式在本模块 `style.less` 内声明（`@keyframes cc-shimmer` + `.cc-skeleton`）。

### D6: 状态管理

本页无跨组件复杂状态，不引入 Pinia store，也**不引入统一 composable 管理数据**。

**每个分区组件自治**：

- 组件内部各自维护 `loading: Ref<boolean>` 和 `data: Ref<T>`
- `onMounted` 时调对应的 API 函数（`to()` 处理 Promise）
- 各分区加载、失败、重试独立
- view 层只做组件组装（无 props 传递数据、无事件总线），但**有日期 prop 与 refreshKey 透传**触发重新拉取

**刷新策略**：顶部"刷新"按钮递增 `refreshKey`；明细表 `:key="refreshKey"` 重新挂载，KPI/趋势/明细表各自的 `watch([..., refreshKey], fetchData)` 重新拉数。

### D7: 顶部工具栏

`dashboard-toolbar.vue` 用 Vue 3.5 的 `defineModel`：

```ts
const innerDate = defineModel<string>('checkDate', { default: '' });
const emit = defineEmits<(e: 'refresh') => void>();
```

- 日期：`v-model:check-date` 双向绑定到父级
- 刷新：`@refresh` 事件由父级接听

### D8: 明细表表头代码仓筛选

`repo-detail-table.vue` 在 `watchEffect` 中调 `tableRef.value?.updateFilterList('repoName', repoList)`，把组件挂载时拉取的 `getRepoList` 结果注入到 base-table 的 repoName 列。`ColumnProps` 配置 `filterable: true, filterType: 'multipleSelect', filterKey: 'repoIds'`，使 base-table 在筛选变化时以 `repoIds` 字段提交到后端。

实现参照 `src/views/dashboard/open-source-project/sub-table.vue`。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/router/routes/modules/dashboard.ts` | 修改 | 追加子路由 `code-check` |
| `src/views/dashboard/code-check/code-check-view.vue` | 新增 | 入口 view（薄入口） |
| `src/views/dashboard/code-check/components/dashboard-toolbar.vue` | 新增 | 顶部工具栏（日期 + 刷新） |
| `src/views/dashboard/code-check/components/kpi-cards.vue` | 新增 | KPI 卡片区（含 kpi-card 子组件） |
| `src/views/dashboard/code-check/components/kpi-card.vue` | 新增 | 单个 KPI 卡片 |
| `src/views/dashboard/code-check/components/trend-chart.vue` | 新增 | 12 周增长趋势折线图 |
| `src/views/dashboard/code-check/components/top-branch-chart.vue` | 新增 | Top10 分支数横向条形图 |
| `src/views/dashboard/code-check/components/top-dup-rank.vue` | 新增 | Top10 高重复率代码仓排行榜 |
| `src/views/dashboard/code-check/components/dup-rate-chart.vue` | 新增 | 重复率分布柱状图 |
| `src/views/dashboard/code-check/components/severity-rose-chart.vue` | 新增 | 告警严重等级玫瑰图 |
| `src/views/dashboard/code-check/components/repo-detail-table.vue` | 新增 | 代码仓明细表（含表头代码仓筛选） |
| `src/views/dashboard/code-check/config/columns.ts` | 新增 | 表格列配置 |
| `src/views/dashboard/code-check/style.less` | 新增 | 模块公共样式（骨架、卡片） |
| `src/views/dashboard/code-check/utils.ts` | 新增 | 调色板（`CHART_PALETTE` / `KPI_ICON_PALETTE`） |
| `src/api/dashboard/code-check.ts` | 新增 | `getKpiSummary` / `getTrend` |
| `src/types/code-check.ts` | 新增 | 类型定义 |
| `src/utils/format-value.ts` | 新增（已上提） | `formatFloat` 共享工具 |
| `src/constants/index.ts` | 新增（已上提） | `EMPTY_VALUE` 共享常量 |
| `src/views/dashboard/code-check/__tests__/utils.test.ts` | 新增 | 工具函数 + 调色板单测 |
| `src/views/dashboard/code-check/__tests__/columns.test.ts` | 新增 | 列配置契约单测 |
| `src/views/dashboard/code-check/__tests__/dashboard.e2e.test.ts` | 新增 | dashboard e2e |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| ECharts 玫瑰图字段命名易错（`radius` vs `area`） | 按 ECharts v6 官方示例编写 |
| 页面组件超出 400 行 | 每个分区独立组件，view 层 <100 行 |
| 骨架样式与已有页面冲突 | 骨架 class 加 `cc-` 前缀命名空间 |
| 表头筛选的 `filterKey` 与接口字段名不匹配 | 单元测试断言 `filterKey === 'repoIds'` |
| ECharts 6 `containLabel` 已弃用 | 迁到 `outerBoundsMode` + `outerBoundsContain` |

## 跨仓影响

无。仅 `openlibing-ops-web` 前端页面变更。

## 关联

- Issue: https://gitcode.com/openlibing/openlibing-ops-web/issues/33
- Proposal: [proposal.md](./proposal.md)
