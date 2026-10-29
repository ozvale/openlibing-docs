# 设计：管理中心菜单显隐统一治理 & 下线机机管理

## Context

`manageCenter/index.vue` 是管理中心的容器页，侧边菜单由 `el-menu` + `el-sub-menu` 手写，每个分组的显隐各对应一个 `computed`：

```
menuShow / aiManageShow / aiConfigShow / argusManageShow / opsMenuList / opsShow
```

这些 `computed` 直接读取 `app.user.permissions` 并做 `includes` 判断，权限码以字符串字面量硬编码在模板中。与此同时，`router/manageRouter.ts` 已经为每条路由声明了 `meta.auth`，`router/guard.ts` 也在用同一份 `meta.auth` 做路由级拦截——两套规则并存，必然漂移。

机机管理是独立业务模块（机机账号、机机接口权限、机机日志），产品侧已确认下线。

## Goals / Non-Goals

### Goals

1. 管理中心菜单显隐只有一个判定入口：`hasAuth(routeName)`。
2. 判定语义与 `router/guard.ts` 完全一致（超管空权限全可见 + auth 命中可见 + 无 auth 声明默认可见）。
3. 菜单结构由数据（`menuGroups`）驱动，新增菜单不改模板逻辑。
4. 完整移除机机管理模块前端代码与路由/接口。

### Non-Goals

- 不改造 `router/guard.ts` 与后端权限模型。
- 不改变管理中心的视觉样式与布局（分组图标、配色保持不变）。
- 不为机机管理提供迁移或兼容入口。

## Decisions

### D1：以路由 `meta.auth` 为唯一权限来源

权限码不再写在 `manageCenter/index.vue`，而是从 `manageRouter` 递归读取：

```ts
function collectRouteAuth(routes, map = new Map()) {
  routes.forEach((route) => {
    if (route.name && route.meta?.auth)
      map.set(String(route.name), String(route.meta.auth));
    if (route.children?.length) collectRouteAuth(route.children, map);
  });
  return map;
}
const routeAuthMap = collectRouteAuth(manageRouter);
```

优点：权限码只存在于路由声明一处；菜单与路由天然对齐。

### D2：`hasAuth` 保持与 guard 一致的三段语义

```ts
function hasAuth(name: string): boolean {
  const auth = routeAuthMap.get(name);
  if (!auth) return true; // 路由未声明 auth -> 不限制
  const list = permissions.value;
  return list.length === 0 || list.includes(auth); // 空权限=超管
}
```

与 `router/guard.ts` 的判定必须同步演进；后续若 guard 语义变化，本函数需同步。

### D3：声明式 `menuGroups` 取代 6 组 `computed`

```ts
interface MenuGroup {
  key: string;
  icon: Component;
  color: string;
  title: string;
  children: MenuItem[];
}
```

分组为组织管理、权限管理、日志管理、运营运维、AI管理、漏洞挖掘管理。`children[].name` 即路由 `name`。模板：

```html
<el-sub-menu
  v-for="group in visibleGroups"
  :key="group.key"
  :index="group.key"
></el-sub-menu>
```

`visibleGroups` 先过滤子项、再丢弃空分组，避免出现"空分组"占位。

### D4：首页/帮助中心入口纳入同一判定

`manageCenter/Home/index.vue` 的入口卡片与侧边菜单同源，改为 `hasAuth('manageCenterHome')` / `hasAuth('helpCenterSetting')`，消除两处不同步。

### D5：机机管理按"页面 -> 接口 -> 路由 -> 入口"顺序整体删除

删除范围（自底向上）：

| 层   | 内容                                                                                                                               |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 页面 | `src/views/machineManagement/account/{machineAccount,permissionDrawer,promptDialog}.vue`、`machineInterface.vue`、`machineLog.vue` |
| 接口 | `src/api/api.ts` 机机函数、`src/api/url.ts` 机机常量                                                                               |
| 路由 | `src/router/manageRouter.ts` 机机路由                                                                                              |
| 入口 | `manageCenter/Home/index.vue` 卡片、`manageCenter/index.vue` 分组                                                                  |

