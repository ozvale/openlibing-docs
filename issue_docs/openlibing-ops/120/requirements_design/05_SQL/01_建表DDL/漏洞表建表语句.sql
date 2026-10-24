CREATE TABLE IF NOT EXISTS openlibing.sdi_rd_efc_cve_details
(
    id                         VARCHAR(64)     NOT NULL COMMENT '主键(Mongo _id/ObjectId)',
    affected_repository        VARCHAR(255)    NULL COMMENT '受影响仓库名(后续关联仓库用)',
    issue_id                   VARCHAR(64)     NULL COMMENT 'issue ID',
    affected_branches          VARCHAR(1024)   NULL COMMENT '受影响分支',
    affected_software          VARCHAR(255)    NULL COMMENT '受影响软件',
    cve_level                  VARCHAR(32)     NULL COMMENT 'CVE等级',
    cve_num                    VARCHAR(512)    NULL COMMENT 'CVE编号(源含URL链接,原64过短)',
    cve_public_time            DATETIME        NULL COMMENT 'CVE公开时间',
    cve_vtopia_public_time     DATETIME        NULL COMMENT 'vtopia公开时间',
    cve_vtopia_rec_time        DATETIME        NULL COMMENT 'vtopia收录时间',
    cvss_score                 DOUBLE          NULL COMMENT 'CVSS评分',
    issue_created_time         DATETIME        NULL COMMENT 'issue创建时间',
    issue_customize_state      VARCHAR(64)     NULL COMMENT 'issue自定义状态',
    issue_labels               VARCHAR(2048)   NULL COMMENT 'issue标签(可为批量拼接,加宽)',
    issue_state                VARCHAR(64)     NULL COMMENT 'issue状态',
    issue_url                  VARCHAR(2048)   NULL COMMENT 'issue地址(加宽)',
    milestone                  VARCHAR(4096)   NULL COMMENT '里程碑(分支:结论,加宽)',
    not_analyzed_branches      VARCHAR(1024)   NULL COMMENT '未分析分支',
    nvd_score                  DOUBLE          NULL COMMENT 'NVD评分',
    organization_score         DOUBLE          NULL COMMENT '组织评分',
    reason_map                 VARCHAR(8192)   NULL COMMENT '原因映射(可长,加宽)',
    sa_public_time             DATETIME        NULL COMMENT 'SA公开时间',
    this_time_cvss             DOUBLE          NULL COMMENT '本次CVSS',
    unaffected_branches        VARCHAR(1024)   NULL COMMENT '不受影响分支',
    user_login                 VARCHAR(255)    NULL COMMENT '操作人',
    version                    VARCHAR(2048)   NULL COMMENT '软件版本(源为逗号分隔版本列表,加宽)',
    versions                   VARCHAR(1024)   NULL COMMENT '版本列表(数组字符串化)',
    cve_rec_duration           DOUBLE          NULL COMMENT 'CVE修复时长(天)',
    cve_repair_start_time      DATETIME        NULL COMMENT 'CVE修复开始时间',
    first_import_time          DATETIME        NULL COMMENT '首次导入时间',
    is_overdue_statistics      VARCHAR(8)      NULL COMMENT '是否超期统计',
    is_slo                     BIGINT          NULL COMMENT '是否SLO',
    issue_patch_time           DATETIME        NULL COMMENT 'issue补丁时间',
    issue_plan_closed_time     DATETIME        NULL COMMENT 'issue计划关闭时间',
    patch_duration_time        VARCHAR(64)     NULL COMMENT '补丁时长(源类型未知,先varchar,首跑确认)',
    affect_update              VARCHAR(8)      NULL COMMENT '是否影响更新',
    abnormal_create_time       DATETIME        NULL COMMENT '异常创建时间',
    abnormal_operator          VARCHAR(255)    NULL COMMENT '异常操作人',
    abnormal_reason            VARCHAR(2048)   NULL COMMENT '异常原因(加宽)',
    abnormal_state             VARCHAR(64)     NULL COMMENT '异常状态',
    affected_branches_list     VARCHAR(2048)   NULL COMMENT '受影响分支列表(数组字符串化)',
    not_analyzed_branches_list VARCHAR(2048)   NULL COMMENT '未分析分支列表(数组字符串化)',
    unaffected_branches_list   VARCHAR(2048)   NULL COMMENT '不受影响分支列表(数组字符串化)'
)
UNIQUE KEY(id)
DISTRIBUTED BY HASH(id) BUCKETS 16
PROPERTIES
(
    "enable_unique_key_merge_on_write" = "true"
);
