# 流水线操作日志页对齐与日期范围组件 — tasks

> 实现已随业务分支 `dev-chenning-20260923-log` 完成，本清单按实际交付内容勾选。

## 1. DateRangePicker 组件（DevUI 移植，仓内副本）

- [x] 1.1 新增 `DateRangePanel.vue`：DevUI 18.0.0 DatepickerPro 的 Vue 移植（附 `DEVUI-LICENSE`、`README.md`），双月滚动日历、时间编辑、快捷时间栏、`minDate`/`maxDate` 边界。
- [x] 1.2 新增 `dateRange.ts` 纯函数层：`resolveDateRange`（快捷键 key 查询时重算）、`isValidDateRange`、`linkDateRange`、`updateDateEndpoint`、`dateRangeQuery`、`dateRangeLabel`、`dateRangePanelWidth`、`defaultShortcuts`。
- [x] 1.3 新增 `index.ts` 统一导出。
- [x] 1.4 移植组件按本仓 prettier 配置格式化（`142a484`）。

## 2. CategorySearch daterange 类型重构

- [x] 2.1 `types.ts`：`'dateRange'` 重命名为 `'daterange'`；新增 `rangeShortcuts`/`minDate`/`maxDate`。
- [x] 2.2 `CategorySearchEditor.vue`：内嵌 `DateRangePanel`（datetime mode）替代原生 `el-date-picker`；草稿数组/快捷键 key 两形态回显；`validRange` 校验（起止顺序 + min/max）与"结束时间不能早于开始时间"提示（role=alert）；未完整选择禁止确认；range 模式编辑器宽度/标题/操作按钮行样式适配。
- [x] 2.3 `CategorySearch.vue`：daterange 回显走 `dateRangeLabel`（空端"不限"/快捷键名称）；已选/待选 popper 宽度按 `dateRangePanelWidth` 动态计算。

## 3. ColumnFilter 触发器重构

- [x] 3.1 触发器 `el-icon Filter` → 原生 `<button>` + 内联 SVG 漏斗，保留 `aria-label`，新增 `is-active` 激活态与 hover 变色，`@click.stop`。
- [x] 3.2 面板复用 `CategorySearchEditor`，daterange 宽度自适应随 Editor 升级生效。

## 4. 流水线操作日志页重构（PipelineLog/index.vue）

- [x] 4.1 筛选重构：原生日期选择器 + 散落下拉 → CategorySearch 组合筛选（操作时间 daterange + 操作/资源名称/触发人员/执行结果/IP checkbox 多选）+ 刷新按钮；移除"重置"按钮（`edb99f6`）；`searchModel` computed 桥接 v-model。
- [x] 4.2 筛选选项服务端化：`POST /logging/filter-meta` 五维（moduleId/userName/resourceName/ip/logResult）随时间区间联动，查询/页大小变化重拉；选项 `menuName` 优先展示、count 拼 `(n)`（`0c0de08`）；删除前端硬编码操作/模块枚举；执行结果回退"成功/失败"默认项；下线 users/targetNames 接口调用。
- [x] 4.3 查询 payload 多值化：`moduleId`/`resourceName`/`userName`/`ip`/`logResult` 数组 + `resolveDateRange` 按查询时刻换算 `startTime`/`endTime`。
- [x] 4.4 列集重构：触发人员/操作（menuName，筛选值 moduleId）/资源名称/操作开始时间/操作结束时间/执行结果 tag/IP/失败信息/数据详情；列头筛选 `TableHeaderFilter` → `ColumnFilter`（`3eb8975` 模块筛选移入操作列，`902215e` 列拆分，`bc01887` 下线菜单 ID 列并重排序）。
- [x] 4.5 执行结果 tag 三态：成功=绿/进行中=黄/失败=红，label 兼容旧值 1/0（`be56741`）。
- [x] 4.6 详情按钮空数据守卫 `hasDetailData`（兼容 null/空串/'null'，`b74ff05`）；详情弹窗操作模块展示优先 menuName → moduleId → operationModule → module（`ade826f`）。
- [x] 4.7 布局：工具栏 CategorySearch + 刷新按钮样式、分页左对齐（`b00307c`）。

## 5. 调用方同步与 API 层

- [x] 5.1 SecurityOptions 三处 `type: 'dateRange'` → `'daterange'` 并补 `rangeShortcuts: false`（保持原交互无快捷栏，`f34a9e3`）。
- [x] 5.2 `api/urls.ts` 新增 `PIPELINE_OPERATION_LOG_FILTER_META`（`/logging/filter-meta`）；`api/api.ts` 新增 `getPipelineOperationLogFilterMeta` 封装。

## 6. 验证

- [x] 6.1 改动文件 ESLint 通过，无新增 error/warn；移植组件按本仓 prettier 配置格式化。
- [x] 6.2 全仓无 `'dateRange'` 旧类型残留（3 处调用方已同步）。
- [x] 6.3 手动验证：流水线日志页 daterange 筛选（快捷栏/回显/清空/未完整禁止确认）、五维筛选与列头筛选、filter-meta 选项展示、执行结果三态 tag、详情守卫、分页对齐。
- [x] 6.4 手动验证：DateRangePanel 双月滚动/时间编辑/快捷键/min-max 禁选。
- [x] 6.5 手动验证：SecurityOptions 三处备案/扫描时间筛选形态与功能不变。
