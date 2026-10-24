-- ---------- TOKEN_PERM 插件权限基准配置表（2026-09-29）----------
-- 用途：指标4 令牌权限检查的插件给定权限基准（单一配置源，追加/停用插件只改本表）
-- 匹配键 = workflow 中 uses 值截掉 @tag/sha/branch 后的完整路径
-- 未命中本表的 uses 引用（codearts/marketplace/仓内 action）按只读检查（脚本逻辑，无需配置）
-- scope 取值：none（不给权限，实际为 read 不罚只罚 write）/ read / write
CREATE TABLE IF NOT EXISTS sdi_sec_token_perm_plugin
(
    official_path    VARCHAR(256) NOT NULL COMMENT '插件官方路径(uses截掉@ref后的完整路径，唯一键)，如 openlibing/sca-action/sca-pr-action',
    plugin_name      VARCHAR(128) NULL     COMMENT '插件显示名(13清单名，如 sca-pr-scan)',
    aliases          VARCHAR(512) NULL     COMMENT '别名列表(逗号分隔，兼容裸名历史写法，如 openlibing-pre-commit-action)',
    plugin_type      VARCHAR(32)  NULL DEFAULT 'openlibing' COMMENT '插件类别(openlibing/codearts)',
    perm_project     VARCHAR(8)   NULL DEFAULT 'none' COMMENT 'project scope 给定权限(none/read/write)',
    perm_pr          VARCHAR(8)   NULL DEFAULT 'none' COMMENT 'pr scope 给定权限',
    perm_issue       VARCHAR(8)   NULL DEFAULT 'none' COMMENT 'issue scope 给定权限',
    perm_note        VARCHAR(8)   NULL DEFAULT 'none' COMMENT 'note scope 给定权限',
    perm_repository  VARCHAR(8)   NULL DEFAULT 'read' COMMENT 'repository scope 给定权限',
    is_active        TINYINT      NULL DEFAULT 1 COMMENT '是否启用(1=启用参与检查,0=停用)',
    remark           VARCHAR(256) NULL     COMMENT '备注',
    update_time      DATETIME     NULL DEFAULT CURRENT_TIMESTAMP COMMENT '配置更新时间'
)
UNIQUE KEY (official_path)
COMMENT 'TOKEN_PERM 令牌权限检查-插件权限基准配置表'
DISTRIBUTED BY HASH(official_path) BUCKETS 1
PROPERTIES ("replication_allocation" = "tag.location.default: 3");


INSERT INTO sdi_sec_token_perm_plugin
(official_path, plugin_name, aliases, plugin_type, perm_project, perm_pr, perm_issue, perm_note, perm_repository, remark)
VALUES
('openlibing/test-action/pytest-orch',                            'pytest-orch',                     'pytest-orch',                            'openlibing', 'none', 'none', 'none', 'none', 'read', '1 pytest用例执行器'),
('openlibing/test-action/upload-reports',                         'openlibing-upload-reports',       'openlibing-upload-reports,upload-reports', 'openlibing', 'none', 'none', 'none', 'none', 'read', '2 上传测试报告至OBS'),
('openlibing/test-action/test-result-display',                    'test-result-display',             'test-result-display',                    'openlibing', 'none', 'none', 'none', 'none', 'read', '3 测试结果展示'),
('openlibing/test-action/metadata-collect',                       'openlibing-metadata-collect',     'openlibing-metadata-collect,metadata-collect', 'openlibing', 'none', 'none', 'none', 'none', 'read', '4 pytest用例元数据收集'),
('openlibing/test-action/precision-test',                         'precision-test',                  'precision-test',                         'openlibing', 'none', 'none', 'none', 'none', 'read', '5 精准测试选例'),
('openlibing/api-scan-action',                                    'api-scan',                        'api-scan',                               'openlibing', 'none', 'none', 'none', 'none', 'read', '6 接口兼容性扫描'),
('openlibing/pre-commit-action',                                  'openlibing-pre-commit-action',    'openlibing-pre-commit-action',           'openlibing', 'none', 'none', 'none', 'none', 'read', '7 pre-commit CI插件'),
('openlibing/upload-sarif-action',                                'upload-sarif-action',             'upload-sarif-action',                    'openlibing', 'none', 'none', 'none', 'none', 'read', '8 上传sarif至平台'),
('openlibing/code-metrics-action',                                'code-metrics-action',             'code-metrics-action',                    'openlibing', 'none', 'none', 'none', 'none', 'read', '9 代码度量扫描'),
('openlibing/security-compilation-options-action',                'security-compilation-options-action', 'security-compilation-options-action', 'openlibing', 'none', 'none', 'none', 'none', 'read', '10 安全编译选项扫描'),
('openlibing/sca-action/sca-pr-action',                           'sca-pr-scan',                     'sca-pr-scan',                            'openlibing', 'none', 'none', 'none', 'none', 'read', '11 SCA开源片段PR扫描'),
('openlibing/malicious-code-scan-action/malicious-code-pr-scan-action', 'malicious-code-pr-scan',     'malicious-code-pr-scan',                 'openlibing', 'none', 'none', 'none', 'none', 'read', '12 恶意代码PR扫描'),
('openlibing/vulnerability-hunting-action/argus-action',          'vulnerability-hunting-action',    'vulnerability-hunting-action',           'openlibing', 'none', 'none', 'none', 'none', 'read', '13 Argus漏洞扫描(CASE参数化权限忽略,统一按只读)');
