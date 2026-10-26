# #293 任务分解

## 1. 基本信息

| 项目       | 内容                                                                                                                 |
| ---------- | -------------------------------------------------------------------------------------------------------------------- |
| 需求文档   | [需求_feature_293.md](./需求_feature_293.md)                                                                         |
| 关联 Issue | https://gitcode.com/openlibing/openlibing-ops/issues/293                                                             |
| 开发分支   | `feature_293`                                                                                                        |
| 后端仓库   | openlibing-ops                                                                                                       |
| 指标字典   | openlibing-metric                                                                                                    |
| ETL        | DolphinScheduler（仓库外）                                                                                           |
| 目标       | 排队 P90、NPU 消耗/平均/使用率统一为成功运行口径；例外备案改为最近 10 次成功运行中任一次单次达标；主表与下钻保持一致 |

## 2. 任务总览

| 编号 | 任务                      | 仓库/模块                    | 主要文件                                             | 依赖   | 验收要点                                     |
| ---- | ------------------------- | ---------------------------- | ---------------------------------------------------- | ------ | -------------------------------------------- |
| T0   | 口径冻结与基线采集        | 数据/产品                    | —                                                    | 无     | 确认例外备案分母、回刷范围；保存改造前基线   |
| T1   | 主表 PR 排队 P90 成功口径 | openlibing-ops / 主表        | `OpsMainStatMapper.xml`                              | T0     | 构建/测试排队 P90 仅取成功运行               |
| T2   | 主表 NPU 成功口径         | openlibing-ops / 主表        | `OpsMainStatMapper.xml`                              | T0     | NPU 消耗、平均、使用率均为成功口径；CPU 不变 |
| T3   | 仓库级 PR 下钻对齐        | openlibing-ops / 下钻        | `OpsRepoDetailMapper.xml`、`OpsRepoDetail*Resp.java` | T1、T5 | 排队 P90 成功口径；例外备案直读 ETL 结果     |
| T4   | 环境资源下钻对齐          | openlibing-ops / 下钻        | `OpsResourceDetailMapper.xml`                        | T2     | NPU 与主表可对账；CPU、行集不变              |
| T4b  | 运行记录接口与 Excel 标注 | openlibing-ops               | `OpsResourceRun*`、`OpsOverviewMainResp.java`        | T4     | 接口支持 onlySuccess；Excel 表头标注成功口径 |
| T5   | ETL 仓库级例外备案重写    | DolphinScheduler             | `dwi_repo_pipeline_quality_day`                      | T0     | 最近 10 次成功运行中任一次单次达标           |
| T6   | ETL 项目级例外备案率      | DolphinScheduler             | `dm_project_quality_overview_day`                    | T5     | 项目率与仓库级达标结果一致                   |
| T7   | 指标字典与文案            | openlibing-metric / 指标平台 | 指标定义数据                                         | T0     | 指标含义、统计范围与新口径一致               |
| T8   | 回归验证与发布            | Doris / 页面                 | —                                                    | T1-T7  | 数据、接口、页面、性能全部通过               |
| T9   | 历史数据回刷（可选）      | DolphinScheduler             | 相关 ETL 任务                                        | T6、T8 | 回刷范围确认并完成对账                       |

## 3. 详细任务

### T0 口径冻结与基线采集

**目标**：在改代码前固定验收基线，避免口径反复。

**步骤**：

1. 确认例外备案项目级分母：
   - 建议口径：`达标仓库数 / 有成功运行且 flag 非空的仓库数`；
   - 如现网不同，由产品与数据侧确认后冻结。
2. 确认历史数据是否回刷；默认只对新日期生效。
3. 采集改造前基线，建议项目：`2、4、300036、300037、300091`，日期：`2026-10-20 ~ 2026-10-23`。
4. 基线内容：
   - 主表 `buildQueueP90 / dtQueueP90 / prNpuUsage / prNpuAvg / prNpuRate`；
   - Nightly、整体 NPU 指标；
   - 仓库级排队 P90、环境资源明细 NPU；
   - 例外备案项目率与仓库级 flag。

**产出**：基线数据表或 Markdown，附在验证记录中。

---

### T1 主表 PR 排队 P90 成功口径

