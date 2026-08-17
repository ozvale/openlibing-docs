# NPU 资源视图与主表格资源列调整 — 技术设计

## 方案概述

复用现有 `resourceColumns(prefix)` 工厂模式按需裁剪列；`resource-tab.vue` 引入 `currentFilter` 三态（PR / Nightly / NPU），切换到 NPU 时挂载新组件 `npu-resource-panel.vue`；NPU 资源弹窗复用 `el-dialog` + `base-table` + `getCommonDetail` 走新 category。

> 本文档已经过两轮回写：第一轮对齐接口文档 v2/v3（见各节"回写修正"），第二轮（2026-08-06）覆盖 `1338009` 之后的 commit，新增决策 3.2 / 3.3 / 8 / 9 / 10 / 11 / 12 并修正决策 3 与 7。偏差汇总见 `proposal.md`。

## 架构决策

### 1. 主表格列裁剪策略

**决策**：重构 `resourceColumns(prefix)` 工厂函数，按 prefix 返回不同列集，而非删除 `ProjectRow` 字段。

**原因**：

- 后端可能仍返回已删字段，前端不展示即可，避免后端联动改动
- `column-setting` 按 prop diff 兼容：用户已勾选的 prop 若被删除则自动剔除，新增 prop 按 `defaultShow` 显示
- `main-table.vue` 的 `resourceTotalCols` / `resourceRateCols` / `resourceOtherCols` 数组同步精简，避免 `getTips` 引用已删 prop

### 2. PR 资源排队时长列（回写修正）

**字段**：`resourceQueueTime`（number，单位分钟；接口文档 v2 命名，去掉 pr 前缀）
**列定义**：`{ prop: 'resourceQueueTime', label: 'PR资源排队时长(min)-P90', minWidth: 154, sortable: true, defaultShow: true, helpTip: engineeringMetricTips.resourceQueueTime }`
**位置（回写修正）**：**`prPipeline`（PR流水线）分组** children 末位，位于 `prDurationP90` 之后——该指标语义属流水线效率而非资源用量，故不放在 `resourceEnv/prResource` 下
**main-table.vue**：`resourceOtherCols` 首项加入 `resourceQueueTime`
**helpTip**：`metric-tips.ts` 的 `resourceQueueTime`（P90 公式说明；回写：公式已修正为 `P90构建排队时长 + P90测试排队时长`，删除原先错误的 `/ 60`）

### 3. NPU 使用率与使用卡时列（回写修正）

**`npuAllRate`**（number，0-1 比率）——接口文档原写"分配率"有误，实际语义为**使用率**；原设计的 `overallNpuUsageRate` 与之重复，已删除，统一用 `npuAllRate`
**`npuAllUsage`**（回写修正）——原设计写"不展示"，实际**已作为整体资源列展示**：`{ prop: 'npuAllUsage', label: 'NPU使用(卡时)', minWidth: 104, sortable: true }`（未设 `defaultShow`，需列设置手动开启），位于 `overallNpuRate` 之后、`npuAllRate` 之前。理由：使用率是比值，缺少绝对量无法判断基数大小，两者互为参照
**`npuAllRate` 列定义**：`{ prop: 'npuAllRate', label: 'NPU使用率', subLabel: '(>30%)', minWidth: 124, sortable: true, defaultShow: true, helpTip: resourceMetricTips.npuUsageRate }`
**main-table.vue**：`resourceRateCols = ['overallNpuRate', 'npuAllRate']`，`getLightStatus` 纳入 `npuAllRate` 红绿灯逻辑
**主表叶子列总数**：**25**（回写：非 24，`npuAllUsage` 为新增）。顶层分组 7 个；资源环境区叶子列由 24（3 区 × 8）降为 10（PR 2 + Nightly 2 + 整体 6），即实际删除 **16** 列。

### 3.1 NPU 消耗列抽取（回写新增）

**决策**：将 `resourceColumns(prefix)` 中重复的 `NPU消耗` / `NPU平均消耗` 两列抽为 `npuUsageColumns(prefix)` 工厂方法，PR / Nightly / overall 复用，减少重复。

