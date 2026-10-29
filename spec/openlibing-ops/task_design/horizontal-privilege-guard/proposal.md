# 横向越权防护（AOP + 注解资源归属校验）

## 需求背景

openlibing 平台的用户请求权限目前由 gateway 统一控制：`AuthFilter` 负责登录态校验（JWT 验签 + Redis token 存在性 + userId 与 `three_party_user_info` 一致性）与**垂直权限**（菜单 URL 权限，`userPermissionAuth`），`PermissionCheckFilter` 仅对 `/openlibing-cicd/` 前缀路径做项目级校验。

但 gateway 的垂直权限只校验"URL 是否在用户菜单中"，`menu_url_info.available_value` 的动态参数取值校验**只作用于 PathVariable 段，从不覆盖 query 参数**（`UserAuthHelper.comparePath` 以 `exchange.getRequest().getPath().value()` 匹配，不含 query string）。因此对 openlibing-ops 等服务存在**横向越权**缺口：用户菜单中包含 `/repo/**`、`/ops-overview/**` 等接口后，即可篡改请求中的 `projectId`/`repoId` 等参数访问其他项目的数据。

安全扫描确认：

- **openlibing-ops**：21 个 Controller 中 `RepoController`、`PipelineController`、`OpsGithubController`、`OpsOverviewController`、`ResourceOperationController` 等大量接口直接信任客户端传入的 `projectId`/`repoId`，业务侧零授权校验，攻击面大，风险等级**高**。
- **openlibing-metric**：7 个 Controller 入参不含跨项目资源标识（`metricCode`/`domainId` 等为全局业务主键），经典"篡改 projectId"攻击面不存在；但所有接口零授权，任意登录用户可改/删任意记录，`AiDashboard` 接口对任意用户返回全量 AI 用户数据，风险等级**中**。

## 目标

1. 在 openlibing-ops 实现**通用、可复用**的横向越权防护：通过自定义注解 + AOP 切面对携带 `projectId`/`repoId` 的接口做资源归属校验，越权即返回 403。
2. 校验数据全部走 MySQL 权限表（`user_role_info` 等），语义与 gateway `hasPermission` 及 framework `verifyPermissions` 对齐。
3. 形成可向 openlibing-metric 等仓推广的通用模式。

## 验收标准

- [ ] 携带 `projectId`/`repoId` 的 ops 核心接口全部打上资源归属校验注解
- [ ] 用户访问不属于自己的项目/仓库数据时，接口返回 403（`NO_PERMISSION`）
- [ ] 平台管理员（`super_admin` / SYSTEM 类型角色）与已授权用户访问不受影响
- [ ] 无 userId 的内部调用/白名单路径（健康检查等）正常放行
- [ ] ops 仓编译通过，相关单元测试通过
- [ ] metric 仓扫描结论沉淀，后续按需推广

## 关联 Issue

待创建（业务 Issue，创建后回填）
