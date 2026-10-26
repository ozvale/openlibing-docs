# #293 需求分析说明书（细化版）

## 1. 基础信息

| 项目       | 内容                                                                                                |
| ---------- | --------------------------------------------------------------------------------------------------- |
| 需求名称   | 【蓝区】【运营看板】工程能力运营看板流水线指标统计优化                                              |
| 关联 Issue | https://gitcode.com/openlibing/openlibing-ops/issues/293                                            |
| 关联页面   | https://www.openlibing.com/ops/dashboard/engineering-capability                                     |
| 后端仓库   | openlibing-ops                                                                                      |
| 前端仓库   | openlibing-ops-web（无代码改动；指标提示由指标字典下发）                                            |
| 指标字典   | openlibing-metric                                                                                   |
| ETL        | DolphinScheduler（仓库外，产出 `dwi_repo_pipeline_quality_day`、`dm_project_quality_overview_day`） |

> **本期实施范围（feature_293_new）**：仅实施“例外备案和 committer 审核一体化”场景，包括仓库级判定、项目级聚合和后端明细消费。排队 P90、NPU 成功口径、Excel 标注等其他优化暂缓，不在本分支实施。

## 2. 已确认决策

1. 【暂缓】主表与下层下钻明细同时修改，必须使用同一套成功口径。
2. 【暂缓】NPU **消耗总量**也改为成功口径，不只是平均消耗。
3. 成功运行定义：GitCode 使用 `pipeline_status='COMPLETED'`，GitHub 使用 `conclusion='success'`。
4. 【本期实施】例外备案：最近 10 次成功运行中，任意一次单次运行满足 `new=1 且 old=0` 即达标；仓库级 `has_old` / `has_new` 取最近一次成功运行，仅用于明细展示。

## 3. 范围

### 3.1 范围内

- 主表以下指标改为仅统计成功运行：
  - PR 构建资源排队时长 P90
  - PR 测试资源排队时长 P90
  - PR 流水线 NPU 消耗、NPU 平均消耗
  - Nightly 流水线 NPU 消耗、NPU 平均消耗
  - 流水线整体 NPU 消耗、NPU 平均消耗
  - 由 NPU 消耗推导的 NPU 使用率
- 下层下钻同步：
  - 仓库级 PR 明细中的构建/测试排队 P90
  - 环境资源明细中的 PR/Nightly NPU 消耗、NPU 平均消耗、卡片汇总
  - 运行记录接口提供 `onlySuccess` 可选筛选（前端暂不接入，默认全量）
- Excel 导出表头对成功口径列标注“成功运行”
- 例外备案和 committer 审核一体化：
  - 过滤失败流水线
  - 查看截至统计日的最近 10 次成功 PR 流水线运行
  - **单次运行**满足 `has_new_codecheck = 1` 且 `has_old_codecheck = 0` 即视为该次运行达标；最近 10 次中任意一次达标，则仓库达标
- 指标字典文案同步。

### 3.2 范围外

- PR 执行时长 P90：当前已是 `COMPLETED` 口径，不调整计算逻辑。
- CPU 消耗、CPU 平均消耗、CPU 使用率：本次不调整，仍为全量运行口径。
- NPU 总量、NPU 使用（占用）卡时：属于资源容量/机器占用指标，不调整。
- Nightly 编译成功率、版本可用度：不调整。
- #294 的 run 级执行明细：单独设计，不在本文展开。

## 4. 口径定义

### 4.1 PR run 样本

主表 P90、仓库级 P90、环境资源明细统一使用以下样本定义：

1. `dwi_rd_efc_pr_info_sum` 关联桥表 `sdi_rd_efc_pipeline_run_pr_relation_codearts`，且 `pr_id IS NOT NULL`；
2. 关联 `dwr_rd_efc_pipeline_run_unified`，按 `pipeline_run_id` 去重；
3. 流水线归属项目通过 `sdi_repo_info` 解析，仅统计 `sdi_rd_efc_repo_operate_conf.is_operate = 1` 的运营仓；
4. GitHub run 仅保留 `dim_ecod_github_show_pr_config` 配置范围内的 workflow；
5. 时间按 run 统一表 `start_time` 过滤；
6. **新增：`status = 'COMPLETED'`**；
7. 时长/排队样本要求 `end_time IS NOT NULL`。

### 4.2 指标口径对照

| 指标/字段                  | 现状                 | 目标                                   | 说明                                                 |
| -------------------------- | -------------------- | -------------------------------------- | ---------------------------------------------------- |
| `prDurationP90`            | 成功运行             | 不变                                   | 本次仅校验一致性                                     |
| `buildQueueP90`            | 全部状态             | 成功运行                               | 每个 run 内 BUILD job 的 `MAX(job_pending_duration)` |
| `dtQueueP90`               | 全部状态             | 成功运行                               | 每个 run 内 DT job 的 `MAX(job_pending_duration)`    |
| `resourceQueueTime`        | 两项之和             | 自动跟随                               | 保持“分项各自 ROUND(2) 后相加”                       |
| `prNpuUsage`               | 全部状态             | 成功运行                               | 总量也改成功口径                                     |
| `prNpuAvg`                 | 全部状态             | 成功运行                               | 分母为成功且有 NPU 消耗的 run 数                     |
| `prNpuRate`                | 全量分子             | 成功分子 / 容量分母                    | 容量分母不变                                         |
| `nightlyNpuUsage/Avg/Rate` | 全部状态             | 成功运行                               | 同上                                                 |
| `overallNpuUsage/Avg/Rate` | 全部状态             | 成功运行                               | PR + Nightly 成功口径之和                            |
| CPU 系列                   | 全部状态             | 不变                                   | 避免扩大改动范围                                     |
| `exceptionReviewRate`      | ETL 最新一条运行 job | 最近 10 次成功运行中任一次仅含新版检查 | 详见 5.4                                             |

