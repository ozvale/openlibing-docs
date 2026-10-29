-- ============================================================
-- #293 例外备案：原版口径 vs 优化版口径 对比验证
-- 用途：在同一数据库执行两条 SELECT，比较每个仓库的达标结论差异
--
-- 说明：
-- 1. 两条 SQL 只读，不写库；去掉原 SQL 的 INSERT 与 stat_date 列。
-- 2. 全量仓库集合直接取 sdi_repo_info(platform in gitcode/github)，
--    与原 SQL 的 all_keys（auto_fix_result ∪ codecheck_result_all）等价：
--    auto_fix_result 由 repo_base LEFT JOIN 得到，保证每仓一行。
-- 3. 输出列完全一致，可直接导出后按 project_id + repo_id 对比。
-- 4. 差异汇总见文件末尾“对比 SQL 3/3”。
-- ============================================================


-- ============================================================
-- 对比 SQL 1/3：原版口径（附件 SQL：每仓只取最新一次运行，
--                        跨 pipeline 用 MIN(has_new) 判定）
-- ============================================================
WITH repo_base AS (
    SELECT project_id, repo_id, repo_name, platform
    FROM sdi_repo_info
    WHERE platform IN ('gitcode', 'github')
),
     latest_pr_run AS (
         -- 指标5: 每个仓库只取最新一次运行的 pipeline_run_id
         SELECT repo_id, repo_name, project_id, pipeline_id, latest_run_id
         FROM (
                  SELECT
                      rp.repo_id,
                      rp.repo_name,
                      rp.project_id,
                      r.pipeline_id,
                      p.pipeline_run_id AS latest_run_id,
                      ROW_NUMBER() OVER (
                          PARTITION BY rp.repo_id
                          ORDER BY p.pipeline_start_time DESC
                          ) AS rn
                  FROM sdi_repo_info rp
                           JOIN dwi_rd_efc_pr_info_sum pr ON rp.repo_url = pr.repo_url
                           JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
                                ON pr.repo_url = r.git_url AND pr.number = r.pr_id
                           JOIN dwr_rd_efc_pipeline_run_fact p
                                ON p.pipeline_id = r.pipeline_id
                                    AND p.pipeline_run_id = r.pipeline_run_id
                           JOIN dwi_rd_efc_pipeline_info pi ON pi.pipeline_id = p.pipeline_id
                  WHERE rp.platform = 'gitcode'
                    AND LOWER(r.pipeline_name) LIKE 'pr-pipeline%'
                    AND pi.is_deleted != 1
              ) t
         WHERE rn = 1
     ),
     pr_job_detail AS (
         SELECT
             lr.repo_id,
             lr.repo_name,
             lr.project_id,
             lr.pipeline_id,
             j.job_name,
             CASE
                 WHEN LOWER(j.job_name) LIKE '%codecheck%'
                     AND LOWER(j.job_name) NOT LIKE '%pre-commit%'
                     AND LOWER(j.job_name) NOT LIKE '%lintrunner%'
                     THEN 1 ELSE 0
                 END AS is_old_codecheck,
             CASE
                 WHEN LOWER(j.job_name) LIKE '%pre-commit%'
                     OR LOWER(j.job_name) LIKE '%lintrunner%'
                     THEN 1 ELSE 0
                 END AS is_new_codecheck
         FROM latest_pr_run lr
                  JOIN dwr_rd_efc_pipeline_run_job_fact j
                       ON j.pipeline_run_id = lr.latest_run_id
     ),
     pipeline_codecheck AS (
         SELECT
             project_id,
             repo_id,
             repo_name,
             pipeline_id,
             MAX(is_old_codecheck) AS has_old_codecheck,
             MAX(is_new_codecheck) AS has_new_codecheck,
             GROUP_CONCAT(CASE WHEN is_old_codecheck = 1 THEN job_name ELSE NULL END) AS old_codecheck_jobs,
             GROUP_CONCAT(CASE WHEN is_new_codecheck = 1 THEN job_name ELSE NULL END) AS new_codecheck_jobs
         FROM pr_job_detail
         GROUP BY project_id, repo_id, repo_name, pipeline_id
     ),
     codecheck_result AS (
         SELECT
             project_id,
             repo_id,
             repo_name,
             MAX(has_old_codecheck) AS has_old_codecheck,
             MIN(has_new_codecheck) AS has_new_codecheck,
             CASE WHEN MAX(has_old_codecheck) = 0 AND MIN(has_new_codecheck) = 1 THEN 1 ELSE 0 END AS uses_proper_codecheck,
             CASE
                 WHEN MAX(has_old_codecheck) = 1
                     THEN GROUP_CONCAT(CASE WHEN has_old_codecheck = 1 THEN old_codecheck_jobs ELSE NULL END)
                 ELSE NULL
                 END AS old_codecheck_jobs,
             CASE
                 WHEN MAX(has_new_codecheck) = 1
                     THEN GROUP_CONCAT(CASE WHEN has_new_codecheck = 1 THEN new_codecheck_jobs ELSE NULL END)
                 ELSE NULL
                 END AS new_codecheck_jobs
         FROM pipeline_codecheck
         GROUP BY project_id, repo_id, repo_name
     ),
     github_repo_base AS (
         SELECT project_id, repo_id, repo_name, repo_url
         FROM sdi_repo_info
         WHERE platform = 'github'
     ),
     github_pr_workflow_latest AS (
         SELECT w.repo_url, w.name AS workflow_name, MAX(w.workflow_run_id) AS latest_run_id
         FROM dwi_rd_efc_workflow_run_raw_github w
                  JOIN github_repo_base rb ON rb.repo_url = w.repo_url
         WHERE w.event IN ('pull_request', 'pull_request_target')
         GROUP BY w.repo_url, w.name
     ),
     github_precommit_hit AS (
         SELECT l.repo_url, l.workflow_name AS hit_name
         FROM github_pr_workflow_latest l
         WHERE l.workflow_name = 'Pre-Commit Check'
         UNION
         SELECT l.repo_url, CONCAT(l.workflow_name, '/', j.job_name) AS hit_name
         FROM github_pr_workflow_latest l
                  JOIN dwi_rd_efc_workflow_run_job_github j
                       ON j.workflow_run_id = l.latest_run_id
                           AND j.repo_url = l.repo_url
         WHERE LOWER(j.job_name) LIKE '%pre-commit%'
     ),
     github_codecheck_result AS (
         SELECT
             g.project_id,
             g.repo_id,
             g.repo_name,
             0 AS has_old_codecheck,
             CASE WHEN h.repo_url IS NOT NULL THEN 1 ELSE 0 END AS has_new_codecheck,
             CASE WHEN h.repo_url IS NOT NULL THEN 1 ELSE 0 END AS uses_proper_codecheck,
             NULL AS old_codecheck_jobs,
             h.new_codecheck_jobs
         FROM (
                  SELECT DISTINCT rb.project_id, rb.repo_id, rb.repo_name, rb.repo_url
                  FROM github_repo_base rb
                           JOIN github_pr_workflow_latest l ON l.repo_url = rb.repo_url
              ) g
                  LEFT JOIN (
             SELECT repo_url, GROUP_CONCAT(DISTINCT hit_name) AS new_codecheck_jobs
             FROM github_precommit_hit
             GROUP BY repo_url
         ) h ON h.repo_url = g.repo_url
     ),
     codecheck_result_all AS (
         SELECT project_id, repo_id, repo_name, has_old_codecheck, has_new_codecheck,
                uses_proper_codecheck, old_codecheck_jobs, new_codecheck_jobs
         FROM codecheck_result
         UNION ALL
         SELECT project_id, repo_id, repo_name, has_old_codecheck, has_new_codecheck,
                uses_proper_codecheck, old_codecheck_jobs, new_codecheck_jobs
         FROM github_codecheck_result
     )
