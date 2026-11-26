# 横向越权防护方案 v2（项目级）

- 适用仓库：openlibing-ops
- 关联文档：
  - 旧方案：`openlibing-docs/spec/openlibing-ops/task_design/horizontal-privilege-guard/design.md`
  - 权限组方案：`openlibing-docs/spec/openlibing-cicd/task_design/resource-permission-scheme/design.md`
- 代码基准：openlibing-ops `dev`、openlibing-framework `master`、openlibing-gateway `master`、openlibing-common `master`

## 1. 背景

网关 `AuthFilter` 负责登录认证和菜单级纵向权限，只判断“当前用户的角色能否访问这个 URL”，不校验 URL 参数里的 `projectId`/`repoId` 是否属于该用户。ops 服务内没有资源归属校验，因此同一菜单权限下的用户可以篡改 `projectId`/`repoId` 访问其他项目的数据，典型问题包括：

- 精准覆盖率 `file/detail`、`case/file/detail` 返回其他项目源码；
- 测试报告 `repoUrls` 为空时查全量仓库明细；
- 仓库分支配置、E2E 达标阈值、看板链接配置可改他人项目；
- 项目/仓库列表、GitHub 仓库列表可枚举全量数据。

旧方案 `horizontal-privilege-guard` 已实现注解 + 切面，但在 2026-10-20 被 `72b926a11` 整体摘除。回退原因不是方向错误，而是判定语义有四个硬伤：

1. `system`/`general` 角色类型直接短路放行，导致 `visitor`、`dashboard`、`数字化运营看板管理员` 可以看所有项目源码；
2. 资源 id 为空时跳过校验，列表/导出仍可拉全量；
3. repo 类型角色行带 `project_id` 就放行整个项目，仓库角色越权到项目级；
4. 读和写用同一套判定，写操作没有更严格的角色要求。

本方案在旧组件基础上重做判定语义，不改变网关，不改机机接口。

## 2. 平台权限模型现状

### 2.1 角色与作用域

权限数据在 MySQL `openlibing` 库，核心表：

| 表 | 关键字段 | 说明 |
|---|---|---|
| `user_role_info` | `user_id, role, product_id, project_id, repo_id, perm_group_id` | 用户角色行，一行代表一个作用域 |
| `role_type_info` | `role, type` | `type = system/product/project/repo/general` |
| `project_info` | `project_id, product_id, parent_id` | 项目、所属产品、父子层级 |
| `repo_info` | `repo_id, repo_url, project_id` | 仓库归属项目 |
| `sdi_repo_info`（Doris） | `repo_id, repo_url, project_id` | 分析库仓库维度，用于 repoUrl 反查 |
| `perm_group` / `perm_group_resource_binding` | `project_id, resource_type, resource_id` | 权限组资源绑定，目前仅 PIPELINE，测试库 5 条 |

测试库数据特征（2026-11-14）：

- `user_role_info` 48,782 行，`perm_group_id` 全部为 0；
- project 类型角色 11,343 行，repo 类型角色 33,217 行，visitor 3,964 行；
- 平均每用户 12 条角色，最大 520 条；
- 80 个项目中 19 个有父项目，最深 3 层；
- 589 个用户只有 repo 角色、没有同项目的 project 角色，涉及 2,510 条 repo 角色行。

### 2.2 网关的边界

- `AuthMapper.queryMenuUrlByUserId`：`user_role_info → role_permission_manager → menu_url_info`，只算 URL 白名单，不含 query 参数；
- `identification = general_config` 的 URL 对所有登录用户放行；
- 网关会把 JWT 中的 `userId/userName/accountId/accountPlatform` 覆盖到 query 参数，下游拿到的 `userId` 可信；
- 无自定义权限组数据时，`perm_group_id = 0` 是默认组语义。

### 2.3 菜单授权现状（ops 相关）

| 菜单 | menu_level | 已授权角色 |
|---|---|---|
| 开源项目运营看板 100576 | menu_system | admin、dashboard、platform_operater、数字化运营看板管理员 |
| 工程能力运营看板 100834 | menu_system | admin、dashboard、数字化运营看板管理员 |
| 精准测试 100904 | menu_general | visitor、admin |
| 查询测试报告 100925 | menu_general | visitor |
| ops备案系统 100980 | menu_general | visitor、数字化运营看板管理员 |