**文件**：`openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`

**步骤**：

1. 在 `pr_run_sample` 中增加 `u.status = 'COMPLETED'`。
2. 保留 `p90_stat` 的 `end_time IS NOT NULL` 与状态判断。
3. 更新 CTE 注释：删除“排队时长不过滤 pipeline_status”，改为成功口径。
4. 确认 `queue_stat` 的构建/测试分项仍分别 `ROUND(..., 2)` 后相加。

**验收**：

- `buildQueueP90`、`dtQueueP90`、`resourceQueueTime` 仅由成功 PR run 计算；
- `prDurationP90` 数值不变；
- 失败 run 不再进入排队样本。

---

### T2 主表 NPU 成功口径

**文件**：`openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`

**步骤**：

1. `unified_npu_stat` 的 PR 分支增加 `u.status = 'COMPLETED'`。
2. Nightly 分支同样增加状态过滤。
3. 确认以下字段变为成功口径：
   - `prNpuUsage / prNpuAvg / prNpuRate`；
   - `nightlyNpuUsage / nightlyNpuAvg / nightlyNpuRate`；
   - `overallNpuUsage / overallNpuAvg / overallNpuRate`。
4. 确认 CPU 相关 CTE、NPU 总量、机器占用卡时未改动。
5. 更新字段注释，明确“成功运行口径”。

**验收**：

- NPU 消耗、平均、使用率均可通过成功运行 SQL 复算；
- CPU 指标与改造前一致；
- NPU 总量、`npuAllAssignedHours` 不变。

---

### T3 仓库级 PR 下钻对齐

**文件**：

- `openlibing-ops/src/main/resources/mapper/OpsRepoDetailMapper.xml`
- `openlibing-ops/src/main/java/com/openlibing/ops/api/response/ops/OpsRepoDetailResp.java`
- `openlibing-ops/src/main/java/com/openlibing/ops/api/response/common/detail/OpsRepoDetailDetailResp.java`

**步骤**：

1. `pr_run_sample` 增加 `u.status = 'COMPLETED'`，使构建/测试排队 P90 与主表一致。
2. `uses_proper_codecheck` 改为直读 ETL 字段，不再由 `has_old_codecheck` / `has_new_codecheck` 推导。
3. `codecheck_detail` 优先判断 `uses_proper_codecheck = 1`，达标时返回 `NULL`。
4. 更新 `usesProperCodecheck`、`hasOldCodecheck`、`hasNewCodecheck` 注释：
   - `usesProperCodecheck`：最近 10 次成功运行中任一次单次达标；
   - `hasOldCodecheck` / `hasNewCodecheck`：最近一次成功运行，仅用于明细展示。

**验收**：

- 仓库级排队 P90 与主表使用同一状态口径；
- 达标仓库不展示旧版 codecheck 告警；
- 不达标仓库的明细文案来自最近一次成功运行。

---

### T4 环境资源下钻对齐

**文件**：`openlibing-ops/src/main/resources/mapper/OpsResourceDetailMapper.xml`

**步骤**：

1. PR / Nightly 流水线列表内层样本增加 `u.status`。
2. 使用 NPU 条件聚合：
   - `npu = SUM(CASE WHEN status='COMPLETED' THEN npu_second END) / 3600`；
   - `npu_run_count = COUNT(DISTINCT CASE WHEN status='COMPLETED' AND npu_second > 0 THEN pipeline_run_id END)`；
   - `npu_avg = npu / NULLIF(npu_run_count, 0)`。
3. `queryResourceSummary` 同步条件聚合，`total_npu_avg` 使用成功 NPU 运行数。
4. `queryResourceDetail` 旧查询同步处理，避免后续误用。
5. 行集、`countResourceDetailList`、CPU 聚合保持不变。

**验收**：

- 主表 `prNpuUsage` = 资源明细 PR 列表 `npu` 之和；
- 主表 `prNpuAvg` = `SUM(npu) / SUM(npu_run_count)`；
- CPU 字段与改造前一致；
- 无成功运行的流水线 NPU 为空，页面展示 `--`。

---

### T4b 运行记录接口与 Excel 标注

**文件**：

