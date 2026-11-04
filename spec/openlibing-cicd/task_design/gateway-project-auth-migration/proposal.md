# 网关侧 cicd 特殊放行逻辑整改下线

## 背景

openlibing-gateway 的 `PermissionCheckFilter`（order=3）对所有 `/openlibing-cicd/` 且路径含 `/project/<数字>/` 的请求做项目级横向鉴权：从 Cookie 解析 userId，将路径归一化为 `/project/{projectId}`，再查 `user_role_info` / `role_permission_manager` / `menu_url_info` 判断用户是否拥有该项目下对应菜单权限。

安全评审认为「网关跨服务执行项目级鉴权」不合规，决定整个删除该过滤器；鉴权职责下移到业务服务 openlibing-cicd 自身。

影响范围：cicd 下 7 个 Controller 共 49 个端点（`/project/{projectId}/**`），其他 cicd 接口与其他仓库不受影响。

## 目标

1. 删除网关 `PermissionCheckFilter` 后，这 49 个端点的鉴权行为与删除前**严格等价**（含历史遗留的 pulls 路径坍缩规则）。
2. 为后续删除网关过滤器提供前置条件：cicd 侧先上线并验证通过。

## 非目标

- 不覆盖 `openlibing-cicd#334` 中的其余项：`/build/v1/**`、`/image/v1/**`、`/cross-region/**` 拦截器扩展；`/project/pr/shortcut/**`、`/project/email/send` 补注解；「无注解默认拒绝」开关；网关侧 claim/白名单/IP 的 fail-open 情形；`#437` 零校验接口。
- 不改动 `PipelineControllerV2` 现有 3 个方法级 `@ProjectAuth` 与 30 个 `@CheckPermission` 的行为。
- 不改动网关侧代码（由网关同事执行删除）。

## 验收标准

1. 7 个 Controller 的类级 `@ProjectAuth` 生效，49 个端点均要求登录 + 项目菜单权限；匿名请求返回 401（`MISSING_USER_ID`），无权限返回 403（`PERMISSION_DENIED`）。
2. 类级鉴权的 projectId 只从路径变量 `projectId` 获取；路径中缺失该变量时 fail-closed（400/403），不回落到 query 或 body。
3. 类级鉴权 SQL 含 `visitor` 角色放行，与网关 `UserRoleMapper.hasPermission` 逐字等价。
4. `/pr/pulls/{number}/**` 与 `/pr/gitcode/pulls/{number}/**` 按 `/pr/pulls/{number}`、`/pr/gitcode/pulls/{number}` 查询菜单权限，复刻网关坍缩行为。
5. 类级 `@ProjectAuth` 与 `@CheckPermission` 同时存在时，两者均执行（AND 叠加），项目级校验在前。
6. `PipelineControllerV2` 3 个方法级 `@ProjectAuth` 行为不变（仍走 query/body 取 projectId、不含 visitor 的 SQL）。
7. `AuthInterceptorTest` 覆盖以上判定分支并全部通过。
8. BETA 环境按角色矩阵（admin / platform_operater / repo_observer / visitor / 项目成员 / 项目外用户 / 匿名）人工验证，结果与删除前一致。

## 关联 Issue

- `openlibing/openlibing-codecheck#401`（当月统一漏洞 issue，`Refs` + 完整 URL，不自动关闭，合入后置「待验收」）
- `openlibing/openlibing-cicd#334`（`Refs` + 完整 URL，本次仅覆盖其中「`/project/{projectId}/**` 项目级鉴权承接」一项，不能关闭）

## 发布顺序

1. cicd 本需求上线；
2. BETA 验证 49 端点鉴权行为无变化；
3. 网关侧删除 `PermissionCheckFilter` 及其测试、`UserRoleMapper.hasPermission` 死代码，同步 `AGENTS.md` / `README.md` 过滤器清单。

若顺序颠倒，会出现 `/project/{projectId}/**` 项目级鉴权真空期。
