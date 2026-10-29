## Purpose

定义特性运营看板前端指标配置弹窗的多维度拆分（指标类型/聚合方式/全量数据计算/社区列展示开关/目标维度/目标类型/目标启停开关）、目标值开关单独成列与目标相关列联动、六列表头 tooltip、可选目标值与社区粒度配置 UI，以及指标卡片按目标维度、目标类型与卡片位置展示完成率/贡献率与动态目标标签的行为（消减目标不展示完成率/贡献率）。

## ADDED Requirements

### Requirement: 配置弹窗六维度独立配置

指标配置弹窗 SHALL 把原"聚合类型"配置项拆为六个独立可配项：指标类型（数值/比率，`aggregationType`）、聚合方式（求和/平均/不聚合，`aggregationMethod`）、全量数据计算（求和/平均值，`allColumnCalcMethod`）、社区列展示开关（UI 列名"社区列"，开启=社区列与全部列均展示（默认，`communityColumnVisible=true`）、关闭=仅全部列展示（`communityColumnVisible=false`）；原设计字段 `allColumnOnly` 与开关语义相反，未发布直接改名并反转语义；非编辑态以只读 `el-switch` 直显开关态，与"目标"开关一致）、目标维度（社区/特性，`targetDimension`，默认社区）、目标类型（增长/消减，`targetType`，默认增长）。每项为独立下拉或开关，互不联动覆盖。单位为指标自身属性（不随"目标"开关启停）且为必填项：保存时单位为空（或全空白字符）SHALL 被阻止并提示；切换指标类型为比率时单位自动设为"%"（不依赖"目标"开关状态）；切离比率时已填单位保留不清空。

聚合方式区分时间段内多条上报数据如何聚合：求和=周期内累加、平均=周期内算术平均、不聚合=取周期内最新一次上报值（`last_value`）。

#### Scenario: 六维度独立配置

- **WHEN** 用户在配置弹窗编辑指标，分别选择指标类型=数值、聚合方式=不聚合、全量数据计算=平均值、社区列开关=关闭、目标维度=特性、目标类型=消减
- **THEN** 保存时请求体携带 `aggregationType=count`、`aggregationMethod=last_value`、`allColumnCalcMethod=avg`、`communityColumnVisible=false`、`targetDimension=feature`、`targetType=reduction`，六项相互独立（指标类型选比率时除外：全量数据计算固定为求和，见"比率型禁用并固定全量数据计算为求和"）

#### Scenario: 目标维度默认社区

- **WHEN** 用户新增指标未显式选择目标维度
- **THEN** 目标维度默认为"社区"（`targetDimension=community`）

#### Scenario: 目标类型默认增长

- **WHEN** 用户新增指标未显式选择目标类型
- **THEN** 目标类型默认为"增长"（`targetType=growth`）

#### Scenario: 社区列开关默认开启

- **WHEN** 用户新增指标未操作"社区列"开关
- **THEN** 开关默认开启（`communityColumnVisible=true`），指标在社区列与全部列均正常展示

#### Scenario: 关闭社区列开关后仅全部列展示

- **WHEN** 用户将"社区列"开关关闭并保存
- **THEN** 保存的 `communityColumnVisible=false`，该指标在社区列隐藏、仅在全部列展示

#### Scenario: 切换指标类型联动单位

- **WHEN** 用户将指标类型切换为比率
- **THEN** 单位自动设为"%"（不依赖"目标"开关状态）；切离比率时已填单位（如"个"）保留；聚合方式不被清空

#### Scenario: 单位必填校验

- **WHEN** 用户未填写单位（留空或仅空白字符）并保存
- **THEN** 保存被阻止并提示"请输入单位"；预设指标（用户数/访问量）应用预设时自动填入默认单位（人/次）

### Requirement: 配置弹窗六列表头 tooltip 图标

