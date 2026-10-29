# Design: add-sbom-notice-export

## Context

- 成分分析页面（`apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`）导出区域已改造为 `el-dropdown`（`trigger="click"`）：触发按钮为「导出」+ 下箭头图标，菜单含「全量导出」「声明文档」两项，两个菜单项的 tooltip 均为说明性短文案（见 D0）。「导出声明文档」此前接通的是**点击即 blob 下载**（`handleExportNotice` + `exportNoticeScan`），本次变更为弹窗交互。
- notice 扫描为后端异步任务：`POST /project/notice/scan/start` 启动，`/info` 查询进度与明细，`/supplement` 人工补充失败软件，`/export` 导出合并 NOTICE。后端实体（openlibing-sca 仓库）：
  - `/info` 返回 `ProjectNoticeScanInfoVO`：`status`（0-待处理/1-处理中/2-成功/3-FAILED）、`totalCount`/`successCount`/`failCount`、`errorMsg`、`details[]`（`softwareName`、`version`、`downloadUrl`、`status`（0-待处理/1-成功/2-失败）、`errorMsg`）。
  - `/supplement` 入参 `ProjectNoticeScanSupplementPo`：`productName` + `supplements[]`（`softwareName` 必填、`version` 可选、`downloadUrl` 可选、`content`），返回 `ProjectNoticeScanVO`（`scanStatus`/`scanStatusName`/`mergedOssUrl`/剩余 `failedDetails[]`）。
- Apifox 项目（id 8752475）中「notice信息」接口（`/gateway/openlibing-sca/project/notice/scan/info`）已登记但 schema 未录入，请求/响应契约以 openlibing-sca 代码为准。
- 页面现有 API 集中在 `src/api/scaApi/softWareCompent.js`（SCA 服务，`apiClient.post` 风格）；`exportNoticeScan` 由本分支新增（任务模式契约）。
- `src/utils/until.js` 既有 `exportFile(blob, fileName)` 与 `xssFilter`（本变更不再新增/使用 blob 链路工具，曾引入的 `parseContentDispositionFilename` 已随 blob 链路移除一并删除）。
- ApiClient 对 blob 响应的 `data?.code` 检查不生效，blob 业务错误须在页面层识别。

## Goals / Non-Goals

**Goals:**

- 「导出声明文档」点击后打开弹窗，表格展示扫描明细（软件包名称、版本、状态、下载地址），轮询刷新直到终态。
- 失败明细支持批量编辑：勾选失败行 → 逐条填写下载地址或 NOTICE 内容（二选一）→ 一次性提交 supplement 接口 → 刷新表格。
- 扫描成功且无失败明细时，弹窗内提交导出任务并接入全局导出中心（右下角浮窗进度提醒、完成后自动下载）。
- 不改动任何既有 SBOM 代码逻辑（`sbomExportDialog.vue`、`src/api/sbom/*` 保持原样）。

**Non-Goals:**

- 不在本变更内修改 openlibing-sca 后端代码；supplement 校验放宽（content 从必填改为与 downloadUrl 二选一）记为跨仓协调项，由后端单独调整。
- 不处理导出进度条/分块下载。

## Decisions

### D0: 导出区域下拉改造（已落地，保持不变）

原单个「全量导出」按钮改为 `el-dropdown`（`trigger="click"`）+ 内部 `el-button type="primary"` 触发按钮，`:disabled="!productName"` 复用原有禁用逻辑；「全量导出」菜单项 command 保持原行为。菜单项说明 tooltip 挂在 `QuestionFilled` 图标上（tooltip 直接包裹图标，`el-dropdown-item` 内无需额外 div），图标 `@click.stop`。菜单项文案均为说明性描述：「全量导出」tooltip 为「导出SPDX、CycloneDX格式的全量制品数据」；「声明文档」tooltip 为「查看软件包声明文档明细，支持导出」（口径调整：原「全量导出」与名称一致、「声明文档」长文案的方案已按实现收敛为短说明文案）。

### D1: API 函数归入 `src/api/scaApi/softWareCompent.js`

notice 接口均属 `openlibing-sca` 服务，统一归入既有 SCA API 模块（与 `exportNoticeScan` 归属一致），遵循该文件默认导出对象风格：

