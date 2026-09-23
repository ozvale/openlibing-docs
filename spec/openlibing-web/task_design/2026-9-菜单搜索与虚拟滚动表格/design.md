# Design: 菜单管理页签节点搜索与 el-table-v2 虚拟滚动

## 技术方案

### 修改文件

| 文件                                                       | 修改内容                                                         |
| ---------------------------------------------------------- | ---------------------------------------------------------------- |
| apps/web-openlibing/src/views/authorityManagement/menu.vue | 搜索下拉、虚拟滚动迁移、样式对齐、状态保持（单文件实现全部改动） |

### 搜索功能（el-select-v2）

- `flatMenuOptions` computed：深度优先平铺整树节点，`label` 拼接祖先路径（`path / menuName`），既可区分同名节点，也支持按路径关键字过滤（el-select-v2 内置 filterable + 虚拟滚动渲染下拉）
- `selectedNodeId` 保存选中节点 id，高亮由 `tableRowClass` 在行渲染期读取 `selectedNodeId` 驱动
- `handleNodeSelect`：
  - 选中 → `expandToNode`：首次选择前快照当前展开状态到非响应式字段 `preSelectExpandedIds`（created 中初始化），展开祖先链并 `scrollToRow` 居中
  - 清空 → `restoreExpandSnapshot`：按快照还原展开状态

### 虚拟滚动迁移（el-table-v2）

- `el-auto-resizer` 提供容器宽高；固定 `row-height=40`、`header-height=40`
- `tableRows` computed：按 `expandedIds`（Set）深度优先平铺出当前可见行，展开/收起只重算可见行数组，不直接操作 DOM
- `rowMetaMap` computed：提供缩进深度/是否有子节点/是否展开元数据，供单元格渲染
- `buildTableColumns(width)`：URL 列吸收剩余宽度（最小 220 保底），窄窗口时保底宽度撑出横向滚动
- 单元格用 `cellRenderer`（h 函数）渲染，不携带本组件 scopeId，样式统一放非 scoped 块并以 `.menu-table-v2` 作命名空间

### 样式对齐与满宽修复

对齐接口列表 `.table-common`（normal.less）：无 border 属性、表头灰底、仅横向分隔线。

- `--el-table-header-bg-color: #f4f6fa` 表头灰底
- 无竖线/外框，行自带 `border-bottom` 横线

满宽修复（右侧空白/横线不通/表头色不满三症状同源）：

- 根因：el-table-v2 内部 `bodyWidth = width - vScrollbarSize`（vScrollbarSize 默认 6px），行/表头渲染宽比容器窄；且行自带 `padding-inline-end: var(--el-table-scrollbar-size)`（此前误设 8px）；而列总宽按容器全宽计算，导致错位——横线画在行元素上断在 W-6 处，表头被 `header-wrapper` 的 `overflow: hidden` 裁剪
- 修复：模板加 `:v-scrollbar-size="0"` + `--el-table-scrollbar-size: 0px`，行渲染宽 = 容器宽、无行右 padding，单元格恰好填满
- 副作用评估：竖向滚动条为 overlay 覆盖式，视觉宽度走组件独立默认值，不受该 prop 影响；窄窗口横向滚动走 window 元素原生滚动，行为不变

### 增删改后状态保持

- `getMenuList(keepState)` 增加参数：`keepState=true` 时跳过状态重置（不清空 `expandedIds`/快照、不重新 `expandToNode`），仅将 `expandedIds` 与搜索前快照同最新树求交集（`collectTreeIds`），过滤已删除节点的悬空展开 id
- 删除/新增/修改成功后调用 `getMenuList(true)`；首次加载与 tab 切回保持全量重置行为不变

## 影响范围

- 仅修改 menu.vue 单文件，不涉及接口/数据模型变更
- 下拉与表格均为组件内交互，无对外契约变化
- 无安全影响（无鉴权/输入/凭证相关改动）
