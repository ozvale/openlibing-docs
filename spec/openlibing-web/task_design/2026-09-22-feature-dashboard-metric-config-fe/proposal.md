## Why

特性运营看板前端 `FeatureDashboard` 的指标配置弹窗用单一"聚合类型"下拉（count/rate/last_value）同时表达多个正交维度，用户无法独立配置"指标类型/聚合方式/全部列计算方式"，且聚合方式缺少"平均"选项、无法表达"仅全部列展示"的指标；目标值必填且为全局单值，无法按社区设置、无法区分目标维度（社区维度/特性维度），且"是否有目标值"缺少显式请求字段、无目标时目标相关字段（目标类型/维度/单位/目标值）仍随请求传递造成语义噪音；目标语义用"正向/负向"表达不直观，需改为"目标类型"（增长/消减）；`MetricCard` 的完成率/贡献率标签与目标标签需按目标维度、目标类型与卡片位置联动（消减目标不展示完成率/贡献率）。需要在前端拆解配置维度、支持目标维度与社区粒度目标值、以显式 `targetEnabled` 裁剪目标载荷、按维度+类型+位置展示完成率/贡献率，与后端多维度配置模型对齐。

## What Changes

- `MetricConfigDialog.vue` 把原"聚合类型"列拆为六个独立配置项：**指标类型**（数值/比率，`aggregationType`）、**聚合方式**（求和/平均/不聚合，`aggregationMethod`）、**全量数据计算**（求和/平均值，`allColumnCalcMethod`）、**社区列**开关（开启=社区列与全部列均展示（默认，`communityColumnVisible=true`）、关闭=仅全部列展示（`communityColumnVisible=false`）；原设计字段 `allColumnOnly` 与开关语义相反，未发布直接改名并反转语义，非编辑态只读开关直显）、**目标维度**（社区/特性，`targetDimension`，默认社区）、**目标类型**（增长/消减，`targetType`，默认增长，取代原"目标方向"正向/负向）；比率型时禁用"全量数据计算"列。六列表头各带 `?` 图标 tooltip（统一子组件 `MetricConfigColHeader` 渲染），全量数据计算 tooltip 附"比率型固定合并分子分母"注。
- 新增"仅全部列展示"支持：`communityColumnVisible=false` 的指标在社区列（矩阵社区单元格、详情抽屉单社区查询）不展示，仅在全部列展示。
- 目标启停显式化：保存请求始终携带 `targetEnabled` 布尔（对应"目标"开关）；**`unit` 为指标自身属性、请求始终携带**（无目标指标也可配置单位用于当前值展示），`targetEnabled=false` 时请求不携带 `targetType`/`targetDimension`/`targetValue`/`communityTargets`（后端清空目标存储）；`targetEnabled=true` 时仅携带对应形态目标值字段（feature 模式 `targetValue`、community 模式 `communityTargets`），另一形态不携带。响应新增 `targetEnabled`，前端直读，缺省时按目标值存在性推导（兼容旧后端）。
- 目标值开关单独成列"**目标**"（非编辑态以只读 `el-switch` 直显开关态），目标相关列顺序：目标 → 目标维度 → 目标类型 → 目标值 → 单位。开关关闭时目标维度/类型/目标值三列禁用并展示"--"（**单位列始终可编辑**，单位不随目标启停）；开启时按目标维度展开不同输入——`community` 模式展开社区目标子表（触发文案"N 社区目标"），`feature` 模式展开单个总体目标值输入框。切换指标类型为比率时单位自动设为"%"（不依赖目标开关），切离比率保留已填单位。开关 off→on 保留已填社区目标值（仅保存时按 `targetEnabled` 裁剪目标字段）。切换维度清空另一形态。
- `MetricCard.vue` 按目标维度 + 目标类型 + 卡片位置展示对应率与目标标签：
  - 全部列卡（不区分目标维度）：进度标签"目标完成率"，完成率 = 全部列实际值/全部列目标值 ×100%（仅增长目标）；消减目标不计算（无进度条），仅展示当前值与目标值。目标标签"增长目标（总体）/消减目标（总体）"，增长 ≥100% 达标。
  - community 模式社区卡：进度标签"目标完成率"，目标标签"增长目标（社区）/消减目标（社区）"；仅增长目标计算完成率（实际/该社区目标），消减目标不计算（无进度条）。
  - feature 模式社区卡：进度标签"目标贡献率"，目标标签"增长目标（总体）/消减目标（总体）"；仅增长目标计算贡献率（该社区实际/总体目标），消减目标不计算（无进度条）。
  - 目标标签规则：全部列统一"增长/消减目标（总体）"；社区卡 community 维度"（社区）"、feature 维度"（总体）"。
  - 未启用目标值不渲染进度条且不渲染目标区域（标签+值隐藏），卡片仅展示当前值。
  - 全部列与社区卡率均由前端计算（`calcRate(actual, target)`，消减目标的"不计算率"由 `MetricCard` 承担），全部列实际值/目标值直接消费后端聚合结果；卡片单位渲染去重（比率型格式化输出已含"%"，文本已以单位结尾时不再渲染，避免"%%"）。
