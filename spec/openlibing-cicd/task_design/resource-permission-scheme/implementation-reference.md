# CICD 资源级权限方案实现参考文档

本文档面向开发实现，配合《CICD资源级权限方案-设计文档.md》使用，不替代正式设计文档。以下类名、方法名、SQL 引用均为基于现状代码调研结论给出的参考实现，Trae 追码时需以实际代码为准做修正。

## 一、修改文件列表

### framework 层（新增）

- `PermSchemeController.java`（新增）
- `PermSchemeService.java`（新增）
- `PermSchemeResourceBindingService.java`（新增）
- `PermSchemeMapper.java` / `PermSchemeMapper.xml`（新增）
- `PermSchemeMemberMapper.java` / `PermSchemeMemberMapper.xml`（新增）
- `PermSchemeResourceBindingMapper.java` / `PermSchemeResourceBindingMapper.xml`（新增）
- 建表 SQL：`perm_scheme`、`perm_scheme_member`、`perm_scheme_resource_binding`（新增）

### CICD 层（改造 + 新增）

- `AuthInterceptor.java`（改造，`preHandle` 方法）
- `PermSchemeResourceBindingLocalMapper.java` / 对应 XML（新增，本地只读查询）
- 流水线列表/详情相关 Controller、Service（需 Trae 定位实际类名，参考调研中提到的 `ProjectUserService` 同级模块）：新增方案配置入口调用、列表返回结构补充方案标识字段

## 二、类和方法级修改点

### `AuthInterceptor#preHandle`

现状调用链（L123 起）：`extractPermissionContext`（解析上下文，含 `userId` —— 注意该值取自请求 body/query 参数，非登录态解析，是现状已知缺陷，见"四、已知遗留风险披露"）→ `isGitUrlPublic` 公开仓短路判断（命中直接放行）→ `userId` 为空时走 `checkAnonymousAccess`（L130，公开仓允许匿名）→ 均未命中时才调用 `userRoleMapper.hasPermission`（单条 `CASE WHEN EXISTS` SQL，四表联查一次判完，不是"查角色列表 + Java层匹配"的两段式）。

改造点：绑定查询插入在 `extractPermissionContext` 之后、`isGitUrlPublic` 判断之前，命中绑定后跳过公开仓短路与匿名放行两个分支。改造后的方法逻辑：

```java
// AuthInterceptor#preHandle 伪代码
PermissionContext ctx = extractPermissionContext(request);

// 新增：查询资源是否绑定了自定义方案（本地直查 + 独立Guava缓存，不复用现状匿名访问结果缓存）
SchemeBindingInfo binding = permSchemeResourceBindingLocalMapper
        .queryBinding(ctx.getProjectId(), ctx.getResourceType(), ctx.getResourceId());

if (binding != null) {
    // 命中绑定：跳过现状公开仓短路与匿名放行分支
    if (ctx.getUserId() == null) {
        return false; // 方案成员不含匿名身份，直接拒绝
    }
    // 调用新增的镜像单SQL（UNION ALL：admin穿透段 + 方案成员段），不做Java层角色列表拉取与二次匹配
    return userRoleMapper.hasPermissionByScheme(
            ctx.getUserId(), binding.getSchemeId(), ctx.getProjectId(), ctx.getUrl());
}

// 未命中绑定：以下为现状逻辑，原样保留，不做任何改动
if (isGitUrlPublic(ctx.getProjectId(), ctx.getPipelineId())) {
    return true;
}
if (ctx.getUserId() == null) {
    return checkAnonymousAccess(ctx);
}
return userRoleMapper.hasPermission(ctx.getUserId(), ctx.getProjectId(), ctx.getUrl());
```

注意事项：

