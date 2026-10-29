# 流水线操作日志页对齐与日期范围组件 — design

## 方案设计

总体分三层：共享日期范围组件（DateRangePicker 移植）、CategorySearch/ColumnFilter 类型升级（daterange 重命名 + 共享面板接入）、流水线操作日志页重构（filter-meta 服务端选项 + 组合筛选）：

```text
components/DateRangePicker/            # DevUI DatepickerPro 的 Vue 移植 + 纯函数层（与 openlibing-web 同源）
components/CategorySearch/             # 'dateRange'→'daterange' 重命名，编辑器内嵌 DateRangePanel
components/ColumnFilter.vue            # 触发器 button 化，面板宽度随 daterange 自适应
views/pipeline/PipelineLog/index.vue   # 页面重构：CategorySearch + filter-meta + 新列集
views/pipeline/PipelineLog/DetailDialog.vue  # 操作模块取值优先级更新
views/SecurityOptions/{index,FilingRecordsView,FilingListView}.vue  # 调用方类型同步
api/{api,urls}.ts                      # +/logging/filter-meta
```

## 实现逻辑设计

### 1. DateRangePicker 组件（与 openlibing-web 同源的仓内副本）

- `DateRangePanel.vue`：DevUI 18.0.0 DatepickerPro 的 Vue 移植（保留 `DEVUI-LICENSE`），双月滚动日历、时间编辑、hover 预览、快捷时间栏、`minDate`/`maxDate` 边界；本仓仅使用 `datetime` mode、range selection（无 single 模式场景）。
- `dateRange.ts` 纯函数层：`resolveDateRange`（数组直通；快捷键 key 按当时时间重算并格式化 `YYYY-MM-DD HH:mm:ss`）、`isValidDateRange`（两端非空可解析且起点 ≤ 终点）、`linkDateRange`（编辑一端交叉时清空另一端）、`updateDateEndpoint`、`dateRangeQuery`（date-only 换算完整天）、`dateRangeLabel`（回显）、`dateRangePanelWidth`（datetime 445，带快捷栏 +112）、`defaultShortcuts`（今天/昨天/最近 7 天/最近 30 天/本周/本月/上月）。
- 本仓无独立单测文件（openlibing-web 仓承载纯函数测试），以页面手动验证为准。

### 2. CategorySearch `daterange` 类型重构

- `types.ts`：`CategorySearchType` 联合中 `'dateRange'` 重命名为 `'daterange'`；`CategorySearchCategory` 新增 `rangeShortcuts?: DateRangeShortcut[] | false`（`false` 表示不显示快捷时间栏）、`minDate`/`maxDate`。
- `CategorySearchEditor.vue`：
  - `draftDateRange: [string,string]|null` → `draftRange: DateRangeValue`（数组或快捷键 key 字符串）；watch 回显两形态。
  - range 模式渲染 `DateRangePanel`（`mode="datetime"`，透传 `shortcuts`/`minDate`/`maxDate`），编辑器容器宽度按 `dateRangePanelWidth` 设置，标题行隐藏，操作按钮行反转居中。
  - `canConfirm` 走 `validRange`：`isValidDateRange` + `resolvedRange[0] >= minDate` + `resolvedRange[1] 日期部分 <= maxDate`；不合法且两端已选时展示"结束时间不能早于开始时间"（`role="alert"`）。
  - 确认 emit 数组拷贝或快捷键 key 原值（保留相对时间语义）。
- `CategorySearch.vue`：`displayValue`/`fullDisplayValue` 对 daterange 走 `dateRangeText`（数组"起 至 止"、空端"不限"、key 显示快捷键名称）；已选/待选两个 popper 宽度按 `dateRangePanelWidth('datetime', rangeShortcuts)` 动态计算。

### 3. ColumnFilter 触发器 button 化

- `el-icon Filter` → 原生 `<button type="button">` + 内联 SVG 漏斗（stroke 描边风格），保留 `aria-label`（`${title}筛选`）；新增 `is-active` 激活态（图标填充高亮）与 hover 变色；`@click.stop` 防触发行点击。
- 面板仍复用 `CategorySearchEditor`——daterange 类型下宽度自适应与校验逻辑随 Editor 升级自动生效。

### 4. 流水线操作日志页重构

