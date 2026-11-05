# 实现步骤

## 一、注解与拦截器

- [x] `ProjectAuth`：`@Target` 改为 `{ElementType.METHOD, ElementType.TYPE}`，类注释补充类级用法说明
- [x] `AuthInterceptor.preHandle`：方法级 `@ProjectAuth` 缺失时回退类级 `@ProjectAuth`，记录 `fromClassLevel`
- [x] `AuthInterceptor.preHandle`：删除命中 `@ProjectAuth` 后的 `return true`，改为继续执行 `@CheckPermission` 校验
- [x] `AuthInterceptor.handleProjectAuth`：新增 `fromClassLevel` 参数
  - [x] 类级：projectId 仅取 `URI_TEMPLATE_VARIABLES_ATTRIBUTE` 中的 `projectId`，缺失 fail-closed
  - [x] 类级：使用现有 `hasPermission`（SQL 正文与 Mapper 均不改动）
  - [x] 类级：菜单 URL 经 `collapsePullsSuffix` 处理
  - [x] 方法级：保持 query/body 取 projectId + `hasPermission`，行为不变
- [x] `AuthInterceptor`：新增常量 `GATEWAY_PULLS_PATTERN` 与私有方法 `collapsePullsSuffix`

## 二、Controller

- [x] `PrController` 加类级 `@ProjectAuth`
- [x] `PrDashboardController` 加类级 `@ProjectAuth`
- [x] `PrCommentController` 加类级 `@ProjectAuth`
- [x] `PrLabelController` 加类级 `@ProjectAuth`
- [x] `BranchController` 加类级 `@ProjectAuth`
- [x] `LabelController` 加类级 `@ProjectAuth`
- [x] `OpenUbmcFeatureController` 加类级 `@ProjectAuth`

## 三、测试

- [x] 改造前基线：执行现有 `AuthInterceptorTest`（`mvn -o test -Dtest=AuthInterceptorTest`），记录结果（实测 50 例全通过）
- [x] 改造前锁定存量语义（characterization）：方法级 `@ProjectAuth` 的取参来源、错误码，并用 `verify` 锁定调用 `hasPermission`、菜单 URL 不做坍缩
- [x] `@BeforeEach` 新增 1 行 fixture stub：`HandlerMethod` 为 mock，`getBeanType()` 默认返回 null，改造后类级回查会 NPE
- [x] `AuthInterceptorTest` 补类级用例：
  - [x] 类级注解命中 + 路径变量 projectId + 有权限 → 放行
  - [x] 类级注解命中 + 路径变量缺失 → fail-closed
  - [x] 类级注解命中 + 无权限 → 403 `PERMISSION_DENIED`
  - [x] 类级注解命中 + 缺 userId → 401 `MISSING_USER_ID`
  - [x] 类级 + `@CheckPermission` 同时存在且项目级通过、流水线级拒绝 → 拒绝（AND 叠加）
  - [x] pulls 后缀坍缩：`/pulls/{number}/commits` 查询 URL 为 `/pulls/{number}`
  - [x] gitcode pulls 后缀坍缩
  - [x] 占位符改名负向用例：`/pulls/{prNumber}/commits` 仍坍缩为 `/pulls/{number}`
  - [x] 方法级 `@ProjectAuth` 行为不变（query/body 取参，优先于类级且不坍缩）
- [x] 改造后回归：存量 50 个用例的用例体不改，仅依赖上述 fixture stub，全部通过；新增用例全部通过
- [x] 守卫测试：用 `ClassPathScanningCandidateComponentProvider` 扫描 `com.openlibing.cicd.business.controller`（不启动 Spring 上下文、不依赖 DB），所有 `/project/{变量}/**` 形态端点必须带方法级或类级 `@ProjectAuth`，类级注解所在类的映射路径必须包含名为 `projectId` 的路径变量，并断言端点总数（49）
- [x] 执行 `mvn -o clean test -Dtest=AuthInterceptorTest`（该仓为单模块仓，不用 `-pl`），61 例全通过

## 四、交付与验证

- [x] 本地自检：仅改动本仓、无无关重构、无硬编码凭证
- [x] 接口变动检测：判定为无接口变更
- [x] 代码格式化：`mvn -o spotless:check` 通过
- [x] 输出变更文件清单，等待用户本地 Review 与自测

## 五、后续（不属于本 PR）

- [ ] 网关侧删除 `PermissionCheckFilter.java` + `PermissionCheckFilterTest.java` + `UserRoleMapper.hasPermission` 死代码链，同步 `AGENTS.md` / `README.md`
- [ ] BETA 环境按角色矩阵验证后，网关再执行删除
