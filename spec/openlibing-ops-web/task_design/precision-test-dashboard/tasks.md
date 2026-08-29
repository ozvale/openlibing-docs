# 精准测试看板 — 实现任务

## 进度: 0/12

### 基础设施

- [ ] Task 1: 新增 `src/views/dashboard/precision-test/mock-data.ts`（communityData + generateProjects / generateLineData + 类型定义）
- [ ] Task 2: 新增 `src/views/dashboard/precision-test/utils.ts`（`getCoverageClass` / `getReductionClass` / `formatNumber` / 日期工具）

### 页面骨架

- [ ] Task 3: 新增路由 `src/router/routes/modules/dashboard.ts`（PrecisionTestDashboard 子路由，path `precision-test`）
- [ ] Task 4: 新增入口 view `src/views/dashboard/precision-test/precision-test-view.vue`（组织/详情视图切换 + 日期状态 + 图表实例管理）

### 组件

- [ ] Task 5: 新增 `components/page-header.vue`（面包屑 + 快捷时间区间 + 起止日期）
- [ ] Task 6: 新增 `components/kpi-cards.vue`（5 个 KPI 卡片，组织/详情复用）
- [ ] Task 7: 新增 `components/line-chart-card.vue`（行覆盖率折线图）
- [ ] Task 8: 新增 `components/bar-chart-card.vue`（PR 测试时长降幅柱状图）
- [ ] Task 9: 新增 `components/org-table.vue`（社区/子组织列表 + rowspan 合并 + 点击下钻）
- [ ] Task 10: 新增 `components/project-table.vue`（子组织项目明细列表）

### 样式

- [ ] Task 11: 新增 `src/views/dashboard/precision-test/style.less`（scrollbar、表格 hover、sticky 列阴影）

### 验证

- [ ] Task 12: `npm run type-check` / `npm run lint:es` / `npm run lint:style` 通过

## 验证记录

（待填写）
