# engineering-capability-dashboard — 技术设计

## 方案概述

在 `src/views/dashboard/engineering-capability/` 下按「页面入口 + 工具栏 + 主表 + 下钻面板 + Modal」分层组织，遵循仓库既有 dashboard 模块模式（参考 `test-dashboard`）。数据层用 `vite-plugin-mock` 拦截 HTTP 请求（mock 文件放仓库根目录 `mock/`），API 函数走真实 `http` 调用，后端就绪后删除 mock 文件即可切换。状态管理用组合式函数（composables）而非 Pinia store，因为状态作用域仅限本页面，无需跨页面共享。

## 架构决策

### 决策 1：页面级状态用 composables，不引入 Pinia store

**原因**：本页面状态（时间段、列显隐、组件筛选、下钻面板开合、当前选中组件/列、各表分页）仅在本页面内流转，不跨页面共享。参考 `test-dashboard` 模块也未使用 store。引入 store 会增加不必要的复杂度。

**实现**：`composables/use-engineering-capability.ts` 统一管理页面状态，子组件通过 props/inject 接收。

### 决策 2：mock 数据集中管理，API 层预留切换入口

**原因**：用户确认先用 mock 数据开发，但后端 API 后续会就绪。若 mock 数据散落在组件内，切换成本高。

**实现**：

- 新建仓库根目录 `mock/` 文件夹（当前不存在），`mock/engineering-capability.ts` 导出 `MockMethod[]`，定义拦截规则（url/method/response），内含 5 个组件的完整 mock 数据
- `api/dashboard/engineering-capability.ts` 定义 API 函数（`getEngineeringCapabilityList`、`getComponentDetail`、`getRunsRecord`、`getBranchConfig`、`saveBranchConfig`、`getLinkConfig`、`saveLinkConfig`），走真实 `http.post(...)` 调用，由 mock 中间件拦截返回 `{ records, total }` 分页结构
- TS 类型在 `types/engineering-capability.ts` 统一定义，API 与 mock 共用
- E2E 测试在 dev 模式运行（playwright.config.ts 中 `command: 'npm run dev'`），mock 天然生效

### 决策 3：主表与下钻表统一用仓库公共组件 `base-table`

**原因**：仓库已有 `src/components/base-table.vue`（基于 `el-table` 封装），内置分页（`el-pagination`）、多级表头（`ColumnProps.children` 嵌套）、插槽自定义渲染、排序、筛选等能力。03-项目结构.md 明确要求"无特殊要求必须使用公共部分"，04-组件规范.md 要求"交互组件库二次封装必须使用 Element Plus 组件"。

**实现**：

- **主表**：5 个组件行无需分页，用 `data` 属性传本地数据 + `pagerShow=false`。三级表头通过 `columns` 配置的 `children` 嵌套实现（`base-column` 递归渲染）。sticky 首列用 `fixed="left"`。单元格点击下钻用 `el-table` 的 `@cell-click` 事件。tooltip 用 `base-column` 的 `helpTip` 或插槽 + `el-tooltip`。
- **下钻面板 3 个明细表 + 运行记录表**：用 `requestApi` 模式（mock API 返回 `{ records, total }` 分页结构），分页由 `base-table` 内置 `el-pagination` 承载，无需额外组件。
- 列配置抽到 `config/columns.ts` 和 `config/detail-columns.ts`，数据驱动渲染。

### 决策 3.5：列设置用仓库公共组件 `column-setting`

**原因**：仓库已有 `src/components/column-setting.vue`（树形列设置 + 多级表头支持 + localStorage 持久化 + 全选/恢复默认 + `update:data` 事件回传带 `show` 字段的列配置）。03-项目结构.md 要求"无特殊要求必须使用公共部分"。设计稿中工具栏的「列设置下拉」改用此组件，无需自实现下拉，也无需单独的 `use-column-visibility` hook。

**实现**：

- 工具栏内用 `<column-setting :data="columns" :original-data="columns" data-key="engineering-capability-main" @update:data="onColumnsChange" />`
- `column-setting` 通过 `update:data` 事件回传处理后的列配置（含 `show` 字段），主表用此配置驱动 `base-table` 的 `columns`（`base-column` 的 `v-if="column.show ?? true"` 自动显隐）
- 下钻面板代码仓 Tab 的列设置同理用 `column-setting`，`data-key` 区分

