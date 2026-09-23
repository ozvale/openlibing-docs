# CICD 资源级权限方案设计文档（v5）

> 关联 Issue：https://gitcode.com/openlibing/openlibing-cicd/issues/223
> 流程模式：Full（跨仓跨团队：framework + cicd + gateway + codecheck + coderepo + 前端）
> v5 变化（评审后重大转向）：**放弃独立建表方案，改为在 `user_role_info` 表上加 `perm_group_id` 列**；概念更名为"权限组"（Permission Group）；默认组与其他组同等地位（同步仅对默认组，其余组纯手工维护）；存量跨服务直查 SQL 全量整改（部署门禁）；gateway 鉴权层纳入设计视野。
> 2026/09/17 同步：成员平行接口定案删除、复用存量链路（8 章）；RPC 分阶段策略定稿（4.4）；framework/cicd 全量审计整改完成（3.1.1）；fillPermGroupInfo 下沉 service（5 章）。
> 2026/09/23 勘误与实现状态同步：穿透口径由单一 admin 扩为三全局角色 `admin`/`super_admin`/`platform_operater`（与存量 checkProjectPermissions 口径对齐，4.2/9 章）；RPC 已落地实现（4.4/5 章，非"计划"状态）；成员管理复用存量 `/project/user/*` 接口（8 章，注意不是 `/manage/product/user/*`）。

## 30 秒速览

**一句话**：`user_role_info` 增加 `perm_group_id` 列（存量数据全部置 0 = 默认权限组）；资源绑定某权限组后，鉴权的角色数据按该组过滤；未绑定资源走默认组，行为与现状完全一致。

| 概念         | 是什么                                              | 存在哪                                    |
| ------------ | --------------------------------------------------- | ----------------------------------------- |
| 默认权限组   | `perm_group_id = 0` 的存量数据（保留值，非自增 id） | `user_role_info` 现有行                   |
| 自定义权限组 | 同表内 `perm_group_id = 组id` 的成员-角色记录       | `user_role_info` + `perm_group`（组定义） |
| 资源绑定     | 某条资源指定用哪个组鉴权                            | `perm_group_resource_binding`（新增）     |

**效果示例**：流水线 P1（未绑定）→ 按默认组鉴权，与今天完全一致；流水线 P2（绑定组"生产发布管控"）→ 仅该组成员与全局角色（admin/super_admin/platform_operater）可操作，项目管理员未入组同样被拒（已定案）。

**核心不变式**：权限组只改变"角色数据来源的过滤范围"，不改变"角色能做什么"（后者永远由角色-菜单-URL 矩阵决定）。

## 1. 方案设计

| #   | 要点                                                              | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 同表加列                                                          | `user_role_info` 新增 `perm_group_id INT NOT NULL DEFAULT 0`；存量 47331 行自动归默认组，MySQL 8 INSTANT DDL 秒级无锁                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2   | 保留值 0                                                          | 默认组用 `perm_group_id=0` 而非真实记录——迁移零成本；`perm_group` 表不插 id=0 的行（避免 MySQL 自增语义问题），默认组在组列表接口中**虚拟返回**（id=0 + 项目名 + "默认"标记）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 3   | 组间同等地位                                                      | 组的 CRUD、绑定、成员管理能力完全一致；**务实差异仅一条：三方同步（gitee/gitcode）只写默认组**（已与领导确认），自定义组纯手工维护                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 4   | 复制创建                                                          | 支持基于默认组或其他组复制（同表 `INSERT ... SELECT`，改 perm_group_id），复制后互不联动                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| 5   | 删除语义（已定案，2026/09/16 更新为勾选式）                       | 成员列表为平铺展示（每行一条组记录），删除默认删一行；删默认组行时弹窗列出该成员在其他权限组的记录，**逐条勾选**是否连带删除（默认全不勾，opt-in）——取代原"删全部+二选一提示"与 `isValidProjectMember` 僵尸标记方案。删自定义组行静默只删该行。删除后组本身保留（空组无害，绑定关系不变）                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 6   | 资源绑定即整体切换                                                | 绑定后该资源全部 `@CheckPermission` 接口按组过滤鉴权（含查看类，已定案）；解绑自动回退                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 7   | 不新增权限维度                                                    | 不在绑定层面定义操作粒度；更细管控走 framework 新增角色                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 8   | 管理端形态（2026/09/16 二次定案：**一页化增强**，取代"两页并存"） | 现有成员管理页（`projectUserManage.vue`）原地增强为**全组平铺**：存量 `POST /project/user/query-project-user` 改造（每行一条组记录，新增 permGroupId/groupName 返回字段 + 可选 permGroupIds 筛选参数，不传=全部组含默认组行）；列表加"权限组"列；工具栏加权限组**下拉多选筛选**；右上"管理权限组"按钮弹窗承载组的创建/删除（默认组删除置灰提示"默认权限组不允许删除"；有绑定提示"仍绑定了 N 个资源，请先解绑"）。**行级操作按 permGroupId 路由**：默认组行 → 存量 update/delete-project-user（保留同步/审计联动）；自定义组行 → 存量接口 + permGroupId 入参。添加成员弹窗沿用存量输入账号模式 + **权限组多选**（默认组+自定义组可同勾，统一走存量接口，自定义组传 permGroupId）。原"独立权限组页"与"组页签查询"接口废弃 |

