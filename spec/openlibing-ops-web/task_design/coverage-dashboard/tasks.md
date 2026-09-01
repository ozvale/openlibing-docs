# test-coverage 任务清单

> 图例：✅ 已完成

## L0 骨架

- [x] 路由注册 + 页面骨架：`TestCoverage`（`test-coverage/:productId?`）+ 入口 view + 组件空壳 + config 目录 —— ✅
- [x] 菜单「测试用例覆盖率看板」挂载 dashboard 首页 —— ✅

## L1 基础设施

- [x] 类型定义 `src/types/coverage-dashboard.ts`（PathNodeType 六层、定位参数、PathNode / PathTreeNode / 契约响应）—— ✅
- [x] API 层 `src/api/dashboard/coverage-dashboard.ts`（getTestcasePathTree）—— ✅
- [x] 工具 `utils.ts`（时间快捷项、routeToNodeKey / nodeToRouteQuery / navigateQuery 定位编码、isExpandableNode）+ 单测 —— ✅
- [x] 徽章 `config/badges.ts`（优先级 / 流水线 / 结果 / 节点类型 / 合计）+ 单测 —— ✅
- [x] 图表 option `config/chart-options.ts`（4 builder + 色板）+ 单测 —— ✅
- [x] 列定义 `config/columns.ts`（四组列 + buildCommunityRows）+ 单测 —— ✅
- [x] KPI 映射 `config/kpi.ts`（buildKpiItems）—— ✅

## L2 组合式函数 / 复用组件

- [x] KPI 卡行 `coverage-kpi-cards.vue`（getCommonCard + base-kpi-card）—— ✅
- [x] 树懒加载 `use-coverage-tree.ts`（缓存 / 去重 / 重试 / 祖先链定位 / 收起）+ 单测 —— ✅

## L3 业务区块

- [x] 总览：`coverage-overview.vue` + `coverage-trend-chart.vue` + `community-trend-chart.vue` + `community-distribution-chart.vue` + `community-table.vue` —— ✅
- [x] 详情：`coverage-detail.vue` + `structure-tree.vue` + `tree-node-item.vue` + `node-breadcrumb.vue` + `node-trend-chart.vue` + `node-status-pie.vue` + `child-node-table.vue` + `case-detail-table.vue` + `exec-record-dialog.vue` —— ✅
