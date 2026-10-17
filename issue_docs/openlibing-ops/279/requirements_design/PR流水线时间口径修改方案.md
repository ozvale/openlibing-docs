# PR 流水线时间口径修改方案

## 1. 背景与目标

### 1.1 现状问题

`/ops-overview/main` 及其仓库级下钻 `/common/detail?category=ops-repo-detail` 中，PR 执行时长与 PR 资源排队时长仍按 **PR 创建时间（`dwi_rd_efc_pr_info_sum.created_at`）** 筛选，而同一接口内的 PR 运行次数、NPU 消耗、Nightly 次数等指标已按 **PR 流水线开始时间（`dwr_rd_efc_pipeline_run_unified.start_time`）** 筛选，存在两套时间口径：

- PR 在窗口内创建、流水线在窗口后才运行 → 当前会计入 PR 时长/排队；
- PR 在窗口前创建、流水线在窗口内运行 → 当前不会计入 PR 时长/排队；
- 同一项目的 PR 时长样本集合与 `prCount`、NPU run 数可能不一致。

### 1.2 目标

将以下两个接口中 **PR 流水线相关的执行时长、排队时长** 统一改为按 **PR 流水线开始时间** 筛选：

1. `POST /ops-overview/main`
2. `POST /common/detail`（`category=ops-repo-detail`）

不涉及 PR 数量、贡献者、PR 生命周期（创建→合入）等非流水线指标。

### 1.3 范围

| 接口                                  | 修改文件                                                           | 修改内容                 |
| ------------------------------------- | ------------------------------------------------------------------ | ------------------------ |
| `/ops-overview/main`                  | `openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`   | `pr_run_sample` 时间谓词 |
| `/common/detail`（`ops-repo-detail`） | `openlibing-ops/src/main/resources/mapper/OpsRepoDetailMapper.xml` | `pr_run_sample` 时间谓词 |

> 两处必须同批修改：`ops-repo-detail` 是运营总览主表的仓库级下钻，展示同名指标，若只改一处会造成同页面上口径撕裂。

---

## 2. 口径定义

### 2.1 采用字段

统一使用 `dwr_rd_efc_pipeline_run_unified.start_time`。

理由：

1. 与 `pr_count`、`unified_npu_stat`、`nightly_count`、`ops-resource-detail` 等已使用 `u.start_time` 的口径一致；
2. `start_time` 已在 `pr_run_sample` 的联表结果中，无需新增关联；
3. 语义为"流水线创建/开始时间"，符合"按 PR 流水线时间筛选"的诉求。

### 2.2 备选字段与取舍

| 字段               | 语义                               | 结论                           |
| ------------------ | ---------------------------------- | ------------------------------ |
| `u.start_time`     | 流水线创建/触发时间                | **采用**，与其他指标一致       |
| `u.run_start_time` | 流水线实际开始执行时间（不含排队） | 不建议，会与其他指标再次不一致 |
| `u.end_time`       | 流水线完成时间                     | 不采用，属于"窗口内完成"口径   |

### 2.3 窗口语义

- 窗口 `[startTime, endTime]` 两端闭区间，与现有 `between` 等价；
- 归属规则：流水线在窗口内开始即计入该窗口；
- 跨窗口运行：以开始时间归属起始窗口，不按完成时间拆分。

---

## 3. 影响面

### 3.1 `/ops-overview/main`

调用链：`OpsOverviewController#queryMain` → `OpsOverviewService#queryMain` → `OpsMainStatMapper#queryMainStat`。

`pr_run_sample` 的两个消费方：

| CTE          | 输出字段                                           | 说明                                             |
| ------------ | -------------------------------------------------- | ------------------------------------------------ |
| `p90_stat`   | `prDurationP90`                                    | PR 执行时长 P90（分钟，Service 层 `/60` 后返回） |
| `queue_stat` | `resourceQueueTime`、`buildQueueP90`、`dtQueueP90` | PR 构建/测试资源排队时长 P90                     |

不受影响：

- `prCpuUsage` / `nightlyCpuUsage`：来自 `dwi_project_resource_indicator_day`，按 `stat_date` 日期段；
- `prNpuUsage` / `prNpuAvg`：`unified_npu_stat` 已按 `u.start_time`；
- `prCount`（`prCpuAvg` 分母）：已按 `u.start_time`；
- `passStatus`：仅消费 `prDurationP90` 结果，逻辑不变，但数值变化可能导致绿灯/红灯翻转。

### 3.2 `/common/detail?category=ops-repo-detail`

