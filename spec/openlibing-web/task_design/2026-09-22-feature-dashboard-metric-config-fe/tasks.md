## 1. 类型与常量

- [x] 1.1 `FeatureDashboard/types.ts` 新增类型 `AggregationMethod = 'sum' | 'avg' | 'last_value'`、`AllColumnCalcMethod = 'sum' | 'avg'`、`TargetType = 'growth' | 'reduction'`、`TargetDimension = 'community' | 'feature'`、`CommunityTarget = { community: string; targetValue: string }`。
- [x] 1.2 `FeatureDashboard/types.ts` `MetricConfigItem` 增字段 `aggregationMethod`/`allColumnCalcMethod`/`communityColumnVisible`/`targetType`/`targetDimension`/`targetEnabled?`/`communityTargets?: CommunityTarget[]`；`MetricDisplay` 增 `targetDimension`/`targetType`/`communityTargets?` 与后端聚合字段 `allColumnActual?`/`allColumnTarget?`。
- [x] 1.3 `FeatureDashboard/constants.ts` 新增 `AGGREGATION_METHOD_LABEL`（求和/平均/不聚合）、`ALL_COLUMN_CALC_LABEL`（求和/平均值）、`COMMUNITY_COLUMN_TIPS`（开启/关闭，社区列展示开关）、`TARGET_TYPE_LABEL`（增长/消减）、`TARGET_DIMENSION_LABEL`（社区/特性）及对应 description/tips；`AGGREGATION_TYPE_LABEL` 收窄为 `{ count: '数值', rate: '比率' }`（移除 last_value）。
- [x] 1.4 `FeatureDashboard/constants.ts` `USER_METRIC_PRESET_OPTIONS` 补 `aggregationMethod`（默认 sum）与 `targetDimension`（默认 community）字段。

## 2. 数值工具（formatters.ts，原 utils.ts 数值部分拆分；utils.ts 保留兼容 re-export）

- [x] 2.1 重构 `calcRate(current, target)`：率 = current/target×100，值封顶 999（进度条宽度另行封顶 100）；target≤0 或 current 非有限返回 null。函数不接收 targetType 参数，消减目标的"不计算率"由 `MetricCard` 承担——用于全部列完成率、community 社区卡完成率与 feature 社区卡贡献率（仅增长目标调用）。
- [x] 2.2 `resolveMetricNumeric` 按值形态驱动判定：rate 对象（{numerator,denominator}）→分子分母×100、`{number,description}` 对象→number、其余→Number；`formatMetricValue` 依 `aggregationType` 决定纯数字是否追加 %，`last_value` 解析路径由调用方按 `aggregationMethod === 'last_value'` 触发 `parseLastValueMetric`（如 `DetailDrawer.buildMetricValues`）。

## 3. 载荷与兼容推导（metricPayload.ts，由 useDashboard.ts 调用）

- [x] 3.1 `toCreatePayload`/`toUpdatePayload` 带上 `aggregationMethod`/`allColumnCalcMethod`/`communityColumnVisible`/`targetEnabled`；**`unit` 为指标自身属性、始终携带**（`targetEnabled=false` 时也携带）；按 `targetEnabled` 裁剪目标载荷——`targetEnabled=false` 时携带 `targetEnabled=false` 与 `unit`，省略 `targetType`/`targetDimension`/`targetValue`/`communityTargets`；`targetEnabled=true` 时携带 `targetType`/`targetDimension`/`unit` 并按 `targetDimension` 只带对应形态目标字段——feature 模式传 `targetValue`（单值）、community 模式传 `communityTargets` 列表（另一形态不携带，维度切换时由后端重置存储）。
- [x] 3.4 补充 `toUpdatePayload` 用例：更新载荷始终携带 `unit`（含 `targetEnabled=false` 场景），锁定单位解耦契约。
- [x] 3.2 `normalizeMetricConfig`（`useMetricConfig.load` 调用）解析响应时，若 `MetricConfigItem` 缺新字段，本地推导默认值（`aggregationMethod='sum'`、`allColumnCalcMethod='sum'`、`communityColumnVisible=true`、`targetType='growth'`、`targetDimension='feature'`）；缺 `targetEnabled` 时按目标值存在性推导（feature 模式 `targetValue` 非空、community 模式任一社区目标值非空）；旧 `aggregationType='last_value'` 推导为 `aggregationType='count'`+`aggregationMethod='last_value'`；旧 `targetDirection`（higher_better/lower_better）映射为 `targetType`（growth/reduction）。
- [x] 3.3 `useFeatureDetail.load` 存储详情原始响应；`MetricConfigItemDTO` 的 `allColumnActual`/`allColumnTarget`/`communityTargets`/`targetDimension`/`targetType` 由 `DetailDrawer.buildMetricValues` 透传到 `MetricDisplay`。

