# 任务：管理中心菜单显隐统一治理 & 下线机机管理

> 分支：`jzcfork/202610managemenu`　提交：`7d21569d`、`0ef3206f`

## 1. 菜单显隐改为路由 meta.auth 驱动

- [x] 删除 `menuShow`、`aiManageShow`、`aiConfigShow`、`argusManageShow`、`opsMenuList`、`opsShow` 等 `computed`
- [x] 新增 `interface MenuItem { name; label }`
- [x] 新增 `interface MenuGroup { key; icon; color; title; children }`
- [x] 新增 `menuGroups: MenuGroup[]`，覆盖组织管理 / 权限管理 / 日志管理 / 运营运维 / AI管理 / 漏洞挖掘管理
- [x] 新增 `collectRouteAuth(routes, map)` 递归收集 `route.name -> route.meta.auth`
- [x] 新增 `routeAuthMap = collectRouteAuth(manageRouter)`
- [x] 新增 `permissions = computed(() => app?.user?.permissions ?? [])`
- [x] 新增 `hasAuth(name)`：无 auth 声明返回 `true`；`permissions` 为空或包含 auth 返回 `true`
- [x] 新增 `visibleGroups`：过滤子项并丢弃空分组
- [x] 模板改为 `v-for="group in visibleGroups"` + `<component :is="group.icon" />`
- [x] 首页入口改 `v-if="hasAuth('manageCenterHome')"`
- [x] 帮助中心入口改 `v-if="hasAuth('helpCenterSetting')"`

## 2. 下线机机管理模块

- [x] 删除 `src/views/machineManagement/account/machineAccount.vue`
- [x] 删除 `src/views/machineManagement/account/permissionDrawer.vue`
- [x] 删除 `src/views/machineManagement/account/promptDialog.vue`
- [x] 删除 `src/views/machineManagement/machineInterface.vue`
- [x] 删除 `src/views/machineManagement/machineLog.vue`
- [x] 删除 `src/api/api.ts` 中机机接口函数
- [x] 删除 `src/api/url.ts` 中机机 URL 常量
- [x] 删除 `src/router/manageRouter.ts` 中机机路由声明
- [x] 删除 `manageCenter/Home/index.vue` 中机机入口卡片
- [x] 删除 `manageCenter/index.vue` 中机机菜单分组

## 3. 验证

- [ ] 超管（权限为空）可见全部 6 个分组与子菜单
- [ ] 仅含日志类 auth 的账号只看到"日志管理"分组，无空分组占位
- [ ] 无任何管理中心 auth 的账号菜单为空且页面正常
- [ ] 逐条核对 `manageRouter` 的 `meta.auth` 与 `menuGroups.children.name` 映射完整
- [ ] 旧机机管理 URL 访问返回 404 / 重定向，无白屏
- [ ] 管理中心首页与帮助中心入口显隐与侧边菜单一致

## 4. 交付

- [ ] `pnpm build` 通过（无残留 import）
- [ ] ESLint / TypeScript 检查通过
- [ ] 发布说明标注机机管理下线
