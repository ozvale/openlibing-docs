# 版本级流水线看板新增E2E执行平均时长(去除重试)指标 — 技术设计

## 方案概述
在两个数据源表中新增`efficiency_duration_ms`字段，后端两个接口新增聚合和返回字段，前端新增展示列并替换Chart指标。

## 架构决策
| 决策 | 选择 | 原因 |
|------|------|------|
| 字段命名 | `efficiency_duration_ms` | 与PR门禁模块已有"去除重试"命名规范一致（参考`efficiency_avg_duration`） |
| 数据写入 | 上游ETL计算 | 同步计算去除重试后的时长写入新字段，无需后端额外处理 |
| 兼容性 | 新增字段+保留旧字段 | 原有"E2E执行"分组保持不变，新增独立分组，互不干扰 |
| Chart替换 | 前端替换key | 后端同时返回`avgAccessDuration`和`avgEfficiencyDuration`，不破坏兼容性 |

## 数据流

```
ETL任务写入
    │
    ├── dwr_rd_efc_build_fact_nightly_test_case_pipeline_run.efficiency_duration_ms
    │     ↓
    │   NightlyPipelineDashboardMapper.xml (pipeline_stats CTE)
    │   AVG / MAX / PERCENTILE 聚合
    │     ↓
    │   NightlyPipelineDashboardResp.efficiencyDurationAvgMinutes
    │   + P50/P90/P95/Max
    │     ↓
    │   前端表格渲染
    │
    └── dm_rd_efc_build_dim_nightly_pipeline_day.efficiency_duration_ms
          ↓
        DmRdEfcBuildDimNightlyPipelineDayMapper.xml
        ROUND(efficiency_duration_ms / 60000.0, 2)
          ↓
        VersionPipelineChartResp.avgEfficiencyDuration
          ↓
        前端Chart渲染
```

## 涉及接口
| 接口 | 方法 | 数据源表 |
|------|------|---------|
| `POST /pipeline/version/chart` | 图表 | `dm_rd_efc_build_dim_nightly_pipeline_day` |
| `POST /common/detail` (category=nightly-dashboard) | 表格 | `dwr_rd_efc_build_fact_nightly_test_case_pipeline_run` (主表) + `sdi_version_pipeline_base_info` (维度) |

## 涉及文件

### openlibing-ops（后端）
| 文件 | 操作 | 说明 |
|------|------|------|
| `NightlyPipelineDashboardMapper.xml` | 修改 | pipeline_stats CTE新增聚合、finalSelect新增分钟转换、resultMap新增映射 |
| `NightlyPipelineDashboard.java` | 修改 | 新增efficiencyDurationAvgMinutes等5个字段 |
| `NightlyPipelineDashboardResp.java` | 修改 | 新增5个字段及构造方法赋值 |
| `DmRdEfcBuildDimNightlyPipelineDayMapper.xml` | 修改 | resultMap和SQL查询新增efficiency_duration_minutes |
| `DmRdEfcBuildDimNightlyPipelineDay.java` | 修改 | 新增efficiencyDurationMinutes字段 |
| `VersionPipelineChartResp.java` | 修改 | PipelineInfoDayChart新增avgEfficiencyDuration字段 |
| `PipelineHandleImpl.java` | 修改 | buildDayCharts方法新增avgEfficiencyDuration赋值 |

### openlibing-ops-web（前端）
| 文件 | 操作 | 说明 |
|------|------|------|
| `version-pipeline-columns.ts` | 修改 | 新增E2E执行(去除重试)独立分组列 |
| `version-pipeline-chart.vue` | 修改 | metricList替换为E2E执行平均时长(min)(去除重试) |
| `metric-tips.ts` | 修改 | 新增efficiencyDurationAvgMinutes提示文案 |

## 命名对照
| 现有字段(含重试) | 新增字段(去除重试) | 单位 |
|------------------|-------------------|------|
| `actual_duration_ms` / `actualDurationAvgMinutes` | `efficiency_duration_ms` / `efficiencyDurationAvgMinutes` | 毫秒/分钟 |
| `actualDurationP50Minutes` | `efficiencyDurationP50Minutes` | 分钟 |
| `actualDurationP90Minutes` | `efficiencyDurationP90Minutes` | 分钟 |
| `actualDurationP95Minutes` | `efficiencyDurationP95Minutes` | 分钟 |
| `actualDurationMaxMinutes` | `efficiencyDurationMaxMinutes` | 分钟 |

