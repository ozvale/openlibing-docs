# NPU 资源视图与主表格资源列调整

## 需求背景

工程能力运营看板的资源环境模块当前展示 24 列（PR/Nightly/整体 各 8 列），信息密度过高且 CPU 维度占比过大；同时缺少 NPU 资源池级别的使用情况视图，难以观测 NPU 资源实际占用。需精简主表格列、突出 NPU 维度，并新增 NPU 资源专门视图。

关联业务 Issue: https://gitcode.com/openlibing/openlibing-ops-web/issues/31

## 功能描述

### 1. 主表格列调整（资源环境区）

**新增**：

- PR流水线资源 → `PR资源排队时长(min)`（prop: `resourceQueueTime`）
- 流水线整体资源 → `NPU使用率`（prop: `npuAllRate`，复用后端全量资源字段）

**删除**（共 18 列）：

- PR流水线资源：CPU总量、NPU总量、CPU分配率、NPU分配率、CPU消耗、CPU平均消耗
- Nightly流水线资源：CPU总量、NPU总量、CPU分配率、NPU分配率、CPU消耗、CPU平均消耗
- 流水线整体资源：CPU分配率、CPU总量、CPU消耗、CPU平均消耗

**调整后保留列**：

- PR流水线资源：NPU消耗、NPU平均消耗 → 2 列（`PR资源排队时长` 归入 PR流水线区，非资源环境区）
- Nightly流水线资源：NPU消耗、NPU平均消耗 → 2 列
- 流水线整体资源：NPU消耗、NPU平均消耗、NPU总量、NPU分配率、NPU使用(卡时)(新)、NPU使用率(新) → 6 列

> 回写：`PR资源排队时长(min)-P90` 实际落在 `prPipeline` 分组（PR执行时长之后），不在 `resourceEnv/prResource` 下；整体资源额外保留 `npuAllUsage`（NPU使用(卡时)），故主表叶子列共 **25 列**。

**列默认显隐（回写）**：并非所有新增列都默认显示，`defaultShow` 已按信息密度收敛：

| 列                                     | defaultShow  | 说明                                                |
| -------------------------------------- | ------------ | --------------------------------------------------- |
| `{prefix}NpuUsage`（NPU 消耗(卡时)）   | 否           | 三个资源区一致，需列设置手动开启                    |
| `{prefix}NpuAvg`（NPU 平均消耗(卡时)） | 仅 `pr` 为是 | `npuUsageColumns` 内 `const show = prefix === 'pr'` |
| `overallNpuTotal`（NPU 总量(卡时)）    | 否           | —                                                   |
| `overallNpuRate`（NPU 分配率）         | 否           | 回写：初期为是，后收敛为否                          |
| `npuAllUsage`（NPU使用(卡时)）         | 是           | 回写新增列                                          |
| `npuAllRate`（NPU使用率）              | 是           | —                                                   |
| `resourceQueueTime`（PR资源排队时长）  | 是           | 位于 prPipeline 分组                                |

### 2. 下钻页面（资源环境页签）调整

**filter-bar**：三选一按钮，NPU资源 移到最左侧（默认选中），顺序：NPU资源 / PR / Nightly

**PR/Nightly 页签**：

- KPI 卡片：删除 CPU消耗 / CPU平均消耗 / CPU总量 / NPU总量（保留 NPU消耗 / NPU平均消耗 2 个）
- 明细表格列：删除 CPU消耗 / CPU平均消耗（保留 流水线名称 / NPU消耗 / NPU平均消耗 3 列）

**NPU资源页签**（新增）：

- 5 个 KPI 卡片，回写后的顺序为「使用 → 总量 → 分配」：**NPU使用率 / NPU使用卡时 / NPU总量 / NPU分配率 / NPU分配卡时**
  - 字段依次为 `npuRate` / `totalNpuUsage` / `totalNpuHours` / `overallNpuRate` / `overallNpuUsage`
  - 接口文档 v3：移除独立 `/ops-overview/npu-all-summary`，合并到 `/ops-overview/resource-summary`（type=`All`），返回上述 5 字段，卡片全部有实值（不再有 `--` 占位）
