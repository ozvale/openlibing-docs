## Context

### 前端现状

| 项 | 现状 |
|---|---|
| 页面 | `gitUrlList.vue`，Tab `openSourceCompliance` |
| 表格数据 | `table.list`，列配置来自 `analysisTable.config.js` 的 `column` |
| 匹配度列 | `{ label: '匹配度', id: 'matched', width: 85, show: true }`，无 `sortable` |
| 查询方法 | `queryRiskData()` → `softWareCompent.getScanIssue({ data: params })` |
| 分页 | `pagesConfig.pageNo` / `pageSize`，组件 `sca-pagination` |
| 排序 | **未实现**，表格无 `@sort-change` |

### 后端现状（调研结论，供后端 PR 参考）

| 项 | 现状 |
|---|---|
| 接口 | `POST /open/scan/scanIssue/query` |
| 请求 DTO | `ScanIssueQueryVO`：含 `pageNo`、`pageSize` 及筛选字段，**无排序字段** |
| 数据层 | MongoDB 集合 `scan_issue`，`MongoTemplate` 查询 |
| 当前排序 | 硬编码 `Sort.by(Sort.Order.asc("scanFile"))`（`OpenScanServiceImpl` 约 1116 行） |
| 匹配度字段 | Mongo/VO 均为 `matched`，值如 `"90%"`、`"100%"` |
| 参考实现 | `/open/scan/repos` 使用 `sortColumn` + `sortOrder`（`ascending`/`descending`）+ 白名单枚举 |

### 项目内前端排序惯例

`communityList.vue` 为 SCA 服务端排序标准范式：

1. 列配置 `sortable: 'custom'`
2. 状态 `sortParams: { sortColumn, sortOrder }`
3. `@sort-change` → 去重 → 更新状态 → `pageNo = 1` → 重新查询
4. 请求参数附带 `sortColumn`、`sortOrder`（Element Plus 原值，不做 ASC/DESC 转换）

## Goals / Non-Goals

**Goals:**

- 用户点击「匹配度」列头可升序/降序/取消排序
- 排序作用于**全量分页数据**（依赖后端）
- 与 `communityList.vue` 参数命名和交互一致，降低维护成本
- 前端改造可独立合入，后端就绪后联调即可

**Non-Goals:**

- 本次不实现后端 Mongo 排序逻辑
- 不扩展其他列（供应商、组件名称等）排序，但列配置结构预留 `sortable`
- 不涉及 `projectCompliance` Tab
- 不改变 `matched` 列的展示格式（仍为 `"90%"` 字符串）

## Decisions

### 1. 排序参数命名：沿用 `sortColumn` + `sortOrder`

**选择**：与 `communityList` / `ScanCommunityReq` 保持一致，传 Element Plus 的 `prop` 与 `order` 原值。

**备选**：`sortField` + `sortType`（`ASC`/`DESC`，如 `integrationEfficiency.vue`）——与 SCA scan 模块不一致，弃用。

```javascript
// queryRiskData 中追加（有值才传）
if (this.sortParams.sortColumn && this.sortParams.sortOrder) {
  params.sortColumn = this.sortParams.sortColumn;
  params.sortOrder = this.sortParams.sortOrder;
}
```

### 2. 仅 `matched` 列启用排序

**选择**：在 `analysisTable.config.js` 为 `matched` 增加 `sortable: 'custom'`；表格列绑定 `:sortable="column.sortable"`。

**原因**：需求明确为匹配度；其他列后端尚未支持，避免 UI 可点但接口无效。

### 3. 默认排序：不传参，保持后端行为

**选择**：`sortParams` 初始为空 `{ sortColumn: '', sortOrder: '' }`，不设 `:default-sort`。

**原因**：后端当前默认 `scanFile ASC`；产品未要求进入页面即按匹配度排序。用户首次点击列头才触发排序请求。

**备选**：默认 `matched descending`——需与产品确认，且后端未就绪时行为不确定。

