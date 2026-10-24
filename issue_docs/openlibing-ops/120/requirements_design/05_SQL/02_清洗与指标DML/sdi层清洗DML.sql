-- =====================================================================
-- sdi 层清洗 DML（raw → sdi，纯 Doris SQL，不依赖 SeaTunnel）
-- 引擎：Apache Doris 3.x；库名 openlibing（raw/sdi 同库）
-- 使用方式：每段独立执行，对应 Dolphin 里一个 SQL 任务；依次按序跑。
--   前置：先执行 sdi层6表建表DDL.sql（7 张 sdi 目标表）。
--   依赖：各 raw 表同批次已采集完成（先跑 raw 任务）。
-- 口径：取 raw 最新自然日批次清洗（etl_time 为行级入库时间，大表一次任务
--   分多批提交、跨多秒写入；等值取 MAX(etl_time) 只会命中最后一批——实测
--   contribute 7926 行仅命中 194 行，故改为按日过滤）。
--   T4a/T4b 需同一天先后跑完，否则按日过滤两侧批次错位会导致 org 关联丢失。
--   reviewer 的 unique key 不含 etl_time，覆盖同名 reviewer。
-- =====================================================================

-- =====================================================================
-- [1] 指标3 T1a 分支保护 → sdi_rd_efc_branch_protection
--     以默认分支(default_branch=true)驱动一仓一行
--     is_protected = 默认分支是否在保护列表；no_one_can_push 从 data_json 拆
--     ⚠️ 暂缓建议：T1a 采集因 token 权限不足仅部分仓成功（raw 仅 48 行），
--        LEFT JOIN 会把"取不到"当"未保护"(is_protected=0) → 指标3 失真。
--        待 token 提权、T1a 全量跑通后再执行本段。
-- =====================================================================
INSERT INTO openlibing.sdi_rd_efc_branch_protection
    (repo_id, branch_name, is_protected, no_one_can_push, etl_time)
SELECT bi.repo_id,
       bi.name                                                            AS branch_name,
       IF(bp.repo_id IS NOT NULL, 1, 0)                                   AS is_protected,
       IF(json_extract_bool(bp.data_json, '$.no_one_can_push'), 1, 0)     AS no_one_can_push,
       NOW()                                                              AS etl_time
FROM   openlibing.sdi_repo_branch_info bi
LEFT JOIN (
    SELECT repo_id, branch_name, data_json
    FROM   openlibing.raw_repo_branch_protection
    WHERE  CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_repo_branch_protection)
) bp
    ON  bp.repo_id     = bi.repo_id
    AND bp.branch_name = bi.name
WHERE  bi.default_branch = TRUE;

-- =====================================================================
-- [2] 指标3 T1b PR设置 → sdi_rd_efc_pr_setting
--     merge_method/only_allow_merge_if_pipeline_succeeds 顶层
--     approval_required_approvers 在 merge_request_setting 子对象
--     ⚠️ 暂缓建议：T1b 同因 token 权限不足未全量跑通；空表时本段 INSERT 0 行无害，
--        部分数据时 sdi 覆盖不全。待 T1b 跑通后再执行本段。
-- =====================================================================
INSERT INTO openlibing.sdi_rd_efc_pr_setting
    (repo_id, merge_method, only_allow_merge_if_pipeline_succeeds, approval_required_approvers, etl_time)
SELECT repo_id,
       get_json_string(data_json, '$.merge_method')                                     AS merge_method,
       IF(json_extract_bool(data_json, '$.only_allow_merge_if_pipeline_succeeds'),1,0)  AS only_allow_merge_if_pipeline_succeeds,
       json_extract_int(data_json, '$.merge_request_setting.approval_required_approvers') AS approval_required_approvers,
       NOW()                                                                            AS etl_time
FROM   openlibing.raw_repo_pr_setting
WHERE  CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_repo_pr_setting);

-- =====================================================================
-- [3] 指标14 Release → sdi_rd_efc_release
--     has_sha256_asset / has_signature_asset 按 assets[].name 正则派生
--     （GitCode 实际命名为 *.sha256sum；签名资产实测普遍缺失）
-- =====================================================================
truncate table sdi_rd_efc_release_info;
INSERT INTO openlibing.sdi_rd_efc_release_info
    (repo_id, release_tag, release_name, published_at, prerelease, target_commitish,
     author_login, assets_json, has_sha256_asset, has_signature_asset, etl_time)
