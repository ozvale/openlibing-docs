-- ============================================================
-- #293 状态筛选前后对比 SQL
--
-- all_*     = 改造前口径（不筛选运行状态）
-- success_* = 改造后口径（仅 status = 'COMPLETED'）
--
-- 使用说明：
-- 1. 每个查询独立执行，修改各查询顶部 params 中的 project_id / start_time / end_time。
-- 2. 在 openlibing 库下执行；表名与 Mapper 中保持一致。
-- 3. 示例项目：300036；示例时间：2026-10-01 ~ 2026-10-23。
-- 4. PERCENTILE / COUNT(DISTINCT CASE ...) 的计算方式与 OpsMainStatMapper 保持一致。
-- ============================================================


-- ------------------------------------------------------------
-- 1. 运行状态分布：先确认成功/失败样本占比
-- ------------------------------------------------------------
WITH params AS (
    SELECT
        300036 AS project_id,
        '2026-10-01 00:00:00' AS start_time,
        '2026-10-23 23:59:59' AS end_time
),
pr_run_sample AS (
    SELECT DISTINCT
        sd.project_id,
        u.pipeline_run_id,
        u.status
    FROM dwi_rd_efc_pr_info_sum pr
    INNER JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts rel
        ON pr.repo_url = rel.git_url
       AND pr.number = rel.pr_id
    INNER JOIN dwr_rd_efc_pipeline_run_unified u
        ON rel.pipeline_id = u.pipeline_id
       AND rel.pipeline_run_id = u.pipeline_run_id
    INNER JOIN (
        SELECT repo_id, repo_url, project_id
        FROM sdi_repo_info
        WHERE repo_id IN (
            SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1
        )
    ) sd ON pr.repo_url = sd.repo_url
    CROSS JOIN params p
    WHERE sd.project_id = p.project_id
      AND u.start_time >= p.start_time
      AND u.start_time <= p.end_time
      AND (
          u.platform != 'github'
          OR EXISTS (
              SELECT 1
              FROM dim_ecod_github_show_pr_config gc
              INNER JOIN dwi_rd_efc_pr_workflow_run pw
                  ON pw.repo_url = gc.repo_url
                 AND pw.workflow_name = gc.workflow_name
              WHERE pw.workflow_run_id = u.pipeline_run_id
                AND gc.project_id = sd.project_id
          )
      )
)
SELECT
    status,
    COUNT(*) AS run_cnt
FROM pr_run_sample
GROUP BY status
ORDER BY run_cnt DESC;


