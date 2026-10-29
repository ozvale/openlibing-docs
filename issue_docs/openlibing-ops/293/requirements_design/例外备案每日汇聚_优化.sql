-- ============================================================
-- #293 例外备案和 committer 审核一体化 — 仓库级质量日快照（DWI）
--
-- 用途：每日为每个仓库写入一行快照，供下游使用
--   1) 项目级聚合：仓库配置指标汇总.sql → dm_project_quality_overview_day
--   2) 仓库明细下钻：后端直读 uses_proper_codecheck
-- 目标表：dwi_repo_pipeline_quality_day
-- 主键：project_id + repo_id + stat_date（UNIQUE KEY，同一天重复执行按主键覆盖）
-- 数据范围：sdi_repo_info 中 platform ∈ (gitcode, github) 的全部仓库；
--           无流水线/无扫描数据的仓库也写一行，保证项目级分母完整
--
-- 指标范围：
--   · 指标4 代码风格自动修复（保持现网逻辑）
--       - GitCode：is_auto_format=1，或存在 action_type='0' 且 is_enable='true' 的触发配置
--       - GitHub：取最新扫描日的 dwi_repo_quality_scan_day.has_pre_commit_ci_autofix
--   · 指标5 例外备案和 committer 审核一体化（本期重写，口径见下）
--
-- 指标5 口径（GitCode / GitHub 统一按“已合入 PR”采样）：
--   1) 样本 PR：从“有成功运行的 PR”中筛已合入 PR
--      （dwi_rd_efc_pr_info_sum.state='merged' 且 merged_at 非空），
--      按 merged_at 倒序取每仓最新 10 个；不足 10 个按实际数量。
--   2) 样本运行（仅成功运行）：
--      - GitCode：pipeline_status='COMPLETED'，桥表 pr_id 非空，
--        LOWER(pipeline_name) LIKE 'pr-pipeline%'，pipeline 在信息表且未删除；
--      - GitHub：status='COMPLETED'，event ∈ (pull_request, pull_request_target)，
--        桥表映射 pipeline_run_id=workflow_run_id、pipeline_name=workflow_name、git_type='github'。
--   3) 去重：同一 run 关联多个 PR（GitCode 桥表存在该情况）时按 run_id 只保留一行；
--      再按仓库内运行时间倒序编 rn（rn=1 为最近一次，仅用于展示）。
--   4) 单次运行判定（只匹配 job 名，不看 job_status）：
--      - 新版：命中 pre-commit 或 lintrunner；
--      - 旧版：命中 codecheck 且不含前两者（仅 GitCode 适用，GitHub 恒为 0）；
--      - 单次达标：新版=1 且 旧版=0。
--   5) 仓库级结果：
--      - uses_proper_codecheck：样本运行中任意一次达标即为 1，否则为 0；
--      - has_old_codecheck / has_new_codecheck / job 明细：取 rn=1 的最近一次运行，仅用于展示。
--   6) 无任何样本运行时：has_* 与 job 明细写 NULL，uses_proper_codecheck 写 0，
--      仍计入项目级分母。
--
-- 输出字段：
--   has_auto_fix / auto_fix_pipeline_ids / pre_commit_ci_autofix_reason → 指标4
--   has_old_codecheck / has_new_codecheck / uses_proper_codecheck /
--   old_codecheck_jobs / new_codecheck_jobs → 指标5
--   stat_date = CURRENT_DATE()（不回溯 D-1），create_time = now()
-- ============================================================

WITH repo_base AS (
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
-- 指标5: 例外备案 — PR 运行样本（GitCode / GitHub 归一）
-- 统一结构: platform + repo + pipeline + run + 状态 + 时间
-- ============================================================
     gitcode_pr_run AS (
         -- GitCode: 桥表 pr_id 确认 PR 关联，流水线名限定 pr-pipeline%
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
         -- GitHub: 同样经桥表确认 PR 关联
         -- 映射关系: pipeline_id=workflow_id, pipeline_run_id=workflow_run_id, pipeline_name=workflow_name
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

-- 采样：两平台统一按“最新 10 个已合入 PR”取样
-- 1) 从有成功运行的 PR 中筛出已合入 PR（DISTINCT 收敛同一 PR 的多次运行）
     merged_pr AS (
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
-- 2) 每个仓库取最新合入的 10 个 PR
     merged_recent_pr AS (
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
-- 3) 取这 10 个 PR 对应的成功流水线，并补仓库内运行序号（rn=1 为最近一次，仅用于展示）
     recent_run AS (
         SELECT
             platform, project_id, repo_id, repo_name, repo_url, pipeline_id, pipeline_name,
             run_id, run_status, run_time, pr_id, pr_rn,
             ROW_NUMBER() OVER (
                 PARTITION BY platform, repo_id
                 ORDER BY run_time DESC, run_id DESC
                 ) AS rn
         FROM (
                  -- 同一 run 可能关联多个 PR（GitCode 桥表存在该情况），先按 run 去重
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
         -- 两平台 job 明细统一为 (platform, repo_id, run_id, job_name)
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
             -- 最近一次成功运行的 flag / job 明细，仅用于展示
             MAX(CASE WHEN rn = 1 THEN run_has_old_codecheck END) AS has_old_codecheck,
             MAX(CASE WHEN rn = 1 THEN run_has_new_codecheck END) AS has_new_codecheck,
             -- 样本中任意一次运行满足 new=1 且 old=0 即达标
             MAX(CASE WHEN run_has_new_codecheck = 1 AND run_has_old_codecheck = 0
                      THEN 1 ELSE 0 END) AS uses_proper_codecheck,
             MAX(CASE WHEN rn = 1 THEN old_codecheck_jobs END) AS old_codecheck_jobs,
             MAX(CASE WHEN rn = 1 THEN new_codecheck_jobs END) AS new_codecheck_jobs
         FROM run_flag
         GROUP BY project_id, repo_id, repo_name
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
    af.project_id,
    af.repo_id,
    CURRENT_DATE() AS stat_date,
    af.repo_name,
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
FROM auto_fix_result af
         LEFT JOIN codecheck_result_all cc
                   ON af.project_id = cc.project_id
                       AND af.repo_id = cc.repo_id;
