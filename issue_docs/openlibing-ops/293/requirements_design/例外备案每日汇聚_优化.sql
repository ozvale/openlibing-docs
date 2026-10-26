-- ============================================================
-- #293 例外备案和 committer 审核一体化 — 仓库流水线质量日聚合（优化版）
-- 写入表: dwi_repo_pipeline_quality_day
--
-- 本次只调整指标5（例外备案），指标4（代码风格自动修复）保持原逻辑。
--
-- 核心变化：
-- 1. 统计日改为 D-1，截止到 D-1 23:59:59。
-- 2. GitCode 取最近 10 次成功 PR run（pipeline_status='COMPLETED'）。
-- 3. GitHub 取最近 10 次成功 PR workflow run（conclusion='success'）。
-- 4. 按单次运行判定 new=1 & old=0，最近 10 次中任意一次满足即仓库达标。
-- 5. 无成功运行时 has_old/new 置 NULL，uses_proper_codecheck=0（仍计入项目分母）。
-- 6. GitCode 不再用 pipeline_name LIKE 'pr-pipeline%' 识别 PR，改用桥表 pr_id。
-- ============================================================

WITH params AS (
    SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) AS stat_date
),
     repo_base AS (
         -- 仓库维度的全量基表, 覆盖 gitcode(流水线/开关判定) + github(pre-commit.ci 扫描判定)
         SELECT project_id, repo_id, repo_name, is_auto_format, platform
         FROM sdi_repo_info
         WHERE platform IN ('gitcode', 'github')
     ),
     pipeline_auto_fix AS (
         -- 指标4: 逐pipeline的自动修复启用情况（保持原逻辑）
         SELECT
             r.project_id,
             r.repo_id,
             MAX(CASE
                     WHEN e.action_type = '0' AND e.is_enable = 'true' THEN 1
                     ELSE 0
                 END) AS pipeline_has_auto_fix,
             GROUP_CONCAT(CASE
                              WHEN e.action_type = '0' AND e.is_enable = 'true'
                                  THEN e.source_pipeline_id ELSE NULL
                 END) AS auto_fix_pipeline_ids
         FROM sdi_pipeline_event_trigger e
                  INNER JOIN dwi_rd_project_pipeline_relation r
                             ON e.source_pipeline_id = r.pipeline_id
                                 AND e.project_id = r.project_id
         GROUP BY r.project_id, r.repo_id
     ),
     scan_auto_fix AS (
         -- 指标4 GitHub: 取每个repo最新扫描的 pre-commit.ci 自动修复判定（保持原逻辑）
         SELECT
             s.repo_id,
             MAX(s.has_pre_commit_ci_autofix) AS has_pre_commit_ci_autofix,
             MAX(s.pre_commit_ci_autofix_reason) AS pre_commit_ci_autofix_reason
         FROM dwi_repo_quality_scan_day s
         INNER JOIN (
             SELECT repo_id, MAX(scan_date) AS max_date
             FROM dwi_repo_quality_scan_day
             GROUP BY repo_id
         ) latest ON s.repo_id = latest.repo_id AND s.scan_date = latest.max_date
         GROUP BY s.repo_id
     ),
     auto_fix_result AS (
         -- 指标4: 仓库级 has_auto_fix（保持原逻辑）
         SELECT
             rb.project_id,
             rb.repo_id,
             rb.repo_name,
             CASE
                 WHEN rb.platform = 'github'
                     THEN COALESCE(saf.has_pre_commit_ci_autofix, 0)
                 WHEN COALESCE(rb.is_auto_format, 0) = 1
                     OR COALESCE(paf.pipeline_has_auto_fix, 0) = 1
                     THEN 1 ELSE 0
                 END AS has_auto_fix,
             CASE WHEN rb.platform = 'github' THEN NULL ELSE paf.auto_fix_pipeline_ids END AS auto_fix_pipeline_ids,
             CASE WHEN rb.platform = 'github'
                 THEN saf.pre_commit_ci_autofix_reason ELSE NULL END AS pre_commit_ci_autofix_reason
         FROM repo_base rb
                  LEFT JOIN pipeline_auto_fix paf
                            ON rb.project_id = paf.project_id
                                AND rb.repo_id = paf.repo_id
                  LEFT JOIN scan_auto_fix saf
                            ON rb.repo_id = saf.repo_id
     ),

