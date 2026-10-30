# 卡数趋势 — 技术设计

## 方案概述

后端在通用图表框架 `/common/chart` 下**新增** category `ops-npu-usage-card-trend`（与 `ops-npu-usage-trend` 同参、同 5 分钟切片口径），返回三条 series；前端新增一个图表组件（结构照搬 `usage-trend-chart.vue`），插入到「趋势分析」与「热力图」之间，下钻复用既有 `open-slot` 事件链路。

无新增技术决策，沿用现有 NPU 使用率分析的分层（CommonChartHandler → ChartService → NpuUsageService → NpuUsageMapper）。

## 数据口径

| 曲线 | 口径 | 取数来源 |
|------|------|---------|
| 总卡数（张） | 所选资源池的**机器物理卡数**：静态维表 `sdi_rd_efc_server_machine_hidevlab` 按 `server_ip` 机器级去重后 `SUM(actual_npu_num)`（一卡多代已折算），**窗口内恒定**（图上为水平线），与「使用率」分母同源；**与使用卡数 / 等待卡数不是同一口径**，不存在 总卡数 = 使用卡数 + 等待卡数 | `queryTrendTotalCards`（机器维表小表聚合，一次） |
| 使用卡数（张） | 该切片**有运行秒数**的任务（`job_current_slot_running_seconds > 0`）按各自「申请卡数」求和；申请卡数与等待卡数同源同算法，直接取 5m 明细表 `dwr_rd_efc_resource_npu_detail_5m.total_npu`：先按 `(platform, job_id, server_ip)` 取 `MAX(total_npu)` 消掉切片维度，再按 `(platform, job_id)` 求和得到 job 总申请卡数；**不按机器容量封顶**，故可大于总卡数 | 同上（`queryTrendCardSeries` 条件聚合列之一，卡数子查询片段 `jobTotalNpu`） |
| 等待卡数（张） | 该切片**有等待秒数**的任务（`job_current_slot_pending_seconds > 0`）按各自「申请卡数」求和；申请卡数取数与使用卡数完全一致（同 5m 明细表 `total_npu` 的 job 级两层聚合） | 同上（`queryTrendCardSeries` 条件聚合列之一，卡数子查询片段 `jobTotalNpu`） |

- 缺失切片补 0（与其他 5m 类接口一致）。
- 申请卡数已统一为 5m 明细表 `total_npu` 单一来源（明细列「申请卡数」与趋势两条曲线同源同算法），原先 codearts 历史整点记账换算与 `npu_second / job_duration` 推算口径已全部下线。
- **使用卡数 / 等待卡数与「使用率」脱钩（已知且本期接受）**：使用卡数 / 等待卡数均为「申请卡数」口径，而使用率（趋势分析曲线 / 热力图 / KPI）为分配卡时口径 `Σ assign_npu_hours / (Σ total_npu_num / 12)`，因此 `使用卡数 ÷ 总卡数 ≠ 使用率`（总卡数虽与使用率分母同源，但使用卡数不是分配卡时）。两者不存在数学等价关系：申请卡数是任务申请的**整卡数**（5m 表 `total_npu`，上游由各平台任务申请量清洗而来，取整后按 job 汇总），分配卡时是机器上按秒累计的**占用**（`assign_npu_second`），量纲与来源都不同。偏差来源：部分切片启停按整卡计入、job 卡数按整卡汇总、明细表缺该任务行时曲线计 0、以及边界切片两线重复计数。是否把使用率也统一到申请卡数口径，留待下期评估。

## 窗口无关不变量（强制）

同一切片的取值不得随查询窗口变化。实现约束：

- **集合**来自切片：活跃任务集合由 5m 表按 `slot_time BETWEEN …` 取 `job_current_slot_pending_seconds > 0 OR job_current_slot_running_seconds > 0` 去重得到；**归属规则只看该切片自身**——有运行秒数（`> 0`）计入使用卡数、有等待秒数（`> 0`）计入等待卡数，两者不互斥（同一任务在该切片既等又跑时两条曲线各计一次）。窗口变化 → 覆盖的切片范围变化，这是正常的。
- **属性**按 job 主键取、不做时间过滤：申请卡数一律从 5m 明细表按 `platform + job_id` 取 job 级常量（先 `(platform, job_id, server_ip)` 取 MAX 消切片，再按 job 求和），**明细表不加时间过滤**，保证同一 (切片, 任务) 的**卡数**与窗口无关——这才是关键。
- **窗口无关性逐曲线成立**（**不存在** 总卡数 = 使用卡数 + 等待卡数 这一恒等式：总卡数是机器物理卡数口径，使用 / 等待是任务申请卡数口径，三者不可加）：总卡数取维表常量，只随项目 / 资源池筛选变化；使用卡数 / 等待卡数按切片条件聚合，取值只依赖该切片自身数据。

