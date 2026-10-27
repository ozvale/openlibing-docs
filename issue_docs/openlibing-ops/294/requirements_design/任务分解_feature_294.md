# #294 任务分解

## 1. 基础信息

| 项目 | 内容 |
|---|---|
| Issue | https://gitcode.com/openlibing/openlibing-ops/issues/294 |
| 后端仓库 | openlibing-ops |
| 前端仓库 | openlibing-ops-web（本期不改动） |
| 开发分支 | `feature_293_new` |
| 目标 | 三个入口对应两种明细：流水线执行明细、任务明细（构建/测试） |

## 2. 任务总览

| 编号 | 任务 | 主要文件 | 依赖 | 验收要点 |
|---|---|---|---|---|
| T1 | 新增两个 detail category 与请求/响应模型 | `DetailCommonEnum`、`DetailReq`、`OpsPrPipelineRunDetailReq/Resp`、`OpsPrPipelineJobDetailReq/Resp` | — | category 路由可解析，参数校验生效 |
| T2 | 流水线执行明细 Mapper | `OpsPrPipelineRunDetailMapper.xml` + 接口 | T1 | 18 列齐全，任务聚合来自 job_unified |
| T3 | 任务明细 Mapper | `OpsPrPipelineJobDetailMapper.xml` + 接口 | T1 | 仅由流水线明细下钻进入（`pipelineRunId` 必填），返回该 run 任务；`jobType` 可选过滤 |
| T4 | Service 层：排序白名单、参数校验、单位换算 | `OpsPrPipelineRunDetailDetailService`、`OpsPrPipelineJobDetailDetailService` | T2、T3 | 排序白名单与状态校验生效；不拼装 URL |
| T5 | 单测与 XML 注册校验 | `src/test/...` | T2-T4 | XML statement 可解析，Service 委派正确 |
| T6 | 数据对账与文档 | Doris、`docs/issue/294` | T2-T5 | 抽查仓库样本与主表 P90 一致 |
| T7 | pr-access 执行次数与时间口径改造 | `DmRdEfcRepoSumPipelineStatisticsDayMapper.xml`、`RepoPrPipelineDetailResp` | T1 | 执行次数=下钻 total；仅 PR 个数按创建时间 |
| T8 | 明细扩展：状态筛选 + NPU + CHECK | `OpsPrPipelineRunDetailReq/Resp/Mapper` | T2 | 状态筛选生效，新增 3 列与数据一致 |
| T9 | 趋势图与表格同源 | `OpsRepoPrChartMapper`、`RepoHandle`、`RepoChartResp` | T7 | 图表不再依赖已停更 DM，PR 总数与表格一致 |

## 3. T1 接口与模型

1. `DetailCommonEnum` 新增：
   - `OPS_PR_PIPELINE_RUN_DETAIL("ops-pr-pipeline-run-detail", "PR流水线执行明细")`
   - `OPS_PR_PIPELINE_JOB_DETAIL("ops-pr-pipeline-job-detail", "PR流水线任务明细")`
2. `DetailReq` 的 `@JsonSubTypes` 注册两个请求类。
3. `OpsPrPipelineRunDetailReq`：
   - `projectId`（必填）
   - `repoId`（可选）
   - `startDate` / `endDate`（必填）
   - `status`（可选）
   - `page` / `pageSize`
   - `sortField` / `sortRule`（默认 `start_time desc`）
4. `OpsPrPipelineJobDetailReq`：
   - `projectId`（必填）
   - `pipelineRunId`（**必填**，任务明细仅由流水线执行明细行下钻进入）
   - `jobType`（可选，`BUILD` / `DT`；为空=全部类型）
   - `repoId` / `visibility` / `repoIdList`（可选，与页面筛选透传一致）
   - `startDate` / `endDate`（必填）
   - `page` / `pageSize`
   - 校验：`pipelineRunId` 必填（为空直接返回参数校验错误）；`jobType` 若传仅允许 `BUILD`/`DT`
5. 响应字段按《需求_feature_294.md》6.1 / 6.2，时间统一返回 `yyyy-MM-dd HH:mm:ss`，时长统一返回分钟（1 位小数）。

## 4. T2 流水线执行明细

**步骤**：