- `types.ts` 新增 `AggregationMethod`（sum/avg/last_value）/`AllColumnCalcMethod`/`TargetType`（growth/reduction）/`TargetDimension`/`CommunityTarget` 类型；`MetricConfigItem`/`MetricDisplay` 增对应字段（含 `communityColumnVisible`、`targetEnabled`）。
- `constants.ts` 新增五组 label/option/tips（聚合方式/全量数据计算/社区列展示开关/目标类型/目标维度）；`AGGREGATION_TYPE_LABEL` 收窄为数值/比率；`TARGET_TYPE_LABEL` 为"增长/消减"。
- `formatters.ts`（原 `utils.ts` 数值部分）：`calcAttainmentRate` 重构为 `calcRate(current, target)`（率=实际/目标 ×100，值封顶 999；达标判定：增长 ≥100%；消减目标的"不计算率"由 `MetricCard` 承担），移除 lower→target/actual 反转公式与负值手动取负逻辑；`resolveMetricNumeric` 按值形态驱动判定（rate 对象→分子分母、`{number}` 对象、纯数字），`formatMetricValue` 依 `aggregationType` 决定纯数字是否加 %，`last_value` 解析路径由调用方按 `aggregationMethod === 'last_value'` 触发 `parseLastValueMetric`。
- `metricPayload.ts`：`toCreatePayload`/`toUpdatePayload` 按维度与 `targetDimension` 组装目标载荷，携带 `communityColumnVisible` 与 `targetEnabled` 并按启停裁剪目标字段；读取时兼容推导旧字段（`targetDimension` 推导为 feature、旧 `targetDirection` 映射为 `targetType`、缺 `targetEnabled` 按目标值存在性推导）。
- 兼容：后端仅返回旧 `aggregationType` 时本地推导新维度默认值（过渡期）。

## Capabilities

### New Capabilities

- `feature-dashboard-metric-display`: 特性看板前端指标配置弹窗（六维度拆分 + 目标维度/类型联动可选目标值 + 目标启停显式开关 + 社区列展示开关）与指标卡片按维度+类型+位置展示完成率/贡献率的行为。

### Modified Capabilities

无。特性看板前端为既有功能，但 `openspec/specs/` 下无对应 spec，按新增能力处理。

## Impact

- **受影响代码**（已按职责拆分落位，`utils.ts` 保留为兼容 re-export）：
  - `openlibing-web/apps/web-openlibing/src/views/manageCenter/FeatureDashboard/types.ts`、`constants.ts`
  - `formatters.ts`（`calcRate`/`resolveMetricNumeric`/`formatMetricValue`/`parseLastValueMetric`）、`matrixAdapter.ts`（matrix 归一化与详情查询参数）、`metricPayload.ts`（载荷组装与旧字段兼容推导）、`metricConfigForm.ts`（表单构建/展示文案/行校验）、`useMetricEditing.ts`（弹窗行编辑状态机）、`useDashboard.ts`（数据加载与 CRUD 调用）
  - `components/MetricConfigDialog.vue`（弹窗外壳与保存动作）、`MetricConfigGroup.vue`（分组表格内联编辑模板）、`MetricConfigColHeader.vue`、`metricEditContext.ts`、`MetricCard.vue`、`DetailDrawer.vue`
  - `__tests__/utils.spec.ts`（补 `calcRate`/`resolveMetricNumeric` 用例）、`__tests__/metricPayload.spec.ts`（载荷裁剪与兼容推导用例）
- **受影响接口**：消费后端 `POST /manage/feature-dashboard/metrics`、`POST /manage/feature-dashboard/update-metrics`、`GET /manage/feature-dashboard/query-features/detail`、`GET /manage/feature-dashboard/features/query-metrics/detail` 的新增字段（含 `communityColumnVisible`、`targetEnabled`、全部列聚合结果 `allColumnActual`/`allColumnTarget`）。
- **风险**：
  - 过渡期后端未上线新字段时前端兼容推导（旧 `aggregationType` → 六维度默认，旧 `targetDirection` → `targetType`）。
  - 社区目标子表社区列表来源为看板已配置社区，需在弹窗打开时传入。
  - 比率型禁用"全量数据计算"需强约束，避免提交无效值。
  - "仅全部列展示"指标的社区列过滤需与后端单社区查询过滤口径一致（后端不返回，前端不渲染）。
  - `targetEnabled=false` 的载荷裁剪需与后端"清空目标存储"口径一致；**单位已解耦为指标属性（始终携带），后端需同步调整原"无目标时清空单位"行为，否则无目标指标保存的单位会被丢弃**；响应缺 `targetEnabled` 时按目标值存在性推导兜底。
