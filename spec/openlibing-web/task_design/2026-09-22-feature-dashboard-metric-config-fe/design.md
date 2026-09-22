## Context

特性看板前端 `FeatureDashboard` 由 `index.vue`（矩阵总览）、`StatusMatrix.vue`（社区×特性矩阵，仅展示特性状态、不涉及指标）、`DetailDrawer.vue`（详情抽屉，按周期/社区查指标）、`MetricCard.vue`（单指标卡片，含完成率进度条）、`MetricConfigDialog.vue`（指标配置弹窗外壳与保存动作）组成；配置弹窗的分组表格模板在 `MetricConfigGroup.vue`，行编辑状态机在 `useMetricEditing.ts`，表单构建/展示文案/行校验在 `metricConfigForm.ts`，编辑上下文在 `metricEditContext.ts`。数值工具按职责拆分：`formatters.ts`（`calcRate`/`resolveMetricNumeric`/`formatMetricValue`/`parseLastValueMetric`）、`matrixAdapter.ts`（matrix 归一化）、`metricPayload.ts`（`toCreatePayload`/`toUpdatePayload`/`normalizeMetricConfig`），`utils.ts` 保留为兼容 re-export。`resolveMetricNumeric` 按值形态驱动判定比率形态。载荷组装在 `metricPayload.ts`，由 `useDashboard` 调用。详见 proposal.md - Why。

## Goals / Non-Goals

**Goals:**

- 配置弹窗拆六独立配置项（指标类型/聚合方式/全部列计算/社区列展示开关/目标维度/目标类型），与后端六字段一一对应；聚合方式支持求和/平均/不聚合。
- 目标值"启用开关（`targetEnabled`）+ 目标维度联动"：community 模式社区子表，feature 模式单值输入；保存载荷按 `targetEnabled` 裁剪目标字段。
- 比率型禁用"全部列计算"项。
- `MetricCard` 按维度+类型+位置选完成率/贡献率标签、目标标签与公式：全部列统一"目标完成率"；消减目标一律不计算率（社区列与全部列均无进度条）。
- "仅全部列展示"（`communityColumnVisible=false`）指标在社区列过滤隐藏。
- 兼容后端仅返回旧 `aggregationType`/`targetDirection` 的过渡期响应（含缺 `targetEnabled` 时按目标值存在性推导）。

**Non-Goals:**

- 不改 `StatusMatrix.vue` 矩阵状态逻辑与 `index.vue` 统计卡。
- 不在前端做全部列二次聚合（口径由后端负责）。
- 不引入新 UI 组件库或新依赖。
- 不细化完成率/贡献率着色分档（本期暂不细化，统一达标/未达标二色或不区分）。
- 不改 `DetailDrawer.vue` 周期/社区切换交互骨架，仅调 `MetricCard` 入参与展示。

## Decisions

### Decision 1: 配置弹窗拆六列，保留行内编辑模式

**选择**：`MetricConfigDialog.vue` 拆为六列（指标类型/聚合方式/全部列计算/社区列/目标维度/目标类型），指标类型/聚合方式/全部列计算/目标维度/目标类型为 `el-select`，"社区列"用 `el-switch`（开启=社区列与全部列均展示，默认开启；关闭=仅全部列展示，对应 `communityColumnVisible=false`；原设计字段 `allColumnOnly` 与开关语义相反，未发布直接改名并反转语义使开关值与字段值直对应；非编辑态以只读 `el-switch` 直显开关态，与"目标"开关一致），复用既有行内编辑模式与 `metric-config__edit-col` 样式。（表格模板已落位于 `MetricConfigGroup.vue`，编辑状态机在 `useMetricEditing.ts`，经 `metricEditContext.ts` 下发；非编辑态"目标"等开关取值在响应缺 `targetEnabled` 时按目标值存在性推导兜底，与 Decision 7 兼容口径一致。）

**理由**：弹窗已有成熟行内编辑模式，新增列零额外组件、视觉一致；六项独立可配满足正交配置需求。

**备选**：抽屉式分步表单——破坏交互一致性、增步骤，不采用。

### Decision 2: 目标值开关单独成列"目标" + 目标维度/类型联动

