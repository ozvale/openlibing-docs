# Webhook 事件链路增强 — 技术设计

## 方案概述

本次改动包含两个独立但相关的功能：

1. **Push 事件处理器**：新增 `PushEventHandler` 实现 `WebHookEventHandler` 接口，监听 `Push Hook` / `push` 事件，判定分支新增/删除后调用 `RepoServiceImpl#syncSingleBranch` 增量同步单条分支记录。重复投递由 `syncSingleBranch` 自身的幂等性兜底（新增 `INSERT IGNORE`、删除按 `repoId + branchName`），**不引入 Redis 限流**。整体复用既有 webhook 处理器模式与系统账号约定。

2. **Webhook 入口 MQ 异步化**：在 `WebHookEventController` 与 `WebHookEventService` 之间插入 RabbitMQ 消息队列：Controller 鉴权通过后把 `WebhookEventDTO` 序列化为 JSON 投递到持久化队列，新增 `WebhookEventConsumer` 消费消息并调用 `WebHookEventService.handleWebhookEvent` 执行事件分发。消费失败按退避策略重试，超过最大次数后丢弃并记录错误日志。

## 架构决策

### 功能一：Push 事件处理器

| 决策 | 选择 | 原因 |
|------|------|------|
| 事件类型字符串 | `Push Hook`（gitcode/gitee）+ `push`（github） | gitcode/gitee webhook 请求头 `X-GitCode-Event` / `X-Gitee-Event` 在 push 事件下取值为 `Push Hook`；github 请求头 `X-GitHub-Event` 取值为小写 `push`。两者风格不同，需同时支持 |
| 分发匹配方式 | 覆写 `supportedEventTypes()` 返回 `{Push Hook, push}` 集合 | `WebHookEventHandler` 接口已提供 `supportedEventTypes()` 默认方法（返回单值集合），`WebHookEventServiceImpl#dispatchEvent` 已用 `contains` 匹配。覆写为多值集合即可让一个 handler 处理多平台事件类型，无需改 dispatcher |
| 同步入口 | 新增 `RepoServiceImpl#syncSingleBranch`，**增量**同步单条分支 | 全量同步 `syncRepoBranch` 每次都要调用平台 API 拉取全部分支，对高频 push 场景压力过大且容易触发平台限流；webhook 已明确知道新增/删除的是哪条分支（`ref` 字段），直接增删该条记录即可。`syncSingleBranch` 只操作本地 `repo_branch` 表，不调用平台 API，性能与稳定性更优 |
| 系统账号标识 | `"system"` | 与 `XxlJobHandler#syncRepoBranchData` 一致 |
| branchName 解析 | `ref.substring("refs/heads/".length())` | webhook payload 的 `ref` 形如 `refs/heads/feat-x`，去掉前缀即为分支名 |
| is_default 处理 | 新增分支时置 `0` | push payload 不含默认分支信息；该字段准确性由 `XxlJobHandler` 定时全量同步兜底修正，不依赖 webhook |
| 分支新增 SQL | 复用 `insertRepoBranch`（已 `INSERT IGNORE`） | 既有 XML 已用 `INSERT IGNORE INTO repo_branch ...`，唯一索引冲突时静默跳过，符合 webhook 重复投递幂等性要求 |
| 分支删除 SQL | 新增 `deleteByRepoIdAndBranchName` | 既有 `deleteByIds` 需先 `queryByRepoIdAndBranchName` 拿 `branchId`，两次 SQL 浪费；按 `repoId + branchName` 直接删一次即可 |
| token 获取 | 不再需要 | 增量同步不调用平台 API，无需 `accessToken`，`PushEventHandler` 不再注入 `CommonService` |
| **去重策略（修订）** | **依赖 `syncSingleBranch` 幂等性，不引入 Redis 限流** | 原方案参照 `NotifyConfigEventHandler#acquireYamlCheckLock` 用 Redis `trySet` 3 分钟限流。实施后发现：限流 key 仅用 `repoUrl`，导致**同一仓库不同分支的新增/删除事件、或同一仓库不同操作事件（新增+删除）在 3 分钟窗口内被静默丢弃**。改为依赖 `syncSingleBranch` 自身的幂等性（新增 `INSERT IGNORE` 静默跳过重复记录、删除按 `repoId + branchName` 幂等），既保证重复投递安全，又不丢失不同分支/操作的事件 |
| 分支判定 | `ref` 以 `refs/heads/` 开头 + `created`/`deleted` 布尔字段或 before/after 全 0 | gitcode 标准 push payload 用 before/after 全 0；gitee / github 优先用 `created`/`deleted` 布尔字段，更准确，缺失时回退 before/after 全 0 |
| tag 排除 | `ref` 不以 `refs/tags/` 开头即跳过 | tag 推送不触发分支同步 |
| 仓库 URL 反查 | 依次尝试 `git_http_url` → `clone_url` → `html_url` | gitcode/gitee payload 用 `git_http_url`；github payload 无该字段，用 `clone_url`（带 `.git`）和 `html_url`（无后缀）。本地 `repo_url` 由用户录入，格式不确定，多候选依次反查提高命中率 |
| github webhook 事件订阅 | `events` 由 `["pull_request"]` 改为 `["pull_request", "push"]` | github webhook 配置用 `events` 数组（不同于 gitcode/gitee 的 `is_push_events` 布尔位），需显式加入 `push` |
| 既有 webhook push 订阅补齐 | `XxlJobHandler#refreshWebhookHandler` 自动检测并 PATCH 原地更新 | 已注册的 webhook 可能缺 push 事件订阅，刷新时用 PATCH 原地更新而非删除重建，避免影响既有订阅；本地/beta 环境跳过订阅检查 |