- 绑定查询必须插入在 `isGitUrlPublic` 判断**之前**，否则已绑定方案的公开仓流水线会被公开仓短路逻辑绕过（对应 Trae 核实的 Gap 1）；同理必须覆盖 `userId` 为空的匿名分支（Gap 2），命中绑定后 `userId` 为空需直接拒绝，不得复用 `checkAnonymousAccess` 的公开仓豁免逻辑。
- `hasPermissionByScheme` 是新增的一条平行 SQL 方法，与现状 `hasPermission` 方法并存，不改造 `hasPermission` 本身，避免影响其存量单元测试（对应 Gap 3）。
- 该 SQL 内嵌的 admin 穿透段固定查询 `user_role_info`，不带 `project_id` 条件，但需落在该 URL 的角色白名单子查询内，与现状 `(uri.project_id = #{projectId} or uri.role = 'admin')` 穿透语义保持等价（对应 Gap 4，具体 SQL 见设计文档"2.1"）。
- SQL 内的方案成员段末尾带一个 `EXISTS` 校验用户在 `user_role_info` 中仍是有效项目成员，用于兜底成员一致性，不依赖各删除路径的应用层清理是否完整（对应 Gap 5）；已核实 `user_role_info` 区分记录层级的字段为 `repo_id`（`NULL` = 系统/产业/项目级记录，非 `NULL` = 仓库级记录），当前 `EXISTS` 口径为"`project_id` 匹配即视为有效项目成员"，与成员管理页面查询口径一致；若业务确认需收紧为仅项目级角色，追加 `AND uri2.repo_id IS NULL` 即可。
- 镜像 SQL 的 join 字段名已对照现状 `hasPermission` SQL 核实：`role_permission_manager` 关联 `role_type_info` 用 `rpm.role_id = rti.id`（该表无 `role_type_id` 字段），`menu_url_info` 的字段为 `menu_id` / `menu_url`（不是 `id` / `url`），照抄本页参考 SQL 时勿回退到错误字段名。已核实 `user_role_info` 仅有主键索引、`user_id` 无二级索引（现状 `hasPermission` 本身即全表扫描），补充 `(user_id, project_id, role)` 组合索引需 framework 团队通过 Liquibase 幂等 changeSet 评估落地。
- 绑定查询结果缓存需使用独立的 Guava 缓存实例，不得与现状 `AuthInterceptor` 中缓存匿名访问结果的本地缓存共用（对应问题 11）。

### `UserRoleMapper#hasPermissionByScheme`（新增方法，CICD 层）

对应 XML 参考（与现状 `hasPermission` 并存于同一 Mapper XML，不修改现状 `hasPermission` 语句本身）：

```xml
<select id="hasPermissionByScheme" resultType="boolean">
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM user_role_info uri
        WHERE uri.user_id = #{userId}
          AND uri.role = 'admin'
          AND uri.role IN (
              SELECT rti.role FROM role_type_info rti
              JOIN role_permission_manager rpm ON rti.id = rpm.role_id
              JOIN menu_url_info mui ON rpm.menu_id = mui.menu_id
              WHERE mui.menu_url = #{url}
          )
        UNION ALL
        SELECT 1 FROM perm_scheme_member psm
        WHERE psm.scheme_id = #{schemeId}
          AND psm.user_id = #{userId}
          AND psm.role_code IN (
              SELECT rti.role FROM role_type_info rti
              JOIN role_permission_manager rpm ON rti.id = rpm.role_id
              JOIN menu_url_info mui ON rpm.menu_id = mui.menu_id
              WHERE mui.menu_url = #{url}
          )
          AND EXISTS (
              SELECT 1 FROM user_role_info uri2
              WHERE uri2.user_id = psm.user_id
                AND uri2.project_id = #{projectId}
          )
    ) THEN 1 ELSE 0 END
</select>
```

### `PermSchemeService`

```java
// 复制方案伪代码
public Long createScheme(CreateSchemeRequest req) {
    Long newSchemeId = permSchemeMapper.insert(
            req.getProjectId(), req.getSchemeName(), req.getSourceSchemeId());
    if (req.getSourceSchemeId() != null) {
        List<SchemeMember> sourceMembers =
                permSchemeMemberMapper.listBySchemeId(req.getSourceSchemeId());
        for (SchemeMember m : sourceMembers) {
            permSchemeMemberMapper.insert(newSchemeId, m.getUserId(), m.getRoleCode());
        }
    }
    return newSchemeId;
}

// 删除方案前校验绑定占用
public void deleteScheme(Long schemeId) {
    int bindingCount = permSchemeResourceBindingMapper.countBySchemeId(schemeId);
    if (bindingCount > 0) {
        throw new BizException("该方案存在资源绑定，需先解绑后再删除");
    }
    permSchemeMemberMapper.deleteBySchemeId(schemeId);
    permSchemeMapper.deleteById(schemeId);
}
```

### `PermSchemeResourceBindingService`

```java
// 绑定/解绑伪代码，唯一索引 (project_id, resource_type, resource_id) 保证幂等
public void bindScheme(Long projectId, String resourceType, String resourceId,
                        Long schemeId, String operator) {
    permSchemeResourceBindingMapper.upsert(
            projectId, resourceType, resourceId, schemeId, operator);
    // 需记录审计日志：绑定操作人、时间、变更前后 schemeId
}

public void unbindScheme(Long projectId, String resourceType, String resourceId,
                          String operator) {
    permSchemeResourceBindingMapper.delete(projectId, resourceType, resourceId);
    // 需记录审计日志
}
```

## 三、建表 SQL 参考

