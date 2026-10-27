# #294 需求分析说明书

## 1. 基础信息

| 项目 | 内容 |
|---|---|
| 需求名称 | 【蓝区】【运营看板】PR流水线数据支持明细查看 |
| 关联 Issue | https://gitcode.com/openlibing/openlibing-ops/issues/294 |
| 关联页面 | https://www.openlibing.com/ops/dashboard/engineering-capability |
| 后端仓库 | openlibing-ops |
| 前端仓库 | openlibing-ops-web（本期不改动） |
| 开发分支 | `feature_293_new` |

## 2. 需求目标

工程能力看板“项目详情-PR流水线”的三个指标统一下钻到**同一种明细**：

| 入口指标 | 明细类型 |
|---|---|
| PR执行时长(min)[P90] | **流水线执行明细**（18 列） |
| PR构建资源排队时长(min)[P90] | **流水线执行明细**（18 列） |
| PR测试资源排队时长(min)[P90] | **流水线执行明细**（18 列） |

三个入口（以及 pr-access 执行次数）打开的都是同一张流水线执行明细；每行均可再下钻查看该次运行的任务明细（与 pr-access 一致）。

### 2.1 pr-access 页面扩展（/dashboard/pr-access/:projectId）

- 表格新增“执行次数”列
- 点击执行次数下钻到“流水线执行明细”，并与页面“流水线状态”筛选联动（全部 / 成功 / 失败）
- 流水线执行明细的每一行支持再次下钻查看**该次运行的任务明细**，展示：任务名称、任务时长(min)、任务状态、排队时长(min)、调度时间、NPU(卡时)
- 下钻明细在原 15 列基础上增加：NPU资源数据（总卡时）、代码检查任务平均时长、代码检查任务最长时长
- 时间口径：
  - PR 个数（总数、开启中、已关闭、已合入、强制合入数）按 **PR 创建时间** 筛选
  - 其他所有指标（执行次数、成功率、时长、资源、编译/测试/代码检查任务、PR闭环/合入时长、E2E达标率）按 **流水线执行时间** 筛选

## 3. 口径与数据源

明细样本必须与主表 `OpsMainStatMapper.xml` 的 `pr_run_sample` 完全一致：

- 运行表：`dwr_rd_efc_pipeline_run_unified`
- 任务表：`dwr_rd_efc_pipeline_run_job_unified`
- PR 样本：`dwi_rd_efc_pr_info_sum` → `sdi_rd_efc_pipeline_run_pr_relation_codearts`（`pr_id` 非空）→ 统一运行表，按 run 去重
- 仓库范围：`sdi_repo_info` 中 `repo_id IN (sdi_rd_efc_repo_operate_conf.is_operate=1)`，按 `sdi_repo_info.project_id` 归属项目
- GitHub 运行额外限定：`dim_ecod_github_show_pr_config`（`gc.project_id = sd.project_id`）+ `dwi_rd_efc_pr_workflow_run` 关联，与主表一致
- 时间窗：按 `u.start_time` 过滤
- **不叠加** `pipeline_type='PR'` 判断（主表 2026-09-17 统一后的 PR 门禁口径：桥表 `pr_id` 非空即 PR run）

### 3.1 两个现有 Mapper 的口径差异（需确认）

| 位置 | pipeline_type='PR' | GitHub 配置匹配 |
|---|---|---|
| `OpsMainStatMapper.xml`（主表） | 不加 | `gc.project_id = sd.project_id` |
| `OpsRepoDetailMapper.xml`（仓库明细） | 加 | `cfg.openlibing_project_id = projectId` 且 `cfg.repo_url = pr.repo_url` |

本期 #294 明细**以主表为准**（用户确认）。仓库级 P90 与明细可能出现样本条数差异，需产品确认是否将两者收敛到同一口径。

## 4. 明细一：流水线执行明细

入口：PR执行时长 P90、构建资源排队 P90、测试资源排队 P90、pr-access 执行次数。四个入口打开同一张明细，**均支持任务下钻**（传 `pipelineRunId` 调 6.2 任务明细接口）。

样本：与主表 `p90_stat` 一致时传 `pipelineStatus=true`（`status='COMPLETED'` 且 `end_time` 非空）；从 pr-access 执行次数进入时，样本与页面状态筛选一致。

