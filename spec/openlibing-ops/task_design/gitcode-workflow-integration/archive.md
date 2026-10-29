# gitcode-workflow-integration — 归档

## 需求背景

将 GitCode 平台的 Workflow（PR 流水线）运行数据接入研发效能数仓与运营看板，与既有 codearts、github 两平台数据合并统计，消除"双平台 UNION + 名称匹配 + 硬编码兜底"的维护成本。分两期交付：

- phase_a（初版）：gitcode 数据链路接入（DS 采集任务 + dwi 层扩展），配套 ETL 在生产任务上打补丁分支，已全部被 v0.5 方案取代，脚本不再维护。
- phase_v0.5（最终版）：dwr 层建三平台归一事实表，ETL 与后端聚合查询统一切换归一口径。

本归档只沉淀 v0.5 最终方案。

## 总体架构

```
dwi 层（平台独立，不做归一）
  codearts: dwi_rd_efc_pipeline_run / _job / _step
  gitcode:  dwi_rd_efc_workflow_run_gitcode（T1 扩 7 字段）/ _job / _step
                        ↓
dwr 层
  平台专属 fact（子类型，明细/深钻用）：codearts run/job/build fact、gitcode job fact、github run/job fact
  统一事实表（超类型，聚合/跨平台用，platform 打标）：
    dwr_rd_efc_pipeline_run_unified       ← run 级（UNIQUE KEY: platform, project_id, pipeline_id, pipeline_run_id）
    dwr_rd_efc_pipeline_run_job_unified   ← job 级（UNIQUE KEY 加 job_id, server_ip，同一 job 跨多机一行一机）
                        ↓
后端 openlibing-ops
  项目/仓库/流水线维度聚合 → 统一事实表；PR 关联经桥表 sdi_rd_efc_pipeline_run_pr_relation_codearts
  platform 字段透出前端，跳转 URL 由前端按 platform 拼接（后端不拼、不落库）
```

设计要点（Kimball 超类型/子类型）：

- 统一表只放三平台共有、可过滤可聚合的字段 + platform 列；纯展示的平台专属字段收 ext_info JSON
- project_id 列存原始归属（codearts=项目ID，gitcode/github=repo_url），repo→project 多对多映射不固化在 dwr，由 dm 层 relation（dm_rd_efc_project_pipeline_relation）解析
- event / pull_request_id 不入统一表：PR 绑定统一走桥表（E8 后三平台覆盖）
- 状态统一大写枚举直出；job_type 三平台同规则分类（BUILD/CHECK/DT/OTHER）
- run 级三时间：start_time（触发）/ run_start_time（实际执行开始=MIN(job_start_time)）/ end_time；queue_ms = MIN(job_start_time) - start_time
- retry_count 预留字段（恒 0），后续接重试数据表结构无需变更

## 关键口径

| 项             | 口径                                                                                                                   |
| -------------- | ---------------------------------------------------------------------------------------------------------------------- |
| nightly 判定   | relation 表 pipeline_type='NIGHTLY'，不再 UNION sdi_version_pipeline_base_info                                         |
| PR 门禁判定    | 桥表 pr_id IS NOT NULL 即算，不看流水线名称/类型；项目归属按 repo 单项目                                               |
| github nightly | 不纳入 E4/E5 fact（无测试用例数据，is_version_available 恒 0 会拉低版本可用度）                                        |
| 分位数         | 实时从统一表 PERCENTILE 计算，不预聚合                                                                                 |
| 跨平台 id join | pipeline_id 三平台实测无碰撞（32 位 hex vs 9 位纯数字），ETL 简化为不带 platform join；后端 join 统一表建议带 platform |

## 数据层交付（数据组）

| 顺序 | 脚本           | 职责                                                                                                                       |
| ---- | -------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1    | T1             | dwi_rd_efc_workflow_run_gitcode 扩 7 字段                                                                                  |
| 2    | E1             | gitcode workflow 运行数据计算按扩字段重写（历史回刷同脚本）                                                                |
| 3    | T2/T3          | 建 run/job 统一事实表                                                                                                      |
| 4    | E7             | dwi 统一表任务删 gitcode UNION 分支（先消除污染源）                                                                        |
| 5    | E2             | 新建 DS 任务"三平台归一计算"，每小时调度，48h 增量窗口 + 每日低峰全量兜底                                                  |
| 6    | E3             | PR 维度统计切统一表，PR 口径统一为"run 带 pr_id"                                                                           |
| 7    | E4             | nightly 事实表切统一表 + relation 化判定 + step 补 gitcode                                                                 |
| 8    | E5_1/E5_2/E5_4 | 工程能力看板任务 nightly 维统一 relation、fact 源切统一表                                                                  |
| 9    | E6             | 并发统计 tmp 表补 gitcode 分支（pipeline_run_number 取 dwi_rd_efc_workflow_run_gitcode）                                   |
| 10   | E8             | PR 绑定桥表补 github 分支（三平台覆盖）                                                                                    |
| 11   | E9             | relation 清洗：nightly 归属修正（NIGHTLY 优先于 PR 判定，version_base 注册的 nightly 流水线正确归类），truncate 后全量重建 |

