# 侧栏「数字化作业 / 数字化运营」切换开关权限动态推导

- 分支：`jzcfork/202610numberoperation`
- 关联提交：`063fe908`

## Why

1. `layouts/basic.vue` 中控制切换开关显隐的权限码 `switchMenuAuth` 是**硬编码三元组**：

   ```ts
   const switchMenuAuth = [
     "engineering_capability_operation",
     "test_resource_consumption",
     "open_source_project",
   ];
   ```

2. 该列表与路由定义（`meta.menuModule === '2'` 的运营菜单）无任何关联，运营侧新增菜单时必须记得回来手改 `basic.vue`，否则新菜单持有者看不到切换开关。
3. 已出现实际缺陷：持有 `test_coverage`、`engineering_security_operation`、`npu_resource` 权限的用户看不到切换开关，无法进入运营菜单。

## What Changes

1. **删除硬编码权限码列表**，改为 `switchMenuAuth: string[] = []` 容器。
2. **新增 `collectSwitchMenuAuth(routes)`**：递归遍历路由，收集 `route.meta?.menuModule === '2'` 且声明了 `route.meta.auth` 的权限码。
3. **从 `#/router/routes` 引入 `accessRoutes`** 并执行一次收集；同时 `import type { RouteRecordRaw } from 'vue-router'`。
4. 原有 `watch(() => app.user.permissions)` 中的 `switchMenuAuth.some(i => set.has(i))` 判定逻辑不变，仅数据来源由字面量变为路由推导。

## Capabilities

### New

- 运营菜单权限码自动从路由元信息推导，新增运营菜单只需声明 `meta.menuModule = '2'` + `meta.auth`。

### Modified

- 侧栏切换开关（`#switch-menu`）的显隐判定数据来源。
- 无运营权限时的降级行为（`menuModule` 回落 `'1'`）保持不变。

### Removed

- `basic.vue` 中硬编码的 3 个运营权限码字面量。

## Impact

### 受影响代码

| 文件                                        | 影响                             |
| ------------------------------------------- | -------------------------------- |
| `apps/web-openlibing/src/layouts/basic.vue` | 权限码改为路由动态收集（+16/-5） |

### 明确不受影响

- `SwitchMenu` 组件本身（切换行为、样式）不变。
- `app.showSwitchMenu` 的消费方（模板 `v-if="app.showSwitchMenu"`）不变。
- 无运营权限用户的降级逻辑（`menuModule: '1'`）不变。

### 风险

- 收集发生在模块加载期（`collectSwitchMenuAuth(accessRoutes)` 顶层调用），要求 `accessRoutes` 为完整静态路由；若后续改为异步路由注册，需调整收集时机。
- 判定条件从"三个固定码"扩展为"全部 `menuModule === '2'` 的路由 auth"，**任何**具备其中一个运营菜单权限的用户都会看到切换开关。这是预期的行为修正，但需确认产品是否接受。
- `switchMenuAuth` 数组为模块级可变状态，重复执行收集（如 HMR）可能重复 push；当前 `accessRoutes` 为常量、模块只加载一次，风险可忽略，但可在实现中加入去重。

## 验证清单

| 场景                                                                     | 期望                                               |
| ------------------------------------------------------------------------ | -------------------------------------------------- |
| 持有 `engineering_capability_operation`                                  | 显示切换开关                                       |
| 持有 `test_coverage` / `engineering_security_operation` / `npu_resource` | 显示切换开关（本次修复项）                         |
| 仅持有普通作业类权限                                                     | 隐藏切换开关，`menuModule` 回落 `'1'`              |
| 新增一个 `menuModule='2'` + `auth='xxx'` 的运营路由                      | 无需改 `basic.vue` 即可对持有 `xxx` 的用户显示开关 |