-- ============================================================
-- 指标5: GitCode — 最近 10 次成功 PR run
-- ============================================================
     gitcode_run_base AS (
         SELECT DISTINCT
             rp.repo_id,
             rp.repo_name,
             rp.project_id,
             r.pipeline_id,
             p.pipeline_run_id,
             p.pipeline_start_time
         FROM sdi_repo_info rp
                  JOIN dwi_rd_efc_pr_info_sum pr
                       ON rp.repo_url = pr.repo_url
                  JOIN sdi_rd_efc_pipeline_run_pr_relation_codearts r
                       ON pr.repo_url = r.git_url
                           AND pr.number = r.pr_id
                  JOIN dwr_rd_efc_pipeline_run_fact p
                       ON p.pipeline_id = r.pipeline_id
                           AND p.pipeline_run_id = r.pipeline_run_id
                  LEFT JOIN dwi_rd_efc_pipeline_info pi
                            ON pi.pipeline_id = p.pipeline_id
                  CROSS JOIN params ps
         WHERE rp.platform = 'gitcode'
           AND r.pr_id IS NOT NULL
           AND p.pipeline_status = 'COMPLETED'
           AND p.pipeline_start_time < DATE_ADD(ps.stat_date, INTERVAL 1 DAY)
           AND COALESCE(pi.is_deleted, 0) != 1
     ),
     gitcode_recent_run AS (
         SELECT repo_id, repo_name, project_id, pipeline_id, pipeline_run_id, rn
         FROM (
                  SELECT
                      repo_id,
                      repo_name,
                      project_id,
                      pipeline_id,
                      pipeline_run_id,
                      ROW_NUMBER() OVER (
                          PARTITION BY repo_id
                          ORDER BY pipeline_start_time DESC, pipeline_run_id DESC
                          ) AS rn
                  FROM gitcode_run_base
              ) t
         WHERE rn <= 10
     ),
     gitcode_run_job AS (
         SELECT
             lr.repo_id,
             lr.repo_name,
             lr.project_id,
             lr.pipeline_id,
             lr.pipeline_run_id,
             lr.rn,
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
         FROM gitcode_recent_run lr
                  LEFT JOIN dwr_rd_efc_pipeline_run_job_fact j
                            ON j.pipeline_run_id = lr.pipeline_run_id
     ),
     gitcode_run_flag AS (
         SELECT
             repo_id,
             repo_name,
             project_id,
             pipeline_id,
             pipeline_run_id,
             rn,
             MAX(is_old_codecheck) AS run_has_old_codecheck,
             MAX(is_new_codecheck) AS run_has_new_codecheck,
             GROUP_CONCAT(CASE WHEN is_old_codecheck = 1 THEN job_name ELSE NULL END) AS old_codecheck_jobs,
             GROUP_CONCAT(CASE WHEN is_new_codecheck = 1 THEN job_name ELSE NULL END) AS new_codecheck_jobs
         FROM gitcode_run_job
         GROUP BY repo_id, repo_name, project_id, pipeline_id, pipeline_run_id, rn
     ),
     gitcode_repo_result AS (
         SELECT
             project_id,
             repo_id,
             repo_name,
             -- 最近一次成功运行的 flag 和 job 明细，仅用于展示
             MAX(CASE WHEN rn = 1 THEN run_has_old_codecheck END) AS has_old_codecheck,
             MAX(CASE WHEN rn = 1 THEN run_has_new_codecheck END) AS has_new_codecheck,
             MAX(CASE WHEN rn = 1 THEN old_codecheck_jobs END) AS old_codecheck_jobs,
             MAX(CASE WHEN rn = 1 THEN new_codecheck_jobs END) AS new_codecheck_jobs,
             -- 最近 10 次中任意一次运行满足 new=1 且 old=0 即达标
             MAX(CASE WHEN run_has_new_codecheck = 1 AND run_has_old_codecheck = 0
                      THEN 1 ELSE 0 END) AS uses_proper_codecheck
         FROM gitcode_run_flag
         GROUP BY project_id, repo_id, repo_name
     ),

