# 实现任务

## Task 1: 父组件透传 filterLine

**文件**: `apps/web-openlibing/src/views/CodeCheckDashboard/StaticSeverityPage.vue`

- [ ] 在 `<code-list-component>` 标签上新增 `:filterLine="filterLine"` prop 绑定

## Task 2: 子组件新增 filterLine prop

**文件**: `apps/web-openlibing/src/views/CodeCheckDashboard/codeListComponent.vue`

- [ ] `props` 新增 `filterLine: { type: Object, default: () => ({}) }`
- [ ] 新增计算属性 `displayDataCount`：全量操作返回 `formInline.total`，否则返回 `dialogForm.data.length`
- [ ] 新增辅助方法 `isAllOperation(op)`：判断 op 是否为 4 个全量 operation 之一

## Task 3: 子组件 template 新增 4 个全量按钮

**文件**: `apps/web-openlibing/src/views/CodeCheckDashboard/codeListComponent.vue`

- [ ] 在「批量屏蔽」按钮后新增「全量屏蔽」按钮，v-if 同「批量屏蔽」，disabled=`formInline.codeList.length === 0`，点击 `batchOperationAll('全量屏蔽')`
- [ ] 在「批量审核」按钮后新增「全量审核」按钮，v-if 同「批量审核」
- [ ] 在「批量转审」按钮后新增「全量转审」按钮，v-if 同「批量转审」
- [ ] 在「批量撤销」按钮后新增「全量撤销」按钮，v-if 同「批量撤销」

## Task 4: 子组件新增 batchOperationAll 方法

**文件**: `apps/web-openlibing/src/views/CodeCheckDashboard/codeListComponent.vue`

- [ ] 新增 `batchOperationAll(operation)`：
  - 设置 `this.mode = 'all'`、`this.operation = operation`、`this.dialogForm.data = []`
  - 屏蔽 / 审核 / 转审：调用 `getReviewer()` 或 `getReferralReviewer()`，打开 `dialogStatusVisible = true`（注意：不调用 `prefetchApprovalLink`，因无 detailsId）
  - 撤销：调用 `confirmReturn()`（无 id 参数，走全量分支）

## Task 5: 子组件 sureSubmit 增加全量分支

**文件**: `apps/web-openlibing/src/views/CodeCheckDashboard/codeListComponent.vue`

- [ ] `case` 中新增 `全量屏蔽`、`全量审核`、`全量转审` 分支，调用同一接口，参数带 `query + count`：
  - 屏蔽：`applyShield(this.getAllSubmitParam('apply'))`
  - 审核：`apiClientInstant.post(CK_SHIELD_AUDIT, { data: this.getAllSubmitParam('examine') })`
  - 转审：`apiClientInstant.post(CK_SHIELD_REFERRAL, { data: this.getAllSubmitParam('switch') })`
- [ ] 新增 `getAllSubmitParam(type)` 方法：复用 `getSubmitParam(type)` 思路，但用 `query + count` 替换 `detailsId`
- [ ] 接收返回值后判断 `res.code === 409`，若是则 `this.$message.warning(...)` + `this.refresh()` + 关闭弹窗

## Task 6: 子组件 confirmReturn 增加全量撤销分支

**文件**: `apps/web-openlibing/src/views/CodeCheckDashboard/codeListComponent.vue`

- [ ] `confirmReturn(id)` 增加无 id 入参的全量分支：基于 `this.operation === '全量撤销'` 判断
- [ ] 全量分支提交参数：`{ type, query: { ...this.filterLine }, count: this.formInline.total }`
- [ ] `.then((res) => { ... })` 内判断 `res.code === 409`：若是则 `this.$message.warning(...)` + `this.refresh()`

## Task 7: 弹窗模板分支兼容全量 operation

**文件**: `apps/web-openlibing/src/views/CodeCheckDashboard/codeListComponent.vue`

- [ ] 「选中项数量」展示从 `dialogForm.data.length` 改为 `displayDataCount`
- [ ] `operation === '批量审核' || operation === '审核'` 扩展为同时包含 `'全量审核'`
- [ ] `operation === '批量转审' || operation === '转审'` 扩展为同时包含 `'全量转审'`
- [ ] `else`（屏蔽类弹窗分支）天然兼容 `'全量屏蔽'`

## Task 8: 自检与验证

- [ ] 运行 `pnpm lint` 确保无新增 ESLint error/warn
- [ ] 运行 `pnpm check:type` 确保无类型错误
- [ ] 手动验证：4 个全量按钮显隐、disabled、提交参数、409 刷新行为
