# 实现步骤

## 一、注解与拦截器

- [ ] `ProjectAuth`：`@Target` 改为 `{ElementType.METHOD, ElementType.TYPE}`，类注释补充类级用法说明
- [ ] `AuthInterceptor.preHandle`：方法级 `@ProjectAuth` 缺失时回退类级 `@ProjectAuth`，记录 `fromClassLevel`
- [ ] `AuthInterceptor.preHandle`：删除命中 `@ProjectAuth` 后的 `return true`，改为继续执行 `@CheckPermission` 校验
- [ ] `AuthInterceptor.handleProjectAuth`：新增 `fromClassLevel` 参数
  - [ ] 类级：projectId 仅取 `URI_TEMPLATE_VARIABLES_ATTRIBUTE` 中的 `projectId`，缺失 fail-closed
  - [ ] 类级：使用 `hasProjectMenuPermission`
  - [ ] 类级：菜单 URL 经 `collapsePullsSuffix` 处理
  - [ ] 方法级：保持 query/body 取 projectId + `hasPermission`，行为不变
- [ ] `AuthInterceptor`：新增常量 `GATEWAY_PULLS_COLLAPSE_PREFIXES` 与私有方法 `collapsePullsSuffix`

## 二、Mapper

- [ ] `UserRoleMapper.hasPublicPermission` 改名 `hasProjectMenuPermission`
- [ ] `UserRoleMapper.xml` 对应 `<select id>` 改名

## 三、Controller

- [ ] `PrController` 加类级 `@ProjectAuth`
- [ ] `PrDashboardController` 加类级 `@ProjectAuth`
- [ ] `PrCommentController` 加类级 `@ProjectAuth`
- [ ] `PrLabelController` 加类级 `@ProjectAuth`
- [ ] `BranchController` 加类级 `@ProjectAuth`
- [ ] `LabelController` 加类级 `@ProjectAuth`
- [ ] `OpenUbmcFeatureController` 加类级 `@ProjectAuth`

## 四、测试

- [ ] `AuthInterceptorTest` 补类级用例：
  - [ ] 类级注解命中 + 路径变量 projectId + 有权限 → 放行
  - [ ] 类级注解命中 + 路径变量缺失 → fail-closed
  - [ ] 类级注解命中 + 无权限 → 403 `PERMISSION_DENIED`
  - [ ] 类级注解命中 + 缺 userId → 401 `MISSING_USER_ID`
  - [ ] 类级 + `@CheckPermission` 同时存在且项目级通过、流水线级拒绝 → 拒绝（AND 叠加）
  - [ ] pulls 后缀坍缩：`/pulls/{number}/commits` 查询 URL 为 `/pulls/{number}`
  - [ ] gitcode pulls 后缀坍缩
  - [ ] 方法级 `@ProjectAuth` 行为不变（query/body 取参、不含 visitor）
- [ ] 守卫测试：7 个 Controller 的类级注解存在性 + 其所有 mapping 路径均含 `{projectId}` 路径变量
- [ ] 执行 `mvn -pl openlibing-cicd test -Dtest=AuthInterceptorTest` 及相关测试

## 五、交付与验证

- [ ] 本地自检：仅改动本仓、无无关重构、无硬编码凭证
- [ ] 接口变动检测：判定为无接口变更
- [ ] 输出变更文件清单，等待用户本地 Review 与自测

## 六、后续（不属于本 PR）

- [ ] 网关侧删除 `PermissionCheckFilter.java` + `PermissionCheckFilterTest.java` + `UserRoleMapper.hasPermission` 死代码链，同步 `AGENTS.md` / `README.md`
- [ ] BETA 环境按角色矩阵验证后，网关再执行删除
