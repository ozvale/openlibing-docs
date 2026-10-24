-- =====================================================================
-- 贡献者链路 email 敏感数据合规清理（2026-10-19）
-- 背景：贡献者相关 raw/sdi 表存储了用户 email（敏感个人信息，一律不落库）：
--   - raw_repo_contribute_info：data_json 存贡献者 JSON 全量原文，9130 行全带 email
--   - sdi_rd_efc_repo_contributor：user_email 列显式清洗落库
--   - raw_user_company：data_json 存用户接口 JSON 全量原文，364 行带真实 email
-- 处理：三表 DROP 重建（新结构不含任何 email 存储通道），由采集/清洗任务重跑回填。
--   重建表结构分别与 raw层6表建表DDL.sql / sdi层6表建表DDL.sql /
--   user_company建表DDL.sql 保持一致（同源复制，勿单独维护）。
-- 执行：生产 Doris 客户端直接执行（本文件仅 DROP/CREATE，无 < > & 转义字符问题）。
-- 执行顺序（重要）：
--   ① 本文件（DROP + CREATE 三表）
--   ② DS 替换 T4a conf（获取贡献者.conf，json_field 最小化）并重跑 T4a
--   ③ DS 重跑 T7（获取用户company.conf 已本地更新，需同步上传 DS）
--   ④ 清洗 [4]（贡献者）+ [9]（用户公司）重跑
--   ⑤ D2-18 等下游按需重跑（company 口径数据无变化，可不动）
-- 幂等性：可重复执行；重跑后数据量应与清理前一致
--   （raw_repo_contribute_info ~9130 / raw_user_company ~3989）。
-- =====================================================================

-- ---------- ① raw_repo_contribute_info（T4a 贡献者，去 data_json 加 contributions）----------
DROP TABLE IF EXISTS raw_repo_contribute_info;
CREATE TABLE IF NOT EXISTS raw_repo_contribute_info
(
    repo_id       BIGINT       NOT NULL COMMENT '仓库ID',
    user_login    VARCHAR(128) NOT NULL COMMENT '贡献者login(contributors.name)',
    etl_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)',
    owner         VARCHAR(128) NOT NULL COMMENT '仓库所属组织/用户',
    repo          VARCHAR(128) NOT NULL COMMENT '仓库名',
    contributions INT          NULL     COMMENT '贡献次数(contributors.contributions)'
)
UNIQUE KEY (repo_id, user_login)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- ② sdi_rd_efc_repo_contributor（清洗 [4]，去 user_email 列）----------
DROP TABLE IF EXISTS sdi_rd_efc_repo_contributor;
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

-- ---------- ③ raw_user_company（T7 用户公司，去 data_json 加 company/name）----------
DROP TABLE IF EXISTS raw_user_company;
CREATE TABLE IF NOT EXISTS raw_user_company
(
    user_login VARCHAR(128) NOT NULL COMMENT '用户login(贡献者/PR作者)',
    etl_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)',
    company    VARCHAR(256) NULL     COMMENT '所属公司(users.company原值,未填写为NULL)',
    name       VARCHAR(256) NULL     COMMENT '用户昵称(users.name)'
)
UNIQUE KEY (user_login)
DISTRIBUTED BY HASH(user_login) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- 验证（执行 + 重跑后自查）----------
-- 清理后重跑回填，确认无 email 残留：
--   SELECT COUNT(*) FROM raw_repo_contribute_info;            -- 预期 ~9130
--   SELECT COUNT(*) FROM raw_user_company;                     -- 预期 ~3989
--   SELECT COUNT(*) FROM sdi_rd_efc_repo_contributor;          -- 预期与清理前一致
--   （三表新结构已无任何 email 存储字段，无需再查 email 内容）
