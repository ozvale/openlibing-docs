# query-role-by-id — 实现任务

## 进度: 7/7 complete

- [x] Task 1: RoleService 接口新增 `queryRoleById(Integer id)` 方法声明
- [x] Task 2: RoleServiceImpl 实现 `queryRoleById` 逻辑（查询角色 + 权限组装）
- [x] Task 3: RoleController 新增 `queryRoleById` GET 端点
- [x] Task 4: RoleServiceImplTest 新增 `queryRoleById` 单元测试（3 个用例：成功/角色不存在/角色存在但无权限）
- [x] Task 5: MenuUrlInfoMapper 新增 `queryByRoleId` 方法 + XML JOIN 查询 SQL
- [x] Task 6: MenuService 接口 + MenuServiceImpl 实现 `queryMenuUrlByRole` 方法
- [x] Task 7: MenuController 新增 `queryMenuUrlByRole` GET 端点