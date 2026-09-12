# NPU 资源看板 — 实现任务

- 业务 Issue：https://gitcode.com/openlibing/openlibing-ops-web/issues/40
- 提案：`./proposal.md`　技术设计：`./design.md`
- 开发分支：`feat-resource`（5 阶段原始交付）→ 经 release 分支合并（!117/!118 → `release_20260824`，!120 → `main`；!122 `dev_20260825` → `release_20260831`，!123 → `main`）
- 交付节奏：5 阶段各一次交付 + 多轮重构/联调收口（对接真实后端），最后合入 release 分支

> 本文件为**实现后回写版**：任务清单与验证记录均已按落地代码更新（真实后端对接、三热力图、`project-heat-card` 合并、去 popover、`disabled-date` 校验等），全部任务已完成。

## 进度: 全部完成（5 阶段 + 3 轮重构/收口 + 后续修复）

### 阶段 A — 基础设施

- [x] A1: 扩展 `src/plugins/charts/echarts.ts`：注册 `HeatmapChart` / `VisualMapComponent` / `GraphicComponent`，`ECOption` 追加 3 个联合类型
- [x] A2: 新增 `src/types/npu-resource.ts`：`NpuSummaryResp` / `NpuTrendResp` / `NpuHeatResp` / `NpuHeatServer` / `NpuRunAnalysisResp` / `NpuProjectAllocTrendResp` / `NpuProjectEfficiencyItem` / `NpuPipelineEfficiencyItem` / `NpuRunItem` / `NpuPoolDetail` 等 interface（无 `any`），后按接口文档对齐
- [x] A3: 新增 `src/api/dashboard/npu-resource.ts`：`getNpuSummary` / `getNpuTrend` / `getNpuHeatmap` / `getNpuRunAnalysis` / `getNpuProjectAllocTrend`，表格/资源池明细复用 `getCommonDetail`（`category`：`ops-project-efficiency` / `ops-pipeline-efficiency` / `ops-pipeline-run-detail` / `ops-resource-pool-detail`）
- [x] A4: `src/api/dashboard/index.ts` 追加 `export * from './npu-resource';`
- [x] A5: `mock/npu-resource.ts` 曾用于联调，**已注释停用（gitignored）**——最终不依赖 mock，全部走真实后端
- [x] A6: 新增路由 `NpuResource`（`path: 'npu-resource'`，`meta.title: 'NPU 资源看板'`）到 `src/router/routes/modules/dashboard.ts`
- [x] A7: 新增 `config/constants.ts`（`HEAT_COLORS` 7 色 / `TREND_PALETTE` 12 色 / `NPU_TIME_QUICK_OPTIONS` / `QUEUE_WARN_THRESHOLD` / `MAX_TIME_SPAN_DAYS` / `NPU_MIN_SELECTABLE_DATE`）+ `utils.ts` 纯函数（`heatLevelForPct` / `resolveHeatValue`（`Math.abs` 口径）/ `reconcileHeatFilters` / `filterServers` / `buildMarker` / `toRunAnalysisView` / `colorizeTrendGroups` / `buildTrendTooltip` / 热力 option 构造器）。原 `validateTimeSpan` / `resolveQuickRange` / `buildHourLabels` / `effDiff`（`max(0, …)`）随 `disabled-date` 校验与绝对值口径改造后移除
- [x] A8: 新增 `config/columns.ts`：`npuProjectColumns`(4) / `npuPipelineColumns`(5) / `npuRunColumns`(7)（机器列不在此，见阶段 D——`machineColumns` 内联在 `pool-detail-row.vue`）

**阶段验证**：`npm run type-check` 通过；`utils` + `columns` 单测先行。

### 阶段 B — 主页面骨架与上半部分

