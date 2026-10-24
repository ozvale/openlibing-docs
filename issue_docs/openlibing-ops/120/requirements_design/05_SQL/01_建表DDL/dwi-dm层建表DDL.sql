-- =====================================================================
-- dwi / dm 层建表 DDL（代码安全检查评分看板 · design.md v4 §7）
-- 引擎：Apache Doris 3.x；建在 openlibing 库
-- 共 9 张：dwi 明细 7 张 + dm 宽表 1 张 + 权重配置表 1 张
--   ① dwi_rd_efc_security_maintained_scan   指标17 MAINTAINED（SQL）
--   ② dwi_rd_efc_security_pr_scan           指标7 CODE_REVIEW + 10 CI_TESTS（SQL）
--   ③ dwi_rd_efc_security_branch_protect_scan 指标8（✅ 2026-09-28 规则更新转正 v4.4）
--   ④ dwi_rd_efc_security_file_scan         指标2/3/4/6/8(明细)/12/14/15（Python P1）
--   ⑤ dwi_rd_efc_security_license_scan      指标1 LICENSE（Python P2 scancode）
--   ⑥ dwi_rd_efc_security_meta_api_scan     指标9/11/18（SQL）
--   ⑦ dwi_rd_efc_security_vuln_scan         指标16 VULNS（✅ 2026-09-22 接入，源表 sdi_rd_efc_cve_details）
--   ⑧ dm_rd_efc_security_scan_score         汇聚宽表（18 指标 + 两套加权分 + 分母快照 + 亮灯）
--   ⑨ dm_rd_efc_security_metric_conf        指标权重配置（18 行静态；D4 汇聚取权重，
--                                            后端渲染取指标元数据；UPDATE weight 下批生效）
--   ⑩ dwi_rd_efc_security_copyright_file_detail 版权逐文件明细（2026-10-07 明细试验，
--                                            不合格文件全量落库，看板分页）
-- 与 design.md §7 的差异（均已核实必要）：
--   a. Doris Unique 模型 KEY 列必须为建表列的【前缀且连续】，故 repo_id /
--      metric_code / scan_time 统一前置（design.md 原稿 repo_url 夹在 KEY 列之间，非法）。
--   b. KEY 列不允许 NULL：scan_time / metric_code 加 NOT NULL。
--   c. ① maintained 表以 commit_cnt_90d / issue_cnt_90d 计数列 + detail_json
--      （存样本 id）替代 design.md 的 ids JSON——90 天 commit 可达千级，
--      全量 ids 落 JSON 会爆行，明细可随时回 sdi 表反查。
--   d. 各表补 etl_time（value 列，DML NOW() 填充），与 sdi 层惯例一致。
-- 前置：先于 dwi-dm指标计算DML.sql 执行（一次性建表）。
-- =====================================================================

