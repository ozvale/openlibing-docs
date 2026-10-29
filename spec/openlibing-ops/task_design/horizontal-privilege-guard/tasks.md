# 横向越权防护实现任务清单

分支：`feat-horizontal-privilege-guard`（基于 origin/main 创建，追踪 `nane/feat-horizontal-privilege-guard`）
模式：Standard（单仓、约 30-300 行、无外部接口/数据模型变更、低安全影响边界→按安全影响升级处理测试）

## 基础组件

- [x] `ResourceTypeEnum`（PROJECT / REPO）`infrastructure/enums/`
- [x] `@ResourcePermission` + `@ResourcePermissions`（`@Repeatable`，`ResourceIdEnum` 指定入参字段）`infrastructure/aop/permission/`
- [x] `ResourceIdEnum`（PROJECT_ID / REPO_ID，含单数/复数/List 字段名族）`infrastructure/enums/`
- [x] `PermissionDeniedException`（`BizException(NO_PERMISSION)` + detail 审计字段）`infrastructure/exception/`
- [x] `GlobalExceptionHandler` 新增 `PermissionDeniedException` handler → 403

## 权限校验链路

- [x] `ResourcePermissionMapper` + XML：`hasResourceAccess`（单 EXISTS 判定）+ `selectProjectIdByRepoId`（repo→project 反查），`@DataSource(MYSQL)`
- [x] `ResourcePermissionService.check(userId, type, ids)`：REPO 反查、逐 id 校验、任一失败抛 403
- [x] `ResourcePermissionAspect`：RequestContextHolder 取 userId → 按字段名提取资源 id → 归一化展平（嵌套集合/String/Number）→ 校验 → proceed

## Controller 接入（首轮 5 个，29 个方法）

- [x] `RepoController`：8 个方法（PROJECT/REPO，含 List<DTO> 集合元素取值）
- [x] `PipelineController`：2 个方法（`queryPipelineInfo` repoUrl 维度遗留）
- [x] `OpsGithubController`：7 个方法
- [x] `OpsOverviewController`：7 个方法
- [x] `ResourceOperationController`：5 个方法（均 PROJECT_ID）

## 测试与验证

- [x] `ResourcePermissionServiceTest`：6 用例（放行/拒绝/REPO 反查 null/空集合跳过/部分失败拒绝）
- [x] `mvn compile` 通过
- [x] 既有 `RepoControllerTest` 等不受影响（standaloneSetup 不织入切面）
- [ ] 集成验证：无权限用户访问他人 projectId 数据返回 403（用户自测）

## 后续（不在本轮范围）

- [ ] 第二轮 Controller 接入（Report/NpuUsage/CodeCheck/Precision*/Project/QualityDashboard/TestCaseBoard/external）
- [ ] 全量列表可见性治理（不传资源 id 返回全部数据的遗留行为）
- [ ] metric 仓推广：写接口权限切面 + AiDashboard 可见范围控制
