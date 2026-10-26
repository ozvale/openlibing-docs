-- =====================================================================
-- 补丁：LICENSE 指标失败卡 filter 修正
-- 背景：初始录入的 conf 中 failItems.filter 为 {"status":"!=达成"}，
--       会把「未评估」台阶也铺成失败卡，违反原型语义（cond===null 不铺卡）。
--       修正为 {"status":"!=达成,!=未评估"}，与 classpath 兜底 JSON 保持一致。
-- 用法：在 Doris 中执行本文件一次即可（UNIQUE KEY(metric_code) 后写覆盖）。
-- 生成：ai-assisted 2026-09-28
-- =====================================================================
INSERT INTO dm_rd_efc_security_metric_detail_conf (metric_code, conf_json, enabled, updated_by, updated_at)
VALUES ('LICENSE',
'{"summary":[{"key":"spdx","label":"SPDX 标识","value":"#join:$detected_licenses:spdx:、","level":"#gt:$detected_licenses:0:success"},{"key":"reached","hidden":true,"value":"#qcount:$ladder:status=达成"},{"key":"blocked","hidden":true,"value":"#qcount:$ladder:status=被阻断"},{"key":"missed","hidden":true,"value":"#qcount:$ladder:status=未达成"},{"label":"当前档位","value":"#tpl:{score} 分","level":"#eq:$score:10:success"},{"label":"已达成台阶","value":"#tpl:{s.reached} / 4"},{"label":"未达成","value":"#tpl:{s.missed}","level":"#gt:$s.missed:0:error"},{"label":"被阻断","value":"#tpl:{s.blocked}","level":"#gt:$s.blocked:0:warning"}],"failNote":"#tpl:阶梯计分：只取满足的最高档，无逐条扣分（故卡片不显示扣分值）　｜　当前 {score} 分","failEmptyText":"全部满足：四个台阶全部达成，取最高档 10 分","dataNote":"阶梯计分，只取满足的最高档：有许可证 5 分 → 满足模板 8 分 → copyright 年份与责任人替换正确 9 分 → 满足 OSI/FSF 标准 10 分；无许可证 0 分。⚠ 阶梯是连续的：前置台阶未达成时后续台阶被阻断。本指标无 NA 条件，无许可证记 0 分并参与汇聚（0 分进分母，NA 剔除分子分母）。许可证与模板的逐条差异明细暂未采集。","failItems":{"from":"$ladder","filter":{"status":"!=达成,!=未评估"},"card":{"title":"#tpl:台阶「{name}」{status}","fields":[{"label":"台阶","value":"$name"},{"label":"判定","value":"$status","level":"#map:$status:未达成:error,被阻断:warning,*:na"},{"label":"判定依据","value":"$why"}],"reason":"#tpl:{why}","searchText":"#tpl:{name} {status} {why}"}},"groups":[{"key":"ladder","label":"计分阶梯","columns":[{"label":"阶梯","key":"step","type":"number"},{"label":"台阶","key":"name","type":"text"},{"label":"是否达成","key":"ok","type":"text"},{"label":"判定依据","key":"why","type":"text"}],"rowsFrom":"$ladder","cellOf":{"step":{"text":"$step"},"name":{"text":"$name"},"ok":{"text":"$status","level":"#map:$status:达成:success,被阻断:warning,未达成:error,*:na"},"why":{"text":"$why"}},"searchText":"#tpl:{step} {name} {status} {why}"}],"emptyHint":"许可证匹配差异明细暂未采集，当前仅展示计分阶梯"}',
1, 'ai-assisted', NOW());
