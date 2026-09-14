# 测试用例覆盖率看板 — 技术设计

## 方案概述

新增 dashboard 页面模块 `test-coverage`：单一路由 `TestCoverage`（可选参数 `productId`）承载总览/详情两个视图。数据层走通用接口（`card` / `chart` / `detail` / `path tree`），以 `category` 区分各数据区；API 契约由前端定型，后端后续对接。页面状态在视图层与组合式函数中管理（不用 Pinia）；结构树异步懒加载；样式 Tailwind 优先。

## 架构决策

### 1. 路由与视图切换

- `src/router/routes/modules/dashboard.ts` 新增：`name: 'TestCoverage'`、`path: 'test-coverage/:productId?'`、`meta.title: '测试用例覆盖率看板'`。
- 无 `productId` → 总览 `coverage-overview.vue`；有 `productId` → 详情 `coverage-detail.vue`。
- 下钻 / 树 / 面包屑导航统一 `router.push({ name: 'TestCoverage', params: { productId }, query })`；回总览 push 无参路由。

### 2. 状态管理（视图层 + 组合式函数，提供/注入时间参数）

- 入口 `test-coverage-view.vue` 持有时间范围 `dateRange`，派生 `dateParams = { startDate, endDate }`，经 `provide(COVERAGE_DETAIL_PARAMS_KEY)` 注入给各区域组件。
- 总览数据在 `coverage-overview.vue` 内请求，详情数据在 `coverage-detail.vue` 内请求；跨组件通过 props / emits 通信。
- 请求模式：`const [err, res] = await to(api(...))`；错误提示由 http 拦截器统一处理，不重复 toast。

### 3. API 契约（category 驱动）

通用接口：`getCommonCard` / `getCommonChart` / `getCommonDetail` 来自 `src/api/dashboard/common.ts`（`baseURL = apiConfig.ops`），`getTestcasePathTree` 来自 `src/api/dashboard/coverage-dashboard.ts`。

| 函数                     | 路径                       | 用途            |
| ------------------------ | -------------------------- | --------------- |
| `getCommonCard<T, U>`    | POST `/common/card`        | KPI 卡数据      |
| `getCommonChart<T, U>`   | POST `/common/chart`       | 图表数据        |
| `getCommonDetail<T, U>`  | POST `/common/detail`      | 表格 / 列表数据 |
| `getTestcasePathTree<T>` | POST `/testcase/path/tree` | 结构树子级      |

各数据区以入参 `category` 区分：

| category                             | 数据区          |
| ------------------------------------ | --------------- |
| `testcase-overview`                  | KPI 卡          |
| `testcase-pass-rate-trend`           | 全局 / 节点趋势 |
| `testcase-community-pass-rate-trend` | 社区趋势        |
| `testcase-community-distribution`    | 社区分布        |
| `testcase-community-project-list`    | 社区列表        |
| `testcase-child-node-list`           | 子节点列表      |
| `testcase-file-case-list`            | 用例详情        |
| `testcase-status-distribution`       | 用例状态分布    |
| `testcase-case-run-detail`           | 执行记录        |

### 4. 类型模型（`src/types/coverage-dashboard.ts`）

```ts
type PathNodeType = "product" | "project" | "repo" | "branch" | "dir" | "file"; // 六层

interface CoverageLocateParams {
  productId?: number | null;
  projectId?: number | null;
  repoUrl?: string;
  repoBranch?: string;
  nodePath?: string;
  nodeType?: PathNodeType | "";
}
interface CoverageCommonReq extends CoverageLocateParams {
  category: string;
  nodeKey?: string;
  caseKey?: string;
  page?: number;
  pageSize?: number;
  startDate?: string;
  endDate?: string;
}
interface CoverageNodeKey extends CoverageLocateParams {
  nodeType: PathNodeType;
  nodeLevel: number;
}

interface PathNode {
  nodeKey;
  nodeType;
  nodeLevel;
  nodePath;
  productId;
  projectId;
  repoUrl;
  repoBranch;
  productName;
  projectName;
  repoName;
}
interface PathTreeNode extends PathNode {
  id;
  name;
  childCount;
  children?;
  loaded;
  loading;
}
interface CoverageNodeDetail {
  node: PathTreeNode;
  ancestors: PathTreeNode[];
}

interface KpiCardItem {
  metric;
  name;
  value;
  unit;
  precision;
}
interface ChartData<D> {
  title;
  xAxis: string[];
  series: ChartSeriesItem<D>[];
}
interface CommunityStat {
  /* 社区行 + projects 列 */
}
interface ChildNodeStat {
  /* 子节点行 */
}
interface TestcaseCaseItem {
  caseKey;
  caseNumber;
  className;
  level;
  type;
  repoName;
  repoBranch;
  fullFilePath;
  runCnt;
  passedCnt;
  failedCnt;
  skipCnt;
  durationP50;
  durationP90;
  avgNpuConsumption;
}
interface TestcaseExecRecord {
  level;
  type;
  jobName;
  startTime;
  endTime;
  pipelineType;
  result;
  time;
  npuConsumption;
}
```

### 5. 结构树（异步懒加载）

- 无全量树接口：根与子级均经 `getTestcasePathTree` 按 `nodeKey`（空参数拉根级）按需拉取。
- 页面级 composable `use-coverage-tree.ts`：`nodeById` / `childrenCache` / `loadedIds` / `pending` / `rootChildren` / `expandedIds`。
  - `ensureRootLoaded(productId)`：拉社区根并过滤；
  - `ensureChildren(nodeId)`：缓存命中直返、并发 Promise 去重、失败不缓存可重试、兄弟按名称排序；
  - `expandNode` / `toggleExpand` / `collapseToChain`（一键收起）；
  - `expandToLocate(target)`：沿祖先链逐层 `ensureChildren` 定位选中节点，仅展开祖先、不预取目标子级；`file` 之外自动展开一层。