- `openlibing-ops/src/main/java/com/openlibing/ops/api/request/ops/OpsResourceRunReq.java`
- `openlibing-ops/src/main/java/com/openlibing/ops/api/request/common/detail/OpsResourceRunsDetailReq.java`
- `openlibing-ops/src/main/resources/mapper/OpsResourceRunMapper.xml`
- `openlibing-ops/src/main/java/com/openlibing/ops/api/response/ops/OpsOverviewMainResp.java`

**步骤**：

1. 运行记录请求增加 `onlySuccess`，列表和 count SQL 同步过滤。
2. 前端本次不修改，默认仍展示全量；接口层可使用 `onlySuccess=true` 获取成功运行。
3. Excel 导出表头对 PR 执行时长、构建/测试排队 P90、PR/Nightly/整体 NPU 消耗与平均标注“成功运行”。

**验收**：

- 默认展示全量运行记录；接口传 `onlySuccess=true` 时只展示成功运行，分页总数同步减少；
- 接口开启成功筛选后，运行记录 NPU 之和可与成功口径 KPI 对账；
- Excel 导出表头能明确识别成功口径列。

---

### T5 ETL 仓库级例外备案重写

**目标表**：`dwi_repo_pipeline_quality_day`

**步骤**：

1. 每个仓库取截至 `D-1 23:59:59` 的最近 10 次成功 PR run，按 run 去重。
2. 按单次运行计算：
   - `run_has_new_codecheck`：job 名命中 `pre-commit` / `lintrunner`；
   - `run_has_old_codecheck`：job 名含 `codecheck` 且不含 `pre-commit` / `lintrunner`。
3. 仓库级 `uses_proper_codecheck`：最近 10 次中任一次满足 `new=1 且 old=0`。
4. 仓库级 `has_old_codecheck` / `has_new_codecheck`、job 明细：取最近一次成功运行。
5. 无成功运行时，上述字段写 `NULL`。
6. 复用现有字段，无 DDL 变更。

**验收场景**：

- 最新运行失败，但历史成功运行存在仅新版检查；
- 一次旧版运行 + 一次仅新版运行，判定达标；
- 每次运行都新旧并存，判定不达标；
- 全部只有旧版或无检查任务，判定不达标；
- 成功运行不足 10 次；
- 从未有成功运行。

---

### T6 ETL 项目级例外备案率

**目标表**：`dm_project_quality_overview_day`

**步骤**：

1. 按项目统计 `uses_proper_codecheck = 1` 的仓库数。
2. 分母使用有成功运行、flag 非空的仓库数。
3. 更新 ETL 注释与口径说明。
4. 与改造前项目率对比，记录差异并确认。

**验收**：

- 项目率 = 达标仓库数 / 参与统计仓库数；
- 仓库级明细与项目级率来自同一 `uses_proper_codecheck`；
- 无成功运行的仓库不进入分母。

---

### T7 指标字典与文案

**文件/平台**：`openlibing-metric`、指标管理平台

**步骤**：

1. 更新“例外备案和 committer 审核一体化率”：
   - 最近 10 次成功 PR 运行中，任一次仅新版检查即达标。
2. 更新“NPU 消耗(卡时)”“NPU 平均消耗(卡时)”：
   - 统计范围改为成功运行；
   - 平均分母为有 NPU 消耗的成功运行数。
3. 更新“PR 资源排队时长”“PR 构建/测试资源排队时长 P90”：
   - 统计范围改为成功运行。
4. 发布指标字典并确认页面提示已刷新。

**验收**：

- 页面指标提示与新口径一致；
- 不再出现“统计全部运行”或“最新一次运行”的旧描述。

---

### T8 回归验证与发布

**步骤**：

1. 按 T0 基线逐项对比主表、仓库级、资源级数据。
2. 验证 CPU、PR 执行时长、NPU 总量、机器占用卡时未变化。
3. 验证 NPU 消耗、平均、使用率变化方向合理。
4. 执行后端质量门禁：

```bash
mvn spotless:apply
mvn checkstyle:check
mvn spotbugs:check
mvn pmd:check
mvn test
```