-- ============================================================
-- 指标5: GitHub — 最近 10 次成功 PR workflow run
-- ============================================================
     github_repo_base AS (
         SELECT project_id, repo_id, repo_name, repo_url
         FROM sdi_repo_info
         WHERE platform = 'github'
     ),
     github_recent_run_base AS (
         SELECT DISTINCT
             w.repo_url,
             w.run_id AS workflow_run_id,
             w.name AS workflow_name,
             w.created_at
         FROM sdi_rd_efc_workflow_run_raw_github w
                  JOIN github_repo_base rb ON rb.repo_url = w.repo_url
                  CROSS JOIN params ps
         WHERE w.event IN ('pull_request', 'pull_request_target')
           AND w.conclusion = 'success'
           AND w.created_at < DATE_ADD(ps.stat_date, INTERVAL 1 DAY)
     ),
     github_recent_run AS (
         SELECT repo_url, workflow_run_id, workflow_name, created_at, rn
         FROM (
                  SELECT
                      repo_url,
                      workflow_run_id,
                      workflow_name,
                      created_at,
                      ROW_NUMBER() OVER (
                          PARTITION BY repo_url
                          ORDER BY created_at DESC, workflow_run_id DESC
                          ) AS rn
                  FROM github_recent_run_base
              ) t
         WHERE rn <= 10
     ),
     github_run_hit AS (
         SELECT
             r.repo_url,
             r.workflow_run_id,
             r.rn,
             MAX(CASE
                     WHEN r.workflow_name = 'Pre-Commit Check'
                         OR LOWER(j.job_name) LIKE '%pre-commit%'
                         OR LOWER(j.job_name) LIKE '%lintrunner%'
                         THEN 1 ELSE 0
                 END) AS run_has_new_codecheck,
             GROUP_CONCAT(DISTINCT CASE
                                      WHEN r.workflow_name = 'Pre-Commit Check'
                                          THEN r.workflow_name
                                      WHEN LOWER(j.job_name) LIKE '%pre-commit%'
                                          OR LOWER(j.job_name) LIKE '%lintrunner%'
                                          THEN j.job_name
                                      ELSE NULL
                 END) AS new_codecheck_jobs
         FROM github_recent_run r
                  LEFT JOIN sdi_rd_efc_workflow_run_job_github j
                            ON j.workflow_run_id = r.workflow_run_id
                                AND j.repo_url = r.repo_url
         GROUP BY r.repo_url, r.workflow_run_id, r.rn
     ),
     github_repo_with_runs AS (
         SELECT DISTINCT rb.project_id, rb.repo_id, rb.repo_name, rb.repo_url
         FROM github_repo_base rb
                  JOIN github_recent_run r ON r.repo_url = rb.repo_url
     ),
     github_repo_result AS (
         SELECT
             g.project_id,
             g.repo_id,
             g.repo_name,
             0 AS has_old_codecheck,
             MAX(CASE WHEN h.rn = 1 THEN h.run_has_new_codecheck END) AS has_new_codecheck,
             MAX(CASE WHEN h.run_has_new_codecheck = 1 THEN 1 ELSE 0 END) AS uses_proper_codecheck,
             NULL AS old_codecheck_jobs,
             MAX(CASE WHEN h.rn = 1 THEN h.new_codecheck_jobs END) AS new_codecheck_jobs
         FROM github_repo_with_runs g
                  LEFT JOIN github_run_hit h ON h.repo_url = g.repo_url
         GROUP BY g.project_id, g.repo_id, g.repo_name
     ),

-- gitcode + github codecheck 结果合并
     codecheck_result_all AS (
         SELECT project_id, repo_id, repo_name, has_old_codecheck, has_new_codecheck,
                uses_proper_codecheck, old_codecheck_jobs, new_codecheck_jobs
         FROM gitcode_repo_result
         UNION ALL
         SELECT project_id, repo_id, repo_name, has_old_codecheck, has_new_codecheck,
                uses_proper_codecheck, old_codecheck_jobs, new_codecheck_jobs
         FROM github_repo_result
     ),

-- 汇总所有维度键
     all_keys AS (
         SELECT af.project_id, af.repo_id, af.repo_name, ps.stat_date
         FROM auto_fix_result af
                  CROSS JOIN params ps
         UNION
         SELECT cc.project_id, cc.repo_id, cc.repo_name, ps.stat_date
         FROM codecheck_result_all cc
                  CROSS JOIN params ps
     )

INSERT INTO dwi_repo_pipeline_quality_day (
    project_id,
    repo_id,
    stat_date,
    repo_name,
    has_auto_fix,
    auto_fix_pipeline_ids,
    pre_commit_ci_autofix_reason,
    has_old_codecheck,
    has_new_codecheck,
    uses_proper_codecheck,
    old_codecheck_jobs,
    new_codecheck_jobs,
    create_time
)
SELECT
    k.project_id,
    k.repo_id,
    k.stat_date,
    k.repo_name,
    af.has_auto_fix,
    af.auto_fix_pipeline_ids,
    af.pre_commit_ci_autofix_reason,
    cc.has_old_codecheck,
    cc.has_new_codecheck,
    -- 无成功运行/无 codecheck 数据时按不达标 0 计，仍进入项目级分母
    COALESCE(cc.uses_proper_codecheck, 0) AS uses_proper_codecheck,
    cc.old_codecheck_jobs,
    cc.new_codecheck_jobs,
    now() AS create_time
FROM all_keys k
         LEFT JOIN auto_fix_result af
                   ON k.project_id = af.project_id
                       AND k.repo_id = af.repo_id
         LEFT JOIN codecheck_result_all cc
                   ON k.project_id = cc.project_id
                       AND k.repo_id = cc.repo_id;
