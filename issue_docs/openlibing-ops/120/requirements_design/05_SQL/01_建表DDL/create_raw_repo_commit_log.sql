-- raw_repo_commit_log 代码仓 commit 信息原始数据表
-- 存储每个 repo/branch 上 commit 的基础元数据，一行一条 commit
--
-- 设计要点：
-- 1. 唯一键 (repo_id, branch_name, commit_hash)：Doris UNIQUE KEY 模型按该键去重,
--    同一 commit 重复扫描时以新值覆盖旧值（不堆积）。
-- 2. commit 元数据不可变，故同键覆盖后值一致，天然满足每日增量扫描 + 防丢。
-- 3. commit_title 仅存首行标题（控制存储量）。
-- 4. scan_time 为本次写入时间，非 commit 时间。

CREATE TABLE IF NOT EXISTS raw_repo_commit_log (
    repo_id           BIGINT        COMMENT '仓库ID',
	branch_name       VARCHAR(200)  COMMENT '分支名',
	commit_hash       VARCHAR(64)   COMMENT 'commit 完整 SHA',
    repo_git_url      VARCHAR(500)  COMMENT '仓库Git URL',
    repo_name         VARCHAR(200)  COMMENT '仓库名',
    author_name       VARCHAR(200)  COMMENT '作者名',
    author_email      VARCHAR(255)  COMMENT '作者邮箱',
    commit_time       DATETIME      COMMENT 'commit 提交时间（author 时间，已转本地无时区）',
    commit_title      VARCHAR(500)  COMMENT 'commit 标题（首行）',
    scan_time         DATETIME      COMMENT '扫描写入时间'
) ENGINE=OLAP
UNIQUE KEY (repo_id, branch_name, commit_hash)
COMMENT '代码仓 commit 信息原始数据表'
DISTRIBUTED BY HASH(repo_id) BUCKETS 10
PROPERTIES (
    "replication_num" = "3"
);
