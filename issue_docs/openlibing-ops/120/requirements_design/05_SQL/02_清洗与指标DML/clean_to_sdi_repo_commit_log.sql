-- sdi_repo_commit_log 清洗 SQL
-- 从 raw_repo_commit_log 全量清洗覆盖写入 sdi 层（UNIQUE KEY 自动覆盖）
-- 可在 DolphinScheduler 的 SQL 节点直接执行

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
