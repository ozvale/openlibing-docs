# Proposal: 安全编译选项数据工程能力建设

## 需求背景

当前安全编译选项（BIND_NOW / NX / PIC / PIE / ASLR / RELRO / NO Rpath / SP / Strip / FS / Fvisibility / Ftrapv / Fstackcheck / Fstackclash 共 14 项）的检测数据缺乏前端展示页面，无法直观查看各代码仓的安全编译选项开启情况，也没有针对未达标产物包的备案与跟踪闭环能力。研发与安全团队需要：

1. 概览视图：以代码仓为单位查看 14 项安全编译选项的检测分布与开启率
2. 文件级下钻：查看单个产物包内每个文件的安全编译选项检测明细
3. 备案闭环：对未达标项进行批量备案、记录跟踪、取消与过滤
4. 多维筛选：代码仓 / 文件路径 / 检测完成时间 / 多选指标 / 排序的灵活组合

通过本次能力建设，让安全编译选项的检测 → 备案 → 跟踪形成完整闭环，提升研发团队对安全编译选项的可见性与可治理性。

## 需求描述

1. **主页面（构建产物 tab）**：`SecurityOptions/index.vue`，el-tabs + el-table 布局，展示各代码仓的 14 项安全编译选项检测概览
2. **多维度筛选**：通过自研 `CategorySearch` 组件支持代码仓 / 文件路径 / 检测完成时间范围 / 多选指标的组合筛选
3. **表格能力**：14 个安全指标列 + 概要列，支持自定义排序（`sortByField` / `sort`），代码仓 / 流水线 / 文件三列固定在左侧
4. **文件详情弹窗**：`FileDetailDialog.vue`，展示单个产物包内文件级安全编译选项明细，支持文件名模糊搜索
5. **产物包详情页**：`PackageDetailPage.vue` + `PackageDetailView.vue`，独立路由 `/securityOptions/package-detail`，展示产物包级别的明细与备案入口
6. **备案记录页**：`FilingRecordsPage.vue` + `FilingRecordsView.vue`，独立路由 `/securityOptions/filing-records`，展示历史备案记录
7. **备案列表视图**：`FilingListView.vue`，提供表头筛选、批量备案、单条取消、确认对话框等完整操作能力
8. **批量备案对话框**：`FilingBatchDialog.vue`，支持多选文件 + 备案原因（可选）+ 提交
9. **权限控制**：备案操作根据用户 filing 权限动态启用 / 禁用
10. **自研组件沉淀**：`CategorySearch` / `CategorySearchEditor` / `ColumnFilter` 抽取为可复用组件

## 验收标准

- [ ] 主页面 `/securityOptions` 正常渲染，14 项安全编译选项列展示正确
- [ ] `CategorySearch` 工具栏支持代码仓 / 文件路径 / 时间范围 / 多选指标的组合筛选
- [ ] 代码仓下拉数据来源于 dropdown 接口 `data.repoNames`
- [ ] 文件下拉与代码仓联动，数据来源于 dropdown 接口 `data.packageNames`
- [ ] 检测完成时间范围筛选传入 `startTime` / `endTime` 参数
- [ ] 表格排序参数为 `sortByField` / `sort` 格式
- [ ] 代码仓 / 流水线 / 文件三列固定在左侧
- [ ] 流水线列支持跳转链接（`pipelineLink`）
- [ ] 开启率列颜色分级：≥80% 绿 / ≥50% 橙 / <50% 红
- [ ] 点击文件名弹出详情弹窗，展示文件级安全编译选项明细
- [ ] 弹窗内文件名支持 `TableHeaderFilter` 模糊搜索
- [ ] 未扫描项以 `UNSCANNED` 占位值标识，不与 YES / NO / N/A 混淆
- [ ] 检测值映射：YES 绿 / NO 红 / N/A 灰
- [ ] 路由 `/securityOptions/package-detail` 正常打开产物包详情页
- [ ] 路由 `/securityOptions/filing-records` 正常打开备案记录页
- [ ] `FilingListView` 表头筛选与表格数据联动
- [ ] 批量备案对话框支持多选 + 备案原因（可选）+ 提交
- [ ] 单条取消备案弹出确认对话框，避免误操作
- [ ] 备案列表通过 `recordId` 定位 filer-list，确保数据变更后同步刷新
- [ ] 备案保存请求携带 `recordId`，保证幂等性
- [ ] 备案操作根据用户 filing 权限启用 / 禁用
- [ ] 文件扫描结果总览按已扫描项过滤，与产物包详情对齐

## 影响范围

### 新增文件

| 文件                                                     | 说明                                |
| -------------------------------------------------------- | ----------------------------------- |
| `src/api/SecurityOptions/api.ts`                         | 8 个安全编译选项相关 API 封装       |
| `src/api/SecurityOptions/url.ts`                         | API URL 常量定义                    |
| `src/components/CategorySearch/CategorySearch.vue`       | 自研分类筛选工具栏组件              |
| `src/components/CategorySearch/CategorySearchEditor.vue` | 筛选条件编辑器子组件                |
| `src/components/CategorySearch/types.ts`                 | CategorySearch 类型定义             |
| `src/components/CategorySearch/index.ts`                 | CategorySearch 导出入口             |
| `src/components/ColumnFilter.vue`                        | 表格列筛选器组件                    |
| `src/views/SecurityOptions/constants.ts`                 | 14 项安全编译选项枚举与颜色分级工具 |
| `src/views/SecurityOptions/FilingBatchDialog.vue`        | 批量备案对话框                      |
| `src/views/SecurityOptions/FilingListView.vue`           | 备案列表视图                        |
| `src/views/SecurityOptions/FilingRecordsPage.vue`        | 备案记录页面壳                      |
| `src/views/SecurityOptions/FilingRecordsView.vue`        | 备案记录视图主体                    |
| `src/views/SecurityOptions/PackageDetailPage.vue`        | 产物包详情页面壳                    |
| `src/views/SecurityOptions/PackageDetailView.vue`        | 产物包详情视图主体                  |

### 修改文件

| 文件                                             | 说明                                                                      |
| ------------------------------------------------ | ------------------------------------------------------------------------- |
| `src/views/SecurityOptions/index.vue`            | 主页面重构：接入 CategorySearch、新增多选筛选与时间排序、对齐 filing 权限 |
| `src/views/SecurityOptions/FileDetailDialog.vue` | 文件详情弹窗：popover 挂载到 dialog、rawOptions 重命名、列标签调整        |
| `src/components/TableHeaderFilter.vue`           | 新增 `placement` / `popperClass` props                                    |
| `src/components/BatchOperation.vue`              | 适配批量备案操作                                                          |
| `src/router/index.ts`                            | 新增 `filing-records` 与 `package-detail` 子路由                          |
| `src/App.vue`                                    | 应用层布局适配                                                            |
| `src/api/ApiClient.ts`                           | 客户端扩展                                                                |

## 关联 Issue

openlibing/openlibing-cicd-web#25
