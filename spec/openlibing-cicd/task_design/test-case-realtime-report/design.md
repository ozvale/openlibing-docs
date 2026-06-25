# 测试用例结果支持接口更新，实时查看 — 技术设计

## 方案概述

新增 `POST /test-case/report` 实时上报接口，业务侧主动推送用例状态；`getTestReport` 查询接口内部增加"分支 B"逻辑读取新数据，与原"分支 A"（`log_id` 路径）结果合并后统一返回。新增 `test_case_job_context` 缓存表，避免重复调华为云 `ShowPipelineRunDetail` 反查 `jobId → step_run_id / task_name / project_id` 的映射。

## 架构决策

### ADR-1: 方案选型 — 新增分支 B 而非污染 `pipeline_obs_product`

| 方案 | 思路 | 结论 |
|------|------|------|
| 方案 A | `running` 态补齐 `pipeline_obs_product` 占用记录 | ❌ 污染该表状态机，影响其他接口 |
| 方案 B | `test_case_result` 自带流水线上下文，查询分叉 | ✅ 采纳 |

**理由**：`pipeline_obs_product` 由 `analyzePipelineRun` 在流水线结束后批量同步，是"产物 + 任务"维度的事实表；塞 `running` 态的占位记录会破坏其状态机，并影响产物的统计/查询逻辑。`test_case_result` 才是"用例"维度的事实表，由其承担 `running` 态更自然。

### ADR-2: 上下文补全采用持久化缓存表，不引入 Redis

- 同一 `pipelineRunId + jobId` 的映射在流水线运行期间不变
- 持久化到 MySQL 即可命中，无需引入新中间件
- 收益：架构更轻、运维成本低、跨实例共享

### ADR-3: 唯一键使用 `(pipeline_run_id, execute_id)` 而非 `id`

- 业务侧的 `executeId` 是用例维度的天然唯一键
- `pipeline_run_id` 参与避免跨运行重试时 `executeId` 冲突
- 历史数据 `execute_id IS NULL` 视为互不冲突（MySQL UNIQUE 索引允许多个 NULL）

### ADR-4: 上报接口不加 `@CheckPermission`

- 脚本调用场景，与 `BuildArtifactController.reportSecOptionScan` 保持一致
- 后续如需鉴权，统一补充独立 token 机制（不阻塞本次）

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `dto/pipeline/TestCaseReportRequestDTO.java` | 新增 | 上报接口请求 DTO |
| `entity/pipeline/TestCaseJobContextEntity.java` | 新增 | 持久化缓存表实体 |
| `entity/pipeline/TestCaseResultEntity.java` | 修改 | 加 5 字段（`projectId`/`pipelineId`/`pipelineRunId`/`stepRunId`/`taskName`） |
| `mapper/TestCaseJobContextMapper.java` | 新增 | 缓存表 CRUD |
| `mapper/TestCaseResultMapper.java` | 修改 | 加 `upsertByExecuteId` / `selectByPipelineRunId` |
| `resources/mapper/TestCaseResultMapper.xml` | 新增 | upsert 与查询 SQL |
| `service/PipelineService.java` | 修改 | 加 `reportTestCaseResult` 接口 |
| `service/impl/PipelineServiceImpl.java` | 修改 | 实现 + 改 `getTestReport` |
| `controller/BuildArtifactController.java` | 修改 | 加 `POST /test-case/report` |
| `resources/db/changelog/db.changelog.xml` | 修改 | 加 `addColumn`/`createTable` 变更集 |

## 关键设计细节

### 1. 写入链路

```
POST /test-case/report
       │
       ▼
  1. 参数校验：接口级必填 pipelineId/pipelineRunId/jobId，
     用例级必填 executeId/name/number/state，
     state ∈ {running, passed, failed, investigated, unavailable, blocked}
       │
       ▼
  2. 上下文补全（查 test_case_job_context）
     WHERE pipeline_run_id = ? AND job_id = ?
     ├─ 命中 → 直接取 step_run_id / task_name / project_id
     └─ 未命中 → 调华为云 ShowPipelineRunDetail(pipelineRunId)
                 遍历 stages → jobs → steps
                 在 stepRun.getInputs() 里匹配 key="jobId"
                 取 stepRun.getId() = step_run_id
                 取 stepRun.getName() = task_name
                 （匹配到多个 step 时取第一个）
                 写入 test_case_job_context
       │
       ▼
  3. 遍历 cases 逐条 upsert test_case_result
     命中 (pipeline_run_id, execute_id) → UPDATE 全字段
     未命中                          → INSERT (id = UUID.randomUUID())
     beginTime/endTime 用 SDF.format(new Date(item.getBeginTime())) 转换
     （参考现有 PipelineEventConsumer.buildTestCaseResultEntity）
```

### 2. 查询链路（双分支合并）

