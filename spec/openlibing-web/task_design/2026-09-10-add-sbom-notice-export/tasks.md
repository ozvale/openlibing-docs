# Tasks: add-sbom-notice-export

## 1. 导出区域下拉改造（已在工作区落地）

- [x] 1.1 将 `index.vue` 中单个「全量导出」按钮改为 `el-dropdown`（`trigger="click"`）+「导出」触发按钮，`:disabled="!productName"`
- [x] 1.2 菜单项「全量导出」「声明文档」各带说明图标 tooltip：「全量导出」tooltip 文案与其名称一致，「声明文档」tooltip 为说明性文案（查看进度与明细、补充、提交导出任务、从导出中心下载），tooltip 直接包裹 `QuestionFilled` 图标
- [x] 1.3 「全量导出」command 保持原行为（打开 `showExportDialog` 对话框）
- [x] 1.4 每个菜单项文字后加 `QuestionFilled` 说明图标，图标 `@click.stop` 使点击图标不触发导出命令

## 2. 共享工具

- [x] 2.1 曾在 `apps/web-openlibing/src/utils/until.js` 新增 `parseContentDispositionFilename(disposition)`（解析 `content-disposition` 文件名）；导出链路确定改为任务模式后 blob 链路整体移除，该工具**已从 `until.js` 删除**，不留无调用方代码
- [x] 2.2 新增 `apps/web-openlibing/src/hooks/usePollingTask.js`：通用轮询 hook（防重入、`enabled` 双重校验、连续失败达 `maxErrors` 自动停止、`resetErrorCount`），被 `useNoticeScan` 消费
- [x] 2.3 新增 `apps/web-openlibing/src/hooks/useExportTaskSubmit.ts`：统一导出任务提交 hook（调导出接口 → `extractExportIdFromResponse` 提取任务 ID → `exportTaskStore.addTask` 注册 → 提示），返回 `exportLoading` 防重复点击

## 3. API 层

- [x] 3.1 在 `apps/web-openlibing/src/api/scaApi/softWareCompent.js` 中**新增** `exportNoticeScan(a, s)`（URL `/gateway/openlibing-sca/project/notice/scan/export`，任务模式契约：返回 `{ exportTaskId, fileName, message }`；非既有函数，随本分支一并加入）
- [x] 3.2 在同文件新增 `noticeScanInfo(a, s)`：POST `/gateway/openlibing-sca/project/notice/scan/info`
- [x] 3.3 在同文件新增 `noticeScanSupplement(a, s)`：POST `/gateway/openlibing-sca/project/notice/scan/supplement`
- [x] 3.4 在同文件新增 `noticeScanStart(a, s)`：POST `/gateway/openlibing-sca/project/notice/scan/start`（生成声明文档入口使用，请求体 `{ productName }`）

## 4. 声明文档导出弹窗（拆分为 `component/noticeExport/` 模块：`index.vue` 容器 + `NoticeScanSummary.vue` + `NoticeDetailTable.vue` + `BatchSupplementDialog.vue` + `useNoticeScan.ts`，配套 `__tests__/` 拆分冒烟测试）

- [x] 4.1 弹窗骨架（`noticeExport/index.vue`，标题「声明文档明细」）：`v-model:visible` 控制显隐、props 接收 `productName`；打开时立即调用 `noticeScanInfo({ data: { productName } })` 首查；导出/补充/生成请求进行中时阻止关闭弹窗（`handleVisibleChange` 守卫三个 loading 态）
- [x] 4.2 概要区（`NoticeScanSummary.vue`）：整体状态以彩色圆点状态胶囊展示（整体状态文案 0-待处理/1-生成中/2-生成完成/3-生成失败，处理中圆点带呼吸动画）；处理中且已有明细数据且无状态筛选时，额外展示进度条与「已完成 x/总数」（按明细已完成数实时计算）；进入终态后展示软件总数与 `successCount`/`failCount`，失败终态额外展示 `errorMsg`
- [x] 4.3 明细表格（`NoticeDetailTable.vue`）：列 = 软件包名称（`softwareName`）、版本（`version`，空显示「-」）、状态（明细 0-待处理/1-成功/2-失败映射文案标签 + 失败原因 tooltip）、下载地址（可点击外链，为空显示「-」）、操作（编辑图标，仅失败行可打开单条补充弹层，非失败行置灰并 tooltip 提示）；表格 `row-key`（`softwareName@@version`）+ `reserve-selection` 保证轮询刷新/筛选变更时勾选保留
- [x] 4.4 轮询（`useNoticeScan.ts` + `usePollingTask.js`）：整体状态为待处理/处理中、或明细中存在待处理子任务（如补充后重新进入待处理）时每 5 秒轮询刷新（禁用全局 loading，局部 `v-loading` 仅首次加载/尚无数据时展示）；已有数据后单次查询失败保留旧数据继续轮询（自愈），连续失败 3 次自动停止，首查失败停止并展示空态；进入终态且明细无待处理子任务后停止；弹窗关闭/组件卸载清除定时器
- [x] 4.5 无扫描记录的空态提示（「该制品尚未生成声明文档」），不轮询；空态仅在首查完成后渲染（`firstLoadDone`），避免打开弹窗时 Empty 闪现
- [x] 4.6 「生成声明文档」按钮（终态位于明细工具栏，空态位于空态提示区，非终态禁用，详见第 9 节）：终态点击经 `ElMessageBox.confirm` 二次确认（重新生成将覆盖当前扫描结果与明细）后调用 `noticeScanStart({ data: { productName } })`，空态直接发起无需确认；请求中按钮 loading 且防重复点击；成功后立即调用一次 `fetchScanInfo()` 刷新（待处理/处理中由既有轮询接管）；失败按钮恢复可点击

