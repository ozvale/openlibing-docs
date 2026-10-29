# Proposal：同步仓库悬浮进度条 + 双链路互斥（sync-progress-display）

> 关联仓：openlibing-coderepo（主）、openlibing-web
> 页面：仓库管理页 `views/Repos/index.vue` "同步仓库"按钮
> 日期：2026-09-16

## 1. 需求背景

仓库管理页的"同步仓库"按钮触发项目级仓库同步（POST `/project-repo/sync-repo`），后端提交异步任务后立即返回，全程无进度数据，用户只能盲目等待或手动刷列表。

同时现状存在隔离缺陷：页面链路已由 Redisson 项目锁互斥（`distributed_lock:PROJECT_SYNC:{projectId}`），但 XxlJob 定时同步的 step2（repo_info 更新+分支同步）完全不加锁、step8（SIG 仓同步）仅本地内存判定，与页面链路可跨实例并发写 `repo_info` / `repo_branch`。另有一个既有缺陷一并修复：同步收口 finally 中 `unlock()` 先于 `inFlight--` 执行，超 30 分钟锁过期后 unlock 抛异常导致计数泄漏、项目永久卡"同步中"。

## 2. 需求内容

1. 鼠标悬浮"同步仓库"按钮展示弹出层：同步进行中显示真实进度条（仓库级粒度），无任务时显示空闲状态；
2. 进度数据来自后端同步任务真实执行进度，页面链路与 XxlJob 定时链路**共享同一套进度查询**；
3. 页面链路与 XxlJob 链路通过项目级 Redis 分布式锁互斥隔离（多实例安全）；
4. 进入页面时查询同步状态：若 running，按钮禁用并展示 loading，悬浮可查看进度，直到同步结束自动恢复并刷新列表；
5. 点击提交后按钮同样禁用+loading 并全程跟踪（不依赖悬浮）。

## 3. 验收标准

- [ ] 悬浮按钮弹出进度条：running 显示百分比 + 已完成 x/y + 正在同步仓 + 失败数；finished 显示完成状态；none 显示"当前无同步任务"
- [ ] 进度条数据反映真实同步进度（手动触发与定时触发均可观察，含触发方式标识）
- [ ] 同步 running 期间按钮 disabled+loading；点击提交成功后立即生效；页面刷新后状态自动恢复
- [ ] 轮询发现 finished：按钮恢复 + 仓库列表自动刷新一次 + success 提示（单次）
- [ ] 页面链路与 XxlJob 链路互斥（同一把 Redisson 锁）：同步期间二次点击被拒（"当前项目正在同步仓库信息，请稍后重试"）；XxlJob step2/step8 拿不到锁时跳过该项目本轮（日志可见）且不阻塞整轮
- [ ] 进度数据与互斥锁解耦：进度服务只写进度 Hash，不引入第二把锁
- [ ] 既有缺陷修复：submitProjectSyncTask finally 重排（inFlight-- → finishProgress → isHeldByCurrentThread 才 unlock），超长同步场景不泄漏 inFlight
- [ ] 新增查询接口有项目级横向越权校验
- [ ] coderepo 单测通过；pre-commit 通过

## 4. 明确不做

- 不做分支级进度、不做 SSE 推送
- 不改 XxlJob step1（组织→project_repo_info）与 token 相关步骤（step3~7）
- 不动 `repoLockMap`（分支级内存锁）
- 不修复 token 变更重跑丢失窗口（waitTime=0，prod 既有行为，范围外单独设计）
- 不启用 Redisson watchdog（leaseTime=-1），维持 30min 固定租约
- 不修复 SIG 弹窗死代码（存量问题）
