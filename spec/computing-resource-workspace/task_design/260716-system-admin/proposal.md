# 260610-system-admin - Proposal

## 需求背景

当前系统没有角色/权限体系，所有通过 JWT 鉴权的用户权限相同。黑白名单管理接口等系统级操作需要管理员权限控制，否则任何登录用户都能修改系统配置。

项目角色（user/admin/owner）是项目级别的，与系统管理员完全不同，不应混杂。

## 功能描述

增加系统管理员角色机制：

1. **管理员表**：`workspace_system_admin`，存储系统管理员 userId/userName 及三方账号快照（accountPlatform/accountLogin）
2. **权限注解**：`@RequireAdmin`，标记需要管理员权限的接口
3. **权限拦截器**：`AdminAuthInterceptor`，校验当前用户是否为管理员
4. **前端权限感知**：`GET /api/permission` 接口，返回 `{isAdmin: true}`，前端控制管理页面可见性
5. **管理员管理**：管理员的增删查（需管理员权限），不能删除自己；添加接口统一使用三方账号信息（accountPlatform + accountLogin），与 addMembers 一致
6. **自举机制**：通过 Apollo 配置 `workspace.admin.init-users` 注入初始管理员（保持 userId 逻辑）
7. **操作人记录**：createdBy 存储操作人 userName（前端列表直接展示），日志中 operatedBy 仍保留 userId

## 验收标准

- [x] `workspace_system_admin` 表创建（含 account_platform/account_login 列）
- [x] `@RequireAdmin` 注解 + `AdminAuthInterceptor` 拦截器
- [x] 拦截器注册在 `OpenlibingAuthInterceptor` 之后
- [x] `GET /api/permission` 返回当前用户是否为管理员
- [x] 管理员 CRUD 接口（GET/POST），需 `@RequireAdmin`
- [x] 不能删除自己
- [x] Apollo `workspace.admin.init-users` 自举逻辑
- [x] 管理员缓存（Redis，TTL 60s，增删时失效）
- [x] 黑白名单管理接口添加 `@RequireAdmin`
- [x] 添加管理员接口改用 accountPlatform + accountLogin（复用 AccountUserResolverService）
- [x] createdBy 改存操作人 userName
- [x] bootstrap 初始化保持 userId 逻辑不变

## 影响范围

- **新增模块**：SystemAdminService、AdminAuthInterceptor、PermissionController、AccountUserResolverService（与黑白名单共用）
- **新增数据表**：`workspace_system_admin`
- **修改**：`WebConfig.java`（注册拦截器+自举逻辑）、黑白名单 Controller（添加注解）
- **前端影响**：应用初始化时调用 `/api/permission`，控制管理页面入口可见性