| # | 列 | 字段 / 计算 |
|---|---|---|
| 1 | 流水线执行编号 | `run_number`（主展示）+ `pipeline_run_id`（跳转参数） |
| 2 | 流水线名称 | `pipeline_name` |
| 3 | 流水线平台 | `platform`，取值 `gitcode` / `github` / `codearts`（与 Nightly 明细一致，展示文案由前端映射） |
| 4 | 流水线启动时间 | `start_time` |
| 5 | 流水线结束时间 | `end_time`（运行中为 NULL，展示 `-`） |
| 6 | 流水线状态 | `status` |
| 7 | 流水线执行时长(min) | `ROUND(duration_ms / 60000, 1)` |
| 8 | 构建任务平均时长(min) | `AVG(job_duration) WHERE job_type='BUILD'` |
| 9 | 构建任务最长时长(min) | `MAX(job_duration) WHERE job_type='BUILD'` |
| 10 | 构建任务排队平均时长(min) | `AVG(job_pending_duration) WHERE job_type='BUILD'` |
| 11 | 构建任务最长排队时长(min) | `MAX(job_pending_duration) WHERE job_type='BUILD'` |
| 12 | 测试任务平均时长(min) | `AVG(job_duration) WHERE job_type='DT'` |
| 13 | 测试任务最长时长(min) | `MAX(job_duration) WHERE job_type='DT'` |
| 14 | 测试任务排队平均时长(min) | `AVG(job_pending_duration) WHERE job_type='DT'` |
| 15 | 测试任务最长排队时长(min) | `MAX(job_pending_duration) WHERE job_type='DT'` |
| 16 | NPU资源数据(卡时) | `ROUND(npu_second / 3600, 2)`（测试入口固定展示总卡时） |
| 17 | 代码检查任务平均时长(min) | `AVG(job_duration) WHERE job_type='CHECK'` |
| 18 | 代码检查任务最长时长(min) | `MAX(job_duration) WHERE job_type='CHECK'` |

交互与排序：

- 编号列支持跳转，URL 规则见 6.3
- pr-access 入口下钻时，每行提供“查看任务”，携带 `pipelineRunId` 打开任务明细（6.2），展示该次运行的全部任务；工程能力看板入口不绑定该事件
- 默认按 `start_time DESC`；支持按启动时间、执行时长、构建/测试平均时长排序
- 运行中没有对应类型任务时，8-15、17-18 列展示 `-`
- 状态筛选：只保留 `COMPLETED` / `FAILED` 两种实际状态
  - 为空（全部）= `status IN ('COMPLETED','FAILED')`
  - `true`（成功）= `status = 'COMPLETED'`
  - `false`（失败）= `status = 'FAILED'`
  - `CANCELED / IGNORED / RUNNING / INIT` 不计入执行次数，也不在下钻中返回
- 页面与下钻统一过滤 `end_time IS NOT NULL`

## 5. 明细二：任务明细

入口：**流水线执行明细行下钻**（必传 `pipelineRunId`，返回该次运行的任务；`jobType` 可选，用于按类型过滤）。构建/测试排队入口不再直接进入任务明细。

样本：所属运行 `end_time` 非空（不限运行状态）。

| # | 列 | 字段 / 计算 |
|---|---|---|
| 1 | 任务执行编号 | `job_id`（支持跳转，URL 追加 `/job/{jobId}` 或 `jobRunId`） |
| 2 | 任务名称 | `job_name` |
| 3 | 流水线名称 | `unified.pipeline_name` |
| 4 | 流水线平台 | `unified.platform`，取值 `gitcode` / `github` / `codearts` |
| 5 | 任务类型 | `job_type`（BUILD=构建，DT=测试，CHECK=代码检查，OTHER=其他） |
| 6 | 任务状态 | `job_status` |
| 7 | 调度时间 | `job_run_start_time`（任务被调度、开始执行的时刻；排队时长 = 调度时间 − 入队时间） |
| 8 | 任务入队时间 | `job_start_time`（排队起点） |
| 9 | 任务结束时间 | `job_end_time`（未结束展示 `-`） |
| 10 | 任务时长(min) | `ROUND(job_duration / 60, 1)`（job 表时长为秒） |
| 11 | 排队时长(min) | `ROUND(job_pending_duration / 60, 1)`（job 表时长为秒） |
| 12 | NPU(卡时) | `ROUND(npu_second / 3600, 2)`（任务级 npu_second，单位秒） |
| 13 | 流水线执行编号 | `unified.run_number`（便于定位） |
| 14 | 流水线ID | `unified.pipeline_id`（跳转必需参数，可不展示） |