```js
const softWareCompent = {
  // ...
  /** 导出声明文档（notice）：提交导出任务，返回 { exportTaskId, fileName, message } */
  exportNoticeScan: (a, s) =>
    apiClient.post("/gateway/openlibing-sca/project/notice/scan/export", a, s),
  /** notice 扫描启动（生成声明文档常驻入口使用） */
  noticeScanStart: (a, s) =>
    apiClient.post("/gateway/openlibing-sca/project/notice/scan/start", a, s),
  /** notice 扫描信息查询（轮询用） */
  noticeScanInfo: (a, s) =>
    apiClient.post("/gateway/openlibing-sca/project/notice/scan/info", a, s),
  /** notice 扫描失败软件人工补充 */
  noticeScanSupplement: (a, s) =>
    apiClient.post(
      "/gateway/openlibing-sca/project/notice/scan/supplement",
      a,
      s,
    ),
};
```

> 说明：四个函数均为本分支新增（`exportNoticeScan` 非既有函数，任务模式契约在新增时即确定）。

### D2: 「导出声明文档」点击行为改为打开弹窗

`handleExportCommand('notice')` 改为打开声明文档弹窗（标题「声明文档明细」）并传入当前 `productName`；原有的直接下载逻辑整体废弃，由弹窗内「导出声明文档」按钮触发的任务提交取代，行为规范见 D6。弹窗实现按职责拆分为 `component/noticeExport/` 模块（与 `sbomExportDialog.vue` 同级的模块目录）：`index.vue`（弹窗容器 + 明细工具栏）、`NoticeScanSummary.vue`（概要区）、`NoticeDetailTable.vue`（明细表格）、`BatchSupplementDialog.vue`（补充编辑弹层）、`useNoticeScan.ts`（扫描状态层：查询 + 轮询 + 筛选 + 展示态 computed），并配套 `__tests__/` 拆分冒烟测试。弹窗通过 `v-model:visible` 控制显隐、props 传入 `productName`。导出/补充/生成请求进行中（对应 loading 态为 true）时，弹窗 SHALL 阻止关闭（`handleVisibleChange` 守卫），避免请求在途中弹窗关闭导致状态丢失。

### D3: 轮询策略

弹窗打开时立即调用一次 `/info`，此后：

- 扫描整体 `status` 为 0（待处理）或 1（处理中）时，每 **5 秒**轮询一次，直至进入 2（成功）/3（失败）终态。
- 概要区状态以彩色圆点状态胶囊展示（处理中圆点带呼吸动画，替代静态 el-tag）；处理中且已有明细数据时，额外展示进度条与「已完成 x/总数」（按明细已完成数/`totalCount` 实时计算，随轮询前进，进度条不显示百分比文字避免重复）；进入终态后才展示软件总数与成功/失败数量（后端在扫描完成前不产出计数数据）。
- 轮询统一由通用 hook `usePollingTask`（`src/hooks/usePollingTask.js`，本分支新增）驱动：防重入（在途请求不重复发起）、`enabled` 双重校验（发起前 + 响应后，弹窗已关闭则丢弃结果）、连续失败达阈值自动停止。
- **失败自愈策略**：首查失败（尚无数据）时停止轮询并展示空态；已有数据后单次查询失败**保留旧数据继续轮询**（瞬时网络错误可自愈），连续失败达 3 次（`maxErrors`）由 hook 自动停止，非 200 错误信息由 ApiClient 拦截器统一提示。
- **补充后继续轮询**：轮询保持条件为「整体状态为待处理/处理中，或明细中存在待处理子任务」——人工补充提交成功后，失败软件重新进入待处理，此时即使整体已为终态也保持 5s 轮询，直至明细中不存在待处理子任务（`shouldKeepPolling`）。
- 弹窗关闭（`v-model` 变为 false）或组件卸载时清除定时器，防止内存泄漏与后台续跑。
- 补充提交成功后主动触发一次 `/info` 查询刷新表格。
- 轮询请求传 `disabledLoading: true` 禁用 ApiClient 全局 loading，避免每次轮询在页面触发加载遮罩；弹窗内局部 `v-loading` 宿主为「概要 + 明细」整体外层容器（`min-height: 220px`），仅在首次加载（尚无数据）时展示——快请求随首查完成立即消失，轮询刷新期间不出现任何加载遮罩（原方案的 300ms 防抖已简化移除，仅保留"首查才展示"条件）。

固定间隔轮询而非 SSE/WebSocket：扫描为分钟级任务，5s 轮询实现简单、与后端现有接口形态匹配，无实时性压力。

### D4: 表格与状态映射

