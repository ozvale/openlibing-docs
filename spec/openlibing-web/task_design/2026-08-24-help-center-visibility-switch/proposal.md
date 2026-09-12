# 2026-08-24 帮助中心文档可见性开关提案

## 1. 需求背景

帮助中心文档目前对所有用户可见。业务上需要将部分文档标记为"管理中心文档"，仅对特定范围展示。同时，管理员需要一个便捷的入口在管理中心下维护帮助文档，而无需进入普通帮助中心页面。

### 问题描述

- 文档缺少"管理中心文档"可见性标记，无法区分普通文档与管理中心专属文档
- `visibility` 字段为 int 型（1 开 / 0 关），后端已支持，前端缺少编辑入口
- 管理中心缺少帮助文档维护入口
- 帮助中心页面 `handleNodeClick` 中 `router.push({ query })` 在异步等待后执行，若期间路由已跳走，会把 `?id=xxx` 挂到其他页面 URL 上

## 2. 验收标准

### 功能验收

- [x] 文档标题行最右侧显示"管理中心文档"开关（element-plus el-switch）
- [x] 开关仅在同时满足以下两个条件时显示：
  - 用户拥有 `manage_config` 权限（`app.user.permissions` 包含 `manage_config`）
  - 当前 URL 在 `/manageCenter` 路径下
- [x] 开关绑定 `currentReadInfo.visibility`（int 型：1 开 / 0 关，未取到值默认 0）
- [x] 切换开关调用 `updateHelpCenterFile` 接口（与编辑弹窗确定同一接口），仅 `visibility` 字段变更
- [x] 接口失败时回滚开关状态
- [x] 管理中心左侧菜单新增"帮助中心 → 帮助文档"入口，路由为 `/manageCenter/helpCenterSetting`
- [x] `handleNodeClick` 的 `router.push` 增加组件激活守卫，组件失活后不执行跳转

### 代码质量验收

- [x] pre-commit 全部钩子通过（prettier / eslint / detect-secrets 等）
- [x] 无未使用导入残留

## 3. 变更范围

### 涉及模块

- **前端组件**: `apps/web-openlibing/src/views/HelpCenter/helpCenter.vue` — 可见性开关 + 路由跳转守卫
- **路由配置**: `apps/web-openlibing/src/router/manageRouter.ts` — 新增管理中心帮助文档路由
- **管理中心菜单**: `apps/web-openlibing/src/views/manageCenter/index.vue` — 新增帮助中心菜单入口

### 变更类型

- 新功能（可见性开关 + 管理中心入口）
- 缺陷修复（异步路由跳转守卫）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 帮助中心页面展示逻辑、管理中心菜单；不涉及后端接口变更
- **破坏性变更**: 无（`visibility` 未取到时默认 0，与原有文档行为兼容）

## 5. 关联信息

- **分支**: `jzcfork/202608help`
- **Commits**: `51ee95e1`、`1df589e8`
- **标签**: ai-assisted