## 2. 两大任务结构（本次交付的整体框架）

```
任务一：CICD 数据级权限改造（本需求核心）
  └─ 完成后不可立即部署
任务二：全仓直查整改与对齐（组织级数据治理）
  └─ 完成度 = 部署门禁
```

| 任务           | 范围                                                                  | 产出                                |
| -------------- | --------------------------------------------------------------------- | ----------------------------------- |
| 一、数据级权限 | framework 组管理接口 + `user_role_info` 加列 + cicd 鉴权组分支 + 前端 | 可部署的代码（等门禁）              |
| 二、直查整改   | 组织内所有直查 `user_role_info` 的仓：盘点→分类→出 patch→对齐认领     | 各仓加 `perm_group_id=0` 的整改合入 |

**部署门禁（硬约束）**：任务一上线即产生自定义组数据，未加 `perm_group_id=0` 的存量查询立刻混入（用户在自定义组的角色污染其他服务的鉴权）。因此：**组织内所有直查服务整改完成前不得部署**；上线排期以任务二收口为准（跨团队对齐通常是关键路径）。

## 3. 存量直查整改（任务二详设）

### 3.1 当前已知直查分布（grep 扫描，全集待组织确认）

| 服务      | 直查处 | 写入情况                                                                                                                                                                                                                                     |
| --------- | :----: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| framework |   46   | **写入大头**：成员 CRUD、三方同步、项目级联删除。**✅ 2026/09/17 全量审计整改完成（见 3.1.1）**                                                                                                                                              |
| coderepo  |   20   | 待细查（`RepoUserRoleInfoMapper` 疑有仓级角色写入）                                                                                                                                                                                          |
| gateway   | **6**  | ⚠️ 有写入：`insertUserRoles` / `deleteSyncUserByUserId`（历史同步落库残留）。**高危标注：`AuthMapper.queryMenuUrlByUserId` 查用户全部可访问 URL 白名单（仅按 user_id 过滤），自定义组角色会扩大用户的 URL 白名单，必须加 `perm_group_id=0`** |
| codecheck |   8    | 纯查看                                                                                                                                                                                                                                       |
| cicd      |   6    | 纯查看（鉴权 + 成员展示 + `HwProjectInfoMapper` 的 isProjectAdmin/isProjectMember——角色过滤判断）。**✅ 2026/09/17 全量审计整改完成（见 3.1.1）**                                                                                            |

**排查方法（四层搜索，防漏）**：① 表名字符串 `user_role_info`（XML/注解 SQL/文档）；② Entity 类名（`UserRoleInfoEntity`——MyBatis-Plus QueryWrapper 在 Java 拼 WHERE，XML 搜不到）；③ MP 泛型签名（`BaseMapper<UserRoleInfo` 等，自带无 XML 方法）；④ Liquibase changelog 引用。

### 3.1.1 framework / cicd 全量审计结果（2026/09/17，已整改合入 feat/perm-scheme）

两仓按四层法完成全量审计并整改（framework commit `e97ecc5f` + `3a1264c6`，cicd commit `d03a9e703`）：

- **SQL 级固定滤组（8 条方法）**：`queryInfoByUser` / `queryInfoByRole` / `queryUserInfos`（UserRoleMapper + UserBasicMapper 两处）/ `queryByProjectId` / `queryAllAccountName` + `queryAllAccountNameCount` / `isUserInRoleInfo`（死代码，按"防复活"定案补条件不删）/ `IAMAccountMapper` 2 处角色子查询
- **Java 调用点补 `setPermGroupId(0L)`（15 处）**：`InternalServerImpl` 4 处 RPC 鉴权入口（`checkRepoUserNamePermission` / `getUserRole` / `checkProjectPermissions` / `checkPermissions`）+ ProjectUser / ProductUser / SystemUser / ApplyPermission / UserBasic 各 ServiceImpl 的成员查重与管理员判定
- **cicd Wrapper 滤组（1 处）**：`ShortcutServiceImpl.checkUserPermission`（实体补 `permGroupId` 字段以支持列映射）