SELECT
    rb.project_id,
    rb.repo_id,
    rb.repo_name,
    rb.platform,
    cc.has_old_codecheck,
    cc.has_new_codecheck,
    COALESCE(cc.uses_proper_codecheck, 0) AS uses_proper_codecheck
FROM repo_base rb
         LEFT JOIN codecheck_result_all cc
                   ON rb.project_id = cc.project_id
                       AND rb.repo_id = cc.repo_id
ORDER BY rb.project_id, rb.repo_id;


-- ============================================================
-- 对比 SQL 2/3：优化版口径（每仓最新合入的 10 个 PR，取其成功流水线；
--                        单次 run 判定，GitCode / GitHub 统一经桥表确认 PR 关联）
-- ============================================================
WITH repo_base AS (
    SELECT project_id, repo_id, repo_name, platform
    FROM sdi_repo_info
    WHERE platform IN ('gitcode', 'github')
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
     ),
     github_pr_run AS (
         -- 桥表映射: pipeline_id=workflow_id, pipeline_run_id=workflow_run_id, pipeline_name=workflow_name
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
         SELECT
             r.platform,
             r.project_id,
             r.repo_id,
             r.repo_name,
             r.run_id,
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
                 END) AS new_codecheck_jobs
         FROM recent_run r
                  LEFT JOIN run_job j
                            ON j.platform = r.platform
                                AND j.repo_id = r.repo_id
                                AND j.run_id = r.run_id
         GROUP BY r.platform, r.project_id, r.repo_id, r.repo_name, r.run_id, r.rn
     ),
     codecheck_result_all AS (
         SELECT
             project_id,
             repo_id,
             repo_name,
             MAX(CASE WHEN rn = 1 THEN run_has_old_codecheck END) AS has_old_codecheck,
             MAX(CASE WHEN rn = 1 THEN run_has_new_codecheck END) AS has_new_codecheck,
             MAX(CASE WHEN run_has_new_codecheck = 1 AND run_has_old_codecheck = 0
                      THEN 1 ELSE 0 END) AS uses_proper_codecheck,
             MAX(CASE WHEN rn = 1 THEN old_codecheck_jobs END) AS old_codecheck_jobs,
             MAX(CASE WHEN rn = 1 THEN new_codecheck_jobs END) AS new_codecheck_jobs
         FROM run_flag
         GROUP BY project_id, repo_id, repo_name
     )
