## Why

`openlibing-web` 当前在「项目合规 - 文件级兼容性 - 风险数据看板」（`communityList.vue` 的 `projectCompliance` Tab）只有一个「导出」按钮，导出范围是整个看板数据，无法精准导出尚未处理完成的数据子集。运营/分析同学需要频繁导出"未确认 + 手动分析"两类数据进行线下处理，每次都需要在全量导出后人工筛选，效率低且容易遗漏。

同时，「项目合规 - 文件级兼容性」的风险数据详情页（`gitUrlList.vue` 的 `projectCompliance` 分支）缺少批量处理能力：
- 列表无复选框，无法批量勾选数据
- 缺少「批量分析」按钮和批量分析弹窗，需要逐条进入详情操作
- 缺少「分析结果」列，无法在列表直观看到 `manualRiskLevel` 的当前值；缺少「分析说明」列，无法直观看到 `manualDescription`

「开源片段引用合规 - 风险数据详情」（`PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue`）已经具备完整的批量分析能力（复选框 + 批量分析按钮 + 弹窗），可作为交互模式参考。本次需要在「项目合规 - 文件级兼容性 - 风险数据详情」中实现同样的交互模式，并新建项目合规场景专用的批量分析弹窗组件，仅保留项目合规场景需要的表单项：
- 仅包含「分析人」「分析结果」「分析说明」三项表单
- 「分析结果」选项只保留「有风险」「无风险」两项

## What Changes

- 在 `communityList.vue` 的「项目合规」Tab 操作区，将原独立的「导出」按钮与待新增的「导出未确认」按钮合并为一个 `el-dropdown` 组合按钮：外层触发按钮文案为「导出」并带向下箭头，点击展开下拉菜单
  - 下拉项一：「导出当前列表」——点击触发原「导出」逻辑（导出风险数据看板列表全部数据）
  - 下拉项二：「导出未确认」——点击调用新接口导出未确认 + 手动分析数据
  - 每个下拉项文字后挂一个 `<el-tooltip>` 问号图标作为使用提示，分别提示「导出风险数据看板列表全部数据」「导出未确认和已手动分析的数据」
  - 受同一 `canHandle('community_export')` 权限控制；触发按钮 `loading` 取 `exportLoading || exportUnconfirmedLoading`
- 在 `gitUrlList.vue` 的 `projectCompliance` 分支表格新增首列 `type="selection"` 复选框列，支持批量勾选
- 在 `gitUrlList.vue` 的 `projectCompliance` 分支表格新增「分析结果」列，渲染 `manualRiskLevel` 字段，初始值显示「未确认」；新增「分析说明」列，渲染 `manualDescription` 字段
- 在 `gitUrlList.vue` 的 `projectCompliance` 分支顶部操作区新增「批量分析」按钮，受 `canHandle('repo_batch_analysis')` 权限控制，未勾选数据时 disabled
- 新建 `projectComplianceConfirmBox.vue`（路径 `@/views/sca/softInformation/projectComplianceConfirmBox.vue`，组件名 `ProjectComplianceConfirm`）作为「项目合规 - 文件级兼容性」专用的批量分析弹窗：
  - 表单项：分析人、分析结果（2 项）、分析说明
  - 「分析结果」下拉选项固定为 `有风险` / `无风险`
  - 提交调用 `softWareCompent.batchConfirmProject`，成功后关闭弹窗
- 在 `api/scaApi/softWareCompent.js` 中新增两个接口方法（接口已按后端明确实现，命名为 `exportUnconfirmedData` / `batchConfirmProject`）：
  - `exportUnconfirmedData`：导出未确认 + 手动分析数据，复用 `exportActiveParams` 提示组件
  - `batchConfirmProject`：批量确认项目合规文件级兼容性风险数据，复用 `confirm` 接口的请求体结构

## Capabilities

### New Capabilities

- `project-compliance-export-unconfirmed`: 在「项目合规 - 文件级兼容性 - 风险数据看板」导出未确认 + 手动分析数据子集的能力
- `project-compliance-batch-analysis`: 在「项目合规 - 文件级兼容性 - 风险数据详情」批量勾选并执行批量分析的能力，使用独立的 `projectComplianceConfirmBox.vue` 弹窗组件（仅含分析人/分析结果(2项)/分析说明，无审核人、无 tips、无非片段引用展开）

### Modified Capabilities

- `project-compliance-risk-detail-list`: 风险数据详情列表新增复选框列与「分析结果」列，原列表数据展示语义不变

## Impact

- **关联前端变更**：
  - `apps/web-openlibing/src/views/sca/softInformation/communityList.vue` — 将原「导出」按钮与新增「导出未确认」合并为 `el-dropdown` 下拉按钮，新增 `handleExportCommand` 分发方法、下拉项 `<el-tooltip>` 问号提示与对应样式（`.dropdown-item-content` / `.dropdown-tip`）
  - `apps/web-openlibing/src/views/sca/softInformation/gitUrlList.vue` — `projectCompliance` 分支新增复选框列、「分析结果」列、「分析说明」列、「批量分析」按钮及对应方法；`activeName === 'projectCompliance'` 时渲染 `<project-compliance-confirm-box>`（不传 `:isAnalysisOne`）
  - `apps/web-openlibing/src/views/sca/softInformation/projectComplianceConfirmBox.vue` — 新建独立组件（项目合规专用弹窗，仅批量操作）
  - `apps/web-openlibing/src/api/scaApi/softWareCompent.js` — 新增两个 API 方法
- **关联后端契约**：
  - `GET /gateway/openlibing-sca/license/export/unconfirmed`（导出未确认 + 手动分析，query 参数为 `community` / `platform`，后端已明确）
  - `POST /gateway/openlibing-sca/license/manualAnalysis/batch`（批量手动分析，body 为 `[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]`，接口已明确）
- **权限**：新增按钮沿用 `canHandle('community_export')` 和 `canHandle('repo_batch_analysis')` 权限点，不新增权限码
- **数据字段**：列表新增 `manualRiskLevel` / `manualDescription` 字段透传，`manualRiskLevel` 值域 `有风险` / `无风险` / `未确认`（来自后端，前端只渲染不修改）；`objectId` / `file` / `fileHash` 字段从列表数据透传给批量分析接口（来自后端，前端只读）
