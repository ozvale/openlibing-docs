# 卡数趋势 — 技术设计

## 方案概述

后端在通用图表框架 `/common/chart` 下**新增** category `ops-npu-usage-card-trend`（与 `ops-npu-usage-trend` 同参、同 5 分钟切片口径），返回三条 series；前端新增一个图表组件（结构照搬 `usage-trend-chart.vue`），插入到「趋势分析」与「热力图」之间，下钻复用既有 `open-slot` 事件链路。

无新增技术决策，沿用现有 NPU 使用率分析的分层（CommonChartHandler → ChartService → NpuUsageService → NpuUsageMapper）。

## 数据口径

| 曲线 | 口径 | 取数来源 |
|------|------|---------|
| 总卡数（张） | 该切片**全部活跃任务**（等待任务 ∪ 运行任务，`job_current_slot_pending_seconds > 0 OR job_current_slot_running_seconds > 0`）的申请卡数之和；与使用卡数 / 等待卡数**同源同集合**，恒有 总卡数 = 使用卡数 + 等待卡数；**不再是静态维表的机器容量水平线** | `queryTrendCardSeries` + 片段 `trendActiveJobs`，一次事实表 join + 条件聚合算出三列 |
| 使用卡数（张） | 该切片**归为运行**的任务（互斥归类：`job_current_slot_running_seconds >= job_current_slot_pending_seconds`）按各自「申请卡数」求和；申请卡数与等待卡数同源同算法（三张平台任务事实表 `npu_second / job_duration`，job 级 MAX 去重、四舍五入、下限 1；codearts 历史整点记账 `npu_second % 3600 == 0 → npu_second / 3600`）；**不按机器容量封顶** | 同上（`queryTrendCardSeries` 条件聚合列之一） |
| 等待卡数（张） | 该切片**归为等待**的任务（互斥归类：`job_current_slot_running_seconds < job_current_slot_pending_seconds`）按各自「申请卡数」求和；申请卡数取三张平台任务事实表（`dwr_rd_efc_build_job_fact` / `..._workflow_run_job_gitcode_fact` / `..._workflow_run_job_github_fact`）的 `npu_second / job_duration`，job 级 MAX 去重、四舍五入、下限 1；codearts 历史整点记账数据（`npu_second` 为 3600 整数倍）直接 `÷ 3600` | 同上（`queryTrendCardSeries` 条件聚合列之一） |

- 缺失切片补 0（与其他 5m 类接口一致）。
- codearts 历史整点记账换算已与明细列「申请卡数」统一（同为 `npu_second % 3600 == 0 → npu_second / 3600`），不再存在历史 codearts 任务两处口径不一致的问题。
- **三条卡数曲线与「使用率」脱钩（已知且本期接受）**：总卡数 / 使用卡数 / 等待卡数均为「申请卡数」口径，而使用率（趋势分析曲线 / 热力图 / KPI）仍为分配卡时口径 `Σ assign_npu_hours / Σ total_npu_num`，因此 `使用卡数 ÷ 总卡数 ≠ 使用率`（**总卡数现在也是申请卡数口径，不能写成「使用率 = 使用卡数 / 总卡数」**）。两者在「任务跑满整片」时数学等价（`assign_npu_second` 本身由同一 `npu_second` 按占比分摊而来，`assign × 12 = npu_second / job_duration = 申请卡数`），偏差只来自部分切片启停按整卡计入、四舍五入下限 1、事实表缺数据任务被漏计。是否把使用率也统一到申请卡数口径，留待下期评估。

## 窗口无关不变量（强制）

同一切片的取值不得随查询窗口变化。实现约束：

- **集合**来自切片：活跃任务集合由 5m 表按 `slot_time BETWEEN …` 取 `job_current_slot_pending_seconds > 0 OR job_current_slot_running_seconds > 0` 去重得到，再按互斥规则（`job_current_slot_running_seconds >= job_current_slot_pending_seconds` 归运行，否则归等待）分类；同一 (切片, 任务) 的**归类**只由该切片内的 running / pending 秒数孰大决定，与窗口无关。窗口变化 → 覆盖的切片范围变化，这是正常的。
- **属性**按 job 主键取、不做时间过滤：申请卡数一律从平台任务事实表按 `platform + job_id` 取 job 级常量，**事实表不加时间过滤**，保证同一 (切片, 任务) 的**卡数**与窗口无关——这才是关键。
- **恒等式**：总卡数 = 使用卡数 + 等待卡数 对每个切片严格成立，且与查询窗口无关——同一集合的互斥切分结果只依赖该切片自身数据。

反例（修改前的实现）：申请卡数由窗口内运行行的 `assign_npu_second / job_current_slot_running_seconds` 推导，短窗口下尚未跑起来的排队任务会取不到值而被遗漏 → 同一 00:00 切片：72h 窗口 3346、20min 窗口 247。

修复后 SQL 级验证：72h 与 20min 窗口下 00:00~00:20 五个切片三条曲线逐个相同（等待卡数 3118 / 3242 / 3321 / 3315 / 3395），且 00:00 与「排队任务明细抽屉」的申请卡数汇总量对齐。

## 性能