**选择**：目标值开关单独成列"目标"（非编辑态以只读 `el-switch` 直显开关态，不渲染"是/否"文字）；目标相关列顺序：目标 → 目标维度 → 目标类型 → 目标值 → 单位。开关状态以显式字段 `targetEnabled` 同步到请求与响应：关闭时三列（目标维度/目标类型/目标值）禁用并展示"--"，**单位列始终可编辑**（单位为指标自身属性，无目标指标也可配置单位用于当前值展示）；保存请求携带 `targetEnabled=false` 与 `unit`、省略 `targetType`/`targetDimension`/`targetValue`/`communityTargets`（后端负责清空目标存储；单位按指标属性保留，需后端同步调整原"无目标清空单位"行为）；开启时按 `targetDimension` 展开——community 模式社区子表（触发文案"N 社区目标"），feature 模式单个目标值输入框；切换指标类型为比率时单位自动设为"%"（不依赖目标开关），切离比率保留已填单位；切换维度清空另一形态。开关 off→on 保留已填社区目标值（仅保存时按 `targetEnabled` 裁剪目标字段）。

**理由**：开关单独成列使"是否有目标"语义明确，与目标值列区分；非编辑态只读开关比"是/否"文字更直观；off→on 保留值避免误操作丢失输入；显式 `targetEnabled` 字段消除"无目标时仍传空目标字段"的请求噪音，与后端契约一一对应。

**备选**：开关嵌入目标值列——开关与值混在一列语义不清，不采用；仅靠目标值存在性隐式推断启停——语义不显式且无法表达开关中间态，不采用。

### Decision 3: 目标语义改为"目标类型"（增长/消减），率公式统一为实际/目标

**选择**：原"目标方向"（正向/负向，`targetDirection` higher_better/lower_better）改为"**目标类型**"（`targetType`：`growth` 增长 = 越大越好 / `reduction` 消减 = 越小越好）。率公式统一为 `实际值/目标值 ×100%`，达标判定按类型：增长 ≥100% 达标。**消减目标一律不计算率**（社区列与全部列均无进度条，仅展示目标标签与目标值）；增长目标照常计算（community 维度社区卡完成率=实际/社区目标、feature 维度社区卡贡献率=社区实际/总体目标、全部列完成率=全部列实际/全部列目标）。率计算函数为 `calcRate(current, target)`（不接收 targetType 参数），消减目标的"不计算率"由 `MetricCard` 的 `attainment` 计算承担（reduction 直接返回 null）；率值封顶 999（进度条宽度另行封顶 100%）。

**理由**：用户明确要求用"增长/消减"替代"正向/负向"；消减语义下"社区贡献率/完成率"无业务含义（单社区消减进度无法归因），故消减目标不计算率；统一公式消除了原 lower→target/actual 反转与负值手动取负的复杂逻辑；`calcRate` 保持纯公式函数，目标类型语义判定收敛到卡片层一处。

**备选**：消减目标社区列展示反转公式完成率——语义混乱（>100% 表示更差）且用户未要求，不采用。

### Decision 4: 比率型禁用"全量数据计算" + 表头 tooltip

**选择**：`aggregationType==='rate'` 时"全量数据计算" `el-select` `:disabled`（置灰）；比率型禁用提示"比率型固定合并分子分母"通过表头 tooltip 承载（不在单元格内弹 tooltip）；提交保留当前值（后端忽略）。

**理由**：用户明确比率型特殊；单元格内 tooltip 与表头 tooltip 结构不一致会干扰渲染，故禁用提示统一到表头 tooltip 末尾。

### Decision 5: `MetricCard` 按维度+类型+位置选率与目标标签

**选择**：`progressLabel`——全部列卡统一"目标完成率"；community 社区卡"目标完成率"；feature 社区卡"目标贡献率"。`targetLabel`——全部列统一"增长/消减目标（总体）"；community 社区卡"增长/消减目标（社区）"；feature 社区卡"增长/消减目标（总体）"。`attainment`（率）——仅增长目标计算：全部列卡→`calcRate(allColumnActual, allColumnTarget)`；community 社区卡→`calcRate(社区actual, communityTargets[community])`；feature 社区卡→`calcRate(社区actual, 总体targetValue)`；消减目标不计算（null，无进度条）。移除 30/20/10 分档；进度条宽度按完成率封顶 100%。卡片单位渲染去重：比率型格式化输出已含"%"，渲染单位前判断文本已以单位结尾则跳过（避免"%%"），非比率单位（如"个"）正常渲染。全部列取值带兜底：后端未返回 `allColumnActual`/`allColumnTarget` 时回退到当前值/总体目标值（过渡期兼容）。

