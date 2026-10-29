# 横向越权防护技术方案

## 1. 信任边界与身份来源

### 1.1 网关已保证的信任基础

网关 `AuthFilter.getNewRequestParams`（`openlibing-gateway/.../filter/AuthFilter.java:658-697`）从 JWT claim 提取 4 个字段，通过 `params.put(key, singletonList(value))` **整体覆盖**客户端同名 query 参数：

| 字段              | 含义                              |
| ----------------- | --------------------------------- |
| `userId`          | openlibing 平台用户 ID            |
| `userName`        | 用户姓名                          |
| `accountId`       | 三方账号 ID                       |
| `accountPlatform` | 三方平台（gitcode/gitee/ubmc 等） |

**结论：下游服务收到的 `userId` query 参数不可伪造**。framework 各 Controller 亦以此约定直接 `@RequestParam userId` 信任使用（平台既有惯例）。

### 1.2 权限校验数据全部走 MySQL 表

权限关系数据位于 MySQL（由 openlibing-framework 维护 DDL），与网关同库：

| 表               | 主键维度     | 用途                                                        |
| ---------------- | ------------ | ----------------------------------------------------------- |
| `user_role_info` | `user_id`    | 平台用户角色（role、product_id、project_id、repo_id）       |
| `role_type_info` | role         | 角色类型枚举：`system`/`product`/`project`/`repo`/`general` |
| `project_info`   | `project_id` | project → product 归属反查                                  |
| `repo_info`      | `repo_id`    | repo → project 归属反查                                     |

身份维度**仅以 `user_role_info`（user_id 维度）为准**，与 gateway `hasPermission` 语义一致；不引入 `project_user_role_info` / `repo_user_role_info`（三方账号维度）兜底，避免双数据源判定歧义。

ops 本地不缓存、不引入 Redis 权限副本，每请求实时查 MySQL，先保证正确性；后续如需性能优化再加缓存（需评估 ops 当前无 Redis 依赖的现状）。

### 1.3 信任边界声明

- 假设所有外部流量必须经过网关（网关已完成 JWT 验签并覆盖注入 userId）。
- ops 切面以 query 参数 `userId` 为唯一身份来源（`RequestContextHolder` 取当前请求）。
- userId 缺失直接拒绝（不做白名单放行）；绕过网关直连 ops 的伪造攻击不在本次范围（属网络层防护）。

## 2. 权限判定语义（对齐 gateway/framework）

复用 gateway `UserRoleMapper.hasPermission` 与 framework `CommonServiceImpl.verifyPermissions2`（`openlibing-framework/.../service/impl/CommonServiceImpl.java:240-292`）的判定语义，收敛为单条 EXISTS 查询：

```
userId 为空                                → 拒绝
资源 id 为空 / 空集合                        → 跳过校验（必传参数由 @NotNull 挡）
角色为 super_admin / admin / visitor        → 放行（全局管理员短路）
角色类型为 system / general                 → 放行
角色类型为 product 且 product_id 匹配项目归属  → 放行
角色类型为 project 且 project_id 匹配        → 放行
角色类型为 repo 且 project_id 或 repo_id 匹配 → 放行
其余                                       → 拒绝，返回 403
```

**语义要点**：

- 空资源 id 跳过：列表接口"不传 id 返回全量可见数据"的既有行为不破坏；跨项目拉取全量数据作为遗留项后续治理。
- 集合参数逐个校验，任一无权限即整体拒绝（防部分越权）。
- REPO 校验先反查 `repo_info.project_id`（repoId 不存在抛 403），再按 project+repo 双匹配判定。

## 3. 核心组件设计

### 3.1 组件清单（最终落地位置）

| 组件                                           | 位置                             | 说明                                                                                                                        |
| ---------------------------------------------- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `@ResourcePermission` + `@ResourcePermissions` | `infrastructure/aop/permission/` | 方法级注解，`@Repeatable` 支持同一接口校验多个资源标识                                                                      |
| `ResourceTypeEnum`                             | `infrastructure/enums/`          | PROJECT / REPO（仅两种）                                                                                                    |
| `ResourceIdEnum`                               | `infrastructure/enums/`          | 资源 id 入参字段枚举：PROJECT_ID / REPO_ID，各自带字段名族（projectId/projectIds/projectIdList、repoId/repoIds/repoIdList） |
| `ResourcePermissionAspect`                     | `infrastructure/aop/permission/` | `@Around` 切面：取 userId → 按字段名提取资源 id → 归一化展平 → 调校验服务                                                   |
| `ResourcePermissionService`                    | `domain/service/permission/`     | 资源归属校验逻辑（REPO 反查 + 权限判定）                                                                                    |
| `ResourcePermissionMapper` + XML               | `domain/mapper/permission/`      | 单 EXISTS 查询判定权限 + repo→project 反查                                                                                  |
| `PermissionDeniedException`                    | `infrastructure/exception/`      | 越权异常（`BizException(NO_PERMISSION)`），携带 `detail` 审计字段                                                           |
| `GlobalExceptionHandler` 扩展                  | 已有文件                         | 新增 `PermissionDeniedException` handler → 403                                                                              |