### 4.3 例外备案判定样本

- 统计日：`stat_date = D-1`，取数截止到 `D-1 23:59:59`（即 `start_time/created_at < D 00:00:00`）。
- 成功运行按平台定义：
  - GitCode：`dwr_rd_efc_pipeline_run_fact.pipeline_status = 'COMPLETED'`；
  - GitHub：`sdi_rd_efc_workflow_run_raw_github.conclusion = 'success'`。
- 每个仓库取截至截止时间的最近 10 次成功 PR 运行：
  - GitCode：桥表 `pr_id` 非空，按仓库取最近 10 次成功 pipeline run；
  - GitHub：`event in ('pull_request', 'pull_request_target')`，按仓库取最近 10 次成功 workflow run。
- 对最近 10 次运行**逐次**判定：
  - GitCode：job 名命中 `pre-commit` / `lintrunner` → `run_has_new_codecheck=1`；job 名含 `codecheck` 且不含 `pre-commit` / `lintrunner` → `run_has_old_codecheck=1`；
  - GitHub：workflow 名为 `Pre-Commit Check`，或 job 名命中 `pre-commit` / `lintrunner` → `run_has_new_codecheck=1`；GitHub 无旧版 codecheck，`run_has_old_codecheck=0`；
  - 单次运行达标条件：`run_has_new_codecheck=1` 且 `run_has_old_codecheck=0`。
- 仓库级达标：最近 10 次中**任意一次运行**满足上述条件，即 `uses_proper_codecheck = 1`。
- 仓库级 `has_old_codecheck`、`has_new_codecheck` 及 job 明细：取最近一次成功运行的判定结果，用于明细展示。
- 成功运行不足 10 次时，按实际条数计算；一条成功运行都没有时：
  - `has_old_codecheck` / `has_new_codecheck` / job 明细置 `NULL`；
  - `uses_proper_codecheck` 写 `0`，仍计入项目级分母（与现网 `pipeline_agg` 的 `COUNT(*)` 口径一致）。

判定规则：

- 新版检查：
  - GitCode：`job_name` 命中 `pre-commit` 或 `lintrunner`；
  - GitHub：`workflow_name = 'Pre-Commit Check'`，或 `job_name` 命中 `pre-commit` / `lintrunner`。
- 旧版检查：仅 GitCode 适用，`job_name` 含 `codecheck`，且不含 `pre-commit` / `lintrunner`；GitHub `has_old_codecheck` 恒 0。
- job 判定不额外过滤 `job_status` / `conclusion`，只要求所属流水线/ workflow 运行成功；该次运行中存在对应任务即计入。
- 注意：`run_has_old_codecheck` 是“单次运行内”的字段，不再表示“最近 10 次中是否出现过旧版检查”。某次运行同时存在新旧检查时，该次运行不达标，但不影响其他仅含新版检查的运行达标。

## 5. 详细设计

### 5.1 主表：OpsMainStatMapper.xml

文件：`openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`

#### 5.1.1 排队 P90 改为成功口径

`pr_run_sample` 同时被 `p90_stat` 和 `queue_stat` 消费。PR 执行时长本来就要求成功，因此在样本 CTE 中统一增加状态过滤即可：

```sql
pr_run_sample AS (
    SELECT DISTINCT
        sd.project_id,
        u.pipeline_run_id,
        u.status,
        u.duration_ms,
        u.end_time
    FROM ...
    WHERE u.start_time >= #{req.startTime}
      AND u.start_time <= #{req.endTime}
      AND u.status = 'COMPLETED'          -- 新增：统一成功口径
      AND (
          u.platform != 'github'
          OR EXISTS (...)
      )
)
```

同步修改：

- `queue_stat` 内部 `WHERE s.end_time IS NOT NULL` 保留；
- 更新 CTE 与方法注释，删除“排队时长不过滤 pipeline_status”的描述；
- `p90_stat` 内已有的 `status = 'COMPLETED'` 可保留，作为防御性过滤。

影响字段：

- `build_queue_p90`
- `dt_queue_p90`
- `resource_queue_time`（两项之和，自动变化）

#### 5.1.2 NPU 消耗与平均改为成功口径

`unified_npu_stat` 的 PR 分支和 Nightly 分支都增加：

```sql
AND u.status = 'COMPLETED'
```

PR 分支示例：

