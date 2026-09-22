# pipeline-status-poison-message-fix: 修复 pipeline_status_queue 毒消息卡死 60 条 + 消息体敏感字段脱敏

## 需求背景

`openlibing-cicd` 项目在生产环境 MQ 监控中观察到 `pipeline_status_queue` 持续稳定积压 60 条 unacked 消息不下降，重启容器后消息数仍不下降。单条毒消息的消费日志只打印 1 次（不在循环）。

经排查根因为：

1. **业务 bug**：`PipelineServiceImpl.syncPrLabel:5413-5416` 在 `getPRAllLabels` 返回 GitCode API 纯字符串数组（如 `["label1","label2"]`）时，fastjson2 泛型擦除导致 `List<String>`，后续 `.map(LabelResponseDTO::getName)` 抛 `ClassCastException: String cannot be cast to LabelResponseDTO`。
2. **框架放大**：`pipelineStatusListenerContainerFactory` 配的 `setDefaultRequeueRejected(true)` 配合缺失的 retry interceptor，让毒消息 nack(requeue=true) 回队首后，consumer 状态异常导致消息卡在 unacked 槽位。
3. **日志泄露**：`PipelineStatusUpdateConsumer` 三个日志点（info / IllegalArgumentException catch / Exception catch）直接打印 `messageJson` 原文，消息体中包含 `accessToken` 等敏感凭证，存在 ELK / 日志平台扩散风险。

## 功能描述

1. **业务代码修复**：`getPRAllLabels` 兼容字符串数组返回，优先 `LabelResponseDTO` 对象数组解析，失败时按 `String` 数组兜底；同时在 catch 块加 WARN 日志记录兜底路径触发频率 + body + 异常堆栈。
2. **框架配置加固**：在 `pipelineStatusListenerContainerFactory` 上挂 `RetryInterceptorBuilder.stateless()` + `RejectAndDontRequeueRecoverer`，实现真正的"3 次重试后入 DLQ"语义。
3. **日志脱敏**：新增 `maskSensitiveFields` 静态工具方法，对 `accessToken` / `access_token` / `token` / `password` / `secret` / `privateKey` / `private_key` 字段做脱敏（替换为 `******`），替换 `PipelineStatusUpdateConsumer` 3 个日志点。

## 验收标准

- [x] `getPRAllLabels` 优先按 `LabelResponseDTO` 数组解析，失败时按 `String` 数组兜底
- [x] `getPRAllLabels` 兜底路径触发时记录 WARN 日志（含 url / body / 异常堆栈）
- [x] `pipelineStatusListenerContainerFactory` 关闭 `setDefaultRequeueRejected`（即 `false`），挂 `RetryInterceptorBuilder.stateless()` + `RejectAndDontRequeueRecoverer`
- [x] `PipelineStatusUpdateConsumer.handlePipelineStatusUpdate` 3 个日志点（info / IllegalArgumentException catch / Exception catch）通过 `maskSensitiveFields` 过滤敏感字段
- [x] `mvn compile` 通过
- [x] `mvn test -Dtest=PipelineServiceImplTest` -> `Tests run: 206, Failures: 0, Errors: 0`
- [x] 用户 dev 自测：broker 端 `messages_unacknowledged` 从 60 降为 0；重投毒消息 3 次重试后入 DLQ；日志中 `accessToken` 显示为 `******`

## 影响范围

| 文件 | 操作 | 说明 |
|---|---|---|
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java` | 修改 | `getPRAllLabels` 兼容字符串数组返回 + 兜底路径 WARN 日志 |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/common/config/rabbitmq/RabbitConnectionFactoryConfig.java` | 修改 | `pipelineStatusListenerContainerFactory` 加 retry interceptor + 关 default requeue |
| `openlibing-cicd/src/main/java/com/openlibing/cicd/business/listener/PipelineStatusUpdateConsumer.java` | 修改 | 新增 `maskSensitiveFields` + 替换 3 个日志点 |

## 关联 Issue

- 业务 Issue：openlibing/openlibing-cicd#169
- 业务 PR：openlibing/openlibing-cicd#449
