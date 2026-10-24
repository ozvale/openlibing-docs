-- =====================================================================
-- dwi / dm 层指标计算 DML（代码安全检查评分看板 · design.md v4 §5/§6/§11）
-- 引擎：Apache Doris 3.x；库名 openlibing
-- 使用方式：每段独立执行，对应 DolphinScheduler 一个 SQL 任务，按序跑。
--   前置：① 先执行 sdi层6表建表DDL.sql + sdi层清洗DML.sql（[3][4][5][6] 必跑）
--         ② 再执行 dwi-dm层建表DDL.sql（含 [9] 权重配置表建表 + 18 行初始 INSERT）
--   顺序：[D1] → [D2] → [D3](⚠️待S2 commit数据) → [D5](指标16 VULNS)
--         → [D7](指标8 分支保护,依赖 P1 的 rebot.yaml 明细) → [D4](汇聚,建议最后)。
--         D5/D7 为后补段：物理位置在 D4 前、编号在 D4 后，执行时勿按编号顺序——
--         先 D5/D7 产数，D4 才能汇聚到 score_vulns / score_branch_protection。
--         D7 前置：P1 security_file_scan.py 已跑（产出 metric_code=
--         'BRANCH_PROTECTION' 的 yaml 明细行）；未跑时 D7 全仓按默认 8 分落库。
-- 扫描范围：sdi_rd_efc_repo_operate_conf.is_operate=1 且 platform='gitcode'
--   （JOIN sdi_repo_info 过滤；2026-10-06 起安全指标仅评估 GitCode 仓，
--   与 SeaTunnel 接口收集层 / P1 文件扫描脚本同口径），
--   各段统一以该表驱动（LEFT JOIN），无数据的仓也落行（score NULL / is_na=1），
--   保证 dm 汇聚仓库清单完整。
-- scan_time 口径（§3"每批一致性"）：本轮各段用 NOW()；DS 编排上线后建议替换为
-- 机器人识别（§3）：login 含 bot / robot / [bot] 即机器人（不区分大小写）。
-- =====================================================================

-- =====================================================================
-- [D1] 指标7 CODE_REVIEW + 指标10 CI_TESTS → dwi_rd_efc_security_pr_scan
--   PR 集合（7/10 共用）：dwi_rd_efc_pr_info_sum 每仓 merged_at 倒序近 30 次
--   已合入 PR，剔除机器人创建（§5.7/§5.10）
--   评审判定：sdi_rd_efc_pr_review_reviewer.is_effective_review=1
--             且 reviewer_login <> PR 创建者（本人 /lgtm 不算评审）
--   CI 判定（2026-09-26 口径升级 §5.10）：PR 关联的流水线中存在
--             测试 job（dwr_rd_efc_pipeline_run_job_unified job_type='DT'）
--             即视为有 CI；不看 job_status（失败也算跑，检查的是有没有跑）。
--             ⚠️ job 表 project_id 实为 git_url（与关联表的 CodeArts 项目 ID
--             语义不同，禁止按 project_id 同名关联），用 pipeline_run_id
--             + git_url 双键关联（实测无碰撞）。
--             口径影响：旧口径"跑了流水线"命中 81 万，新口径"有测试 job"
--             命中 3.4 万，CI 指标分数会普遍明显下降（构建/门禁流水线
--             不再计入）。
--   score_review / score_ci = 10 × 达标数 / 总数；PR 数=0 → NA
--   2026-10-07：明细 JSON（pr_unreviewed_detail / pr_ci_detail）新增
--   title / creator 字段（源 dwi_rd_efc_pr_info_sum 自带，CONCAT 拼 JSON
--   时对反斜杠和双引号做转义），配合明细配置新增"标题/创建人"两列。
--   同日补充：新增 url 字段（PR 完整链接，merge_requests 格式），配合
--   明细配置 PR 值的 href 跳转（引擎过 gitcode.com 白名单）。
-- =====================================================================
INSERT INTO openlibing.dwi_rd_efc_security_pr_scan
    (repo_id, scan_time, repo_url, pr_total_count, pr_numbers,
     pr_reviewed_count, pr_unreviewed_detail, score_review,
     pr_ci_detail, score_ci, is_na, etl_time)
WITH pr30 AS (
    SELECT p.repo_id, p.repo_url, p.number, p.title, p.creator, p.url, p.merged_at
    FROM (
        SELECT oc.repo_id, oc.repo_url, pr.number, pr.title, pr.creator, pr.url, pr.merged_at,
               ROW_NUMBER() OVER (PARTITION BY oc.repo_id ORDER BY pr.merged_at DESC) AS rn
        FROM   openlibing.dwi_rd_efc_pr_info_sum pr
        INNER JOIN (SELECT cf.repo_id, cf.repo_url
                    FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
                    JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
                    WHERE  cf.is_operate = 1
                      AND  ri.platform = 'gitcode') oc
                ON oc.repo_url = pr.repo_url
        WHERE  pr.merged_at IS NOT NULL
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%bot%'
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%robot%'
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%[bot]%'
    ) p
    WHERE p.rn <= 30
),
ci_pr AS (
    -- 有 CI = PR 关联的流水线中存在测试 job（job_type='DT'，不看 job_status：
    -- 失败也算跑，检查的是有没有跑）
    -- ⚠️ 关联键：job 表 project_id 实为 git_url，用 pipeline_run_id + git_url
    --    双键（禁止按 project_id 同名关联两表，语义不同）
    SELECT DISTINCT cr.git_url, CAST(cr.pr_id AS INT) AS pr_no
    FROM   openlibing.sdi_rd_efc_pipeline_run_pr_relation_codearts cr
    INNER JOIN (
        SELECT DISTINCT project_id, pipeline_run_id
        FROM   openlibing.dwr_rd_efc_pipeline_run_job_unified
        WHERE  job_type = 'DT'
    ) dt
        ON  dt.pipeline_run_id = cr.pipeline_run_id
    WHERE  cr.pr_id IS NOT NULL
),
pr_agg AS (
    SELECT pr30.repo_id, pr30.number, pr30.title, pr30.creator, pr30.url, pr30.merged_at,
           MAX(CASE WHEN rv.reviewer_login IS NOT NULL THEN 1 ELSE 0 END) AS is_reviewed,
           MAX(CASE WHEN ci.pr_no IS NOT NULL THEN 1 ELSE 0 END)          AS has_ci
    FROM   pr30
    LEFT JOIN openlibing.sdi_rd_efc_pr_review_reviewer rv
           ON  rv.repo_id    = pr30.repo_id
           AND rv.pr_number  = pr30.number
           AND rv.is_effective_review = 1
           AND rv.reviewer_login <> pr30.creator
    LEFT JOIN ci_pr ci
           ON  ci.git_url = pr30.repo_url
           AND ci.pr_no   = pr30.number
    GROUP BY pr30.repo_id, pr30.number, pr30.title, pr30.creator, pr30.url, pr30.merged_at
),
stat AS (
    SELECT repo_id,
           COUNT(*)                              AS total_cnt,
           SUM(is_reviewed)                      AS reviewed_cnt,
           SUM(has_ci)                           AS ci_cnt,
           CAST(CONCAT('[', GROUP_CONCAT(CAST(number AS STRING) ORDER BY merged_at DESC), ']') AS JSON)
                                                  AS pr_numbers_json,
           CAST(CONCAT('[', IFNULL(GROUP_CONCAT(
               CASE WHEN is_reviewed = 0
                    THEN CONCAT('{"number":', CAST(number AS STRING),
                                ',"title":"', REPLACE(REPLACE(IFNULL(title, ''), '\\', '\\\\'), '"', '\\"'),
                                '","creator":"', REPLACE(REPLACE(IFNULL(creator, ''), '\\', '\\\\'), '"', '\\"'),
                                '","url":"', REPLACE(REPLACE(IFNULL(url, ''), '\\', '\\\\'), '"', '\\"'),
                                '","merged_at":"', CAST(merged_at AS STRING), '"}')
               END ORDER BY merged_at DESC), ''), ']') AS JSON)      AS unreviewed_json,
           CAST(CONCAT('[', GROUP_CONCAT(
               CONCAT('{"number":', CAST(number AS STRING),
                      ',"title":"', REPLACE(REPLACE(IFNULL(title, ''), '\\', '\\\\'), '"', '\\"'),
                      '","creator":"', REPLACE(REPLACE(IFNULL(creator, ''), '\\', '\\\\'), '"', '\\"'),
                      '","url":"', REPLACE(REPLACE(IFNULL(url, ''), '\\', '\\\\'), '"', '\\"'),
                      '","has_ci":', IF(has_ci = 1, 'true', 'false'), '}') ORDER BY merged_at DESC), ']') AS JSON)      AS ci_json
    FROM   pr_agg
    GROUP BY repo_id
)
SELECT oc.repo_id,
       NOW()                                                AS scan_time,
       oc.repo_url,
       IFNULL(s.total_cnt, 0)                               AS pr_total_count,
       IFNULL(s.pr_numbers_json, CAST('[]' AS JSON))        AS pr_numbers,
       IFNULL(s.reviewed_cnt, 0)                            AS pr_reviewed_count,
       IFNULL(s.unreviewed_json, CAST('[]' AS JSON))        AS pr_unreviewed_detail,
       CASE WHEN IFNULL(s.total_cnt, 0) = 0 THEN NULL
            ELSE ROUND(10.0 * s.reviewed_cnt / s.total_cnt, 2) END AS score_review,
       IFNULL(s.ci_json, CAST('[]' AS JSON))                AS pr_ci_detail,
       CASE WHEN IFNULL(s.total_cnt, 0) = 0 THEN NULL
            ELSE ROUND(10.0 * s.ci_cnt / s.total_cnt, 2) END       AS score_ci,
       IF(IFNULL(s.total_cnt, 0) = 0, 1, 0)                 AS is_na,
       NOW()                                                AS etl_time