### 3.2 defaultShow 收敛策略（回写新增）

**决策**：新增列不一律 `defaultShow: true`，按信息价值分层——比值类与 PR 关键指标默认显示，绝对量类默认隐藏交由列设置开启。

```ts
function npuUsageColumns(prefix: string): ColumnProps[] {
  const show = prefix === "pr"; // NPU 平均消耗仅 PR 区默认显示
  // NPU 消耗：三区一律不设 defaultShow
  // NPU 平均消耗：defaultShow: show（pr 为 true，nightly / overall 显式 false）
}
```

`overallNpuRate`（NPU分配率）的 `defaultShow` 在 `a58a01d` 中取消——分配率与使用率并列会造成误读，使用率是主指标。`npuAllUsage`（NPU使用(卡时)）同样未设 `defaultShow`。实际默认显示的资源环境区列仅 `prNpuAvg` 与 `npuAllRate` 两列。

### 3.3 P90 语义标注（回写新增）

**决策**：分位数指标在 label 上显式标注 `-P90` 后缀，而非仅靠 helpTip 说明。

**原因**：`prDurationP90` 的 prop 名带 P90 但 label 不带，用户会误读为均值；`resourceQueueTime` 的 prop 名甚至不含 P90 提示。统一在三处标注：主表列、`prDetailColumns`、`repo-tab.vue` KPI 卡片标签。

### 4. 资源环境页签三态切换

**决策**：`currentFilter` 类型从 `'PR' | 'Nightly'` 扩展为 `'PR' | 'Nightly' | 'NPU'`，默认值为 `'NPU'`
**布局**：

- filter-bar：`NPU资源 / PR / Nightly` 三个按钮互斥，**NPU资源 位于最左侧**（回写修正）
- 切换 PR/Nightly：保持现有 KPI 卡片（精简为 2 个：NPU消耗、NPU平均消耗）+ 明细表格（精简为 3 列）
- 切换 NPU资源：挂载 `npu-resource-panel.vue`，隐藏原 KPI 行与明细表格
- 用 `v-if="currentFilter === 'NPU'"` 切换显示
- `onMounted` 仅在非 NPU 态调用 `fetchSummary`（回写修正）

### 5. NPU 资源面板组件（回写修正）

**新组件**：`components/npu-resource-panel.vue`（页级组件，≤400 行）
**inject**：`E_C_DETAIL_PARAMS_KEY`（提供 `projectId` + `dateParams`）
**布局**：

- KPI 行：5 卡片，回写后按「使用 → 总量 → 分配」阅读顺序排列：

  | 顺序 | 标签        | 字段              | 格式化       | color   |
  | ---- | ----------- | ----------------- | ------------ | ------- |
  | 1    | NPU使用率   | `npuRate`         | `formatRate` | blue    |
  | 2    | NPU使用卡时 | `totalNpuUsage`   | `formatNum`  | yellow  |
  | 3    | NPU总量     | `totalNpuHours`   | `formatNum`  | indigo  |
  | 4    | NPU分配率   | `overallNpuRate`  | `formatRate` | rose    |
  | 5    | NPU分配卡时 | `overallNpuUsage` | `formatNum`  | emerald |

  全部取自 summary，无 `--` 占位；样式用共享 `kpi-row kpi-row--5`

- 表格：`base-table` + `npuResourceColumns`（**4 列**：资源池名称 / 资源池使用卡时 / 资源池总卡时 / NPU使用率），`row-key="resourcePoolId"`
- 数据源：列表走 `getCommonDetail({category: 'ops-npu-all-detail', projectId, ...dateParams})`（回写：category 为独立的 `ops-npu-all-detail`，非 `ops-resource-detail` type=`All`）；summary 走 `getOpsNpuAllSummary`（接口文档 v3 合并到 `/resource-summary` type=`All`），用 `to()` 包装：`const [err, res] = await to(getOpsNpuAllSummary({...}))`
- 行点击 `resourcePoolName` → 打开 `npu-resource-detail-modal.vue`
- 数值格式化复用 `config/time-range` 的公共 `formatRate` / `formatNum`，不重复实现本地方法

