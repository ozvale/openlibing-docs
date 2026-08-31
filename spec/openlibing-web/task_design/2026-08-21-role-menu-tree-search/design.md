# 2026-08-21-role-menu-tree-search — 技术设计

## 方案概述

在 role.vue 权限菜单树上方新增 `el-autocomplete` 搜索框（联想数据来自菜单树扁平化列表）；选中后通过 Element Plus Tree API 展开父级并 `setCurrentKey` 高亮，再借 el-tree 节点 DOM 自带的 `data-key` 属性精确定位目标节点，手动计算并设置树容器 `scrollTop` 完成滚动居中。

## 架构决策

- **滚动定位用 `data-key` DOM 查询 + 手动计算 scrollTop，而非 `node.$el.scrollIntoView`**：Element Plus 2.13.0 的 tree 内部 Node 模型没有 `$el` 属性，旧实现（commit 47c01e99）的滚动实际是空操作；且原生 `scrollIntoView` 会连带滚动整个弹窗。`.el-tree-node` 元素原生携带 `data-key`（值为 node-key），可直接 `querySelector` 精确定位，只滚动树容器。
- **展开父级用 Node 模型直接赋值 `expanded = true`**：tree store 经 `ref()` 深度代理，赋值可触发响应式更新（与 EP 内部实现一致），无需遍历数据源。
- **联想列表 `trigger-on-focus: false`**：避免聚焦即弹全量菜单列表，仅输入关键字后匹配。

## 涉及文件

| 文件                                                       | 操作 | 说明                                                                                                       |
| ---------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------- |
| apps/web-openlibing/src/views/authorityManagement/role.vue | 修改 | 模板加搜索框/容器 ref/highlight-current；脚本加扁平化、联想、定位逻辑；非 scoped 样式加 `.is-current` 高亮 |

## 关键实现点

1. `flattenMenuTree`：DFS 扁平化菜单树为 `{ id, label, value(完整路径) }` 列表，在 `getSubMenu` 成功回调中重建并重置关键字
2. `querySearchMenu`：按 label 不区分大小写包含匹配
3. `handleSelectMenu`：展开父级链 → `setCurrentKey` → `$nextTick` 后 `querySelector('.el-tree-node[data-key="id"]')` → 按容器与节点 rect 计算 `scrollTop` 居中

## 风险 & 缓解

- 无新接口/数据模型/安全影响；行为验证依赖手动自测（应用内无单测基础设施），已通过 ESLint 检查

## 跨仓影响

无
