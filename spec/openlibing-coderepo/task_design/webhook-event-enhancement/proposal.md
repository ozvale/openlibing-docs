# Webhook 事件链路增强 — 分支同步 + MQ 异步化

## 业务 Issue

- Chenmingxu/openlibing-coderepo#1 — Push 事件处理器（分支新增/删除自动同步）
- Chenmingxu/openlibing-coderepo#2 — Webhook 入口 MQ 异步化
- https://gitcode.com/Chenmingxu/openlibing-coderepo/issues/1
- https://gitcode.com/Chenmingxu/openlibing-coderepo/issues/2

## 需求背景

`openlibing-coderepo` 的 webhook 链路存在两个独立但相关的问题，本次一并解决：

### 问题一：分支新增/删除不会自动同步

当前 webhook 仅监听 `Merge Request Hook` 事件处理 PR 检视。当代码仓发生**分支新增 / 删除**时，本地仓库分支信息不会自动同步，需用户手动触发 `RepoController#syncRepoBranchInfo`。实际使用中容易遗忘，导致本地分支视图与远端不一致，影响分支策略、codecheck 触发等下游业务。

### 问题二：webhook 入口同步处理存在可靠性缺陷

`WebHookEventController` 三个入口方法（`gitCodeWebhookEvent` / `giteeWebhookEvent` / `githubWebhookEvent`）鉴权通过后，同步调用 `WebHookEventServiceImpl.handleWebhookEvent`，后者用 `CompletableFuture.runAsync` 做进程内异步分发。该方案存在：

- **无持久化**：服务重启时正在处理的 webhook 事件会丢失
- **无削峰**：高并发推送时默认 ForkJoinPool 可能被打满，导致事件处理延迟或被拒绝
- **无重试**：处理器抛异常后事件直接丢弃，无法恢复

项目已有成熟的 RabbitMQ 基础设施（`NotifyRabbitConfig` + `NotifyConsumer` + `RabbitConnectionFactoryConfig`），可直接复用。

## 功能描述

### 功能一：Push 事件处理器（关联 Issue #1）

参照 `MergeRequestEventHandler` 与 `NotifyConfigEventHandler` 的实现模式，新增 `PushEventHandler`，监听 gitcode / gitee / github 平台的 Push 事件：

1. 仓库 URL 反查：依次尝试 `repository.git_http_url`（gitcode/gitee）、`repository.clone_url`、`repository.html_url`（github），命中已注册仓库即处理；未注册仓库安全跳过。
2. 仅当 push 事件为分支新增或删除时触发同步：
   - `ref` 必须以 `refs/heads/` 开头（排除 tag 推送）
   - 分支新增：gitee / github 优先用 `created=true`，gitcode 或该字段缺失时回退 `before` 全 0
   - 分支删除：gitee / github 优先用 `deleted=true`，gitcode 或该字段缺失时回退 `after` 全 0
3. **增量同步**：命中后从 `ref` 解析分支名（去掉 `refs/heads/` 前缀），调用 `RepoServiceImpl#syncSingleBranch(repoInfoEntity, "system", branchName, isCreated, isDeleted)`：
   - 分支新增：构造 `RepoBranchInfoEntity` 并 `INSERT IGNORE`（`is_default` 置 `0`，push payload 无默认分支信息，待下次全量同步修正）；记录已存在则静默跳过
   - 分支删除：按 `repoId + branchName` 删除单条 `repo_branch` 记录
   - **不再调用** `syncRepoBranch` 全量拉取平台 API 分支列表，避免每次 push 都对平台 API 发起一次完整分支查询
4. **重复投递幂等**：依赖 `syncSingleBranch` 自身的幂等性兜底（新增用 `INSERT IGNORE`，删除按 `repoId + branchName`），**不引入 Redis 限流去重**。原方案的「同一仓库 3 分钟内 Redis 限流」在实施中被移除，原因见 `archive.md`「设计偏差与取舍」。
5. 启用仓库自动配置 webhook 时的 push 事件订阅：
   - gitcode / gitee：`RepoWebhook.setIsPushEvents(true)`
   - github：`events` 列表由 `["pull_request"]` 改为 `["pull_request", "push"]`
   - `XxlJobHandler#refreshWebhookHandler` 自动补齐 push 事件订阅，本地 / beta 环境跳过订阅检查，已注册但缺 push 订阅的 webhook 用 PATCH 原地更新（不删除重建）
