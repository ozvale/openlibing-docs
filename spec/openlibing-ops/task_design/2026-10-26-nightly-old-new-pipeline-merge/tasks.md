# Nightly 流水线新旧切换历史数据合并 - 开发任务清单

- 关联 Issue：https://gitcode.com/openlibing/openlibing-ops/issues/289
- 需求设计文档：`design.md`
- 最终建表语句：`docs/table.sql`
- 目标仓库：`openlibing-ops`、`openlibing-docs`
- 编写日期：2026-10-27

---

## 1. 开发前提

- `dm_rd_efc_project_pipeline_relation` 的 `NIGHTLY` 识别默认正确，本次不修改 relation 任务。
- 逻辑运行表、逻辑日汇总表都按现有 DM 表方式全量刷新，不做增量。
- 映射表当前人工维护，不做自动生成。
- 工程能力运营看板只展示到昨天，允许预聚合滞后。
- 日汇总宽表只存分子/分母，率字段由查询 SQL 计算。

---

## 2. 数据库任务

### 2.1 新建表

- [ ] 新建 `dm_rd_efc_nightly_pipeline_alias`
  - 字段：`project_id`、`pipeline_project`、`platform`、`pipeline_id`、`logical_pipeline_id`、`logical_pipeline_name`、`valid_from`、`valid_to`
  - 唯一键：`(project_id, pipeline_project, platform, pipeline_id)`
- [ ] 新建 `dm_rd_efc_nightly_pipeline_logical_run`
  - 唯一键：`(project_id, pipeline_project, platform, pipeline_id, pipeline_run_id, run_date)`
  - 不做分区
- [ ] 新建 `dm_rd_efc_nightly_pipeline_logical_day`
  - 唯一键：`(project_id, pipeline_project, platform, logical_pipeline_id, run_date)`
  - 不做分区

### 2.2 初始化映射数据

- [ ] 根据已切换的 Nightly 流水线，手工写入 `dm_rd_efc_nightly_pipeline_alias`
- [ ] 每条记录填写 `pipeline_project` 和 `logical_pipeline_name`
- [ ] 每条逻辑流水线写入所有实际 ID：
  - 旧 ID：`valid_from = 1970-01-01`，`valid_to = 切换时间`
  - 中间 ID：`valid_from = 上一次切换时间`，`valid_to = 下一次切换时间`
  - 当前新 ID：`valid_from = 最后一次切换时间`，`valid_to = 9999-12-31`
- [ ] 校验区间连续、无重叠、无空洞

---

## 3. DolphinScheduler 任务

项目：`openlibing`（`169400948446944`），环境：`prod`，数据源：Doris（datasource id `1`）。

### 3.1 改动总览

| 工作流（code）                                                                                      | 任务（code）                                                                                                                                       | 动作                                       |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `[job][raw->dwi][codearts]工程能力看板汇聚PR和Nightly资源消耗`（`177530921784672`）                 | `Nightly流水线资源消耗日聚合`（`177531009881440`）                                                                                                 | 改 SQL：Nightly 资源改读逻辑日汇总宽表     |
| `[job][raw->dwi][codearts]工程能力看板汇聚PR和Nightly资源消耗`（`177530921784672`）                 | `工程能力看板数据汇总（流水线资源消耗 + 开源项目资源使用率 + 编译成功率 + 版本可用度）`（`177531067754848`）                                       | 改 SQL：`nightly_stats` 改读逻辑日汇总宽表 |
| `[job][dm][nightly]逻辑流水线数据构建`（新建）                                                      | `[dm]Nightly逻辑运行事实表全量刷新`（新建）                                                                                                        | 新增 SQL 任务                              |
| `[job][dm][nightly]逻辑流水线数据构建`（新建）                                                      | `[dm]Nightly逻辑日汇总宽表全量刷新`（新建）                                                                                                        | 新增 SQL 任务                              |
| `[job][dwi->dwr][codearts]Nightly流水线测试用例执行事实表（每条执行记录一行）`（`169496639078592`） | `[dwr]dwr_rd_efc_build_fact_nightly_test_case_pipeline_run`（`169496639079616`）                                                                   | 不改，作为新任务上游                       |
| `[job][dwr->dm][codearts]nightly流水线每日汇总`（`169496639269056`）                                | `[dm]dm_rd_efc_build_dim_test_case_nightly_pipeline_day`（`169496639269057`）、`[dm]dm_rd_efc_build_dim_nightly_pipeline_day`（`169496639269058`） | 不改，保留运行；查询层全部切换后再评估下线 |
| `[job][base]项目与流水线关联关系生成`（`182739749033248`）                                          | 同工作流 SQL 任务                                                                                                                                  | 不改，alias 依赖它生成的 relation          |

