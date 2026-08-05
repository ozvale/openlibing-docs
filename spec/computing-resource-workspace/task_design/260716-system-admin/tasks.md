# 260610-system-admin - Tasks

## Phase 1: 数据模型与基础设施

- [x] 1.1 创建 Liquibase changelog：`workspace_system_admin` 表
- [x] 1.2 创建实体类：`SystemAdmin`
- [x] 1.3 创建 Mapper：`SystemAdminMapper` 及 XML

## Phase 2: 核心服务

- [x] 2.1 实现 `SystemAdminService`：isAdmin / queryAdmins / addAdmin / removeAdmin
- [x] 2.2 实现缓存层：Redis 缓存 `system:admin` -> `Set<userId>`，TTL 60s，增删时失效
- [x] 2.3 实现 Apollo 自举逻辑：`@Value("${workspace.admin.init-users:}")`，管理员表为空时插入初始管理员
- [x] 2.4 Bootstrap 时从 `workspace_user_info` 回填 userName
- [x] 2.5 增加 `workspace.admin.force-reinit` 配置项，支持清空管理员表重新 bootstrap

## Phase 3: 权限拦截

- [x] 3.1 创建 `@RequireAdmin` 注解
- [x] 3.2 实现 `AdminAuthInterceptor`：校验 `@RequireAdmin` 注解，非管理员返回 403
- [x] 3.3 `WebConfig` 注册 `AdminAuthInterceptor`（在 `OpenlibingAuthInterceptor` 之后）

## Phase 4: 管理接口

- [x] 4.1 `SystemAdminController`：管理员 CRUD（GET /api/admin/query, POST /api/admin/add, POST /api/admin/{id}/delete）
- [x] 4.2 删除自己校验：不能删除当前用户
- [x] 4.3 所有接口添加 `@RequireAdmin`
- [x] 4.4 添加管理员时从 workspace_user_info 回填 userName
- [x] 4.5 删除接口改为 REST 风格 `/{id}/delete`（路径参数替代请求体）

## Phase 5: 前端权限感知

- [x] 5.1 `PermissionController`：`GET /api/permission`，返回 `{isAdmin: true/false}`
- [x] 5.2 从 Token/Cookie 解析 userId，查询管理员缓存

## Phase 6: 集成黑白名单

- [x] 6.1 黑白名单管理接口（`/api/access/**`）添加 `@RequireAdmin` 注解
- [x] 6.2 校验接口（`/api/access/check`）不需要管理员权限

## Phase 7: 三方账号信息统一（合并自 260727-access-list-thirdparty-account）

- [x] 7.1 `workspace-system-admin.xml` 追加 changeSet：`workspace_system_admin` 加 account_platform/account_login
- [x] 7.2 `SystemAdmin` 实体加 accountPlatform/accountLogin 字段
- [x] 7.3 `SystemAdminController.addAdmin` 改用 `AccountUserResolverService` 解析三方账号，请求体改为 accountPlatform + accountLogin
- [x] 7.4 `SystemAdminService.addAdmin` 签名加 accountPlatform/accountLogin（bootstrap 不变）
- [x] 7.5 删除 `SystemAdminController` 中原 resolveUserName/UserInfoMapper

## Phase 8: 操作人记录调整（bedb5f7）

- [x] 8.1 `createdBy` 改存操作人 userName（`UserContext.getUserName()`），前端列表直接展示
- [x] 8.2 日志中 `operatedBy` 仍保留 userId

## 验证

- [x] V1 非管理员访问管理接口返回 403
- [x] V2 管理员正常访问管理接口
- [x] V3 `GET /api/permission` 正确返回 isAdmin
- [x] V4 管理员添加/删除正常
- [x] V5 不能删除自己
- [x] V6 Apollo 自举：空表时自动插入初始管理员
- [x] V7 管理员缓存生效，增删后失效
- [x] V8 黑白名单管理接口需管理员权限
- [x] V9 添加管理员传 accountPlatform + accountLogin 成功
- [x] V10 添加管理员重复 userId 抛 BusinessException
- [x] V11 bootstrap 保持 userId 初始化逻辑不变
