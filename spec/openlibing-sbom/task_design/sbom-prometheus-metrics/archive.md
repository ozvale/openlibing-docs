# Archive: sbom-prometheus-metrics

- 仓名：openlibing-sbom
- 业务 Issue：https://gitcode.com/openlibing/openlibing-sbom/issues/165
- 业务 PR：https://gitcode.com/openlibing/openlibing-sbom/merge_requests/167（目标分支 `release_20261029_iter2`）
- 特性分支：`feat-sbom-prometheus-metrics`（fork Chenmingxu/openlibing-sbom）
- 模式：Standard
- 归档日期：2026-10-30

## 交付内容

SBOM 服务接入 CCE 云原生监控（Prometheus 自定义指标上报 AOM）代码侧步骤①：暴露 `/actuator/prometheus` 采集点，输出 4 个 `sbom_task_*` Gauge 指标。

| 指标                             | 口径                                                                                                            |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `sbom_task_running`              | `raw_sbom` 中 `task_status='RUNNING'` 记录数                                                                    |
| `sbom_task_queued`               | `raw_sbom` 中 `task_status='WAIT'` 记录数                                                                       |
| `sbom_task_success_rate`         | 近 100 条终态任务（FINISH/FAILED/FAILED_FINISH）中 FINISH 占比，0~1；无终态样本 NaN                             |
| `sbom_task_duration_p99_seconds` | 同口径近 100 条终态任务耗时 P99（秒），取 `sbom_batch_job_execution` 的 `end_time - start_time`；无有效样本 NaN |

## 交付物与 commit 链

| commit                                                                                                     | 说明                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| [bcf37826](https://gitcode.com/openlibing/openlibing-sbom/commit/bcf37826f6882b589ba702513d7536734428b432) | 4 指标暴露链路：actuator/prometheus 依赖与配置、TaskMetricsProvider 契约、PipelineMetricsService、TaskMetricsMeterBinder、单测 |
| [cac4ee6d](https://gitcode.com/openlibing/openlibing-sbom/commit/cac4ee6dc3f81e0c3261be878f359a07c28f35f2) | P99 对齐成功率口径（近 100 条）+ 单位改秒                                                                                      |
| [60d083ae](https://gitcode.com/openlibing/openlibing-sbom/commit/60d083aeb0572282de3433a01052e76e01a0c94c) | 样本过滤终态 + `raw_sbom` 声明 `idx_raw_sbom_update_time` 索引                                                                 |
| [573237a1](https://gitcode.com/openlibing/openlibing-sbom/commit/573237a147f74cfc820458f810f241b2dc9d58b8) | 检视修复①：成功率空样本 NaN、duration_p99 baseUnit seconds、Gauge description                                                  |
| [291e31d4](https://gitcode.com/openlibing/openlibing-sbom/commit/291e31d450736cc01c60c54c1638512f51fb1e89) | 检视修复②：Binder 注入加固、P99 SQL 常量驱动、单测精确匹配口径、scenario 契约与 DDL 注释                                       |

## 关键设计决策

1. **通用契约模式**：`TaskMetricsProvider` 接口 + `TaskMetricsMeterBinder` 统一注册（对齐 openlibing-ops MR #209 模式），新场景实现接口即可接入；`scenario` 标签非空且各 Provider 间唯一。
2. **P99 取数路径**：Spring Batch 6 `JobRepository` API 无耗时聚合方法且无对应 JPA 实体，按用户确认采用 `JdbcTemplate` 直查 `sbom_batch_job_execution`（表前缀 `sbom_batch_` 与 `@EnableJdbcJobRepository` 一致）。
3. **NaN 语义约定**：NaN = 无数据，0 = 全部失败；成功率与 P99 空样本均返回 NaN，避免看板/告警误报。
4. **口径同源**：终态集合与近 100 条窗口由 `TERMINAL_STATUSES` / `RECENT_LIMIT` 常量驱动，P99 SQL 的 IN 占位符由常量生成并参数绑定，两指标口径无法漂移；单测精确匹配口径参数 + SQL 契约断言。
5. **索引**：`raw_sbom` 新增 `idx_raw_sbom_update_time`（`ddl-auto=none` 下实体声明不生效，存量环境需手工 `CREATE INDEX CONCURRENTLY`，见 issue #165）。

## 反馈循环与检视记录

- **口径迭代**（用户驱动）：P99 从全量改为近 100 条（与成功率同口径）→ 单位毫秒改秒 → 样本过滤终态 → 加 update_time 索引（gamma EXPLAIN 验证全表扫描消除）。
- **P99 样本损耗**：gamma 库 100 条终态样本仅 97 条有效（2 条缺 job_execution_id、1 条缺起止时间），属数据完整性过滤，保留 `IS NOT NULL` 条件，已在 Javadoc 与 issue 说明。
- **running/queued 出现小数**：Java long 无小数，`3.0` 为 Prometheus double 标准表示；真小数仅来自多副本 avg 聚合，非精度缺陷。
- **检视修复①**（ozvale 2 条，`573237a1`）：成功率空样本 0→NaN；`baseUnit("seconds")` 使暴露名为 `sbom_task_duration_p99_seconds`。
- **检视修复②**（atomgit-bot 7 条 P3，`291e31d4`）：采纳 5 条（List 注入加固、测试精确匹配、SQL 常量驱动、scenario 契约、DDL 注释），部分采纳 1 条（P99 样本过滤保留 + 补注释），暂缓 1 条（task_status 索引，当前 626 行亚毫秒级，规模增长后再评估）。已逐串回复处理结论。

## 验证证据

- 单测 14 个全绿（4 指标口径 + 边界 + Binder 注册/tag/异常 NaN + P99 SQL 契约）；
- pre-commit（Spotless/CheckStyle/SpotBugs/PMD/secrets）每轮交付全部通过；
- 合入 `sbom-dev` 测试环境分支部署验证：`/actuator/prometheus` 输出 4 指标，数值与库内计算一致；
- gamma 库 EXPLAIN ANALYZE：成功率/P99 查询走 `idx_raw_sbom_update_time` 索引，4 条 SQL 亚毫秒级；
- PR CI 流水线（构建/病毒扫描/安全编码/UT）COMPLETED。

## 遗留与后续

- **AOM 看板/告警改名**：若已按旧名 `sbom_task_duration_p99` 配置，合入后需同步改为 `sbom_task_duration_p99_seconds`（已在 PR 回复提醒）。
- **committer 评审**：检视修复 commit 推送后 lgtm 标签被自动移除，需 committer 重新 `/lgtm` + `/approve`。
- **task_status 索引**：数据规模增长或出现抓取超时后再评估（设计文档第 5 节）。
- **步骤②③④**：部署侧负载配置、集群监控插件安装、AOM 上报，非本仓代码范围。