### 3.2 新建工作流与任务

- [ ] 新建工作流 `[job][dm][nightly]逻辑流水线数据构建`
- [ ] 任务 1：`[dm]Nightly逻辑运行事实表全量刷新`，SQL 类型，Doris 数据源 `1`
- [ ] 任务 2：`[dm]Nightly逻辑日汇总宽表全量刷新`，SQL 类型，Doris 数据源 `1`，依赖任务 1
- [ ] 两个任务都执行 `TRUNCATE` + 全量 `INSERT`
- [ ] 调度：每小时一次，必须排在 Nightly 事实表任务 `169496639079616` 完成之后

### 3.3 新任务 1：逻辑运行事实表全量刷新

对应 `dm_rd_efc_nightly_pipeline_logical_run`，完整 SQL：

```sql
TRUNCATE TABLE dm_rd_efc_nightly_pipeline_logical_run;

WITH pipeline_binding AS (
    SELECT
        project_id,
        pipeline_project,
        platform,
        pipeline_id,
        MAX(pipeline_type) AS pipeline_type
    FROM dm_rd_efc_project_pipeline_relation
    GROUP BY project_id, pipeline_project, platform, pipeline_id
)
INSERT INTO dm_rd_efc_nightly_pipeline_logical_run (
    project_id,
    pipeline_project,
    platform,
    pipeline_id,
    pipeline_run_id,
    run_date,
    logical_pipeline_id,
    logical_pipeline_name,
    pipeline_run_number,
    pipeline_name,
    pipeline_status,
    pipeline_run_starttime,
    pipeline_run_endtime,
    actual_duration_ms,
    efficiency_duration_ms,
    build_count,
    build_pass_count,
    build_avg_time_ms,
    build_max_time_ms,
    build_min_time_ms,
    test_count,
    test_pass_count,
    test_avg_time_ms,
    test_max_time_ms,
    test_min_time_ms,
    build_pending_duration_ms,
    test_pending_duration_ms,
    build_execution_duration_ms,
    test_execution_duration_ms,
    is_version_available,
    case_total_count,
    case_release_count,
    case_run_count,
    case_skip_count,
    case_run_pass_count,
    case_run_fail_count,
    case_release_rate,
    case_pass_rate,
    case_total_count_p0,
    case_release_count_p0,
    case_run_count_p0,
    case_run_pass_count_p0,
    case_run_fail_count_p0,
    case_release_rate_p0,
    case_pass_rate_p0
)
SELECT
    b.project_id,
    b.pipeline_project,
    b.platform,
    f.pipeline_id,
    f.pipeline_run_id,
    DATE(f.pipeline_run_endtime),
    COALESCE(a.logical_pipeline_id, f.pipeline_id),
    COALESCE(a.logical_pipeline_name, f.pipeline_name),
    f.pipeline_run_number,
    f.pipeline_name,
    f.pipeline_status,
    f.pipeline_run_starttime,
    f.pipeline_run_endtime,
    f.actual_duration_ms,
    f.efficiency_duration_ms,
    f.build_count,
    f.build_pass_count,
    f.build_avg_time_ms,
    f.build_max_time_ms,
    f.build_min_time_ms,
    f.test_count,
    f.test_pass_count,
    f.test_avg_time_ms,
    f.test_max_time_ms,
    f.test_min_time_ms,
    f.build_pending_duration_ms,
    f.test_pending_duration_ms,
    f.build_execution_duration_ms,
    f.test_execution_duration_ms,
    f.is_version_available,
    f.case_total_count,
    f.case_release_count,
    f.case_run_count,
    f.case_skip_count,
    f.case_run_pass_count,
    f.case_run_fail_count,
    f.case_release_rate,
    f.case_pass_rate,
    f.case_total_count_p0,
    f.case_release_count_p0,
    f.case_run_count_p0,
    f.case_run_pass_count_p0,
    f.case_run_fail_count_p0,
    f.case_release_rate_p0,
    f.case_pass_rate_p0
FROM dwr_rd_efc_build_fact_nightly_test_case_pipeline_run f
JOIN pipeline_binding b
    ON b.pipeline_id = f.pipeline_id
LEFT JOIN dm_rd_efc_nightly_pipeline_alias a
    ON a.project_id = b.project_id
   AND a.pipeline_project = b.pipeline_project
   AND a.platform = b.platform
   AND a.pipeline_id = f.pipeline_id
WHERE f.pipeline_run_endtime IS NOT NULL
  AND (
      (a.pipeline_id IS NOT NULL
       AND a.valid_from <= f.pipeline_run_endtime
       AND a.valid_to > f.pipeline_run_endtime)
      OR (a.pipeline_id IS NULL AND b.pipeline_type = 'NIGHTLY')
  );
```

