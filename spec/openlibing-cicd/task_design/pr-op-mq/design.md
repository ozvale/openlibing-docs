# pr-op-mq — 技术设计

## 方案概述

新增 `pr_op_event_exchange`（DirectExchange）+ `pr_op_event_queue`（TTL 24h，复用现有 `dead_exchange` 死信）一条主 MQ 链路；以及 `pr_op_event_delay_exchange`（DirectExchange）+ `pr_op_event_delay_queue_30s`（TTL 30s，DLX=`pr_op_event_exchange`）一条 30s 延迟重试链路。

`PipelineServiceImpl.savePipelineInfoWithAsyncPrOps` 改为发消息到主队列，`PrOpEventConsumer` 异步消费并调用 `PipelineService.reflashPrInfo` 执行 `updatePrLabel` / `reflashCommentPipelineInfo` / `pushGitCodeCommitStatus` 三步。

捕获 `ThirdPartyApiRateLimitException` / `ThirdPartyApiTimeoutException` 时，**原消息 ACK**，将消息体重新发布到 30s 延迟队列，30s 后通过 DLX 自动路由回主队列重试，**绕过 Spring AMQP 默认的 3 次重试链路**，避免在第三方接口抖动期重试放大问题。

整体沿用现有 `PipelineStatusUpdateProducer.sendTimeoutRetry` + 60s 延迟队列的模式，仅 TTL 改为 30s（与 `PipelineEventRabbitConfig` 中 `pipelineStatusDelayQueue30s` 一致）。

## 架构决策

1. **新建独立 exchange / queue，不复用 `pipeline_event_exchange`**：PR 异步操作链路独立清晰，便于后续独立监控队列积压、单独扩缩容、单独路由策略。
2. **新建独立延迟 exchange / queue，不复用 `pipelineStatusDelayExchange` / `pipelineStatusDelayQueue30s`**：现有 `pipelineStatusDelayQueue30s` 的 DLX 是 `pipelineStatusExchange`，DLX 必须是 `pr_op_event_exchange` 才能让延迟消息回到 PR 主队列；无法复用。新建 `pr_op_event_delay_exchange` + `pr_op_event_delay_queue_30s`。
3. **TTL 选 30s**：与 `PipelineEventRabbitConfig` 中现有的 `pipelineStatusDelayQueue30s`（TTL=30s，DLX=pipelineStatusExchange）保持一致；30s 足够让第三方限流 / 超时窗口过去，又不会让用户等待过久。
4. **直接序列化 `PipelineParamDTO` 作为消息载荷，不新建独立 DTO**：`reflashPrInfo` 三个步骤需要 `accessToken` / `owner` / `repo` / `repoType` / `prId` / `commitId` / `status` / `pipelineRunId` / `projectId` / `pipelineId` 等大量字段，新建一个等价的 DTO 反而是冗余；`PipelineParamDTO` 字段全为简单类型 + 已实现 Serializable 子结构，Gson 序列化/反序列化无问题。
5. **`reflashPrInfo` 改为 `public` 并通过 `PipelineService` 接口暴露**：Consumer 与 Service 跨包（`business.listener` ↔ `business.service.impl`），直接调 impl 类会绕开 Spring AOP 代理；走 `PipelineService` 接口更规范。
6. **限流/超时异常走 30s 延迟队列而非 Spring AMQP 默认重试**：与现有 `PipelineStatusUpdateConsumer` 处理 `ThirdPartyApiTimeoutException | ThirdPartyApiRateLimitException` 的策略一致——使用专门的延迟重试通道，避免在第三方接口抖动期重试放大问题。
7. **复用现有 `dead_exchange` / `dead_queue` 死信链路**：主队列 24h TTL，过期后进死信；与 `auto_create_issue_queue` / `pipeline_fail_email_queue` 一致。
8. **异常分类处理**：`JsonSyntaxException`（消息体损坏，不可恢复）→ 记录日志后直接 return（不抛出，不触发重投，避免死循环）；`IllegalArgumentException` / 其他业务异常 → 原样抛出，触发 Spring AMQP 重试和死信机制。
9. **Consumer 并发度 5**：与 `PipelineEventConsumer` 中其他 PR 流水线相关 consumer 的 `concurrency = "5"` 保持一致。
10. **不为限流/超时异常加最大重试次数限制**：与现有 `sendTimeoutRetry` 60s 模式保持一致；如果第三方持续返回 429，消息会持续每 30s 重试，符合"让限流自动恢复"的预期。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `common/config/rabbitmq/PipelineEventRabbitConfig.java` | 修改 | 新增 6 个 `@Value` 字段 + 6 个 Bean（主队列 3 + 延迟队列 3） |
| `business/service/PipelineService.java` | 修改 | 接口新增 `void reflashPrInfo(PipelineParamDTO param)` |
| `business/service/impl/PipelineServiceImpl.java` | 修改 | 注入 `PipelineEventProducer`；`reflashPrInfo` 改为 `public @Override`；`savePipelineInfoWithAsyncPrOps` 改为调 `sendPrOpEvent` |
| `business/service/impl/PipelineEventProducer.java` | 修改 | 新增 `sendPrOpEvent` / `sendPrOpEventTimeoutRetry` 两个方法 + 4 个 `@Value` 字段 |
| `business/listener/PrOpEventConsumer.java` | 新增 | 监听 `pr_op_event_queue`，反序列化 + 调 service，捕获限流/超时异常重发延迟队列 |
| `src/main/resources/application.yaml` | 修改 | 新增 6 个 `_beta` 后缀 key |
| `src/main/resources/application-gama.yaml` | 修改 | 新增 6 个 `_gama` 后缀 key |
| `src/main/resources/application-prod.yaml` | 修改 | 新增 6 个 `_prod` 后缀 key |
| `src/test/java/.../listener/PrOpEventConsumerTest.java` | 新增 | 7 个单元测试覆盖关键合约 |

