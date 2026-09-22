## Context

屏蔽规则管理页（`managerConfiguration`）数据流为：后端 `shieldList` 一次返回全量 → 父组件 `tableDatas` → `fetchFrontData` 前端 slice 分页 → `tableList` 展示。顶部 `el-autocomplete` 通过 `vendor` 参数触发服务端 LIKE 查询，但 `querySearch` 为空实现，联想从未生效。

同 SCA 模块 `communityList.vue` 已在列头使用 `filterDropdown` + `tableFilters` 模式，本变更对齐该交互范式，但筛选与排序均在前端完成（数据已在内存）。

**列字段映射**（`tableHeader.id`）：

| 列 | id | 筛选来源 |
|----|-----|----------|
| 平台 | `platform` | 静态 `gitcode`、`gitee` |
| 供应商 | `vendor` | `tableDatas` 去重 |
| 组件名称 | `shieldRole` | `tableDatas` 去重 |
| 创建时间 | `created` | 仅排序，格式 `yyyy-MM-dd HH:mm:ss` |

## Goals / Non-Goals

**Goals:**

- 平台、供应商、组件名称三列支持列头多选筛选（`filterDropdown`）
- 创建时间列支持前端升序/降序切换
- 筛选 + 排序 + 分页流水线：`filter → sort → slice`
- 移除顶部供应商 autocomplete 及 `vendor` 服务端模糊查询
- 切换社区/仓库时重置筛选与排序状态

**Non-Goals:**

- 后端 API、`shieldList` 参数、Mapper 修改
- 其他列（代码仓、创建者、屏蔽问题个数）筛选
- 创建时间日期范围筛选
- 服务端分页或排序
- `getVendors` API 接入

## Decisions

### 1. 筛选实现位置：父组件 `index.vue`

**选择**：`tableFilters` 与 `sortParams` 放在 `index.vue`，`tableList` 通过 props/emit 交互。

**理由**：`tableDatas` 全量在父组件；`fetchFrontData` 已在父组件；与 `communityList` 单页模式一致。

**备选**：在 `tableList` 内筛选 — 需传入全量 `tableDatas`，props 膨胀且分页 emit 需改造。

### 2. filterDropdown 模式：静态 + 动态 options，无 `getOptions` API

**选择**：

- `platform`：`filters: [{ label: 'gitcode', value: 'gitcode' }, { label: 'gitee', value: 'gitee' }]`
- `vendor`、`shieldRole`：父组件从 `tableDatas` 去重生成 `filters`，通过 prop 传入 `tableList` 列配置

**理由**：用户明确要求从表格数据提取选项；无需额外 API；`filterDropdown` 有静态 `options` 时走本地搜索。

**备选**：`@get-options` 动态拉取 — 无对应后端接口，不适用。

### 3. 参考 `communityList` 而非 `publishTable`

**选择**：列头 `#header` + `filterDropdown`，`@change` → `handleTableFilter`。

**理由**：`publishTable` 服务端筛选需 `getOptions`/`setOptions`；本场景纯前端。

### 4. 数据流水线

```text
tableDatas (API 全量)
  → applyTableFilters(tableDatas, tableFilters)   // 多列 AND，每列 selected values 包含匹配
  → applySort(filtered, sortParams)               // created 列 parse 后比较
  → slice(pageNum, pageSize)                      // tableShowDatas
```

筛选变更或排序变更时：`pageNum = 1` 并重新 `fetchFrontData`。

### 5. 动态 filters 更新时机

**选择**：`getShieldList` 成功后根据新 `tableDatas` 重算 `vendorFilters`、`shieldRoleFilters`；若当前 `tableFilters` 含已不存在的值，保留 key 但在 filter 时无匹配（自然为空结果）。

**备选**：筛选值失效时自动清除 — 增加复杂度，首版不实现。

### 6. filterResetKey

**选择**：社区/仓库切换时递增 `filterResetToken`，清空 `tableFilters` 与 `sortParams`，传给 `filterDropdown` 的 `:key` 强制 remount。

### 7. 创建时间排序

**选择**：`created` 列 `sortable: 'custom'`；`@sort-change` 更新 `sortParams: { prop: 'created', order: 'ascending' | 'descending' | null }`；解析 `yyyy-MM-dd HH:mm:ss` 为时间戳比较。

**默认**：与后端一致 `created desc`（`order: 'descending'`），或首次无排序直至用户点击。

### 8. tableList 改造范围

- 扩展 `tableHeader` 项：`filterAble`、`filters`、`newFilterIcon`
- `#header` 条件渲染 `filterDropdown`（仅 `filterAble` 列）
- `created` 列 `:sortable="'custom'"`
- `el-table` 增加 `@sort-change`，emit 给父组件
- 引入 `filterDropdown` 组件

### 9. 分页状态：父组件单一数据源

**选择**：`pageNum`、`pageSize` 保留在 `index.vue`；`tableList` 通过 props `page`/`limit` 与 `v-model:page`/`v-model:limit`（`update:page`、`update:limit`）绑定 `sca-pagination`，不再在子组件内维护 `pagesConfig`。

**理由**：筛选/排序时父组件将 `pageNum` 设为 1 后，分页器 UI 必须同步；子组件本地页码会导致表格数据与分页器显示不一致。

**实现要点**：
- `pageChange(pages)` 仅在收到 `pages` 参数时更新 `pageNum`/`pageSize`；无参数时保留当前页码（供筛选设 1 后刷新数据）
- `fetchFrontData()` 在切片前校验：若 `pageNum` 大于筛选后最大页，回退到最后一页

### 10. 筛选图标高亮（不修改 filterDropdown）

**选择**：
- 父组件传入 `tableFilters`；`tableList` 用 `is-filter-active` 类 + `:deep()` CSS 高亮图标
- 移除 `el-table` 上 `:key="tableShowDatas?.length"`，避免筛选后 remount 清空 `filterDropdown` 内部选中态

**理由**：高亮状态需与父级 `tableFilters` 持久一致；按行数绑 `key` 会破坏组件内部状态。

### 11. 表头垂直居中

**选择**：在 `tableList.vue` 为表头 `.cell` 及 `filter-header-wrap` 内 `el-dropdown` 补充 `flex` / `inline-flex` 对齐样式；不修改 `filterDropdown.vue`。

### 12. 动态列无选项时不展示筛选

**选择**：`vendor`、`shieldRole` 在 `columnFilters` 为空时 `filterAble: false`，避免空 `options` 触发 `filterDropdown` 的 `getOptions` 请求。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 全量数据量大时前端 filter/sort 性能 | 与现状一致（本就全量返回）；数据量极大时再考虑后端分页 |
| 移除顶部搜索后用户找不到供应商筛选 | 列头「供应商」筛选提供等价多选能力；静态平台选项更直观 |
| 动态 options 在筛选后变少 | options 始终从全量 `tableDatas` 生成，非当前页 |
| `tree-props` 遗留配置 | 不改动，避免无关 diff |
| 筛选后当前页超出范围 | `fetchFrontData` 自动将 `pageNum` 校正为最大有效页 |

## Migration Plan

纯前端发布，无数据迁移。部署后顶部搜索框消失，用户改用列头筛选。无需回滚后端。

## Open Questions

（无 — 需求已明确：前端筛选、固定平台枚举、去重动态选项、移除 autocomplete）
