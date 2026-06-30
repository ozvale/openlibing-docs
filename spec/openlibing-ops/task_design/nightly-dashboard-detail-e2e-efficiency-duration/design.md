# Nightly 流水线看板下钻页面增加 E2E 执行时长（不含重试）列 — 技术设计

## 方案概述

后端 3 层补全 `efficiencyDurationMinutes` 字段链路，前端在列定义数组中追加一列即可。

数据库 `dwr_rd_efc_build_fact_nightly_test_case_pipeline_run.efficiency_duration_ms` 列已在 issue 50 的 DDL 中新增并完成 ETL 填充，无需任何 DB/ETL 变更。

## 架构决策

| 决策 | 原因 |
|------|------|
| 后端只增加 1 个 Avg 字段（`efficiencyDurationMinutes`），不加 P50/P90/P95/Max | 明细页是单次执行记录，不是聚合视图，只有 1 个值；分位统计在主表 `NightlyPipelineDashboardResp` 中已有 |
| 命名与已有 `actualDurationMinutes` 对齐 | 保持 VO 风格一致：`xxxDurationMinutes`，前端 prop 同名 |
| 单位转换在 SQL 中完成（`/60000`） | 与 `actual_duration_ms → actual_duration_minutes` 逻辑一致，不引入新约定 |

## 数据流

```
DWR表 efficiency_duration_ms (bigint, 毫秒)
    ↓ ROUND(efficiency_duration_ms / 60000.0, 2)  -- Mapper XML SELECT
    ↓ resultMap: efficiency_duration_minutes
    ↓ Java Model: efficiencyDurationMinutes (BigDecimal)
    ↓ VO: efficiencyDurationMinutes (BigDecimal)
    ↓ JSON: "efficiencyDurationMinutes": 12.34
    ↓ 前端: row.efficiencyDurationMinutes → 表格列
```

## 涉及文件

### openlibing-ops（后端）

| 文件 | 操作 | 说明 |
|------|------|------|
| `DwrRdEfcBuildFactNightlyTestCasePipelineRun.java:84` | 新增 | 加 `private BigDecimal efficiencyDurationMinutes;` |
| `DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml:39` | 修改 | resultMap 加 `<result column="efficiency_duration_minutes" property="efficiencyDurationMinutes"/>` |
| `DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml:161` | 修改 | `getNightlyPipelineDetail` SELECT 加 `ROUND(efficiency_duration_ms / 60000.0, 2) as efficiency_duration_minutes` |
| `NightlyPipelineDetailResp.java:89` | 修改 | 加 `private BigDecimal efficiencyDurationMinutes;` |
| `NightlyPipelineDetailResp.java:132` | 修改 | 构造函数加 `this.efficiencyDurationMinutes = run.getEfficiencyDurationMinutes();` |

### openlibing-ops-web（前端）

| 文件 | 操作 | 说明 |
|------|------|------|
| `version-pipeline-detail.vue:109` | 新增 | 在 `actualDurationMinutes` 列后插入 `efficiencyDurationMinutes` 列定义 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| DWR 表中部分旧记录的 `efficiency_duration_ms` 为 NULL | SQL 中 `ROUND(NULL / 60000.0, 2)` → MySQL 返回 NULL，前端 `row.efficiencyDurationMinutes || 0` 不展示；与现有 NULL 处理一致 |
| 前端 columnData 未抽取到 columns.ts 文件 | 保持与现有代码风格一致（组件内定义），不做额外抽取 |