- [x] B1: 新增 `npu-resource-view.vue`：薄入口，持有 `dateRange` / `refreshTime` / `poolDrawerVisible` / `projectDrawerVisible` + 下钻项目三元组，provide 下钻上下文（`N_R_DETAIL_PARAMS_KEY`），组装子组件；根容器 `.bg-slate-50` + `base-card` 组合
- [x] B2: 新增 `style.less`：仅热力色阶（`.npu-heat-0`…`.npu-heat-6`）、shimmer 关键帧、`prefers-reduced-motion` 降级、Element Plus 深度覆盖；布局 / chip / seg / 徽标 / 迷你占比条一律 Tailwind utility，组件内无 `<style scoped>`
- [x] B3: 新增 `npu-time-range-toolbar.vue`：复用共享组件 `time-range-filter`（quick options 仅「昨日 / 最近一周」）+ `min-date = 2026-08-20` + `disabled-date` 三重禁用（今天及未来 / 早于最小日期 / 跨度 > 7 天）+ 右侧「数据更新于」时间戳，容器 `base-card`。**无「应用」按钮、无 4 档校验文案**（`validateTimeSpan` 废弃，非法选择由 disabled-date 直接禁止）
- [x] B4: 新增 `npu-kpi-card.vue`：双行对比卡（`base-card` + `base-card--hover-lift`），header（标题 + 图标）/ body（华为云 / 实验室两行）/ footer（`查看资源池明细 →`，emit `view-pool-detail`）
- [x] B5: 新增 `npu-kpi-cards.vue`：4 卡响应式 grid（>1100px 4 列 / 768–1100 2 列 / <768 1 列）+ 骨架态；KPI 总量按代际 tag
- [x] B6: 新增 `npu-trend-chart.vue`：`ChartsUI` 折线图；资源池/代际分段切换 + `el-select-v2` 分组筛选（实线分配 / 虚线使用），分组配色 `TREND_PALETTE` 按 index 循环取色；自定义 tooltip（`buildTrendTooltip`，实心/空心 + 折叠+ / 显隐逻辑）

**阶段验证**：`npm run dev` 下工具条时间切换生效、KPI 卡数值与双行布局正确、趋势图两个维度均可切换不报错。

### 阶段 C — 热力图与项目表

- [x] C1: 新增 `npu-heatmap-filters.vue`：三级联筛选（pool / gen / ip 三组 `Record<string, boolean>`），**不可用选项直接收敛移除**（不渲染 `{值} (无)` 禁用态）；IP 选项数 ≤5 隐藏搜索框、>5 需输入确认选择；`重置` 清空三个 map
- [x] C2: 新增 `npu-heatmap-panel.vue`：容器（`base-card`）+ 筛选 + **三个独立热力图**：`效率分析（分配率 − 使用率）` / `分配率明细` / `使用率明细`，各 400px 高、`FullscreenView` 全屏（`change` 事件驱动 `chart-renderer` 重绘）、`dataZoom` 按容器宽度决定是否滚动；三图由同一 `filteredServers` computed 派生（三级筛选天然同步）
- [x] C3: 热力 tooltip：统一 `buildHeatTooltip` —— `{IP}（{代际}·{资源池}）` + `时间：` + 分配率 / 使用率 / 效率差三项 + 运行业务 job 列表，空值 `--`；效率差口径 = `Math.abs(分配率 − 使用率)`
- [x] C4: 新增 `project-efficiency-table.vue`：`base-table` + `npuProjectColumns`(4)，项目名列 `text-link` 可点击（emit `drill`），分页 small；容器 `base-card`

**阶段验证**：三级联筛选收敛正确、`重置` 三图同步刷新、时间范围切换三图同步、点击项目名能触发下钻事件。

### 阶段 D — 两个抽屉

- [x] D1: 新增 `pool-detail-row.vue`：手风琴行（caret 旋转 + `aria-expanded`）+ 类型徽标（`云上`/`实验室`）+ 展开区 6 列机器表（机器 IP / 总卡时 / 分配卡时 / 使用卡时 / 分配率 / 使用率，后两列含迷你占比条）；`machineColumns` 内联定义在组件内，数据由 `getCommonDetail({ category: 'ops-resource-pool-detail' })` 一次性拉取后用 `base-table`（`pager-show=false` + `border=false`）渲染
- [x] D2: 新增 `pool-detail-drawer.vue`：**80%** `el-drawer`（`direction="rtl"`），头部标题 + 随时间范围联动的副标题、3 个手风琴行（首个默认展开、独立开合）
- [x] D3: 新增 `project-summary-stats.vue`：项目概要统计条（stats 列表渲染），数据源为下钻传递的 `projectRow`（效率行），非独立接口；警示值上警示色
- [x] D4: **合并**原 `project-request-chart.vue` + `project-heatmap-chart.vue` 为单一 `project-heat-card.vue`：资源申请次数（实线）/ 每小时总排队时长（警示色虚线）双线图 + 项目关联服务器 × 小时分配热力（`buildProjectHeatmapOption`），两实例并列一卡；加载态用统一骨架
- [x] D5: 新增 `pipeline-efficiency-table.vue`：`base-table` + `npuPipelineColumns`(5)：流水线名称 / 类型（PR·Nightly 徽标）/ 资源排队时长[P90](min) / 分配卡时 / 运行次数 + 操作列「查看运行明细」（emit `view-runs`）；分页 small
- [x] D6: 新增 `project-drill-drawer.vue`：80% / `min-width: 880px` `el-drawer`，面包屑（`项目效率 › {项目} › {流水线} 运行分析`，点「项目效率」返回）；body 双态：`v-show="!activePipeline"` 概要（`ProjectSummaryStats` + `ProjectHeatCard` + `PipelineEfficiencyTable`）/ `v-if="activePipeline"` 运行分析面板；图表 resize 由 `chart-renderer` 按 DOM 变化重置（无 `@opened` + `setTimeout`）

