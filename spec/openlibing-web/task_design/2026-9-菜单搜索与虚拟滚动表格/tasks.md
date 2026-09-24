# Tasks: 菜单管理页签节点搜索与 el-table-v2 虚拟滚动

## 实现步骤

- [x] 1. 搜索下拉：新增 el-select-v2（filterable/clearable）与 `flatMenuOptions` computed，平铺全树并带祖先路径 label
- [x] 2. 搜索定位：`handleNodeSelect` / `expandToNode` / `scrollToSelectedRow`，展开祖先链 + 高亮 + 滚动居中
- [x] 3. 搜索前快照：`preSelectExpandedIds`（created 初始化，非响应式），清空选择时 `restoreExpandSnapshot` 还原
- [x] 4. 虚拟滚动迁移：el-table-v2 + el-auto-resizer，`tableRows`/`rowMetaMap` computed 按 `expandedIds` 平铺可见行
- [x] 5. 列定义 `buildTableColumns(width)`：URL 列吸收剩余宽度，窄窗口保底出横向滚动
- [x] 6. 单元格 cellRenderer（h 函数）渲染 + 样式放非 scoped 块（.menu-table-v2 命名空间）
- [x] 7. 样式对齐接口列表：表头灰底 #f4f6fa、无竖线/外框、仅横向分隔线
- [x] 8. 满宽修复：`:v-scrollbar-size="0"` + `--el-table-scrollbar-size: 0px`，消除右侧空白/横线断开/表头色不满
- [x] 9. 刷新防收起：`collectTreeIds` + `expandedIds` 与最新树求交集过滤悬空 id
- [x] 10. 增删改状态保持：`getMenuList(keepState)`，删除/新增/修改成功后 `getMenuList(true)`；首次加载与 tab 切换保持重置行为
- [x] 11. ESLint 校验通过，用户自测验证通过
