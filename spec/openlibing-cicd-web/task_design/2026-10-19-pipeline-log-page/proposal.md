# 流水线操作日志页对齐与日期范围组件 — proposal

- 变更目录：`spec/openlibing-cicd-web/task_design/2026-10-19-pipeline-log-page/`
- 业务分支：`dev-chenning-20260923-log`（fork 仓 `weixin_45521051/openlibing-cicd-web`）
- 基线：`upstream/master`，领先 13 个 commit，约 1648 行新增 / 387 行删除（16 文件）
- 日期：2026-10-19

## Why

1. 流水线操作日志页（`views/pipeline/PipelineLog/`）与代码仓操作日志页形态不一致：原生 `el-date-picker` datetimerange + 三个下拉（操作模块/操作对象/触发人员）散落页面，筛选体验与代码仓日志页（CategorySearch 组合筛选 + 列头筛选）割裂。
2. 操作/模块枚举硬编码在前端（13 个 `operationOptions` + 3 个 `moduleOptions`），后端菜单化改造后枚举由服务端管理，前端需要切换为 `filter-meta` 服务端下发，展示 `menuName` 并带条数。
3. 接口契约变化：日志字段从 `operationModule`/`operation`/`operationTargetName`/`operationDate`/`operationResult` 迁移为 `moduleId`/`menuName`/`resourceName`/`operationStartTime`/`operationEndTime`/`logResult`（含"进行中"态）。
4. 日期范围选择体验差：原生 `el-date-picker` 缺双月联动、时分秒编辑与项目统一的快捷时间栏；`CategorySearch` 的 `dateRange` 类型基于原生选择器，需换用与 openlibing-web 同源的 `DateRangePanel` 共享面板。
5. 细节缺陷：详情按钮对空 `oldData`/`newData`（null/空串/`'null'`）仍展示；执行结果缺"进行中"态颜色；分页右对齐与代码仓日志页不一致。

## What Changes

- **新增 `DateRangePicker` 组件**（`src/components/DateRangePicker/`）：`DateRangePanel.vue` 为 DevUI 18.0.0 DatepickerPro 的 Vue 移植（附 `DEVUI-LICENSE`/`README`），双月滚动日历、时间编辑、快捷时间栏、`minDate`/`maxDate` 边界；`dateRange.ts` 纯函数层（`resolveDateRange`/`isValidDateRange`/`linkDateRange`/`updateDateEndpoint`/`dateRangeQuery`/`dateRangeLabel`/`dateRangePanelWidth`/`defaultShortcuts`），`datetime` mode；`index.ts` 统一导出。
- **CategorySearch `daterange` 类型重构**（`CategorySearch/types.ts`、`CategorySearchEditor.vue`、`CategorySearch.vue`）：
  - 类型重命名 `'dateRange'` → `'daterange'`，新增 `rangeShortcuts?: DateRangeShortcut[] | false`、`minDate`/`maxDate` 配置。
  - 编辑器内嵌 `DateRangePanel`（`datetime` mode），替代原生 `el-date-picker`；草稿支持数组与快捷键 key 两形态回显；校验起止顺序（"结束时间不能早于开始时间"，`role="alert"`）与 `minDate`/`maxDate` 边界；未完整选择禁止确认。
  - 已选回显走 `dateRangeLabel`（数组"起 至 止"、空端"不限"、快捷键显示名称）；气泡与编辑器宽度按 `dateRangePanelWidth('datetime', rangeShortcuts)` 动态计算。
