# Nightly 流水线看板下钻页面增加 E2E 执行时长（不含重试）列

## 需求背景

Nightly 流水线看板（版本级流水线看板）主表已在 `version-pipeline-columns.ts` 中增加了 `efficiencyDuration` 分组（E2E执行(去除重试)，P50/P90/P95/Avg/Max 5 个分位），但下钻明细页（`version-pipeline-detail.vue`）点击单条流水线进入的每次执行记录清单中，只展示了 `actualDurationMinutes`（E2E执行时长，含重试），缺失 `efficiencyDurationMinutes`（E2E执行时长，不含重试）列。

用户需要在下钻页看到每次 Nightly 执行的 E2E 执行时长（不含重试），以便与含重试时长对比，定位重试耗时占比。

## 功能描述

- **做什么**：在 Nightly 流水线看板下钻明细页（`version-pipeline-detail.vue`）的表格中新增 `efficiencyDurationMinutes` 列
- **不做什么**：不新增 KPI 卡片；不修改主表列；不修改 ETL/DDL（数据库字段 `efficiency_duration_ms` 已存在）

## 验收标准

- [ ] 下钻页表格展示"E2E执行时长（min）（不含重试）"列，数据来源为后端返回的 `efficiencyDurationMinutes` 字段
- [ ] 后端 `NightlyPipelineDetailResp` 返回 `efficiencyDurationMinutes`，值来自 DWR 表 `efficiency_duration_ms` 的分钟换算
- [ ] 列可排序，默认显示
- [ ] 不影响已有列的行为和展示
- [ ] 后端编译通过，前端 dev server 正常

## 影响范围

| 仓库 | 文件 | 操作 |
|------|------|------|
| `openlibing-ops` | `DwrRdEfcBuildFactNightlyTestCasePipelineRun.java` | 新增字段 |
| `openlibing-ops` | `DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml` | resultMap + SELECT 新增 |
| `openlibing-ops` | `NightlyPipelineDetailResp.java` | 新增字段 + 构造函数赋值 |
| `openlibing-ops-web` | `version-pipeline-detail.vue` | columnData 新增列定义 |