结论：不能按“角色类型”一刀切放行。`visitor` 被授予了精准测试/测试报告菜单，但业务上不允许其查看源码和测试明细，必须在 ops 内做项目级校验。

## 3. 设计目标与原则

1. 网关保持现状：认证 + 菜单级纵向权限。
2. ops 内按**项目级**做横向权限，不做仓库级。
3. 显式声明每个接口的资源范围，不再按角色类型猜测。
4. 详情接口缺资源 id 返回 400，不跳过；列表接口按可见集合过滤。
5. 读、写分离：读允许项目成员，写只允许项目管理员和全局管理员。
6. 判定在 SQL 层完成，禁止先查全量再内存过滤。
7. 默认拒绝，越权返回 403 并记录审计。

## 4. 最终权限模型

### 4.1 资源范围

| 范围 | 判定 | 典型接口 |
|---|---|---|
| `GLOBAL` | 不查资源，网关菜单权限已控制 | 全局汇总看板、项目/产品下拉元数据、健康检查 |
| `PROJECT` | 校验项目权限；`repoId` 先反查 `project_id` | 项目/仓库明细、测试报告、精准覆盖率、流水线明细 |
| `OWNER` | `userId` 等于资源归属人 | 备案、备注等个人数据 |
| `LIST_FILTER` | 不返回 403，按可见项目集合过滤 | 列表、导出、下拉 |

不设 `REPO` 范围。`repoId`、`repoUrl`、`pipelineId` 都先反查 `project_id`，再按项目权限判断。

### 4.2 判定矩阵

| 角色/条件 | 全局汇总读 | 项目明细读 | 项目配置写 |
|---|---|---|---|
| `super_admin` / `admin` / `platform_operater` | 放行 | 放行 | 放行 |
| `dashboard` / `数字化运营看板管理员` | 放行 | 放行（跨项目） | 拒绝 |
| `product_manager` 且 `product_id` 命中 | 放行 | 放行 | 拒绝 |
| project 类型角色且 `project_id` 命中目标或祖先 | 放行 | 放行 | 仅 `project_manager` |
| repo 类型角色 | 放行（如果菜单允许） | 拒绝 | 拒绝 |
| `visitor` / `general` | 放行（如果菜单允许） | 拒绝 | 拒绝 |

说明：

- “project 类型角色”指 `role_type_info.type = 'project'`，包括 `project_member`、`project_manager`、`project_tool_manager`、`project_approver`、`project_cie` 等。
- repo 类型角色即使行里带 `project_id`，也不作为项目权限依据。
- `dashboard` / `数字化运营看板管理员` 可跨项目看明细，属于高权限角色，必须记录访问审计。
- `product_manager` 默认按“可读本产品下所有项目”处理。

### 4.3 项目层级继承

- 读/写判定时，目标项目取“自身 + 所有祖先项目”的集合：`projectIds = {projectId} ∪ ancestors(projectId)`。
- 可见项目列表取“用户有权限的项目 + 这些项目的所有子孙项目”。
- `project_info` 只有 80 行，启动时加载为 `Map<projectId, parentId>`，内存解析祖先/子孙，5 分钟刷新一次，不写递归 SQL。

### 4.4 与旧方案的区别

| 项 | 旧方案 | v2 |
|---|---|---|
| 角色类型短路 | system/general 全放行 | 只对显式全局读角色放行；visitor 不放行项目明细 |
| 空资源 id | 跳过校验 | PROJECT 缺 id 返回 400；列表走 LIST_FILTER |
| repo 角色 | 带 project_id 可看整个项目 | 不算项目权限 |
| 读写 | 同一套 | 写只允许全局管理员 + `project_manager` |
| 列表/导出 | 可查全量 | 按可见项目集合过滤 |
| 项目层级 | 不处理 | 父项目继承子项目 |
| 权限组 | 不处理 | 固定 `perm_group_id = 0`，为后续留口子 |

## 5. 组件设计