1. `pr_run_sample`：与 `OpsMainStatMapper.xml` 完全一致
   - `dwi_rd_efc_pr_info_sum` → 桥表（`pr_id` 非空）→ `dwr_rd_efc_pipeline_run_unified`
   - 仓库范围：`sdi_repo_info` 且 `repo_id IN (sdi_rd_efc_repo_operate_conf.is_operate=1)`，按 `project_id` 归属
   - GitHub 额外走 `dim_ecod_github_show_pr_config`（`gc.project_id = sd.project_id`）
   - **不加** `pipeline_type='PR'` 过滤（主表 2026-09-17 统一口径）
   - `u.start_time` 限定时间窗
2. `page_run`：在 `pr_run_sample` 上统一过滤 `end_time IS NOT NULL`，且只保留实际状态 `status IN ('COMPLETED','FAILED')`；`CANCELED/IGNORED/RUNNING/INIT` 不返回
   - 空（全部）= `status IN ('COMPLETED','FAILED')`
   - `true`（成功）= `status = 'COMPLETED'`
   - `false`（失败）= `status = 'FAILED'`
   - 再排序分页；分页 total 与列表使用同一套过滤条件
3. `job_agg`：只对 `page_run` 的 run 聚合 `job_unified`
   - `BUILD` / `DT` / `CHECK` 的 `AVG/MAX(job_duration)`，`BUILD` / `DT` 另算排队
4. 输出 18 列：
   - 编号、名称、平台、起止时间、状态来自 `unified`
   - 流水线执行时长 `ROUND(duration_ms/60000,1)`
   - NPU 总卡时 `ROUND(npu_second/3600,2)`
   - 8-15、17-18 列来自 `job_agg`（平均用 AVG，最长用 MAX）
5. `count` 语句复用 `pr_run_sample` 的过滤条件。

## 5. T3 任务明细

**步骤**：

1. 基于 `pr_run_sample` 关联 `dwr_rd_efc_pipeline_run_job_unified`
2. 过滤 `s.end_time IS NOT NULL`；`jobType` 非空时加 `j.job_type = #{jobType}`；`pipelineRunId` 非空时加 `s.pipeline_run_id = #{pipelineRunId}`
3. 输出：`job_id`、`job_name`、`job_type`、`job_status`、`platform`、
   `job_run_start_time`（调度时间）、`job_start_time`（入队时间）、`job_end_time`、
   `job_pending_duration`、`job_duration`、`npu_second`、`pipeline_id`、`pipeline_run_id`、`run_number`、`pipeline_name`
4. 排序：仅下钻一种场景，默认 `job_run_start_time ASC`（空调度时间排最后）
5. total 与列表共用同一 WHERE 片段

## 6. T4 Service：排序与参数校验

1. 排序白名单：
   - 流水线：`start_time`、`end_time`、`duration_minutes`、`build_avg_duration_minutes`、`dt_avg_duration_minutes`（含各 avg/max/pending/check/npu）
   - 任务：`pending_minutes`、`schedule_time`、`start_time`、`end_time`、`duration_minutes`、`npu_hours`
   - 非法字段抛 `IllegalArgumentException`
2. 状态/参数校验：`pipelineStatus` 仅允许空/`true`/`false`；任务明细 `pipelineRunId` 必填，`jobType` 可选
3. **不拼装 URL**：后端只返回 `platform`、`repoUrl`、`pipelineId`、`pipelineRunId`、`jobId`，跳转链接由前端按 `getPipelineUrl` 拼接

## 7. T5 单测

1. `XMLMapperBuilder` 加载三个 Mapper（执行明细、任务明细、仓库汇总），断言 statement 已注册
2. Service 测试：排序字段校验、默认排序（执行明细 `start_time desc`；任务下钻 `schedule_time asc`）、`pipelineRunId` 必填校验
3. 单位换算：`duration_ms`（毫秒）→ 分钟保留 1 位；`job_duration`/`job_pending_duration`（秒）→ 分钟保留 1 位；NPU 秒 → 卡时保留 2 位
4. `pipelineRunId` 下钻：`jobType` 为空返回全部类型
5. 参数校验：`pipelineRunId` 为空时抛校验异常

## 8. T6 数据对账

