## Context

`communityList.vue` 在同一组件内维护两个 Tab 表格：

| Tab | 表格数据 | API | 任务状态字段 |
|-----|---------|-----|-------------|
| `openSourceCompliance` | `table.column` | `open/scan/repos` | `scanResult`（`1`/`-1`/`0`）— 已接入筛选 |
| `projectCompliance` | `table.projectColumn` | `license/repos` | `repoResult` → 前端映射为 `scanResult`（`success`/`fail`） |

`projectCompliance` 表格（约 242–354 行）当前问题：

1. **无表头筛选**：`projectColumn` 中 `scanResult` 列未配置 `filterAble`，模板无 `#header` 插槽
2. **客户端排序**：`scanTime`、`fileNum` 及嵌套三列使用 `sortable: true`，仅排序当前页；表格无 `@sort-change`
3. **值域不一致**：单元格模板用 `'success'`/`'fail'` 判断样式，但 `showCause` 仍判断 `!== '-1'`（沿用 openSource 逻辑）
4. **参数未透传**：`initQueryData` 的 `projectCompliance` 分支不传 `sortColumn`/`sortOrder`/`repoResult`

同文件 `openSourceCompliance` 已实现目标模式（`filterDropdown` + `sortable: 'custom'` + `handleCustomSort` + `tableFilters`），可作为直接参考。

后端 `license/repos`（`LicenseServiceImpl.getScanByCommunity`）当前固定按 `repository` 中文排序后内存分页，**不支持** `repoResult` 筛选与 `sortColumn`/`sortOrder`。本设计按用户要求仅改前端，定义与 openSource Tab 对齐的参数契约供后续后端扩展。

## Goals / Non-Goals

**Goals:**

- 在 `projectCompliance` 表格「任务状态」列表头提供多选筛选 UI（成功 / 失败）
- 筛选确认后带 `repoResult` 参数重新请求 `license/repos`，`pageNo` 重置为 1
- 将主表及嵌套可排序列改为 `sortable: 'custom'`，排序变更触发服务端重新请求
- 切换社区/平台/代码仓/Tab 时清空筛选、排序状态并重建 filterDropdown
- 统一 `projectCompliance` 任务状态展示与交互的值域（`success`/`fail`）

**Non-Goals:**

- 不修改 `openSourceCompliance` 表格（已由 `community-list-task-status-filter` 完成）
- 不修改 `openlibing-sca` 后端
- 不抽取通用表格组件
- 不为其他列（代码仓、平台等）增加表头筛选
- 不增加「执行中」筛选项（`repo_result` 值域仅 `success`/`fail`，见 `ResultType` 枚举）

## Decisions

### 1. 复用同文件 openSource 模式，而非引入 publishTable

**选择**：在 `projectCompliance` 的 `el-table-column` `v-for` 与嵌套列中直接接入 `filterDropdown` 与 `sortable: 'custom'`。

**理由**：`filterDropdown`、`tableFilters`、`handleTableFilter`、`filterResetKey` 已在同组件实现；改动最小、行为一致。

**备选**：抽取 `scaTable` 封装——超出本次范围。

### 2. 筛选项值域使用 `success`/`fail`，查询参数名为 `repoResult`

`projectCompliance` 后端字段为 `repoResult`（`TblScan.repo_result`），枚举值为 `success`/`fail`（`ResultType`），与 openSource 的 `1`/`-1`/`0` 不同。

```javascript
// projectColumn scanResult 列
filters: [
  { label: '成功', value: 'success' },
  { label: '失败', value: 'fail' },
],
name: 'repoResult',  // tableFilters key 与 API 参数名
```

`initQueryData` projectCompliance 分支合并：

```javascript
const repoResultFilter = this.tableFilters.repoResult;
if (repoResultFilter?.length) {
  params.repoResult = repoResultFilter.join(',');
}
```

**备选**：沿用 `scanResult` 参数名——与后端 `LicenseInfoVO.repoResult` 字段不一致，联调易混淆。

### 3. 服务端自定义排序参数与 openSource 对齐