审计新发现、此前任何清单未覆盖的漏网点：权限快照构建 `queryInfoByUser`（污染 Redis 24h 权限缓存）、IAM 账号可见性子查询、`queryAllAccountName` 成员候选。P2 展示类（管理端分页 / 个人中心角色展示 / AOP 日志快照）按定案本次不动。

**2026/09/17 全量复审修复（合入前扫描发现，均已修复）**：

- `getOperationPermissions`（UserBasicServiceImpl，前端按钮矩阵数据源）漏加组过滤——自定义组 PROJECT 角色会混入按钮计算导致误亮——已补 `setPermGroupId(0L)`
- `getUserRole` RPC 此前 `setPermGroupId(0L)` 未被 `queryByLimit`/`count` SQL 消费（假整改）——两条 SQL 已补 permGroupId 动态条件，其他调用方不传不受影响
- `query-project-user` 的 `countProjectUserByUserId`/`countProjectUserByAccount` 补 permGroupIds 筛选（此前 limit 分支已筛选、count 分支漏筛，组合筛选时分页 total 不一致）
- `queryInfoByUser`/`queryInfoByRole` SELECT 补 `perm_group_id` 列（同 queryInfo 曾发生的"实体恒 null"同型隐患）
- cicd 2 参 `getPipelineDetail` 恢复独立实现（此前误委托 3 参重载导致内部 6 处调用方异常面扩大——绑定查询失败会抛进事件监听器）
- 遗留待定：`SelectServiceImpl.getSpaceSelect` 系统级角色查询未滤组（正常写入路径无自定义组系统角色，防御性遗漏，是否补待定）

### 3.2 整改原则（一句话版）

> **存量一律 `perm_group_id = 0`（SELECT 加条件 / INSERT 显式写值），无例外；动态 perm_group_id 只存在于新功能四处**（cicd 资源鉴权、组页签查询、添加成员组写入、framework RPC/接口入参）。

**为什么写死 0 是对的**：存量服务的业务需求没变（只做接口级鉴权），`AND perm_group_id = 0` 唯一的差别是排除"本不属于他们的自定义组数据"——行为完全等价的防御性修复，无逻辑评审负担。

**高危子类提示**："查用户全部角色再内存遍历判断"的调用模式（各服务 `checkProjectPermissions` 类逻辑）必须逐一确认，否则自定义组里的 `project_manager` 角色会在其他服务被误判为真项目管理员——跨服务数据污染是加列后的最大隐患。

### 3.3 整改判据（按场景，不按服务）

| 判据                          | 处理                                                                                                           |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 读路径且语义为"项目成员/角色" | 本次加 `perm_group_id=0`（等价修复）                                                                           |
| 是否切 framework RPC          | **分库准备度问题，独立专项，不与本次上线捆绑**——对齐会上作为各负责人的选项（0 / RPC / 0+RPC 排期），不替他们选 |

### 3.4 对齐表模板（任务二交付物）

| 服务                        | 位置（文件+SQL id） | 使用场景（业务语言） | 类型 |  分类   | 整改方案         | 负责人   | 状态                        |
| --------------------------- | ------------------- | -------------------- | :--: | :-----: | ---------------- | -------- | --------------------------- |
| （每处一行，grep+细读后填） |                     |                      | R/W  | A/B/C/D | 加0 / RPC / 不动 | 对齐后填 | 待对齐→已认领→已整改→已验证 |

分类定义：A=纯默认组语义 / B=需感知资源组（预期极少）/ C=写入 / D=纯 JOIN 辅助（可不动）。

**降低协调成本的技巧**：扫描后直接为各仓准备好现成 patch（diff 形式），对齐会变成"认领 patch 会"。

### 3.5 验证判据

整改完成的判据不是"改完了"，而是：**BETA 验收用例——造一条 `perm_group_id != 0` 的数据后，跑各服务存量功能，确认自定义组数据不混入**（含：cicd 鉴权、gateway 鉴权、codecheck/coderepo 的管理员判断、framework 成员页）。

## 4. 实现逻辑设计

### 4.1 鉴权调用链路（三层视野）