1. 抽查 1 个仓库：主表 P90 的样本 `run` 数 = 明细总条数（同时间窗、同口径）
2. 抽查 1 个 run：
   - `duration_ms/60000` 与页面执行时长一致（`duration_ms` 为毫秒）
   - `AVG/MAX(job_duration)` 与 job 表手工聚合一致（`job_duration`/`job_pending_duration` 为**秒**，换算分钟用 `/60`）
3. 抽查任务下钻：传 `pipelineRunId` 返回该 run 全部任务，默认按调度时间升序；`jobType` 可选过滤
4. 前端用后端返回的 `platform`/`repoUrl`/`pipelineId`/`pipelineRunId`/`jobId` 拼接跳转链接（后端不返回 URL）
5. 口径一致性：确认明细样本与 `OpsMainStatMapper.xml` 的 `pr_run_sample` 同源（不加 `pipeline_type`、含运营仓过滤、GitHub 配置匹配一致）

**已执行对账（2026-10-27，Doris）**：

| 校验项 | 结果 |
|---|---|
| 样本：project 300033 / repo 401224（ops-nn）/ 2026-09-20~10-23 | 运行样本 3259 条（COMPLETED 2396、FAILED 863） |
| `repo-pr-pipeline` 改造后 `runCount`（同窗口同仓库） | 3259，与明细 total 一致 |
| PR 个数（ALL_PIPELINE_STATUS） | 1417，与改造前一致 |
| 任务聚合（run 级，最终口径） | build 平均 449.45s（7.5min）/ P90 816.5s（13.6min）、DT 平均 run 级 |
| 任务聚合（job 行级，仅作对比） | build 平均 136.81s / P90 418.0s；已被 run 级替代 |
| 趋势图 PR 天数累加 | 34 天合计 1417，与表格 PR 个数一致 |
| 趋势图运行指标抽样（10-23） | 门禁 329.1s、编译/测试/代码检查按 run 级（先 MAX 后平均） |
| 任务下钻（`pipelineRunId`） | 返回该 run 全部任务，`调度时间 = job_run_start_time`，`时长 = job_duration/60` |

## 9. 验收清单

- [ ] 工程能力三个入口 + pr-access 执行次数均打开同一张流水线执行明细（18 列）
- [ ] 流水线明细 18 列齐全（含流水线平台、NPU、代码检查），8-15/17-18 列来自 job 聚合
- [ ] 所有入口的流水线明细均支持任务下钻（`pipelineRunId` 必填，`jobType` 可选）
- [ ] 编号跳转由前端拼接（后端返回 `platform`/`repoUrl`/`pipelineId`/`pipelineRunId`/`jobId`）
- [ ] pr-access 执行次数 = 下钻 total（同时间窗与状态筛选）
- [ ] 状态筛选三档下，执行次数与下钻 total 同步变化且相等
- [ ] 统一过滤 `end_time IS NOT NULL`，`CANCELED/IGNORED/RUNNING/INIT` 不出现
- [ ] PR 个数按 PR 创建时间，其余指标按流水线开始时间
- [ ] PR 个数改造前后逐项数值一致（含全部/成功/失败三档），状态筛选逻辑未改动
- [ ] 运行中记录结束时间与任务列展示 `-`
- [ ] 明细与主表 P90 同源，抽检样本一致
- [ ] 任务明细含调度时间（`job_run_start_time`）与任务级 NPU(卡时)，6 列展示与文档一致
- [ ] 页面/图表/工程能力主表与仓库明细的编译、测试、代码检查时长与排队均为 **run 级**，三处一致
- [ ] 趋势图有最新数据（不停在 2026-09-23），各仓 PR 总数之和 = 表格 PR 个数，状态切换同步
- [ ] 工程能力 `resourceQueueTime = buildQueueP90 + dtQueueP90` 恒等
- [ ] 未改动 `openlibing-ops-web`

## 10. T7 pr-access 执行次数与时间口径

**现状**：`dm_rd_efc_pr_sum_pipeline_statistics_day.data_time` = PR 创建日期，导致所有指标按 PR 创建时间筛选。

**步骤**：

