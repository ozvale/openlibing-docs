-- =====================================================================
-- raw 层建表 DDL（指标 3/14/17/19 接口采集 + Euler 软件包详情）
-- 引擎：Apache Doris 3.x；库名由连接配置指定（无库前缀，建在当前连接库）
-- 约定：GitCode 域表带 repo_id（关联 sdi_repo_info）；euler 域例外，以 os_project 标识。
--   etl_time：普通 value 列（非主键），由库 DEFAULT CURRENT_TIMESTAMP 自动插入，
--            记录采集时间；每天清表重查只保留当天批次。
--   data_json 存接口原文 JSON；webhook 表特例：password 仅判空落 password_is_null，不落明文。
-- 注意：Doris Unique 模型 UNIQUE KEY 列必须是建表声明中【按顺序连续】的列，
--       故仅实体键(repo_id + 实体键)入 key 区放最前；etl_time 为 value 列不入 key。
-- =====================================================================

-- ---------- T1a 分支保护（指标3）----------
CREATE TABLE IF NOT EXISTS raw_repo_branch_protection
(
    repo_id     BIGINT       NOT NULL COMMENT '仓库ID(关联sdi_repo_info.repo_id)',
    branch_name VARCHAR(128) NOT NULL COMMENT '保护分支名',
    etl_time    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)',
    owner       VARCHAR(128) NOT NULL COMMENT '仓库所属组织/用户',
    repo        VARCHAR(128) NOT NULL COMMENT '仓库名',
    data_json   JSON         NULL     COMMENT '该保护分支接口返回JSON全量(原文)'
)
UNIQUE KEY (repo_id, branch_name)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- T1b PR/合并设置（指标3）----------
CREATE TABLE IF NOT EXISTS raw_repo_pr_setting
(
    repo_id   BIGINT      NOT NULL COMMENT '仓库ID',
    etl_time  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)',
    owner     VARCHAR(128) NOT NULL COMMENT '仓库所属组织/用户',
    repo      VARCHAR(128) NOT NULL COMMENT '仓库名',
    data_json JSON        NULL     COMMENT 'pull_request_settings JSON全量(含merge_request_setting子对象)'
)
UNIQUE KEY (repo_id)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- T3 Release（指标14）----------
CREATE TABLE IF NOT EXISTS raw_repo_release_info
(
    repo_id     BIGINT      NOT NULL COMMENT '仓库ID',
    release_tag VARCHAR(256) NOT NULL COMMENT 'release tag(tag_name)',
    etl_time    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)',
    owner       VARCHAR(128) NOT NULL COMMENT '仓库所属组织/用户',
    repo        VARCHAR(128) NOT NULL COMMENT '仓库名',
    data_json   JSON        NULL     COMMENT '单个release JSON全量(含assets,供sha256/签名派生)'
)
UNIQUE KEY (repo_id, release_tag)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- T4a 贡献者（指标17,第一跳）----------
-- ⚠ 合规最小化（2026-10-19）：不再存贡献者 JSON 全量原文（data_json，含 email
--   敏感字段，一律不落库；接口实测仅 name/contributions/email 三字段，name 已入
--   user_login 列），采集任务改为 json_field 仅提取 contributions；
--   旧表含 data_json 列且已落数（9130 行全带 email），需 DROP 重建后由 T4a 重跑回填：
--     DROP TABLE IF EXISTS raw_repo_contribute_info;
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

-- ---------- T4b 贡献者所属组织（指标17,第二跳）----------
CREATE TABLE IF NOT EXISTS raw_contrib_organize
(
    repo_id    BIGINT       NOT NULL COMMENT '仓库ID',
    user_login VARCHAR(128) NOT NULL COMMENT '贡献者login',
    org_login  VARCHAR(128) NULL     COMMENT '所属组织login(可为空=无组织)',
    etl_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)',
    owner      VARCHAR(128) NOT NULL COMMENT '仓库所属组织/用户',
    repo       VARCHAR(128) NOT NULL COMMENT '仓库名',
    data_json  JSON         NULL     COMMENT '组织行JSON全量(id/login/path/name/description/avatar_url)'
)
UNIQUE KEY (repo_id, user_login, org_login)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- T5 Webhook（指标19）----------
-- 注意：不存 password 明文（json_field 根本不取 password 字段），故无密码列。
--       created_at 为 webhook 创建时间（接口字段），保留。
CREATE TABLE IF NOT EXISTS raw_repo_webhook
(
    repo_id     BIGINT       NOT NULL COMMENT '仓库ID',
    webhook_id  BIGINT       NOT NULL COMMENT 'webhook id',
    etl_time    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)',
    owner       VARCHAR(128) NOT NULL COMMENT '仓库所属组织/用户',
    repo        VARCHAR(128) NOT NULL COMMENT '仓库名',
    url         VARCHAR(512) NULL     COMMENT 'webhook回调url',
    active      TINYINT      NULL     COMMENT '激活状态三态(1=活跃,0=不活跃,NULL=接口字段缺失/解析异常)',
    password_is_null TINYINT NULL     COMMENT 'password是否为空(1=空/未配置secret,0=非空;只存判空结果,不存密码明文)',
    result_code INT          NULL     COMMENT '连接测试返回码',
    created_at  DATETIME     NULL     COMMENT 'webhook创建时间(created_at)'
)
UNIQUE KEY (repo_id, webhook_id)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- Euler 软件包详情（eulermaker data-api） ----------
-- 一包一行；data_path=spec_commits.* 由插件拆 map 值为数组逐包展开，
-- 包名(map key)不在包对象内，sdi 层由 spec_url 尾段反解（实测 4951 包 100% 一致）；
-- custom_packages 当前快照为 null，暂不采集，有数据后另加任务。
CREATE TABLE IF NOT EXISTS raw_euler_package_info
(
    os_project VARCHAR(128) NOT NULL COMMENT 'Euler工程名(openEuler-24.03-LTS-SP4:everything)',
    spec_url   VARCHAR(512) NOT NULL COMMENT '包spec源码仓URL(包名反解依据:尾段去.git=包名)',
    data_json  JSON         NULL     COMMENT '包详情原文{commit_id,commit_time,git_repo,git_tag,spec_branch,spec_url,specify_commit}',
    etl_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间(库自动插入)'
)
UNIQUE KEY (os_project, spec_url)
DISTRIBUTED BY HASH(os_project) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");
