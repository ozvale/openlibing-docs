-- =====================================================================
-- 补丁：COPYRIGHT 指标评分说明改扣分制（替代原比率制文案）
-- 背景：2026-10-08 拍板版权合规打分改为扣分制：
--       score = max(0, round(10 − 0.2 × 不合格文件数, 2))，每个不合格文件扣 0.2 分，
--       50 个扣完 10 分，与 BINARY_ARTIFACTS / TOKEN_PERM 同族，替代原比率制 10×含声明/目标总数。
--       原 conf 的 failNote 仍展示比率制公式（评分：10 × 含声明文件数 x / 目标文件总数 y），
--       且 dataNote 中「分子分母均不计」为比率制措辞，与本轮 Python 脚本（已改扣分制）不一致。
-- 变更：
--   1. summary 增加隐藏项 miss = 目标文件总数 − 含声明数（供 failNote / reason 引用 {s.miss}）；
--   2. failNote 改为「评分：10 − 0.2 × 不合格文件数 {s.miss} = {score}｜每个不合格文件扣 0.2 分，扣完为止」；
--   3. failItems 卡片增加「不合格文件数」字段，reason 同步扣分口径；
--   4. dataNote「分子分母均不计」改为「不计入目标文件数（既不算合格也不算不合格）」。
-- 用法：在 Doris 中执行本文件一次即可（UNIQUE KEY(metric_code) 后写覆盖）。
--       执行后最多 5 分钟（conf 缓存 TTL）自动生效，无需发版重启。
-- 同步：openlibing-ops src/main/resources/security/detail-conf/COPYRIGHT.json（classpath 兜底）
--       与 detail-conf-init.sql 已同步更新，三处 conf_json 内容一致。
-- 生成：ai-assisted 2026-10-08
-- =====================================================================
INSERT INTO dm_rd_efc_security_metric_detail_conf (metric_code, conf_json, enabled, updated_by, updated_at)
VALUES ('COPYRIGHT',
'{"summary":[{"key":"total","label":"目标文件总数","value":"$target_file_count"},{"key":"matched","label":"含声明","value":"$matched_count","level":"#gt:$matched_count:0:success"},{"key":"rate","hidden":true,"value":"#pct:$matched_count,$target_file_count"},{"key":"miss","hidden":true,"value":"#sub:$target_file_count,$matched_count"},{"label":"含声明率","value":"#tpl:{s.rate}%","level":"#lt:$matched_count:$target_file_count:warning"},{"label":"超大文件跳过","value":"#ifnull:$oversize_file_count:0","level":"na"}],"failNote":"#tpl:评分：10 − 0.2 × 不合格文件数 {s.miss} = {score}　｜　每个不合格文件扣 0.2 分，扣完为止（50 个扣完 10 分）","failEmptyText":"全部满足：所有目标后缀文件均检出合规的 copyright 声明","dataNote":"判定正则为「Copyright (c) 年份 Huawei Technologies Co.」有空格写法。超 8MB / 不可读文件不计入目标文件数（既不算合格也不算不合格）。未检出与内容不匹配的逐文件明细暂未采集，明细仅提供按后缀统计。","failItems":[{"when":"matched_count<target_file_count","title":"存在未检出版权声明的文件","fields":[{"label":"目标文件总数","value":"$target_file_count"},{"label":"含声明","value":"$matched_count"},{"label":"不合格文件数","value":"#sub:$target_file_count,$matched_count","level":"error"},{"label":"含声明率","value":"#tpl:{s.rate}%","level":"warning"}],"reason":"#tpl:未满足：{target_file_count} 个目标后缀文件中 {s.miss} 个不合格（未检出合规 copyright 声明），每个扣 0.2 分","searchText":"版权头 未检出"}],"groups":[{"key":"ext","label":"按后缀统计","columns":[{"label":"后缀","key":"ext","type":"text"},{"label":"目标文件数","key":"total","type":"number"},{"label":"含版权头","key":"matched","type":"number"},{"label":"缺失","key":"miss","type":"number"},{"label":"匹配率","key":"rate","type":"text"}],"rowsFrom":"$by_ext","cellOf":{"ext":{"text":"$ext"},"total":{"text":"$file_count"},"matched":{"text":"$matched_count","level":"#gt:$matched_count:0:success"},"miss":{"text":"#sub:$file_count,$matched_count","level":"#lt:$matched_count:$file_count:warning"},"rate":{"text":"#pct:$matched_count,$file_count"}},"searchText":"#tpl:{ext} {file_count} {matched_count}"}]}',
1, 'ai-assisted', NOW());
