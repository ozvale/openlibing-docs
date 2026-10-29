# design — npu-usage-pool-split

## 技术方案

单仓（`openlibing-ops-web`）前端改造，不新增路由、不新增外部依赖，复用既有 `base-table` / `base-kpi-card` / `kpi-row` / 服务器明细弹窗。

### 1. 类型定义（`src/types/engineering-capability.ts`）

- `ProjectRow`：删除 `npuAllRate` 与 `npuAllUsage`，新增 `npuAllAssignedHours` 以及三层使用率 `npuAssignedRate` / `npuSharedAssignedRate` / `npuExclusiveAssignedRate`（均 `number | null`）
- `OpsNpuAllSummaryResp`（resource-summary type=All 响应）三层 9 字段：

```ts
interface OpsNpuAllSummaryResp {
  totalNpuAssignedHours: number | null;
  totalNpuHours: number | null;
  npuAssignedRate: number | null;
  sharedNpuAssignedHours: number | null;
  sharedNpuHours: number | null;
  sharedNpuAssignedRate: number | null;
  exclusiveNpuAssignedHours: number | null;
  exclusiveNpuHours: number | null;
  exclusiveNpuAssignedRate: number | null;
}
```

- `NpuResourceRow`（资源池明细行）字段：`resourcePoolId: string` / `resourcePoolName` / `assignedNpuHours` / `totalNpuHours` / `npuAssignedRate`（数值字段均 `number | null`）

主表流水线消耗列 `overallNpuUsage` / `overallNpuAvg` 等保持不变，与 summary 的 assigned 字段互不影响。

### 2. 列配置（`config/columns.ts`）

`resourceColumns('overall')` 在「流水线整体资源」分组下：

- 保留 `overallNpuTotal`「NPU 总量(卡时)」（metricCode 10055）
- `npuAllUsage` → `npuAllAssignedHours`，label「NPU使用(占用)卡时」，`minWidth: 124`，`sortable`
- 删除 `npuAllRate`
- 新增三列（均可排序、按百分比渲染）：
  - `npuAssignedRate`：label「NPU使用率」、subLabel `(>=30%)`、`metricCode: 10045`、`minWidth: 142`、`defaultShow: true`
  - `npuSharedAssignedRate`：label「共享池NPU使用率」、`metricCode: 10072`、`minWidth: 142`、`defaultShow: false`
  - `npuExclusiveAssignedRate`：label「独立池NPU使用率」、`metricCode: 10073`、`minWidth: 142`、`defaultShow: false`

资源池表格列 `npuResourceColumns`（共享/独立共用）：

```ts
[
  { prop: "resourcePoolName", label: "资源池名称", minWidth: 120 },
  {
    prop: "npuAssignedRate",
    label: "NPU使用(占用)率",
    minWidth: 130,
    sortable: true,
  },
  {
    prop: "assignedNpuHours",
    label: "NPU使用(占用)卡时",
    minWidth: 140,
    sortable: true,
  },
  { prop: "totalNpuHours", label: "总卡时", minWidth: 120, sortable: true },
];
```

服务器明细弹窗列 `npuResourceServerColumns`：资源池名称(180) / 资源IP(140) / NPU使用(占用)率（`npuAssignedRate`，128）/ NPU使用(占用)卡时（`assignedNpuHours`，140）/ 总卡时(120)。

排序参数取自列 `prop`（`use-table` 的 `sortChange` 以 `sortField: prop` 上送），字段改名后排序自动使用新名，无需额外适配。

### 3. 阈值灯配置（`config/light-status.ts`）

```ts
export const resourceRateCols = [
  "npuAssignedRate",
  "npuSharedAssignedRate",
  "npuExclusiveAssignedRate",
];
const resourceLightCols = ["npuAssignedRate"];
```

三列均按百分比渲染、均可点击下钻到资源环境 Tab（由 `main-table.vue` 的 `rateCols` / `clickableCols` 自动覆盖）。阈值灯只对汇总使用率 `npuAssignedRate` 生效：`>=30%` 绿、`15%~30%` 黄、`<15%` 红；共享池 / 独立池使用率不亮灯（`getLightStatus` 返回 null）。

