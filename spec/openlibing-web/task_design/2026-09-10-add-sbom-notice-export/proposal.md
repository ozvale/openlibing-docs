# Proposal: add-sbom-notice-export

## Why

SBOM 成分分析页面（CompositionAnalysis）的导出能力需要扩展：导出区域原本只有一个「全量导出」按钮，需要改造为下拉菜单以容纳多种导出类型，并新增「导出声明文档」入口。声明文档由后端扫描生成（notice 扫描），导出前用户需要了解扫描进度与失败软件明细，并对失败软件人工补充下载地址或 NOTICE 内容后重新合并，因此「导出声明文档」需要由"点击即下载"升级为"弹窗 + 轮询 + 失败数据人工补充 + 弹窗内导出"的完整交互。

## What Changes

### 已落地：导出区域下拉改造（保持不变）

- 成分分析页面导出区域改造：将原有单个「全量导出」按钮改为「导出」下拉按钮（点击展开菜单），菜单包含「全量导出」「声明文档」两个菜单项，每个菜单项文字后带说明图标，tooltip 提示作用于说明图标（「全量导出」tooltip 为说明性文案「导出SPDX、CycloneDX格式的全量制品数据」，「声明文档」tooltip 为说明性描述文案），点击图标不触发导出；未选择制品时下拉按钮禁用。「全量导出」原有行为（打开导出对话框）保持不变。

### 本次调整：导出声明文档改为弹窗交互

- 点击「声明文档」菜单项不再直接下载，而是打开「声明文档明细」弹窗：
  - **表格展示**：弹窗内表格展示当前制品的 notice 扫描明细，字段为软件包名称（`softwareName`）、版本（`version`）、状态（`status`）、下载地址（`downloadUrl`）。
  - **轮询刷新**：表格内容通过轮询调用 notice 信息接口（`POST /gateway/openlibing-sca/project/notice/scan/info`，Apifox「notice信息」）获取；扫描整体状态为待处理/处理中、或明细中存在待处理子任务（如人工补充后失败软件重新进入待处理）时按固定间隔（5 秒）轮询，进入终态且明细无待处理子任务后停止轮询，弹窗关闭时停止轮询并清理定时器；查询失败采用自愈策略（首查失败展示空态并停止，已有数据保留旧数据继续轮询、连续失败 3 次自动停止）。
  - **明细状态筛选**：状态列表头提供筛选下拉（复用项目共享 `filterDropdown` 组件，单选模式，选项「待处理/成功/失败」），为服务端筛选——选中后 info 请求附加单值 `status` 字段重新查询，不传则表示全量；筛选生效时处理中概要区仅展示状态胶囊、不展示按明细计算的进度（过滤子集无法计算整体进度）。
  - **失败数据补充编辑**：对状态为失败的明细行提供补充编辑能力，入口包括操作列编辑图标单条补充与勾选失败行后点击「批量补充信息」按钮批量编辑，在编辑弹层中逐条填写下载地址或 NOTICE 内容；校验规则为**每条补充项下载地址与 NOTICE 内容二选一**（填写了下载地址则内容可不填，未填下载地址则必须填内容）。提交时调用 openlibing-sca 的 `POST /gateway/openlibing-sca/project/notice/scan/supplement` 接口，成功后刷新表格数据。
  - **生成声明文档常驻按钮**：弹窗常驻提供「生成声明文档」按钮——空态（无扫描记录）下展示在空态提示区、点击直接发起扫描；有扫描记录时按钮位于明细表格工具栏（生成 → 批量补充 → 导出），终态（成功/失败）点击经二次确认后重新生成，非终态（待处理/处理中）按钮禁用展示；启动调用 `POST /gateway/openlibing-sca/project/notice/scan/start`（请求体 `{ productName }`），成功后立即重新调用 info 接口并按既有轮询逻辑刷新。
  - **补充入口处理中禁用**：扫描整体处于待处理/处理中时，单条补充入口与批量补充提交均禁用（提示「任务生成中，暂不能补充信息」），避免处理中提交补充信息。
  - **弹窗内导出**：仅当扫描整体状态为成功（status=2）时，弹窗内「导出声明文档」按钮可用，点击后调用 `/gateway/openlibing-sca/project/notice/scan/export` 提交导出任务（后端返回 `{ exportTaskId, fileName, message }` 并登记到统一导出框架），前端经共享 hook `useExportTaskSubmit` 将任务注册进全局导出中心（`exportTask` store，任务名优先取响应 `fileName`、缺失时兜底 `声明文档-<productName>`），后续进度提醒（右下角浮窗、顶栏角标）与完成后自动下载由导出中心接管，弹窗内不再做 blob 下载。
