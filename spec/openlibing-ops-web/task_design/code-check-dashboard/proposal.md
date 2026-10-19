# 代码检查运营看板

## 需求背景

研发管理层需要一个统一的可视化入口，用于全局把握公司所有代码仓的质量健康度。当前分散在 GitCode、静态扫描平台、开源合规平台的数据无法聚合分析，管理者难以：

- 快速识别代码规模异常增长、分支膨胀严重的代码仓
- 定位重复率高的业务模块并推动重构
- 掌握静态告警在不同严重等级的分布
- 追踪产品开源代码片段的合规确认进度

因此需要在 `openlibing-ops-web` 新增"代码检查运营看板"页面，作为质量运营的统一视图。

## 功能描述

### 做什么

新增前端页面 `/dashboard/code-check`，包含 7 大区块（自上而下）：

1. **顶部工具栏**：日期选择 + 刷新（**不**做"按代码仓搜索"全局控件；代码仓筛选迁移到明细表表头列筛选）
2. **KPI 卡片区（8 个）**：代码仓数、代码规模、分支数、静态告警数、未确认开源片段、平均函数行数、代码重复率、文件重复率
3. **各代码仓最近 12 周增长趋势**：多线折线图
4. **Top10 代码仓分支数**：横向条形图（**已优化排序**，先在 `buildOption` 内 `[...items].reverse()` 使柱图与排名一致）
5. **Top10 高重复率代码仓**：CSS 进度条排行榜
6. **各代码仓重复率对比**：柱状图（代码重复率 + 文件重复率 + 20% 警戒线）
7. **告警严重等级分布**：玫瑰图（严重/高/中/低）+ 图例列表
8. **代码仓明细表**：`base-table`，**代码仓列支持表头多选筛选**（通过 `filterable: true, filterType: 'multipleSelect', filterKey: 'repoIds'` 实现，与 `sub-table.vue` 一致）

### 不做什么

- 不做后端 API 实现（前端通过 `getCommonDetail` 的 `category` 字段路由到 `codeCheck` 系列接口）
- 不做代码仓详情下钻（本次仅顶层聚合展示）
- 不做告警条目级钻取（仅统计维度）
- 不做导出按钮（**已从原方案移除**）
- 不重构现有 `test-dashboard` / `engineering-capability` 页面

## 验收标准

- [x] 新页面通过路由 `/dashboard/code-check` 可访问，页面 title 为 `代码检查运营看板`
- [x] 8 个 KPI 卡片响应式布局：≥1100px 4 列 / 768-1100 2 列 / <768 1 列
- [x] 5 个图表用 `ChartsUI` + ECharts 6 渲染，加载态显示骨架 shimmer
- [x] 明细表使用 `base-table` 公共组件，代码仓列表头多选筛选
- [x] 颜色遵循 Slate + Blue 基线，语义色仅在告警等级/警戒线中使用
- [x] 尊重 `prefers-reduced-motion`
- [x] 所有 Props 定义 TS `interface`，禁止 `any`
- [x] API 层：`src/api/dashboard/code-check.ts`（`getKpiSummary` / `getTrend` 等），类型：`src/types/code-check.ts`
- [x] 数据加载使用 `to()` 处理 Promise
- [x] 单元测试：utils 工具函数 + columns 配置契约 + e2e dashboard
- [x] `npm run type-check` 通过（code-check 模块）
- [x] `npm run lint:es` / `npm run lint:style` 通过
- [x] `npm run test:unit` 通过（code-check 范围 15/15）

## 影响范围

| 模块 | 变更类型 | 说明 |
|------|---------|------|
| 路由 `src/router/routes/modules/dashboard.ts` | 修改 | 新增 `CodeCheckDashboard` 子路由 |
| 页面 `src/views/dashboard/code-check/` | 新增 | 完整目录（view + components + config + utils + style.less） |
| API `src/api/dashboard/code-check.ts` | 新增 | `getKpiSummary` / `getTrend` / `getCommonDetail` 调用 |
| 类型 `src/types/code-check.ts` | 新增 | KPI / 图表 / 表格类型定义 |
| 单测 | 新增 | `src/views/dashboard/code-check/__tests__/`（utils / columns / e2e） |

**不影响**：

- 现有页面路由和组件
- 全局样式（新增样式仅落在本模块 `style.less`）
- Pinia store（本次页面无需跨组件状态，仅局部 ref）

## 关键决策（与原方案差异）

1. **顶部"按代码仓搜索"控件移除**：原方案把代码仓选择作为顶部 el-select，影响接口 `repoIds` 入参。新方案改为明细表表头列筛选（`updateFilterList('repoName', repoList)`），由 `base-table` 自动以 `filterKey: 'repoIds'` 提交到接口。理由：UI 入口更聚焦于表格本身，且与 `open-source-project/sub-table.vue` 实现一致。
2. **导出按钮移除**：原方案设计稿含导出按钮，本次交付范围不含。
3. **mock 数据被真实 API 替代**：从早期"先用 mock"切到调用 `getCommonDetail`（`category: 'codeCheckRepo'` 等） + `getTrend` + `getKpiSummary` + `getRepoList` 的真实接口。
4. **SeverityRoseChart props 统一**：从 `{ loading, buckets, total }` 简化为 `{ loading, data: SeverityBucket[] }`，`total` 内部从 `data` 累加派生；与其他图表组件（`data: XxxItem[]`）保持一致。
5. **格式工具上提**：`formatFloat` 抽到 `src/utils/format-value.ts` 共享；模块本地 `utils.ts` 仅保留 `CHART_PALETTE` / `KPI_ICON_PALETTE` 调色板与本地 `EMPTY_VALUE` 抽出到 `@/constants`。
6. **ECharts 6 grid 配置**：从 `containLabel: true` 迁到 `outerBoundsMode: 'same'` + `outerBoundsContain: 'axisLabel'`。

## 关联

- Issue: https://gitcode.com/openlibing/openlibing-ops-web/issues/33
