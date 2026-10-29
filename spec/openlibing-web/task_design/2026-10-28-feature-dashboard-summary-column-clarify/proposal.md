# 2026-10-28 特性看板汇总列命名澄清与详情入口调整提案

## 1. 需求背景

特性运营看板（`FeatureDashboard`）社区×特性矩阵的最后一列原列名为"全部"，其点亮口径为"任一社区（含未归属任何社区的上报数据）存在上报即点亮"（OR 聚合，由后端 `resolveMatrixStatus` 计算，接口值 `ALL`）。"全部"字面容易被理解为"所有社区都接入"（AND），导致"各社区列均未点亮、该列却点亮"的困惑——实际点亮来源可能是未归属任何社区的上报数据，属正常现象。

### 需求描述

- 列名"全部"改为"汇总"，消除"全部=所有社区都接入"的误读
- "已接入"单元格的对勾状态圈替换为"详情"链接按钮，点击打开汇总详情抽屉（与原对点击行为一致）
- 移除汇总列相关 tooltip（列头说明图标与提示、单元格"汇总视角"提示）
- 所有逻辑不动：接口值 `ALL`、OR 点亮口径、下钻行为、统计卡口径均保持现状，纯展示层调整

### 术语决策

- **汇总列（ALL）**：该列的权威名称。展示全部社区及未归属社区上报数据的聚合视图，存在任一上报即点亮。后续文档与 UI 文案统一用"汇总"，避免使用"全部"。
- **未归属社区数据**：不属于任何一个社区、但计入汇总列的上报数据，是"社区列全灭而汇总列点亮"的正常成因。

## 2. 验收标准

### 功能验收

- [x] 矩阵最后一列表头显示"汇总"，不再带说明图标与 tooltip
- [x] "已接入"单元格显示"详情"链接按钮，点击打开汇总详情抽屉；插件明细子行同样生效
- [x] "未接入/不涉及"单元格保留原状态图标，且不再弹出"汇总视角"tooltip
- [x] 详情抽屉社区下拉选项"全部"改为"汇总"
- [x] 指标配置弹窗中 5 处用户可见"全部列"文案统一为"汇总列/「汇总」"
- [x] 各社区列的状态图标与 tooltip 不受影响

### 代码质量验收

- [x] ESLint 无错误；`FeatureDashboard` 模块 56 个单元测试全部通过
- [x] pre-commit 钩子（prettier/ESLint/secrets 扫描）全部通过

## 3. 变更范围

### 涉及模块

- **前端组件**：`apps/web-openlibing/src/views/manageCenter/FeatureDashboard/`
  - `components/StatusMatrix.vue` — 列名改"汇总"、移除列头图标与 tooltip、对勾替换为"详情"按钮、移除单元格 tooltip
  - `components/StatusCell.vue` — `content` 为空时禁用 tooltip（避免空气泡），社区列用法不变
  - `components/DetailDrawer.vue` — 社区下拉"全部"→"汇总"
  - `constants.ts` — 指标配置弹窗 5 处"全部列"文案及相邻注释改"汇总列"
  - `index.vue` — 注释同步更名

### 变更类型

- 体验优化（命名澄清 + 下钻入口显性化），无逻辑变更、无接口变更、无破坏性变更

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅特性看板展示层；接口值 `'ALL'`、状态聚合口径、下钻与统计卡逻辑均未动
- **破坏性变更**: 无
- **遗留说明**: `types.ts`/`MetricCard.vue` 等内部注释中仍有"全部列"字样，属代码注释不影响用户，后续顺手清理

## 5. 关联信息

- **业务仓**: dyy-1/openlibing-web_9915（openlibing-web fork 仓）
- **业务仓分支**: `perf-web-lcp-no-data`
- **Commit**:
  - `5595d81b` feat(feature-dashboard): rename ALL column to 汇总 and clarify scope
  - `eea755ca` feat(feature-dashboard): replace check icon with detail button in summary column
  - `a7b443e2` feat(feature-dashboard): remove summary column hint icon and cell tooltips
- **关联 spec**: 本调整为 `2026-09-22-feature-dashboard-metric-config-fe` 之外独立的展示层调整，不改变该 spec 定义的配置弹窗行为与字段契约
