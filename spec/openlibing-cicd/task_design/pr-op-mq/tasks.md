# pr-op-mq — 实现任务

## 进度: 11/11 complete

### MQ 配置

- [x] Task 1: 在 `PipelineEventRabbitConfig` 新增 3 个 `@Value` 字段（`prOpEventExchange` / `prOpEventQueue` / `prOpEventKey`）
- [x] Task 2: 在 `PipelineEventRabbitConfig` 新增 3 个 Bean（`prOpEventExchange` DirectExchange / `prOpEventQueue` Queue / `prOpEventBinding` Binding）
- [x] Task 11: 在 `PipelineEventRabbitConfig` 新增 3 个 `@Value` 字段（`prOpEventDelayExchange` / `prOpEventDelayQueue30s` / `prOpEventDelayKey30s`）
- [x] Task 12: 在 `PipelineEventRabbitConfig` 新增 3 个 Bean（`prOpEventDelayExchange` / `prOpEventDelayQueue30s` / `prOpEventDelayBinding30s`）

### 接口 & 核心 Service

- [x] Task 3: 在 `PipelineService` 接口新增 `void reflashPrInfo(PipelineParamDTO param)` 方法
- [x] Task 4: 在 `PipelineServiceImpl` 注入 `PipelineEventProducer` 字段
- [x] Task 5: `PipelineServiceImpl.reflashPrInfo` 改为 `public @Override`
- [x] Task 6: `PipelineServiceImpl.savePipelineInfoWithAsyncPrOps` 改为调 `pipelineEventProducer.sendPrOpEvent(param)`

### Producer

- [x] Task 7: 在 `PipelineEventProducer` 新增 `sendPrOpEvent(PipelineParamDTO param)` 方法 + 2 个 `@Value` 字段
- [x] Task 13: 在 `PipelineEventProducer` 新增 `sendPrOpEventTimeoutRetry(String messageJson, String pipelineRunId)` 方法 + 2 个 `@Value` 字段

### Consumer

- [x] Task 8: 新增 `PrOpEventConsumer`，监听 `pr_op_event_queue`，处理反序列化和业务异常
- [x] Task 14: `PrOpEventConsumer` 注入 `PipelineEventProducer`，捕获 `ThirdPartyApiRateLimitException` / `ThirdPartyApiTimeoutException` 后调用 `sendPrOpEventTimeoutRetry` 路由到 30s 延迟队列

### 环境配置

- [x] Task 9: 三套环境 yaml 同步新增 `pr_op_event_exchange` / `pr_op_event_queue` / `pr_op_event_key`（`_beta` / `_gama` / `_prod` 后缀）
- [x] Task 15: 三套环境 yaml 同步新增 `pr_op_event_delay_exchange` / `pr_op_event_delay_queue_30s` / `pr_op_event_delay_key_30s`（`_beta` / `_gama` / `_prod` 后缀）

### 测试

- [x] Task 10: 新增 `PrOpEventConsumerTest` 7 个用例：正常消息 / 空消息 / 非法 JSON / 缺 pipelineRunId / **限流异常** / **超时异常** / 其他业务异常