-- ---------- [1] 指标17 项目维护 ----------
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_maintained_scan
(
    repo_id        INT          NOT NULL COMMENT '仓库ID',
    scan_time      DATETIME     NOT NULL COMMENT '批次扫描时间戳(全指标统一)',
    repo_url       VARCHAR(512) NULL     COMMENT '仓库地址',
    repo_status    VARCHAR(32)  NULL     COMMENT '仓库状态(archived/normal/suspend/not_exist/unknown)',
    commit_cnt_90d INT          NULL     COMMENT '近90天commit数(默认分支,待S2数据)',
    issue_cnt_90d  INT          NULL     COMMENT '近90天新建issue数',
    detail_json    JSON         NULL     COMMENT '明细{sample_commit_ids,sample_issue_ids}',
    score          DECIMAL(5,2) NULL     COMMENT '指标17得分=min(10,10*(commit+issue)/13);NA=NULL',
    is_na          TINYINT      NULL     COMMENT '是否NA(归档/创建不足90天=1)',
    etl_time       DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [2] 指标7 代码评审 + 指标10 CI测试 ----------
-- 一仓一扫描批次一行：指标7/10 共用同一 PR 集合（近30次已合入、剔机器人），NA 条件相同
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_pr_scan
(
    repo_id             INT          NOT NULL COMMENT '仓库ID',
    scan_time           DATETIME     NOT NULL COMMENT '批次扫描时间戳',
    repo_url            VARCHAR(512) NULL     COMMENT '仓库地址',
    pr_total_count      INT          NULL     COMMENT '近30次已合入PR数(剔机器人后)',
    pr_numbers          JSON         NULL     COMMENT 'PR编号列表(merged_at倒序)',
    pr_reviewed_count   INT          NULL     COMMENT '已评审PR数(有效评审且非创建者本人)',
    pr_unreviewed_detail JSON        NULL     COMMENT '未评审PR明细[{number,merged_at}]',
    score_review        DECIMAL(5,2) NULL     COMMENT '指标7得分=10*已评审/总数;NA=NULL',
    pr_ci_detail        JSON         NULL     COMMENT '每PR是否跑CI[{number,has_ci}]',
    score_ci            DECIMAL(5,2) NULL     COMMENT '指标10得分=10*有CI/总数;NA=NULL',
    is_na               TINYINT      NULL     COMMENT '是否NA(剔机器人后PR数=0)',
    etl_time            DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [3] 指标8 分支保护（✅ 2026-09-28 规则更新转正 v4.4，D7 产出） ----------
-- 规则坍缩为二元：平台默认满足 T1/T2/T3 得基础 8 分；rebot.yaml 配 lgtm_need_num=2
-- 且近30PR均有两条不同人 /lgtm（剔机器人/作者）再 +2 满分；无中间分、无 NA。
-- ⚠️ 旧表（tier_detail/tier_scores/unlocked_tier 结构）若已在库中需 DROP 后重建。
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_branch_protect_scan
(
    repo_id          INT          NOT NULL COMMENT '仓库ID',
    scan_time        DATETIME     NOT NULL COMMENT '批次扫描时间戳',
    repo_url         VARCHAR(512) NULL     COMMENT '仓库地址',
    base_pass        TINYINT      NULL     COMMENT '默认满足T1/T2/T3(平台默认+机器人lgtm=1):恒1,得基础8分',
    has_rebot_yaml   TINYINT      NULL     COMMENT '是否存在 .infra_self_service/rebot.yaml:1有 0无',
    yaml_lgtm_config VARCHAR(128) NULL     COMMENT 'yaml中lgtm配置原文(连名带值),如 lgtm_need_num=2;无文件/无配置=NULL',
    lgtm_need_num    INT          NULL     COMMENT '解析后lgtm_need_num数值;未配置/无文件=NULL,按默认1处理',
    pr_lgtm_pass     TINYINT      NULL     COMMENT '近30PR是否均有两条不同人/lgtm:1是 0否 NULL=未触发检查(need_num!=2或无yaml)',
    pr_numbers       JSON         NULL     COMMENT '参与检查的PR编号列表(近30次已合入,剔机器人创建)',
    pr_lgtm_detail   JSON         NULL     COMMENT '逐PR明细[{pr_number,lgtm_count,distinct_author,pass,lgtms:[{login,time}]}],lgtms取最后两条/lgtm的评论人和时间',
    score            DECIMAL(5,2) NULL     COMMENT '指标8得分:默认8;yaml存在且need_num=2且pr_lgtm_pass=1则10(二元)',
    is_na            TINYINT      NULL     COMMENT '是否NA(本指标恒0)',
    etl_time         DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [4] 文件扫描明细（指标2/3/4/6/8明细/12/14/15 · Python P1） ----------
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_file_scan
(
    repo_id     INT          NOT NULL COMMENT '仓库ID',
    metric_code VARCHAR(32)  NOT NULL COMMENT '指标编码:COPYRIGHT/DANGEROUS_WF/TOKEN_PERM/BINARY_ARTIFACTS/BRANCH_PROTECTION/PACKAGING/SAST/SECURITY_POLICY',
    scan_time   DATETIME     NOT NULL COMMENT '批次扫描时间戳',
    repo_url    VARCHAR(512) NULL     COMMENT '仓库地址',
    detail_json JSON         NULL     COMMENT '按 metric_code 的结构化明细(见 design.md §7.2④)',
    score       DECIMAL(5,2) NULL     COMMENT '该指标得分',
    is_na       TINYINT      NULL     COMMENT '是否NA',
    etl_time    DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, metric_code, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [5] 指标1 开源许可证（Python P2 · scancode） ----------
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_license_scan
(
    repo_id        INT          NOT NULL COMMENT '仓库ID',
    scan_time      DATETIME     NOT NULL COMMENT '批次扫描时间戳',
    repo_url       VARCHAR(512) NULL     COMMENT '仓库地址',
    scan_branch    VARCHAR(128) NULL     COMMENT '扫描分支(默认分支;no_default_branch的NA行为NULL)',
    spdx           VARCHAR(64)  NULL     COMMENT 'SPDX许可证标识,如 Apache-2.0/MIT',
    has_license    TINYINT      NULL     COMMENT '检出许可证文件:1有(>=5分) 0无(0分)',
    template_match TINYINT      NULL     COMMENT '满足模板(scancode score=100):1是(>=8分)',
    copyright_ok   TINYINT      NULL     COMMENT 'copyright年份/责任人正确:1是(>=9分)',
    osi_fsf_ok     TINYINT      NULL     COMMENT '满足OSI/FSF:1是(10分)',
    osi_approved_ok TINYINT     NULL     COMMENT 'SPDX isOsiApproved:1是/0否/NULL清单不可用(issue#126)',
    fsf_libre_ok   TINYINT      NULL     COMMENT 'SPDX isFsfLibre:1是/0否/NULL清单不可用(issue#126)',
    detail         JSON         NULL     COMMENT '明细{template_id,matched_text_diagnostics,copyright_matched,osi_approved_ok,fsf_libre_ok}',
    raw_json       TEXT         NULL     COMMENT 'scancode原始JSON(排查用)',
    score          DECIMAL(5,2) NULL     COMMENT '阶梯分:有5/模板8/版权9/OSI-FSF10/无0',
    is_na          TINYINT      NULL     COMMENT '是否NA(本指标恒0)',
    etl_time       DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- 增量迁移（2026-09-26 issue #126：OSI/FSF 分列记录，存量表执行；新表已含上述列）
ALTER TABLE dwi_rd_efc_security_license_scan
    ADD COLUMN osi_approved_ok TINYINT NULL COMMENT 'SPDX isOsiApproved:1是/0否/NULL清单不可用(issue#126)' AFTER osi_fsf_ok;
ALTER TABLE dwi_rd_efc_security_license_scan
    ADD COLUMN fsf_libre_ok TINYINT NULL COMMENT 'SPDX isFsfLibre:1是/0否/NULL清单不可用(issue#126)' AFTER osi_approved_ok;
-- 增量迁移（2026-09-26：记录扫描分支，存量表执行）
ALTER TABLE dwi_rd_efc_security_license_scan
    ADD COLUMN scan_branch VARCHAR(128) NULL COMMENT '扫描分支(默认分支;no_default_branch的NA行为NULL)' AFTER repo_url;

-- ---------- [6] 接口类指标明细（指标9/11/18 · SQL） ----------
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_meta_api_scan
(
    repo_id     INT          NOT NULL COMMENT '仓库ID',
    metric_code VARCHAR(32)  NOT NULL COMMENT '指标编码:WEBHOOKS/SIGNED_RELEASES/CONTRIBUTORS',
    scan_time   DATETIME     NOT NULL COMMENT '批次扫描时间戳',
    repo_url    VARCHAR(512) NULL     COMMENT '仓库地址',
    detail_json JSON         NULL     COMMENT '按 metric_code 的结构化明细(见 design.md §7.2⑥)',
    score       DECIMAL(5,2) NULL     COMMENT '该指标得分',
    is_na       TINYINT      NULL     COMMENT '是否NA',
    etl_time    DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, metric_code, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [7] 指标16 已知漏洞 VULNS（✅ 2026-09-22 接入 · 源表 sdi_rd_efc_cve_details，C10 关闭） ----------
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_vuln_scan
(
    repo_id       INT          NOT NULL COMMENT '仓库ID',
    scan_time     DATETIME     NOT NULL COMMENT '批次扫描时间戳',
    repo_url      VARCHAR(512) NULL     COMMENT '仓库地址',
    overdue_count INT          NULL     COMMENT '超期未关闭漏洞数(计划完成时间<当前且未关闭;closed/rejected均视为关闭)',
    vuln_detail   JSON         NULL     COMMENT '超期漏洞明细[{issue_id,cve_num,severity,plan_closed_time,status}],每仓截断50条',
    deduct_detail JSON         NULL     COMMENT '扣分明细{critical:n,high:n,medium:n,low:n,deduct_points}',
    score         DECIMAL(5,2) NULL     COMMENT '指标16得分=max(0,10-致命*10-高危*5-中危*2-低危*1);cve_level为None/空按Low扣1;无CVE记录(未覆盖)则NULL',
    is_na         TINYINT      NULL     COMMENT '是否NA(数据源未接入/无覆盖)',
    etl_time      DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [8] dm 汇聚宽表（全指标 + 两套加权分 + 亮灯） ----------
-- 暂缓指标(5/8/13/16)对应列恒 NULL,汇聚分母自动剔除(同 NA 逻辑,§6)
CREATE TABLE IF NOT EXISTS dm_rd_efc_security_scan_score
(
    repo_id                 INT          NOT NULL COMMENT '仓库ID',
    scan_time               DATETIME     NOT NULL COMMENT '批次扫描时间戳(全指标统一)',
    repo_url                VARCHAR(512) NULL     COMMENT '仓库地址',
    score_license           DECIMAL(5,2) NULL     COMMENT '1  开源许可证(规则7.5)',
    score_copyright         DECIMAL(5,2) NULL     COMMENT '2  版权合规(规则10)',
    score_dangerous_wf      DECIMAL(5,2) NULL     COMMENT '3  危险工作流(规则10)',
    score_token_perm        DECIMAL(5,2) NULL     COMMENT '4  令牌权限(规则7.5)',
    score_pinned_dep        DECIMAL(5,2) NULL     COMMENT '5  依赖锁定(建议5,⏸️暂缓恒NULL)',
    score_binary_artifacts  DECIMAL(5,2) NULL     COMMENT '6  二进制制品(规则7.5)',
    score_code_review       DECIMAL(5,2) NULL     COMMENT '7  代码评审(规则7.5)',
    score_branch_protection DECIMAL(5,2) NULL     COMMENT '8  分支保护(规则7.5,⏸️暂缓恒NULL)',
    score_webhooks          DECIMAL(5,2) NULL     COMMENT '9  Webhook安全(规则10)',
    score_ci_tests          DECIMAL(5,2) NULL     COMMENT '10 CI测试(规则2.5)',
    score_signed_releases   DECIMAL(5,2) NULL     COMMENT '11 发布签名(建议5)',
    score_packaging         DECIMAL(5,2) NULL     COMMENT '12 软件包发布(规则5)',
    score_fuzzing           DECIMAL(5,2) NULL     COMMENT '13 模糊测试(建议5,⏸️暂缓恒NULL)',
    score_sast              DECIMAL(5,2) NULL     COMMENT '14 SAST(建议5)',
    score_security_policy   DECIMAL(5,2) NULL     COMMENT '15 安全策略(规则5)',
    score_vulns             DECIMAL(5,2) NULL     COMMENT '16 已知漏洞(规则7.5,⏸️暂缓恒NULL)',
    score_maintained        DECIMAL(5,2) NULL     COMMENT '17 项目维护(规则2.5)',
    score_contributors      DECIMAL(5,2) NULL     COMMENT '18 贡献者多样性(建议2.5)',
    score_rule_weighted     DECIMAL(5,2) NULL     COMMENT '规则项加权总分(已实现11项权重和75,NA剔除,用于项目层级)',
    score_all_weighted      DECIMAL(5,2) NULL     COMMENT '全部指标加权总分(已实现14项权重和87.5,仅展示)',
    rule_weight_sum         DECIMAL(5,2) NULL     COMMENT '本批次规则项实际分母(口径快照=active规则型且score非NULL的权重和;权重配置变更后历史批次仍可复算得分率)',
    all_weight_sum          DECIMAL(5,2) NULL     COMMENT '本批次全部指标实际分母(口径快照,同上)',
    rule_light              TINYINT      NULL     COMMENT '仓库亮灯(按规则项得分率):1绿(>=80%) 2黄(>=50%) 3红(<50%)',
    etl_time                DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time)
DISTRIBUTED BY HASH(repo_id) BUCKETS 16
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [9] 指标权重配置（轻量静态 18 行 · D4 汇聚取权重 + 后端渲染元数据） ----------
-- 调权重：直接 UPDATE weight，下批扫描生效，无需改 D4 SQL 重新发布 DS 任务。
-- 同时服务后端明细渲染：18 指标的名称 / 顺序 / 暂缓状态由此表驱动。
-- 初始化仅首次执行；重复执行按 metric_code 去重覆盖（Unique 模型）。
CREATE TABLE IF NOT EXISTS dm_rd_efc_security_metric_conf
(
    metric_code   VARCHAR(32)  NOT NULL COMMENT '指标编码(稳定标识,与dwi明细表metric_code一致)',
    metric_name   VARCHAR(64)  NULL     COMMENT '指标中文名',
    metric_type   VARCHAR(16)  NULL     COMMENT '指标类型:rule规则/advice建议',
    weight        DECIMAL(4,1) NULL     COMMENT '权重(单项满分10下的加权系数)',
    status        VARCHAR(16)  NULL     COMMENT '状态:active启用/deferred暂缓(暂缓项dm列恒NULL,汇聚分母自动剔除)',
    display_order INT          NULL     COMMENT '前端展示顺序(1-18)',
    etl_time      DATETIME     NULL     COMMENT '配置时间'
)
UNIQUE KEY (metric_code)
DISTRIBUTED BY HASH(metric_code) BUCKETS 1
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- 初始化 18 行（权重 / metric_type 与 D4 原硬编码口径完全一致：
--   active 规则 11 项 = 75；active 全部 14 项 = 87.5；deferred 4 项 = 25，
--   暂缓项接入后全部指标分母 87.5 → 112.5）
INSERT INTO openlibing.dm_rd_efc_security_metric_conf
    (metric_code, metric_name, metric_type, weight, status, display_order, etl_time)
VALUES
    ('LICENSE',           '开源许可证',   'rule',   7.5, 'active',   1, NOW()),
    ('COPYRIGHT',         '版权合规',     'rule',  10.0, 'active',   2, NOW()),
    ('DANGEROUS_WF',      '危险工作流',   'rule',  10.0, 'active',   3, NOW()),
    ('TOKEN_PERM',        '令牌权限',     'rule',   7.5, 'active',   4, NOW()),
    ('PINNED_DEP',        '依赖锁定',     'advice', 5.0, 'deferred', 5, NOW()),
    ('BINARY_ARTIFACTS',  '二进制制品',   'rule',   7.5, 'active',   6, NOW()),
    ('CODE_REVIEW',       '代码评审',     'rule',   7.5, 'active',   7, NOW()),
    ('BRANCH_PROTECTION', '分支保护',     'rule',   7.5, 'deferred', 8, NOW()),
    ('WEBHOOKS',          'Webhook安全',  'rule',  10.0, 'active',   9, NOW()),
    ('CI_TESTS',          'CI测试',       'rule',   2.5, 'active',  10, NOW()),
    ('SIGNED_RELEASES',   '发布签名',     'advice', 5.0, 'active',  11, NOW()),
    ('PACKAGING',         '软件包发布',   'rule',   5.0, 'active',  12, NOW()),
    ('FUZZING',           '模糊测试',     'advice', 5.0, 'deferred', 13, NOW()),
    ('SAST',              '静态安全测试', 'advice', 5.0, 'active',  14, NOW()),
    ('SECURITY_POLICY',   '安全策略',     'rule',   5.0, 'active',  15, NOW()),
    ('VULNS',             '已知漏洞',     'rule',   7.5, 'deferred', 16, NOW()),
    ('MAINTAINED',        '项目维护',     'rule',   2.5, 'active',  17, NOW()),
    ('CONTRIBUTORS',      '贡献者多样性', 'advice', 2.5, 'active',  18, NOW());

-- ---------- [10] 项目(社区)层级每日分数（D6 汇聚 · 2026-09-23 新增） ----------
-- 口径（design.md §6）：每日一份快照（stat_date），同日重跑幂等覆盖；
-- 得分 = AVG(仓库分)，无分仓（dm 无记录或整仓规则项全 NA）不进分母；
-- 亮灯 = 仓库 rule_light 取 MAX（最低灯：1绿 2黄 3红，存在红即红）；
-- null_repo_count 单列透明记录无分仓数，不拖低项目安全水位。
-- 注意：Doris 要求 UNIQUE KEY 列必须是列声明顺序的有序前缀，
--       故 stat_date 排在 project_name 之前（2026-09-27 修复建表报错）
CREATE TABLE IF NOT EXISTS dm_rd_efc_security_project_score
(
    project_id      INT          NOT NULL COMMENT '项目(社区)ID',
    stat_date       DATE         NOT NULL COMMENT '统计日期(每日一份快照,同日重跑幂等覆盖)',
    project_name    VARCHAR(255) NULL     COMMENT '项目名称(sdi_project_info冗余)',
    repo_count      INT          NULL     COMMENT '项目下应扫仓数(is_operate=1,含无分仓)',
    null_repo_count INT          NULL     COMMENT '无分仓数(dm无该仓记录或整仓规则项全NA)',
    score_rule      DECIMAL(5,2) NULL     COMMENT '项目规则项得分=∑仓库规则分/有效仓数(0-10,无分仓剔除分母,用于亮灯)',
    score_all       DECIMAL(5,2) NULL     COMMENT '项目总得分=∑仓库总分(规则+建议)/有效仓数(仅展示)',
    green_count     INT          NULL     COMMENT '绿灯仓数',
    yellow_count    INT          NULL     COMMENT '黄灯仓数',
    red_count       INT          NULL     COMMENT '红灯仓数',
    light           TINYINT      NULL     COMMENT '项目亮灯(取仓库最低灯=MAX rule_light):1绿 2黄 3红',
    etl_time        DATETIME     NULL     COMMENT '入库时间'
)
UNIQUE KEY (project_id, stat_date)
DISTRIBUTED BY HASH(project_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");

-- ---------- [11] 版权合规逐文件明细（2026-10-07 明细试验新增 · security_file_scan-明细试验.py） ----------
-- 背景：主表 detail_json 的 unmatched_samples 每类原因截断 200，repo_401712 单仓
--       不合格文件 1.2 万+ 无法全量展示；本表全量落不合格文件，看板走分页查询。
-- 粒度：一行 = 一个不合格文件 × 一个批次（scan_time 与主表 dwi_rd_efc_security_file_scan 同批）。
-- 量级：实测 130 仓每日约 4-5 万行；多批次历史与主表同口径保留。
-- 注意：明细为辅助数据——脚本侧插入失败仅告警不阻断主表落库；reason 与主表
--       unmatched_reasons 主原因同口径（upstream_banner 不单列，走 is_banner 标记）。
CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_copyright_file_detail
(
    repo_id    INT           NOT NULL COMMENT '仓库ID',
    scan_time  DATETIME      NOT NULL COMMENT '批次扫描时间戳(与主表 dwi_rd_efc_security_file_scan 同批)',
    file_path  VARCHAR(1024) NOT NULL COMMENT '不合格文件相对路径(默认分支工作区,git ls-files)',
    ext        VARCHAR(16)   NULL     COMMENT '文件后缀(小写含点,如 .cpp)',
    reason     VARCHAR(32)   NULL     COMMENT '不合格主原因:no_header/no_copyright_line/owner_mismatch/template_mismatch',
    is_banner  TINYINT       NULL     COMMENT '是否上游banner(part of the llvm project):1=是,仅标注不改判定',
    etl_time   DATETIME      NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time, file_path)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");