```sql
FROM dwr_rd_efc_pipeline_run_unified u
INNER JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
    ON u.pipeline_id = r.pipeline_id
   AND u.pipeline_run_id = r.pipeline_run_id
INNER JOIN dm_rd_efc_project_pipeline_relation rel
    ON rel.pipeline_id = u.pipeline_id
   AND rel.pipeline_type = 'PR'
INNER JOIN sdi_repo_info si
    ON r.git_url = si.repo_url
WHERE u.start_time >= #{req.startTime}
  AND u.start_time <= #{req.endTime}
  AND u.status = 'COMPLETED'          -- 新增
  AND r.pr_id IS NOT NULL
  AND si.repo_id IN (...)
```

Nightly 分支同样增加 `u.status = 'COMPLETED'`。

由于该 CTE 同时产出消耗和运行次数，修改后以下字段全部变为成功口径：

| 字段                                                        | 变化                           |
| ----------------------------------------------------------- | ------------------------------ |
| `pr_npu_usage`                                              | 成功运行 NPU 卡时之和          |
| `pr_run_count`                                              | 成功且有 NPU 消耗的 run 数     |
| `pr_npu_avg`                                                | `pr_npu_usage / pr_run_count`  |
| `nightly_npu_usage`、`nightly_run_count`、`nightly_npu_avg` | 同上                           |
| `overall_npu_usage`、`overall_npu_avg`                      | PR + Nightly 成功口径          |
| `pr_npu_rate`、`nightly_npu_rate`、`overall_npu_rate`       | 分子变为成功口径，容量分母不变 |

注意：

- `pr_cpu_usage`、`pr_cpu_avg`、`nightly_cpu_*`、`overall_cpu_*` 来自其他 CTE，不受影响。
- `pr_npu_total`、`overall_npu_total`、`npu_all_assigned_hours` 不调整。

### 5.2 仓库级下钻：OpsRepoDetailMapper.xml

文件：`openlibing-ops/src/main/resources/mapper/OpsRepoDetailMapper.xml`

`pr_run_sample` 增加状态过滤：

```sql
WHERE u.start_time >= #{req.startTime}
  AND u.start_time <= #{req.endTime}
  AND u.status = 'COMPLETED'          -- 新增
  AND u.pipeline_id IN (...)
```

影响：

- `queue_p90` 的 `build_pending_p90`、`dt_pending_p90` 变为成功口径；
- `resource_queue_time`、`build_queue_p90`、`dt_queue_p90` 自动跟随；
- `e2e_p90` 本来只取 `COMPLETED`，逻辑不变。

行集不变：仍按运营仓返回仓库列表，避免无成功运行的仓库整行消失；其排队字段为 `NULL`，前端展示 `--`。

### 5.3 环境资源下钻：OpsResourceDetailMapper.xml

文件：`openlibing-ops/src/main/resources/mapper/OpsResourceDetailMapper.xml`

该接口同时承载 CPU 和 NPU 字段。为避免误改 CPU 口径，**不能对整段样本直接加状态过滤**，而是对 NPU 做条件聚合。

#### 5.3.1 PR / Nightly 流水线列表

内层样本增加 `u.status` 字段，聚合改为：

```sql
SUM(t.cpu_second) / 3600 AS vcpu,                                    -- CPU 保持全量
SUM(CASE WHEN t.status = 'COMPLETED'
         THEN t.npu_second END) / 3600 AS npu,                       -- NPU 成功口径
COUNT(*) AS run_count,                                                -- CPU 均值分母，保持全量
COUNT(DISTINCT CASE WHEN t.status = 'COMPLETED' AND t.npu_second > 0
                    THEN t.pipeline_run_id END) AS npu_run_count      -- NPU 均值分母
```

输出改为：

```sql
p.vcpu / NULLIF(p.run_count, 0) AS vcpu_avg,        -- 不变
p.npu  / NULLIF(p.npu_run_count, 0) AS npu_avg      -- 改为成功 NPU 运行数
```

Nightly 分支做同样处理。

行集与 `countResourceDetailList` 保持不变，仍返回窗口内有运行的流水线；没有成功运行的流水线 NPU 展示为空，便于发现异常。这样：

- CPU 字段行为不变；
- 列表 NPU 汇总与主表 `prNpuUsage` / `nightlyNpuUsage` 可对账；
- 流水线级 `npuAvg` 分母与主表口径一致。

#### 5.3.2 环境资源卡片汇总

`queryResourceSummary` 的 PR / Nightly 分支同样改为条件聚合：

```sql
SUM(t.cpu_second) / 3600 AS total_vcpu,
SUM(CASE WHEN t.status = 'COMPLETED' THEN t.npu_second END) / 3600 AS total_npu,
COUNT(*) AS run_count,
COUNT(DISTINCT CASE WHEN t.status = 'COMPLETED' AND t.npu_second > 0
                    THEN t.pipeline_run_id END) AS npu_run_count
```

- `total_vcpu_avg = total_vcpu / run_count`，不变；
- `total_npu_avg = total_npu / npu_run_count`，随成功口径变化。

#### 5.3.3 旧查询同步

`queryResourceDetail` 当前未在接口链路中使用，但为避免后续误用，建议同步增加 `status` 字段与 NPU 条件聚合。

#### 5.3.4 运行记录列表

`OpsResourceRunMapper.queryResourceRuns` 默认保留全量运行记录，并提供 `onlySuccess` 可选接口参数：

