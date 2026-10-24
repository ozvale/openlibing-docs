-- =====================================================================
-- 贡献者公司采集建表 DDL（指标18 CONTRIBUTORS company 口径，2026-10-16 拍板）
-- 引擎：Apache Doris 3.x；建在 openlibing 库（raw/sdi 同库）
-- 背景：指标18 归属口径从"平台组织"（T4b orgs 链路）切换为"用户所属公司"
--       （GET /api/v5/users/:username 的 company 字段，用户自填）。
--       company 为空即未知、不计入 N（推动用户补填资料）；
--       华为系写法归一（huawei/hw/华为→华为技术有限公司）在指标层 D2 处理，
--       sdi 层只存原值（sdi 保留全面数据，过滤/归一下放指标层）。
-- 前置：先于 sdi层清洗DML.sql [9] 执行（一次性建表）。
-- 注意：Doris Unique 模型 KEY 列必须是建表声明中【按顺序连续】的列；
--       本组表为用户维度（无 repo_id，粒度例外同 euler 域），
--       仅 user_login 入 key 区放最前，etl_time 为 value 列。
-- =====================================================================

-- ---------- T7 用户公司（指标18，raw 层）----------
-- 一人一行；404（用户注销/改名）由采集任务 error_handling=continue 跳过，不落行；
-- 每日全量重拉本日活跃贡献者（量级与 T4b 同级且更低，fetch 限流见 获取用户company.conf）。
-- ⚠ 合规最小化（2026-10-19）：不再存接口 JSON 全量原文（data_json，含用户 email
--   等敏感字段，一律不落库），采集任务改为 json_field 仅提取 company/name 两字段；
--   旧表含 data_json 列且已落数（364 行带真实 email），需 DROP 重建后由 T7 重跑回填：
--     DROP TABLE IF EXISTS raw_user_company;
--     （再执行本 DDL，随后重跑 T7 采集任务）
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

-- ---------- 指标18 用户公司（sdi 层）----------
-- 一人一行；company 存接口原值（不归一、不去空——归一在指标层 D2 处理）；
-- company 缺失/空串统一清洗为 NULL（"未填写"语义）。
CREATE TABLE IF NOT EXISTS sdi_rd_efc_user_company
(
    user_login VARCHAR(128) NOT NULL COMMENT '用户login',
    company    VARCHAR(256) NULL     COMMENT '所属公司(users.company原值,华为系归一在指标层D2)',
    name       VARCHAR(256) NULL     COMMENT '用户昵称(users.name)',
    etl_time   DATETIME     NULL     COMMENT '清洗时间'
)
UNIQUE KEY (user_login)
DISTRIBUTED BY HASH(user_login) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");
