-- =====================================================================
-- 开源安全评分看板 · 指标18 贡献者多样性（CONTRIBUTORS）明细展示配置更新
-- 表：dm_rd_efc_security_metric_detail_conf（单行压缩 conf_json）
-- 变更：归属口径 v2（2026-10-16 拍板）→ v3（2026-10-20）——组织（orgs 接口）→ 公司
--       （GitCode 用户资料 company 字段，users/:username 接口）。N = 存在至少 1 名活跃作者
--       （近 30 次 PR 中贡献 ≥ 5 个）的公司个数；未填写/404 统一归入「未配置公司」，参与 N（v3）；
--       华为系写法（huawei/hw/华为/华为技术有限公司/华为科技有限公司/上海华为技术有限公司）归一为
--       「华为技术有限公司」（归一在指标层 D2-18，sdi 保留原值）。
--       2026-10-19 增补：groups 新增「贡献者明细（近 30 次 PR）」分组（detail_json
--       新增 authors 数组：贡献者/公司/近30次PR数/主页链接，贡献者可跳转 GitCode 主页），
--       emptyHint 同步更新。依赖 D2-18 重跑产出 authors 字段。
--       2026-10-20 口径 v3：未填写 company 或账号已注销/改名（404）的作者统一归入
--       虚拟公司「未配置公司」，与真实公司平权参与 N 值（拍板：参与计分 + 合并为一个）；
--       明细表公司列「未填写」改为「未配置公司」；rule/definition/dataNote/emptyHint 同步。
-- 同步：本文件 / openlibing-ops classpath security/detail-conf/CONTRIBUTORS.json /
--       2026-09-23 模版SQL目录 detail-conf-init.sql 三处同一份配置。
-- 幂等：UPDATE 全量替换 conf_json，重复执行无副作用。
-- 生效：执行后最多 5 分钟（conf 缓存 TTL）自动生效，无需发版重启；D2-18 重跑
--       前执行不影响旧数据展示（字段沿用 author_count/n_orgs/qualified_orgs）。
-- ⚠️ 执行通道：本文件 conf_json 含 < 字符（when "n<@p.minOrgs"），必须在生产
--       Doris 客户端直接执行（source / 粘贴）；禁止经会转义 < > & 的写入通道，
--       否则会复现 10-14 批次 u003c 吃字损坏（when 条件失效、卡片全部失效）。
-- 生成：ai-assisted 2026-10-16
-- =====================================================================

UPDATE openlibing.dm_rd_efc_security_metric_detail_conf
SET conf_json = '{"rule":{"brief":"检查最近 30 次已合入 PR 的作者（剔除机器人）来自多少个不同公司，且这些公司中是否有活跃作者（近 30 次 PR 中个人贡献 ≥ 5 个）。公司取自 GitCode 用户资料的 company 字段。","formula":"得分 = 10 × N / 3，上限 10 分（N = 存在至少 1 名活跃作者的公司个数，3 个即满分）","conditions":[{"label":"活跃作者","value":"近 30 次已合入 PR 中该作者贡献 ≥ 5 个"},{"label":"N 值","value":"存在至少 1 名活跃作者的公司个数"},{"label":"公司归属","value":"GitCode 用户资料 company 字段；未填写或账号已注销/改名的作者统一归入「未配置公司」，视为一个公司参与 N 值；华为系写法已归一为「华为技术有限公司」"},{"label":"PR 口径","value":"最近 30 次已合入 PR，剔除机器人创建的 PR"}],"naCondition":"近 30 次已合入 PR 为 0 时，本指标不参评（不计入总分，不是 0 分）。","notes":[]},"definition":{"brief":"衡量仓库贡献者来源公司的多样性：近 30 次已合入 PR 中，活跃作者覆盖的不同公司个数。","purpose":"单一公司依赖意味着 bus factor 风险：一旦该公司退出，项目可能失去维护能力；多公司参与是社区健康度的信号。","details":[{"label":"数据来源","value":"GitCode 用户资料 company 字段（users/:username 接口，T7 每日采集）"},{"label":"统计口径","value":"N = 存在至少 1 名活跃作者（近 30 次 PR 中贡献 ≥ 5 个）的公司个数，剔除机器人；未填写公司或账号已注销/改名的作者统一归入虚拟公司「未配置公司」，与真实公司平权参与 N 值"},{"label":"计分","value":"N ≥ 3 即满分"}],"notes":[]},"params":{"minOrgs":"3"},"summary":[{"label":"作者数（去重）","value":"$author_count"},{"label":"公司数","value":"$n_orgs"},{"key":"n","label":"达标公司数 N","value":"#count:$qualified_orgs","level":"#lt:$s.n:$p.minOrgs:error"},{"label":"达标门槛","value":"#tpl:N ≥ {p.minOrgs}"}],"failNote":"#tpl:评分：min(10, 10 × 达标公司数 {s.n} / {p.minOrgs}) = {score}　｜　达标公司 = 该公司内存在至少 1 名作者近 30 次 PR 数达标　｜　因 min(10,…) 封顶，卡片不显示逐条扣分","failEmptyText":"全部满足：达标公司数已达门槛，贡献者多样性足够","dataNote":"贡献者口径为「近 30 次已合入 PR 的作者」（非全量贡献者）。公司取自 GitCode 用户资料的 company 字段，当前填写率较低（2026-10 实测约 1.6%）；未填写或账号已注销/改名的作者统一归入虚拟公司「未配置公司」，视为一个公司参与 N 值（贡献者补填 GitCode 资料后即可浮出为真实公司）；华为系写法（huawei/hw/华为等）已归一为「华为技术有限公司」。","failItems":[{"when":"n<@p.minOrgs","title":"达标公司数未达门槛","fields":[{"label":"作者数（去重）","value":"$author_count"},{"label":"公司数","value":"$n_orgs"},{"label":"达标公司数 N","value":"#tpl:{s.n}","level":"error"},{"label":"达标门槛","value":"#tpl:N ≥ {p.minOrgs}"}],"reason":"#tpl:未满足：达标公司数 {s.n}，低于门槛 {p.minOrgs}","searchText":"公司 多样性"}],"groups":[{"key":"org","label":"达标公司","columns":[{"label":"公司","key":"org","type":"text"}],"rowsFrom":"$qualified_orgs","cellOf":{"org":{"text":"$this"}},"searchText":"$this"},{"key":"authors","label":"贡献者明细（近 30 次 PR）","columns":[{"label":"贡献者","key":"user","type":"text"},{"label":"公司","key":"org","type":"text"},{"label":"近30次PR","key":"pr_cnt","type":"text"}],"rowsFrom":"$authors","cellOf":{"user":{"text":"#tpl:{user}","href":"$url"},"org":{"text":"#ifnull:$org:未配置公司"},"pr_cnt":{"text":"#tpl:{pr_cnt}"}},"searchText":"#tpl:{user} {org}"}],"emptyHint":"贡献者明细为近 30 次已合入 PR 窗口内的全部作者（按 PR 数倒序）；达标公司清单仅列出存在活跃作者的公司；「未配置公司」= GitCode 资料未填 company 或账号已注销/改名的作者（视为一个公司参与 N 值）"}',
    updated_by = 'ai-assisted',
    updated_at = NOW()
WHERE metric_code = 'CONTRIBUTORS';