pr-access 任务下钻仅展示 6 列：**任务名称(2)、任务时长(10)、任务状态(6)、排队时长(11)、调度时间(7)、NPU(12)**，其余列由接口返回、前端按需渲染。

排序与筛选：

- 固定按 `pipelineRunId` 过滤，只返回该次运行的任务
- `jobType` 可选：为空返回全部任务类型；传 `BUILD`/`DT` 时只返回对应类型
- 默认按 `job_run_start_time ASC`（按调度先后），空调度时间排在最后
- 时间窗按所属运行 `unified.start_time` 过滤
- 运行状态不限（与主表排队口径“全部状态 + `end_time` 非空”一致）

## 6. 接口设计

复用 `POST /common/detail`，新增两个 category。

### 6.1 流水线执行明细

```text
category = ops-pr-pipeline-run-detail
```

请求：

| 参数 | 必填 | 说明 |
|---|---|---|
| projectId | 是 | openlibing 项目 ID |
| repoId | 否 | 单仓过滤 |
| startDate / endDate | 是 | 按运行 start_time 过滤 |
| pipelineStatus | 否 | 空=COMPLETED+FAILED，`true`=COMPLETED，`false`=FAILED |
| visibility | 否 | 开源类型，与页面筛选透传一致 |
| repoIdList | 否 | 多仓筛选，与页面筛选透传一致 |
| page / pageSize | 是 | 分页 |
| sortField / sortRule | 否 | 默认 start_time desc |

统一过滤 `end_time IS NOT NULL`；`CANCELED/IGNORED/RUNNING/INIT` 不返回。该参数需与 pr-access 页面筛选一致，保证“执行次数 = 明细 total”。

响应行：`runNumber, pipelineRunId, pipelineId, pipelineName, platform, repoId, repoName, repoUrl, status, startTime, endTime, durationMinutes, buildAvgDurationMinutes, buildMaxDurationMinutes, buildAvgPendingMinutes, buildMaxPendingMinutes, dtAvgDurationMinutes, dtMaxDurationMinutes, dtAvgPendingMinutes, dtMaxPendingMinutes, npuHours, checkAvgDurationMinutes, checkMaxDurationMinutes`

### 6.2 任务明细

```text
category = ops-pr-pipeline-job-detail
```

请求：

| 参数 | 必填 | 说明 |
|---|---|---|
| projectId | 是 | openlibing 项目 ID |
| pipelineRunId | 是 | 流水线运行ID：任务明细仅用于流水线执行明细行下钻 |
| jobType | 否 | `BUILD` / `DT`；为空表示该次运行的全部任务类型 |
| repoId | 否 | 单仓过滤 |
| visibility | 否 | 开源类型，与页面筛选透传一致 |
| repoIdList | 否 | 多仓筛选，与页面筛选透传一致 |
| startDate / endDate | 是 | 按所属运行 start_time 过滤 |
| page / pageSize | 是 | 分页 |
| sortField / sortRule | 否 | 默认 `job_run_start_time asc`（空调度时间排最后） |

`pipelineRunId` 为空时直接返回参数校验错误（避免退化为全量任务查询）。

响应行：`jobId, jobName, jobType, jobStatus, pipelineId, pipelineRunId, runNumber, pipelineName, platform, repoId, repoName, repoUrl, scheduleTime, startTime, endTime, pendingMinutes, durationMinutes, npuHours`

### 6.3 跳转 URL 规则（由前端拼接）

后端**不返回** URL，仅返回拼接所需字段：`platform`、`repoUrl`、`pipelineId`、`pipelineRunId`、`jobId`。前端按 `getPipelineUrl` 既有规则拼接：

- `platform in (gitcode, github)`：`{repoBase}/actions/runs/{pipelineRunId}`；任务：追加 `/job/{jobId}`
- 其他（codearts 等）：`{origin}/apps/pipelineDetail?pipelineId=..&projectId=..&pipelineRunId=..`；任务：追加 `&jobRunId={jobId}`

`repoBase` 由响应中的 `repoUrl` 去掉 `.git` 得到；`projectId` 使用请求参数。

## 7. SQL 设计

### 7.1 公共样本（与主表一致）

