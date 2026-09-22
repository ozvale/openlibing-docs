# repo-token-scope-check（仓库令牌权限校验与告警）技术方案

## 架构概览

```
前端（保存前）POST /repo/check-token-permission（Body 与 add/update/batch-update 一致）
  ▼
RepoController.checkTokenPermission（fastjson2/Jackson 解析，按 repoIds 区分批量/单个）
  ▼
RepoServiceImpl
  ├─ checkTokenPermission（单个）/ checkBatchTokenPermission（批量，线程池并行逐仓探测）
  │     ▼
  │  TokenPermissionEvaluator.probe（实时探测，不写库）
  │     ├─ fetchMetadata：GET /user 取 token 级元数据（login/scope/tokenStatus，批量同 token 复用缓存）
  │     │    ├─ GitCode.getTokenMetadata（GitCode）
  │     │    └─ Github.getTokenPermissionMetadata（GitHub；Classic PAT 读 X-OAuth-Scopes，
  │     │       Fine-grained PAT github_pat_ 固定 "--" 占位）
  │     ├─ resolveMemberRole：目标仓成员角色（逐仓调用）
  │     │    ├─ GitCode：getGitcodeRepoCollaborators 匹配 username → role_name_cn
  │     │    └─ Github：GET /repos/{owner}/{repo} role_name/permissions 双路径解析（read 角色 token 可调用）
  │     ├─ evaluateScopeStatus：scope 并集比对（含别名/上级覆盖）
  │     └─ evaluateRoleStatus：维护者级（GitCode）/ maintain+（GitHub）判定
  │     ▼
  │  TokenPermissionAlertBuilder.build → needAlert + alertInfo（前端弹框，不阻断保存）
  │
  ├─ 保存路径（addRepo / updateRepo / batchEditRepoInfo）
  │     └─ fillTokenPermissionFields：探测结果写实体四字段 → repo_info
  ├─ validateBatchAccessTokenUpdate：批量改 token 前置校验（阻断性）
  └─ refreshBatchEditedTokenMetadata：事务 afterCommit + 专用线程池异步刷新

告警文案支撑：
  PlatformTokenErrorResolver：平台 API 错误（401/403）→ 细分中文提示，透传至弹框
  TokenPermissionAlertBuilder：按平台组装权限要求 + 当前检测结论

数据回流：
  XxlJobHandler 令牌元数据刷新任务（项目级/自设 token）─ 刷新时同步回填四字段
  RepoExportDelegateImpl：Excel 导出 8 个令牌列
  RepoServiceImpl.getRepoList：filterMeta 三维度筛选 + isInheritProjectToken
```

## 核心流程

### 1. 保存前校验（check-token-permission）

1. Controller 收到与保存接口一致的 Body：含 `repoIds` 反序列化为 `BatchEditRepoInfoDTO` 走批量，否则 `RepoDTO` 走单个；解析异常返回统一失败提示，不抛出
2. 单个场景：编辑时（repoId 非空）以库中仓库实体为准解析 platform / repoUrl / token（与保存路径对齐）；新增场景按请求体校验项目权限后直接探测
3. 仅 `isEditAccessToken=true` 时执行校验，未修改令牌不弹框
4. Gitee 平台直接跳过（返回 needAlert=false）
5. 批量场景：线程池并行逐仓探测，同 token 复用 `GET /user` 元数据缓存（metadataCache，key=platform+token）；gitcode 与 github 混选时跳过校验
6. 探测结果 `TokenPermissionSnapshot.isAllNormal()`（tokenValid 且 scope/role 均 normal）为 false 时 needAlert=true，批量任一仓异常即告警，错误提示取首个非空细分文案

### 2. 令牌权限探测（TokenPermissionEvaluator.probe）

| 步骤 | 说明 |
| ---- | ---- |
| 元数据获取 | `GET /user`：login（令牌账号名）、scope、tokenStatus；GitHub Classic PAT 从 `X-OAuth-Scopes` 响应头提取，Fine-grained PAT（`github_pat_` 前缀）固定 `"--"` 占位并按过期时间响应头回填状态 |
| 令牌无效判定 | login 为空或 tokenStatus=invalid → invalidTokenSnapshot（scope/role 均 abnormal，携带细分错误信息） |
| scope 状态 | 见「scope 判定矩阵」；Fine-grained PAT 跳过 scope 校验，snapshot 中 scopeStatus=null，入库置空串 |
| 角色解析 | 逐仓调用：GitCode 按 collaborators 列表匹配 username 取 `role_name_cn`；GitHub 用 `GET /repos/{owner}/{repo}` 解析当前认证用户有效权限（role_name 优先，缺失时按 permissions 布尔位收敛为 admin/maintain/write/triage/read），read 角色 token 亦可调用 |
| 探测异常 | catch 后返回 platformFailureSnapshot（platformProbeFailed=true），上层跳过告警，不降级读库 |

### 3. scope 判定矩阵

