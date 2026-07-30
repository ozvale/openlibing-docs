## 1. API 层

- [x] 1.1 在 `apps/web-openlibing/src/api/scaApi/softWareCompent.js` 新增 `exportUnconfirmedData` 方法，GET `/gateway/openlibing-sca/license/export/unconfirmed`，参数为 `community` / `platform`（已按后端明确接口对齐）

- [x] 1.2 在 `apps/web-openlibing/src/api/scaApi/softWareCompent.js` 新增 `batchConfirmProject` 方法，POST `/gateway/openlibing-sca/license/manualAnalysis/batch`，请求体为 `[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]`

## 2. 看板列表「导出」合并下拉按钮

- [ ] 2.1 在 `communityList.vue` 的 `projectCompliance` Tab 按钮组（第 37-51 行附近）将原「导出」与「导出未确认」两个按钮合并为一个 `el-dropdown`：外层 `el-button type="primary"` 文字为「导出」并带 `el-icon ArrowDown`，`v-if="canHandle('community_export')"` 受同一权限控制

- [ ] 2.2 `el-dropdown` 内提供两个 `el-dropdown-item`：第一个 `command="exportLicense"` 文字为「导出当前列表」；第二个 `command="exportUnconfirmed"` 文字为「导出未确认」。每个 `el-dropdown-item` 内 `span.dropdown-item-content` 包裹文字与 `<el-tooltip effect="dark" placement="top">`，提示文案分别为「导出风险数据看板列表全部数据」「导出未确认和已手动分析的数据」，tooltip 内挂 `el-icon el-icon-question dropdown-tip` + `QuestionFilled` 问号图标

- [ ] 2.3 触发按钮 `:loading` 绑定 `exportLoading || exportUnconfirmedLoading`，任一导出动作进行中都呈现加载

- [ ] 2.4 在 `communityList.vue` 的 `<style scoped>` 新增 `.dropdown-item-content`（`display: inline-flex` + `gap: 6px`）与 `.dropdown-tip`（`color: #9199ab`、`cursor: help`）样式

- [ ] 2.5 在 `communityList.vue` 的 `data` 中确认存在 `exportLoading: false` 与 `exportUnconfirmedLoading: false` 两个 loading 状态

- [ ] 2.6 在 `communityList.vue` 的 `methods` 中保留 `exportLicenseExcel`（调用 `softWareCompent.exportLicenseData`）与新增 `exportUnconfirmedExcel`（调用 `softWareCompent.exportUnconfirmedData`），两者成功都触发 `exportActiveParams.status = true`，失败都 `$message.error`

- [ ] 2.7 在 `communityList.vue` 的 `methods` 中新增 `handleExportCommand(command)` 分发方法：`command === 'exportLicense'` 时调 `exportLicenseExcel`，`command === 'exportUnconfirmed'` 时调 `exportUnconfirmedExcel`

