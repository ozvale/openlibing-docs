# gitcode-pipeline-commit-status — 实现任务

## 进度: 14/14 complete

### DTO / VO / 事件对象

- [x] Task 1: 在 `PipelineParamDTO` 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch` / `userName` / `pipelineName`
- [x] Task 2: 在 `PipelineStatusUpdateMessage` 新增同样 5 个字段，确保 MQ 反序列化可还原
- [x] Task 3: 在 `PrStartPipelineVo` 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch`
- [x] Task 4: 在 `PullRequestEvent` 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch`，GitCode 路径下填充
- [x] Task 5: 在 `NoteEvent` 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch`，GitCode 路径下填充
- [x] Task 6: 新增 `GitCodePipelineStatusDTO`（含嵌套 `PipelineDetail`），字段命名与 `design.md` "API 调用细节" 严格一致

### 事件处理 / Consumer

- [x] Task 7: `PipelineStartEventHandler` 的 PR open / update / note 三处填充 `sourceBranch` / `userName` / `pipelineName`，并在 `reflashPipelineInfo` 透传到 `PipelineParamDTO`
- [x] Task 8: `PipelineStatusUpdateConsumer.buildPipelineParamFromMessage` 透传 5 个新增字段；DB fallback 路径保留兼容

### 核心 Service 改动

- [x] Task 9: `PipelineServiceImpl` 新增 `mapToGitCodeCommitStatus`，覆盖全部分支
- [x] Task 10: `PipelineServiceImpl` 新增 `pushGitCodeCommitStatus(param, pipelineStatus)`，内部按 `projectId` 查 `hwProjectId` / `region`，按 `design.md` 拼接 URL / Header / Body / `pipeline_detail` JSON
- [x] Task 11: `recordQueuedPipeline` 中调用 `pushGitCodeCommitStatus(param, "QUEUED")` 推送 `pending`
- [x] Task 12: `recordPipelineInfo` 非排队路径在拿到 `pipelineRunDetail` 后调用 `pushGitCodeCommitStatus(param, pipelineRunDetail.getStatus())` 推送对应状态

### 测试

- [x] Task 13: 扩展 `PipelineParamDtoBuilder` 链式构造方法覆盖新增 5 个字段
- [x] Task 14: `PipelineServiceImplTest` 新增/调整测试：`mapToGitCodeCommitStatus` 全分支 + `pushGitCodeCommitStatus` 4 类场景（跳过/成功/失败/异常）+ URL/Header/Body 完整断言
