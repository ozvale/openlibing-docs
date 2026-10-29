# tasks — npu-usage-pool-split

## 实现步骤

- [x] 1. 更新类型 `src/types/engineering-capability.ts`
  - [x] 1.1 `ProjectRow`：删 `npuAllRate`、`npuAllUsage`，增 `npuAllAssignedHours` 与 `npuAssignedRate` / `npuSharedAssignedRate` / `npuExclusiveAssignedRate`
  - [x] 1.2 `OpsNpuAllSummaryResp`：三层 9 字段（`totalNpuAssignedHours` / `sharedNpuAssignedHours` / `exclusiveNpuAssignedHours` 等）
  - [x] 1.3 `NpuResourceRow`：`resourcePoolId` / `resourcePoolName` / `assignedNpuHours` / `totalNpuHours` / `npuAssignedRate`
- [x] 2. 更新列配置 `config/columns.ts`
  - [x] 2.1 `resourceColumns('overall')`：删 npuAllRate、npuAllUsage 改名 `npuAllAssignedHours`（124）、新增三使用率列（142，含 metricCode/默认显隐）
  - [x] 2.2 `npuResourceColumns`：资源池名称(120) / `npuAssignedRate`(130) / `assignedNpuHours`(140) / `totalNpuHours`(120)
  - [x] 2.3 `npuResourceServerColumns`：资源池名称(180) / 资源IP(140) / `npuAssignedRate`(128) / `assignedNpuHours`(140) / `totalNpuHours`(120)
- [x] 3. 更新 `config/light-status.ts`：`resourceRateCols` 改为三个 assigned 使用率字段；仅 `npuAssignedRate` 亮灯（绿灯 `>=30%`、黄灯 15%~30%、红灯 `<15%`），共享/独立不亮灯
- [x] 4. 新增组件 `components/npu-pool-section.vue`：标题 + 3 KPI 卡 + base-table，props/emit 按设计
- [x] 5. 重构 `components/npu-resource-panel.vue`：汇总卡片区 + 共享/独立两 section + 服务器弹窗
- [x] 6. 区块容器统一使用公共 `.base-card`，区块间距 16px，模块 `style.less` 去重
- [x] 7. 质量验证：`npm run type-check`、`npm run lint`

## 验证方式

- 类型：vue-tsc type-check 通过；lint 无新增问题
- 手动自测（用户）：选含独立池项目（如 vllm-ascend）与仅共享池项目，核对主表新列名/字段、下钻三区块（汇总仅卡片、共享/独立卡片+表格，含 `assignedNpuHours` 列排序）、空态、服务器弹窗
