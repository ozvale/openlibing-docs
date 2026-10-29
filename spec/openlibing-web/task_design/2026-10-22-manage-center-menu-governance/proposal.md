# 管理中心菜单显隐统一治理 & 下线机机管理模块

- 分支：`jzcfork/202610managemenu`
- 关联提交：`7d21569d`（菜单显隐 meta.auth 驱动）、`0ef3206f`（下线机机管理）

## Why

1. **菜单显隐规则分散且易漂移**：`manageCenter/index.vue` 为每个分组各维护一个 `computed`（`menuShow`、`aiManageShow`、`aiConfigShow`、`argusManageShow`、`opsShow`、`opsMenuList`），每新增一个受权限控制的菜单就要再加一个判断，硬编码权限码散落在模板与脚本中，与 `router/guard.ts` 的鉴权语义不一致。
2. **首页入口与侧边菜单各自判断**：`Home/index.vue` 里的入口卡片需要独立维护显隐，容易与侧边菜单不同步。
3. **机机管理模块整体下线**：`machineManagement/` 下的机机账号、机机接口、机机日志等页面及对应 API/路由已无使用场景，保留会带来维护成本与潜在安全面。

## What Changes

1. **显隐改为路由 meta.auth 单一来源**

   - 定义 `interface MenuItem { name; label }` 与 `interface MenuGroup { key; icon; color; title; children }`。
   - 用 `menuGroups: MenuGroup[]` 声明式描述分组（组织管理 / 权限管理 / 日志管理 / 运营运维 / AI管理 / 漏洞挖掘管理），`children[].name` 与路由 `name` 一一对应。
   - 新增 `collectRouteAuth(routes, map)` 递归遍历 `manageRouter`，产出 `name -> meta.auth` 的 `routeAuthMap`。
   - `permissions = computed(() => app?.user?.permissions ?? [])`。
   - `hasAuth(name)`：路由未声明 `auth` 时返回 `true`；否则 `permissions` 为空数组（超管语义）或包含该 auth 时返回 `true`（与 `router/guard.ts` 判定保持一致）。
   - `visibleGroups`：对每个分组过滤子项，分组下无可见子项则整组隐藏。
   - 模板改为 `v-for="group in visibleGroups"` + `<component :is="group.icon" />`；首页与帮助中心入口改为 `v-if="hasAuth('manageCenterHome')"` / `v-if="hasAuth('helpCenterSetting')"`。
   - 删除原有 6 组 `computed` 判断。

2. **下线机机管理模块**
   - 删除 `src/views/machineManagement/` 下全部页面：`account/machineAccount.vue`、`account/permissionDrawer.vue`、`account/promptDialog.vue`、`machineInterface.vue`、`machineLog.vue`。
   - 删除 `src/api/api.ts` 中机机相关接口函数、`src/api/url.ts` 中对应 URL 常量。
   - 删除 `src/router/manageRouter.ts` 中机机路由声明。
   - 删除 `manageCenter/Home/index.vue` 中机机入口卡片、`manageCenter/index.vue` 中机机菜单分组。

## Capabilities

### New

- 管理中心菜单显隐由"路由声明 + 用户权限"自动推导，新增菜单只需在路由上声明 `meta.auth` 与在 `menuGroups` 中登记，无需写显隐逻辑。

### Modified

- 管理中心侧边菜单、首页入口、帮助中心入口的显隐来源统一为 `hasAuth()`。
- `manageCenter/index.vue` 由命令式判断改为声明式分组配置。

### Removed

- 机机管理模块全部前端页面（账号管理、接口管理、日志管理）。
- 机机相关 API 函数、URL 常量与路由。
- 管理中心中机机管理菜单分组与首页入口。

## Impact

### 受影响代码

| 文件                                                        | 影响                                             |
| ----------------------------------------------------------- | ------------------------------------------------ |
| `apps/web-openlibing/src/views/manageCenter/index.vue`      | 菜单显隐重构（+155/-150），并删除机机分组（-12） |
| `apps/web-openlibing/src/views/manageCenter/Home/index.vue` | 删除机机入口卡片（-8）                           |
| `apps/web-openlibing/src/router/manageRouter.ts`            | 删除机机路由（-41）                              |
| `apps/web-openlibing/src/api/api.ts`                        | 删除机机接口函数（-24）                          |
| `apps/web-openlibing/src/api/url.ts`                        | 删除机机 URL 常量（-24）                         |
| `apps/web-openlibing/src/views/machineManagement/**`        | 整目录删除（5 文件，-1402）                      |

### 明确不受影响

- `router/guard.ts` 的路由级鉴权逻辑不变，本改动是让菜单显隐与其语义对齐。
- 其他业务模块（SCA、发布、待办中心等）的菜单与路由不变。
- 后端接口不变（仅前端不再调用机机接口）。

### 风险

- `hasAuth` 依赖路由 `name` 与 `menuGroups.children[].name` 严格一致，拼写错误会导致菜单永久隐藏或永久显示。需以类型 + 代码审查约束。
- 删除机机模块后，若有外部系统通过 URL 直达机机页面将得到 404（预期行为，需在发布说明中标注）。
- `permissions` 为空数组时视为"全可见"（超管语义），需与后端权限模型保持一致。

## 后续建议

- 可在 `MenuItem.name` 上引入路由 `name` 的联合类型（或从 `manageRouter` 推导），把"名称漂移"从运行时问题降级为编译期问题。