弹窗表格列：软件包名称（`softwareName`）、版本（`version`，空显示「-」）、状态（`status`）、下载地址（`downloadUrl`，可点击外链，为空显示「-」）、操作（编辑图标，仅失败行可点击打开单条补充弹层，非失败行置灰并 tooltip 提示「仅失败软件支持补充信息」）。明细状态映射：0-待处理 / 1-成功 / 2-失败（失败行以 danger 标签展示并携带 `errorMsg` tooltip）。表格上方概要区以彩色圆点状态胶囊展示扫描整体状态，整体状态文案为 0-待处理 / 1-生成中 / 2-生成完成 / 3-生成失败（区别于明细状态的「待处理/成功/失败」），处理中圆点带呼吸动画，处理中且已有明细数据时额外展示进度条与已完成数，进入终态后展示 `totalCount`/`successCount`/`failCount` 概要，失败终态额外展示 `errorMsg`。

### D5: 失败数据批量编辑（二选一校验）

- 表格首列多选框，**仅失败行可勾选**（`selectable`）；「批量补充信息」按钮仅在存在勾选行时可用，按钮文案提示勾选数量（如「已选 2」）。另有操作列编辑图标作为**单条补充入口**（仅失败行可用，见 D4）。
- **整体任务处理中禁用补充**：扫描整体状态为待处理/处理中时，操作列图标与批量补充入口/提交均禁用（tooltip「任务生成中，暂不能补充信息」），弹窗容器侧 `openBatchEdit`/`confirmBatchEdit` 兜底拦截，避免处理中提交补充信息。
- **勾选跨刷新保留**：表格设置 `row-key`（`softwareName@@version` 稳定 key）+ `reserve-selection`，5s 轮询替换整个 `details` 数组或筛选变更导致数据整体替换时，用户勾选不丢失；`reserve-selection` 恢复勾选不受 `selectable` 限制，`openBatchEdit` 内对传入行做失败状态过滤兜底，补充成功后主动 `clearSelection` 清空。
- 点击「批量补充信息」或操作列图标打开编辑弹层（「补充失败软件信息」，提示每条失败软件包可补充「下载地址」或「NOTICE 内容」），按勾选行逐条渲染编辑表单：下载地址（输入框，可选）+ NOTICE 内容（文本域，视下载地址填写情况可必填，未填下载地址时必填提示）。
- **校验规则（用户确认的需求口径）**：每条补充项 `downloadUrl` 与 `content` **二选一**——填写了下载地址则内容可不填；未填下载地址则必须填写内容。
- 提交调用 `noticeScanSupplement`，请求体 `{ productName, supplements: [{ softwareName, version, downloadUrl, content }] }`（`version` 原样带回用于精确匹配明细），成功后 `ElMessage.success` + 关闭编辑弹层 + 刷新表格。
- ⚠️ **与当前后端代码的冲突**：openlibing-sca 现有实现（`ProjectNoticeScanSupplementPo.content` `@NotNull` + service 层「softwareName与content不能为空」校验）要求 content 必填，不支持"仅填下载地址"。按 AGENTS.md 约定以需求口径写入 spec，同时在本设计记录：**openlibing-sca 需将校验放宽为 downloadUrl/content 二选一**，联调前需后端完成该项调整。

### D6: 弹窗内导出接入全局导出中心（方案调整：原方案为弹窗内 blob 下载）

- 可用条件不变：**仅取决于扫描整体 `status` = 2（成功）**（用户确认的口径）；非成功态置灰，失败态（`status` = 3）tooltip 展示后端返回的失败原因 `errorMsg`，其余非成功态提示"扫描未完成，暂不能导出"。
- 后端 `/export` 已由文件流改为异步任务模式：返回 `{ code: 200, data: { exportTaskId, fileName, message } }`，任务登记到统一导出框架（与顶栏「我的导出」抽屉同源）。
- 前端实现收敛为共享 hook `useExportTaskSubmit`（`src/hooks/useExportTaskSubmit.ts`，本分支新增）：弹窗 `handleExport` 以请求函数 `exportNoticeScan({ data: { productName } })`（无 blob）+ 任务元信息 `{ source: 'sbom-notice', type: 'NOTICE_EXPORT', defaultTaskName: '声明文档-<productName>' }` 调用 `submitExport`，hook 内部完成「提取任务 ID（`extractExportIdFromResponse`，已兼容 `exportTaskId` 字段）→ `exportTaskStore.addTask` 注册（任务名优先取响应 `fileName`，缺失时用 `defaultTaskName` 兜底）→ 提示「已提交导出任务」」，并提供 `exportLoading` 供按钮 loading 防重复点击；提取不到任务 ID 时提示「导出任务创建失败」不注册任务。该 hook 可被其他导出入口复用。
- 后续进度轮询、右下角浮窗提醒、顶栏「我的导出」角标、完成后自动下载均由 `exportTask` store 既有逻辑接管，弹窗内不再做 blob 下载、`content-disposition` 文件名解析与 JSON 错误体识别；`exportLoading` 态绑定导出按钮防止重复点击，try/finally 复位。
- `mapExportRecord.ts` 的 `TYPE_LABEL` 新增 `NOTICE_EXPORT: '声明文档'`（「我的导出」抽屉类型文案）。
- 曾随 blob 方案引入的 `parseContentDispositionFilename` 已从 `until.js` 删除（blob 链路整体移除后无调用方）。

