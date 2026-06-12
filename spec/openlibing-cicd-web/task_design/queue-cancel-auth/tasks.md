# Tasks: 排队Tab取消排队按钮增加权限判断

## 实现步骤

- [x] 1. Queue.vue 引入 `getUserRole` API 和 `TipMemberListComp` 组件
- [x] 2. 添加 `hasAuth` ref（默认 true）和 `getCurrentProjectAuth` 方法
- [x] 3. 在 `projectInfo` watch 中调用 `getCurrentProjectAuth`
- [x] 4. 模板中「取消排队」按钮增加 `v-if="hasAuth"` / `v-else` 权限判断
- [x] 5. 无权限时使用 `TipMemberListComp` 包裹禁用按钮
- [x] 6. Detail.vue 移除 Turing 项目限制，使权限判断对所有项目生效
- [x] 7. Detail.vue / Queue.vue 增加未登录保护（app.user?.userId 为空时跳过 getUserRole）
- [x] 8. ApiClient.ts 提取 `getHostBus()` 和 `navigateToRoute()` 统一路由跳转
- [x] 9. ApiClient.ts 403 处理 needCheck=2 补全路由跳转到 noApplicationPermission
- [x] 10. ApiClient.ts 改善类型安全（sourceTokenMap / loading / timer）
