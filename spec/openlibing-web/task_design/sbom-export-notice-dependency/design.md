# sbom-export-notice-dependency — 技术设计

> 前置阅读：[proposal.md](./proposal.md)
> 代码基线：`openlibing-web` 仓 `notice_sbom` 分支
> UI 组件库：Element Plus 2.13.0 + @element-plus/icons-vue 2.3.1（新代码禁用 element-ui）

## 1. 现状与代码基线

### 1.1 页面结构（CompositionAnalysis/index.vue，约 2800 行）

```text
index.vue（SBOM 组成分析主页）
├─ 制品信息区块（L3-255）
│  ├─ subTitle：制品信息标题 + 收起/展开
│  ├─ filter-summary：CategorySearch 条件筛选 + 刷新按钮（L37-43）★A1 落点
│  ├─ 制品表格 el-table（L50-242）
│  └─ el-pagination（L243-253）
├─ 软件成分数据区块（L256-929）
│  ├─ filter-row：CategorySearch + 漏洞刷新 + 导出下拉（L362-394）
│  ├─ 成分表格 el-table（树形，L404-917）
│  └─ el-pagination（L918-927）
├─ el-dialog 漏洞详情列表（L930-944）
├─ SbomExportDialog 全量导出弹窗（L945-949，480px）
└─ NoticeExportDialog 声明文档明细弹窗（L950-953，960px）
```

两区块互斥展开（`productExpanded`/`compositionExpanded`）：点击制品行"详情"后制品表收起为单行预览、成分区展开。

### 1.2 与本次需求相关的既有实现