## 4. 配置弹窗（MetricConfigDialog.vue 外壳 + MetricConfigGroup.vue 表格模板 + useMetricEditing.ts 状态机 + metricConfigForm.ts 表单工具）

- [x] 4.1 把原"聚合类型"列改 UI label "指标类型"（数值/比率），`el-option` 用收窄后的 `AGGREGATION_TYPE_LABEL`。
- [x] 4.2 新增"聚合方式"列（求和/平均/不聚合）、"全部列计算"列（求和/平均值）、"社区列"开关列（开启=社区列与全部列均展示、关闭=仅全部列展示；编辑态 `el-switch`，非编辑态只读开关直显）、"目标类型"列（增长/消减）、"目标维度"列（社区/特性），复用 `metric-config__edit-col` 样式。
- [x] 4.3 当 `editing.data.aggregationType === 'rate'` 时，"全部列计算" `el-select` `:disabled="true"`，且切换为比率时该值同步固定为 `sum`（比率型固定合并分子分母，存量编辑时归一）；禁用提示"比率型固定合并分子分母"由表头 tooltip note 承载。
- [x] 4.4 "目标"开关单独成列（编辑态 `el-switch`，非编辑态只读开关直显，取值按 `targetEnabled` 缺省时存在性推导）；关闭时目标维度/类型/目标值三列禁用并展示"--"（**单位列始终可编辑**，无目标指标也可配置单位）；开启时按 `targetDimension` 展开不同输入——`community` 模式展开社区目标子表 popover（触发文案"N 社区目标"，社区列表来自 props.communities，缺失时补齐、为空提示"暂无已配置社区"）；`feature` 模式展开单个目标值 `el-input`。切换 `targetDimension` 时清空另一形态的目标值；off→on 保留已填值（仅保存时按 `targetEnabled` 裁剪目标字段）。
- [x] 4.5 `buildEmptyForm`/`cloneMetricItem`（`metricConfigForm.ts`）增 `aggregationMethod:'sum'`/`allColumnCalcMethod:'sum'`/`communityColumnVisible:true`/`targetType:'growth'`/`targetDimension:'community'`/`communityTargets:[]`/`targetEnabled:false` 默认值；`onAggregationTypeChange`（`useMetricEditing.ts`）调整为切换 aggregationType 时联动单位（rate→'%'，**不依赖目标开关**；切离比率保留已填单位），不清空 aggregationMethod。
- [x] 4.6 `validateMetricRow`/`validateTargetValueMessage`（`metricConfigForm.ts`）：启用目标值时校验——community 模式校验每个社区目标值（至少一个社区有值）；feature 模式校验单值；rate 型 0~100 且最多两位小数、count 型正整数；未启用时不校验目标值。
- [x] 4.7 `saveEditingRow` 组装 payload 时带显式 `targetEnabled`，目标字段裁剪由 `toCreatePayload`/`toUpdatePayload` 按 `targetEnabled`/`targetDimension` 完成（`targetEnabled=false` 省略全部目标字段）。
- [x] 4.8 单位改为必填项（用户指标与业务指标统一生效）：`validateMetricRow` 增加单位非空校验（空/全空白阻止保存并提示"请输入单位"）；`applyPresetToData` 应用预设时直接填入预设默认单位（用户数=人、访问量=次）；"单位"列表头增加必填星号。
- [x] 4.9 预设用户指标（用户数/访问量）锁定"全量数据计算"为求和：`useMetricEditing` 新增 `isAllColumnCalcLocked`（命中预设键时锁定），`startEdit` 将存量预设指标归一为 `sum`，锁定状态经 `metricEditContext` 透传至分组表格禁用下拉。
- [x] 4.10 比率型指标"全量数据计算"固定为求和：`onAggregationTypeChange` 切换为比率时同步置 `sum`；`startEdit` 将存量比率型指标归一；`normalizeMetricConfig` 对详情回显数据归一为 `sum`。

## 5. MetricCard.vue

