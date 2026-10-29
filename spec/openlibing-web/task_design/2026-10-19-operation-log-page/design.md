# 操作日志页面与日期范围组件 — design

## 总体结构

改动分四块：通用日期范围组件、CategorySearch/ColumnFilter 类型扩展、两个操作日志页面、菜单配置与路由权限，全部位于 `apps/web-openlibing/src/`：

```text
components/DateRangePicker/            # DevUI DatepickerPro 的 Vue 移植 + 纯函数层
  DateRangePanel.vue / dateRange.ts / index.ts / README.md / DEVUI-LICENSE
components/CategorySearch/             # +date/datetime/daterange/datetimerange 四类型
views/Repos/components/ColumnFilter.vue # 列头筛选透传日期类型
views/Repos/components/JsonDiffViewer.vue  # JSON 前后对比（两日志页共用）
views/Repos/operationLog.vue           # 项目维操作日志页（/apps/repoOperationLog）
views/manageCenter/log/operationLogUnified.vue # 平台统一操作日志页
views/Repos/index.vue                  # 操作日志入口按钮
views/authorityManagement/menu.vue     # 菜单配置 writeLog
router/manageRouter.ts / routes/modules/noMenu.ts
api/{api,url}.ts、api/Repos/{api,url}.ts
constants/permissions-meta.ts
```

## 关键设计决策

### 1. DateRangePicker：快捷键存 key、查询时重算（相对时间语义）

- `DateRangeValue = string[] | string`：数组为绝对区间，字符串为快捷键 key（`today`/`yesterday`/`last7Days`/`last30Days`/`thisWeek`/`thisMonth`/`lastMonth`）。
- `resolveDateRange(value, mode, shortcuts, now)`：数组直通拷贝；key 经 `shortcut.getRange(now)` 重算并按 mode 格式化（date=`YYYY-MM-DD`，datetime=`YYYY-MM-DD HH:mm:ss`）——**相对区间在每次查询时以当时时间重算**，面板展示与查询口径一致。
- `isValidDateRange`：两端非空、可解析、起点 ≤ 终点；`linkDateRange`：编辑一端后若与另一端交叉，同日 datetime 场景对齐为同值，否则清空另一端；`updateDateEndpoint`：编辑表头冻结当前相对区间、仅改单端（date 粒度）。
- `dateRangeQuery`：date-only UI 查询完整天——起点 `startOf('day')`、终点 `endOf('day')`，输出 `startTime`/`endTime`（`YYYY-MM-DD HH:mm:ss`）。
- `dateRangePanelWidth`：date 330 / datetime 445，带快捷栏 +112；CategorySearch 气泡与 ColumnFilter popover 宽度共用该计算。
- `DateRangePanel.vue` 为 DevUI 18.0.0 DatepickerPro 的 Vue 移植（保留 `DEVUI-LICENSE`），支持 `selection="range"|"single"`（single 隐藏快捷栏）、双月滚动、时间编辑、hover 预览。
- 纯函数层配 `dateRange.spec.ts`；面板交互配 `datetime.spec.ts`（回显/清空/取消草稿/范围未完整禁止确认/终点禁选早于起点）。

### 2. CategorySearch 四种日期类型

- `CategorySearchType` 扩展 `date`/`datetime`/`daterange`/`datetimerange`；`CategorySearchCategory` 新增 `rangeShortcuts?: DateRangeShortcut[] | false`、`minDate`/`maxDate`。
- `daterange`/`datetimerange`：编辑器内嵌 `DateRangePanel`（range 模式），确认提交 `[start, end]` 数组或快捷键 key；未完整选择时禁止确认；校验失败提示「结束时间不能早于开始时间」；`minDate`/`maxDate` 约束两端。
- `date`：复用 `DateRangePanel` + `selection="single"`（无快捷栏），单值写入文本草稿，受 `minDate`/`maxDate` 约束。
- `datetime`：`el-date-picker`（`category-search-date-popper` popper，避免外点关闭误判），`value-format="YYYY-MM-DD HH:mm:ss"`。
- 回显：`displayValue`/`fullDisplayValue` 对 range 类型走 `dateRangeLabel`（数组 `起 至 止`，空端显示「不限」；key 显示快捷键 label）。
- 气泡宽度：range 类型按 `dateRangePanelWidth` 动态设置；日期类编辑器仅在 `editingField === field` 时挂载（避免多面板同渲染）。
- 外点关闭判断把 `.category-search-date-popper` 一并排除。
- 新增 `actions` 具名插槽（作用域 `reset`）替代内置清空按钮（`v-else-if` 衔接），页面可自定义操作区；`clearAll` 去掉早退守卫保证空态也可复位。

### 3. 两个日志页面共用 JsonDiffViewer、各自筛选形态

