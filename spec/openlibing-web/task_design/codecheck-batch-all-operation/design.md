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

## operation 命名

新增 4 个 operation 常量（字符串），与原批量 operation 区分：

| operation  | 复用弹窗分支                         | 复用确认框                             |
| ---------- | ------------------------------------ | -------------------------------------- |
| `全量屏蔽` | 是（与 `批量屏蔽` 同一弹窗模板分支） | 否                                     |
| `全量审核` | 是（与 `批量审核` 同一弹窗模板分支） | 否                                     |
| `全量转审` | 是（与 `批量转审` 同一弹窗模板分支） | 否                                     |
| `全量撤销` | 否                                   | 是（与 `批量撤销` 同一 confirmReturn） |

为减少模板分支改动，将 `operation === '批量审核' || operation === '审核'` 这类判断扩展为 `operation === '批量审核' || operation === '审核' || operation === '全量审核'`，其他分支同理。

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

- 不修改原 `批量屏蔽/审核/转审/撤销` 分支，仅在分支判断中 OR 新增 operation 常量。
- `isCopyLinkOperation` 暂不扩展到全量操作（全量屏蔽/转审的「复制审核链接」依赖选中项 detailsId，全量模式下无 detailsId， prefetchApprovalLink 在全量模式下不调用即可）。
- 父组件 `filterLine` 字段含 `date: null` 等空值，传给后端时直接浅拷贝原样传递（与列表查询时一致）。