- 主表列：`scanTime`、`fileNum` 的 `sortable` 改为 `'custom'`
- 嵌套列：`compatibilityNumber`、`incompatibleNumber`、`unrecognizedNumber` 改为 `'custom'`
- `projectCompliance` 表格增加 `ref="projectComplianceTable"`、`@sort-change="handleCustomSort"`
- `handleCustomSort` 复用现有实现（写 `sortParams`，调用 `initQueryData`）
- `initQueryData` projectCompliance 分支追加：

```javascript
if (this.sortParams.sortColumn) {
  params.sortColumn = this.sortParams.sortColumn;
  params.sortOrder = this.sortParams.sortOrder;
}
```

`sortOrder` 沿用 Element Plus 原值：`ascending` / `descending`（与 openSource 一致）。

**排序字段白名单（前端约定，供后端实现参考）**：

| sortColumn | 含义 |
|------------|------|
| `scanTime` | 最新扫描时间（映射自 `licenseCreateTime`） |
| `fileNum` | 文件总数 |
| `compatibilityNumber` | 合规数 |
| `incompatibleNumber` | 未确认数 |
| `unrecognizedNumber` | 未识别数 |

### 4. 筛选与排序状态按 Tab 隔离

`tableFilters` 与 `sortParams` 两 Tab 共用同一对象。切换 `activeName` 时 `resetQueryContext()` 已清空二者；`projectCompliance` 筛选使用 `tableFilters.repoResult`，openSource 使用 `tableFilters.scanResult`，互不冲突。

`resetQueryContext` 扩展：除 `openSourceTable.clearSort()` 外，增加 `projectComplianceTable?.clearSort()`。

### 5. 修正任务状态单元格与 showCause 值域

`projectCompliance` 模板中 `showCause` 失败判断改为 `scope.scanResult === 'fail'`（或通过 `column.id === 'scanResult'` 分支内判断 `fail`）。

`statusMap` 对 projectCompliance 需补充 `success`/`fail` 映射，或在单元格渲染分支直接使用 `ResultType` 对应中文，避免 `statusMap['success']` 显示 `--`。

推荐在 `statusMap` 扩展：

```javascript
statusMap: {
  1: '成功', '-1': '失败', 0: '执行中',  // openSource
  success: '成功', fail: '失败',           // projectCompliance
}
```

### 6. 不实现 `@get-options`

任务状态为固定枚举，静态 `filters` 即可，与 openSource Tab 一致。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 后端 `license/repos` 尚未支持 `repoResult`/`sortColumn`，筛选排序无效 | 前端先完成 UI 与参数透传；tasks 中标注联调前置；spec 固定参数契约 |
| `repoResult` 与 `scanResult` 参数名并存，维护者混淆 | design/spec 明确两 Tab 参数差异；`name: 'repoResult'` 仅用于 projectCompliance |
| 嵌套列 `sort-change` 的 `prop` 与后端字段映射 | 透传 Element Plus 的 `prop` 值；后端按白名单实现 |
| 筛选后 `total` 是否应为过滤后总数 | 与 openSource 一致，默认由后端筛选后更新 `total`；前端不做客户端过滤 |
| 共用 `handleCustomSort` 对两 Tab 均生效 | 切换 Tab 时 `resetQueryContext` 清空 `sortParams`；各 Tab 独立触发 `initQueryData` |

## Migration Plan

1. 前端发版后即具备表头筛选 UI 与服务端排序参数透传
2. 后端扩展 `ScanCommunityDto` + `LicenseServiceImpl` 后联调验证
3. 回滚：移除 `projectColumn` 的 `filterAble` 配置、恢复 `sortable: true`、删除参数合并逻辑

## Open Questions

1. **后端 `repoResult` 多值格式**：默认逗号分隔 `repoResult=success,fail`；联调时按后端反馈调整
2. **嵌套列排序是否纳入首期后端**：前端一并透传；若后端首期仅支持 `scanTime`/`fileNum`，嵌套列排序可暂无效直至后端补齐
3. **是否存在 `repo_result` 为空的记录**：SQL 已 `WHERE repo_result IS NOT NULL`；无需「执行中」筛选项
