# NPU 资源视图与主表格资源列调整 — 实现任务

关联 Issue: https://gitcode.com/openlibing/openlibing-ops-web/issues/31
分支: `feat/engineering-capability-npu-resource`（领先 `origin/main` 22 个 commit）

## 进度: 14/14 complete（8 项主任务 + 第二轮回写追加 6 项）

> 说明：以下勾选项为实际实现结果，字段名/结构以接口文档 v2/v3 与联调结果为准（回写）。Task 9-14 为第二轮回写（2026-08-06）补记的后续 commit。

### Phase 3 任务清单

- [x] Task 1: 类型与 API 扩展
  - `types/engineering-capability.ts`：`ResourcePipelineType` 扩展 `'NPU'`；新增 `NpuResourceRow`（`resourcePoolId: string`）/ `NpuResourceServerRow` / NPU 全量 summary 响应类型；`ProjectRow` 新增 `resourceQueueTime` / `npuAllRate`
  - `api/dashboard/engineering-capability.ts`：新增 `getOpsNpuAllSummary`
  - 验证：`npm run lint:es` + `npm run typecheck`

- [x] Task 2: metric-tips 扩展
  - `config/metric-tips.ts`：新增 `resourceQueueTime`（PR 资源排队 P90 说明）与 `npuUsageRate`（NPU 使用率说明）
  - 验证：lint

- [x] Task 3: 主表格列定义重构
  - `config/columns.ts`：重构 `resourceColumns(prefix)`；抽取 `npuUsageColumns(prefix)`（NPU消耗 / NPU平均消耗）；**`prPipeline` 分组**在 `prDurationP90` 之后加 `resourceQueueTime`（回写：不在资源环境区）；整体资源在 `NPU分配率` 之后加 `npuAllUsage`（NPU使用(卡时)）+ `npuAllRate`（NPU使用率）；`prDetailColumns` 在 `prDuration` 后加 `resourceQueueTime`；精简 `resourceDetailColumns`（删除 CPU消耗 / CPU平均消耗）
  - 验证：`__tests__/columns.test.ts` 更新断言并通过（回写：后续新增 `npuAllUsage` 时未同步，已在 Task 14 修正）

- [x] Task 4: main-table.vue 适配
  - `resourceRateCols = ['overallNpuRate', 'npuAllRate']`；`resourceOtherCols` 首项加入 `resourceQueueTime`
  - `getLightStatus` 纳入 `npuAllRate` 红绿灯逻辑
  - 验证：lint + 单测

- [x] Task 5: resource-tab.vue 三态切换
  - filter-bar 加 `NPU资源` 按钮并置于**最左侧**；`currentFilter` 支持 'NPU'，默认 `'NPU'`
  - KPI 卡片精简为 2 个（NPU消耗 / NPU平均消耗）
  - 表格列精简（流水线名称 / NPU消耗 / NPU平均消耗）
  - `v-if="currentFilter === 'NPU'"` 挂载 `npu-resource-panel.vue`；`onMounted` 仅在非 NPU 态调用 `fetchSummary`
  - 验证：lint

- [x] Task 6: npu-resource-panel.vue 新增
  - 5 KPI 卡片，回写后顺序为「使用→总量→分配」：NPU使用率 / NPU使用卡时 / NPU总量 / NPU分配率 / NPU分配卡时（全部有实值，无 `--` 占位）
  - 表格 4 列（资源池名称 / 资源池使用卡时 / 资源池总卡时 / NPU使用率），`row-key="resourcePoolId"`
  - 行点击 `resourcePoolName` 触发 `npu-resource-detail-modal.vue`
  - summary 用 `to()` 包装调用 `getOpsNpuAllSummary`；列表走 `getCommonDetail({category: 'ops-npu-all-detail'})`（回写：独立 category，非 `ops-resource-detail` type=`All`）
  - 数值格式化复用 `config/time-range` 公共 `formatRate` / `formatNum`
  - 验证：lint + 行数 ≤400

- [x] Task 7: npu-resource-detail-modal.vue 新增
  - `el-dialog` + `base-table` 分页
  - 表格 5 列（资源名称 / 资源ip / 使用卡时 / 资源总卡时 / NPU使用率）
  - 调用 `getCommonDetail({category: 'ops-npu-all-server-detail', resourcePoolId(String)})`
  - 复用公共 `formatRate`
  - 验证：lint

