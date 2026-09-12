# NPU 资源看板 — 需求提案

- 业务 Issue：https://gitcode.com/openlibing/openlibing-ops-web/issues/40
- 目标仓：`openlibing-ops-web`
- 开发分支：`feat-resource`
- 流程模式：**Full**
- 设计稿：`ResourceOverview0818_optimized.html`（主页面）、`PoolDrawer.html`（资源池明细抽屉）

> 本文件为需求提案的**实现后回写版**：功能描述、不做什么、验收标准均已按落地代码更新（对接真实后端接口、三热力图、双线图与热力合并单卡、运行分析面板调整等），与当前实现保持一致。

## 需求背景

当前 NPU 资源数据分散在「工程能力运营看板」的一个内嵌页签（`npu-resource-panel.vue`）中，仅有 5 个 KPI 与「资源池 → 服务器」两层表格。这个视图只能回答"用了多少卡时"，无法回答运营真正关心的三个问题：

1. **分配了但没用起来的浪费有多少？** 现有视图没有「分配率 vs 使用率」的对照维度。
2. **浪费集中在哪台机器、哪个时段？** 缺少服务器 × 小时的二维视图。
3. **是谁造成的排队？** 缺少项目 → 流水线 → 单次运行的归因链路。

因此新建独立的 NPU 资源看板页面，提供 **资源池 → 服务器 → 项目 → 流水线 → 单次运行** 的完整下钻链路，并把「分配率 − 使用率」作为一等公民指标贯穿全页。

## 功能描述

### 做什么

新增前端页面 `/dashboard/npu-resource`，由 1 个主页面 + 2 个抽屉 + 1 个内嵌分析面板组成。

#### 主页面（5 个区块，自上而下）

| #   | 区块            | 内容                                                                                                                                                                                                                                                                                                                               |
| --- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 时间范围工具条  | 快捷项**仅两个：`昨日` / `最近一周`**（均以昨日收尾，不含当天）+ 自定义区间（最晚到昨日，跨度**硬上限 7 天**）；复用共享组件 `time-range-filter.vue`（segmented 快捷项 + 日期区间）；今日及未来、早于最小可选日期（2026-08-20）、超过 7 天跨度的日期由 `disabled-date` 直接禁用；右侧「数据更新于」时间戳（来自 `getRefreshTime`） |
| 2   | KPI 卡 ×4       | `资源池数量` / `资源总量` / `分配率` / `NPU 使用率`；**每卡内含「华为云 / 实验室」双行对比**；`资源总量`卡按代际显示 tag（如 `A5 (3卡)`），其余卡显示数值 + 单位；底部「查看资源池明细 →」入口                                                                                                                                     |
| 3   | NPU 趋势图      | 折线图，`资源池`/`代际` 维度切换 + `el-select-v2` 多选下拉筛选分组（带色点）；实线 = 分配率，虚线 = 使用率；Y 轴 0–100%                                                                                                                                                                                                            |
| 4   | 服务器 NPU 热力 | 三级联筛选（资源池 / 代际 / 服务器 IP，IP 可搜索确认）+ **3 个独立热力图**：效率分析（分配率 − 使用率）/ 分配率明细 / 使用率明细，各自支持全屏                                                                                                                                                                                     |
| 5   | 项目资源效率表  | 4 列：项目名称（可点击下钻）/ PR 资源排队时长 P90 / PR NPU 消耗 / NPU 使用率；开启分页，默认每页 20                                                                                                                                                                                                                                |

#### 资源池明细抽屉（KPI 卡 →「查看资源池明细」）

- **80%** 宽右侧抽屉，标题 `资源池明细`，副标题随时间范围联动
- 3 个资源池**手风琴行**（各自独立开合，非互斥，首个默认展开）
- 折叠态：caret + 池名 + 类型徽标（`华为云` / `实验室`）+ 使用项目 chip 组 + 右侧 `分配率`/`使用率`
- 展开态：6 列机器明细表（`机器 IP` / `总卡时` / `分配卡时` / `使用卡时` / `分配率` / `使用率`），用 `base-table`，后两列为数值 + 迷你占比条
- 数据来自 `getCommonDetail`（`category: 'ops-resource-pool-detail'`），按时间范围参数拉取