FROM   (SELECT cf.repo_id, cf.repo_url
        FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
        JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
        WHERE  cf.is_operate = 1
          AND  ri.platform = 'gitcode') oc
LEFT JOIN stat s ON s.repo_id = oc.repo_id;

-- =====================================================================
-- [D2] 指标9 WEBHOOKS + 11 SIGNED_RELEASES + 18 CONTRIBUTORS
--      → dwi_rd_efc_security_meta_api_scan（metric_code 长表，每仓每指标一行）
-- =====================================================================

-- ---------- [D2-9] 指标9 WEBHOOKS（§5.9 · C7 已解决） ----------
-- score = FLOOR(10 × 配置密钥钩子数 / 活跃钩子数)；
--   配置密钥 = is_active=1 且 password_is_null=0；分母 = is_active=1；
--   无活跃 Webhook = 10 分（上游明确，非 NA）；全部未配密钥 = 0 分
INSERT INTO openlibing.dwi_rd_efc_security_meta_api_scan
    (repo_id, metric_code, scan_time, repo_url, detail_json, score, is_na, etl_time)
SELECT oc.repo_id,
       'WEBHOOKS'                                           AS metric_code,
       NOW()                                                AS scan_time,
       oc.repo_url,
       CAST(CONCAT('{"active_count":', CAST(IFNULL(w.active_cnt, 0) AS STRING),
                   ',"secured_count":', CAST(IFNULL(w.secured_cnt, 0) AS STRING),
                   ',"webhooks":[', IFNULL(w.hooks_json, ''), ']}') AS JSON),
       CASE WHEN IFNULL(w.active_cnt, 0) = 0 THEN 10
            ELSE FLOOR(10.0 * IFNULL(w.secured_cnt, 0) / w.active_cnt) END AS score,
       0                                                    AS is_na,
       NOW()                                                AS etl_time
FROM   (SELECT cf.repo_id, cf.repo_url
        FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
        JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
        WHERE  cf.is_operate = 1
          AND  ri.platform = 'gitcode') oc
LEFT JOIN (
    SELECT repo_id,
           COUNT(*)                                                       AS active_cnt,
           SUM(CASE WHEN password_is_null = 0 THEN 1 ELSE 0 END)          AS secured_cnt,
           GROUP_CONCAT(CONCAT('{"id":', CAST(webhook_id AS VARCHAR),
                               ',"url":',  json_quote(IFNULL(webhook_url, '')),
                               ',"active":', IF(is_active = 1, 'true', 'false'),
                               ',"password_is_null":', IF(password_is_null = 1, 'true', 'false'),
                               '}'))                                      AS hooks_json
    FROM   openlibing.sdi_rd_efc_repo_webhook
    WHERE  is_active = 1
    GROUP BY repo_id
) w ON w.repo_id = oc.repo_id;

-- ---------- [D2-11] 指标11 SIGNED_RELEASES（§5.11 · C2 已定 · 2026-10-20 口径调整） ----------
--   版本集合：全部版本（含 prerelease 预发布，2026-10-10 口径调整，与 GitCode
--   Releases 页面展示对齐，不再排除）→ 排除"仅源码包"版本 → published_at
--   倒序取近 30 个；source_only 判定 = 资产数>0 且资产数 = /archive/ 源码资产数
--   （LENGTH/REPLACE 计数法，assets_json 转字符串后统计）
--   签名判定（2026-10-20 调整）= has_signature_asset=1（.asc/.sig/.pgp 等资产名）
--              AND has_sha256_asset=1（.sha256/.sha256sum 等资产名）——两者均须存在；
--              移除原 SLSA/ATTESTATION 关键字等效判定
--   打分：全部版本同时含 sha256 校验文件与签名文件 = 10；任一不满足 = 0；无有效版本 = NA
INSERT INTO openlibing.dwi_rd_efc_security_meta_api_scan
    (repo_id, metric_code, scan_time, repo_url, detail_json, score, is_na, etl_time)