```sql
WITH github_show_cfg AS (
    SELECT DISTINCT
        openlibing_project_id AS project_id,
        repo_url,
        workflow_name
    FROM dim_ecod_github_show_pr_config
),
pr_run_sample AS (
    SELECT DISTINCT
        sd.project_id, sd.repo_id, pr.repo_url,
        u.platform, u.pipeline_id, u.pipeline_run_id,
        u.pipeline_name, u.run_number, u.status, u.start_time, u.end_time,
        u.duration_ms, u.npu_second
    FROM dwi_rd_efc_pr_info_sum pr
    INNER JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts rel
        ON pr.repo_url = rel.git_url AND pr.number = rel.pr_id
    INNER JOIN dwr_rd_efc_pipeline_run_unified u
        ON rel.pipeline_id = u.pipeline_id
       AND rel.pipeline_run_id = u.pipeline_run_id
    INNER JOIN (
        SELECT repo_id, repo_url, project_id
        FROM sdi_repo_info
        WHERE repo_id IN (
                  SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1
              )
          AND project_id = #{req.projectId}
        -- repoId 可选过滤
    ) sd ON pr.repo_url = sd.repo_url
    WHERE u.start_time >= #{req.startTime}
      AND u.start_time <= #{req.endTime}
      AND (
          u.platform != 'github'
          OR EXISTS (
              SELECT 1
              FROM github_show_cfg gc
              INNER JOIN dwi_rd_efc_pr_workflow_run pw
                  ON pw.repo_url = gc.repo_url AND pw.workflow_name = gc.workflow_name
              WHERE pw.workflow_run_id = u.pipeline_run_id
                AND gc.project_id = sd.project_id
          )
      )
)
```

### 7.2 流水线执行明细

先分页取运行，再只对这些 run 聚合任务，避免全量 job 扫描：

```sql
page_run AS (
    SELECT * FROM pr_run_sample
    WHERE end_time IS NOT NULL
      AND status IN ('COMPLETED', 'FAILED')
      AND (#{req.pipelineStatus} IS NULL
           OR (#{req.pipelineStatus} = 'true'  AND status = 'COMPLETED')
           OR (#{req.pipelineStatus} = 'false' AND status = 'FAILED'))
    ORDER BY start_time DESC
    LIMIT #{req.pageSize} OFFSET #{offset}
),
job_agg AS (
    SELECT pipeline_run_id,
           AVG(CASE WHEN job_type = 'BUILD' THEN job_duration END)         AS build_avg_duration,
           MAX(CASE WHEN job_type = 'BUILD' THEN job_duration END)         AS build_max_duration,
           AVG(CASE WHEN job_type = 'BUILD' THEN job_pending_duration END) AS build_avg_pending,
           MAX(CASE WHEN job_type = 'BUILD' THEN job_pending_duration END) AS build_max_pending,
           AVG(CASE WHEN job_type = 'DT' THEN job_duration END)            AS dt_avg_duration,
           MAX(CASE WHEN job_type = 'DT' THEN job_duration END)            AS dt_max_duration,
           AVG(CASE WHEN job_type = 'DT' THEN job_pending_duration END)    AS dt_avg_pending,
           MAX(CASE WHEN job_type = 'DT' THEN job_pending_duration END)    AS dt_max_pending,
           AVG(CASE WHEN job_type = 'CHECK' THEN job_duration END)         AS check_avg_duration,
           MAX(CASE WHEN job_type = 'CHECK' THEN job_duration END)         AS check_max_duration
    FROM dwr_rd_efc_pipeline_run_job_unified
    WHERE pipeline_run_id IN (SELECT pipeline_run_id FROM page_run)
      AND job_type IN ('BUILD', 'DT', 'CHECK')
    GROUP BY pipeline_run_id
)
```

流水线执行时长取 `duration_ms / 60000`；本期无重试耗时数据，不再区分“不含重试”。

### 7.3 任务明细

任务明细使用共享的 `pr_run_base`（与执行明细同源，但**不**限定运行状态，对齐主表 `queue_stat`），仅过滤所属运行 `end_time IS NOT NULL`：

