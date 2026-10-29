# sbom-export-notice-dependency — 实现任务清单

> 设计依据：[design.md](./design.md)（实现前必读，尤其 §5 接口契约与 §8 开放问题）
> 开发分支：`openlibing-web` 仓 `notice_sbom`（延续当前开发分支，开工前与用户确认）
> 约束：本轮交付在业务仓提交 commit；业务 PR 需关联 Issue 并打 `ai-assisted` 标签；不携带 spec 文件入业务 PR

## Phase 0 — 前置确认

- [x] 0.1 与用户确认：继续在 `notice_sbom` 分支开发
- [x] 0.2 后端契约已在 openlibing-sca `dev_beta_20261019` 落地（exportBatch / scanStatusByMultiFilter / info / export），前端按已实现契约对接
- [ ] 0.3 创建/关联业务 Issue（Phase 4 前）
- [x] 0.4 检查导出按钮视觉基准：与 `filter-refresh-btn`（index.vue L37-43、样式 L2373-2377）逐项对齐（尺寸/颜色/图标规格/文字样式/间距 8px）

## Phase 1 — 基础层（常量提取 + API 定义）

- [x] 1.1 `common.ts`：提取 `scanStatusMap`、`SCAN_STATUS_OPTION_GROUPS`、`expandScanStatusFilterValues`（自 index.vue L1071/L1178/L1187，机械搬移不改行为）
- [x] 1.2 `index.vue`：删除本地定义改为 import（回归制品列表筛选/排序无变化）
- [x] 1.3 `common.ts`：新增 `DEPENDENCY_TYPE` / `DEPENDENCY_TYPE_TEXT`（0/1/2 映射，design §4.1）
- [x] 1.4 `softWareCompent.js`：新增 `exportNoticeBatch`（POST /project/notice/scan/exportBatch）与 `noticeScanStatusByMultiFilter`（POST /project/notice/scan/scanStatusByMultiFilter）
- [x] 1.5 验证：ESLint 通过，制品主列表回归通过（查询/筛选/排序/分页/收起展开）

## Phase 2 — Feature A：制品导出（design §3）

- [x] 2.1 `index.vue`：制品信息 `filter-summary` 刷新按钮旁新增"导出声明文档"按钮（primary 蓝色背景、Download 图标、复用 `filter-refresh-btn` + `filter-export-btn`（margin-left 0 覆盖 Element Plus 默认 12px 左边距、宽度自适应，间距由容器 gap 8px 提供）、`white-space: nowrap`）；**主列表无数据时禁用**
- [x] 2.2 新建 `component/ProductExportDialog.vue`：
  - [x] 2.2.1 el-dialog 骨架（title"导出制品数据"、`width="min(960px, 94%)"` + `stacked-overlay-dialog` 固定高度 `min(640px, calc(100% - 30px))`、dialog-common、close-on-click-modal=false）
  - [x] 2.2.2 制品列表：制品名称列（min-width 220、show-overflow-tooltip；**无排序无筛选**——后端排序被忽略、filters.NAME 仅精确匹配不支持模糊）+ **状态列（NOTICE 扫描状态，width 140、无排序、el-tag：待扫描 info/扫描中 primary/成功 success/失败 danger/未扫描 info、列头 filterDropdown checkbox 多选——选项 待扫描/扫描中/成功/失败，选中值经 statuses 传后端 SCA 本地过滤）** + **总数列**（width 170、直接依赖统计 directTotalCount 原值、未扫描显示 '--'）+ **失败数列**（width 180、直接依赖统计 directFailCount 原值、未扫描显示 '--'）+ **操作列**（width 80、"详情"打开对应制品声明文档弹窗）
  - [x] 2.2.3 查询逻辑：数据源唯一 `noticeScanStatusByMultiFilter`（productType + **filters 透传主列表过滤项**（父组件 productListFilters computed，与 buildProductListParam 同口径）+ statuses + pageNum/pageSize），返回 DPage `{ pageNum/pageSize/total/pages/list }`；状态筛选变更回第 1 页重查
  - [x] 2.2.4 分页：`layout="sizes, total, prev, pager, next"`、page-sizes [10,20,30]（**后端分页**：翻页/改页大小触发请求，pageNum 1-based；页码越界自动回第 1 页重查）
  - [x] 2.2.5 watch(visible)：打开 resetState + 首查；关闭重置；Empty 空态 + v-loading
  - [x] 2.2.6 工具栏：`制品列表` 标题 + spacer + **"生成版本级声明文档"按钮（default 样式，total=0 或提交中禁用）** + 导出按钮（primary、无下拉、**固定 exportScope=DIRECT**、total=0 时禁用）
  - [x] 2.2.7 查询参数组装抽取 `buildQueryParam()`（productType + filters + pageNum/pageSize + 可选 statuses），列表查询与生成版本级声明文档共用，保证生成入参与列表查询口径一致
