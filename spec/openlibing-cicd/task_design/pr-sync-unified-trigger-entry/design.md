# Design · PR 同步统一触发模型 v2（实现版）

> 本文以实际代码实现为准，取代 2026-11-06 HTML 可视化设计与 2026-11-05 v1 文档中冲突描述。实现版与 HTML v2 的差异集中在「triggerEvent 事件词汇」，见第 9 节。

## 1. 方案设计

总体链路：

```
workflow on 监听配置（唯一事件开关）
  → 平台 PR 事件 / 评论
  → action 插件（组装触发请求：triggerEvent + commitId 反查补齐）
  → POST /pr-sync/trigger
  → openlibing-cicd（白名单校验 → 幂等 → PR 维度限流 → req_type 原样透传进 MQS → 插流水线记录 + msgId 落库）
  → 黄区消费端状态机（对账类三级对账 / 标记类改 MR 状态）
  → 结构化回执（msgId 绑定）
  → 插件统一轮询 → 回写标签 → 终态输出
```

一句话规则：`on.types` 里写了哪个 action，那个事件发生时流水线拉起并触发同步；没写的 action 事件根本不会进来。插件不配事件集合、不做过滤。紧急停用走插件输入 `trigger_enabled=false`（仅应急用）。

关键方案决策：

| 决策点        | 结论                                                                                                       | 理由                                                                                 |
| ------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 事件词汇      | 统一词汇五 action：open / reopen / update / merge / comment（插件归一化映射，cicd 白名单同词汇）           | 词汇全链路统一，屏蔽平台差异（如 GitHub closed+merged 二义性），语义由黄区状态机解释 |
| 接口契约      | `PrSyncTriggerReqDTO.triggerEvent` 可选，空白/缺省归一化为 comment                                         | 旧调用方零破坏                                                                       |
| req_type 决策 | cicd 不做语义决策：req_type = triggerEvent 原样透传                                                        | 类型语义唯一解释点在黄区状态机                                                       |
| 统一处理线    | 所有事件（含 merge）同一条路：触发即插记录、进轮询、回写标签至终态                                         | 删除 v1 生命周期旁路，消除双链路维护成本                                             |
| CLOSED 事件   | 插件侧 skipped（「无需处理」输出），不经触发接口                                                           | 关闭语义由 merge / 黄区标记类覆盖                                                    |
| commitId 来源 | payload sha/after（RepoContext.commitSha）；comment 无 sha 经 PR 详情反查 head sha；缺失时黄区降级重新同步 | commit_id 是黄区三级对账基准                                                         |

## 2. 实现逻辑设计

### 2.1 action 插件（openlibing/pr-sync-action，分支 feat-pr-sync-trigger-events）

- 事件归一化：`src/platform/event-normalizer.ts`，各平台 payload action → CanonicalEvent；GitHub `closed && merged===true` 特判为 MERGED。
- triggerEvent 映射：`src/main.ts` `CANONICAL_TO_TRIGGER_EVENT`：OPENED→open、REOPENED→reopen、SYNCHRONIZE→update、MERGED→merge、COMMENTED→comment；CLOSED 不映射，走 skipped 输出。
- 触发请求组装：`main.ts buildTriggerRequest`——PR 详情优先取 payload，缺失时经平台 API 按 PR 编号反查 global id 与分支（覆盖 comment 无 sha 场景），反查失败退化为纯轮询；`commitId = ctx.commitSha ?? detail.commitSha`（各 adapter 从 ATOMGIT_SHA / GITHUB_SHA / GITEE_COMMIT 取）。
- 统一链路：`main.ts` → `PrSyncService.run`：触发 POST `cross-region/pr-sync/trigger` → 首次轮询延迟 2 秒进入 Poller 统一轮询 `getPipelineInfo` → 回写 running/终态标签（`lastWrittenLabel` 去重，`pr-sync-service.ts`）→ 终态输出。无任何 SEND_OK 短路分支。
- 工作流输入（action.yml）：无 `trigger_events` 过滤输入；保留 openlibing_apig_url / debug / poll_* / ignore_failure / trigger_enabled / git_token / platform / label_* 等既有输入。