### 3.2 注解定义

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Repeatable(ResourcePermissions.class)
public @interface ResourcePermission {
  /** 资源类型：PROJECT / REPO */
  ResourceTypeEnum type();

  /** 资源 id 的入参字段，按字段名从方法实参取值；值为空或空集合时跳过校验 */
  ResourceIdEnum resourceId();
}
```

`resourceId` 使用枚举而非 SpEL 字符串：使用方只需写 `resourceId = ResourceIdEnum.PROJECT_ID` / `REPO_ID`，切面按字段名族自动从参数名、对象属性、集合元素属性三种来源取值（`REPO_ID` 自动匹配 `repoId`/`repoIds`/`repoIdList`），无需记忆 SpEL 语法。同一接口需校验多个资源标识时叠加注解（如 `queryBaseDashboard` 同时校验 PROJECT_ID 与 REPO_ID）。

### 3.3 切面流程

`ResourcePermissionAspect`（`@Around("@annotation(...ResourcePermission)")`）：

1. **取 userId**：`RequestContextHolder` 取当前请求 query 参数 `userId`（网关覆盖注入，可信）。缺失抛 `PermissionDeniedException`。
2. **提取资源 id**：按 `ResourceIdEnum` 的字段名族从方法实参提取：参数名匹配（如 `projectId` 参数）、对象属性（如 `req.getProjectId()`）、集合元素属性（如 `List<DTO>` 逐元素取 `getRepoId()`）三种来源；同一资源的单数/复数/List 命名变体一次覆盖。
3. **归一化展平**：`normalize()/flatten()` 将嵌套集合展平、String/Number 统一转 Integer；空结果跳过校验。
4. **校验**：调 `ResourcePermissionService.check(userId, type, ids)`，失败抛 `PermissionDeniedException`（`detail` 记录 userId、资源类型、资源 id、projectId）。
5. 通过则 `joinPoint.proceed()`。

**异常包装规避**：`DataSourceAspect` 会把方法内 Throwable 包装为 `IllegalStateException`，破坏 403 语义。因此 Mapper 方法只做查询（`@DataSource(MYSQL)` 作用域内），`PermissionDeniedException` 在 Service/Aspect 层抛出（DataSource 切面作用域外）。

### 3.4 校验服务（ResourcePermissionService）

仅支持两种资源类型，**统一收敛到 project 维度校验**：

| 资源类型 | 反查逻辑                                       | 最终校验维度        |
| -------- | ---------------------------------------------- | ------------------- |
| PROJECT  | 无，projectId 直接使用                         | project 级校验      |
| REPO     | repoId → `repo_info.project_id`（null 抛 403） | project+repo 级校验 |

**判定入口**：`check(userId, type, resourceIds)` 逐 id 校验；权限判定下推为单条 EXISTS SQL（`hasResourceAccess`），语义见第 2 节。

带 `runId`/`pipelineId` 的接口若同时携带 `projectId`（如 `ResourceOperationController.run-analysis`），直接按 PROJECT 校验 projectId 即可覆盖，不做实例级反查。

### 3.5 异常与响应

- `PermissionDeniedException extends BizException`，构造时传 `ResponseCodeEnum.NO_PERMISSION`（403，`openlibing-ops/.../response/ResponseCodeEnum.java:27` 已定义），携带 `detail` 审计字段。
- `GlobalExceptionHandler`（`infrastructure/exception/GlobalExceptionHandler.java`）新增：
  ```java
  @ExceptionHandler(PermissionDeniedException.class)
  public Result handlePermissionDenied(PermissionDeniedException e) {
    log.warn("permission denied: {}", e.getDetail());
    return Result.error(e.getResponseCodeEnum());
  }
  ```
- 统一返回 `Result.error(NO_PERMISSION)`，前端提示"没有权限"。

## 4. 接入示例

```java
// GET query 参数形态（projectId 参数名命中字段族）
@ResourcePermission(type = ResourceTypeEnum.PROJECT, resourceId = ResourceIdEnum.PROJECT_ID)
public Result<?> queryRepoPlatform(@RequestParam Integer projectId, ...) { ... }

// POST body 字段形态（req.getProjectId() / req.getRepoId() 属性命中）
@ResourcePermission(type = ResourceTypeEnum.REPO, resourceId = ResourceIdEnum.REPO_ID)
public Result<?> queryRepoConcurrentChart(@RequestBody RepoConcurrentDetailReq req) { ... }