- **JsonDiffViewer**：入参 `oldData`/`newData`（对象/数组/字符串/原始值均可）；`normalizeJsonValue` 递归 parse JSON 字符串并按 key 排序，保证同构数据 diff 稳定；格式化为行级 `is-add/is-del/is-same` 三态着色，「操作前数据/操作后数据」双列并排滚动。
- **统一操作日志页**（option API）：`getOperationLogModules` 拉菜单树，`el-tree-select`（`check-strictly` + `identification` 节点键）选操作，`identification→menuName` map 做列表/详情展示转换；人员用 `ContactInformation`；时间用原生 `el-date-picker datetimerange`；列含菜单标识（`moduleId`）独立列；详情走 `GET /manage/operation-logs/{id}`。
- **项目维操作日志页**（script setup）：CategorySearch 组合筛选（操作时间 `daterange` + 操作/资源名称/触发人员/执行结果/IP checkbox，均 `searchable`）；列头 `ColumnFilter` —— 时间拆「操作开始时间/操作结束时间」两个 `date` 单选，经 `computed` get（`resolveDateRange` 取端）+ set（`updateDateEndpoint` 写端）与 `timeRange` 双向联动，起止互为 min/max 约束。
- **filter-meta 服务端选项**：`filterMetaDimensions = [moduleId, userName, resourceName, ip, logResult]` 随当前时间区间请求；选项转换优先 `menuName`（操作模块维度），带 `count` 时 label 拼接 `(n)`。
- **查询口径**：`buildQuery` 组合全部筛选 + `dateRangeQuery(timeRange)` 的 `startTime`/`endTime`；`queryDate` 在每次构建查询时刷新，保证相对快捷键按查询时刻重算。
- **防重复加载**：`handleRefresh` 复用同一 `timeQuery` 同时刷列表与 filter-meta，避免两次计算不一致；搜索重置页码。
- **详情守卫**：`hasDetailData` 兼容 `null`/空串/`'null'` 形态，任一字段有实际内容才展示「展示详情」；详情数据懒加载（`GET /manage/operation-logs/{id}`）。
- 执行结果 tag：成功=success、进行中=warning、其余=danger。

### 4. 入口、路由与权限

- 代码仓管理页工具栏「操作日志」按钮：`repo_manage:query` 操作码 + `NoPermissionPopover`（无权限气泡说明授权路径）+ disabled 置灰 + uem 埋点；点击 `router.push('/apps/repoOperationLog?projectId=')`。
- `noMenu.ts` 注册 `repoOperationLog` 免菜单路由（`hideInMenu` + `noKeepAlive`）；页面从 `route.query.projectId` 取项目上下文，缺失时不发请求。
- `manageRouter.ts` 注册管理中心 `operationLog` 路由（`auth: log_manage`），`manageCenter/index.vue` 日志管理子菜单加「操作日志」项。
- `permissions-meta.ts` 新增 `repo_manage:query`：操作日志查询权限的介绍与授权指引（项目管理员角色 / 服务单）。

### 5. 菜单配置 writeLog

- 菜单 URL 配置项新增「是否记录日志」radio（0=不记录默认 / 1=记录），随行数据读取（`url.writeLog || 0` 兜底）、新增行与模板默认值统一 0；label 宽度 150→135 适配布局。

## 影响范围

| 维度      | 说明                                                                                                                                                                  |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 组件契约  | `DateRangePanel`/`JsonDiffViewer` 为新增通用组件；`CategorySearch`/`ColumnFilter` 类型联合扩展为向后兼容新增（原三种类型行为不变，`clearAll` 移除早退守卫为行为微调） |
| 接口契约  | 消费 `/manage/operation-logs/*` 与 `/repo/logging/*` 新接口；菜单配置保存新增可选 `writeLog`                                                                          |
| 路由/权限 | 新增两条路由；新增 `repo_manage:query` 操作码依赖后端下发；统一日志页挂 `log_manage`                                                                                  |
| 样式      | CategorySearch 容器高度/输入框高度微调（36/28px）+ `box-sizing`，对既有使用方为视觉微调                                                                               |
| 测试      | 新增 `dateRange.spec.ts`（155 行）与 `datetime.spec.ts`（560 行）两组单测                                                                                             |
| 兼容性    | 旧业务日志/安全日志页不动；未配置 `writeLog` 的菜单按不记录处理                                                                                                       |

## 验证方式

1. `pnpm lint`（改动文件 ESLint）无新增 error/warn；`pnpm check:type` 无本模块相关错误。
2. `pnpm test:unit` 运行 `dateRange.spec.ts`、`datetime.spec.ts` 全部通过。
3. 手动验证 DateRangePanel：双月滚动、时间编辑、快捷键选择与回显、min/max 禁选、single 模式。
4. 手动验证 CategorySearch：四类日期条件添加/编辑/回显/清空；快捷键条件跨天重算；actions 插槽重置按钮生效。
5. 手动验证统一日志页：菜单树筛选、列表列展示、详情 JSON 对比、分页；权限 `log_manage`。
6. 手动验证项目维日志页：入口按钮权限置灰；组合筛选 + 列头筛选联动；起止时间互约束；filter-meta 选项随时间区间变化；详情空数据守卫；刷新不重复加载。
7. 手动验证菜单配置：writeLog 默认不记录、保存回显。