指标类型、聚合方式、全量数据计算、社区列展示开关、目标维度、目标类型六列表头 SHALL 各带一个 `?` 图标 tooltip，hover 展示该维度各选项的含义说明；全量数据计算的 tooltip 末尾 SHALL 附"注：比率型固定合并分子分母，此字段对比率型不生效"。六列表头 tooltip 由统一子组件 `MetricConfigColHeader` 渲染。

#### Scenario: 表头 tooltip 展示选项说明

- **WHEN** 用户 hover 六列表头任一 `?` 图标
- **THEN** 弹出 tooltip 展示该维度各选项 label + description；全量数据计算额外附比率型不生效的注

### Requirement: 比率型禁用并固定全量数据计算为求和

当指标类型为比率(rate)时，配置弹窗 SHALL 禁用"全量数据计算"配置项（置灰不可选），且 SHALL 将其值同步固定为"求和"（`allColumnCalcMethod=sum`）——比率型全部列固定合并分子分母，取平均无意义：切换指标类型为比率时，前端同步将该字段置为 `sum`，提交载荷携带 `sum`；编辑存量比率型指标时，历史存储的其他值 SHALL 归一为 `sum`。比率型禁用提示通过表头 tooltip 承载（不在单元格内弹 tooltip）。

#### Scenario: 切换为比率时禁用并固定求和

- **WHEN** 用户将指标类型选为比率
- **THEN** "全量数据计算"下拉被禁用（置灰），且值被同步置为"求和"（`allColumnCalcMethod=sum`），提交时携带 `sum`

#### Scenario: 计数型启用全量数据计算

- **WHEN** 用户将指标类型选为数值（含从比率切回）
- **THEN** "全量数据计算"下拉可用，可在求和/平均值间选择（切回数值后保持"求和"，可重新选择）

#### Scenario: 存量比率型指标归一为求和

- **WHEN** 用户编辑历史存储的比率型指标（其 `allColumnCalcMethod` 为其他值）
- **THEN** 编辑态与保存载荷中 `allColumnCalcMethod` 均为 `sum`

### Requirement: 预设用户指标全量数据计算锁定为求和

预设用户指标（用户数 `unique_visitor`、访问量 `page_view`）SHALL 将"全量数据计算"锁定为"求和"（不可选择平均值）：UV/PV 为跨社区流量计数，全部列取平均无业务含义。新增预设指标时该下拉禁用且值为 `sum`；编辑存量预设指标时禁用该下拉，并将历史存储的其他值归一为 `sum`。

#### Scenario: 新增预设指标锁定全量数据计算

- **WHEN** 用户通过"新增"选择预设指标"用户数"或"访问量"
- **THEN** "全量数据计算"禁用且值为"求和"，保存载荷携带 `allColumnCalcMethod=sum`

#### Scenario: 编辑存量预设指标归一为求和

- **WHEN** 用户编辑历史存储的预设用户指标（其 `allColumnCalcMethod` 非求和）
- **THEN** 编辑态"全量数据计算"禁用且归一为"求和"，保存后存储为 `sum`

### Requirement: 社区列展示开关（仅全部列展示指标）

指标配置 SHALL 支持"仅全部列展示"（`communityColumnVisible=false` 时生效，默认 true，由"社区列"开关关闭态表达）：`communityColumnVisible=false` 的指标在社区列（详情抽屉单社区查询；状态矩阵仅展示特性状态、不涉及指标）不展示，仅在全部列（"全部"社区场景）展示；指标上报与数据聚合口径不受影响。

#### Scenario: 关闭后社区列隐藏

- **WHEN** 指标 `communityColumnVisible=false`，用户在详情抽屉查看单社区
- **THEN** 该指标不出现在社区列展示中

#### Scenario: 全部列正常展示

- **WHEN** 指标 `communityColumnVisible=false`，用户在详情抽屉选择"全部"社区
- **THEN** 该指标正常展示，增长目标展示目标完成率（消减目标不展示率，仅展示当前值与目标值）