```sql
CREATE TABLE perm_scheme (
    id                BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id        INT NOT NULL,
    scheme_name       VARCHAR(128) NOT NULL,
    source_scheme_id  BIGINT NULL,
    creator           VARCHAR(64) NOT NULL,
    create_time       DATETIME NOT NULL,
    update_time       DATETIME NOT NULL,
    KEY idx_project_id (project_id)
);

CREATE TABLE perm_scheme_member (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    scheme_id    BIGINT NOT NULL,
    user_id      VARCHAR(32) NOT NULL,  -- 类型对齐 user_role_info.user_id
    role_code    VARCHAR(100) NOT NULL,  -- 长度对齐 role_type_info.role
    create_time  DATETIME NOT NULL,
    KEY idx_scheme_id (scheme_id)
);

CREATE TABLE perm_scheme_resource_binding (
    id                     BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id             INT NOT NULL,
    resource_type          VARCHAR(32) NOT NULL,
    resource_id            VARCHAR(128) NOT NULL,
    resource_display_info  VARCHAR(256) NULL,
    scheme_id              BIGINT NOT NULL,
    operator               VARCHAR(64) NOT NULL,
    create_time            DATETIME NOT NULL,
    update_time            DATETIME NOT NULL,
    UNIQUE KEY uk_resource (project_id, resource_type, resource_id)
);
```

## 四、开发注意事项

1. **默认方案不落库**：前端"默认方案"页签不应对应 `perm_scheme` 表中的真实记录，其增删改操作应调用现状的项目成员管理接口，不要为了统一接口形态而强行插入一条"默认方案"记录，否则会与自定义方案的复制、删除等逻辑产生歧义。
2. **绑定表不应包含操作粒度字段**：不要在 `perm_scheme_resource_binding` 中增加 `action` 或类似字段试图描述"该资源上此方案能执行哪些操作"。角色能执行哪些操作，唯一权威来源是现状的角色-菜单-URL 权限矩阵；若未来确有更细粒度诉求，应通过在 framework 角色体系中新增角色实现，而不是在本表中新增维度。
3. **resource_id 不使用 JSON 结构**：该字段为字符串类型，具体拼接规则由各业务模块自行约定（如流水线场景直接使用 `pipelineId` 转字符串），framework 与 CICD 均不解析其内部结构，仅做整体匹配，以保证索引查找效率。
4. **成员一致性的安全防线在查询时校验，不依赖应用层清理的完整性**：`user_role_info` 存在多条删除路径（手工移除 `ProjectUserServiceImpl.deleteProjectUser`、三方同步删除 `SyncUserServiceImpl.deleteSyncUserByProjectId`、项目级联删除 `ProjectServiceImpl` 中的 `userRoleMapper.deleteByProjectId`），不要假设只在其中一处补充清理逻辑就能保证 `perm_scheme_member` 不残留已离开项目的用户。真正的安全防线是 `hasPermissionByScheme` SQL 内嵌的 `EXISTS` 校验（见上文），该校验不依赖任何清理路径的完整性。手工移除路径仍建议同步清理 `perm_scheme_member`，但目的是保持方案管理页面数据整洁（数据卫生），不是安全层面的必要条件。
5. **系统级角色穿透固定写在 `hasPermissionByScheme` SQL 内部的第一段 `UNION ALL` 分支，不是 Java 层方法判断**：与现状 `hasPermission` SQL 内嵌的 `(uri.project_id = #{projectId} or uri.role = 'admin')` 语义对齐，admin 段不带 `project_id` 限制，但需落在该 URL 的角色白名单子查询内。
6. **写路径统一走 framework 接口**：CICD 侧的流水线页面在方案配置、绑定/解绑操作中，均需调用 framework 层提供的接口完成，不应直接操作 `perm_scheme` 相关表，以保证深拷贝、校验、审计日志等业务逻辑不被绕过。
7. **绑定查询缓存需使用独立 Guava 缓存实例**：现状 `AuthInterceptor` 的本地缓存（`maximumSize=1000`，1min TTL）专用于缓存匿名访问判断结果，新增的绑定关系缓存不得复用该实例，避免互相挤占命中率；`isGitUrlPublic` 结果走的是 Redis 缓存（key 为 `projectId+pipelineId`），与本次新增缓存也是各自独立的两套机制，不要混用。
8. **绑定检查覆盖范围为 `PipelineControllerV2` 下全部带 `pipelineId` 的 `@CheckPermission` 方法**（约 30 个，含查看类接口如 `/detailInfo`、`/build/log`、`/exec-log` 等）；不带 `pipelineId` 的列表接口（`/list`、`/pipeline-run/list`）不受影响，继续走现状逻辑。查看类接口一并被收紧是否符合预期，需业务方在开发前确认（详见设计文档"7.安全设计"）。
9. **已知遗留风险披露，不在本次修复范围**：`extractPermissionContext` 中 `userId` 取自请求参数，客户端可伪造，绑定方案后同样可能被用于伪造方案内成员身份。本次改造不处理该问题，若开发过程中发现该问题被放大或需一并处理，需提前与需求方确认优先级，不要在实现过程中擅自扩大改造范围。