### 4. 排序状态生命周期

| 操作 | 行为 |
|---|---|
| 点击列头排序 | 更新 `sortParams`，`pageNo = 1`，`queryRiskData()` |
| 翻页 / 改 pageSize | 保留 `sortParams`，仅 `queryRiskData()` |
| 筛选条件变更（`updateCondition`） | 保留 `sortParams`（与 communityList 筛选+排序共存一致），`pageNo = 1` |
| 切换代码仓 / scanId | **重置** `sortParams`（新数据集） |
| 切换 Tab | 不污染另一 Tab 的查询参数 |

### 5. 改动文件与代码结构

```
analysisTable.config.js
  └── matched 列增加 sortable: 'custom'

gitUrlList.vue
  ├── data: sortParams + DEFAULT_SORT_PARAMS 常量
  ├── el-table: @sort-change="handleCustomSort"（仅 openSourceCompliance 表）
  ├── el-table-column: :sortable="column.sortable"
  ├── methods: handleCustomSort（参考 communityList）
  ├── queryRiskData: 附加 sortColumn/sortOrder
  └── 切换 scanId 时 resetSortParams()
```

### 6. `handleCustomSort` 实现要点

```javascript
handleCustomSort({ prop, order }) {
  // 本期仅 matched 列走服务端排序，其他列忽略
  if (prop !== 'matched') return;

  const nextColumn = order ? prop : '';
  const nextOrder = order || '';
  if (
    this.sortParams.sortColumn === nextColumn &&
    this.sortParams.sortOrder === nextOrder
  ) {
    return;
  }
  this.sortParams = order
    ? { sortColumn: prop, sortOrder: order }
    : { sortColumn: '', sortOrder: '' };
  this.pagesConfig.pageNo = 1;
  this.queryRiskData();
}
```

### 7. 后端对接约定（供后续 PR）

前端将传递：

| 字段 | 示例 | 说明 |
|---|---|---|
| `sortColumn` | `"matched"` | 与列 `prop` / VO 字段一致 |
| `sortOrder` | `"ascending"` / `"descending"` | Element Plus 约定 |

后端需：

1. `ScanIssueQueryVO` 新增 `sortColumn`、`sortOrder`
2. 白名单校验（至少含 `matched` → Mongo 字段 `matched`）
3. `matched` 按数值排序（去 `%` 解析，可参考 `FileUtil.getMatchedScore`）
4. 无排序参数时保持 `scanFile ASC`
5. 排序必须在 Mongo `skip/limit` **之前**执行，否则分页结果错误

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| 后端未就绪时点击排序无效或报错 | 前端先合入；联调前可 mock 或 feature flag；接口失败时 `$message.error` 已有 |
| 仅 matched 可排序，用户可能误点其他列 | 其他列不设 `sortable`；`handleCustomSort` 对非 matched 直接 return |
| 取消排序回退到 scanFile ASC，用户可能无感知 | 符合后端默认行为；可在帮助文案中说明（非必须） |
| 合并单元格 `arraySpanMethod` 与排序共存 | 当前 openSourceCompliance 表使用 span-method；需联调确认排序后合并逻辑是否仍正确 |

## Migration Plan

1. **Phase 1（本次）**：前端合入，排序参数透传，UI 可交互
2. **Phase 2（后端）**：`openlibing-sca` 实现 Mongo 动态排序
3. **Phase 3（联调）**：大数据量 scanId 下验证升序/降序/取消/翻页/筛选组合
4. **回滚**：前端移除 `sortParams` 传参即可恢复现状，无数据迁移

## Open Questions

1. 产品是否要求进入页面默认按匹配度降序？当前方案为「用户触发才排序」。
2. 排序后 `arraySpanMethod` 合并行是否需调整？需联调时确认。
3. 后续是否扩展更多可排序列（如 `type`、`vendor`）？可在后端白名单一次性规划。
