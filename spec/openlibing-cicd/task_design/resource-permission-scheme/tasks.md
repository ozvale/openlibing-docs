# 任务清单（v5 · 双任务结构）

> v5 结构：任务一（数据级权限开发）+ 任务二（全仓直查整改，部署门禁）。
> 分支（已创建，基于 upstream/master）：openlibing-framework → `feat/perm-scheme`、openlibing-cicd → `feat/perm-scheme`。
> 前端由其他同事开发（文末交接清单）。gateway / codecheck / coderepo 整改属任务二，由各仓负责人认领。
> 每任务一 commit（`feat(perm-group): ...`）。

## 任务一：数据级权限开发

### 前置

- [ ] framework 管理中心权限点配置：组 CRUD、绑定/解绑接口（`menu_url_info` + `role_permission_manager`，建议授 project_manager）——**待确认：成员管理复用存量 `PROJECT_USER_ADD`/`UPDATE`/`DELETE` 后，本项仅剩组/绑定接口**

### framework 仓（commit F1~F7）

| #   | 任务                                                                                                                                                                                                                                           | 验证                                                         | 依赖   |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------ |
| F1  | ✅ Liquibase：`user_role_info` 加 `perm_group_id INT NOT NULL DEFAULT 0`（INSTANT DDL）+ `perm_group` / `perm_group_resource_binding` 建表                                                                                                     | compile + changeSet 语法                                     | 无     |
| F2  | ✅ `PermGroup` / `PermGroupResourceBinding` Entity + Mapper + XML；`UserRoleMapper` 加按 perm_group_id 过滤的成员查询/写入方法                                                                                                                 | compile + 单测                                               | F1     |
| F3  | ✅ `PermGroupService`：创建（空白/复制——`copyGroupMembers` 三条件过滤仅复制人工可添加成员）+ 同项目重名校验 + 删除（绑定占用校验，成员记录连带删）+ createGroup 返回复制计数                                                                   | 单测（复制含默认组来源、占用拒绝、重名拒绝、删除连带清成员） | F2     |
| F4  | ✅ `PermGroupResourceBindingService`：单条绑定/解绑 + 批量 + 按资源查询 + 按资源批量查 + 按组反查                                                                                                                                              | 单测（唯一索引幂等 upsert、批量）                            | F2     |
| F5  | ✅ `PermGroupController` + DTO：9 个接口（groups 列表/创建/删除、bindings 单条/批量绑定、解绑、按资源查/批量查/按组反查；GET groups 虚拟返回默认组 id=0）+ framework AOP 审计日志。**成员接口无独立实现（2026/09/16 定案删除，复用存量链路）** | BETA 冒烟                                                    | F3, F4 |
| F6  | ✅ framework 存量 SQL 全量审计整改（2026/09/17，commit `e97ecc5f`+`3a1264c6`）：8 条 SQL 固定滤组 + 15 处 Java 调用点 `setPermGroupId(0L)`，清单见 design.md 3.1.1                                                                             | 单测 + 存量功能回归                                          | F1     |
| F7  | 收尾：质量门禁五连全绿 + 全量单测                                                                                                                                                                                                              | `run-mvn.py`                                                 | 全部   |

### cicd 仓（commit C1~C6，C1/C2 可与 F3~F6 并行）

| #   | 任务                                                                                                                                                                                                                                                                                                       | 验证                                                                             | 依赖   |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------ |
| C1  | ✅ `UserRoleMapper.hasPermissionByGroup` 新方法 + XML（单段 SQL：`(role='admin' OR perm_group_id=#{permGroupId})` + 角色白名单子查询；join 字段 `rpm.role_id`/`mui.menu_id`/`mui.menu_url`）                                                                                                               | 单测（admin 穿透/组成员/白名单拦截三 case）                                      | F1     |
| C2  | ✅ `PermGroupResourceBindingLocalMapper` + `PermGroupQueryService`（独立 Guava 缓存 maximumSize=1000，TTL 5 秒，未绑定结果也缓存防穿透）                                                                                                                                                                   | 单测（命中/未命中/过期）                                                         | F1     |
| C3  | ✅ `AuthInterceptor` 绑定分支：`extractPermissionContext` 后、`isGitUrlPublic` 前插绑定查询；命中 → userId 空抛 `LOGIN_REQUIRED_BY_GROUP`(401)、非成员抛 `PERMISSION_DENIED_BY_GROUP`(403，携 `permGroupName`)；未命中零改动                                                                               | **16 个存量单测回归** + 新增分支单测（绑定命中/未命中、匿名、admin、公开仓绑定） | C1, C2 |
| C4  | ✅ cicd 存量 SQL 全量审计整改（2026/09/17，commit `d03a9e703`）：`hasPermission`/`hasPublicPermission` 加 `perm_group_id=0`（admin/visitor 穿透段不滤组）；`HwProjectInfoMapper` / `OpenUbmcFeatureMapper` 全部滤组；`ShortcutServiceImpl.checkUserPermission` Wrapper 补滤组（实体补 `permGroupId` 字段） | 单测 + 回归                                                                      | F1     |
| C5  | ✅ `/detailInfo` 补 `permGroupId`/`permGroupName`/`groupOperations`（`fillPermGroupInfo` 在 `PipelineServiceImpl`，2026/09/17 从 controller 下沉，commit `e111de724`）+ 独立接口 `GET /pipeline/group-permissions` 总览；`/list` 不改                                                                      | 单测 + BETA 冒烟                                                                 | C3     |
| C6  | 收尾：质量门禁全绿 + 16 存量单测终回归 + `triggerPermissionType` 对方案类 403 豁免核查                                                                                                                                                                                                                     | `run-mvn.py`                                                                     | 全部   |

