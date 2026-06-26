# 版本级流水线看板新增E2E执行平均时长(去除重试)指标 — 实现任务

## 进度: 0/15 complete

### #50 版本级流水线看板子页面

- [ ] T1: Doris DDL 执行 — 两个数据源表新增 `efficiency_duration_ms` 字段
- [ ] T2: DS ETL 工作流修改 — DWR 表 INSERT 新增 LEFT JOIN + 字段（workflow 169496639078592）
- [ ] T3: DS ETL 工作流修改 — DM 表 SELECT 新增 AVG 聚合（workflow 169496639269056）
- [ ] T4: 后端 Mapper XML — `NightlyPipelineDashboardMapper.xml` CTE + finalSelect + resultMap
- [ ] T5: 后端 Model — `NightlyPipelineDashboard.java` 新增 5 个字段
- [ ] T6: 后端 Response DTO — `NightlyPipelineDashboardResp.java` 新增字段 + 构造赋值
- [ ] T7: 后端 Mapper XML — `DmRdEfcBuildDimNightlyPipelineDayMapper.xml` resultMap + SQL
- [ ] T8: 后端 Model — `DmRdEfcBuildDimNightlyPipelineDay.java` 新增字段
- [ ] T9: 后端 Response DTO — `VersionPipelineChartResp.java` 新增字段
- [ ] T10: 后端 Handler — `PipelineHandleImpl.java` buildDayCharts() 赋值
- [ ] T11: 前端表格列定义 — `version-pipeline-columns.ts` 新增分组
- [ ] T12: 前端 Chart 组件 — `version-pipeline-chart.vue` 替换 key
- [ ] T13: 前端提示文案 — `metric-tips.ts` 新增

### #59 开源项目运营总览主表

- [ ] T14: Doris DDL + DS ETL — `dwi_project_statistics` 新增字段 + 工作流新增 CTE（workflow 172676072332288）
- [ ] T15: 后端 Mapper/Model/Response + 前端列定义 — 全线新增 `versionEfficiencyDuration`
