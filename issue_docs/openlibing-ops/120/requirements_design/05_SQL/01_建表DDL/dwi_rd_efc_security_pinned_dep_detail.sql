-- =====================================================================
-- 依赖锁定（PINNED_DEP）依赖条目全量明细表
-- 背景：主表 dwi_rd_efc_security_file_scan.detail_json 的 deps 数组截断前 200 条，
--       大仓明细展示不全；仿版权合规 dwi_rd_efc_security_copyright_file_detail 模式，
--       全量条目独立落表，供 /security/pinned-dep-list 分页接口查询。
-- 数据源：security_gcheck_scan.py（gcheck 离线扫描批次）pinned-deps check 的 items，
--         全量写入（已固定 + 未固定，不截断）；NA 仓无明细行。
-- 键设计：dep_id = gcheck items 数组序号（批内唯一），保证 UNIQUE KEY 幂等覆盖
--         （同批次重跑自动去重，不残留旧行）。
-- 执行：Doris 手工执行（建表一次性）；执行后重跑扫描批次即可回填数据。
-- 生成：ai-assisted 2026-10-15
-- =====================================================================

CREATE TABLE IF NOT EXISTS dwi_rd_efc_security_pinned_dep_detail
(
    repo_id    INT           NOT NULL COMMENT '仓库ID',
    scan_time  DATETIME      NOT NULL COMMENT '批次扫描时间戳(与主表 dwi_rd_efc_security_file_scan 同批)',
    dep_id     INT           NOT NULL COMMENT '依赖条目序号(gcheck items 数组下标,批内唯一)',
    dep_type   VARCHAR(64)   NULL     COMMENT '依赖判据:containerImage/pipCommand/npmCommand/goCommand/chocoCommand/nugetCommand/downloadThenRun/ciAction/unknown/...',
    file_path  VARCHAR(1024) NULL     COMMENT '文件相对路径(默认分支工作区)',
    line       INT           NULL     COMMENT '行号',
    dep_ref    STRING        NULL     COMMENT '依赖引用原文(源文件真实那一行 snippet)',
    pinned     TINYINT       NULL     COMMENT '是否已固定:1=compliant,0=nonCompliant,NULL=无法判定(notSupported/error等)',
    signal     VARCHAR(32)   NULL     COMMENT '判定信号:mutableTag/variableRef/noRef/...(仅镜像类条目有值)',
    reason     STRING        NULL     COMMENT 'gcheck 整改路径文案(items[].detail)',
    etl_time   DATETIME      NULL     COMMENT '入库时间'
)
UNIQUE KEY (repo_id, scan_time, dep_id)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8
PROPERTIES ("replication_allocation" = "tag.location.default: 3");
