# 网关侧 cicd 特殊放行逻辑整改下线 — 设计文档

## 1. 方案设计

采用「扩展现有 `@ProjectAuth` 注解 + 类级声明」的方案，不新增独立注解、不启用 URL 模式自动生效、不逐方法加注解。

- `@ProjectAuth` 的 `@Target` 从 `{METHOD}` 扩展为 `{METHOD, TYPE}`。
- 7 个 Controller 加类级 `@ProjectAuth`，方法体零改动，Controller 层保持纯转发。
- `AuthInterceptor.preHandle` 支持类级查找，并删除「命中 `@ProjectAuth` 立即 return true」的提前返回，使 `@ProjectAuth` 与 `@CheckPermission` 可以 AND 叠加。
- 类级来源与方法级来源在取参、SQL、路径处理上分别处理，保证方法级存量行为不变。

方案选择理由：`@ProjectAuth` 的语义（项目级横向鉴权）与本需求完全一致，扩展注解目标比新增注解更小、更集中；类级声明避免 49 处重复标注。

## 2. 实现逻辑设计

### 2.1 注解解析优先级

1. 方法级 `@ProjectAuth`（`handlerMethod.getMethodAnnotation`）优先；
2. 方法级不存在时，取类级（`handlerMethod.getBeanType().getAnnotation`）；
3. 记录来源 `fromClassLevel`，后续取参与 SQL 选择由来源决定。

### 2.2 校验顺序（AND 叠加）

```
preHandle:
  ProjectAuth pa = 方法级 ?? 类级
  if (pa != null) handleProjectAuth(request, pa, fromClassLevel)   // 失败抛异常
  CheckPermission cp = 方法级
  if (cp == null) return true
  ... 现有流水线级校验 ...
```

删除原 `return true` 后，两者同时存在时项目级先校验、流水线级后校验，任一失败即拒绝。

该规则对方法级与类级 `@ProjectAuth` 一视同仁。已核实：`PipelineControllerV2` 中 3 个方法级 `@ProjectAuth`（`/updatePipelineConfig`、`/batchUpdatePipelineConfig`、`/cancelPipelineQueue`）均**未**同时标注 `@CheckPermission`，`@CheckPermission` 的 30 处均不在这些方法上；全仓 Controller 中也不存在同时标注两者的方法。因此删除提前返回后，现有端点判定结果不变；AND 叠加只对将来新增的「两类注解共存」方法生效。

### 2.3 projectId 来源

| 来源           | projectId 取值                                                        | 缺失处理                                                        |
| -------------- | --------------------------------------------------------------------- | --------------------------------------------------------------- |
| 方法级（存量） | GET 取 query 参数；非 GET 取请求体                                    | 400 `MISSING_PROJECT_ID`                                        |
| 类级（新增）   | 仅 `HandlerMapping.URI_TEMPLATE_VARIABLES_ATTRIBUTE` 中的 `projectId` | 直接 fail-closed（`MISSING_PROJECT_ID`），**不**回落 query/body |

userId 统一只取网关注入的 query 参数（`userIdKey`），不采信请求体。

### 2.4 SQL 选择

| 来源   | 方法                                                        | visitor 放行 |
| ------ | ----------------------------------------------------------- | ------------ |
| 类级   | `hasProjectMenuPermission`（原 `hasPublicPermission` 改名） | 是           |
| 方法级 | `hasPermission`                                             | 否           |

类级 SQL 与网关 `openlibing-gateway` 的 `UserRoleMapper.hasPermission` **逐字一致**，已逐行比对确认（仅缩进不同）：

```sql
select role from user_role_info uri
    where uri.user_id = #{userId} and ((uri.project_id = #{projectId} and uri.perm_group_id = 0) or uri.role = 'admin' or uri.role = 'visitor') and
    uri.role in (select role from role_type_info rti
    left join role_permission_manager rpm on rti.id = rpm.role_id
    left join menu_url_info mui on rpm.menu_id = mui.menu_id
    where mui.menu_url = #{menuUrl})
```

cicd 侧存量 `hasPublicPermission` 与该语句在 `visitor` 放行、`role_type_info` 关联、`menu_url_info` 匹配三个维度上完全一致，因此本次只需改名，正文不改动。

### 2.5 pulls 路径坍缩（复刻网关）

网关历史实现（`PermissionCheckFilter` L41-44、L108-120）两个模式并存：

