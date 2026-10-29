# [需求]: 【openlibing-coderepo】分支列表 staticAlertCount 落表——告警数写时推送 + 查询 SQL 化

## 需求背景

分支管理页查询接口 `POST /repo/branch/list` 的 `staticAlertCount`（未处理静态告警数，口径 = `OPEN + PENDING_REVIEW`）当前**无任何落库或缓存**：每次列表查询实时 Feign 调 codecheck 的 Mongo 聚合接口（`/internal/codescan/v1/static-alarm/issue/count/batch`）计算，并因此被迫走「全量取回 + 内存排序 + 内存分页」路径。具体问题：

1. **查询路径重**：每次列表查询都发起一次跨服务 Feign + Mongo 聚合，与页面访问量线性相关；
2. **排序被迫全量取回**：告警数不是本地数据库列无法 `ORDER BY`，按告警数排序时须取回筛选后的全部分支行，内存排序后再切页，数据量放大耗时与内存；
3. **非告警排序也要回填**：即使按更新时间等字段排序，当前页仍需实时调 codecheck 回填告警数用于展示。

本需求是 #257（代码度量最新快照物化到分支表）预告的后续优化：#257 已将 5 个代码度量指标落表并实现 SQL 排序，其范围声明明确「代码检查告警数（staticAlertCount，存 codecheck Mongo）本次不改动，记后续优化」，本 issue 承接该后续项。UT 覆盖率三列、度量五列均已落表，staticAlertCount 是分支列表最后一个仍走实时跨服务聚合的排序字段。

## 改造方案

将告警数落为 `repo_branch` 分支表冗余列 `static_alert_count`（+ `static_alert_count_synced_at` 刷新时间列），查询侧直接 SQL 排序分页。写入侧采用「写时推送」，**不引入常态定时兜底对账任务**（评审结论）：

1. **写时推送（唯一常态写入通道，秒级）**：codecheck 在三个告警数据变更点——SARIF 解析完成（`SarifParseService#parse`）、屏蔽/解除屏蔽（`shield` / `batchUnshieldIssues`）、告警状态流转（人工处理/恢复）——对受影响的 (代码仓, 分支) **重算一次未处理数**，经新增 MQ 队列 `static_alert_count_refresh` 推送；coderepo 新增消费者按 (projectId, 仓库坐标) 反查仓库后单行 UPDATE 落库；
2. **消息原子化**：一条消息 = 一个代码仓 + 一个分支 + 一个归属项目（单 projectId 载荷）；推送的是重算后的**全量数值**而非增量 delta，消息乱序/重复不产生累积误差；
3. **消费可靠性**：消费失败不丢消息，持续重试直至成功（间隔退避，MQ 持久化覆盖服务重启）——无兜底对账前提下，链路正确性由「不丢消息」策略保障；
4. **历史数据一次性回填**：coderepo 新增内部接口 `/internal/branch/static-alert-count/backfill`（分批限流，复用现有批量计数接口），上线时手动调用一次，非常驻定时任务；
5. **查询侧 SQL 化**：`queryProjectBranch` 移除告警数内存排序分支与查询链路 Feign 回填，排序下推 `ORDER BY IFNULL(static_alert_count, 0)`（与现内存排序中空值按 0 的口径一致）。

数据语义与现状完全一致：`NULL` = 未接入/未取到数（前端显示 `--`）、`0` = 明确无未处理告警；刷新范围不区分分支是否接入代码检查；跨域名场景沿用 `RepoUrlParser` 坐标解析（atomgit/gitcode 双域名兼容）。

**范围**：`openlibing-coderepo` + `openlibing-codecheck` 两仓；前端零改动；对外接口出入参、字段语义、排序语义不变。仓库管理 tab（repo 维度整仓告警数）仍走现有实时接口，不在本期范围。

## 验收标准

- [ ] 分支管理页 `staticAlertCount` 展示、`--`/`0`/数值语义与改造前一致，列表值与 codecheck 告警列表聚合值同源一致（含 `OPEN + PENDING_REVIEW` 边界抽样比对）
- [ ] 查询接口每次请求不再实时调 codecheck 聚合接口；按告警数排序为 SQL `ORDER BY` 下推分页，内存排序路径删除，总条数正确
- [ ] 扫描解析完成、屏蔽/解除屏蔽、告警状态流转后，对应分支告警数秒级更新（屏蔽后减少、复现后增加）
- [ ] MQ 消息满足原子化（一条消息一个代码仓 + 一个分支 + 一个归属项目，重算全量值），消费失败不丢消息、持续重试直至成功，重复消费幂等
- [ ] 历史回填接口一次性执行后存量分支告警数补齐，幂等可重复调用
- [ ] 接口出入参与排序口径不变，前端零改动；仓库管理 tab 现有链路回归通过
- [ ] 两仓本地编译 + 相关单测通过；pre-commit 检查通过

## 关联 issue

- #257 （同系列前置：代码度量最新快照物化到分支表，其范围声明预告的后续优化即本需求）