E9 执行后需重跑 E4/E5 系列 nightly fact，并验证各项目 fact_pipelines 与 nightly_pipelines 数量一致。

## 后端交付（openlibing-ops，分支 feat-gitcode-workflow-unified）

### 最终实现（含两处方案纠偏）

1. **基建**：DwrRdEfcPipelineRunUnified / DwrRdEfcPipelineRunJobUnified 实体 + Mapper + Service（MyBatis-Plus）。
2. **PR 详情查询**：gitcode 不建独立 handler（中途曾按 type=gitcode-workflow 新增 GitcodeWorkflowHandleImpl，后推翻删除），与 codearts 统一由 `PipelineHandleImpl`（type=pipeline）处理：桥表查 run_id → 归一表过滤 platform IN (codearts, gitcode) → job 统一表按 jobType 分 BUILD/DT/CHECK。前端 type 推导保持 `isGithub ? 'workflow' : 'pipeline'` 不变。
3. **跳转字段**：后端不拼 URL（中途曾后端拼接，后调整），run 级返回 platform/pipelineId/pipelineRunId，job 级返回 jobId/platform，前端按 platform 拼。
4. **nightly 看板 relation 化**：OpsNightlyDetailMapper 删除 vllm-ascend Nightly-A2/A3 硬编码 UNION 分支，github nightly 版本可用度改为 relation 驱动现算；OpsMainStatMapper 删除 github_nightly_rate 兜底 CTE，放开 selected_pipelines 的 github 过滤；OpsResourceDetailMapper nightly 资源统计放开 github。
5. **看板 platform 透出**：ops-nightly-detail（relation 直出）、ops-resource-detail（run 统一直出，All 机器行为 NULL）、jobTimeSlot 子表（表无 platform 列，service 层用 run 归一表按 pipelineRunId 批量反查）。
6. **PR 归属口径统一**（前置修复）：主表聚合与钻穿明细统一为 relation 多项目归属 vs repo 单项目口径对齐，PR 分支过滤空 pr_id 的 run。

### 明确不动清单（防止过度修改）

- OpsGithubMapper（github 专属看板）、测试用例看板（codearts 专属）、NpuUsageMapper（npu_detail 三平台 UNION 原有，jobUrl CASE 已覆盖）、WorkflowHandleImpl/WorkflowNewHandleImpl（github 既有链路）、dm/dwr 快照汇总表查询（ETL 产出，SQL 零改动）。

## 前端交付（openlibing-ops-web，4 处）

| 位置                   | 改动                                                                                            |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| pipeline-detail.vue    | 跳转按行 platform 拼：gitcode/github 拼平台 actions 链接，codearts 沿用 getPipelineUrl 站内路由 |
| nightly-tab.vue        | 同上（用页面已有仓库地址拼）                                                                    |
| resource-tab.vue       | 同上                                                                                            |
| concurrency-detail.vue | jobTimeSlot 子表拼 job 级链接                                                                   |

拼接规则：

- gitcode：`https://gitcode.com/${owner}/${repo}/actions/runs/${pipelineRunId}(/job/${jobId})`
- github：`https://github.com/${owner}/${repo}/actions/runs/${pipelineRunId}(/job/${jobId})`
- 前缀即仓库地址去 `.git`；`/job/${jobId}` 可选段仅 job 级行拼

## 交付历程（openlibing-ops）

- commit `2e6dc8ee`：统一 PR 归属口径（工程能力看板主表与明细数值不一致修复，+172/-66）
- commit `41fe663e`：gitcode 合并进统一 pipeline handler，删除独立 GitcodeWorkflowHandleImpl（+122/-413）
- merge `431a99c0`：feat 分支合入 develop_new
- commit `3ca0c1f8`：github nightly 处理统一 relation 口径，清除硬编码兜底（+177/-224）

## 验证与遗留

- 单测：PipelineHandleImplTest(27) / PipelineControllerTest(2) / RepoPrPipelineDetailRespTest(5) / DwiPipelineJobTimeSlotServiceImplTest(4) 全部通过
- 数据侧验证门槛（V1 对账 / V2 既有指标 diff=0 / 状态展示抽检 / PR 关联抽检 / 性能 P95）按 README §6 由数据组与联调执行
- 口径切换后 PR 样本集变大、nightly 流水线集合以 relation 为准，部分看板数值有系统性偏移属预期，切换前数据组出具 diff 评估
- 跨平台 id join 不带 platform 是隐式假设，新增平台或 id 格式变化时需改为带 platform join
- 后续接重试数据：只需 E2 源头补重试次数计算 + job 去重口径，表结构无需变更

## 归档日期

2026-09-22
