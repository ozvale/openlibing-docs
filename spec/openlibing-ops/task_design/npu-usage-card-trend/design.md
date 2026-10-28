# 卡数趋势 — 技术设计

## 方案概述

后端在通用图表框架 `/common/chart` 下**新增** category `ops-npu-usage-card-trend`（与 `ops-npu-usage-trend` 同参、同 5 分钟切片口径），返回三条 series；前端新增一个图表组件（结构照搬 `usage-trend-chart.vue`），插入到「趋势分析」与「热力图」之间，下钻复用既有 `open-slot` 事件链路。

无新增技术决策，沿用现有 NPU 使用率分析的分层（CommonChartHandler → ChartService → NpuUsageService → NpuUsageMapper）。

## 数据口径

| 曲线 | 口径 | 取数来源 |
|------|------|---------|
| 总卡数（张） | 所选资源池的**机器物理卡数**：静态维表 `sdi_rd_efc_server_machine_hidevlab` 按 `server_ip` 机器级去重后 `SUM(actual_npu_num)`（一卡多代已折算），**窗口内恒定**（图上为水平线），与「使用率」分母同源；**与使用卡数 / 等待卡数不是同一口径**，不存在 总卡数 = 使用卡数 + 等待卡数 | `queryTrendTotalCards`（机器维表小表聚合，一次） |
| 使用卡数（张） | 该切片**有运行秒数**的任务（`job_current_slot_running_seconds > 0`）按各自「申请卡数」求和；申请卡数与等待卡数同源同算法（三张平台任务事实表 `npu_second / job_duration`，job 级 MAX 去重、四舍五入、下限 1；codearts 历史整点记账 `npu_second % 3600 == 0 → npu_second / 3600`）；**不按机器容量封顶**，故可大于总卡数 | 同上（`queryTrendCardSeries` 条件聚合列之一） |
| 等待卡数（张） | 该切片**有等待秒数**的任务（`job_current_slot_pending_seconds > 0`）按各自「申请卡数」求和；申请卡数取三张平台任务事实表（`dwr_rd_efc_build_job_fact` / `..._workflow_run_job_gitcode_fact` / `..._workflow_run_job_github_fact`）的 `npu_second / job_duration`，job 级 MAX 去重、四舍五入、下限 1；codearts 历史整点记账数据（`npu_second` 为 3600 整数倍）直接 `÷ 3600` | 同上（`queryTrendCardSeries` 条件聚合列之一） |

- 缺失切片补 0（与其他 5m 类接口一致）。
- codearts 历史整点记账换算已与明细列「申请卡数」统一（同为 `npu_second % 3600 == 0 → npu_second / 3600`），不再存在历史 codearts 任务两处口径不一致的问题。
- **使用卡数 / 等待卡数与「使用率」脱钩（已知且本期接受）**：使用卡数 / 等待卡数均为「申请卡数」口径，而使用率（趋势分析曲线 / 热力图 / KPI）为分配卡时口径 `Σ assign_npu_hours / (Σ total_npu_num / 12)`，因此 `使用卡数 ÷ 总卡数 ≠ 使用率`（总卡数虽与使用率分母同源，但使用卡数不是分配卡时）。两者在「任务跑满整片」时数学等价（`assign_npu_second` 本身由同一 `npu_second` 按占比分摊而来，`assign × 12 = npu_second / job_duration = 申请卡数`），偏差只来自部分切片启停按整卡计入、四舍五入下限 1、事实表缺数据任务被漏计、以及边界切片两线重复计数。是否把使用率也统一到申请卡数口径，留待下期评估。

## 窗口无关不变量（强制）

同一切片的取值不得随查询窗口变化。实现约束：

- **集合**来自切片：活跃任务集合由 5m 表按 `slot_time BETWEEN …` 取 `job_current_slot_pending_seconds > 0 OR job_current_slot_running_seconds > 0` 去重得到；**归属规则只看该切片自身**——有运行秒数（`> 0`）计入使用卡数、有等待秒数（`> 0`）计入等待卡数，两者不互斥（同一任务在该切片既等又跑时两条曲线各计一次）。窗口变化 → 覆盖的切片范围变化，这是正常的。
- **属性**按 job 主键取、不做时间过滤：申请卡数一律从平台任务事实表按 `platform + job_id` 取 job 级常量，**事实表不加时间过滤**，保证同一 (切片, 任务) 的**卡数**与窗口无关——这才是关键。
- **窗口无关性逐曲线成立**（**不存在** 总卡数 = 使用卡数 + 等待卡数 这一恒等式：总卡数是机器物理卡数口径，使用 / 等待是任务申请卡数口径，三者不可加）：总卡数取维表常量，只随项目 / 资源池筛选变化；使用卡数 / 等待卡数按切片条件聚合，取值只依赖该切片自身数据。

反例（修改前的实现）：申请卡数由窗口内运行行的 `assign_npu_second / job_current_slot_running_seconds` 推导，短窗口下尚未跑起来的排队任务会取不到值而被遗漏 → 同一 00:00 切片：72h 窗口 3346、20min 窗口 247。

