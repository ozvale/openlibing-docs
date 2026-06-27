# gitcode-pipeline-commit-status

## 需求背景

openLiBing 配置的流水线需要在 GitCode PR 的检查（Check）中正常呈现流水线状态，使开发者能在 PR 页面直接看到流水线运行情况，无需跳转到 openLiBing 平台查看。

## 功能描述

1. 在 `PipelineServiceImpl.recordPipelineInfo` 中，**不管流水线是否排队**（`QUEUED` / `RUNNING` / `COMPLETED` / `FAILED` / `CANCELED` / `SKIPPED` / `IGNORED` 等），都调用 GitCode Commit Status API 推送一次状态。
2. 排队中的流水线 → `pending`；非排队流水线 → 按 `mapToGitCodeCommitStatus` 映射。
3. GitCode 端点：`POST https://api.gitcode.com/api/v4/projects/{gitcodeRepoId}/statuses/{commitId}`。
4. 涉及两个 DTO 字段的扩展：
   - `PipelineParamDTO` / `PrStartPipelineVo` / `PullRequestEvent` / `NoteEvent` / `PipelineStatusUpdateMessage`：
     新增 `gitcodeRepoId`（Integer，GitCode 源仓库项目 ID）、`gitcodeHookId`（Integer，hook ID）、`sourceBranch`（源分支）、`userName`（触发人名）、`pipelineName`（流水线名）。
5. 任何 GitCode API 异常均**不影响**主流程，仅记录 warn/error 日志。

### 状态映射

| openLiBing 状态 | GitCode Commit Status |
|---|---|
| QUEUED / INIT / PAUSED / SUSPEND / 空值 | pending |
| RUNNING | running |
| COMPLETED | success |
| FAILED | failed |
| CANCELED | canceled |
| SKIPPED / IGNORED | success |

## 不做什么

- 不修改非 gitcode 平台（gitee 等）的流水线逻辑。
- 不修改现有的 PR 评论、PR 标签、流水线报告渲染逻辑。
- 不修改 `PipelineStatusUpdateConsumer` 的 MQ 重试 / 死信处理机制。
- 不向 GitCode 端点请求新增 `Accept` 之外的认证机制，沿用 `PRIVATE-TOKEN`。
- 不持久化 GitCode hook payload 的 `hook_id` 到新表（仅作为 `pipeline_detail` 字段随请求发送）。

## 验收标准

- [ ] 排队中的流水线调用 GitCode API 推送 `pending`。
- [ ] 运行中 / 完成 / 失败 / 取消 / 跳过 / 忽略 的流水线调用 GitCode API 推送对应状态。
- [ ] 仅 `RepoType.GITCODE` 时触发 API 调用；gitee 平台不触发。
- [ ] `param.getRepoType() != GITCODE` 或 `gitcodeRepoId / gitcodeHookId / commitId / accessToken` 任一为空 → 跳过调用并打 info 日志。
- [ ] API 调用失败不抛异常，不影响 `recordPipelineInfo` 主流程。
- [ ] 请求体字段、Header 与"API 调用细节"小节严格一致。
- [ ] `PipelineParamDTO` 等 DTO 新增字段命名统一为 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch` / `userName` / `pipelineName`。

## 影响范围

### 业务仓 `openlibing-cicd`

| 文件 | 操作 | 说明 |
|------|------|------|
| `business/dto/pipeline/PipelineParamDTO.java` | 修改 | 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch` / `userName` / `pipelineName` |
| `business/dto/pipeline/PipelineStatusUpdateMessage.java` | 修改 | 同上 |
| `business/dto/pipeline/GitCodePipelineStatusDTO.java` | 新增 | GitCode 提交状态请求体 + 嵌套 `PipelineDetail` |
| `business/dto/webhooks/PullRequestEvent.java` | 修改 | 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch`；GitCode 路径下填充 |
| `business/dto/webhooks/NoteEvent.java` | 修改 | 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch`；GitCode 路径下填充 |
| `business/vo/PrStartPipelineVo.java` | 修改 | 新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch` |
| `business/listener/PipelineStartEventHandler.java` | 修改 | PR open / update / note 三个分支填充 `sourceBranch` / `userName` / `pipelineName`，并在 `reflashPipelineInfo` 中透传到 `PipelineParamDTO` |
| `business/listener/PipelineStatusUpdateConsumer.java` | 修改 | `buildPipelineParamFromMessage` 透传新增字段 |
| `business/service/impl/PipelineServiceImpl.java` | 修改 | 新增 `pushGitCodeCommitStatus` / `mapToGitCodeCommitStatus`；在 `recordQueuedPipeline` 和 `recordPipelineInfo` 非排队路径中各调一次 |
| `src/test/java/.../PipelineParamDtoBuilder.java` | 修改 | 新增对应字段的链式构造 |
| `src/test/java/.../PipelineServiceImplTest.java` | 修改 | 覆盖 `mapToGitCodeCommitStatus` 全部状态分支 + `pushGitCodeCommitStatus` 跳过/成功/失败/异常 4 类场景 |

### docs 仓 `openlibing-docs`

| 文件 | 操作 | 说明 |
|------|------|------|
| `spec/openlibing-cicd/task_design/gitcode-pipeline-commit-status/proposal.md` | 重写 | 本文件 |
| `spec/openlibing-cicd/task_design/gitcode-pipeline-commit-status/design.md` | 重写 | 详见 `design.md` |
| `spec/openlibing-cicd/task_design/gitcode-pipeline-commit-status/tasks.md` | 重写 | 详见 `tasks.md` |

### 业务仓 `openlibing-codecheck`

| 文件 | 操作 | 说明 |
|------|------|------|
| `business/model/PrStartPipelineVo.java` | 修改 | 同步新增 `gitcodeRepoId` / `gitcodeHookId` / `sourceBranch`，与 `openlibing-cicd` 侧 `PrStartPipelineVo` 字段对齐 |
