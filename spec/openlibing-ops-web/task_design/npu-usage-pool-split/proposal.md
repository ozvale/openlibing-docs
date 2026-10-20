# npu-usage-pool-split

## 需求背景

工程能力运营看板（`engineering-capability`）当前 NPU 相关指标以「NPU利用率」单一指标呈现，资源池明细只有「全部资源池」单一层级，无法区分共享池与独立池的占用情况。

需求 Issue：[#207](https://gitcode.com/openlibing/openlibing-ops/issues/207)。接口契约已调整为「NPU使用(占用)率」口径，使用（占用）相关字段统一为 assigned 词根命名；资源池明细拆分为「汇总 / 共享 / 独立」三个层级，前端需对齐新的接口字段与展示结构。

## 功能描述

### 1. 主表字段调整（仅限「资源环境 → 流水线整体资源」分组）

| 变更             | 字段                                  | 展示文案          | 说明                                                                                                             |
| ---------------- | ------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------- |
| 删除             | `npuAllRate`                          | NPU利用率         | 新契约不再返回该字段，列移除                                                                                     |
| 改名             | `npuAllUsage` → `npuAllAssignedHours` | NPU使用(占用)卡时 | 字段随新口径改名，列宽 124，可排序                                                                               |
| 新增             | `npuAssignedRate`                     | NPU使用率         | 汇总使用率，metricCode `10045`、subLabel `(>=30%)`、列宽 142、默认展示；阈值灯 `>=30%` 绿、15%~30% 黄、`<15%` 红 |
| 新增（默认隐藏） | `npuSharedAssignedRate`               | 共享池NPU使用率   | metricCode `10072`，列宽 142，`defaultShow: false`，不亮灯，可点击下钻                                           |
| 新增（默认隐藏） | `npuExclusiveAssignedRate`            | 独立池NPU使用率   | metricCode `10073`，列宽 142，`defaultShow: false`，不亮灯，可点击下钻                                           |

「PR流水线资源」「Nightly流水线资源」两组列不做任何改动；`overallNpuUsage` / `overallNpuAvg` / `overallNpuTotal` 等流水线消耗列保持不变。

### 2. 下钻面板「资源环境 → NPU资源」拆分为三部分

页面自上而下纵向堆叠三个区块，卡片数据来自同一次 `resource-summary`（type=All）响应：

1. **汇总（仅卡片）**：3 张 KPI 卡（展示顺序：率 → 卡时 → 总卡时）
   - NPU使用(占用)率 `npuAssignedRate` / NPU使用(占用)卡时 `totalNpuAssignedHours` / 总卡时 `totalNpuHours`
2. **共享资源池（卡片 + 表格）**
   - 卡片：NPU使用(占用)率 `sharedNpuAssignedRate` / NPU使用(占用)卡时 `sharedNpuAssignedHours` / 总卡时 `sharedNpuHours`
   - 表格：`POST /common/detail`，category = `ops-npu-shared-detail`
3. **独立资源池（卡片 + 表格）**
   - 卡片：NPU使用(占用)率 `exclusiveNpuAssignedRate` / NPU使用(占用)卡时 `exclusiveNpuAssignedHours` / 总卡时 `exclusiveNpuHours`
   - 表格：category = `ops-npu-exclusive-detail`
   - 项目无独立池时 `exclusive*` 为 null，卡片显示 `--`、表格为空

- 两个资源池表格列结构一致，列顺序与文案：资源池名称 / NPU使用(占用)率（`npuAssignedRate`）/ NPU使用(占用)卡时（`assignedNpuHours`）/ 总卡时（`totalNpuHours`），列宽依次 120 / 130 / 140 / 120，后三列可排序。
- 点击资源池名称打开服务器明细弹窗（category `ops-npu-all-server-detail`，按 `resourcePoolId` 查询），弹窗列顺序与文案：资源池名称(180) / 资源IP(140) / NPU使用(占用)率(128) / NPU使用(占用)卡时（`assignedNpuHours`，140）/ 总卡时(120)。
- 率值均为 0-1 小数，沿用 `formatFloat(..., { isPercent: true })` 展示；卡时为空时显示 `--`。

## 验收标准

- [ ] 主表「流水线整体资源」下不再出现「NPU利用率」列；「NPU使用率」列默认展示，阈值灯为 `>=30%` 绿、15%~30% 黄、`<15%` 红，点击可下钻到资源环境 Tab
- [ ] 主表「共享池NPU使用率」「独立池NPU使用率」列默认隐藏，可通过列设置开启，率值按百分比展示，不亮阈值灯，点击可下钻到资源环境 Tab
- [ ] 主表「NPU使用(占用)卡时」对应字段 `npuAllAssignedHours`，文案正确；PR/Nightly 两组资源列与改造前完全一致
- [ ] 下钻 NPU 资源页依次展示「汇总 / 共享资源池 / 独立资源池」三区块，区块均有标题且各有边框卡片容器区分，区块间距 16px
- [ ] 汇总区块仅 3 卡片，无表格；共享、独立区块各 3 卡片 + 1 表格；卡片顺序为 NPU使用(占用)率 → NPU使用(占用)卡时 → 总卡时
- [ ] 两个资源池表格请求 category 分别为 `ops-npu-shared-detail` / `ops-npu-exclusive-detail`，列文案、字段（含 `assignedNpuHours`）与顺序一致，排序正常
- [ ] 无独立池的项目，独立区块卡片显示 `--`、表格无记录，页面无报错
- [ ] 服务器明细弹窗可从任一资源池表格打开，列顺序、文案与字段为新口径
- [ ] `type-check`、lint 无新增问题
