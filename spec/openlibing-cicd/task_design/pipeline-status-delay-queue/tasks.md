# Tasks: 非终态流水线状态更新队列改造为延迟队列

## 实现步骤

- [x] 1. PipelineEventRabbitConfig 新增延迟队列基础设施
  - 新增延迟交换机 `pipelineStatusDelayExchange`（DirectExchange, durable）
  - 新增 10s 延迟队列 `pipelineStatusDelayQueue10s`（TTL=10s, DLX=pipelineStatusExchange）
  - 新增 60s 延迟队列 `pipelineStatusDelayQueue60s`（TTL=60s, DLX=pipelineStatusExchange）
  - 新增 2 个 Binding（延迟交换机 → 延迟队列）

- [x] 2. PipelineStatusUpdateProducer 接口新增 `sendDelayedStatusUpdate(message, delayMillis)` 方法

- [x] 3. PipelineStatusUpdateProducerImpl 实现延迟发送逻辑
  - `resolveDelayRoutingKey`: 根据 delayMillis 选择对应 routing key（10s/60s）
  - `sendDelayedStatusUpdateWithRetry`: 带重试的延迟发送（最多3次）
  - `doSendDelayedStatusUpdate`: 使用 Publisher Confirm 机制发送到延迟交换机

- [x] 4. PipelineServiceImpl.savePipelineInfoWithAsyncPrOps 改用延迟发送
  - RUNNING 状态：`sendDelayedStatusUpdate(message, 10_000L)`
  - INIT/QUEUED 状态：`sendDelayedStatusUpdate(message, 60_000L)`

- [ ] 5. Apollo 配置中心新增延迟队列配置项
  - `spring.rabbitmq.cicd.pipeline_status_delay_exchange`
  - `spring.rabbitmq.cicd.pipeline_status_delay_queue_10s`
  - `spring.rabbitmq.cicd.pipeline_status_delay_key_10s`
  - `spring.rabbitmq.cicd.pipeline_status_delay_queue_60s`
  - `spring.rabbitmq.cicd.pipeline_status_delay_key_60s`

- [ ] 6. 部署验证
  - 确认 RabbitMQ 管理控制台延迟交换机和延迟队列已自动创建
  - 触发流水线验证延迟消费生效
  - 确认 GitCode API 请求频率降低
  - 确认终态检测和事件触发功能正常

## 不修改的部分

- ScheduleTaskImpl.fullPipelineMonitor：兜底任务暂不修改，当前多层兜底机制已足够
- PipelineStatusUpdateConsumer：消费者监听的队列和消息格式不变，无需修改
- PipelineStatusUpdateProducer.sendStatusUpdate：首次消息发送逻辑不变，仍走即时队列
