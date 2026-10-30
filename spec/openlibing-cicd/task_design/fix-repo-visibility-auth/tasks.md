# fix-repo-visibility-auth — 实现任务

## 进度: 已完成（PR !638 功能提交已合入）

> `09d7a2a6a` + `ae807f8c4`，10 files。

### 越权修复

- [x] Task 1: `PipelineControllerV2` — build/log、export、pre-commit 入参扩展
- [x] Task 2: `validateExportBuildJobInPipelineRun` + `isBuildJobReferencedInPipelineRun`
- [x] Task 3: `getBuildLog` / `exportBuildLog` 调用绑定校验
- [x] Task 4: `getPreCommitResult` 三元组；PR 评论内部调用同步
- [x] Task 5: `TestCaseResultMapper` + XML + `getTestReport` 传入 pipelineId

### 性能

- [x] Task 6: `buildJobPipelineRunBindCache` 30s；失败不缓存
- [x] Task 7: `PipelineServiceImplTest` 校验/缓存用例

### 验证与发布

- [x] Task 8: `PipelineControllerV2Test` 等单测；编译通过
- [ ] Task 9: **openlibing-cicd-web** 合入：build/log、build-log/export、pre-commit 透传 `pipelineId` / `pipelineRunId`（及 pre-commit 的 `projectId`）
- [ ] Task 10: **联合发布**：web 与 cicd 后端同窗口上线；生产冒烟（design.md 发布顺序 1–3）
- [ ] Task 11: 若曾「仅后端 !638 上生产」：记录是否已热修 web 或后端回滚（design.md §6.2）
- [ ] Task 12: **`pipeline_run_info` 归属校验**（或等价）：`validateExportBuildJobInPipelineRun` 前断言 `projectId+pipelineId+pipelineRunId` 三元组；单测/集成测「A 权限 + B 的 run+jobId」拒绝；若改走华为云隔离依赖，在 design §2.2 登记依赖并补负例联调