- 资源表格（4 列，资源池层级）：资源池名称、资源池使用卡时、资源池总卡时、NPU使用率
  - 接口：`common/detail` category=**`ops-npu-all-detail`**（回写：非 `ops-resource-detail` type=`All`）
  - 点击资源池名称下钻弹窗
- 下钻弹窗（70% 宽，5 列服务器层级）：资源池名称、资源IP、使用卡时、资源总卡时、NPU使用率
  - 接口：`common/detail` category=`ops-npu-all-server-detail`，参数 `resourcePoolId`(String) + `projectId`

### 3. PR 明细表格扩展

`prDetailColumns` 在 `PR执行时长(min)-P90` 之后新增 `PR资源排队时长(min)-P90` 列（prop: `resourceQueueTime`），对应接口 `ops-repo-detail` 新增字段。

### 4. 代码仓页签 KPI 扩展（回写新增）

`repo-tab.vue` 非本地编码态新增「PR资源排队时长-P90」KPI 卡片（`repoSummary.resourceQueueTime`），KPI 行由 4 列改为 5 列。同时把 `PR执行时长` 卡片标签改为 `PR执行时长-P90`。

### 5. P90 语义标注统一（回写新增）

分位数指标在标签上显式标注 `-P90`，避免用户误读为均值。覆盖范围：

- 主表：`PR执行时长-P90`、`PR资源排队时长(min)-P90`
- PR 明细表：`PR执行时长(min)-P90`、`PR资源排队时长(min)-P90`
- repo-tab KPI：`PR执行时长-P90`、`PR资源排队时长-P90`

### 6. 指标说明修正（回写新增）

- `resourceQueueTime` 计算公式修正：`P90构建排队时长 + P90测试排队时长`，取项目下各仓库 MAX（**删除原公式中错误的 `/ 60`**，两个分量已是分钟）
- 资源分配率：公式名由「使用率」更正为「分配率」，含义补充"描述资源池内的NPU资源是否闲置"
- NPU 使用率：含义补充"描述流水线占用的NPU资源是否充分使用，申请规格是否过大"

### 7. 列设置缓存 key 迁移（回写新增）

列设置 localStorage key 由 `engineering-capability-columns` 改为 `engineeringCapabilityColumns`，并在 `App.vue` 挂载时 `localStorage.removeItem('engineering-capability-columns')` 清理旧 key——列结构变动后历史缓存与新实现不兼容，仅靠 prop diff 无法完全兼容。

## 不做

- 不改动其他页签（本地编码 / PR流水线 / Nightly流水线）
- 不改动主表格其他区（开源组件 / 本地编码 / 本地构建 / PR流水线 / Nightly流水线）
- 不改动后端接口实现（前端先 mock，后端按约定字段名对齐）

## 验收标准

- [x] 主表格按需求增删列，列设置按 prop diff 兼容用户已有勾选（回写：叠加 localStorage key 迁移 + 旧 key 清理）
- [x] 资源环境页签 filter-bar 三选一切换正常（NPU资源 / PR / Nightly 互斥覆盖原内容）
- [x] NPU资源页面 5 卡片 + 4 列资源池表格 + 行点击下钻 5 列服务器弹窗正常
- [x] 弹窗 70% 宽、分页
- [x] mock 数据放 `/mock` 文件夹且不入库（保持 .gitignore 规则）
- [x] 组件文件名 kebab-case，页级组件 ≤400 行
- [x] P90 指标标签统一标注 `-P90`（主表 / PR明细 / repo-tab KPI）
- [x] **相关单元测试更新并通过** — 回写：`225ea02` 同步 `columns.test.ts` 断言后，本需求 3 个测试文件 / 29 个用例全通过

## 影响范围