#### Scenario: 默认开启社区列正常展示

- **WHEN** 新增指标未关闭"社区列"开关
- **THEN** `communityColumnVisible=true`，指标在社区列与全部列均正常展示

### Requirement: 目标值开关单独成列与目标相关列联动

指标配置弹窗 SHALL 将"是否有目标值"开关单独作为一列"目标"（非编辑态以只读 `el-switch` 直显开关态，不渲染文字），并按以下顺序排列目标相关列：目标（开关） → 目标维度 → 目标类型 → 目标值 → 单位。开关状态 SHALL 以显式字段 `targetEnabled` 体现在请求与响应中，与后端契约一一对应。开关关闭时，目标维度、目标类型、目标值三列 MUST 禁用（置灰不可选）并展示"--"；**单位列始终可编辑**（单位为指标自身属性，不随目标启停，无目标指标也可配置单位用于当前值展示）。开关开启时，目标维度与目标类型可选，目标值列根据目标维度展开不同输入形态：`community` 模式展开社区目标子表（社区 + 目标值两列，社区列表来自看板已配置社区），`feature` 模式展开单个目标值输入框。切换目标维度清空另一形态目标值。社区目标 popover 触发文案为紧凑计数式"N 社区目标"。

保存载荷 SHALL 按开关状态裁剪目标字段，单位始终携带：`targetEnabled=true` 时请求携带 `targetType`、`targetDimension`、`unit`，并仅携带对应形态目标值字段（feature 模式携带 `targetValue`、community 模式携带 `communityTargets`）；`targetEnabled=false` 时请求携带 `targetEnabled=false` 与 `unit`，不携带 `targetType`、`targetDimension`、`targetValue`、`communityTargets`（由后端清空目标存储；单位按指标自身属性保留存储）。

#### Scenario: 关闭目标开关后目标三列禁用且载荷省略目标字段（单位仍携带）

- **WHEN** 用户关闭"目标"开关并保存
- **THEN** 目标维度、目标类型、目标值三列被禁用（置灰不可选）并展示"--"，单位列仍可编辑；保存请求携带 `targetEnabled=false` 与 `unit`，不携带 `targetType`、`targetDimension`、`targetValue`、`communityTargets`

#### Scenario: 无目标指标配置单位

- **WHEN** 用户在未开启"目标"开关的指标上填写单位（如"个"）并保存
- **THEN** 保存请求携带 `unit="个"`，保存后看板卡片当前值展示该单位

#### Scenario: 非编辑态开关以只读开关展示

- **WHEN** 指标行非编辑态且未配置目标
- **THEN** "目标"列展示一个 disabled `el-switch`（关闭态），不渲染"是/否"文字

#### Scenario: 开启后按维度展开输入形态

- **WHEN** 用户开启"目标"开关，选择目标维度=社区
- **THEN** 目标值列展开社区目标子表（社区 + 目标值两列）；选择特性时展开单个目标值输入框

#### Scenario: 开启目标开关后载荷携带目标字段

- **WHEN** 用户开启"目标"开关、目标维度=特性、填写目标值与单位后保存
- **THEN** 保存请求携带 `targetEnabled=true`、`targetType`、`targetDimension=feature`、`unit` 与 `targetValue`，不携带 `communityTargets`；目标维度=社区时携带 `communityTargets`、不携带 `targetValue`

#### Scenario: 开关 off→on 保留已填社区目标值

- **WHEN** 用户在 community 模式填入社区目标值后关闭"目标"开关，再重新开启
- **THEN** 已填的社区目标值保留恢复（关闭时不清空内存数据，仅保存时按 `targetEnabled=false` 裁剪 payload）

#### Scenario: 校验目标值格式

- **WHEN** 指标类型为比率，用户在目标值（feature 模式）或社区子表（community 模式）填写非数字或超出 0~100 的值并保存
- **THEN** 保存被阻止并提示目标值格式错误

