# query-role-by-id — 角色详情查询

## 需求背景

管理中心-角色管理目前缺少按角色 ID 查询角色详情及权限信息的接口，无法在前端展示单个角色的完整信息（含可访问菜单权限）。

## 功能描述

### 角色详情查询

RoleController 新增 GET 接口 `queryRoleById`，根据角色 ID 查询：

1. 角色基础信息（通过 `RoleInfoMapper.queryById`）
2. 角色权限菜单信息（通过 `RolePermissionMapper.queryByRoleId`）

### 做什么

- RoleController 新增 `queryRoleById` 端点，GET 请求，入参角色 ID（非空校验）
- RoleService 接口新增 `queryRoleById` 方法
- RoleServiceImpl 实现：查询角色基础信息 + 权限信息，组装到 RoleInfoEntity.menuIds 返回
- 返回 `DataResult<RoleInfoEntity>`

### 不做什么

- 不改动数据模型
- 不改动现有 CRUD 接口
- 不涉及权限校验逻辑变更

## 验收标准

- [x] 提供 `GET /manage/role/query-role-by-id` 接口，入参 `id` 校验非空
- [x] 正确返回角色基础信息 + 关联的菜单权限 ID 列表
- [x] 角色 ID 不存在时返回 `DataResult.failureMessage("角色信息不存在，请核实")`
- [x] 单元测试覆盖正常场景和异常场景

## 影响范围

- 仓：openlibing-framework（单仓）
- 模块：角色管理（RoleController / RoleService / RoleServiceImpl）