- [x] 5.1 `progressLabel` 按 `metric.targetDimension` + 卡片位置返回——全部列卡统一"目标完成率"；community 模式社区卡"目标完成率"；feature 模式社区卡"目标贡献率"。
- [x] 5.2 `targetLabel` 按 `targetType` + 维度 + 位置返回——全部列卡统一"增长目标（总体）/消减目标（总体）"；community 社区卡"增长目标（社区）/消减目标（社区）"；feature 社区卡"增长目标（总体）/消减目标（总体）"。
- [x] 5.3 `attainment` 计算（统一 `calcRate(actual, target)`，消减目标直接返回 null）：全部列卡→`calcRate(allColumnActual, allColumnTarget)`（后端未返回时回退当前值/总体目标值）；community 社区卡→`calcRate(社区actual, communityTargets[community])`；feature 社区卡→`calcRate(社区actual, 总体 targetValue)`；消减目标不计算（null，无进度条，社区卡与全部列卡均不展示进度条）。
- [x] 5.4 `progressClass` 移除 30/20/10 分档，统一达标（≥100）/未达标二色着色。
- [x] 5.5 全部社区场景：`currentText`/`targetText` 取后端 `allColumnActual`/`allColumnTarget`；社区场景：`currentText`=该社区 actual、`targetText` 按 `targetDimension` 取社区目标或特性目标。
- [x] 5.6 无目标值（未启用、或 `targetDimension=community` 且 `communityTargets[community]` 空、或 `targetDimension=feature` 且 `targetValue` 空）时 `v-if="attainment !== null"` 不渲染 `__progress` 区块；目标区块在 targetText 非 '--' 时渲染、无 target 时隐藏。
- [x] 5.7 `communityColumnVisible=false` 的指标在社区列场景（非全部）不渲染卡片（过滤在 `DetailDrawer.buildMetricValues` 兜底，与后端单社区查询过滤口径一致）。
- [x] 5.8 卡片单位渲染去重：渲染单位前判断格式化文本已以单位结尾则跳过（比率型输出已含"%"，避免"%%"）；文本为"--"或单位为空不渲染；非比率单位正常展示。

## 6. DetailDrawer.vue

- [x] 6.1 `buildMetricValues` 注入 `targetDimension`/`targetType`/`communityTargets`/`allColumnActual`/`allColumnTarget` 到 `MetricDisplay`。
- [x] 6.2 `MetricCard` 调用处传入 `:is-all-community="isAllCommunity"`；社区列 target 取 `communityTargets[community]`（community 模式）或特性 `targetValue`（feature 模式）。
- [x] 6.3 兼容：后端未返回全部列字段时（过渡期单社区查询本就为 null），社区列正常展示；全部列卡回退当前值/总体目标值。

## 7. index.vue

- [x] 7.1 `MetricConfigDialog` 调用处新增 `:communities="communities"` prop（来自 `useFeatureMatrix`）。

## 8. 前端测试

- [x] 8.1 `FeatureDashboard/__tests__/utils.spec.ts` 增 `calcRate` 用例：实际/目标公式（不四舍五入）、目标值无效→null（消减目标的"不计算率"行为由 `MetricCard` 承担）。
- [x] 8.2 增 `resolveMetricNumeric` 用例：rate 对象按 num/denom、旧格式纯数值兼容、`{number,description}` 对象、空值/无效值→null。
- [x] 8.3 新增 `__tests__/metricPayload.spec.ts`：`toCreatePayload`/`toUpdatePayload` 按 `targetEnabled` 裁剪目标字段、按维度只带对应形态目标值、URL 清洗；`normalizeMetricConfig` 旧 last_value 映射、旧 targetDirection 映射、缺省字段推导、缺 `targetEnabled` 存在性推导。

## 9. 验证

- [x] 9.1 对改动文件运行 lint 与 typecheck：FeatureDashboard 全部 55 个单测（constants/metricPayload/utils 三个 spec）通过；vue-tsc 无 FeatureDashboard 相关错误（`packages/stores` 存在与本改动无关的存量类型错误）。
- [x] 9.2 手动验证：配置弹窗六项独立可选；比率型禁用全部列计算；目标值开关 + 目标维度联动（community 子表 / feature 单值）；保存后请求体按 `targetEnabled` 裁剪目标字段（无目标时不携带目标类型/维度/目标值，**`unit` 始终携带**）；无目标指标填写单位后保存、卡片当前值展示该单位；仅全部列展示（`communityColumnVisible=false`）指标社区列隐藏。
- [x] 9.3 手动验证：`MetricCard` 全部列卡增长"目标完成率"/消减无进度条、community 社区卡增长"目标完成率"/消减无进度条、feature 社区卡增长"目标贡献率"/消减无进度条；无目标值卡片不显示进度条；比率型卡片不出现"%%"（单位去重）。
- [x] 9.4 联调：后端仅返回旧 aggregationType/targetDirection 时前端推导渲染正常；后端返回全部列聚合字段 `allColumnActual`/`allColumnTarget` 时卡片直接消费。
- [x] 9.5 联调（阻塞项）：后端同步调整"单位与目标解耦"——`targetEnabled=false` 时按请求保存 `unit` 而非清空；后端未调整前无目标指标保存的单位会在存储层丢失（已实测：请求体 unit="个"、响应 unit=""）。