先删页面可让未清理的 import 在构建期暴露，避免遗漏。

## 交互矩阵

| 用户权限                   | 路由是否声明 auth | 菜单                               | 首页入口             |
| -------------------------- | ----------------- | ---------------------------------- | -------------------- |
| `permissions = []`（超管） | 声明/未声明       | 全部可见                           | 全部可见             |
| 含 `auth_x`                | `auth_x`          | 该菜单可见                         | 若声明同 auth 则可见 |
| 不含 `auth_x`              | `auth_x`          | 隐藏；分组下无其他可见项则整组隐藏 | 隐藏                 |
| 任意                       | 未声明            | 可见                               | 可见                 |

## 后端接口契约

无变更。机机管理删除后，前端不再调用其接口。

## 涉及文件

| 文件                                                                           | 操作 | 说明                                                                                  |
| ------------------------------------------------------------------------------ | ---- | ------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/manageCenter/index.vue`                         | 修改 | 新增 `MenuGroup` 配置与 `hasAuth`/`visibleGroups`；删除 6 组 `computed`；删除机机分组 |
| `apps/web-openlibing/src/views/manageCenter/Home/index.vue`                    | 修改 | 删除机机入口卡片                                                                      |
| `apps/web-openlibing/src/router/manageRouter.ts`                               | 修改 | 删除机机路由声明                                                                      |
| `apps/web-openlibing/src/api/api.ts`                                           | 修改 | 删除机机接口函数                                                                      |
| `apps/web-openlibing/src/api/url.ts`                                           | 修改 | 删除机机 URL 常量                                                                     |
| `apps/web-openlibing/src/views/machineManagement/account/machineAccount.vue`   | 删除 | 机机账号管理页                                                                        |
| `apps/web-openlibing/src/views/machineManagement/account/permissionDrawer.vue` | 删除 | 机机权限抽屉                                                                          |
| `apps/web-openlibing/src/views/machineManagement/account/promptDialog.vue`     | 删除 | 机机提示弹窗                                                                          |
| `apps/web-openlibing/src/views/machineManagement/machineInterface.vue`         | 删除 | 机机接口管理页                                                                        |
| `apps/web-openlibing/src/views/machineManagement/machineLog.vue`               | 删除 | 机机日志页                                                                            |

## 风险与兼容性

| 风险                                                  | 影响               | 应对                                                                                               |
| ----------------------------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------- |
| `menuGroups.children[].name` 与路由 `name` 拼写不一致 | 高（菜单异常显隐） | 代码审查 + 建议后续用类型约束；`hasAuth` 对未命中的 name 走"无 auth -> 可见"分支，可降低误隐藏概率 |
| `permissions` 空数组即超管，与后端定义漂移            | 中                 | 与后端确认语义；此逻辑与 guard 已有实现一致，不新增风险                                            |
| 机机管理书签/外链直接访问 404                         | 低                 | 发布说明标注下线                                                                                   |
| 删除后残留 import 导致构建失败                        | 低                 | 构建期暴露，按报错清理                                                                             |
| 分组图标/配色被误改                                   | 低                 | 迁移时保持 `icon`/`color` 原值                                                                     |

## 验证策略

1. 超管账号（`permissions = []`）登录，管理中心 6 个分组与全部子菜单可见，首页入口全部可见。
2. 构造仅含 `log` 相关 auth 的账号，仅"日志管理"分组可见，其余分组隐藏且无空分组占位。
3. 构造不含任何管理中心 auth 的账号，管理中心菜单为空但页面不报错。
4. 逐条核对 `manageRouter` 中 `meta.auth` 与 `menuGroups.children.name` 映射完整（脚本或人工对表）。
5. 直接访问 `/manageCenter/machine*` 旧 URL 应 404 或重定向到首页，不出现白屏。
6. 管理中心首页、帮助中心入口显隐与侧边菜单一致。
