# 提案：openlibing-web 功能下线预告组件

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/offline-component`（fork：`vermouth_fee/openlibing-web`）
- **流程模式**：Standard
- **Issue 关联方式**：暂不关联（本轮仅编码交付，后续补充）
- **创建日期**：2026-08-24

## 1. 背景与动机

平台持续迭代，部分功能在版本演进中需要逐步下线。当前没有统一的"下线预告"提示机制，存在以下问题：

- 下线信息分散：部分功能通过发版公告告知，部分功能用户在功能被移除后才发现。
- 用户感知不一致：不同模块各用各的样式（Alert、文字、Dialog），视觉与交互不统一。

需要一个**统一的、轻量级、可复用**的下线预告组件，让功能负责人能快速给即将下线的功能挂上预告提示。

## 2. 目标

提供一个 `OfflineNotice` 组件（警示锚点 + Popover 形式），具备：

- **轻量挂载**：在任意需要预告的功能入口旁挂上，使用一个警示「OFF」圆标作为视觉锚点。
- **交互可控**：hover / click 弹出深色浮层，展示功能名（即将下线）、说明、链接。
- **样式统一**：视觉与现有 `NoPermissionPopover.vue` 同手法（popper-class 覆盖 + popperOptions 自适应），融入 Element Plus 主题。
- **配置透传**：通过 props 配置，不引入集中配置表或后端接口。
- **菜单集成**：通过菜单 `extraRender` 扩展点接入，可在菜单项标题旁渲染预告锚点（首个落地场景）。

> 本轮范围已随实现收敛：组件实际为深色浮层卡片形态 +「OFF」圆标，非白底卡片；不提供 `width` / `iconSize` 自定义，宽度随内容自适应；`iconColor` 语义为圆标底色。

## 3. 非目标

- **不展示具体下线时间**，不计算剩余天数。
- **不区分已下线状态**，组件仅提示"即将下线"。
- 不做集中配置表（`src/constants/offline-notice.ts`）——配置由使用方 props 透传。
- 不接入后端接口下发下线清单。
- 不提供首次进入弹窗、内联横幅、Tooltip 文字提示等其他形式。
- 不做权限校验、不做用户级"已读"持久化。
- **本期不交付单元测试**（纯展示组件，测试留待接入业务页面后按需补充）。

## 4. 验收标准

### AC1 组件渲染

- 给定 `featureName` prop，组件渲染一个警示「OFF」圆标作为锚点。
- 圆标底色默认为浅警示橙 `#fff1d6`、文字/徽标色 `#ffa034`，可通过 `iconColor` 覆盖底色；圆标带轻量脉动动画（尊重 `prefers-reduced-motion`）。

### AC2 Popover 内容

- hover（默认）或 click 时，弹出深色浮层，浮层内包含：
  - 感叹号图标 + 标题：`<featureName> 即将下线`
  - 说明文案：`description` prop（可选）
  - 链接：`link` prop（可选），新窗口打开，文案默认「了解更多」可由 `linkText` 覆盖
- 气泡宽度随内容自适应（`max-content`），不设固定宽度。
- 无 `description` 且无 `link` 时，气泡只展示标题。

### AC3 交互可控

- `trigger` prop 支持 `hover` / `click`，默认 `hover`。
- `placement` prop 支持 el-popover 标准 12 方向，默认 `top`。
- `disabled` prop 为 `true` 时禁用气泡。

### AC4 视觉一致性

- 浮层与 `NoPermissionPopover.vue` 同手法：popper-class 全局覆盖 el-popover 白边/阴影，深色工具条式浮层（`#2a2a2a` 底、白色文字、`#ffa034` 强调色）。
- 使用 scoped 样式 + popper-class 覆盖，不污染全局（独立前缀 `offline-notice-popper`）。

### AC5 类型与导出

- 组件使用 `<script setup lang="ts">`，Props 类型内联。
- 通过使用方直接 `import` 路径引入。

### AC6 测试

- 单元测试：本期未提供（纯展示、props 驱动，留待接入业务页面后按需补充）。
- 手动验证覆盖：锚点渲染、气泡文案、description/link、`#reference` slot 覆盖、菜单项 `extraRender` 接入。

## 5. 风险与依赖

- **无后端依赖**：纯前端 props 驱动。
- **样式冲突**：popper-class 全局覆盖可能与现有样式冲突，需用独立前缀 `offline-notice-popper`。
- **共享包改动**：菜单 `extraRender` 扩展点落在 `@core/ui-kit/menu-ui`、`@core/base/typings`、`@vben/utils` 等共享包，改动需保证向后兼容（新增可选字段，不破坏既有菜单渲染）。

## 6. 关联

- 业务分支：`feature/offline-component`
- 业务 Issue：暂不关联
- docs 分支：`spec-openlibing-web-offline-notice`