-- ------------------------------------------------------------
-- 2. 主表 PR 构建/测试排队 P90：改造前 vs 改造后
-- ------------------------------------------------------------
WITH params AS (
    SELECT
        300036 AS project_id,
        '2026-10-01 00:00:00' AS start_time,
        '2026-10-23 23:59:59' AS end_time
),
pr_run_sample AS (
    SELECT DISTINCT
        sd.project_id,
        u.pipeline_run_id,
        u.status,
        u.end_time
    FROM dwi_rd_efc_pr_info_sum pr
    INNER JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts rel
        ON pr.repo_url = rel.git_url
       AND pr.number = rel.pr_id
    INNER JOIN dwr_rd_efc_pipeline_run_unified u
        ON rel.pipeline_id = u.pipeline_id
       AND rel.pipeline_run_id = u.pipeline_run_id
    INNER JOIN (
        SELECT repo_id, repo_url, project_id
        FROM sdi_repo_info
        WHERE repo_id IN (
            SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1
        )
    ) sd ON pr.repo_url = sd.repo_url
    CROSS JOIN params p
    WHERE sd.project_id = p.project_id
      AND u.start_time >= p.start_time
      AND u.start_time <= p.end_time
      AND (
          u.platform != 'github'
          OR EXISTS (
              SELECT 1
              FROM dim_ecod_github_show_pr_config gc
              INNER JOIN dwi_rd_efc_pr_workflow_run pw
                  ON pw.repo_url = gc.repo_url
                 AND pw.workflow_name = gc.workflow_name
              WHERE pw.workflow_run_id = u.pipeline_run_id
                AND gc.project_id = sd.project_id
          )
      )
),
run_job AS (
    SELECT
        s.project_id,
        s.pipeline_run_id,
        s.status,
        MAX(CASE WHEN j.job_type = 'BUILD' THEN j.job_pending_duration END) AS build_pd,
        MAX(CASE WHEN j.job_type = 'DT' THEN j.job_pending_duration END) AS dt_pd
    FROM pr_run_sample s
    INNER JOIN dwr_rd_efc_pipeline_run_job_unified j
        ON j.pipeline_run_id = s.pipeline_run_id
    WHERE s.end_time IS NOT NULL
    GROUP BY s.project_id, s.pipeline_run_id, s.status
),
queue_all AS (
    SELECT
        project_id,
        COUNT(*) AS run_cnt,
        ROUND(PERCENTILE(build_pd, 0.9) / 60.0, 2) AS build_p90,
        ROUND(PERCENTILE(dt_pd, 0.9) / 60.0, 2) AS dt_p90
    FROM run_job
    GROUP BY project_id
),
queue_success AS (
    SELECT
        project_id,
        COUNT(*) AS run_cnt,
        ROUND(PERCENTILE(build_pd, 0.9) / 60.0, 2) AS build_p90,
        ROUND(PERCENTILE(dt_pd, 0.9) / 60.0, 2) AS dt_p90
    FROM run_job
    WHERE status = 'COMPLETED'
    GROUP BY project_id
)
SELECT
    p.project_id,
    IFNULL(a.run_cnt, 0) AS all_run_cnt,
    IFNULL(s.run_cnt, 0) AS success_run_cnt,
    a.build_p90 AS all_build_p90,
    s.build_p90 AS success_build_p90,
    a.dt_p90 AS all_dt_p90,
    s.dt_p90 AS success_dt_p90,
    ROUND(IFNULL(a.build_p90, 0) + IFNULL(a.dt_p90, 0), 2) AS all_resource_queue,
    ROUND(IFNULL(s.build_p90, 0) + IFNULL(s.dt_p90, 0), 2) AS success_resource_queue
FROM params p
LEFT JOIN queue_all a ON a.project_id = p.project_id
LEFT JOIN queue_success s ON s.project_id = p.project_id;


