# tool-report-sla — 技术设计

## 方案概述

待办中心两个工具举报列表（申请 / 审核）通过扩展 `applyTableColumn` / `reviewTableColumn` 配置新增两列展示 SLA 信息，并在数据加载后对 `slaExpired` 字段做格式化转换（`'1'` → 「是」）。工具详情页将原有的 `v-else-if` / `v-else` 链改为基于 `reportStatus` 显式值的独立 `v-if` 判断，避免状态值异常时错误回退。

## 架构决策

| 决策点                        | 选择                                                       | 原因                                                                                   |
| ----------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| SLA 字段格式化位置            | 前端 map 转换                                              | 后端返回 `'1'`/`'0'` 字符串，前端展示「是」/「否」更符合中文交互习惯，无需后端额外加工 |
| 列配置方式                    | 复用既有 `applyTableColumn` / `reviewTableColumn` ref 数组 | 与同文件其他列配置风格一致，无新技术引入                                               |
| 详情页状态判断                | 显式 `v-if` 替代 `v-else-if`/`v-else`                      | 状态值 `0/1/2` 是枚举封闭集合，显式判断可避免后端返回异常值时错误回退到「可举报」状态  |
| `pendingReviewCount` 递减时机 | `submitReview` 成功后立即递减                              | 与既有 `toolReportCount` 递减时机保持一致，避免计数滞后                                |

## 涉及文件

| 文件                                                                  | 操作 | 说明                                                            |
| --------------------------------------------------------------------- | ---- | --------------------------------------------------------------- |
| `apps/web-openlibing/src/views/ToDoCenter/ToolReportApplication.vue`  | 修改 | 新增 2 列配置 + 数据加载时格式化 `slaExpired`                   |
| `apps/web-openlibing/src/views/ToDoCenter/ToolReportReview.vue`       | 修改 | 新增 2 列配置 + 格式化 `slaExpired` + 递减 `pendingReviewCount` |
| `apps/web-openlibing/src/views/ToolManagement/ToolMarket/details.vue` | 修改 | 修复举报状态显示逻辑（`v-else-if`/`v-else` → 显式 `v-if`）      |

## 关键代码

### 1. 列配置新增

```js
{
  label: '审核截止时间',
  prop: 'slaDeadline',
  width: '120px',
},
{
  label: '是否已超时自动下架',
  prop: 'slaExpired',
  width: '120px',
},
```

### 2. 数据格式化

```js
applyTableData.value =
  list.map((item) => ({
    ...item,
    slaExpired: item.slaExpired === "1" ? "是" : "否",
  })) || [];
```

### 3. 审核通过后递减待办计数

```js
if (app.pendingReviewCount > 0) {
  app.setPendingReviewCount(app.pendingReviewCount - 1);
}
if (app.toolReportCount > 0) {
  app.setToolReportCount(app.toolReportCount - 1);
}
```

### 4. 详情页状态显式判断

```vue
<div v-if="toolDetail.reportStatus === '2'" style="width: 80px">
  <img src="@/assets/images/common/discontinued.png" alt="" />
</div>
<div v-if="toolDetail.reportStatus === '1'" style="width: 80px">
  <img src="@/assets/images/common/reviewing.png" alt="" />
</div>
<template v-if="toolDetail.reportStatus === '0'">
  <!-- 举报入口（须具备 tool_report 权限） -->
</template>
```

## 风险 & 缓解

- **风险**：后端未返回 `slaDeadline` / `slaExpired` 字段时，列显示为空。
  **缓解**：前端只做字段映射与格式化，未定义字段在 Element Plus 表格中默认显示空值，不影响其他列。
- **风险**：`slaExpired` 字段值非 `'1'`/`'0'`（如 `true`/`false` 布尔值）时统一显示为「否」。
  **缓解**：当前实现是显式 `=== '1'` 严格判断，与后端约定的字符串枚举一致；若后端字段类型变更需同步调整。

## 跨仓影响

- 后端：需提供 `slaDeadline`、`slaExpired` 字段（如尚未提供）
- 无前端跨仓影响