## MQ 拓扑

```text
[PipelineServiceImpl.savePipelineInfoWithAsyncPrOps]
        |
        | sendPrOpEvent(param)  # Gson.toJson(param)
        v
[pr_op_event_exchange] --routingKey=pr_op_event_key--> [pr_op_event_queue]
                                                                   |
                                                                   | x-dead-letter-exchange = dead_exchange
                                                                   | x-dead-letter-routing-key = dead_key
                                                                   | x-message-ttl = 24h
                                                                   v
                                                            [PrOpEventConsumer]
                                                                   |
                                                                   | pipelineService.reflashPrInfo(param)
                                                                   |
                                                +------------------+------------------+
                                                |                                     |
                                                v                                     v
                                  [正常 ACK]                          [ThirdPartyApiRateLimitException
                                                |                       / ThirdPartyApiTimeoutException]
                                                |                                     |
                                       [updatePrLabel]                                | sendPrOpEventTimeoutRetry(json, runId)
                                       [reflashCommentPipelineInfo]                   |
                                       [pushGitCodeCommitStatus]                      v
                                                                  [pr_op_event_delay_exchange]
                                                | --routingKey=pr_op_event_delay_key_30s--> [pr_op_event_delay_queue_30s]
                                                |                                                |
                                                |                                                | x-message-ttl = 30s
                                                |                                                | x-dead-letter-exchange = pr_op_event_exchange
                                                |                                                | x-dead-letter-routing-key = pr_op_event_key
                                                |                                                v
                                                |                                  (30s 后 DLX 自动路由回 pr_op_event_queue)
                                                |                                                |
                                                +------------------------------------------------+
                                                                                [重新进入 PrOpEventConsumer 重试]

   [pr_op_event_queue] --(reject/expire)--> [dead_exchange] --(dead_key)--> [dead_queue]
```

### Bean 配置

