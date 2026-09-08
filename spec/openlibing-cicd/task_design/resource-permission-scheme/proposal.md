# resource-permission-scheme（资源级权限方案）

- 关联 Issue：https://gitcode.com/openlibing/openlibing-cicd/issues/223
- FE 需求名称：流水线白名单支持按人员维度配置
- 流程模式：Full（跨仓：openlibing-framework + openlibing-cicd，涉及鉴权/数据模型）

## 需求背景

当前流水线权限控制在"角色 → 菜单 → URL 接口"权限矩阵之上，粒度停留在接口/角色级别，无法区分"同一角色的用户对不同资源实例"的操作权限差异。业务诉求：项目下绝大多数流水线仍可由全体流水线工程师操作，但个别关键流水线（如生产发布流水线）需收紧为仅指定少数人可操作。

方案引入"权限方案"（Permission Scheme）机制：framework 层新增通用资源级权限管控能力（方案 CRUD、方案成员管理、资源绑定关系），cicd 鉴权链路在资源绑定命中时切换角色数据来源；能力与业务模块解耦，后续 CodeCheck、CodeRepo 可复用。完整设计见 design.md，代码级实现参考见 implementation-reference.md。

## 需求范围

- **framework 层（新增）**：`perm_scheme` / `perm_scheme_member` / `perm_scheme_resource_binding` 三张表（Liquibase 管理）、方案管理/资源绑定 REST 接口、方案复制与删除保护、审计日志
- **cicd 层（改造）**：`AuthInterceptor` 绑定分支（位于公开仓短路与匿名放行之前）、`hasPermissionByScheme` 镜像 SQL、绑定查询本地 Mapper + 独立 Guava 缓存、流水线列表返回方案标识
- **前端**：成员管理页签扩展（默认方案 + 自定义方案）、流水线列表方案配置入口
- **不做什么**：不修改现状 `hasPermission` SQL 与存量行为；不新增角色维度；绑定表不含操作粒度字段；不修复 userId 可伪造的现状缺陷（仅披露）

## 验收标准

- [ ] 未绑定资源的鉴权路径与现状完全一致（公开仓短路、匿名判断、hasPermission 原样保留）
- [ ] **无感知原则**：未绑定方案的资源，用户全链路无感知——交互、提示、错误码、性能均与现状一致；仅绑定了自定义方案的资源用户才感知差异
- [ ] 绑定资源后，仅方案成员（且仍是有效项目成员）与 admin 角色可通过鉴权
- [ ] 匿名访问绑定资源收到"需登录"提示（LOGIN_REQUIRED_BY_SCHEME）；登录后非方案成员收到方案版拒绝（PERMISSION_DENIED_BY_SCHEME，携带方案名与建议角色指引）
- [ ] 绑定资源为公开仓关联时，不再被公开仓短路放行；匿名访问被直接拒绝
- [ ] admin 穿透不受方案影响（SQL 内嵌 UNION 段，不限定项目但需落在 URL 角色白名单内）
- [ ] 成员经任一删除路径（手工移除/三方同步/项目级联）移出项目后，无法通过方案分支鉴权（EXISTS 校验兜底）
- [ ] 方案删除时若存在资源绑定则拒绝删除
- [ ] 方案复制（含基于默认方案复制）后与来源方案互不联动
- [ ] 现状 16 个 AuthInterceptor 单测全部通过，新增绑定分支单测覆盖上述场景

## 业务决策项（已与需求方确认定案）

1. **查看类接口一并收紧（选 A）**：资源整体管控；需要只读访问的用户，由管理员将其加入方案并配置可查看角色（如 project_member——查看类矩阵对项目成员开放、执行类不开放，天然实现"能看不能跑"）。
2. **project_manager 不穿透（选 A，与现状语义一致）**：现状 hasPermission 中 project_manager 本就是项目匹配放行而非穿透角色，admin 是唯一 SQL 内穿透；镜像 SQL 保持同语义。绑定后管理员需显式加入方案。
3. **EXISTS 成员有效性口径选宽松（选 A）**：project_id 匹配即视为有效项目成员，与成员管理页面查询口径一致。
4. **userId 可伪造缺陷本次不修（选 A）**：仅披露、独立事项跟进；该风险与现状相同，方案未使其恶化。
5. **绑定/解绑权限走现有角色矩阵（选 A）**：绑定/解绑/方案管理接口在 framework 管理中心作为普通权限点配置（上代码前需配置好，写于 tasks.md 前置项）；悬浮置灰走现有 NoPermissionPopover 角色版气泡。**关键约束：管控配置操作本身不随方案走**——否则可能出现"管理员绑定了方案、新方案内无配置权、无人能解绑"的死锁；资源级方案只管控业务操作（@CheckPermission 接口），配置操作永远走全局角色矩阵。

## 跨团队协作项

- `user_role_info` 补充 `(user_id, project_id, role)` 组合索引：该表仅有主键索引，现状 hasPermission 已全表扫描；需 framework 团队通过 Liquibase 幂等 changeSet 评估落地