### 3.4 新任务 2：逻辑日汇总宽表全量刷新

对应 `dm_rd_efc_nightly_pipeline_logical_day`，完整 SQL：

```sql
TRUNCATE TABLE dm_rd_efc_nightly_pipeline_logical_day;

WITH pipeline_binding AS (
    SELECT
        project_id,
        pipeline_project,
        platform,
        pipeline_id,
        MAX(pipeline_type) AS pipeline_type
    FROM dm_rd_efc_project_pipeline_relation
    GROUP BY project_id, pipeline_project, platform, pipeline_id
),
metrics AS (
    SELECT
        project_id,
        pipeline_project,
        platform,
        logical_pipeline_id,
        run_date,
        MAX(logical_pipeline_name) AS logical_pipeline_name,
        COUNT(DISTINCT pipeline_run_id) AS run_count,
        SUM(CASE WHEN pipeline_status = 'COMPLETED' THEN 1 ELSE 0 END) AS run_success_count,
        SUM(build_count) AS build_count,
        SUM(build_pass_count) AS build_pass_count,
        SUM(test_count) AS test_count,
        SUM(test_pass_count) AS test_pass_count,
        MAX(is_version_available) AS is_version_available,
        CAST(ROUND(AVG(actual_duration_ms), 0) AS BIGINT) AS e2e_duration_ms,
        CAST(ROUND(AVG(efficiency_duration_ms), 0) AS BIGINT) AS efficiency_duration_ms,
        CAST(ROUND(AVG(build_avg_time_ms), 0) AS BIGINT) AS build_avg_time_ms,
        MAX(build_max_time_ms) AS build_max_time_ms,
        CAST(ROUND(AVG(test_avg_time_ms), 0) AS BIGINT) AS test_avg_time_ms,
        MAX(test_max_time_ms) AS test_max_time_ms
    FROM dm_rd_efc_nightly_pipeline_logical_run
    GROUP BY project_id, pipeline_project, platform, logical_pipeline_id, run_date
),
case_ranked AS (
    SELECT
        project_id,
        pipeline_project,
        platform,
        logical_pipeline_id,
        logical_pipeline_name,
        run_date,
        pipeline_run_id,
        pipeline_status,
        pipeline_run_endtime,
        case_total_count,
        case_release_count,
        case_run_count,
        case_skip_count,
        case_run_pass_count,
        case_run_fail_count,
        case_total_count_p0,
        case_release_count_p0,
        case_run_count_p0,
        case_run_pass_count_p0,
        case_run_fail_count_p0,
        ROW_NUMBER() OVER (
            PARTITION BY project_id, pipeline_project, platform, logical_pipeline_id, run_date
            ORDER BY CASE WHEN pipeline_status = 'COMPLETED' THEN 0 ELSE 1 END,
                     pipeline_run_endtime DESC
        ) AS rn
    FROM dm_rd_efc_nightly_pipeline_logical_run
),
case_selected AS (
    SELECT
        project_id,
        pipeline_project,
        platform,
        logical_pipeline_id,
        logical_pipeline_name,
        run_date,
        pipeline_run_id,
        pipeline_status,
        case_total_count,
        case_release_count,
        case_run_count,
        case_skip_count,
        case_run_pass_count,
        case_run_fail_count,
        case_total_count_p0,
        case_release_count_p0,
        case_run_count_p0,
        case_run_pass_count_p0,
        case_run_fail_count_p0
    FROM case_ranked
    WHERE rn = 1
),
resource AS (
    SELECT
        b.project_id,
        b.pipeline_project,
        b.platform,
        COALESCE(a.logical_pipeline_id, u.pipeline_id) AS logical_pipeline_id,
        DATE(u.end_time) AS run_date,
        MAX(COALESCE(a.logical_pipeline_name, u.pipeline_name)) AS logical_pipeline_name,
        COUNT(DISTINCT u.pipeline_run_id) AS resource_run_count,
        SUM(CAST(u.cpu_second AS DOUBLE)) AS cpu_seconds,
        SUM(CAST(u.npu_second AS DOUBLE)) AS npu_seconds,
        SUM(CAST(u.memory_second AS DOUBLE)) AS memory_seconds
    FROM dwr_rd_efc_pipeline_run_unified u
    JOIN pipeline_binding b
        ON b.pipeline_id = u.pipeline_id
       AND b.platform = u.platform
    LEFT JOIN dm_rd_efc_nightly_pipeline_alias a
        ON a.project_id = b.project_id
       AND a.pipeline_project = b.pipeline_project
       AND a.platform = b.platform
       AND a.pipeline_id = u.pipeline_id
    WHERE u.end_time IS NOT NULL
      AND u.platform IN ('codearts', 'gitcode')
      AND (
          (a.pipeline_id IS NOT NULL
           AND a.valid_from <= u.end_time
           AND a.valid_to > u.end_time)
          OR (a.pipeline_id IS NULL AND b.pipeline_type = 'NIGHTLY')
      )
    GROUP BY
        b.project_id,
        b.pipeline_project,
        b.platform,
        COALESCE(a.logical_pipeline_id, u.pipeline_id),
        DATE(u.end_time)
),
all_keys AS (
    SELECT project_id, pipeline_project, platform, logical_pipeline_id, run_date FROM metrics
    UNION
    SELECT project_id, pipeline_project, platform, logical_pipeline_id, run_date FROM case_selected
    UNION
    SELECT project_id, pipeline_project, platform, logical_pipeline_id, run_date FROM resource
)
INSERT INTO dm_rd_efc_nightly_pipeline_logical_day (
    project_id,
    pipeline_project,
    platform,
    logical_pipeline_id,
    run_date,
    logical_pipeline_name,
    run_count,
    run_success_count,
    build_count,
    build_pass_count,
    test_count,
    test_pass_count,
    is_version_available,
    e2e_duration_ms,
    efficiency_duration_ms,
    build_avg_time_ms,
    build_max_time_ms,
    test_avg_time_ms,
    test_max_time_ms,
    case_run_id,
    case_pipeline_status,
    case_total_count,
    case_release_count,
    case_run_count,
    case_skip_count,
    case_run_pass_count,
    case_run_fail_count,
    case_total_count_p0,
    case_release_count_p0,
    case_run_count_p0,
    case_run_pass_count_p0,
    case_run_fail_count_p0,
    resource_run_count,
    cpu_seconds,
    npu_seconds,
    memory_seconds
)
SELECT
    k.project_id,
    k.pipeline_project,
    k.platform,
    k.logical_pipeline_id,
    k.run_date,
    COALESCE(m.logical_pipeline_name, c.logical_pipeline_name, r.logical_pipeline_name),
    m.run_count,
    m.run_success_count,
    m.build_count,
    m.build_pass_count,
    m.test_count,
    m.test_pass_count,
    m.is_version_available,
    m.e2e_duration_ms,
    m.efficiency_duration_ms,
    m.build_avg_time_ms,
    m.build_max_time_ms,
    m.test_avg_time_ms,
    m.test_max_time_ms,
    c.pipeline_run_id,
    c.pipeline_status,
    c.case_total_count,
    c.case_release_count,
    c.case_run_count,
    c.case_skip_count,
    c.case_run_pass_count,
    c.case_run_fail_count,
    c.case_total_count_p0,
    c.case_release_count_p0,
    c.case_run_count_p0,
    c.case_run_pass_count_p0,
    c.case_run_fail_count_p0,
    r.resource_run_count,
    r.cpu_seconds,
    r.npu_seconds,
    r.memory_seconds
FROM all_keys k
LEFT JOIN metrics m
    ON m.project_id = k.project_id
   AND m.pipeline_project = k.pipeline_project
   AND m.platform = k.platform
   AND m.logical_pipeline_id = k.logical_pipeline_id
   AND m.run_date = k.run_date
LEFT JOIN case_selected c
    ON c.project_id = k.project_id
   AND c.pipeline_project = k.pipeline_project
   AND c.platform = k.platform
   AND c.logical_pipeline_id = k.logical_pipeline_id
   AND c.run_date = k.run_date
LEFT JOIN resource r
    ON r.project_id = k.project_id
   AND r.pipeline_project = k.pipeline_project
   AND r.platform = k.platform
   AND r.logical_pipeline_id = k.logical_pipeline_id
   AND r.run_date = k.run_date;
```

