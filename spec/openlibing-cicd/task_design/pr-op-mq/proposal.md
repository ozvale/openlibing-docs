# pr-op-mq

## 需求背景

`PipelineServiceImpl.savePipelineInfoWithAsyncPrOps` 中调用的 `reflashPrInfo` 同步执行三件外部 API 操作：

1. `updatePrLabel`：调用 GitCode / Gitee 等 PR 标签接口
2. `reflashCommentPipelineInfo`：更新 PR 报告评论
3. `pushGitCodeCommitStatus`：推送 GitCode Commit Status

这三步都属于外部 HTTP 调用，单次耗时可能 100ms~数秒，且当任一平台抖动时会把主流程的 `recordPipelineInfo` 拖慢、放大 PR 流水线的监控时延。

此外，第三方接口在高峰期可能出现**限流（HTTP 429）** 或**超时（SocketTimeout / ConnectTimeout）** 异常。如果用默认的 3 次重试链路，瞬时重试只会进一步压垮第三方接口，反而放大问题。

## 功能描述

将 `reflashPrInfo` 改造为异步执行：

1. **新增 MQ 队列 `pr_op_event_queue`**：DirectExchange + 队列，与 `auto_create_issue` / `pipeline_fail_email` 同模式，独立 binding 路由键 `pr_op_event_key`。
2. **新增 30s 延迟队列 `pr_op_event_delay_queue_30s`**：DirectExchange `pr_op_event_delay_exchange` + 队列，TTL=30s，过期后通过 DLX 自动路由回主队列 `pr_op_event_queue` 重试。专门用于 `ThirdPartyApiRateLimitException` / `ThirdPartyApiTimeoutException` 异常场景。
3. **新增 `PrOpEventConsumer`**：监听主队列，接收 JSON 化的 `PipelineParamDTO`，反序列化后调用 `PipelineService.reflashPrInfo`；捕获限流/超时异常后**原消息 ACK**，重新发布到 30s 延迟队列，绕过普通重试链路。
4. **改造 `PipelineServiceImpl.savePipelineInfoWithAsyncPrOps`**：将同步调用 `reflashPrInfo` 改为调用 `PipelineEventProducer.sendPrOpEvent(param)` 发消息。
5. **暴露 `reflashPrInfo` 为 public 方法**：通过 `PipelineService` 接口暴露，供 Consumer 注入调用；删除原 `// todo: 改造成发送消息` / `// todo: 改造成接收消息` 注释。
6. **复用现有 `dead_exchange` 作为主队列死信交换机**：主队列 24h TTL，过期后进死信。

### 消息载荷

直接序列化 `PipelineParamDTO`（Gson），消费者端反序列化为 `PipelineParamDTO` 调用 `reflashPrInfo`。`PipelineParamDTO` 字段均为简单类型 + `PipelineInfoEntity.ConfigJson` + `Map<String, List<CommentTableVo>>`，Gson 均可正常序列化/反序列化。

### 异常路由策略

| 异常 | 处理路径 | 触发行为 |
|------|---------|---------|
| `JsonSyntaxException` | 丢弃 | 记录 ERROR 日志后 return |
| `param.pipelineRunId == null` | 丢弃 | 记录 ERROR 日志后 return |
| `ThirdPartyApiRateLimitException` (429) | 30s 延迟队列 | 重新发布到 `pr_op_event_delay_queue_30s`，30s 后 DLX 回到主队列重试 |
| `ThirdPartyApiTimeoutException` | 30s 延迟队列 | 同上 |
| 其他 Exception | Spring AMQP 默认重试 + 死信 | 原样抛出 |

## 不做什么

- 不修改 `updatePrLabel` / `reflashCommentPipelineInfo` / `pushGitCodeCommitStatus` 三个私有方法的内部实现。
- 不修改 `PipelineService` 接口的其他方法。
- 不修改 `PipelineEventProducer` 已有的 6 个发送方法（`sendBisectTask` / `sendNeedDownloadFile` / `sendAnalyzeBuildJobEvent` / `sendAnalyzePipelineDetailEvent` / `sendQueryQueueTimeEvent` / `sendAutoCreateIssueEvent` / `sendPipelineFailEmailEvent`）。
- 不修改任何 RabbitMQ 连接工厂、监听器容器工厂、消息转换器配置。
- 不修改任何业务 DTO 字段。
- 不为限流/超时异常加最大重试次数限制（与现有 `PipelineStatusUpdateProducer.sendTimeoutRetry` 60s 模式保持一致）。