```
浏览器 → gateway PermissionCheckFilter（第一道：JWT 取 userId，直查 user_role_info 粗过滤；
         /pipeline/ 前缀放行交给 cicd 自建鉴权；无 token 的非 pipeline 请求在此 403）
       → cicd AuthInterceptor（第二道，本需求改造点）
       → 业务接口
```

**网关层的两个影响已评估**：

1. 网关版 `hasPermission` SQL 同样直查 `user_role_info` → 纳入整改清单（加 `perm_group_id=0`）
2. 匿名可达性：网关对非 `/pipeline/` 的项目路径无 token 直接 403 → **匿名请求仅 `/pipeline/` 前缀能到达 cicd**，恰好与绑定资源路径重合，匿名分支设计按实际可达路径生效；不可达路径的匿名分支属防御性代码保留（不删——网关行为不是 cicd 的契约，cicd 鉴权完整性不依赖上游宽容）

**职责边界原则（网关只查默认组为何正确且不会错杀）**：网关对 `/pipeline/` 路径**直接放行**（现状代码注释"流水线在openlibing-cicd仓库校验权限"），资源级裁决完全由 cicd 按绑定组执行。网关的用户级白名单只裁决"接口级/角色级"权限——组内角色本就不该影响这类判断，所以它只看默认组是职责边界的正确映射，而非妥协：**网关白名单是粗筛下限，资源级鉴权是精筛，精筛严于粗筛时网关永不错杀**。推论（对后续 codecheck/coderepo 接入的约束）：每个接入资源级权限的服务须具备自己的绑定组鉴权拦截层，并保证该资源路径能过网关粗筛（路径放行约定，或默认组角色天然覆盖）。

### 4.2 cicd 鉴权 SQL（同表后大幅简化）

存量 `hasPermission` / `hasPublicPermission` **属整改项**：逻辑结构不动，加 `perm_group_id=0`（与项目匹配段同级，全局角色穿透段保持不滤组）。新增 `hasPermissionByGroup`，同表后**不再需要 UNION ALL 和 EXISTS 兜底**；该 SQL 落在 **framework 仓 `UserRoleMapper`**，cicd 经内部 RPC 调用（见 4.4）：

```sql
SELECT CASE WHEN EXISTS (
    SELECT role FROM user_role_info uri
    WHERE uri.user_id = #{userId}
      AND (uri.role IN ('admin','super_admin','platform_operater') OR uri.perm_group_id = #{permGroupId})
      AND uri.role IN (
          SELECT rti.role FROM role_type_info rti
          JOIN role_permission_manager rpm ON rti.id = rpm.role_id
          JOIN menu_url_info mui ON rpm.menu_id = mui.menu_id
          WHERE mui.menu_url = #{url}
      )
) THEN TRUE ELSE FALSE END
```

> 与现状穿透语义对齐：全局角色（admin/super_admin/platform_operater，与存量 checkProjectPermissions 口径一致）不限项目（但需在 URL 角色白名单内）；组内成员按 `perm_group_id` 过滤后仍需过角色白名单——**白名单判断逻辑不变，只是数据范围从"项目"换成"组"**。
> join 字段已核实：`rpm.role_id` / `mui.menu_id` / `mui.menu_url`（该表无 `role_type_id` 字段，`menu_url_info` 字段非 `id`/`url`，勿回退错误字段名）。
> 原设计的 EXISTS 成员兜底、`isValidProjectMember` 僵尸标记、双数据源复制分支——**全部消失**（同表红利）。

### 4.3 插入位置（不变，v4 结论保留）

绑定查询插在 `extractPermissionContext` 之后、`isGitUrlPublic` **之前**——否则绑定的公开仓资源被短路和匿名放行绕过。命中绑定跳过公开仓短路与匿名分支；未绑定零改动。绑定查询经内部 RPC 调 framework（见 4.4）+ 独立 Guava 缓存（TTL 5 秒，未绑定结果也缓存防穿透）。

### 4.4 方案管理链路与 RPC 分阶段策略（2026/09/17 定案）

- 组/绑定的写路径统一走 framework 接口；cicd 鉴权读路径**已 RPC 化**（已实现：cicd `PermGroupQueryServiceImpl` 经 `PermGroupFeignClient` 调 framework 内部接口 + 绑定独立 Guava 缓存 TTL 5 秒，未绑定结果也缓存防穿透）

**RPC 分阶段策略**（为分库做准备，分库前两个月先搞定新增查询）：