### Requirement: 指标卡片按目标维度、目标类型与位置展示率与目标标签

指标卡片 SHALL 按 `targetDimension`、`targetType` 与卡片位置（社区卡 / 全部列卡）展示对应的率与目标标签：

- **全部列卡**（不区分目标维度）：进度标签"目标完成率"，完成率 = 全部列实际值/全部列目标值 ×100%（≥100% 达标）；消减目标不进行完成率计算（无进度条），仅展示当前值与目标值。目标标签按目标类型为"增长目标（总体）"（增长）或"消减目标（总体）"（消减）。
- **community 模式社区卡**：进度标签"目标完成率"，目标标签"增长目标（社区）"/"消减目标（社区）"；增长目标完成率 = 该社区实际值/该社区目标值 ×100%（≥100% 达标）；消减目标不进行完成率计算（无进度条），仅展示当前值与目标值。
- **feature 模式社区卡**：进度标签"目标贡献率"，目标标签"增长目标（总体）"/"消减目标（总体）"；增长目标贡献率 = 该社区实际值/总体目标值 ×100%；消减目标不进行贡献率计算（无进度条）。

目标值无效（空/非数字/≤0）时不计算率。进度条按完成率封顶 100% 展示（完成率文本最大显示 999%），颜色按达标/未达标区分。

#### Scenario: community 模式增长社区卡

- **WHEN** 用户查看 `targetDimension=community`、`targetType=growth` 指标的社区卡
- **THEN** 进度标签"目标完成率"，目标标签"增长目标（社区）"，完成率 = 实际值/该社区目标值，≥100% 达标

#### Scenario: community 模式消减社区卡无进度条

- **WHEN** 用户查看 `targetDimension=community`、`targetType=reduction` 指标的社区卡
- **THEN** 目标标签"消减目标（社区）"，不展示进度条与完成率，仅展示当前值与目标值

#### Scenario: feature 模式增长社区卡贡献率

- **WHEN** 用户查看 `targetDimension=feature`、`targetType=growth` 指标的单社区卡片
- **THEN** 进度标签"目标贡献率"，目标标签"增长目标（总体）"，贡献率 = 该社区实际值/总体目标值 ×100%

#### Scenario: feature 模式消减社区卡无进度条

- **WHEN** 用户查看 `targetDimension=feature`、`targetType=reduction` 指标的单社区卡片
- **THEN** 目标标签"消减目标（总体）"，不展示进度条与贡献率，仅展示当前值与目标值

#### Scenario: 增长目标全部列卡展示目标完成率

- **WHEN** 用户查看 `targetType=growth` 指标的全部列卡
- **THEN** 进度标签"目标完成率"，目标标签"增长目标（总体）"，完成率 = 全部列实际值/全部列目标值 ×100%，≥100% 达标

#### Scenario: 消减目标全部列卡无进度条

- **WHEN** 用户查看 `targetType=reduction` 指标的全部列卡
- **THEN** 目标标签"消减目标（总体）"，不展示进度条与完成率，仅展示当前值与目标值

### Requirement: 指标卡片单位渲染去重

指标卡片 SHALL 对单位渲染去重：格式化函数对比率型指标输出的文本已以"%"结尾，当配置单位与文本结尾相同时不再重复渲染单位，避免比率型卡片当前值/目标值出现"%%"；非比率型指标（单位如"个"）正常渲染单位。单位为空或文本为占位符"--"时不渲染单位。

#### Scenario: 比率型卡片不重复渲染百分号

- **WHEN** 比率型指标配置单位为"%"，卡片展示当前值 95（格式化输出"95%"）
- **THEN** 卡片展示"95%"，不出现"95%%"；目标值同理

#### Scenario: 非比率型卡片正常渲染单位

- **WHEN** 数值型指标配置单位为"个"，卡片展示当前值 150
- **THEN** 卡片展示"150个"

### Requirement: 未启用目标值时隐藏率与目标区域

