# Nightly 流水线看板下钻页面增加 E2E 执行时长（不含重试）列 — 实现任务

## 进度: 3/4 complete（Task 4 延期到独立 PR）

### openlibing-ops（后端）

- [x] Task 1: `DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml` — resultMap 新增 `efficiency_duration_minutes` 映射，`getNightlyPipelineDetail` SELECT 新增 `ROUND(efficiency_duration_ms / 60000.0, 2) as efficiency_duration_minutes`
- [x] Task 2: `DwrRdEfcBuildFactNightlyTestCasePipelineRun.java` — 新增 `private BigDecimal efficiencyDurationMinutes;` 字段
- [x] Task 3: `NightlyPipelineDetailResp.java` — 新增字段 + 构造函数赋值

### openlibing-ops-web（前端）

- [ ] Task 4: `version-pipeline-detail.vue` — columnData 数组在 `actualDurationMinutes` 后新增 `efficiencyDurationMinutes` 列定义（已延期，本次需求交付中未 cherry-pick 对应 commit `fb9eee8`，由后续独立 issue 跟进）