### 2.2 openlibing-cicd（分支 feat-pr-sync-trigger-events）

- 接口入口：`CrossRegionController#prSyncTrigger`（POST `/pr-sync/trigger`，APIG 等价 `/apig/v1/cross-region/pr-sync/trigger`），入参 `PrSyncTriggerReqDTO`（accessToken 已按安全要求 #335 移除）。
- `resolveTriggerEvent`（`CrossRegionServiceImpl`）：仅做空白→缺省 comment、trim/lowercase、白名单校验（open/reopen/update/merge/comment）；不解释语义、不映射 req_type。
- req_type 透传：`reqType = triggerEvent`，经 `sendPrSyncMessage` 原样写入 MQS，commit_id 随消息下发。
- 全 action 统一插记录：插 `YellowRegionPipelineEntity`，status=START、pipelineStatus=WAIT_START；MQS SEND_OK 后 `updateById` 绑定 msgId 落库；发送失败置 FAILURE、释放限流占位、返回 failureMessage。
- 幂等窗口（先于限流判定）：`queryLatestNonTerminalPipeline`，窗口内（默认 10 分钟）且记录带 msgId 的非终态记录 → 返回 `{msgId: 既有 msgId, sendStatus: SEND_OK}`；超窗或无 msgId 放行打断重建（`interruptNonTerminalPipeline`）。
- PR 维度限流：Redis key `cross-region:pr-sync:ratelimit:{org}:{repo}:{prNumber}`，`setIfAbsent` 60 秒（SET NX EX），窗口可配 `cross-region.pr-sync.rate-limit-window-seconds`；Redis 异常 fail-open。
- PR 元数据补全：`upsertTriggerPrInfo`。

## 3. 类设计

| 模块   | 类/文件                                                    | 职责                                                                                                                |
| ------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| cicd   | `CrossRegionController#prSyncTrigger`                      | 触发接口入口                                                                                                        |
| cicd   | `PrSyncTriggerReqDTO`                                      | 入参 DTO（含 triggerEvent，无 accessToken）                                                                         |
| cicd   | `CrossRegionService / CrossRegionServiceImpl`              | resolveTriggerEvent / 幂等 / 限流 / 插记录 / sendPrSyncMessage / upsertTriggerPrInfo / interruptNonTerminalPipeline |
| cicd   | `YelloRegionPipelineMapper#queryLatestNonTerminalPipeline` | 幂等窗口查询                                                                                                        |
| action | `src/main.ts`                                              | 事件映射、buildTriggerRequest、统一链路编排、终态输出                                                               |
| action | `src/platform/event-normalizer.ts`                         | 各平台 payload action → CanonicalEvent                                                                              |
| action | `src/services/pr-sync-service.ts`                          | 触发调用、轮询编排、标签回写（去重）                                                                                |
| action | `src/platform/{gitcode,github,gitee}-adapter.ts`           | 平台适配（sha 来源、PR 详情反查）                                                                                   |

## 4. 数据模型设计

无新增表、无 schema 迁移。复用 `yellow_region_pipeline`（流水线记录 + msgId 落库绑定）与 PR 元数据表。

## 5. 性能设计

复用既有防护能力：触发维度限流（同 org/repo/prNumber 60 秒固定窗口，Redis SET NX EX，异常 fail-open）；幂等窗口（10 分钟内带 msgId 的非终态记录视为重复触发直接返回既有 msgId）；插件轮询最小间隔 30 秒下限、首次轮询延迟 2 秒。

## 6. API 接口设计

### 6.1 触发接口

