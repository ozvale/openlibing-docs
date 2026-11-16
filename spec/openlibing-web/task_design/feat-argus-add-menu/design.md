# 技术方案

## 方案选型

与既有 argus 管理页面接入方式完全一致：`WujieMiddlewareComponent` + 路由 meta.url 指向子应用页面 + `auth` 权限码控制。不引入新接入方式。

## 实现设计

1. **路由注册**（`manageRouter.ts` argusManager 路由组）：

```ts
{
  name: 'accessControl',
  path: '/manageCenter/argus-access-control',
  component: WujieMiddlewareComponent,
  meta: {
    title: '用户白名单',
    url: import.meta.env.DEV
      ? `https://localhost.beta.openlibing.com:5173/argus/access-control`
      : `${import.meta.env.VITE_APP_OPENLIBING_URL}/argus/access-control`,
    noKeepAlive: true,
    auth: 'argus_manage',
  },
}
```

- dev/prod 双环境 url，对齐同组 dashboard、projects 等路由的既有写法。
- `noKeepAlive: true`：白名单页数据需实时刷新，不保留缓存实例。

2. **菜单注册**（`manageCenter/index.vue` 「漏洞挖掘」菜单分组）：`{ name: 'accessControl', label: '用户白名单' }`，置于「调度配置」与「审计日志」之间。

3. **首页能力卡片**（`manageCenter/Home/index.vue` 「漏洞挖掘」capabilities）：`routes` 数组追加 `'accessControl'`。

## 关键点

- 权限沿用 `argus_manage`，不新增权限码；无权限时路由守卫（guard.ts）拦截。
- 子应用侧页面已存在，本改动仅为主应用导航接入，不涉及子应用改动（符合无痕接入子应用约定：不改主应用打包配置、不在子应用内做主应用业务）。

## 影响范围

| 文件                                                        | 变更              |
| ----------------------------------------------------------- | ----------------- |
| `apps/web-openlibing/src/router/manageRouter.ts`            | +13 行路由        |
| `apps/web-openlibing/src/views/manageCenter/index.vue`      | +1 行菜单项       |
| `apps/web-openlibing/src/views/manageCenter/Home/index.vue` | routes 数组 +1 项 |

## 验证设计

- 有 `argus_manage` 权限：菜单可见、点击加载 Wujie 子应用页面。
- 无权限：菜单不展示，直接访问 URL 被路由守卫拦截。
- 回归同组既有 argus 菜单（仪表盘/项目管理/调度配置/审计日志）跳转正常。