调用链：`CommonController#queryDetail` → `CommonService#queryDetail` → `OpsRepoDetailDetailService#queryDetail` → `OpsOverviewService#queryRepoDetail` → `OpsRepoDetailMapper#queryRepoDetail`。

`pr_run_sample` 的两个消费方：

| CTE         | 输出字段                                           |
| ----------- | -------------------------------------------------- |
| `e2e_p90`   | `prDuration`                                       |
| `queue_p90` | `resourceQueueTime`、`buildQueueP90`、`dtQueueP90` |

---

## 4. 修改方案

### 4.1 `OpsMainStatMapper.xml`

文件：`openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`

#### 4.1.1 核心修改（`pr_run_sample`，第 95 行）

修改前：

```sql
WHERE pr.created_at between #{req.startTime} and #{req.endTime}
```

修改后：

```sql
WHERE u.start_time &gt;= #{req.startTime}
  AND u.start_time &lt;= #{req.endTime}
```

> MyBatis XML 中需使用实体转义：`&gt;=`、`&lt;=`。

#### 4.1.2 注释同步

| 位置      | 修改前                                            | 修改后                                                   |
| --------- | ------------------------------------------------- | -------------------------------------------------------- |
| 第 50 行  | `按 PR创建时间取数`                               | `按 PR 流水线 start_time 取数`                           |
| 第 112 行 | `按 PR创建时间取 COMPLETED 运行效率时长`          | `按 PR 流水线开始时间取 COMPLETED 运行效率时长`          |
| 第 127 行 | `project 级直接按 PR创建时间取全部状态运行算 P90` | `project 级直接按 PR 流水线开始时间取全部状态运行算 P90` |

#### 4.1.3 保持不变

- `pr_run_sample` 的 `SELECT DISTINCT` 去重；
- `dwi_rd_efc_pr_info_sum` 与桥表、run 统一表的关联关系（用于确定 PR 存在性与项目归属）；
- GitHub run 白名单 `EXISTS` 条件；
- `p90_stat` 的 `status='COMPLETED' AND end_time IS NOT NULL`；
- `queue_stat` 的 `s.end_time IS NOT NULL`。

### 4.2 `OpsRepoDetailMapper.xml`

文件：`openlibing-ops/src/main/resources/mapper/OpsRepoDetailMapper.xml`

#### 4.2.1 核心修改（`pr_run_sample`，第 86 行）

修改前：

```sql
WHERE pr.created_at between #{req.startTime} and #{req.endTime}
```

修改后：

```sql
WHERE u.start_time &gt;= #{req.startTime}
  AND u.start_time &lt;= #{req.endTime}
```

#### 4.2.2 注释同步

在第 43-45 行的取数说明中补充：`时间统一按 run 统一表 start_time 过滤`。

#### 4.2.3 保持不变

- `u.pipeline_id IN (SELECT pipeline_id FROM dm_rd_efc_project_pipeline_relation WHERE pipeline_type = 'PR')`；
- GitHub run 白名单 `EXISTS` 条件；
- `e2e_p90` / `queue_p90` 的聚合逻辑；
- 仓库列表骨架来自 `dwi_repo_quality_scan_day` 最新快照，不变。

### 4.3 可选优化（非必需）

`dwi_rd_efc_pr_info_sum` 在改为按 run 时间过滤后，可保留一个安全上界用于剪枝：

```sql
AND pr.created_at &lt;= #{req.endTime}
```

依据：PR 必然早于其流水线运行，加上界不会误过滤；是否添加以 `EXPLAIN` 结果为准。

---

## 5. 行为变化与影响评估

### 5.1 计入规则变化

| 场景                            | 修改前             | 修改后         |
| ------------------------------- | ------------------ | -------------- |
| PR 窗口前创建，流水线窗口内运行 | 不计入             | **计入**       |
| PR 窗口内创建，流水线窗口内运行 | 计入               | 计入           |
| PR 窗口内创建，流水线窗口后运行 | 计入               | **不计入**     |
| PR 窗口内创建，流水线未完成     | 计入（若后续完成） | 视开始时间归属 |

排队三字段与执行时长同步变化。

### 5.2 实测影响示例

窗口 `2026-09-08 ~ 2026-10-08`，项目级 COMPLETED run 对比：

| project_id | 旧口径 run 数 | 旧口径 P90(秒) | 新口径 run 数 | 新口径 P90(秒) |
| ---------- | ------------- | -------------- | ------------- | -------------- |
| 4          | 4158          | 4504.5         | 5797          | 4112.2         |
| 300033     | 18531         | 1445.2         | 21108         | 1438.0         |
| 300057     | 1763          | 3277.6         | 2164          | 3283.4         |
| 300073     | 27            | 341.6          | 27            | 341.6          |
| 300091     | 1735          | 2240.2         | 2026          | 2268.0         |