-- ------------------------------------------------------------
-- 3. 主表 PR / Nightly / 整体 NPU 消耗与平均：改造前 vs 改造后
-- ------------------------------------------------------------
WITH params AS (
    SELECT
        300036 AS project_id,
        '2026-10-01 00:00:00' AS start_time,
        '2026-10-23 23:59:59' AS end_time
),
pr_run AS (
    SELECT DISTINCT
        si.project_id,
        u.pipeline_run_id,
        u.status,
        u.npu_second
    FROM dwr_rd_efc_pipeline_run_unified u
    INNER JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
        ON u.pipeline_id = r.pipeline_id
       AND u.pipeline_run_id = r.pipeline_run_id
    INNER JOIN dm_rd_efc_project_pipeline_relation rel
        ON rel.pipeline_id = u.pipeline_id
       AND rel.pipeline_type = 'PR'
    INNER JOIN sdi_repo_info si
        ON r.git_url = si.repo_url
    CROSS JOIN params p
    WHERE si.project_id = p.project_id
      AND u.start_time >= p.start_time
      AND u.start_time <= p.end_time
      AND r.pr_id IS NOT NULL
      AND si.repo_id IN (
          SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1
      )
      AND (
          u.platform != 'github'
          OR EXISTS (
              SELECT 1
              FROM dim_ecod_github_show_pr_config gc
              INNER JOIN dwi_rd_efc_pr_workflow_run pw
                  ON pw.repo_url = gc.repo_url
                 AND pw.workflow_name = gc.workflow_name
              WHERE pw.workflow_run_id = u.pipeline_run_id
                AND gc.project_id = si.project_id
          )
      )
),
nightly_run AS (
    SELECT DISTINCT
        rel.project_id,
        u.pipeline_run_id,
        u.status,
        u.npu_second
    FROM dwr_rd_efc_pipeline_run_unified u
    INNER JOIN dm_rd_efc_project_pipeline_relation rel
        ON rel.pipeline_id = u.pipeline_id
       AND rel.pipeline_type = 'NIGHTLY'
    CROSS JOIN params p
    WHERE rel.project_id = p.project_id
      AND u.start_time >= p.start_time
      AND u.start_time <= p.end_time
),
pr_stat AS (
    SELECT
        project_id,
        SUM(npu_second) / 3600 AS all_npu,
        SUM(CASE WHEN status = 'COMPLETED' THEN npu_second END) / 3600 AS success_npu,
        COUNT(DISTINCT CASE WHEN npu_second > 0 THEN pipeline_run_id END) AS all_npu_runs,
        COUNT(DISTINCT CASE WHEN status = 'COMPLETED' AND npu_second > 0 THEN pipeline_run_id END) AS success_npu_runs
    FROM pr_run
    GROUP BY project_id
),
nightly_stat AS (
    SELECT
        project_id,
        SUM(npu_second) / 3600 AS all_npu,
        SUM(CASE WHEN status = 'COMPLETED' THEN npu_second END) / 3600 AS success_npu,
        COUNT(DISTINCT CASE WHEN npu_second > 0 THEN pipeline_run_id END) AS all_npu_runs,
        COUNT(DISTINCT CASE WHEN status = 'COMPLETED' AND npu_second > 0 THEN pipeline_run_id END) AS success_npu_runs
    FROM nightly_run
    GROUP BY project_id
)
SELECT
    p.project_id,
    ROUND(IFNULL(pr.all_npu, 0), 2) AS pr_npu_usage_all,
    ROUND(IFNULL(pr.success_npu, 0), 2) AS pr_npu_usage_success,
    IFNULL(pr.all_npu_runs, 0) AS pr_npu_runs_all,
    IFNULL(pr.success_npu_runs, 0) AS pr_npu_runs_success,
    ROUND(pr.all_npu / NULLIF(pr.all_npu_runs, 0), 2) AS pr_npu_avg_all,
    ROUND(pr.success_npu / NULLIF(pr.success_npu_runs, 0), 2) AS pr_npu_avg_success,
    ROUND(IFNULL(ni.all_npu, 0), 2) AS nightly_npu_usage_all,
    ROUND(IFNULL(ni.success_npu, 0), 2) AS nightly_npu_usage_success,
    IFNULL(ni.all_npu_runs, 0) AS nightly_npu_runs_all,
    IFNULL(ni.success_npu_runs, 0) AS nightly_npu_runs_success,
    ROUND(ni.all_npu / NULLIF(ni.all_npu_runs, 0), 2) AS nightly_npu_avg_all,
    ROUND(ni.success_npu / NULLIF(ni.success_npu_runs, 0), 2) AS nightly_npu_avg_success,
    ROUND(IFNULL(pr.all_npu, 0) + IFNULL(ni.all_npu, 0), 2) AS overall_npu_usage_all,
    ROUND(IFNULL(pr.success_npu, 0) + IFNULL(ni.success_npu, 0), 2) AS overall_npu_usage_success,
    ROUND(
        (IFNULL(pr.all_npu, 0) + IFNULL(ni.all_npu, 0))
        / NULLIF(IFNULL(pr.all_npu_runs, 0) + IFNULL(ni.all_npu_runs, 0), 0),
        2
    ) AS overall_npu_avg_all,
    ROUND(
        (IFNULL(pr.success_npu, 0) + IFNULL(ni.success_npu, 0))
        / NULLIF(IFNULL(pr.success_npu_runs, 0) + IFNULL(ni.success_npu_runs, 0), 0),
        2
    ) AS overall_npu_avg_success
FROM params p
LEFT JOIN pr_stat pr ON pr.project_id = p.project_id
LEFT JOIN nightly_stat ni ON ni.project_id = p.project_id;


