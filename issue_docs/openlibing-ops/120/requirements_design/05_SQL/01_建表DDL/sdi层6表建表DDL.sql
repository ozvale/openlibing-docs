-- =====================================================================
-- sdi 层建表 DDL（指标 3/14/17/19 + 指标2 清洗目标表 + Euler 软件包详情）
-- 引擎：Apache Doris 3.x；建在 openlibing 库（与 raw 同库）
-- 约定：Unique 模型保证 DML 重跑幂等（同 key 覆盖，不追加重复行）；
--       etl_time 为 value 列，由 DML 的 NOW() 填充，记录清洗时间。
-- 注意：Doris Unique 模型 KEY 列必须是建表声明中【按顺序连续】的列；
--       KEY 列不允许 NULL，故 sdi_rd_efc_repo_contributor.org_login 用 NOT NULL DEFAULT ''
--       配合 DML 的 IFNULL(o.org_login, '') 写入（NULL 进 Unique KEY 不去重，会累积重复行）。
-- 前置：先于 sdi层清洗DML.sql 执行（一次性建表）。
-- =====================================================================

-- ---------- [1] 指标3 T1a 分支保护 ----------
CREATE TABLE IF NOT EXISTS sdi_rd_efc_branch_protection
(
    repo_id         BIGINT       NOT NULL COMMENT '仓库ID(关联sdi_repo_info.repo_id)',
    branch_name     VARCHAR(128) NOT NULL COMMENT '分支名',
    is_protected    TINYINT      NULL     COMMENT '默认分支是否受保护(1=是,0=否)',
    no_one_can_push TINYINT      NULL     COMMENT '保护分支是否禁止任何人推送(1=是,0=否)',
    etl_time        DATETIME     NULL     COMMENT '清洗时间'
)
UNIQUE KEY (repo_id, branch_name)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [2] 指标3 T1b PR/合并设置 ----------
CREATE TABLE IF NOT EXISTS sdi_rd_efc_pr_setting
(
    repo_id                               BIGINT      NOT NULL COMMENT '仓库ID',
    merge_method                          VARCHAR(32) NULL     COMMENT '合并方式(merge/squash/rebase)',
    only_allow_merge_if_pipeline_succeeds TINYINT     NULL     COMMENT '流水线成功才允许合并(1=是,0=否)',
    approval_required_approvers           INT         NULL     COMMENT '合并所需批准人数',
    etl_time                              DATETIME    NULL     COMMENT '清洗时间'
)
UNIQUE KEY (repo_id)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [3] 指标14 Release ----------
CREATE TABLE IF NOT EXISTS sdi_rd_efc_release_info
(
    repo_id             BIGINT       NOT NULL COMMENT '仓库ID',
    release_tag         VARCHAR(256) NOT NULL COMMENT 'release tag(tag_name)',
    release_name        VARCHAR(256) NULL     COMMENT 'release 标题',
    published_at        DATETIME     NULL     COMMENT '发布时间(接口created_at)',
    prerelease          TINYINT      NULL     COMMENT '是否预发布(1=是,0=否)',
    target_commitish    VARCHAR(64)  NULL     COMMENT '目标分支/commit',
    author_login        VARCHAR(128) NULL     COMMENT '发布者login',
    assets_json         JSON         NULL     COMMENT '资产数组原文',
    has_sha256_asset    TINYINT      NULL     COMMENT '含sha256校验资产(1=是,0=否)',
    has_signature_asset TINYINT      NULL     COMMENT '含签名资产(1=是,0=否)',
    etl_time            DATETIME     NULL     COMMENT '清洗时间'
)
UNIQUE KEY (repo_id, release_tag)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [4] 指标17 贡献者(人×组织) ----------
-- ⚠ 合规（2026-10-19）：移除 user_email 列（贡献者 email 属敏感个人信息，一律不落库）；
--   旧表含该列且已落数，需 DROP 重建后由清洗 [4] 重跑回填：
--     DROP TABLE IF EXISTS sdi_rd_efc_repo_contributor;
CREATE TABLE IF NOT EXISTS sdi_rd_efc_repo_contributor
(
    repo_id             BIGINT       NOT NULL COMMENT '仓库ID',
    user_login          VARCHAR(128) NOT NULL COMMENT '贡献者login',
    org_login           VARCHAR(128) NOT NULL DEFAULT '' COMMENT '所属组织login(空串=无组织/未匹配)',
    contributions_count INT          NULL     COMMENT '贡献次数(contributions)',
    org_name            VARCHAR(256) NULL     COMMENT '组织名称',
    etl_time            DATETIME     NULL     COMMENT '清洗时间'
)
UNIQUE KEY (repo_id, user_login, org_login)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [5] 指标19 Webhook ----------
CREATE TABLE IF NOT EXISTS sdi_rd_efc_repo_webhook
(
    repo_id         BIGINT       NOT NULL COMMENT '仓库ID',
    webhook_id      BIGINT       NOT NULL COMMENT 'webhook id',
    webhook_url     VARCHAR(512) NULL     COMMENT '回调url',
    is_active       TINYINT      NULL     COMMENT '激活三态(1=活跃,0=不活跃,NULL=接口字段缺失/解析异常)',
    password_is_null TINYINT    NULL     COMMENT 'password是否为空(1=空/未配置secret,0=非空;指标19判据,透传raw)',
    event_flags_json JSON        NULL     COMMENT '事件订阅位(采集层未取,预留NULL,如需须回采集补齐)',
    result_code     INT          NULL     COMMENT '连接测试返回码',
    created_at      DATETIME     NULL     COMMENT 'webhook创建时间',
    etl_time        DATETIME     NULL     COMMENT '清洗时间'
)
UNIQUE KEY (repo_id, webhook_id)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [6] 指标2 PR评审人 ----------
-- 口径：同 reviewer 同 PR 覆盖保留最后一次评论（unique key 不含 etl_time），
--       指标2 关心"是否有人评审"，非逐条评论明细。
CREATE TABLE IF NOT EXISTS sdi_rd_efc_pr_review_reviewer
(
    repo_id             BIGINT       NOT NULL COMMENT '仓库ID',
    pr_number           INT          NOT NULL COMMENT 'PR编号',
    reviewer_login      VARCHAR(128) NOT NULL COMMENT '评审人login',
    reviewer_user_id    VARCHAR(64)  NULL     COMMENT '评审人用户ID',
    review_type         VARCHAR(64)  NULL     COMMENT '评论命令类型(/lgtm /approve 其他)',
    is_bot              TINYINT      NULL     COMMENT '是否机器人(1=是,0=否)',
    is_effective_review TINYINT      NULL     COMMENT '是否有效评审(1=是,0=否)',
    comment_time        DATETIME     NULL     COMMENT '评论时间',
    etl_time            DATETIME     NULL     COMMENT '清洗时间'
)
UNIQUE KEY (repo_id, pr_number, reviewer_login)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [7] Euler 软件包详情 ----------
-- 一包一行；package_name 由 raw.spec_url 尾段反解（去 .git），
-- 已实测 4951 包与接口 spec_commits map key 100% 一致。
CREATE TABLE IF NOT EXISTS sdi_rd_efc_euler_package
(
    os_project     VARCHAR(128) NOT NULL COMMENT 'Euler工程名(openEuler-24.03-LTS-SP4:everything)',
    package_name   VARCHAR(256) NOT NULL COMMENT '软件包名(spec_url尾段去.git反解)',
    commit_id      VARCHAR(64)  NULL     COMMENT '当前spec commit ID',
    commit_time    DATETIME     NULL     COMMENT 'commit时间(接口unix秒转换)',
    git_repo       VARCHAR(512) NULL     COMMENT '内部git仓相对路径',
    git_tag        VARCHAR(128) NULL     COMMENT 'git tag(常为空串)',
    spec_branch    VARCHAR(128) NULL     COMMENT 'spec分支(如openEuler-24.03-LTS-SP4)',
    spec_url       VARCHAR(512) NULL     COMMENT '包spec源码仓URL(溯源)',
    specify_commit VARCHAR(64)  NULL     COMMENT '指定commit方式(branch/tag/commit)',
    etl_time       DATETIME     NULL     COMMENT '清洗时间'
)
UNIQUE KEY (os_project, package_name)
DISTRIBUTED BY HASH(os_project) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");