### 3.5 修改任务 1：`Nightly流水线资源消耗日聚合`

工作流 `[job][raw->dwi][codearts]工程能力看板汇聚PR和Nightly资源消耗`（`177530921784672`），任务 `177531009881440`。

改动：不再查 `dwr_rd_efc_pipeline_run_unified` + relation，改为直接汇总逻辑日汇总宽表的资源字段，只汇总到昨天。完整替换 SQL：

```sql
TRUNCATE TABLE dwi_project_nightly_resource_day;

INSERT INTO dwi_project_nightly_resource_day (
    project_id,
    stat_date,
    project_name,
    product_id,
    product_name,
    cpu_seconds,
    npu_seconds,
    memory_seconds,
    update_time
)
SELECT
    ld.project_id,
    ld.run_date AS stat_date,
    spi.project_name,
    spi.product_id,
    NULL,
    ROUND(SUM(ld.cpu_seconds)),
    ROUND(SUM(ld.npu_seconds)),
    ROUND(SUM(ld.memory_seconds)),
    now() AS update_time
FROM dm_rd_efc_nightly_pipeline_logical_day ld
LEFT JOIN sdi_project_info spi
    ON ld.project_id = spi.project_id
WHERE ld.run_date <= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
GROUP BY
    ld.project_id,
    ld.run_date,
    spi.project_name,
    spi.product_id;
```