SELECT repo_id,
       release_tag,
       get_json_string(data_json, '$.name')                                 AS release_name,
       CAST(get_json_string(data_json, '$.created_at') AS DATETIME)         AS published_at,
       IF(json_extract_bool(data_json, '$.prerelease'), 1, 0)               AS prerelease,
       get_json_string(data_json, '$.target_commitish')                     AS target_commitish,
       get_json_string(data_json, '$.author.login')                         AS author_login,
       json_extract(data_json, '$.assets')                                  AS assets_json,
       IF(UPPER(IFNULL(CAST(json_extract(data_json, '$.assets[*].name') AS STRING), ''))
          REGEXP '\\.(SHA256|SHA256SUM|SHA256.MD5)', 1, 0)                   AS has_sha256_asset,
       IF(UPPER(IFNULL(CAST(json_extract(data_json, '$.assets[*].name') AS STRING), ''))
          REGEXP '\\.(ASC|SIG|PGP|GPG|MINISIG|PEM|CRT|CER|P7S)', 1, 0)      AS has_signature_asset,
       NOW()                                                                AS etl_time
FROM   openlibing.raw_repo_release_info
WHERE  CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_repo_release_info);

-- =====================================================================
-- [4] 指标17 贡献者 → sdi_rd_efc_repo_contributor
--     raw_repo_contribute_info(贡献者) LEFT JOIN raw_contrib_organize(组织)
--     → 人×组织多行；无组织成员 org_login = ''（IFNULL，配合 sdi 表 NOT NULL 键）
--     2026-10-19 合规：不再写 user_email（敏感字段不落库，sdi 表已移除该列）；
--     T4a 最小化改造后 contributions 为 raw 表独立列，直接引用。
-- =====================================================================
truncate table sdi_rd_efc_repo_contributor;
INSERT INTO openlibing.sdi_rd_efc_repo_contributor
    (repo_id, user_login, contributions_count, org_login, org_name, etl_time)
SELECT c.repo_id,
       c.user_login,
       c.contributions                                  AS contributions_count,
       IFNULL(o.org_login, '')                          AS org_login,
       get_json_string(o.data_json, '$.name')           AS org_name,
       NOW()                                            AS etl_time
FROM   (SELECT * FROM openlibing.raw_repo_contribute_info
        WHERE CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_repo_contribute_info)) c
LEFT JOIN (SELECT * FROM openlibing.raw_contrib_organize
           WHERE CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_contrib_organize)) o
    ON  o.repo_id    = c.repo_id
    AND o.user_login = c.user_login;

-- =====================================================================
-- [5] 指标19 Webhook → sdi_rd_efc_repo_webhook
--     is_active 透传 raw.active（采集层 Sql transform 三态标准化：
--     1=活跃, 0=不活跃, NULL=接口字段缺失/解析异常）
--     password_is_null 透传 raw.password_is_null（采集层判空：password 为
--     NULL/空串/字段缺失 → 1，非空 → 0；明文不落库）→ 指标19 判据
--     "活跃且均配 secret" 即 is_active=1 AND password_is_null=0
--     event_flags_json = NULL（raw 采集未取事件位，如需须回采集补齐）
-- =====================================================================
truncate table sdi_rd_efc_repo_webhook;
INSERT INTO openlibing.sdi_rd_efc_repo_webhook
    (repo_id, webhook_id, webhook_url, is_active, password_is_null, event_flags_json, result_code, created_at, etl_time)
SELECT repo_id,
       webhook_id,
       url               AS webhook_url,
       active            AS is_active,
       password_is_null,
       NULL              AS event_flags_json,
       result_code,
       created_at,
       NOW()             AS etl_time
FROM   openlibing.raw_repo_webhook
WHERE  CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_repo_webhook);