#### 项目下钻抽屉（项目表 → 点击项目名）

- 80% / min-width 880px 抽屉，标题 `项目下钻 · {项目} · {时间范围}`
- 项目概要统计条（**3 项**：PR 资源排队时长 P90 / PR NPU 分配 / NPU 使用率 + 资源池 pill）
- **单卡 `project-heat-card`**：流水线资源分配热力（项目关联服务器 × 小时）+ 每小时「资源申请次数」/「总排队时长」双线图（实线 + 警示色虚线）并列展示，含服务器 IP 筛选
- 流水线资源效率表（**5 列**：流水线 / 类型 / 排队 P90 / 分配卡时 / 运行次数，`PR`/`Nightly` 分段切换），开启分页，默认每页 20；操作列「查看运行明细」

#### 流水线运行明细分析面板（流水线表 →「查看运行明细」）

- 面包屑 `项目效率 › {项目} › {流水线} 运行分析`，可回退 + 运行上下文行（CPU 图标 + 流水线名 + 类型徽标）
- 运行明细表 7 列 + 操作列（状态徽标；`highlight-current-row` 默认选中首行并自动加载 NPU 分析；操作列「查看NPU使用」单选定位）
- `NPU 分配率分析` / `NPU 使用率分析` 两个**自绘 DOM 网格热力图**（1 小时/格、7 级色阶；窗口宽度由接口返回的 `timeLabels` 决定，非固定 4 小时）
- 每个测试任务一条排队 / 运行连线标记（空心起点 + 实心终点 + 文字胶囊），hover 显示内联原生 tooltip（运行 ID、起止、时长、分配机器、使用卡时）

### 不做什么

- **前端已对接真实后端接口**（`/gateway/.../resource-operation/*`），不再依赖 `/mock`；`mock/npu-resource.ts` 已注释停用，接口签名以 `src/api/dashboard/npu-resource.ts` 为准。
- 不改动现有「工程能力运营看板」的 `npu-resource-panel.vue` 及其页签，两者并存（后续是否下线由产品另行决策）。
- 不做导出功能（设计稿工具条中的「导出」已在原型中移除）。
- 不做项目搜索 / 排序控件（设计稿中 `#projSearch`、`#projSortBtn` 的 DOM 已移除，仅残留失效 JS）。
- 不做真实权限控制（沿用 `dashboard` 父路由既有约束）。
- 不做移动端适配，仅保证 ≥768px 的响应式降级。
- 不做排队时长 ≥ 10min 的表内警示色（`QUEUE_WARN_THRESHOLD` 常量已声明但未应用于表格渲染）。
- 不做运行分析「定位结论」卡（设计稿底部结论区未移植）。

## 验收标准