```sql
SELECT j.job_id, j.job_name, j.job_type, j.job_status,
       j.job_run_start_time AS schedule_time,
       j.job_start_time     AS start_time,
       j.job_end_time,
       ROUND(j.job_pending_duration / 60.0, 1) AS pending_minutes,
       ROUND(j.job_duration / 60.0, 1)         AS duration_minutes,
       ROUND(j.npu_second / 3600.0, 2)         AS npu_hours,
       r.pipeline_id, r.pipeline_run_id, r.run_number, r.pipeline_name, r.platform,
       r.repo_id, r.repo_name, r.repo_url
FROM pr_run_base r
INNER JOIN dwr_rd_efc_pipeline_run_job_unified j
    ON j.pipeline_run_id = r.pipeline_run_id
WHERE r.end_time IS NOT NULL
  <if test="req.jobType != null and req.jobType != ''">
    AND j.job_type = #{req.jobType}
  </if>
  <if test="req.pipelineRunId != null and req.pipelineRunId != ''">
    AND r.pipeline_run_id = #{req.pipelineRunId}
  </if>
ORDER BY
  <choose>
    <when test="req.sortField == 'schedule_time'">
      CASE WHEN j.job_run_start_time IS NULL THEN 1 ELSE 0 END ASC,
      j.job_run_start_time ${req.sortRule},
    </when>
    <when test="req.sortField != null and req.sortField != ''">
      ${req.sortField} ${req.sortRule},
    </when>
    <when test="req.pipelineRunId != null and req.pipelineRunId != ''">
      CASE WHEN j.job_run_start_time IS NULL THEN 1 ELSE 0 END ASC,
      j.job_run_start_time ASC,
    </when>
    <otherwise>j.job_pending_duration DESC,</otherwise>
  </choose>
  j.job_id ASC
LIMIT #{req.pageSize} OFFSET #{offset}
```

- `schedule_time` = `job_run_start_time`（调度时间），`start_time` = `job_start_time`（入队时间），两者差值即 `job_pending_duration`
- `job_duration` / `job_pending_duration` 单位为**秒**，展示时 `ROUND(x/60, 1)` 换算分钟；`unified.duration_ms` 为毫秒，`ROUND(duration_ms/60000, 1)` 换算分钟
- `npu_second` 为任务级 NPU 秒数，展示时 `ROUND(npu_second/3600, 2)` 换算卡时
- `pipelineRunId` 下钻场景走同一 Mapper statement，仅附加 run 过滤与排序切换；total 使用同一 WHERE 片段

## 8. 数据现状与限制

### 8.1 执行时长

- `dwr_rd_efc_pipeline_run_unified.retry_count` 近 30 天全为 0，`dwr_rd_efc_pipeline_run_efficiency` 近 30 天仅 gitcode 1 条，无重试耗时数据
- 结论：流水线执行明细只保留一列“流水线执行时长”，取 `duration_ms`，不再区分“不含重试”

### 8.2 为什么任务时长必须从 job 表聚合

- `dwr_rd_efc_pipeline_run_fact` 中 `build_duration = build_max_duration`、`build_pending_duration = build_max_pending_duration` 全部相等（476,684 行验证），无法区分“平均/总量”和“最长”
- 统一运行表本身不含 build/dt 聚合列，故按 run 聚合 job 统一表计算

### 8.2.1 聚合层级（已确认）

| 场景 | 聚合方式 | 说明 |
|---|---|---|
| 流水线执行明细的“构建任务平均/最长时长” | 该 run 内所有 BUILD 任务的 `AVG/MAX(job_duration)` | 单次运行内部的任务均值 |
| PR门禁看板 / 趋势图 / 工程能力主表与仓库明细的“编译/测试/代码检查时长、排队时长” | **run 级**：先按 run 取该类型任务的 `MAX(时长/排队)`，**再跨 run** 计算 `AVG/PERCENTILE` | 2026-10 三处统一为 run 级 |

说明：run 级反映“一次门禁中最长任务/排队”，是考核口径；job 行级会被大量零排队任务稀释（ops-nn 抽样：编译 P90 job 行级 418.0s vs run 级 816.5s，平均 136.8s vs 449.5s）。明细行内的“平均”仍是 run 内多任务均值，与看板跨 run 平均语义不同，不矛盾。

### 8.3 平台覆盖

- 运行统一表含 github / codearts / gitcode 三平台
- github 任务的 `job_type` 可能为 OTHER，构建/测试列在 github 运行上通常为 `-`，属正常

## 9. 范围

- 本期只做后端接口与 SQL，不改动 `openlibing-ops-web`
- 前端交互（入口点击、列渲染）后续单独提需求