-- =====================================================================
-- [6] 指标2 代码评审人 → sdi_rd_efc_pr_review_reviewer
--     复用 raw_pr_comment_gitcode，owner+repo 反查 repo_id
--     ⚠️ 2026-09-26 修正（三项）：
--        ① 反查源改用 sdi_repo_info（sdi 层保全量，不与 operate_conf 关联、
--           不做扫描范围过滤——范围过滤下放指标层 D1 处理；
--           2026-09-18 "sdi_repo_info 为空表" 的结论已过时，现有 1587 仓，
--           评论可匹配率约 98%）
--        ② 修复 repo_name 拆解 bug：SUBSTRING_INDEX(repo_url,'/',5) 在
--           https://gitcode.com/owner/repo.git 这种 5 段 URL 上返回的是
--           完整 URL 而非第 5 段，JOIN 永不命中（旧版实测清洗 0 行）；
--           改为 SUBSTRING_INDEX(repo_url,'/',-1) 取末段再去 .git
--        ③ sdi_repo_info 存在 142 组同 owner/repo 多 repo_id（JOIN 扇出，
--           不去重时 384 万 raw 会膨胀到 581 万行）；字典按 owner/repo
--           GROUP BY 去重，repo_id 取 MIN(repo_id)
--        ⚠️ 已知坐标系错位（4 仓，待数据侧治理）：operate_conf 与
--           sdi_repo_info 同 owner/repo 但 repo_id 不同（cann/ops-batchinvariant、
--           Ascend/MindIE-Motor、Ascend/MultimodalSDK、cann/shmem）。
--           指标层 D1 的 pr30.repo_id 取自 operate_conf，这 4 仓的评论
--           repo_id（sdi_repo_info 口径）JOIN 不上 → 评审判不到。
--           根因是两表 repo_id 不一致，需在源数据治理（统一 repo_id）或
--           D1 侧对齐后才能消除，与本次清洗逻辑无关。
--     raw_pr_comment_gitcode 无 etl_time 列，不做按日批次过滤（UNIQUE KEY
--     幂等覆盖，同 reviewer 同 PR 多条评论保留最后一次）
--     is_bot = 名称含 bot/robot/[bot]；review_type = body 首个 / 命令(小写)
--     ⚠️ 2026-10-20 口径收紧（design v4.8）：is_effective_review = is_bot=0
--        且 body 任意行存在独立 /lgtm 命令（token 级正则匹配，以空白符为
--        边界，适配 /approve\n/lgtm 跨行连发与 /squash\n/lgtm\n/approve
--        命令束；独立 /approve 不再算评审，/lgtmfoo、/lgtm-cancel 等粘连
--        形态不误伤）。有效评审的 review_type 统一归一 '/lgtm'
--        （指标8 D7 复用本表按 review_type='/lgtm' 统计，口径自动对齐）。
--        重跑链路：sdi[6] → D1 → D4 → D6 → D7
--     ⚠️ 排除 PR 创建人/最近30次合入：在指标计算层按 dwi_rd_efc_pr_info_sum 处理
-- =====================================================================
truncate table sdi_rd_efc_pr_review_reviewer;
INSERT INTO openlibing.sdi_rd_efc_pr_review_reviewer
    (repo_id, pr_number, reviewer_login, reviewer_user_id, review_type, is_bot, is_effective_review, comment_time, etl_time)
-- 性能与正确性优化（2026-09-26，2026-10-20 v4.8 调整）：
--   ① JSON 每字段只解析一次（内层子查询提取，避免同行 8 次 get_json_string）
--   ② 正则只算必要次数：review_type 取首命令一次；has_lgtm 做 token 级
--      匹配一次（is_effective_review 改由 has_lgtm 判定，不再依赖 review_type）
--   ③ GROUP BY 预聚合到"每评审人×每PR 一行"再写入：384 万评论 → 去重后行数，
--      消除 UNIQUE KEY 写入侧海量键冲突的合并代价；同时修复键覆盖 bug——
--      旧写法后写入的行胜出，评审人先 /lgtm 后闲聊会被覆盖成 is_effective_review=0，
--      现 MAX(is_effective_review) 保证"历史上打过 /lgtm（任意行）即有效"，
--      review_type 对有效评审统一归一 '/lgtm'（非有效兜底取首命令）
SELECT t.repo_id,
       t.pr_number,
       t.reviewer_login,
       MAX(t.reviewer_user_id)                                              AS reviewer_user_id,
       CASE WHEN MAX(t.is_effective_review) = 1 THEN '/lgtm'
            ELSE MAX(t.review_type) END                              AS review_type,
       MAX(t.is_bot)                                                        AS is_bot,
       MAX(t.is_effective_review)                                           AS is_effective_review,
       MAX(t.comment_time)                                                  AS comment_time,
       NOW()                                                                AS etl_time
