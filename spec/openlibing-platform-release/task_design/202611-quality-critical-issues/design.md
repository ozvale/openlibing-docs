# design：质量管理——关键问题统计（缺陷/资料/需求交付率）与单包重试发布

> v2（2026-11-26）：按最终交付更新——新增需求交付率、缓存改评审单维度 2 分钟、透出病毒扫描/验签结果、新增单包重试发布。

## 代码仓来源

从评审单 `release_review` 关联的 `release_artifact_info`（repoUrl）+ 发行版仓 + json 内地址仓去重收集；由后端按 reviewId 反查，前端不传仓列表。

## 接口设计

新增 `QualityController`（`business/controller`），springdoc `@Operation`，统一返回 `DataResult<T>`：

```
POST /quality/queryCriticalIssuesSummary
  入参 Query: userId, projectId, reviewId
  出参 QualitySummaryVo {
    repoUrl, repoName, artifactName,
    defectCriticalCount, docCriticalCount,
    requirementDeliveryRate,   // 需求交付率（百分比整数；无制品 -1，分母 0 返回 0）
    virusScanStatus,           // 病毒扫描状态
    verifyResult,              // 验签结果
    countedAt, cacheExpireAt
  }

POST /quality/queryCriticalIssuesDetail
  入参 Query: userId, projectId；Body: { reviewId, repoUrl, metricType: defect|doc }
  出参 List<QualityDetailGroupVo> { artifactName, repoUrl, repoName, issues: List<QualityIssueVO> }
  QualityIssueVO { issueTitle, issueUrl, priority, labels, state, repoUrl }
```

## 权限

- `@ProjectPermission` AOP 校验 projectId。
- Service 内校验 release_review.projectId 与入参一致（防横向越权）。
- userId 从登录态上下文解析（与现有接口一致），不信任前端。
- detail 的 repoUrl 必须属于该 reviewId 的仓集合。

## 缓存设计（Redis，评审单维度 2 分钟）

- 复用 `RedisOperateUtils.set(key, value, timeout, unit)`。
- Key：`quality:critical:{projectId}:{reviewId}`（评审单维度，v2 由 repo 维度收敛而来）
- Value：`QualityCacheModel` JSON `{ defectCount, docCount, requirementTotalCount, requirementClosedCount, defectIssues[], docIssues[], countedAt, cacheExpireAt }`
- 模式：命中返回 → miss/过期实时统计 → 回写 → 返回；异常计 0。
- 明细与统计同源缓存，点击数字读缓存，不二次调 GitCode。
- 2 分钟 TTL 折中：发起评审后前端轮询数字可较快刷新，同时避免高频打 GitCode API。

## GitCode issue 查询与需求交付率

- HTTP：`HttpRequestUtil`（OkHttp）；token：`GitPlatformUtil.getGitPlatformToken`（DB 加密 token 解密）。
- `GET /api/v5/repos/{owner}/{repo}/issues?state=all&per_page=100` 分页拉全量 issue（v2 由 state=open 改为 state=all，需求交付率需要 closed 统计）。
- 本地过滤：
  - 缺陷：类型或 label ∈ {bug, 缺陷}，优先级 ∈ {致命, 严重}，state = open
  - 资料：类型 = 资料，优先级 ∈ {致命, 严重}，state = open
  - 需求：类型或 label ∈ {需求, requirement}（state 不限）
- 需求交付率 = `requirementClosedCount / requirementTotalCount × 100`（百分比整数，四舍五入）；
  - 制品信息缺失 → 全部指标返回 -1；
  - `requirementTotalCount == 0` → 交付率 0。
- GitCode v5 不支持类型/优先级服务端过滤，拉全量后本地判定；优先级取 issue 的 priority 字段，缺失时回退 label 匹配。

## 触发时机

`ReleaseBaseService.addReleaseReview`（正式提交评审路径）成功后异步触发统计（线程池/CompletableFuture），失败仅记日志不影响评审。

## 单包重试发布（v2 新增）

- `ReleaseDecisionController` 新增 `retryArtifactRelease` 入口；`ReleaseDecisionService.retryArtifactRelease(reviewId, artifactId)`。
- 状态机：仅整单状态 = RELEASE_FAILED 时允许重试；抢占式条件更新（乐观锁）防止与整单发布/其他重试并发重复执行。
- 重试前删除该制品该发布方式的历史 RELEASE_FAILED 发布结果记录；RELEASE_SUCCESS 记录幂等跳过不重复发布。
- 完成回调与整单发布共用 `refreshReleaseReviewStatus`：按制品维度聚合全部发布结果，全部成功 → RELEASE_SUCCESS，否则 → RELEASE_FAILED。
- 已知遗留（后续 issue 跟进）：发布决策状态机竞态窗口加固（发布中可重复触发、撤回与异步回调竞态，CWE-362），见 issue #140/#141。

## 影响范围

- 新增：QualityController、QualityService(+Impl)、QualityDetailQueryDTO、vo/quality（QualitySummaryVo/QualityIssueVo/QualityDetailGroupVo/QualityCacheModel）、QualityServiceImplTest。
- 修改：ReleaseBaseServiceImpl（提交评审后异步触发）、ReleaseDecisionService(+Impl)（单包重试）、ReleaseDecisionController、ReleaseArtifactExcelServiceImpl（模板字段）、release_artifact_info_template.xlsx、pom.xml（SDK 1.0.21.6）。
- 无 schema 变更；Redis key 口径变化（repo 维度 → 评审单维度，旧 key 随 TTL 自然失效）。

## 测试策略

- 单测：issue 过滤口径（类型/label/优先级/状态）、需求交付率（分母 0、无制品 -1、已关闭占比）、缓存 miss/命中/过期、reviewId 归属校验、repoUrl 白名单校验、单包重试（失败记录清理/成功幂等/状态抢占）。
- 现有测试回归：mvn test 相关模块；QualityServiceImplTest 增量行覆盖率 81%。