### 功能二：Webhook 入口 MQ 异步化

#### 决策 1：Controller 前置发 MQ，而非 Service 层替换

- **选择**：Controller 三个方法鉴权后直接发 MQ，不再调 `service.handleWebhookEvent`
- **原因**：用户明确要求「给接口入口做前置处理」。Controller 层发 MQ 能最快返回响应，避免 Service 层任何同步逻辑阻塞 HTTP 线程
- **影响**：`WebHookEventServiceImpl.handleWebhookEvent` 保留但改为同步执行（供 Consumer 调用），去掉原来的 `CompletableFuture.runAsync`

#### 决策 2：复用 RabbitMQ 基础设施，不引入新依赖

- **选择**：复用现有 `RabbitConnectionFactoryConfig` 提供的 `RabbitTemplate` 和监听器容器工厂模式
- **原因**：项目已有成熟的 RabbitMQ 配置（连接工厂、发布确认、退回回调），`NotifyRabbitConfig` + `NotifyConsumer` 提供了完整的队列/消费者模式参考
- **影响**：新增独立的 `WebhookRabbitConfig`（队列配置）和 `WebhookEventConsumer`（消费者），复用 `RabbitTemplate`

#### 决策 3：简单队列，不引入交换机/死信队列

- **选择**：使用默认交换机（`""`）+ 持久化队列，routing key = 队列名
- **原因**：webhook 事件只有一种消费场景，无需复杂路由。失败重试在 Consumer 内用 try-catch + 退避实现（与 `NotifyConsumer` 一致），不需要死信队列
- **对比**：`NotifyRabbitConfig` 用了死信队列是因为有延迟投递需求（TTL 到期转发），webhook 事件无此需求

#### 决策 4：消息序列化用 fastjson2

- **选择**：`WebhookEventDTO` 用 `JSON.toJSONString` 序列化为 JSON 字符串，Consumer 用 `JSON.parseObject` 反序列化
- **原因**：与 `NotifyConsumer` 处理 `NotifyMessageDTO` 的方式一致；`WebhookEventDTO` 是纯 POJO（String + Map<String,String>），可安全序列化

#### 决策 5：复用 NotifyConsumer 的重试模式

- **选择**：MAX_RETRY=3，BACKOFF_MS={1000, 5000, 15000}，try-catch 内重试，超限丢弃
- **原因**：与 `NotifyConsumer.processOneWithRetry` 保持一致，项目内统一重试策略
- **不引入幂等锁**：webhook 事件本身幂等，各 handler 内部有去重逻辑（如 `PushEventHandler` 依赖 `syncSingleBranch` 幂等，`MergeRequestEventHandler` 的事件去重）

