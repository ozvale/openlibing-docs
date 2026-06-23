# 版本级流水线看板新增E2E执行平均时长(去除重试)指标 — 前端设计

## 方案概述
在版本级流水线看板表格中新增独立分组列，替换Chart组件中的指标key，新增提示文案。

## 架构决策
| 决策 | 选择 | 原因 |
|------|------|------|
| 表格列位置 | 在`actualDuration`分组后、`buildTime`分组前插入 | 按"E2E执行→E2E执行(去除重试)→构建任务"的逻辑顺序排列 |
| 默认展示 | 仅平均列`defaultShow: true` | 需求明确要求仅平均列默认展示，其余子列用户可按需开启 |
| Chart替换 | 替换原有key，不保留旧指标 | 去除重试的时长更能反映真实效率，且后端同时返回新旧两个字段 |

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `version-pipeline-columns.ts` | 修改 | 新增efficiencyDuration分组，5个子列 |
| `version-pipeline-chart.vue` | 修改 | metricList替换key和label |
| `metric-tips.ts` | 修改 | 新增efficiencyDurationAvgMinutes文案 |

## 字段映射
| 后端字段 | 前端prop | 前端label |
|---------|---------|----------|
| `efficiencyDurationP50Minutes` | `efficiencyDurationP50Minutes` | P50E2E执行时长(min)(去除重试) |
| `efficiencyDurationP90Minutes` | `efficiencyDurationP90Minutes` | P90E2E执行时长(min)(去除重试) |
| `efficiencyDurationP95Minutes` | `efficiencyDurationP95Minutes` | P95E2E执行时长(min)(去除重试) |
| `efficiencyDurationAvgMinutes` | `efficiencyDurationAvgMinutes` | E2E执行平均时长(min)(去除重试) |
| `efficiencyDurationMaxMinutes` | `efficiencyDurationMaxMinutes` | E2E执行最长时长(min)(去除重试) |