当指标未配置目标值时，指标卡片 SHALL 不渲染进度条区块**且不渲染目标区域（目标标签+目标值）**，仅展示当前值与运行时说明。

#### Scenario: 无目标值卡片不显示进度条与目标区域

- **WHEN** 指标未配置目标值
- **THEN** 卡片不渲染进度条区块与目标区域，仅展示当前值与运行时说明

### Requirement: 率由前端计算，全部列使用后端聚合值

指标卡片在"全部"社区场景 SHALL 直接使用后端返回的聚合实际值（`Σa`）与聚合目标值，不在前端重新聚合各社区值。`community` 模式社区卡完成率由前端用该社区实际值与 `communityTargets[community]` 计算（仅增长目标）；`feature` 模式社区卡贡献率由前端用该社区实际值/总体目标值计算（仅增长目标）；全部列完成率由前端用 `allColumnActual`/`allColumnTarget` 计算（仅增长目标），不依赖后端返回的率字段；消减目标一律不计算率。

#### Scenario: 全部列直接消费后端聚合值

- **WHEN** 用户在详情抽屉选择"全部"社区
- **THEN** 卡片当前值、目标值取自后端返回的聚合结果，前端不做二次聚合；完成率由前端用聚合值与目标类型计算

#### Scenario: feature 模式社区卡前端计算贡献率

- **WHEN** 用户查看 `targetDimension=feature`、`targetType=growth` 指标的单社区卡片
- **THEN** 卡片贡献率由前端用该社区实际值/总体目标值计算，不依赖后端 `communityContribution`

### Requirement: 旧字段兼容推导

读取指标配置时，若后端响应仅返回旧 `aggregationType`（无新维度字段），前端 SHALL 本地推导默认值：`aggregationMethod=sum`、`allColumnCalcMethod=sum`、`communityColumnVisible=true`、`targetType=growth`、`targetDimension=feature`（因旧全局目标值本质为特性维度）；响应缺 `targetEnabled` 字段时 SHALL 按目标值存在性推导（feature 模式 `targetValue` 非空、community 模式任一社区目标值非空）；旧 `aggregationType=last_value` 推导为 `aggregationMethod=last_value`、`aggregationType=count`；过渡期若响应返回旧 `targetDirection` 字段（higher_better/lower_better），SHALL 映射为 `targetType`（growth/reduction）。比率型指标（`aggregationType=rate`，`allColumnCalcMethod` 字段对其不生效）的 `allColumnCalcMethod` SHALL 归一为 `sum`。

#### Scenario: 后端仅返回旧字段时推导

- **WHEN** 后端响应指标配置仅含 `aggregationType=count`，无 `aggregationMethod` 等新字段
- **THEN** 前端本地推导 `aggregationMethod=sum`、`allColumnCalcMethod=sum`、`communityColumnVisible=true`、`targetType=growth`、`targetDimension=feature` 并正常渲染

#### Scenario: 响应缺 targetEnabled 时按目标值存在性推导

- **WHEN** 后端响应未返回 `targetEnabled`，指标 `targetDimension=feature` 且 `targetValue` 非空（或 community 模式任一社区目标值非空）
- **THEN** 前端推导 `targetEnabled=true`；目标值全为空时推导为 `false`

#### Scenario: 旧 targetDirection 映射

- **WHEN** 后端响应返回旧字段 `targetDirection=lower_better`
- **THEN** 前端映射为 `targetType=reduction` 并正常渲染

#### Scenario: 旧 last_value 推导

- **WHEN** 后端响应 `aggregationType=last_value`
- **THEN** 前端推导为 `aggregationType=count`、`aggregationMethod=last_value`，弹窗展示对应选中态

#### Scenario: 比率型指标回显归一为求和

- **WHEN** 后端返回 `aggregationType=rate` 且 `allColumnCalcMethod` 为其他值或缺省
- **THEN** 前端将 `allColumnCalcMethod` 归一为 `sum` 并正常渲染
