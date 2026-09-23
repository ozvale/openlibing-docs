# Archive: 菜单管理页签节点搜索与 el-table-v2 虚拟滚动

## 需求概述

菜单管理页签新增节点搜索能力，并将树形表格迁移到 el-table-v2 虚拟滚动，解决大数据量卡顿；随后三轮迭代修复树状态与表格样式问题，最终样式与接口列表一致且增删改不丢状态。

## 实现总结

### 搜索功能

- el-select-v2 + `flatMenuOptions` 平铺全树，label 带祖先路径，支持关键字过滤
- 选中后 `expandToNode` 展开祖先链 + 行高亮 + `scrollToRow` 居中；首次选择前快照 `preSelectExpandedIds`，清空时还原
- `collectTreeIds` 收集整树节点 id，刷新后 `expandedIds` 求交集过滤已删除节点的悬空展开 id，防止刷新后树被收起

### 虚拟滚动迁移

- el-table-v2 + el-auto-resizer，`tableRows` 按 `expandedIds` 平铺可见行，展开/收起仅重算数组不直接操作 DOM
- `buildTableColumns(width)` 让 URL 列吸收剩余宽度，窄窗口保底 220 出横向滚动
- cellRenderer 用 h 函数渲染不携带 scopeId，样式统一放非 scoped 的 `.menu-table-v2` 命名空间

### 样式对齐与满宽修复

- 表头灰底 `--el-table-header-bg-color: #f4f6fa`，无竖线/外框、仅横向分隔线，对齐接口列表 `.table-common`
- 满宽修复：`:v-scrollbar-size="0"` + `--el-table-scrollbar-size: 0px`。根因是 el-table-v2 内部 `bodyWidth = width - vScrollbarSize`（默认 6px）且行自带 `padding-inline-end: var(--el-table-scrollbar-size)`，列宽按全宽计算导致右侧 6~14px 错位——表现为右侧空白、横线断开、表头背景不满

### 增删改状态保持

- `getMenuList(keepState)`：增删改后 `getMenuList(true)` 只刷新数据并交集过滤展开 id，不清空状态、不重新触发搜索定位；首次加载与 tab 切换保持全量重置

## 关联

- 业务仓库：openlibing-web（fork: jiangzhichao/openlibing-web）
- 业务分支：jzcfork/202609menusearch
- Commits：6050fc19（搜索功能）、e61b99f5（虚拟滚动迁移）、596fd567（刷新防收起+样式对齐）、ddf873ef（满宽修复）、a1ec5157（增删改状态保持）

## 经验沉淀

已沉淀至 `spec/openlibing-web/ai_memory.md`（el-table-v2 宽度机制、cellRenderer 渲染作用域、状态保持模式）。
