# file-contents-dto 任务清单

## Phase 3: AI 编码交付

- [ ] **1. 新建 DTO**
  - 路径：`src/main/java/com/openlibing/codecheck/business/entity/QueryTaskFileContentModel.java`
  - 字段：`projectName`、`projectId`、`repoUrl`、`repoName`、`manifestBranch`、`path`、`summaryId`
  - Lombok：`@Data` + `@NoArgsConstructor` + `@AllArgsConstructor`
  - **不带任何 Jakarta Validation 注解**

- [ ] **2. 修改 CheckboardController**
  - `getTaskFileContents` 形参由 `@RequestBody @Valid QuerySummaryModel` 改为 `@RequestBody QueryTaskFileContentModel`（去掉 `@Valid`，因新 DTO 无校验）
  - 顺手提交之前遗留的 `getIncTaskSum` `@Deprecated` 标记 + INFO 日志

- [ ] **3. 修改 CheckboardDelegate 接口**
  - `getTaskFileContents(QuerySummaryModel)` → `getTaskFileContents(QueryTaskFileContentModel)`

- [ ] **4. 修改 CheckboardDelegateImpl**
  - 形参与方法体中类型替换：`QuerySummaryModel` → `QueryTaskFileContentModel`
  - 业务逻辑保持不变

- [ ] **5. 修改 CodePlateHelper**
  - `getRepoFileContents(String, QuerySummaryModel, String)` → `getRepoFileContents(String, QueryTaskFileContentModel, String)`

- [ ] **6. 修改 GiteePlate**
  - `getRepoFileContents` 形参类型替换 + 方法体内 `querySummaryModel.getXxx()` 调用保持（`QueryTaskFileContentModel` 字段名与 `QuerySummaryModel` 对齐）
  - 同步更新 Javadoc

- [ ] **7. 修改 GitCodePlate**
  - 同 #6

- [ ] **8. 更新单元测试**
  - `CheckboardControllerTest`：import + 形参类型
  - `CodePlateHelperTest`：import + `new QuerySummaryModel()` → `new QueryTaskFileContentModel()`
  - `GiteePlateTest`：同上
  - `GitCodePlateTest`：同上

- [ ] **9. 更新 API 文档**
  - `doc/api/checkboard.md` 中 `/codecheck/full/task/file/contents` 段：
    - 请求体 `QuerySummaryModel` → `QueryTaskFileContentModel`
    - 字段列表替换为 7 字段精简版
    - 移除 `pageNum` / `pageSize` / `branchName` / `gitUrl` / `gitBranch` / `repoIds` / `id` / `sourceBranch` / `uuid` / `taskId` / `userId` / `mrId` / `mrUrl` / `startTime` / `endTime` / `sigName` / `result` 等

- [ ] **10. 本地编译验证**
  - 运行 `mvn -pl . compile -DskipTests`（或 IDE 编译）确认无报错
  - 重点关注 `CheckboardDelegateImpl` 中 `getCriteria` / `getRepoSummary` 等仍引用 `QuerySummaryModel` 的代码**未受影响**

- [ ] **11. 提交 commit**
  - 单次 commit，格式：
    ```
    fix(codecheck): split file-contents interface into dedicated DTO

    * 新建 QueryTaskFileContentModel，与 QuerySummaryModel 解耦
    * /codecheck/full/task/file/contents 改用新 DTO，前端不再被 pageNum/pageSize 强制校验阻断
    * 同步更新调用链与单元测试
    * 顺手把 getIncTaskSum 标记为 @Deprecated 并加 INFO 日志

    Refs openlibing/openlibing-codecheck#138
    ```
  - 推到 fork 远端：`git push origin fix-file-contents-dto`（HTTP+token，**不要 SSH**）

## Phase 4: 业务 PR

- [ ] **12. 创建 PR**
  - base：`upstream/release_20260709`
  - compare：`yanzhaohong/openlibing-codecheck:fix-file-contents-dto`
  - 标题：`fix(codecheck): split file-contents interface into dedicated DTO`
  - 描述：变更摘要 + 关联 issue #138 + 测试计划
  - 标签：`ai-assisted`（创建后用 `gitcode pr edit` 补打）

## Phase 5: 归档（用户触发）

- [ ] **13. docs 仓归档 PR**
  - 在 `openlibing-docs/spec/openlibing-codecheck/task_design/file-contents-dto/` 下补 `archive.md`
  - 分支 `spec_openlibing-codecheck_file-contents-dto`
  - PR 关联业务 issue #138
