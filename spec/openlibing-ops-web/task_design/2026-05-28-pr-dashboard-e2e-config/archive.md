# PR看板E2E配置弹窗与指标字段 — 归档

## 需求概要

PR 门禁看板支持 E2E 目标时长配置入口，并在表格中新增 PR E2E 时长、流水线启动时长、合入时长、E2E 达标率等指标字段。

## 实现方案

### 弹窗改造

在 `scan-branch-config.vue` 中，使用 `el-tabs` 组件将弹窗拆分为两个页签：

- **代码量扫描分支配置**（`name="BRANCH"`）：保持原有展示分支选择逻辑不变
- **PR门禁E2E达标时长配置**（`name="TARGET"`）：使用 `el-input-number` 配置目标时长

页签 `name` 直接作为 API 的 `actionType` 参数，提交时按类型发送对应的配置数据。

数据模型独立：`BranchRowItem`（repoId/repoName/showBranch/branchList/loading）与 `E2ERowItem`（repoId/repoName/targetMinutes）完全分离。

### 表格字段

**prPipelineColumnData（Repo 层级）**：
| 插入位置 | 新增字段 |
|---------|---------|
| PR数量 后 | PRE2E时长（P50/P90/平均） |
| 门禁E2E执行(不含重试) 后 | 流水线启动时长（P50/P90/平均） |
| 备注 前 | 合入时长（P50/P90/平均）+ E2E达标率 |

**prInfoDetailColumn（PR 层级）**：
| 插入位置 | 新增字段 |
|---------|---------|
| 门禁是否成功 后 | PRE2E时长 |
| 门禁E2E执行(不含重试) 后 | PR流水线启动时长 |
| 备注 前 | PR合入时长 |

### API 适配

`POST /repo/branch/config/batch` 新增必填字段 `actionType`（`BRANCH`/`TARGET`）：

- `BRANCH` 模式：传 `repoId` + `showBranch`
- `TARGET` 模式：传 `repoId` + `targetMinutes`

## 变更文件

| 文件                                                             | 操作 | 说明                                                         |
| ---------------------------------------------------------------- | ---- | ------------------------------------------------------------ |
| `src/api/dashboard/open-source-project.ts`                       | 修改 | `RepoItem` 接口增加 `targetMinutes` 字段                     |
| `src/views/dashboard/open-source-project/scan-branch-config.vue` | 修改 | 弹窗分页签 + E2E 配置表格 + 独立数据模型                     |
| `src/views/dashboard/open-source-project/sub-table.vue`          | 修改 | 按钮名称"代码量扫描分支配置"→"配置"                          |
| `src/views/dashboard/open-source-project/columns/pr-columns.ts`  | 修改 | 新增 3 组列（PRE2E时长/流水线启动时长/合入时长 + E2E达标率） |

## 提交记录

| Hash      | 消息                                                                            |
| --------- | ------------------------------------------------------------------------------- |
| `8729cd5` | feat(dashboard): add PR E2E config tab and new metric columns                   |
| `3667865` | fix(dashboard): remove spaces and unit in new column labels                     |
| `617ebec` | fix(dashboard): separate branch/E2E data and add actionType to batch config API |
| `8cfe818` | refactor(dashboard): clean data types and simplify submit with actionType       |

## 业务 PR

- openlibing/openlibing-ops-web#52

## 验收结果

- [x] 按钮名称改为"配置"，弹窗含 2 个页签
- [x] E2E 时长配置页签可输入数字，调用 API 保存成功
- [x] Repo 级表格新增字段位置正确、带单位
- [x] PR 级明细表格新增字段位置正确、带单位