WITH rel AS (
    SELECT r.repo_id, r.release_tag, r.published_at,
           r.has_signature_asset, r.has_sha256_asset, r.assets_json,
           -- 资产总数：数 "name" 键出现次数（每资产一个 name）
           (CHAR_LENGTH(CAST(r.assets_json AS STRING))
            - CHAR_LENGTH(REPLACE(CAST(r.assets_json AS STRING), '"name"', '')))
             / 6                                               AS asset_cnt,
           -- 源码包数：数 /archive/ 出现次数（GitCode 自动源码资产 URL 特征）
           (CHAR_LENGTH(CAST(r.assets_json AS STRING))
            - CHAR_LENGTH(REPLACE(CAST(r.assets_json AS STRING), '/archive/', '')))
             / 9                                               AS archive_cnt
    FROM   openlibing.sdi_rd_efc_release_info r
    WHERE  r.assets_json IS NOT NULL          -- 2026-10-10 口径调整：不再排除 prerelease，与 GitCode 页面一致
),
rel_valid AS (
    -- 排除"仅源码包"版本（忽略 source-only 场景）
    SELECT *, ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY published_at DESC) AS rn
    FROM   rel
    WHERE  NOT (asset_cnt > 0 AND asset_cnt = archive_cnt)
),
rel30 AS (
    SELECT * FROM rel_valid WHERE rn <= 30
),
stat AS (
    SELECT repo_id,
           COUNT(*)                                                        AS release_cnt,
           SUM(CASE WHEN IFNULL(has_signature_asset, 0) = 1
                     AND IFNULL(has_sha256_asset, 0) = 1
                     THEN 1 ELSE 0 END)                                    AS signed_cnt,
           GROUP_CONCAT(CONCAT('{"tag":"', release_tag,
                               '","signed":',
                               IF(IFNULL(has_signature_asset, 0) = 1
                                  AND IFNULL(has_sha256_asset, 0) = 1,
                                  'true', 'false'),
                               ',"has_sha256":',
                               IF(IFNULL(has_sha256_asset, 0) = 1, 'true', 'false'),
                               ',"has_signature":',
                               IF(IFNULL(has_signature_asset, 0) = 1, 'true', 'false'),
                               ',"source_only":false}'))                  AS releases_json
    FROM   rel30
    GROUP BY repo_id
)
SELECT oc.repo_id,
       'SIGNED_RELEASES'                                   AS metric_code,
       NOW()                                               AS scan_time,
       oc.repo_url,
       CAST(CONCAT('{"release_count":', CAST(IFNULL(s.release_cnt, 0) AS STRING),
                   ',"signed_count":', CAST(IFNULL(s.signed_cnt, 0) AS STRING),
                   ',"all_signed":', IF(IFNULL(s.release_cnt, 0) > 0
                                         AND s.signed_cnt = s.release_cnt, 'true', 'false'),
                   ',"releases":[', IFNULL(s.releases_json, ''), ']}') AS JSON),
       CASE WHEN IFNULL(s.release_cnt, 0) = 0 THEN NULL           -- 无有效版本 → NA
            WHEN s.signed_cnt = s.release_cnt THEN 10             -- 全满足
            ELSE 0 END                                            AS score,
       IF(IFNULL(s.release_cnt, 0) = 0, 1, 0)                    AS is_na,
       NOW()                                                     AS etl_time
FROM   (SELECT cf.repo_id, cf.repo_url
        FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
        JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
        WHERE  cf.is_operate = 1
          AND  ri.platform = 'gitcode') oc
LEFT JOIN stat s ON s.repo_id = oc.repo_id;

-- ---------- [D2-18] 指标18 CONTRIBUTORS（§5.18 · C6 已定 · 2026-10-16 归属口径v2） ----------
--   作者集合：与 D1 同批近 30 次已合入 PR 的作者（去重，剔机器人创建）
--   公司归属：sdi_rd_efc_user_company（users/:username.company，一人一行；2026-10-16 拍板
--             从"平台组织 orgs"切换为"用户所属公司"，为空即未知、不计入 N——推动用户补填资料）
--   华为系写法归一（上游拍板）：LOWER(TRIM(company)) IN
--       ('huawei','hw','华为','华为技术有限公司','华为科技有限公司','上海华为技术有限公司')
--       → '华为技术有限公司'
--   N = 满足"该公司内存在至少 1 名作者其近 30 次 PR 数 >= 5"的公司个数
--       （org_login='' 为未采集到/未填写公司，不计入 N）
--   detail_json 字段：author_count / n_orgs / qualified_orgs /
--       authors（逐贡献者明细：贡献者、公司、近30次PR数、GitCode 主页链接）
--   score = min(10, 10 × N / 3)；近 30 次已合入 PR 为 0 → NA
INSERT INTO openlibing.dwi_rd_efc_security_meta_api_scan
    (repo_id, metric_code, scan_time, repo_url, detail_json, score, is_na, etl_time)
WITH pr30 AS (
    SELECT p.repo_id, p.creator, p.merged_at
    FROM (
        SELECT oc.repo_id, pr.creator, pr.merged_at,
               ROW_NUMBER() OVER (PARTITION BY oc.repo_id ORDER BY pr.merged_at DESC) AS rn
        FROM   openlibing.dwi_rd_efc_pr_info_sum pr
        INNER JOIN (SELECT cf.repo_id, cf.repo_url
                    FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
                    JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
                    WHERE  cf.is_operate = 1
                      AND  ri.platform = 'gitcode') oc
                ON oc.repo_url = pr.repo_url
        WHERE  pr.merged_at IS NOT NULL
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%bot%'
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%robot%'
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%[bot]%'
    ) p
    WHERE p.rn <= 30
),
author_stat AS (
    SELECT repo_id, creator AS user_login, COUNT(*) AS pr_cnt
    FROM   pr30
    GROUP BY repo_id, creator
),
author_org AS (
    SELECT a.repo_id, a.user_login, a.pr_cnt,
           CASE
               WHEN uc.user_login IS NULL                            THEN '未配置公司'  -- 未采集到该用户(404/注销/改名)
               WHEN uc.company IS NULL OR TRIM(uc.company) = ''      THEN '未配置公司'  -- 未填写公司
               WHEN LOWER(TRIM(uc.company)) IN ('huawei','hw','华为',
                                              '华为技术有限公司','华为科技有限公司',
                                              '上海华为技术有限公司')
                                                                   THEN '华为技术有限公司'  -- 华为系写法归一(上游拍板)
               ELSE TRIM(uc.company)
           END AS org_login
    FROM   author_stat a
    LEFT JOIN openlibing.sdi_rd_efc_user_company uc
           ON uc.user_login = a.user_login
),
org_pass AS (
    SELECT repo_id, org_login,
           COUNT(*)                                            AS author_cnt,
           MAX(CASE WHEN pr_cnt >= 5 THEN 1 ELSE 0 END)        AS has_active
    FROM   author_org
    WHERE  org_login <> ''
    GROUP BY repo_id, org_login
),
stat AS (
    SELECT repo_id,
           COUNT(*)                                            AS n_orgs,
           GROUP_CONCAT(org_login)                             AS qualified_orgs
    FROM   org_pass
    WHERE  has_active = 1
    GROUP BY repo_id
),
author_cnt AS (
    SELECT repo_id, COUNT(*) AS author_count FROM author_stat GROUP BY repo_id
),
authors_json AS (
    -- 逐贡献者明细（前端「贡献者明细」表）：贡献者/公司/近30次PR数/主页链接
    -- 口径 v3：未采集到/未填写统一为「未配置公司」（真实公司名），org 无空串分支
    -- url = GitCode 个人主页（https://gitcode.com/<login>），配合 conf href 跳转
    SELECT repo_id,
           GROUP_CONCAT(
               CONCAT('{"user":"',   REPLACE(REPLACE(user_login, '\\', '\\\\'), '"', '\\"'),
                      '","org":',    IF(org_login = '', 'null',
                                          CONCAT('"', REPLACE(REPLACE(org_login, '\\', '\\\\'), '"', '\\"'), '"')),
                      ',"pr_cnt":',  CAST(pr_cnt AS STRING),
                      ',"url":"https://gitcode.com/', user_login, '"}')
               ORDER BY pr_cnt DESC, user_login ASC) AS au
    FROM   author_org
    GROUP BY repo_id
)
SELECT oc.repo_id,
       'CONTRIBUTORS'                                      AS metric_code,
       NOW()                                               AS scan_time,
       oc.repo_url,
       CAST(CONCAT('{"author_count":', CAST(IFNULL(ac.author_count, 0) AS STRING),
                   ',"n_orgs":', CAST(IFNULL(s.n_orgs, 0) AS STRING),
                   ',"qualified_orgs":[', IFNULL(GROUP_CONCAT_json.qo, ''), '],',
                   '"authors":[', IFNULL(aj.au, ''), ']}') AS JSON),
       CASE WHEN IFNULL(ac.author_count, 0) = 0 THEN NULL
            ELSE LEAST(10, ROUND(10.0 * IFNULL(s.n_orgs, 0) / 3, 2)) END AS score,
       IF(IFNULL(ac.author_count, 0) = 0, 1, 0)            AS is_na,
       NOW()                                               AS etl_time
