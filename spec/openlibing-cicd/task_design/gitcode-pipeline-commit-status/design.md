# gitcode-pipeline-commit-status — 技术设计

## 方案概述

在 `PipelineServiceImpl.recordPipelineInfo` 的排队路径（`recordQueuedPipeline`）和非排队路径（拿到 `pipelineRunDetail` 之后）中各调一次 `pushGitCodeCommitStatus(param, status)`，按 GitCode Commit Status API v4 提交完整请求体（包含 PR 元数据、流水线运行上下文、`pipeline_detail` JSON 子对象），使流水线状态在 GitCode PR Checks 标签页正常呈现。

## 架构决策

1. **统一从 `PipelineParamDTO` 读取所有 GitCode 上下文**：`gitcodeRepoId` / `gitcodeHookId` / `sourceBranch` / `userName` / `pipelineName` 全部由调用方填充，避免 Service 层再做 DB 查询（仅 `hwProjectId` / `region` 例外，因其用于拼接华为云 URL 模板，保留在 Service 内按 `projectId` 查 `HwProjectInfoEntity`）。
2. **`hwProjectId` 在 `pushGitCodeCommitStatus` 内部按 `projectId` 查询**：避免调用方多传一个参数；查询失败则按 `region` 缺失一起跳过，行为一致。
3. **API 调用失败不阻断主流程**：try/catch 包到方法边界；`null` 响应 / 非 2xx / 异常统一只打日志。
4. **新增独立 DTO `GitCodePipelineStatusDTO`**：避免在 Service 中堆 `JSONObject.put`，便于测试与未来字段扩展；`pipeline_detail` 字段类型为 `String`（不是嵌套对象），由调用方把 `PipelineDetail` 子对象 `JSON.toJSONString` 后塞入。
5. **状态映射保持 `RUNNING → running` / `FAILED → failed` / `CANCELED → canceled` / `SKIPPED/IGNORED → success` / 其他 → `pending`**：与 GitCode 官方文档列举的状态值集合一致。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `business/dto/pipeline/PipelineParamDTO.java` | 修改 | 新增 5 个 GitCode 上下文字段 |
| `business/dto/pipeline/PipelineStatusUpdateMessage.java` | 修改 | 同上，确保 MQ 链路可还原 |
| `business/dto/pipeline/GitCodePipelineStatusDTO.java` | 新增 | 请求体 + 嵌套 `PipelineDetail` |
| `business/dto/webhooks/PullRequestEvent.java` | 修改 | GitCode 路径填充 3 个新增字段 |
| `business/dto/webhooks/NoteEvent.java` | 修改 | GitCode 路径填充 3 个新增字段 |
| `business/vo/PrStartPipelineVo.java` | 修改 | 新增 3 个字段供 `PipelineStartEventHandler` 填充 |
| `business/listener/PipelineStartEventHandler.java` | 修改 | PR open/update/note 三处 `setSourceBranch` / `setUserName` / `setPipelineName` |
| `business/listener/PipelineStatusUpdateConsumer.java` | 修改 | `buildPipelineParamFromMessage` 透传 5 个字段 |
| `business/service/impl/PipelineServiceImpl.java` | 修改 | 新增 2 个私有方法 + 2 处调用点 |
| 测试 `PipelineParamDtoBuilder` / `PipelineServiceImplTest` | 修改 | 覆盖 5 个新字段 + API 行为 |

## API 调用细节

### 端点与 Header

```
POST https://api.gitcode.com/api/v4/projects/{gitcodeRepoId}/statuses/{commitId}
PRIVATE-TOKEN: {accessToken}
Accept-Encoding: identity
Content-Type: application/json
```

### 请求体字段映射

| DTO 字段 | JSON 字段 | 取值来源 |
|---|---|---|
| `mergeRequestIid` | `merge_request_iid` | `param.getPrId()` |
| `state` | `state` | `mapToGitCodeCommitStatus(pipelineStatus)` |
| `name` | `name` | `param.getPipelineName()` |
| `targetUrl` | `target_url` | `https://devcloud.{region}.huaweicloud.com/cicd/project/{hwProjectId}/pipeline/detail/{pipelineId}/{pipelineRunId}` |
| `stopUrl` | `stop_url` | `https://cloudpipeline-backend.{region}.myhuaweicloud.com:8443/CloudPipelineServer/v5/{hwProjectId}/pipelines/{pipelineId}/pipeline-runs/{pipelineRunId}s/stop` |
| `ref` | `ref` | `param.getSourceBranch()` |
| `buildId` | `build_id` | `param.getPipelineRunId()` |
| `stage` | `stage` | `param.getPipelineName()` |
| `triggerUser` | `trigger_user` | `param.getUserName()` |
| `rebuildFailedUrl` | `rebuild_failed_url` | `https://cloudpipeline-backend.{region}.myhuaweicloud.com:8443/CloudPipelineServer/v5/pipelines/{pipelineId}/pipeline-runs/{pipelineRunId}s/codehub/retry/{region}` |
| `pipelineDetail` | `pipeline_detail` | `JSON.toJSONString(PipelineDetail)`，**必须是字符串** |
| `reportType` | `report_type` | 固定 `"pipeline"` |
| `pipelineId` | `pipeline_id` | `param.getPipelineId()` |
| `pipelineRunId` | `pipeline_run_id` | `param.getPipelineRunId()` |

