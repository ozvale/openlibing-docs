# 设计：切换开关权限动态推导

## Context

主布局 `layouts/basic.vue` 负责渲染侧栏、项目选择、切换开关（`SwitchMenu`）。切换开关用于在"数字化作业"（`menuModule = '1'`）与"数字化运营"（`menuModule = '2'`）两套菜单体系间切换。

是否展示该开关，取决于当前用户是否具备任意一个"运营菜单权限"。此前实现：

```ts
const switchMenuAuth = [
  "engineering_capability_operation",
  "test_resource_consumption",
  "open_source_project",
];
```

该列表与路由定义完全脱耦，属于"第二事实源"。

## Goals / Non-Goals

### Goals

1. 权限码来源唯一：路由 `meta`。
2. 消除硬编码遗漏导致的功能缺陷（`test_coverage` 等权限持有者看不到开关）。
3. 新增运营菜单零改动 `basic.vue`。

### Non-Goals

- 不改变 `SwitchMenu` 组件的切换逻辑与样式。
- 不改变 `app.showSwitchMenu` 的消费方式。
- 不引入新的状态管理或权限存储。

## Decisions

### D1：以 `meta.menuModule === '2'` + `meta.auth` 作为运营菜单的判定标准

```ts
function collectSwitchMenuAuth(routes: RouteRecordRaw[]) {
  routes.forEach((route) => {
    if (route.meta?.menuModule === "2" && route.meta?.auth) {
      switchMenuAuth.push(route.meta.auth);
    }
    if (route.children?.length) collectSwitchMenuAuth(route.children);
  });
}
```

`menuModule` 已是项目内用于区分菜单体系的既有元信息，复用它比新增标记字段成本更低，语义也更准确（"属于运营体系的菜单"）。

### D2：在模块初始化时一次性收集

```ts
import { accessRoutes } from "#/router/routes";
collectSwitchMenuAuth(accessRoutes);
```

`accessRoutes` 是静态路由表常量，模块加载即确定，无需在 `onMounted` 或 `watch` 中重复收集。收集结果被 `watch(..., { immediate: true })` 首次消费时已就绪。

### D3：保持原有交集判定与降级行为

```ts
const set = new Set(value);
const hasAuth = switchMenuAuth.some((i) => set.has(i));
app.showSwitchMenu = Boolean(hasAuth);
if (!hasAuth) menuModuleObj = { menuModule: "1" };
```

- `some + Set` 的复杂度为 O(n)，权限数量有限，无需优化。
- 无运营权限时主动把 `menuModule` 回落 `'1'`，防止用户停留在不可见的运营菜单体系中（原有行为保留）。

### D4：显式声明 `RouteRecordRaw` 类型导入

```ts
import type { RouteRecordRaw } from "vue-router";
```

递归函数的入参需要类型，且 `type` 导入可被完全擦除，不引入运行时依赖。

## 时序

```
模块加载
  ├─ import accessRoutes（静态路由表）
  ├─ collectSwitchMenuAuth(accessRoutes)  -> switchMenuAuth 就绪
  └─ watch(app.user.permissions, { immediate: true })
        ├─ 首次执行（权限可能为空，不处理）
        └─ 权限到达 -> 计算 hasAuth -> 设置 app.showSwitchMenu -> coverPreferences
```

## 涉及文件

| 文件                                        | 操作 | 说明                                               |
| ------------------------------------------- | ---- | -------------------------------------------------- |
| `apps/web-openlibing/src/layouts/basic.vue` | 修改 | 删除硬编码权限码；新增收集函数与调用；补充类型导入 |

## 风险与兼容性

| 风险                                        | 影响 | 应对                                                                      |
| ------------------------------------------- | ---- | ------------------------------------------------------------------------- |
| `accessRoutes` 若改为异步注册，收集时机失效 | 中   | 当前为静态常量；如后续调整路由注册方式需同步调整收集时机                  |
| 开关可见范围扩大到"全部运营菜单权限"        | 中   | 属预期修正；需产品确认是否所有运营权限都应能切换                          |
| 模块级数组在 HMR 下重复 push                | 低   | 可在实现中加去重（`if (!switchMenuAuth.includes(auth))`）；生产构建无影响 |
| `route.meta.auth` 类型可能为 `unknown`      | 低   | 现有 `meta` 类型已声明 `auth?: string`；保持现有类型体系                  |

## 验证策略

1. 分别用持有 `engineering_capability_operation`、`test_coverage`、`engineering_security_operation`、`npu_resource` 的账号登录，切换开关均应显示。
2. 用仅持作业类普通权限的账号登录，开关隐藏，`preferences.sidebar.menuModule` 为 `'1'`。
3. 新增一个临时运营路由（`menuModule='2'` + 新 auth），确认不改 `basic.vue` 即可对持有该 auth 的账号显示开关（验证后可移除）。
4. 切换开关前后，菜单体系切换、`coverPreferences` 落库、刷新后状态保持均正常。