## 5. 失败明细补充编辑（批量 + 单条入口）

- [x] 5.1 表格首列多选框，仅失败行可勾选（`selectable`）；「批量补充信息」按钮仅在有勾选行时可用并显示勾选数量；操作列编辑图标提供单条补充入口（仅失败行可用）；扫描整体待处理/处理中时补充入口（单条 + 批量提交）统一禁用（提示「任务生成中，暂不能补充信息」，`openBatchEdit`/`confirmBatchEdit` 兜底拦截）
- [x] 5.2 批量补充弹层（`BatchSupplementDialog.vue`，「补充失败软件信息」）：按勾选行逐条渲染表单（下载地址输入框 + NOTICE 内容文本域，软件名 + 版本 tag 标识）
- [x] 5.3 表单校验：每条补充项下载地址与 NOTICE 内容二选一（填了下载地址内容可空；都没填则阻止提交并提示）
- [x] 5.4 提交：调用 `noticeScanSupplement({ data: { productName, supplements: [{ softwareName, version, downloadUrl, content }] } })` 单次提交全部勾选项；成功后提示、关闭编辑弹层、清空勾选并触发一次 `noticeScanInfo` 刷新表格；补充项匹配失败等错误提示后编辑内容不丢失
- [x] 5.5 提交前 XSS 防护（design.md D8，口径随实现调整）：`downloadUrl` 仅允许 http/https 协议（`javascript:` 等伪协议行内报错并阻止提交）；`content` **不做前端 HTML 过滤**（`xssFilter` 会损坏 `<xxx>` 等合法纯文本），trim 后原样入参，XSS 防线为 URL 协议白名单 + 后端 NOTICE 渲染场景统一过滤 + 前端展示层插值转义

## 6. 弹窗内导出接入全局导出中心（方案调整：原 blob 下载改为导出任务模式，后端已同步调整契约）

- [x] 6.1 `handleExport` 改为调用 `submitExport(() => exportNoticeScan({ data: { productName } }), { source: 'sbom-notice', type: 'NOTICE_EXPORT', defaultTaskName: '声明文档-<productName>' })`（无 blob），hook 内经 `extractExportIdFromResponse`（兼容 `exportTaskId` 字段）提取任务 ID；无法提取时提示「导出任务创建失败」且不注册任务
- [x] 6.2 导出按钮可用条件不变：仅扫描整体状态为成功（status=2）时可用；否则置灰，失败态（status=3）提示展示失败原因 errorMsg，其余态提示扫描未完成
- [x] 6.3 拿到任务 ID 后由 `useExportTaskSubmit` 调用 `exportTaskStore.addTask({ id, source: 'sbom-notice', taskName: fileName || '声明文档-<productName>', type: 'NOTICE_EXPORT' })`（任务名优先响应 `fileName`，缺失兜底 `声明文档-<productName>`）并提示「已提交导出任务」；后续进度轮询、右下角浮窗、顶栏角标、完成后自动下载均由全局导出中心接管
- [x] 6.4 `mapExportRecord.ts` 的 `TYPE_LABEL` 新增 `NOTICE_EXPORT: '声明文档'`
- [x] 6.5 `index.vue` 中 `handleExportCommand('notice')` 改为打开弹窗（传入当前 `productName`），移除页面内直接下载路径与 `noticeExportLoading`

## 7. 验证