-- ------------------------------------------------------------
-- 4. 仓库级排队 P90：改造前 vs 改造后（按变化绝对值 Top 20）
-- ------------------------------------------------------------
WITH params AS (
    SELECT
        300036 AS project_id,
        '2026-10-01 00:00:00' AS start_time,
        '2026-10-23 23:59:59' AS end_time
),
repo_sample AS (
    SELECT DISTINCT
        sd.project_id,
        sd.repo_id,
        sd.repo_url,
        u.pipeline_run_id,
        u.status,
        u.end_time
    FROM dwi_rd_efc_pr_info_sum pr
    INNER JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts rel
        ON pr.repo_url = rel.git_url
       AND pr.number = rel.pr_id
    INNER JOIN dwr_rd_efc_pipeline_run_unified u
        ON rel.pipeline_id = u.pipeline_id
       AND rel.pipeline_run_id = u.pipeline_run_id
    INNER JOIN (
        SELECT repo_id, repo_url, project_id
        FROM sdi_repo_info
        WHERE repo_id IN (
            SELECT repo_id FROM sdi_rd_efc_repo_operate_conf WHERE is_operate = 1
        )
    ) sd ON pr.repo_url = sd.repo_url
    CROSS JOIN params p
    WHERE sd.project_id = p.project_id
      AND u.start_time >= p.start_time
      AND u.start_time <= p.end_time
      AND (
          u.platform != 'github'
          OR EXISTS (
              SELECT 1
              FROM dim_ecod_github_show_pr_config gc
              INNER JOIN dwi_rd_efc_pr_workflow_run pw
                  ON pw.repo_url = gc.repo_url
                 AND pw.workflow_name = gc.workflow_name
              WHERE pw.workflow_run_id = u.pipeline_run_id
                AND gc.project_id = sd.project_id
          )
      )
),
repo_job AS (
    SELECT
        s.repo_id,
        s.repo_url,
        s.pipeline_run_id,
        s.status,
        MAX(CASE WHEN j.job_type = 'BUILD' THEN j.job_pending_duration END) AS build_pd,
        MAX(CASE WHEN j.job_type = 'DT' THEN j.job_pending_duration END) AS dt_pd
    FROM repo_sample s
    INNER JOIN dwr_rd_efc_pipeline_run_job_unified j
        ON j.pipeline_run_id = s.pipeline_run_id
    WHERE s.end_time IS NOT NULL
    GROUP BY s.repo_id, s.repo_url, s.pipeline_run_id, s.status
),
repo_all AS (
    SELECT
        repo_id,
        MAX(repo_url) AS repo_url,
        COUNT(*) AS run_cnt,
        ROUND(PERCENTILE(build_pd, 0.9) / 60.0, 2) AS build_p90,
        ROUND(PERCENTILE(dt_pd, 0.9) / 60.0, 2) AS dt_p90
    FROM repo_job
    GROUP BY repo_id
),
repo_success AS (
    SELECT
        repo_id,
        COUNT(*) AS run_cnt,
        ROUND(PERCENTILE(build_pd, 0.9) / 60.0, 2) AS build_p90,
        ROUND(PERCENTILE(dt_pd, 0.9) / 60.0, 2) AS dt_p90
    FROM repo_job
    WHERE status = 'COMPLETED'
    GROUP BY repo_id
)
SELECT
    a.repo_url,
    IFNULL(a.run_cnt, 0) AS all_run_cnt,
    IFNULL(s.run_cnt, 0) AS success_run_cnt,
    a.build_p90 AS all_build_p90,
    s.build_p90 AS success_build_p90,
    a.dt_p90 AS all_dt_p90,
    s.dt_p90 AS success_dt_p90,
    ROUND(IFNULL(s.build_p90, 0) - IFNULL(a.build_p90, 0), 2) AS build_delta,
    ROUND(IFNULL(s.dt_p90, 0) - IFNULL(a.dt_p90, 0), 2) AS dt_delta
FROM repo_all a
LEFT JOIN repo_success s ON s.repo_id = a.repo_id
ORDER BY ABS(IFNULL(s.build_p90, 0) - IFNULL(a.build_p90, 0)) DESC
LIMIT 20;