| 平台 | required 并集 | 别名/覆盖规则 | 精确匹配项 |
| ---- | ---- | ---- | ---- |
| GitCode | read_user、read_projects、all_hook、all_pr、all_note | read_user ← {read_user, all_user}；read_projects ← {read_projects, all_projects} | all_hook / all_pr / all_note |
| GitHub | read:user、repo、admin:repo_hook、read:project | read:user ← {read:user, user}；read:project ← {read:project, project} | repo / admin:repo_hook |

- scope 字符串解析兼容逗号或空格分隔（GitCode OAuth 两种格式均出现）
- blank 或 `"--"` 判为 abnormal

### 4. 角色判定

| 平台 | 最低要求 | 判定逻辑 |
| ---- | ---- | ---- |
| GitCode | 维护者及以上 | 角色名包含 管理员 / 维护者 / owner / Owner / 仓库owner |
| GitHub | maintain 及以上 | role ∈ {owner, admin, maintain}（大小写不敏感） |

- 角色为空判为 abnormal
- 演进：GitHub 最低要求由 owner/admin 放宽至 maintain+（25a38570），因为角色解析改用仓库详情接口后 write/read 令牌也能正确读取自身权限

### 5. 四字段入库与刷新

- `fillTokenPermissionFields`：探测成功写四字段；null 写空串（确保 updateRepo 覆盖旧值，令牌失效后不残留历史账号名/角色）；探测失败写兜底值（invalidTokenSnapshot 口径），异常吞掉不阻断保存
- 入库路径：addRepo / updateRepo / batchEditRepoInfo / XxlJob 令牌元数据刷新（项目级 token 下发与自设 token 刷新两处）
- 批量编辑（updateWrapper 仅更新 access_token 时）：保存事务提交后（TransactionSynchronization.afterCommit）由专用线程池执行 `refreshBatchEditedTokenMetadata` 逐仓刷新元数据与四字段；事务未激活时直接提交线程池；best-effort，失败仅日志

### 6. 批量修改令牌前置校验（阻断性，区别于弹框）

- `validateBatchAccessTokenUpdate`：仅 `isEditAccessToken=true` 时执行
- token 置空（继承项目 token）→ 放行（保持原有行为）
- 非空 token：勾选仓库平台去重后 >1 → 拒绝"批量修改令牌时不支持跨平台混选仓库"；唯一平台调用一次 `validateAccessToken`，失败即阻断批量保存

### 7. 仓库列表三维度筛选

- `QueryRepoDTO.filterMetaDimensions` 白名单扩展：tokenMemberRole（动态值）、tokenScopeStatus / tokenRoleStatus（固定枚举 normal/abnormal）
- 多选 OR 语义；`""` 表示筛选空值（未继承 token 或未探测）
- mapper 按参数化条件过滤（RepoInfoMapper.xml），成员角色支持空值筛选
- 列表返回新增 `isInheritProjectToken`：按仓库 access_token 实时判断（空=继承项目）

### 8. Excel 导出

- 新增 8 列（列序 13–20）：令牌账号名、令牌状态、令牌来源、令牌过期时间、令牌权限范围、令牌权限状态、令牌角色、令牌角色状态
- 枚举中文映射：normal/abnormal → 正常/异常；valid/expired/invalid → 有效/已过期/失效；project/self → 继承项目/自身设置

## DDL 变更（db.changelog.xml）

| 列 | 类型 | 说明 |
| ---- | ---- | ---- |
| token_account_name | VARCHAR(512) | 令牌账号名（平台 login） |
| token_member_role | VARCHAR(512) | 令牌角色：目标仓成员角色 |
| token_scope_status | VARCHAR(16) | 令牌权限状态：normal/abnormal |
| token_role_status | VARCHAR(16) | 令牌角色状态：normal/abnormal |

- changeSet `20260916_add_repo_token_permission_fields`，preConditions 防重（列存在则 MARK_RAN），含 rollback
- 仅 GitCode/GitHub 写入；Gitee 四字段保持 NULL

## 错误映射（PlatformTokenErrorResolver）

| HTTP | GitCode | GitHub | 映射文案 |
| ---- | ---- | ---- | ---- |
| 401 | Bad credentials | Bad credentials | 令牌已过期或无效，请重新填写 |
| 401 | token not found | Requires authentication | 令牌不存在或已失效，请重新填写 |
| 403 | has not permission | Resource not accessible by personal access token | 令牌权限不足，请检查令牌权限配置 |
| 403 | Unauthorized access | Must have admin access | 令牌角色不足，请检查令牌角色配置 |
| 其他 | — | — | 不匹配返回 empty，调用方回退默认文案（最终兜底：调用平台接口失败，请检查令牌或账号权限） |

- 错误文本提取：GitCode 取 `error_message` 字段，GitHub 取 `message` 字段，解析失败用原始 body
- 映射命中打 warn 日志（错误文本截断至 500 字符）；Gitee 不介入

## 告警文案（TokenPermissionAlertBuilder）