**阶段验证**：KPI 卡入口能打开资源池抽屉且手风琴独立开合；项目名能打开下钻抽屉、概要/热力卡/流水线表齐全；抽屉内热力/趋势实际生效。

### 阶段 E — 第三层分析面板与测试收口

- [x] E1: **移除** `run-marker-popover.vue`——标记浮层改为原生 `:title` tooltip（任务名 · 时长 min · 起止），无 teleport 浮层；标记数据由 `utils.buildMarker`（按 mode 决定时长/起止字段）统一构造，组件内不再内联
- [x] E2: 新增 `run-marker-heatmap.vue`：自绘 DOM 网格（`180px + repeat(n, 1fr)`，列数 = `timeLabels.length` 小时数，非固定 4 小时）+ 7 级色阶数值格 + 每任务一行连线标记（百分比定位、双端点、可聚焦文字胶囊）+ 无运行机器整行降透明 + 两套图例（分配：申请开始/分配成功/等待区间；使用：使用开始/使用结束/使用区间）；跨午夜窗口处理（`secondsBetween` 负差 +24h）
- [x] E3: 新增 `run-analysis-panel.vue`：面包屑 + 运行上下文行 + 运行明细表（`base-table` + `npuRunColumns`(7)，状态徽标、`分析 NPU` 高亮导航）+ `NPU 分配率分析` / `NPU 使用率分析` 两块网格热力图（复用 `run-marker-heatmap`）。**无「定位结论」卡**（字段按接口文档对齐后移除）
- [x] E4: 新增 `__tests__/utils.test.ts`：`heatLevelForPct` 7 档边界、`resolveHeatValue`（`Math.abs` 口径）、`reconcileHeatFilters` 级联收敛、`filterServers`、`buildTrendTooltip` / 热力 option、`toRunAnalysisView` / `buildMarker`（alloc/usage 模式、跨午夜）、`colorizeTrendGroups`
- [x] E5: 新增 `__tests__/columns.test.ts`：4 组列配置契约断言（列数、`prop`、`label`、`sortable`、`align`、`unit`）
- [x] E6: 新增 `__tests__/npu-kpi-card.test.ts`：双行渲染、`base-card` 类存在、空值 `--` 降级、`view-pool-detail` emit
- [x] E7: 新增 `__tests__/pool-detail-row.test.ts`：折叠/展开切换、`aria-expanded` 同步、6 列表头、占比条宽度
- [x] E8: 全页自检：无任何注释（JSDoc / `//` / `/* */` / `<!-- -->`）、无 `<section>` 元素、卡片均用 `base-card`、静态样式无内联 `style=`（动态值走 `:style` 绑定 CSS 变量）、无 `any`、数据加载均用 `to()`、指标均 `tabular-nums`
- [x] E9: 质量门禁：`npm run lint` / `npm run format` / `npm run test:unit` / `npm run type-check` 全部通过

**阶段验证**：第三层下钻完整可用（表→网格→标记→tooltip）；四项质量门禁全绿。

## 交付后流程（实际状态）

- [x] 用户自测 / 反馈循环：已完成多轮，覆盖真实后端联调、视觉效果与交互打磨
- [x] Phase 4：业务 PR 通过 release 分支合入——!117 / !118 合并 `feat-resource` → `release_20260824`，!120 → `main`；!122 `dev_20260825` → `release_20260831`，!123 → `main`；`ai-assisted` 标签已补打
- [ ] Phase 5：最终归档（`archive.md` + `ai_memory.md` 增量，docs PR）——**待用户明确触发**