### 6. NPU 资源明细弹窗（回写修正）

**新组件**：`components/npu-resource-detail-modal.vue`
**Props**：`{ visible, params: { resourcePoolId, resourcePoolName, startDate, endDate } }`
**布局**：`el-dialog` + `base-table` 分页 + `npuResourceServerColumns`（**5 列**：资源名称 / 资源ip / 使用卡时 / 资源总卡时 / NPU使用率）
**数据源**：`getCommonDetail({category: 'ops-npu-all-server-detail', resourcePoolId(String), projectId, startDate, endDate})`
**格式化**：复用公共 `formatRate`

### 7. 列设置兼容与缓存 key 迁移（回写修正）

`column-setting` 组件按 prop 持久化勾选。新增列 `resourceQueueTime` / `npuAllRate` / `npuAllUsage` 的 `defaultShow` 见 3.2；删除列的 prop 在用户本地存储中失效后自动忽略。`prDetailColumns`（PR 明细）在 `prDuration` 后新增 `{ prop: 'resourceQueueTime', label: 'PR资源排队时长(min)-P90', minWidth: 134, sortable: true }`。

**回写修正**：仅靠 prop diff **不足以**兼容。本次删除 16 列 + 三级表头结构变动后，历史缓存的树形勾选结构与新 `mainTableColumns` 不兼容，会导致列显隐异常。补充两步处理：

1. `engineering-capability-view.vue` 的 `column-data-key` 由 `engineering-capability-columns` 改为 `engineeringCapabilityColumns`（换 key 等价于让老用户回到默认配置）
2. `src/App.vue` 挂载时 `localStorage.removeItem('engineering-capability-columns')` 清理旧 key，避免僵尸数据长期占用存储

### 8. 下钻 Tab 解析重构（回写新增）

**决策**：`resolveTabByColKey` 由字符串前缀/`includes` 判断改为构建期建立的声明式映射表。

**原因**：原实现 `if (colKey.includes('Cpu') || colKey.includes('Npu')) return 'resource'` 依赖 CPU/NPU 字符串特征。本次删除全部 CPU 列后该判断失效，且 `resourceQueueTime` 移入 prPipeline 分组后按名称无法归组。改为从 `mainTableColumns` 的分组结构反推，结构即真相：

```ts
const TAB_BY_GROUP: Record<string, DetailTab> = {
  nightlyPipeline: "nightly",
  resourceEnv: "resource",
  prPipeline: "pr",
};

function collectLeafProps(columns: ColumnProps[]): string[] {
  return columns.flatMap((col) =>
    col.children?.length ? collectLeafProps(col.children) : [col.prop],
  );
}

// 模块加载时一次性建 Map，避免每次点击重复遍历
const colKeyToTab = new Map<string, DetailTab>();
// ...
function resolveTabByColKey(colKey: string): DetailTab {
  return colKeyToTab.get(colKey) ?? "repo";
}
```

**副作用**：`resourceQueueTime` 归入 prPipeline 后，点击该列打开的是 PR 页签而非资源页签——与其语义一致。

### 9. dateParams 注入上下文（回写新增）

**决策**：`startDate` / `endDate` 由各组件 props 逐层透传改为通过 `E_C_DETAIL_PARAMS_KEY` 注入上下文提供（`ECDetailParamsContext` 含 `projectId` / `repoSummary` / `dateParams`）。

**原因**：新增 npu-resource-panel → npu-resource-detail-modal 两层组件后，日期参数需穿透 3 层。改注入后 `detail-panel` / `nightly-tab` / `repo-tab` / `resource-tab` / `runs-record-modal` 一并简化。

### 10. kpi-row 共享网格样式（回写新增）

**决策**：各 tab 组件内重复定义的 `.kpi-row-2` / `.kpi-row-4` / `.kpi-row-5` 局部样式上提到 `style.less`，统一为 `.kpi-row` 基类 + `.kpi-row--2` / `.kpi-row--5` 修饰类，并集中定义响应式断点（1280px → 3 列，768px → 2 列，480px → 1 列）。