- 定位编码：`routeToNodeKey`（query → CoverageNodeKey）、`nodeToRouteQuery` / `navigateQuery`（节点 → 路由 query，保留非节点键）。
- 竞态防护：组件内 `locateSeq` 递增，异步结果落地前校验 seq 一致性，避免快速切换导致旧态覆盖新态。
- `structure-tree.vue`：拖拽调宽（原生 mouse 事件，180–500，默认 288）、折叠 48px 窄条（仅恢复按钮）、选中后 `requestAnimationFrame` 平滑滚动。

### 6. 图表（`config/chart-options.ts`，纯函数构建）

全部经 `ChartsUI` + `useCharts` 渲染，加载时骨架遮罩。

| builder                     | 说明                                                   |
| --------------------------- | ------------------------------------------------------ |
| `buildGlobalTrendOption`    | 通过率 / 执行率双折线，yAxis 百分比，面积渐变          |
| `buildCommunityTrendOption` | 多社区多折线，10 色循环                                |
| `buildDistributionOption`   | 通过 / 失败堆叠柱                                      |
| `buildStatusPieOption`      | 环形图（通过 / 失败 / 未执行），tooltip / label 带占比 |

色板 `COVERAGE_CHART_PALETTE`（`#2563eb / #0ea5e9 / #10b981 / #f59e0b / #8b5cf6 / #ef4444 / #0891b2 / #d97706 / #7c3aed / #059669`）；通过 `#10b981`、失败 `#ef4444`、未执行 `#cbd5e1`、通过率线 `#0ea5e9`、执行率线 `#8b5cf6`。

### 7. 表格（四张表全部复用公共 `base-table`）

| 表         | request category                  | 分页                             |
| ---------- | --------------------------------- | -------------------------------- |
| 社区分组表 | `testcase-community-project-list` | 无（`span-list` rowSpan）        |
| 子节点列表 | `testcase-child-node-list`        | 无                               |
| 用例详情表 | `testcase-file-case-list`         | 10 条/页                         |
| 执行记录表 | `testcase-case-run-detail`        | 15 条/页，`height=100%` 表头吸顶 |

列定义集中在 `config/columns.ts`，徽章渲染走 `config/badges.ts`；社区表经 `buildCommunityRows` 生成社区/项目扁平行，`handle-table-data` 转换响应。

### 8. 徽章（`config/badges.ts`）

- 优先级：`level-badge level-P0..P3`；流水线：PR=amber / NIGHTLY=emerald / OTHER=neutral；结果：1 成功 / 0 失败 / 2 跳过 / 3 未执行；节点类型：社区 / 项目 / 代码仓 / 分支 / 目录 / 文件；`TOTAL_BADGE` 合计（蓝）。
- 统一 `{ label, class, icon? }` 结构，class 为 Tailwind 类串。

### 9. KPI 卡行与执行记录弹窗生命周期

- KPI 复用公共 `base-kpi-card.vue`：`config/kpi.ts` 的 `buildKpiItems` 按 metric 映射图标（Odometer / CircleCheck / CircleClose / TrendCharts / Aim）与配色（blue / emerald / red / sky / amber），`coverage-kpi-cards.vue` v-for 渲染，加载时骨架。
- 执行记录弹窗 `exec-record-dialog.vue` 由父组件 `v-if="activeCase"` 控制挂载，挂载即拉第 1 页；`close` → 父组件卸载，每次打开全新实例。

## 涉及文件

| 文件                                                                             | 说明                                                                    |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `src/router/routes/modules/dashboard.ts`                                         | 修改：新增 TestCoverage 路由                                            |
| `src/api/dashboard/coverage-dashboard.ts`                                        | 新增：getTestcasePathTree                                               |
| `src/api/dashboard/common.ts`                                                    | 复用：getCommonCard / Chart / Detail                                    |
| `src/types/coverage-dashboard.ts`                                                | 新增：契约类型                                                          |
| `src/views/dashboard/test-coverage/test-coverage-view.vue`                       | 新增：入口编排（时间范围 + 视图切换 + 面包屑）                          |
| `src/views/dashboard/test-coverage/use-coverage-tree.ts`                         | 新增：树懒加载 composable                                               |
| `src/views/dashboard/test-coverage/utils.ts`                                     | 新增：路由定位编码 / 格式化常量                                         |
| `src/views/dashboard/test-coverage/config/{badges,chart-options,columns,kpi}.ts` | 新增：徽章 / 图表 option / 列 / KPI 映射                                |
| `src/views/dashboard/test-coverage/components/*.vue`（15 个）                    | 新增：总览与详情各区块组件                                              |
| `src/views/dashboard/test-coverage/__tests__/*.test.ts`（5 个）                  | 新增：utils / badges / chart-options / columns / use-coverage-tree 单测 |

## 风险 & 缓解

| 风险                         | 缓解                                                                                     |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| 后端接口未就绪，线上无数据   | 契约由前端定型（category 驱动），各区域有空态；错误由拦截器静默处理                      |
| 懒加载树快速切选导致状态错乱 | `locateSeq` 竞态防护 + Promise 并发去重、失败不缓存                                      |
| 样式两套体系混用             | Tailwind 优先，不建页面级 style.less；`<style lang="less">` 仅用于 `:deep()` / keyframes |
