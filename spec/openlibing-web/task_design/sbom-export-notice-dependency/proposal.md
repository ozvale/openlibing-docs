# 【openlibing-web】SBOM 制品导出与声明文档依赖类型增强

> 流程模式：**Full**（涉及接口契约变化与跨仓协调，预计前端改动 300+ 行）
> 代码基线：`openlibing-web` 仓 `notice_sbom` 分支
> 文档版本：v1（2026-10-13）

## 需求背景

SBOM 管理模块（菜单：构建管理-SBOM，路由 `/apps/sbomManage`，页面 `CompositionAnalysis/index.vue`）当前存在两处能力缺口：

1. **制品数据导出缺少独立入口**。现有 SBOM 文档导出（全量导出）位于"软件成分数据"区块的导出下拉中，且强依赖先选中某个制品（`productName`），用户无法在制品维度按筛选条件批量导出制品 SBOM 文档，也无法选择"仅导出直接依赖"的数据范围。
2. **声明文档明细缺少依赖类型维度**。声明文档明细弹窗（NoticeExportDialog）的软件包明细表仅有"状态"筛选，无法区分直接/间接依赖；摘要区仅有整体"软件总数/成功/失败"统计，缺少按依赖类型的分类统计；失败数据的常见原因是下载地址错误，但弹窗内无引导提示，用户需自行摸索。

本次需求为上述两处提供增强能力，涉及前端（openlibing-web）与后端服务 openlibing-sca 的契约对接（后端已在 `dev_beta_20261019` 分支实现）。

## 需求决策记录（已确认）

| 决策点                 | 结论                                                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 制品导出弹窗的导出范围 | **按当前筛选结果导出全部**（弹窗继承主列表过滤项 + 弹窗内 NOTICE 状态筛选，不做勾选选择）                                                   |
| 导出内容与格式         | **导出各制品合并 NOTICE 声明文档（exportBatch）**，无规范/格式选择弹窗；**固定仅导出直接依赖**（exportScope=DIRECT，不提供全量导出选项）    |
| 后端契约               | **后端已在 openlibing-sca `dev_20261019` 落地**（exportBatch / scanStatusByMultiFilter / info / export / startBatch），前端按已实现契约对接 |
| 流程模式               | **Full**                                                                                                                                    |

## 功能描述

### A. 制品信息模块优化

- **A1 导出按钮**：制品信息区块筛选行内、刷新按钮旁新增"导出声明文档"按钮（`el-button` primary 蓝色背景 + Download 图标 + 文字），32px 与筛选框等高、宽度自适应（`margin-left: 0` 覆盖 Element Plus 相邻按钮默认 12px 左边距，与刷新按钮间距由容器 gap 8px 提供）；**主列表无数据时按钮禁用**。
- **A2 导出弹窗**：点击导出按钮弹出"导出制品数据"模态弹窗（`el-dialog` + `dialog-common`）：
  - 列表展示**制品名称、状态（NOTICE 扫描状态）、总数、失败数、操作**五列；状态取值：**待扫描、扫描中、成功、失败**（未发起过扫描的制品显示"未扫描"）；
  - **总数**与**失败数**列展示 NOTICE 扫描的直接依赖统计（后端 `directTotalCount`/`directFailCount` 原值；未扫描制品显示 `--`）；
  - **操作**列"详情"可点击，打开对应制品的声明文档明细弹窗；
  - 列表支持**筛选**：**继承主列表当前过滤项**（filters 透传后端，口径与主列表一致）+ 扫描状态集合多选（经 statuses 后端 SCA 本地过滤：非空时未扫描制品被排除）。**不提供排序与名称筛选**——后端排序参数被忽略、SBOM filters.NAME 仅精确匹配不支持模糊，后端不支持的功能前端不做；
  - 数据源为 `scanStatusByMultiFilter` 单接口（productType + filters + statuses + pageNum/pageSize，DPage 分页返回 `{ total, list }`），**后端分页**，翻页/改页大小触发请求。
- **A3 导出按钮**：弹窗列表上方工具栏右侧为"导出"按钮（primary，**固定仅导出直接依赖**，无下拉选项），**列表无数据时禁用**。
- **A6 生成版本级声明文档**：导出按钮左侧新增"生成版本级声明文档"按钮（default 样式），点击按当前筛选条件（入参与列表查询一致：productType + filters + 可选 statuses，pageNum/pageSize 随体透传但不参与后端语义）提交 `startBatch` 异步受理；**列表无数据或提交中禁用**；受理成功提示"已提交生成任务"并刷新列表（制品状态进入待扫描/扫描中，statuses 非空时仅对状态命中的制品发起扫描）；提交中禁止关闭弹窗。
- **A4 导出执行**：点击导出按钮**直接提交批量导出任务**（不弹格式选择弹窗）：按当前筛选（主列表 filters + 弹窗状态 statuses）循环拉取全量制品名后提交 `exportBatch`（productNames + **exportScope=DIRECT**，不传 userId），走平台统一导出中心（`useExportTaskSubmit`），由导出中心负责进度、提醒与下载。
- **A5 响应式**：导出按钮与弹窗在不同屏幕尺寸下不出现布局错乱或样式冲突（弹窗宽度自适应上限 960px、表格列 min-width 横向滚动、工具栏 flex 自适应）。

