# 提案：openlibing-web 按钮无权限控制（NoPermissionPopover 落地）

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/nopermission`（fork：`vermouth_fee/openlibing-web`）
- **流程模式**：Standard
- **Issue 关联方式**：暂不关联
- **创建日期**：2026-08-27
- **最近同步**：对齐 `feature/nopermission` 最新提交 `cb8f8842`

## 1. 背景与动机

平台各页面按钮权限控制方式不统一：

- 部分页面用 `v-if="canHandle(xxx)"` 直接隐藏无权限按钮，用户看不到功能入口，也不知道如何获得权限。
- 部分按钮虽然 `:disabled` 置灰，但无任何提示，用户不知道为何不可点、如何申请。

现有 `NoPermissionPopover.vue` 组件已提供"无权限 hover 三段式气泡"（无权限提示 / 角色归属级别 / 权限介绍与申请指引），但仅在部分页面（如 Repos）使用。本轮将该模式推广到更多业务页面，统一按钮权限交互。

## 2. 目标

- 对以下页面按钮改用 `NoPermissionPopover` 包裹：无权限时按钮置灰 + hover 弹出申请指引；有权限时按钮正常可用：
  - 项目管理（编辑 / 成员管理）
  - 项目成员管理（添加 / 编辑 / 删除成员）
  - 漏洞视图（视图配置 / 同步漏洞）
  - 发布评审（发布模版 / 发布设置）
  - 工具市场（创建工具 / 工具管理 / 我的流程）
  - SCA 布局（社区配置）
- 为涉及的 12 个权限码在 `permissions-meta.ts` 补充操作名、介绍与申请指引元数据。
- 无权限时点击不触发业务动作（如同步漏洞按钮在方法入口加权限守卫）。

## 3. 非目标

- 不修改 `NoPermissionPopover.vue` 组件本身（复用现有能力）。
- 不做路由级权限拦截（已有 guard.ts 负责）。
- 不覆盖全部页面的权限按钮（本轮仅 6 处页面场景）。
- 不改动后端权限接口 / 权限码定义。

## 4. 验收标准

### AC1 项目管理

- 项目列表"操作"列编辑按钮、成员管理按钮：无权限时置灰 + hover 显示 NoPermissionPopover，有权限时正常可点。
- 无权限时不渲染 `el-tooltip`（避免与 NoPermissionPopover 的 el-popover 嵌套冲突）。

### AC2 项目成员管理

- "添加项目成员"按钮与成员列表编辑/删除按钮：无权限时置灰 + 气泡提示，有权限时正常。

### AC3 漏洞视图

- "配置"按钮与"同步漏洞"按钮：无权限时置灰 + 气泡提示。
- 无权限点击"同步漏洞"不触发请求（`syncVulnerabilityRefresh` 内加权限守卫）。
- `cve.less` 中 disabled 光标由 `cursor: text` 调整为 `cursor: not-allowed`。

### AC4 发布评审

- "发布模版" / "发布设置"按钮：无权限时置灰 + 气泡提示，有权限时正常。

### AC5 工具市场

- "创建工具" / "工具管理" / "我的流程"按钮：无权限时置灰 + 气泡提示，有权限时正常。

### AC6 SCA 布局

- SCA 侧边导航"社区配置"按钮（`managerConfiguration`）：无权限时置灰 + 气泡提示。

### AC7 权限元数据

- `permissions-meta.ts` 新增 12 个权限码元数据，无权限气泡能展示正确的操作名 / 介绍 / 申请指引。

## 5. 风险与依赖

- **el-tooltip 嵌套冲突**：`NoPermissionPopover` 内部是 `el-popover`，若按钮同时被 `el-tooltip` 包裹会造成 tooltip 失效 / 气泡不弹。解决：仅在有权限时渲染 `el-tooltip`（`v-if="canHandle(...)"`），无权限时渲染裸按钮。
- **纯前端改动**：无后端接口变更，无数据模型变化。

## 6. 关联

- 业务分支：`feature/nopermission`
- 业务 Issue：暂不关联
- docs 分支：`spec-openlibing-web-offline-notice`