```
getTestReport(projectId, pipelineId, pipelineRunId, stepRunIds)
       │
       ├── 分支 A（历史数据，逻辑不动）
       │   ├─ 查 pipeline_obs_product → Map<logId, taskName>
       │   ├─ 查 test_case_result WHERE log_id IN (...)
       │   └─ taskName 从 idTaskNameMap 取
       │
       ├── 分支 B（实时上报数据，新逻辑）
       │   ├─ 查 test_case_result
       │   │   WHERE pipeline_run_id = ?
       │   │     AND pipeline_run_id IS NOT NULL
       │   │     AND step_run_id IN (...)  // stepRunIds 不传则不加此条件
       │   └─ taskName 从 test_case_result.task_name 取
       │
       ▼
  两段结果直接合并（去重依赖：路径 A execute_id 全为 null，路径 B 全为 uuid4，不重叠）
       │
       ▼
  统计 passedCount / passRate / failedCount（基于合并后全量）
       │
       ▼
  内存过滤（name/number/state） + 按 beginTime 排序 + 内存分页
```

### 3. 状态流

```
用例开始执行  →  上报 state=running，URL 字段为空  ─→  upsert（同 executeId）
                                                            │
用例执行完毕  →  上报 state=passed/failed/...，补填 URL   ─┘
                                                            ▼
                                              running 态记录被覆盖为最终态
```

### 4. 重试场景

| 场景 | 行为 | 可接受？ |
|------|------|---------|
| 用例集合不变，`executeId` 不变 | upsert 覆盖，状态正常更新 | ✅ |
| 用例集合不变，`executeId` 变了 | 旧记录残留 + 新记录插入 | ⚠️ 业务侧重试时复用同一 executeId 可规避 |
| 用例集合变化（用例被移除） | 被移除用例旧记录残留 | ⚠️ 同上 |

> **约定**：业务侧重试时应复用同一 `executeId`，规避残留问题。

### 5. 数据模型

#### `test_case_result` 新增字段

```sql
ALTER TABLE test_case_result
    ADD COLUMN project_id      VARCHAR(64)  NULL COMMENT '项目ID，新上报接口填入，路径A数据为null',
    ADD COLUMN pipeline_id     VARCHAR(64)  NULL COMMENT '流水线ID，新上报接口填入，路径A数据为null',
    ADD COLUMN pipeline_run_id VARCHAR(64)  NULL COMMENT '流水线运行记录ID，新上报接口填入，路径A数据为null',
    ADD COLUMN step_run_id     VARCHAR(64)  NULL COMMENT '子任务运行记录ID，新上报接口填入，路径A数据为null',
    ADD COLUMN task_name       VARCHAR(256) NULL COMMENT '子任务名称，新上报接口填入，路径A数据为null';
```

#### 新建 `test_case_job_context` 表

```sql
CREATE TABLE test_case_job_context (
    id              BIGINT       AUTO_INCREMENT PRIMARY KEY,
    pipeline_run_id VARCHAR(64)  NOT NULL COMMENT '流水线运行记录ID',
    job_id          VARCHAR(64)  NOT NULL COMMENT '构建任务ID（CodeArts Build）',
    step_run_id     VARCHAR(64)  NULL     COMMENT '对应的流水线 step 运行ID',
    task_name       VARCHAR(256) NULL     COMMENT '对应的 step 名称',
    project_id      VARCHAR(64)  NULL     COMMENT '项目ID',
    pipeline_id     VARCHAR(64)  NULL     COMMENT '流水线ID',
    create_time     DATETIME              COMMENT '创建时间',
    UNIQUE KEY uk_pipeline_run_job (pipeline_run_id, job_id)
);
```

#### 新增索引

```sql
-- upsert 唯一键；execute_id 为 null 时 MySQL 视为互不冲突，路径A数据不受影响
CREATE UNIQUE INDEX uk_pipeline_run_execute
    ON test_case_result (pipeline_run_id, execute_id);

-- 分支B查询加速
CREATE INDEX idx_pipeline_run_step
    ON test_case_result (pipeline_run_id, step_run_id);

-- 分支A查询（确认是否已有，无则补建）
-- SHOW INDEX FROM test_case_result;
CREATE INDEX idx_log_id
    ON test_case_result (log_id);
```

## 性能设计

| 维度 | 设计 |
|------|------|
| 写性能 | `INSERT ... ON DUPLICATE KEY UPDATE` 单条 SQL 原子操作，无额外事务 |
| 读性能 | 分支 B 走 `pipeline_run_id` 唯一索引前缀，与分支 A 持平 |
| 合并 | 两段结果在内存合并，不引入额外 DB 查询 |
| 统计/分页 | 与现有一致，不新增性能风险 |
| 外部接口 | 缓存命中后不再调 `ShowPipelineRunDetail` |
| 限额 | 单次上报 ≤ 500 条用例，超出建议业务侧分批 |

**接口性能目标**：

| 接口 | 目标 |
|------|------|
| `POST /test-case/report`（首次，含华为云 API 调用） | TP99 < 3s |
| `POST /test-case/report`（缓存命中） | TP99 < 1s |
| `GET /test-report`（含双分支合并） | 与现有持平 |