- 在 SCA 服务 API 模块 `src/api/scaApi/softWareCompent.js` 中新增 `noticeScanInfo`、`noticeScanSupplement`、`noticeScanStart`、`exportNoticeScan` 四个接口函数（`exportNoticeScan` 为本分支新增，直接采用任务模式契约：返回 `{ exportTaskId, fileName, message }`）。

### 跨仓协调项（openlibing-sca）

- supplement 接口当前后端实现校验每条补充项 `content` 必填，与"填写了下载地址则内容可选"的新需求冲突；需 openlibing-sca 后端将校验放宽为 `downloadUrl` 与 `content` 二选一。前端按新需求实现表单校验，联调前依赖后端同步调整。
- export 接口契约已由后端调整：由返回 blob 文件流改为返回 `{ exportTaskId, fileName, message }` 并登记到统一导出框架（后端已完成）；前端通过既有工具 `extractExportIdFromResponse`（兼容 `exportTaskId` 字段）提取任务 ID，无需修改该共享工具。

## Capabilities

### New Capabilities

- `sbom-notice-export`: SBOM 成分分析页面的声明文档（notice）导出能力，包括：导出下拉菜单、扫描状态弹窗与轮询刷新、生成声明文档常驻入口（空态直发、终态二次确认重新生成）、失败软件明细的批量人工补充（下载地址/NOTICE 内容二选一，处理中禁用）、扫描成功后提交导出任务并接入全局导出中心（浮窗进度提醒与自动下载）。

### Modified Capabilities

（无 — `openspec/specs/` 目前为空，没有需要修改的既有能力）

## Impact

- **代码**：
  - `apps/web-openlibing/src/api/scaApi/softWareCompent.js`（新增 `exportNoticeScan`（任务模式契约）、`noticeScanInfo`、`noticeScanSupplement`、`noticeScanStart`）
  - `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`（「声明文档」菜单项由直接下载改为打开弹窗；新增弹窗组件挂载）
  - `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/noticeExport/`（新增声明文档导出模块：`index.vue` 弹窗容器与工具栏、`NoticeScanSummary.vue` 概要区、`NoticeDetailTable.vue` 明细表格、`BatchSupplementDialog.vue` 补充编辑弹层、`useNoticeScan.ts` 扫描状态层，及 `__tests__/` 拆分冒烟测试）
  - `apps/web-openlibing/src/hooks/usePollingTask.js`（新增通用轮询 hook：防重入、enabled 双重校验、连续失败达阈值自动停止）
  - `apps/web-openlibing/src/hooks/useExportTaskSubmit.ts`（新增导出任务提交 hook：调导出接口 → 提取任务 ID → 注册全局导出中心 → 提示）
  - `apps/web-openlibing/src/stores/exportTask.ts` 与 `apps/web-openlibing/src/utils/extractExportId.ts`（既有全局导出中心，复用不修改；`extractExportIdFromResponse` 已兼容 `exportTaskId` 字段）
  - `apps/web-openlibing/src/views/MyExports/mapExportRecord.ts`（`TYPE_LABEL` 新增 `NOTICE_EXPORT` 类型文案）
- **接口**：
  - 依赖 `POST /gateway/openlibing-sca/project/notice/scan/start`，请求体 `{ productName: string }`，启动 notice 扫描（「生成声明文档」常驻入口使用；Apifox「生成notice」接口请求体 schema 未录字段，契约以用户确认口径为准）。
  - 依赖 `POST /gateway/openlibing-sca/project/notice/scan/info`，请求体 `{ productName: string, status?: number }`（`status` 为后端新增的可选单值筛选字段，明细状态 0-待处理/1-成功/2-失败，不传表示全量），返回扫描状态 + 明细列表（筛选生效时为过滤子集）。
  - 依赖 `POST /gateway/openlibing-sca/project/notice/scan/supplement`，请求体 `{ productName: string, supplements: [{ softwareName, version?, downloadUrl?, content? }] }`，二选一校验依赖 openlibing-sca 后端调整（见跨仓协调项）。
  - `POST /gateway/openlibing-sca/project/notice/scan/export` 已由后端调整为返回 `{ exportTaskId, fileName, message }` 并登记统一导出框架，后续状态查询/下载复用 `getFrameworkExportDetail` / `getFrameworkExportList` / `getFrameworkExportDownloadUrl`。
- **无破坏性变更**：现有「全量导出」行为不受影响；「导出声明文档」由直接下载改为弹窗交互属于本变更目标行为。