- 默认 `onlySuccess=false`，展示全量运行，便于定位失败运行；
- 接口层支持 `onlySuccess=true` 时只返回 `status='COMPLETED'` 的运行；
- 前端运行记录弹窗本次不修改，默认仍展示全量；
- 每行展示单次真实 NPU 消耗，并已有 `status` 列；
- 运行记录是明细事实，默认不与成功口径 KPI 直接求和；调用方传 `onlySuccess=true` 时可用于对账。

`onlySuccess` 同时作用于列表和 count SQL，保证分页总数一致。

### 5.4 例外备案 ETL 改造

涉及表：

- `dwi_repo_pipeline_quality_day`
- `dm_project_quality_overview_day`
- 下游接口自动生效：
  - 主表 `exceptionReviewRate`
  - 仓库级 `usesProperCodecheck`、`codecheckDetail`

#### 5.4.1 仓库级判定

**现状 SQL 问题（附件）**

1. GitCode `latest_pr_run` 只取每个仓库最新一次运行，未过滤 `dwr_rd_efc_pipeline_run_fact.pipeline_status`，失败运行参与判定。
2. GitCode `has_new_codecheck` 使用 `MIN` 跨 pipeline 聚合，要求所有 pipeline 都有新版；与“最近 10 次中任一次单次运行达标”冲突。
3. GitCode 用 `LOWER(r.pipeline_name) LIKE 'pr-pipeline%'` 识别 PR，与主表/后端的桥表 `pr_id` + relation 口径不一致。
4. `dwi_rd_efc_pipeline_info` 使用 INNER JOIN，与注释“保留不在该表中的 pipeline”不一致；不在表中的 pipeline 会被丢弃。
5. GitHub `github_pr_workflow_latest` 只取每个 workflow 最新一次运行，未过滤 `conclusion`，没有最近 10 次概念。
6. `all_keys` 使用 `CURRENT_DATE()`，没有按 D-1 统计。
7. `INSERT` 使用 `COALESCE(uses_proper_codecheck, 0)`，项目级 `COUNT(*)` 统计全部运营仓库；无成功运行仓库按不达标 0 计。原文档“NULL 不参与分母”与现网 SQL 不一致，需修正。

**目标口径**

- GitCode 成功：`dwr_rd_efc_pipeline_run_fact.pipeline_status = 'COMPLETED'`。
- GitHub 成功：`sdi_rd_efc_workflow_run_raw_github.conclusion = 'success'`。
- 每个仓库取截至 `D-1 23:59:59` 的最近 10 次成功 PR 运行。
- 单次运行达标：GitCode `new=1 且 old=0`；GitHub `old=0`，命中 pre-commit/lintrunner 或 workflow 名为 `Pre-Commit Check`。
- 仓库 `uses_proper_codecheck`：最近 10 次中任一次单次达标。
- 仓库 `has_old/new`、job 明细取最近一次成功运行；无成功运行时 flag NULL、`uses_proper=0`，仍计入分母。

**GitCode 改造要点**

```sql
-- 1) 替换 latest_pr_run：最近 10 次成功 PR run
gitcode_recent_run AS (
    SELECT ..., p.pipeline_run_id,
           ROW_NUMBER() OVER (
               PARTITION BY rp.repo_id
               ORDER BY p.pipeline_start_time DESC, p.pipeline_run_id DESC
           ) AS rn
    FROM sdi_repo_info rp
    JOIN dwi_rd_efc_pr_info_sum pr ON rp.repo_url = pr.repo_url
    JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
        ON pr.repo_url = r.git_url AND pr.number = r.pr_id
    JOIN dwr_rd_efc_pipeline_run_fact p
        ON p.pipeline_id = r.pipeline_id AND p.pipeline_run_id = r.pipeline_run_id
    LEFT JOIN dwi_rd_efc_pipeline_info pi ON pi.pipeline_id = p.pipeline_id
    CROSS JOIN params ps
    WHERE rp.platform = 'gitcode'
      AND r.pr_id IS NOT NULL
      AND p.pipeline_status = 'COMPLETED'
      AND p.pipeline_start_time < DATE_ADD(ps.stat_date, INTERVAL 1 DAY)
      AND COALESCE(pi.is_deleted, 0) != 1
)
-- 外层 WHERE rn <= 10

-- 2) job 明细按 run 聚合（dwr_rd_efc_pipeline_run_job_fact）
-- 3) 仓库聚合：
--    uses_proper = MAX(CASE WHEN run_has_new=1 AND run_has_old=0 THEN 1 ELSE 0 END)
--    has_old/new、old/new jobs 取 rn=1 的最近成功运行
```

- 删除 `LOWER(r.pipeline_name) LIKE 'pr-pipeline%'`，以桥表 `pr_id` 为准。
- `pipeline_info` 改 LEFT JOIN，保留不在表中的 pipeline。
- `pipeline_codecheck` 分组键改为 `project_id, repo_id, pipeline_id, pipeline_run_id, rn`。
- 不再使用跨 pipeline 的 `MIN(has_new)`。

**GitHub 改造要点**