```java
// 主队列
@Bean
public DirectExchange prOpEventExchange() {
    return directExchange(prOpEventExchange).durable(true).build();
}

@Bean
public Queue prOpEventQueue() {
    return durable(prOpEventQueue)
        .deadLetterExchange(deadExchange)
        .deadLetterRoutingKey(deadKey)
        .ttl(TTL) // 24小时
        .build();
}

@Bean
public Binding prOpEventBinding() {
    return bind(prOpEventQueue()).to(prOpEventExchange()).with(prOpEventKey);
}

// 30s 延迟队列
@Bean
public DirectExchange prOpEventDelayExchange() {
    return directExchange(prOpEventDelayExchange).durable(true).build();
}

@Bean
public Queue prOpEventDelayQueue30s() {
    return durable(prOpEventDelayQueue30s)
        .deadLetterExchange(prOpEventExchange)
        .deadLetterRoutingKey(prOpEventKey)
        .ttl(30_000)
        .build();
}

@Bean
public Binding prOpEventDelayBinding30s() {
    return bind(prOpEventDelayQueue30s()).to(prOpEventDelayExchange()).with(prOpEventDelayKey30s);
}
```

### 环境配置

`application.yaml`（beta）：
```yaml
spring:
  rabbitmq:
    cicd:
      pr_op_event_exchange: pr_op_event_exchange_beta
      pr_op_event_queue: pr_op_event_queue_beta
      pr_op_event_key: pr_op_event_key_beta
      pr_op_event_delay_exchange: pr_op_event_delay_exchange_beta
      pr_op_event_delay_queue_30s: pr_op_event_delay_queue_30s_beta
      pr_op_event_delay_key_30s: pr_op_event_delay_key_30s_beta
```

`application-gama.yaml`：`..._gama` 后缀；`application-prod.yaml`：`..._prod` 后缀。

> 实际生产值由 Apollo 配置中心覆盖（与现有 MQ 配置一致）。

## 消息载荷

`PipelineParamDTO` 完整 JSON（字段：projectName / projectId / pipelineId / pipelineRunId / accessToken / repoType / owner / repo / prId / retryNum / isRetry / status / commitId / gitcodeRepoId / gitcodeHookId / sourceBranch / userName / pipelineName / RunNumber / configJson / tableData）。

> 注意：`accessToken` 是敏感字段；`PrOpEventConsumer` 的 INFO 日志只打 `pipelineRunId` / `status`，不打印全量消息体，无敏感泄露风险。延迟重试时直接转发原消息 JSON，不重新打日志。

## 业务流程

```text
recordPipelineInfo(param)
  ...
  └─ savePipelineInfoWithAsyncPrOps(param)
        ├─ LOGGER.info(...)  # 记录入口
        └─ if (checkPrParam(param)):
              pipelineEventProducer.sendPrOpEvent(param)
                    └─ gson.toJson(param)  →  PERSISTENT message
                            → rabbitTemplate.convertAndSend(prOpEventExchange, prOpEventKey, msg)

[MQ 异步]
PrOpEventConsumer.handlePrOpEvent(messageJson)
  ├─ gson.fromJson(messageJson, PipelineParamDTO.class)
  ├─ if (param == null || pipelineRunId == null) → 丢弃
  ├─ LOGGER.info(...)
  ├─ try pipelineService.reflashPrInfo(param)
  │     ├─ updatePrLabel(param)
  │     ├─ reflashCommentPipelineInfo(param)
  │     └─ pushGitCodeCommitStatus(param)
  ├─ catch ThirdPartyApiRateLimitException | ThirdPartyApiTimeoutException:
  │     └─ pipelineEventProducer.sendPrOpEventTimeoutRetry(messageJson, pipelineRunId)
  │           └─ rabbitTemplate.convertAndSend(prOpEventDelayExchange, prOpEventDelayKey30s, msg)
  │     # 30s 后 DLX 自动回到 pr_op_event_queue
  ├─ catch JsonSyntaxException:
  │     └─ LOGGER.error(...) + return
  └─ catch Exception:
        └─ LOGGER.error(...) + throw  (Spring AMQP 重试 + 死信)
```

