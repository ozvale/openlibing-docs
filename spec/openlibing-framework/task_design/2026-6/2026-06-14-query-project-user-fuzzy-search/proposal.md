## Why

项目成员管理页（`projectUserManage.vue`）通过 `ContactInformation` 组件在失焦/回车时以 `accountLogin` 筛选成员列表，但 `query-project-user` 接口当前对 **gitcode / gitee / openubmc** 等三方账号使用精确匹配（`account_login = ?`），且 Service 层先经 `commonService.getUser()` 做精确 `queryByLogin` 解析 userId 再分流查询。用户输入部分关键字无法命中结果，与前端「保留 change 触发、不新增联想接口」的模糊筛选预期不一致。

**uniportal 账号保持现网精确逻辑不变**（`getUser` 精确解析、`errorMsg` 失败返回、`queryProjectUserByUserIdLimit` 等）。

## What Changes

- `POST /project/user/query-project-user` 在 `accountPlatform` 为 **gitcode / gitee / openubmc**（非 uniportal）且携带 `accountLogin` 时，对账号条件改为**包含匹配**（SQL `LIKE %keyword%`），返回所有匹配的项目成员记录
- 上述三方平台列表筛选**不再依赖** `commonService.getUser()` 的精确解析结果来决定查询路径；改为统一的模糊过滤 UNION 查询
- **uniportal 平台完全保留原逻辑**：仍走 `getUser` 精确 `queryByLogin` → 有 `userId` 走 `queryProjectUserByUserIdLimit`；解析失败仍返回 `failureMessage`
- 请求/响应契约不变：仍使用 `UserDTO` 现有字段（`accountLogin`、`accountPlatform`、`projectId`、`userRole`、分页、排序等）
- 不新增联想/suggest 接口；不修改前端代码

## Capabilities

### New Capabilities

- `project-user-account-fuzzy-search`: `query-project-user` 接口在 **非 uniportal** 账号筛选场景下支持 `accountLogin` 模糊匹配，覆盖 `user_role_info`（已登录 openLiBing 用户）与 `project_user_role_info`（未登录三方账号）两条数据源

### Modified Capabilities

（无——`openspec/specs/` 下尚无已归档的 project-user 相关 spec）

## Impact

- **API**: `POST /openlibing-framework/project/user/query-project-user`（行为变更：三方平台精确 → 模糊；uniportal 不变）
- **Service**: `ProjectUserServiceImpl.queryProjectUser` 查询路径分流逻辑（按平台分支）
- **Mapper**: `ProjectUserRoleInfoMapper.xml`（`userQueryWithConditions`、`projectUserQueryWithConditions` 及对应 count；不含 uniportal 模糊条件）
- **测试**: `ProjectUserServiceImplTest` 补充三方平台模糊匹配用例；uniportal 现有用例保持/回归
- **前端**: `openlibing-web` 无需改动（`getCommunityUser` 请求体不变）
- **关联系统**: 仅影响通过 `query-project-user` 做列表筛选的调用方；`queryCommitterInfo` 等精确查人接口不在范围内