- [x] 2.3 `ProductExportDialog` 导出链路（按钮直连，无格式弹窗）：点击导出 → **按当前筛选循环拉取全量制品名**（fetchAllFilteredProductNames，页大小 1000/上限 100 页防御）→ `exportNoticeBatch`（productNames + **exportScope=DIRECT**，**不传 userId**）→ `useExportTaskSubmit` 注册导出中心 → 成功关闭弹窗
- [x] 2.3a `ProductExportDialog` 生成版本级声明文档链路（A6，design §3.4）：点击 → `generateVersionNoticeBatch`（startBatch，入参 buildQueryParam 共用，25060aef2 契约：statuses 非空仅命中状态制品、pageNum/pageSize 不参与语义、受理成功无 data）→ 成功 toast"已提交生成任务"并 fetchList 刷新；提交中按钮 loading + 弹窗不可关闭
- [x] 2.4 `index.vue` 挂载 `<ProductExportDialog>`（productType 与主列表同源；`:filters="productListFilters"` 透传主列表当前过滤项；`@show-notice` 打开对应制品声明文档明细弹窗）
- [ ] 2.5 响应式自查：1366/1920 + devtools 375/768（弹窗收缩、表格横向滚动、按钮行不错乱）
- [ ] 2.6 联调验证（契约已上线）：真实提交批量导出（exportScope=DIRECT），导出中心进度与文件内容抽检（仅含直接依赖数据）；生成版本级声明文档（startBatch）受理成功、列表状态流转为扫描中→终态

## Phase 3 — Feature B：声明文档明细增强（design §4）

- [x] 3.1 `useNoticeScan.ts` 扩展（**后端分页 + 后端状态过滤**，对齐 /info 新契约）：
  - [x] 3.1.1 类型：`NoticeScanDetail.dependencyType`、`NoticeScanDetailPage`（DPage 分页结构）
  - [x] 3.1.2 `queryState`（pageNum/pageSize）随 /info 传后端（SCA 侧内存分页，1-based 缺省 1/10）；`detailRows`/`detailTotal` 取 `details.list`/`details.total`
  - [x] 3.1.3 `filterStatus` 经 /info `status` 传后端过滤，变更回第 1 页重新请求（refreshDetails 带 loading）；依赖类型筛选不启用（后端 dependencyTypes 已支持，产品决策不开启）
  - [x] 3.1.4 `shouldKeepPolling` 改 scan 级计数（totalCount > successCount + failCount 即存在待处理明细，分页后不能遍历明细判断）
  - [x] 3.1.5 `resetScanState` 复位 filterStatus 与 queryState
- [x] 3.2 `NoticeDetailTable.vue`：版本列后新增"依赖类型"列（width 130、"直接/间接依赖"不换行、`dependencyTypeText` 渲染、空值 '--'、**无筛选**）；表格下方新增 el-pagination（后端分页，翻页/改页大小触发请求，[10,20,30]）
- [x] 3.3 `noticeExport/index.vue`：NoticeDetailTable 传分页 props 并接分页/筛选事件（filter-change → handleStatusFilterChange；size-change/page-change 触发请求）
- [x] 3.4 `NoticeScanSummary.vue`：整体统计"软件总数 X / 成功 Y / 失败 Z"（无直接/间接拆解括号；成功 #67c23a / 失败 #f56c6c）；进度改 scan 级计数（successCount+failCount / totalCount）
- [x] 3.5 `noticeExport/index.vue`：工具栏与表格之间新增失败引导提示条（`showFailureGuideTip = failCount > 0`；InfoFilled + warning 色系样式 design §4.4；文案逐字对齐需求）
- [x] 3.6 `noticeExport/index.vue`："导出声明文档"按钮（primary、无下拉），点击直接调 `/export`（productName + **exportScope=DIRECT**，**不传 userId**），不弹格式弹窗
- [ ] 3.7 联调验证：依赖类型列渲染、状态筛选（后端过滤）与分页（翻页/改页大小/回第 1 页）、整体统计终态随轮询收敛、提示语显隐与失败行编辑闭环、跨页勾选保留

## Phase 4 — 测试与质量（Full 模式）

- [ ] 4.1 组件/逻辑测试（如项目单测框架可用）：useNoticeScan 筛选组合与降级、ProductExportDialog 请求组装（design §10.1）
- [ ] 4.2 Playwright e2e 用例：A 导出链路 + B 声明文档链路（design §10.2；注意 e2e 目录当前未入库的本地工程状态）
- [ ] 4.3 手工验证清单执行（design §10.3：真实导出（DIRECT）、轮询统计、补充信息闭环、响应式、样式自查）
- [ ] 4.4 回归：制品主列表（常量提取影响）、现有全量导出、声明文档既有全链路（生成/轮询/补充/状态筛选/导出）
- [ ] 4.5 生成前约束自检：仅改 spec 范围内文件；无硬编码凭证；遵循目标仓组件/命名/错误处理风格；无无关重构

## Phase 5 — 交付与归档

- [ ] 5.1 业务仓 commit（单 commit 对应本轮交付，规范见 AGENTS.md）
- [ ] 5.2 用户自测与反馈循环（每轮修改新 commit，不 amend）
- [ ] 5.3 业务 PR：确认源分支（fork 仓）→ 创建跨仓 PR（`--head fork-owner:branch`）→ 补 `ai-assisted` 标签 → 关联业务 Issue
- [ ] 5.4 业务 PR 合入后，用户触发归档：docs 仓 PR 提交本 spec 目录（含 archive.md），分支 `spec-openlibing-web-sbom-export-notice-dependency`

## 验收对照

交付时逐项勾选 proposal.md「验收标准」A/B 全部条目，并在 PR 描述中附对照结果。