## 前置校验

- `param` 为 null 或 `param.getPipelineRunId()` 为空 → 记录 ERROR 日志后丢弃（不抛，不重投）。
- `JsonSyntaxException`（消息体损坏）→ 记录 ERROR 日志后丢弃（不抛，不重投）。
- `ThirdPartyApiRateLimitException` / `ThirdPartyApiTimeoutException` → 记录 WARN 日志后调用 `sendPrOpEventTimeoutRetry`（**不抛**，原消息 ACK）。
- 其他业务异常 → 记录 ERROR 日志后**原样抛出**，触发 Spring AMQP 重试和死信队列机制。

## 错误处理

| 异常类型 | 处理 | 触发重投 | 触发死信 | 触发 30s 延迟重试 |
|----------|------|---------|---------|-----------------|
| 反序列化结果为 null | LOGGER.error 后 return | 否 | 否 | 否 |
| `param.pipelineRunId` 为空 | LOGGER.error 后 return | 否 | 否 | 否 |
| `JsonSyntaxException` | LOGGER.error 后 return | 否 | 否 | 否 |
| `ThirdPartyApiRateLimitException` | LOGGER.warn + sendPrOpEventTimeoutRetry | 否 | 否 | 是（30s 后） |
| `ThirdPartyApiTimeoutException` | LOGGER.warn + sendPrOpEventTimeoutRetry | 否 | 否 | 是（30s 后） |
| 其他 Exception | LOGGER.error 后 throw | 是 | TTL 过期或超出重试次数后 | 否 |

## 测试

`PrOpEventConsumerTest` 7 个用例：

1. **正常消息**：Gson 序列化 `PipelineParamDTO` → 消费 → `verify(pipelineService).reflashPrInfo(any())`。
2. **空消息**：传入字符串 `"null"` → Gson 解析为 null → LOGGER.error 后 return，**不调** service / producer。
3. **非法 JSON**：传入 `"{not valid json}"` → `JsonSyntaxException` 被 catch，**不调** service / producer，**不抛**。
4. **缺 pipelineRunId**：序列化仅含 `status` 的 DTO → LOGGER.error 后 return，**不调** service / producer。
5. **限流异常**：mock `pipelineService.reflashPrInfo` 抛 `ThirdPartyApiRateLimitException` → consumer **不抛**，调 `pipelineEventProducer.sendPrOpEventTimeoutRetry(messageJson, runId)`。
6. **超时异常**：mock `pipelineService.reflashPrInfo` 抛 `ThirdPartyApiTimeoutException` → consumer **不抛**，调 `pipelineEventProducer.sendPrOpEventTimeoutRetry(messageJson, runId)`。
7. **其他业务异常**：mock `pipelineService.reflashPrInfo` 抛 `RuntimeException` → consumer **原样抛出** 供 Spring AMQP 重试。

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| 第三方接口持续返回 429，消息无限重试 | 与现有 `sendTimeoutRetry` 60s 模式行为一致；限流恢复后自动消化；后续可加最大重试次数 |
| 队列积压导致 `accessToken` 过期 | 主队列 TTL 24h + 死信兜底；Consumer 端不打印敏感字段 |
| `PipelineParamDTO` 字段演进导致反序列化失败 | Gson 默认忽略未知字段，新增字段不会破坏旧消息；删除字段需谨慎 |
| 延迟队列 TTL 修改后旧队列仍存在 | RabbitMQ 不支持动态修改队列 TTL（项目硬约束）；如需调整必须先删除再重建 |
| 30s 延迟比 60s 更激进，可能在持续抖动期重试过快 | 30s 与现有 `pipelineStatusDelayQueue30s` 一致；可通过 yaml 调整 |
| Consumer 注入 `PipelineService` 接口走 Spring 代理 | `reflashPrInfo` 是普通方法（非 `@Transactional`），代理与否不影响行为 |

## 跨仓影响

无。仅 `openlibing-cicd` 单仓改动。
