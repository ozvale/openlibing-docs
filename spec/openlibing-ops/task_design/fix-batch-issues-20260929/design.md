# 批量修复 11 个看板缺陷 — 技术设计

## #144 未执行任务显示成功

`PipelineStatusEnum`（infrastructure/enumeration/pipeline/PipelineStatusEnum.java）中 `SKIPPED("跳过", result=true)`、`IGNORED("忽略", result=true)`。`PipelineJobResp`/`PipelineRunDetailResp` 用 `isResult()` 映射 成功/失败，导致 gitcode 未执行的构建任务（skipped）显示"成功"。

**修复**：SKIPPED/IGNORED 的 result 置 false。`show` 不变（allShowStatus 过滤行为不受影响）。

## #145 门禁E2E执行时长小数位

`RepoPrPipelineDetailResp` 中 access 系列用 `timeNumberConvert`（1 位），efficiency 系列用 `timeNumberConvertTwo`（2 位）；`PrInfoResp` 同。前端 pr-columns.ts 中"门禁E2E执行"列（access*）与"(不含重试)"列（efficiency*）小数位不一致。

**修复**：access 系列（Avg/P50/P90/P95/Max）改 `timeNumberConvertTwo`，涉及 RepoPrPipelineDetailResp 两处构造、PrInfoResp 两处构造。

## #161 productName 全为 null

~~原分析：`DmProjectQualityOverviewDayMapper.queryMainSnapshot` 直接 SELECT `dm_project_quality_overview_day.product_name`（ETL 未回填/被脏批次覆盖为 null），无维表 join，需 join `sdi_project_info` + `sdi_product_info` 补齐。~~

**2026-09-30 已回退**：用户确认该 issue 提错了（非代码问题），`DmProjectQualityOverviewDayMapper.xml` 改动已还原，不做任何修改。

## #166 NPU 平均消耗(卡时)错误

~~原分析：`OpsMainStatMapper.unified_npu_stat` 从 run 统一表 `SUM(npu_second)/3600` 取 NPU 消耗；`OpsResourceDetailMapper.queryResourceSummary` 同理。既定口径（项目规则）应为 `SUM(assign_npu_second)/3600` 取自 `dwr_rd_efc_resource_npu_detail`。（已回退）~~

**2026-10-01 重新修复（区分流水线归属项目）**：

根因：`OpsMainStatMapper.queryMainStat` 的 `unified_npu_stat` CTE 用全量 relation（`pj`，不区分 pipeline_type）做项目归属：

- Nightly run 归属取 `pj.project_id`，流水线被多个项目共用时，同一 run 的 NPU 消耗被重复 SUM 到每个项目 → Nightly 消耗与整体消耗虚高；
- PR run 归属取 repo 项目，但 WHERE 过滤用的是流水线归属项目（`pj.project_id`），两者不一致导致 PR run 归属错位/被误过滤 → PR 平均消耗错误。

对照 `ops-resource-detail`（OpsResourceDetailMapper）：PR 分支按 `sdi_repo_info.project_id`（repo 归属项目）过滤、Nightly 分支按 `relation.project_id`（流水线归属项目）过滤，每个 run 归属明确。

**修复**：`unified_npu_stat` 改为两个独立分支（UNION ALL），与 ops-resource-detail 同口径：

- PR run：桥表 pr_id 非空 + relation pipeline_type='PR'，归属 `si.project_id`（repo 项目），按 `si.project_id` 过滤 projectIds；
- Nightly run：relation pipeline_type='NIGHTLY'，归属 `rel.project_id`，按 `rel.project_id` 过滤 projectIds。

涉及文件：OpsMainStatMapper.xml（unified_npu_stat CTE）。`nightly_pipeline_dim` 仍被 nightly_count 使用，保留。

## #146/#152/#158 gitcode 数据链路

根因：repo-pr-pipeline 查询与 PR 详情（PipelineHandleImpl）均经 `sdi_rd_efc_pipeline_run_pr_relation_codearts` 桥表（git_url+pr_id）关联 run 统一表，gitcode PR run 不在桥表，导致排队时长、构建/测试数据、任务数缺失。

**ETL 侧已确认（beta DS 项目 openlibing）**：桥表由 DS 任务 `[job][raw->sdi][codearts]流水线与PR关联关系`（workflow 173390037917696，内含 SQL 任务「流水线与PR的绑定关系(包含子流水线)」）构建，**仅覆盖 codearts**；DS 中不存在 gitcode PR 关联任务。

