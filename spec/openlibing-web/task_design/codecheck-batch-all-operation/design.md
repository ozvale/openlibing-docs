# 技术设计

## 数据流

```text
StaticSeverityPage.vue
  └── filterLine (查询条件对象，含 pageNum/pageSize/defectLevel/...)
        │  通过 prop 透传
        ▼
codeListComponent.vue
  ├── prop filterLine          → 全量操作时作为 query 提交
  ├── prop formInline.total    → 作为 count 提交
  ├── data.operation           → '全量屏蔽' / '全量审核' / '全量转审' / '全量撤销'
  └── batchOperationAll(op)    → 分发到弹窗 / 确认框
        ├── 屏蔽/审核/转审 → dialogStatusVisible=true（复用 MajunDialog）
        └── 撤销         → confirmReturn（无 id 参数走全量分支）
```

## 提交参数对比

| 操作 | 批量参数                                                                                   | 全量参数                                                                                      |
| ---- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| 屏蔽 | `{ userId, user, shieldType, reason, type, detailsId, solutionTime, repoUrl, notifyType }` | `{ userId, user, shieldType, reason, type, query, count, solutionTime, repoUrl, notifyType }` |
| 审核 | `{ auditResult, type, detailsId, projectName, projectId, auditOpinion, solutionTime }`     | `{ auditResult, type, query, count, projectName, projectId, auditOpinion, solutionTime }`     |
| 转审 | `{ userId, user, type, detailsId, notifyType }`                                            | `{ userId, user, type, query, count, notifyType }`                                            |
| 撤销 | `{ type, detailsId }`                                                                      | `{ type, query, count }`                                                                      |

`query` 即父组件 `filterLine` 的浅拷贝；`count` 取 `formInline.total`。

## 全量态分发（基于 mode 标志）

`mode` 已有三态：`batchOperation` 设置 `'batch'`、`batchOperationAll` 设置 `'all'`、`singleOperation` 设置 `'single'`。全量态的分发以统一的 `mode === 'all'` 标志为依据，**不在各 operation 字符串判断中逐处 OR 追加**：

```js
// 计算属性：全量态标志
isAllMode() {
  return this.mode === 'all';
}
```

- 弹窗模板中「是否展示批量明细」「是否走全量参数」等分支，统一用 `isAllMode`（或 `isAllOperation(operation)` 辅助方法）判断，不再写成 `operation === '批量审核' || operation === '审核' || operation === '全量审核'` 这类逐个追加的 OR 链。
- operation 字符串仅用于区分**具体操作类型**（屏蔽 / 审核 / 转审 / 撤销），不承担「是否全量」的分发职责；每新增一个全量操作只需在 `batchOperationAll` 的 switch 中加一个 case，无需同步修改其他分支判断。

新增 4 个 operation 常量（字符串），与原批量 operation 区分：

| operation  | 复用弹窗分支                         | 复用确认框                             |
| ---------- | ------------------------------------ | -------------------------------------- |
| `全量屏蔽` | 是（与 `批量屏蔽` 同一弹窗模板分支） | 否                                     |
| `全量审核` | 是（与 `批量审核` 同一弹窗模板分支） | 否                                     |
| `全量转审` | 是（与 `批量转审` 同一弹窗模板分支） | 否                                     |
| `全量撤销` | 否                                   | 是（与 `批量撤销` 同一 confirmReturn） |

## 全量按钮 disabled 口径

全量按钮的 `disabled` 与提交参数 `count` 必须同口径，均以 `formInline.total`（当前筛选条件命中的总条数）为准：

```html
<el-button
  v-if="..."
  :disabled="formInline.total === 0"
  @click="batchOperationAll('全量屏蔽')"
></el-button>
```

- 批量按钮 disabled 用 `selects.length === 0`（依赖勾选行）；全量按钮 disabled 用 `formInline.total === 0`（不依赖勾选行）。
- 不用 `formInline.codeList.length === 0`（当前页已加载行数）作为全量按钮 disabled 条件：当筛选条件命中多页数据、但用户停留在已无数据的末页时，`codeList.length === 0` 会误禁用按钮，与「列表有数据（total > 0）即可全量操作」的语义不符。

## 防重复提交

全量操作直接作用于整批数据，重复提交影响面大，提交期间必须防护：

- 新增 data 标志 `submitting: false`。
- 全量提交入口（`sureSubmit` 的全量 case、`confirmReturn` 的全量分支）先守卫再置位：

```js
if (this.submitting) return;
this.submitting = true;
try {
  // 提交逻辑
} finally {
  this.submitting = false;
}
```

- 弹窗确认按钮 / 确认框提交按钮设置 `:disabled="submitting"`、`:loading="submitting"`，接口返回前按钮置灰不可再点。

## 409 处理

各接口在 `try/catch` 之外基于返回的 `code` 判断：

```js
const res = await apiClientInstant.post(CK_SHIELD_AUDIT, { data });
if (res?.code === 409) {
  this.$message.warning("列表数据已变化，已自动刷新");
  this.refresh();
  this.dialogStatusVisible = false;
  return;
}
```

- `applyShield` 走 `staticCheck.js` 包装，返回的 Promise resolve 值即后端响应体；按相同方式判断。
- `confirmReturn` 内 `apiClientInstant.post(...).then((res) => { if (res.code === 409) ... })` 同样处理。

## 弹窗「选中项数量」展示

新增计算属性：

```js
displayDataCount() {
  return this.isAllOperation(this.operation)
    ? this.formInline?.total ?? 0
    : this.dialogForm.data.length;
}
```

模板中 `{{ dialogForm.data.length }}` 替换为 `{{ displayDataCount }}`。

## 兼容性

- 不修改原 `批量屏蔽/审核/转审/撤销` 分支；模板与提交分支以 `isAllMode` / `isAllOperation` 统一判断是否全量，不逐处 OR 追加 operation 字符串。
- `isCopyLinkOperation` 暂不扩展到全量操作（全量屏蔽/转审的「复制审核链接」依赖选中项 detailsId，全量模式下无 detailsId， prefetchApprovalLink 在全量模式下不调用即可）。
- 父组件 `filterLine` 字段含 `date: null` 等空值，传给后端时直接浅拷贝原样传递（与列表查询时一致）。
