# Webhook 事件链路增强 — 实现任务

## 进度: 13/13 complete

### 功能一：Push 事件处理器（关联 Issue #1）

- [x] Task 1: 新增 `PushEventHandler.java`，实现 `WebHookEventHandler` 接口，`supportedEventType()` 返回 `Push Hook`，覆写 `supportedEventTypes()` 返回 `{Push Hook, push}`
- [x] Task 2: 实现 `handle` 方法：解析候选 repoUrl 列表 → 依次反查 RepoInfoEntity → 分支判定 → 从 `ref` 解析 `branchName` → 调用 `syncSingleBranch(repoInfo, "system", branchName, created, deleted)`
- [x] Task 3: 实现辅助方法：`extractCandidateUrls`（git_http_url/clone_url/html_url）、`findRegisteredRepo`、`isBranchRef`、`isBranchCreated`、`isBranchDeleted`（兼容 gitcode/gitee/github）、`extractBranchName`（ref → branchName）
- [x] Task 4a: 新增 `RepoBranchInfoMapper#deleteByRepoIdAndBranchName` 接口方法 + XML SQL
- [x] Task 4b: 新增 `RepoServiceImpl#syncSingleBranch(repo, userName, branchName, isCreated, isDeleted)` 增量同步方法 + 私有 `buildRepoBranchInfoEntity(repo, userName, branchName)` 重载
- [x] Task 4c: 修改 `RepoServiceImpl.java` 自动配置 webhook 部分：gitcode/gitee `setIsPushEvents(true)`；github `events` 加 `push`；`XxlJobHandler#refreshWebhookHandler` 自动补齐既有 webhook 的 push 订阅（PATCH 原地更新，本地/beta 跳过）
- [x] Task 5: 新增 `PushEventHandlerTest.java`，覆盖 gitcode/gitee/github × 新增/删除/普通推送/tag 推送/未注册仓库/重复投递/不同分支+操作/空 body/字段缺失回退/URL 兜底反查，共 17 个场景，验证 `syncSingleBranch` 调用参数（branchName / isCreated / isDeleted）
- [x] Task 6: 编译验证 + 跑 `PushEventHandlerTest`

### 功能二：Webhook 入口 MQ 异步化（关联 Issue #2）

- [x] Task 7: 新增 `WebhookRabbitConfig.java`，配置持久化队列 Bean
- [x] Task 8: 新增 `WebhookEventConsumer.java`，实现 `@RabbitListener` 消费 + 重试逻辑
- [x] Task 9: 修改 `WebHookEventController.java`，三个方法鉴权后改为发 MQ
- [x] Task 10: 修改 `WebHookEventServiceImpl.java`，去掉 `CompletableFuture.runAsync`，改为同步 dispatch
- [x] Task 11: 修改 `application.yaml` / `application-gama.yaml` / `application-prod.yaml`，增加 `webhook_event_queue` 配置
- [x] Task 12: 新增 `WebhookEventConsumerTest.java`，覆盖正常消费/重试成功/超限丢弃/非法 JSON/空 body/失败结果触发重试 6 个场景
- [x] Task 13: 编译验证并运行测试

## 验证方式

### 功能一

- `mvn -pl . compile -DskipTests`（或 IDE 编译）通过
- `mvn -pl . test -Dtest=PushEventHandlerTest` 通过（17 用例）
- 不破坏既有 `MergeRequestEventHandlerTest` / `WebHookEventServiceImplTest`

### 功能二

- `mvn -o -DskipTests compile` 编译通过
- `mvn -o -Dtest=WebhookEventConsumerTest test` 测试通过（6 用例）
- 代码审查：确认 Controller 不再直接调 service.handleWebhookEvent，Consumer 正确调用 service

## 关联

- 业务 Issue 1: https://gitcode.com/Chenmingxu/openlibing-coderepo/issues/1
- 业务 Issue 2: https://gitcode.com/Chenmingxu/openlibing-coderepo/issues/2
- 业务分支: `feat-push-event-branch-sync`
- 关联 commit:
  - `5a34026` 代码仓webhook推送事件订阅以及响应（2026-07-21，初始交付）
  - `95f2880` UT问题修复（2026-07-27）
  - `0db17b1` webhook推送事件删除同一事件去重逻辑&代码风格修复（2026-07-30，移除 Redis 限流）
- 参考实现: `MergeRequestEventHandler` / `NotifyConfigEventHandler` / `NotifyRabbitConfig` / `NotifyConsumer`
- 调用入口: `RepoController#syncRepoBranchInfo` / `RepoServiceImpl#syncRepoBranch`
