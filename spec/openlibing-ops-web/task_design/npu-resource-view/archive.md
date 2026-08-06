# NPU 资源视图与主表格资源列调整 — 归档

| 项目           | 内容                                                                          |
| -------------- | ----------------------------------------------------------------------------- |
| 目标仓         | `openlibing-ops-web`                                                          |
| 需求目录       | `spec/openlibing-ops-web/task_design/npu-resource-view/`                      |
| 关联业务 Issue | https://gitcode.com/openlibing/openlibing-ops-web/issues/31                   |
| 开发分支       | `feat/engineering-capability-npu-resource`（领先 `origin/main` 22 个 commit） |
| 流程模式       | Light（spec 回写 + 归档）                                                     |
| 归档日期       | 2026-08-06                                                                    |
| 归档时 HEAD    | `225ea02`                                                                     |

## 交付结果

### 已实现范围

1. **主表格资源列精简**：资源环境区删除 16 列 CPU/NPU 冗余列（PR 6 + Nightly 6 + 整体 4），该区叶子列由 24（3 区 × 8）降为 10；新增 `resourceQueueTime`（PR资源排队时长-P90，归入 `prPipeline` 分组）与 `npuAllUsage` / `npuAllRate`（整体资源 NPU 使用卡时 / 使用率）。主表叶子列合计由 24 → **25** 列，顶层分组 7 个。
2. **NPU 资源视图**：资源 tab 新增 NPU 资源面板（category `ops-npu-all-detail`），5 张 KPI 卡片按「使用 → 总量 → 分配」顺序排列 + 资源池明细表；点击资源池下钻到服务器级弹窗（category `ops-npu-all-server-detail`）。
3. **repo-tab KPI**：新增 `PR资源排队时长-P90` 卡片，kpi-row 由 4 列扩为 5 列。
4. **P90 标签统一**：主表 / PR 明细 / repo-tab KPI 统一补 `-P90` 后缀，避免误读为均值。
5. **指标说明修正**：排队时长公式去掉错误的 `/60`；分配率公式命名与含义修正；NPU 使用率含义补充。
6. **列设置缓存 key 迁移**：缓存 key 改为 `engineeringCapabilityColumns`，并在 `App.vue` 清理旧 key（列结构变动后旧缓存不兼容，prop diff 不足以兼容）。
7. **工程化改造**：抽取 `npuUsageColumns` 工厂；`dateParams` 改为 injection context 下发；`resolveTabByColKey` 改为声明式 `TAB_BY_GROUP` 映射 + 构建期 Map；抽取共享 `kpi-row` 栅格样式；表格单元格无 link/tooltip slot 时回退纯文本渲染；默认时间范围 30 → 7 天。

### 验证结果（HEAD = `225ea02`）

| 范围                                               | 命令                                                        | 结果                    |
| -------------------------------------------------- | ----------------------------------------------------------- | ----------------------- |
| 本需求单测                                         | `npx vitest run src/views/dashboard/engineering-capability` | 3 文件 / 29 用例全通过  |
| 全量单测（排除本需求外的 `base-kpi-card.test.ts`） | `npx vitest run --exclude "**/base-kpi-card.test.ts"`       | 12 文件 / 99 用例全通过 |

## 关键偏差回顾

实现与初始设计的偏差已逐条记录在 `proposal.md` 的「实现偏差说明（回写）」与 `design.md` 的对应决策条目中，主要集中在三类：

1. **字段名与分组归属**：后端实际字段为 `resourceQueueTime`（非 `prResourceQueueTime`），且该指标语义属流水线效率，落在 `prPipeline` 分组而非资源环境区。
2. **列可见性收敛**：新增列并非一律 `defaultShow: true`。资源环境区实际默认显示的仅 `prNpuAvg`（NPU平均消耗，`prefix === 'pr'`）与 `npuAllRate`（NPU使用率）两列；NPU消耗三区均未声明 `defaultShow`，`overallNpuRate` 与 `npuAllUsage` 同样未声明，需由列设置手动开启。
3. **缓存兼容策略**：列结构变动后靠 prop diff 无法兼容旧缓存，最终改为换 key + 清理旧 key。

## 遗留问题

无。原记录的 `columns.test.ts` 断言未同步问题已在 `225ea02` 修复（列数断言 24 → 25，过时的 `not.toContain('npuAllUsage')` 改为正向断言）。

## 后续建议

1. 分支上 `789e540`（code-check 卡片基类合并）不属于本需求范围，归属其自身需求目录，未纳入本 spec。
2. 主表叶子列总数断言属于「结构性断言」，后续增删列时须同步；建议在新增列的同一 commit 内更新 `columns.test.ts`，避免再次出现断言滞后。

## Artifact 索引

| 文件          | 说明                                                 |
| ------------- | ---------------------------------------------------- |
| `proposal.md` | 需求背景、功能描述、验收标准、影响范围、实现偏差说明 |
| `design.md`   | 技术方案与 12 项关键决策、涉及文件、风险             |
| `tasks.md`    | 14 项实现任务（8 项主任务 + 6 项回写补记）与验证结果 |
| `archive.md`  | 本文件                                               |
