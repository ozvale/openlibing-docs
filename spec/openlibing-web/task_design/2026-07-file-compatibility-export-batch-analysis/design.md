## Context

### 现状链路

「项目合规 - 文件级兼容性」的入口为 `communityList.vue`（看板）→ `gitUrlList.vue`（风险数据详情）。`communityList.vue` 通过 `activeName === 'projectCompliance'` 区分开源片段引用合规与项目合规两个 Tab，渲染不同的表格列与按钮组。

```
componentAnalysis/index.vue
  ├─ activeName === 'projectCompliance' && !chooseBranchObject?.id
  │   └─ communityList.vue (风险数据看板)
  │         └─ 导出按钮 (exportLicenseExcel → exportLicenseData API)
  └─ activeName === 'projectCompliance' && chooseBranchObject?.id
      └─ gitUrlList.vue (风险数据详情)
            ├─ 表格 (无复选框, 无分析结果列)
            └─ 顶部操作区 (combinationCondition, 无批量分析按钮)
```

### 参考实现

「开源片段引用合规 - 风险数据详情」的批量分析能力位于 `PRComponentAnalysis/components/openSourceCompliance/analysisTable.vue`，可作为交互模式参考（复选框 + 批量分析按钮 + 弹窗）。本期项目合规场景不复用其弹窗组件，而是新建独立组件 `projectComplianceConfirmBox.vue`。

### 数据契约

`getScanProjectIssue` 接口返回的数据结构包含：
- `fileName` / `file`：文件名
- `licenseStatus` / `compatible`：兼容性状态
- `licenseRemark` / `licenseDesc`：许可证描述
- `licenses`：许可证列表
- `copyrights` / `localLicenses`：本地许可证
- `manualRiskLevel`：分析结果（有风险/无风险/未确认）
- `manualDescription`：分析说明
- `objectId` / `file` / `fileHash`：用于批量分析接口的字段

`manualRiskLevel`（分析结果）和 `manualDescription`（分析说明）字段已存在于响应中，前端无需新增字段透传，仅需在表格列中渲染即可。`objectId` / `file` / `fileHash` 字段同样来自列表数据，用于批量分析接口的请求体构造。

### 现状瓶颈

1. `gitUrlList.vue` 的 `projectCompliance` 分支表格定义在 `table.columnPro`，仅 2 列（fileName / compatible），缺少复选框列、分析结果列
2. 顶部操作区 `top-right` 仅在 `openSourceCompliance` 分支下显示「批量分析」按钮，`projectCompliance` 分支完全没有该按钮和权限判断
3. `communityList.vue` 的 `projectCompliance` Tab 按钮组只渲染「导出」按钮，缺少「导出未确认」按钮
4. 项目合规场景缺少专用的批量分析弹窗组件，需要新建

## Goals / Non-Goals

**Goals:**

- 「项目合规 - 文件级兼容性 - 风险数据看板」将原独立的「导出」与「导出未确认」两个按钮合并为一个 `el-dropdown` 下拉按钮：外层触发按钮文字为「导出」并带向下箭头，点击展开下拉菜单，内含两个可选项
  - 「导出当前列表」——调 `exportLicenseExcel`（导出风险数据看板列表全部数据）
  - 「导出未确认」——调 `exportUnconfirmedExcel`（导出未确认和已手动分析的数据）
  - 每个下拉项文字后挂一个 `<el-tooltip>` 问号图标作为使用提示
- 「项目合规 - 文件级兼容性 - 风险数据详情」列表新增复选框支持批量勾选
- 「项目合规 - 文件级兼容性 - 风险数据详情」列表新增「分析结果」列，展示 `manualRiskLevel`；新增「分析说明」列，展示 `manualDescription`
- 「项目合规 - 文件级兼容性 - 风险数据详情」顶部新增「批量分析」按钮，未勾选时禁用
- 新建独立的批量分析弹窗组件 `projectComplianceConfirmBox.vue`，仅包含分析人、分析结果（2 项）、分析说明三项表单，分析结果只保留「有风险」「无风险」
- 批量分析接口已明确：`POST /license/manualAnalysis/batch`，请求体为 `[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]`，其中 `objectId` / `file` / `fileHash` 从勾选的行数据中提取
- 仅支持批量操作，不引入单条分析逻辑（移除 `isAnalysisOne` prop）
- 接口已按后端明确实现，无需按合理假设实现，预留调整空间

**Non-Goals:**

- 不修改后端接口（接口已按后端明确实现）
- 不修改权限码（沿用现有 `community_export` / `repo_batch_analysis`）
- 不在本期实现单条分析（详情页「分析」按钮已在 `openSourceCompliance` 分支存在，`projectCompliance` 分支本期不补）
- 不实现列配置（列配置功能仅在 `openSourceCompliance` 分支存在，本期不为 `projectCompliance` 补）
- 不实现单条双击编辑 `manualRiskLevel` 功能（仅开源片段引用合规有 `clarifyType` 双击编辑，本期不为 projectCompliance 补）

