# resource-permission-scheme → v5 更名：权限组（perm-group）

- 关联 Issue：https://gitcode.com/openlibing/openlibing-cicd/issues/223
- FE 需求名称：流水线白名单支持按人员维度配置
- 流程模式：Full（跨仓跨团队：framework + cicd + gateway + codecheck + coderepo + 前端）
- 版本：v5（评审后重大转向，见 design.md 头部说明）

## 需求背景

流水线权限现状为"角色-菜单-URL"接口级控制，无法区分"同一角色用户对不同资源实例"的权限差异。业务诉求：绝大多数流水线全员可操作，个别关键流水线（如生产发布）收紧为指定人员可操作。

v5 方案：`user_role_info` 加 `perm_group_id` 列（存量置 0 = 默认权限组），资源绑定自定义权限组后鉴权按组过滤；能力落在 framework 层，后续 CodeCheck、CodeRepo 可复用。

## 需求范围

- **任务一（数据级权限）**：framework 权限组管理（组 CRUD/复制/绑定）+ `user_role_info` 加列（Liquibase）+ cicd 鉴权组分支（`hasPermissionByGroup` 单段 SQL）+ framework/cicd 自身存量 SQL 整改
- **任务二（全仓直查整改，部署门禁）**：组织内所有直查 `user_role_info` 的仓盘点（四层搜索）→ 分类对齐表 → patch 认领 → BETA 混入验证放行
- **前端**（交接其他同事）：成员管理页一页化增强（全组平铺 + 权限组列 + 下拉多选筛选 + 管理权限组弹窗）、添加成员多选组、删除成员勾选式连带删除、流水线列表组版交互
- **不做什么**：不修改角色-菜单矩阵；绑定表无操作粒度；跨服务 RPC 化独立专项不捆绑本次；gateway 同步落库归属不重构

## 验收标准

- [ ] 未绑定资源全链路无感知（行为/提示/错误码与现状一致）
- [ ] 绑定资源后仅组成员与全局角色（admin/super_admin/platform_operater）可操作
- [ ] 匿名访问绑定资源（网关放行的 pipeline 路径）收到登录提示；登录后非成员收到组版 403（携 groupName）
- [ ] 移除项目成员删该行组记录；删默认组行时前端弹窗勾选其他组记录连带删除（opt-in）
- [ ] 组删除时存在绑定则拒绝；复制组（含默认组来源）互不联动
- [ ] 16 个 AuthInterceptor 存量单测全过
- [ ] **部署门禁**：组织内全部直查服务整改完成 + BETA 混入验证通过（`perm_group_id != 0` 数据不污染任何存量功能）方可上线

## 业务决策定案（v5）

1. 数据模型：同表加列（评审否决独立建表）
2. 命名：权限组（Permission Group）
3. 组同等地位；三方同步仅默认组（领导确认）
4. 删除成员 = 删一行组记录；删默认组行时勾选式连带删除其他组记录（opt-in）
5. 查看收紧 / project_manager 不穿透 / userId 伪造不修披露 / 绑定解绑走全局矩阵防死锁（沿用）
6. 整改范围 = 组织全部直查服务；RPC 化独立专项

## 跨团队协作项

- 任务二全链路（盘点/对齐/合人）由 cicd 侧主导闭环，各服务负责人认领
- `user_role_info` 组合索引（`user_id, project_id, role` 或含 group_id 变体）需 framework 团队评估写入开销