FROM (
    SELECT dic.repo_id,
           c.number       AS pr_number,
           c.login        AS reviewer_login,
           c.uid          AS reviewer_user_id,
           c.review_type,
           c.is_bot,
           IF(c.is_bot = 1, 0, c.has_lgtm)                        AS is_effective_review,
           c.comment_time
    FROM (
        -- 内层：每字段只做一次 JSON 解析 / 一次正则
        SELECT owner,
               repo,
               number,
               get_json_string(data_json, '$.user.login')  AS login,
               get_json_string(data_json, '$.user.id')     AS uid,
               CONCAT('/', LOWER(IFNULL(regexp_extract(get_json_string(data_json,'$.body'),
                                                       '^/([A-Za-z0-9_-]+)', 1), '其他'))) AS review_type,
               -- v4.8：body 任意行存在独立 /lgtm 命令（空白符边界 token 匹配，
               -- 覆盖 /lgtm 独发、/lgtm\n/approve、/approve\n/lgtm 跨行、
               -- /lgtm\n\n/approve 空行分隔；/lgtmfoo、/lgtm-cancel 不误伤）
               IF(lower(get_json_string(data_json,'$.body')) REGEXP
                  '(^|[[:space:]])/lgtm($|[^a-z0-9_-])', 1, 0) AS has_lgtm,
               IF( LOWER(IFNULL(get_json_string(data_json,'$.user.login'),'')) LIKE '%bot%'
                 OR LOWER(IFNULL(get_json_string(data_json,'$.user.login'),'')) LIKE '%robot%'
                 OR LOWER(IFNULL(get_json_string(data_json,'$.user.login'),'')) LIKE '%[bot]%'
                 , 1, 0)                                AS is_bot,
               CAST(get_json_string(data_json, '$.created_at') AS DATETIME) AS comment_time
        FROM   openlibing.raw_pr_comment_gitcode
    ) c
    INNER JOIN (
        -- owner/repo → repo_id 字典：仅 sdi_repo_info，按 owner/repo 去重防扇出，
        -- repo_id 取 MIN（同 owner/repo 多登记时选最小 id 作为 canonical）
        SELECT t.repo_owner,
               t.repo_name,
               MIN(t.repo_id) AS repo_id
        FROM (
            SELECT repo_id,
                   SUBSTRING_INDEX(SUBSTRING_INDEX(repo_url, '/', 4), '/', -1) AS repo_owner,
                   CASE WHEN RIGHT(SUBSTRING_INDEX(repo_url, '/', -1), 4) = '.git'
                        THEN LEFT(SUBSTRING_INDEX(repo_url, '/', -1),
                                  CHAR_LENGTH(SUBSTRING_INDEX(repo_url, '/', -1)) - 4)
                        ELSE SUBSTRING_INDEX(repo_url, '/', -1)
                   END                                                           AS repo_name
            FROM   openlibing.sdi_repo_info
        ) t
        GROUP BY t.repo_owner, t.repo_name
    ) dic
        ON  dic.repo_owner = c.owner
        AND dic.repo_name  = c.repo
    WHERE  c.login IS NOT NULL
           -- 过滤 user.login 缺失的评论（实测 384 万条中 276 条）：无评审人身份，
           -- 无法归属评审也无法做 D1 的 reviewer<>creator 判定，不落库
) t
GROUP BY t.repo_id, t.pr_number, t.reviewer_login;

-- =====================================================================
-- [7] Euler 软件包详情 → sdi_rd_efc_euler_package
--     package_name 由 raw.spec_url 尾段反解（去 .git）；
--     commit_time 接口返回 unix 秒字符串，FROM_UNIXTIME 转 DATETIME。
--     反解依赖 URL 规整性：regexp 未命中 → NULL，可按 package_name IS NULL
--     监控 URL 模式变化（采集时已实测 4951 包 100% 匹配）。
-- =====================================================================
INSERT INTO openlibing.sdi_rd_efc_euler_package
    (os_project, package_name, commit_id, commit_time, git_repo, git_tag, spec_branch, spec_url, specify_commit, etl_time)