**原因**：nightly-tab / repo-tab / resource-tab / npu-resource-panel 四处重复同一网格定义，且断点不一致。

### 11. 主表无 slot 单元格渲染修复（回写新增）

**问题**：`main-table.vue` 的链接列模板只有 `v-if`（有链接配置）和 `v-else`（显示"未配置数据，请联系李亮亮配置"tooltip）两个分支。有值但无链接配置的单元格会落到 `v-else`，显示误导性提示。

**修复**：插入 `v-else-if="row[col.key]"` 分支渲染纯文本，`v-else` 收窄为真正缺值时显示 `--` + tooltip。

### 12. 默认统计窗口收窄（回写新增）

`DEFAULT_TIME_RANGE` 由 `'30'` 改为 `'7'`，`time-range.test.ts` / `use-engineering-capability.test.ts` 同步更新断言。NPU 资源数据量大，30 天默认窗口首屏加载偏慢。

## 涉及文件

| 文件                                                                                      | 操作 | 说明                                                                                                                                                                                                                                                                                                                                                               |
| ----------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/views/dashboard/engineering-capability/config/columns.ts`                            | 修改 | 重构 `resourceColumns(prefix)`；抽取 `npuUsageColumns(prefix)`（含 `defaultShow` 收敛）；`prPipeline` 分组加 `resourceQueueTime`（PR执行时长之后）；overall 加 `npuAllUsage` + `npuAllRate`（NPU分配率之后）；新增 `npuResourceColumns`(4列)/`npuResourceServerColumns`(5列)；`prDetailColumns` 加 `resourceQueueTime`；精简 `resourceDetailColumns`；P90 标签标注 |
| `src/views/dashboard/engineering-capability/config/metric-tips.ts`                        | 修改 | 新增 `resourceQueueTime`（P90 说明）/ `npuUsageRate` tips；修正排队时长公式（去 `/60`）与分配率/使用率语义描述                                                                                                                                                                                                                                                     |
| `src/views/dashboard/engineering-capability/config/time-range.ts`                         | 修改 | `DEFAULT_TIME_RANGE` `'30'`→`'7'`；新增公共 `formatRate` / `formatNum`                                                                                                                                                                                                                                                                                             |
| `src/views/dashboard/engineering-capability/components/main-table.vue`                    | 修改 | `resourceRateCols=['overallNpuRate','npuAllRate']`；`resourceOtherCols` 首项 `resourceQueueTime`；`getLightStatus` 纳入 `npuAllRate`；无 slot 单元格加 `v-else-if` 纯文本分支                                                                                                                                                                                      |
| `src/views/dashboard/engineering-capability/components/resource-tab.vue`                  | 修改 | filter-bar 三选一（NPU资源最左，默认 NPU）；KPI 精简为 2 卡片；表格列精简；挂载 NPU 资源面板；onMounted 非 NPU 才 fetchSummary；fetchSummary 用 `to()`；复用公共 `formatNum`                                                                                                                                                                                       |
| `src/views/dashboard/engineering-capability/components/repo-tab.vue`                      | 修改 | 新增 `PR资源排队时长-P90` KPI 卡片；`kpi-row-4`→`kpi-row-5`；`PR执行时长` 标签加 `-P90`                                                                                                                                                                                                                                                                            |
| `src/views/dashboard/engineering-capability/components/nightly-tab.vue`                   | 修改 | 局部 kpi-row 网格样式移除，改用共享修饰类                                                                                                                                                                                                                                                                                                                          |
| `src/views/dashboard/engineering-capability/components/npu-resource-panel.vue`            | 新增 | NPU 资源页签主组件（5 卡片按"使用→总量→分配"排序 + 4 列表格 + 弹窗触发），category `ops-npu-all-detail`，summary 用 `to()`，复用公共 `formatRate` / `formatNum`                                                                                                                                                                                                    |
| `src/views/dashboard/engineering-capability/components/npu-resource-detail-modal.vue`     | 新增 | 服务器层级下钻弹窗（5 列表格），category `ops-npu-all-server-detail`，复用公共 `formatRate`                                                                                                                                                                                                                                                                        |
| `src/views/dashboard/engineering-capability/composables/use-engineering-capability.ts`    | 修改 | `resolveTabByColKey` 重构为 `TAB_BY_GROUP` 声明式映射 + 构建期 Map                                                                                                                                                                                                                                                                                                 |
| `src/views/dashboard/engineering-capability/engineering-capability-view.vue`              | 修改 | `column-data-key` 迁移为 `engineeringCapabilityColumns`                                                                                                                                                                                                                                                                                                            |
| `src/views/dashboard/engineering-capability/style.less`                                   | 修改 | `kpi-row` 基类 + `--2`/`--5` 修饰类 + 响应式断点集中定义                                                                                                                                                                                                                                                                                                           |
| `src/App.vue`                                                                             | 修改 | 挂载时清理旧列设置 localStorage key                                                                                                                                                                                                                                                                                                                                |
| `src/types/engineering-capability.ts`                                                     | 修改 | `ProjectRow` 加 `resourceQueueTime` / `npuAllRate` / `npuAllUsage`；新增 `NpuResourceRow`(resourcePoolId:string) / `NpuResourceServerRow` / summary 响应类型；`ResourcePipelineType` 扩展 'NPU'；`ECDetailParamsContext` 加 `dateParams`                                                                                                                           |
| `src/api/dashboard/engineering-capability.ts`                                             | 修改 | `getOpsResourceSummary` 泛型化；`getOpsNpuAllSummary` 复用之（`type='All'`，接口文档 v3 合并到 `/resource-summary`）                                                                                                                                                                                                                                               |
| `src/views/dashboard/engineering-capability/__tests__/columns.test.ts`                    | 修改 | 更新列数断言、新增列断言；回写：`npuAllUsage` 加入后断言滞后，已在 `225ea02` 同步（叶子列 25、`npuAllUsage` 改为正向断言）                                                                                                                                                                                                                                         |
| `src/views/dashboard/engineering-capability/__tests__/time-range.test.ts`                 | 修改 | `DEFAULT_TIME_RANGE` 断言改 `'7'`                                                                                                                                                                                                                                                                                                                                  |
| `src/views/dashboard/engineering-capability/__tests__/use-engineering-capability.test.ts` | 修改 | 默认时间范围断言改 `'7'`；资源页签解析用例由 `prCpuRate`（已删除）改为 `prNpuUsage`                                                                                                                                                                                                                                                                                |
| `/mock/npu-all-detail.ts`                                                                 | 新增 | vite-plugin-mock 单文件，rawResponse 按 category/type 分发（summary + 资源池列表 + 服务器列表），不入库                                                                                                                                                                                                                                                            |

## 风险 & 缓解

| 风险                                                         | 缓解                                                                                                 |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| 后端字段名与约定不一致（`resourceQueueTime` / `npuAllRate`） | 前端先 mock，字段名写入 ai_memory 与 archive，后端按约定对齐；接口文档 `npuAllRate` 语义修正为使用率 |
| 列设置用户已有勾选失效                                       | 回写修正：prop diff **不足**，实际靠 localStorage key 迁移 + 旧 key 清理兜底（见决策 7）             |
| 弹窗分页参数与 base-table 默认行为不一致                     | 复用 base-table 既有分页机制，initParams 传 resourcePoolId/startDate/endDate                         |
| mock 数据被误提交                                            | mock 采用 vite-plugin-mock `.ts` 文件，`.gitignore` 已含 `/mock` 规则                                |
| 列增删后测试断言失效（回写新增）                             | 已在 `225ea02` 同步断言。硬编码列数断言对频繁增删列的表脆弱，建议增删列与断言更新放同一 commit       |
| 按列名字符串特征归组失效（回写新增）                         | 决策 8 改为从列结构反推分组，结构即真相                                                              |

## 跨仓影响

无。改动仅限 `openlibing-ops-web` 业务仓与 `openlibing-docs` 文档仓。
