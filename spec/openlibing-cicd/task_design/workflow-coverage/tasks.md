# workflow-coverage 实现任务

## openlibing-cicd 仓

- [ ] 在 `WorkflowCoverageConfig` 中读取 Apollo `dashboard.matrix.communities` + 各服务 URL
- [ ] 创建 `FrameworkProjectClient`（封装 framework /select/get-project-by-name）
- [ ] 创建 `CoderepoQueryClient`（封装 coderepo /project-repo/query-repo 分页拉取）
- [ ] 创建 `GitCodeContentsClient`（封装 GitCode contents API + PRIVATE-TOKEN）
- [ ] 创建 `RepoWorkflowFile` / `CommunityWorkflowReport` DTO
- [ ] 创建 `WorkflowCoverageService` 接口与 `WorkflowCoverageServiceImpl` 实现
- [ ] 在 `XxlJobHandler` 中新增 `@XxlJob("reportWorkflowCoverageHandler")` 方法
- [ ] 单元测试 `WorkflowCoverageServiceImplTest`：覆盖指标计算 / 异常隔离 / pre-commit 命中
- [ ] 在 `application-gama.yaml` / `application-beta.yaml` 中（如需）补充新增的 Apollo 配置项默认值

## openlibing-framework 仓（手工，不入 PR）

- [ ] 在 `feature_ops_dashboard_metric_config` 表手工 INSERT 4 条：
  - `feature='流水线'`, `metric_key='config_repo_count'`, `aggregation_type='count'`
  - `feature='流水线'`, `metric_key='config_coverage'`, `aggregation_type='rate'`
  - `feature='流水线'`, `metric_key='pre_commit_action_repo_count'`, `aggregation_type='count'`
  - `feature='流水线'`, `metric_key='pre_commit_action_coverage'`, `aggregation_type='rate'`

## openlibing-docs 仓

- [ ] `proposal.md`（本仓已落盘）
- [ ] `design.md`（本仓已落盘）
- [ ] `tasks.md`（本文件）
