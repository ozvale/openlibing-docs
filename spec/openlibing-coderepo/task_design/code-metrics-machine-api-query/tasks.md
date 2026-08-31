# coderepo 暴露代码度量时序关联查询接口 - Tasks

> 关联 spec：`proposal.md` / `design.md`
> 关联业务仓分支：`openlibing-coderepo: feat-code-metrics-machine-api-query`

## 任务清单

### A. coderepo 仓改动

#### A.1 新增 DTO

- [ ] A.1.1 新增 `LatestMetricsBeforeTimeQueryDTO`（路径：`business/entity/dto/metrics/`）
  - 字段：`gitUrl` / `branchName` / `beforeTime`
  - 注解：`@NotBlank` / `@NotBlank` / `@NotNull`
- [ ] A.1.2 新增 `CodeMetricsSnapshotDTO`（路径：`business/entity/dto/metrics/`）
  - 字段：`gitUrl` / `branchName` / `pipelineRunId` / `runNumber` / `metricsDataJson` / `detectionStartedAt` / `detectionCompletedAt`
  - 时间字段加 `@JsonFormat(pattern = DateUtil.YYYYMMDDHHMMSS, timezone = "GMT+8")`

#### A.2 Controller

- [ ] A.2.1 新增 `MachineApiCodeMetricsController`（路径：`business/controller/`）
  - 类级路径 `/machine-api/v1/metrics/code`
  - `POST /latest-before-time`：单条查询
  - `POST /latest-before-time/batch`：批量查询，入参 `@Size(min=1, max=100)`

#### A.3 Service

- [ ] A.3.1 `CodeMetricsService` 接口新增 2 个方法签名
  - `getLatestMetricsBeforeTime(String gitUrl, String branchName, Date beforeTime)`
  - `getLatestMetricsBeforeTimeBatch(List<LatestMetricsBeforeTimeQueryDTO> queries)`
- [ ] A.3.2 `CodeMetricsServiceImpl` 实现 2 个方法
  - 单条：调 `selectLatestBeforeTime`
  - 批量：调 `selectLatestBeforeTimeBatch`，按 `(gitUrl, branchName)` 分组取 `detection_completed_at` 最大的一条
  - 私有方法 `toSnapshotDto` 做 Entity → DTO 转换

#### A.4 Mapper

- [ ] A.4.1 `CodeMetricsRecordMapper` 接口新增 2 个方法签名
  - `selectLatestBeforeTime(gitUrl, branchName, beforeTime)`
  - `selectLatestBeforeTimeBatch(List<LatestMetricsBeforeTimeQueryDTO> queries)`
- [ ] A.4.2 `CodeMetricsRecordMapper.xml` 新增 2 条 SQL
  - 单条：`WHERE git_url=#{gitUrl} AND branch_name=#{branchName} AND status=0 AND detection_completed_at &lt; #{beforeTime} ORDER BY detection_completed_at DESC LIMIT 1`
  - 批量：`WHERE status=0 AND (git_url, branch_name, detection_completed_at) IN (...) ORDER BY git_url, branch_name, detection_completed_at DESC`
  - 注意 XML 中 `<` 用 `&lt;` 转义

#### A.5 插件上报逻辑

- [ ] A.5.1 `metrics_data_json` 新增 6 个字段
  - `codeLineTotal` / `commentLines` / `complexityCount` / `cyclomaticComplexityPerFile` / `duplicatedBlocks` / `duplicatedLines`
  - 字段缺失容忍（旧记录无新字段，消费方兜底）
- [ ] A.5.2 插件上报 DTO / 解析逻辑补充 6 个字段

#### A.6 数据库索引

- [ ] A.6.1 在 `code_metrics_record` 表上建立联合索引
  - `CREATE INDEX idx_metrics_git_branch_status_completed ON code_metrics_record(git_url, branch_name, status, detection_completed_at DESC);`
  - 评估对现有写入性能的影响

### B. 测试

- [ ] B.1 `MachineApiCodeMetricsControllerTest`：HTTP 接口契约测试
  - 单条 + 批量 + 入参校验（`@NotBlank` / `@NotNull` / `@Size(max=100)`）
- [ ] B.2 `CodeMetricsServiceImplTest`：补充新 Service 方法用例
  - 单条命中 / 单条未命中 / 批量多条命中 / 批量部分未命中 / 批量空入参
- [ ] B.3 `CodeMetricsRecordMapperTest`：补充新 Mapper 方法用例
  - SQL 正确性 / `status != 0` 过滤 / `detection_completed_at < beforeTime` 过滤

### C. 验证

- [ ] C.1 本地构建通过（`mvn compile` / `mvn test`）
- [ ] C.2 索引创建后查询性能验证
- [ ] C.3 与 codecheck 仓 Feign client 联调

## 不在范围

- 不动现有 `CodeMetricsController` 的 4 个接口
- 不动 `getLatestMetricsByGitUrl` Service 方法
- 不动 `code_metrics_file_detail` 表
- docs 仓 spec 归档（Phase 5 统一处理）

## 依赖关系

- 上游依赖：无（coderepo 是接口提供方）
- 下游依赖：`openlibing-codecheck` 的 `CodeQlSummaryOperation` + Feign client 调用本接口
- 跨仓 PR 顺序：coderepo 业务 PR 先行 → codecheck 业务 PR 跟进 → docs PR 统一归档
