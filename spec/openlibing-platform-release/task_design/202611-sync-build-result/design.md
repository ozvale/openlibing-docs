# 技术方案：同步构建结果到仓库

## 推荐方案

平台侧薄封装：归属校验 + 幂等防重后，按 job 名查 Jenkins 任务配置
（`jenkins_job_config`），解密 token 拼接 `buildWithParameters` URL 触发
`get-latest-rpms` 参数化构建；完成判定不依赖回调，用
"整体等待时长届满即视为成功"的惰性推进模式（Jenkins 任务执行 + 仓库同步生效
合计约 35 分钟）。

## 关键改动

### 1. 端点（OpeneulerjenkinsController）

`POST /publish/jenkins/syncBuildResultToRepo`：`reviewId` 经
`@RequestBody JenkinsParamQuery` 传入，`userId` 经 `@RequestParam` 传入。

### 2. 触发链路（OpeneulerjenkinsDelegateImpl#syncBuildResultToRepo）

```
归属校验（userId == reviewInfo.creatorId）
→ 幂等防重（syncBuildResult == EXECUTING 直接返回）
→ 版本号拆解：versionNum.indexOf("_update") 前缀即 branch
→ queryJobConfigByJobName("get-latest-rpms") 取 jenkinsUrl + 密文 token
→ 拼 URL：buildWithParameters?token=<解密token>&branch=<branch>
→ 状态置 EXECUTING（含 syncBuildResultTriggerTime = now）
→ executeJenkinsJob(url)
→ saveReviewHistory("执行同步构建结果到仓库", EXECUTE_SUCCESS)
```

失败分支：catch BusinessException → 状态置 EXECUTE_FAILED → 操作历史记失败
→ 返回错误码与"同步构建结果到仓库失败"。

### 3. 完成判定（无回调，等待时长惰性推进）

`get-latest-rpms` 任务无 Jenkins → 平台回调，真实同步生效时间不可观测。
采用保守等待：触发后整体等待 35 分钟（常量 `SYNC_BUILD_RESULT_WAIT_MILLIS`）
即认为仓库同步完成。推进逻辑收敛在公共方法 `advanceSyncBuildResultIfTimeout`：

- 触发条件：`syncBuildResult == EXECUTING` 且 `syncBuildResultTriggerTime != null`
  且 `now - triggerTime >= 35min`
- 动作：状态槽置 EXECUTE_SUCCESS
- 调用方：查询接口 `querySyncBuildResult`（前端轮询时）与自动化编排定时任务
  `UpdateAutomationJobs.process`（步骤 1 轮询时），两处共用

### 4. 状态存储（MongoDB jenkins_job_exec_status）

| 字段 | 说明 |
|---|---|
| `syncBuildResult` | 状态槽（null / EXECUTING / EXECUTE_SUCCESS / EXECUTE_FAILED） |
| `syncBuildResultTriggerTime` | 触发时间（BSON Date，UTC 存储），等待时长判定基准 |

写入位置：`OpenEulerJenkinsOperation#updateJenkinsJobExecStatus`
（`JenkinsJobName.SYNC_BUILD_RESULT` 分支，EXECUTING 时同步写触发时间）。

## 影响范围

- 修改：OpeneulerjenkinsController、OpeneulerjenkinsDelegate(Impl)、
  OpenEulerJenkinsOperation、JenkinsJobExecStatusModel（新增 2 字段）
- 兼容性：MongoDB 模型加字段，旧文档读出为 null，等待判定对 null 触发时间不生效，向后兼容
- 联动：`202611-update-automation` 编排步骤 1 直接复用本接口

## 风险与注意事项

- **token 拼接在 URL query**：沿用本仓 Jenkins 触发的既有模式（历史安全分支
  曾评估并撤回 token 迁移，`9403c53e` revert 保持原实现），不在本任务扩大范围。
- **等待时长是经验值**：35 分钟覆盖 Jenkins 排队 + 执行 + 仓库同步生效；若上游
  任务变慢会出现"未届满前查询一直执行中"的体验问题，但超时兜底由编排任务的
  45 分钟步骤级超时（`202611-update-automation`）接住。
- **无完成回调的取舍**：该 Jenkins 任务不回调平台，采用时长判定而非改造
  Jenkins 任务加回调，改动面最小；提前/推迟完成对后续步骤的影响可控
  （后续步骤消费的是发布仓库内容，同步完成后才推进）。