```sql
-- 1) 替换 github_pr_workflow_latest：最近 10 次成功 PR workflow run
github_recent_run AS (
    SELECT w.repo_url, w.run_id AS workflow_run_id, w.name AS workflow_name,
           ROW_NUMBER() OVER (
               PARTITION BY w.repo_url
               ORDER BY w.created_at DESC, w.run_id DESC
           ) AS rn
    FROM sdi_rd_efc_workflow_run_raw_github w
    JOIN github_repo_base rb ON rb.repo_url = w.repo_url
    CROSS JOIN params ps
    WHERE w.event IN ('pull_request', 'pull_request_target')
      AND w.conclusion = 'success'
      AND w.created_at < DATE_ADD(ps.stat_date, INTERVAL 1 DAY)
)
-- 外层 WHERE rn <= 10

-- 2) 每次运行检查 workflow 名或 job 名
-- 3) 仓库聚合：
--    uses_proper = MAX(run_has_new)
--    has_old = 0
--    has_new/new jobs 取 rn=1 的最近成功运行
```

- 不再只取每个 workflow 最新 run，也不再只按最新 run 判存在性。
- GitHub 无旧版 codecheck，`has_old_codecheck` 恒 0。
- 无成功 PR workflow 运行时，flag NULL、`uses_proper=0`。

**合并与写入**

- `codecheck_result_all` = GitCode 结果 UNION ALL GitHub 结果。
- `all_keys` 的 `stat_date` 改为 D-1（`DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)` 或调度参数）。
- 插入保持 `COALESCE(cc.uses_proper_codecheck, 0)`，无成功运行仓库按 0 计入项目分母。

通用伪 SQL（概念参考，实际 ETL 按上述平台表拆分）：

```sql
WITH pr_run AS (
    SELECT DISTINCT
        sd.project_id,
        sd.repo_id,
        u.pipeline_run_id,
        u.start_time
    FROM sdi_rd_efc_pipeline_run_pr_relation_codearts r
    INNER JOIN dwr_rd_efc_pipeline_run_unified u
        ON u.pipeline_id = r.pipeline_id
       AND u.pipeline_run_id = r.pipeline_run_id
    INNER JOIN sdi_repo_info sd
        ON sd.repo_url = r.git_url
    WHERE r.pr_id IS NOT NULL
      AND u.status = 'COMPLETED'
      AND sd.repo_id IN (
          SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1
      )
      AND u.start_time < DATE_ADD(#{statDate}, INTERVAL 1 DAY)
),
recent_run AS (
    SELECT repo_id, pipeline_run_id, rn
    FROM (
        SELECT
            repo_id,
            pipeline_run_id,
            ROW_NUMBER() OVER (
                PARTITION BY repo_id
                ORDER BY start_time DESC, pipeline_run_id DESC
            ) AS rn
        FROM pr_run
    ) t
    WHERE rn <= 10
),
run_flag AS (
    SELECT
        c.repo_id,
        c.pipeline_run_id,
        c.rn,
        MAX(CASE WHEN LOWER(j.job_name) REGEXP 'pre-commit|lintrunner'
                 THEN 1 ELSE 0 END) AS run_has_new_codecheck,
        MAX(CASE WHEN LOWER(j.job_name) REGEXP 'codecheck'
                  AND NOT LOWER(j.job_name) REGEXP 'pre-commit|lintrunner'
                 THEN 1 ELSE 0 END) AS run_has_old_codecheck,
        GROUP_CONCAT(DISTINCT CASE
            WHEN LOWER(j.job_name) REGEXP 'pre-commit|lintrunner'
            THEN j.job_name END) AS new_codecheck_jobs,
        GROUP_CONCAT(DISTINCT CASE
            WHEN LOWER(j.job_name) REGEXP 'codecheck'
             AND NOT LOWER(j.job_name) REGEXP 'pre-commit|lintrunner'
            THEN j.job_name END) AS old_codecheck_jobs
    FROM recent_run c
    LEFT JOIN dwr_rd_efc_pipeline_run_job_unified j
        ON j.pipeline_run_id = c.pipeline_run_id
    GROUP BY c.repo_id, c.pipeline_run_id, c.rn
),
repo_compliance AS (
    SELECT
        repo_id,
        MAX(CASE WHEN run_has_new_codecheck = 1 AND run_has_old_codecheck = 0
                 THEN 1 ELSE 0 END) AS uses_proper_codecheck
    FROM run_flag
    GROUP BY repo_id
),
latest_flag AS (
    SELECT
        repo_id,
        run_has_old_codecheck,
        run_has_new_codecheck,
        old_codecheck_jobs,
        new_codecheck_jobs
    FROM run_flag
    WHERE rn = 1
)
SELECT
    repo.repo_id,
    latest_flag.run_has_old_codecheck AS has_old_codecheck,
    latest_flag.run_has_new_codecheck AS has_new_codecheck,
    latest_flag.old_codecheck_jobs,
    latest_flag.new_codecheck_jobs,
    CASE
        WHEN latest_flag.repo_id IS NULL THEN NULL
        ELSE IFNULL(comp.uses_proper_codecheck, 0)
    END AS uses_proper_codecheck
FROM operate_repo_dim repo
LEFT JOIN latest_flag ON latest_flag.repo_id = repo.repo_id
LEFT JOIN repo_compliance comp ON comp.repo_id = repo.repo_id
```

实现要求：