SELECT os_project,
       regexp_extract(spec_url, '([^/]+)\\.git$', 1)                       AS package_name,
       get_json_string(data_json, '$.commit_id')                          AS commit_id,
       FROM_UNIXTIME(CAST(get_json_string(data_json, '$.commit_time') AS BIGINT)) AS commit_time,
       get_json_string(data_json, '$.git_repo')                            AS git_repo,
       get_json_string(data_json, '$.git_tag')                            AS git_tag,
       get_json_string(data_json, '$.spec_branch')                        AS spec_branch,
       spec_url,
       get_json_string(data_json, '$.specify_commit')                     AS specify_commit,
       NOW()                                                               AS etl_time
FROM   openlibing.raw_euler_package_info
WHERE  CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_euler_package_info);

--(8)commit信息
truncate table sdi_repo_commit_log;
INSERT INTO sdi_repo_commit_log (
    repo_id,
    repo_git_url,
    repo_name,
    branch_name,
    commit_hash,
    author_name,
    author_email,
    commit_time,
    commit_title,
    author_username,
    author_domain,
    author_name_clean,
    is_bot,
    etl_time
)
SELECT
    repo_id,
    repo_git_url,
    repo_name,
    branch_name,
    commit_hash,
    author_name,
    author_email,
    commit_time,
    commit_title,
    -- 邮箱 @ 前缀作为账号名；无邮箱时回退作者名
    CASE
        WHEN author_email IS NOT NULL AND LOCATE('@', author_email) > 0
            THEN LOWER(SUBSTRING_INDEX(author_email, '@', 1))
        ELSE NULL
    END                                                                     AS author_username,
    -- 邮箱 @ 后缀作为域名；无邮箱时置 NULL
    CASE
        WHEN author_email IS NOT NULL AND LOCATE('@', author_email) > 0
            THEN LOWER(SUBSTRING_INDEX(author_email, '@', -1))
        ELSE NULL
    END                                                                     AS author_domain,
    -- 作者名清洗：trim + 合并连续空白 + 回退
    CASE
        WHEN author_name IS NOT NULL AND LENGTH(TRIM(author_name)) > 0
            THEN REGEXP_REPLACE(TRIM(author_name), '[[:space:]]+', ' ')
        ELSE 'unknown'
    END                                                                     AS author_name_clean,
    -- 机器人判定：
    -- 1 判定为机器人（名称/邮箱含明显 bot 特征）
    -- 0 判定非机器人（名称和邮箱都有内容且无 bot 特征）
    -- 2 未知（名称和邮箱都为空，属机器人生成概率高，此处归 1；若不确定可留 2）
    CASE
        WHEN author_name IS NOT NULL
             AND (LOWER(author_name) LIKE '%[bot]%'
                  OR LOWER(author_name) LIKE '%bot'
                  OR LOWER(author_name) LIKE 'bot%')
            THEN 1
        WHEN author_email IS NOT NULL
             AND (LOCATE('noreply', LOWER(author_email)) > 0
                  OR LOCATE('[bot]', LOWER(author_email)) > 0)
            THEN 1
        WHEN (author_name IS NULL OR LENGTH(TRIM(author_name)) = 0)
             AND (author_email IS NULL OR LENGTH(TRIM(author_email)) = 0)
            THEN 2
        ELSE 0
    END                                                                     AS is_bot,
    NOW()                                                                   AS etl_time
FROM raw_repo_commit_log;

-- =====================================================================
-- [9] 指标18 用户公司 → sdi_rd_efc_user_company
--     raw_user_company（T7 每日采集，users/:username.company 口径，2026-10-16 拍板）
--     → 一人一行；company 原值落库（缺失/空串统一 NULL = "未填写"）；
--     华为系写法归一（huawei/hw/华为→华为技术有限公司）在指标层 D2 处理，
--     sdi 层不做归一（保留全面数据，过滤/归一下放指标层）。
--     ⚠ 依赖 T4a 先跑（T7 遍历源 = raw_repo_contribute_info 当日批次）。
--     2026-10-19：T7 合规最小化改造后 raw 表只存 company/name 两列
--     （不再存含 email 的 JSON 全量原文），本段改为直接列引用。
-- =====================================================================
truncate table sdi_rd_efc_user_company;
INSERT INTO openlibing.sdi_rd_efc_user_company
    (user_login, company, name, etl_time)
SELECT user_login,
       NULLIF(company, '') AS company,
       name                AS name,
       NOW()               AS etl_time
FROM   openlibing.raw_user_company
WHERE  CAST(etl_time AS DATE) = (SELECT MAX(CAST(etl_time AS DATE)) FROM openlibing.raw_user_company);
