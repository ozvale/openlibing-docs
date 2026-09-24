# Design：同步仓库悬浮进度条 + 双链路互斥（sync-progress-display）

> 修订版 v3：验收反馈调整（R1 口径对齐 / R2 job 参数化 / R3 全局配置中断+重跑落地），见 §11。
> 修订版 v2：基于源仓 master（`79210023`，含「运行代次+检查点协作中断」同步重构）重新设计。
> 相对 v1 的关键变化：**放弃自研 SET NX 锁，互斥完全复用既有 Redisson 项目锁**；进度服务只做进度。

## 1. 现状基线（源仓 master 已有能力）

| 链路                                    | 互斥                                                                                         | 进度  |
| --------------------------------------- | -------------------------------------------------------------------------------------------- | ----- |
| manual（POST /sync-repo）               | ✅ Redisson `distributed_lock:PROJECT_SYNC:{projectId}`，`tryLock(0, 30min)`，持锁到任务结束 | ❌ 无 |
| token 变更重跑（resyncOnTokenChange）   | ✅ 同上（走同一收口 submitProjectSyncTask）                                                  | ❌ 无 |
| XxlJob step2（repo_info 更新+分支同步） | ❌ 完全无锁                                                                                  | ❌ 无 |
| XxlJob step8（SIG 仓同步）              | ⚠️ 仅本地内存 `hasProjectSyncInFlight`，多实例失效                                           | ❌ 无 |

另有一个既有缺陷需在本次触碰范围内顺手修复（见 §4.3）。

## 2. 整体方案

```
┌─ 页面/token变更链路 submitProjectSyncTask ──┐      ┌─ XxlJob step2/step8 ─────────────┐
│ Redisson tryLock(0, 30min)（既有）          │      │ 逐项目 Redisson tryLock(0, 30min) │
│   ├─ initProgress(manual|job)               │      │ 拿不到 → 日志+跳过该项目本轮       │
│   ├─ step1 查到仓库后 setTotal(n)           │ 互斥  │ 拿到 → initProgress(job)+setTotal │
│   ├─ 每仓 setCurrentRepo + finally incr    │◄────►│ 逐仓 setCurrentRepo + finally incr│
│   └─ finally: inFlight-- → finish → unlock │      │ finish → 防御性 unlock            │
└────────────────────────────────────────────┘      └──────────────────────────────────┘
                     │ 共享 Redis 进度 Hash（唯一新增存储）
                     ▼
   GET /project-repo/sync-progress?userId=&projectId=
                     ▼
   前端按钮 loading/disabled 跟踪 + el-popover(hover) + status 驱动轮询 + finished 自动刷新
```

原则：**一把锁、一个进度 Hash、一个查询接口**。锁不新增 key，进度服务不承担互斥职责。

## 3. Redis 数据结构

| Key                                         | 类型           | 字段/值                                                                                                             | TTL                      |
| ------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `distributed_lock:PROJECT_SYNC:{projectId}` | Redisson RLock | （既有，不动）                                                                                                      | tryLock 显式 lease 30min |
| `coderepo:sync:progress:{projectId}`        | Hash           | total, completed, currentRepo, failedCount, status(running/finished), triggerSource(manual/job), startTime, endTime | 30min，每次写续期        |

不涉及数据库 schema 变更。`triggerSource` 约定：`manual`=页面触发；`job`=XxlJob 定时与 token 变更重跑（byJob=true）。

## 4. 后端设计（openlibing-coderepo）

### 4.1 进度服务（SyncProgressService，仅进度）

- `initProgress(projectId, triggerSource)`：覆盖写入全字段（total/completed 等初始 0）+ status=running + TTL；总数由 `setTotal` 在查到仓库列表后补充
- `setTotal(projectId, total)`：total 在 step1 查到仓库列表后补充（锁成功时仓库数未知）
- `setCurrentRepo(projectId, repoUrl)`：当前处理仓库
- `incrCompleted(projectId, repoUrl, failed)`：HINCRBY completed 1；failed 时 HINCRBY failedCount 1；更新 currentRepo；EXPIRE 续期
- `finishProgress(projectId)`：status=finished + endTime + EXPIRE
- `getProgress(projectId)`：返回 VO；无记录（过期/从未同步）→ status=none，其余字段 null

### 4.2 manual/token变更链路埋点（submitProjectSyncTask 内）