| 阶段             | 范围                                                                                                        | 状态                                         |
| ---------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| 本次（任务一内） | **新增查询走 RPC**：`hasPermissionByGroup`、`queryBoundPermGroup` 等 cicd 侧新增查询改调 framework 内部接口 | **已实现**（framework `InternalPermGroupController` 4 接口 + cicd `PermGroupFeignClient`） |
| 本次（任务一内） | **存量热路径维持本地直查**：`hasPermission` 等只补 `perm_group_id=0`                                        | 已完成（3.1.1 审计整改）                     |
| 任务二           | 其余存量直查的 RPC 化作为各仓独立选项（0 / RPC / 0+RPC 排期），不替对方选                                   | 待对齐                                       |

**framework 侧内部接口**（4 个，已实现，前缀 `/internal-server/perm-group/`，独立 `InternalPermGroupController`——不进 `InternalServerController` 防持续膨胀）：`POST /check`（组鉴权，即 hasPermissionByGroup）、`POST /bound-group`（按资源查绑定组）、`POST /group-operations`（组操作权限）、`POST /project-permissions`（项目绑定关系总览）；粗粒度合并模式，热路径每请求最多 1 次 RPC（鉴权与绑定信息合并返回，避免按资源逐条 RPC）。

**cicd 侧配套**（Spring Cloud Feign + OkHttp）：

- **连接池**：启用 OkHttp 连接池复用 TCP 连接，避免每次请求新建连接放大延迟
- **超时**：connect 1s / read 2s（短超时快速失败）
- **缓存**：组鉴权热路径独立 Guava 缓存，键 `(userId, permGroupId, url)`，TTL 5 秒；绑定查询沿用既有独立缓存（TTL 5~10 秒）
- **失败语义（fail-closed）**：RPC 调用失败一律鉴权拒绝、绝不降级放行；绑定查询失败按全拒绝处理；**拒绝结果不缓存**（防故障期间拒绝被固化）

## 5. 类设计

### framework 层

| 类名                                          | 职责                                                                                                                                                                                                               |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PermGroupController`                         | 仅 9 个接口：组列表（虚拟返回默认组）/ 创建（支持复制，返回复制计数）/ 删除（绑定占用校验）+ 绑定 6 个（单条/批量绑定、解绑、按资源查/按组反查/批量查）。**成员增删改无独立接口，复用存量项目成员链路（见 8 章）** |
| `PermGroupService`                            | 组核心逻辑：复制（`copyGroupMembers` 三条件排除：排除 `role='committer_project'`（代码提交者）、repo 非空（仓库角色）、`sync_flag` 无效（同步账号）的记录——仅复制人工可添加成员）、删除前绑定占用校验、同项目重名校验                                  |
| 存量成员 Service（ProjectUserServiceImpl 等） | `BatchAddUserDTO` 加可选 `permGroupId`（入组写入，`insertUserRoles` 取实体 IFNULL 值）；查重按 `(userId, role, projectId, permGroupId)` 四元组；`updateProjectUserData` 编辑查重加组维度                           |
| `InternalPermGroupController`（已实现）   | 4 个内部 RPC 接口（见 4.4），承接 cicd 新增查询                                                                                                                                                                    |
| `PermGroupResourceBindingService`             | 绑定关系维护：单条/批量/按资源查询/按组反查                                                                                                                                                                        |
| 组定义 Mapper + 绑定 Mapper                   | `perm_group` / `perm_group_resource_binding` 持久层（**成员数据无独立 Mapper——直接在 `UserRoleMapper` 加按 perm_group_id 过滤的查询/写入方法**）                                                                   |
| `SyncUserServiceImpl` 等                      | 存量写入链路加 `perm_group_id=0`（framework 自身整改）                                                                                                                                                             |

### CICD 层

| 类名                                          | 改造内容                                                                                                                                                                                                                                               |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AuthInterceptor`                             | 插入绑定分支（同 v4 位置结论）；未命中零改动                                                                                                                                                                    |
| `UserRoleMapper`                              | 存量 `hasPermission` 加 `perm_group_id=0`（组鉴权 SQL `hasPermissionByGroup` 落在 framework 侧，cicd 经 RPC 调用，见 4.2/4.4）                                                                                |
| `PermGroupQueryService`（新增）               | 组查询统一入口（已 RPC 化）：经 Feign 调 framework 内部接口——绑定组查询（独立 Guava 缓存 TTL 5 秒，未绑定结果也缓存防穿透）+ 单组/项目级组操作权限计算 + 项目绑定关系总览                                         |
| `PermGroupFeignClient`（新增）                | Feign 客户端（Spring Cloud Feign + OkHttp 连接池，配套 `PermGroupOkHttpConfig`：连接事件监听与失败日志，connect 1s / read 2s）；取代早期设计的本地只读 `PermGroupResourceBindingLocalMapper` 方案                  |
| `PipelineServiceImpl`                         | `fillPermGroupInfo` 填充逻辑所在（2026/09/17 从 controller 下沉）：3 参重载 `getPipelineDetail(projectId, pipelineId, userId)` 供 controller 用；2 参重载供事件监听器 / AuthInterceptor 等 6 处内部调用方使用（不触发绑定查询）；controller 仅协议透传 |
| `ShortcutServiceImpl`                         | `checkUserPermission` Wrapper 补 `perm_group_id=0`（2026/09/17 审计）                                                                                                                                                                                  |