**理由**：用户明确 4.1/4.2 展示与计算关系；仅增长目标计算率（社区列与全部列），消减目标一律不计算；公式统一后前端一个函数覆盖全部场景。

### Decision 6: 未启用目标值隐藏进度条与目标区域，全部列用后端聚合值

**选择**：无目标值时 `v-if="hasTarget"` 不渲染目标区域（标签+值）、`v-if="attainment !== null"` 不渲染 `__progress`，卡片仅展示当前值；全部社区场景直接用后端 `allColumnActual`/`allColumnTarget`；社区卡率由前端 `calcRate(actual, target, targetType)` 计算。

**理由**：用户明确无目标不渲染目标区域与进度条，卡片干净；后端负责聚合、前端负责率计算，职责清晰。

### Decision 7: 兼容推导旧字段

**选择**：`useMetricConfig.load`（`useDashboard.ts`）解析响应时调用 `metricPayload.ts` 的 `normalizeMetricConfig`，缺新维度字段则推导默认（`aggregationMethod='sum'`、`allColumnCalcMethod='sum'`、`communityColumnVisible=true`、`targetType='growth'`、`targetDimension='feature'`）；响应缺 `targetEnabled` 时按目标值存在性推导（feature 模式 `targetValue` 非空、community 模式任一社区目标值非空）；旧 `aggregationType='last_value'` 推导为 `count`+`last_value`；过渡期响应若含旧 `targetDirection`（higher_better/lower_better）映射为 `targetType`（growth/reduction）。提交始终发新字段并按 `targetEnabled` 裁剪目标字段。

**理由**：过渡期后端可能仅返回旧字段，推导保证渲染不崩；提交始终发新字段推动迁移。

**备选**：强制后端先上线——阻塞前端交付，不采用。

### Decision 8: 六列表头 tooltip 抽子组件 `MetricConfigColHeader`

**选择**：指标类型/聚合方式/全量数据计算/社区列展示开关/目标维度/目标类型六列表头 `#header` tooltip 结构一致（仅 label + TIPS 数组 + 可选 note 不同），抽统一子组件 `MetricConfigColHeader.vue` 渲染，消除模板重复。

**理由**：六列 tooltip 模板重复，抽子组件后修改一处生效，降低维护成本。

**备选**：保留六处重复模板——重复高、维护差，不采用。

## Risks / Trade-offs

- **[社区子表社区列表来源]** → 弹窗打开时需传入 communities；若为空提示"暂无已配置社区"。
- **[比率型禁用项提交值]** → 提交保留当前值（非删字段），需与后端口径一致（后端对比率型忽略）。
- **[全部列后端聚合结果响应结构]** → 前端依赖后端 `allColumnActual`/`allColumnTarget` 字段名，联调时确认，若不同仅调 `DetailDrawer.buildMetricValues` 映射。
- **[社区列展示过滤口径]** → 依赖后端单社区查询不返回 `communityColumnVisible=false` 指标；过渡期后端未实现时前端兜底过滤。
- **[targetEnabled 载荷裁剪口径]** → 前端省略目标字段（unit 除外，始终携带）+ 后端清空目标存储需一致；**单位已解耦为指标属性**，后端需同步调整原"targetEnabled=false 时清空单位"行为，否则无目标指标保存的单位会被丢弃（已实测复现：请求体 unit="个"、响应 unit=""）；响应缺 `targetEnabled` 时按目标值存在性推导兜底。
- **[兼容推导与真实新字段混存]** → 推导值与真实值无视觉区分，过渡期可接受；后端全量上线后推导分支自然不触发。

## Open Questions

- 后端全部列聚合结果 `allColumnActual`/`allColumnTarget` 的具体响应字段名待联调确认，不改变 spec 行为。
