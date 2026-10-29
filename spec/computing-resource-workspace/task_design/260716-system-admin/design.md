# 260610-system-admin — 系统管理员角色设计文档

## 1. 需求概述

为 computing-resource-workspace 增加系统管理员角色机制，用于控制管理类接口的访问权限（如黑白名单管理、用户管理等）。

**与黑白名单的关系**：黑白名单管理接口需要管理员权限，但管理员角色本身是独立的通用能力，不应耦合在黑白名单设计中。

## 2. 现状分析

当前系统没有角色/权限体系：
- 所有通过 JWT 鉴权的用户权限相同
- 没有管理员概念，任何登录用户都能访问所有接口
- `AuthInterceptor` 有白名单机制，但那是 HiDevLab 权限体系，与本项目无关
- 项目角色（user / admin / owner）是项目级别的，与系统管理员完全不同

**项目角色 vs 系统管理员**：

| 维度 | 项目角色（user/admin/owner） | 系统管理员 |
|------|---------------------------|-----------|
| 作用范围 | 单个项目 | 全局（跨项目） |
| 管理对象 | 项目内资源 | 系统级配置（黑白名单、用户管理等） |
| 存储位置 | HiDevLab 权限体系 | 本项目 `workspace_system_admin` 表 |
| 前端页面 | 项目详情页 | 系统管理页（独立入口） |

系统管理员与项目角色完全独立，不应混杂。

## 3. 设计方案

### 3.1 数据模型

#### `workspace_system_admin`（系统管理员表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT AUTO_INCREMENT | 主键 |
| `user_id` | VARCHAR(128) | userId |
| `user_name` | VARCHAR(128) | 用户名（展示用） |
| `account_platform` | VARCHAR(64) | 三方平台（添加时快照，NULL） |
| `account_login` | VARCHAR(128) | 三方登录名（添加时快照，NULL） |
| `created_by` | VARCHAR(64) | 操作人 userName |
| `created_at` | DATETIME | 创建时间 |

**索引**：
- `uk_admin_user` UNIQUE (`user_id`) - 每个用户只能有一条管理员记录

**设计决策**：
- 管理员表独立，不引入复杂角色体系（如 RBAC）
- 当前只有一种角色：系统管理员
- 不做权限分级，管理员拥有所有管理权限
- 管理员表的增删由现有管理员操作（自举问题见 3.3）
- `created_by` 存储操作人 userName（非 userId），前端列表直接展示；日志中 `operatedBy` 仍保留 userId
- `account_platform`/`account_login` 为添加时的三方账号快照，仅展示用，权限判断不依赖；bootstrap 初始化的记录为 NULL

### 3.2 管理员判断逻辑

```java
@Service
public class SystemAdminService {

    /**
     * 判断用户是否为系统管理员
     */
    public boolean isAdmin(String userId) {
        // 查缓存 → 查库
    }

    /**
     * 获取所有管理员（分页）
     */
    public PageResult<SystemAdmin> queryAdmins(int page, int size) { ... }

    /**
     * 添加管理员
     */
    public void addAdmin(String userId, String userName, String accountPlatform,
                         String accountLogin, String operatedBy) { ... }

    /**
     * 移除管理员
     */
    public void removeAdmin(Long id, String operatedBy) { ... }
}
```

**缓存策略**：
- Redis 缓存，Key：`system:admin` → `Set<userId>`，TTL 60s
- 增删时主动失效缓存

### 3.3 自举问题（第一个管理员如何产生）

系统首次部署时管理员表为空，需要一种方式创建第一个管理员。

**方案**：通过 Apollo 配置注入初始管理员。

```java
@Value("${workspace.admin.init-users:}")
private String initAdminUsers;

@Value("${workspace.admin.force-reinit:false}")
private boolean forceReinit;
```

Apollo 配置项：

| 配置项 | 说明 | 示例 |
|-------|------|------|
| `workspace.admin.init-users` | 初始管理员 userId 列表（逗号分隔） | `u-20250601xxxx,u-20250602yyyy` |
| `workspace.admin.force-reinit` | 强制重新初始化（清空管理员表并重新 bootstrap） | `true` |

**启动时逻辑**：
1. 检查 `force-reinit` 是否为 true → 是则清空管理员表
2. 检查管理员表是否为空
3. 为空时，读取 `workspace.admin.init-users` 配置
4. 对每个 userId，尝试从 `workspace_user_info` 表回填 userName（新环境可能为 null）
5. 将配置中的用户插入管理员表
6. 管理员表非空时，忽略此配置

**userName 回填链路**：
- 新环境首次部署时，`workspace_user_info` 表为空，bootstrap 只能写入 userId，userName 为 null
- 首个管理员登录后，`OpenlibingAuthInterceptor.triggerUserInfoSync()` → `UserInfoSyncService.syncOnRequest()` 会写入 `workspace_user_info`
- 同时 `UserInfoSyncService.updateUserNameInBusinessTables()` 会顺带回填管理员表的 userName
- 后续添加其他管理员时，`SystemAdminController.addAdmin()` 会从 `workspace_user_info` 查询并回填 userName

**安全考虑**：
- 此配置仅在管理员表为空时生效，不会覆盖已有管理员
- 生产环境通过 Apollo 动态配置注入，不硬编码在配置文件中
- 初始管理员登录后应立即通过管理接口添加其他管理员，然后可移除配置
- **如果 userId 填错导致系统锁死**：在 Apollo 中设置 `workspace.admin.force-reinit=true`，重启服务后会清空管理员表并重新 bootstrap。bootstrap 成功后务必将 `force-reinit` 改回 `false`

### 3.4 管理员注解