| 能力                   | 位置                                                                          | 要点                                                                                                                                                                                                                   |
| ---------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 制品刷新按钮           | index.vue L37-43                                                              | el-button + Refresh 图标 + 文字，`.filter-refresh-btn` 强制 32px 高、与筛选框等高                                                                                                                                      |
| 制品列表查询           | `queryProductListMultiFilter`（POST `/sbom-api/queryProductListMultiFilter`） | 入参含 productType、pageNum(0 起)、pageSize、filters(NAME/SCAN_STATUS/动态字段)、sortField/sortDir；响应取 content/totalElements                                                                                       |
| 制品排序映射           | productSortPropMap L1148-1153                                                 | name→NAME、scanStatus→SCAN_STATUS；默认创建时间倒序                                                                                                                                                                    |
| 解析状态枚举           | scanStatusMap L1071-1079                                                      | FINISH→success、FAILED/FAILED_FINISH→danger、RUNNING→warning、VUL_REFRESHING→warning                                                                                                                                   |
| 解析状态筛选分组       | SCAN_STATUS_OPTION_GROUPS L1178-1184                                          | 5 组（解析完成/解析失败/解析中/等待解析/漏洞信息刷新中）；组内值逗号拼接为选项 key，查询前展开为后端原始状态值数组                                                                                                     |
| 依赖类型映射（成分表） | index.vue L530-538、L1308-1311                                                | 0=直接依赖、1=间接依赖、2=直接/间接依赖，其余显示 --                                                                                                                                                                   |
| 导出下拉交互范式       | index.vue L362-394                                                            | el-dropdown(click) + primary 按钮"导出"+ArrowDown；菜单项内 QuestionFilled + tooltip（click.stop）实现悬停提示                                                                                                         |
| SbomExportDialog       | sbomExportDialog.vue（480px）                                                 | 规范→版本→格式三级联动（级联清空+自动选中首个可用组合）；选项来自 exportSbomOptions（依赖 productName）；确认调 exportSbom（GET blob）解析 content-disposition 后触发下载                                              |
| 声明文档明细弹窗       | noticeExport/index.vue（min(960px, 94%)，dialog-common）                      | 摘要（NoticeScanSummary）→ 工具栏（生成/批量补充/导出）→ 明细表（NoticeDetailTable）→ 批量补充弹窗（BatchSupplementDialog，640px append-to-body）                                                                      |
| 明细表结构             | NoticeDetailTable.vue L15-116                                                 | 列：勾选(仅失败行可选，跨页保留)/软件包名称/版本/依赖类型/状态(可筛选，status 传后端)/下载地址/操作(编辑)；无排序；表格下方 el-pagination（后端分页，翻页触发请求）                                                    |
| 声明文档状态层         | useNoticeScan.ts                                                              | 明细行含 softwareName/version/status/errorMsg/downloadUrl/dependencyType；整体含 status/totalCount/successCount/failCount/details（DPage 分页）；5s 轮询（usePollingTask）；状态筛选经 status 传后端、明细分页后端分页 |
| 摘要统计               | NoticeScanSummary.vue                                                         | 终态展示"软件总数/成功/失败"；成功绿色(#67c23a)、失败红色(#f56c6c)                                                                                                                                                     |
| 图标+文本提示范式      | BatchSupplementDialog.vue L10-13                                              | InfoFilled + 文本 + 浅色背景条（8px 12px 内边距、4px 圆角、12px 字号）                                                                                                                                                 |
| 统一导出任务提交       | useExportTaskSubmit.ts                                                        | 调导出接口 → 提取任务 id → 注册 exportTask store → toast；此后进度/浮窗/下载由导出中心接管                                                                                                                             |
| 声明文档 API           | @/api/scaApi/softWareCompent                                                  | noticeScanStart/Info/Supplement/exportNoticeScan → POST `/gateway/openlibing-sca/project/notice/scan/*`                                                                                                                |
| 弹窗通用规范           | normal.less `.el-dialog.dialog-common`                                        | 绝对定位垂直居中、max-height 限制、body 滚动、footer 按钮宽 88px（取消在左/主按钮在右）                                                                                                                                |

## 2. 总体设计与交互流程

### 2.1 Feature A：制品导出

```text
制品信息区块
  └─ [导出声明文档] 按钮（primary，刷新按钮旁）
       └─ ProductExportDialog「导出制品数据」
            ├─ 制品列表（制品名称/状态/总数/失败数/操作五列；服务端筛选/分页）
            └─ 工具栏右侧 [生成版本级声明文档] + [导出] 按钮
                 └─ 点击导出 → 按弹窗当前筛选逐页拉取全量制品名
                      → 提交 exportBatch（exportScope=DIRECT）
                           └─ 统一导出中心接管进度/提醒/下载 → 关闭弹窗
```

### 2.2 Feature B：声明文档明细增强

```text
NoticeExportDialog
  ├─ NoticeScanSummary：现有状态胶囊/进度/整体统计（软件总数/成功/失败，无拆解括号）
  ├─ 工具栏（生成/批量补充/导出，导出按钮直连 DIRECT，无下拉）
  ├─ 新增：失败引导提示条（存在失败数据时展示）
  └─ NoticeDetailTable
       └─ 新增：依赖类型列（版本列后，纯文本展示，无筛选）
```

## 3. 方案设计 — Feature A

### 3.1 A1：制品信息区导出按钮

- **落点**：制品信息区块筛选行内、刷新按钮之后。
- **形态**：el-button **primary（蓝色背景）** + Download 图标 + "导出声明文档"文字，复用现有 `filter-refresh-btn` 样式类（`filter-export-btn` 附加类覆盖 Element Plus 相邻按钮默认 `margin-left:12px`）——32px 高、与筛选框等高、宽度自适应。
- **间距**：`margin-left: 0`，与刷新按钮 8px 间距由容器 gap 提供；按钮文字不换行。
- **状态**：主列表无数据时按钮禁用；不做权限控制（与成分区导出入口权限策略一致）。

### 3.2 A2：ProductExportDialog（新增组件）

新增组件 `CompositionAnalysis/component/ProductExportDialog.vue`，与主列表解耦、内聚全部弹窗逻辑。

**组件契约**：

| 项                | 值             | 说明                                          |
| ----------------- | -------------- | --------------------------------------------- |
| props.visible     | boolean        | v-model:visible 控制开关                      |
| props.productType | string         | 与主列表查询的 productType 同源（项目上下文） |
| emits             | update:visible | 关闭回传                                      |

**弹窗骨架**：el-dialog，标题"导出制品数据"，`dialog-common` 规范，禁止点击遮罩关闭；body 含工具栏（左：制品列表标题；右：生成版本级声明文档按钮 + 导出按钮）、制品表格、分页。

**制品列表设计**：

| 列       | 宽度                        | 排序                               | 筛选                                                                                                            |
| -------- | --------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 制品名称 | min-width 220，超长 tooltip | 无（服务端忽略排序，不加排序功能） | 无（SBOM filters.NAME 仅精确多值匹配、不支持模糊，后端不支持故不加筛选）                                        |
| 状态     | 140                         | 无（同上）                         | 列头 filterDropdown 多选（**NOTICE 扫描状态**：待扫描/扫描中/成功/失败，选中值经 statuses 传后端 SCA 本地过滤） |

- 状态为 **NOTICE 扫描状态**（后端 ProjectNoticeScanStatus：0-待处理/1-处理中/2-成功/3-失败），弹窗文案映射为 待扫描/扫描中/成功/失败；未发起过扫描（status=null）展示"未扫描"灰 tag。el-tag 配色：待扫描 info/扫描中 primary/成功 success/失败 danger。
- 附加三列：**总数**（170，直接依赖统计 `directTotalCount` 原值）、**失败数**（180，直接依赖统计 `directFailCount` 原值；未扫描制品两列均显示 `--`）、**操作**（80，"详情"打开对应制品声明文档明细弹窗）。
- **详情弹窗覆盖效果**：声明文档明细弹窗与导出弹窗**同宽同高**（均 `width="min(960px, 94%)"` + `stacked-overlay-dialog` 固定高度 `min(640px, calc(100% - 30px))`）、同视口居中定位（dialog-common absolute 居中），导出弹窗保持打开，明细弹窗后开**完全覆盖**其上（z-index 自动更高，底下弹窗不可见）；明细内容超出固定高度时 body 内部滚动；关闭明细弹窗即回到导出弹窗（筛选与分页状态保留）。

**查询与状态逻辑**（单接口 + 后端分页）：

- **数据源唯一**：`scanStatusByMultiFilter`（productType + **filters 透传主列表当前过滤项** + 可选 statuses + pageNum/pageSize），返回 DPage `{ pageNum/pageSize/total/pages/list }`，total 为 statuses 过滤后总记录数；制品分页列表接口不再使用。filters 由父组件经 `productListFilters` computed（与 `buildProductListParam` 同一组装口径：NAME/INCLUDE_VUL_SEVERITIES/EXCLUDE_VUL_SEVERITIES/SCAN_STATUS/动态属性键，逗号分隔多值）传入，保证弹窗与主列表口径一致。
- **后端分页**（SCA 侧内存分页，pageNum 1-based 缺省 1、pageSize 缺省 10）：翻页/改页大小触发请求；状态筛选变更回第 1 页再请求；页码越界（total 实时缩小致当前页取空）自动回第 1 页重查；直接依赖统计聚合仅覆盖当前页（后端降低聚合规模的设计）。
- 状态筛选语义（后端契约）：statuses 空=全部（含未扫描制品）；非空=仅命中集合制品，**未扫描制品被排除**。NOTICE 扫描状态筛选独立于主列表过滤项，两者叠加生效。
- watch(visible)：打开时重置状态 + 首次查询；关闭时重置。加载态 v-loading、空态用 Empty 组件。
- **导出取数适配**：后端分页后列表仅持有当前页数据，导出前按当前筛选（filters + statuses）循环拉取全量制品名（页大小 1000、上限 100 页防御），再提交 exportBatch，保证导出范围与"所见"（当前筛选）一致。

**导出禁用态**：列表 total 为 0 时导出按钮置灰（附 tooltip 说明当前无制品可导出）。

### 3.3 A3：导出按钮

- **形态**：primary 按钮"导出"（**无下拉**），列表 total 为 0 或提交中时禁用。
- **行为**：点击**直接提交批量导出任务**（exportBatch，**exportScope 固定 DIRECT**——仅直接依赖，不提供全量导出选项），不弹格式选择弹窗——后端仅产出合并 NOTICE 文件，无规范/格式概念。

### 3.4 A6：生成版本级声明文档（startBatch 直连）

- **落点**：弹窗工具栏导出按钮左侧，"生成版本级声明文档"按钮（default 样式）。
- **交互**：列表 total=0 或提交中禁用；点击按当前筛选直接提交（不弹确认框）。
- **契约**（`POST /project/notice/scan/startBatch`，25060aef2）：**入参与 scanStatusByMultiFilter 请求体一致**（productType + filters + 可选 statuses + pageNum/pageSize，后两者随体透传但不参与本接口语义）；受理时后端按 productType 查 SBOM 取制品名（空则拒绝），statuses 非空时仅对最新扫描状态命中的制品发起扫描（未扫描制品不参与命中）；后台单线程池逐制品调用 /start 生成声明文档，单个失败跳过不中断；受理成功返回无 data（无 taskId，无导出中心注册）。
- **参数组装**：`buildQueryParam()` 与列表查询 fetchList 共用同一组装函数，保证生成范围与"所见"（当前筛选）一致。
- **反馈**：受理成功（code=200）toast"已提交生成任务"并刷新列表（制品状态将进入待扫描/扫描中，实际结果以列表刷新/轮询为准）；提交中按钮 loading 防重复、弹窗不可关闭；失败不关闭弹窗（ApiClient 拦截器统一提示）。

### 3.5 A4：批量导出提交链路（exportBatch 直连）

导出单步提交，全部经 `useExportTaskSubmit`（loading、错误提示、导出中心注册复用统一范式）：

- **导出取数适配**：后端分页后列表仅持有当前页数据，导出前按当前筛选（主列表 filters + 状态 statuses）经 `fetchAllFilteredProductNames` 循环拉取全量制品名（页大小 1000、上限 100 页防御）后提交 `exportBatch`（body：productNames + **exportScope=DIRECT**），保证导出范围与"所见"（当前筛选）一致；未生成 NOTICE 的制品由后端跳过，前端无需预过滤。**不传 userId**（后端已移除该参数）。
- 提交成功后 toast 提示并关闭弹窗；此后进度、浮窗提醒、自动下载全部由平台导出中心接管。
- 提交期间按钮 loading 防重复、弹窗不可关闭；失败（含接口未上线）不关闭弹窗、不报 JS 错误。
- **明确不做**前端逐制品循环下载——统一走后端任务式批量导出（跨制品去重合并为单个 NOTICE 文件，与声明文档单制品导出范式一致）。
- **废弃说明**：原"格式选择弹窗（sbomExportDialog mode='select'）+ exportSbomByFilter"方案已随契约落地下线，sbomExportDialog 保持基线零改动。

### 3.6 A5：响应式设计

| 场景             | 方案                                                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| 弹窗宽度         | 上限 960px（明细表弹窗规范宽度），窄屏自动收缩至视口 94%；高度自适应由 dialog-common 全局样式保证            |
| 制品列表         | 制品名称 min-width 220 + 超长 tooltip；窄屏表格内横向滚动，不挤压状态列                                      |
| 工具栏           | flex 布局 + 弹性占位（对齐 noticeExport 工具栏），按钮不换行                                                 |
| 制品信息区按钮行 | 导出声明文档按钮与刷新按钮同规格（32px、primary、margin-left 0、宽度自适应），filter-summary flex 布局自适应 |

## 4. 方案设计 — Feature B

### 4.1 B1：依赖类型列

- **位置**：明细表"版本"列之后、"状态"列之前，列宽 130（"直接/间接依赖"单行不换行）。
- **渲染**：0=直接依赖、1=间接依赖、2=直接/间接依赖，空值/未知显示 `--`；纯文本（与成分表依赖类型列一致，不用 tag）。
- **筛选**：**列头不提供筛选**（后端 /info 已支持 dependencyTypes 多选过滤——严格等值匹配、NULL 未补充明细不命中；当前产品决策不启用，如后续需要可低成本开启）。
- **样式统一**：列宽、字号与状态列一致（table-common 全局样式）。

### 4.2 B1 支撑：useNoticeScan 状态层扩展

**类型扩展**（契约已落地，字段见 §5.2）：

| 结构                          | 新增字段                              | 说明                                              |
| ----------------------------- | ------------------------------------- | ------------------------------------------------- |
| 明细行 NoticeScanDetail       | dependencyType?: number               | 0/1/2，可空（空=未补充，渲染 --）                 |
| 明细分页 NoticeScanDetailPage | { pageNum/pageSize/total/pages/list } | /info 的 details 为 DPage 分页返回，list 为当前页 |

**筛选/分页与状态逻辑**（后端分页 + 后端状态过滤）：

| 项                             | 设计                                                                                                              |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| filterStatus                   | 单值状态筛选（null=全部）：作为 /info 的 status 入参传后端过滤                                                    |
| queryState（pageNum/pageSize） | 明细分页：随 /info 请求传后端（SCA 侧内存分页，1-based，缺省 1/10）                                               |
| detailRows / detailTotal       | 直接取 `data.details.list` / `data.details.total`（DPage 分页结构；total 为 status 过滤后明细总数）               |
| 筛选变更处理                   | 状态筛选变更回第 1 页重新请求；翻页/改页大小触发请求（refreshDetails，带表格 loading）                            |
| isDetailFiltered               | 状态筛选生效即 true：空态文案切换"当前筛选条件下暂无软件包"；进度/统计用 scan 级计数，不受筛选与分页影响          |
| 轮询条件 shouldKeepPolling     | 整体非终态，或 totalCount > successCount + failCount（存在待处理明细；分页后 details 仅当前页，不能遍历明细判断） |
| 状态重置                       | resetScanState 复位 filterStatus 与 queryState（回第 1 页/页大小 10）                                             |
| 明细 row-key                   | 不变（softwareName+version）+ reserve-selection，翻页/轮询刷新保留跨页勾选                                        |

### 4.3 B2：数量统计

- **内容与格式**：摘要区保持整体统计"软件总数 X / 成功 Y / 失败 Z"（成功绿 #67c23a、失败红 #f56c6c，数值加粗），**不展示直接/间接拆解括号**（后端 2×2 拆解聚合字段——successDirectCount/successIndirectCount/failDirectCount/failIndirectCount——前端当前不消费）。
- **展示时机**：仅终态展示（处理中只展示状态与进度）；数值为终态值，随 5s 轮询收敛更新。
- **口径**：scan 级计数（totalCount/successCount/failCount），不随明细筛选/分页变化；分页后明细仅当前页，进度/统计不遍历明细。

### 4.4 B3：失败引导提示语

- **位置**：工具栏与明细表之间。
- **展示条件**：存在失败数据（failCount > 0，处理中实时判定）时常驻展示，无失败数据时隐藏（开放问题 Q3 已标注可改常驻）。
- **形式**：信息图标 + 文本的提示条（对齐系统"图标+文本+浅色背景条"提示范式），换用 **warning 色系**——浅黄底（#fdf6ec）、警示黄图标与正文同色（#e6a23c，对齐 el-alert warning：标题文字与图标同色系，保持提示语义统一）、14px 字号；不做悬停（提示需醒目直达）。
- **文案**：严格使用需求原文：软件包明细中状态为"失败"的数据可能是由于下载地址错误导致，请检查并编辑添加正确的下载地址。
- **引导闭环**：与既有"操作列编辑下载地址 / 批量补充信息"能力天然衔接，不新增编辑入口。

## 5. 接口契约（后端 dev_beta_20261019 已实现，ProjectNoticeScanController）

> 契约来源：openlibing-sca `dev_20261019` 分支（与 `dev_beta_20261019` 同源提交）`ProjectNoticeScanController` 及配套 PO/VO 源码。前端改动收敛在 useNoticeScan.ts 类型与 ProductExportDialog 的请求组装两处，影响面可控。

### 5.1 批量导出制品合并 NOTICE 文件（openlibing-sca）

`POST /gateway/openlibing-sca/project/notice/scan/exportBatch`

**请求字段**（ProjectNoticeBatchExportPo）：

| 字段         | 类型     | 必填 | 说明                                                                                                                                                 |
| ------------ | -------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| productNames | string[] | 是   | 制品名称集合（服务端去空白去重）；按弹窗当前筛选逐页拉取全量制品名（fetchAllFilteredProductNames），未生成 NOTICE 的制品由服务端跳过，全部缺失时拒绝 |
| exportScope  | string   | 否   | FULL=全量（缺省，下载各制品已生成的合并文档）/ DIRECT=仅直接依赖（按直接依赖明细实时重建）；**前端固定传 DIRECT**                                    |

**响应**：导出任务受理模式（useExportTaskSubmit 兼容结构）——code 200 + data 含 taskId（及 fileName）。后台逐制品产出 NOTICE 内容，跨制品去重合并（同软件同版本仅保留一份、License 全文去重）为单个文件转存导出桶，由平台导出中心接管进度与下载。

**配套**：`POST /project/notice/scan/scanStatusByMultiFilter`（ProjectNoticeScanMultiFilterQueryPo：productType 必填 + **filters 主列表过滤项透传 SBOM**（NAME/INCLUDE_VUL_SEVERITIES/EXCLUDE_VUL_SEVERITIES/SCAN_STATUS/动态属性键，逗号分隔多值精确匹配）+ 可选 statuses 扫描状态集合；排序分页参数被服务端忽略、返回全量）——**弹窗列表唯一数据源**，返回每制品 productName/status/statusName/totalCount/failCount/directTotalCount/directFailCount。statuses 取值 0-待处理/1-处理中/2-成功/3-失败（ProjectNoticeScanStatus），SCA 侧本地过滤：传空返回全量（含未扫描制品）；非空仅返回最新扫描状态命中集合的制品，未扫描制品（status=null）被排除。

### 5.2 声明文档扫描信息（openlibing-sca）

`POST /gateway/openlibing-sca/project/notice/scan/info`

**请求参数**（ProjectNoticeScanInfoQueryPo）：productName 必填 + status 可选（明细状态过滤，0-待处理/1-成功/2-失败，null=全部）+ dependencyTypes 可选（明细依赖类型多选过滤，List&lt;Integer&gt;：0-直接/1-间接/2-直接&间接；严格等值匹配、NULL 未补充明细不参与命中；**前端当前不传**——产品决策不启用依赖类型筛选）+ pageNum/pageSize（明细分页，SCA 侧内存分页，1-based，缺省 1/10）。

**响应 data 字段**（ProjectNoticeScanInfoVO + ProjectNoticeScanDetailInfoVO）：

| 字段                                                                            | 位置              | 结构                                          | 说明                                                                             |
| ------------------------------------------------------------------------------- | ----------------- | --------------------------------------------- | -------------------------------------------------------------------------------- |
| totalCount / successCount / failCount                                           | data 顶层         | number                                        | 整体统计（进度/统计展示与轮询判断使用）                                          |
| successDirectCount / successIndirectCount / failDirectCount / failIndirectCount | data 顶层         | number（可 null）                             | 依赖类型 2×2 拆解统计（后端单扫描聚合；直接&间接仅计入直接；**前端当前不消费**） |
| dependencyType                                                                  | details.list[] 内 | number（可空）                                | 0=直接依赖 1=间接依赖 2=直接/间接依赖；null=未补充（渲染 --）                    |
| details                                                                         | data 顶层         | DPage `{ pageNum/pageSize/total/pages/list }` | 明细分页返回，total 为 status 过滤后明细总数                                     |

### 5.3 单制品导出声明文档（openlibing-sca）

`POST /gateway/openlibing-sca/project/notice/scan/export`（ProjectNoticeExportPo：productName + 可选 exportScope=FULL/DIRECT）——声明文档明细弹窗"导出声明文档"按钮调用，**前端固定传 exportScope=DIRECT**，与 exportBatch 同一受理范式，**不传 userId**。

### 5.4 批量生成版本级声明文档（openlibing-sca，25060aef2）

`POST /gateway/openlibing-sca/project/notice/scan/startBatch`

**请求体**：复用 ProjectNoticeScanMultiFilterQueryPo（**与 scanStatusByMultiFilter 完全一致**）：productType 必填 + filters 主列表过滤项透传 + 可选 statuses 扫描状态集合 + pageNum/pageSize（随体透传但不参与本接口语义）。前端经 `buildQueryParam()` 与列表查询共用组装。

**语义**：受理时按 productType 查 SBOM 取制品名（空则拒绝）；statuses 非空时仅对最新扫描状态命中的制品发起扫描（未扫描制品不参与命中）；后台单线程池逐制品调用 /start 生成声明文档（保留事务语义），单个失败跳过记日志不中断。

**响应**：受理成功返回 code 200、无 data（无 taskId，不注册导出中心）；实际受理/成功/失败条数见服务日志，结果以列表刷新/轮询为准。

### 5.5 前端 API 层

softWareCompent.js 新增 `exportNoticeBatch`（exportBatch）、`noticeScanStatusByMultiFilter`（scanStatusByMultiFilter）与 `generateVersionNoticeBatch`（startBatch）三个请求函数（对齐现有函数风格）；api/sbom 层零改动。

## 6. 共享常量提取（重构，控制影响面）

解析状态相关常量现散落在 index.vue，提取到 `SbomManagement/common.ts`（弹窗状态列已改为 NOTICE 扫描状态、不再消费这些常量，但提取仍消除主列表内联定义）：

| 常量/函数                    | 原位置          | 说明                                                                                         |
| ---------------------------- | --------------- | -------------------------------------------------------------------------------------------- |
| scanStatusMap                | index.vue L1071 | 状态→tag 类型/文案映射（主列表消费）                                                         |
| SCAN_STATUS_OPTION_GROUPS    | index.vue L1178 | 状态筛选 5 分组（含 FAILED+FAILED_FINISH 合并等细节，避免复制漂移；主列表消费）              |
| expandScanStatusFilterValues | index.vue L1187 | 筛选选中值展开为后端状态值数组（主列表消费）                                                 |
| DEPENDENCY_TYPE / TEXT       | 新增            | 依赖类型枚举与文案映射，NoticeDetailTable 列渲染引用（成分表内联映射保持不动，避免无关改动） |

NOTICE 扫描状态映射（NOTICE_STATUS_TAG/noticeStatusOptions，弹窗文案 待扫描/扫描中/成功/失败）仅 ProductExportDialog 消费，定义在组件内、不进 common.ts。

index.vue 仅做"删除本地定义 + import"的机械替换，不改变任何运行行为。

## 7. 边界场景与降级策略

| #   | 场景                                                    | 行为                                                                                                  |
| --- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | 导出弹窗打开时主列表有筛选                              | **继承主列表过滤项**（filters 透传，口径与主列表一致）；NOTICE 扫描状态筛选初始为全部（含未扫描制品） |
| 2   | 弹窗列表为空（total=0）                                 | 导出按钮置灰 disabled                                                                                 |
| 3   | exportBatch / scanStatusByMultiFilter 未部署（404/502） | 拦截器统一错误提示；提交失败弹窗不关闭，无 JS 报错                                                    |
| 4   | 制品名集合为空（筛选无结果）                            | 导出按钮随 total=0 禁用，无可提交场景                                                                 |
| 5   | 2×2 聚合字段全 null（后端聚合失败）                     | 前端不消费拆解字段，整体统计正常展示（不受影响）                                                      |
| 6   | details.list[].dependencyType 缺失/null                 | 依赖类型列显示 --                                                                                     |
| 7   | 状态筛选 + 分页叠加                                     | 筛选变更回第 1 页重新请求；翻页带当前筛选，total 为筛选后总数                                         |
| 8   | 轮询期间切换筛选/翻页                                   | usePollingTask 防重入跳过在途请求，refreshDetails 完成后按新条件查询；轮询始终携带当前筛选与分页      |
| 9   | 导出提交中重复点击                                      | loading 防重复（useExportTaskSubmit 内建）                                                            |
| 10  | 弹窗关闭再打开                                          | 各弹窗均在 watch(visible) 中重置，筛选/格式回初始                                                     |
| 11  | 制品名超长 / 空列表                                     | 超长 tooltip / Empty 空态组件                                                                         |
| 12  | 嵌套弹窗层级                                            | SbomExportDialog append-to-body，避免被父 dialog 裁切                                                 |

## 8. 风险与开放问题

### 风险

| 风险                                       | 等级 | 缓解                                                                                      |
| ------------------------------------------ | ---- | ----------------------------------------------------------------------------------------- |
| 后端契约未就绪即开发，联调时字段/结构变动  | 高   | 契约收敛在 useNoticeScan.ts（B）与 ProductExportDialog 请求组装（A）两处；§5 已备降级方案 |
| 依赖类型枚举前端(2)/后端设计文档(3)不一致  | 中   | 联调首日核对；单一常量表修改                                                              |
| 批量导出数据量大（全量制品）               | 中   | 任务式异步导出，前端不感知数据量；后端评估打包耗时（契约已注明 zip 建议）                 |
| index.vue 已约 2800 行                     | 低   | 新逻辑全部收敛在新组件，index.vue 仅增加按钮/挂载/状态                                    |
| e2e 目录当前未入库（本地 Playwright 工程） | 低   | e2e 按现有本地工程编写；入库策略另行处理                                                  |

### 开放问题（联调/评审时确认）

| #   | 问题                                                     | 当前假设                                                                             |
| --- | -------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Q1  | dependencyType=2 在分类统计中计入 direct 还是 indirect？ | **已确认：仅计入直接**（后端 breakdown 聚合修正 403a09ddf2）；前端当前不消费拆解统计 |
| Q2  | 依赖类型拆解统计是否展示？                               | **已确认：不展示**（产品决策移除括号拆解，仅保留整体统计；后端字段保留供后续启用）   |
| Q3  | 失败引导提示语是否需要常驻（无失败数据也展示）？         | 仅 failCount>0 时展示                                                                |
| Q4  | 制品导出是否需要独立权限控制点？                         | 不加，与现有导出入口一致                                                             |
| Q5  | exportBatch 的 exportScope 取值命名                      | 后端契约为 FULL/DIRECT（已落地），前端直接对齐                                       |
| Q6  | 批量导出任务名是否体现导出范围                           | 后端返回 fileName 时以其为准，否则固定默认名                                         |

## 9. 跨仓协调

| 仓             | 角色                            | 交付物                                                                                        |
| -------------- | ------------------------------- | --------------------------------------------------------------------------------------------- |
| openlibing-web | 本次实现                        | 前端全部改动（§3、§4、§6）                                                                    |
| openlibing-sca | 契约依赖（dev_20261019 已实现） | notice/scan/exportBatch、scanStatusByMultiFilter、info（含明细 dependencyType）、export（§5） |

协调动作：本 design.md §5 即接口对接文档，Phase 2 结束后推送后端团队；联调窗口安排在 Phase 3 交付后。

## 10. 测试策略（Full 模式）

### 10.1 单元/组件测试（如项目单测框架可用）

- useNoticeScan：状态筛选、isDetailFiltered 空态文案、resetScanState 复位完整性。
- ProductExportDialog：filters 透传主列表过滤项、状态筛选参数组装（statuses 数组/空）、分页重置、导出链路请求组装（productNames + exportScope=DIRECT，无 userId）。
- sbomExportDialog：基线零改动，回归既有单制品导出即可。

### 10.2 E2E（Playwright，现有本地 e2e 工程）

- A 链路：导出声明文档按钮 → 弹窗加载 → 状态筛选/分页 → 导出按钮提交（exportScope=DIRECT，mock 契约响应）→ toast 与关闭。
- B 链路：依赖类型列渲染 → 状态筛选（后端过滤）与分页 → 整体统计终态展示 → 失败提示语显隐。

### 10.3 手工验证清单（beta + 联调）

1. 契约就绪后真实导出（exportScope=DIRECT），导出中心进度与文件内容抽检（仅含直接依赖数据）。
2. 扫描进行中打开弹窗：进度条正常推进；终态后软件总数/成功/失败统计展示且随轮询收敛。
3. 补充信息闭环：失败行编辑下载地址 → 补充成功 → 统计与提示语联动更新。
4. 响应式：1366/1920 及窄屏模拟下检查按钮行、弹窗、表格布局。
5. 样式自查：对照 ui-style-guide 规范（按钮尺寸/间距/配色/弹窗规范）。

### 10.4 回归范围

- 制品主列表查询/筛选/排序/分页（常量提取为机械替换）。
- 现有"全量导出"（单制品）与"声明文档"导出链路。
- 声明文档弹窗既有能力：生成/轮询/批量补充/状态筛选/导出。
