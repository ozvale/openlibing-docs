# 操作日志页面与日期范围组件 — tasks

> 实现已随业务分支 `dev-chenning-20260923-log` 完成，本清单按实际交付内容勾选。

## 1. DateRangePicker 组件（DevUI 移植）

- [x] 1.1 新增 `DateRangePanel.vue`：DevUI 18.0.0 DatepickerPro 的 Vue 移植（附 `DEVUI-LICENSE`、`README.md`），双月滚动日历、时间编辑、hover 预览、`range`/`single` 两种 selection、`minDate`/`maxDate` 边界。
- [x] 1.2 新增 `dateRange.ts` 纯函数层：`resolveDateRange`（key 查询时重算）、`isValidDateRange`、`linkDateRange`（编辑端联动清空/对齐）、`updateDateEndpoint`（表头冻结区间改单端）、`dateRangeQuery`（date-only 换算完整天）、`dateRangeLabel`、`dateRangePanelWidth`、`defaultShortcuts`（今天/昨天/最近 7 天/最近 30 天/本周/本月/上月）。
- [x] 1.3 新增 `index.ts` 统一导出组件、函数与类型（`DateRangeMode`/`DateRangeShortcut`/`DateRangeValue`）。
- [x] 1.4 新增 `__tests__/dateRange.spec.ts`：动态时间范围解析/校验/联动/查询换算用例。

## 2. CategorySearch / ColumnFilter 类型扩展

- [x] 2.1 `types.ts`：`CategorySearchType` 扩展 `date`/`datetime`/`daterange`/`datetimerange`；`CategorySearchCategory` 新增 `rangeShortcuts`/`minDate`/`maxDate`。
- [x] 2.2 `CategorySearchEditor.vue`：range 内嵌 `DateRangePanel`（未完整禁止确认 + 越界错误提示）、date 用 `selection="single"` 单选、datetime 用 `el-date-picker`；草稿回显数组/字符串两形态；`minDate`/`maxDate` 校验。
- [x] 2.3 `CategorySearch.vue`：range 回显走 `dateRangeLabel`（空端「不限」/快捷键 label）；气泡宽度按 `dateRangePanelWidth` 动态计算；日期类编辑器条件挂载；外点关闭排除 `.category-search-date-popper`；新增 `actions` 插槽（作用域 `reset`）替代内置清空按钮；`clearAll` 移除早退守卫。
- [x] 2.4 `ColumnFilter.vue`：type 联合扩展四种日期类型，透传 `rangeShortcuts`/`minDate`/`maxDate`，面板宽度自适应，range 重置 emit `[]`。
- [x] 2.5 新增 `CategorySearch/__tests__/datetime.spec.ts`：日期时间筛选回显/清空/取消草稿、搜索条操作区重置、范围面板选择与确认约束用例。

## 3. 统一操作日志页（管理中心）

- [x] 3.1 新增 `manageCenter/log/operationLogUnified.vue`：操作菜单树（`el-tree-select` + `identification→menuName` 映射）、资源名称、日期范围、触发人员、执行结果筛选；分页列表。
- [x] 3.2 列展示：开始/结束时间、操作（名称映射）、菜单标识（`moduleId`）、资源名称、触发人员、触发人员 ID、执行结果（成功=绿/进行中=黄/失败=红）、失败信息、IP、数据详情。
- [x] 3.3 详情弹窗：`GET /manage/operation-logs/{id}` 懒加载 + `JsonDiffViewer` 前后对比。
- [x] 3.4 路由与菜单：`manageRouter.ts` 注册 `operationLog`（`auth: log_manage`）；管理中心日志管理子菜单新增「操作日志」项。

## 4. 代码仓项目维操作日志页

- [x] 4.1 新增 `Repos/operationLog.vue`：CategorySearch 组合筛选（操作时间 `daterange` + 操作/资源名称/触发人员/执行结果/IP）+ 刷新按钮（同一 timeQuery 复用防重复加载）+ 分页。
- [x] 4.2 列头筛选：触发人员/操作/资源名称/IP/执行结果 checkbox + 操作开始/结束时间 `date` 单选（computed + `updateDateEndpoint` 与 `timeRange` 双向联动、起止互为 min/max）；筛选确认/重置触发查询。
- [x] 4.3 `filter-meta` 选项服务端下发：`filterMetaDimensions` 五维随时间区间请求，选项 `menuName` 优先展示、count 拼接 label。
- [x] 4.4 查询口径：`dateRangeQuery` 按完整天换算 `startTime`/`endTime`；相对快捷键按查询时刻重算；`projectId` 缺失不发请求。
- [x] 4.5 详情守卫与懒加载：`hasDetailData` 兼容 `null`/空串/`'null'` 空形态；`GET /manage/operation-logs/{id}` 拉详情 + `JsonDiffViewer` 对比。
- [x] 4.6 代码仓管理页入口：`Repos/index.vue` 工具栏「操作日志」按钮（`repo_manage:query` 权限 + `NoPermissionPopover` + uem 埋点），跳转 `/apps/repoOperationLog?projectId=`；`noMenu.ts` 注册免菜单路由。

## 5. JsonDiffViewer 组件

- [x] 5.1 新增 `Repos/components/JsonDiffViewer.vue`：`normalizeJsonValue` 递归 parse 字符串 + key 排序；行级 `is-add/is-del/is-same` 三态着色；「操作前数据/操作后数据」双列并排。
- [x] 5.2 两个日志页详情弹窗统一接入该组件（统一日志页从各自实现收敛为共用样式）。

## 6. 菜单配置、API 与权限元数据

- [x] 6.1 `authorityManagement/menu.vue`：URL 配置项新增「是否记录日志」radio（`writeLog` 0=不记录默认 / 1=记录），读取兜底、新增行默认、label 宽度适配。
- [x] 6.2 API 层：framework `POST /manage/operation-logs/list`、`GET /manage/operation-logs/modules`、`GET /manage/operation-logs/{id}`；repo `POST /repo/logging/list`、`POST /repo/logging/filter-meta`。
- [x] 6.3 `permissions-meta.ts` 新增 `repo_manage:query`（操作日志查询）介绍与授权指引。

## 7. 验证

- [x] 7.1 改动文件 ESLint 通过，无新增 error/warn。
- [x] 7.2 `dateRange.spec.ts`、`datetime.spec.ts` 单测通过。
- [x] 7.3 手动验证：DateRangePicker 双月滚动/时间编辑/快捷键/min-max 禁选；CategorySearch 四类日期条件与重置；范围未完整禁止确认。
- [x] 7.4 手动验证：统一日志页菜单树筛选与详情对比；项目维日志页组合筛选、列头起止时间联动、filter-meta 选项、详情空数据守卫。
- [x] 7.5 手动验证：入口按钮无权限置灰；`writeLog` 默认不记录、保存回显。
- [x] 7.6 过程修复记录：详情按钮空数据守卫、刷新防重复加载、重置 tooltip 文案「清空筛选条件」、操作列拆分菜单名称/菜单标识并下线菜单 ID 列、执行结果 tag 支持进行中态、less 孤立花括号构建报错修复、JsonDiffViewer 移至统一日志页共用。