## 涉及文件

| 文件 | 操作 | 归属功能 | 说明 |
|------|------|----------|------|
| `business/handler/PushEventHandler.java` | 新增 | 功能一 | Push 事件处理器，覆写 `supportedEventTypes()` 返回 `{Push Hook, push}`，URL 反查兼容 gitcode/gitee/github，从 `ref` 解析 branchName 后调 `syncSingleBranch`；无 Redis 限流 |
| `business/service/impl/RepoServiceImpl.java` | 修改 | 功能一 | 新增 `syncSingleBranch(repo, userName, branchName, isCreated, isDeleted)` 增量同步方法；新增私有 `buildRepoBranchInfoEntity(repo, userName, branchName)` 重载；gitcode/gitee `setIsPushEvents(true)`；github `events` 加 `push` |
| `business/mapper/RepoBranchInfoMapper.java` | 修改 | 功能一 | 新增 `deleteByRepoIdAndBranchName(repoId, branchName)` |
| `resources/mapper/RepoBranchInfoMapper.xml` | 修改 | 功能一 | 新增 `deleteByRepoIdAndBranchName` SQL |
| `common/job/XxlJobHandler.java` | 修改 | 功能一 | `refreshWebhookHandler` 自动补齐 push 事件订阅（PATCH 原地更新，本地/beta 跳过） |
| `business/entity/webhooks/RepoWebhook.java` | 修改 | 功能一 | `pushEvents` 相关字段调整 |
| `test/.../handler/PushEventHandlerTest.java` | 新增 | 功能一 | 单元测试 17 用例（gitcode/gitee/github × 新增/删除/普通推送/tag 推送/未注册仓库/重复投递/不同分支+操作/空 body/字段缺失回退/URL 兜底反查） |
| `.gitignore` | 修改 | 功能一 | 忽略 `.gitcode/workflows/*.yaml` |
| `business/controller/WebHookEventController.java` | 修改 | 功能二 | 三个方法：鉴权后构造 DTO，调 `rabbitTemplate.convertAndSend` 发 MQ，返回「事件接收成功」 |
| `business/service/impl/WebHookEventServiceImpl.java` | 修改 | 功能二 | `handleWebhookEvent` 去掉 `CompletableFuture.runAsync`，改为直接同步调 `dispatchEvent`；返回值简化为成功/失败 |
| `common/config/rabbitmq/WebhookRabbitConfig.java` | 新增 | 功能二 | 持久化队列 Bean，队列名从 `${spring.rabbitmq.coderepo.webhook_event_queue}` 读取 |
| `business/service/WebhookEventConsumer.java` | 新增 | 功能二 | `@RabbitListener` 消费消息，反序列化后调 `webhookEventService.handleWebhookEvent`，失败重试 |
| `src/main/resources/application.yaml` | 修改 | 功能二 | 增加 `spring.rabbitmq.coderepo.webhook_event_queue: webhook_event_queue_beta` |
| `src/main/resources/application-gama.yaml` | 修改 | 功能二 | 增加 `webhook_event_queue_gama` |
| `src/main/resources/application-prod.yaml` | 修改 | 功能二 | 增加 `webhook_event_queue_prod` |
| `test/.../service/WebhookEventConsumerTest.java` | 新增 | 功能二 | Consumer 单元测试 6 用例：正常消费 / 重试成功 / 超限丢弃 / 非法 JSON / 空 body / 失败结果触发重试 |
| `test/.../controller/WebHookEventControllerTest.java` | 修改 | 功能二 | 适配 MQ 改造 |
| `test/.../service/impl/WebHookEventServiceImplTest.java` | 修改 | 功能二 | 适配同步 dispatch 改造 |

## 关键代码结构

### PushEventHandler（功能一）

