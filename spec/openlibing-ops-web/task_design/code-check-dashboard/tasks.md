# 代码检查运营看板 — 实现任务

## 进度: 14/14 (主任务) + 6/6 (后续 refactor) complete

### 基础设施

- [x] Task 1: 新增类型定义 `src/types/code-check.ts`（KpiSummary、GrowthTrend、TopBranchItem、TopDupItem、DupRateItem、SeveritySummary、RepoDetailItem 等 interface）
- [x] Task 2: 新增 API 层 `src/api/dashboard/code-check.ts`（`getKpiSummary` / `getTrend`，并复用 `getCommonDetail` 路由 `codeCheck*`）
- [x] Task 3: 接入真实接口替代早期 mock（`category` 字段路由：codeCheckKpi / codeCheckTrend / codeCheckRepo）

### 页面骨架

- [x] Task 4: 新增路由 `src/router/routes/modules/dashboard.ts`（CodeCheckDashboard 子路由）
- [x] Task 5: 新增入口 view `src/views/dashboard/code-check/code-check-view.vue`（薄入口，组装所有子组件）
- [x] Task 6: 取消 composables 目录，各组件内部自治管理自己的 loading + data

### 组件

- [x] Task 7: 新增 `dashboard-toolbar.vue`（日期 + 刷新；用 `defineModel('checkDate')`）
- [x] Task 8: 新增 `kpi-cards.vue` + `kpi-card.vue`（8 个 KPI 卡片 + 响应式 grid）
- [x] Task 9: 新增 `trend-chart.vue`（12 周增长趋势 ECharts 多线折线图）
- [x] Task 10: 新增 `top-branch-chart.vue`（Top10 分支数 ECharts 横向条形图）
- [x] Task 11: 新增 `top-dup-rank.vue`（Top10 高重复率代码仓 CSS 进度条排行榜）
- [x] Task 12: 新增 `dup-rate-chart.vue`（重复率分布 ECharts 分组柱状图 + 20% 警戒线）
- [x] Task 13: 新增 `severity-rose-chart.vue`（告警严重等级 ECharts 玫瑰图 + 图例列表）
- [x] Task 14: 新增 `repo-detail-table.vue`（代码仓明细表 + 表头代码仓多选筛选）

### 样式

- [x] Task 15: 新增 `src/views/dashboard/code-check/style.less`（模块公共样式：骨架 shimmer、卡片、图表容器、`prefers-reduced-motion` 适配）

### 测试

- [x] Task 16: 新增 `src/views/dashboard/code-check/__tests__/`（utils 工具 + columns 配置 + dashboard e2e）

### 验证

- [x] Task 17: `npm run type-check` / `npm run lint:es` / `npm run lint:style` / `npm run test:unit` 全部通过（code-check 范围 0 错误 / 15/15 tests）

## 后续 refactor（按 commit 顺序）

- [x] R1: 8f5a880 仓库筛选切到多选 + 移除 project options API
- [x] R2: 44b582f 简化 toolbar + 加 null-safe 展示
- [x] R3: 9c3970a 接入真实接口（按 design-final 契约）
- [x] R4: 4afb329 提取共享样式、调色板、格式器
- [x] R5: f0e2229 `formatFloat` 上提到 `src/utils/format-value.ts`
- [x] R6: a27d0ac `EMPTY_VALUE` 统一到 `@/constants`、删除 4 个透传 slot、ECharts 6 grid 迁移
- [x] R7: f6042d3 顶部"按代码仓搜索"迁移到明细表表头列筛选（`updateFilterList`）
- [x] R8: 7549ae5 SeverityRoseChart props 统一为 `{ loading, data }`
- [x] R9: 64848cb 标题/描述文案精简、top-branch 柱图排序修复、columns helpTip 去前缀、列筛选 `filterKey: 'repoIds'`

## 验证记录（截至 2026-07-31）

- `npm run type-check`（code-check 范围）：0 错误
- `npm run lint:es` / `npm run lint:style`：全绿
- `npm run test:unit -- src/views/dashboard/code-check`：3 files / 15 tests 通过
- husky pre-commit：prettier + eslint + stylelint + commitlint 全绿