| 项   | 说明                                                                                                                                                                                                                      |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 路径 | POST `/pr-sync/trigger`（APIG 等价：POST `/apig/v1/cross-region/pr-sync/trigger`）                                                                                                                                        |
| 入参 | orgName、repoName、prNumber、prId、platform（gitcode/gitee/github，蓝区默认 gitcode）、sourceBranch、targetBranch、gitUrl、account、commitId、triggerEvent（可选，缺省 comment，合法值 open/reopen/update/merge/comment） |
| 校验 | orgName/repoName/prNumber/prId 必填；platform 白名单；triggerEvent 白名单（仅校验，不决策）                                                                                                                               |
| 响应 | 成功：DataResult 成功 + MqsResponseDTO（msgId、sendStatus=SEND_OK）；幂等命中：返回在途 msgId；失败：failureMessage（参数错误 / platform 非法 / 限流拒绝 / 发送失败）                                                     |

### 6.2 MQS 消息契约（黄区消费端）

- req_type 取值（实现版词汇）：open / reopen / update / merge / comment，与 triggerEvent 全链路一致、原样透传。
- 其余字段不变：org_name、repo_name、repo_type、br_name=目标分支、tgt_branch=源分支、pr_id、commit_id、account、timestamp、params；不携带 access_token。
- 黄区语义（状态机解释，可重放）：
  - 对账类（open / reopen / update / comment）：三级对账——① 目标仓临时分支 HEAD == commit_id？② MR 是否存在？③ 门禁流水线在跑/有结果？缺哪补哪；全满足标记 SKIPPED 并立即回执真实状态。
  - 标记类（merge）：目标 MR 状态置「已合入」，不做真实合并、不同步代码；幂等（重复标记=空操作）。
  - 两条铁律：重复消息不产生副作用；每条消息必有回执（msgId 绑定的统一结构化回执）。
  - coderepo webhook push 直发链路保持现状，与插件触发在黄区幂等共存。

## 7. 安全设计

沿用既有约束：MQS 消息不携带仓库令牌（黄区使用平台已授权令牌），DTO 的 accessToken 字段已移除（#335）；触发接口经 OIDC 认证（AppCode 静态凭证已禁用）；account 记录真实触发人，禁止回退 PR 作者造成误归属；黄区消费侧白名单校验为产品维度（映射产品下的有效用户，admin 全局账号跨产品放行，未加入产品或状态非有效即拒绝）。

## 8. 测试设计要点

关键边界：缺省 triggerEvent 等价 comment（回归保护）；非法值参数错误且不发 MQS、不插记录；merge 也统一插记录并绑定 msgId（与 v1 相反，勿沿用旧断言）；全事件均进轮询、无 SEND_OK 短路；幂等命中返回既有 msgId 且先于限流；MQS 失败置 FAILURE 并释放限流占位；先清旧标签再打 running、首返 running 不重复写；GitHub closed+merged→merge 不得误判 skipped；closed（非 merged）skipped 不调接口；comment 无 sha 反查 head sha，反查失败纯轮询；黄区三级对账全满足 SKIPPED 立即回执。

## 9. 与 HTML v2 设计的差异说明（以本文档为准）

| 差异点            | HTML v2 设计                                                               | 实际实现（采纳）                                                                               | 影响评估                                                                 |
| ----------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| triggerEvent 词汇 | 原始 payload action 名：opened / synchronize / commented / closed / merged | 统一词汇：open / reopen / update / merge / comment（normalizer 归一化映射，cicd 白名单同词汇） | 架构语义不变（仍透传、零决策）；词汇统一屏蔽平台差异，黄区契约按本表对齐 |
| closed 事件       | closed 也透传                                                              | 插件对 CLOSED 事件输出 skipped，不经触发接口                                                   | 关闭语义由 merge / 黄区标记类覆盖                                        |
| 事件归一化层      | v2 删除 MERGED 归一化                                                      | 保留（GitHub closed+merged 特判→MERGED）                                                       | 属词汇统一的一部分，非 v1 决策逻辑残留                                   |
| 限流命中行为      | 在途返回在途 msgId                                                         | 在途 msgId 由幂等窗口实现（返回既有 msgId + SEND_OK）；限流命中返回失败提示文案                | 行为更精细：重复触发拿到同一 msgId，限流防频次                           |
