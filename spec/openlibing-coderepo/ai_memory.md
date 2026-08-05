# openlibing-coderepo — AI 可复用经验

> 本文件沉淀经过验证且未来会复用的规则。一次性实现细节不入此文件，归各 task_design 的 archive.md。

## Webhook 事件处理

### 重复投递去重：优先业务幂等，慎用 Redis 限流

- handler 内部已有幂等机制（`INSERT IGNORE` / 唯一索引 / 按业务主键删除）时，**不要再叠加 Redis 限流**，避免限流 key 粒度过粗导致合法事件丢失。
- 若必须限流，限流 key 必须覆盖完整业务维度（如 `repoUrl + branchName + operation`），**禁止仅用 `repoUrl`**。`webhook:push:sync:{repoUrl}` 形式的 key 会丢失同一仓库下不同分支 / 不同操作的并发事件（已在 webhook-event-enhancement 任务中验证并修复）。
- `PushEventHandler#handle` 当前依赖 `RepoServiceImpl#syncSingleBranch` 的幂等性兜底，无 Redis 限流。

### Push 事件 payload 跨平台差异

| 平台 | 事件类型（请求头值） | 仓库 URL 字段 | 分支新增判定 | 分支删除判定 |
|------|-------------------|--------------|------------|------------|
| gitcode | `Push Hook`（`X-GitCode-Event`） | `repository.git_http_url` | `before` 全 0 | `after` 全 0 |
| gitee | `Push Hook`（`X-Gitee-Event`） | `repository.git_http_url` | `created=true`，缺失回退 `before` 全 0 | `deleted=true`，缺失回退 `after` 全 0 |
| github | `push`（`X-GitHub-Event`） | `repository.clone_url`（带 `.git`）/ `repository.html_url`（无后缀） | `created=true` | `deleted=true` |

- 覆写 `WebHookEventHandler#supportedEventTypes()` 返回多值集合（如 `{Push Hook, push}`）即可让单 handler 处理多平台事件类型，无需改 dispatcher。
- 本地 `repo_info.repo_url` 由用户录入，格式可能带/不带 `.git`，github 需用 `clone_url` 和 `html_url` 双候选依次反查。
- 普通 commit 推送：`created=false` 且 `deleted=false`（或 `before`/`after` 均非 0），handler 应跳过。

### 既有 webhook 配置补齐

- 新增 webhook 事件订阅（如 push）时，除了在新建仓库自动配置时启用，还需在 `XxlJobHandler#refreshWebhookHandler` 中检测既有 webhook 并用 **PATCH 原地更新**，避免删除重建影响其他订阅。
- 本地 / beta 环境跳过 webhook 订阅检查（环境无外网回调或仓库未注册）。
- gitcode / gitee 用 `RepoWebhook.setIsPushEvents(true)`；github 用 `events` 数组追加 `push`。

## Webhook 入口 MQ 异步化

- Controller 鉴权后直接 `rabbitTemplate.convertAndSend` 发 MQ，不再调 `service.handleWebhookEvent`；Service 改为同步 dispatch（去掉 `CompletableFuture.runAsync`），异步由 Consumer 提供。
- 消费失败重试复用 `NotifyConsumer` 模式：`MAX_RETRY=3`，`BACKOFF_MS={1000, 5000, 15000}`，try-catch 内重试，超限 ACK 丢弃并记录错误日志。
- 消息序列化用 `fastjson2`（`JSON.toJSONString` / `JSON.parseObject`），与 `NotifyConsumer` 处理 `NotifyMessageDTO` 一致。
- 不引入死信队列（webhook 事件无延迟投递需求）。

## 数据库与幂等

- `repo_branch` 表唯一索引保证分支记录唯一，新增用 `INSERT IGNORE` 静默跳过重复。
- 增量同步单分支删除按 `repoId + branchName`，避免 `deleteByIds` 需先查询拿 `branchId` 的两次 SQL。
- `is_default` 字段在 push payload 中无信息，新增分支时置 `0`，准确性由 `XxlJobHandler` 定时全量同步兜底修正。