- [ ] 路由 `/dashboard/npu-resource` 可访问，页面 title 为 `NPU 资源看板`
- [ ] `npm run dev` 下三个热力图、趋势图、三张表格、两个抽屉、分析面板均可交互
- [ ] 时间范围切换后趋势图与三个主热力图同步刷新；抽屉内副标题文案同步
- [ ] 时间快捷项只有 `昨日` 和 `最近一周` 两个，均以昨日为区间末端（不含当天）；日期选择器禁用今天及未来、早于最小可选日期（2026-08-20）的日期
- [ ] 自定义区间超过 7 天跨度时，超出范围的选择由 `disabled-date` 禁用（无独立「应用」按钮与校验文案）
- [ ] 三级联筛选具备级联收敛：`代际` 选项收敛到已选资源池存在的代际，`服务器 IP` 收敛到匹配的机器；不可用选项直接从列表收敛移除（不渲染 `{值} (无)` 禁用态）；IP 选项数 ≤5 时隐藏搜索框
- [ ] `重置` 同时刷新三个热力图（效率 / 分配率明细 / 使用率明细）
- [ ] `代际` 维度切换不报错
- [ ] 抽屉内服务器 IP 筛选实际生效
- [ ] 三个热力图均支持全屏（`FullscreenView`），全屏后自适应重绘
- [ ] 所有卡片容器使用 `base-card`；**全页不出现 `<section>` 元素**
- [ ] 所有指标数字使用 `tabular-nums`
- [ ] 效率差值取 `|分配率 − 使用率|`（`Math.abs`，非 `max(0, …)`）
- [ ] 尊重 `prefers-reduced-motion`（抽屉滑入、卡片抬升、shimmer 全部降级）
- [ ] 所有 Props / 数据结构定义 TS `interface`，无 `any`
- [ ] 数据加载统一使用 `to()` 包装
- [ ] 单元测试覆盖：`config/columns` 契约、`utils` 纯函数（色阶分档、热力数据构造、趋势 option、运行分析视图转换）、KPI 卡、资源池抽屉行、时间范围工具条组件渲染
- [ ] `npm run lint` / `npm run format` / `npm run test:unit` / `npm run type-check` 全部通过

## 复用清单（用户硬性要求：使用已有公共内容）

| 类别 | 复用项                                                                                                         | 位置                                                                                           |
| ---- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 样式 | `base-card` / `base-card--hover-shadow` / `base-card--hover-lift`                                              | `src/assets/style/card.less`                                                                   |
| 样式 | `.text-link`、`.status-dot`、`.status-badge`                                                                   | `src/assets/style/common.less`                                                                 |
| 组件 | `base-table`（明细表、流水线表、运行明细表）                                                                   | `src/components/base-table.vue`                                                                |
| 组件 | `ChartsUI` + `useCharts`（趋势图、3 个 ECharts 热力图）                                                        | `src/plugins/charts`                                                                           |
| 组件 | `time-range-filter.vue`（时间范围快捷项 + 日期区间，`minDate` 夹取）                                           | `src/views/dashboard/components/time-range-filter.vue`（由 `engineering-capability` 抽取共享） |
| 类型 | `ColumnProps` / `PagerProps`                                                                                   | `src/types/table.ts`                                                                           |
| 函数 | `to()` Promise 错误包装                                                                                        | `src/utils/promise.ts`                                                                         |
| 函数 | `formatValue` / `formatFloat` / `isValueEmpty`                                                                 | `src/utils/format-value.ts`                                                                    |
| 常量 | `EMPTY_VALUE`（`--`）                                                                                          | `src/constants/index.ts`                                                                       |
| 口径 | 既有 NPU 字段命名（`usedNpuHours` / `totalNpuHours` / `npuRate` / `resourcePoolName`）                         | `engineering-capability/config/columns.ts`                                                     |
| 模式 | 抽屉实现范式（`defineModel` + `destroy-on-close` + `tableHeight` 计算）                                        | `github/components/pr-detail-drawer.vue`                                                       |
| 模式 | 骨架 shimmer / 响应式 KPI grid / 模块 `style.less` 前缀化                                                      | `dashboard/code-check/`                                                                        |
| 模式 | provide/inject 下钻上下文（`N_R_DETAIL_PARAMS_KEY`，传递 `projectId`/`projectName`/`projectRow`/`dateParams`） | `npu-resource-view.vue` 定义，下钻链路各组件 `inject`                                          |

## 约束与冲突记录

