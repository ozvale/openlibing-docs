-- sdi_repo_commit_log 代码仓 commit 信息 sdi 清洗层表
-- 数据来源: raw_repo_commit_log（raw 层，脚本采集）
--
-- 设计要点：
-- 1. 粒度与 raw 一致: (repo_id, branch_name, commit_hash) 唯一，天然不重复。
-- 2. 作者规范化派生列:
--    - author_username : 从 author_email 提取 @ 前缀（等于 git 账号名）
--    - author_domain   : 从 author_email 提取 @ 后缀域名
--    - is_bot          : 常见机器人账号判定（名字/邮箱含 bot、noreply 等）
--    - author_name_clean: 清洗后的作者名（trim + 统一空白），空名回退占位
-- 3. UNIQUE KEY 保证重复清洗覆盖，不堆积。

CREATE TABLE IF NOT EXISTS sdi_repo_commit_log (
    repo_id           BIGINT        COMMENT '仓库ID',
    branch_name       VARCHAR(200)  COMMENT '分支名',
    commit_hash       VARCHAR(64)   COMMENT 'commit 完整 SHA',
    repo_git_url      VARCHAR(500)  COMMENT '仓库Git URL',
    repo_name         VARCHAR(200)  COMMENT '仓库名',
    author_name       VARCHAR(200)  COMMENT '作者名（原始）',
    author_email      VARCHAR(255)  COMMENT '作者邮箱（原始）',
    commit_time       DATETIME      COMMENT 'commit 提交时间（author 时间）',
    commit_title      VARCHAR(500)  COMMENT 'commit 标题',
    -- 作者规范化派生字段
    author_username   VARCHAR(255)  COMMENT '作者账号名（邮箱@前缀）',
    author_domain     VARCHAR(255)  COMMENT '作者邮箱域名（@后缀）',
    author_name_clean VARCHAR(200)  COMMENT '清洗后作者名（trim+统一空白，空回退）',
    is_bot            TINYINT       COMMENT '是否机器人 0:否 1:是 2:未知',
    etl_time          DATETIME      COMMENT 'ETL 清洗写入时间'
) ENGINE=OLAP
UNIQUE KEY (repo_id, branch_name, commit_hash)
COMMENT '代码仓 commit 信息 sdi 清洗层'
DISTRIBUTED BY HASH(repo_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "3"
);
