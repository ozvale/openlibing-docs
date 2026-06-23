# 版本级流水线看板新增E2E执行平均时长(去除重试)指标 — 前端实现任务

## 进度: 3/3 complete

- [x] **T1: 表格列定义修改**
  - 文件: `version-pipeline-columns.ts`
  - 内容: 新增`efficiencyDuration`分组，5个子列
  - 关键点: 仅`efficiencyDurationAvgMinutes`设置`defaultShow: true`

- [x] **T2: Chart组件修改**
  - 文件: `version-pipeline-chart.vue`
  - 内容: metricList替换，key从`avgAccessDuration`改为`avgEfficiencyDuration`

- [x] **T3: 提示文案新增**
  - 文件: `metric-tips.ts`
  - 内容: 新增`efficiencyDurationAvgMinutes`，含指标定义和计算方式

### 验证方式
- [ ] 表格正确展示新分组和列
- [ ] Chart正确渲染去除重试的平均时长
- [ ] 字段为NULL时页面显示"-"或空值（不崩溃）