### `pipeline_detail` 子对象字段

`GitCodePipelineStatusDTO.PipelineDetail` 序列化为 JSON 字符串后填入顶层 `pipeline_detail`：

| DTO 字段 | JSON 字段 | 取值 |
|---|---|---|
| `hookId` | `hook_id` | `param.getGitcodeHookId()` |
| `hookType` | `hook_type` | 固定 `"project"` |
| `jobLogUrl` | `job_log_url` | `null`（按 GitCode 样例留空） |
| `jobRunTime` | `job_run_time` | `null` |
| `pipelineTotalTime` | `pipeline_total_time` | `null` |
| `projectId` | `project_id` | `hwProjectId`（查 `HwProjectInfoEntity` 得来） |
| `projectHost` | `project_host` | `https://cloudpipeline-ext.{region}.myhuaweicloud.com` |

> 命名说明：第二个值字段是 `project_host`（不是 `endpoint`），以 GitCode 实际接口样例为准。

## 状态映射逻辑

```java
private String mapToGitCodeCommitStatus(String pipelineStatus) {
    if (StringUtils.isBlank(pipelineStatus)) {
        return "pending";
    }
    switch (pipelineStatus) {
        case "RUNNING":    return "running";
        case "COMPLETED":  return "success";
        case "FAILED":     return "failed";
        case "CANCELED":   return "canceled";
        case "SKIPPED":
        case "IGNORED":    return "success";
        case "QUEUED":
        case "INIT":
        case "PAUSED":
        case "SUSPEND":
        default:           return "pending";
    }
}
```

## 业务流程

```text
recordPipelineInfo(param)
  ├─ 查 HwProjectInfoEntity → (hwProjectId, region)
  ├─ getPipelineRunDetail(...) → pipelineRunDetail
  ├─ 若是 QUEUED → recordQueuedPipeline(projectId, param)
  │     └─ 入库 + pushGitCodeCommitStatus(param, "QUEUED")
  └─ 通用路径
        └─ 渲染报告 + pushGitCodeCommitStatus(param, pipelineRunDetail.getStatus())
             └─ 内部:
                  1. 前置校验 (repoType=GITCODE, 4 个必填字段非空)
                  2. 查 HwProjectInfoEntity → hwProjectId, region
                  3. 校验 hwProjectId / region 非空
                  4. 拼 URL
                  5. 装填 GitCodePipelineStatusDTO
                  6. 序列化 PipelineDetail → 字符串 → 写入 pipelineDetail
                  7. HttpRequestUtil.sendRequest("POST", url, body, headers)
                  8. 200/201 → info；其他 → warn；异常 → error
```

## 前置校验

- `param == null` 或 `!RepoType.GITCODE.equals(param.getRepoType())` → 静默 return。
- `param.getGitcodeRepoId() / getGitcodeHookId() / getCommitId() / getAccessToken()` 任一为空 → info 日志 + return。
- `pipelineStatus` 为空 → info 日志 + return。
- `HwProjectInfoEntity` 查不到、`hwProjectId` 或 `region` 为空 → info 日志 + return。

## 错误处理

- HTTP `200` / `201` → info 日志。
- HTTP 其他状态码 → warn 日志（含 body）。
- `HttpRequestUtil.sendRequest` 返回 `null` → warn 日志。
- 任意 Exception → error 日志（含 stack），**不抛**。

## 测试

`PipelineServiceImplTest` 用反射调私有方法，并 `MockedStatic<HttpRequestUtil>` 验证入参：

- `mapToGitCodeCommitStatus` 覆盖全部分支。
- `pushGitCodeCommitStatus` 覆盖：非 gitcode 跳过、`gitcodeRepoId` null 跳过、`gitcodeHookId` null 跳过、`commitId` 空白跳过、`accessToken` 空白跳过、`pipelineStatus` 空白跳过、API 200 成功、API 5xx 失败、`HttpRequestUtil` 抛异常、`param` null、URL 模板正确性、Header `Accept-Encoding=identity` & `PRIVATE-TOKEN` 正确性、Body 全部字段与 `pipeline_detail` JSON 字符串结构。

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| GitCode API 不可用 | try/catch 包到方法边界，失败仅日志 |
| `accessToken` 缺权限 | warn 日志，便于排障 |
| `HwProjectInfoEntity` 缺失 / `region` 缺失 | 静默跳过，不影响主流程 |
| 字段命名与 GitCode 不一致（如 `project_host` vs `endpoint`） | 以本 design.md "API 调用细节" 为唯一事实来源 |

## 跨仓影响

涉及两个业务仓：

- `openlibing-cicd`：主仓，新增 `GitCodePipelineStatusDTO` / DTO 字段扩展 / 事件链路填充 / Service 新增方法与调用点 / MQ 链路透传。
- `openlibing-codecheck`：仅同步 `PrStartPipelineVo` 的 3 个字段（`gitcodeRepoId` / `gitcodeHookId` / `sourceBranch`），与主仓 VO 保持一致，便于跨仓引用。
