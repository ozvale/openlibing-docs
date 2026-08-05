# pipeline-status-poison-message-fix — 技术设计

## 问题定位

### 1. 业务 bug

**Sink**：`PipelineServiceImpl.java:5413-5416`（`syncPrLabel`）

```java
Set<String> existing = getPRAllLabels(param).stream()
        .map(LabelResponseDTO::getName)   // ← 炸：String cannot be cast to LabelResponseDTO
        .collect(Collectors.toSet());
```

**Source**：`PipelineServiceImpl.java:5470`（`getPRAllLabels`）

```java
return JSON.parseArray(response.getResponseBody(), LabelResponseDTO.class);
```

GitCode `https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls/{prId}/labels` 接口在部分 PR 场景下返回纯字符串数组 `["label1","label2"]` 而非 `[{name:"label1"}]` 对象数组。fastjson2 泛型擦除后 `JSON.parseArray(..., LabelResponseDTO.class)` 实际构造出 `List<String>`，导致后续 `.map(LabelResponseDTO::getName)` 抛 `ClassCastException`。

### 2. 框架配置

[RabbitConnectionFactoryConfig.java:125-151](file:///d:/code/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/common/config/rabbitmq/RabbitConnectionFactoryConfig.java#L125-L151) `pipelineStatusListenerContainerFactory`：

```java
factory.setDefaultRequeueRejected(true);  // 异常 → nack(requeue=true) → 消息回队首
```

注释声称"配合死信队列使用，最多重试 3 次后进入死信队列"，但**没有**：
- `RetryOperationsInterceptor`（重试次数限制）
- `MessageRecoverer`（重试耗尽后的恢复器）
- `setAdviceChain`（advice 链）

DLQ 路由**只在 `requeue=false` 时触发**。`requeue=true` 直接把消息塞回原队列，**永远不会进 DLQ**。

### 3. 日志泄露

[PipelineStatusUpdateConsumer.java:73-80](file:///d:/code/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/listener/PipelineStatusUpdateConsumer.java#L73-L80) 3 个日志点直接 `logger.xxx("...", messageJson, e)`，未对 `accessToken` 字段做脱敏。

## 攻击 / 异常链还原

```
GitCode webhook 推送 FAILED 状态 → producer 投递到 pipeline_status_queue
  → PipelineStatusUpdateConsumer.handlePipelineStatusUpdate
  → doHandlePipelineStatusUpdate
  → pipelineService.recordPipelineInfo
  → savePipelineInfoWithAsyncPrOps
  → updatePrLabel
  → syncPrLabel
  → getPRAllLabels(URL=https://api.gitcode.com/api/v5/repos/openlibing/openlibing-ops/pulls/100/labels)
  → GitCode API 返回 ["xxx"] 字符串数组
  → JSON.parseArray(..., LabelResponseDTO.class) 解析为 List<String>
  → .map(LabelResponseDTO::getName) 抛 ClassCastException
  → 异常冒泡 → catch (Exception) → throw new PipelineProcessException(...)
  → Spring AMQP nack(requeue=true) → 消息回队首
  → consumer 状态异常 → 消息卡 unacked → 60 条积压
```

## 修复方案

### 方案对比

| 方案 | 改动量 | 风险 | 推荐度 |
|---|---|---|---|
| `getPRAllLabels` 字符串数组兜底 + retry interceptor + 脱敏 | 3 文件 +50/-12 | 低 | ⭐⭐⭐ 推荐 |
| 仅业务代码兜底，不动框架 | 1 文件 +20/-0 | 中：毒消息仍会让 consumer 卡死 | ⭐ 不推荐 |
| 升级 GitCode API 调用方用对象 schema | 跨仓改动 | 高 | ⭐ 不推荐 |

采用 **方案 1**：业务代码 + 框架配置 + 日志安全 三层联动修复。

### 修复代码

#### 1. `getPRAllLabels` 字符串数组兜底

```java
private List<LabelResponseDTO> getPRAllLabels(PipelineParamDTO param) {
    String url = String.format(LABEL_LIST_URL, param.getOwner(), param.getRepo(), param.getPrId());
    HttpRequest request = ...;
    String body = HttpClientUtil.doGet(request);
    if (StringUtils.isBlank(body)) {
        return Collections.emptyList();
    }
    List<LabelResponseDTO> labels = new ArrayList<>();
    try {
        List<LabelResponseDTO> parsed = JSON.parseArray(body, LabelResponseDTO.class);
        if (parsed != null && !parsed.isEmpty()) {
            return parsed;
        }
    } catch (JSONException e) {
        // 对象数组解析失败时回落到字符串数组
        LOGGER.warn("getPRAllLabels parse as LabelResponseDTO array failed, "
                + "fallback to String array. url={}, body={}", url, body, e);
    }
    List<String> strs = JSON.parseArray(body, String.class);
    if (strs != null) {
        for (String s : strs) {
            LabelResponseDTO d = new LabelResponseDTO();
            d.setName(s);
            labels.add(d);
        }
    }
    return labels;
}
```

#### 2. retry interceptor + 关 default requeue

```java
factory.setDefaultRequeueRejected(false);
factory.setAdviceChain(
    RetryInterceptorBuilder.stateless()
        .maxAttempts(3)
        .backOffOptions(1000, 2.0, 5000)
        .recoverer(new RejectAndDontRequeueRecoverer())
        .build()
);
```

#### 3. 日志脱敏

```java
private static final Pattern SENSITIVE_FIELDS_PATTERN = Pattern.compile(
        "\"((?:accessToken|access_token|token|password|secret|privateKey|private_key))\"\\s*:\\s*\"[^\"]*\"",
        Pattern.CASE_INSENSITIVE);

private static String maskSensitiveFields(String messageJson) {
    if (StringUtils.isBlank(messageJson)) {
        return messageJson;
    }
    return SENSITIVE_FIELDS_PATTERN.matcher(messageJson).replaceAll("\"$1\":\"******\"");
}
```

替换 3 个日志点：`logger.info("...: {}", maskSensitiveFields(messageJson))`、`logger.error("Invalid message format, ...", maskSensitiveFields(messageJson), e)`、`logger.error("Failed to process ... will retry", maskSensitiveFields(messageJson), e)`。

### 关键决策

1. **业务兜底 vs 修 GitCode API 客户端**：GitCode API 行为是上游约束，业务侧兜底最稳；改 schema 影响面太大。
2. **retry 次数定 3 次**：`maxAttempts(3)` 配合 `backOffOptions(1000, 2.0, 5000)` 退避策略，1s / 2s / 5s 总耗时约 8s，符合业务对瞬时异常恢复的预期。
3. **`setDefaultRequeueRejected(false)` 必须配套 `RejectAndDontRequeueRecoverer`**：否则会直接丢弃无重试。
4. **脱敏用正则而非解析 JSON**：热路径避免 Gson parse 开销；正则覆盖 `accessToken` / `access_token` / `token` / `password` / `secret` / `privateKey` / `private_key` 7 个常见敏感字段。
5. **`PipelineEventConsumer` 的其他 listener 不在本 PR 范围**：它们也使用 `setDefaultRequeueRejected`（Spring AMQP 默认 `true`），但 catch (Exception) 不重抛，行为不同，单独工单跟进。

## 测试设计

### 已通过的本地测试

| 验证项 | 结果 |
|---|---|
| `mvn compile` | ✅ |
| `mvn test -Dtest=PipelineServiceImplTest` | ✅ `Tests run: 206, Failures: 0, Errors: 0` |

### 用户 dev 环境自测项

1. 部署后 broker 端 `messages_unacknowledged` 从 60 降为 0
2. 重投 `pipelineRunId=7a932143218748528bc4a57a21ff03b1, prId=100` 应 3 次重试后入 DLQ
3. 真实 PR 触发 FAILED 时应走兜底路径，业务功能正常

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 字符串数组兜底可能在某种 GitCode 响应格式下误判（如对象字段名也匹配） | 正则只匹配双引号包裹的 token-style 字段，不会误伤普通字段 |
| `setDefaultRequeueRejected` 改动影响其他 listener 行为 | 工厂只针对 `pipelineStatusListenerContainerFactory`，其他 listener 不受影响 |
| 正则无法覆盖带转义引号的 token 值（如 `"my\"token"`） | 已知边界，token 实际不包含引号；如未来需要可改用 JSON parse + 字段过滤 |
| 3 次重试 + 5s 退避后入 DLQ，可能延迟业务处理 | 业务功能可容忍 8s 延迟；DLQ 告警有 `handleDeadLetterEvent` 兜底 |

## 跨仓影响

- **业务仓 openlibing-cicd**：修改 3 个文件 +50/-12
- **docs 仓 openlibing-docs**：本 PR 提交
- **其他仓**：无影响

## 后续独立工单

- [ ] `bisectQueue` 的 DLX 指向自己的交换机（[PipelineEventRabbitConfig.java:142-148](file:///d:/code/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/common/config/rabbitmq/PipelineEventRabbitConfig.java#L142-L148)），会形成二分定位任务失败时的死循环
- [ ] `deadQueue` 消费者只解析 `PipelineEventMessage` 类型 + 缺乏持久化
- [ ] 其他 7 个业务队列的统一 retry / 脱敏治理