FROM   (SELECT cf.repo_id, cf.repo_url
        FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
        JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
        WHERE  cf.is_operate = 1
          AND  ri.platform = 'gitcode') oc
LEFT JOIN stat s              ON s.repo_id  = oc.repo_id
LEFT JOIN author_cnt ac       ON ac.repo_id = oc.repo_id
LEFT JOIN authors_json aj      ON aj.repo_id = oc.repo_id
LEFT JOIN (SELECT repo_id, GROUP_CONCAT(CONCAT('"', org_login, '"')) AS qo
           FROM org_pass WHERE has_active = 1 GROUP BY repo_id) GROUP_CONCAT_json
       ON GROUP_CONCAT_json.repo_id = oc.repo_id;

-- =====================================================================
-- [D3] 指标17 MAINTAINED → dwi_rd_efc_security_maintained_scan（§5.17）
--   ⚠️ 依赖 S2：sdi_repo_commit_log 建表 + commit 采集数据到位后才可执行！
--      （commit 链路：代码仓commit扫描脚本.py → raw_repo_commit_log → sdi）
--   score = min(10, 10 × (commit数90d + issue数90d) / 13)
--   NA：仓库已归档 或 创建不足 90 天 → score NULL + is_na=1
--   仓库状态来源：sdi_repo_info_all.status（⚠️ sdi_repo_info 为空表不可用；
--     info_all 仅覆盖 79/136 仓，未覆盖仓 status 按未知处理、不判 NA，
--     覆盖率风险待仓库主数据补齐后消除——详见交付说明）
--   创建时间口径：platform_create_time（代码平台仓库创建时间）优先，
--     缺失回退 create_time（openlibing 录入时间），均 CAST AS DATETIME
--   detail_json 含 commit_rows / issue_rows 两个明细数组（2026-10-08 接入，
--     近 90 天各取最近 20 条，供看板 /security/metric-detail groups 渲染；
--     ⚠️ 本 Doris 版本 GROUP_CONCAT 两个坑：JSON 参数必须 CAST AS STRING；
--     不支持 SEPARATOR 关键字（默认分隔符即逗号，排序用 ORDER BY col））
-- =====================================================================
INSERT INTO openlibing.dwi_rd_efc_security_maintained_scan
    (repo_id, scan_time, repo_url, repo_status, commit_cnt_90d, issue_cnt_90d,
     detail_json, score, is_na, etl_time)
WITH repo AS (
    SELECT oc.repo_id, oc.repo_url,
           IFNULL(a.status, 'unknown')                                     AS repo_status,
           CAST(NULLIF(COALESCE(a.platform_create_time, a.create_time), '')
                AS DATETIME)                                               AS repo_created
    FROM   (SELECT cf.repo_id, cf.repo_url
            FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
            JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
            WHERE  cf.is_operate = 1
              AND  ri.platform = 'gitcode') oc
    LEFT JOIN openlibing.sdi_repo_info_all a ON a.repo_id = oc.repo_id
),
commit90 AS (
    -- 采集链路按仓库默认分支拉取（见 代码仓commit扫描脚本.py），此处不再过滤分支
    SELECT repo_id, COUNT(*) AS commit_cnt
    FROM   openlibing.sdi_repo_commit_log
    WHERE  CAST(commit_time AS DATETIME) >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    GROUP BY repo_id
),
issue90 AS (
    SELECT repo_id, COUNT(*) AS issue_cnt
    FROM   openlibing.sdi_repo_issue_info
    WHERE  CAST(created_at AS DATETIME) >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    GROUP BY repo_id
),
commit_rows AS (
    -- 近 90 天 commit 明细，每仓取最近 20 条（按 commit_time DESC）
    -- ⚠️ 本 Doris 版本 GROUP_CONCAT 不支持 SEPARATOR 关键字，默认分隔符即逗号
    --   （同 D7 段 pr_numbers_json 写法：GROUP_CONCAT(expr ORDER BY col)）
    SELECT t.repo_id,
           CONCAT('[', IFNULL(GROUP_CONCAT(CAST(t.j AS STRING) ORDER BY t.rn), ''), ']') AS commit_rows_json
    FROM  (SELECT repo_id, rn,
                  JSON_OBJECT('commit_time',   CAST(commit_time AS STRING),
                              'author_name',   IFNULL(author_name, ''),
                              'author_username', IFNULL(author_username, ''),
                              'commit_title',  IFNULL(commit_title, ''),
                              'commit_hash',   IFNULL(commit_hash, '')) AS j
           FROM  (SELECT repo_id, commit_time, author_name, author_username,
                         commit_title, commit_hash,
                         ROW_NUMBER() OVER (PARTITION BY repo_id
                                            ORDER BY commit_time DESC) AS rn
                  FROM   openlibing.sdi_repo_commit_log
                  WHERE  CAST(commit_time AS DATETIME) >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                     AND commit_time IS NOT NULL) ranked) t
    WHERE  t.rn <= 20
    GROUP BY t.repo_id
),
issue_rows AS (
    -- 近 90 天 issue 明细，每仓取最近 20 条（按 created_at DESC）
    SELECT t.repo_id,
           CONCAT('[', IFNULL(GROUP_CONCAT(CAST(t.j AS STRING) ORDER BY t.rn), ''), ']') AS issue_rows_json
    FROM  (SELECT repo_id, rn,
                  JSON_OBJECT('number',      CAST(number AS STRING),
                              'url',         IFNULL(url, ''),
                              'state',       IFNULL(state, ''),
                              'title',       IFNULL(title, ''),
                              'creator',     IFNULL(creator, ''),
                              'created_at',  CAST(created_at AS STRING)) AS j
           FROM  (SELECT repo_id, number, url, state, title, creator, created_at,
                         ROW_NUMBER() OVER (PARTITION BY repo_id
                                            ORDER BY created_at DESC) AS rn
                  FROM   openlibing.sdi_repo_issue_info
                  WHERE  CAST(created_at AS DATETIME) >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                     AND created_at IS NOT NULL) ranked) t
    WHERE  t.rn <= 20
    GROUP BY t.repo_id
)
SELECT r.repo_id,
       NOW()                                                AS scan_time,
       r.repo_url,
       r.repo_status,
       IFNULL(c.commit_cnt, 0)                              AS commit_cnt_90d,
       IFNULL(i.issue_cnt, 0)                               AS issue_cnt_90d,
       CAST(CONCAT('{"commit_cnt_90d":', CAST(IFNULL(c.commit_cnt, 0) AS STRING),
                   ',"issue_cnt_90d":', CAST(IFNULL(i.issue_cnt, 0) AS STRING),
                   ',"commit_rows":', IFNULL(cr.commit_rows_json, '[]'),
                   ',"issue_rows":', IFNULL(ir.issue_rows_json, '[]'),
                   ',"repo_created":"', IFNULL(CAST(r.repo_created AS STRING), ''),
                   '"}') AS JSON),
       CASE WHEN r.repo_status = 'archived'
              OR (r.repo_created IS NOT NULL
                  AND r.repo_created >= DATE_SUB(NOW(), INTERVAL 90 DAY))
            THEN NULL
            ELSE LEAST(10, ROUND(10.0 * (IFNULL(c.commit_cnt, 0)
                                         + IFNULL(i.issue_cnt, 0)) / 13, 2)) END AS score,
       CASE WHEN r.repo_status = 'archived'
              OR (r.repo_created IS NOT NULL
                  AND r.repo_created >= DATE_SUB(NOW(), INTERVAL 90 DAY))
            THEN 1 ELSE 0 END                               AS is_na,
       NOW()                                                AS etl_time