结论：样本量与 P90 会发生变化，属于口径切换的预期结果。

### 5.3 前端与联动影响

- 主表"PR执行时长[P90]"展示值变化；
- 达标灯 `passStatus`（GREEN/RED）可能翻转，属预期；
- 下钻 `ops-repo-detail` 与主表时间口径一致后，同页面数值可互相解释；
- 前端无需改动（排序、亮灯均消费返回值）。

### 5.4 明确不解决的问题

- `300077`（triton-ascend）、`300127`（vllm-ascend）等项目的 `prDurationP90` 为 `null`，原因是桥表 `sdi_rd_efc_pipeline_run_pr_relation_codearts` 缺少对应 GitHub 仓 URL 的关联行，与时间口径无关，本次不处理。

### 5.5 已知口径差异（本次不处理）

- 主接口 `pr_run_sample` 未加 `pipeline_type='PR'` 过滤，而 `ops-repo-detail`、`repo-pr-pipeline` 加了该过滤，两者样本集合存在细微差异；
- 建议后续单独评估是否统一，避免与本次时间口径变更混合。

---

## 6. 风险评估

| 风险                                            | 等级 | 应对                                         |
| ----------------------------------------------- | ---- | -------------------------------------------- |
| 两处未同批修改导致项目级/仓库级口径不一致       | 高   | 同一提交内完成两处修改                       |
| P90 与亮灯变化被误判为缺陷                      | 中   | 上线前与产品确认口径，并保留修改前后对比数据 |
| `u.start_time` 过滤导致执行计划变化、扫描量上升 | 中   | 修改前后分别 `EXPLAIN`，确认时间过滤可下推   |
| GitHub 项目仍为 null 被误认为本次引入           | 中   | 在验收说明中明确该问题独立存在               |
| 注释未同步导致后续维护误解                      | 低   | 与代码同批更新注释                           |

---

## 7. 验证方案

### 7.1 SQL 级验证

1. 同一窗口分别以 `pr.created_at` 与 `u.start_time` 计算，逐项目/逐仓对比 run 数与 P90；
2. 抽样人工计算 `PERCENTILE(duration_ms/1000, 0.9)`，与接口返回核对；
3. 确认 `null` 项目集合无新增异常。

### 7.2 接口级验证

1. `POST /ops-overview/main`：同一项目、同一窗口，检查 `prDurationP90`、`resourceQueueTime`、`buildQueueP90`、`dtQueueP90`；
2. `POST /common/detail`（`category=ops-repo-detail`）：检查 `prDuration` 与三个排队字段；
3. 核对主表与下钻的样本时间窗口一致；
4. 抽查 `passStatus` 接近阈值的项目，确认翻转符合新值。

### 7.3 边界验证

- 单日窗口（`startDate = endDate`）；
- 跨月、跨季度窗口；
- 窗口内无流水线运行的项目/仓库（应返回 `null` 或 `--`，不应报错）；
- 运行中（未结束）的流水线不参与时长 P90。

### 7.4 性能验证

- 对 `queryMainStat`、`queryRepoDetail` 修改前后执行 `EXPLAIN`，对比扫描行数、耗时；
- 重点确认 `u.start_time` 条件能下推到 run 统一表。

### 7.5 回归范围

- `/ops-overview/main` 排序、分页、亮灯；
- `ops-repo-detail` 分页、排序、`noPipelineReason` 等非时长字段；
- 本次不修改 Mapper 单元测试（现有测试未覆盖该 SQL 口径）。

---

## 8. 上线与回滚

- 无 DDL、无数据迁移、无前端改动；
- 两处 Mapper 修改合并为同一提交；
- 回滚时两处同时还原，避免口径不一致；
- 建议上线说明中同步告知"PR 时长/排队口径由 PR 创建时间切换为 PR 流水线开始时间"。

---

## 9. 附件：修改点清单

| 序号 | 文件                                                               | 行号         | 修改                             |
| ---- | ------------------------------------------------------------------ | ------------ | -------------------------------- |
| 1    | `openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`   | 95           | `pr.created_at` → `u.start_time` |
| 2    | `openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`   | 50、112、127 | 注释口径同步                     |
| 3    | `openlibing-ops/src/main/resources/mapper/OpsRepoDetailMapper.xml` | 86           | `pr.created_at` → `u.start_time` |
| 4    | `openlibing-ops/src/main/resources/mapper/OpsRepoDetailMapper.xml` | 43-45        | 注释口径同步                     |
