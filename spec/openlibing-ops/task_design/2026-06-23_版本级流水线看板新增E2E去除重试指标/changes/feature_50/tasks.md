# 版本级流水线看板新增E2E执行平均时长(去除重试)指标 — 实现任务

## 进度: 8/8 complete

### 后端 — openlibing-ops

- [x] **T1: 数据库DDL**
  - 文件: DDL.sql
  - 操作: 两个表新增`efficiency_duration_ms`字段
  - 状态: DBA执行（脚本已就绪）

- [x] **T2: NightlyPipelineDashboardMapper.xml 修改**
  - pipeline_stats CTE 新增 efficiency_duration 聚合（AVG/MAX/PERCENTILE）
  - finalSelect 新增分钟转换
  - resultMap 新增映射

- [x] **T3: NightlyPipelineDashboard.java Model 新增字段**
  - 新增 efficiencyDurationAvgMinutes/MaxMinutes/P50Minutes/P90Minutes/P95Minutes

- [x] **T4: NightlyPipelineDashboardResp.java 新增字段+构造赋值**
  - 新增5个字段及构造方法赋值

- [x] **T5: Chart接口 Mapper/Model 修改**
  - DmRdEfcBuildDimNightlyPipelineDayMapper.xml: resultMap + SQL查询
  - DmRdEfcBuildDimNightlyPipelineDay.java: 新增efficiencyDurationMinutes

- [x] **T6: Chart接口 Resp/Handler 修改**
  - VersionPipelineChartResp.java: 新增avgEfficiencyDuration
  - PipelineHandleImpl.java: buildDayCharts赋值

### 前端 — openlibing-ops-web

- [x] **T7: 表格列定义修改**
  - version-pipeline-columns.ts: 新增E2E执行(去除重试)分组

- [x] **T8: Chart组件+提示文案修改**
  - version-pipeline-chart.vue: metricList替换
  - metric-tips.ts: 新增提示文案

### 验证方式
- [ ] 表格接口返回数据中包含`efficiencyDurationAvgMinutes`等字段
- [ ] Chart接口返回数据中包含`avgEfficiencyDuration`字段
- [ ] 前端表格正确展示新分组和列
- [ ] Chart正确渲染去除重试的平均时长
- [ ] 字段为NULL时页面显示"-"或空值（不崩溃）
