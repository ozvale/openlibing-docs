# 实现步骤：update 发布自动化编排

## 已交付（分支 feat-update-release-automation）

### 编排状态与启动接口（commit `480e1cd0`）

- [x] JenkinsJobExecStatusModel 新增 updateAutomationStatus / Step / StepTime / UserId / StartTime 字段
- [x] OpenEulerJenkinsOperation 新增 startUpdateAutomation（初始化编排五字段）、updateUpdateAutomationStatus（状态 + 指针推进）、queryUpdateAutomationExecuting（扫描查询）
- [x] OpeneulerjenkinsDelegateImpl 实现 startUpdateAutomation：归属校验 / 幂等防重 / firstPendingAutomationStep 计算续跑起点 / 初始化并触发步骤 1
- [x] firstPendingAutomationStep 按状态槽顺序定位第一个未成功步骤（javadoc 与 UpdateAutomationJobs#stepStatus 互相锚定）
- [x] OpeneulerjenkinsController 暴露 `POST /publish/jenkins/startUpdateAutomation`

### 定时编排任务（UpdateAutomationJobs，commit `480e1cd0` + 后续修复）

- [x] 每分钟 cron + Redis setIfAbsent 分布式锁（300s 超时，锁值校验删除）
- [x] process 单条处理：超时兜底 / 步骤 1 惰性推进 / 完成判定 / 失败终止 / 成功推进
- [x] triggerStep 七步触发映射（步骤 5/6 入参为已接纳 ids，空则失败）
- [x] acceptAllCveAndBugfix 步骤 3 完成后自动接纳全部 cve/bugfix
- [x] 步骤级超时兜底 45 分钟（commit `0ca70473`，由 4 小时调整为 45 分钟）

### 生成 CVE 公告纳入编排（commits `165524b0` / `a0a9cd2a` / `868e0578` / `fe2291ab`）

- [x] 编排新增步骤 7：generateNotice(reviewId, userId, flag=1)
- [x] generateNotice 接口支持 flag 双按钮状态跟踪（手动/编排走独立状态槽）
- [x] 编排完成判定看 generateSafeNoticeResult1（新按钮状态字段）
- [x] 生成公告触发前置"执行中"状态，避免轮询空窗

### 操作历史与修复

- [x] 各触发点写入评审单操作历史
- [x] 修复 collectBugfix 公示 issue 无评论时也置执行成功（commit `f8fbfed8`，防编排卡死步骤 3）

### 交付质量

- [x] 编译 + 静态检查通过，spotless 格式化续跑相关 javadoc（commit `e4d04955`）
- [x] 分支恢复真实业务代码后推送远端

## 验证记录

- [x] generateUpdateinfo 远程触发链路 curl 实测 201 入队（2026-11-02，
      见 `202611-generate-updateinfo`）
- [x] 本地测试分支 `feat-update-release-automation-test` 完成 mock 调试，
      真实业务代码已还原回交付分支

## 后续增强（另行立项，不在本任务范围）

- [ ] 编排"暂停/取消"能力（当前只能等失败/超时终止）
- [ ] 编排过程人工介入（部分接纳 cve/bugfix）
- [ ] 编排执行过程的时间线展示（各步骤耗时统计）
