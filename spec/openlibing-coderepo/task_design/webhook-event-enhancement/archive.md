# Webhook 事件链路增强 — 归档

## 关联

- 业务 Issue 1: https://gitcode.com/Chenmingxu/openlibing-coderepo/issues/1 （Push 事件处理器）
- 业务 Issue 2: https://gitcode.com/Chenmingxu/openlibing-coderepo/issues/2 （Webhook 入口 MQ 异步化）
- 业务分支: `feat-push-event-branch-sync`
- 业务 PR: 待创建（用户自测确认后进入 Phase 4）
- docs PR: 待创建（本归档提交后通过 `gitcode pr create` 发起）

## 交付历程

业务分支 `feat-push-event-branch-sync` 上 3 轮 webhook 相关 AI 编码交付（不含 master 合入与 codeql workflow 更新）：

- commit `5a34026` (2026-07-21) **代码仓webhook推送事件订阅以及响应** — 初始交付，新增 `PushEventHandler.java` (306 行) + `WebhookEventConsumer.java` (122 行) + `WebhookRabbitConfig.java` (37 行) + `RepoServiceImpl` 增量同步方法 (+346 行) + `RepoBranchInfoMapper.deleteByRepoIdAndBranchName` + 三套 application.yaml 队列配置 + `PushEventHandlerTest` (359 行) + `WebhookEventConsumerTest` (124 行)，共 15 文件 +1376/-8。初始方案含 Redis 限流。
- commit `95f2880` (2026-07-27) **UT问题修复** — 适配 `WebHookEventControllerTest` 与 `WebHookEventServiceImplTest`，2 文件 +10/-8。
- commit `0db17b1` (2026-07-30) **webhook推送事件删除同一事件去重逻辑&代码风格修复** — 移除 `PushEventHandler` 的 Redis 限流逻辑（`acquireSyncLock` / `SYNC_RATE_LIMIT_*` 常量 / `OpenlibingRedis` 依赖），改由 `syncSingleBranch` 自身幂等性兜底；同步更新 `PushEventHandlerTest`（移除 `testRateLimitSkipsSync`，新增 `testDuplicatePushEventBothTriggerSync` 与 `testDifferentBranchAndOperationEventsBothTriggerSync`）；代码风格修复。9 文件 +580/-609。

业务分支上还有 2 个 master 合入 commit 与 1 个 codeql workflow 更新（非 webhook 工作范围，不计入交付历程）：
- `4db5805` Merge master（含废弃接口清理）
- `0e812a3` Merge master
- `c0f4064` update codeql action

## 用户自测反馈

- **问题**：原方案对同一仓库 push 事件做 Redis `trySet` 3 分钟限流去重，限流 key 仅用 `repoUrl`。实测发现：同一仓库短时间内若发生**不同分支的新增/删除事件**、或**同一仓库不同操作事件（新增 + 删除）**，会被 3 分钟窗口内先到的事件独占 key，后到的事件被静默丢弃，导致本地分支视图与远端不一致。
- **修复**：commit `0db17b1` 移除 `PushEventHandler` 中 `acquireSyncLock` / `SYNC_RATE_LIMIT_MINUTES` / `SYNC_RATE_LIMIT_KEY_PREFIX` 常量与 `OpenlibingRedis` 字段依赖，改为完全依赖 `syncSingleBranch` 自身的幂等性兜底：
  - 分支新增：`insertRepoBranch` 已用 `INSERT IGNORE`，唯一索引冲突静默跳过
  - 分支删除：按 `repoId + branchName` 删除单条记录，重复投递结果幂等
- **测试更新**：移除 `testRateLimitSkipsSync`（原限流场景），新增 `testDuplicatePushEventBothTriggerSync`（验证重复投递两次都触发 syncSingleBranch）和 `testDifferentBranchAndOperationEventsBothTriggerSync`（验证不同分支/不同操作事件均触发同步，不被错误去重）。

## 最终验证

- **编译**：`mvn -o -DskipTests compile` 通过
- **单元测试**：`PushEventHandlerTest` 17 用例 + `WebhookEventConsumerTest` 6 用例全部通过
- **既有测试无回归**：`MergeRequestEventHandlerTest` / `WebHookEventServiceImplTest` / `WebHookEventControllerTest` 通过
- **静态约束自检**：
  - [x] 仅修改 `openlibing-coderepo` 业务仓与 `openlibing-docs` 归档仓
  - [x] 遵循目标仓既有 `WebHookEventHandler` 接口模式与 `NotifyConsumer` 重试模式
  - [x] 无硬编码凭证 / 敏感信息 / 危险默认值 / 注入风险
  - [x] 行为变化（移除限流）有匹配测试覆盖

## 设计偏差与取舍

| 偏差 | 原方案 | 实际交付 | 原因 |
|------|--------|----------|------|
| 去重策略 | Redis `trySet` 3 分钟限流，key = `webhook:push:sync:{repoUrl}` | 依赖 `syncSingleBranch` 自身幂等性（`INSERT IGNORE` + 单分支删除） | Redis 限流 key 仅用 `repoUrl` 粒度过粗，同一仓库不同分支/不同操作事件在 3 分钟窗口内被静默丢失；幂等兜底既保证重复投递安全，又不丢失合法事件 |

其余设计决策与原方案一致，无其他偏差。

## 可复用经验

1. **webhook 重复投递去重应优先用业务幂等性**：handler 内部已有幂等机制（`INSERT IGNORE` / 唯一索引 / 按业务主键删除）时，不要再叠加 Redis 限流，避免限流 key 粒度过粗导致合法事件丢失。
2. **限流 key 设计时必须覆盖业务维度**：若必须限流，key 应包含 `repoUrl + branchName + operation` 等业务字段，而非仅 `repoUrl`，否则会丢失同一资源下不同子维度的并发事件。
3. **Push 事件 payload 跨平台差异**：gitcode/gitee 用 `Push Hook` 事件类型 + `git_http_url` 字段 + `before`/`after` 全 0 判定；github 用 `push` 事件类型 + `clone_url`/`html_url` 字段 + `created`/`deleted` 布尔字段判定。覆写 `supportedEventTypes()` 返回多值集合即可让单 handler 处理多平台事件。
4. **既有 webhook 配置补齐**：新增事件订阅（如 push）时，除了在新建仓库时配置，还需在 `XxlJobHandler#refreshWebhookHandler` 中用 PATCH 原地更新既有 webhook，避免删除重建影响其他订阅；本地/beta 环境跳过订阅检查。

以上经验同步沉淀到 `openlibing-docs/spec/openlibing-coderepo/ai_memory.md`（新建）。

## 归档日期

2026-07-31