6. 事件类型匹配：覆写 `supportedEventTypes()` 返回 `{Push Hook, push}`，同时支持 gitcode/gitee 的 `Push Hook`（`X-GitCode-Event` / `X-Gitee-Event` 请求头）与 github 的 `push`（`X-GitHub-Event` 请求头）。

### 功能二：Webhook 入口 MQ 异步化（关联 Issue #2）

给 `WebHookEventController` 三个入口方法做前置处理：鉴权通过后将 `WebhookEventDTO` 投递到 RabbitMQ，由独立的 Consumer 异步消费，执行原有的事件分发逻辑。

- Controller 三个方法鉴权后改为发 MQ 消息（不再直接调 `service.handleWebhookEvent`）
- 新增 `WebhookRabbitConfig`：配置 webhook 事件队列（持久化）
- 新增 `WebhookEventConsumer`：消费 MQ 消息，调用 `WebHookEventService.handleWebhookEvent` 执行分发
- `WebHookEventServiceImpl.handleWebhookEvent` 调整：去掉 `CompletableFuture.runAsync`，改为同步执行 `dispatchEvent`（Consumer 已提供异步消费）
- 消费失败自动重试（复用 `NotifyConsumer` 的 MAX_RETRY=3 + BACKOFF={1s,5s,15s} 模式）
- 补充 `application.yaml` / `application-gama.yaml` / `application-prod.yaml` 队列配置
- 补充单元测试

## 不做

- 标签（tag）推送事件处理
- 普通 commit 推送（非分支新增/删除）触发同步
- 跨仓影响（仅限 `openlibing-coderepo`）
- 修改既有 `MergeRequestEventHandler` / `NotifyConfigEventHandler` 逻辑
- 修改 `RepoController#syncRepoBranchInfo` 接口签名
- 不改变 Controller 的鉴权逻辑和请求头解析
- 不改变 `WebHookEventHandler` 接口和各 handler 实现（含 PushEventHandler）
- 不引入死信队列（失败重试在 Consumer 内用 try-catch + 退避实现，与 NotifyConsumer 一致）
- **不引入 Redis 限流去重**（webhook 事件本身幂等，重复投递由 `syncSingleBranch` 的 `INSERT IGNORE` + 单分支删除幂等性兜底）

## 验收标准

### 功能一：Push 事件处理器

- [x] gitcode 平台：分支新增事件触发 `syncSingleBranch(repo, "system", branchName, true, false)`，仅插入该分支
- [x] gitcode 平台：分支删除事件触发 `syncSingleBranch(repo, "system", branchName, false, true)`，仅删除该分支
- [x] gitee 平台：分支新增事件触发 `syncSingleBranch` 增量插入
- [x] gitee 平台：分支删除事件触发 `syncSingleBranch` 增量删除
- [x] github 平台：分支新增事件触发 `syncSingleBranch` 增量插入
- [x] github 平台：分支删除事件触发 `syncSingleBranch` 增量删除
- [x] github 平台：`clone_url` 反查未命中时用 `html_url` 兜底命中
- [x] 普通 commit 推送（非分支新增/删除）**不**触发同步
- [x] 标签（tag）推送**不**触发同步
- [x] 仓库未注册到本系统时安全跳过，不抛异常
- [x] **同一仓库重复 push 事件**：两次事件都触发 `syncSingleBranch`，由 `INSERT IGNORE` / 单分支删除幂等性兜底，不被错误丢弃
- [x] **同一仓库不同分支 / 不同操作（新增+删除）事件**：均独立触发同步，不互相影响（原 Redis 限流方案会丢失这类事件）
- [x] 分支新增：传入 `branchName` 从 `ref` 中正确解析（`refs/heads/feat-x` → `feat-x`）
- [x] 分支新增：`is_default` 置 `0`（push payload 无默认分支信息）
- [x] 分支新增：记录已存在时 `INSERT IGNORE` 静默跳过，不抛异常
- [x] 分支删除：按 `repoId + branchName` 删除单条记录
- [x] gitcode / gitee 新建仓库自动配置 webhook 时 `push_events` 已启用（`setIsPushEvents(true)`）
- [x] github 新建仓库自动配置 webhook 时 `events` 包含 `push`
- [x] `XxlJobHandler#refreshWebhookHandler` 自动补齐缺 push 订阅的既有 webhook（PATCH 原地更新，本地/beta 跳过检查）
- [x] `PushEventHandler.supportedEventTypes()` 同时包含 `Push Hook` 与 `push`
- [x] 新增 `PushEventHandler` 单元测试覆盖上述场景（共 17 个用例）