- 业务仓：`openlibing-ops-web`
- 分支：`feat/engineering-capability-npu-resource`（领先 `origin/main` 21 个 commit）
- 模块：`src/views/dashboard/engineering-capability/`
- 主要文件：
  - `config/columns.ts`（主表格列定义、`npuUsageColumns` 工厂、resourceDetailColumns、prDetailColumns、npuResourceColumns、npuResourceServerColumns）
  - `config/metric-tips.ts`（新增指标 tips + 公式/含义修正）
  - `config/time-range.ts`（`DEFAULT_TIME_RANGE` 30→7；公共 `formatRate` / `formatNum`）
  - `components/main-table.vue`（resourceRateCols / resourceOtherCols / getLightStatus 调整 + 无 slot 单元格纯文本渲染修复）
  - `components/resource-tab.vue`（filter-bar 三选一、卡片精简、NPU 资源页面切换）
  - `components/repo-tab.vue`（新增 PR资源排队时长-P90 KPI，kpi-row 4→5）
  - `components/npu-resource-panel.vue`（新增）
  - `components/npu-resource-detail-modal.vue`（新增）
  - `components/nightly-tab.vue`（kpi-row 样式统一）
  - `composables/use-engineering-capability.ts`（`resolveTabByColKey` 重构为声明式映射表）
  - `engineering-capability-view.vue`（列设置缓存 key 迁移）
  - `style.less`（`kpi-row` 网格布局 + 响应式断点上提）
  - `src/App.vue`（清理旧列设置 localStorage key）
  - `types/engineering-capability.ts`（新增类型 + `dateParams` 注入上下文）
  - `api/dashboard/engineering-capability.ts`（`getOpsResourceSummary` 泛型化 + `getOpsNpuAllSummary`）
  - `__tests__/columns.test.ts` / `time-range.test.ts` / `use-engineering-capability.test.ts`（测试更新）
  - `/mock/npu-all-detail.ts`（mock 数据，不入库）
- 文档仓：`openlibing-docs/spec/openlibing-ops-web/task_design/npu-resource-view/`

## 实现偏差说明（回写）

实际实现与初始设计的关键偏差（按接口文档 v2 调整）：

| 维度                 | 初始设计                             | 实际实现                                                                     | 原因                                                              |
| -------------------- | ------------------------------------ | ---------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| PR排队时长字段名     | `prResourceQueueTime`                | `resourceQueueTime`                                                          | 后端实际字段名为 `resourceQueueTime`，主表与 ops-repo-detail 共用 |
| NPU使用率字段名      | `overallNpuUsageRate`                | `npuAllRate`                                                                 | 后端实际字段名为 `npuAllRate`，与主表全量资源指标共用             |
| NPU卡片接口路径      | `/ops-overview/npu-resource-summary` | `/ops-overview/resource-summary`（type=`All`）                               | 接口文档 v3 移除独立 summary 接口，合并到 resource-summary        |
| NPU卡片响应字段      | 5 字段                               | 5 字段（totalNpuUsage/totalNpuHours/npuRate/overallNpuUsage/overallNpuRate） | 接口文档 v3 补齐整体NPU消耗/分配率，卡片全部有实值                |
| NPU资源表格 category | `ops-npu-resource-list`              | **`ops-npu-all-detail`**                                                     | 后端最终提供独立 category，未复用 ops-resource-detail             |
| NPU资源表格列数      | 6 列（含资源名称/ip）                | 4 列（资源池层级）                                                           | 接口文档 v2 改为资源池层级聚合                                    |
| 下钻弹窗 category    | `ops-npu-resource-daily`             | `ops-npu-all-server-detail`                                                  | 接口文档 v2 改为服务器层级（非按天）                              |
| 下钻弹窗列数         | 6 列（按天明细）                     | 5 列（服务器明细）                                                           | 接口文档 v2 改为服务器层级                                        |
| 下钻弹窗参数         | `resourceId`                         | `resourcePoolId`(String)                                                     | resourcePoolId 为 String 类型（避免 JS 大整数精度丢失）           |
| NPU资源按钮位置      | 最右侧                               | 最左侧（默认选中）                                                           | 用户要求                                                          |
| prDetailColumns      | 无 resourceQueueTime                 | 新增资源排队时长列                                                           | 接口文档 v2 新增 ops-repo-detail 字段                             |
| mock 文件            | 3 个 json                            | 1 个 ts（npu-all-detail.ts）                                                 | vite-plugin-mock 要求 .ts 文件                                    |
| 错误处理             | try/catch                            | `await to()` 包装器                                                          | 与项目其他接口请求风格一致                                        |
| formatRate           | 本地实现                             | 复用 `config/time-range` 公共方法                                            | 避免重复代码                                                      |
| formatNum            | resource-tab 本地实现                | 抽到 `config/time-range` 公共方法并复用                                      | 避免 panel / resource-tab 重复实现                                |
| getOpsNpuAllSummary  | 独立 http.post                       | 复用泛型化的 `getOpsResourceSummary`                                         | 同一端点，消除重复 endpoint 字面量                                |

