# 测试用例结果支持接口更新，实时查看 — 实现任务

## 进度: 0/8 complete

> 模式：Standard  
> 业务仓：openlibing-cicd  
> 业务 Issue：openlibing/openlibing-cicd#133  
> 关联设计：[design.md](./design.md) | [proposal.md](./proposal.md)

### 数据层

- [ ] Task 1: `db.changelog.xml` 新增 changeSet
  - [ ] `test_case_result` 加 5 字段（`project_id` / `pipeline_id` / `pipeline_run_id` / `step_run_id` / `task_name`）
  - [ ] `test_case_result` 加唯一索引 `uk_pipeline_run_execute (pipeline_run_id, execute_id)`
  - [ ] `test_case_result` 加普通索引 `idx_pipeline_run_step (pipeline_run_id, step_run_id)`
  - [ ] `test_case_result` 加普通索引 `idx_log_id (log_id)`（确认已有则跳过）
  - [ ] 新建 `test_case_job_context` 表 + 唯一索引 `uk_pipeline_run_job (pipeline_run_id, job_id)`
  - 验证：本地启动项目，Liquibase 自动执行成功；`SHOW INDEX FROM test_case_result` / `DESC test_case_job_context` 与设计一致

- [ ] Task 2: `entity/pipeline/TestCaseJobContextEntity.java`（新增）
  - 字段：`id` (AUTO) / `pipelineRunId` / `jobId` / `stepRunId` / `taskName` / `projectId` / `pipelineId` / `createTime`
  - `@TableName("test_case_job_context")`
  - 验证：编译通过

- [ ] Task 3: `entity/pipeline/TestCaseResultEntity.java` 加 5 字段
  - 新增 `projectId` / `pipelineId` / `pipelineRunId` / `stepRunId` / `taskName`
  - 验证：编译通过；不破坏现有 Lombok `@Data` 自动生成

### Mapper 层

- [ ] Task 4: `mapper/TestCaseJobContextMapper.java`（新增）
  - `TestCaseJobContextEntity selectByPipelineRunIdAndJobId(pipelineRunId, jobId)`
  - `int insert(TestCaseJobContextEntity entity)`
  - 验证：编译通过

- [ ] Task 5: `mapper/TestCaseResultMapper.java` 加 2 个方法 + XML
  - `int upsertByExecuteId(TestCaseResultEntity entity)`（XML 写 `INSERT ... ON DUPLICATE KEY UPDATE`）
  - `List<TestCaseResultEntity> selectByPipelineRunId(pipelineRunId, stepRunIds)`
  - 验证：编译通过；XML namespace 与 BaseMapper 绑定正确

### DTO 层

- [ ] Task 6: `dto/pipeline/TestCaseReportRequestDTO.java`（新增）
  - 接口级字段：`@NotBlank pipelineId` / `pipelineRunId` / `jobId`；`@NotEmpty cases`
  - 内嵌 `TestCaseItem` 类：`@NotBlank executeId` / `name` / `number`；`@NotBlank @Pattern("running|passed|failed|investigated|unavailable|blocked") state`；其余选填
  - Service 层校验：单次 `cases.size() > 500` 返回 400
  - 验证：编译通过；现有 `@Validated` 风格一致

### Service 层

- [ ] Task 7: `service/PipelineService.java` + `impl/PipelineServiceImpl.java`
  - `DataResult<Void> reportTestCaseResult(TestCaseReportRequestDTO requestDTO)` 实现
    1. 参数校验 + 单次 ≤500 校验
    2. 查 `test_case_job_context` → 未命中则调 `ShowPipelineRunDetail` 反查并写缓存
    3. 遍历 `cases`，构造 `TestCaseResultEntity`（`beginTime` / `endTime` 用 `SDF.format(new Date(...))` 转换，参考 `PipelineEventConsumer.buildTestCaseResultEntity`）
    4. 逐条 `testCaseResultMapper.upsertByExecuteId(entity)`
    5. 记录审计日志（`pipelineRunId` / `jobId` / 上报时间 / 用例数）
  - `getTestReport` 修改：保留分支 A，新增分支 B 查询
    - 分支 B：`SELECT * FROM test_case_result WHERE pipeline_run_id = ? AND pipeline_run_id IS NOT NULL AND step_run_id IN (...)`
    - 两段结果直接合并（路径 A `execute_id` 全为 null，路径 B 全为 uuid4，不重叠）
    - 统计/过滤/分页逻辑统一在合并后做
  - 验证：单测覆盖 upsert、上下文补全（命中/未命中）、查询合并三处；与 `PipelineServiceImplTest` 风格一致

### Controller 层

- [ ] Task 8: `controller/BuildArtifactController.java` 加 `POST /test-case/report`
  - 方法签名参考 `reportSecOptionScan`：`@PostMapping("/test-case/report")`、`@RequestBody @Validated`
  - 不加 `@CheckPermission`
  - 日志脱敏：URL 类字段不打印
  - 验证：编译通过；与 `reportSecOptionScan` 风格一致

### 端到端验证

- [ ] Task 9: 本地自测用例（用户执行）
  - 构造一个 nightly 流水线，`POST /test-case/report` 上报 1 个 `running` 用例 → `GET /test-report` 立即可查到
  - 同 `executeId` 上报 `passed` → `GET /test-report` 状态更新为 `passed`，无重复
  - 不同 `executeId` 上报 → 不应覆盖原记录，应产生新记录
  - 同一 `pipelineRunId + jobId` 第二次上报 → 监控日志，确认无 `ShowPipelineRunDetail` 调用
  - 单次上报 501 条 → 返回 400

### 提交与归档

- [ ] Task 10: Phase 3 AI 交付结束 → 等待用户自测
- [ ] Task 11: 用户自测通过 → 用户触发 Phase 4 业务 PR
- [ ] Task 12: 业务 PR 合入后 → 用户触发 Phase 5 最终归档（本 spec 进入 archive.md 落盘）

## 已废弃/已确认无需做的任务

- ~~修改 `pipeline_obs_product` 表~~ — 已确认不动
- ~~改 MQ 异步链路~~ — 已确认保留兜底
- ~~引入 Redis 做上下文缓存~~ — 已确认用 MySQL 持久化表代替
- ~~给上报接口加 `@CheckPermission`~~ — 已确认不加，与 `reportSecOptionScan` 一致