## 验收标准

- [ ] `PipelineEventRabbitConfig` 新增 `prOpEventExchange` / `prOpEventQueue` / `prOpEventBinding` 三个 Bean。
- [ ] `PipelineEventRabbitConfig` 新增 `prOpEventDelayExchange` / `prOpEventDelayQueue30s` / `prOpEventDelayBinding30s` 三个 Bean，延迟队列 TTL=30s、DLX=`pr_op_event_exchange`、DLRK=`pr_op_event_key`。
- [ ] `PipelineService` 接口新增 `void reflashPrInfo(PipelineParamDTO param)` 方法。
- [ ] `PipelineServiceImpl` 注入 `PipelineEventProducer` 并把 `reflashPrInfo` 改为 `public` 加 `@Override`。
- [ ] `savePipelineInfoWithAsyncPrOps` 改为调用 `pipelineEventProducer.sendPrOpEvent(param)`。
- [ ] `PipelineEventProducer.sendPrOpEvent(param)` 序列化整个 `PipelineParamDTO` 并发送到 `pr_op_event_exchange / pr_op_event_key`。
- [ ] `PipelineEventProducer.sendPrOpEventTimeoutRetry(messageJson, pipelineRunId)` 发送原消息 JSON 到 `pr_op_event_delay_exchange / pr_op_event_delay_key_30s`。
- [ ] `PrOpEventConsumer` 捕获 `ThirdPartyApiRateLimitException` / `ThirdPartyApiTimeoutException` 后调用 `sendPrOpEventTimeoutRetry` 并 return（不抛出）。
- [ ] 三套环境 yaml 同步新增 `pr_op_event_exchange` / `pr_op_event_queue` / `pr_op_event_key` / `pr_op_event_delay_exchange` / `pr_op_event_delay_queue_30s` / `pr_op_event_delay_key_30s` 六个 key（后缀分别为 `_beta` / `_gama` / `_prod`）。
- [ ] `PrOpEventConsumerTest` 7 个用例全部通过：正常消息 / 空消息 / 非法 JSON / 缺 `pipelineRunId` / **限流异常** / **超时异常** / 其他业务异常。
- [ ] 其他 listener 测试无回归（`PipelineStartEventHandlerTest` / `PipelineStopEventHandlerTest` / `PipelineRetryEventHandlerTest`）。

## 影响范围

### 业务仓 `openlibing-cicd`

| 文件 | 操作 | 说明 |
|------|------|------|
| `common/config/rabbitmq/PipelineEventRabbitConfig.java` | 修改 | 新增 6 个 `@Value` 字段 + 6 个 Bean（主队列 3 + 延迟队列 3） |
| `business/service/PipelineService.java` | 修改 | 接口新增 `void reflashPrInfo(PipelineParamDTO param)` |
| `business/service/impl/PipelineServiceImpl.java` | 修改 | 注入 `PipelineEventProducer`；`reflashPrInfo` 改为 `public @Override`；`savePipelineInfoWithAsyncPrOps` 改为调 `sendPrOpEvent` |
| `business/service/impl/PipelineEventProducer.java` | 修改 | 新增 2 个方法（`sendPrOpEvent` / `sendPrOpEventTimeoutRetry`）+ 4 个 `@Value` 字段 |
| `business/listener/PrOpEventConsumer.java` | 新增 | 监听 `pr_op_event_queue`，反序列化 + 调 service，捕获限流/超时异常重发延迟队列 |
| `src/main/resources/application.yaml` | 修改 | 新增 6 个 `_beta` 后缀 key |
| `src/main/resources/application-gama.yaml` | 修改 | 新增 6 个 `_gama` 后缀 key |
| `src/main/resources/application-prod.yaml` | 修改 | 新增 6 个 `_prod` 后缀 key |
| `src/test/java/.../listener/PrOpEventConsumerTest.java` | 新增 | 7 个单元测试覆盖关键合约 |

### docs 仓 `openlibing-docs`

| 文件 | 操作 | 说明 |
|------|------|------|
| `spec/openlibing-cicd/task_design/pr-op-mq/proposal.md` | 新增 | 本文件 |
| `spec/openlibing-cicd/task_design/pr-op-mq/design.md` | 新增 | 详见 `design.md` |
| `spec/openlibing-cicd/task_design/pr-op-mq/tasks.md` | 新增 | 详见 `tasks.md` |
