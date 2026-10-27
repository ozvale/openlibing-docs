# 卡数趋势 — 实现任务

## 进度: 9/9 complete

- [x] Task 1: 后端枚举扩展（`ChartCommonEnum` 新增 category；`OpsNpuChartSeries` 新增三个系列名）
- [x] Task 2: 后端 `ChartReq.@JsonSubTypes` 登记 category（漏登记会让 Jackson 回落基类，接口报「系统错误」）
- [x] Task 3: 后端 Mapper 扩展（`SlotRow.pendingCards` + `queryTrendPendingCards` 接口 + XML 片段 `trendQueuedJobs` 与 select）
- [x] Task 4: 后端 `NpuUsageService.queryCardTrend` 三序列组装（对齐切片、补 0、使用卡数 cap）
- [x] Task 5: 后端新增 `OpsNpuUsageCardTrendChartService` 处理器
- [x] Task 6: 后端单测 + 编译验证（`NpuUsageServiceTest` 25 用例全过；新增 `ChartReqJsonTest` 锁定多态映射）
- [x] Task 7: 前端 `usage-card-trend-chart.vue` + `buildUsageCardTrendOption` + 配色 + 视图插入
- [x] Task 8: 前端 `npm run type-check`（本次改动文件无报错，报错均为存量无关文件）
- [x] Task 9: 等待卡数改取平台任务事实表口径，消除窗口依赖（SQL 级验证 72h/20min 五切片逐个相同；应用侧接口 457~1008ms；本地页面自测数据自洽核对通过）

## 提交记录

- `672c960c feat(npu): 使用率分析新增卡数趋势曲线`（openlibing-ops，9 文件）
- `b1b48add fix(npu): 卡数趋势等待卡数改取事实表口径，消除窗口依赖`（openlibing-ops，1 文件）

