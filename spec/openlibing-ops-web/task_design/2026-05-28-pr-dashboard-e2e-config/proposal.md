# PR看板新增E2E配置弹窗与指标字段

## 需求背景

PR 门禁看板需要支持：
1. E2E 目标时长配置入口（页面弹窗）
2. 新增 PR E2E 时长、流水线启动时长、合入时长、E2E 达标率等指标字段展示

## 功能描述

### 一、弹窗修改（scan-branch-config.vue + sub-table.vue）
- 按钮名称从"代码量扫描分支配置"改为"配置"
- 弹窗内容改为 2 个页签：
  - Tab 1：代码量扫描分支配置（原内容不变）
  - Tab 2：PR门禁E2E达标时长配置（两列：代码仓 + 时长配置，只允许输入数字）
- 时长配置调用 E2E 目标配置 API（参考 E2E目标配置API接口文档.md）

### 二、表格字段修改（pr-columns.ts）
- prPipelineColumnData（Repo 层级）：
  - 在 门禁E2E执行 前插入 PR E2E 时长 (prE2eAvgTime/P50/P90)
  - 在 门禁E2E执行(不含重试) 后插入 流水线启动时长 (pipelineStartupAvgTime/P50/P90)
  - 在 备注 前插入 合入时长 (mergeLeadTimeAvg/P50/P90) + E2E达标率 (e2eMeetRate)
- prInfoDetailColumn（PR 层级）：
  - 在 门禁是否成功 后插入 PR E2E 时长 (prE2eTime)
  - 在 门禁E2E执行(不含重试) 后插入 流水线启动时长 (pipelineStartupTime)
  - 在 备注 前插入 合入时长 (mergeLeadTime)

## 验收标准
- [ ] 按钮名称改为"配置"，弹窗含 2 个页签
- [ ] E2E 时长配置页签可输入数字，调用 API 保存成功
- [ ] Repo 级表格新增字段位置正确、带单位
- [ ] PR 级明细表格新增字段位置正确、带单位

## 影响范围
- openlibing-ops-web: scan-branch-config.vue, sub-table.vue, pr-columns.ts, API 文件