FROM   repo r
LEFT JOIN commit90 c ON c.repo_id = r.repo_id
LEFT JOIN issue90  i ON i.repo_id = r.repo_id
LEFT JOIN commit_rows cr ON cr.repo_id = r.repo_id
LEFT JOIN issue_rows  ir ON ir.repo_id = r.repo_id;

-- =====================================================================
-- [D5] 指标16 已知漏洞 VULNS → dwi_rd_efc_security_vuln_scan（2026-09-22 接入）
--   源表：sdi_rd_efc_cve_details（openLiBing 漏洞视图；实测 56318 条 / 2203 仓，
--         135 仓运营清单按仓库名命中 45 仓，其余 90 仓无记录 → 满分，2026-10-16）
--   关联：affected_repository（纯仓库名）= repo_url 末段（去 .git）
--   拍板口径（2026-09-22；2026-10-16 更新④）：
--     ① rejected 视为关闭态，不扣分（同 closed）
--     ② cve_level 为 None/空 → 按最低档 Low 计（每个扣 1）
--     ③ 源表 is_overdue_statistics 含历史超期已关闭记录（closed 也标 1），
--        不采用；超期自行判定 = 状态非关闭态 AND 计划完成时间 < 当前
--     ④ 无 CVE 记录（漏洞平台未覆盖）→ 满分 10（is_na=0，计数 0/明细空；
--        2026-10-16 口径更新：原 NA 改满分）；
--        有覆盖且无超期 → 10 分
--   打分（C4）：score = max(0, 10 − 致命×10 − 高危×5 − 中危×2 − 低危×1)
--   明细截断：vuln_detail 每仓最多 50 条入 JSON（overdue_count 为全量计数）
--   注意：本段须在 [D4] 汇聚之前执行（D5 编号为后补，物理位置在 D4 前）
-- =====================================================================
INSERT INTO openlibing.dwi_rd_efc_security_vuln_scan
    (repo_id, scan_time, repo_url, overdue_count, vuln_detail, deduct_detail,
     score, is_na, etl_time)
WITH cve AS (
    -- 清单仓 × CVE 明细（owner+仓库名双键关联，防同名仓误配；等级归一：None/空 → Low，拍板②）
    -- 关联键来源：issue_url（https://<域名>/<owner>/<repo>/issues/<id>）第4/5段 vs repo_url 第4段+末段
    --   ① owner 两侧 LOWER：实测 CVE 侧多小写（ascend）、清单侧多首字母大写（Ascend）
    --   ② 仓库名保留大小写精确比较（GitCode 仓名区分大小写）
    --   ③ 实测排除纯仓库名关联的跨 owner 污染：src-openeuler/tensorflow(225)、
    --      src-openeuler/pytorch(47)、src-openeuler/sip(7) 不再计入；
    --      github.com/triton-lang/triton-ascend 与 gitcode.com/ascend/triton-ascend
    --      视为不同仓（2 条 CVE 不计入，2026-09-27 用户确认按 issue_url 校验）
    --   ④ 关联命中 43 仓 / 1511 条（原纯仓库名 45 仓 / 1792 条）
    SELECT oc.repo_id, oc.repo_url, c.issue_id, c.cve_num,
           CASE WHEN c.cve_level IN ('Critical', 'High', 'Medium', 'Low')
                THEN c.cve_level ELSE 'Low' END AS level_norm,
           c.issue_state, c.issue_plan_closed_time
    FROM   openlibing.sdi_rd_efc_cve_details c
    INNER JOIN (SELECT cf.repo_id, cf.repo_url
                FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
                JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
                WHERE  cf.is_operate = 1
                  AND  ri.platform = 'gitcode') oc
            ON  LOWER(SUBSTRING_INDEX(SUBSTRING_INDEX(oc.repo_url, '/', 4), '/', -1))
                = LOWER(SUBSTRING_INDEX(SUBSTRING_INDEX(c.issue_url, '/', 4), '/', -1))
            AND SUBSTRING_INDEX(SUBSTRING_INDEX(oc.repo_url, '/', -1), '.', 1)
                = SUBSTRING_INDEX(SUBSTRING_INDEX(c.issue_url, '/', 5), '/', -1)
),
overdue AS (
    -- 超期未关闭池（关闭态 = closed/rejected，拍板①；计划完成时间 < 当前）
    SELECT repo_id, issue_id, cve_num, level_norm, issue_state,
           issue_plan_closed_time,
           CASE level_norm WHEN 'Critical' THEN 10
                           WHEN 'High'     THEN 5
                           WHEN 'Medium'   THEN 2
                           ELSE 1 END      AS deduct
    FROM   cve
    WHERE  issue_state NOT IN ('closed', 'rejected')
      AND  issue_plan_closed_time IS NOT NULL
      AND  issue_plan_closed_time < NOW()
),
overdue_top AS (
    -- 明细截断：每仓扣分高者优先，最多 50 条入 JSON（计数仍全量）
    SELECT repo_id, issue_id, cve_num, level_norm, issue_state,
           issue_plan_closed_time, deduct
    FROM   (SELECT repo_id, issue_id, cve_num, level_norm, issue_state,
                   issue_plan_closed_time, deduct,
                   ROW_NUMBER() OVER (PARTITION BY repo_id
                                      ORDER BY deduct DESC,
                                               issue_plan_closed_time) AS rn
            FROM   overdue) t
    WHERE  rn <= 50
),
overdue_agg AS (
    SELECT repo_id,
           COUNT(*)               AS overdue_count,
           IFNULL(SUM(deduct), 0) AS deduct_sum,
           SUM(CASE WHEN level_norm = 'Critical' THEN 1 ELSE 0 END) AS n_critical,
           SUM(CASE WHEN level_norm = 'High'     THEN 1 ELSE 0 END) AS n_high,
           SUM(CASE WHEN level_norm = 'Medium'   THEN 1 ELSE 0 END) AS n_medium,
           SUM(CASE WHEN level_norm = 'Low'      THEN 1 ELSE 0 END) AS n_low
    FROM   overdue GROUP BY repo_id
),
detail_agg AS (
    SELECT repo_id,
           CAST(CONCAT('[', IFNULL(GROUP_CONCAT(
               CONCAT('{"issue_id":"', issue_id,
                      '","cve_num":"', cve_num,
                      '","severity":"', level_norm,
                      '","plan_closed_time":"', CAST(issue_plan_closed_time AS VARCHAR),
                      '","status":"', issue_state, '"}')
               ORDER BY deduct DESC, issue_plan_closed_time), ''), ']') AS JSON)
           AS vuln_detail
    FROM   overdue_top GROUP BY repo_id
)
SELECT oc.repo_id,
       NOW()                                              AS scan_time,
       oc.repo_url,
       -- 无覆盖（2026-10-16 口径更新：原 NA 改满分）→ 计数 0 / 明细空数组 / 扣分全 0
       IFNULL(oa.overdue_count, 0)                        AS overdue_count,
       IFNULL(da.vuln_detail, CAST('[]' AS JSON))         AS vuln_detail,
       CAST(CONCAT('{"critical":', CAST(IFNULL(oa.n_critical, 0) AS STRING),
                    ',"high":',     CAST(IFNULL(oa.n_high,     0) AS STRING),
                    ',"medium":',   CAST(IFNULL(oa.n_medium,   0) AS STRING),
                    ',"low":',      CAST(IFNULL(oa.n_low,      0) AS STRING),
                    ',"deduct_points":', CAST(IFNULL(oa.deduct_sum, 0) AS STRING),
                    '}') AS JSON)                          AS deduct_detail,
       -- 无覆盖 → 满分 10（2026-10-16 口径更新：原 NA 改满分）
       GREATEST(0, 10 - IFNULL(oa.deduct_sum, 0))         AS score,
       0                                                  AS is_na,
       NOW()                                              AS etl_time
