-- =====================================================================
-- 版权声明模板配置表 (指标: 代码仓 COPYRIGHT 合规检查)
-- 目标库: openlibing    建表模型: UNIQUE KEY (template_id 为主键, 支持更新)
-- 说明:
--   1. template_type 三类, 驱动检查引擎分流:
--        mulan   -> 木兰仓专用: 单模板严格比对 + 软件名称必检(require_sw_name=1)
--        builtin  -> 4+1 内置: 与 custom 合成匹配集, OR 语义(符合任一即过)
--        custom   -> 业务自定义(如 CANN 格式): 并入 4+1 匹配集
--   2. is_system=1 的系统行(mulan 4条 + builtin 5条)禁止删除和修改 content,
--      仅可启停(status); 业务只能自由增删 custom 行
--   3. license_ids 为可选绑定: 引擎默认不按协议过滤(非木兰不关心具体协议),
--      该字段留作将来做协议一致性检查的口子; 空数组 = 不限协议
--   4. 占位符统一为 {software_name}(引擎同时兼容官方原文的 {filename}),
--      其余: {year} {owner} {license_url} {license_name} {license_id}
--   5. replication_num 按集群实际副本数调整, 单副本环境改为 "1"
-- =====================================================================

CREATE TABLE IF NOT EXISTS `dim_copyright_template_config` (
    `template_id`     varchar(64)   NOT NULL COMMENT '模板唯一标识: mulan-psl-2.0 / builtin-reuse / custom-cann',
    `template_type`   varchar(16)   NOT NULL COMMENT 'mulan=木兰官方(固定) / builtin=4+1内置 / custom=业务自定义(并入4+1匹配集)',
    `template_name`   varchar(128)  NOT NULL COMMENT '模板显示名',
    `license_ids`     array<string>          COMMENT '绑定协议标识, 如["CANN-2.0"]; 空数组=不限协议',
    `content`         string        NOT NULL COMMENT '模板正文, 占位符: {year} {owner} {software_name} {license_url} {license_name} {license_id}',
    `require_sw_name` tinyint       NOT NULL DEFAULT '0' COMMENT '1=软件名称必检(木兰模板为1)',
    `is_system`       tinyint       NOT NULL DEFAULT '0' COMMENT '1=系统内置行, 禁删禁改content, 仅可启停',
    `match_priority`  int           NOT NULL DEFAULT '100' COMMENT '4+1匹配顺序, 值小者优先',
    `status`          tinyint       NOT NULL DEFAULT '1' COMMENT '1=启用 0=停用',
    `description`     varchar(512)  NOT NULL COMMENT '说明',
    `create_time`     datetime      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`     datetime      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=OLAP
UNIQUE KEY(`template_id`)
DISTRIBUTED BY HASH(`template_id`) BUCKETS 1
PROPERTIES (
    "replication_num" = "3"
);

-- =====================================================================
-- 种子数据 (11 条)
-- =====================================================================

-- ---------- 木兰官方 4 条 (mulan) ----------

INSERT INTO `dim_copyright_template_config`
(template_id, template_type, template_name, license_ids, content, require_sw_name, is_system, match_priority, status, description)
VALUES
('mulan-psl-2.0', 'mulan', '木兰宽松许可证 v2 (MulanPSL-2.0)', ['MulanPSL-2.0'],
'Copyright (c) {year} {owner}
{software_name} is licensed under Mulan PSL v2.
You can use this software according to the terms and conditions of the Mulan PSL v2.
You may obtain a copy of Mulan PSL v2 at:
         http://license.coscl.org.cn/MulanPSL2
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
See the Mulan PSL v2 for more details.',
1, 1, 0, 1, '木兰官方模板原文; 版权工具项目 license_fetcher.MULAN_LICENSES 同源'),

('mulan-psl-1.0', 'mulan', '木兰宽松许可证 v1 (MulanPSL-1.0)', ['MulanPSL-1.0'],
'Copyright (c) {year} {owner}
{software_name} is licensed under the Mulan PSL v1.
You can use this software according to the terms and conditions of the Mulan PSL v1.
You may obtain a copy of Mulan PSL v1 at:
    http://license.coscl.org.cn/MulanPSL
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
See the Mulan PSL v1 for more details.',
1, 1, 0, 1, '注意 v1 措辞与 v2 有差异: licensed under the Mulan PSL v1(带the)'),

('mulan-publ-2.0', 'mulan', '木兰公共许可证 v2 (MulanPubL-2.0)', ['MulanPubL-2.0'],
'Copyright (c) {year} {owner}
{software_name} is licensed under Mulan PubL v2.
You can use this software according to the terms and conditions of the Mulan PubL v2.
You may obtain a copy of Mulan PubL v2 at:
         http://license.coscl.org.cn/MulanPubL-2.0
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
See the Mulan PubL v2 for more details.',
1, 1, 0, 1, '木兰公共许可证(传染性)官方模板'),

('mulan-publ-1.0', 'mulan', '木兰公共许可证 v1 (MulanPubL-1.0)', ['MulanPubL-1.0'],
'Copyright (c) {year} {owner}
{software_name} is licensed under the Mulan PubL v1.
You can use this software according to the terms and conditions of the Mulan PubL v1.
You may obtain a copy of Mulan PubL v1 at:
    http://license.coscl.org.cn/MulanPubL-1.0
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
See the Mulan PubL v1 for more details.',
1, 1, 0, 1, '木兰公共许可证 v1 官方模板');

-- ---------- 4+1 内置 5 条 (builtin) ----------

INSERT INTO `dim_copyright_template_config`
(template_id, template_type, template_name, license_ids, content, require_sw_name, is_system, match_priority, status, description)
VALUES
('builtin-business', 'builtin', '业务实践模板', [],
'Copyright (c) {year} {owner}
All rights reserved.

Licensed under the License;
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

{license_url}

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.',
0, 1, 10, 1, '业务默认模板; 正文只写 the License, 协议名不出现'),

('builtin-reuse', 'builtin', 'REUSE 标准模板', [],
'SPDX-FileCopyrightText: {year} {owner}

SPDX-License-Identifier: {license_id}',
0, 1, 20, 1, 'REUSE Specification 标准头, 两行式'),

('builtin-k8s', 'builtin', 'Kubernetes 风格模板', [],
'Copyright {year} {owner}

Licensed under the {license_name} license (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    {license_url}

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.',
0, 1, 30, 1, 'Kubernetes 风格, 版权行无(c), 含协议名'),

('builtin-tensorflow', 'builtin', 'TensorFlow 风格模板', [],
'Copyright {year} {owner}. All Rights Reserved.

Licensed under the {license_name} license (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    {license_url}

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.',
0, 1, 40, 1, 'TensorFlow 风格, 版权行含 . All Rights Reserved.'),

('builtin-linux-kernel', 'builtin', 'Linux Kernel 风格模板', [],
'SPDX-License-Identifier: {license_id}

{software_name}

Copyright (C) {year} {owner}',
0, 1, 50, 1, 'Linux Kernel 风格; {software_name}占位符此处对应原工具的{filename}');

-- ---------- 业务自定义示例 1 条 (custom) ----------

INSERT INTO `dim_copyright_template_config`
(template_id, template_type, template_name, license_ids, content, require_sw_name, is_system, match_priority, status, description)
VALUES
('custom-cann', 'custom', 'CANN 自有格式', ['CANN-2.0'],
'Copyright (c) {year} {owner}
This program is free software, you can redistribute it and/or modify it under the terms and conditions of
CANN Open Software License Agreement Version 2.0 (the "License").
Please refer to the License for details. You may not use this file except in compliance with the License.
THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE.
See LICENSE in the root of the software repository for the full text of the License.',
0, 0, 60, 1, '华为 CANN 仓实际使用的标准头(实测 repo_401224 等34仓); 2026-10-07 修正: MERCHANTABILITY 后补逗号, 与113仓96.6%多数派逐字一致(标点级粒度); 首尾装饰线由归一化剥离, 不在content中');

-- =====================================================================
-- 验证查询 (执行后自查)
-- =====================================================================
-- SELECT template_type, count(*) AS cnt, sum(status) AS enabled_cnt
-- FROM dim_copyright_template_config GROUP BY template_type ORDER BY template_type;
-- 预期: builtin=5(5) / custom=1(1) / mulan=4(4)