## Decisions

### 1. 弹窗组件策略：新建 `projectComplianceConfirmBox.vue` 独立组件

本期为「项目合规 - 文件级兼容性」新建独立组件 `projectComplianceConfirmBox.vue`，路径 `@/views/sca/softInformation/projectComplianceConfirmBox.vue`，组件名 `ProjectComplianceConfirm`。该组件仅服务项目合规场景，不与其他场景共用文件。

组件结构：

- 标题：批量分析
- 表单项：分析人（`form.clarifyAuthor`）、分析结果（`form.manualRiskLevel`，2 项静态选项 `有风险` / `无风险`）、分析说明（wangEditor）
- 不含审核人、不含红色 tip、不含「非片段引用」展开表单、不含「确认结果」二次弹窗与复制审批链接相关逻辑
- 提交时调用 `softWareCompent.batchConfirmProject`（接口已按后端明确实现），成功后关闭弹窗并 `emit('closeBox', true)`
- 根 dialog class：`batch-update-infor dialog-common project-compliance-confirm-box`（隔离样式作用域）

`gitUrlList.vue` 中按 `activeName` 渲染该组件，使用 `v-if="dialogVisible && activeName === 'projectCompliance'"` 控制显示，传入 `:is-batch-status="isBatchStatus"` 并监听 `@closeBox="closeBox"` 事件。

**理由**：独立组件让项目合规场景的弹窗演进只受自身需求驱动，避免与其他场景的弹窗逻辑互相影响。

### 2. 「导出」合并下拉按钮

参考 `analysisTable.vue` 第 145-190 行 `el-dropdown` + `el-dropdown-item` 的组合用法，将原独立的「导出」与「导出未确认」两个按钮合并为一个外层「导出」按钮 + 下拉菜单。

**交互细节**：

- 触发按钮 `loading` 状态取 `exportLoading || exportUnconfirmedLoading`，任一导出动作进行中都会显示加载
- 下拉项文字后挂 `<el-tooltip>` + `<QuestionFilled>` 问号图标，悬停显示该选项的导出口径提示
- `handleExportCommand(command)` 在 methods 中分发：`command === 'exportLicense'` 调 `exportLicenseExcel`，`command === 'exportUnconfirmed'` 调 `exportUnconfirmedExcel`
- `.dropdown-item-content` 使用 `inline-flex` + `gap: 6px` 让文字与问号图标对齐；`.dropdown-tip` 使用与表格头问号一致的 `#9199ab` 灰色
- `ArrowDown` / `QuestionFilled` 通过 Element Plus 全局注册使用，无需新增 import

**理由**：

- 两个按钮语义相近（都是导出），合并后顶部按钮组更紧凑，避免与 `combinationCondition` 筛选器争夺横向空间
- 问号 `tooltip` 让操作前即可看到每个选项的精确语义（导出全部 vs 导出未确认 + 已手动分析），降低误操作概率
- 沿用已存在的 `el-dropdown` 交互模式，无需引入新组件库能力

### 3. 「分析结果」与「分析说明」列渲染

参考 `gitUrlList.vue` 第 392-406 行 `openSourceCompliance` 分支对 `clarifyType` 的渲染方式（仅参考样式，不参考字段名）。

`projectCompliance` 分支的表格定义在 `table.columnPro`（仅 2 列），需要在 `gitUrlList.vue` 的 `table.columnPro` 数组中新增 `manualRiskLevel` 和 `manualDescription` 列，并在表格模板的 `v-else`（即 `projectCompliance` 分支）中渲染。

为 `manualRiskLevel` 列增加专门渲染逻辑，空值显示「未确认」，`manualDescription` 列空值显示「--」。

**不启用双击编辑**：`projectCompliance` 分支不实现双击编辑（见 Non-Goals）。

### 4. 批量分析按钮位置

参考 `gitUrlList.vue` 第 117-125 行 `openSourceCompliance` 分支的按钮组结构。`projectCompliance` 分支当前没有 `top-right` 区域，需要新增。

考虑到 `projectCompliance` 分支的表格上方只有 `combinationCondition2`（兼容性筛选），将批量分析按钮放在筛选条件左侧。

为避免 `openSourceCompliance` 分支按钮重复渲染，需将原 `openSourceCompliance` 分支的 `top-right` 区域用 `v-if="activeName === 'openSourceCompliance'"` 包裹，再 `v-else` 渲染 `projectCompliance` 的按钮组。

### 5. 复选框列与 `handleSelectionChange`

`openSourceCompliance` 分支表格已绑定 `@selection-change="handleSelectionChange"` 并维护 `multipleSelection`，`projectCompliance` 分支表格（第 450-491 行）当前没有这个绑定。需要在 `projectCompliance` 表格上新增：
- 首列增加 `type="selection"` 的复选框列
- 绑定 `@selection-change="handleSelectionChange"` 事件

