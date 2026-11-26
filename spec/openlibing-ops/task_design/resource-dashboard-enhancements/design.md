# 资源运营看板能力增强 — 技术设计（草稿）

## 1. 方案选择

### 方案 A：复用现有链路，增量扩展（推荐）

复用 `ops-npu-slot-queue-detail`、`ops-npu-slot-running-detail` 及现有任务分组、跳转、排序逻辑，只增加小时粒度过滤；其他需求在现有 DTO、Service 和 Mapper 中增量实现。

优点：重复代码少，统计口径与使用率分析一致，改动范围可控。缺点：小时过滤需同步修改任务查询和申请卡数查询，必须通过测试防止两处口径不一致。

### 方案 B：新增资源总览专用 detail category

独立实现小时任务查询。隔离性较好，但会重复任务明细、URL、资源池分组等逻辑，形成两套维护口径，不采用。

### 方案 C：仅由前端传小时 startTime/endTime

后端无需修改，但小时下钻只是隐式调用方式，无法清晰表达接口契约，也不符合本次后端增强目标，不采用。

## 2. 热力图小时下钻

### 接口契约

继续使用 `/common/detail`：

- 排队：`category=ops-npu-slot-queue-detail`
- 运行：`category=ops-npu-slot-running-detail`

`OpsNpuSlotTaskDetailReq` 移除 `slotTime`、`slotGranularity`。前端点击热力图格子或折线图时点时，将选中窗口的开始、结束时间写入继承自 `DetailReq` 的 `startTime/endTime`，并按页面条件携带 `serverIp/projectId/resourcePoolIds`。

### 查询语义

- `querySlotTasks` 与 `querySlotTaskNpu` 仅使用 `slot_time BETWEEN startTime AND endTime`，不再叠加单个切片或小时窗口条件。
- 两个查询使用同一时间条件，确保任务列表与申请卡数来自同一窗口。
- 排队、运行判定及任务完整时长、分组和不分页返回逻辑保持不变。

## 3. 跳转仓库信息

### 3.1 `ops-pipeline-run-detail`

`OpsPipelineRunDetailResp` 新增 `repoUrl`。`platform` 已存在，不重复添加。

`ResourceEfficiencyMapper.xml` 中从 `dm_rd_efc_project_pipeline_relation` 按 `pipeline_id + platform` 预聚合 `MAX(pipeline_project) AS repo_url`，再关联到运行明细。预聚合保证一条运行仍只返回一行，避免关系表多行导致分页和记录数放大。

### 3.2 `nightly-dashboard`

在现有 `sdi` 流水线集合 CTE 中补充 `MAX(pipeline_project) AS repo_url`，经 `pipeline_stats`、`finalSelect` 透传到 `NightlyPipelineDashboard` 和 `NightlyPipelineDashboardResp`。响应字段标记 `@ExcelIgnore`，不改变导出列。

已有 `projectId/platform/pipelineId` 保持不变，前端根据平台和仓库地址拼接流水线页面 URL。

## 4. run-analysis 排序

在 `ResourceOperationService.toServerCells` 完成资源池元数据组装后统一排序：

1. `pool` 按字符串升序，`null` 排最后。
2. 同一资源池内 `ip` 按字符串升序。

`allocServers` 和 `usageServers` 使用同一比较器。不能只给 XML 增加 `ORDER BY`，因为 Service 会重新按 IP 集合组装结果。现有一机多池元数据取舍不在本次调整范围内。

## 5. PR 平均排队时长

`OpsProjectResourceEfficiencyResp` 新增：

| 字段 | 类型 | 单位 | 口径 |
| --- | --- | --- | --- |
| `prAvgQueueMinutes` | Double | 分钟 | 每个 PR run 取排队最长的 job 作为 run 样本，再对全部 run 样本求平均 |

在现有 `qagg` 中与 `PERCENTILE(..., 0.9)` 并列增加 `AVG(sample_duration) / 60.0`，经 `pr_agg` 和最终 SELECT 透传。Service 复用 `NumberUtil.roundDecimalOrNull` 保留两位小数，无样本保持 `null`。

该方案复用同一批 `queue_sample`，不新增申请表扫描，不改变 `queueP90` 口径。

## 6. SQL 与性能约束

已参考工程能力运营主看板按 PR、Nightly、Resource 等领域拆查询并并行组装的实现。本次修改不引入新的跨领域聚合：

- 平均排队与 P90 共用样本和同一聚合，不拆成重复查询。
- Nightly 仅在已有流水线关系 CTE 中透传仓库字段。
- 运行明细的仓库关系先按流水线、平台预聚合，再 LEFT JOIN，避免记录放大。
- 小时下钻利用现有 `slot_time/server_ip` 过滤和资源池机器范围子查询，不增加全表额外扫描。

因此本次不做形式化的大 SQL 拆分。若后续运行明细查询继续加入其他数据域，再按主看板方式独立查询并在 Service 组装。

## 7. 错误处理与兼容性

- 前端下钻请求统一传 `startTime/endTime`，不再传 `slotTime/slotGranularity`。
- 无法补充仓库地址时 `repoUrl` 返回 `null`，不影响其他指标。
- 平均排队无样本时返回 `null`，不兜底为 0。
- 空池名不参与异常处理，统一排最后；空列表仍返回空列表。

## 8. 测试设计