**修复方向（数据组/ETL）**：扩展/新增 DS SQL 任务，将 gitcode workflow run 与 PR 绑定写入 `sdi_rd_efc_pipeline_run_pr_relation_codearts`（gitcode run 的 pipeline_run_id 与 PR 的关联可从 gitcode workflow 事件/PR 触发信息解析）。后端无需改动（桥表有数据后现有查询自动生效）。

## #149 Nightly 汇总接口 P95 超时

`NightlyPipelineDashboardMapper.getNightlyPipelineDashboardSummary`（CTE pipelineStatsCTE 等）projectId 未下推、对全量流水线做 12+ 次 PERCENTILE 聚合后再过滤。

**修复**：projectId 下推进 pipelineStatsCTE 的 sdi 子查询 WHERE，只对目标项目流水线做聚合（仓库暂无缓存基建，未引入缓存依赖）。

## #157 nightly 使用率分析未展示时间跨度

NPU 资源看板「使用率分析」的 KPI/趋势/热力图面板不展示所选时间范围（仅顶部筛选条有）。

**前端改动点（openlibing-ops-web，本次未改代码，待前端自行实现）**：

1. `src/views/dashboard/npu-resource/usage-analysis/utils.ts`：新增工具函数
   ```ts
   /** 回显使用率分析所选时间跨度（小时粒度），便于面板展示当前分析范围 */
   export function formatUsageTimeSpan(filter: NpuUsageFilter | null): string {
     const start = filter?.startTime
       ? dayjs(filter.startTime).format("YYYY-MM-DD HH:00")
       : "";
     const end = filter?.endTime
       ? dayjs(filter.endTime).format("YYYY-MM-DD HH:00")
       : "";
     return start && end ? `${start} ~ ${end}` : "";
   }
   ```
2. `src/views/dashboard/npu-resource/usage-analysis/components/usage-kpi-panel.vue`：在「排队任务」「使用率」两张卡片标题旁加时间跨度回显。模板：`<span class="text-base font-semibold text-slate-800">排队任务</span>` 后追加 `<span class="ml-2 text-xs text-slate-400" v-if="timeSpan">{{ timeSpan }}</span>`；script 中 `import { formatUsageTimeSpan } from '../utils'` 并 `const timeSpan = computed(() => formatUsageTimeSpan(props.filter));`
3. `usage-trend-chart.vue`：header 内「趋势分析」标题后加同样的 `timeSpan` 回显（`v-if="timeSpan"`），script 同上。
4. `usage-heatmap.vue`：header 内「使用率热力图」标题后加同样的 `timeSpan` 回显，script 同上。

每日类面板（每日排队/每日卡时）已展示「最近 7 日」，无需改动。

## #164 codearts 流水线跳转错位

~~原分析：`NpuUsageMapper.querySlotTasks` 生成 codearts jobUrl 时 projectId 取 `MAX(relation.project_id)`（按 pipeline_id 分组），共享流水线会取到其他项目导致跳错项目，需 LEFT JOIN run 统一表取 run 真实 project_id。~~

**2026-09-30 已回退**：`NpuUsageMapper.xml` 改动已还原，本批不做修改。

## #168 PR执行时长[P90] 不一致

eCDashboard main 的 `pr_duration_p90` 来自 `p90_stat`（COMPLETED run 的 duration_ms P90，桥表样本）；PR 流水线明细口径不同。需对齐样本/时长定义。

## 涉及文件

| 文件                                                                                 | 操作 |
| ------------------------------------------------------------------------------------ | ---- |
| PipelineStatusEnum.java                                                              | 修改 |
| RepoPrPipelineDetailResp.java                                                        | 修改 |
| PrInfoResp.java                                                                      | 修改 |
| DmProjectQualityOverviewDayMapper.xml                                                | 修改 |
| OpsMainStatMapper.xml                                                                | 修改 |
| OpsResourceDetailMapper.xml                                                          | 修改 |
| NightlyPipelineDashboardMapper.xml / NightlyPipelineDashboardSummaryServiceImpl.java | 修改 |

## 风险 & 缓解

- 枚举 result 变更影响所有 job 状态展示：已核对 isResult() 仅用于 PipelineJobResp/PipelineRunDetailResp 的 成功/失败 映射，影响面可控。
- NPU 口径切换会导致看板数值系统性变化：符合项目既定口径（npu_detail），属预期修正。
