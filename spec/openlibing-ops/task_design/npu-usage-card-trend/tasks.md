# 卡数趋势 — 实现任务

## 进度: 10/10 complete

- [x] Task 1: 后端枚举扩展（`ChartCommonEnum` 新增 category；`OpsNpuChartSeries` 新增三个系列名）
- [x] Task 2: 后端 `ChartReq.@JsonSubTypes` 登记 category（漏登记会让 Jackson 回落基类，接口报「系统错误」）
- [x] Task 3: 后端 Mapper 扩展（`SlotRow.pendingCards` + `queryTrendPendingCards` 接口 + XML 片段 `trendQueuedJobs` 与 select）
- [x] Task 4: 后端 `NpuUsageService.queryCardTrend` 三序列组装（对齐切片、补 0、使用卡数 cap）
- [x] Task 5: 后端新增 `OpsNpuUsageCardTrendChartService` 处理器
- [x] Task 6: 后端单测 + 编译验证（`NpuUsageServiceTest` 25 用例全过；新增 `ChartReqJsonTest` 锁定多态映射）
- [x] Task 7: 前端 `usage-card-trend-chart.vue` + `buildUsageCardTrendOption` + 配色 + 视图插入
- [x] Task 8: 前端 `npm run type-check`（本次改动文件无报错，报错均为存量无关文件）
- [x] Task 9: 等待卡数改取平台任务事实表口径，消除窗口依赖（SQL 级验证 72h/20min 五切片逐个相同；应用侧接口 457~1008ms；本地页面自测数据自洽核对通过）
- [x] Task 10: 申请卡数统一改取 5m 明细表 `total_npu`（`06ac35d6`）：明细 `applyNpuNum` 与趋势使用 / 等待卡数同源同算法（`(platform, job_id, server_ip)` 取 MAX 消切片 → 按 job SUM），`applyCardsFact` / `calcApplyNpuNum` / codearts 整点特例 / 下限 1 全部下线；验证：单测 25 用例全过，卡数趋势 09-15 全天 288 切片（总卡数 1316 水平线、使用卡数峰值 128、等待卡数峰值 65），接口 690ms

## 提交记录

- `672c960c feat(npu): 使用率分析新增卡数趋势曲线`（openlibing-ops，9 文件）
- `b1b48add fix(npu): 卡数趋势等待卡数改取事实表口径，消除窗口依赖`（openlibing-ops，1 文件）
- `f499cc46 fix(npu): 卡数趋势使用卡数改取运行任务真实申请卡数`（openlibing-ops）
- `0e23ebaf fix(npu): 卡数趋势三条曲线统一为同一份任务数据源`（openlibing-ops）
- `4e52b6de fix(npu): 卡数趋势总卡数改回机器物理卡数口径`（openlibing-ops）
- `06ac35d6 refactor(npu-usage): 申请卡数改用 5m 明细表 total_npu 取数`（openlibing-ops，5 文件）