## 验证记录

### 阶段 A

- 状态：✅ 已完成
- 内容：types / api / mock（gitignored）/ charts 插件 / 路由 / utils / columns + 单测
- 验证：`npm run type-check` 通过；`vitest run src/views/dashboard/npu-resource` 全绿

### 阶段 B

- 状态：✅ 已完成
- 内容：npu-resource-view.vue 薄入口 + style.less + npu-time-range-toolbar.vue + npu-kpi-card/c-ards.vue + npu-trend-chart.vue；样式全部 Tailwind utility，组件内无 `<style scoped>`
- 验证：`npm run type-check` 通过（npu-resource 0 报错）；`eslint src/views/dashboard/npu-resource --quiet` 0 错误；`vitest` 全绿；lint-staged + stylelint + prettier 门禁通过

### 阶段 C

- 状态：✅ 已完成
- 内容：npu-heatmap-filters.vue（三级联筛选）+ npu-heatmap-panel.vue（热力图）+ project-efficiency-table.vue（base-table + 下钻 emit + 分页）+ npu-resource-view.vue 接入
- 验证：`npm run type-check` 通过（npu-resource 0 报错）；`eslint src/views/dashboard/npu-resource --quiet` 0 错误；`vitest run src/views/dashboard/npu-resource` 全绿

### 阶段 D

- 状态：✅ 已完成
- 内容：pool-detail-row.vue + pool-detail-drawer.vue + project-summary-stats.vue + project-request-chart.vue + project-heatmap-chart.vue + pipeline-efficiency-table.vue + project-drill-drawer.vue + npu-resource-view.vue 接入两抽屉
- 验证：`npm run type-check` 通过；`eslint src/views/dashboard/npu-resource --quiet` 0 错误；`vitest` 全绿

### 阶段 E

- 状态：✅ 已完成
- 内容：run-analysis-panel.vue + run-marker-heatmap.vue + run-marker-popover.vue（后移除）+ `__tests__` 4 个文件
- 验证：`npm run lint` / `npm run format` / `npm run test:unit` / `npm run type-check` 四项门禁全绿

### 轮次 R1 — 真实后端对接重构

- 状态：✅ 已完成（多轮收口）
- 内容：mock 停用，全部切换真实接口；`getNpuServerHeat`/`getNpuPoolDetail`/`getNpuProjectDrill` 调整为 `getNpuHeatmap`/`getNpuRunAnalysis`/`getNpuProjectAllocTrend` + `getCommonDetail`
- 验证：`npm run type-check` / `lint` / `test:unit` 全绿

### 轮次 R2 — 运行分析双热力 + 项目分配趋势

- 状态：✅ 已完成
- 内容：`project-request-chart` + `project-heatmap-chart` 合并为 `project-heat-card`；运行分析由单网格扩展为 alloc/usage 双网格；`toRunAnalysisView` / `buildMarker` 落地
- 验证：`npm run test:unit` 全绿

### 轮次 R3 — 三热力图 + 全屏

- 状态：✅ 已完成
- 内容：双栅格热力拆分/新增为「效率分析 / 分配率明细 / 使用率明细」三个独立热力图，各带 `FullscreenView`
- 验证：`npm run type-check` / `lint` / `test:unit` 全绿

### 轮次 R4 — 时间 / 导航 / 细节打磨

- 状态：✅ 已完成
- 内容：时间选择限制 ≥ 2026-08-20；IP 搜索确认 + 运行分析导航；IP 选项 ≤5 隐藏搜索；运行卡显示运行 ID；标记胶囊定位与图例打磨；趋势 tooltip 可滚动并保持在视口；`buildMarker` 按 mode 解析运行标记；自定义趋势 tooltip 共享 margin；测试断言对齐
- 验证：`npm run type-check` / `lint` / `test:unit` 全绿

### 后续修复（release 合入后）

- 状态：✅ 已完成
- 内容：趋势图右缘与热力绘图区对齐；资源池明细列表填满抽屉 body；可选的资源池名 + tooltip 边界修正；修正源码变更后的陈旧单测
- 验证：`npm run test:unit` 全绿