**复用 `handleSelectionChange` 方法**：两个表格共享同一 `multipleSelection` 状态，无需新增方法。但需要注意两个表格 ref 不同（`multipleTable` vs `singleTable`），`closeBox` 中清理选区时需要分别处理。

### 6. `closeBox` 适配

`gitUrlList.vue` 的 `closeBox` 方法（第 1569-1590 行）当前调用 `this.$refs.multipleTable.clearSelection()`，需要扩展为根据 `activeName` 选择对应的 table ref：

- `openSourceCompliance` 分支使用 `this.$refs.multipleTable`
- `projectCompliance` 分支使用 `this.$refs.singleTable`
- 分别调用 `clearSelection()` 清空选区

### 7. 接口契约

**导出未确认接口**（后端已明确：`GET /license/export/unconfirmed`，参数仅 `community` / `platform`）：
- 路径：`GET /gateway/openlibing-sca/license/export/unconfirmed`
- 参数：`community` / `platform`
- 在 `softWareCompent.js` 中新增 `exportUnconfirmedData` 方法

**批量手动分析接口**（接口已明确：`POST /license/manualAnalysis/batch`）：
- 路径：`POST /gateway/openlibing-sca/license/manualAnalysis/batch`
- 请求体：`[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]`
- 在 `softWareCompent.js` 中新增 `batchConfirmProject` 方法

`projectComplianceConfirmBox.vue` 的 `getConfirmParams` 从 `this.$parent.multipleSelection` 提取 `objectId` / `file` / `fileHash`，并附加 `manualRiskLevel` / `manualDescription`，组装为 `[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]` 后由 `multipleSelectUpdate` 调用 `softWareCompent.batchConfirmProject`。

**待后端明确后调整**：批量手动分析接口已明确，无需调整。导出未确认接口已按后端提供实现：`GET /license/export/unconfirmed`，query 参数为 `community` / `platform`。

### 8. 权限码沿用

- 「导出未确认」按钮：`canHandle('community_export')`（与原「导出」按钮一致）
- 「批量分析」按钮：`canHandle('repo_batch_analysis')`（与 `openSourceCompliance` 分支一致）

**理由**：不新增权限码，避免后端权限配置变更。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 「导出未确认」接口调整可能持续 | URL 和请求体集中在 `softWareCompent.js` 中，后续调整仅需改 1-2 处；当前已与后端对齐：`GET /license/export/unconfirmed`，query 参数 `community` / `platform` |
| 批量手动分析接口请求体依赖 `multipleSelection` 中每行包含 `objectId` / `file` / `fileHash` 字段 | 若后端列表数据未返回这些字段，需补充 `getScanProjectIssue` 的字段透传；当前假定字段已存在 |
| `projectCompliance` 分支新增复选框列后，表格行高与 `openSourceCompliance` 分支不一致 | 复用 `el-table-column type="selection" width="45"`，行高由 Element Plus 自动处理 |
| 「导出」合并为下拉按钮后，触发按钮 `loading` 需要同时反映两个导出动作的进度 | 通过 `exportLoading \|\| exportUnconfirmedLoading` 联合判断；任一动作结束都会重置自身 loading 标志，无需额外计时器 |
| `singleTable` ref 在 `openSourceCompliance` 分支下不存在 | `closeBox` 中通过 `activeName` 判断，未命中分支不调用 `clearSelection` |

## Migration Plan

1. 前端本地修改完成后，开发者自测覆盖以下场景：
   - 「导出」下拉按钮：点击触发按钮展开下拉菜单；下拉项「导出当前列表」「导出未确认」各自能调通对应 API；外层 `loading` 在任一导出动作进行中呈现
   - 下拉项问号 `tooltip`：鼠标悬停时分别显示「导出风险数据看板列表全部数据」与「导出未确认和已手动分析的数据」两条提示
   - 复选框勾选/取消/全选/反选
   - 「分析结果」列展示未确认/有风险/无风险；「分析说明」列展示 `manualDescription`
   - 「批量分析」按钮启用/禁用状态
   - `projectComplianceConfirmBox.vue` 弹窗：仅含分析人/分析结果（2 项）/分析说明、无审核人、无 tip、提交时请求体包含 `[{ objectId, file, fileHash, manualRiskLevel, manualDescription }]`
2. 「导出未确认」接口已对齐后端（`GET /license/export/unconfirmed`，参数 `community` / `platform`），无需再调整
3. 联调通过后进入 PR 阶段

## Open Questions

1. ~~「导出未确认」接口的请求参数与「导出」接口是否一致（`community` / `platform` / `projectId`）？~~——后端已明确：仅 `community` / `platform`，路径 `/license/export/unconfirmed`
2. 「分析结果」列是否需要双击编辑能力？——本期不实现，待用户反馈后补充
3. 「导出未确认」是否需要进度提示组件？——复用 `exportActiveParams`（与原「导出」一致）
