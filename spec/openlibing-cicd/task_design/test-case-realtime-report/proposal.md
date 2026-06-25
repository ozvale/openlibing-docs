# 测试用例结果支持接口更新，实时查看

## 需求背景

CICD 平台 nightly 流水线单次运行时间长达数小时，用例数动辄成百上千。现有链路中，测试用例结果通过 RabbitMQ 异步消息进入 `test_case_result` 表，必须等子任务全部跑完才开始落库，导致用户**无法在执行过程中实时查看进度**，体验较差。

需要新增一个实时上报接口，业务侧在用例开始执行时主动上报 `running` 态、完成后上报最终结果态，让 `getTestReport` 查询接口在流水线运行期间也能返回已经产生的用例结果。

## 功能描述

### 1. 新增 `POST /test-case/report` 实时上报接口

- 业务侧在每个用例开始执行时调用一次，传入 `state=running`、不填结果 URL
- 用例执行完毕再调用一次，传入同一个 `executeId`，`state` 改为最终结果，补填 URL
- 服务端以 `(pipeline_run_id, execute_id)` 为唯一键做 upsert：
  - 首次上报：INSERT
  - 后续上报：UPDATE 全字段
  - 同一 `executeId` 的 `running` 态被最终态覆盖
- 服务端根据 `pipelineRunId + jobId` 反查补全 `step_run_id / task_name / project_id`（避免业务侧传无关字段）

### 2. `GET /test-report` 查询接口内部增加"分支 B"逻辑

- 保持原入参、响应结构不变，对前端完全透明
- 分支 A（历史数据）：走 `log_id` 路径，逻辑不变
- 分支 B（实时上报数据）：走 `pipeline_run_id + step_run_id` 路径
- 两段结果在内存中合并后做统一的统计/过滤/分页

### 3. 新增 `test_case_job_context` 持久化缓存表

- 首次上报时调华为云 `ShowPipelineRunDetail` 反查 `jobId → step_run_id / task_name / project_id`
- 后续同一 `pipeline_run_id + job_id` 直接命中缓存，不再重复调外部接口
- 无需引入 Redis 等额外中间件

### 4. `test_case_result` 加字段

新增 5 个字段（均允许 NULL）：

| 字段 | 说明 |
|------|------|
| `project_id` | 项目 ID |
| `pipeline_id` | 流水线 ID |
| `pipeline_run_id` | 流水线运行 ID |
| `step_run_id` | 子任务运行 ID |
| `task_name` | 子任务名称 |

历史数据全部为 NULL，零影响。

## 不做

- 不修改 `pipeline_obs_product` 表的结构或写入逻辑
- 不修改 `pipeline_run_info` 表的结构
- 不修改华为云 API 的调用方式
- 不修改 `getTestReport` 的入参/响应结构
- 不引入 Redis 等外部中间件
- 不改异步链路（MQ 链路保留作为兜底）
- 不对上报接口加 `@CheckPermission`（脚本调用场景，与 `reportSecOptionScan` 保持一致）

## 验收标准

- [ ] 业务侧可通过 `POST /test-case/report` 上报用例 `running` 态，`getTestReport` 在流水线运行期间能查询到该用例
- [ ] 同一 `executeId` 的 `running` 态可被最终态（`passed`/`failed`/...）覆盖
- [ ] `executeId` 复用触发 upsert 覆盖，`executeId` 变更产生新记录
- [ ] 首次上报时调一次华为云 `ShowPipelineRunDetail`，后续同 `pipeline_run_id + job_id` 不再重复调
- [ ] `getTestReport` 查询结果中合并分支 A 和分支 B 数据，分页/过滤/统计与变更前一致
- [ ] 查询结果中 `running` 态的用例能正常返回
- [ ] 分支 B 数据的 `taskName` 来自 `test_case_result.task_name`，与分支 A 字段一致
- [ ] 历史数据查询行为完全不变（兼容老数据 `log_id` 路径）
- [ ] 单次上报超过 500 条用例时返回 400 错误码并提示分批
- [ ] 关键路径单元测试与已有 `PipelineServiceImplTest` 风格一致，覆盖 upsert、上下文补全、查询合并三处

## 影响范围

- **后端仓**：`openlibing-cicd`
  - `dto/pipeline/TestCaseReportRequestDTO.java`（新增）
  - `entity/pipeline/TestCaseJobContextEntity.java`（新增）
  - `entity/pipeline/TestCaseResultEntity.java`（加 5 个字段）
  - `mapper/TestCaseJobContextMapper.java`（新增）
  - `mapper/TestCaseResultMapper.java`（加 `upsertByExecuteId`、`selectByPipelineRunId`）
  - `resources/mapper/TestCaseResultMapper.xml`（新增 SQL）
  - `service/PipelineService.java`（加 `reportTestCaseResult` 方法声明）
  - `service/impl/PipelineServiceImpl.java`（实现 `reportTestCaseResult` + 改 `getTestReport` 增加分支 B）
  - `controller/BuildArtifactController.java`（加 `POST /test-case/report`）
  - `resources/db/changelog/db.changelog.xml`（新增 `addColumn` 与 `createTable` 变更集）

- **数据库**：
  - `test_case_result` 加 5 字段 + 2 索引
  - 新建 `test_case_job_context` 表

- **前端**：无（接口对前端完全透明）

- **docs 仓**：`openlibing-docs`（本仓，本 spec 归档）