### 决策 3.6：时间段筛选参照 `test-dashboard`，快捷选项 + `el-date-picker` 联动

**原因**：用户明确要求参照 `test-dashboard` 的 `time-range-selector.vue`。该模式提供「今日 / 近7天 / 近30天 / 近90天」快捷按钮 + `el-date-picker`（daterange），快捷选项与日期选择器双向联动，体验优于纯日期选择器。仓库内已有成熟实现可复用模式。

**实现**：

- `config/time-range.ts` 导出 `TIME_RANGE_OPTIONS`（与 test-dashboard 一致：今日/近7天/近30天/近90天）和 `TimeRange` 类型（`'today' | '7d' | '30d' | '90d' | 'custom'`）
- `composables/use-engineering-capability.ts` 管理 `timeRange` + `dateRange` 状态，提供 `setTimeRange(range)`（计算日期并同步 dateRange）和 `setDateRange(range)`（置 timeRange 为 custom）方法，逻辑参照 `test-dashboard-store.ts`
- 工具栏 `engineering-toolbar.vue` 内渲染快捷按钮组（active 态高亮）+ `el-date-picker`（type="daterange", format="YYYY-MM-DD", value-format="YYYY-MM-DD")
- 日期计算用 dayjs（仓库已依赖）：今日=[今天,今天]，近7天=[今天-6,今天]，近30天=[今天-29,今天]，近90天=[今天-89,今天]

### 决策 3.7：链接配置 / 分支配置 Modal 调接口持久化

**原因**：用户明确要求两个 Modal 需要调接口。本期无真实后端，但走 mock 拦截 + localStorage 兜底，保证交互闭环且后端就绪后零改动。

**实现**：

- `api/dashboard/engineering-capability.ts` 新增 4 个 API 函数：
  - `getBranchConfig(component)`：获取组件下代码仓分支配置
  - `saveBranchConfig(data)`：保存分支配置
  - `getLinkConfig(component, colKey)`：获取列链接配置
  - `saveLinkConfig(data)`：保存链接配置
- `mock/engineering-capability.ts` 新增对应拦截规则，response 从 localStorage 读取（key 含 component/colKey），无则返回默认配置；POST 请求写入 localStorage
- `branch-config-modal.vue` 打开时调 `getBranchConfig` 加载，保存时调 `saveBranchConfig`
- `link-config-modal.vue` 打开时调 `getLinkConfig` 加载，保存时调 `saveLinkConfig`

### 决策 4：下钻面板用 `el-drawer` 而非自实现 slide-panel

**原因**：设计稿用自实现 `.slide-panel` + transform，但 Element Plus `el-drawer` 提供开箱即用的滑出动画、遮罩、z-index 管理、a11y，符合"交互组件库二次封装必须使用 Element Plus"规范。

**实现**：`el-drawer` direction="rtl"（从右滑出），size="60%"，内含 3 个 Tab（`el-tabs`）。

### 决策 5：状态徽章用独立组件 `status-badge.vue`

**原因**：设计稿中「满足/不满足」状态在代码仓明细表多处出现（编码风格、pre-commit、自动修复、例外备案），渲染逻辑一致（ok→绿色✓，fail→红色✗+原因）。抽成组件复用，符合"样式去重铁律"（06-样式规范.md §8）。

### 决策 6：E2E 测试用 mock 模式，不依赖真实后端

**原因**：本期无真实后端，E2E 若依赖真实数据会不稳定。Playwright 配置已有 `vite-plugin-mock`，可在 E2E 时拦截 API 返回固定 mock 数据。

**实现**：E2E 测试中页面天然走 mock API（因为 API 函数当前返回 mock），无需额外 mock 拦截。后端就绪后，E2E 需补充 mock 拦截或改用测试环境数据。

## 涉及文件

### 业务仓 `openlibing-ops-web`