SELECT
    rb.project_id,
    rb.repo_id,
    rb.repo_name,
    rb.platform,
    cc.has_old_codecheck,
    cc.has_new_codecheck,
    COALESCE(cc.uses_proper_codecheck, 0) AS uses_proper_codecheck
FROM repo_base rb
         LEFT JOIN codecheck_result_all cc
                   ON rb.project_id = cc.project_id
                       AND rb.repo_id = cc.repo_id
ORDER BY rb.project_id, rb.repo_id;


-- ============================================================
-- 对比 SQL 3/3：差异汇总（定位口径变化仓库）
--
-- 两条对比 SQL 的仓库集合相同（都来自 repo_base），所以直接落两张临时表
-- 做全量 JOIN 即可，不会出现单边缺失：
--
--   CREATE TABLE tmp_293_old AS <对比 SQL 1/3>;
--   CREATE TABLE tmp_293_new AS <对比 SQL 2/3>;
--
-- 再执行下面的差异 SQL：
-- ============================================================
SELECT
    o.project_id,
    o.repo_id,
    o.repo_name,
    o.platform,
    o.has_old_codecheck AS old_has_old,
    n.has_old_codecheck AS new_has_old,
    o.has_new_codecheck AS old_has_new,
    n.has_new_codecheck AS new_has_new,
    o.uses_proper_codecheck AS old_uses_proper,
    n.uses_proper_codecheck AS new_uses_proper,
    CASE
        WHEN o.uses_proper_codecheck = 0 AND n.uses_proper_codecheck = 1 THEN '不达标→达标'
        WHEN o.uses_proper_codecheck = 1 AND n.uses_proper_codecheck = 0 THEN '达标→不达标'
        ELSE '达标结论一致，明细变化'
        END AS change_type
FROM tmp_293_old o
         JOIN tmp_293_new n
              ON o.project_id = n.project_id AND o.repo_id = n.repo_id
WHERE o.uses_proper_codecheck <> n.uses_proper_codecheck
   OR COALESCE(o.has_old_codecheck, -1) <> COALESCE(n.has_old_codecheck, -1)
   OR COALESCE(o.has_new_codecheck, -1) <> COALESCE(n.has_new_codecheck, -1)
ORDER BY o.project_id, o.repo_id;
