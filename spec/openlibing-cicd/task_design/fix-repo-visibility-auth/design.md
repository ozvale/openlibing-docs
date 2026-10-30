# fix-repo-visibility-auth — 技术设计

## 1. 方案设计

在 **项目级 `@CheckPermission`** 之上，增加 **流水线运行实例级绑定**：

```
已具备 project 权限的请求
  → validateExportBuildJobInPipelineRun（构建日志/导出）
      → 30s 本地缓存 → 否 → showPipelineRunDetail → jobId 是否在 steps inputs 中
  → getPreCommitResult(projectId, pipelineId, pipelineRunId)
  → getTestReport 分支 B 带 pipelineId 查库
```

## 2. 实现逻辑设计

### validateExportBuildJobInPipelineRun

- 缓存 key：`projectId:pipelineId:pipelineRunId:jobId`，TTL 30s，max 5000。
- `getPipelineRunDetail` 失败或 data 为空：**不写缓存**。
- 成功拿到 detail 后 `put(bound)`；bound=false 返回「构建任务不属于该流水线运行实例…」。
- `isBuildJobReferencedInPipelineRun` 遍历 stages/jobs，复用 `findMatchedStep(jobRun, jobId)`。

### 预提交

```java
wrapper.eq(projectId).eq(pipelineId).eq(pipelineRunId);
```

PR 评论内部 `getPreCommitResult` 同步三参数。

## 3. 类设计

`PipelineControllerV2`、`PipelineServiceImpl`、`TestCaseResultMapper`（+ XML）。

## 4. 数据模型设计

无 DDL 变更；使用 `pre_commit_record`、`test_case_result` 既有 `project_id` / `pipeline_id` / `pipeline_run_id` 字段。

## 5. 性能设计

构建日志轮询靠 30s 缓存降低 `showPipelineRunDetail` QPS；未命中时单次请求多 1 次详情调用。

## 6. API 接口设计

基路径：`/project/pipeline`（`PipelineControllerV2`）。

| 接口                     | 新增/必填入参                                              |
| ------------------------ | ---------------------------------------------------------- |
| GET `/build/log`         | `pipelineId`, `pipelineRunId`                              |
| POST `/build-log/export` | Body：`pipelineId`, `pipelineRunId`（Controller 非空校验） |
| GET `/pre-commit`        | `projectId`, `pipelineId`, `pipelineRunId`                 |

`getTestReport`：DTO 的 `pipelineId` + `pipelineRunId` 用于分支 B。

## 7. 安全设计

鉴权：继承原有鉴权逻辑

敏感信息：不打印日志，不明文存储数据库，不可下载

硬编码：appkey，token，cookie不写在代码中

审计日志：操作记录可追溯

---

补充：在菜单权限通过后防止 **横向越权**（跨 pipelineRun / 跨 job）。

## 跨仓影响

openlibing-cicd-web 构建日志、预提交页需同步 query/body 字段。
