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

### 验证

- [x] Task 8: `PipelineControllerV2Test` 等单测；编译通过
- [ ] Task 9: 前端透传 pipelineId、pipelineRunId