### 3.6 修改任务 2：`工程能力看板数据汇总`

工作流 `[job][raw->dwi][codearts]工程能力看板汇聚PR和Nightly资源消耗`（`177530921784672`），任务 `177531067754848`。

改动：

- 删除 `nightly_pipeline_dim` CTE（不再需要 relation 判定）；
- `nightly_stats` 改为从 `dm_rd_efc_nightly_pipeline_logical_day` 按 `project_id + run_date` 汇总，只统计到昨天；
- 其余 PR 资源、资源总量维度、`combined` 逻辑保持不变。

完整替换 SQL：

```sql
TRUNCATE TABLE dwi_project_resource_indicator_day;

WITH pr_resource AS (
    -- PR流水线资源消耗（codearts+gitcode，按流水线启动日聚合），只统计运营中仓库
    -- PR 门禁口径（2026-09-17 统一）: run 带 pr_id（桥表 pr_id 非空）即算 PR 门禁，
    --   桥表中 push/schedule 触发的行 pr_id 为空（约 58%），必须显式排除
    SELECT
        re.project_id,
        DATE(u.start_time) AS stat_date,
        ROUND(SUM(CAST(u.cpu_second AS DOUBLE))) AS cpu_seconds,
        ROUND(SUM(CAST(u.npu_second AS DOUBLE))) AS npu_seconds,
        ROUND(SUM(CAST(u.memory_second AS DOUBLE))) AS memory_seconds
    FROM dwr_rd_efc_pipeline_run_unified u
    JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
        ON u.pipeline_id = r.pipeline_id
        AND u.pipeline_run_id = r.pipeline_run_id
    JOIN sdi_repo_info re ON r.git_url = re.repo_url
    WHERE u.start_time IS NOT NULL
      AND r.pr_id IS NOT NULL
      AND re.repo_id IN (
          SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1
      )
    GROUP BY re.project_id, DATE(u.start_time)
),

combined AS (
    -- PR与Nightly按 project_id + stat_date 合并
    SELECT
        COALESCE(pr.project_id, nr.project_id) AS project_id,
        COALESCE(pr.stat_date, nr.stat_date) AS stat_date,
        pr.cpu_seconds     AS pr_cpu_seconds,
        pr.npu_seconds     AS pr_npu_seconds,
        pr.memory_seconds  AS pr_memory_seconds,
        nr.cpu_seconds     AS nightly_cpu_seconds,
        nr.npu_seconds     AS nightly_npu_seconds,
        nr.memory_seconds  AS nightly_memory_seconds
    FROM pr_resource pr
    FULL OUTER JOIN dwi_project_nightly_resource_day nr
        ON pr.project_id = nr.project_id
        AND pr.stat_date = nr.stat_date
),

pr_dim AS (
    SELECT
        project_id,
        group_id,
        cpu_total_cores,
        npu_total_cards,
        memory_total_gb
    FROM dim_project_resource_total
    WHERE pipeline_type = 'Pr'
),

nightly_dim AS (
    SELECT
        project_id,
        group_id,
        cpu_total_cores,
        npu_total_cards,
        memory_total_gb
    FROM dim_project_resource_total
    WHERE pipeline_type = 'Nightly'
),

-- 指标10+11: 构建成功率 + 版本可用度（逻辑日汇总宽表）
-- 构建成功率 = SUM(pass)/SUM(count)；版本可用度 = MAX(is_version_available)
nightly_stats AS (
    SELECT
        project_id,
        run_date AS stat_date,
        CAST(SUM(build_pass_count) AS DOUBLE) / CAST(NULLIF(SUM(build_count), 0) AS DOUBLE) AS nightly_build_success_rate,
        CAST(MAX(is_version_available) AS DOUBLE) AS nightly_version_availability_rate
    FROM dm_rd_efc_nightly_pipeline_logical_day
    WHERE run_date <= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
    GROUP BY project_id, run_date
)

INSERT INTO dwi_project_resource_indicator_day (
    project_id,
    project_name,
    product_id,
    product_name,
    stat_date,
    pr_group_id,
    nightly_group_id,
    pr_cpu_seconds,
    pr_npu_seconds,
    pr_memory_seconds,
    nightly_cpu_seconds,
    nightly_npu_seconds,
    nightly_memory_seconds,
    pr_cpu_usage_rate,
    pr_npu_usage_rate,
    pr_memory_usage_rate,
    nightly_cpu_usage_rate,
    nightly_npu_usage_rate,
    nightly_memory_usage_rate,
    nightly_build_success_rate,
    nightly_version_availability_rate,
    update_time
)
SELECT
    c.project_id,
    spi.project_name,
    spi.product_id,
    NULL,
    c.stat_date,
    pd.group_id    AS pr_group_id,
    nd.group_id   AS nightly_group_id,
    c.pr_cpu_seconds,
    c.pr_npu_seconds,
    c.pr_memory_seconds,
    c.nightly_cpu_seconds,
    c.nightly_npu_seconds,
    c.nightly_memory_seconds,
    CASE
        WHEN pd.cpu_total_cores IS NOT NULL AND pd.cpu_total_cores > 0
        THEN c.pr_cpu_seconds / (pd.cpu_total_cores * 86400)
    END AS pr_cpu_usage_rate,
    CASE
        WHEN pd.npu_total_cards IS NOT NULL AND pd.npu_total_cards > 0
        THEN c.pr_npu_seconds / (pd.npu_total_cards * 86400)
    END AS pr_npu_usage_rate,
    CASE
        WHEN pd.memory_total_gb IS NOT NULL AND pd.memory_total_gb > 0
        THEN c.pr_memory_seconds / (pd.memory_total_gb * 86400)
    END AS pr_memory_usage_rate,
    CASE
        WHEN nd.cpu_total_cores IS NOT NULL AND nd.cpu_total_cores > 0
        THEN c.nightly_cpu_seconds / (nd.cpu_total_cores * 86400)
    END AS nightly_cpu_usage_rate,
    CASE
        WHEN nd.npu_total_cards IS NOT NULL AND nd.npu_total_cards > 0
        THEN c.nightly_npu_seconds / (nd.npu_total_cards * 86400)
    END AS nightly_npu_usage_rate,
    CASE
        WHEN nd.memory_total_gb IS NOT NULL AND nd.memory_total_gb > 0
        THEN c.nightly_memory_seconds / (nd.memory_total_gb * 86400)
    END AS nightly_memory_usage_rate,
    ns.nightly_build_success_rate,
    ns.nightly_version_availability_rate,
    now() AS update_time
FROM combined c
LEFT JOIN sdi_project_info spi
    ON c.project_id = spi.project_id
LEFT JOIN pr_dim pd
    ON c.project_id = pd.project_id
LEFT JOIN nightly_dim nd
    ON c.project_id = nd.project_id
LEFT JOIN nightly_stats ns
    ON c.project_id = ns.project_id
    AND c.stat_date = ns.stat_date;
```