- 小时下钻：覆盖小时内多个 5 分钟切片、跨小时隔离、原 5 分钟等值行为，以及任务与申请卡数过滤一致。
- 运行明细：验证 `platform/repoUrl` 透传，检查仓库关系预聚合和 JOIN 键。
- Nightly：验证 Model → Response 的 `repoUrl` 映射，检查 CTE 和 ResultMap 透传。
- run-analysis：构造 Mapper 乱序数据，分别断言 alloc/usage 的完整 `(pool, ip)` 顺序及空池名位置。
- 平均排队：验证字段映射、两位小数和 `null` 保持。
- 执行相关单元测试及 Maven 编译；不默认执行完整质量门禁，除非用户另行要求。

## 9. 交付约束

- 业务分支：`feat-resource-dashboard-enhancements`
- 文档分支：`spec-openlibing-ops-resource-dashboard-enhancements`
- 只修改 `openlibing-ops` 和本需求文档目录。
- 不修改数据库，不做无关重构或格式化。
- 按用户要求，本轮完成后先不 commit、不 push、不创建 PR。

## 10. 工程能力看板仓库范围过滤

`OpsProjectResourceEfficiencyReq` 新增可选 `Boolean engineeringScope`。缺省或为 `false` 时不生成范围过滤 SQL，保持原有行为；为 `true` 时，`queryProjectEfficiencyList` 与 `countProjectEfficiencyList` 使用同一项目范围：

- 项目至少绑定一个资源池，且在 `sdi_repo_info` 中至少存在一个仓库属于 `sdi_rd_efc_repo_operate_conf.is_operate = 1` 的运营仓集合。
- 项目过滤使用 `EXISTS`，避免一对多仓库关系导致项目、分页和 count 放大。
- PR 排队与 PR NPU 指标只统计运营仓 run；在公共 `prRunRelation` 的 `EXISTS` 内关联 `sdi_repo_info`，通过 `git_url = repo_url` 匹配仓库。
- GitHub run 额外匹配 `dim_ecod_github_show_pr_config`，按项目、仓库地址和 workflow 名称限定，与工程能力运营主看板一致。
- 资源池利用率、占用率没有仓库维度，不强行按仓库拆分；入围项目仍保留其项目级资源池指标。
- 不预查仓库 ID 列表，不引入 JOIN 放大；条件化 SQL 仅在 `engineeringScope=true` 时增加 `EXISTS` 子查询。

测试覆盖 `true`、`false` 和缺省三种动态 SQL，断言列表/count 同口径、PR 两个聚合分支均限定运营仓及 GitHub 展示配置，并验证兼容行为。执行：

```powershell
mvn "-Dtest=ResourceEfficiencyMapperXmlTest,ResourceEfficiencyServiceTest" test
mvn spotless:check
```

## 11. 流水线每日排队 P90 趋势

### 11.1 接口方案

在现有 `/common/chart` 体系新增 `category=ops-pipeline-queue-p90`，请求复用平均卡时趋势的项目、流水线类型和时间范围参数，响应沿用 `ChartResp` 的 `xAxis + series`。不扩展 `ops-pipeline-resource-efficiency`，避免一个 category 同时承担两张图的语义。

每条流水线返回一条折线，首条返回“全部流水线”。每个 run 取最大 job `pending_seconds` 作为样本，按窗口内最早申请时间归属日期；PR/Nightly 范围、GitHub run 约束和节假日过滤与流水线资源效率列表一致。窗口最长 30 天，缺样本日期补 0，分钟值保留两位小数。

### 11.2 聚合与性能

SQL 单次扫描时间范围内的申请表，先按 pipeline+run+job 去重，再形成 pipeline+run 级排队样本。基于同一样本集合分别计算单流水线每日 P90 和全部流水线每日 P90，避免前端对各流水线 P90 做无统计意义的平均或汇总。

“全部流水线”直接由全量 run 样本计算。Service 只负责日期补零、系列组装和舍入，不逐流水线发起查询。

## 12. run-analysis 单任务卡时汇总

`OpsPipelineRunAnalysisResp` 新增顶层 `taskSummaries`，每条包含 `jobId`、`taskName`、`npuHours`、`serverIps`。按 `jobId` 聚合当前 `queryRunSlots` 已返回的全部机器和小时切片，机器列表去重后排序。

卡时直接累加原始 `assign_npu_second`，最后统一除以 3600 并保留两位小数，避免先舍入单机卡时再求和造成误差。该过程为内存聚合，不新增 Mapper 查询。

原 `labels`、`allocServers`、`usageServers` 及其 `jobs[]` 继续按现有逻辑生成，任务汇总只作为新增独立返回，不改变两张 NPU 热力图的数据和任务连线。

## 13. 新增功能测试与前端交付

- 趋势 Service：覆盖全部/单流水线系列、缺日补零、两位小数、空数据和 PR/Nightly 默认值。
- 趋势 SQL：覆盖 run 级样本、日归属、PR/Nightly 动态条件和全量 P90 独立聚合。
- run-analysis：覆盖跨机器、跨小时卡时累加，机器去重排序，以及旧热力图和任务连线不变。
- 执行相关单元测试、Maven 编译和 Spotless 检查。
- 更新 `frontend-integration.md`，提供 category、请求响应示例、任务汇总字段和前端自测清单；不修改 `openlibing-ops-web`。
- 按用户要求，本轮完成后不 commit、不 push、不创建 PR。