| 文件                                                                                   | 操作 | 说明                                                                                                                                                                     |
| -------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/types/engineering-capability.ts`                                                  | 新增 | 所有 TS 类型：ProjectRow、RepoItem、ResourceItem、NightlyItem、RunsRecord 等                                                                                             |
| `src/api/dashboard/engineering-capability.ts`                                          | 新增 | API 函数（走真实 http，由 mock 拦截）：getEngineeringCapabilityList、getComponentDetail、getRunsRecord、getBranchConfig、saveBranchConfig、getLinkConfig、saveLinkConfig |
| `mock/engineering-capability.ts`                                                       | 新增 | vite-plugin-mock 拦截规则 + 5 个组件完整 mock 数据 + 分支/链接配置 localStorage 持久化（新建 mock/ 文件夹）                                                              |
| `src/views/dashboard/engineering-capability/config/columns.ts`                         | 新增 | 主表三级表头列配置（colKey/colGroup/label/rowspan/colspan）                                                                                                              |
| `src/views/dashboard/engineering-capability/config/detail-columns.ts`                  | 新增 | 下钻代码仓表列配置                                                                                                                                                       |
| `src/views/dashboard/engineering-capability/config/time-range.ts`                      | 新增 | 时间段快捷选项配置（TIME_RANGE_OPTIONS）+ TimeRange 类型                                                                                                                 |
| `src/views/dashboard/engineering-capability/composables/use-engineering-capability.ts` | 新增 | 页面主状态 hook（含 timeRange/dateRange 联动逻辑）                                                                                                                       |
| `src/views/dashboard/engineering-capability/components/engineering-toolbar.vue`        | 新增 | 工具栏                                                                                                                                                                   |
| `src/views/dashboard/engineering-capability/components/main-table.vue`                 | 新增 | 主表                                                                                                                                                                     |
| `src/views/dashboard/engineering-capability/components/detail-panel.vue`               | 新增 | 下钻面板容器                                                                                                                                                             |
| `src/views/dashboard/engineering-capability/components/repo-tab.vue`                   | 新增 | 代码仓 Tab                                                                                                                                                               |
| `src/views/dashboard/engineering-capability/components/resource-tab.vue`               | 新增 | 资源环境 Tab                                                                                                                                                             |
| `src/views/dashboard/engineering-capability/components/nightly-tab.vue`                | 新增 | Nightly Tab                                                                                                                                                              |
| `src/views/dashboard/engineering-capability/components/branch-config-modal.vue`        | 新增 | 分支配置 Modal                                                                                                                                                           |
| `src/views/dashboard/engineering-capability/components/link-config-modal.vue`          | 新增 | 链接配置 Modal                                                                                                                                                           |
| `src/views/dashboard/engineering-capability/components/runs-record-modal.vue`          | 新增 | 运行记录 Modal                                                                                                                                                           |
| `src/views/dashboard/engineering-capability/components/kpi-card.vue`                   | 新增 | KPI 卡片                                                                                                                                                                 |
| `src/views/dashboard/engineering-capability/components/status-badge.vue`               | 新增 | 状态徽章                                                                                                                                                                 |
| `src/views/dashboard/engineering-capability/engineering-capability-view.vue`           | 新增 | 页面入口                                                                                                                                                                 |
| `src/views/dashboard/engineering-capability/style.less`                                | 新增 | 模块公共样式                                                                                                                                                             |
| `src/views/dashboard/engineering-capability/__tests__/columns.test.ts`                 | 新增 | 列配置测试                                                                                                                                                               |
| `src/views/dashboard/engineering-capability/__tests__/mock-data.test.ts`               | 新增 | mock 数据结构测试                                                                                                                                                        |
| `src/views/dashboard/engineering-capability/__tests__/status-badge.test.ts`            | 新增 | 状态徽章组件测试                                                                                                                                                         |
| `src/router/routes/modules/dashboard.ts`                                               | 修改 | 新增路由 `engineering-capability`                                                                                                                                        |
| `e2e/engineering-capability.spec.ts`                                                   | 新增 | E2E 测试                                                                                                                                                                 |

### 文档仓 `openlibing-docs`

| 文件                                                                               | 操作 |
| ---------------------------------------------------------------------------------- | ---- |
| `spec/openlibing-ops-web/task_design/engineering-capability-dashboard/proposal.md` | 新增 |
| `spec/openlibing-ops-web/task_design/engineering-capability-dashboard/design.md`   | 新增 |
| `spec/openlibing-ops-web/task_design/engineering-capability-dashboard/tasks.md`    | 新增 |

## 关键数据模型

```typescript
// 组件主表行（主表每行对应一个开源组件）
interface ProjectRow {
  component: string; // MindIE / PTA / openEuler / ...
  color: "blue" | "green" | "orange" | "purple" | "red";
  ttfhw: number | null; // 整体 TTFHW（分钟）
  localCoding: {
    envPrepare: number | null;
    styleVisible: MetricStatus;
    precommit: MetricStatus;
  };
  localBuild: {
    incBuild: number | null;
    fullBuild: number | null;
    utExec: number | null;
  };
  prPipeline: {
    checkRules: number;
    autoFix: MetricStatus;
    exceptionReview: MetricStatus;
    prDuration: number;
  };
  resource: {
    pr: ResourceMetrics;
    nightly: ResourceMetrics;
    overall: ResourceMetrics;
  };
  nightly: {
    nightlyBuildSuccess: number; // 百分比
    versionAvail: number; // 百分比
  };
}

