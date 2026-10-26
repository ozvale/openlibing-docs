-- ============================================================
-- #293 例外备案和 committer 审核一体化 — 项目质量指标汇总（优化版）
-- 写入表: dm_project_quality_overview_day
--
-- 本期只调整例外备案相关口径：
-- 1. exception_review_rate 分母保持“全部运营仓库”，与现网 COUNT(*) 一致。
-- 2. 无成功运行的仓库在 dwi 层写入 uses_proper_codecheck=0，仍计入分母。
-- 3. 快照 stat_date 改为 D-1。
-- 指标1-4 逻辑不变。
-- ============================================================

INSERT INTO dm_project_quality_overview_day (
    project_id, stat_date, project_name, product_id, product_name,
    style_visible_rate, precommit_rate, check_rules_total,
    python_rules_avg, cpp_rules_avg, java_rules_avg,
    auto_fix_rate, exception_review_rate,
    update_time
)
WITH
-- ============================================
-- CTE1: 指标1-3 项目级聚合（保持原逻辑）
-- ============================================
scan_agg AS (
    SELECT
        ri.project_id,
        qs.scan_date AS stat_date,
        CAST(SUM(CASE WHEN qs.style_overall_pass = 1 THEN 1 ELSE 0 END) AS DOUBLE)
            / NULLIF(SUM(CASE WHEN qs.style_overall_pass IN (0, 1) THEN 1 ELSE 0 END), 0) AS style_visible_rate,
        CAST(SUM(CASE WHEN qs.has_pre_commit_cfg = 1 THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0) AS precommit_rate,
        SUM(
            COALESCE(qs.python_ruff_enabled_rules, 0) +
            COALESCE(qs.cpp_clang_tidy_checks, 0) +
            COALESCE(qs.java_checkstyle_modules, 0) +
            CASE WHEN qs.java_google_format_found = 1 THEN 31 ELSE 0 END
        ) AS check_rules_total,
        MAX(
            CASE WHEN qs.top1_language IN ('Python', 'Cython') OR qs.top2_language IN ('Python', 'Cython')
                 THEN COALESCE(qs.python_ruff_enabled_rules, 0)
            END
        ) AS python_rules_avg,
        MAX(
            CASE WHEN qs.top1_language IN ('C', 'C Header', 'C++', 'C++ Header', 'Cpp', 'C#', 'Objective C', 'Objective C++', 'ObjC', 'Obj-C', 'Cuda', 'D', 'Nim', 'Haxe')
                  OR qs.top2_language IN ('C', 'C Header', 'C++', 'C++ Header', 'Cpp', 'C#', 'Objective C', 'Objective C++', 'ObjC', 'Obj-C', 'Cuda', 'D', 'Nim', 'Haxe')
                 THEN COALESCE(qs.cpp_clang_tidy_checks, 0)
            END
        ) AS cpp_rules_avg,
        MAX(
            CASE WHEN qs.top1_language IN ('Java', 'JavaServer Pages', 'JSP', 'Kotlin', 'Scala', 'Groovy', 'Clojure')
                  OR qs.top2_language IN ('Java', 'JavaServer Pages', 'JSP', 'Kotlin', 'Scala', 'Groovy', 'Clojure')
                 THEN COALESCE(qs.java_checkstyle_modules, 0) + CASE WHEN qs.java_google_format_found = 1 THEN 31 ELSE 0 END
            END
        ) AS java_rules_avg
    FROM dwi_repo_quality_scan_day qs
    JOIN sdi_repo_info ri ON qs.repo_id = ri.repo_id
    WHERE EXISTS (
        SELECT 1 FROM sdi_rd_efc_repo_operate_conf oc
        join sdi_rd_efc_project_operate_conf poc on poc.project_id = oc.project_id and poc.is_operate = 1
        WHERE oc.repo_id = qs.repo_id AND oc.is_operate = 1
    )
    GROUP BY ri.project_id, qs.scan_date
),

-- ============================================
-- CTE2: 指标4-5 项目级聚合
-- ============================================
pipeline_agg AS (
    SELECT
        rp.project_id,
        rp.stat_date,
        -- 指标4: 自动修复满足率（保持原逻辑）
        CAST(SUM(CASE WHEN rp.has_auto_fix = 1 THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0) AS auto_fix_rate,
        -- 指标5: 例外备案满足率
        -- 分母保持全部运营仓库；无成功运行仓库的 uses_proper_codecheck 已在 DWI 层写 0
        CAST(SUM(CASE WHEN rp.uses_proper_codecheck = 1 THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0) AS exception_review_rate
    FROM dwi_repo_pipeline_quality_day rp
    WHERE EXISTS (
        SELECT 1 FROM sdi_rd_efc_repo_operate_conf oc
        join sdi_rd_efc_project_operate_conf poc on poc.project_id = oc.project_id and poc.is_operate = 1
        WHERE oc.repo_id = rp.repo_id AND oc.is_operate = 1
    )
    GROUP BY rp.project_id, rp.stat_date
),
scan_latest AS (
    SELECT project_id, style_visible_rate, precommit_rate, check_rules_total,
           python_rules_avg, cpp_rules_avg, java_rules_avg
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY stat_date DESC) AS rn
        FROM scan_agg
    ) t WHERE rn = 1
),
pipeline_latest AS (
    SELECT project_id, auto_fix_rate, exception_review_rate
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY stat_date DESC) AS rn
        FROM pipeline_agg
    ) t WHERE rn = 1
)

SELECT
    COALESCE(sl.project_id, pl.project_id) AS project_id,
    -- 快照日期改为 D-1，与 DWI 层统计日对齐
    DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) AS stat_date,
    pi.project_name,
    pi.product_id,
    NULL AS product_name,
    sl.style_visible_rate,
    sl.precommit_rate,
    sl.check_rules_total,
    sl.python_rules_avg,
    sl.cpp_rules_avg,
    sl.java_rules_avg,
    pl.auto_fix_rate,
    pl.exception_review_rate,
    CURRENT_TIMESTAMP() AS update_time
FROM scan_latest sl
FULL OUTER JOIN pipeline_latest pl ON sl.project_id = pl.project_id
LEFT JOIN sdi_project_info pi
    ON COALESCE(sl.project_id, pl.project_id) = pi.project_id;
