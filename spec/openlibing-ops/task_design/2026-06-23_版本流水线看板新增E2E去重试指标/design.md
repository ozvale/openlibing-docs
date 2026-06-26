# 版本级流水线看板新增E2E执行平均时长(去除重试)指标 — 技术设计

## 方案概述

复用 PR 门禁流水线效率计算任务已有的 `efficiency_duration_sec` 字段，通过 ETL 链路写入 DWR → DM → DWI 三层，后端两个子页面共 3 个接口返回新字段，前端对应展示。

## 架构决策

| 决策 | 选项 | 选择原因 |
|------|------|---------|
| 数据源复用 | 复用 `dwr_rd_efc_pipeline_run_efficiency` | 已有 PR 模块计算好的去除重试时长，避免重复计算 |
| 字段命名 | 统一使用 `efficiency` 前缀 | 与 PR 模块命名一致，语义清晰 |
| 单位体系 | 毫秒（存储）→ 分钟（展示） | DWR/DM 层存毫秒与含重试字段一致；前端统一转分钟 |
| 向后兼容 | 新增字段允许 NULL | 已有数据不受影响，上下游无需联动修改 |
| Chart 替换策略 | 后端同时返回新旧字段，前端替换 key | 不破坏 API 兼容性，前端可控切换 |

## 数据流

```
PR门禁流水线效率计算任务（已有）
    │
    ├── dwr_rd_efc_pipeline_run_efficiency.efficiency_duration_sec (秒) ← 已有
    │     ↓ LEFT JOIN
    │
    ├── dwr_rd_efc_build_fact_nightly_test_case_pipeline_run.efficiency_duration_ms (毫秒) ← #50 T1
    │     ↓ AVG
    │
    ├── dm_rd_efc_build_dim_nightly_pipeline_day.efficiency_duration_ms (毫秒) ← #50 T1
    │     ├── ↓ (Chart) ROUND(/60000) → VersionPipelineChartResp.avgEfficiencyDuration
    │     ├── ↓ (Table) AVG/MAX/PERCENTILE → NightlyPipelineDashboardResp.efficiencyDurationAvgMinutes 等
    │     └── ↓ (ETL) AVG(/1000) → dwi_project_statistics.version_efficiency_duration (秒) ← #59 T2
    │               ↓
    │           ProjectDetailResp.versionEfficiencyDuration
    │
    └── 前端展示
        ├── version-pipeline-chart.vue: Chart 指标替换
        ├── version-pipeline-columns.ts: 表格新增分组
        └── project-columns.ts: 开源项目总览新增列
```

## 涉及文件

### #50 版本级流水线看板

| 文件 | 操作 | 说明 |
|------|------|------|
| Doris DDL: dwr_rd_efc_build_fact_nightly_test_case_pipeline_run | 新增字段 | ADD COLUMN efficiency_duration_ms bigint |
| Doris DDL: dm_rd_efc_build_dim_nightly_pipeline_day | 新增字段 | ADD COLUMN efficiency_duration_ms bigint |
| DS workflow 169496639078592 (v14→v15) | 修改 | DWR 表 INSERT 新增 LEFT JOIN + 字段 |
| DS workflow 169496639269056 (v4→v5) | 修改 | DM 表 SELECT 新增 AVG(efficiency_duration_ms) |
| NightlyPipelineDashboardMapper.xml | 修改 | CTE 新增聚合 + finalSelect 分钟转换 + resultMap 映射 |
| NightlyPipelineDashboard.java | 修改 | 新增 5 个 BigDecimal 字段 |
| NightlyPipelineDashboardResp.java | 修改 | 新增 5 个字段 + 构造赋值 |
| DmRdEfcBuildDimNightlyPipelineDayMapper.xml | 修改 | resultMap + SQL 新增 efficiency_duration_minutes |
| DmRdEfcBuildDimNightlyPipelineDay.java | 修改 | 新增 efficiencyDurationMinutes 字段 |
| VersionPipelineChartResp.java | 修改 | 新增 avgEfficiencyDuration 字段 |
| PipelineHandleImpl.java | 修改 | buildDayCharts() 新增赋值 |
| version-pipeline-columns.ts | 修改 | 新增 efficiencyDuration 分组 + 5 个子列 |
| version-pipeline-chart.vue | 修改 | metricList 替换 key |
| metric-tips.ts | 修改 | 新增 efficiencyDurationAvgMinutes 提示文案 |

### #59 开源项目运营总览

| 文件 | 操作 | 说明 |
|------|------|------|
| Doris DDL: dwi_project_statistics | 新增字段 | ADD COLUMN version_efficiency_duration INT |
| DS workflow 172676072332288 (v2→v3) | 修改 | 新增 project_version_efficiency CTE |
| DwiProjectStatisticsMapper.xml | 修改 | resultMap 新增映射 |
| DwiProjectStatistics.java | 修改 | 新增字段 + SORT_FIELD_MAPPING |
| ProjectDetailResp.java | 修改 | 新增字段 + @ExcelProperty + 构造赋值 |
| project-columns.ts | 修改 | 新增列定义 |
| metric-tips.ts | 引用 | 复用已有文案 |

## 风险 & 缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| ETL 源表 `efficiency_duration_sec` 数据不完整 | 低 | 字段为 NULL | LEFT JOIN 未匹配时写入 NULL，API 已做 NULL 处理 |
| Doris ADD COLUMN 锁表 | 低 | 写入阻塞 | UNIQUE KEY 表支持 light schema change，在线执行 |
| 前端新列数据为 NULL 显示异常 | 低 | 展示不友好 | 前端框架默认处理 NULL 值为 "-" |
| 回滚遗漏 | 低 | 数据不一致 | 各层均有明确回滚方案 |

## 跨仓影响

| 仓库 | 影响 |
|------|------|
| openlibing-ops | 后端 API 改造 |
| openlibing-ops-web | 前端展示改造 |
| Doris | 3 个表 DDL |
| DolphinScheduler | 3 个工作流 SQL 修改 |
