# workflow-coverage 技术方案

## 架构概览

```
xxl-job-admin (每日调度 reportWorkflowCoverageHandler)
  │
  ▼
openlibing-cicd
  ├── XxlJobHandler.reportWorkflowCoverageHandler()       // 新增：入口
  ├── WorkflowCoverageService / WorkflowCoverageServiceImpl  // 新增：核心编排（含 5min 社区缓存）
  ├── FrameworkProjectClient (Feign)                      // 新增：framework 3 个调用集中
  │      /select/only-one/get-project-by-name
  │      /manage/feature-dashboard/matrix
  │      /manage/feature-dashboard/report
  ├── CodeRepoClient (Feign)                              // 修改：原 sec-option 客户端新增 queryRepo
  │      /project-repo/internal/query-repo-list          (sec-option 原有)
  │      /project-repo/query-repo                        (workflow 新增)
  ├── GitCodeContentsClient                               // 新增：GitCode contents API（外部 API，raw HTTP）
  └── WorkflowCoverageConfig                              // 新增：静态配置（systemUserId、默认分支、gitcode api base、缓存 TTL）
  │
  ├─→ framework  GET  /select/only-one/get-project-by-name  (取 projectId，Feign)
  ├─→ framework  GET  /manage/feature-dashboard/matrix       (取社区列表，Feign，缓存 5min)
  ├─→ framework  POST /manage/feature-dashboard/report      (上报指标，Feign)
  ├─→ coderepo   POST /project-repo/query-repo              (取仓库列表，Feign)
  └─→ gitcode    GET  /api/v5/repos/{owner}/{repo}/contents/.gitcode/workflows  (raw HTTP + PRIVATE-TOKEN)
```

无新增数据库表，所有指标通过 framework 的 `feature_ops_dashboard_report` 表落地。

## 关键设计决策

1. **社区列表走 framework `/matrix` Feign**：每次任务启动时调 framework `GET /manage/feature-dashboard/matrix`，取 `data.communities` 作为本轮社区列表。带 5 分钟 TTL 内存缓存（`workflow.coverage.matrix-cache-ttl-seconds` 可配），避免单次任务内多次调用。无需在 Apollo 维护社区列表。

2. **GitCode 鉴权**：沿用 `XxlJobHandler` 中 `acceptProjectInvitationHandler` 的模式 —— `crossRegionService.getRepoAccessToken(repoUrl)` 拿加密 token，`SecurityUtil.decrypt(token, part1)` 解密。`part1` 通过 `@Value("${security.part1}")` 注入。

3. **服务间调用统一走 Feign**：参考 `CodeRepoClient` 风格，`FrameworkProjectClient`（`@FeignClient("https://openlibing-framework", contextId="openlibing-framework-workflow")`）和 `CoderepoWorkflowClient`（`@FeignClient("https://openlibing-coderepo", contextId="openlibing-coderepo-workflow")`）。仅 GitCode 作为外部 API 仍走 raw HTTP + `PRIVATE-TOKEN`。

4. **指标分两类**：
   - `配置仓库数` / `pre-commit action配置仓库数` → `aggregationType='count'`
   - `流水线配置覆盖率` / `pre-commit action覆盖率` → `aggregationType='rate'`，值域 [0,1]（framework 端会对 rate 加 % 后缀）

5. **覆盖率分母**：以"该社区在 coderepo 平台下过滤后的 gitcode 仓库数"为准，不依赖 framework 的"已上报仓库数"。

6. **GitCode 目录空 vs 接口失败**：HTTP 404 视为该仓库未配置工作流目录；HTTP 403/5xx 视为读取失败，单仓失败不中断整体任务（warn 日志 + 计入"无法判定"，不纳入分子分母）。

7. **分支默认 `master`**：workflow 目录查询 `?ref=master`；若仓库默认分支是 main（少数仓库），单仓跳过 + warn。

8. **并发控制**：按社区串行，仓库级别 `CompletableFuture` 控制在 5 并发（避免 GitCode 限流）。

9. **报告频率**：建议 xxl-job cron `0 0 1 * * ?`（每日 01:00），framework 端"当天已上报则刷新"逻辑可保证幂等。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `openlibing-cicd/src/main/java/com/openlibing/cicd/common/job/XxlJobHandler.java` | 修改 | 新增 `@XxlJob("reportWorkflowCoverageHandler")` 方法 |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/common/config/WorkflowCoverageConfig.java` | 新增 | 静态配置：coderepo systemUserId、默认分支、gitcode api base、matrix 缓存 TTL |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/feign/FrameworkProjectClient.java` | 新增 | Feign：framework 全部 3 个调用（`/select/only-one/get-project-by-name`、`/manage/feature-dashboard/matrix`、`/manage/feature-dashboard/report`） |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/feign/CodeRepoClient.java` | 修改 | 在已有 sec-option 客户端上新增 `queryRepo` 方法（同一 coderepo 服务的所有 Feign 调用集中在本接口） |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/common/utils/GitCodeContentsClient.java` | 新增 | 调 GitCode contents API（外部 API，raw HTTP） |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/WorkflowCoverageService.java` | 新增 | 接口 |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/WorkflowCoverageServiceImpl.java` | 新增 | 编排 + 社区缓存 + 指标聚合 + 上报 |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/dto/dashboard/RepoWorkflowFile.java` | 新增 | 仓库级 workflow 文件 DTO |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/dto/dashboard/CommunityWorkflowReport.java` | 新增 | 社区级指标聚合 DTO |
| `openlibing-cicd/src/test/java/com/openlibing/cicd/business/service/impl/WorkflowCoverageServiceImplTest.java` | 新增 | 单元测试 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| GitCode 限流 | 仓库级并发 5 + 重试 1 次（指数退避 1s） |
| 大社区仓库数大 | 分页 + 仅过滤 platform=gitcode、status=normal；如单社区 >200 仓库则只取前 200（与 coderepo 默认 pageSize 对齐） |
| framework/coderepo 不可用 | 单仓 / 单社区失败 warn，不中断；最终任务返回 SUCCESS |
| metric 预注册遗漏 | 文档明示需在 framework 端 `feature_ops_dashboard_metric_config` 表手工 INSERT 4 条 |
| `getRepoAccessToken` 返回 null | 该仓跳过 + warn，不纳入分子分母 |

## 跨仓影响

- `openlibing-framework`：无代码改动；需手工预注册 4 条 `feature_ops_dashboard_metric_config` 记录（feature=`流水线`，key=见下表，aggregationType 见下表）

| metric_key | aggregationType | 含义 |
|------------|----------------|------|
| `config_repo_count` | count | 配置了 .yaml 文件的仓库数 |
| `config_coverage` | rate | 流水线配置覆盖率（0-1） |
| `pre_commit_action_repo_count` | count | pre-commit action 仓库数 |
| `pre_commit_action_coverage` | rate | pre-commit action 覆盖率（0-1） |

- `openlibing-coderepo`：无代码改动；仅调用 `/project-repo/query-repo` 既有接口
- `openlibing-docs`：本 spec 文档