### 4. 下钻面板组件拆分

```text
components/
├── npu-resource-panel.vue       # 编排层：请求一次 summary，汇总卡片区 + 共享/独立两区块 + 服务器弹窗
└── npu-pool-section.vue         # 标题 + 3 卡片 + 资源池表格（共享/独立复用）
```

- `npu-resource-panel.vue`
  - `onMounted` 调 `getOpsNpuAllSummary`（`resource-summary` type=All）一次，结果存 `summary`
  - 模板：汇总区块（`.npu-summary-section.base-card`，仅 3 卡，`kpi-row--3`）→ `<npu-pool-section>` 共享 → `<npu-pool-section>` 独立
  - 汇总卡片绑定 `npuAssignedRate` / `totalNpuAssignedHours` / `totalNpuHours`
  - 持有服务器明细弹窗与当前行 `curRow`，子区块通过 `rowClick` 事件上抛
- `npu-pool-section.vue`（props）
  - `title: string`（共享资源池 / 独立资源池）
  - `category: string`（`ops-npu-shared-detail` / `ops-npu-exclusive-detail`）
  - `rate / usage / hours: number | null`（卡片值）
  - `initParams` computed：`{ category, projectId, ...dateParams }`，注入 `base-table` 的 `request-api = getCommonDetail`
  - emit `rowClick(row: NpuResourceRow)`
- 资源池名称以 `text-link` 插槽渲染，点击打开服务器明细弹窗；率列插槽用 `formatFloat(..., { isPercent: true })` 渲染

卡片展示顺序统一为：NPU使用(占用)率 → NPU使用(占用)卡时 → 总卡时。

三个区块（汇总卡片区 / 共享资源池 / 独立资源池）的根容器复用公共 `.base-card`（白底、1px `#e2e8f0` 描边、12px 圆角、20px 内边距）区分，相邻区块间距 16px（模块 `style.less`）。资源池区块内部的表格容器去掉自身描边，避免双层边框。

null 卡片值经 `formatNum` / `formatFloat` 的 `isValueEmpty` 兜底统一显示 `--`；无数据时 `base-table` 自然展示空态。

### 5. 服务器明细弹窗

`npu-resource-detail-modal.vue` 逻辑不变（category `ops-npu-all-server-detail` + `resourcePoolId`，行键 `resourceIp`），列文案、列顺序与字段随 `npuResourceServerColumns` 更新。

## 影响范围

| 范围          | 影响                                                                                                 |
| ------------- | ---------------------------------------------------------------------------------------------------- |
| 主表列数      | 叶子列 27 → 29（删 1：npuAllRate；增 3：三层使用率；改名 1：npuAllUsage → npuAllAssignedHours）      |
| 下钻 NPU 面板 | 由单层「全部资源池」改为汇总卡片区 + 共享/独立两个卡片+表格区块                                      |
| 明细字段      | 资源池/服务器明细率字段为 `npuAssignedRate`、使用卡时为 `assignedNpuHours`（含排序参数）             |
| 页面/路由     | 无变化                                                                                               |
| 其他 Tab      | PR / Nightly / 本地编码相关组件与接口不变                                                            |
| 接口          | 无新增接口，仅对齐已上线的字段与 category                                                            |
| 历史持久化    | 列设置 localStorage 中旧 `npuAllRate` / `npuAllUsage` 键失效（与已删除列处理方式一致），新键自动生成 |

## 风险与对策

- **字段同源不同名**：`ProjectRow.overallNpuUsage`（流水线消耗，保留）与 assigned 系列字段语义不同，重构类型时不要误删主表消耗列。
- **字段批量改名**：主表（`npuAllAssignedHours` / 三 rate）、summary（9 字段）、明细行（`assignedNpuHours` / `npuAssignedRate`）三处命名需与契约一致，列 `prop` 即上送的排序字段，漏改会导致列无值或排序失败。
- **两区块复用**：共享/独立均使用 `npu-pool-section.vue`，避免卡片/表格重复代码（符合样式与组件去重规则）。
- **空池项目**：独立池可能为 null，卡片与表格均需空态兜底，自测覆盖「仅共享池」项目。
