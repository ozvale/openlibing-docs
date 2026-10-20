# 静态检查看板全量操作（全量屏蔽/审核/转审/撤销）

## 需求背景

静态检查看板（CodeCheckDashboard）当前支持基于勾选行的批量操作：批量屏蔽、批量审核、批量转审、批量撤销。当缺陷列表条数较多、且需要按当前筛选条件一次性处理整批数据时，逐页勾选提交效率较低，且存在前后端数量不一致风险（其他人在此期间增删了符合条件的数据）。

本次需求在不改变现有批量操作行为的前提下，为上述 4 种操作各新增一种「全量」操作入口：按当前列表查询条件（query）+ 当前列表总数量（count）作为参数提交，由后端按条件批量处理。

## 功能描述

### 做什么

- 在 `codeListComponent.vue` 操作按钮区，为以下 4 种操作各新增一个「全量」按钮：
  - 全量屏蔽（对应「批量屏蔽」）
  - 全量审核（对应「批量审核」）
  - 全量转审（对应「批量转审」）
  - 全量撤销（对应「批量撤销」）
- 全量按钮的显隐权限（`v-if` 条件）与对应批量按钮一致；`disabled` 条件为 `formInline.total === 0`（与提交参数 `count` 同口径，按筛选条件命中的总条数判断，不依赖勾选行，也不受当前页加载行数影响）。
- 全量操作复用原操作接口（`CK_SHIELD_SUBMIT` / `CK_SHIELD_AUDIT` / `CK_SHIELD_REFERRAL` / `CK_SHIELD_REVOKE`）；提交参数相对原操作：
  - 移除 `detailsId` 字段
  - 新增 `query` 对象（当前列表的查询条件，由父组件传入）
  - 新增 `count` 字段（当前列表的总数量，取 `formInline.total`）
- 全量屏蔽 / 全量审核 / 全量转审 复用现有弹窗（输入审核人、屏蔽类型、申请理由、审核意见、是否通过等）；全量撤销复用现有确认框。
- 弹窗中「选中项数量」在全量操作下显示为 `formInline.total`。
- 全量提交具备防重复提交防护：提交期间确认按钮 loading 置灰，重复触发被 `submitting` 标志拦截。
- 后端返回 `code === 409` 表示前端持有的 count 与后端实际可处理数量不一致；前端需主动调用 `this.refresh()` 重置 `pageNum=1` 重新拉取列表数据，并提示用户。

### 不做什么

- 不修改原有 4 种批量操作的接口、参数、行为。
- 不修改后端接口契约（仅在前端请求体上新增 `query`/`count` 字段，由后端兼容识别）。
- 不引入跨页选中状态持久化。
- 不修改批量撤销历史、单条操作逻辑。

## 验收标准

- [ ] 4 个全量按钮在对应 `currentTag` 下显隐正确：
  - 全量屏蔽：`currentTag === 'all' && defectStatus === '0'`
  - 全量审核 / 全量转审：`currentTag === 'myExamine'`
  - 全量撤销：`currentTag === 'myAplication'`
- [ ] 全量按钮在 `formInline.total === 0`（筛选条件无命中数据）时 disabled；`total > 0` 且未勾选任何行、或停留在无数据的末页时，仍可正常点击全量按钮。
- [ ] 全量按钮点击后弹窗 / 确认框正常打开，弹窗中「选中项数量」展示为 `formInline.total`。
- [ ] 提交参数中不含 `detailsId`，包含 `query`（与父组件 `filterLine` 一致）和 `count`（`formInline.total`）。
- [ ] 提交期间确认按钮 loading 置灰且不可重复触发，接口返回后恢复。
- [ ] 提交成功后列表自动 refresh。
- [ ] 后端返回 `code === 409` 时，前端主动调用 `this.refresh()` 重置 `pageNum=1` 重新拉取列表，并给用户错误提示。
- [ ] 原 4 种批量操作行为不受影响。

## 影响范围

- 文件：
  - `apps/web-openlibing/src/views/CodeCheckDashboard/codeListComponent.vue`（主要修改）
  - `apps/web-openlibing/src/views/CodeCheckDashboard/StaticSeverityPage.vue`（仅向子组件透传 `filterLine` prop）
- 模块：CodeCheckDashboard - 静态检查看板
- 接口：无新增后端接口；复用 `CK_SHIELD_SUBMIT` / `CK_SHIELD_AUDIT` / `CK_SHIELD_REFERRAL` / `CK_SHIELD_REVOKE`，请求体新增 `query` / `count` 字段。
