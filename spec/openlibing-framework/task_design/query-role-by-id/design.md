# query-role-by-id — 技术设计

## 方案概述

在现有 RoleController 中新增一个 GET 端点，复用已有的 `RoleInfoMapper.queryById()` 和 `RolePermissionMapper.queryByRoleId()` 方法，将角色基础信息与权限菜单 ID 组装后返回。

## 架构决策

| 决策     | 选择                             | 原因                                            |
| -------- | -------------------------------- | ----------------------------------------------- |
| 接口风格 | 延续现有 REST 风格               | 与现有接口保持一致                              |
| 参数校验 | 使用 `@NotNull` + `@Min` 注解    | 与现有 `deleteRole`/`deleteMenu` 的校验方式一致 |
| 异常处理 | 返回 `DataResult.failureMessage` | 与现有角色不存在处理一致                        |

## 涉及文件

| 文件                       | 操作 | 说明                                        |
| -------------------------- | ---- | ------------------------------------------- |
| `RoleController.java`      | 修改 | 新增 `queryRoleById` 端点                   |
| `RoleService.java`         | 修改 | 新增 `queryRoleById` 接口方法声明           |
| `RoleServiceImpl.java`     | 修改 | 新增 `queryRoleById` 实现                   |
| `RoleServiceImplTest.java` | 修改 | 新增 `queryRoleById` 的单元测试（3 个用例） |

## 实现逻辑

### 角色详情查询

```
GET /manage/role/query-role-by-id?id={roleId}

1. 校验入参 id 非空（@NotNull）
2. 调用 roleInfoMapper.queryById(id) 查询角色基础信息
   - 若返回 null → DataResult.failureMessage("角色信息不存在，请核实")
3. 调用 rolePermissionMapper.queryByRoleId(id) 查询权限菜单列表
   - 将 List<RolePermissionEntity> 映射为 List<Integer> menuIds
4. 将 menuIds 设置到 RoleInfoEntity.menuIds
5. 返回 DataResult.successData(roleInfoEntity)
```

## 风险 & 缓解

- 无新增风险，仅复用已有 Mapper 方法

## 跨仓影响

- 无