## 安全设计

- **鉴权**：上报接口放在 `BuildArtifactController` 下，与 `reportSecOptionScan` 保持一致，脚本调用场景不加 `@CheckPermission`
- **敏感信息**：`resultDownloadUrl` / `envDownloadUrl` 等 URL 不打印到日志
- **硬编码**：appkey/token/cookie 不写代码，继承现有配置管理方式
- **审计日志**：Service 层记录上报操作日志，含 `pipelineRunId` / `jobId` / 上报时间 / 用例数量
- **数据隔离**：服务端通过 `pipelineRunId` 反查补全 `projectId`，查询时携带 `projectId` 过滤

## API 接口设计

### 1. 上报接口

**请求**

```
POST /test-case/report
Content-Type: application/json
```

**请求体**

```json
{
  "pipelineId": "xxxx",
  "pipelineRunId": "xxxx",
  "jobId": "xxxx",
  "cases": [
    {
      "executeId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "name": "QWEN2_5_7B_Inference_MindIE_910b_0004",
      "number": "QWEN2_5_7B_Inference_MindIE_910b_0004",
      "state": "running",
      "description": "",
      "beginTime": 1763430624000,
      "endTime": null,
      "executorAddress": "10.116.239.252",
      "resultPreviewUrl": "",
      "resultDownloadUrl": "",
      "envPreviewUrl": "",
      "envDownloadUrl": "",
      "url": ""
    }
  ]
}
```

**字段说明**

| 字段 | 必填 | 说明 |
|------|------|------|
| `pipelineId` | ✅ | 流水线 ID |
| `pipelineRunId` | ✅ | 流水线本次运行记录 ID |
| `jobId` | ✅ | 构建任务 ID（CodeArts Build 体系） |
| `cases[].executeId` | ✅ | uuid4，upsert 唯一键，同一次用例执行全程不变，重试时复用 |
| `cases[].name` | ✅ | 用例名称 |
| `cases[].number` | ✅ | 用例编号 |
| `cases[].state` | ✅ | `running` / `passed` / `failed` / `investigated` / `unavailable` / `blocked` |
| `cases[].beginTime` | ❌ | UTC 时间戳 (ms)，`running` 态可不填 |
| `cases[].endTime` | ❌ | UTC 时间戳 (ms)，执行完成后填入 |
| `cases[].resultPreviewUrl` | ❌ | `running` 态可不填 |
| `cases[].resultDownloadUrl` | ❌ | `running` 态可不填，完成后填入 |
| `cases[].envPreviewUrl` | ❌ | 选填 |
| `cases[].envDownloadUrl` | ❌ | 选填 |
| `cases[].executorAddress` | ❌ | 选填 |
| `cases[].description` | ❌ | 选填 |
| `cases[].url` | ❌ | 选填 |

> `step_run_id / task_name / project_id` 均由服务端反查补全，业务侧无需传。

**业务侧调用约定**

- 用例开始执行时调一次，`state=running`，结果相关 URL 不填
- 用例执行完毕后调一次，传同一个 `executeId`，`state` 更新为最终结果，补填 URL
- 重试时复用同一个 `executeId`，触发 upsert 覆盖旧记录

**响应**

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

**错误码**

| 场景 | code | 说明 |
|------|------|------|
| 必填字段缺失或 `state` 非法值 | 400 | 参数校验失败 |
| `jobId` 在流水线详情中匹配不到 step | 400 | jobId 不合法或流水线尚未初始化 |
| 华为云 API 调用失败 | 500 | 上报失败，建议重试 |
| 单次上报用例数 > 500 | 400 | 建议业务侧分批调用 |

### 2. 查询接口变更说明

`GET /test-report` 入参、响应结构均不变，内部新增分支 B 逻辑，对调用方完全透明。变化点：

- 查询结果中新增 `state=running` 的记录
- 分支 B 数据的 `taskName` 字段来自 `test_case_result.task_name`，与分支 A 一致

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 重试时 `executeId` 变化导致旧记录残留 | 业务侧约定复用 `executeId`；未来可加清理 job |
| 首次上报时 `ShowPipelineRunDetail` 慢 | 缓存表持久化，后续命中不再调；设置 3s 性能目标 |
| 分支 A/B 合并出现重复记录 | 经核对两条路径 `execute_id` 不重叠（路径 A 全 null，路径 B 全 uuid4），实际无重复 |
| 加字段对历史查询性能影响 | 历史数据新字段全为 NULL，零索引命中，零影响 |
| 新增唯一索引 `uk_pipeline_run_execute` 对历史数据的影响 | 历史数据 `execute_id` 多数为 null，MySQL UNIQUE 允许多个 NULL，不会冲突 |

## 跨仓影响

无。前端无需改动（接口对前端透明）；其他业务仓不涉及。

## 兼容性

- 历史 `log_id` 路径数据查询行为完全不变
- `getTestReport` 响应结构零变化，前端零改动
- 异步 MQ 链路保留作为兜底，不删除