反例（修改前的实现）：申请卡数由窗口内运行行的 `assign_npu_second / job_current_slot_running_seconds` 推导，短窗口下尚未跑起来的排队任务会取不到值而被遗漏 → 同一 00:00 切片：72h 窗口 3346、20min 窗口 247。

实测（2026-09-15 全天，`ops-npu-usage-card-trend`）：288 个切片点齐满，总卡数恒为 1316（水平线）、使用卡数峰值 128（Σ=6715）、等待卡数峰值 65（Σ=2193），使用卡数未超总卡数，无 job 级重复放大；接口耗时 690ms。使用卡数 / 等待卡数与明细两个 category 的 `applyNpuNum` 同源，同一 (切片, 任务) 两处取值一致（明细需带 `slotTime` 方可逐点对齐；不带 `slotTime` 时明细是窗口内 job 级去重，跨切片合并，不能与单切片值直接比）。

## 性能

- 应用侧实测（本地 PID 35136）：`/common/chart` 457~1008ms，与同页其它曲线（471~1008ms）同量级；本页最慢的是 `/npu-usage/heatmap`（3.6~4.1s）。
- 申请卡数改取 5m 明细表 `total_npu` 后（后端 commit `06ac35d6`）：卡数趋势 `/common/chart` 实测 690ms，与改动前同量级；卡数子查询由「三张事实表 UNION ALL 全扫」换成「5m 明细表按 `platform + job_id` 两层聚合」，未出现性能回退。
- **踩坑（重要）**：在 Doris 控制台里，这条 SQL 与 `SELECT 1` 都稳定耗时约 4 秒——该 4 秒是控制台/会话固定开销，**控制台耗时不能作为 SQL 性能判据**，必须以应用侧 `PathFilter` 的 `request uri … cost` 日志为准。
- （改前实现）事实表 key 前缀为 `(project_id, pipeline_id, pipeline_run_id, job_id, server_ip)`，`job_id` 非首列 → 单列过滤走不了前缀索引，只能全扫；但事实表全表仅约 47.7 万行，应用侧耗时可接受，暂不做 ETL 物化。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `openlibing-ops/.../enumeration/common/chart/ChartCommonEnum.java` | 修改 | 新增 `OPS_NPU_USAGE_CARD_TREND("ops-npu-usage-card-trend")` |
| `openlibing-ops/.../enumeration/common/chart/OpsNpuChartSeries.java` | 修改 | 新增 `TOTAL_CARDS` / `USED_CARDS` / `PENDING_CARDS` |
| `openlibing-ops/.../api/request/common/chart/ChartReq.java` | 修改 | `@JsonSubTypes` 登记 `ops-npu-usage-card-trend`（漏登记会导致 Jackson 回落基类 → `ClassCastException`） |
| `openlibing-ops/.../domain/mapper/ops/NpuUsageMapper.java` | 修改 | `SlotRow` 新增 `usedCards` / `pendingCards` 字段（`totalCards` 已在 `4e52b6de` 移除）；新增 `queryTrendCardSeries`（一条 SQL 一次事实表 join + 条件聚合同时算出两列） |
| `openlibing-ops/.../resources/mapper/NpuUsageMapper.xml` | 修改 | `slotMap` 增 `used_cards` / `pending_cards` 映射（`total_cards` 映射已在 `4e52b6de` 移除）；新增片段 `trendActiveJobs`（活跃任务集合 = `pending_seconds > 0 OR running_seconds > 0`，归属按该切片是否有运行 / 等待秒数判定，不互斥）/ `jobTotalNpu`（申请卡数取 5m 明细表 `total_npu`：先 `(platform, job_id, server_ip)` 取 MAX 消切片，再按 `(platform, job_id)` 求和；`06ac35d6` 起替代原 `applyCardsFact` 的三张事实表 `npu_second / job_duration` 换算）；新增 select 一次性算出两列 |
| `openlibing-ops/.../app/service/ops/OpsNpuUsageCardTrendChartService.java` | 新增 | ChartService 处理器，委托 `NpuUsageService.queryCardTrend` |
| `openlibing-ops/.../app/service/ops/NpuUsageService.java` | 修改 | 新增 `queryCardTrend(req)`：总卡数委托 `queryTrendTotalCards`（机器维表物理卡数，窗口内恒定），使用卡数 / 等待卡数委托 `queryTrendCardSeries` 一次算出 |
| `openlibing-ops/.../test/.../NpuUsageServiceTest.java` | 修改 | 新增 `queryCardTrend` 用例：stub `queryTrendTotalCards` 返回机器物理卡数（1316），断言总卡数窗口内**每条切片取值相同**、使用卡数不按容量封顶、缺失切片补 0；`testCardTrendWithEmptyData` 不 stub 总卡数（返回 null → 0），覆盖空数据不抛异常 |
| `openlibing-ops/.../test/.../ChartReqJsonTest.java` | 新增 | 锁定 category → 子类的 Jackson 多态映射 |
| `openlibing-ops-web/src/views/.../usage-analysis/components/usage-card-trend-chart.vue` | 新增 | 卡数趋势组件（含点击下钻） |
| `openlibing-ops-web/src/views/.../usage-analysis/utils.ts` | 修改 | 新增 `buildUsageCardTrendOption` |
| `openlibing-ops-web/src/views/.../usage-analysis/constants.ts` | 修改 | 新增三条曲线配色 |
| `openlibing-ops-web/src/views/.../usage-analysis/usage-analysis-view.vue` | 修改 | 插入 `UsageCardTrendChart` |
| `openlibing-ops/.../api/response/common/detail/OpsNpuSlotTaskResp.java` | 修改 | `applyNpuNum` 注释改述为「取 5m 明细表 `total_npu`，同一任务各机器分配卡数求和后取整」（`06ac35d6`） |
| `openlibing-ops/.../domain/mapper/ops/NpuUsageMapper.java` | 修改 | `SlotTaskNpuRow` 字段由 `npuSecond` / `jobDuration` 改为 `jobId` / `totalNpu(Double)`；`querySlotTaskNpu` 改为 5m 明细表按 `(platform, job_id)` 两层聚合（`06ac35d6`） |
| `openlibing-ops/.../app/service/ops/NpuUsageService.java` | 修改 | `queryApplyNpuNums` 直读 `totalNpu` 四舍五入取整；删除 `calcApplyNpuNum`（codearts 整点特例 + 下限 1）与常量 `SECONDS_PER_HOUR`（`06ac35d6`） |
| `openlibing-ops/.../test/.../NpuUsageServiceTest.java` | 修改 | 明细申请卡数用例改按 `totalNpu`；「运行时长非正不填卡数」用例改为「`total_npu` 为空不填卡数」 |

