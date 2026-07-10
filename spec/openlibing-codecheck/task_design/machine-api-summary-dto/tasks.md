# machine-api-summary-dto 任务清单

## Phase 3: AI 编码交付

- [ ] **1. 新建 DTO**
  - 路径：`src/main/java/com/openlibing/codecheck/business/entity/QueryTaskSummaryMachineApiModel.java`
  - 字段：**与 `QuerySummaryModel` 完全一致**（25 个字段，含 `repoIds` 自定义 `getRepoIds` / `setRepoIds`）
  - 唯一区别：`pageNum` / `pageSize` **不带** `@NotNull` / `@Range`
  - Lombok：`@Data` + `@NoArgsConstructor` + `@AllArgsConstructor`
  - **其他字段**没有任何 Jakarta Validation 注解（与 `QuerySummaryModel` 保持一致）

- [ ] **2. 修改 MachineApiCheckboardController**
  - import 新 DTO + `org.springframework.beans.BeanUtils`
  - `getFullTaskResultSummaryForMachineApi` 形参改 `QueryTaskSummaryMachineApiModel`
  - 内部用 `BeanUtils.copyProperties(newDto, querySummaryModel)` 转换后调 delegate
  - `queryFullTaskResultSummary` 同上

- [ ] **3. 更新单元测试**
  - `MachineApiCheckboardControllerTest`：import + `new QuerySummaryModel()` → `new QueryTaskSummaryMachineApiModel()`（2 处）
  - `verify` 仍校验 delegate 调用（转换路径不可见，对外行为等价）

- [ ] **4. 更新 API 文档**
  - `doc/api/machine-api.md` 中两个接口段：
    - 请求体 `QuerySummaryModel` → `QueryTaskSummaryMachineApiModel`
    - 字段列表精简为实际使用字段（标 `可选` / `不校验`）

- [ ] **5. 编译 + 单测**
  - `mvn -o compile -DskipTests` 成功
  - `mvn -o test -Dtest='MachineApiCheckboardControllerTest'` 全绿
  - 同时跑 `CheckboardControllerTest` + `CheckboardDelegateImplTest` 确认 `getFullTaskResultSummary` 链路未受影响

- [ ] **6. 提交 commit**
  - 单次 commit，格式：
    ```
    fix(codecheck): relax machine-api summary interfaces to dedicated DTO

    * 新建 QueryTaskSummaryMachineApiModel，与 QuerySummaryModel 解耦
    * /machine-api/v1/codecheck/full/task/result/summary 与 /full-codecheck-record/list
      改用新 DTO，pageNum/pageSize 不再被强制校验
    * 内部用 BeanUtils.copyProperties 转 QuerySummaryModel 后调现有 delegate，
      不动 CheckboardController 与 delegate 接口
    * 同步更新单元测试与 doc/api/machine-api.md
    ```
  - 推到 fork 远端：`git push origin fix-machine-api-summary-dto`（HTTP+token）

## Phase 4: 业务 PR（用户决定）

- [ ] **7. 由用户创建 PR**
  - 用户告知时再确认 base 分支（默认与上次一致 `upstream/release_20260709`）
  - 标题：`fix(codecheck): relax machine-api summary interfaces to dedicated DTO`
  - 描述：变更摘要 + 关联 issue（若用户决定创建）+ 测试计划
  - 标签：`ai-assisted`

## Phase 5: 归档（用户触发）

- [ ] **8. docs 仓归档 PR**
  - 在 `openlibing-docs/spec/openlibing-codecheck/task_design/machine-api-summary-dto/` 下补 `archive.md`
  - 分支 `spec_openlibing-codecheck_machine-api-summary-dto`
  - PR 关联业务 issue（若存在）