FROM   (SELECT cf.repo_id, cf.repo_url
        FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
        JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
        WHERE  cf.is_operate = 1
          AND  ri.platform = 'gitcode') oc
LEFT JOIN overdue_agg oa ON oa.repo_id = oc.repo_id
LEFT JOIN detail_agg da ON da.repo_id = oc.repo_id;

-- 指标16 激活（与 [D5] 投产同步执行，与 D4 一起跑即可）：
--   激活后规则项分母 75 → 82.5、全量分母 87.5 → 95，本批 dm 重算即带 VULNS。
--   （权重表 [9] 初始 INSERT 中 VULNS 为 deferred，本 UPDATE 是唯一需要的激活动作）
UPDATE openlibing.dm_rd_efc_security_metric_conf
SET    status = 'active', etl_time = NOW()
WHERE  metric_code = 'VULNS';

-- =====================================================================
-- [D7] 指标8 分支保护 BRANCH_PROTECTION → dwi_rd_efc_security_branch_protect_scan
--   （2026-09-28 规则更新接入 v4.4，design.md §5.8；原 T1a/T1b 接口链路废弃）
--   规则（二元，无中间分、无 NA）：
--     ① 平台默认满足 T1/T2/T3 → 基础 8 分（base_pass 恒 1）
--     ② rebot.yaml 存在且 lgtm_need_num=2（唯一触发条件，其他取值不触发）
--        且近 30 个已合入 PR（剔机器人创建，与 D1 同口径）每个都有
--        两条不同人的 /lgtm（剔机器人评论、剔 PR 作者本人）→ 满分 10
--     ③ 触发检查但未通过（含触发而无 PR）→ 仍 8 分
--   数据源：
--     yaml 明细 ← P1 文件扫描 dwi_rd_efc_security_file_scan
--                (metric_code='BRANCH_PROTECTION'，detail_json 含
--                 has_rebot_yaml/yaml_lgtm_config/lgtm_need_num，score 恒 NULL)
--     /lgtm 评论 ← sdi_rd_efc_pr_review_reviewer（复用指标 7 链路；
--                UNIQUE KEY 一人一PR一行天然去重，"不同人"= 行数≥2）
--   ⚠️ P1 未跑/该仓无 yaml 行时按"无个性化配置"处理（has_rebot_yaml=0，
--      8 分）——与规则"无文件即默认 lgtm=1"方向一致，不会超分。
-- =====================================================================
INSERT INTO openlibing.dwi_rd_efc_security_branch_protect_scan
    (repo_id, scan_time, repo_url, base_pass, has_rebot_yaml, yaml_lgtm_config,
     lgtm_need_num, pr_lgtm_pass, pr_numbers, pr_lgtm_detail, score, is_na, etl_time)
WITH yaml_src AS (
    -- P1 产出的 rebot.yaml 明细：每仓最新批次、非 NA 行（三态异常仓 is_na=1 不参与）
    SELECT repo_id, detail_json,
           ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC) AS rn
    FROM   openlibing.dwi_rd_efc_security_file_scan
    WHERE  metric_code = 'BRANCH_PROTECTION'
      AND  is_na = 0
),
yaml AS (
    SELECT repo_id,
           CAST(get_json_string(detail_json, '$.has_rebot_yaml') AS INT) AS has_rebot_yaml,
           get_json_string(detail_json, '$.yaml_lgtm_config')            AS yaml_lgtm_config,
           CAST(get_json_string(detail_json, '$.lgtm_need_num') AS INT)  AS lgtm_need_num
    FROM   yaml_src
    WHERE  rn = 1
),
pr30 AS (
    -- 与 D1 完全同口径：每仓 merged_at 倒序近 30 次已合入 PR，剔机器人创建
    SELECT p.repo_id, p.number, p.creator, p.merged_at
    FROM (
        SELECT oc.repo_id, pr.number, pr.creator, pr.merged_at,
               ROW_NUMBER() OVER (PARTITION BY oc.repo_id ORDER BY pr.merged_at DESC) AS rn
        FROM   openlibing.dwi_rd_efc_pr_info_sum pr
        INNER JOIN (SELECT cf.repo_id, cf.repo_url
                    FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
                    JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
                    WHERE  cf.is_operate = 1
                      AND  ri.platform = 'gitcode') oc
                ON oc.repo_url = pr.repo_url
        WHERE  pr.merged_at IS NOT NULL
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%bot%'
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%robot%'
          AND  LOWER(IFNULL(pr.creator, '')) NOT LIKE '%[bot]%'
    ) p
    WHERE p.rn <= 30
),
lgtm_rows AS (
    -- 有效 /lgtm 记录：review_type='/lgtm' 且 is_effective_review=1（含非机器人）、
    -- 剔 PR 创建人本人；rn 按评论时间倒序用于取"最后两条"落明细
    SELECT pr30.repo_id, pr30.number,
           rv.reviewer_login, rv.comment_time,
           ROW_NUMBER() OVER (PARTITION BY pr30.repo_id, pr30.number
                              ORDER BY rv.comment_time DESC) AS rn
    FROM   pr30
    INNER JOIN openlibing.sdi_rd_efc_pr_review_reviewer rv
            ON  rv.repo_id   = pr30.repo_id
            AND rv.pr_number = pr30.number
            AND rv.review_type = '/lgtm'
            AND rv.is_effective_review = 1
            AND rv.reviewer_login <> pr30.creator
),
pr_stat AS (
    -- 每 PR：有效 /lgtm 人数（一人一 PR 一行，人数即"不同人"数）+ 明细 JSON
    --（0 条 /lgtm 的 PR 也要出明细行：pass=false，看得出缺什么）
    SELECT pr30.repo_id, pr30.number, pr30.merged_at,
           COUNT(lr.reviewer_login) AS lgtm_cnt,
           CAST(CONCAT('{"pr_number":', CAST(pr30.number AS STRING),
                       ',"lgtm_count":', COUNT(lr.reviewer_login),
                       ',"distinct_author":', COUNT(lr.reviewer_login),
                       ',"pass":', IF(COUNT(lr.reviewer_login) >= 2, 'true', 'false'),
                       ',"lgtms":[', IFNULL(GROUP_CONCAT(
                           CASE WHEN lr.rn <= 2
                                THEN CONCAT('{"login":"', lr.reviewer_login,
                                            '","time":"', CAST(lr.comment_time AS STRING), '"}')
                           END ORDER BY lr.comment_time DESC), ''), ']}') AS JSON) AS pr_detail
    FROM   pr30
    LEFT JOIN lgtm_rows lr
           ON  lr.repo_id = pr30.repo_id
           AND lr.number  = pr30.number
    GROUP BY pr30.repo_id, pr30.number, pr30.merged_at
),
repo_stat AS (
    SELECT repo_id,
           COUNT(*) AS pr_cnt,
           SUM(CASE WHEN lgtm_cnt >= 2 THEN 1 ELSE 0 END) AS pass_cnt,
           CAST(CONCAT('[', GROUP_CONCAT(CAST(number AS STRING) ORDER BY merged_at DESC), ']') AS JSON)
                                                  AS pr_numbers_json,
           CAST(CONCAT('[', GROUP_CONCAT(CAST(pr_detail AS STRING)), ']') AS JSON)
                                                  AS pr_lgtm_detail_json
    FROM   pr_stat
    GROUP BY repo_id
)
SELECT oc.repo_id,
       NOW()                                                     AS scan_time,
       oc.repo_url,
       1                                                         AS base_pass,
       IFNULL(y.has_rebot_yaml, 0)                               AS has_rebot_yaml,
       y.yaml_lgtm_config                                        AS yaml_lgtm_config,
       y.lgtm_need_num                                           AS lgtm_need_num,
       -- pr_lgtm_pass：仅 need_num=2 触发检查；无 PR 或任一 PR 不达标 = 0；未触发 = NULL
       CASE WHEN y.has_rebot_yaml = 1 AND y.lgtm_need_num = 2
            THEN IF(IFNULL(rs.pr_cnt, 0) > 0 AND rs.pass_cnt = rs.pr_cnt, 1, 0)
       END                                                       AS pr_lgtm_pass,
       IFNULL(rs.pr_numbers_json, CAST('[]' AS JSON))            AS pr_numbers,
       IFNULL(rs.pr_lgtm_detail_json, CAST('[]' AS JSON))        AS pr_lgtm_detail,
       -- 二元得分：触发且全过 = 10；其余（未触发/触发未过/触发无PR）= 8
       CASE WHEN y.has_rebot_yaml = 1 AND y.lgtm_need_num = 2
             AND IFNULL(rs.pr_cnt, 0) > 0 AND rs.pass_cnt = rs.pr_cnt
            THEN 10.0 ELSE 8.0 END                               AS score,
       0                                                         AS is_na,
       NOW()                                                     AS etl_time