## 10. pr-access 页面改造（repo-pr-pipeline）

### 10.1 现状问题

- 查询 `dm_rd_efc_pr_sum_pipeline_statistics_day`，`data_time` 实测等于 PR 创建日期（一个 PR 一行）
- 因此执行次数、成功率、时长、资源、任务时长、PR 闭环/合入、E2E 达标率目前全部随 **PR 创建时间** 过滤，与目标口径不符

### 10.2 目标口径

| 指标组 | 时间口径 |
|---|---|
| PR 个数（总数、开启中、已关闭、已合入、强制合入数） | PR 创建时间（DM `data_time`），**状态筛选逻辑保持现网不变** |
| 其余全部指标 | 流水线开始时间 `u.start_time` |

### 10.3 改造方案

1. **PR 个数（完全沿用现网逻辑，不做改造）**：继续查 `dm_rd_efc_pr_sum_pipeline_statistics_day`，按 `data_time between startDate and endDate`（PR 创建日期）过滤；`pipeline_status` 映射保持现网三档：空 → `ALL_PIPELINE_STATUS`、`true` → `COMPLETED`、`false` → `FAILED`；`count(distinct number)` 与 `state` / `access_status` 计数逻辑均不变
   - 现状实测（`cann/ops-nn`，2026-09-20~10-23）：全部 1417 / 成功 1311 / 失败 654，PR 个数随状态筛选变化，属预期行为，本次不调整
2. **运行指标**：复用 `pr_run_sample`（与主表一致），按 repo 聚合
   - 执行次数 `COUNT(DISTINCT pipeline_run_id)`，成功次数与成功率
   - `duration_ms` 的 avg / max / p50 / p90 / p95
   - `SUM(cpu_second / npu_second / memory_second)`（换算核时/卡时/GB·h）
   - `LEFT JOIN dwr_rd_efc_pipeline_run_efficiency` 取不含重试时长
3. **任务指标**：`job_unified` **按 run 级**聚合——先按 run 取 `BUILD / DT / CHECK` 的 `MAX(时长/排队)`，再跨 run 计算 avg / max / p50 / p90 / p95；任务级 CPU/NPU/内存按 run 汇总后求和（与主表/仓库明细一致，见 8.2.1）
4. **PR 生命周期**：基于“窗口内有运行”的 PR 集合计算 PR 闭环时长、合入时长、E2E 达标率
5. **状态筛选**：`pipelineStatus` 同时作用于 PR 个数（保持现网三档映射）与执行次数、运行指标、任务指标；PR 生命周期类指标不随之变化（见 10.5）
6. **执行次数字段归一为 `runCount`**：按 `pipelineStatus` 过滤；原 `executeCount`、`executeTotalCount` 在本接口响应中**不再返回**（三者原本同值，避免前端误用）。DM 侧 `execute_count` 字段仍保留给外部接口/历史查询使用
7. 下钻：调用 `ops-pr-pipeline-run-detail`，传 `projectId + repoId + 时间窗 + pipelineStatus`

### 10.3.1 趋势图改造（与表格同源）

**问题**：改造前趋势图（`POST /repo/pr/chart`）读 `dm_rd_efc_repo_sum_pipeline_statistics_day`；该表实测**全表 `max(data_time) = 2026-09-23`（821 个仓全部停更）**。表格改实时后，同页会出现“表格有数、图表近一个月空白”。

**改造**：新增 `OpsRepoPrChartMapper`，按（仓库, 天）聚合，与表格使用同一数据源：

| 图表指标 | 数据源 | 时间口径 |
|---|---|---|
| PR总数、PR闭环、流水线启动、PR合入 | PR 维度 DM（`dm_rd_efc_pr_sum_pipeline_statistics_day`，与表格 PR 个数同源） | `data_time` = PR 创建日 |
| 门禁时长（accessAvgTime） | 实时运行统一表 | `DATE(u.start_time)` |
| 编译/测试/代码检查时长 | 实时 job 统一表，先按 run 取 MAX 再跨 run 平均（与表格 run 级同口径） | `DATE(u.start_time)` |
| 构建/测试最大并发 | `dwi_repo_pipeline_concurrent_statistics`（未停更，保持原样） | `data_time` |

