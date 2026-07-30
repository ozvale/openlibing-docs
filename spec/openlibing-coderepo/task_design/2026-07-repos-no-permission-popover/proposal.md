# 代码仓管理页面操作无权限提示气泡

## 需求背景

代码仓管理页面（涉及 openlibing-coderepo、openlibing-framework、openlibing-web 三仓）的操作按钮，当前对无权限用户采用 `v-if` 隐藏或 `:disabled` 禁用，用户无法得知「该功能存在但需要何种角色」，导致：
- 用户不知道某功能是否存在
- 用户不知道需要什么角色才能使用某功能
- 用户不知道如何申请对应权限

需求要求改为：页面加载时获取当前用户角色 + 操作权限元数据，对无权限按钮在悬浮时弹出气泡提示，引导用户申请权限。

UI Demo 已审核确认：`ui-demo/no-permission-dialog.html`（三段式气泡，340px 宽，悬浮触发，自动定位）。

业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/73

## 功能描述

### 后端（framework）

新增 1 个 HTTP 接口 `GET /user/get-operation-permissions`，一次性返回所有操作的权限元数据，包含：
- 操作权限码（identification）
- 操作名（operationName，来自 menu_info.menu_name）
- 当前用户对该操作是否有权限（hasPermission）
- 该操作有权限的角色，按 5 级（system/product/project/repo/general）分组

### 前端（web）

1. **接入新接口**：`Content.vue` 在 `getUserInfor` 之后并行调用新接口，存入 `useAppStore().operationPermissions`
2. **新建 `NoPermissionPopover.vue` 组件**：封装三段式气泡，Props 含 `auth` / `operationName` / `trigger`，有权限时透传点击，无权限时显示气泡
3. **新建 `permissions-meta.ts` 常量**：按 identification 维护操作名/介绍/指引文案
4. **改造 Repos 目录 4 个页面**：`index.vue` / `branches.vue` / `repoUserManage.vue` / `tagManagement.vue`，将现有 canHandle 调用点改为 `NoPermissionPopover` 包裹

### 不做什么

- 不改动 coderepo 仓代码（复用 framework 新接口）
- 不做 DB schema 变更（复用现有 4 张表）
- 不引入新前端依赖
- 不改造 Repos 目录以外的页面（后续可复用组件推广）
- 不实现「申请权限」按钮的实际跳转逻辑（仅占位 alert，跳转目标后续对接）
- 不实现「联系客服」按钮的实际逻辑（仅占位 alert）

## 验收标准

- [ ] framework 新增 `GET /user/get-operation-permissions` 接口，响应结构符合契约
- [ ] framework 接口基于 `menu_info` → `role_permission_manager` → `role_info` 反查，按 5 级分组
- [ ] framework `hasPermission` 复用现有 permissions 缓存逻辑
- [ ] framework 单元测试覆盖反查 + 分组 + hasPermission 计算
- [ ] web 新组件 `NoPermissionPopover.vue` 三段式样式与 UI Demo 一致
- [ ] web `permissions-meta.ts` 覆盖 Repos 目录所有权限码
- [ ] web `Content.vue` 接入新接口，存入 store
- [ ] web `useAppStore` 扩展 `operationPermissions` 状态
- [ ] web `Repos/index.vue` 操作按钮（编辑/删除/成员管理/分支管理/同步/新增/批量编辑）改造完成
- [ ] web `Repos/branches.vue` 操作按钮改造完成
- [ ] web `Repos/repoUserManage.vue` 操作按钮改造完成
- [ ] web `Repos/tagManagement.vue` 操作按钮改造完成
- [ ] 气泡 hover 触发，支持 ESC 关闭、滚动关闭、自动定位（下方优先，空间不足翻上方）
- [ ] 有权限按钮行为不变（正常点击执行原逻辑）
- [ ] 主品牌色 `#526ecc`、链接色 `#409eff`
- [ ] 跨仓联调通过（framework 接口 → web 气泡展示）
- [ ] 三仓 PR 均打 `ai-assisted` 标签 + 关联 Issue #73

## 影响范围

| 仓 | 改动类型 | 估算行数 |
|---|---|---|
| openlibing-framework | 新增 controller 方法 + service + DTO + 单测 | 100-150 行 |
| openlibing-coderepo | 0 改动 | 0 |
| openlibing-web | 新增组件 + 常量 + store 扩展 + 4 个页面改造 | 250-350 行 |
| openlibing-docs | spec 三件套 + archive | 本文档 |

**跨仓契约**：framework 新接口响应结构需与 web 前端对齐。

**部署影响**：framework / web 两仓分别部署，coderepo 不发版。
