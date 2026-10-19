# 操作日志页面与日期范围组件 — proposal

- 变更目录：`spec/openlibing-web/task_design/2026-10-19-operation-log-page/`
- 业务分支：`dev-chenning-20260923-log`（fork 仓 `weixin_45521051/openlibing-web`）
- 基线：`upstream/master`，领先 27 个 commit，约 3770 行改动（24 文件）
- 日期：2026-10-19

## Why

1. 平台缺少统一操作日志查询入口：管理中心日志管理仅有业务日志/安全日志（复用旧 `find/all/logging` 接口），无按菜单维度组织的操作日志页，无法展示菜单标识、按菜单树筛选。
2. 代码仓管理页缺少项目维操作日志查询：代码仓的关键操作（录入、同步、配置变更等）无审计入口，项目成员无法按项目查看"谁在何时对什么资源做了什么、结果如何"。
3. 操作记录的前后数据对比缺少可视化：日志的 `oldData`/`newData` 为 JSON 字符串，需要并排 diff 展示。
4. 日期范围筛选体验差：原页面用两个独立时间选择器或原生 `el-date-picker` range，缺双月联动、快捷相对时间（今天/最近 7 天等）、时分秒编辑；`CategorySearch`/`ColumnFilter` 组件不支持日期/日期范围类型。
5. 菜单配置缺"是否记录日志"开关：菜单 URL 配置需支持 `writeLog` 字段控制是否记录操作日志。

## What Changes

- **新增 `DateRangePicker` 组件**（`src/components/DateRangePicker/`）：`DateRangePanel.vue` 为 DevUI 18.0.0 DatepickerPro 的 Vue 移植（附 `DEVUI-LICENSE`/`README`），双月滚动日历、时间编辑、动态快捷栏；`dateRange.ts` 纯函数层（`resolveDateRange`/`isValidDateRange`/`linkDateRange`/`updateDateEndpoint`/`dateRangeQuery`/`dateRangeLabel`/`dateRangePanelWidth`/`defaultShortcuts`），支持 `date`/`datetime` 两种 mode、`range`/`single` 两种 selection、`minDate`/`maxDate` 边界。
- **CategorySearch 扩展 4 种类型**：`date`/`datetime`/`daterange`/`datetimerange`；`daterange`/`datetimerange` 值为 `string[]` 或快捷键 key 字符串（查询时重算相对区间），新增 `rangeShortcuts`（数组或 `false`）、`minDate`/`maxDate` 配置；`date` 单选复用 `DateRangePanel(selection="single")`，`datetime` 用 `el-date-picker`；气泡宽度按面板与快捷栏动态计算；新增 `actions` 具名插槽（携带 `reset`）供页面自定义操作区。
- **ColumnFilter 扩展**：透传 4 种日期类型与 `rangeShortcuts`/`minDate`/`maxDate`，日期类型面板宽度自适应。
- **新增统一操作日志页**（`src/views/manageCenter/log/operationLogUnified.vue`）：挂载到管理中心「日志管理 → 操作日志」菜单（路由 `auth: log_manage`）；筛选含操作菜单树（`getOperationLogModules` 返回树 + `identification→menuName` 映射）、资源名称、日期范围、触发人员、执行结果；列含开始/结束时间、操作、菜单标识、资源名称、触发人员、触发人员 ID、执行结果（成功=绿/进行中=黄/失败=红 tag）、失败信息、IP、数据详情；详情弹窗用 `JsonDiffViewer` 展示操作前后数据对比。
- **新增代码仓操作日志页**（`src/views/Repos/operationLog.vue`，路由 `/apps/repoOperationLog` 免菜单页，从代码仓管理页「操作日志」按钮携带 `projectId` 跳转）：CategorySearch 组合筛选（操作时间 daterange + 操作/资源名称/触发人员/执行结果/IP 多选）+ 列头 ColumnFilter（时间列拆"操作开始时间/操作结束时间"两端单选联动）+ 数据详情对比弹窗；筛选项与列选项来自 `filter-meta` 服务端下发（`menuName` 优先展示、带 count）；`dateRangeQuery` 保证 date-only 查询按完整天换算时间戳；详情按钮对 `oldData`/`newData` 空形态（null/空串/'null'）守卫。
- **新增 `JsonDiffViewer` 组件**（`src/views/Repos/components/JsonDiffViewer.vue`）：`oldData`/`newData` 归一化（字符串递归 parse、对象 key 排序）后格式化为行级 diff，"操作前数据/操作后数据"双列并排，按行类型（增/删/同）着色；两个日志页共用。
- **代码仓管理页入口**（`views/Repos/index.vue`）：工具栏新增「操作日志」文字按钮（`repo_manage:query` 权限控制 + `NoPermissionPopover` + uem 埋点）。
- **菜单配置**（`views/authorityManagement/menu.vue`）：菜单 URL 配置项新增「是否记录日志」radio（`writeLog` 0=不记录/1=记录，默认 0），随配置保存下发。
- **API 层**：framework 统一日志三接口 `POST /manage/operation-logs/list`、`GET /manage/operation-logs/modules`、`GET /manage/operation-logs/{id}`；代码仓项目维日志两接口 `POST /repo/logging/list`、`POST /repo/logging/filter-meta`。
- **权限元数据**（`constants/permissions-meta.ts`）：新增 `repo_manage:query`（操作日志查询）介绍与授权指引。
- **路由**：`manageRouter.ts` 新增 `operationLog` 路由；`noMenu.ts` 新增 `repoOperationLog` 免菜单路由。
- **测试**：`DateRangePicker/__tests__/dateRange.spec.ts`（动态时间范围纯函数）；`CategorySearch/__tests__/datetime.spec.ts`（日期时间筛选回显/清空/取消、搜索条操作区重置、操作时间范围面板交互）。

