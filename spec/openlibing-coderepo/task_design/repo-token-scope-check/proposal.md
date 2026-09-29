# repo-token-scope-check: 仓库令牌权限校验与告警（GitCode/GitHub scope 与成员角色探测）

## 需求背景

- **保存前令牌权限校验**：新增 `POST /repo/check-token-permission` 接口（Body 与 add-repo / update-repo / batch-update-repo 一致，含 repoIds 走批量），保存前实时探测 GitCode/GitHub 令牌的 scope 与目标仓成员角色是否满足业务要求，不写库、不阻断保存，仅返回 `needAlert` + `alertInfo` 供前端弹框确认。
- **令牌权限四字段入库**：`repo_info` 表新增 `token_account_name`（令牌账号名）、`token_member_role`（目标仓成员角色）、`token_scope_status`（权限状态 normal/abnormal）、`token_role_status`（角色状态 normal/abnormal）四列；录入 / 编辑 / 批量编辑 / 令牌元数据定时刷新任务在保存路径同步探测并回填。
- **令牌无效细分告警**：令牌校验失败不再固定提示"令牌无效或已过期"，通过 `PlatformTokenErrorResolver` 将平台 API 错误（401 Bad credentials / 403 权限不足等）映射为用户可操作的细分中文文案，沿检测链路透传至告警弹框。
- **批量修改令牌前置校验**：批量编辑仓库勾选修改 access_token 时，非空 token 拒绝跨平台混选仓库，并按唯一平台调用一次 `validateAccessToken`，校验失败立即阻断批量保存；token 置空（继承项目 token）跳过校验。
- **仓库列表令牌权限筛选**：filterMeta 新增令牌成员角色（动态值）、令牌权限状态 / 角色状态（固定枚举 normal/abnormal）三个筛选维度，OR 语义、支持空值筛选；列表返回新增 `isInheritProjectToken`（按仓库 access_token 实时判断是否继承项目令牌）。
- **Excel 导出令牌信息列**：导出新增令牌账号名、状态、来源、过期时间、权限范围、权限状态、角色、角色状态 8 列，枚举值映射为中文展示。
- **平台差异适配**：GitHub Classic PAT 从 `X-OAuth-Scopes` 响应头提取 scope；Fine-grained PAT（github_pat_ 前缀）不返回 OAuth scope，跳过 scope 自动校验并在弹框中说明；GitHub 角色解析改用 `GET /repos/{owner}/{repo}`（read 角色 token 亦可调用），角色最低要求放宽为 maintain 及以上；GitCode scope 支持 `all_user/all_projects` 覆盖 `read_user/read_projects`、角色最低为维护者（含管理员）。

**不做**：Gitee 平台不介入本次校验与告警（保留现网文案与行为）；不阻断任何保存流程（校验结果仅弹框提示，用户可确认后继续保存）；GitHub Fine-grained PAT 不做 scope 自动校验（提示用户自行确认）；不修改既有 token 有效性校验（valid/expired/invalid）口径。

## 验收标准

- [ ] 保存仓库前调用 check-token-permission：GitCode/GitHub 令牌 scope 或角色不满足要求时返回 needAlert=true，弹框展示平台对应的权限要求与当前检测结论
- [ ] 弹框仅在修改 access_token（isEditAccessToken=true）时触发，未修改令牌不弹框
- [ ] 令牌无效（401/过期/不存在）时弹框展示 PlatformTokenErrorResolver 映射的细分错误文案，批量场景取首个非空提示
- [ ] GitHub Fine-grained PAT（github_pat_ 前缀）跳过 scope 校验，token_scope_status 入库置空，弹框提示自行确认权限
- [ ] GitHub read:user / read:project 可被上级 scope（user / project）满足；repo / admin:repo_hook 精确匹配；GitCode read_* 可被 all_* 覆盖，all_hook / all_pr / all_note 精确匹配
- [ ] GitHub 角色最低要求为 maintain 及以上（admin/maintain），GitCode 为维护者及以上（含管理员）；GitHub 角色经 GET /repos/{owner}/{repo} 的 role_name/permissions 双路径解析
- [ ] 仓库录入 / 编辑 / 批量编辑 / XxlJob 令牌元数据刷新后，token 四字段正确入库；令牌失效时账号名与角色清空覆盖（写空串），不残留历史值
- [ ] 批量修改 access_token：跨平台混选拒绝并阻断保存，token 无效阻断保存，token 置空放行
- [ ] 仓库列表支持按令牌成员角色 / 权限状态 / 角色状态三维度筛选（OR 语义，"" 表示筛空值），isInheritProjectToken 按实时 access_token 判断
- [ ] Excel 导出包含 8 个令牌信息列，normal/abnormal、令牌状态、令牌来源等枚举值以中文展示
- [ ] 批量修改令牌后的元数据与四字段刷新在事务提交后（afterCommit）由专用线程池执行，事务回滚不产生脏数据
- [ ] 平台 API 探测失败时跳过告警（不误报），异常不抛出、不阻断保存与刷新主流程

## 关联 Issue

- 无（随业务分支 feature/repo-token-scope-check 交付，commit 链 f588d9c0..25a38570）