- tryLock 成功后 → `initProgress(projectId, byJob ? "job" : "manual")`
- `runProjectSyncSteps` step1 查到 `repoInfoEntities` 后 → `setTotal(size)`
- `syncAllRepoInfoFromRemote`：**删除内部内存锁 `projectLockMap`**（外层已有项目级 Redisson 锁，多实例下内存锁冗余且无效）；每仓 try 前 `setCurrentRepo`，既有 catch 分支标记 failed，finally `incrCompleted`
- SIG 仓同步、用户同步不计入 completed（total 语义固定为"仓库分支同步进度"）
- 代次中断提前退出路径：finally 兜底 `finishProgress`（status=finished），前端视为终态自然恢复

### 4.3 finally 防御性重排（修复既有 inFlight 泄漏缺陷）

现状顺序：`unlock() → inFlight--`。同步超过 30min 锁过期后 `unlock()` 抛 `IllegalMonitorStateException`，`inFlight--` 被跳过 → 计数泄漏 → `hasProjectSyncInFlight` 永真 → `/sync-repo` 永远"正在同步"、XxlJob step8 永远跳过该项目，直到实例重启。

重排为：

```
inFlight.decrementAndGet();
finishProgress(projectId);
if (projectSyncLock.isHeldByCurrentThread()) projectSyncLock.unlock();
```

### 4.4 XxlJob step2 重构（互斥 + 进度）

`syncDataFromProjectRepoInfoToRepoInfo`：锁粒度提到项目级，需先聚合——

1. 按项目收集所有 platform:org 条目命中的仓库（platform, repoInfo, projectRepo 三元组列表），业务行为不变
2. 逐项目：`redissonClient.getLock(PROJECT_SYNC_LOCK_PREFIX + projectId).tryLock(0, 30, MINUTES)`
   - 拿不到 → log + 跳过该项目本轮（不阻塞整轮，下个周期再同步）
   - 拿到 → `initProgress(projectId, "job")` + `setTotal(n)` → 逐仓 `setCurrentRepo` + try/finally `incrCompleted`（updateRepo + syncRepoBranch）→ `finishProgress` → finally 防御性 unlock
3. 原 `updateExistingReposAndSyncBranches` 拆为"收集命中列表"与"逐仓处理"两个私有方法

### 4.5 XxlJob step8 加锁（SIG 仓同步，同 step2 模式）

既有 `hasProjectSyncInFlight` 跳过保留（快路径，省一次 Redis 调用），追加：`redissonClient.getLock(...).tryLock(0, 30, MINUTES)` 拿不到 → 跳过该项目；拿到 → finally 防御性 unlock。SIG 同步本身**不写进度 Hash**（total 语义与仓库分支同步不同，避免计数口径混乱）。

### 4.6 进度生命周期

| 场景                     | 行为                                                                       |
| ------------------------ | -------------------------------------------------------------------------- |
| 拿锁成功                 | initProgress 覆盖写入（status=running，total=0），立即对查询可见           |
| step1 查到仓库           | setTotal(n)                                                                |
| 每仓完成（成功/失败）    | HINCRBY completed + 更新 currentRepo/failedCount + EXPIRE 续期             |
| 任务结束（含被代次中断） | status=finished, endTime + EXPIRE 30min                                    |
| 进程崩溃                 | 无 finish，status 停留 running 直至 TTL 过期 → 查询返回 none，前端恢复按钮 |

### 4.7 查询接口

`GET /project-repo/sync-progress?userId=&projectId=`（网关前缀 `/gateway/openlibing-coderepo`）：

- 鉴权：`verifyPermissionsByProduct(userId, null, projectId, null, REPO_QUERY)`（复用现有权限点）
- 入参 `@NotBlank`/`@NotNull` 校验；出参 `DataResult<SyncProgressVO>`
- VO：`status / triggerSource / total / completed / currentRepo / failedCount / startTime / endTime`；`status=none` 时其余字段 null
- 纯新增接口，无既有契约变化

## 5. 与代次中断机制的兼容性分析

### 5.1 中断窗口（旧代次任务持锁未退出 + 新代次任务已提交）

新任务 `tryLock(0)` 失败 → 放弃并 `inFlight--`。**已知限制**（prod 既有行为，本次不改）：此时"按新配置重跑"静默丢失，等下次触发。根因是 `waitTime=0`，修复需改变入口语义，范围外单独设计。

### 5.2 超长同步（>30min）

租约过期后另一触发源可进入（串行假设被打破）——prod 既有行为。本次修复其**次生缺陷**：unlock 抛异常导致的 inFlight 泄漏（§4.3）。是否启用 watchdog（leaseTime=-1）范围外单独讨论。

