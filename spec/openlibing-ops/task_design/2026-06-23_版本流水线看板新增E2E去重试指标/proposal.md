# 版本级流水线看板新增E2E执行平均时长(去除重试)指标

## 需求背景

版本级流水线看板当前展示的"E2E执行平均时长"包含重试耗时，无法准确反映流水线实际执行效率。需要在看板中新增"去除重试"的E2E执行时长指标，帮助SRE和开发团队更准确地评估流水线执行效率。

**两个阶段：**
1. **Issue #50（版本级流水线看板子页面）**：在 `version-pipeline` 子页面的 Chart 和表格中新增去除重试的 E2E 时长指标
2. **Issue #59（开源项目运营总览主表）**：在 `open-source-project` 主表的「Nightly流水线运营→流水线平均时长」分组中新增不含重试的 E2E 时长列

## 功能描述

### 做什么

1. **数据库**：两个数据源表新增 `efficiency_duration_ms` 字段；`dwi_project_statistics` 表新增 `version_efficiency_duration` 字段
2. **ETL 链路**：复用 PR 门禁流水线效率计算任务的 `efficiency_duration_sec` 字段，经过 DWR → DM → DWI 层写入
3. **后端 API**：
   - `POST /pipeline/version/chart`：返回 `avgEfficiencyDuration` 字段
   - `POST /common/detail (category=nightly-dashboard)`：返回 `efficiencyDurationAvgMinutes` 等 5 个统计字段
   - `POST /common/detail (category=project)`：返回 `versionEfficiencyDuration` 字段
4. **前端展示**：
   - Chart 图表：替换为"E2E执行平均时长（min）（去除重试）"
   - 表格新增独立分组"E2E执行(去除重试)"，含 P50/P90/P95/平均/最长 5 个子列
   - 开源项目运营总览主表新增"E2E执行平均时长(min)(不含重试)"列

### 不做什么

- 不修改含重试的已有字段和展示
- 不修改其他看板页面
- 不修改 PR 门禁流水线已有逻辑

## 验收标准

- [ ] 两个数据源表 DDL 执行成功，`efficiency_duration_ms` 字段可写入
- [ ] `dwi_project_statistics` 表 DDL 执行成功，`version_efficiency_duration` 字段可写入
- [ ] ETL 工作流执行后，DWR/DM/DWI 三层表均有去除重试的时长数据
- [ ] Chart 接口返回 `avgEfficiencyDuration`，表格接口返回 `efficiencyDurationAvgMinutes` 等字段
- [ ] 开源项目总览接口返回 `versionEfficiencyDuration` 字段
- [ ] 前端 Chart 正确渲染去除重试的平均时长
- [ ] 前端表格正确展示新分组和列
- [ ] 字段为 NULL 时页面显示 "-" 或空值（不崩溃）
- [ ] 含重试字段数据不变

## 影响范围

| 模块 | 仓库 | 影响说明 |
|------|------|---------|
| Doris DDL | — | 3 个表新增字段，均允许 NULL，在线执行 |
| ETL 工作流 | DolphinScheduler | 3 个工作流 SQL 修改 |
| 后端 Mapper | openlibing-ops | 3 个 Mapper XML 新增字段映射 |
| 后端 Model | openlibing-ops | 3 个 Model 新增字段 |
| 后端 Response DTO | openlibing-ops | 2 个 Response DTO 新增字段 + 构造赋值 |
| 后端 Handler | openlibing-ops | 1 个 Handler Chart 赋值 |
| 前端列定义 | openlibing-ops-web | 2 个列定义文件新增列 |
| 前端 Chart | openlibing-ops-web | 1 个 Chart 组件替换 key |
| 前端文案 | openlibing-ops-web | 1 个提示文案新增 |