- **筛选模型**：`queryForm` 全量多值化（`operationModule: []`/`resourceName: []`/`userName: []`/`logResult: []`/`ip: []` + `dateRange`）；`searchModel` computed get/set 桥接 `CategorySearch` v-model。
- **筛选分类**：`searchCategories` computed——操作时间 `daterange`（默认快捷栏）+ 操作/资源名称/触发人员/IP checkbox（`searchable`）+ 执行结果 checkbox；选项 ref 由 filter-meta 填充。
- **filter-meta 服务端选项**：`loadFilterMeta` 以 `filterMetaDimensions = [moduleId, userName, resourceName, ip, logResult]` + 当前时间区间请求；`toFilterOptions` 转换（操作模块维度优先 `menuName`，`count` 存在时 label 拼 `(n)`）；失败/无项目回退空选项，执行结果回退"成功/失败"默认项；触发时机：项目切换、查询、页大小变化（翻页不重拉）。
- **查询 payload**：`buildPayload`——`resolveDateRange(dateRange, 'datetime', defaultShortcuts)` 动态换算 `startTime`/`endTime`（快捷键按查询时刻重算）；五维筛选以数组提交，操作字段名映射 `operationModule → moduleId`。
- **列集**：触发人员 / 操作（`menuName`，列头筛选值 `moduleId`）/ 资源名称（`resourceName || operationTargetName` 回退）/ 操作开始时间（`operationStartTime || operationDate`）/ 操作结束时间 / 执行结果 tag（成功=success、进行中=warning、其余=danger，label 兼容 `1`/`0` 旧值）/ IP / 失败信息 / 数据详情（fixed right）。
- **详情守卫**：`hasDetailData(row)` 兼容 `null`/空串/`'null'` 空形态，`exMessage` 或任一数据字段有实际内容才展示"展示详情"，否则"--"；详情 `parseJsonSafely` 预解析不变。
- **布局**：工具栏 CategorySearch（flex:1）+ 刷新按钮；移除"重置"按钮（CategorySearch 自带清空交互）；分页左对齐与代码仓日志页一致。
- **查询防抖**：既有 `queryTimer` watch 保留。

## 类设计

无新增类；均为组合式 API 页面内函数与组件 props/类型扩展。

## 数据模型设计

- `filterMeta` 响应结构：`{ filterMeta: { moduleId?, userName?, resourceName?, ip?, logResult?: Array<string | { value, menuName?, count? }> } }`。
- 列表查询 payload：`{ projectId, startTime?, endTime?, moduleId?: string[], resourceName?: string[], userName?: string[], logResult?: string[], ip?: string[], pageNum, pageSize }`。
- 无本地持久化，无 schema/迁移。

## 性能设计

- filter-meta `disabledLoading` 静默加载，不阻塞列表；仅查询/页大小变化/项目切换时重拉（翻页不重拉）。
- 列表查询防抖沿用 `queryTimer`。
- DateRangePanel 为页内懒挂载（popper 内条件渲染），不增加页面首屏成本。

## API接口设计

前端仅消费（无后端改动，本仓为前端仓）：

| 方法 | 路径（CICD 代理）                        | 用途                                                                                      |
| ---- | ---------------------------------------- | ----------------------------------------------------------------------------------------- |
| POST | `/logging/filter-meta`                   | 五维筛选选项（`filterMetaDimensions` + 可选时间区间），返回带 `menuName`/`count` 的选项集 |
| POST | `/logging/pipelineLog/list`              | 日志分页查询（请求/响应字段按新契约，见数据模型设计）                                     |
| —    | `/logging/users`、`/logging/targetNames` | 前端停止调用（封装保留在 api 层不删除）                                                   |

## 安全设计

- 筛选值均由服务端下发的选项集合约束（checkbox 多选，无自由文本注入面）；日期为组件受控值。
- 旧接口封装保留但不再调用，无新增敏感信息展示（失败信息 `exMessage` 为既有字段）。

## 影响范围

| 维度     | 说明                                                                                                                                                                                             |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 组件契约 | `CategorySearchType` 重命名为破坏性变更（`'dateRange'` → `'daterange'`），全仓 3 处调用方已同步并补 `rangeShortcuts: false`；`ColumnFilter` 触发器 DOM 结构变化（样式类 `active` → `is-active`） |
| 页面行为 | 流水线日志页筛选/列集/详情入口/分页对齐整体重构；查询字段名变更（`operationModule`→`moduleId` 等）                                                                                               |
| 接口契约 | 新消费 `/logging/filter-meta`；列表接口按新契约提交；停止调用 users/targetNames                                                                                                                  |
| 兼容性   | 展示层对旧字段做回退；新旧混存期间旧数据筛选值可能不命中                                                                                                                                         |
| 双仓同步 | `DateRangePicker`/CategorySearch daterange 改动与 openlibing-web 同源，后续缺陷修复需双仓同步                                                                                                    |

## 验证方式

1. `pnpm lint` 改动文件无新增 error/warn（移植组件已按本仓 prettier 配置格式化，`142a484`）。
2. 全仓检索确认无 `'dateRange'` 旧类型残留（SecurityOptions 3 处已同步，`f34a9e3`）。
3. 手动验证流水线日志页：CategorySearch 操作时间 daterange（快捷栏选择/回显/清空/未完整禁止确认）、五维 checkbox 筛选与列头筛选联动、filter-meta 选项 menuName 与 count 展示、执行结果 tag 三态、详情按钮空数据守卫、分页左对齐。
4. 手动验证 DateRangePanel：双月滚动、时间编辑、快捷键选择与查询时重算、min/max 禁选。
5. 手动验证 SecurityOptions 三处备案/扫描时间筛选：面板形态与升级前一致（无快捷栏），筛选功能正常。
