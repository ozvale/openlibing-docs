# 技术设计：openlibing-web 功能下线预告组件

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/offline-component`
- **流程模式**：Standard
- **创建日期**：2026-08-24

## 1. 总体方案

新增独立组件 `OfflineNotice.vue`，置于 `apps/web-openlibing/src/components/` 下，与 `NoPermissionPopover.vue` 同级，遵循项目既有组件目录约定。

组件形态：图标 + `el-popover`，与 `NoPermissionPopover.vue` 同样的 slot 透传 + popper-class 全局覆盖模式。

**简化原则**：组件仅提示"即将下线"，不展示下线时间、不计算剩余天数、不区分已下线态。

## 2. 组件 API

### 2.1 Props

```ts
export interface OfflineNoticeProps {
  /** 即将下线的功能名（必填，用于气泡标题与 aria-label） */
  featureName: string;
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
  /** 气泡宽度，默认 280 */
  width?: number;
  /** 图标尺寸，默认 16 */
  iconSize?: number;
  /** 图标颜色，覆盖默认警示橙 */
  iconColor?: string;
  /** 是否禁用气泡 */
  disabled?: boolean;
}
```

### 2.2 Slots

- `#reference`：可选，覆盖默认图标作为气泡锚点（与 `NoPermissionPopover.vue` 保持一致的扩展点）。
  - 不传则使用默认警示图标。

### 2.3 不提供 emits

组件纯展示，无事件外抛。

## 3. 关键实现

### 3.1 标题文案

固定为 `<featureName> 即将下线`，`featureName` 为空时回退为 `该功能 即将下线`。

### 3.2 Popper 自适应

复用 `NoPermissionPopover.vue` 的 `popperOptions`（flip + fallbackPlacements + preventOverflow + offset），保证窄空间下气泡位置自适应。

### 3.3 样式

- scoped 样式：气泡内部布局（head + 可选 body）。
- 全局样式（非 scoped）：`offline-notice-popper.el-popper` 覆盖 el-popover 默认白边与阴影。
- 色板：
  - 警示橙：`#f0883a`（图标）/ `#fff7e6`（head 渐变起点）/ `#ffd6a8`（分割线）
  - 文本主色：`#1f2329`，次级文本：`#4e5969`
- body 仅当 `description` 或 `link` 任一存在时才渲染。

### 3.4 可访问性

- 图标外层 `<span role="img" :aria-label="...">`，aria-label 即标题文案。

## 4. 影响范围

### 4.1 新增文件

| 路径                                                                 | 说明     |
| -------------------------------------------------------------------- | -------- |
| `apps/web-openlibing/src/components/OfflineNotice.vue`               | 组件本体 |
| `apps/web-openlibing/src/components/__tests__/OfflineNotice.spec.ts` | 单元测试 |

### 4.2 修改文件

无。本组件为纯新增，不修改任何现有文件。

### 4.3 接入示例（文档中说明，不实际修改业务页面）

```vue
<template>
  <div class="page-header">
    <h2>漏洞处理</h2>
    <OfflineNotice
      feature-name="漏洞批量忽略"
      description="该能力将整合至「漏洞规则中心」，请提前迁移规则。"
      link="https://internal-docs.example.com/vuln-rule-migration"
    />
  </div>
</template>

<script setup lang="ts">
import OfflineNotice from "@/components/OfflineNotice.vue";
</script>
```

## 5. 测试策略

### 5.1 单元测试（Vitest + @vue/test-utils + jsdom）

覆盖用例：

1. **渲染**：传入 `featureName`，渲染出图标元素，`aria-label` 包含功能名与"即将下线"。
2. **标题文案**：气泡标题为 `<featureName> 即将下线`。
3. **空 featureName 回退**：`featureName` 为空时标题为 `该功能 即将下线`。
4. **description 渲染**：传入 `description`，气泡内显示文案。
5. **link 渲染**：传入 `link`，渲染 `<a target="_blank" rel="noopener noreferrer">`，链接文案默认"了解更多"，可被 `linkText` 覆盖。
6. **body 缺省**：无 `description` 且无 `link` 时，不渲染 body。
7. **仅 link 无 description**：渲染 body 与 link，不渲染 description。
8. **iconColor 自定义**：传入 `iconColor`，图标颜色覆盖默认橙。
9. **iconSize 应用**：传入 `iconSize`，图标尺寸生效。
10. **slot 覆盖**：传入 `#reference` slot，使用 slot 内容作为气泡锚点。

### 5.2 手动验证（用户自测）

- 在任一业务页面挂上 `<OfflineNotice>`，启动 `pnpm dev:ob`。
- 验证 hover/click 弹出气泡、文案正确、链接可点击。

## 6. 兼容性与回滚

- 纯新增组件，无破坏性变更。
- 回滚：删除组件文件即可，无残留依赖。