interface ResourceMetrics {
  cpuUsage: number; // CPU 消耗（核时）
  cpuAvg: number; // CPU 平均消耗
  cpuTotal: number; // CPU 总量
  cpuRate: number; // CPU 使用率（百分比）
  npuUsage: number; // NPU 消耗（卡时）
  npuAvg: number;
  npuTotal: number;
  npuRate: number;
}

interface MetricStatus {
  ok: boolean;
  reason?: string;
  extra?: number; // 附加信息（如规则数）
}

// 代码仓明细
interface RepoItem {
  name: string;
  url: string;
  branch: string;
  languages: string[];
  style: MetricStatus;
  precommit: MetricStatus;
  rulesCount: number;
  autofix: MetricStatus;
  exception: MetricStatus;
  prTime: number;
}

// 资源流水线行
interface ResourcePipelineRow {
  pipelineName: string;
  type: "PR" | "Nightly" | "Overall";
  cpuUsage: number;
  cpuAvg: number;
  npuUsage: number;
  npuAvg: number;
}

// Nightly 流水线行
interface NightlyPipelineRow {
  pipeline: string;
  nightlyBuildSuccess: number;
  versionAvail: number;
}

// 流水线运行记录
interface RunsRecord {
  id: number;
  startTime: string;
  status: "success" | "failed" | "running";
  cpuUsage: number;
  npuUsage: number;
}

// 分支配置（Modal 持久化）
interface BranchConfigItem {
  repoName: string;
  branches: string[];
  selectedBranch: string;
}
interface BranchConfigPayload {
  component: string;
  repos: BranchConfigItem[];
}

// 链接配置（Modal 持久化）
interface LinkConfigItem {
  colKey: string;
  label: string;
  linkUrl: string;
  linkValue?: string;
}
interface LinkConfigPayload {
  component: string;
  colKey: string;
  configs: LinkConfigItem[];
}
```

## 风险 & 缓解

| 风险                                                       | 缓解                                                                                                  |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 主表 36 列 + 三级表头列配置繁琐，易错                      | 列配置抽到 `config/columns.ts` 用 `children` 嵌套数据驱动渲染，单元测试校验列结构与 colspan 总数      |
| 组件可能超过 400 行限制                                    | 严格拆分：主表、面板、每个 Tab、每个 Modal 各自独立组件；工具栏独立                                   |
| mock 数据量大，手写易出错                                  | mock 数据结构用 TS 类型约束，单元测试校验字段完整性                                                   |
| E2E 在无后端时可能不稳定                                   | dev 模式下 `vite-plugin-mock` 天然拦截 API 返回 mock 数据，E2E 稳定；后端就绪后删除 mock 文件即可     |
| 设计稿用 Tailwind，仓库已有 Tailwind 4 但样式规范要求 less | 优先用 less + 既有 token，Tailwind 工具类仅用于布局（flex/grid/spacing），颜色/圆角/阴影用 less token |
| 单 commit ≤1000 行限制（仓库 AGENTS.md Rule 4）            | 分多轮交付，每轮一个 commit：①类型+API+mock ②工具栏+主表 ③下钻面板 ④Modal ⑤测试                       |

## 跨仓影响

无跨仓接口契约变化。`openlibing-docs` 仅新增 spec 文档，不影响其他仓。