窗口无关性验证（上一版互斥口径实测）：72h 与 20min 窗口下 00:00~00:20 五个切片逐曲线取值相同（如等待卡数 3118 / 3242 / 3321 / 3315 / 3395），且 00:00 与「排队任务明细抽屉」的申请卡数汇总量对齐。去掉互斥归类后该性质不变（归属只依赖切片自身数据），数值略有上浮，待重启后刷新实测值。

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
| `openlibing-ops/.../domain/mapper/ops/NpuUsageMapper.java` | 修改 | `SlotRow` 新增 `usedCards` / `pendingCards` 字段（`totalCards` 已在 `4e52b6de` 移除）；新增 `queryTrendCardSeries`（一条 SQL 一次事实表 join + 条件聚合同时算出两列） |
| `openlibing-ops/.../resources/mapper/NpuUsageMapper.xml` | 修改 | `slotMap` 增 `used_cards` / `pending_cards` 映射（`total_cards` 映射已在 `4e52b6de` 移除）；新增片段 `trendActiveJobs`（活跃任务集合 = `pending_seconds > 0 OR running_seconds > 0`，归属按该切片是否有运行 / 等待秒数判定，不互斥）/ `applyCardsFact`；新增 select 一次性算出两列 |
| `openlibing-ops/.../app/service/ops/OpsNpuUsageCardTrendChartService.java` | 新增 | ChartService 处理器，委托 `NpuUsageService.queryCardTrend` |
| `openlibing-ops/.../app/service/ops/NpuUsageService.java` | 修改 | 新增 `queryCardTrend(req)`：总卡数委托 `queryTrendTotalCards`（机器维表物理卡数，窗口内恒定），使用卡数 / 等待卡数委托 `queryTrendCardSeries` 一次算出 |
| `openlibing-ops/.../test/.../NpuUsageServiceTest.java` | 修改 | 新增 `queryCardTrend` 用例：stub `queryTrendTotalCards` 返回机器物理卡数（1316），断言总卡数窗口内**每条切片取值相同**、使用卡数不按容量封顶、缺失切片补 0；`testCardTrendWithEmptyData` 不 stub 总卡数（返回 null → 0），覆盖空数据不抛异常 |
| `openlibing-ops/.../test/.../ChartReqJsonTest.java` | 新增 | 锁定 category → 子类的 Jackson 多态映射 |
| `openlibing-ops-web/src/views/.../usage-analysis/components/usage-card-trend-chart.vue` | 新增 | 卡数趋势组件（含点击下钻） |
| `openlibing-ops-web/src/views/.../usage-analysis/utils.ts` | 修改 | 新增 `buildUsageCardTrendOption` |
| `openlibing-ops-web/src/views/.../usage-analysis/constants.ts` | 修改 | 新增三条曲线配色 |
| `openlibing-ops-web/src/views/.../usage-analysis/usage-analysis-view.vue` | 修改 | 插入 `UsageCardTrendChart` |

## 风险 & 缓解

- 新增 category 必须在 `ChartReq.@JsonSubTypes` 同步登记，否则 Jackson 回落 `defaultImpl = ChartReq`，强转子类抛 `ClassCastException`（表现为接口报「系统错误」）；已补 `ChartReqJsonTest` 锁住映射，防回归。
- 等待卡数、使用卡数、总卡数均为**派生 / 外部口径**（5m 表既无 `npu_second` / `job_duration`，也无机器容量），已固化公式并在 API 文档中说明。**三条曲线与「使用率」不同源、彼此也不同口径**：`使用率 ↔ 使用卡数 ↔ 总卡数` 的旧自洽关系（31.12% ↔ 409.55 ↔ 1316）不再成立（总卡数已改为机器物理卡数口径，使用 / 等待为申请卡数口径），不能写成「使用率 = 使用卡数 / 总卡数」，也**不存在** `总卡数 = 使用卡数 + 等待卡数`；下期若确认把使用率也统一到申请卡数口径，再一并回归。
- **边界切片重复计数（已知且本期接受）**：归属规则只看该切片自身——有运行秒数计入使用卡数、有等待秒数计入等待卡数，两者**不互斥**。同一任务在同一 5 分钟切片内可能既有等待秒数又有运行秒数（实测 2026-09-02 00:05 切片 119 个运行任务 / 434 个排队任务中有 **15 个重叠**，如 `PreSmoke_msprof` 排队 0.92min、运行 3.55min），此时会在两条曲线各计一次，因此 `使用卡数 + 等待卡数` **不是**该切片活跃任务的申请卡数总和。这是刻意的取舍：用「三列可加」换取「看得清排队与运行的真实需求」，因为总卡数已是容量口径（不同量纲），互斥归类带来的可比性收益不再存在。
- 事实表需全表扫描（`job_id` 非 key 首列，走不了前缀索引），使用卡数 / 等待卡数两列由**同一次事实表 join + 条件聚合**算出（集合取 `pending_seconds > 0 OR running_seconds > 0`），只扫一次事实表；总卡数改走机器维表小表聚合（一次，窗口内恒定），不再参与事实表 join；本地应用侧实测单条约 457~1008ms，量级可接受；若后续数据量明显增长，可在 ETL 侧物化 `platform + job_id → 申请卡数` 映射表。
- 复用现有表与 SQL 框架，无新增表、无 schema 变更，风险低。

## 跨仓影响

- 后端新增 category 为**纯增量**，对既有 `ops-npu-usage-trend` 消费方零影响。
- 前端仅新增组件，不改动既有组件行为。
