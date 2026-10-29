# 代码仓管理页面操作无权限提示气泡 — 实现任务

## 进度: 0/12 complete

## 后端（framework）

- [ ] Task 1: 新增 DTO（OperationPermissionDTO / RoleByLevelDTO / RoleBriefDTO）
- [ ] Task 2: MenuInfoMapper 新增 `queryAllIdentifications()` + XML SQL
- [ ] Task 3: UserBasicService 新增 `getOperationPermissions()` 方法签名
- [ ] Task 4: UserBasicServiceImpl 实现反查 + 5 级分组 + hasPermission 计算
- [ ] Task 5: UserBasicController 新增 `GET /user/get-operation-permissions` 接口
- [ ] Task 6: 单元测试（4 个用例：全量返回 / 5 级分组 / hasPermission / super_admin）

## 前端（web-openlibing）

- [ ] Task 7: 新建 `src/constants/permissions-meta.ts`，覆盖 Repos 目录所有权限码
- [ ] Task 8: 新增 API（`api/url.ts` + `api/api.ts`）+ store 扩展（`stores/app.ts` 的 `operationPermissions`）
- [ ] Task 9: `Content.vue` 接入新接口（并行调用 + try-catch 降级）
- [ ] Task 10: 新建 `src/components/NoPermissionPopover.vue` 三段式气泡组件
- [ ] Task 11: 改造 Repos 目录 4 个页面（index.vue / branches.vue / repoUserManage.vue / tagManagement.vue）的 canHandle 调用点
- [ ] Task 12: 组件单测 + 跨仓联调验证

## 依赖关系

```
Task 1 → Task 4 → Task 5 → Task 6（后端可独立验证）
Task 2 → Task 4
Task 3 → Task 4

Task 7 → Task 10 → Task 11
Task 8 → Task 9 → Task 11
Task 9 → Task 11

Task 5 + Task 11 → Task 12（跨仓联调）
```

## 执行顺序

1. 先做后端 Task 1-6（framework 独立可测）
2. 再做前端 Task 7-11（web 依赖后端接口契约，可先 mock 联调）
3. 最后 Task 12 跨仓联调