### 3.7 调度与依赖

- 新工作流 `[job][dm][nightly]逻辑流水线数据构建`：
  - 上游 1：`[job][dwi->dwr][codearts]Nightly流水线测试用例执行事实表（每条执行记录一行）`（`169496639078592`）的 `[dwr]dwr_rd_efc_build_fact_nightly_test_case_pipeline_run`（`169496639079616`）；
  - 上游 2：`[job][base]项目与流水线关联关系生成`（`182739749033248`），保证 relation 已刷新；
  - 上游 3：`dwr_rd_efc_pipeline_run_unified` 的刷新任务。现网对应 `[job][dwr->dwr]流水线信息归一`（`185073956306240`）中的 `[job][dwr->dwr]流水线运行信息归一`（`185073961563456`），开发时确认该任务确实产出 `dwr_rd_efc_pipeline_run_unified`；
  - 优先用 DS 工作流依赖触发；若用 cron，每小时一次，错开上述任务完成时间。
- `Nightly流水线资源消耗日聚合`（`177531009881440`）与 `工程能力看板数据汇总`（`177531067754848`）仍按现网频率运行，保持原有先后顺序；现网约凌晨 3~4 点跑，只处理昨天数据，不需要额外错峰。
- alias 由开发维护，后续再自动化，不放入日常调度。
- 两张新表都不做分区，不设置动态分区，数据量小，暂不自动清理。
- 逻辑运行表/日汇总表先按每小时全量跑上线，耗时过长再评估降频或改增量。