### RPC 改造（2026/09/17 定稿，代码未动工——3 个 commit 计划）

> 设计见 design.md 4.4：新增查询走 RPC，存量热路径维持本地直查。**待办，下一步实施。**

- [ ] R1：framework `InternalPermGroupController`（4 个内部接口，前缀 `/internal-server/perm-group/`，粗粒度合并模式——热路径每请求最多 1 次 RPC）
- [ ] R2：cicd Feign 客户端 + OkHttp 连接池 + 超时（connect 1s / read 2s）+ 组鉴权缓存（键 `(userId, permGroupId, url)`，TTL 5 秒）+ fail-closed（失败全拒绝、拒绝结果不缓存）；`hasPermissionByGroup` / `queryBoundPermGroup` 等新增查询切换到 RPC
- [ ] R3：回归验证（16 存量单测 + 绑定分支单测 + RPC 故障注入——断 framework 验证 fail-closed）

## 任务二：全仓直查整改（部署门禁，你主导闭环）

| #   | 任务                                                                                                                                                                         | 产出                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| T1  | **拉取组织内全部仓库**（清单从 GitCode org 获取），四层搜索：表名 / Entity 类名 / MP 泛型签名 / Liquibase changelog                                                          | 直查处全集（当前已知 5 服务 92 处，全集待确认） |
| T2  | 逐处细读分类：使用场景（业务语言）/ R 或 W / A(默认组)/B(需感知组)/C(写入)/D(纯JOIN)                                                                                         | 对齐表（design.md 3.4 模板）                    |
| T3  | 为各仓生成现成 patch（`perm_group_id=0` 的 diff）                                                                                                                            | patch 集                                        |
| T4  | 与各服务负责人对齐会：认领 patch；RPC 化作为独立选项（0 / RPC / 0+RPC 排期），不替对方选                                                                                     | 认领状态表                                      |
| T5  | 跟进各仓合入（gateway 12 处 / codecheck 8 处 / coderepo 20 处含写入细查）                                                                                                    | 全部"已整改"                                    |
| T6  | **BETA 混入验证（部署门禁判据）**：造一条 `perm_group_id != 0` 数据 → 跑各服务存量功能（cicd 鉴权、gateway 鉴权、codecheck/coderepo 管理员判断、framework 成员页）确认不混入 | 验证报告 → **放行部署**                         |
| T7  | BETA 端到端：绑定关键流水线 → 组外成员被拒、组内放行、admin 放行、匿名（pipeline 路径）拒绝；未绑定全量回归；移出项目（删全部组）后组分支拒绝                                | 验收                                            |

## 前端交接清单（其他同事实施，术语=权限组，字段统一 permGroupId/permGroupName）

- 成员管理页（openlibing-web / projectUserManage.vue）**一页化增强**：`query-project-user` 平铺返回 `permGroupId`/`permGroupName`（每行一条组记录，默认组行 permGroupName 为 null、permGroupId=0）；列表加"权限组"列；**权限组下拉多选筛选**（参数 permGroupIds，不传=全部组）；"管理权限组"按钮弹窗（组列表含成员数/绑定数，listGroups 返回）
- **行级操作按 permGroupId 路由**：默认组行（permGroupId=0）→ 存量 update/delete-project-user 原参数形态；自定义组行 → 同一存量接口 + permGroupId 入参（2026/09/16 修订：平行成员接口已删除，不走独立新接口）
- 添加成员弹窗：**多选组**；统一走存量 add-project-user（勾选自定义组时传 permGroupId，增量语义）
- 删除成员：存量 delete-project-user 删行；删默认组行时弹窗列出该成员其他组记录**逐条勾选**连带删除（opt-in；"其他组记录"数据源随平行接口删除改为 `query-project-user` 按 userId 过滤 permGroupId≠0 的行）
- 流水线列表（cicd-web 5 文件 29 处实测）：行绑定 permGroupId 非空走 `groupOperations[permGroupId][操作码]` / 空走现状；`NoPermissionPopover` 组版气泡（"请联系项目管理员在权限组「xxx」中配置…"）；匿名（pipeline 路径）"该资源为关键管控资源，请先登录"；批量绑定提示"其中 N 条已从原组切换"；不做延迟生效提示
- 流水线列表 🛡 入口 + 组选择弹窗（含行为变化三警示）
