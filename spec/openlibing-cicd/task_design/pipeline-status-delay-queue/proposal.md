# Proposal: 非终态流水线状态更新队列改造为延迟队列

## 需求背景

PipelineStatusUpdateProducerImpl 生产者用于流水线状态跟踪记录。当前同一流水线在消费结束后，非终态流水线会**立即**重新生产进入队列，形成紧耦合的即时循环：

```
Consumer 消费 → recordPipelineInfo(调华为云API+GitCode API)
  → DB更新后状态仍为非终态 → 立即 sendStatusUpdate 重新入队 → Consumer 立刻消费 → 循环
```

这导致以下问题：
1. **GitCode API 被高频调用**：流水线运行期间每秒可能产生多次请求，触发限流
2. **无效轮询**：流水线在 RUNNING 状态下短时间内状态不会变化，频繁查询毫无意义
3. **消费者资源浪费**：10-50 个并发消费者被无效消息占满

## 解决方案

将非终态流水线重新入队的消息改造为延迟队列（TTL + 死信队列方式）：

- 消息先进入延迟队列等待 TTL 过期
- 过期后通过死信机制自动路由到业务队列被消费
- 按状态分级延迟：RUNNING=10s，INIT/QUEUED=60s

### 方案选型

| 方案 | 结论 |
|------|------|
| rabbitmq_delayed_message_exchange 插件 | 不可用，华为云已于2024/01/15下线此插件 |
| TTL + 死信队列（采用） | 兼容所有 RabbitMQ 版本，项目已有死信基础设施 |

### 消息流转（改造后）

```
首次消息（XxlJobHandler等触发）:
  Producer.sendStatusUpdate() → pipelineStatusExchange → pipelineStatusQueue → Consumer

非终态重新入队（改造核心）:
  Producer.sendDelayedStatusUpdate(10s/60s)
    → pipelineStatusDelayExchange
    → delayQueue10s/delayQueue60s (消息等待TTL过期)
    → (DLX) pipelineStatusExchange → pipelineStatusQueue → Consumer
```

## 验收标准

1. 非终态流水线不再立即重新入队，而是经过延迟间隔后才被消费
2. GitCode API 请求频率大幅降低，不再触发限流
3. 流水线终态检测和事件触发功能不受影响
4. 延迟队列消息持久化，消费者宕机恢复后可继续处理
5. 兜底定时任务(ScheduleTaskImpl)正常工作

## 关联 Issue

yanzhaohong/openlibing-cicd#3