### 5.3 锁 key 统一

job step2/step8 必须复用 `PROJECT_SYNC_LOCK_PREFIX` 同一 key；进度 Hash 与锁 key 相互独立。滚动发布期新旧版本 key 一致，跨版本互斥成立。

## 6. 前端设计（openlibing-web）

### 6.1 轮询与按钮状态机（views/Repos/index.vue）

单一轮询循环，三个激活源（任一激活即轮询）：

- **提交激活**：点击提交成功（或返回"正在同步"被拒）→ 按钮 `disabled+loading`，启动轮询
- **进入页面激活**：`onMounted` 首查——`running` 则与提交激活行为一致（覆盖页面刷新丢状态）；首查即 `finished`/`none` 不刷新列表
- **悬浮激活**：popover `@show` 查询，`running` 则激活轮询

串行轮询：上一次响应返回后再延时 2s（finally 中 setTimeout 链式调度，非 setInterval），任意时刻最多一个在途请求；单次失败忽略、下轮继续。

状态流转（完全由服务端 status 驱动）：

```
running   → 更新进度展示，继续轮询
finished  → 停止轮询 + 按钮恢复 + 自动刷新仓库列表一次 + success 提示
none      → 停止轮询 + 按钮恢复（不提示；覆盖"另一实例同步中但 Hash 过期"的误恢复）
组件卸载 → 清理定时器
```

- 无独立超时上限：以 status 变化为准，异常场景由 30min TTL 自然终止；误恢复再点击由后端 Redisson 锁拒绝，正确性不依赖前端

### 6.2 结构与样式

- 进度 popover 挂在按钮**外层 wrapper 元素**（disabled 后 mouseenter 不触发，挂外层保证悬浮可用）
- 弹层内容：running → `el-progress` + "已完成 x/y" + "正在同步：{currentRepo}" + 失败数（>0 红色）+ 触发方式（手动/定时任务）；finished → 完成态；none → 空闲文案
- 自定义样式用全局 style 按 popper-class 控制（teleport 到 body，scoped 无法命中，项目已知约束）

### 6.3 API 层

- `src/api/Repos/url.ts` 新增 `SYNC_PROGRESS = CODE_REPO + '/project-repo/sync-progress'`
- `src/api/Repos/api.ts` 新增 `querySyncProgress`

## 7. 安全设计

- 新接口项目级横向越权校验（REPO_QUERY 权限点）+ 参数校验
- 互斥沿用 Redisson RLock（holder 校验由 Redisson 保证，finally 以 `isHeldByCurrentThread` 防御）
- Redis key 由 Integer projectId 拼接，无注入面；进度数据不含 accessToken

## 8. 性能设计

- 轮询 2s 一次单 key 读，finished/none 即停；崩溃场景最坏持续至 TTL（约 900 次读，可忽略）
- 后端逐仓 HINCRBY/HSET 单 key 操作，微秒级；EXPIRE 续期合并进写操作
- 进度 Hash 30min TTL，无长期驻留 key；XxlJob 跳过策略保证手动同步不拖住整轮定时任务

## 9. 影响范围

| 文件                                                                             | 变更                                                                                                                                                    |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| coderepo `business/service/SyncProgressService` + `impl/SyncProgressServiceImpl` | 新增（**仅进度**）                                                                                                                                      |
| coderepo `business/vo/SyncProgressVO`                                            | 新增                                                                                                                                                    |
| coderepo `business/controller/RepoController`                                    | 新增 sync-progress 接口                                                                                                                                 |
| coderepo `business/service/RepoService` + `impl/RepoServiceImpl`                 | submitProjectSyncTask 埋点 + finally 重排；runProjectSyncSteps setTotal；syncAllRepoInfoFromRemote 每仓埋点 + 删 projectLockMap；新增 querySyncProgress |
| coderepo `common/job/XxlJobHandler`                                              | step2 按项目聚合重构（Redisson 锁 + 进度埋点）；step8 追加 Redisson 锁                                                                                  |
| coderepo 测试                                                                    | SyncProgressServiceImplTest；RepoServiceImplTest 适配                                                                                                   |
| web `src/api/Repos/{url,api}.ts`                                                 | 新增查询 API                                                                                                                                            |
| web `src/views/Repos/index.vue`                                                  | popover + 轮询状态机 + 按钮状态                                                                                                                         |