```java
@Component
public class PushEventHandler implements WebHookEventHandler {
  private static final String PUSH_HOOK = "Push Hook";
  private static final String PUSH_HOOK_GITHUB = "push";
  private static final String REFS_HEADS_PREFIX = "refs/heads/";
  private static final String ZERO_SHA = "0000000000000000000000000000000000000000";
  private static final String SYSTEM_USER = "system";

  @Autowired private RepoInfoMapper repoInfoMapper;
  @Autowired private RepoServiceImpl repoService;   // 不再注入 CommonService / OpenlibingRedis

  @Override
  public String supportedEventType() { return PUSH_HOOK; }

  @Override
  public Set<String> supportedEventTypes() {
    return new HashSet<>(Arrays.asList(PUSH_HOOK, PUSH_HOOK_GITHUB));
  }

  @Override
  public void handle(WebhookEventDTO event) {
    try {
      // 1. 解析 body
      // 2. extractCandidateUrls: git_http_url / clone_url / html_url
      // 3. findRegisteredRepo: 依次 selectByUrl 反查，未命中则 info 返回
      // 4. isBranchRef(ref): ref 必须以 refs/heads/ 开头（排除 tag）
      // 5. created / deleted 判定（gitee/github 优先用布尔字段，gitcode 或缺失回退 before/after 全 0）
      //    - 普通 commit 推送：created=false 且 deleted=false，跳过
      // 6. extractBranchName(ref) → branchName
      // 7. repoService.syncSingleBranch(repoInfo, SYSTEM_USER, branchName, created, deleted)
      //    —— 重复投递由 syncSingleBranch 幂等性兜底，不做 Redis 限流
    } catch (Exception e) {
      LOGGER.error("Error handling push event, repoType:{}", event.getRepoType(), e);
    }
  }
}
```

### RepoServiceImpl#syncSingleBranch（功能一）

```java
public void syncSingleBranch(
    RepoInfoEntity repoInfoEntity, String userName, String branchName,
    boolean isCreated, boolean isDeleted) {
  // 1. 参数校验 + isCreated/isDeleted 互斥校验
  // 2. 校验仓库是否仍然存在（queryById）
  // 3. isCreated=true:
  //      buildRepoBranchInfoEntity(repo, userName, branchName)  // is_default="0"
  //      repoBranchInfoMapper.insertRepoBranch(entity)         // INSERT IGNORE 静默跳过重复
  // 4. isDeleted=true:
  //      repoBranchInfoMapper.deleteByRepoIdAndBranchName(repoId, branchName)
}
```

### WebhookEventConsumer（功能二）

```java
@Component
public class WebhookEventConsumer {
    private static final int MAX_RETRY = 3;
    private static final long[] BACKOFF_MS = {1_000L, 5_000L, 15_000L};

    @Autowired private WebHookEventService webHookEventService;

    @RabbitListener(queues = "${spring.rabbitmq.coderepo.webhook_event_queue}")
    public void onMessage(Message message) {
        // 反序列化 → processWithRetry
    }

    private void processWithRetry(WebhookEventDTO dto) {
        // 循环 MAX_RETRY 次，调 service.handleWebhookEvent
        // 成功（result.ok()）返回，失败/异常按 BACKOFF_MS 退避后重试
        // 超限记录错误日志，ACK 丢弃
    }
}
```

## 数据流

```
平台 webhook
  ↓ HTTP POST
WebHookEventController.gitCodeWebhookEvent
  ↓ 鉴权（machineInterfaceAuthUtil）
  ↓ 构造 WebhookEventDTO
  ↓ rabbitTemplate.convertAndSend("", webhookEventQueue, msg)  [持久化]
  ↓ 返回 DataResult.successMessage("事件接收成功")

RabbitMQ: webhook_event_queue_<env>
  ↓ 持久化存储

WebhookEventConsumer.onMessage
  ↓ 反序列化 JSON → WebhookEventDTO
  ↓ webhookEventService.handleWebhookEvent(dto)  [同步]
  ↓   └→ dispatchEvent: 遍历 handlers，匹配 eventType 调用 handler.handle
  ↓        ├→ MergeRequestEventHandler  (Merge Request Hook)
  ↓        ├→ NotifyConfigEventHandler  (...)
  ↓        └→ PushEventHandler            (Push Hook / push)  ← 功能一新增
  ↓              ├→ gitcode/gitee: git_http_url 反查
  ↓              ├→ github: clone_url / html_url 反查
  ↓              ├→ isBranchRef / isBranchCreated / isBranchDeleted 判定
  ↓              ├→ extractBranchName(ref) → branchName
  ↓              └→ repoService.syncSingleBranch(repo, "system", branchName, created, deleted)
  ↓                    ├→ isCreated=true: INSERT IGNORE repo_branch (is_default='0')
  ↓                    └→ isDeleted=true: DELETE FROM repo_branch WHERE repo_id=? AND branch_name=?
  ↓                    （重复投递由 INSERT IGNORE / 单分支删除幂等性兜底，无 Redis 限流）
  ↓ 失败 → 重试（MAX_RETRY=3, BACKOFF={1s,5s,15s}）
  ↓ 超限 → 记录错误日志，ACK 消息（丢弃）
```

