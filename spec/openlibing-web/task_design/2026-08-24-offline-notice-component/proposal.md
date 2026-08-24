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
- 缺少下线倒计时：用户无法直观感知"还有多少时间可以用"，迁移/过渡窗口不足。

需要一个**统一的、轻量级、可复用**的下线预告组件，让功能负责人能快速给即将下线的功能挂上预告提示。

## 2. 目标

提供一个 `OfflineNotice` 组件（图标 + Popover 形式），具备：

- **轻量挂载**：在任意需要预告的功能入口旁挂上，使用一个警示图标作为视觉锚点。
- **交互可控**：hover / click 弹出气泡，展示下线时间、说明、链接等。
- **倒计时感知**：自动计算距离下线的剩余天数，到期后自动切换为"已下线"状态。
- **样式统一**：视觉与现有 `NoPermissionPopover.vue` 保持一致风格，融入 Element Plus 主题。
- **配置透传**：通过 props 配置，不引入集中配置表或后端接口。

## 3. 非目标

- 不做集中配置表（`src/constants/offline-notice.ts`）——配置由使用方 props 透传。
- 不接入后端接口下发下线清单。
- 不提供首次进入弹窗、内联横幅、Tooltip 文字提示等其他形式（后续如需要可在同一组件上扩展 prop）。
- 不做权限校验、不做用户级"已读"持久化。

## 4. 验收标准

### AC1 组件渲染

- 给定 `featureName` + `offlineAt` props，组件渲染一个警示图标。
- 图标尺寸默认 16px，颜色默认为警示色（橙黄），可通过 `iconSize` / `iconColor` 覆盖。

### AC2 Popover 内容

- hover（默认）或 click 时，弹出气泡，气泡内包含：
  - 标题：`<featureName> 即将下线` 或（已下线时）`<featureName> 已下线`
  - 下线时间：格式 `YYYY-MM-DD HH:mm`
  - 剩余天数：`距下线还有 N 天` / `今日下线` / `已下线 N 天`
  - 说明文案：`description` prop（可选）
  - 链接：`link` prop（可选），新窗口打开
- 气泡宽度默认 280px，可通过 `width` prop 覆盖。

### AC3 状态自动切换

- 当前时间 < `offlineAt`：显示"即将下线"，图标为警示色。
- 当前时间 ≥ `offlineAt`：显示"已下线"，图标变为中性灰色，气泡标题切换。
- 剩余天数 = 0 且当日未到点：显示"今日下线"。

### AC4 交互可控

- `trigger` prop 支持 `hover` / `click`，默认 `hover`。
- `placement` prop 支持 el-popover 标准 12 方向，默认 `top`。
- 不可用情况（如 `offlineAt` 为空）：组件不渲染任何内容（返回空），不报错。

### AC5 视觉一致性

- 气泡视觉与 `NoPermissionPopover.vue` 风格统一：白底圆角、阴影、内部小卡片布局。
- 使用 scoped 样式 + popper-class 覆盖，不污染全局。

### AC6 类型与导出

- 组件使用 `<script setup lang="ts">`，导出 Props 类型 `OfflineNoticeProps`。
- 通过 `src/components/index.ts`（如存在）或使用方直接 `import` 路径引入。

### AC7 测试

- 单元测试覆盖：渲染、状态切换（即将下线/今日下线/已下线）、props 透传、空值保护。
- 测试文件：`src/components/__tests__/OfflineNotice.spec.ts`。

## 5. 风险与依赖

- **无后端依赖**：纯前端 props 驱动。
- **时间依赖**：使用客户端本地时间，若客户端时间异常可能误判状态（可接受，下线预告非关键路径）。
- **样式冲突**：popper-class 全局覆盖可能与现有样式冲突，需用独立前缀 `offline-notice-popper`。

## 6. 关联

- 业务分支：`feature/offline-component`
- 业务 Issue：暂不关联
- docs 分支：`spec-openlibing-web-offline-notice`
