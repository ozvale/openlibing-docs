# 技术方案

## 方案选型

| 方案                                   | 说明                                                                               | 结论    |
| -------------------------------------- | ---------------------------------------------------------------------------------- | ------- |
| 直接在 menu.ts 内联渲染徽标            | 路由配置文件混入 UI 渲染逻辑，职责不清                                             | ❌      |
| 通过 `meta.extraRender` 挂载函数式组件 | 路由 meta 携带渲染入口，由 menu-item 的 `<component :is>` 统一渲染，配置与渲染解耦 | ✅ 采用 |

## 实现设计

1. `menu.ts` 导入 `h`（vue）与通用组件 `OfflineNotice`。
2. 定义函数式渲染器：

```ts
const testManagementOfflineNotice = () => h(OfflineNotice);
```

3. 在「测试管理」菜单项 `meta` 上挂载：

```ts
meta: {
  title: '测试管理',
  icon: getIcon(testDesign),
  extraRender: testManagementOfflineNotice,
}
```

## 关键点

- `OfflineNotice` 是纯 props 驱动的通用下线预告组件（默认深灰图标 + hover popover + 可选 description/link），视觉交互对齐 `NoPermissionPopover.vue`，此处无 props 使用默认行为。
- 函数式组件形式返回 VNode，避免路由配置在模块加载时立即实例化组件。

## 影响范围

| 文件                                                    | 变更                                |
| ------------------------------------------------------- | ----------------------------------- |
| `apps/web-openlibing/src/router/routes/modules/menu.ts` | +11 行：导入、渲染器定义、meta 挂载 |

仅菜单展示层，不影响路由跳转、鉴权与其他菜单项。

## 验证设计

- 本地 dev 启动后观察侧边栏「测试管理」菜单：图标旁出现灰色预告徽标，hover 出现气泡；点击菜单仍正常跳转。
- 回归相邻菜单项渲染正常。