- [x] 7.1 下拉交互：菜单项与 tooltip 正确；未选制品禁用；「全量导出」不受影响；点击「声明文档」打开弹窗且不触发下载
- [x] 7.2 弹窗与轮询：处理中状态每 5 秒刷新、终态停止（补充后明细重新待处理时继续轮询）、关闭弹窗后无残留请求；已有数据时单次查询失败保留旧数据继续轮询、连续失败 3 次自动停止、首查失败展示空态；处理中概要区展示状态胶囊与进度条；无扫描记录空态正确
- [x] 7.3 生成声明文档常驻按钮：空态与终态（成功/失败）三种场景按钮可用且行为正确（空态直发、终态需确认、取消不发请求；有记录时位于明细工具栏三按钮同行且间距一致）；待处理/处理中（status=0/1）工具栏按钮禁用；终态点击弹出二次确认，确认后向 `/start` 发送 `{ productName }` 请求且请求中防重复点击，取消确认不发起请求；空态点击直接发起、无确认弹窗；成功后立即刷新 info 并进入轮询、按钮随非终态转为禁用；失败按钮恢复可点击
- [x] 7.4 补充编辑：仅失败行可勾选、操作列图标仅失败行可打开单条补充；二选一校验生效；提交请求体结构正确（含 `version` 回填）；成功后表格刷新且失败数减少
- [x] 7.5 弹窗内导出：成功态（status=2）提交任务后右下角浮窗弹出、顶栏「我的导出」角标 +1、任务完成后自动下载、进行中重复点击被阻止；非成功态按钮置灰，失败态提示展示 errorMsg；响应缺少任务 ID 时提示「导出任务创建失败」
- [x] 7.6 与 openlibing-sca 后端联调：确认 supplement 校验已放宽为 downloadUrl/content 二选一（跨仓协调项）
- [x] 7.7 补充提交 XSS 防护（D8，口径随实现调整）：填入 `javascript:` 等非 http/https 下载地址时行内报错并阻止提交；`content` 不做前端 HTML 过滤，含 `<script>` 等标签的文本提交请求体中保持原样（后端 NOTICE 渲染场景统一过滤）；正常 http/https 地址与纯文本内容不受影响

## 8. 明细状态列筛选（增量：后端 `/info` 已扩展 status 单值筛选）

- [x] 8.1 状态列表头接入项目共享筛选组件 `@/components/filterDropdown.vue`（`#header` 插槽，radio 单选模式），静态选项「待处理/成功/失败」与明细状态映射一致，样式与项目其他表格列头筛选一致
- [x] 8.2 服务端筛选：选中状态后 `noticeScanInfo` 请求体附加单值 `status` 字段重新查询；重置（取消筛选）不传 `status` 表示全量；轮询请求统一经 `fetchScanInfo` 组装、天然携带当前筛选值
- [x] 8.3 筛选生效时处理中概要区仅展示状态胶囊、隐藏按明细计算的进度条与已完成数（过滤子集无法计算整体进度）；终态数量统计不受影响
- [x] 8.4 筛选生效且明细为空时空态文案展示「当前筛选条件下暂无软件包」，未筛选保持「暂无扫描明细」
- [x] 8.5 弹窗重开时筛选状态重置为全量（`resetState` 归 null）
- [x] 8.6 验证：单选各状态后请求体携带对应 `status` 单值且表格仅展示对应明细；重置后不传 `status` 且表格全量；筛选生效时处理中不展示进度条；筛选空态文案正确；筛选/轮询刷新后已勾选失败行勾选保留（row-key + reserve-selection）；弹窗关闭重开后筛选恢复默认全量

## 9. 生成声明文档按钮常驻改造（增量，design.md D7 口径调整）

- [x] 9.1 「生成声明文档」按钮常驻展示：有扫描记录且处于终态时置于明细表格工具栏，与「批量补充信息」「导出声明文档」同行（顺序：生成 → 批量补充 → 导出，间距统一由 flex gap 控制）；空态时展示在空态提示区（无工具栏）
- [x] 9.2 可用性（口径随最新实现调整，替代此前的"非终态隐藏"方案）：非终态（待处理/处理中 status=0/1）工具栏按钮常驻渲染并禁用；空态与终态（成功/失败）可点击
- [x] 9.3 终态点击经 `ElMessageBox.confirm` 二次确认（「重新生成将覆盖当前扫描结果与软件包明细」），确认后走既有 `handleStartScan`；空态直接发起；`handleVisibleChange` 关闭守卫沿用 `startLoading`
- [x] 9.4 验证：空态/成功/失败三种场景按钮可用且行为正确（空态直发、终态需确认、取消不发请求）；处理中按钮置灰；重新生成后进入轮询且概要区状态随轮询前进