## 10. 明确不做（范围外，记录待单独设计）

- Redisson watchdog（leaseTime=-1 自动续期）
- 分支级进度、SSE 推送
- XxlJob step3~7 全局 token 步骤的锁与进度
- `repoLockMap`（分支级内存锁）

> v3 调整：原"token 变更重跑丢失窗口（waitTime=0）"与"step1 锁与进度"已由 §11 R2/R3 落地，从本清单移除。

## 11. 验收反馈调整（v3）

### 11.1 R1：XxlJob step2 同步口径对齐手动链路

**问题**：step2 只同步 project_repo_info ∩ repo_info 的 URL 交集，repo_info 独有仓（未配置组织/平台仓记录缺失）永远不被 job 链路刷新。

**方案**：

- `collectSyncTasks` 聚合返回两类任务（URL 命中任务与未命中仓）：
  - `matched`：URL 命中的（platform, repoInfo, projectRepo）三元组，**按 repoId 去重**（同一仓 URL 命中多个 `platform:org` 条目——如同时配置 gitee 组织+企业——只计一次），沿用现有"拷贝状态/可见性 + 刷分支"动作
  - `unmatchedRepos`：repo_info 中未被任何条目命中的仓，改走手动同款平台 API 全量刷新
- `RepoServiceImpl` 抽取手动链路单仓同步体为 `syncSingleRepoInfoFromRemote(repoInfo, projectId, userName)`（平台 API 刷新仓信息 + syncRepoBranch），手动 forEach 与 job 共用；进度埋点（setCurrentRepo/incrCompleted）留在调用方循环
- **total = matched.size() + unmatched.size() = repo_info 该项目全量仓数，与手动链路 `setTotal(repoInfoEntities.size())` 严格相等**
- 顺序：先 matched 后 unmatched，全部纳入锁内与进度计数

### 11.2 R2：syncRepoInfoHandler 参数化（projectId 过滤）

- 复用 `refreshWebhookHandler` 的 `parseJobParam` 模式：`projectId=123`，非法值 `XxlJobHelper.handleFail` 退出
- 作用范围：step1、step2、step5-6（token 元信息刷新）、step8（SIG）的项目列表按 projectId 过滤
- step3（initTokenSource）/step4（initGiteeTokenStatus）/step7（markExpiredTokensAsInvalid）为全局表级操作，不随参数过滤
- 不传参数行为与现状完全一致

### 11.3 R3：全局配置提交 → 可靠的「中断在途 + 按新配置重跑」

**历史逻辑与缺陷**：`updateGlobalConfig`（sig 路径或公共账号变更 → needSync）→ `submitProjectSyncTask`（代次+1，注释声称"中断在途+重跑"）→ 但在途任务持锁期间新任务 `tryLock(0)` 必败被丢弃，且旧任务仅 2 个粗检查点（step1 全量平台同步后 / sig 同步后）退出缓慢 → 配置变更后重跑实际失效。

**方案**（两处组合）：

1. **细化中断粒度**：`syncAllRepoInfoFromRemote` 每仓循环前增加代次检查点（generation 下传），被取代即 break，锁秒级释放（覆盖最耗时的平台同步阶段）
2. **重跑等待锁**：`submitProjectSyncTask` 增加 `lockWaitSeconds` 重载——全局配置触发与 token 变更触发传 **60s**（旧任务中断释放锁后新任务接续执行）；页面手动入口保持 0（立即反馈"正在同步"）

**时序**：配置保存（gen+1 → 新任务等待锁）→ 旧任务下个仓边界检测代次过期 → break → finally `inFlight-- → finishProgress → unlock` → 新任务获锁 → `isProjectSyncCurrent` 通过 → initProgress → 按新配置全链路重跑。旧任务的 finishProgress 先于新任务 initProgress（锁串行保证顺序），前端进度条短暂 finished→running 属预期。

**残余风险（接受）**：旧任务若恰在 sig 扫描等无细粒度检查点阶段持锁超 60s，重跑仍被放弃（warn 日志明确）。sig 逐仓检查点扩散面大，不做。

### 11.4 测试补充

- `XxlJobHandlerTest`：unmatched 仓走平台 API 同步 + total 口径；`projectId=xxx` 过滤生效/非法参数；重复 URL 多条目命中去重
- `RepoServiceImplTest`：代次检查点中断（stale generation break）；`lockWaitSeconds` 重载行为；`syncSingleRepoInfoFromRemote` 抽取后手动链路行为不变