FROM   (SELECT cf.repo_id, cf.repo_url
        FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
        JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
        WHERE  cf.is_operate = 1
          AND  ri.platform = 'gitcode') oc
LEFT JOIN yaml y  ON y.repo_id  = oc.repo_id
LEFT JOIN repo_stat rs ON rs.repo_id = oc.repo_id;

-- 指标8 激活（与 [D7] 投产同步执行，与 D4 一起跑即可）：
--   激活后规则项分母 82.5 → 90、全量分母 95 → 102.5，本批 dm 重算即带 BRANCH_PROTECTION。
UPDATE openlibing.dm_rd_efc_security_metric_conf
SET    status = 'active', etl_time = NOW()
WHERE  metric_code = 'BRANCH_PROTECTION';

-- =====================================================================
-- [D4] 全指标汇聚 + 两套加权分 + 亮灯 → dm_rd_efc_security_scan_score（§6）
--   取数：7 张 dwi 表各自"每仓最新批次"（ROW_NUMBER 取 rn=1，多批次历史全保留；
--         2026-09-22 起新增 ⑦ vuln_scan → 指标16 VULNS 纳入汇聚；
--         2026-09-28 起新增 ⑧ branch_protect_scan → 指标8 纳入汇聚）
--   加权：score = Σ(单项得分×权重) / Σ权重；NULL 项（NA + 暂缓 5/13 + 未跑）
--         分子分母同剔除——P1/P2（文件/license 扫描）未跑时对应列自然 NULL，
--         分母自动收缩，dm 可随 dwi 数据逐步补齐而无需改 SQL
--         （P1 file_scan 中 BRANCH_PROTECTION 行 score 恒 NULL，仅作明细中转，
--          汇聚取 ⑧ 表的实算分）
--   权重：JOIN [9] 配置表 dm_rd_efc_security_metric_conf 取 weight / metric_type
--         （status='active' 才进汇聚；调权重 = UPDATE 配置表 weight,下批扫描生效）
--   两套分：score_rule_weighted（规则类13项/权重和90,项目层级用；指标8 激活后）
--          score_all_weighted（已实现16项/权重和102.5,仅展示；指标8 激活后）
--   分母快照：rule_weight_sum / all_weight_sum = 本批次实际分母（active 且
--         score 非 NULL 的权重和），随批次行固化,权重配置后续变更时
--         历史批次凭这两列仍可复算得分率（口径自洽）
--   亮灯（按规则项得分率 = score_rule_weighted/10）：
--         >=80% 绿(1)；>=50% 黄(2)；<50% 红(3)；无有效指标 → NULL
-- =====================================================================
INSERT INTO openlibing.dm_rd_efc_security_scan_score
    (repo_id, scan_time, repo_url,
     score_license, score_copyright, score_dangerous_wf, score_token_perm,
     score_pinned_dep, score_binary_artifacts, score_code_review,
     score_branch_protection, score_webhooks, score_ci_tests,
     score_signed_releases, score_packaging, score_fuzzing, score_sast,
     score_security_policy, score_vulns, score_maintained, score_contributors,
     score_rule_weighted, score_all_weighted,
     rule_weight_sum, all_weight_sum, rule_light, etl_time)