## 风险 & 缓解

### 功能一：Push 事件处理器

| 风险 | 缓解 |
|------|------|
| webhook 短时间大量重复推送 | `syncSingleBranch` 幂等性兜底：新增 `INSERT IGNORE` 静默跳过重复记录，删除按 `repoId + branchName` 幂等。不再使用 Redis 限流，避免限流粒度过粗丢失不同分支/操作事件 |
| 仓库未注册到本系统 | `selectByUrl` 返回 null 时 info 并返回，不抛异常 |
| gitcode/gitee/github payload 字段差异 | 分支判定优先用 `created`/`deleted` 布尔字段（gitee/github），缺失时回退 before/after 全 0（gitcode 标准） |
| github 仓库 URL 字段与 gitcode/gitee 不同 | 依次尝试 `git_http_url` → `clone_url` → `html_url`，覆盖三平台 payload |
| 本地 `repo_url` 录入格式不确定（带/不带 `.git`） | github 用 `clone_url`（带 `.git`）和 `html_url`（无后缀）双候选反查，提高命中率 |
| 普通 commit 推送误触发 | 严格判定 before/after 全 0 或 created/deleted 为 true，普通推送两者均非 0 且布尔字段缺失，自然跳过 |
| 重复 webhook 投递导致重复插入 | `insertRepoBranch` 已用 `INSERT IGNORE`，唯一索引冲突静默跳过 |
| 增量同步导致 `is_default` 不准 | push payload 无默认分支信息，新增分支时 `is_default` 置 `0`；该字段准确性由 `XxlJobHandler` 定时全量同步兜底修正 |
| 仓库在事件投递后被删除 | `syncSingleBranch` 入口和写库前都校验 `repoInfoMapper.queryById`，不存在则跳过 |
| 平台 API 与本地数据漂移 | 增量同步只覆盖 push 事件覆盖的分支；全量同步由 `XxlJobHandler` 定时任务兜底，两套机制互补 |
| 既有 webhook 缺 push 订阅 | `XxlJobHandler#refreshWebhookHandler` 自动检测并用 PATCH 原地更新，不删除重建影响既有订阅 |

### 功能二：Webhook 入口 MQ 异步化

| 风险 | 缓解 |
|------|------|
| RabbitMQ 不可用导致 webhook 事件丢失 | `RabbitTemplate` 已配置发布确认 + 退回回调（`PubConfirmHandler`），投递失败会记录错误日志。Controller 层捕获异常返回失败，平台会按自身重试策略重发 |
| Consumer 处理慢导致消息堆积 | 复用 `RabbitConnectionFactoryConfig` 的并发消费参数（concurrent=5, max=20, prefetch=5），可动态扩展 |
| 消息反序列化失败 | Consumer 捕获 `JSONException`，记录错误日志后 ACK 丢弃，避免毒消息阻塞队列 |
| 事件重复消费 | 各 handler 内部有去重逻辑（PushEventHandler 依赖 `syncSingleBranch` 幂等、MergeRequestEventHandler 的事件去重），无需 Consumer 层幂等 |
| 服务重启时未消费消息 | 队列持久化 + 消息持久化（`MessageDeliveryMode.PERSISTENT`），重启后继续消费 |

## 跨仓影响

无。改动仅限 `openlibing-coderepo` 单仓，不涉及其他仓的接口或契约变化。