5. 页面验证主表、PR Tab、资源环境 Tab、导出 Excel。
6. 对主表和环境资源接口做 `EXPLAIN` / `Profile`，确认性能无明显退化。
7. 编写发布说明，明确指标口径变化。

**验收**：

- 所有验收项通过；
- 无阻塞性性能问题；
- 发布说明已通知看板使用方。

---

### T9 历史数据回刷（可选）

**前提**：T0 已确认回刷范围。

**步骤**：

1. 优先回刷最近 7 天 `dwi` / `dm` 数据。
2. 回刷后重新核对项目率与仓库级 flag。
3. 保留回刷前快照，便于回滚比对。

**验收**：

- 回刷日期范围内项目率与仓库级结果一致；
- 主表快照读取正常；
- 回刷脚本可重复执行。

## 4. 依赖与实施顺序

```text
T0
├── T1 ── T3（排队部分）
├── T2 ── T4 ── T4b
├── T5 ── T3（例外备案消费）
│         └── T6
└── T7

T1-T7 ── T8 ── T9（可选）
```

建议顺序：

1. T0 口径冻结与基线；
2. T1、T2 后端主表；
3. T5、T6 ETL；
4. T3、T4 下钻对齐；
5. T4b 运行记录筛选与 Excel 标注；
6. T7 指标字典；
7. T8 回归与发布；
8. T9 按需回刷。

## 5. 验收清单

- [ ] 排队 P90 仅统计成功运行。
- [ ] NPU 消耗总量、平均、使用率仅统计成功运行。
- [ ] CPU 指标、PR 执行时长、NPU 总量未变化。
- [ ] 主表与仓库级排队口径一致。
- [ ] 主表 NPU 与环境资源明细可对账。
- [ ] 运行记录默认全量；接口支持 `onlySuccess` 可选筛选（前端不接入）。
- [ ] Excel 成功口径列已标注“成功运行”。
- [ ] 仓库级例外备案直读 ETL `uses_proper_codecheck`。
- [ ] 例外备案按“单次运行达标”判定，最近 10 次任一次即可。
- [ ] 达标仓库不展示旧版 codecheck 告警。
- [ ] 指标字典文案已更新。
- [ ] 基线对比、页面验证、性能验证、质量门禁全部通过。
- [ ] 发布说明已同步看板使用方。

## 6. 提交与 PR 拆分建议

| PR   | 范围                | 建议提交信息                                                       |
| ---- | ------------------- | ------------------------------------------------------------------ |
| PR-1 | 需求文档 + 任务分解 | `docs(issue-293): add requirement design and task breakdown`       |
| PR-2 | T1-T4、T4b 后端     | `fix(ops-dashboard): scope pipeline metrics to successful runs`    |
| PR-3 | T5-T6 ETL           | 由数据侧按 ETL 任务管理流程提交                                    |
| PR-4 | T7 指标字典         | `chore(metrics): update engineering capability metric definitions` |
| PR-5 | T8 验证记录（可选） | `docs(issue-293): add verification record`                         |

后端 PR 建议拆分为三个提交：

1. `fix(ops-overview): scope queue and npu metrics to successful runs`
2. `fix(ops-detail): align drilldown with successful-run metrics`
3. `feat(ops-resource): add optional successful-run filter for run records`

## 7. 风险与回滚

| 风险                     | 应对                                                   |
| ------------------------ | ------------------------------------------------------ |
| 指标数值整体变化         | 发布说明提前通知；保留基线数据                         |
| ETL 与后端发布不同步     | 先完成 ETL 数据核对，再发布后端；例外备案消费兼容 NULL |
| 例外备案分母与现网不一致 | T0 冻结口径；上线前样例项目对比                        |
| CPU 被误改               | T4 使用条件聚合；回归验证 CPU 不变                     |
| 性能退化                 | 保留时间范围限制；观察 Doris Profile                   |
| 回刷数据异常             | 保留回刷前快照；按日期重跑                             |

回滚方式：

- 后端：回滚 `OpsMainStatMapper.xml`、`OpsRepoDetailMapper.xml`、`OpsResourceDetailMapper.xml`；
- ETL：回滚 DolphinScheduler 任务版本；
- 指标字典：恢复旧指标定义；
- 数据：按回刷前快照重跑对应日期。
