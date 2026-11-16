# 技术方案：生成 updateinfo

## 推荐方案

薄封装触发型接口：归属校验后按版本号推导 `update_dir`，查
`update_test_directory_repodata_by_updateinfo` 的 job 配置，解密 token 拼接
`buildWithParameters` URL（`update_type` 固定 `earlyupdateinfo`）。与同步构建
结果不同，该 Jenkins 任务执行快（分钟级），且无回调——采用
"入队成功即视为成功，延迟 30 秒落状态"的轻量判定，不做幂等拦截。

## 关键改动

### 1. 端点（OpeneulerjenkinsController）

`POST /publish/jenkins/generateUpdateinfo`：`reviewId`、`userId`
均经 `@RequestParam` 传入。

### 2. update_dir 推导（复用 buildUpdateDir）

```
versionNum = "openEuler-22.03-LTS_update20240701"
→ split("_")[1] = "update20240701"
→ 提取日期 "20240701"，BASIC_ISO_DATE 解析 + 3 天
→ "update_20240704"
```

与导入测试 repo（operate-repo）使用的目录推导逻辑保持一致，
确保 updateinfo 落在同一测试仓库目录下。

### 3. 触发链路（OpeneulerjenkinsDelegateImpl#generateUpdateinfo）

```
归属校验（userId == reviewInfo.creatorId）
→ buildUpdateDir(versionNum)
→ queryJobConfigByJobName(GENERATE_UPDATEINFO)
→ 拼 URL：buildWithParameters?token=<解密token>&update_type=earlyupdateinfo&update_dir=<dir>
→ 状态置 EXECUTING
→ executeJenkinsJob(url)
→ saveReviewHistory("执行生成updateinfo", EXECUTE_SUCCESS)
→ CompletableFuture.runAsync(..., delayedExecutor(30s))
     30 秒后状态置 EXECUTE_SUCCESS
```

失败分支：catch BusinessException → 状态置 EXECUTE_FAILED → 操作历史记失败。

### 4. 状态判定差异（对比同步构建结果）

| 维度           | 同步构建结果         | 生成 updateinfo                    |
| -------------- | -------------------- | ---------------------------------- |
| 任务耗时       | 长（35 分钟量级）    | 快（分钟级）                       |
| 完成判定       | 等待 35 分钟惰性推进 | 入队成功 + 延迟 30 秒              |
| 执行中重复触发 | 拦截（幂等防重）     | **不拦截**（重复触发自愈卡住状态） |
| 状态槽         | syncBuildResult      | generateUpdateinfoResult           |

不拦截重复触发的原因：该任务幂等（在同目录重复生成 repodata），
重复触发是状态卡住时用户侧成本最低的自愈手段；而同步构建结果任务重、
防重优先。

### 5. 状态存储（MongoDB jenkins_job_exec_status）

新增字段 `generateUpdateinfoResult`（状态槽）。写入位置：
`OpenEulerJenkinsOperation#updateJenkinsJobExecStatus`
（`JenkinsJobName.GENERATE_UPDATEINFO` 分支）。

## 影响范围

- 修改：OpeneulerjenkinsController、OpeneulerjenkinsDelegate(Impl)、
  OpenEulerJenkinsOperation、JenkinsJobExecStatusModel、JenkinsJobName
- 兼容性：模型加字段，旧文档读出为 null，向后兼容
- 延迟置成功使用 `CompletableFuture.delayedExecutor`，占用公共
  ForkJoinPool 调度线程 30 秒后执行一次性写库，负载可忽略

## 风险与注意事项

- **"入队即成功"的取舍**：Jenkins 队列阻塞或任务实际执行失败时状态仍会置
  成功；但该任务的失败可在测试 repo 检查环节暴露，且支持重复触发自愈，
  采用轻量判定是合理折中。
- **token 拼接在 URL query**：沿用仓内既有 Jenkins 触发模式（同
  `202611-sync-build-result` 的风险说明）。
- 延迟置成功与人工重复触发存在并发交错的可能，但两者终态一致
  （EXECUTE_SUCCESS），无竞态风险。