- **ColumnFilter 触发器重构**（`components/ColumnFilter.vue`）：`el-icon Filter` 换为原生 `<button>` + 内联 SVG 漏斗图标（保留 `aria-label`，新增 `is-active` 激活态填充、`@click.stop`）；筛选面板仍复用 `CategorySearchEditor`（daterange 面板宽度自适应随之生效）。
- **流水线操作日志页重构**（`views/pipeline/PipelineLog/index.vue`，607 行变更）：
  - 筛选：原生日期选择器 + 散落下拉 → `CategorySearch` 组合筛选（操作时间 `daterange` + 操作/资源名称/触发人员/执行结果/IP checkbox 多选）+ 刷新按钮；移除"重置"按钮。
  - 筛选选项服务端化：`POST /logging/filter-meta` 按 `filterMetaDimensions = [moduleId, userName, resourceName, ip, logResult]` 拉取五维选项（随当前时间区间联动，查询/翻页大小变化时重拉）；选项转换 `menuName` 优先展示、带 `count` 时 label 拼接 `(n)`；删除前端硬编码操作/模块枚举与 `getPipelineOperationLogUsers`/`getPipelineOperationLogTargets` 两个旧接口调用；执行结果无 meta 时回退"成功/失败"默认项。
  - 查询 payload：多值数组（`moduleId`/`resourceName`/`userName`/`ip`/`logResult`）+ `resolveDateRange` 动态换算 `startTime`/`endTime`（快捷键 key 按查询时刻重算）。
  - 列重构：日期/操作模块/操作类型/备注/操作对象/触发人员/触发人员ID/操作结果 → 触发人员、操作（展示 `menuName`，列头筛选值为 `moduleId`）、资源名称（`resourceName` 回退 `operationTargetName`）、操作开始时间、操作结束时间、执行结果（tag：成功=绿/进行中=黄/失败=红）、IP、失败信息、数据详情；列头筛选 `TableHeaderFilter` → `ColumnFilter`。
  - 详情按钮守卫 `hasDetailData`：兼容 `oldData`/`newData` 为 null/空串/`'null'` 形态，任一有实际内容（或有 `exMessage`）才展示；分页改左对齐。
  - 详情弹窗（`DetailDialog.vue`）：操作模块展示优先级调整为 `menuName` → `moduleId` → `operationModule` → `module`。
- **SecurityOptions 调用方同步**（`SecurityOptions/index.vue`、`FilingRecordsView.vue`、`FilingListView.vue`）：3 处 `type: 'dateRange'` 同步重命名为 `'daterange'` 并补 `rangeShortcuts: false`（不带快捷时间栏，保持原交互形态一致）。

## Capabilities

### New Capabilities

- `pipeline-log-query`: 流水线操作日志页的组合筛选（CategorySearch daterange + 五维 checkbox）、filter-meta 服务端选项联动、多值查询 payload 与执行结果 tag 行为。
- `date-range-panel`: 共享日期时间范围选择面板（DevUI 移植）及其纯函数层的取值/校验/联动/换算行为（本仓 `datetime` mode 场景）。
- `category-search-daterange`: CategorySearch/ColumnFilter 对 `daterange` 条件的编辑、回显、校验与重命名后契约。

### Modified Capabilities

- 流水线操作日志页展示（既有页面重构）：列集、详情入口守卫、分页对齐方式更新；详情弹窗操作模块取值优先级更新。
- SecurityOptions 三个页面：筛选类型标识重命名，交互形态不变（`rangeShortcuts: false`）。

## Impact

- **受影响代码**：
  - 新增：`src/components/DateRangePicker/`（DateRangePanel.vue、dateRange.ts、index.ts、README、DEVUI-LICENSE）
  - 修改：`src/components/CategorySearch/{CategorySearch,CategorySearchEditor}.vue`、`types.ts`；`src/components/ColumnFilter.vue`；`src/views/pipeline/PipelineLog/{index,DetailDialog}.vue`；`src/views/SecurityOptions/{index,FilingRecordsView,FilingListView}.vue`；`src/api/{api,urls}.ts`
- **受影响接口**：新增 `POST /logging/filter-meta`（CICD 网关代理，入参 `projectId` + `filterMetaDimensions` + 可选 `startTime`/`endTime`，出参 `filterMeta` 五维选项含 `menuName`/`count`）；`/logging/pipelineLog/list` 请求字段更新为多值数组 + `moduleId`/`resourceName`/`ip`，响应字段更新为 `menuName`/`operationStartTime`/`operationEndTime`/`logResult`/`exMessage`；下线前端对 `/logging/users`、`/logging/targetNames` 的调用。
- **风险**：
  - 类型重命名 `'dateRange'` → `'daterange'` 为破坏性契约，全仓调用方必须同步（本次 3 处 SecurityOptions 已同步，遗漏会导致筛选面板不渲染）。
  - `filter-meta` 选项随时间区间联动，选项集随筛选变化；选项量大时依赖服务端裁剪。
  - 快捷键 key 存储后按查询时刻重算区间，跨天打开页面区间会随时间漂移（预期语义）。
  - 旧日志数据可能仍是 `operationModule`/`operationTargetName` 等旧字段，展示层做了回退（`resourceName || operationTargetName`、`operationStartTime || operationDate`），但筛选值仅按新契约提交，新旧混存期间旧数据可能筛不中。
  - `DateRangePanel` 为大体积移植组件（约千行），两个前端仓各持有一份副本，后续修 bug 需双仓同步。
