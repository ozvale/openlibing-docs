# openEuler update 发布流程自动化编排（一键串行七步 + 断点续跑）

## 需求背景

openEuler update 发布（update 单）在评审通过后需要依次执行七个独立步骤：
同步构建结果到仓库 → 收集 CVE → 收集 bugfix → 需求基线 → 版本检查 →
导入测试 repo → 生成 CVE 公告。此前每个步骤都是一个独立按钮/接口，
依赖人工逐个点击并盯进度，存在三类痛点：

1. **操作繁琐**：七次手动触发，且部分步骤（如版本检查、导入测试 repo）
   还要先手工完成 CVE/bugfix 接纳等前置操作；
2. **易出错**：步骤顺序与前置条件依赖人工记忆，漏做/错序难以察觉；
3. **不可续跑**：中途某步失败后需要人工判断从哪一步重跑。

本需求新增"update 发布自动化编排"：一键启动、定时任务驱动串行推进、
已成功步骤不重复执行（断点续跑）、失败即整体终止并可重新一键续跑。

## 需求范围

**范围内**：

- 新增 `POST /publish/jenkins/startUpdateAutomation` 启动接口（仅创建者，幂等防重）
- 新增编排状态字段：`updateAutomationStatus`（整体状态）、
  `updateAutomationStep`（步骤指针 1-7）、`updateAutomationStepTime`
  （步骤开始时间）、`updateAutomationUserId`（发起人）、
  `updateAutomationStartTime`
- 断点续跑：启动时计算第一个未成功步骤作为续跑起点，已成功步骤不重复执行
- 新增定时编排任务 `UpdateAutomationJobs`：每分钟扫描执行中的编排记录，
  轮询当前步骤状态并串行推进；Redis 分布式锁防多实例并发
- 编排模式专属行为：收集 CVE/bugfix 完成后自动接纳全部结果；
  导入测试 repo 的 action 固定 `create_or_update`；
  生成 CVE 公告走独立按钮状态字段 `generateSafeNoticeResult1`
- 单步骤超时兜底：45 分钟未完成则整体置失败
- 失败终止：任一步骤失败即整体置失败，重新调用启动接口可续跑

**范围外**：

- 七个步骤本身的实现（均为既有接口，编排只做触发与状态判定）
- 生成 updateinfo / 确认公告 / 发布公告 / 正式发布（编排结束后的后续环节）
- 编排过程的人工介入（如部分接纳 CVE/bugfix；自动接纳为全量）

## 验收标准

1. 非创建者调用启动接口返回 400 无权限。
2. 编排执行中重复调用启动接口直接返回当前状态，不重复初始化。
3. 七步严格串行：步骤 N 成功前不触发步骤 N+1；步骤顺序与
   `firstPendingAutomationStep` / `stepStatus` 的字段映射一致。
4. 已成功步骤不重复执行：重新启动时从第一个未成功步骤继续
   （如步骤 4 失败后重启，`updateAutomationStep` 置为 3＝最后一个已成功步骤，
   由定时任务下一轮触发步骤 4，1-3 不重跑）。
5. 步骤 3（收集 bugfix）完成后自动接纳全部 CVE/bugfix；接纳为空视为失败。
6. 步骤 5/6 以已接纳的 CVE/bugfix 为入参，为空视为失败终止。
7. 单步骤超过 45 分钟未完成，整体置失败。
8. 全部七步成功后整体置成功。
9. 多实例部署下定时任务通过 Redis 锁互斥，同一评审单同一时刻仅一轮扫描推进。
10. 编排过程中各步骤状态可经既有轮询接口观察，操作历史可追溯。

## 关联

- 业务分支：`feat-update-release-automation`（openlibing-platform-release 仓）
- 实现 commit：`480e1cd0`（编排主体）、`165524b0`（新增生成 CVE 公告步骤）、
  `a0a9cd2a`（生成 CVE 公告接口支持双按钮状态跟踪）、
  `868e0578`（生成公告归入新按钮状态字段）、`fe2291ab`（生成公告触发前置执行中状态）、
  `0ca70473`（单步骤超时阈值调整为 45 分钟）、
  `f8fbfed8`（修复：collectBugfix 公示 issue 无评论时也置执行成功）
- 关联 spec：`202611-sync-build-result`（步骤 1）、其余步骤复用既有接口