| #   | 事项                                                                                                                | 处理                                                                                                                                                                                                                   |
| --- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `/mock` 目录在 `.gitignore` 第 33 行，mock 文件**无法提交**                                                         | 按 `ai_memory.md` 规则仍放 `/mock`。**已对接真实后端接口后 `mock/npu-resource.ts` 整体注释停用**。单测不依赖 mock 目录，改用测试内 fixture，保证 CI 可复现                                                             |
| 2   | `ai_memory.md` 写「代码中不写任何注释」，但现网新代码（`code-check`、`base-kpi-card`）普遍带 JSDoc                  | **用户裁定：严格遵循 `ai_memory.md`，本次新增代码不写任何注释**（含 JSDoc、行内注释、模板注释）。既有文件不回改。命名需自解释以补偿注释缺失                                                                            |
| 3   | `ai_memory.md` 写「优先 Tailwind、少写 style 块」，但 `code-check`/`test-dashboard` 实为 `style.less` + scoped less | **用户裁定：严格遵循 `ai_memory.md`，优先 Tailwind utility classes**。`style.less` 仅保留 Tailwind 无法表达的部分（见 design.md D12）                                                                                  |
| 4   | 用户要求卡片用 `base-card`，但 `BaseKpiCard` 是**单值卡**，设计稿 KPI 是双行对比卡                                  | 新建页面级 `npu-kpi-card.vue`，容器沿用 `base-card` 类，满足样式统一要求；不改动 `BaseKpiCard` 以免影响 code-check                                                                                                     |
| 5   | 用户要求不用 `<section>`，但参考实现 `code-check-view.vue` 用了                                                     | 新代码全部用 `<div>`，不回改 code-check（避免无关重构）                                                                                                                                                                |
| 6   | ECharts 未注册 `HeatmapChart` / `VisualMapComponent` / `GraphicComponent`                                           | 在 `src/plugins/charts/echarts.ts` 追加注册 + 扩展 `ECOption`。纯追加，对既有图表零影响。实现中 `GraphicComponent` 实际未使用（三热力图方案不需要双栅格虚线分隔）                                                      |
| 7   | `origin` 直指主仓 `openlibing/openlibing-ops-web`，非 fork                                                          | Phase 4 建 PR 前需与用户确认 head 分支归属与 base 分支（已通过跨仓 PR 合入 release 分支）                                                                                                                              |
| 8   | `ai_memory.md` 写「禁止内联 `style=` 属性」，但迷你占比条宽度、连线标记百分比定位是数据驱动的动态值                 | 静态样式一律 Tailwind / class，不出现静态内联样式。**动态值走 `:style` 绑定 CSS 自定义属性**（如 `:style="{ '--npu-bar-w': pct + '%' }"`），宽度/定位在 class 中读该变量，把内联面从「任意样式」收窄为「单个数值变量」 |

## 设计稿原型缺陷（移植时须修复，不照抄）

| #   | 缺陷                                                                                             | 修复方式                                     |
| --- | ------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| 1   | `#trendSubtitle` 不存在 → 点「代际」抛异常，代际视图不可达                                       | 副标题作为响应式文本渲染，不依赖 DOM 查询    |
| 2   | `#heatReset` 只刷 `renderHeat()`，漏 `renderHeatEff()`                                           | 重置走统一状态，三个热力图由同一响应式源驱动 |
| 3   | 抽屉 `applyProjHeatFilter` 用服务器 `name` 比对 IP 键的筛选表 → IP 筛选恒失效                    | 统一以 IP 为筛选键                           |
| 4   | `.proj-row` 声明 5 列网格但只渲染 4 格（残留「操作」列）                                         | 改为 4 列布局                                |
| 5   | `--npu-heat-use-0..6` 被 `.hm-use-*` 引用但从未定义                                              | 分配率/使用率热力共用同一套 7 级色阶         |
| 6   | 大量失效 CSS / 数据字段（`.ov-concl*`、`.hm-*`、`.proj-mini*`、`Project.spark`、`Run.endHr` 等） | 不移植。「定位结论」卡、排队警示色等未落地   |

## 关联

- 业务 Issue：https://gitcode.com/openlibing/openlibing-ops-web/issues/40
- 既有 NPU 视图 spec：`../npu-resource-view/`
- 最近同类看板 spec（架构参考）：`../code-check-dashboard/`
