# 实现任务清单：openlibing-web 功能下线预告组件

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`fix-permission-bubble-and-offline-notice`（基于 `release_20260831`；前期交付在 `feature/offline-component`）
- **流程模式**：Standard
- **创建日期**：2026-08-24
- **最近同步**：2026-08-31（对齐 `fix-permission-bubble-and-offline-notice` 提交 `a4f622ee` / `53c02179`；此前 2026-08-27 对齐 `feature/offline-component` `a3bc9508`）

## 实现步骤

### Step 1: 创建组件本体

- [x] 新建 `apps/web-openlibing/src/components/OfflineNotice.vue`
- [x] 实现 `<script setup lang="ts">` + Props 类型（全部 `withDefaults` 提供默认值）
- [x] 实现默认锚点：OFF 圆标（文字徽标 + 脉动动画，非内联 SVG 图标）
- [x] 实现 `el-popover` 深色浮层 + `#reference` slot 透传
- [x] 实现 popperOptions 自适应（flip + preventOverflow + offset，复用 `NoPermissionPopover.vue` 模式）
- [x] 实现 scoped 样式（浮层内部布局：感叹号图标 + 标题 + 可选 description/link）
- [x] 实现全局样式覆盖（`offline-notice-popper`，含箭头颜色）
- [x] body 仅当 `description` 或 `link` 存在时渲染
- [x] Props 收敛：移除 `width` / `iconSize`；`iconColor` 语义为圆标底色
- [x] 迭代收敛（`53c02179`）：移除 `featureName` prop，标题固定「即将下线」
- [x] 迭代收敛（`53c02179`）：OFF 圆标改为深灰底 `#666666` + 白字；气泡内感叹号图标改为深灰底 + 白描边；脉动动画颜色同步改为 `rgba(102,102,102)`

### Step 2: 菜单集成（extraRender 扩展点）

- [x] `packages/@core/base/typings/src/menu-record.ts`：`MenuRecordBadgeRaw` 新增 `extraRender?: Component`
- [x] `packages/@core/base/typings/src/vue-router.d.ts`：`RouteMeta` 新增 `extraRender?: Component`
- [x] `packages/utils/src/helpers/generate-menus.ts`：解构并透传 `extraRender`
- [x] `packages/@core/ui-kit/menu-ui/src/sub-menu.vue`：透传 `:extra-render="menu.extraRender"`
- [x] `packages/@core/ui-kit/menu-ui/src/components/menu-item.vue`：标题后渲染 `extraRender` + 全局样式 `.vben-menu-item__extra`
- [x] 菜单实际接入（当前分支 `menu.ts`）：`const offlineNotice = () => h(OfflineNotice)`，「门禁检查」（`entryCheckNew`）与「Nightly流水线看板」（`nightlyPipelineDashboard`）菜单项 meta 挂载 `extraRender: offlineNotice`

### Step 3: 单元测试（本期未落地）

- [ ] `apps/web-openlibing/src/components/__tests__/OfflineNotice.spec.ts` —— **未交付**，纯展示组件，留待接入业务页面后按需补充（已在 proposal 非目标说明）

### Step 4: 验证

- [x] ESLint（本轮针对 `OfflineNotice.vue` 执行 `pnpm exec eslint`，通过；早期文件留待 CI）
- [ ] `pnpm check:type`（typecheck 通过）—— 本地环境受限，留待 CI
- [x] IDE LSP 诊断：无 error / warning
- [x] 手动验证：OFF 圆标渲染、hover/click 浮层、description/link、`#reference` slot、菜单项 `extraRender` 接入（门禁检查、Nightly流水线看板）

### Step 5: 提交

- [x] 业务仓 commit（`feature/offline-component`：`135d4bd0` → `62ea5204` → `e697865d` → `a3bc9508`，已随 `!740` 合入 `release_20260831`）
- [x] 业务仓 commit（`fix-permission-bubble-and-offline-notice`：`a4f622ee` 移除 ToolMarket NoPermissionPopover → `53c02179` OfflineNotice featureName 移除 + 深灰化；分支基于 `release_20260831`，尚未推送）
- [ ] 业务仓 commit（`menu.ts` 菜单接入，工作区改动待提交）
- [x] docs 仓 commit（spec 文档更新，本轮随 `fix-permission-bubble-and-offline-notice` 最新改动同步）
- [ ] 业务仓 PR（用户自测确认后）
- [ ] docs 仓 PR（业务 PR 合入后）

## 不在本轮范围

- 集中配置表（`src/constants/offline-notice.ts`）
- 后端接口下发
- "已读"持久化
- 内联横幅 / Tooltip / 首次弹窗等其他形式
- **下线时间展示、剩余天数计算、已下线状态切换**（已明确移除）
- **功能名展示（`featureName` prop）**（已明确移除，标题固定「即将下线」）
- **单元测试**（已明确移除，见 Step 3）
