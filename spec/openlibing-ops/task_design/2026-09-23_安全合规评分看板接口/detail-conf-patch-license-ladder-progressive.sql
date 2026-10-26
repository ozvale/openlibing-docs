-- =====================================================================
-- 补丁：LICENSE 明细展示对齐"递进累加"计分口径（2026-10-10 口径仲裁）
-- 背景：① LICENSE 计分由"只取满足的最高档"改为递进累加（5→8→9→10），
--         前置台阶未达成时后续台阶不再判定。
--       ② 服务端 buildLicenseLadder 同步改版（按得分推台阶，消除"被阻断"
--         状态）：首个失败台阶=未达成，其后一律=未评估（页面显示为空）。
--       ③ 本 conf 同步移除 blocked/被阻断 计数与文案，rule/failNote/dataNote
--         改为递进累加表述；failItems/表格 level 映射去掉"被阻断:warning"。
-- 前置：需与 openlibing-ops 的 MetricDetailConfigEngine ladder 改版一同生效
--       （引擎与 conf 单独任一变更都不完整）。
-- 用法：在 Doris 中执行本文件一次即可（UNIQUE KEY(metric_code) 后写覆盖）。
-- 生成：ai-assisted 2026-10-10
-- =====================================================================
INSERT INTO dm_rd_efc_security_metric_detail_conf (metric_code, conf_json, enabled, updated_by, updated_at)
VALUES ('LICENSE',
'{"summary":[{"key":"spdx","label":"SPDX 标识","value":"#join:$detected_licenses:spdx:、","level":"#gt:$detected_licenses:0:success"},{"key":"reached","hidden":true,"value":"#qcount:$ladder:status=达成"},{"key":"missed","hidden":true,"value":"#qcount:$ladder:status=未达成"},{"label":"当前档位","value":"#tpl:{score} 分","level":"#eq:$score:10:success"},{"label":"已达成台阶","value":"#tpl:{s.reached} / 4"},{"label":"未达成","value":"#tpl:{s.missed}","level":"#gt:$s.missed:0:error"}],"failNote":"#tpl:递进计分：逐台阶累加（5 → 8 → 9 → 10），无逐条扣分（故卡片不显示扣分值）　｜　当前 {score} 分","failEmptyText":"全部满足：四个台阶全部达成，得 10 分","dataNote":"阶梯计分（递进累加）：有许可证 5 分 → 模板一致 +3 分（8 分）→ copyright 年份与责任人替换正确 +1 分（9 分）→ OSI/FSF 认证 +1 分（10 分）；无许可证 0 分。⚠ 阶梯是递进的：前置台阶未达成时，后续台阶不再判定（显示为未评估）。本指标无 NA 条件，无许可证记 0 分并参与汇聚（0 分进分母，NA 剔除分子分母）。许可证与模板的逐条差异明细暂未采集。","failItems":{"from":"$ladder","filter":{"status":"!=达成,!=未评估"},"card":{"title":"#tpl:台阶「{name}」{status}","fields":[{"label":"台阶","value":"$name"},{"label":"判定","value":"$status","level":"#map:$status:未达成:error,*:na"},{"label":"判定依据","value":"$why"}],"reason":"#tpl:{why}","searchText":"#tpl:{name} {status} {why}"}},"groups":[{"key":"ladder","label":"计分阶梯","columns":[{"label":"阶梯","key":"step","type":"number"},{"label":"台阶","key":"name","type":"text"},{"label":"是否达成","key":"ok","type":"text"},{"label":"判定依据","key":"why","type":"text"}],"rowsFrom":"$ladder","cellOf":{"step":{"text":"$step"},"name":{"text":"$name"},"ok":{"text":"$status","level":"#map:$status:达成:success,未达成:error,*:na"},"why":{"text":"$why"}},"searchText":"#tpl:{step} {name} {status} {why}"}],"emptyHint":"许可证匹配差异明细暂未采集，当前仅展示计分阶梯","rule":{"brief":"检查仓库根目录（或 license 目录）下的 LICENSE 文件：是否有许可证、格式是否符合官方模板、版权年份和责任人是否填写正确、是否通过 OSI/FSF 开源认证。","formula":"阶梯计分（递进累加）：无许可证 0 → 有许可证 5 → 模板一致 +3（8 分）→ 版权正确 +1（9 分）→ OSI/FSF 认证 +1（10 分）；前置台阶未达成时，后续台阶不再评估","conditions":[{"label":"无 LICENSE 文件","value":"0 分（有效低分，不是不参评）"},{"label":"有许可证","value":"5 分（基础分）"},{"label":"格式符合官方模板","value":"+3 分 → 8 分"},{"label":"版权年份和责任人正确","value":"+1 分 → 9 分"},{"label":"通过 OSI/FSF 认证","value":"+1 分 → 10 分"}],"naCondition":"无，本指标恒有得分。","notes":[]}}',
1, 'ai-assisted', NOW());