1. PR 个数：**完全沿用现网逻辑，不改造** —— `dm_rd_efc_pr_sum_pipeline_statistics_day` 按 `data_time`（PR 创建日期）过滤，`pipeline_status` 保持现网三档映射（空=ALL_PIPELINE_STATUS、`true`=COMPLETED、`false`=FAILED），计数表达式不变
2. 运行指标：复用 `pr_run_sample`（按 `u.start_time`）聚合执行次数、成功次数、成功率、时长分位、资源总量；仅此处保留状态过滤
3. 任务指标：`job_unified` **run 级**——先按 run 取该类型 `MAX(时长/排队)`，再跨 run 计算 avg / p50 / p90 / p95 / max；任务级 CPU/NPU/内存按 run 汇总后 sum（与主表/仓库明细一致）
4. PR 生命周期：基于窗口内有运行的 PR 集合，算闭环时长、合入时长、E2E 达标率
5. `repo-pr-pipeline` 响应的执行次数字段归一为 `runCount`（随 `pipelineStatus` 过滤）；移除同值的 `executeCount`、`executeTotalCount`（DM 实体字段保留，供外部接口使用）
6. 执行次数与下钻 total 共用同一 `pr_run_sample` + 状态映射 + `end_time IS NOT NULL`，前端下钻透传 `pipelineStatus`

## 11. T8 明细扩展

1. `OpsPrPipelineRunDetailReq` 增加 `pipelineStatus`（空/`true`/`false`）、`visibility`、`repoIdList`
2. `OpsPrPipelineRunDetailResp` 增加 `npuHours`、`checkAvgDurationMinutes`、`checkMaxDurationMinutes`
3. `job_agg` 增加 CHECK 分支
4. `page_run` 只保留 `COMPLETED`/`FAILED`，统一过滤 `end_time IS NOT NULL`：
   - 空 = `IN ('COMPLETED','FAILED')`，`true` = `COMPLETED`，`false` = `FAILED`
   - `CANCELED / IGNORED / RUNNING / INIT` 既不计入执行次数也不返回
5. 明细 total 与列表共用同一 `<sql>` 过滤片段，避免统计与分页口径漂移
6. 单测覆盖：全部/成功/失败三种筛选下行数与 total 一致

## 11.1 T9 趋势图与表格同源

**背景**：趋势图原读 `dm_rd_efc_repo_sum_pipeline_statistics_day`，实测全表 `max(data_time)=2026-09-23`（821 仓全部停更），表格改实时后同页会“表格有数、图空白”。

**步骤**：

1. 新增 `OpsRepoPrChartMapper` + XML，两条按（repo, day）聚合语句：
   - `queryPrDayStat`：`dm_rd_efc_pr_sum_pipeline_statistics_day` 按 `data_time` 分组 → `pr_count`、`pr_e2e_avg_duration`、`pipeline_start_lead_time_avg`、`merge_lead_time_avg`（与表格 PR 个数同源、同三档 `pipeline_status`）
   - `queryRunDayStat`：实时运行表 + job 统一表，按 `DATE(u.start_time)` 分组 → 门禁平均时长、编译/测试/代码检查平均时长（先按 run 取 MAX 再跨 run 平均，与表格 run 级同口径）
2. `RepoHandle.queryRepoPrChart` 改为调用上述两条语句，按 repo+day 合并；并发指标仍取 `dwi_repo_pipeline_concurrent_statistics`
3. `RepoInfoDayChartResp` 增加无参构造，由 `RepoHandle` 填充字段（不再依赖 DM 实体构造）
4. 过滤条件与表格一致：projectId / 运营仓 / openSource / visibility / repoIdList / 状态
5. 校验：图表各仓 PR 总数之和 = 表格同窗口 PR 个数（ops-nn 实测 1417）

## 12. 风险与待确认

| 编号 | 风险 | 处理建议 |
|---|---|---|
| R1 | `retry_count` 全为 0、无重试耗时数据 | 不提供“不含重试”列，只保留一列流水线执行时长 |
| R2 | `dwr_rd_efc_pipeline_run_fact` 中时长与最长时长两列恒等 | 明细不使用 fact，统一按 job 表聚合 |
| R3 | GitHub 运行通常无 BUILD/DT 任务 | 8-15 列展示 `-`，属正常 |
| R4 | 编号跳转与下钻交互由前端实现 | 本期后端只返回跳转所需字段与数据，不拼装 URL |