### D7: 「生成声明文档」常驻按钮（口径调整，用户已确认）

- **展示（口径再调整，随最新实现）**：按钮常驻提供，不再限于空态——存在扫描记录且处于终态时按钮位于明细表格工具栏，与「批量补充信息」「导出声明文档」同行（排列顺序：生成声明文档 → 批量补充信息 → 导出声明文档；三按钮间距统一由工具栏 flex gap 12px 控制，抵消相邻 `el-button` 默认 margin 避免双重间距）；空态（无明细工具栏）时展示在空态提示区。注意：非终态下按钮的处理口径经历「置灰 → 隐藏 → 置灰」的反复，**最终以实现为准：工具栏常驻渲染、非终态（待处理/处理中）禁用**（空态按钮无禁用概念）。
- **可用性**：非终态（待处理/处理中，status=0/1）下工具栏按钮禁用；空态与终态（成功/失败，status=2/3）可点击，即失败与成功终态都支持重新生成。
- **二次确认（用户确认）**：已存在扫描记录（终态）时点击，先经 `ElMessageBox.confirm` 弹窗确认「重新生成将覆盖当前扫描结果与软件包明细」，确认后调用启动接口；取消则不发起请求。空态下点击直接发起、无需确认。
- 点击按钮调用 Apifox「生成notice」接口 `POST /gateway/openlibing-sca/project/notice/scan/start`（项目 8752475，接口 id 508164764），请求体 `{ productName }`（用户确认：与 `/info` 一致；Apifox 该接口请求体 schema 未录字段，以用户确认口径为准），响应为 `{ code, message, data, total }`（`data` 为字符串，前端仅判断 `code === 200`，不消费 `data`）。
- 请求进行中按钮 loading 并阻止重复点击（独立 `startLoading` 态，try/finally 复位）；确认弹窗打开期间按钮仍可点但 `handleGenerateClick` 以 `startLoading` 防重入，且确认弹窗自身串行。
- 启动成功（`code === 200`）后立即调用一次 `fetchScanInfo()` 刷新：新扫描状态为待处理/处理中时由既有轮询逻辑接管（D3）。
- 启动失败：ApiClient 拦截器统一提示，按钮恢复可点击。
- 该按钮为独立 API 函数 `noticeScanStart`，归入 `src/api/scaApi/softWareCompent.js`（与 D1 一致）。

### D8: 补充信息提交前的 XSS 防护（新增，用户确认）

- **风险分析**：supplement 提交的 `downloadUrl` 与 `content` 均为不可信用户输入，下游两处消费：① `downloadUrl` 在明细表格中以真实链接渲染（`<a :href="row.downloadUrl" target="_blank">`），填入 `javascript:` 等伪协议即形成存储型 XSS；② `content` 由后端合入导出的 NOTICE 文档，同样不可直接信任。
- **措施**：
  - `downloadUrl`：提交校验仅允许 **http/https 协议**（正则 `^https?:\/\//i`），不通过时行内报错「下载地址仅支持 http/https 协议」并阻止提交。不使用项目 `xssFilter` 处理 URL——它是 HTML 标签/属性白名单过滤，对不含标签的裸伪协议 URL（如 `javascript:alert(1)`）无效，URL 场景必须用协议白名单。
  - `content`：**不做前端 HTML 过滤**（口径调整）——`xssFilter` 是 HTML 标签/属性白名单过滤，NOTICE 内容以纯文本写入导出文档，前端过滤会损坏 `<xxx>` 等合法文本内容；提交仅做 trim 后原样入参，XSS 防线为：① 下载地址协议白名单（上条）；② 后端在合入 NOTICE 文档及后续渲染场景做统一过滤；③ 前端弹窗与表格展示均为插值渲染（Vue 自动转义），无 `v-html`。
  - 弹窗与表格内所有展示均为插值渲染（Vue 自动转义），无 `v-html`，展示层无需额外过滤。