- 应用侧实测（本地 PID 35136）：`/common/chart` 457~1008ms，与同页其它曲线（471~1008ms）同量级；本页最慢的是 `/npu-usage/heatmap`（3.6~4.1s）。
- **踩坑（重要）**：在 Doris 控制台里，这条 SQL 与 `SELECT 1` 都稳定耗时约 4 秒——该 4 秒是控制台/会话固定开销，**控制台耗时不能作为 SQL 性能判据**，必须以应用侧 `PathFilter` 的 `request uri … cost` 日志为准。
- 事实表 key 前缀为 `(project_id, pipeline_id, pipeline_run_id, job_id, server_ip)`，`job_id` 非首列 → 单列过滤走不了前缀索引，只能全扫；但事实表全表仅约 47.7 万行，应用侧耗时可接受，暂不做 ETL 物化。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `openlibing-ops/.../enumeration/common/chart/ChartCommonEnum.java` | 修改 | 新增 `OPS_NPU_USAGE_CARD_TREND("ops-npu-usage-card-trend")` |
| `openlibing-ops/.../enumeration/common/chart/OpsNpuChartSeries.java` | 修改 | 新增 `TOTAL_CARDS` / `USED_CARDS` / `PENDING_CARDS` |
| `openlibing-ops/.../api/request/common/chart/ChartReq.java` | 修改 | `@JsonSubTypes` 登记 `ops-npu-usage-card-trend`（漏登记会导致 Jackson 回落基类 → `ClassCastException`） |
| `openlibing-ops/.../domain/mapper/ops/NpuUsageMapper.java` | 修改 | `SlotRow` 新增 `totalCards` / `usedCards` / `pendingCards` 字段；新增 `queryTrendCardSeries`（一条 SQL 一次事实表 join + 条件聚合同时算出三列） |
| `openlibing-ops/.../resources/mapper/NpuUsageMapper.xml` | 修改 | `slotMap` 增 `total_cards` / `used_cards` / `pending_cards` 映射；新增片段 `trendActiveJobs`（活跃任务集合 = `pending_seconds > 0 OR running_seconds > 0`，按互斥规则归运行 / 等待）/ `applyCardsFact`；新增 select 一次性算出三列 |
| `openlibing-ops/.../app/service/ops/OpsNpuUsageCardTrendChartService.java` | 新增 | ChartService 处理器，委托 `NpuUsageService.queryCardTrend` |
| `openlibing-ops/.../app/service/ops/NpuUsageService.java` | 修改 | 新增 `queryCardTrend(req)`：委托 `queryTrendCardSeries` 一次算出总卡数（全部活跃任务申请卡数之和）、使用卡数（归为运行任务申请卡数之和）、等待卡数（归为等待任务申请卡数之和） |
| `openlibing-ops/.../test/.../NpuUsageServiceTest.java` | 修改 | 新增 `queryCardTrend` 用例（含使用卡数不封顶断言） |
| `openlibing-ops/.../test/.../ChartReqJsonTest.java` | 新增 | 锁定 category → 子类的 Jackson 多态映射 |
| `openlibing-ops-web/src/views/.../usage-analysis/components/usage-card-trend-chart.vue` | 新增 | 卡数趋势组件（含点击下钻） |
| `openlibing-ops-web/src/views/.../usage-analysis/utils.ts` | 修改 | 新增 `buildUsageCardTrendOption` |
| `openlibing-ops-web/src/views/.../usage-analysis/constants.ts` | 修改 | 新增三条曲线配色 |
| `openlibing-ops-web/src/views/.../usage-analysis/usage-analysis-view.vue` | 修改 | 插入 `UsageCardTrendChart` |

## 风险 & 缓解

- 新增 category 必须在 `ChartReq.@JsonSubTypes` 同步登记，否则 Jackson 回落 `defaultImpl = ChartReq`，强转子类抛 `ClassCastException`（表现为接口报「系统错误」）；已补 `ChartReqJsonTest` 锁住映射，防回归。
- 等待卡数、使用卡数、总卡数均为派生口径（5m 表无 `npu_second`/`job_duration` 字段），已固化公式并在 API 文档中说明。三条曲线改为申请卡数口径后，`使用率 ↔ 使用卡数 ↔ 总卡数` 的旧自洽关系（31.12% ↔ 409.55 ↔ 1316）不再成立，需按「三条卡数曲线与使用率不同源」的说明向使用方解释（总卡数现在也是申请卡数口径，不能写成「使用率 = 使用卡数 / 总卡数」）；下期若确认把使用率也统一到申请卡数口径，再一并回归。
- **互斥归类是按切片内 running / pending 秒数孰大判定的近似**：同一任务跨切片看，可能在相邻切片分属两条曲线（该切片归运行、下一切片归等待），这是**预期行为**；但在同一 (切片, 任务) 内只归一类，因此恒有 `总卡数 = 使用卡数 + 等待卡数`，切片边界上的重复计数问题已解决。
- 事实表需全表扫描（`job_id` 非 key 首列，走不了前缀索引），三条曲线三列由**同一次事实表 join + 条件聚合**算出（集合取 `pending_seconds > 0 OR running_seconds > 0`），只扫一次事实表，本地应用侧实测单条约 457~1008ms，量级可接受；若后续数据量明显增长，可在 ETL 侧物化 `platform + job_id → 申请卡数` 映射表。
- 复用现有表与 SQL 框架，无新增表、无 schema 变更，风险低。

## 跨仓影响

- 后端新增 category 为**纯增量**，对既有 `ops-npu-usage-trend` 消费方零影响。
- 前端仅新增组件，不改动既有组件行为。