## 风险 & 缓解

- 新增 category 必须在 `ChartReq.@JsonSubTypes` 同步登记，否则 Jackson 回落 `defaultImpl = ChartReq`，强转子类抛 `ClassCastException`（表现为接口报「系统错误」）；已补 `ChartReqJsonTest` 锁住映射，防回归。
- 等待卡数、使用卡数、总卡数均为**外部口径**（任务申请卡数取自 5m 明细表 `total_npu`，机器容量取自静态维表 `actual_npu_num`），已固化公式并在 API 文档中说明。**三条曲线与「使用率」不同源、彼此也不同口径**：`使用率 ↔ 使用卡数 ↔ 总卡数` 的旧自洽关系（31.12% ↔ 409.55 ↔ 1316）不再成立（总卡数已改为机器物理卡数口径，使用 / 等待为申请卡数口径），不能写成「使用率 = 使用卡数 / 总卡数」，也**不存在** `总卡数 = 使用卡数 + 等待卡数`；下期若确认把使用率也统一到申请卡数口径，再一并回归。
- **边界切片重复计数（已知且本期接受）**：归属规则只看该切片自身——有运行秒数计入使用卡数、有等待秒数计入等待卡数，两者**不互斥**。同一任务在同一 5 分钟切片内可能既有等待秒数又有运行秒数（实测 2026-09-02 00:05 切片 119 个运行任务 / 434 个排队任务中有 **15 个重叠**，如 `PreSmoke_msprof` 排队 0.92min、运行 3.55min），此时会在两条曲线各计一次，因此 `使用卡数 + 等待卡数` **不是**该切片活跃任务的申请卡数总和。这是刻意的取舍：用「三列可加」换取「看得清排队与运行的真实需求」，因为总卡数已是容量口径（不同量纲），互斥归类带来的可比性收益不再存在。
- 申请卡数子查询 `jobTotalNpu` 对 5m 明细表做**两层聚合**（内层按 `(platform, job_id, server_ip)` 取 MAX、外层按 `(platform, job_id)` 求和）且**不加时间过滤**（保证窗口无关），使用卡数 / 等待卡数两列由**同一次 join + 条件聚合**算出（集合取 `pending_seconds > 0 OR running_seconds > 0`）；总卡数走机器维表小表聚合（一次，窗口内恒定）；本地应用侧实测 690ms，量级可接受。若后续 5m 表数据量明显增长导致该子查询变慢，可在 ETL 侧物化 `platform + job_id → 申请卡数` 映射表，或退化为「先取窗口活跃 job、再按 job 查卡数」的两步查询。
- 复用现有表与 SQL 框架，无新增表、无 schema 变更，风险低。

## 跨仓影响

- 后端新增 category 为**纯增量**，对既有 `ops-npu-usage-trend` 消费方零影响。
- 前端仅新增组件，不改动既有组件行为。