// 多资源标识叠加校验
@ResourcePermission(type = ResourceTypeEnum.PROJECT, resourceId = ResourceIdEnum.PROJECT_ID)
@ResourcePermission(type = ResourceTypeEnum.REPO, resourceId = ResourceIdEnum.REPO_ID)
public Result<?> queryBaseDashboard(@RequestBody RepoQueryReq req) { ... }

// 批量写接口（List<DTO> 逐元素取 getRepoId()）
@ResourcePermission(type = ResourceTypeEnum.REPO, resourceId = ResourceIdEnum.REPO_ID)
public Result<?> batchSetBranchConfig(@RequestBody List<RepoBranchConfigReq> req) { ... }
```

## 5. 首轮接入范围（已全部落地）

覆盖携带资源标识的 5 个核心 Controller（共 29 个接口方法）：

| Controller                    | 资源类型       | 加注解方法数                                   |
| ----------------------------- | -------------- | ---------------------------------------------- |
| `RepoController`              | PROJECT / REPO | 8                                              |
| `PipelineController`          | PROJECT        | 2（`queryPipelineInfo` 为 repoUrl 维度，遗留） |
| `OpsGithubController`         | REPO / PROJECT | 7                                              |
| `OpsOverviewController`       | PROJECT        | 7                                              |
| `ResourceOperationController` | PROJECT        | 5                                              |

其余 Controller（Report/NpuUsage/CodeCheck/Precision*/Project/QualityDashboard/TestCaseBoard 等）及 external 包接口在第二轮接入；无资源标识的接口（如健康检查）不加注解。

## 6. 基础设施盘点（可复用 vs 需新增）

**可复用**：

- ops 已有自定义注解 + AOP 先例：`@DataSource` + `DataSourceAspect`（`infrastructure/aop/`）、common 的 `@LogApi`
- `spring-boot-starter-aop` 经 openlibing-common 传递引入，无需新增依赖
- maven-compiler-plugin 已开启 `-parameters`，切面可按参数名提取资源 id
- `ResponseCodeEnum.NO_PERMISSION(403)` 与 `BizException`、`GlobalExceptionHandler` 现成

**需新增**：

- 注解（含 Repeatable 容器）、资源类型枚举、资源 id 字段枚举、切面、校验服务、Mapper 接口 + XML、异常类（8 个新文件）+ 改 `GlobalExceptionHandler`
- 5 个 Controller 加注解（29 个方法）
- 权限表查询：ops 的 MySQL 与网关同库，直接查 `user_role_info` / `role_type_info` / `project_info` / `repo_info`

## 7. 测试策略

- 校验服务单元测试（`ResourcePermissionServiceTest`，Mockito mock Mapper）：超管/放行、project 角色匹配、无权限拒绝、REPO 反查 null 拒绝、空集合跳过、集合部分失败拒绝 —— 已完成 6 用例全过
- 既有 Controller 测试（MockMvc standaloneSetup 不织入切面）不受影响 —— 已验证
- 集成验证：本地启动后，用无权限用户访问他人 projectId 数据，确认返回 403（用户自测环节）

## 8. 影响范围

- 修改仓：openlibing-ops（单仓）
- 涉及文件：8 个新增 + `GlobalExceptionHandler` + 5 个 Controller 加注解 + 1 个新增测试类
- 无数据库结构变更、无配置变更、无新增依赖
- 不影响已授权用户的正常访问；空资源 id 请求行为不变（跳过校验）

## 9. 向 openlibing-metric 推广的结论

metric 仓扫描结论（详见 proposal.md）：

- 入参**不含** `projectId`/`repoId`/`userId` 等跨项目资源标识，经典横向越权攻击面不存在，风险等级**中**。
- 真实风险点：① 所有接口零授权，任意登录用户可改/删任意 `metricCode`/`domainId`/`tableRegistryId` 记录；② `AiDashboard` 接口对任意用户返回全量 AI 用户数据（含 userId/userName）；③ `forward-api` 接受客户端自带 token/apiKey 转发，存在凭证冒用风险。
- metric 具备复刻基础：`@DataSource`+`DataSourceAspect` 注解切面先例、`TokenUtils`+common `JwtUtils` 可取 userId claims、`BizException(NO_PERMISSION)`→`GlobalExceptionHandler` 403 链路现成。
- 缺口：无统一用户上下文（UserContext/ThreadLocal）、无权限注解切面、无资源归属服务。
- **推广建议**：ops 方案落地并验证后，metric 侧优先补"写接口（save/update/delete）权限注解切面 + AiDashboard 数据可见范围控制"，暂不需要 PROJECT/REPO 资源维度校验。