- **范围记录**：明细表格 `<a :href="row.downloadUrl">` 渲染的是后端返回数据（可能含本次补充之外的其他来源），本变更仅在补充提交入口做拦截；如需展示层对所有来源统一兜底校验，另起变更。

### D9: 明细状态列筛选（新增，服务端筛选，status 为单值）

- 后端已扩展 `/info` 接口：请求体在 `productName` 基础上新增可选 `status` 字段表示明细状态筛选（单值，0-待处理/1-成功/2-失败），**不传递则表示全量查询**；返回的 `details[]` 即为过滤后的子集。
- **交互样式复用项目既有表头筛选组件** `@/components/filterDropdown.vue`（与 `publishTable.vue`、`vulnTable.vue` 等页面的列头筛选同源）：挂在状态列 `#header` 插槽，`type="radio"` 单选模式（status 为单值），静态选项 `[{待处理,0},{成功,1},{失败,2}]` 与明细状态映射（D4）一致，下拉内含搜索框与「筛选/重置」按钮。
- **数据流**：`filterStatus` ref（`null` = 全部）；`fetchScanInfo` 组装请求体时，`filterStatus` 非 null 才附加 `status` 单值字段；筛选变更（选中或重置）立即触发一次 `fetchScanInfo` 重新查询。轮询请求天然携带当前筛选值（`fetchScanInfo` 统一组装）。若变更瞬间恰有轮询请求在途，本次触发会被 `pollInFlight` 防重入跳过——处理中场景最迟由下一个 5s 轮询周期以新筛选补查，终态场景无在途轮询，自愈无感。
- **筛选与概要进度互斥**：筛选生效时 `details[]` 为过滤子集，按明细计算的「已完成 x/总数」进度会失真，故筛选生效时处理中概要区仅展示状态胶囊、隐藏进度条与已完成数；终态数量统计（`totalCount`/`successCount`/`failCount` 为扫描整体字段）不受筛选影响，正常展示。
- **弹窗重开重置**：`resetState` 将 `filterStatus` 归 null，每次打开弹窗默认全量。
- **空态文案区分**：筛选生效且明细为空时展示「当前筛选条件下暂无软件包」，未筛选时保持「暂无扫描明细」。
- 勾选补充（仅失败行可勾选）与导出可用性（仅取决于扫描整体状态）逻辑不受筛选影响；筛选变更导致表格数据整体替换时，`row-key` + `reserve-selection` 保证勾选跨刷新保留（见 D5），失败行过滤由 `openBatchEdit` 兜底，补充成功后主动清空勾选。

## Risks / Trade-offs

- [supplement 后端校验未放宽前，"仅填下载地址"的补充会提交失败] → 前端校验先行拦截；联调依赖跨仓协调项完成（见 D5 冲突记录）。
- [Apifox 中「notice信息」接口 schema 未录入] → 契约以 openlibing-sca 代码为准（`ProjectNoticeScanInfoVO`/`ProjectNoticeScanDetailInfoVO`），待后端补录 Apifox 后对齐。
- [`/info` 接口对无扫描记录的制品返回失败（「扫描记录不存在」）] → 弹窗展示空态提示「该制品尚未生成声明文档扫描记录」，不轮询。
- [轮询期间用户修改了页面制品选择] → 弹窗以打开时传入的 `productName` 为准，不随页面选择联动；关闭重开即以新制品查询。
- [notice 导出进行中下拉整体禁用] → 迁移进弹窗后仅影响弹窗内导出按钮，不再阻塞全量导出入口，较原实现更优。
- [`/export` 契约改为返回 `exportTaskId` 依赖后端同步上线] → 后端已将响应字段定为 `exportTaskId`；前端 `extractExportIdFromResponse` 已兼容该字段名，联调前若字段不一致仅表现为浮窗不弹出（提示「导出任务创建失败」），不影响其他功能。

## Open Questions

无（下载行为归属、二选一校验口径已与用户确认；轮询间隔 5s 为实现默认值，如需调整只改常量）。
