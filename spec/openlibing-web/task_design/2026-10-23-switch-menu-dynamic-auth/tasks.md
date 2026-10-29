# 任务：切换开关权限动态推导

> 分支：`jzcfork/202610numberoperation`　提交：`063fe908`

## 1. 删除硬编码权限码

- [x] 移除 `basic.vue` 中 `switchMenuAuth = ['engineering_capability_operation','test_resource_consumption','open_source_project']`
- [x] 改为 `const switchMenuAuth: string[] = []`

## 2. 路由动态收集

- [x] 新增 `collectSwitchMenuAuth(routes: RouteRecordRaw[])`，收集 `route.meta?.menuModule === '2'` 且存在 `route.meta?.auth` 的 auth
- [x] 支持 `route.children` 递归
- [x] 调用 `collectSwitchMenuAuth(accessRoutes)`
- [x] `import type { RouteRecordRaw } from 'vue-router'`
- [x] `import { accessRoutes } from '#/router/routes'`

## 3. 保持既有判定与降级

- [x] `watch(() => app.user.permissions)` 中维持 `some + Set` 交集判定
- [x] `app.showSwitchMenu = Boolean(hasAuth)` 逻辑不变
- [x] 无权限时 `menuModule` 回落 `'1'` 逻辑不变

## 4. 验证

- [ ] 持有 `engineering_capability_operation` 账号显示开关
- [ ] 持有 `test_coverage` / `engineering_security_operation` / `npu_resource` 账号显示开关（本次修复项）
- [ ] 仅持作业类普通权限账号隐藏开关，`menuModule` 为 `'1'`
- [ ] 新增临时 `menuModule='2'` 运营路由后，不改 `basic.vue` 即可对持有该 auth 的账号显示开关
- [ ] 切换开关后菜单体系切换、`coverPreferences` 落库、刷新保持正常

## 5. 交付

- [ ] ESLint / TypeScript 检查通过
- [ ] 运营与作业两套菜单体系冒烟通过