提供 `@RequireAdmin` 注解，用于标记需要管理员权限的接口：

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface RequireAdmin {
}
```

**拦截器实现**：

```java
@Component
public class AdminAuthInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        if (handler instanceof HandlerMethod handlerMethod) {
            RequireAdmin requireAdmin = handlerMethod.getMethodAnnotation(RequireAdmin.class);
            if (requireAdmin != null) {
                String userId = UserContext.resolveUserId(null);
                if (!systemAdminService.isAdmin(userId)) {
                    // 返回 403
                    response.setStatus(403);
                    response.setContentType("application/json;charset=UTF-8");
                    response.getWriter().write("{\"code\":403,\"msg\":\"需要管理员权限\"}");
                    return false;
                }
            }
        }
        return true;
    }
}
```

**注册顺序**：在 `OpenlibingAuthInterceptor` 之后，确保 UserContext 已设置。

### 3.5 前端权限感知接口

前端需要知道当前用户是否为系统管理员，以决定是否展示管理页面入口。

**设计原则**：
- 前端只负责**页面可见性**（展示/隐藏管理入口），不负责权限控制
- 后端通过 `@RequireAdmin` 注解做**真正的权限拦截**
- 前端调用一次即可，后续权限校验全靠后端

**接口设计**：

```
GET /api/permission
```

**请求参数**：无（从当前请求的 Token/Cookie 解析 userId）

**响应**：

```json
{
  "code": 200,
  "data": {
    "isAdmin": true
  }
}
```

**设计决策**：
- 独立于黑白名单校验接口（`/api/access/check`），因为两者职责不同：
  - `/api/permission`：返回当前用户的**角色/权限信息**（前端页面控制用）
  - `/api/access/check`：返回当前用户的**访问控制状态**（是否被黑白名单拦截）
- 使用 `isAdmin` 而非 `role` 字段，因为当前只有一种角色。后续如需权限分级（如超级管理员），可扩展为：

```json
{
  "code": 200,
  "data": {
    "isAdmin": true,
    "role": "SUPER_ADMIN"
  }
}
```

- 前端在应用初始化时调用一次，缓存结果，用于控制管理页面的可见性
- 后续所有管理操作的权限校验仍由后端 `@RequireAdmin` 拦截器执行，前端不参与权限判断

### 3.6 管理员管理接口

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 分页查询 | GET | `/api/admin/query` | |
| 添加 | POST | `/api/admin/add` | |
| 删除 | POST | `/api/admin/{id}/delete` | |

所有接口都需要 `@RequireAdmin` 注解。

**添加请求体**（统一使用三方账号信息，与 addMembers 一致；由 `AccountUserResolverService` 解析出 userId）：

```json
{
  "accountPlatform": "gitcode",
  "accountLogin": "zhangsan",
  "userName": "张三"
}
```

> **设计变更（合并自 260727）**：原设计前端直接传 userId，改为传 accountPlatform + accountLogin，后端通过 `AccountUserResolverService` 调用 `FrameworkUserQueryService` 解析 userId 并同步 user_info。bootstrap 初始化仍保持 userId 逻辑（从 Apollo 配置读取）。

**删除路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 管理员记录 ID |

**注意**：不能删除自己（防止最后一个管理员把自己删了导致无管理员）。

**userName 回填机制**：添加管理员时，若 `userName` 为空，后端从 `workspace_user_info` 表抓取；若用户未登录过则 userName 为 null，待用户首次登录触发 `UserInfoSyncService` 同步时自动回填至管理员表。

## 4. 与黑白名单的集成

黑白名单管理接口（`/api/access/**`）添加 `@RequireAdmin` 注解：

```java
@RestController
@RequestMapping("/api/access")
public class AccessControlController {

    @RequireAdmin
    @PostMapping("/whitelist/add")
    public DataResult<?> addWhitelist(@RequestBody AccessWhitelistRequest request) { ... }

    @RequireAdmin
    @PostMapping("/whitelist/delete")
    public DataResult<?> deleteWhitelist(@RequestBody Map<String, Long> params) { ... }

    // ...
}
```

校验接口（`/api/access/check`）不需要管理员权限，任何已登录用户都可以查询自己的访问状态。

## 5. 涉及文件清单

### 5.1 新增文件

| 文件 | 说明 |
|------|------|
| `db/changelog/v1.0.0/workspace-system-admin.xml` | Liquibase 建表 |
| `entity/SystemAdmin.java` | 管理员实体 |
| `mapper/SystemAdminMapper.java` | 管理员 Mapper |
| `mapper/xml/SystemAdminMapper.xml` | 管理员 Mapper XML |
| `service/SystemAdminService.java` | 管理员服务 |
| `service/user/AccountUserResolverService.java` | 三方账号解析公共服务（与黑白名单共用，合并自 260727） |
| `controller/SystemAdminController.java` | 管理员管理接口 |
| `controller/PermissionController.java` | 前端权限感知接口 |
| `annotation/RequireAdmin.java` | 管理员权限注解 |
| `interceptor/AdminAuthInterceptor.java` | 管理员权限拦截器 |

### 5.2 修改文件

| 文件 | 改动说明 |
|------|---------|
| `WebConfig.java` | 注册 `AdminAuthInterceptor`，添加初始管理员启动逻辑 |
| `db/changelog/db.changelog-master.yaml` | 引入新的 changelog 文件 |

## 6. 待确认问题

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | 是否需要管理员操作审计日志？ | 安全审计 | 建议后续增加，当前版本暂不实现 |
| 2 | 管理员是否需要支持用户搜索接口（与黑白名单共享）？ | 用户体验 | 共享 `/api/access/user-search` 接口，后续一起实现 |
