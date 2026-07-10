# machine-api-summary-dto

## 需求背景

`MachineApiCheckboardController` 下两个机机接口当前直接复用 `QuerySummaryModel` 作为请求体：

- `POST /machine-api/v1/codecheck/full/task/result/summary` → `getFullTaskResultSummaryForMachineApi`
- `POST /machine-api/v1/full-codecheck-record/list` → `queryFullTaskResultSummary`

虽然这两个 Controller 没有加 `@Valid`，但**这两个接口最终调用的是与 `CheckboardController.getFullTaskResultSummary` 共用的同一个 delegate 方法**（`getFullTaskResultSummary` / `queryFullTaskResultSummary`），而这两个 delegate 方法内部依赖的 `commonOperation.getSummaryCriteria` / `fullSummaryOperation.getFullSummaryList` / `fullSummaryOperation.queryFullSummaryList` 都接受 `QuerySummaryModel`。

**问题**：机机接口的下游调用方（其他后端服务或定时任务）**按业务语义可能不传分页参数**。一旦后续给这两个接口补 `@Valid` 注解（出于安全加固或与 `CheckboardController` 行为对齐），`pageNum` / `pageSize` 上的 `@NotNull` + `@Range(min=1)` 校验会立即把所有不传分页的调用阻断。

**前置事件**：`fix-summary-pagination-and-repo-dropdown` 任务给 `QuerySummaryModel.pageNum/pageSize` 加了边界防护，导致本任务和 `file-contents-dto` 任务的接口均被波及。`file-contents-dto` 已通过新建 `QueryTaskFileContentModel` 解决单文件内容接口；本任务解决机机 summary 接口。

## 功能描述

### 做什么

1. 新建专用 DTO `QueryTaskSummaryMachineApiModel`（路径 `business/entity/`），字段与 `QuerySummaryModel` **完全一致**（25 个字段，含 `repoIds` 自定义 `getRepoIds` / `setRepoIds`），**`pageNum` / `pageSize` 仅作为可选 `Integer` 字段，不带任何 Jakarta Validation 注解**（这是与 `QuerySummaryModel` 的唯一区别）。
2. 修改 `MachineApiCheckboardController`：
   - 两个接口签名改为接受 `QueryTaskSummaryMachineApiModel`
   - 用 `BeanUtils.copyProperties` 将新 DTO 转换为 `QuerySummaryModel`，再调用现有 delegate 方法
   - 转换路径上**不**加 `@Valid`
3. 同步更新 `MachineApiCheckboardControllerTest`。
4. 同步更新 `doc/api/machine-api.md` 中这两个接口的请求体说明。
5. **不**改 `QuerySummaryModel` 现有字段与校验规则（`CheckboardController` 仍依赖 `@Valid` 加固）。
6. **不**改 delegate 接口与实现（`CheckboardController.getFullTaskResultSummary` 走的是同一条 delegate 链路，保持原状最安全）。

### 不做什么

- 不动 `QuerySummaryModel` 的 `pageNum` / `pageSize` 校验规则。
- 不动 `CheckboardController` 的 `@Valid` 注解。
- 不动 `CheckboardDelegate.getFullTaskResultSummary` / `queryFullTaskResultSummary` 的签名。
- 不动 MongoDB 持久化结构。
- 不改 `getSummaryCriteria` / `getFullSummaryList` / `queryFullSummaryList` 内部逻辑。
- 不动 `preprocessYellowApiParameters` 内部对 `QuerySummaryModel` 的 `setPageNum(1)` / `setPageSize(1)` 强制逻辑（黄区行为不变）。

## 验收标准

- [ ] `MachineApiCheckboardController.getFullTaskResultSummaryForMachineApi` 与 `queryFullTaskResultSummary` 接受 `QueryTaskSummaryMachineApiModel` 作为 `@RequestBody`。
- [ ] 两个方法不传 `pageNum` / `pageSize` 时不报 400，能正常进入 delegate 链路。
- [ ] 两个方法传 `pageNum` / `pageSize` 时（机机调用方想分页）能正常工作。
- [ ] `QueryTaskSummaryMachineApiModel` 字段与 `QuerySummaryModel` 完全一致（共 25 个字段：id、sourceBranch、uuid、taskId、userId、projectName、manifestBranch、mrId、mrUrl、startTime、endTime、sigName、repoUrl、repoName、summaryId、path、result、pageNum、pageSize、branchName、projectId、gitUrl、gitBranch、repoIds），仅 `pageNum` / `pageSize` 不带 `@NotNull` / `@Range` 注解。
- [ ] `CheckboardController.getFullTaskResultSummary` 行为完全不变（仍走 `@Valid` 校验，调用方传分页）。
- [ ] `MachineApiCheckboardControllerTest` 编译通过，2 个测试 case 仍断言通过。
- [ ] `doc/api/machine-api.md` 中 `/codecheck/full/task/result/summary` 与 `/full-codecheck-record/list` 的请求体说明更新为新 DTO 字段。

## 影响范围

- 仓库：openlibing-codecheck
- 模块：机机接口（`MachineApiCheckboardController`）
- 新增文件：
  - `src/main/java/com/openlibing/codecheck/business/entity/QueryTaskSummaryMachineApiModel.java`
- 修改文件：
  - `src/main/java/com/openlibing/codecheck/business/controller/MachineApiCheckboardController.java`
  - `src/test/java/com/openlibing/codecheck/business/controller/MachineApiCheckboardControllerTest.java`
  - `doc/api/machine-api.md`
- 无数据库 schema 变化
- 无外部接口契约破坏（仅入参模型显式细化；机机调用方原本不传或传错的字段从"被校验拦截"变为"按业务规则忽略"）
- 行为完全等价