1. 成功运行按平台判定：GitCode 取 `pipeline_status='COMPLETED'`；GitHub 取 `conclusion='success'`；失败、取消、忽略、运行中均不参与。
2. 每个仓库取截至 `D-1 23:59:59` 的最近 10 次成功 PR 运行：GitCode 以桥表 `pr_id IS NOT NULL` 为准，GitHub 限定 `event in ('pull_request','pull_request_target')`；同一 run 关联多个 PR 时按 `pipeline_run_id` 去重。
3. **按单次运行计算** `run_has_new_codecheck`、`run_has_old_codecheck`；GitCode 单次运行同时存在新旧检查时该次不达标；GitHub 无旧版检查，`run_has_old_codecheck=0`。
4. 仓库级 `uses_proper_codecheck`：最近 10 次中任意一次运行满足 `run_has_new_codecheck = 1 AND run_has_old_codecheck = 0`，即为 1；否则为 0。
5. 仓库级 `has_old_codecheck`、`has_new_codecheck`、`old_codecheck_jobs`、`new_codecheck_jobs`：取最近一次成功运行（`rn = 1`）的结果，用于明细展示。
6. 成功运行不足 10 次时按实际条数计算；一条成功运行都没有时，上述字段全部写 `NULL`，`uses_proper_codecheck` 写 `0`，仍计入项目级分母。
7. 需要将 `uses_proper_codecheck` 作为独立字段写入 `dwi_repo_pipeline_quality_day`，不能再由仓库级 `has_old_codecheck` / `has_new_codecheck` 简单推导。
8. GitCode 删除 `pipeline_name LIKE 'pr-pipeline%'` 过滤，`dwi_rd_efc_pipeline_info` 改 LEFT JOIN；GitHub 不再按 workflow 只取最新一次运行。

复用 `dwi_repo_pipeline_quality_day` 现有字段，无 DDL 变更。

#### 5.4.2 项目级聚合

目标公式：

```text
exception_review_rate =
    达标仓库数（uses_proper_codecheck = 1）
    /
    全部运营仓库数（dwi_repo_pipeline_quality_day 中运营仓库行数）
```

说明：

- 分母保持现网 `pipeline_agg` 的 `COUNT(*)` 口径，即全部运营仓库，不因“无成功运行”而排除。
- 无成功运行仓库在 DWI 层写 `uses_proper_codecheck=0`，作为不达标计入分母。
- 如果 `dwi_repo_pipeline_quality_day` 不能保证 `(project_id, repo_id, stat_date)` 唯一，建议将分母改为 `COUNT(DISTINCT rp.repo_id)`，避免重复计数。
- 上线前必须用样例项目对比现网值，差异需产品确认。

#### 5.4.3 后端消费调整

由于 `uses_proper_codecheck` 变为“最近 10 次中任意一次单次运行达标”，不能再由仓库级
`has_old_codecheck` / `has_new_codecheck` 简单推导，需要调整仓库级明细 SQL：

文件：`openlibing-ops/src/main/resources/mapper/OpsRepoDetailMapper.xml`

1. `uses_proper_codecheck` 直接读取 ETL 字段：

```sql
CASE WHEN pr.repo_id IS NULL THEN NULL
     ELSE p.uses_proper_codecheck
END AS uses_proper_codecheck
```

2. `codecheck_detail` 优先判断 `uses_proper_codecheck`：

```sql
CASE WHEN pr.repo_id IS NULL THEN '--'
     WHEN IFNULL(p.uses_proper_codecheck, 0) = 1 THEN NULL
     WHEN IFNULL(p.has_old_codecheck, 0) = 1 AND IFNULL(p.has_new_codecheck, 0) = 1
          THEN '存在旧版codecheck任务，同时已配置新版检查，需下线旧版任务'
     WHEN IFNULL(p.has_old_codecheck, 0) = 1
          THEN '仅存在旧版codecheck任务，需下线旧版任务并配置pre-commit或lintrunner'
     ELSE '未配置新版检查任务，需新增pre-commit或lintrunner任务'
END AS codecheck_detail
```

3. 同步更新响应字段注释：
   - `usesProperCodecheck`：“最近 10 次成功 PR 运行中任意一次仅配置新版检查即为 1”；
   - `hasOldCodecheck` / `hasNewCodecheck`：“最近一次成功 PR 运行的检查任务情况，仅用于明细展示”。

这样仓库级明细与项目级率使用同一个 `uses_proper_codecheck`，避免两套推导逻辑不一致。

### 5.5 指标字典与文案

需要同步更新指标定义/统计规则：

| 指标                            | 修改点                                                                                                   |
| ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 例外备案和committer审核一体化率 | 删除“仅统计最新一次运行”，改为“最近 10 次成功 PR 运行中，任意一次同时满足新版检查存在且旧版不存在即达标” |
| NPU消耗(卡时)                   | 统计范围改为成功运行                                                                                     |
| NPU平均消耗(卡时)               | 分子分母均改为成功运行；说明分母为有 NPU 消耗的成功运行数                                                |
| PR资源排队时长                  | 统计范围改为成功运行                                                                                     |
| PR构建/测试资源排队时长 P90     | 统计范围改为成功运行                                                                                     |

前端指标提示通过指标字典下发，无需改前端代码；如字典未更新，页面提示会与真实口径不一致。

## 6. 数据一致性校验

### 6.1 队列 P90

