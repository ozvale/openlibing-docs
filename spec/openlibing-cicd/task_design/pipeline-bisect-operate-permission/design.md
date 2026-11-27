# pipeline-bisect-operate-permission: 工程设计

## 1. 方案设计

`AuthInterceptor` 对流水线资源的判定分两层：存量判定（登录 + 公开仓/菜单权限）与权限组判定。权限组判定是**操作类端点专属**，入口形态为：

```text
if (operate && StringUtils.hasText(pipelineId)) { 查绑定权限组 → 组校验 }
```

因此 `operate` 是"要不要感知权限组"的开关。`/bisect/create` 的请求体是 `PipelineParamDTO`，携带 `projectId`、`pipelineId`、`pipelineRunId`，`pipelineId` 可被 `AuthInterceptor` 从 body 解析，具备走组校验的前提。

备选方案：

| 方案                                 | 做法                    | 结论                                                         |
| ------------------------------------ | ----------------------- | ------------------------------------------------------------ |
| 注解补 `operate = true`              | 与 `/run`、`/stop` 对齐 | 采用                                                         |
| 在 Controller/Service 内手工查权限组 | 复制拦截器逻辑          | 拒绝，重复实现且易与拦截器口径漂移                           |
| 保持现状，依赖服务层归属校验         | 不加注解                | 拒绝，`bisect/create` 无服务层归属校验，写操作对组外用户开放 |

## 2. 实现逻辑设计

1. `bisectLocate` 的 `@CheckPermission` 改为 `@CheckPermission(operate = true)`
2. 请求进入 `AuthInterceptor` 后：
   - 匿名 + 已绑定权限组 → 401 `LOGIN_REQUIRED_BY_GROUP`，与仓库是否公开无关
   - 已登录 + 公开仓 + 已绑定权限组 → 仍进入组校验：组内放行，组外 403（业务码 `4030001`）；组校验不通过时，仅当端点声明 `defaultGroupFallback = true` 才回退默认组菜单权限
   - 已登录 + 私有仓 + 已绑定权限组 → 同样进入组校验，规则与公开仓一致
   - 流水线未绑定权限组 → 回落存量判定，行为与改造前完全一致
   - `defaultGroupFallback` 是 `@CheckPermission` 的显式属性，默认 `false`，当前仅单条同步端点使用；`bisectLocate` 未声明，即组校验拒绝时不回退
3. `/bisect/reset` 不改：其入参为 `projectId` / `userId` / `id`，不含 `pipelineId`，`extractPipelineIds` 得到空值，组校验分支恒不触发，加 `operate = true` 是空操作；该端点已有服务层 `requireOwnershipOrThrow` + `requireProjectMemberOrThrow` 兜底
4. 补充 Javadoc 说明按操作类语义校验的原因，便于后续维护者理解为何不是遗漏

## 3. 类设计

| 类                              | 职责                                                   |
| ------------------------------- | ------------------------------------------------------ |
| `PipelineControllerV2`          | 端点声明，`/bisect/create` 标注 `operate = true`       |
| `AuthInterceptor`（既有，未改） | 按 `operate` + `pipelineId` 决定是否进入权限组校验     |
| `AuthInterceptorTest`           | 以真实 Controller 方法注解驱动拦截器，断言三条访问路径 |

## 4. 数据模型设计

无表结构、无实体、无字段变更。

权限组数据来自既有 `menu_info` / `menu_url_info` / `role_permission_manager` / `role_type_info` / `user_role_info`，本需求只消费不改造。

## 5. 性能设计

- 仅改变注解取值，不新增查询
- 组校验结果在拦截器内已有本地缓存与请求内 memo，不会因开启 operate 产生额外的重复查库
- 未绑定权限组的流水线不进入组查询，性能与改造前一致

## 6. API 接口设计

无契约变化。`POST /project/pipeline/bisect/create` 的路径、请求体 `PipelineParamDTO`、响应 `DataResult<String>` 均未改。

行为变化：当流水线已绑定权限组时，组外用户与匿名调用会分别在原有存量判定前后被 403 / 401 拦截。未绑定权限组的流水线行为不变。

## 7. 安全设计

- 覆盖威胁：CWE-862（Missing Authorization）
- 缓解点：写操作纳入权限组管控，与同类操作端点语义一致
- 边界：仅对"已绑定权限组"的流水线生效；未绑定资源的管控仍依赖存量菜单权限模型
- 残余风险：管控只覆盖"已绑定权限组"的流水线；BETA 实测绑定流水线 5 条、组成员 0，需运维补齐成员后管控才真正生效。admin 角色已确认持有 `100842`（当前 493 条菜单权限、130 个 admin 用户），代码不做默认放行兜底
- 回归关注：前端「PR问题定位 - 查看详情」入口在正常权限下可正常触发，不应出现误 403
- 测试覆盖：`AuthInterceptorTest` 新增 4 条用例，全部以真实 `bisectLocate` 方法注解驱动——断言注解 `operate` 为 `true`（防回退）、匿名 + 已绑定组返回 401、组内成员放行、组外用户返回 403（业务码 `4030001`）