```java
PIPELINE_PR_PATTERN = Pattern.compile("/pr/pulls/(.*)");
PIPELINE_PR_GITCODE_PATTERN = Pattern.compile("/pr/gitcode/pulls/(.*)");
```

命中后分别把 `/pr/pulls/<捕获串>` 整体替换为 `/pr/pulls/{number}`、`/pr/gitcode/pulls/<捕获串>` 整体替换为 `/pr/gitcode/pulls/{number}`。即两类 pulls 前缀及其任意子路径统一按前缀本身查菜单权限。

cicd 侧实现不依赖占位符字面名，按路径段正则坍缩：

```java
// 复刻网关下移前对 pulls 子路径的坍缩规则
private static final Pattern GATEWAY_PULLS_PATTERN =
    Pattern.compile("^(/openlibing-cicd/project/\\{projectId\\}/pr/(?:gitcode/)?pulls)/[^/]+(?:/.*)?$");
```

`collapsePullsSuffix(menuUrl)`：命中时返回 `matcher.group(1) + "/{number}"`，否则原样返回。正则按段匹配而非匹配 `{number}` 字面量，因此占位符改名（如 `{prNumber}`）不会静默失效。

已核实：`PrController` 中 12 处 pulls mapping 全部使用 `{number}` 占位符，且测试用 `{prNumber}` 形态做负向用例。

仅类级分支调用（方法级 3 个端点为 `/project/pipeline/**`，网关从未坍缩）。

### 2.6 菜单 URL 构造

`"/openlibing-cicd" + BEST_MATCHING_PATTERN_ATTRIBUTE`，类级分支再经过 `collapsePullsSuffix`。

### 2.7 失败语义

| 场景           | HTTP | errorCode            |
| -------------- | ---- | -------------------- |
| 缺 userId      | 401  | `MISSING_USER_ID`    |
| 缺 projectId   | 400  | `MISSING_PROJECT_ID` |
| 菜单权限不通过 | 403  | `PERMISSION_DENIED`  |

与现有一致，不改动。

## 3. 类设计

| 类                                | 变更                                                                                                                                                     |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProjectAuth`                     | `@Target({METHOD, TYPE})`                                                                                                                                |
| `AuthInterceptor`                 | 新增类级注解查找；`handleProjectAuth` 增加 `fromClassLevel` 参数；新增 `resolveClassLevelProjectId`、`collapsePullsSuffix`、常量 `GATEWAY_PULLS_PATTERN` |
| `UserRoleMapper`（cicd）          | `hasPublicPermission` 改名 `hasProjectMenuPermission`（无 Java 调用方，纯改名）                                                                          |
| `UserRoleMapper.xml`（cicd）      | 对应 `<select id>` 改名                                                                                                                                  |
| `PrController` 等 7 个 Controller | 类级加 `@ProjectAuth`                                                                                                                                    |

`PipelineControllerV2` 不改动。

「7 个 Controller / 49 个端点」是人工枚举结果，不作为代码可推导的假设。守卫测试不遍历白名单类，而是扫描全部 `HandlerMapping`：所有 `/project/**` 形态的端点必须带方法级或类级 `@ProjectAuth`，并核对端点总数，使将来新增的 Controller 漏标时测试直接失败。

## 4. 数据模型设计

无表结构变更，无 liquibase changeSet。

依赖现状数据：

- `user_role_info`、`role_type_info`、`role_permission_manager`、`menu_url_info` 均复用。
- 49 端点中 48 个已在 `menu_url_info` 登记；`GET /project/{projectId}/pr/get-pr-pipeline` 未登记，现状即为 403，本次保持不变（等价）。

## 5. 性能设计

- 每个类级端点新增 1 次菜单权限 SQL 查询（与网关删除前行为一致，总量不增加）。
- 不使用缓存，与网关行为一致，避免缓存导致的权限变更延迟。
- 无批量循环、无 N+1。

## 6. API 接口设计

不新增、不修改任何 HTTP 接口的路径、入参、出参。仅新增服务端鉴权校验。

## 7. 安全设计

- 类级 projectId 只信任路径变量，防止通过 query/body 伪造跨项目访问。
- userId 只信任网关注入的 query 参数。
- 缺参数即 fail-closed，不出现默认放行分支。
- 类级与流水线级校验 AND 叠加，任一失败即拒绝。
- 删除网关过滤器后不存在双通道并存：cicd 侧校验先上线，网关后删除。
- 已知等价偏差（已确认接受）：`GET /project/{projectId}/pr/get-pr-pipeline` 未登记菜单，删除前后均为 403。