过滤条件（项目、运营仓、开源类型/可见性、仓库、状态）与表格完全一致；因此图表按天累加的 PR 总数 = 表格窗口 PR 个数（实测 ops-nn：1417）。

### 10.4 性能与兼容

- 页面按 repo 分页：先分页取 repo，再对这些 repo 聚合 run / job
- DM 表继续保留（其他页面在用），但本页面的**表格与趋势图**均改为实时/PR 维度 DM 聚合，不再依赖已停更的 `dm_rd_efc_repo_sum_pipeline_statistics_day`
- “执行次数”与下钻 total 必须相等，作为验收硬指标

### 10.5 已确认口径

1. **状态筛选按实际状态**：`pipelineStatus` 为空 = `COMPLETED + FAILED`；`true` = `COMPLETED`；`false` = `FAILED`。`CANCELED / IGNORED / RUNNING / INIT` 既不计入执行次数，也不在下钻中返回
2. **统一过滤 `end_time IS NOT NULL`**：执行次数、明细 total、明细列表三处一致
3. **PR 个数**：**完全保持现网逻辑**（DM 主表 + `data_time` = PR 创建日期 + 现网三档 `pipeline_status` 映射），数值与改造前一致，随状态筛选变化
4. **PR 生命周期类指标**（闭环时长、合入时长、E2E 达标率）不随状态筛选变化
5. **资源与时长类指标**（avg / max / p50 / p90 / p95、CPU/NPU/内存）随状态筛选变化

### 10.5.1 跨看板口径差异（实测，供产品/前端提示）

PR门禁看板与工程能力运营看板存在**固有口径差异**，同名指标不可直接对比：

| 维度 | PR门禁看板（本页） | 工程能力主表 | 工程能力仓库明细 |
|---|---|---|---|
| 样本 | 桥表 `pr_id` 非空 + 运营仓 + GitHub 展示配置 | 同左 | **额外加 `pipeline_type='PR'`**，GitHub 配置按 `projectId+repo_url` 匹配 |
| 状态 | 默认 `COMPLETED+FAILED`（可选三档） | P90 仅 `COMPLETED`；排队含全部状态 | 仅 `COMPLETED` |
| 任务时长（构建/测试） | run 级 | **run 级（2026-10 三处统一）** | **run 级（2026-10 三处统一）** |
| 资源 | 运行表 `SUM(cpu/npu/memory_second)` | CPU 取 `dwi_project_resource_indicator_day`；NPU 取运行表（桥表+`pipeline_type='PR'`，无 GitHub 配置过滤、全状态） | — |

**任务/排队口径统一记录（2026-10）**：PR门禁看板、工程能力主表（`OpsMainStatMapper.queue_stat`）、仓库明细（`OpsRepoDetailMapper.queue_p90`）三处统一为 **run 级**——每个 run 取该类型任务的最大时长/排队，再跨 run 求 P90；`resourceQueueTime = buildQueueP90 + dtQueueP90` 保持恒等。

run 级 vs job 行级量级参考（2026-09-20~10-23，仅说明差异，最终口径为 run 级）：

| 项目 | 指标 | run 级（最终） | job 行级（曾评估） |
|---|---|---|---|
| 300080 | 构建排队 P90 | **5.43 min** | 2.52 min |
| 300080 | 测试排队 P90 | **5.67 min** | 3.18 min |
| 300080 | 资源排队（合计） | **11.10 min** | 5.70 min |
| 300033 | 构建排队 P90 | **0.03 min** | 0.02 min |

其余实测差异（2026-09-20~10-23）：

| 指标 | PR门禁看板 | 工程能力 | 差异 |
|---|---|---|---|
| PR执行时长 P90（ops-nn） | 1267.2s | 仓库明细 1524.0s | +20% |
| PR 样本 run 数（project 300127） | 6,696 | 主表 NPU 口径 45,491 | 6.8 倍 |
| NPU 卡时（300127） | 33,057.75 | 70,533.92 | 2.1 倍 |
| CPU 核时（300127） | 571,126.4 | 1,289,246.67（indicator） | 2.3 倍 |
| CPU 核时（300033） | 37.92 | 0（indicator 无数据） | 数据源缺失 |

结论：本期已统一**任务/排队指标**为 run 级；PR门禁看板内部（表格/图表/明细/抽屉/导出）一致。剩余跨看板差异集中在样本过滤（`pipeline_type`、GitHub 配置）、状态口径与资源数据源，需产品确认后再统一。