WITH m AS (
    -- ① dwi_rd_efc_security_pr_scan（指标7/10 同行拆两指标）
    SELECT repo_id, 'CODE_REVIEW' AS metric, score_review AS score, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC) AS rn
    FROM   openlibing.dwi_rd_efc_security_pr_scan
    UNION ALL
    SELECT repo_id, 'CI_TESTS', score_ci, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC)
    FROM   openlibing.dwi_rd_efc_security_pr_scan
    -- ⑥ dwi_rd_efc_security_meta_api_scan（指标9/11/18）
    UNION ALL
    SELECT repo_id, metric_code, score, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id, metric_code ORDER BY scan_time DESC)
    FROM   openlibing.dwi_rd_efc_security_meta_api_scan
    -- ① dwi_rd_efc_security_maintained_scan（指标17）
    UNION ALL
    SELECT repo_id, 'MAINTAINED', score, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC)
    FROM   openlibing.dwi_rd_efc_security_maintained_scan
    -- ④ dwi_rd_efc_security_file_scan（指标2/3/4/6/12/14/15，P1 产出）
    UNION ALL
    SELECT repo_id, metric_code, score, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id, metric_code ORDER BY scan_time DESC)
    FROM   openlibing.dwi_rd_efc_security_file_scan
    -- ⑤ dwi_rd_efc_security_license_scan（指标1，P2 产出）
    UNION ALL
    SELECT repo_id, 'LICENSE', score, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC)
    FROM   openlibing.dwi_rd_efc_security_license_scan
    -- ⑦ dwi_rd_efc_security_vuln_scan（指标16，[D5] 产出，2026-09-22 接入）
    UNION ALL
    SELECT repo_id, 'VULNS', score, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC)
    FROM   openlibing.dwi_rd_efc_security_vuln_scan
    -- ⑧ dwi_rd_efc_security_branch_protect_scan（指标8，[D7] 产出，2026-09-28 接入；
    --    file_scan 中同名 metric_code 行 score 恒 NULL，不影响本汇聚）
    UNION ALL
    SELECT repo_id, 'BRANCH_PROTECTION', score, scan_time,
           ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC)
    FROM   openlibing.dwi_rd_efc_security_branch_protect_scan
),
latest AS (
    -- 权重与指标类型改由 [9] 配置表驱动（去硬编码）；status='active' 才进汇聚，
    -- deferred 暂缓项(5/13)不进 latest → dm 对应列恒 NULL,分子分母同剔除
    SELECT m.repo_id, m.metric, m.score,
           mc.weight                                           AS w,
           CASE WHEN mc.metric_type = 'rule' THEN 1 ELSE 0 END AS is_rule
    FROM   m
    INNER JOIN openlibing.dm_rd_efc_security_metric_conf mc
            ON  mc.metric_code = m.metric
            AND mc.status = 'active'
    WHERE  m.rn = 1
)
SELECT oc.repo_id,
       NOW()                                                        AS scan_time,
       oc.repo_url,
       MAX(CASE WHEN l.metric = 'LICENSE'           THEN l.score END) AS score_license,
       MAX(CASE WHEN l.metric = 'COPYRIGHT'         THEN l.score END) AS score_copyright,
       MAX(CASE WHEN l.metric = 'DANGEROUS_WF'      THEN l.score END) AS score_dangerous_wf,
       MAX(CASE WHEN l.metric = 'TOKEN_PERM'        THEN l.score END) AS score_token_perm,
       MAX(CASE WHEN l.metric = 'PINNED_DEP'        THEN l.score END) AS score_pinned_dep,
       MAX(CASE WHEN l.metric = 'BINARY_ARTIFACTS'  THEN l.score END) AS score_binary_artifacts,
       MAX(CASE WHEN l.metric = 'CODE_REVIEW'       THEN l.score END) AS score_code_review,
       MAX(CASE WHEN l.metric = 'BRANCH_PROTECTION' THEN l.score END) AS score_branch_protection,
       MAX(CASE WHEN l.metric = 'WEBHOOKS'          THEN l.score END) AS score_webhooks,
       MAX(CASE WHEN l.metric = 'CI_TESTS'          THEN l.score END) AS score_ci_tests,
       MAX(CASE WHEN l.metric = 'SIGNED_RELEASES'   THEN l.score END) AS score_signed_releases,
       MAX(CASE WHEN l.metric = 'PACKAGING'         THEN l.score END) AS score_packaging,
       MAX(CASE WHEN l.metric = 'FUZZING'           THEN l.score END) AS score_fuzzing,
       MAX(CASE WHEN l.metric = 'SAST'              THEN l.score END) AS score_sast,
       MAX(CASE WHEN l.metric = 'SECURITY_POLICY'   THEN l.score END) AS score_security_policy,
       MAX(CASE WHEN l.metric = 'VULNS'             THEN l.score END) AS score_vulns,
       MAX(CASE WHEN l.metric = 'MAINTAINED'        THEN l.score END) AS score_maintained,
       MAX(CASE WHEN l.metric = 'CONTRIBUTORS'      THEN l.score END) AS score_contributors,
       -- 规则项加权分（NULL 分子分母同剔；分母=0 时输出 NULL）
       ROUND(SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL
                      THEN l.score * l.w END)
             / NULLIF(SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL
                               THEN l.w END), 0), 2)                 AS score_rule_weighted,
       -- 全部指标加权分
       ROUND(SUM(CASE WHEN l.score IS NOT NULL THEN l.score * l.w END)
             / NULLIF(SUM(CASE WHEN l.score IS NOT NULL THEN l.w END), 0), 2)
                                                                      AS score_all_weighted,
       -- 分母口径快照（本批次实际分母 = active 且 score 非 NULL 的权重和）
       SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL THEN l.w END) AS rule_weight_sum,
       SUM(CASE WHEN l.score IS NOT NULL THEN l.w END)                    AS all_weight_sum,
       CASE
           WHEN SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL
                         THEN l.w END) IS NULL THEN NULL
           WHEN SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL
                         THEN l.score * l.w END)
                / SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL
                           THEN l.w END) >= 8 THEN 1
           WHEN SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL
                         THEN l.score * l.w END)
                / SUM(CASE WHEN l.is_rule = 1 AND l.score IS NOT NULL
                           THEN l.w END) >= 5 THEN 2
           ELSE 3
       END                                                            AS rule_light,
       NOW()                                                          AS etl_time
FROM   (SELECT cf.repo_id, cf.repo_url
        FROM   openlibing.sdi_rd_efc_repo_operate_conf cf
        JOIN   openlibing.sdi_repo_info ri ON ri.repo_id = cf.repo_id
        WHERE  cf.is_operate = 1
          AND  ri.platform = 'gitcode') oc
LEFT JOIN latest l ON l.repo_id = oc.repo_id
GROUP BY oc.repo_id, oc.repo_url;

-- =====================================================================
-- [D6] 项目(社区)层级每日分数 → dm_rd_efc_security_project_score（2026-09-23 新增）
-- 口径（design.md §6）：
--   score_rule = AVG(仓库 score_rule_weighted)：整仓无分（dm 无记录/规则项全 NA）
--                不进分母（与仓库级"NA 权重不进分母"同构），用于项目亮灯
--   score_all  = AVG(仓库 score_all_weighted)：同上，仅展示
--   light      = MAX(仓库 rule_light)：取最低灯（1绿 2黄 3红，存在红即红）
--   repo_count = 项目下 is_operate=1 应扫仓数（含无分仓）；
--   null_repo_count 单列透明记录无分仓数，不拖低项目安全水位
--   stat_date  = 执行日（每日快照，同日重跑幂等覆盖）
-- 取数：dm 每仓最新批次（rn=1，与 D4 latest 口径一致）
-- 依赖：D4 先跑（dm_rd_efc_security_scan_score 有当日数据）
-- =====================================================================
INSERT INTO openlibing.dm_rd_efc_security_project_score
    (project_id, project_name, stat_date, repo_count, null_repo_count,
     score_rule, score_all, green_count, yellow_count, red_count, light, etl_time)
SELECT
    sri.project_id,
    spi.project_name,
    CURRENT_DATE()                                                  AS stat_date,
    COUNT(*)                                                        AS repo_count,
    SUM(CASE WHEN l.repo_id IS NULL
               OR l.score_rule_weighted IS NULL THEN 1 ELSE 0 END)  AS null_repo_count,
    ROUND(AVG(l.score_rule_weighted), 2)                            AS score_rule,
    ROUND(AVG(l.score_all_weighted), 2)                             AS score_all,
    SUM(CASE WHEN l.rule_light = 1 THEN 1 ELSE 0 END)               AS green_count,
    SUM(CASE WHEN l.rule_light = 2 THEN 1 ELSE 0 END)               AS yellow_count,
    SUM(CASE WHEN l.rule_light = 3 THEN 1 ELSE 0 END)               AS red_count,
    MAX(l.rule_light)                                               AS light,
    NOW()                                                           AS etl_time
FROM   (SELECT repo_id
        FROM   openlibing.sdi_rd_efc_repo_operate_conf
        WHERE  is_operate = 1) oc
JOIN    openlibing.sdi_repo_info sri
        ON sri.repo_id = oc.repo_id
        AND sri.platform = 'gitcode'
LEFT JOIN (SELECT repo_id, score_rule_weighted, score_all_weighted, rule_light,
                  ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY scan_time DESC) AS rn
           FROM   openlibing.dm_rd_efc_security_scan_score) l
        ON l.repo_id = sri.repo_id AND l.rn = 1
LEFT JOIN openlibing.sdi_project_info spi
        ON spi.project_id = sri.project_id
GROUP BY sri.project_id, spi.project_name;