### 第二轮回写（2026-08-06，覆盖 `1338009` 之后的 commit）

| 维度                      | 先前文档说法                                     | 当前实现                                                        | 原因 / 来源 commit                                            |
| ------------------------- | ------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------- |
| `npuAllUsage` 列          | 明确"不展示"                                     | 已作为整体资源列展示（`NPU使用(卡时)`，`defaultShow: true`）    | `4b1a07b` 补充绝对值维度，与使用率互为参照                    |
| 主表叶子列总数            | 24                                               | **25**                                                          | `npuAllUsage` 新增；`columns.test.ts` 断言已在 `225ea02` 同步 |
| `PR资源排队时长` 所在分组 | 资源环境 → PR流水线资源                          | **PR流水线（prPipeline）分组**，PR执行时长之后                  | 该指标语义属流水线效率而非资源用量                            |
| NPU 面板卡片顺序          | 使用卡时/总卡时/分配率/整体NPU消耗/整体NPU分配率 | **使用率/使用卡时/NPU总量/分配率/分配卡时**（"使用→总量→分配"） | `70c73cb` 按阅读顺序重排 + 图标调整                           |
| NPU 面板表格列标签        | 资源池/资源使用卡时/资源总卡时                   | 资源池名称/资源池使用卡时/资源池总卡时                          | 明确层级归属                                                  |
| `defaultShow` 收敛        | 新增列一律 `true`                                | NPU消耗全否；NPU平均消耗仅 `pr` 为是；NPU分配率转否             | `4b1a07b` / `a58a01d` 控制默认信息密度                        |
| repo-tab KPI              | 未提及                                           | 新增 `PR资源排队时长-P90` 卡片，kpi-row 4→5                     | `6b35a75`                                                     |
| P90 标签标注              | 未提及                                           | 主表/PR明细/repo-tab KPI 统一加 `-P90` 后缀                     | `4b1a07b` / `1326705` 防止误读为均值                          |
| 排队时长计算公式          | `(P90构建 + P90测试) / 60`                       | `P90构建 + P90测试`（去掉 `/60`）                               | `4b1a07b` 修正：两分量已是分钟，除 60 是错误                  |
| 分配率 tip                | 公式写"使用率 ="                                 | 公式写"分配率 ="，含义补充"资源池内NPU是否闲置"                 | `4b1a07b` 修正命名与语义                                      |
| 列设置缓存 key            | 仅靠 prop diff 兼容                              | key 改 `engineeringCapabilityColumns` + App.vue 清理旧 key      | `70c73cb`：列结构变动后旧缓存不兼容，diff 不足以兼容          |
| `resolveTabByColKey`      | 字符串前缀/`includes('Cpu')` 判断                | 声明式 `TAB_BY_GROUP` 映射 + 递归收集叶子列，构建期建 Map       | `6b35a75`：CPU 列已删除，前缀判断失效且重复遍历               |
| `dateParams` 传递         | 各组件 props 逐层透传                            | 由 `E_C_DETAIL_PARAMS_KEY` 注入上下文统一提供                   | `fd9f0c7` 消除多层透传                                        |
| `DEFAULT_TIME_RANGE`      | `'30'`                                           | `'7'`                                                           | `28380a9` 同步单测；默认窗口收窄                              |
| `kpi-row` 样式            | 各组件内 `kpi-row-N` 局部定义                    | 上提到 `style.less`，`kpi-row--2` / `--5` 修饰类 + 响应式断点   | `8762ebf` 消除 4 个组件的重复网格定义                         |
| 无 slot 单元格渲染        | 未提及                                           | 新增 `v-else-if="row[col.key]"` 渲染纯文本                      | `dfba8ab`：原逻辑让有值单元格误显"未配置数据"提示             |
