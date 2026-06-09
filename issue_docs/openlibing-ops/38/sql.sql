-- =============================================================================
-- dolphinscheduler 定时汇总 SQL 修复版（CTE片段）
-- 修复项：
--   1. 版本可用度：去掉 GROUP BY pipeline_run_endtime，改为按项目汇总所有流水线所有天
--   2. P0通过率：去掉 pipeline_run_endtime 作为 data_time，改为跟随主INSERT汇总日期
--   3. P0通过率分母：用 case_run_count_p0 替代 case_total_count_p0
--   4. P0子查询加 WHERE pipeline_run_endtime <= CURRENT_DATE()
-- =============================================================================

-- =============================================================================
-- CTE 1: project_nightly_availability（版本可用度）
-- 修复：去掉 GROUP BY pipeline_run_endtime，按项目汇总所有流水线所有工作日
-- =============================================================================

project_nightly_availability AS (
    SELECT
        ri.project_id,
        ri.open_source,
        SUM(t.available_days) AS version_available_days,
        SUM(t.total_days) AS version_total_days
    FROM sdi_repo_info ri
    JOIN sdi_version_pipeline_base_info vp ON ri.project_id = vp.project_id
    JOIN (
        SELECT
            pipeline_id,
            COUNT(DISTINCT pipeline_run_endtime) AS total_days,
            SUM(CASE WHEN is_version_available = 1 THEN 1 ELSE 0 END) AS available_days
        FROM (
            SELECT DISTINCT
                dm.pipeline_id,
                dm.pipeline_run_endtime,
                dm.is_version_available
            FROM dm_rd_efc_build_dim_nightly_pipeline_day dm
            LEFT JOIN dim_holiday h ON dm.pipeline_run_endtime = h.holiday_date
            WHERE (h.holiday_date IS NULL AND WEEKDAY(dm.pipeline_run_endtime) < 5)
               OR (h.holiday_date IS NOT NULL AND h.is_off_day = 0)
        ) dedup
        GROUP BY pipeline_id
    ) t ON vp.pipeline_id = t.pipeline_id
    GROUP BY ri.project_id, ri.open_source
)

-- =============================================================================
-- 修复说明（版本可用度）：
-- 原方案 GROUP BY ri.project_id, ri.open_source, t.pipeline_run_endtime
-- 导致每天一行，COUNT(DISTINCT pipeline_run_endtime) 在每天=1，total永远=1
-- 多流水线时 available=4, total=1 → 425%
--
-- 修复后分两层聚合：
-- 1. 内层：按 pipeline_id 聚合，每条流水线算出 available_days 和 total_days
--    - available_days = SUM(CASE WHEN is_version_available=1 THEN 1 ELSE 0 END)
--    - total_days = COUNT(DISTINCT pipeline_run_endtime)
-- 2. 外层：按 project_id 聚合，SUM 各流水线的 available 和 total
--    - version_available_days = SUM(t.available_days)
--    - version_total_days = SUM(t.total_days)
--
-- 这样实现加权平均：SUM(各流水线available) / SUM(各流水线total)
-- 与详情页一致性：详情页每条流水线独立展示，项目汇总=加权平均
-- =============================================================================

-- =============================================================================
-- CTE 2: project_nightly_testcase_p0（P0测试用例通过率）
-- 修复：去掉 pipeline_run_endtime 作为 data_time，加 WHERE <= CURRENT_DATE()
-- =============================================================================

project_nightly_testcase_p0 AS (
    SELECT
        ri.project_id,
        ri.open_source,
        SUM(dmpd.case_run_pass_count_p0) AS p0_case_pass_count,
        SUM(dmpd.case_run_count_p0) AS p0_case_run_count
    FROM sdi_repo_info ri
    JOIN sdi_version_pipeline_base_info vp ON ri.project_id = vp.project_id
    JOIN (
        SELECT
            pipeline_id,
            case_run_pass_count_p0,
            case_run_count_p0
        FROM (
            SELECT
                pipeline_id,
                case_run_pass_count_p0,
                case_run_count_p0,
                ROW_NUMBER() OVER (
                    PARTITION BY pipeline_id
                    ORDER BY pipeline_run_endtime DESC
                ) AS rn
            FROM dm_rd_efc_build_dim_test_case_nightly_pipeline_day
            WHERE pipeline_run_endtime <= CURRENT_DATE()
        ) ranked
        WHERE rn = 1
    ) dmpd ON vp.pipeline_id = dmpd.pipeline_id
    GROUP BY ri.project_id, ri.open_source
)

-- =============================================================================
-- 修复说明（P0通过率）：
-- 原方案3个问题：
-- 1. dmpd.pipeline_run_endtime AS data_time
--    → P0数据只关联到流水线最后运行那天，其他天P0为null
--    → 修复：去掉，P0数据跟随主INSERT的data_time（汇总日期）
--
-- 2. GROUP BY dmpd.pipeline_run_endtime
--    → 多条流水线最后运行日期不同时，同一项目产生多行P0数据
--    → 修复：去掉，GROUP BY 只保留 project_id, open_source
--
-- 3. 子查询无 WHERE pipeline_run_endtime <= CURRENT_DATE()
--    → 取全历史最新运行，不是截至当天的最新运行
--    → 修复：加 WHERE pipeline_run_endtime <= CURRENT_DATE()
--
-- 4. 分母用 case_run_count_p0 而非 case_total_count_p0
--    → 与详情接口一致：P0通过率 = P0通过数 / P0执行数
-- =============================================================================

-- =============================================================================
-- 主INSERT关联方式：
-- INSERT INTO dwi_project_statistics (..., version_available_days, version_total_days,
--                                     p0_case_pass_count, p0_case_run_count)
-- SELECT ..., avail.version_available_days, avail.version_total_days,
--        p0.p0_case_pass_count, p0.p0_case_run_count
-- FROM main_cte m
-- LEFT JOIN project_nightly_availability avail
--   ON m.project_id = avail.project_id AND m.open_source = avail.open_source
-- LEFT JOIN project_nightly_testcase_p0 p0
--   ON m.project_id = p0.project_id AND m.open_source = p0.open_source
-- =============================================================================