## 6. 数据模型设计

### user_role_info 加列（Liquibase，framework 仓）

```sql
ALTER TABLE user_role_info ADD COLUMN perm_group_id INT NOT NULL DEFAULT 0
    COMMENT '权限组id，0=默认权限组' AFTER repo_id;
-- MySQL 8 INSTANT DDL，存量数据自动归默认组
-- 可选幂等索引：idx_uri_group (project_id, perm_group_id)（视 3.5 验证压测定）
```

### perm_group（组定义表，仅自定义组）

| 字段                      | 类型               | 说明                           |
| ------------------------- | ------------------ | ------------------------------ |
| id                        | bigint             | 主键（自增；0 为保留值不使用） |
| project_id                | int                | 所属项目                       |
| group_name                | varchar(128)       | 组名（应用层做同项目重名校验） |
| group_description         | varchar(256)，可空 | 用途说明                       |
| source_group_id           | bigint，可空       | 复制来源组 id，仅展示          |
| creator                   | varchar            | 创建人                         |
| create_time / update_time | datetime           |                                |

### perm_group_resource_binding（资源绑定表）

| 字段                      | 类型               | 说明                                 |
| ------------------------- | ------------------ | ------------------------------------ |
| id                        | bigint             | 主键                                 |
| project_id                | int                | 所属项目                             |
| resource_type             | varchar(32)        | 资源类型枚举（PIPELINE，可扩展）     |
| resource_id               | varchar(128)       | 资源标识，业务方约定格式，仅精确匹配 |
| resource_display_info     | varchar(256)，可空 | 人工查看用                           |
| perm_group_id             | bigint             | 关联 perm_group.id                   |
| operator                  | varchar            | 最近操作人                           |
| create_time / update_time | datetime           |                                      |

唯一索引 `(project_id, resource_type, resource_id)`。解绑 = 删除记录，自动回退默认组。

## 7. 性能设计（相对 v4 的变化点）

| #   | 设计点          | 结论                                                                                                                                      |
| --- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 加列影响        | INSTANT DDL 秒级；47331 行无锁风险                                                                                                        |
| 2   | 鉴权 SQL 复杂度 | **下降**：单段 EXISTS（v4 是 UNION ALL 两段+EXISTS 嵌套）；`(user_id, perm_group_id)` 过滤命中行数 ≤ 原 `project_id` 过滤（组是项目子集） |
| 3   | 绑定缓存        | 独立 Guava，TTL 5~10 秒（方向不对称论证与 Redis 版本号备选升级路径同 v4）                                                                 |
| 4   | 组查询          | 成员页组切换查询 = `project_id + perm_group_id` 双条件（建议补组合索引，视压测）                                                          |
| 5   | 未绑定资源      | 鉴权路径与现状一致（`hasPermission` 多一个 `perm_group_id=0` 等值条件，索引可覆盖，损耗可忽略）                                           |

## 8. API 接口设计

### framework 层（前缀 `/perm-group`，网关全路径 `/gateway/openlibing-framework/perm-group`）

| 接口                           | Method          | 说明                                                                                                                           |
| ------------------------------ | --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `/groups`                      | POST            | 创建组（支持来源组 id 复制；来源 0 = 复制默认组全量可复制成员；返回复制计数，前端据真实数字拼复制口径提示）                    |
| `/groups`                      | GET             | 按项目查组列表（**默认组虚拟返回**：id=0 + "默认"标记；返回含 memberCount / bindingCount，管理权限组弹窗数据源，避免前端 N+1） |
| `/groups/{permGroupId}`        | DELETE          | 删除组（默认组拦截 + 绑定占用拦截；成员记录连带删除，已定案）                                                                  |
| `/bindings`、`/bindings/batch` | POST/DELETE/GET | 绑定/解绑（单条+批量）/按资源查询/按资源批量查/按组反查                                                                        |