### 3.8 不改动但要确认的任务

- [ ] 确认 `[job][dwi->dwr][codearts]Nightly流水线测试用例执行事实表（每条执行记录一行）`（`169496639078592`）不清理历史数据：旧流水线改名后历史事实行仍需保留，否则逻辑运行表无法追溯旧数据。
- [ ] 确认不存在同一 `pipeline_id` 同时出现在 codearts 和 gitcode 的情况：事实表没有 platform，只能通过 relation 补平台，若两边 ID 重复会各生成一行。现有事实表任务也依赖同样的前提。
- [ ] `[job][dwr->dm][codearts]nightly流水线每日汇总`（`169496639269056`）两个任务保留运行，不改 SQL；等所有查询层切换到新表后再评估是否下线。

---

## 4. 后端 Mapper 改造

### 4.1 Nightly 看板

- [ ] `NightlyPipelineDashboardMapper.xml`
  - `selected_pipelines` 改为 relation `NIGHTLY`（旧 ID 改名后判为 OTHER，不需要再查 alias）
  - 运行指标改查 `dm_rd_efc_nightly_pipeline_logical_run`
  - 版本可用度改查 `dm_rd_efc_nightly_pipeline_logical_day`
  - 最新用例改查 `dm_rd_efc_nightly_pipeline_logical_day`
  - 成功率、构建成功率、测试成功率、用例率在 SQL 里用分子/分母计算
- [ ] `DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml`
  - 明细、count 改查 `dm_rd_efc_nightly_pipeline_logical_run`
  - 按 `logical_pipeline_id` 查询
  - 返回实际 `pipeline_id`、`pipeline_run_id` 用于跳转
  - GitHub 明细分支保持不变

### 4.2 Nightly 图表

- [ ] `PipelineHandleImpl.java`
  - `queryVersionPipeline` 改为从 relation `NIGHTLY` 取（旧 ID 为 OTHER，不再单独排除）
  - `queryPipelineRunData` 改为查逻辑日汇总宽表
  - `queryVersionAvailabilityRate` 改为查逻辑日汇总宽表
  - `queryTestCaseData` 改为查逻辑日汇总宽表用例字段
- [ ] `DmRdEfcBuildDimNightlyPipelineDayMapper.xml`
  - 改为查 `dm_rd_efc_nightly_pipeline_logical_day`