- 主表项目级 P90：对项目下全部成功 PR run 的 run 级 `build_pd` / `dt_pd` 直接取 P90。
- 仓库级 P90：按仓库分别取 P90，**不能通过平均仓库 P90 还原项目 P90**。
- 一致性要求：两层使用同一状态过滤和同一 job 聚合方式。

验证 SQL 示例：

```sql
SELECT
    PERCENTILE(t.build_pd, 0.9) / 60.0 AS success_build_p90,
    PERCENTILE(CASE WHEN s.status != 'COMPLETED' THEN t.build_pd END, 0.9) / 60.0 AS failed_build_p90
FROM (
    SELECT
        s.project_id,
        s.pipeline_run_id,
        s.status,
        MAX(CASE WHEN j.job_type = 'BUILD' THEN j.job_pending_duration END) AS build_pd
    FROM pr_run_sample s
    INNER JOIN dwr_rd_efc_pipeline_run_job_unified j
        ON j.pipeline_run_id = s.pipeline_run_id
    GROUP BY s.project_id, s.pipeline_run_id, s.status
) t
```

### 6.2 NPU

- 主表 `prNpuUsage` = 环境资源明细 PR 列表 `npu` 之和。
- 主表 `prNpuAvg` = `SUM(npu) / SUM(npu_run_count)`，不是各流水线 `npuAvg` 的简单平均。
- Nightly、整体同理。

验证 SQL 示例：

```sql
SELECT
    SUM(CASE WHEN status = 'COMPLETED' THEN npu_second END) / 3600 AS success_npu,
    SUM(npu_second) / 3600 AS all_npu,
    COUNT(DISTINCT CASE WHEN status = 'COMPLETED' AND npu_second > 0
                        THEN pipeline_run_id END) AS success_npu_run_count
FROM dwr_rd_efc_pipeline_run_unified
WHERE ...
```

### 6.3 例外备案

- 项目级 `exception_review_rate` = 达标仓库数 / 全部运营仓库数，与 `pipeline_agg` 的 `COUNT(*)` 一致。
- 仓库级 `usesProperCodecheck` 必须直读 ETL 的达标结果；`codecheckDetail` 必须先判断 `usesProperCodecheck`，达标时不得再展示旧版告警。
- 重点验证场景：
  1. 最新一次运行失败，但最近 10 次成功运行中存在一次仅新版检查，应判定达标；
  2. 最近 10 次中一次为旧版检查、另一次为仅新版检查，应判定达标（按单次运行取并集）；
  3. 最近 10 次中每次运行都同时存在旧版和新版检查，应判定不达标；
  4. 最近 10 次全部只有旧版检查或均无检查任务，应判定不达标；
  5. 成功运行不足 10 次，按实际条数判定；
  6. 仓库从未有成功运行，flag 为 NULL、`uses_proper=0`，仍计入项目级分母；
  7. 仓库已达标但最近一次运行仍含旧版任务时，`codecheckDetail` 应为空，不展示旧版告警；
  8. GitHub 仓库无旧版 codecheck，最近 10 次成功 workflow 运行中任一命中 pre-commit/lintrunner 即达标。

## 7. 影响面

| 层           | 文件/对象                                                                   | 变更                                                                                                     |
| ------------ | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 主表 SQL     | `OpsMainStatMapper.xml`                                                     | `pr_run_sample` 增加成功过滤；`unified_npu_stat` 两个分支增加成功过滤                                    |
| 仓库下钻 SQL | `OpsRepoDetailMapper.xml`                                                   | `pr_run_sample` 增加成功过滤；`uses_proper_codecheck` 改为直读 ETL 字段；`codecheck_detail` 优先判断达标 |
| 仓库响应注释 | `OpsRepoDetailResp.java`、`OpsRepoDetailDetailResp.java`                    | 更新 `usesProperCodecheck` 口径说明                                                                      |
| 资源下钻 SQL | `OpsResourceDetailMapper.xml`                                               | PR/Nightly 列表、汇总、旧查询改为 NPU 条件聚合                                                           |
| 主表响应     | `OpsOverviewMainResp.java`                                                  | 数值口径变化；字段注释更新；Excel 表头标注“成功运行”                                                     |
| 资源响应     | `OpsResourceSummaryResp`、`OpsResourceDetailDetailResp`                     | 无结构变化，数值口径变化                                                                                 |
| 运行记录接口 | `OpsResourceRunReq`、`OpsResourceRunsDetailReq`、`OpsResourceRunMapper.xml` | 新增 `onlySuccess` 可选筛选，列表与 count 同步                                                           |
| ETL          | `dwi_repo_pipeline_quality_day`                                             | 重写例外备案 flag 判定                                                                                   |
| ETL          | `dm_project_quality_overview_day`                                           | 项目级达标率按新 flag 聚合                                                                               |
| 指标字典     | `openlibing-metric`                                                         | 更新相关指标定义与统计范围                                                                               |
| 前端         | `openlibing-ops-web`                                                        | 无代码改动；指标提示随字典变化                                                                           |

接口契约不变：

- `POST /ops-overview/main`
- `POST /ops-overview/resource-summary`
- `POST /common/detail`（`category=ops-repo-detail`、`ops-resource-detail`）

## 8. 测试方案