## 风险 & 缓解
| 风险 | 缓解 |
|------|------|
| 新增字段为NULL时页面异常 | 前端处理空值显示"-"；后端返回null |
| ETL未写入新字段 | 字段允许为NULL，不影响现有数据；已有数据不受影响 |
| 上游ETL延迟 | 无数据时Chart/表格对应位置显示空值，不影响其他指标展示 |

## 向后兼容性
- 新增字段`efficiency_duration_ms`允许为NULL，已有数据不受影响
- 新增接口字段不影响现有前端解析（前端只取需要的字段）
- Chart替换key是前端行为，后端同时返回`avgAccessDuration`和`avgEfficiencyDuration`不会破坏兼容性

## ETL设计

### 数据流

```
PR门禁流水线效率计算任务（已有）
    │
    ├── dwr_rd_efc_pipeline_run_efficiency.efficiency_duration_sec（已有，单位秒）
    │     ↑ 已有ETL任务计算（PR模块）
    │
    │     ↓ LEFT JOIN
    │
    ├── [dwi→dwr] Nightly流水线测试用例执行事实表
    │     dwr_rd_efc_build_fact_nightly_test_case_pipeline_run.efficiency_duration_ms（新增）
    │     ← LEFT JOIN dwr_rd_efc_pipeline_run_efficiency → efficiency_duration_sec * 1000
    │
    │     ↓
    │
    └── [dwr→dm] nightly流水线每日汇总
          dm_rd_efc_build_dim_nightly_pipeline_day.efficiency_duration_ms（新增）
          ← AVG(efficiency_duration_ms) FROM DWR表
```

### 任务1: [dwi→dwr] Nightly流水线测试用例执行事实表

**改动1** — INSERT SELECT 中新增 LEFT JOIN（在 `test_case_statistics` JOIN 之后）：

```sql
LEFT JOIN dwr_rd_efc_pipeline_run_efficiency eff 
    ON fp.project_id = eff.project_id 
    AND fp.pipeline_id = eff.pipeline_id 
    AND fp.pipeline_run_id = eff.pipeline_run_id
```

**改动2** — INSERT SELECT 字段列表末尾新增第37列：

```sql
fp.pipeline_end_time,                              -- 36. pipeline_run_endtime
eff.efficiency_duration_sec * 1000                 -- 37. efficiency_duration_ms(去除重试)
```

### 任务2: [dwr→dm] nightly流水线执行任务每日汇总

**改动** — SELECT 聚合列表末尾新增第19列（在 `is_version_available` 之后）：

```sql
MAX(is_version_available) AS is_version_available, -- 18. 版本可用度
CAST(ROUND(AVG(efficiency_duration_ms), 0) AS BIGINT) AS efficiency_duration_ms  -- 19. E2E执行平均时长(去除重试)
```

### 涉及DS任务

| 任务 | 工作流编码 | 任务编码 | 当前版本 |
|------|-----------|---------|---------|
| [dwr]dwr_rd_efc_build_fact_nightly_test_case_pipeline_run | 169496639078592 | 169496639079616 | v14 |
| [dm]nightly流水线执行任务每日汇总 | 169496639269056 | 169496639269058 | v4 |

### 验证方式

1. 任务执行后查询DWR表：`SELECT pipeline_run_id, efficiency_duration_ms FROM dwr_rd_efc_build_fact_nightly_test_case_pipeline_run WHERE efficiency_duration_ms IS NOT NULL LIMIT 10`
2. 任务执行后查询DM表：`SELECT pipeline_id, pipeline_run_endtime, efficiency_duration_ms FROM dm_rd_efc_build_dim_nightly_pipeline_day WHERE efficiency_duration_ms IS NOT NULL LIMIT 10`
3. 调用后端API验证数据返回

## 跨仓影响
- **openlibing-ops** ↔ **openlibing-ops-web**：后端新增字段与前端新增列一一对应，需协调发布
- **上游ETL**：需同步计算`efficiency_duration_ms`并写入两个表
