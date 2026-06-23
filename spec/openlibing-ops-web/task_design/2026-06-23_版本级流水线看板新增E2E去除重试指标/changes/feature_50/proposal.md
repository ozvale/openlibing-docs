# 版本级流水线看板新增E2E执行平均时长(去除重试)指标 — 前端

## 需求
版本级流水线看板前端新增"E2E执行(去除重试)"分组列，并将Chart中的E2E执行平均时长指标替换为去除重试版本。

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `version-pipeline-columns.ts` | 修改 | 在`actualDuration`分组后新增`efficiencyDuration`独立分组 |
| `version-pipeline-chart.vue` | 修改 | metricList中替换key和label |
| `metric-tips.ts` | 修改 | 新增`efficiencyDurationAvgMinutes`提示文案 |

## 改动要点
1. **表格列**：新增独立分组"E2E执行(去除重试)"，含P50/P90/P95/平均/最长5个子列
   - 仅`efficiencyDurationAvgMinutes`设置`defaultShow: true`
   - 其余子列不设置`defaultShow`（即不默认展示）
2. **Chart组件**：metricList中"E2E执行平均时长（min）"→"E2E执行平均时长（min）（去除重试）"
   - key从`avgAccessDuration`改为`avgEfficiencyDuration`
   - helpTip从`actualDurationAvgMinutes`改为`efficiencyDurationAvgMinutes`
3. **提示文案**：新增`efficiencyDurationAvgMinutes`指标定义和计算方式

## 验收标准
- [ ] 表格正确展示"E2E执行(去除重试)"分组，含5个子列
- [ ] 仅"E2E执行平均时长(min)(去除重试)"默认展示
- [ ] Chart正确展示"E2E执行平均时长（min）（去除重试）"曲线
- [ ] 提示文案正确显示指标定义和计算方式
- [ ] 字段为NULL时页面显示"-"或空值（不崩溃）
