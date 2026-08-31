# 技术设计：openlibing-web 功能下线预告组件

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`fix-permission-bubble-and-offline-notice`（基于 `release_20260831`；前期交付在 `feature/offline-component`）
- **流程模式**：Standard
- **创建日期**：2026-08-24
- **最近同步**：2026-08-31（对齐提交 `a4f622ee` / `53c02179`）

## 1. 总体方案

新增独立组件 `OfflineNotice.vue`，置于 `apps/web-openlibing/src/components/` 下，与 `NoPermissionPopover.vue` 同级，遵循项目既有组件目录约定。

组件形态：OFF 深灰圆标 + `el-popover` 深色浮层，与 `NoPermissionPopover.vue` 同样的 slot 透传 + popper-class 全局覆盖模式。

**简化原则**：组件仅提示"即将下线"，不展示下线时间、不计算剩余天数、不区分已下线态、不展示功能名。

## 2. 组件 API

### 2.1 Props（实际实现，全部通过 `withDefaults` 提供默认值）

```ts
interface Props {
  /** 补充说明文案（可选，支持换行） */
  description?: string;
  /** 跳转链接（可选，新窗口打开） */
  link?: string;
  /** 链接文案，默认「了解更多」 */
  linkText?: string;
  /** 触发方式：hover（默认）/ click */
  trigger?: "hover" | "click";
  /** 气泡方向，默认 top */
  placement?:
    | "top"
    | "top-start"
    | "top-end"
    | "bottom"
    | "bottom-start"
    | "bottom-end"
    | "left"
    | "left-start"
    | "left-end"
    | "right"
    | "right-start"
    | "right-end";
  /** 圆标底色（覆盖默认深灰 #666666），OFF 字样固定白色 */
  iconColor?: string;
  /** 是否禁用气泡 */
  disabled?: boolean;
}
```

> **与初版设计的差异**：实现收敛后移除了 `width`（气泡宽度改为内容自适应 `max-content`）与 `iconSize`（圆标尺寸由字号 + padding 撑开）；`iconColor` 语义由「图标颜色」调整为「圆标底色」。后续迭代（`fix-permission-bubble-and-offline-notice`）进一步移除 `featureName` prop——标题固定为「即将下线」，不再拼接功能名；圆标默认配色由浅警示橙（`#fff1d6` 底 + `#ffa034` 字）调整为深灰（`#666666` 底 + 白字）。

### 2.2 Slots

- `#reference`：可选，覆盖默认图标作为气泡锚点（与 `NoPermissionPopover.vue` 保持一致的扩展点）。
  - 不传则使用默认警示图标。

### 2.3 不提供 emits

组件纯展示，无事件外抛。

## 3. 关键实现

### 3.1 标题文案

固定为「即将下线」常量，不拼接功能名（`featureName` prop 已移除）；aria-label 同标题。

### 3.2 Popper 自适应

复用 `NoPermissionPopover.vue` 的 `popperOptions`（flip + fallbackPlacements + preventOverflow + offset），保证窄空间下气泡位置自适应。

### 3.3 样式（实际实现：深色工具条式浮层 + 深灰 OFF 圆标）

- **默认锚点**：`<span class="offline-notice-icon">OFF</span>` 圆标——12px 字重 500 的「OFF」文字，`padding: 0 6px` / `min-width: 22px` / `height: 18px` / `border-radius: 12px`，底色深灰 `#666666`、文字白色；带轻量脉动动画（box-shadow 外扩，`rgba(102,102,102)` 与底色一致），`prefers-reduced-motion` 下禁用。
- **浮层卡片（.offline-notice）**：深色 `#2a2a2a` 底 + 白色文字 + `border-radius: 4px` + `padding: 8px 12px` + 阴影；左侧感叹号圆形图标（深灰 `#666666` 底 + 白色描边），右侧内容区（标题 + 可选 description + 可选 link，链接色 `#ffa034`、hover `#ffc069`）。
- scoped 样式：浮层内部布局；全局样式（非 scoped）：`offline-notice-popper.el-popper` 覆盖 el-popover 白边/阴影/padding（`padding: 0 !important`），并自定义箭头 `::before` 颜色为 `#2a2a2a`。
- body 仅当 `description` 或 `link` 任一存在时才渲染。

### 3.4 可访问性

- 锚点外层 `<span role="img" :aria-label="...">`，aria-label 即固定标题文案「即将下线」。

### 3.5 菜单集成（extraRender 扩展点）

为使菜单项标题旁可挂预告锚点，沿菜单数据链路打通 `extraRender`（Vue 组件）透传：

