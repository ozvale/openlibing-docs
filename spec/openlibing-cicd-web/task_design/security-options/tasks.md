# Tasks: 安全编译选项数据工程能力建设

## 进度: 36/36 complete

### 阶段一：API 层与基础数据

- [x] 1. 创建 `src/api/SecurityOptions/url.ts`，定义 8 个接口 URL 常量（overview / dropdown / file-detail / filing 的 save / cancel / list / record-list / filer-list）
- [x] 2. 创建 `src/api/SecurityOptions/api.ts`，基于 `ApiClient` 封装 8 个 POST 请求函数
- [x] 3. 创建 `src/views/SecurityOptions/constants.ts`，定义 14 项安全编译选项元数据（`SEC_OPTIONS` / `SEC_OPTION_KEYS` / `UNSCANNED_VALUE` / `OPTION_VALUE_TYPE` / `rateClass`）

### 阶段二：自研组件沉淀

- [x] 4. 创建 `src/components/CategorySearch/types.ts`，定义 `CategorySearchType` / `CategorySearchCategory` / `CategorySearchModel` / `CategorySearchChangeEvent` 等类型
- [x] 5. 创建 `src/components/CategorySearch/CategorySearchEditor.vue`，按 `type` 渲染 `el-select` / `el-input` / `el-date-picker`
- [x] 6. 创建 `src/components/CategorySearch/CategorySearch.vue`，作为容器聚合多个 `CategorySearchEditor`，触发 `add` / `clear` / `remove` / `update` 事件
- [x] 7. 创建 `src/components/CategorySearch/index.ts`，导出对外接口
- [x] 8. 创建 `src/components/ColumnFilter.vue`，提供表格列筛选器（`el-checkbox-group`）
- [x] 9. 增强 `src/components/TableHeaderFilter.vue`，新增 `placement` / `popperClass` props，支持弹层挂载位置与样式定制
- [x] 10. 适配 `src/components/BatchOperation.vue`，支持 filing 场景的批量操作

### 阶段三：主页面与文件详情弹窗

- [x] 11. 重构 `src/views/SecurityOptions/index.vue` 主页面，接入 `CategorySearch` 工具栏 + el-table + el-pagination
- [x] 12. 主页面表格列调整对齐 demo（`adjust overview table columns per demo`）：3 列固定 + 14 列安全指标 + 概要列
- [x] 13. 主页面表格头部筛选 + 表格排序统一为 `sortByField` / `sort`（`refactor filing list with header filters and rename endpoint`）
- [x] 14. 主页面接入 `CategorySearch` 工具栏与表头筛选（`add CategorySearch toolbar and table header filters`）
- [x] 15. 主页面新增多选筛选 + 时间排序 + filing 权限控制（`add multi-select filters, time sort and filing permission control`）
- [x] 16. 主页面新增代码仓与文件路径筛选，移除备案记录排序（`add repo and file path filters and drop sort on filing records`）
- [x] 17. 主页面文件扫描结果总览按已扫描项过滤，与产物包详情对齐（`fix(security): 文件扫描结果总览按已扫描项过滤与产物包详情对齐`）
- [x] 18. 改造 `src/views/SecurityOptions/FileDetailDialog.vue`：popover 挂载到 dialog body，`rawOptions` 重命名为 `options`
- [x] 19. `FileDetailDialog` 列标签在产物包详情视图对齐调整（`rename filing column labels in package detail view`）

### 阶段四：备案模块

- [x] 20. 创建 `src/views/SecurityOptions/FilingListView.vue`，提供备案列表视图（表头筛选 + 批量操作 + 单条取消）
- [x] 21. 文件详情后端筛选 + 批量取消备案（`file detail backend filters and batch cancel filing`）
- [x] 22. 统一 filter 图标与 batch filing items API（`unify filter icon and batch filing items API`）
- [x] 23. 修复 filing 详情弹层挂载点 + rawOptions 重命名（`mount file detail popovers into dialog and rename rawOptions`）
- [x] 24. 创建 `src/views/SecurityOptions/FilingBatchDialog.vue`，支持多选 + 备案原因（可选）+ 提交（`make filing reason optional in batch dialog`）
- [x] 25. 单条取消备案确认对话框（`add confirmation dialog to single cancel filing`）
- [x] 26. `CategorySearch` 支持 dateRange 类型筛选（`add dateRange filter support to CategorySearch`）

### 阶段五：路由拆分与产物包 / 备案记录独立页

- [x] 27. 修改 `src/router/index.ts`，新增子路由 `/securityOptions/filing-records`（hideInMenu / noKeepAlive）与 `/securityOptions/package-detail`（hideInMenu / noKeepAlive）
- [x] 28. 拆分产物包详情与备案记录为独立路由页面（`split package detail and filing records into standalone routes`）
- [x] 29. 创建 `src/views/SecurityOptions/FilingRecordsPage.vue`（壳）+ `FilingRecordsView.vue`（主体）
- [x] 30. 创建 `src/views/SecurityOptions/PackageDetailPage.vue`（壳）+ `PackageDetailView.vue`（主体）

### 阶段六：recordId 定位与同步刷新

- [x] 31. 通过 `recordId` 定位文件详情（`locate file detail by recordId`）
- [x] 32. 通过 `recordId` 定位 filing filer-list（`locate filing filer-list by recordId`）
- [x] 33. filing/save 请求携带 `recordId`（`add recordId to filing/save request`）
- [x] 34. filer-list 与备案列表数据变更后同步刷新（`sync filer-list with filing list on data change`）

### 阶段七：杂项

- [x] 35. 移除 filing records note，调整 date picker 位置（`drop filing records note and adjust date picker placement`）
- [x] 36. 添加 `AGENTS.md` 工作区指南（`add AGENTS.md workspace guide for AI agents`）

## 关联 commit（按时间倒序）

| commit    | 说明                                                                                      |
| --------- | ----------------------------------------------------------------------------------------- |
| `a92db31` | feat(security-options): sync filer-list with filing list on data change                   |
| `aebf75c` | feat(security-options): add recordId to filing/save request                               |
| `9b6fbdf` | refactor(security-options): locate filing filer-list by recordId                          |
| `ca8dfd7` | chore: add AGENTS.md workspace guide for AI agents                                        |
| `d94b027` | feat(security-options): split package detail and filing records into standalone routes    |
| `ba5d7d9` | refactor(security-options): locate file detail by recordId                                |
| `790ca0b` | feat(security-options): add dateRange filter support to CategorySearch                    |
| `8683635` | feat(security-options): add confirmation dialog to single cancel filing                   |
| `c3b2df9` | fix(security-options): rename filing column labels in package detail view                 |
| `f729276` | fix(security-options): mount file detail popovers into dialog and rename rawOptions       |
| `0d3f119` | refactor(security-options): unify filter icon and batch filing items API                  |
| `4d78aab` | feat(security-options): file detail backend filters and batch cancel filing               |
| `c402b98` | fix(security): 文件扫描结果总览按已扫描项过滤与产物包详情对齐                             |
| `b12795d` | refactor(security-options): drop filing records note and adjust date picker placement     |
| `ae11b97` | feat(security-options): add multi-select filters, time sort and filing permission control |
| `d577203` | feat(security-options): add repo and file path filters and drop sort on filing records    |
| `8abf05d` | feat(security-options): make filing reason optional in batch dialog                       |
| `33ffbe8` | feat(security-options): add CategorySearch toolbar and table header filters               |
| `992efe9` | refactor(security-options): refactor filing list with header filters and rename endpoint  |
| `8307abd` | feat(security-options): adjust overview table columns per demo                            |