- [x] Task 8: mock 数据 + .gitignore + 测试更新
  - `/mock/npu-all-detail.ts`（vite-plugin-mock 单文件，rawResponse 按 category/type 分发：summary + 资源池列表 + 服务器列表）
  - 确认 `.gitignore` 含 `/mock` 规则
  - 更新 `__tests__/columns.test.ts` 列数与新增列断言
  - 验证：`npm run lint:es` + `npm run test:unit`

### 回写追加任务清单（第二轮，2026-08-06）

- [x] Task 9: dateParams 注入上下文重构（`fd9f0c7`）
  - `types/engineering-capability.ts`：`ECDetailParamsContext` 加 `dateParams`
  - `detail-panel` / `nightly-tab` / `repo-tab` / `resource-tab` / `runs-record-modal` / `npu-resource-panel` / `npu-resource-detail-modal` / `engineering-capability-view` 改用 inject，移除逐层 props 透传
  - 验证：lint + typecheck

- [x] Task 10: resolveTabByColKey 重构 + repo-tab KPI 扩展（`6b35a75`）
  - `composables/use-engineering-capability.ts`：`TAB_BY_GROUP` 声明式映射 + `collectLeafProps` 递归 + 模块加载期建 `colKeyToTab` Map
  - `repo-tab.vue`：新增 `PR资源排队时长` KPI 卡片，`kpi-row-4` → `kpi-row-5`
  - 验证：lint + 单测

- [x] Task 11: 共享样式与渲染修复（`8762ebf` / `dfba8ab`）
  - `style.less`：`kpi-row` 基类 + `--2`/`--5` 修饰类 + 1280/768/480 响应式断点集中定义
  - `nightly-tab` / `repo-tab` / `resource-tab` / `npu-resource-panel`：移除局部网格定义
  - `main-table.vue`：无 slot 单元格加 `v-else-if="row[col.key]"` 纯文本分支，`v-else` 收窄为真缺值
  - 验证：lint:style + lint:es

- [x] Task 12: KPI 卡片重排 + 列设置缓存 key 迁移（`70c73cb`）
  - `npu-resource-panel.vue`：5 卡片按「使用→总量→分配」重排 + 图标调整
  - `engineering-capability-view.vue`：`column-data-key` → `engineeringCapabilityColumns`
  - `App.vue`：`onMounted` 清理旧 key `engineering-capability-columns`
  - 验证：lint + 手工验证列设置在旧缓存存在时不异常

- [x] Task 13: 标签与指标说明修正（`4b1a07b` / `1326705` / `2da280f` / `a58a01d`）
  - `columns.ts`：主表 / `prDetailColumns` P90 后缀标注；新增 `npuAllUsage` 列；`defaultShow` 收敛（NPU消耗全否、NPU平均消耗仅 pr、NPU分配率转否）；多列列宽微调
  - `repo-tab.vue`：`PR执行时长-P90` / `PR资源排队时长-P90` 标签
  - `metric-tips.ts`：排队时长公式去 `/60`；分配率公式名修正 + 含义补充；NPU使用率含义补充
  - 验证：lint

- [x] Task 14: columns.test.ts 断言同步（`225ea02`）
  - `npuAllUsage` 列在 `4b1a07b` 加入后未同步测试断言，导致 2 用例失败，此次修正：
    - `should have 24 leaf columns total after NPU resource refactor` → 改名 25，列数断言 24 → 25
    - `should include npuAllRate as NPU usage rate column`：过时的 `not.toContain('npuAllUsage')` 改为 `toContain('npuAllUsage')` 正向断言
  - 验证：`npx vitest run src/views/dashboard/engineering-capability` → 3 文件 / 29 用例全通过

## 验证方式

- 静态：`npm run lint:es`
- 类型：`npm run typecheck`
- 单测：`npm run test:unit`
- 构建：`npm run build`

### 最近一次实测结果（2026-08-06，HEAD = `225ea02`）

| 范围                                               | 命令                                                        | 结果                    |
| -------------------------------------------------- | ----------------------------------------------------------- | ----------------------- |
| 本需求单测                                         | `npx vitest run src/views/dashboard/engineering-capability` | 3 文件 / 29 用例全通过  |
| 全量单测（排除本需求外的 `base-kpi-card.test.ts`） | `npx vitest run --exclude "**/base-kpi-card.test.ts"`       | 12 文件 / 99 用例全通过 |

> 先前文档记载的「15/15 通过」为 `1338009` 时点结果，已随后续 commit 失效，此处更正。
