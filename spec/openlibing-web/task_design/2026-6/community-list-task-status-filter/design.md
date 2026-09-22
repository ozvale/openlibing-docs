## Context

`communityList.vue` 是 SCA「组件分析 → 开源片段引用合规」页内的风险数据看板子组件。表格通过 `v-for="column in table.column"` 渲染列，列表数据由 `softWareCompent.getRepos`（`GET open/scan/repos`）分页拉取，现有查询参数为 `community`、`platform`、`repository`、`pageNo`、`pageSize`、`sortColumn`、`sortOrder`。

任务状态列字段为 `scanResult`，展示值映射为 `statusMap`：`1`→成功、`-1`→失败、`0`→执行中。

项目内已有成熟的表头筛选模式：`filterDropdown.vue` + 列配置 `filterAble` + 父页面维护 `tableFilters` 并合并进列表请求（参考 `publishTable.vue` / `publishReview/index.vue`）。`communityList.vue` 当前为 Options API 单文件组件，未使用 `filterDropdown`。

后端 `ScanCommunityReq` 目前未声明 `scanResult` 字段；本变更按用户要求仅改前端，以前端参数透传 + 联调约定方式推进。

## Goals / Non-Goals

**Goals:**

- 在 `openSourceCompliance` 表格「任务状态」列表头提供多选筛选 UI
- 筛选确认后带 `scanResult` 参数重新请求 `open/scan/repos`，页码重置为 1
- 切换社区/平台/代码仓/Tab 时清空筛选状态
- 复用现有 `filterDropdown` 组件与静态枚举选项，无需筛选项懒加载接口

**Non-Goals:**

- 不改造 `projectCompliance` 表格
- 不抽取通用表格组件（保持 `communityList.vue` 内联改动）
- 不修改 `openlibing-sca` 后端（但定义前端期望的 query 参数格式供联调）
- 不为其他列（代码仓、平台等）增加表头筛选

## Decisions

### 1. 复用 `filterDropdown` + 列配置驱动，而非 el-table 原生 `:filters`

**选择**：在 `table.column` 的 `scanResult` 项增加 `filterAble: true` 与静态 `filters`，在 `el-table-column` 的 `#header` 插槽条件渲染 `filterDropdown`。

**理由**：原生 `:filters` 仅做客户端过滤，与当前服务端分页冲突；`filterDropdown` 支持确认/重置按钮，与项目其他模块一致。

**备选**：顶部增加独立 `el-select` 筛任务状态——改动面更大，与表头筛选需求不符。

### 2. 静态筛选项，不实现 `@get-options`

任务状态枚举固定三种，直接配置：

```javascript
filters: [
  { label: '成功', value: '1' },
  { label: '失败', value: '-1' },
  { label: '执行中', value: '0' },
]
```

`filterDropdown` 在 `options` 有值时本地过滤，不触发 `getOptions` 事件。

### 3. 筛选状态与请求参数

- 组件内维护 `tableFilters: { scanResult?: string[] }`
- `handleTableFilter({ name, data })`：`data` 为空则 `delete tableFilters.scanResult`，否则 `tableFilters.scanResult = data.map(i => i.value)`
- `initQueryData` 合并参数：`...(tableFilters.scanResult?.length ? { scanResult: tableFilters.scanResult.join(',') } : {})`

**参数格式决策**：使用逗号分隔字符串 `scanResult=1,-1`（与 Spring MVC 单字段绑定兼容性好）。

**备选**：重复 query key `scanResult=1&scanResult=-1`——需确认 `apiClient.get` 序列化行为，当前 axios 对数组默认行为不一致，故采用 join 格式并在 spec 中固定契约。

### 4. 筛选重置与 UI 重建

- 新增 `filterResetToken`，`filterResetKey` 由 `chooseCommunityValue + choosePlatformValue + chooseGitUrlValue + filterResetToken` 组成
- 在 `watch`（社区/平台/代码仓/activeName）中递增 `filterResetToken`、清空 `tableFilters`
- `filterDropdown` 的 `:key="\`${column.id}-${filterResetKey}\`"` 强制 remount，避免残留选中态

### 5. 仅改动 `scanResult` 列的表头，保留现有单元格渲染

在 `v-for` 的 `el-table-column` 内增加：

```vue
<template v-if="column.filterAble" #header>
  <filterDropdown ... @change="handleTableFilter" />
</template>
```

`#default` 中 `column.id === 'scanResult'` 的展示逻辑不变。

### 6. 不引入 `publishTable` 中间层

`communityList` 表格含嵌套列（待处理/已处理告警数），结构不同于 `publishTable`。直接在现有 `el-table-column` 循环中接入筛选，避免为单列筛选引入新封装。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 后端尚未支持 `scanResult` 过滤，筛选无效 | spec 明确参数契约；联调前在 proposal/tasks 标注后端前置；前端可先完成 UI 与参数透传 |
| Options API 与 `filterDropdown`（Options API 组件）混用 | 直接 import 注册组件，事件用 methods 处理，无需 ref/setOptions |
| 逗号分隔格式与后端预期不一致 | Open Questions 中记录，联调时按后端反馈调整为数组或 List |
| 筛选后排序：排序列与筛选叠加 | 保持现有 `sortParams` 逻辑，筛选变更时保留排序状态（与 publishReview 行为一致）；若产品要求筛选时清排序可后续调整 |

## Migration Plan

1. 前端发版后即具备表头筛选 UI 与参数透传
2. 后端支持 `scanResult` 后联调验证分页 total 与列表一致性
3. 回滚：移除列配置 `filterAble` 与相关 handler，请求参数恢复现网

## Open Questions

1. **后端 `scanResult` 参数格式**：逗号分隔字符串 vs 多值 query vs `List<String>` body——需与 `openlibing-sca` 接口负责人确认后固化（当前设计默认 `scanResult=1,-1`）
2. **筛选是否影响顶部统计**（`totalCount` / `riskCount`）：现接口返回看板汇总字段，筛选后是否应同步过滤——待产品确认；默认保持接口返回原样
