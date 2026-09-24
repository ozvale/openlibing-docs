# Tasks：同步仓库悬浮进度条 + 双链路互斥（sync-progress-display）

> 分支：openlibing-coderepo `feat-sync-progress-display`（已 reset 至 prod/master `79210023`）、openlibing-web `feat-sync-progress-display`（编码前需基于 prod/master 重建）
> spec 归档分支：openlibing-docs `spec-openlibing-coderepo-sync-progress-display`
> 约束：spec 文档只落盘不提交；业务仓完成 pre-commit 后暂不 commit，先报告

## A. openlibing-coderepo

- [ ] A1. 新增 `SyncProgressService` + `SyncProgressServiceImpl`（**仅进度，无锁**）：initProgress / setTotal / setCurrentRepo / incrCompleted（HINCRBY + 续期）/ finishProgress / getProgress（none 语义）
- [ ] A2. 新增 `SyncProgressVO`
- [ ] A3. `RepoController` 新增 `GET /project-repo/sync-progress`（参数校验 + verifyPermissionsByProduct 越权校验）；`RepoService` 声明 `querySyncProgress`
- [ ] A4. `RepoServiceImpl#submitProjectSyncTask`：tryLock 成功后 `initProgress(projectId, 0, byJob ? "job" : "manual")`；finally 重排为 `inFlight-- → finishProgress → isHeldByCurrentThread 才 unlock`
- [ ] A5. `RepoServiceImpl#runProjectSyncSteps`：step1 查到仓库列表后 `setTotal(size)`
- [ ] A6. `RepoServiceImpl#syncAllRepoInfoFromRemote`：删内部内存锁 `projectLockMap`；每仓 setCurrentRepo + finally incrCompleted（failed 标记）
- [ ] A7. `XxlJobHandler` step2 重构：按项目聚合命中仓库 → Redisson 同一把锁 tryLock(0,30min) 跳过策略 → init/setCurrent/incr/finish 埋点 → 防御性 unlock
- [ ] A8. `XxlJobHandler` step8：保留 hasProjectSyncInFlight 快路径，追加 Redisson tryLock 跳过策略（不写进度）
- [ ] A9. 单测：SyncProgressServiceImplTest（进度字段/续期/none）；RepoServiceImplTest 适配（埋点 mock、finally 重排）；XxlJobHandler 相关用例
- [ ] A10. coderepo 本地编译 + 相关单测通过

## B. openlibing-web

- [ ] B0. 基于 prod/master 重建 `feat-sync-progress-display` 分支（当前基点是 fork 旧 master）
- [ ] B1. `src/api/Repos/url.ts` + `api.ts`：新增 SYNC_PROGRESS 与 querySyncProgress
- [ ] B2. `views/Repos/index.vue`：按钮外层 wrapper + 进度 popover（running/finished/none 三态、触发方式、失败数）
- [ ] B3. 轮询状态机：onMounted 首查 / 提交激活 / 悬浮激活；串行轮询（响应后 2s）；finished 恢复按钮 + 刷新列表一次；卸载清理
- [ ] B4. popper-class 全局样式（teleport 约束）

## C. 验证与交付

- [ ] C1. web 本地 `pnpm dev:ob` 连 beta 人工验证（验收标准逐条）
- [ ] C2. pre-commit 通过（两业务仓，改动文件全量）
- [ ] C3. 报告分支/文件清单/验证结果（暂不 commit，用户确认后进入 PR 阶段）
- [ ] C4. 用户自测反馈循环
- [ ] C5. Phase 4：业务 PR（ai-assisted 标签 + 关联 Issue）+ docs PR
- [ ] C6. Phase 5：归档 archive.md（用户触发）

## D. 验收反馈调整 v3（design.md §11）

- [ ] D1.（R1）`RepoServiceImpl` 抽取单仓同步体 `syncSingleRepoInfoFromRemote`（平台 API 刷新 + syncRepoBranch），手动 forEach 复用，进度埋点留调用方
- [ ] D2.（R1）`XxlJobHandler#collectMatchedRepos` 扩展：matched 按 repoId 去重 + 收集 unmatchedRepos（repo_info 独有仓）；job 对 unmatched 走 `syncSingleRepoInfoFromRemote`，total = matched + unmatched
- [ ] D3.（R2）`syncRepoInfoHandler` 支持 `projectId=xxx` 参数（parseJobParam 模式，非法值 handleFail）；step1/step2/step5-6/step8 项目列表过滤，step3/4/7 保持全局
- [ ] D4.（R3）`syncAllRepoInfoFromRemote` 每仓循环前加代次检查点（generation 下传），被取代 break
- [ ] D5.（R3）`submitProjectSyncTask` 增加 `lockWaitSeconds` 重载：全局配置触发与 token 变更触发传 60s；页面手动入口保持 0
- [ ] D6. 单测：unmatched 同步/total 口径/去重、projectId 过滤、代次检查点中断、等待重载
- [ ] D7. 全量单测 + pre-commit；commit（v3 调整单 commit）→ 推送 feature → 合入 develop_202609_iter2 推送