## Capabilities

### New Capabilities

- `operation-log-query`: 平台级统一操作日志页的筛选（菜单树/资源/时间/人员/结果）与列表、详情 JSON 对比展示行为。
- `repo-operation-log`: 代码仓项目维操作日志页的组合筛选（CategorySearch + filter-meta 列头筛选 + 双端时间联动）与详情对比展示行为。
- `date-range-picker`: 通用日期/日期时间范围选择面板（DevUI 移植）及其纯函数层的取值/校验/联动/查询换算行为。
- `category-search-date-types`: CategorySearch/ColumnFilter 对 date/datetime/daterange/datetimerange 四类条件的编辑、回显、校验与重置行为。

### Modified Capabilities

- 菜单配置（既有页面增量字段）：菜单 URL 配置新增 `writeLog` 选项，默认不记录，存量配置行为不变。

## Impact

- **受影响代码**：
  - 新增：`src/components/DateRangePicker/`（DateRangePanel.vue、dateRange.ts、index.ts、README、DEVUI-LICENSE、`__tests__/dateRange.spec.ts`）、`src/views/Repos/operationLog.vue`、`src/views/Repos/components/JsonDiffViewer.vue`、`src/views/manageCenter/log/operationLogUnified.vue`、`src/components/CategorySearch/__tests__/datetime.spec.ts`
  - 修改：`src/components/CategorySearch/CategorySearch.vue`、`CategorySearchEditor.vue`、`types.ts`；`src/views/Repos/components/ColumnFilter.vue`、`index.vue`；`src/views/authorityManagement/menu.vue`；`src/views/manageCenter/index.vue`；`src/router/manageRouter.ts`、`src/router/routes/modules/noMenu.ts`；`src/api/api.ts`、`src/api/url.ts`、`src/api/Repos/api.ts`、`src/api/Repos/url.ts`；`src/constants/permissions-meta.ts`
- **受影响接口**（framework/repo 网关代理）：`POST /manage/operation-logs/list`、`GET /manage/operation-logs/modules`、`GET /manage/operation-logs/{id}`、`POST /repo/logging/list`、`POST /repo/logging/filter-meta`；菜单配置保存接口新增 `writeLog` 字段。
- **风险**：
  - 相对快捷键（今天/最近 7 天等）以 key 字符串存储、查询时以当时时间重算，跨天打开页面区间会随时间漂移（预期语义，但需与用户预期一致）。
  - `date` 模式查询经 `dateRangeQuery` 换算为完整天（00:00:00 ~ 23:59:59），依赖后端时间字段口径为 `YYYY-MM-DD HH:mm:ss`。
  - `filter-meta` 选项随当前时间筛选联动下发，选项集随筛选变化；选项量大时依赖服务端裁剪。
  - `JsonDiffViewer` 对非 JSON 字符串直接按文本展示，超大 JSON 无虚拟化，极端数据量下渲染性能受限。
  - 菜单配置 `writeLog` 为可选字段，旧后端不支持时保存该字段可能被忽略（不报错）。
