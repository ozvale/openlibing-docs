# 任务清单

前置（业务决策项已全部定案，见 proposal.md）：
- 绑定/解绑/方案管理接口上代码前，需在 framework 管理中心完成权限点配置（`role_permission_manager` + `menu_url_info`），建议授予 project_manager
- 与 framework 团队确认 `user_role_info` 组合索引 changeSet

## framework 层

- [ ] Liquibase changeSet：新增 `perm_scheme` / `perm_scheme_member` / `perm_scheme_resource_binding` 三张表（字段类型见 design.md 第 4 章；`user_id` 为 varchar(32)、`project_id` 为 int，对齐现状表结构）
- [ ] `PermSchemeMapper` / `PermSchemeMemberMapper` / `PermSchemeResourceBindingMapper` 接口与 XML
- [ ] `PermSchemeService`：创建方案（含基于已有方案复制、成员深拷贝）、删除方案（绑定占用校验）、方案列表查询
- [ ] `PermSchemeResourceBindingService`：绑定/解绑/按资源查询（唯一索引幂等）
- [ ] `PermSchemeController`：7 个管理接口（见 design.md 第 6 章），写入操作记录审计日志（操作人、时间、变更前后内容）
- [ ] 方案成员新增时校验项目成员身份（user_role_info 中 project_id 匹配）
- [ ] `ProjectUserServiceImpl.deleteProjectUser` 移除成员时同步清理该项目下 `perm_scheme_member` 记录（数据卫生，非安全防线）
- [ ] 与 framework 团队确认 `user_role_info` 组合索引 changeSet（如采纳）
- [ ] 单测：方案 CRUD、复制、删除保护、绑定解绑、成员校验

## cicd 层

- [ ] `PermSchemeResourceBindingLocalMapper`（本地只读）+ 独立 Guava 缓存实例（maximumSize=1000，1min TTL，不与匿名访问结果缓存共用）
- [ ] `UserRoleMapper.hasPermissionByScheme` 镜像 SQL（UNION ALL：admin 穿透段 + 方案成员段含 EXISTS 校验；join 字段名以 implementation-reference.md 核实结论为准：`rpm.role_id` / `mui.menu_id` / `mui.menu_url`）
- [ ] `AuthInterceptor.preHandle`：`extractPermissionContext` 之后、`isGitUrlPublic` 之前插入绑定查询；命中绑定跳过公开仓短路与匿名分支（userId 为空直接拒绝）；未命中保持现状逻辑零改动
- [ ] 方案分支拒绝时返回独立错误码 `PERMISSION_DENIED_BY_SCHEME`（区别于现状 `PERMISSION_DENIED`），供前端切换气泡类型
- [ ] `POST /project/pipeline/list` 返回结构行级补充 `schemeId` / `schemeName` / `schemeOperations`（为空表示默认方案；`schemeOperations` 为按操作码的权限 map，如 `{"pipeline_run": false, "pipeline_info_sync": true}`，绑定行由后端按 `hasPermissionByScheme` 逐操作码判断，未绑定行不返回该字段、前端走现状角色判断）
- [ ] `GET /project/pipeline/detailInfo` 返回结构补充同样三字段（详情页有重试/停止/编辑/执行 4 个操作按钮，需要 `schemeOperations`）
- [ ] `schemeOperations` 的 key 复用现有权限码（`pipeline_run` / `pipeline_stop` / `update-pipeline-config` 等，即前端 `hasOperationPermission` 已在用的 `menu_info.identification`），不新造编码
- [ ] framework 侧确认：`menu_url_info.triggerPermissionType` 的 403 权限申请弹框对方案类拒绝（`PERMISSION_DENIED_BY_SCHEME`）豁免，避免误导用户走角色申请
- [ ] 单测：16 个存量单测回归 + 新增绑定分支（绑定命中/未命中、匿名拒绝、admin 穿透、公开仓绑定、EXISTS 兜底）
- [ ] Phase 3 自检：接口变动检测（列表返回结构新增字段，评估是否触发前端接口文档生成）

## 前端（openlibing-cicd-web / openlibing-web）

前端改造页面实测清单（基于 cicd-web 全量扫描 `hasOperationPermission` 使用点，共 5 个文件 29 处）：

- [ ] `pipeline.vue`（流水线列表）：按 `schemeId` 是否为空切换按钮渲染逻辑——绑定行用 `schemeOperations[操作码]` 控制 run/stop/sync 按钮，未绑定行维持现状 `hasOperationPermission` 角色判断（17 处判断，主改造点）
- [ ] `pipelineRunDialog.vue`（运行确认弹窗）：运行按钮同模式接入（`pipeline_run`，列表页触发的二级确认）
- [ ] `PipelineDetail/Detail.vue`（详情页）：重试/停止/编辑/执行按钮接入（6 处判断）；顺带决策：重试按钮现状无任何前端权限判断（reExecute 直连，与停止按钮不一致），本次对齐还是维持现状披露，Phase 2 定
- [ ] `PipelineManage.vue`（白名单管理页）：白名单开关按行接入（`pipeline_whitelist:update`，每行一个 pipelineId，同属资源级操作，与列表页同模式）
- [ ] `PipelineEdit/pipelineEditDialog.vue`（编辑弹窗）：不单独接入——编辑入口按钮在列表/详情页被拦截后弹窗进不去，入口接好即可
- [ ] `NoPermissionPopover` 扩展方案版气泡分支：绑定资源被拒（`PERMISSION_DENIED_BY_SCHEME`）时展示"请联系项目管理员在方案「xxx」中为你配置具备该操作权限的角色"（方案名取自错误响应体，建议角色列表复用现状 `rolesByLevel` 数据源与渲染逻辑，不新做），不展示常规角色申请指引；未绑定资源保持现状角色版气泡
- [ ] 匿名访问绑定资源：悬浮提示"该资源为关键管控资源，请先登录以验证您的身份与访问权限"并附登录入口（`LOGIN_REQUIRED_BY_SCHEME`），登录后按方案成员判断走方案版气泡；未绑定资源维持现状（公开仓匿名可看）；列表接口匿名可访问且仍返回各行 `schemeId`，`schemeOperations` 对匿名用户所有操作码恒为 false
- [ ] 成员管理页面扩展页签：默认方案（现状数据，调用现状接口）+ 自定义方案（调用 framework 方案管理接口）
- [ ] 方案创建支持基于已有方案复制（默认方案或自定义方案）
- [ ] 流水线列表新增方案配置操作项，展示当前生效方案标识

## 验证

- [ ] BETA 环境端到端：绑定关键流水线 → 方案外成员操作被拒、方案内成员放行、admin 放行、匿名拒绝
- [ ] 未绑定流水线全量回归（含公开仓匿名访问场景）
- [ ] 成员移出项目（手工移除路径）后方案分支拒绝
