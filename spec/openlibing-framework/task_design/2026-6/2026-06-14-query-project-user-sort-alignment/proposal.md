## Why

项目成员管理页（`projectUserManage.vue`）对「创建时间」列启用了 Element Plus 服务端排序（`sortable="custom"`），请求体已携带 `sortColumn` / `sortOrder`，但 `openlibing-framework` 的 `query-project-user` 接口未接收这两个字段，SQL 固定 `ORDER BY create_time DESC`。用户点击列头排序无效，且开发者无法本地联调，必须在设计与实现阶段显式对齐前后端契约。

## What Changes

- 在 `UserDTO` 增加可选字段 `sortColumn`、`sortOrder`，与前端 POST body 对齐
- 在 `ProjectUserServiceImpl` 增加白名单映射：前端 camelCase → 数据库 snake_case，Element Plus 排序方向 → SQL `ASC`/`DESC`
- 在 `QueryProjectUserEntity` 增加运行时排序字段（如 `sortDbColumn`、`sortDirection`），供 MyBatis 动态 `ORDER BY` 使用
- 修改 `ProjectUserRoleInfoMapper.xml` 三处列表查询（全量 UNION、按 userId、按三方账号）的 `ORDER BY`，支持按 `create_time` 升序/降序，并保留稳定 tie-breaker
- 补充单元测试，覆盖 sort 参数映射与默认排序行为
- **不修改前端**：前端传参已正确，本变更仅后端对齐

## Capabilities

### New Capabilities

- `project-user-query-sort`: `query-project-user` 接口接收并应用前端 `sortColumn`/`sortOrder`，实现创建时间列服务端排序，与 `projectUserManage.vue` 行为一致

### Modified Capabilities

（无既有 openspec spec）

## Impact

- **API**: `POST /project/user/query-project-user` 请求体新增可选字段，响应结构不变
- **代码**: `UserDTO`、`QueryProjectUserEntity`、`ProjectUserServiceImpl`、`ProjectUserRoleInfoMapper.xml`、`ProjectUserServiceImplTest`
- **前端**: `openlibing-web` `projectUserManage.vue` 无需改动（契约对齐文档见 design.md）
- **数据库**: 无 schema 变更；依赖 `user_role_info.create_time` 与 `project_user_role_info.create_time` 现有列