### B. 声明文档明细弹窗优化（软件成分数据 → 导出 → 声明文档）

- **B1 依赖类型字段**：软件包明细表新增"依赖类型"列（版本列之后，宽 130），取值：直接依赖(0)/间接依赖(1)/直接/间接依赖(2)/空值显示 `--`。**列头不提供筛选**（后端 /info 已支持 dependencyTypes 过滤，当前产品决策不启用）。
- **B2 数量统计**：摘要区保持整体统计"软件总数 X / 成功 Y / 失败 Z"（仅终态展示，随 5s 轮询更新；不展示直接/间接拆解括号）。
- **B5 明细后端分页与状态筛选**：/info 明细改为后端分页（pageNum/pageSize，缺省 1/10，表格下方 el-pagination，翻页/改页大小触发请求），状态筛选经 status 传后端过滤（变更回第 1 页）；进度与整体统计改用 scan 级计数（successCount+failCount / totalCount）。
- **B3 引导性提示语**：列表上方新增信息图标 + 文本的引导提示（warning 色系、醒目但不打扰）：

  > 软件包明细中状态为"失败"的数据可能是由于下载地址错误导致，请检查并编辑添加正确的下载地址

  展示时机：存在失败数据时展示（推荐方案，见 design.md 开放问题 Q3）。

- **B4 导出按钮**：弹窗工具栏"导出声明文档"按钮（primary，**无下拉**），点击**直接提交导出任务**（/export：productName + **exportScope=DIRECT**），不弹格式选择弹窗。

## 后端契约依赖（openlibing-sca，`dev_beta_20261019` 已实现）

| 接口                                                | 用途                                                                                                          | 状态   |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------ |
| `POST /project/notice/scan/exportBatch`             | 批量导出多制品合并 NOTICE（productNames + exportScope，query userId）                                         | 已实现 |
| `POST /project/notice/scan/scanStatusByMultiFilter` | 按筛选批量查询制品 NOTICE 扫描状态与全量/直接依赖统计                                                         | 已实现 |
| `POST /project/notice/scan/info`                    | 扫描信息 + 明细（含 dependencyType；明细分页 DPage + status/dependencyTypes 过滤 + 2×2 拆解统计）             | 已实现 |
| `POST /project/notice/scan/export`                  | 单制品声明文档导出（productName + exportScope，query userId）                                                 | 已实现 |
| `POST /project/notice/scan/startBatch`              | 按筛选批量发起制品 NOTICE 扫描/生成声明文档（异步受理；入参与 scanStatusByMultiFilter 一致，受理成功无 data） | 已实现 |

详细契约见 design.md「接口契约」章节。

## 不做什么

- 不修改软件成分数据区块现有"全量导出/声明文档"下拉入口行为，不修改 SbomExportDialog 既有单制品导出行为（保持基线零改动）
- 不在导出弹窗中提供制品勾选/多选能力（按筛选结果导出全部）
- 不为 NoticeDetailTable 增加排序能力（本次仅新增筛选列；排序为后续独立需求）
- 不改造制品主列表、成分主列表的现有列与筛选逻辑（仅提取共享常量）
- 不新增权限控制点（与现有导出入口保持一致，见 design.md 开放问题 Q4）

## 验收标准

### A. 制品信息模块

