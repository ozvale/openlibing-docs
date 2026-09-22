# repo-token-scope-check（仓库令牌权限校验与告警）实现任务

> 状态：已全部完成（commit 链 f588d9c0..25a38570，feature/repo-token-scope-check 分支）

## 数据层

- [x] db.changelog.xml：新增 changeSet `20260916_add_repo_token_permission_fields`，repo_info 增加 token_account_name / token_member_role / token_scope_status / token_role_status 四列（preConditions 防重 + rollback）
- [x] RepoInfoEntity：新增四字段持久化属性 + tokenMemberRoles / tokenScopeStatuses / tokenRoleStatuses 三个 `@TableField(exist=false)` 查询字段
- [x] RepoInfoMapper.xml：令牌元数据刷新查询带出 token_status / repo_url；新增三维度筛选参数化条件（OR 语义，"" 筛空值）

## 校验评估核心（common/utils）

- [x] TokenPermissionEvaluator（@Component）：probe 实时探测（不写库）/ fillTokenPermissionFields 写四字段 / evaluateScopeStatus / evaluateRoleStatus 静态评估；TokenPermissionSnapshot record（tokenValid / platformProbeFailed / tokenInvalidMessage）
- [x] scope 判定：GitCode required 并集 + all_* 覆盖 read_*；GitHub required 并集 + user/project 上级覆盖 read:*；scope 解析兼容逗号/空格分隔；blank 与 "--" 判 abnormal
- [x] 角色判定：GitCode 维护者及以上（含管理员）；GitHub maintain+（owner/admin/maintain）
- [x] token 级元数据缓存：metadataCache（key=platform+token），批量同 token 复用 GET /user
- [x] TokenPermissionAlertBuilder：按平台组装弹框正文（权限要求 + 当前检测 + Fine-grained PAT 说明 + 批量摘要 + 继承提示）
- [x] PlatformTokenErrorResolver：401/403 错误关键字 → 细分中文文案（令牌过期/不存在/权限不足/角色不足），日志截断 500 字符，resolveOrDefault 兜底

## 平台工具类

- [x] GitCode：getTokenMetadata（含 API 失败时结合 HTTP 状态码映射细分错误信息）；resolveMemberRole（collaborators 匹配 username → role_name_cn）
- [x] Github：getTokenPermissionMetadata（Classic PAT 读 X-OAuth-Scopes；Fine-grained PAT github_pat_ 前缀识别、"--" 占位、按过期时间响应头回填状态）；resolveMemberRole（GET /repos/{owner}/{repo} role_name/permissions 双路径解析）；resolveGithubLogin + GithubLoginResult（单次 GET /user 同时完成校验与 login 解析）
- [x] ProjectConfigServiceImpl：改用 resolveGithubLogin，消除校验后二次请求

## 接口与服务层

- [x] CheckTokenPermissionVO：needAlert / alertInfo
- [x] TokenMetadataDTO：+tokenAccountName / +tokenErrorMessage
- [x] RepoController：POST /repo/check-token-permission（Body 同保存接口，含 repoIds 走批量；异常统一失败文案）
- [x] RepoService / RepoServiceImpl：checkTokenPermission（单个，编辑场景以库中实体解析 platform/repoUrl/token）/ checkBatchTokenPermission（线程池并行逐仓探测，同 token 复用元数据缓存，gitcode+github 混选跳过，任一异常 needAlert=true，错误取首个非空细分文案）
- [x] 校验触发条件：仅 isEditAccessToken=true 执行，未修改令牌不弹框；Gitee 跳过
- [x] validateBatchAccessTokenUpdate：批量改 token 前置阻断校验（空 token 放行 / 跨平台混选拒绝 / 唯一平台调一次 validateAccessToken，失败阻断保存）
- [x] 保存路径四字段回填：addRepo / updateRepo / batchEditRepoInfo（null 写空串覆盖旧值，scopeStatus null 写空串，异常兜底不阻断）
- [x] refreshBatchEditedTokenMetadata：事务 afterCommit + 专用线程池异步刷新（事务未激活直接提交），best-effort
- [x] 列表筛选：QueryRepoDTO.filterMetaDimensions 白名单扩展三维度 + tokenMemberRoles / tokenScopeStatuses / tokenRoleStatuses 多选参数；SpaceRepoDTO.isInheritProjectToken 按实时 access_token 判断

## 定时任务

- [x] XxlJobHandler：项目级 token 下发刷新与自设 token 元数据刷新两处任务，刷新时同步回填令牌四字段

## Excel 导出

- [x] RepoExportDelegateImpl：新增令牌账号名 / 状态 / 来源 / 过期时间 / 权限范围 / 权限状态 / 角色 / 角色状态 8 列；normal/abnormal、valid/expired/invalid、project/self 枚举中文映射
- [x] 移除「禁止合并自己的PR」「评审问题全部解决才能合并」导出列及 formatDisallowFlag（随 8c72b2bd 顺手清理，删除 gitcodePullRequestSettings 下发逻辑）

## 单元测试

- [x] TokenPermissionEvaluatorTest：scope 别名覆盖 / 角色判定 / Fine-grained PAT 跳过 / 探测失败快照 / isAllNormal
- [x] TokenPermissionAlertBuilderTest：平台文案 / 细分错误渲染 / Fine-grained PAT 说明
- [x] PlatformTokenErrorResolverTest：401/403 映射与兜底
- [x] GithubTest / GitCodeTest：元数据解析 / 角色双路径解析 / 错误信息映射
- [x] RepoServiceImplTest：批量前置校验三类场景 / 编辑探测 / 平台探测失败跳过 / 列表筛选与 isInheritProjectToken
- [x] RepoExportDelegateImplTest：令牌列导出与枚举映射
- [x] CheckTokenPermissionParseTest：请求体批量/单个结构区分解析