### 10.6 一致性保障规则

“执行次数 = 下钻 total”是本需求的硬约束，落地时按以下规则保证：

| 规则 | 要求 |
|---|---|
| R1 共享样本 | `pr_run_sample` 抽成 Mapper 内共享 `<sql id="prRunSample">` 片段，执行次数 / 明细 total / 明细列表三处引用同一片段，禁止各自复制改写 |
| R2 共享过滤 | 状态映射与 `end_time IS NOT NULL` 抽成 `<sql id="prRunStatusFilter">`，页面聚合与明细查询共同引用 |
| R3 状态映射 | 空 = `status IN ('COMPLETED','FAILED')`；`true` = `COMPLETED`；`false` = `FAILED`；其余状态一律排除。请求参数大小写/首尾空格在 Service 统一归一后再进入 SQL |
| R4 时间窗 | 统一按 `u.start_time`，边界为 `[startDate 00:00:00, endDate 23:59:59]`，由服务端一次性转换，前端只传 `yyyy-MM-dd` |
| R5 筛选透传 | 下钻请求必须透传 `projectId`、`repoId`、`visibility`、`repoIdList`、`startDate`、`endDate`、`pipelineStatus`，与页面同名同义 |
| R6 total 口径 | 分页 total 与列表共用同一 WHERE 片段，total 在分页外层统计，不得单独再写一套条件 |
| R7 验收断言 | 任一仓库、任一状态档位下，`runCount` 必须等于明细 total；差异即视为缺陷 |
| R8 PR 数量沿用现网 | PR 个数查询块（DM 主表 + 现网三档 `pipeline_status` 映射 + `data_time` 时间窗）整体保留原样，改造时不改写其过滤条件与计数表达式 |
| R9 图表与表格同源 | 趋势图 PR 类指标与表格 PR 个数同源（PR 维度 DM）；运行/任务类指标与表格同源（实时运行表 + job 统一表，run 级聚合）；过滤条件（项目/运营仓/可见性/仓库/状态）必须一致 |

## 11. 验收要点

1. 工程能力三个入口（PR执行时长/构建排队/测试排队）与 pr-access 执行次数，均打开**同一张流水线执行明细**（18 列）
2. 流水线明细的 8-15、17-18 列与 `job_unified` 聚合结果一致（抽查一个 run 手工核对 AVG/MAX）
3. 四个入口的流水线明细均支持任务下钻；任务明细按 `pipelineRunId` 返回该次运行的任务，默认按调度时间升序
4. 后端返回 `platform`、`repoUrl`、`pipelineId`、`pipelineRunId`、`jobId`，前端据此拼接跳转链接可在 gitcode/github/codearts 三类平台打开
5. 运行中记录：结束时间、任务类列展示 `-`
6. 明细样本与主表 P90 同源，抽查仓库的样本条数一致
7. pr-access 页面“执行次数”与下钻 total 相等（相同时间窗与状态筛选），且三档状态（全部/成功/失败）均成立
8. 状态筛选切换“全部/成功/失败”时，执行次数与下钻同步变化；`CANCELED/IGNORED/RUNNING/INIT` 均不出现在明细中
9. NPU 列展示总卡时，与页面“资源总消耗 NPU(卡时)”单位一致
10. 代码检查任务列只统计 `job_type='CHECK'`
11. 页面 PR 个数随 PR 创建时间变化，其余指标随流水线开始时间变化
12. PR 个数在改造前后逐项数值一致（含全部/成功/失败三档），状态筛选逻辑保持现网行为
13. 任务明细展示 6 列：任务名称、任务时长(min)、任务状态、排队时长(min)、调度时间、NPU(卡时)；`调度时间 = job_run_start_time`，`排队时长 ≈ 调度时间 − job_start_time`
14. 任务明细 total 与返回行数一致（同 `pipelineRunId`、同时间窗）；`pipelineRunId` 为空时返回参数校验错误
15. 页面/图表/工程能力主表与仓库明细的编译、测试、代码检查时长与排队时长均为 **run 级**（先 MAX 后分位/平均），三处口径一致
16. 趋势图有最新数据（不再停在 2026-09-23）；图表各仓 PR 总数之和 = 表格同窗口 PR 个数；状态切换时图表与表格同步变化
17. 工程能力 `resourceQueueTime = buildQueueP90 + dtQueueP90` 恒等