- [ ] `DmRdEfcBuildDimTestCaseNightlyPipelineDayMapper.xml`
  - 改为查 `dm_rd_efc_nightly_pipeline_logical_day` 用例字段
- [ ] `DwiVersionPipelineInfoMapper.xml`
  - 版本可用度改为查逻辑日汇总宽表

### 4.3 工程能力看板

- [ ] `OpsNightlyDetailMapper.xml`
  - 流水线集合：relation `NIGHTLY`（旧 ID 为 OTHER，不再单独排除）
  - 版本可用度、编译成功率公共 SQL 抽成 `<sql>` 片段，三处复用
  - 编译成功率：`dm_rd_efc_nightly_pipeline_logical_run`
  - 版本可用度：`dm_rd_efc_nightly_pipeline_logical_day`
  - 明细、汇总、count 按 `logical_pipeline_id`
  - 率字段在 SQL 里计算
- [ ] `OpsResourceDetailMapper.xml`
  - Nightly 明细、count、卡片汇总改为查 `dm_rd_efc_nightly_pipeline_logical_day`
  - 使用宽表的 `cpu_seconds`、`npu_seconds`、`memory_seconds`
  - PR 分支不动
- [ ] `OpsResourceRunMapper.xml`
  - 仍查 `dwr_rd_efc_pipeline_run_unified`
  - 用一条 SQL + `EXISTS OR` 兼容两种情况：已切换按 alias 有效区间，未切换按实际 `pipeline_id`
- [ ] `OpsMainStatMapper.xml`
  - `selected_pipelines` 改为 relation `NIGHTLY`（旧 ID 为 OTHER，不再单独排除）
  - `pipeline_version_avail` 改为查逻辑日汇总宽表
  - `resource_sum` 继续读 `dwi_project_resource_indicator_day`

### 4.4 开源项目运营看板

- [ ] `DwiProjectStatisticsMapper.xml`
  - 用例最新数据改为查 `dm_rd_efc_nightly_pipeline_logical_day`
  - 版本可用度改为查 `dm_rd_efc_nightly_pipeline_logical_day`
  - 流水线集合改为 relation `NIGHTLY`（旧 ID 为 OTHER，不再单独排除）

---

## 5. 前端

- [ ] 默认不需要改前端
- [ ] 验证 Nightly 看板列表仍按 `pipelineId` 渲染
- [ ] 验证明细下钻使用实际 `pipeline_id` 拼跳转链接
- [ ] 验证率字段由后端计算后格式正常
- [ ] 验证工程能力 Nightly 明细、资源环境 Nightly 明细字段没有缺失

---

## 6. 测试与验证

- [ ] 映射区间校验：`valid_to` 等于下一行 `valid_from`，最后一行 `9999-12-31`
- [ ] 新流水线切换前调试运行不在逻辑运行表
- [ ] 旧流水线切换后运行不在逻辑运行表
- [ ] 未切换流水线改造前后执行次数、成功率、分位数一致
- [ ] Nightly 看板列表执行次数与明细列表总数一致
- [ ] 工程能力 Nightly 明细与卡片汇总口径一致
- [ ] 版本可用度按逻辑流水线 + 日期去重后一致
- [ ] 旧运行、新运行的下钻链接都能打开实际流水线
- [ ] 对比改造前后主要接口 P95

---

## 7. 发布顺序

1. DBA 建 3 张表。
2. 手工维护 alias。
3. 上线逻辑运行表全量刷新任务。
4. 上线逻辑日汇总宽表全量刷新任务。
5. 修改工程能力项目级预聚合任务。
6. 发布后端 Mapper 改动。
7. 发布图表查询改动。
8. 验证数据一致性。
9. 开启定时调度。

---

## 8. 注意事项

- 不修改现有事实表、现有 DM 表、relation 表结构。
- 不在现有表加稀疏列。
- relation 识别错误不在本需求兜底。
- 逻辑运行表、日汇总表全量刷新，先上线观察耗时，跑太慢再评估降频或改增量。
- 日汇总宽表不存率字段，查询时计算。
- `run_count` 和 `resource_run_count` 来源不同，不保证相等。
- alias 区间当前由开发维护，后续自动化，上线前必须校验。