**一页化废弃接口**（均为本次未 push 的新增代码，直接净删除）：`GET /groups/{permGroupId}/members`（组内视图查询）、`GET /members`（独立平铺查询）——平铺查询职责由增强后的存量 `query-project-user` 承接。

**成员管理无独立接口（2026/09/16 定案）**：平行成员写接口（`POST/PUT /groups/{permGroupId}/members`、`PUT /members`、`DELETE /members`、`GET /members/other-group-records`）判定为过度设计，净删除。成员增删改复用存量项目成员链路：`BatchAddUserDTO` 加可选 `permGroupId`（查重按 `(userId, role, projectId, permGroupId)` 四元组，`insertUserRoles` 取实体 IFNULL 值）；`updateProjectUserData` 编辑查重加组维度；删除复用存量 delete 链路。权限点复用存量 `PROJECT_USER_ADD`/`UPDATE`/`DELETE`，不新增配置。

**存量接口原地增强**：`POST /project/user/query-project-user`——SQL 片段 `userQueryWithConditions` 加 `LEFT JOIN perm_group` 带出 permGroupId/permGroupName + 可选 permGroupIds 筛选；repo 分支（`project_user_role_info`）输出常量 perm_group_id=0；`UserDTO` 加可选 permGroupIds；resultMap/VO 加 permGroupId/permGroupName。消费方已核实：仅 `projectUserManage.vue`（cicd-web 的 getCommunityUser 为无调用死代码）。存量 add/update/delete-project-user **扩展而非替换**：permGroupId 入参走自定义组写入（默认组不传/传 0 维持原行为），同步/审计联动保留（2026/09/16 从"不改"升级为"扩展"，与成员管理无独立接口定案配套）。

### CICD 层（实际落地形态）

`/detailInfo` 补 `permGroupId` / `permGroupName` / `groupOperations` 三字段（避开 VO 已有流水线分组 `groupId` 命名冲突——流水线自身的分组概念，与本方案无关）；独立接口 `GET /pipeline/group-permissions?projectId=` 返回总览：`resourceBindings`（资源id → 组id 映射）+ `groupOperations`（组id → 操作码权限），流水线列表页一次请求拿全，`/list` 响应不改（SDK 对象零侵入）。错误码 `LOGIN_REQUIRED_BY_GROUP`（401）、`PERMISSION_DENIED_BY_GROUP`（403，提示携带组名）。

### 前端交互（同 v4 结论，术语换为权限组）

无感知原则、气泡双模式（"请联系项目管理员在权限组「xxx」中为你配置…"）、匿名两步分离（适用范围标注：网关放行路径）、`groupOperations` 按钮分支、绑定/解绑无延迟提示、批量绑定切换提示——均保留。新增：成员管理页**一页化增强**（权限组列 + 下拉多选筛选 + 管理权限组弹窗；行级操作按 permGroupId 路由——自定义组行走存量接口 + permGroupId 入参）、添加成员**多选组**、删除成员**跨组同步移除提示**。原型见 `prototype.html`。

## 9. 安全设计

| #   | 项                     | 设计                                                                                                                                                                                                                             |
| --- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 全局角色穿透        | SQL 内 `(role IN ('admin','super_admin','platform_operater') OR perm_group_id=#{permGroupId})`，与存量 checkProjectPermissions 口径对齐（2026/09/23 由单一 admin 扩为三角色）                                                              |
| 2   | project_manager 不穿透 | 已定案，管理员需显式入组                                                                                                                                                                                                         |
| 3   | 死锁防护               | 绑定/解绑/组管理接口走全局角色矩阵，不随组走（v4 结论保留）                                                                                                                                                                      |
| 4   | 数据一致性             | 同表后无需跨表兜底；删除成员 = 删该项目下所有 perm_group_id 记录（前端提示列出涉及组）                                                                                                                                           |
| 5   | 审计                   | 组增删改、成员编辑、绑定/解绑走 framework AOP 操作日志                                                                                                                                                                           |
| 6   | 跨服务混入防护         | **部署门禁**（见 3.2/3.5）——本方案最大安全依赖项                                                                                                                                                                                 |
| 7   | 组成员角色值域         | 原接口级角色白名单随平行成员接口删除一并消失——组行与默认组行同样依赖存量"前端下拉为唯一约束"，扩权面由鉴权侧滤组兜底（接口级鉴权只认默认组行，见 3.2 整改原则）；存量接口补值域校验维持"另提 issue"定位（见遗留风险）            |
| 8   | 默认组写保护           | 默认组成员维护只走存量项目成员接口原参数形态（不传 permGroupId）；扩展的 permGroupId 入参仅接受自定义组 id 且校验组存在——防绕过存量的同步/审计联动直接改写默认组记录；一页化后默认组行与自定义组行同页，前端路由错误亦被后端兜底 |