- 固定开头：说明不满足要求时 Webhook、MR 回写等能力可能失败
- 平台权限要求：GitCode（read_user、read_projects、all_hook、all_pr、all_note + 至少维护者）；GitHub（read:user、repo、admin:repo_hook、read:project + 至少 Maintainer，并说明 Fine-grained PAT 不做自动校验）
- 【当前检测】段：tokenValid=false 时优先渲染细分错误文案（缺省回退"令牌无效或已过期，请重新填写"）；否则按 scopeStatus / roleStatus 拼接"令牌权限不足 / 令牌角色不足，请检查令牌配置"
- 批量场景可附带 batchSummary 摘要行；结尾提示继承项目 token 时同样需满足要求

## 错误处理与降级

| 场景 | 处理 |
| ---- | ---- |
| 平台 API 探测失败（网络/5xx） | platformProbeFailed=true，跳过告警不误报，不降级读库（25a38570 移除早期 DB 降级口径） |
| 令牌无效（401/过期/不存在） | invalidTokenSnapshot，四字段兜底入库，弹框展示细分文案 |
| 批量混选平台（check 接口） | gitcode + github 混选跳过校验（探测口径因平台而异） |
| 校验接口自身异常 | catch 后返回统一失败文案，不抛出、不影响保存 |
| 四字段填充异常 | catch + warn，写兜底值，不阻断保存与刷新 |
| 事务回滚 | 元数据刷新挂 afterCommit，回滚不触发，避免脏数据 |

## 关键设计决策

1. **校验不阻断、告警可确认**：check-token-permission 只探测不写库，needAlert 由前端弹框呈现，用户确认后仍可保存——权限问题是"可用性风险"而非"合法性错误"，与批量改 token 的阻断性前置校验（validateBatchAccessTokenUpdate）分层处理。
2. **token 级元数据缓存 + 仓级角色逐仓探测**：`GET /user` 与目标仓无关，批量同 token 场景用 metadataCache 复用；成员角色与 repoUrl 绑定必须逐仓调用，批量探测走线程池并行。
3. **GitHub 角色解析弃用 collaborators 权限接口**：collaborators/permission 需要 write+ 权限（低角色令牌 403），改用 `GET /repos/{owner}/{repo}` 读取当前认证用户有效权限，read 令牌亦可调用；同时角色最低要求放宽至 maintain+ 与实际业务需要（webhook、MR 回写）对齐。
4. **Fine-grained PAT 跳过 scope 校验**：该类令牌不返回 OAuth scope，强行校验必误报；以 `github_pat_` 前缀识别，token_scope_status 入库置空并在弹框说明，交由用户自行确认。
5. **scope 别名/上级覆盖而非精确匹配**：GitHub `user` 覆盖 `read:user`、`project` 覆盖 `read:project`，GitCode `all_*` 覆盖 `read_*`，避免持上级权限的合法令牌被误判 abnormal；repo / admin:repo_hook / all_hook 等写权限仍精确匹配。
6. **探测失败跳过告警（不降级读库）**：c793b887 曾引入"探测失败降级读库中四字段"，但库值可能过期导致误导性告警，25a38570 移除降级改为直接跳过——宁可漏报不误报。
7. **四字段写空串而非 NULL**：MyBatis callSettersOnNulls=false 且 updateRepo 需覆盖旧值，令牌失效后账号名/角色清空写空串，避免历史值残留；scopeStatus 为 null（Fine-grained PAT）写空串与"--"占位区分。
8. **批量刷新挂 afterCommit + 专用线程池**：批量保存事务内不做串行平台 API 调用（避免长时间持有行锁），提交后异步刷新；回滚不产生脏数据。

## 影响范围

- **openlibing-coderepo（src/main）**：
  - 新增工具类：TokenPermissionEvaluator（@Component，含 TokenPermissionSnapshot record）、TokenPermissionAlertBuilder、PlatformTokenErrorResolver
  - 新增 VO/DTO 扩展：CheckTokenPermissionVO（needAlert/alertInfo）、TokenMetadataDTO（+tokenAccountName/+tokenErrorMessage）
  - 修改 Controller：RepoController（+check-token-permission 端点）
  - 修改 Service：RepoService / RepoServiceImpl（校验、批量前置校验、四字段填充、异步刷新、列表筛选）、ProjectConfigServiceImpl（GitHub 单请求合并）、RepoExportDelegateImpl（+8 令牌列）
  - 修改工具类：GitCode（+getTokenMetadata/+resolveMemberRole）、Github（+getTokenPermissionMetadata/+resolveMemberRole/+resolveGithubLogin/+isFineGrainedPat）
  - 修改任务：XxlJobHandler（令牌元数据刷新回填四字段）
  - DDL：db.changelog.xml 新增 repo_info 四列 changeSet；RepoInfoMapper.xml 刷新查询带 token_status/repo_url、筛选条件
  - 文档：doc/api/repo-management.md 同步接口说明
- **Gitee**：无行为变更（校验跳过、文案保留现网口径）
- **配置**：无新增配置项
- **测试（src/test）**：TokenPermissionEvaluatorTest / TokenPermissionAlertBuilderTest / PlatformTokenErrorResolverTest / GithubTest / GitCodeTest（增量）/ RepoServiceImplTest（增量）/ RepoExportDelegateImplTest（增量）/ CheckTokenPermissionParseTest