### 8.1 SQL / 数据验证

选取项目：`2、4、300036、300037、300091`，日期：`2026-10-20 ~ 2026-10-23`。

1. 对比修改前后的排队 P90、NPU 消耗、NPU 平均、NPU 使用率；
2. 验证主表与仓库级、资源级明细可对账；
3. 验证 CPU 字段与 PR 执行时长数值不变；
4. 验证失败运行确实被剔除，成功运行样本数符合预期；
5. 对例外备案逐仓库核对 job 命中情况，重点覆盖 6.3 的五类场景。

### 8.2 后端质量门禁

```bash
mvn spotless:apply
mvn checkstyle:check
mvn spotbugs:check
mvn pmd:check
mvn test
```

本次以 XML 改动为主，仍需保证现有单元测试通过；新增的 SQL 逻辑通过数据验证脚本覆盖。

### 8.3 页面验证

1. 主表 PR 构建/测试排队 P90 与旧值对比，确认变化方向合理；
2. 主表 PR/Nightly/整体 NPU 消耗、平均、使用率同步变化；
3. PR Tab 仓库明细排队 P90 与主表口径一致；
4. 资源环境 Tab 的 PR/Nightly 卡片与列表 NPU 可对账；
5. 导出 Excel 数值与页面一致；
6. 指标提示文案已更新。

### 8.4 性能验证

- 对主表接口执行 `EXPLAIN` / `Profile`，确认新增状态过滤未导致扫描量异常；
- 对资源明细接口验证 NPU 条件聚合耗时；
- 关注 `dwr_rd_efc_pipeline_run_job_unified` 的大范围扫描，保持现有时间范围限制。

## 9. 风险与发布

| 风险                       | 说明                                                 | 应对                                          |
| -------------------------- | ---------------------------------------------------- | --------------------------------------------- |
| 指标数值整体下降           | 剔除失败运行后，排队 P90、NPU 消耗/平均/使用率会变化 | 提前同步看板使用方，发布说明中标注口径变化    |
| ETL 与本仓库发布不同步     | 例外备案率在 ETL 侧生效                              | 明确 ETL 任务发布时间，后端发布前完成数据核对 |
| 项目级例外备案分母不一致   | 现网分母公式可能与仓库级 flag 集合不一致             | 数据侧确认公式，样例项目对比后再上线          |
| CPU 被误改                 | 资源明细同时含 CPU/NPU                               | 使用条件聚合，CPU 保持全量；回归验证 CPU 不变 |
| 无成功运行的流水线展示为空 | 行集保留，NPU 列为空                                 | 前端展示 `--`，并保留运行记录用于定位         |
| 历史数据未回刷             | 旧日期仍为旧口径                                     | 明确是否回刷最近 N 天；默认只对新日期生效     |

## 10. 任务拆分

| #   | 任务                                       | 涉及对象                                                  | 依赖   |
| --- | ------------------------------------------ | --------------------------------------------------------- | ------ |
| T1  | 主表排队 P90 成功口径                      | `OpsMainStatMapper.xml`                                   | 无     |
| T2  | 主表 NPU 消耗/平均/使用率成功口径          | `OpsMainStatMapper.xml`                                   | 无     |
| T3  | 仓库级排队 P90 成功口径 + 例外备案结果消费 | `OpsRepoDetailMapper.xml`、两个 `OpsRepoDetail*Resp` 注释 | T1、T5 |
| T4  | 资源明细 NPU 条件聚合                      | `OpsResourceDetailMapper.xml`                             | T2     |
| T5  | 例外备案仓库级判定重写                     | DolphinScheduler ETL                                      | 无     |
| T6  | 例外备案项目级聚合调整                     | DolphinScheduler ETL                                      | T5     |
| T7  | 指标字典与文案更新                         | `openlibing-metric` / 指标平台                            | 无     |
| T8  | 数据核对与回归验证                         | Doris / 页面                                              | T1-T7  |

建议发布顺序：

1. T1-T4 后端 SQL；
2. T5-T6 ETL；
3. T7 指标字典；
4. T8 数据核对与页面验收。

## 11. 假设与待确认

1. 成功运行仅指 `COMPLETED`，`IGNORED`、`CANCELED`、`RUNNING`、`INIT` 均不算成功。
2. 例外备案按 `stat_date = D-1` 取数，截止到 `D-1 23:59:59`。
3. 每个仓库统一查看截至截止时间的最近 10 次成功 PR 运行，不再区分“当天窗口”和“兜底窗口”。
4. 最近 10 次中只要有一次运行同时满足“新版检查存在且旧版检查不存在”即达标；某次运行同时存在新旧检查只影响该次运行，不影响其他仅新版运行达标。
5. 仓库级 `has_old_codecheck` / `has_new_codecheck` / job 明细取最近一次成功运行，仅用于明细展示；达标判定以独立的 `uses_proper_codecheck` 为准。
6. 项目级例外备案分母为“有成功运行、flag 非空的仓库数”；如现网定义不同，需产品确认后再冻结。
7. 运行记录列表默认展示全量；接口提供 `onlySuccess` 可选筛选，前端本次不接入。
8. 历史数据默认不回刷；如需回刷，建议至少覆盖最近 7 天并重新核对主表快照。
