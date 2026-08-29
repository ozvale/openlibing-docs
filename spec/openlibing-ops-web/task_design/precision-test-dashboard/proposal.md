# 精准测试看板

## 需求背景

精准测试（按变更影响面智能圈选用例、降低回归成本）已在多个社区推广，但各社区/子组织的精准测试效果（覆盖范围、访问量、PR 渗透率、减少的工作量与测试时长）分散在各项目度量系统中，管理层缺少一个统一视图来掌握整体推广进度与收益。

因此需要在 `openlibing-ops-web` 新增"精准测试看板"页面，提供组织总览 → 子组织下钻两层视图，以社区维度聚合展示精准测试关键指标。

## 功能描述

### 做什么

新增前端页面 `/dashboard/precision-test`，包含两层视图：

**组织总览（默认视图）**
1. **顶部工具栏**：面包屑导航 + 快捷时间区间（今日 / 近7天 / 近30天 / 近90天）+ 起止日期选择
2. **KPI 卡片区（5 个）**：精准测试项目数、精准测试访问量、精准测试 PR 渗透率、PR 测试减少工作量、PR 测试时长降幅
3. **行覆盖率趋势**：多社区折线图（Ascend / CANN / Kunpeng / MindSpore）
4. **PR 测试时长降幅**：多社区柱状图
5. **社区/组织列表**：按社区分组（rowspan 合并），列出子组织/分组的项目数、访问量、PR 渗透率、减少工作量、时长降幅、行/分支/函数/文件覆盖率；点击子组织行下钻

**子组织详情（下钻视图）**
6. 面包屑更新为 `组织 > 社区 > 子组织`，可逐级返回
7. 子组织维度 **KPI 卡片区（5 个）** + **行覆盖率折线图** + **项目时长降幅柱状图**
8. **项目列表**：该子组织下各项目的访问量、PR 渗透率、减少工作量、时长降幅、行/分支/函数/文件覆盖率

### 不做什么

- 不做后端 API（本次采用**静态 mock 数据**，后续可替换为真实接口）
- 不做项目级三级下钻（点击项目暂无跳转）
- 不做导出/刷新按钮（原型无此交互）
- 不重构现有 `test-dashboard` / `code-check` / `engineering-capability` 页面

## 验收标准

- [x] 新页面通过路由 `/dashboard/precision-test` 可访问，页面 title 为 `精准测试看板`
- [x] 组织总览与子组织详情两层视图可正确切换，面包屑导航可返回
- [x] 5 个 KPI 卡片响应式布局：≥1024px 5 列 / 640-1024 2 列 / <640 1 列
- [x] 图表用项目 `ChartsUI` + ECharts 渲染（复用 `@/plugins/charts`），日期区间切换后图表数据随之更新
- [x] 表格行覆盖/时长降幅等百分比列按阈值着色（≥80 绿 / ≥70 黄 / <70 红）
- [x] 所有 Props 定义 TS `interface`，禁止 `any`（`utils.ts` 内部工具除外）
- [x] `npm run type-check` 通过
- [x] `npm run lint:es` / `npm run lint:style` 通过

## 影响范围

| 模块 | 变更类型 | 说明 |
|------|---------|------|
| 路由 `src/router/routes/modules/dashboard.ts` | 修改 | 新增 `PrecisionTestDashboard` 子路由 |
| 页面 `src/views/dashboard/precision-test/` | 新增 | view + components + mock-data + utils + style.less |

**不影响**：现有页面路由、组件、全局样式、Pinia store、后端接口。

## 关联

- Issue: https://gitcode.com/openlibing/openlibing-ops-web/issues/42
