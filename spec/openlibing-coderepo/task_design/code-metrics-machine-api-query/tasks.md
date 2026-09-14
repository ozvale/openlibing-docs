# coderepo 暴露代码度量 commit 关联查询接口 - Tasks

> 状态：最终版。数据口径已全部落定（见 design.md），实现已随业务 PR openlibing/openlibing-coderepo#159 交付。
> 关联 spec：`proposal.md` / `design.md`
> 关联业务仓分支：`openlibing-coderepo: feat-code-metrics-machine-api-query`

## 任务清单

### A. coderepo 仓改动

#### A.1 数据库与实体

- [x] A.1.1 `code_metrics_record` 新增 `commit_id VARCHAR(64)` 列（Liquibase changeSet `20260824_add_commit_id_to_code_metrics_record`，幂等：columnExists 前置检查）
- [x] A.1.2 `CodeMetricsRecordEntity` 新增 `commitId` 字段（注释：触发本次扫描的 commit ID，用于按 commit 关联查询度量记录）

#### A.2 新增 DTO

- [x] A.2.1 新增 `LatestMetricsByCommitQueryDTO`（路径：`business/entity/dto/metrics/`）
  - 字段：`gitUrl` / `branchName` / `commitId`
  - 注解：3 个字段均 `@NotBlank`
- [x] A.2.2 新增 `CodeMetricsSnapshotDTO`（路径：`business/entity/dto/metrics/`）
  - 字段：`gitUrl` / `branchName` / `pipelineRunId` / `runNumber` / `commitId` / `metricsDataJson` / `detectionStartedAt` / `detectionCompletedAt`
  - 时间字段加 `@JsonFormat(pattern = DateUtil.YYYYMMDDHHMMSS, timezone = "GMT+8")`

#### A.3 Controller

- [x] A.3.1 修改 `InternalProjectRepoController`（路径：`business/controller/`，类级路径 `/project-repo/internal`）
  - `POST /metrics/code/latest-by-commit/batch`：批量查询（唯一接口，不提供单条）
  - 入参 `@Valid @RequestBody @Size(min = 1, max = METRICS_BATCH_MAX_SIZE)`（上限 100）

#### A.4 Service

- [x] A.4.1 `CodeMetricsService` 接口新增方法签名
  - `getLatestMetricsByCommitBatch(List<LatestMetricsByCommitQueryDTO> queries)`
- [x] A.4.2 `CodeMetricsServiceImpl` 实现
  - 调 `selectLatestByCommitBatch`，按 `(gitUrl, branchName, commitId)` 三元组分组取 `detection_completed_at` 最大的一条（完成时间为空的记录不参与竞争）
  - 私有方法 `toSnapshotDto` 做 Entity → DTO 转换

#### A.5 Mapper

- [x] A.5.1 `CodeMetricsRecordMapper` 接口新增方法签名
  - `selectLatestByCommitBatch(@Param("queries") List<LatestMetricsByCommitQueryDTO> queries)`
- [x] A.5.2 `CodeMetricsRecordMapper.xml` 新增批量 SQL
  - `WHERE status=0 AND (git_url, branch_name, commit_id) IN (...) ORDER BY git_url, branch_name, detection_completed_at DESC`

#### A.6 插件上报逻辑

- [x] A.6.1 `metrics_data_json` 新增 6 个字段
  - `codeLineTotal` / `commentLines` / `complexityCount` / `cyclomaticComplexityPerFile` / `duplicatedBlocks` / `duplicatedLines`
  - 字段缺失容忍（旧记录无新字段，消费方兜底）
- [x] A.6.2 插件上报 DTO / 解析逻辑补充 6 个字段 + `commitId` 上报（取 `process.env['ATOMGIT_SHA']`），coderepo `readMetaField` 解析入库到 `commit_id` 列

### B. 测试

- [x] B.1 Controller 入参校验：`@NotBlank`（3 字段）/ `@Size(min=1, max=100)`
- [x] B.2 `CodeMetricsServiceImplTest` 补充批量查询用例
  - 同一 commit 重跑取 `detection_completed_at` 最新一条
  - 批量查询无命中返回空 list
  - 混合 repo/branch/commit 查询各三元组正确返回并排序
- [x] B.3 SQL 正确性：`status != 0` 过滤 / 三元组 IN 匹配 / 分组取最新

### C. 验证

- [x] C.1 本地构建通过（`mvn compile` / `mvn test`）
- [ ] C.2 MySQL 8 IN 元组语法性能验证（联调时）
- [x] C.3 与 codecheck 仓 Feign client 联调（`StaticAlarmSummaryOperation` 消费）

## 不在范围

- 不动现有 `CodeMetricsController` 的 4 个接口
- 不动 `getLatestMetricsByGitUrl` Service 方法
- 不动 `code_metrics_file_detail` 表
- 不新建 `(git_url, branch_name, commit_id)` 全量联合索引（留待性能验证后评估）
- docs 仓 spec 归档（Phase 5 统一处理）

## 依赖关系

- 上游依赖：无（coderepo 是接口提供方）
- 下游依赖：`openlibing-codecheck` 的 `StaticAlarmSummaryOperation` + `CodeMetricsFeignClient` 调用本接口
- 跨仓 PR 顺序：coderepo 业务 PR 先行 → codecheck 业务 PR 跟进 → docs PR 统一归档
