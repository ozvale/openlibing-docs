# 技术设计：openlibing-web 功能下线预告组件

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/offline-component`
- **流程模式**：Standard
- **创建日期**：2026-08-24

## 1. 总体方案

新增独立组件 `OfflineNotice.vue`，置于 `apps/web-openlibing/src/components/` 下，与 `NoPermissionPopover.vue` 同级，遵循项目既有组件目录约定。

组件形态：图标 + `el-popover`，与 `NoPermissionPopover.vue` 同样的 slot 透传 + popper-class 全局覆盖模式。

## 2. 组件 API

### 2.1 Props

```ts
export interface OfflineNoticeProps {
  /** 即将下线的功能名（必填，用于气泡标题与 aria-label） */
  featureName: string;
  /** 下线时间，ISO 8601 字符串或 Date（必填）。为空/无效时组件不渲染 */
  offlineAt: string | Date;
  /** 补充说明文案（可选，支持换行） */
  description?: string;
  /** 跳转链接（可选，新窗口打开） */
  link?: string;
  /** 链接文案，默认"了解更多" */
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
  /** 气泡宽度，默认 280 */
  width?: number;
  /** 图标尺寸，默认 16 */
  iconSize?: number;
  /** 图标颜色，默认警示橙 #f0883a（未下线）/ 灰色 #86909c（已下线） */
  iconColor?: string;
  /** 是否禁用气泡（如功能已上线"已读"开关后可关闭） */
  disabled?: boolean;
}
```

### 2.2 Slots

- `#reference`：可选，覆盖默认图标作为气泡锚点（与 `NoPermissionPopover.vue` 保持一致的扩展点）。
  - 不传则使用默认警示图标。

### 2.3 不提供 emits

组件纯展示，无事件外抛。

## 3. 状态机

```
                                    当前时间 ≥ offlineAt
                          ┌─────────────────────────────────┐
                          ▼                                 │
[即将下线] ──(到达当日 0 点)──> [今日下线] ──(到达 offlineAt)──> [已下线]
  图标: 橙                      图标: 橙                      图标: 灰
  标题: 即将下线                标题: 即将下线                标题: 已下线
  副文: 距下线还有 N 天         副文: 今日下线                副文: 已下线 N 天
```

"今日下线"判定：`now.toDateString() === offlineAt.toDateString()` 且 `now < offlineAt`。

## 4. 关键实现

### 4.1 时间计算

- `offlineAt` 统一 `new Date(offlineAt)` 解析；若结果为 Invalid Date，组件返回空。
- 使用 `useNow`（自实现，避免引入额外依赖），每分钟刷新一次当前时间。
  - `setInterval(() => now.value = new Date(), 60_000)`，`onUnmounted` 清理。
- 剩余天数：`Math.ceil((offlineAt - now) / (24 * 3600 * 1000))`，仅取日历日差。

### 4.2 Popper 自适应

复用 `NoPermissionPopover.vue` 的 `popperOptions`（flip + fallbackPlacements + preventOverflow + offset），保证窄空间下气泡位置自适应。

### 4.3 样式

- scoped 样式：气泡内部布局（head + body + link）。
- 全局样式（非 scoped）：`offline-notice-popper.el-popper` 覆盖 el-popover 默认白边与阴影，与 `NoPermissionPopover.vue` 同样手法。
- 色板：
  - 警示橙：`#f0883a`（图标）/ `#fff7e6`（head 渐变起点）/ `#ffd6a8`（分割线）
  - 已下线灰：`#86909c`（图标）/ `#f7f8fa`（head 渐变起点）/ `#e5e6eb`（分割线）
  - 文本主色：`#1f2329`，次级文本：`#4e5969`

### 4.4 可访问性

- 图标外层 `<span role="img" :aria-label="...">`，aria-label 包含功能名 + 状态。
- `tabindex="0"` 让键盘可聚焦，聚焦时触发气泡（hover 模式下，Element Plus 的 el-popover 默认对 focus 也响应）。

## 5. 影响范围

### 5.1 新增文件

| 路径                                                                 | 说明                             |
| -------------------------------------------------------------------- | -------------------------------- |
| `apps/web-openlibing/src/components/OfflineNotice.vue`               | 组件本体                         |
| `apps/web-openlibing/src/components/__tests__/OfflineNotice.spec.ts` | 单元测试                         |
| `apps/web-openlibing/src/components/__tests__/setup.ts`（若不存在）  | 测试公共 setup（若已有则不新增） |

### 5.2 修改文件

无。本组件为纯新增，不修改任何现有文件。

### 5.3 接入示例（文档中说明，不实际修改业务页面）

```vue
<template>
  <div class="page-header">
    <h2>漏洞处理</h2>
    <OfflineNotice
      feature-name="漏洞批量忽略"
      offline-at="2026-09-30T00:00:00+08:00"
      description="该能力将整合至「漏洞规则中心」，请提前迁移规则。"
      link="https://internal-docs.example.com/vuln-rule-migration"
    />
  </div>
</template>

<script setup lang="ts">
import { OfflineNotice } from "@/components/OfflineNotice.vue";
</script>
```

## 6. 测试策略

### 6.1 单元测试（Vitest + @vue/test-utils + jsdom）

覆盖用例：

1. **渲染**：传入有效 props，渲染出图标元素，`aria-label` 包含功能名。
2. **即将下线**：`offlineAt` 为未来日期，气泡文案包含"即将下线"与"距下线还有 N 天"。
3. **今日下线**：`offlineAt` 为今日稍晚时间，文案为"今日下线"。
4. **已下线**：`offlineAt` 为过去日期，图标颜色切换、文案为"已下线 N 天"。
5. **空值保护**：`offlineAt` 为空字符串/Invalid Date，组件不渲染（返回注释节点或空 div）。
6. **props 透传**：`description`、`link`、`linkText`、`width`、`placement`、`trigger` 正确透传至 el-popover 或 DOM。
7. **slot 覆盖**：传入 `#reference` slot，使用 slot 内容作为气泡锚点。

### 6.2 手动验证（用户自测）

- 在任一业务页面挂上 `<OfflineNotice>`，启动 `pnpm dev:ob`。
- 验证 hover/click 弹出气泡、文案正确、链接可点击。
- 验证已下线（修改 offlineAt 为过去）状态下图标变灰、文案切换。

## 7. 兼容性与回滚

- 纯新增组件，无破坏性变更。
- 回滚：删除组件文件即可，无残留依赖。

## 8. 开放问题

- 是否需要"已读"持久化（localStorage）？—— 本期不做，后续如需要可在组件外层包一个 wrapper。
- 是否需要后端下发下线清单？—— 本期不做，后端接口就绪后再以 composable 形态接入。
