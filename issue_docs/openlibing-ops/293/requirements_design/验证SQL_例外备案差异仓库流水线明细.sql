-- ============================================================
-- #293 例外备案：仓库流水线明细（与生产口径完全一致）
-- 用途：查看某仓库最新合入 10 个 PR 对应的成功流水线，逐次核对判定依据
--
-- 使用方式：
--   1. 把 params 中的 project_id / repo_id 改成目标仓库；
--   2. 只想看单个项目时，删掉 `AND rp.repo_id = (SELECT repo_id FROM params)`（GitHub 段同理）。
--
-- 口径（与「例外备案每日汇聚_优化.sql」一致）：
--   1) PR 范围：dwi_rd_efc_pr_info_sum 中 state='merged' 的 PR，
--      每仓按 merged_at 倒序取最新 10 个；
--   2) 运行范围：这 10 个 PR 经桥表关联的成功流水线
--      GitCode：pr_id 非空 + pipeline_name like 'pr-pipeline%'
--               + pipeline 在信息表且未删除 + pipeline_status='COMPLETED'
--      GitHub：pr_id 非空（pipeline_run_id=workflow_run_id、
--              pipeline_name=workflow_name、git_type='github'）
--              + event in (pull_request, pull_request_target)
--              + status='COMPLETED'
--   单次达标 = run_has_new=1 且 run_has_old=0；样本中任意一次达标即仓库达标。
--
-- 说明：本查询只返回被纳入样本的运行，被过滤掉的数据不会出现。
-- ============================================================
WITH params AS (
    SELECT 404151 AS project_id, 123456 AS repo_id
),
     gitcode_pr_run AS (
         SELECT DISTINCT
             'gitcode' AS platform,
             rp.project_id,
             rp.repo_id,
             rp.repo_name,
             rp.repo_url,
             CAST(r.pipeline_id AS VARCHAR) AS pipeline_id,
             r.pipeline_name,
             CAST(p.pipeline_run_id AS VARCHAR) AS run_id,
             p.pipeline_status AS run_status,
             p.pipeline_start_time AS run_time,
             CAST(r.pr_id AS VARCHAR) AS pr_id
         FROM sdi_repo_info rp
                  JOIN dwi_rd_efc_pr_info_sum pr
                       ON rp.repo_url = pr.repo_url
                  JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
                       ON pr.repo_url = r.git_url
                           AND pr.number = r.pr_id
                  JOIN dwr_rd_efc_pipeline_run_fact p
                       ON p.pipeline_id = r.pipeline_id
                           AND p.pipeline_run_id = r.pipeline_run_id
                  JOIN dwi_rd_efc_pipeline_info pi
                       ON pi.pipeline_id = p.pipeline_id
         WHERE rp.platform = 'gitcode'
           AND r.pr_id IS NOT NULL
           AND LOWER(r.pipeline_name) LIKE 'pr-pipeline%'
           AND p.pipeline_status = 'COMPLETED'
           AND pi.is_deleted != 1
           AND rp.project_id = (SELECT project_id FROM params)
           AND rp.repo_id = (SELECT repo_id FROM params)
     ),
     github_pr_run AS (
         SELECT DISTINCT
             'github' AS platform,
             rb.project_id,
             rb.repo_id,
             rb.repo_name,
             rb.repo_url,
             CAST(w.workflow_id AS VARCHAR) AS pipeline_id,
             w.workflow_name AS pipeline_name,
             CAST(w.workflow_run_id AS VARCHAR) AS run_id,
             w.status AS run_status,
             w.created_at AS run_time,
             CAST(r.pr_id AS VARCHAR) AS pr_id
         FROM sdi_repo_info rb
                  JOIN dwi_rd_efc_workflow_run_raw_github w
                       ON rb.repo_url = w.repo_url
                  JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
                       ON r.pipeline_run_id = CAST(w.workflow_run_id AS VARCHAR)
                           AND r.git_url = w.repo_url
                           AND r.git_type = 'github'
                           AND r.pipeline_name = w.workflow_name
         WHERE rb.platform = 'github'
           AND r.pr_id IS NOT NULL
           AND w.event IN ('pull_request', 'pull_request_target')
           AND w.status = 'COMPLETED'
           AND rb.project_id = (SELECT project_id FROM params)
           AND rb.repo_id = (SELECT repo_id FROM params)
     ),
     pr_run AS (
         SELECT * FROM gitcode_pr_run
         UNION ALL
         SELECT * FROM github_pr_run
     ),
     merged_pr AS (
         -- 有成功运行且已合入的 PR
         SELECT DISTINCT
             r.project_id,
             r.repo_id,
             r.repo_name,
             r.repo_url,
             r.pr_id,
             pr.merged_at
         FROM pr_run r
                  JOIN sdi_repo_info rb
                       ON rb.project_id = r.project_id
                           AND rb.repo_id = r.repo_id
                  JOIN dwi_rd_efc_pr_info_sum pr
                       ON pr.repo_url = rb.repo_url
                           AND CAST(pr.number AS VARCHAR) = r.pr_id
         WHERE pr.state = 'merged'
           AND pr.merged_at IS NOT NULL
           AND rb.project_id = (SELECT project_id FROM params)
           AND rb.repo_id = (SELECT repo_id FROM params)
     ),
     merged_recent_pr AS (
         -- 每仓最新合入的 10 个 PR
         SELECT *
         FROM (
                  SELECT
                      merged_pr.*,
                      ROW_NUMBER() OVER (
                          PARTITION BY project_id, repo_id
                          ORDER BY merged_at DESC, pr_id DESC
                          ) AS pr_rn
                  FROM merged_pr
              ) t
         WHERE pr_rn <= 10
     ),
     recent_run AS (
         -- 这 10 个 PR 对应的成功流水线；同一 run 关联多个 PR 时先去重
         SELECT
             platform, project_id, repo_id, repo_name, repo_url, pipeline_id, pipeline_name,
             run_id, run_status, run_time, pr_id, pr_rn,
             ROW_NUMBER() OVER (
                 PARTITION BY platform, repo_id
                 ORDER BY run_time DESC, run_id DESC
                 ) AS rn
         FROM (
                  SELECT
                      r.*,
                      p.pr_rn,
                      ROW_NUMBER() OVER (
                          PARTITION BY r.platform, r.repo_id, r.run_id
                          ORDER BY p.pr_rn, r.pr_id
                          ) AS dup_rn
                  FROM pr_run r
                           JOIN merged_recent_pr p
                                ON p.project_id = r.project_id
                                    AND p.repo_id = r.repo_id
                                    AND p.pr_id = r.pr_id
              ) t
         WHERE dup_rn = 1
     ),
     run_job AS (
         -- 只保留参与判定的 job：GitCode 的新旧 codecheck、GitHub 的 pre-commit/lintrunner
         SELECT
             'gitcode' AS platform,
             r.repo_id,
             r.run_id,
             j.job_name
         FROM recent_run r
                  JOIN dwr_rd_efc_pipeline_run_job_fact j
                       ON j.pipeline_run_id = r.run_id
         WHERE r.platform = 'gitcode'
           AND (LOWER(j.job_name) LIKE '%codecheck%'
             OR LOWER(j.job_name) LIKE '%pre-commit%'
             OR LOWER(j.job_name) LIKE '%lintrunner%')
         UNION ALL
         SELECT
             'github' AS platform,
             r.repo_id,
             r.run_id,
             j.job_name
         FROM recent_run r
                  JOIN dwi_rd_efc_workflow_run_job_github j
                       ON CAST(j.workflow_run_id AS VARCHAR) = r.run_id
                           AND j.repo_url = r.repo_url
         WHERE r.platform = 'github'
           AND (LOWER(j.job_name) LIKE '%pre-commit%'
             OR LOWER(j.job_name) LIKE '%lintrunner%')
     ),
     run_flag AS (
         -- run 级判定：GitHub 无旧版 codecheck，old 仅 GitCode 适用
         SELECT
             r.platform,
             r.project_id,
             r.repo_id,
             r.repo_name,
             r.pipeline_id,
             r.pipeline_name,
             r.run_id,
             r.run_status,
             r.run_time,
             r.pr_id,
             r.rn,
             MAX(CASE
                     WHEN r.platform = 'gitcode'
                         AND LOWER(j.job_name) LIKE '%codecheck%'
                         AND LOWER(j.job_name) NOT LIKE '%pre-commit%'
                         AND LOWER(j.job_name) NOT LIKE '%lintrunner%'
                         THEN 1 ELSE 0
                 END) AS run_has_old_codecheck,
             MAX(CASE
                     WHEN LOWER(j.job_name) LIKE '%pre-commit%'
                         OR LOWER(j.job_name) LIKE '%lintrunner%'
                         THEN 1 ELSE 0
                 END) AS run_has_new_codecheck,
             GROUP_CONCAT(CASE
                              WHEN r.platform = 'gitcode'
                                  AND LOWER(j.job_name) LIKE '%codecheck%'
                                  AND LOWER(j.job_name) NOT LIKE '%pre-commit%'
                                  AND LOWER(j.job_name) NOT LIKE '%lintrunner%'
                                  THEN j.job_name ELSE NULL
                 END) AS old_codecheck_jobs,
             GROUP_CONCAT(CASE
                              WHEN LOWER(j.job_name) LIKE '%pre-commit%'
                                  OR LOWER(j.job_name) LIKE '%lintrunner%'
                                  THEN j.job_name ELSE NULL
                 END) AS new_codecheck_jobs,
             COUNT(j.job_name) AS job_count
         FROM recent_run r
                  LEFT JOIN run_job j
                            ON j.platform = r.platform
                                AND j.repo_id = r.repo_id
                                AND j.run_id = r.run_id
         GROUP BY r.platform, r.project_id, r.repo_id, r.repo_name,
                  r.pipeline_id, r.pipeline_name, r.run_id, r.run_status, r.run_time, r.pr_id, r.rn
     ),
     repo_summary AS (
         -- 仓库级结论：与 ETL 写入 dwi_repo_pipeline_quality_day 的口径一致
         SELECT
             project_id,
             repo_id,
             COUNT(*) AS repo_sample_cnt,
             SUM(CASE WHEN run_has_new_codecheck = 1 AND run_has_old_codecheck = 0
                      THEN 1 ELSE 0 END) AS repo_passed_cnt,
             MAX(CASE WHEN run_has_new_codecheck = 1 AND run_has_old_codecheck = 0
                      THEN 1 ELSE 0 END) AS repo_uses_proper_codecheck
         FROM run_flag
         GROUP BY project_id, repo_id
     )
SELECT
    f.platform,
    f.project_id,
    f.repo_id,
    f.repo_name,
    f.pipeline_id,
    f.pipeline_name,
    f.run_id,
    f.run_status,
    f.run_time,
    f.pr_id,
    f.rn AS sample_rn,
    f.run_has_old_codecheck,
    f.run_has_new_codecheck,
    CASE
        WHEN f.run_has_new_codecheck = 1 AND f.run_has_old_codecheck = 0
            THEN 1 ELSE 0
        END AS run_passed,
    f.old_codecheck_jobs,
    f.new_codecheck_jobs,
    f.job_count,
    s.repo_sample_cnt,
    s.repo_passed_cnt,
    s.repo_uses_proper_codecheck
FROM run_flag f
         JOIN repo_summary s
              ON s.project_id = f.project_id
                  AND s.repo_id = f.repo_id
ORDER BY f.platform, f.run_time DESC, f.run_id DESC;
