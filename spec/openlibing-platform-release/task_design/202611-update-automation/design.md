# 技术方案：update 发布自动化编排

## 推荐方案

"启动接口 + 状态机指针 + 定时任务推进"三段式：

1. **启动接口**只做归属校验、幂等防重、计算续跑起点并初始化编排状态
   （无已成功步骤时直接触发步骤 1）；
2. **状态机**复用 35 阶段任务状态槽（`jenkins_job_exec_status`），每个步骤的
   成败判定映射到既有状态字段，编排自身只新增指针与整体状态字段；
3. **定时任务**（每分钟）扫描执行中的编排记录，轮询当前步骤状态：
   执行中等待下轮、成功推进下一步、失败/超时整体终止。

选择定时轮询而非编排内长阻塞等待：各步骤完成时长差异大（秒级到 35 分钟级），
轮询把推进逻辑收敛在单处，天然支持断点续跑与多评审单并发编排。

## 关键改动

### 1. 端点与启动链路（OpeneulerjenkinsDelegateImpl#startUpdateAutomation）

```
归属校验（userId == reviewInfo.creatorId）
→ 幂等防重（updateAutomationStatus == EXECUTING 直接返回）
→ firstPendingAutomationStep(jobExecStatus) 计算续跑起点（1-8）
→ startStep > 1：startUpdateAutomation(reviewId, userId, startStep-1)
    指针指向最后一个已成功步骤，由定时任务下一轮触发待执行步骤
→ startStep == 1：startUpdateAutomation(reviewId, userId, 1) + 直接触发步骤 1
→ 步骤 1 触发失败：整体置 EXECUTE_FAILED
```

`firstPendingAutomationStep` 按
syncBuildResult → startModule → collectBugfixResult → checkBaseline →
checkVersion → createOrUpdateRepo → generateSafeNoticeResult1 顺序找到第一个
非 EXECUTE_SUCCESS 的字段，返回其步骤号（全成功返回 8，指针置 7，
由定时任务下一轮判定整体成功）。
**字段顺序必须与 `UpdateAutomationJobs#stepStatus` 的步骤映射保持一致**
（两处以注释互相锚定）。

### 2. 步骤-接口-状态槽映射（UpdateAutomationJobs#triggerStep / stepStatus）

| # | 步骤 | 触发方法 | 编排专属行为 | 状态槽 |
|---|---|---|---|---|
| 1 | 同步构建结果到仓库 | `openeulerjenkinsDelegateImpl.syncBuildResultToRepo` | — | syncBuildResult |
| 2 | 收集 CVE | `platformreleaseDelegateImpl.startModule` | 完成后自动接纳（Jenkins 回调写库） | startModule |
| 3 | 收集 bugfix | `platformreleaseDelegateImpl.collectBugfix` | **完成后自动接纳全部 cve/bugfix** | collectBugfixResult |
| 4 | 需求基线 | `openeulerjenkinsDelegateImpl.checkBaseline` | 基于接纳结果冻结 | checkBaseline |
| 5 | 版本检查 | `openeulerjenkinsDelegateImpl.checkVersions` | 入参=已接纳 ids，空则失败 | checkVersion |
| 6 | 导入测试 repo | `openeulerjenkinsDelegateImpl.operateTestingRepo` | action 固定 CREATE_OR_UPDATE；入参=已接纳 ids | createOrUpdateRepo |
| 7 | 生成 CVE 公告 | `platformreleaseDelegateImpl.generateNotice(reviewId, userId, 1)` | 走新按钮链路（flag=1） | generateSafeNoticeResult1 |

步骤 2（startModule）是唯一有 Jenkins 回调的步骤（`saveCveCallbackResult`
按 jobUuid 匹配写库）；其余步骤为平台主动拉取/阻塞等待/惰性推进后写库。

### 3. 定时编排（UpdateAutomationJobs，每分钟 cron）

```
Redis setIfAbsent(锁, 300s) 抢锁
→ queryUpdateAutomationExecuting() 扫描 EXECUTING 记录，逐条 process：
   1. 步骤级超时兜底：now - updateAutomationStepTime >= 45min → 整体失败
   2. step==1 特殊处理：advanceSyncBuildResultIfTimeout 惰性推进
   3. 当前步骤状态：FAILED → 整体失败；非 SUCCESS → 等待下轮
   4. step >= 7 → 整体成功
   5. step==3：acceptAllCveAndBugfix 自动接纳，为空/失败 → 整体失败
   6. triggerStep(next)：成功 → 指针推进到 next；失败 → 整体失败
→ finally 校验锁值一致后删锁
```

单条 process 异常仅记日志，不影响其余记录处理（循环内 try-catch）。

### 4. 编排状态存储（MongoDB jenkins_job_exec_status）

| 字段 | 说明 |
|---|---|
| `updateAutomationStatus` | 整体状态（EXECUTING / EXECUTE_SUCCESS / EXECUTE_FAILED） |
| `updateAutomationStep` | 步骤指针（1-7，指向已触发/已成功的当前步骤） |
| `updateAutomationStepTime` | 当前步骤开始时间（超时判定基准） |
| `updateAutomationUserId` | 发起人（续跑时以其身份触发后续步骤） |
| `updateAutomationStartTime` | 编排整体开始时间 |

写入位置：`OpenEulerJenkinsOperation` 新增
`startUpdateAutomation`（初始化五字段）、`updateUpdateAutomationStatus`
（整体状态 + 可选指针推进）、`queryUpdateAutomationExecuting`（扫描查询）。

### 5. 自动接纳（acceptAllCveAndBugfix）

`queryAllCveAndBugfix(reviewId)` 汇总 cve + bugfix 全部记录 id，
`batchModifyCveOrBugfixOperations`（operations = accept）一次性全量接纳；
收集结果为空视为失败（后续步骤无依赖数据）。手动模式下用户逐条勾选接纳，
编排模式为效率固定全量接纳——这是编排与手动模式的关键行为差异。

## 影响范围

- 修改：OpeneulerjenkinsController、OpeneulerjenkinsDelegate(Impl)、
  OpenEulerJenkinsOperation、JenkinsJobExecStatusModel、JenkinsJobName、
  PlatformreleaseDelegateImpl（generateNotice 支持 flag 双按钮状态）、
  新增 UpdateAutomationJobs
- 兼容性：模型加字段向后兼容；既有手动按钮链路不受影响
  （generateNotice 以 flag 区分，手动走原状态槽，编排走 generateSafeNoticeResult1）
- 依赖：Redis（分布式锁）、Spring @EnableScheduling

## 风险与注意事项

- **指针与状态槽映射的双处维护**：`firstPendingAutomationStep` 与
  `stepStatus`/`triggerStep` 必须同步修改，顺序错位会导致续跑跳步/重跑。
  已用 javadoc 注释互相锚定，若新增步骤须同时改三处。
- **自动接纳全量 cve/bugfix 的业务取舍**：编排模式不做逐条筛选，若某次
  update 需要剔除个别 CVE，应走手动模式。该约束已在产品层面确认。
- **Redis 锁的可见性**：锁超时 300s 大于单轮扫描时长，锁值校验删除防止
  误删他人锁；锁失效依赖超时兜底（进程被 kill 时锁自然过期）。
- **整体无"暂停/取消"能力**：中途只能等失败/超时终止；如需取消需
  人工将状态改库。可作为后续增强。
- **collectBugfix 无评论场景**（`f8fbfed8` 修复）：公示 issue 无评论时
  也置执行成功，避免编排卡死在步骤 3。