1. `RouteMeta` 与 `MenuRecordRaw`（实现在 `MenuRecordBadgeRaw`）新增可选字段 `extraRender?: Component`。
2. `generate-menus.ts` 将 `RouteMeta.extraRender` 解构透传到生成的菜单记录。
3. `sub-menu.vue` 将 `menu.extraRender` 传给 `menu-item`。
4. `menu-item.vue` 在标题 slot 之后渲染 `<component :is="extraRender">`，外包 `.vben-menu-item__extra`（inline-flex 居中）。该包裹层样式必须全局（scoped 哈希不会作用到子组件根元素）。

> 该字段全部可选，不传则不渲染，向后兼容既有菜单。

**实际接入**（`fix-permission-bubble-and-offline-notice` 分支，`apps/web-openlibing/src/router/routes/modules/menu.ts`）：

```ts
import { h } from 'vue';
import OfflineNotice from '@/components/OfflineNotice.vue';

const offlineNotice = () => h(OfflineNotice);

// 菜单项 meta 中挂载
{
  path: '/apps/entryCheckNew',
  name: 'entryCheckNew',
  meta: {
    title: '门禁检查',
    extraRender: offlineNotice,   // 菜单标题旁渲染 OFF 锚点
  },
}
```

当前挂载的菜单项：「门禁检查」（`entryCheckNew`）与「Nightly流水线看板」（`nightlyPipelineDashboard`）。

## 4. 影响范围

### 4.1 新增文件

| 路径                                                   | 说明     |
| ------------------------------------------------------ | -------- |
| `apps/web-openlibing/src/components/OfflineNotice.vue` | 组件本体 |

> 初版计划中的单元测试文件 `__tests__/OfflineNotice.spec.ts` 未落地（见 §5.1）。

### 4.2 修改文件

| 路径                                                         | 说明                                                                            |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| `packages/@core/base/typings/src/menu-record.ts`             | `MenuRecordBadgeRaw` 新增 `extraRender?: Component`                             |
| `packages/@core/base/typings/src/vue-router.d.ts`            | `RouteMeta` 新增 `extraRender?: Component`                                      |
| `packages/@core/ui-kit/menu-ui/src/components/menu-item.vue` | 标题后渲染 `extraRender`，新增全局样式 `.vben-menu-item__extra`                 |
| `packages/@core/ui-kit/menu-ui/src/sub-menu.vue`             | 透传 `:extra-render="menu.extraRender"`                                         |
| `packages/utils/src/helpers/generate-menus.ts`               | 解构并透传 `extraRender` 到菜单记录                                             |
| `apps/web-openlibing/src/router/routes/modules/menu.ts`      | 「门禁检查」「Nightly流水线看板」菜单项 meta 挂载 `extraRender`（当前分支新增） |

> 前 5 个共享包文件为 `feature/offline-component` 交付（已随 `!740` 合入 `release_20260831`）；`menu.ts` 为 `fix-permission-bubble-and-offline-notice` 分支新增接入。

### 4.3 接入方式

组件本身可挂载在任意页面入口：

```vue
<template>
  <div class="page-header">
    <h2>漏洞处理</h2>
    <OfflineNotice
      description="该能力将整合至「漏洞规则中心」，请提前迁移规则。"
      link="https://internal-docs.example.com/vuln-rule-migration"
    />
  </div>
</template>

<script setup lang="ts">
import OfflineNotice from "@/components/OfflineNotice.vue";
</script>
```

菜单项接入方式（`extraRender` + `h()` 渲染函数）见 §3.5 实际接入示例。

## 5. 测试策略

### 5.1 单元测试

初版计划覆盖渲染/标题/description/link/body 缺省/iconColor/slot 等 12 条用例，但**本轮实现未落地测试文件**（`__tests__/OfflineNotice.spec.ts` 未提交）。原因：组件为纯展示、props 驱动，且本地环境受限；测试留待接入业务页面后按需补充。此决策已在 proposal 非目标中说明。

### 5.2 手动验证（用户自测）

- 在任一业务页面挂上 `<OfflineNotice>`，启动 `pnpm dev:ob`。
- 验证 hover/click 弹出浮层、标题与文案正确、链接可点击。
- 验证菜单项（门禁检查、Nightly流水线看板）通过 `extraRender` 挂载后，标题旁渲染深灰 OFF 圆标且浮层正常。

## 6. 兼容性与回滚

- `extraRender` 为新增可选字段，不传不渲染，对既有菜单/路由无破坏性变更。
- `featureName` 移除为 props 收敛（该组件此前无外部使用方传入此 prop，无调用方需适配）；`iconColor` 默认值变更对未显式传值的调用方生效。
- 回滚：删除 `OfflineNotice.vue`、还原 `menu.ts` 中两个菜单项的 `extraRender` 挂载，并还原 5 个共享菜单文件（`menu-record.ts`、`vue-router.d.ts`、`menu-item.vue`、`sub-menu.vue`、`generate-menus.ts`）中 `extraRender` 相关改动即可，无残留依赖。