### 功能二：Webhook 入口 MQ 异步化

- [x] 三个 webhook 入口鉴权通过后，事件被投递到 RabbitMQ 队列
- [x] Consumer 收到消息后正确调用对应 handler 处理事件
- [x] 消费失败时按退避策略重试，超过最大次数后记录错误日志并丢弃
- [x] 消息持久化，服务重启不丢失未消费的消息
- [x] 现有 `MergeRequestEventHandler` / `NotifyConfigEventHandler` / `PushEventHandler` 行为不变
- [x] 编译通过，新增 `WebhookEventConsumerTest` 6 个用例通过（正常消费 / 重试成功 / 超限丢弃 / 非法 JSON / 空 body / 失败结果触发重试）

## 影响范围

| 文件 | 操作 | 归属功能 | 说明 |
|------|------|----------|------|
| `business/handler/PushEventHandler.java` | 新增 | 功能一 | Push 事件处理器，支持 gitcode/gitee（`Push Hook`）与 github（`push`），增量同步，无 Redis 限流 |
| `business/service/impl/RepoServiceImpl.java` | 修改 | 功能一 | 新增 `syncSingleBranch` 增量同步方法；gitcode/gitee `setIsPushEvents(true)`；github `events` 加 `push` |
| `business/mapper/RepoBranchInfoMapper.java` | 修改 | 功能一 | 新增 `deleteByRepoIdAndBranchName` 方法 |
| `resources/mapper/RepoBranchInfoMapper.xml` | 修改 | 功能一 | 新增 `deleteByRepoIdAndBranchName` SQL |
| `common/job/XxlJobHandler.java` | 修改 | 功能一 | `refreshWebhookHandler` 自动补齐 push 事件订阅（PATCH 原地更新） |
| `business/entity/webhooks/RepoWebhook.java` | 修改 | 功能一 | `pushEvents` 字段相关调整 |
| `test/.../handler/PushEventHandlerTest.java` | 新增 | 功能一 | 单元测试 17 用例（含 github 场景，验证 `syncSingleBranch` 调用参数） |
| `.gitignore` | 修改 | 功能一 | 忽略 `.gitcode/workflows/*.yaml` |
| `business/controller/WebHookEventController.java` | 修改 | 功能二 | 三个方法鉴权后改为发 MQ |
| `business/service/impl/WebHookEventServiceImpl.java` | 修改 | 功能二 | 去掉 CompletableFuture.runAsync，改为同步 dispatch |
| `common/config/rabbitmq/WebhookRabbitConfig.java` | 新增 | 功能二 | 队列配置 |
| `business/service/WebhookEventConsumer.java` | 新增 | 功能二 | MQ 消费者 |
| `src/main/resources/application.yaml` | 修改 | 功能二 | 增加队列名配置 |
| `src/main/resources/application-gama.yaml` | 修改 | 功能二 | 增加队列名配置 |
| `src/main/resources/application-prod.yaml` | 修改 | 功能二 | 增加队列名配置 |
| `test/.../service/WebhookEventConsumerTest.java` | 新增 | 功能二 | Consumer 测试 6 用例 |
| `test/.../controller/WebHookEventControllerTest.java` | 修改 | 功能二 | 适配 MQ 改造 |
| `test/.../service/impl/WebHookEventServiceImplTest.java` | 修改 | 功能二 | 适配同步 dispatch 改造 |

- 业务仓：`openlibing-coderepo`
- 不涉及数据库 schema 变更
- 不涉及外部接口契约变化

## 流程模式

Standard 模式：合并 spec（proposal + design + tasks + archive）+ 实现 + 单元测试。