### 5.1 注解

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Repeatable(ResourceScopes.class)
public @interface ResourceScope {
  ScopeType scope();          // GLOBAL / PROJECT / OWNER / LIST_FILTER
  ResourceId resourceId() default ResourceId.NONE;
  OperationType operation() default OperationType.READ;
}
```

`ResourceId` 枚举覆盖字段名族：

- `PROJECT_ID`：`projectId`、`projectIds`、`projectIdList`
- `REPO_ID`：`repoId`、`repoIds`、`repoIdList`
- `REPO_URL`：`repoUrl`、`repoUrls`
- `PIPELINE_ID`：`pipelineId`、`pipelineIds`

`ResourceId.NONE` 用于 `GLOBAL`。

### 5.2 切面流程

`ResourceScopeAspect`：

1. 从 `UserUtil.currentUserId` 取 `userId`（只读 token Cookie）；缺失抛 403。
2. 按 `ResourceId` 从方法实参提取资源 id：参数名、对象 getter、集合元素 getter 三种来源。
3. 归一化：展平集合、String/Number 统一；无法转换抛 400。
4. `GLOBAL` 直接放行；`PROJECT` 缺 id 抛 400；`LIST_FILTER` 不拦截，由 Service 注入可见集合。
5. 调 `ResourceAccessService.checkProject(userId, projectId, operation)`，失败抛 `PermissionDeniedException`。
6. 同一方法多个 `@ResourceScope` 时逐个校验，任一失败整体拒绝。

### 5.3 ResourceAccessService

```java
boolean checkProject(String userId, Integer projectId, OperationType operation);
Set<Integer> visibleProjectIds(String userId);
Integer resolveProjectIdByRepoId(Integer repoId);
Integer resolveProjectIdByRepoUrl(String repoUrl);
Set<Integer> ancestors(Integer projectId);
Set<Integer> descendants(Integer projectId);
```

- `checkProject`：先取目标项目 + 祖先集合，再执行单条 EXISTS。
- `visibleProjectIds`：按角色计算可见项目，再展开子孙项目。
- `resolveProjectIdByRepoId`：查 `repo_info`；不存在返回 null，调用方抛 403。
- `resolveProjectIdByRepoUrl`：先查 `repo_info`，查不到再查 Doris `sdi_repo_info`；都查不到抛 403。
- 所有 Mapper 标注 `@DataSource(DataSourceEnum.MYSQL)`，Doris 查询单独标注。

### 5.4 SQL 语义

读：

```sql
SELECT EXISTS (
  SELECT 1
  FROM user_role_info uri
  JOIN role_type_info rti ON rti.role = uri.role
  WHERE uri.user_id = #{userId}
    AND uri.perm_group_id = 0
    AND (
      uri.role IN ('super_admin','admin','platform_operater',
                   'dashboard','数字化运营看板管理员')
      OR (rti.type = 'product' AND uri.product_id = #{productId})
      OR (rti.type = 'project' AND uri.project_id IN
          <foreach collection="projectIds" item="id" open="(" close=")" separator=",">#{id}</foreach>)
    )
);
```

写：

```sql
SELECT EXISTS (
  SELECT 1
  FROM user_role_info uri
  JOIN role_type_info rti ON rti.role = uri.role
  WHERE uri.user_id = #{userId}
    AND uri.perm_group_id = 0
    AND (
      uri.role IN ('super_admin','admin','platform_operater')
      OR (uri.role = 'project_manager' AND uri.project_id IN
          <foreach collection="projectIds" item="id" open="(" close=")" separator=",">#{id}</foreach>)
    )
);
```

注意：

- 使用 `JOIN role_type_info` 时，`user_role_info` 中存在 `project_cmc`、`committer_project`、`lingshu` 三个未登记角色（共 11 行），会被 JOIN 丢弃；这些行按“无权限”处理，需在数据治理中补登记或清理。
- `perm_group_id = 0` 必须固定，避免后续自定义权限组数据污染。
- `productId` 由 `project_info.product_id` 反查得到，不信任前端传入。

### 5.5 列表过滤

`LIST_FILTER` 接口不抛 403，Service 层：

1. 调 `visibleProjectIds(userId)`；
2. 集合为空直接返回空页；
3. Mapper SQL 增加 `AND project_id IN (...)` 或 `EXISTS` 子查询；
4. 如果请求显式传了 `projectId`，先按 `PROJECT` 校验，不通过返回 403。

Doris 查询同样先在 MySQL 取可见 `project_id` 集合，再下推 `IN`；集合过大时分批。

### 5.6 异常与审计

- `PermissionDeniedException extends BizException(NO_PERMISSION)`，`GlobalExceptionHandler` 统一返回 403。
- 审计日志字段：`userId`、`scope`、`operation`、`projectId/repoId`、请求 URI、结果。
- 对 `dashboard` / `数字化运营看板管理员` 的跨项目访问单独打标，便于审计。

## 6. 接口改造清单

### 6.1 分类

| Controller | 范围 | 说明 |
|---|---|---|
| `PrecisionCoverageController` | `PROJECT` | 所有下钻接口强制 projectId/repoId；`file/detail`、`case/file/detail` 为 P1 |
| `ReportController` | `PROJECT` / `LIST_FILTER` | `data/query` 强制 repoUrls 或 projectId；`template/list` 过滤 |
| `RepoController` | `PROJECT` + `WRITE` | 读写分离；`branch/config/batch` 写权限 |
| `OpsOverviewController` | `GLOBAL` / `PROJECT` + `WRITE` | 汇总 GLOBAL；项目明细 PROJECT；`pr-e2e-target/batch`、`link-config` 写权限 |
| `PipelineController` | `PROJECT` | `repoUrl` 反查 project |
| `ProjectController` | `PROJECT` | 项目详情 |
| `OpsGithubController` | `LIST_FILTER` / `PROJECT` | 不传 projectId 时过滤；传了则校验 |
| `ResourceOperationController` | `PROJECT` | 资源运营明细 |
| `ResourceController` | `PROJECT` | 资源看板 |
| `CodeCheckDashboardController` | `PROJECT` + `WRITE` | `branch-config/add` 写权限 |
| `SecurityDashboardController` | `PROJECT` | 安全/版权/依赖明细 |
| `NpuUsageController` | `PROJECT` / `LIST_FILTER` | filters 过滤；明细校验 |
| `QualityDashboardController` | `PROJECT` | 质量看板 |
| `TestCaseBoardController` | `PROJECT` | 用例目录树 |
| `Filing*` | `OWNER` + 现有审批逻辑 | 保留 creator/审批人/管理员判定 |
| `ProductQuality*` | `PROJECT` + `WRITE` | `milestoneId → projectId` 反查；写权限 |
| `CommonController` | 注册表 | `/common/detail` 按 category 注册；`remark` 走 `OWNER`；`export` 走 `LIST_FILTER` |
| `external/*` | 不纳入 | 机机接口，按网关 HMAC 体系处理 |

### 6.2 拆分原则

1. 明细与汇总拆开：全局汇总保持 `GLOBAL`，项目明细必须带 projectId。
2. 列表与详情拆开：列表走 `LIST_FILTER`，详情走 `PROJECT`。
3. 读与写拆开：写接口单独路径或单独方法，统一 `WRITE`。
4. `/common/detail` 按 category 拆分：`precisionSource`、`testReport` 独立接口；其余 category 进注册表，未知 category 拒绝。

### 6.3 实施顺序

| 阶段 | 范围 |
|---|---|
| P1 | 精准覆盖率源码、测试报告明细、所有配置写接口 |
| P2 | 仓库/流水线/安全/NPU/质量/用例等明细；列表与导出过滤 |
| P3 | `/common/detail` 拆分；全局汇总接口标注 `GLOBAL`；删除“空 id 全量”逻辑 |

## 7. 性能与缓存

- 详情接口单条 `EXISTS`，走 `idx_user_id`；平均 12 条角色、最大 520 条，不预加载全量角色。
- 列表接口用 `IN`/`EXISTS` 下推，禁止先查后过滤。
- 项目层级表 80 行，内存解析；5 分钟刷新。
- 可选 Caffeine：
  - `userId → visibleProjectIds`，TTL 30~60 秒；
  - `projectId → ancestors/descendants`，TTL 5 分钟。
- 权限收回延迟最多一个 TTL；如需秒级生效，可去掉缓存或加失效广播。
- 建议 DDL（需 DBA 执行）：`user_role_info(user_id, project_id, role)` 组合索引。

## 8. 灰度与回滚

1. **shadow**：所有注解先只记录不拦截，统计“会被拒绝”的请求量和用户分布，持续 3~7 天。
2. **P1 强制**：源码/测试明细/写接口先拦截。
3. **P2 强制**：列表/导出改为可见集合过滤。
4. **P3 收口**：拆 `/common/detail`，删除全量兜底。
5. 回滚：注解增加 `enforce = false` 开关，或配置中心灰度白名单；回滚不涉及数据结构变更。

## 9. 数据影响与上线前核对

1. **589 个用户只有 repo 角色、没有项目角色**，涉及 2,510 条 repo 角色行。按本方案这些用户会失去项目明细访问权限。上线前二选一：
   - 补 `project_member` 项目角色（需改数据）；
   - 接受收紧，先 shadow 观察。
2. **visitor 保留精准测试/测试报告菜单**，后端返回 403；前端用 `NoPermissionPopover` 提示“需项目权限”。
3. **未登记角色**：`project_cmc`、`committer_project`、`lingshu` 共 11 行不在 `role_type_info`，按无权限处理；需补登记或清理。
4. **权限组**：当前全部 `perm_group_id=0`；后续启用权限组时，需评估是否让资源绑定组覆盖默认组判定。

## 10. 测试策略

- `ResourceAccessService` 单测：全局读/写、product_manager、project 角色、repo 角色拒绝、父项目继承、visitor 拒绝、空项目集合。
- `ResourceScopeAspect` 单测：参数名/getter/集合提取、缺 id 400、多注解叠加、userId 缺失 403。
- `ProjectHierarchyService` 单测：祖先/子孙解析、环形数据防御。
- Controller 测试：P1 接口无权限 403、有权限通过、列表过滤为空。
- 集成验证：用测试库造“只有 repo 角色”和“只有 project 角色”两类用户，分别访问精准覆盖率源码接口。
- shadow 指标：按 URI 统计 would-deny 数量、用户数、项目分布。

## 11. 风险与待定项

| 项 | 说明 | 处理 |
|---|---|---|
| `dashboard`/`数字化运营看板管理员` 跨项目读明细 | 包括源码/测试明细，权限较高 | 已确认；加访问审计 |
| `product_manager` 读本产品项目 | 代码中无现成产品→项目过滤 | 已按默认处理；如需收紧再改 |
| repoUrl 反查 | `repo_info` 只有 1,192 条，Doris `sdi_repo_info` 更全 | 先 MySQL 后 Doris，查不到拒绝 |
| 520 角色用户 | 可见项目集合可能较大 | 列表用 SQL 子查询，不加载全量 id |
| 权限收回延迟 | 缓存 TTL 30~60s | 可接受则保留，否则去缓存 |
| 项目层级数据异常 | 19 个子项目，最深 3 层 | 启动校验 parent 不存在/环，异常按根处理并告警 |

## 12. 代码改动清单

| 文件 | 改动 |
|---|---|
| `infrastructure/aop/permission/ResourceScope.java` | 新增注解 |
| `infrastructure/aop/permission/ResourceScopes.java` | 新增容器注解 |
| `infrastructure/aop/permission/ResourceScopeAspect.java` | 重写切面 |
| `infrastructure/enums/ScopeType.java` | 新增 |
| `infrastructure/enums/ResourceId.java` | 扩展 REPO_URL/PIPELINE_ID |
| `infrastructure/enums/OperationType.java` | 新增 READ/WRITE |
| `domain/service/permission/ResourceAccessService.java` | 重写判定与可见集合 |
| `domain/service/permission/ProjectHierarchyService.java` | 新增层级解析 |
| `domain/mapper/permission/ResourceAccessMapper.java` + XML | 重写 SQL |
| `infrastructure/exception/PermissionDeniedException.java` | 复用 |
| `infrastructure/exception/GlobalExceptionHandler.java` | 403 handler |
| `api/controller/*` | 按第 6 章加注解、拆接口 |
| `src/test/java/.../permission/*` | 新增单测 |