### 已知遗留风险

- userId 从请求参数获取可伪造（现状缺陷，网关 JWT 层部分缓解但 `/pipeline/` 放行路径仍裸露）——本次不修，独立事项跟进。
- 历史代码中 gateway 承担部分同步落库（`insertUserRoles`/`deleteSyncUserByUserId`），属存量架构债，本次仅整改加 `perm_group_id=0`，不重构归属。
- **三方同步解绑僵尸记录**：同步功能当前仅清理默认组（perm_group_id=0）行，自定义组行（sync_flag=NULL）残留——被移出项目的人若曾有自定义组记录，鉴权仍会放行。消解路径：同步功能演进为删除该项目下所有组的记录，届时问题自然消失；现阶段靠成员管理页跨组提示人工清理。**不在鉴权 SQL 加 EXISTS 前置校验**（会破坏"组间同等地位"：仅自定义组场景合法，如外部专家只开单条流水线）。
- 存量"添加项目成员"接口本身无角色值域校验（前端下拉框是唯一约束），与本方案白名单校验前的新接口同等风险——framework 存量代码，不在本次整改范围，建议另提 issue。
- 前端补充确认（2026/09/16）：存量"添加项目成员"为**输入账号/邮箱模式**（addProjectUser → commonService.getUser 按账号解析 userId，走全平台 user_basic_info），非候选人下拉选人——外部人员入组不存在 UI 缺口，此前"候选人查询挡住纯外部人员"的分析系误判（queryProjectMemberCandidates 仅用于成员列表页搜索展示，与添加动作无关）。权限组添加成员沿用输入账号交互即可支持外部专家场景。

## 附录

### 业务决策定案（v5 评审更新）

| #   | 决策项                                                    | 结论                                                                                                                                                                                                       |
| --- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 数据模型                                                  | **同表加列**（评审否决独立建表：跨服务直查已不合理，不再新增被直查的表）                                                                                                                                   |
| 2   | 命名                                                      | **权限组**（Permission Group），字段 `perm_group_id`，表 `perm_group`                                                                                                                                      |
| 3   | 组地位                                                    | 同等地位；同步仅默认组（务实差异，领导确认）                                                                                                                                                               |
| 4   | 删除语义                                                  | **勾选式连带删除**：删一行默认；删默认组行走存量删除 + 弹窗勾选其他组记录连带删（opt-in）；删自定义组行静默只删该行。**一页化增强**取代两页并存，`query-project-user` 原地增强                             |
| 5   | 查看收紧 / pm 不穿透 / EXISTS 口径 / userId 不修 / 防死锁 | 沿用 v4 定案                                                                                                                                                                                               |
| 6   | 整改范围                                                  | 组织内全部直查服务；RPC 化独立专项不捆绑本次                                                                                                                                                               |
| 7   | 成员管理接口（2026/09/16）                                | 平行成员接口（`POST/PUT /groups/{id}/members`、`PUT/DELETE /members` 等）判定过度设计净删除；成员增删改复用存量项目成员链路 + permGroupId 入参，权限点复用 `PROJECT_USER_ADD`/`UPDATE`/`DELETE`            |
| 8   | RPC 分阶段（2026/09/17）                                  | 新增查询（`hasPermissionByGroup`、`queryBoundPermGroup` 等）本次走 RPC（framework 4 个内部接口，`InternalPermGroupController`）；存量热路径维持本地直查只补滤组；其余存量 RPC 化留任务二各仓选项（见 4.4） |

### v4 → v5 消失的设计（同表红利，Claude 审视时重点看这些删得对不对）

| v4 设计                          | v5 状态                                    |
| -------------------------------- | ------------------------------------------ |
| `perm_scheme_member` 独立表      | ❌ 消失（同表）                            |
| 镜像 SQL UNION ALL + EXISTS 兜底 | ❌ 消失（单段 SQL）                        |
| `isValidProjectMember` 僵尸标记  | ❌ 消失（删全部语义）                      |
| 复制默认方案的双数据源分支       | ❌ 消失（都在一张表）                      |
| 多删除路径清理钩子               | ❌ 消失（framework 内统一）                |
| 新增                             | 双任务结构 + 部署门禁 + 全仓整改（任务二） |
| 新增                             | gateway 鉴权层纳入（三层链路）             |