- [ ] 2.8 `ArrowDown` / `QuestionFilled` 通过 Element Plus 全局注册使用，无需新增 import（与 [analysisTable.vue:158](openlibing-web/apps/web-openlibing/src/views/sca/PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue#L158) 一致）

## 3. 风险数据详情列表改造

- [x] 3.1 在 `gitUrlList.vue` 的 `table.columnPro` 数组新增列定义：`{ label: '分析结果', id: 'manualRiskLevel', show: true }`、`{ label: '分析说明', id: 'manualDescription', show: true }`

- [ ] 3.2 在 `gitUrlList.vue` 的 `projectCompliance` 分支表格（第 450-491 行）首列新增 `<el-table-column type="selection" width="45" />`，并在 `<el-table>` 标签上添加 `@selection-change="handleSelectionChange"`

- [x] 3.3 在 `gitUrlList.vue` 的 `projectCompliance` 分支表格模板中为 `manualRiskLevel` 列新增渲染分支：`<span v-else-if="column.id === 'manualRiskLevel'">{{ scope.row[column.id] || '未确认' }}</span>`，不启用双击编辑

## 4. 批量分析按钮

- [ ] 4.1 在 `gitUrlList.vue` 的 `projectCompliance` 分支顶部操作区新增 `top-right` 容器，包含「批量分析」按钮和原 `combinationCondition2` 筛选条件，按钮受 `canHandle('repo_batch_analysis')` 控制，未勾选时 `:disabled="!batchUpdateStatus"`

- [ ] 4.2 将原 `openSourceCompliance` 分支的 `top-right` 容器用 `v-if="activeName === 'openSourceCompliance'"` 包裹，原 `projectCompliance` 的筛选条件用 `v-else` 渲染到新的 `top-right` 容器中，避免按钮重复

- [ ] 4.3 在 `gitUrlList.vue` 的 `methods` 中 `openBox` 方法已被 `openSourceCompliance` 分支使用，`projectCompliance` 分支复用该方法（设置 `isBatchStatus = true`、`dialogVisible = true`），项目合规专用弹窗组件不再接收 `isAnalysisOne` prop

## 5. 批量分析弹窗组件

- [x] 5.1 在 `apps/web-openlibing/src/views/sca/softInformation/` 新建 `projectComplianceConfirmBox.vue`，组件名 `ProjectComplianceConfirm`，根 dialog class 含 `project-compliance-confirm-box` 用于样式隔离

- [x] 5.2 在 `projectComplianceConfirmBox.vue` 的 `data.options` 中静态固定为 2 项：`有风险` / `无风险`（无需 computed）

- [x] 5.3 在 `projectComplianceConfirmBox.vue` 模板中**不包含**「审核人」表单项、红色 `tip` 提示块、「非片段引用」展开的确认类型/软件名称/软件版本表单项

- [x] 5.4 在 `projectComplianceConfirmBox.vue` 的 `data.rules` 中**不包含** `committers` / `type` / `softwareName` / `softwareVersion` 校验规则，仅保留 `manualRiskLevel` / `clarifyAuthor` / `manualDescription`

- [x] 5.5 在 `projectComplianceConfirmBox.vue` 中**不引入** `selectGetCommitter` / `mapCommitterList`，**不定义** `queryBranchCommiter` 方法，`mounted` 中不调用 committers 加载

- [x] 5.6 在 `projectComplianceConfirmBox.vue` 中**不包含**「确认结果」二次弹窗相关代码：移除 `isShowTipInfor` / `tipListData` / `adjustTipListData` / `closeTipDialog` / `copyLink` / `copyPath` / `Empty` 组件引入及对应模板分支与样式

- [x] 5.7 在 `projectComplianceConfirmBox.vue` 中**移除** `isAnalysisOne` / `isPersonal` / `isRepaired` props 及对应模板分支（`v-show="isRepaired"` 提示块、`v-if="!isShowTipInfor"` 包装等），标题固定为「批量分析」

- [x] 5.8 在 `projectComplianceConfirmBox.vue` 的 `form` 中字段命名为 `manualRiskLevel` / `manualDescription`，`mounted` 中回填逻辑改为读取 `multipleSelection[0].manualRiskLevel` / `multipleSelection[0].manualDescription`

- [x] 5.9 在 `projectComplianceConfirmBox.vue` 的 `getConfirmParams` 方法中，从 `this.$parent.multipleSelection` 提取每行的 `objectId` / `file` / `fileHash`，附加 `manualRiskLevel` / `manualDescription`，组装为 `[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]` 返回

- [x] 5.10 在 `projectComplianceConfirmBox.vue` 的 `multipleSelectUpdate` 方法中调用 `softWareCompent.batchConfirmProject`，成功后 `emit('closeBox', true)`

- [x] 5.11 在 `gitUrlList.vue` 的 `<script>` 中 import 新组件 `projectComplianceConfirmBox`，在 `components` 中注册

- [x] 5.12 在 `gitUrlList.vue` 模板中新增项目合规专用弹窗组件，使用 `v-if="dialogVisible && activeName === 'projectCompliance'"` 控制显示（不传 `:isAnalysisOne` / `:is-repaired` / `:nodes-path`）

## 6. closeBox 适配

- [ ] 6.1 在 `gitUrlList.vue` 的 `closeBox` 方法中根据 `activeName` 选择 table ref：`openSourceCompliance` 用 `this.$refs.multipleTable`，`projectCompliance` 用 `this.$refs.singleTable`，分别调用 `clearSelection`

## 7. 自测验证

- [ ] 7.1 「项目合规 - 文件级兼容性 - 风险数据看板」验证：操作区只有一个「导出」触发按钮（带向下箭头），点击展开下拉菜单
  - 下拉项「导出当前列表」点击调用 `exportLicenseExcel`、调用 `exportLicenseData` 接口
  - 下拉项「导出未确认」点击调用 `exportUnconfirmedExcel`、调用 `exportUnconfirmedData` 接口
  - 每个下拉项文字后的问号图标悬停时显示对应 `tooltip` 文案
  - 任一导出动作进行中触发按钮呈现 loading
  - 权限不足时整个 `el-dropdown` 不渲染

- [ ] 7.2 「项目合规 - 文件级兼容性 - 风险数据详情」验证：列表首列为复选框，可勾选/取消/全选，「分析结果」列展示 `manualRiskLevel`（空值显示「未确认」），「分析说明」列展示 `manualDescription`

- [ ] 7.3 「批量分析」按钮验证：未勾选时 disabled，勾选后可点击，弹窗弹出

- [ ] 7.4 弹窗验证：`projectComplianceConfirmBox.vue` 仅含「分析人」「分析结果」「分析说明」三项表单，分析结果选项仅 2 项（有风险/无风险），无「审核人」、无红色 tip、无「确认结果」二次弹窗

- [ ] 7.5 提交验证：填入分析人和分析说明后点确定，调用 `batchConfirmProject` 接口（`POST /license/manualAnalysis/batch`），请求体为 `[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]`，成功后弹窗关闭、列表刷新、复选框清空