- [ ] 制品信息刷新按钮旁出现"导出声明文档"按钮（primary 蓝色背景、Download 图标 + 文字、32px 等高、间距 8px），窄屏下按钮行不换行错乱；**主列表无数据时按钮禁用**
- [ ] 点击导出弹出"导出制品数据"弹窗（960px 上限、dialog-common 规范），打开即加载第一页数据，加载态与空态正常
- [ ] 状态列展示 NOTICE 扫描状态：待扫描（灰）/扫描中（蓝）/成功（绿）/失败（红），未发起过扫描的制品显示"未扫描"（灰）
- [ ] 弹窗列表继承主列表当前过滤项（filters 透传，与主列表口径一致）；状态列支持多选筛选（待扫描/扫描中/成功/失败，非空时未扫描制品被排除）；制品名称列与状态列**无排序、无名称筛选**（后端不支持）
- [ ] "总数"与"失败数"列展示直接依赖统计原值（directTotalCount/directFailCount），未扫描制品显示 `--`
- [ ] "操作"列"详情"点击打开对应制品的声明文档明细弹窗（与导出弹窗**同宽同高** `min(960px, 94%)` × `min(640px, calc(100% - 30px))`，完全覆盖其上、底下弹窗不可见，关闭后回到导出弹窗且筛选分页状态保留），弹窗数据与主列表点选制品打开一致
- [ ] 筛选变更后自动回到第 1 页并重新请求；翻页/改每页条数触发请求、数据与 total 正确
- [ ] 工具栏右侧"导出"按钮（primary、无下拉）点击**直接提交**批量导出任务（exportScope=DIRECT，不弹格式弹窗），提示"已提交导出任务"并关闭弹窗，导出中心可见该任务
- [ ] 空列表（totalElements=0）时导出按钮置灰；导出提交中有 loading 防重复
- [ ] 导出按钮左侧"生成版本级声明文档"按钮（default 样式）：列表无数据或提交中禁用；点击按当前筛选提交 startBatch，受理成功提示"已提交生成任务"并刷新列表；提交中禁止关闭弹窗
- [ ] 1366/1920 宽度及 devtools 375/768 窄屏模拟下，弹窗与按钮区无布局错乱

### B. 声明文档明细弹窗

- [ ] 明细表"版本"列后出现"依赖类型"列，取值渲染正确（直接依赖/间接依赖/直接/间接依赖/--），列头**无筛选**；单行 `dependencyType` 为 null 时列显示 `--`
- [ ] 状态筛选（单选）经后端过滤生效，变更后回第 1 页重新请求
- [ ] 明细表下方出现分页条：翻页/改每页条数触发请求，数据与 total 正确；勾选跨页保留
- [ ] 筛选生效时空态文案为"当前筛选条件下暂无软件包"
- [ ] 摘要区统计为"软件总数 X / 成功 Y / 失败 Z"（成功绿/失败红，仅终态展示），数值随轮询更新
- [ ] 存在失败明细时展示引导提示语（InfoFilled 图标 + warning 色文本条），无失败数据时不展示
- [ ] "导出声明文档"按钮（primary、无下拉）点击直接提交导出任务（exportScope=DIRECT）、不弹格式弹窗

## 影响范围

### 前端（openlibing-web，本次实现范围）

| 文件                                                                                                            | 操作     | 说明                                                                                                                                                      |
| --------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`                                    | 修改     | 制品信息区新增"导出声明文档"按钮（primary、无数据禁用）；挂载 ProductExportDialog；show-notice 详情入口；解析状态常量改为从 common.ts 引用                |
| `apps/web-openlibing/src/views/SbomManagement/common.ts`                                                        | 修改     | 提取共享常量：scanStatusMap、SCAN_STATUS_OPTION_GROUPS、expandScanStatusFilterValues、依赖类型映射                                                        |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/ProductExportDialog.vue`            | **新增** | 制品导出弹窗（五列列表/状态筛选/后端分页/scanStatusByMultiFilter 单数据源/详情入口/导出按钮直连 exportBatch（DIRECT）/生成版本级声明文档按钮 startBatch） |
| `apps/web-openlibing/src/api/scaApi/softWareCompent.js`                                                         | 修改     | 新增 exportNoticeBatch、noticeScanStatusByMultiFilter、generateVersionNoticeBatch（startBatch）请求函数                                                   |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/noticeExport/useNoticeScan.ts`      | 修改     | /info 后端分页与 status 过滤、轮询条件改 scan 级计数、类型定义、降级逻辑                                                                                  |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/noticeExport/NoticeDetailTable.vue` | 修改     | 新增依赖类型列（无筛选）、分页条（后端分页）、表格 loading                                                                                                |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/noticeExport/NoticeScanSummary.vue` | 修改     | 整体统计（软件总数/成功/失败，无括号拆解）；进度改 scan 级计数                                                                                            |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/noticeExport/index.vue`             | 修改     | 失败引导提示语；导出声明文档按钮直连 /export（DIRECT）                                                                                                    |

### 后端（契约依赖，非本仓范围）

| 仓库           | 变更                                                                                                                               |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| openlibing-sca | `dev_beta_20261019` 已实现：notice/scan/exportBatch、scanStatusByMultiFilter、info（明细含 dependencyType）、export（exportScope） |

## 关联 Issue

待创建/关联（Phase 4 业务 PR 前确认）。
