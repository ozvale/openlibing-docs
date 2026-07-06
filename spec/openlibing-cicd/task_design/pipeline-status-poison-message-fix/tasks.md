# pipeline-status-poison-message-fix — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 修改 `PipelineServiceImpl.getPRAllLabels` 兼容字符串数组返回 + 兜底路径 WARN 日志
- [x] Task 2: 修改 `RabbitConnectionFactoryConfig.pipelineStatusListenerContainerFactory` 加 retry interceptor + 关 default requeue
- [x] Task 3: 修改 `PipelineStatusUpdateConsumer` 新增 `maskSensitiveFields` + 替换 3 个日志点
- [x] Task 4: 修复 G.FMT.04 违规 —— 把 `maskSensitiveFields` 静态方法从类变量区移到类底部方法区，遵循"类变量 → 实例变量 → 构造器 → 方法"声明顺序

## 详细任务

### Task 1: getPRAllLabels 字符串数组兜底

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java`
- 改动：
  - 重构 `getPRAllLabels` 方法体：先按 `LabelResponseDTO` 数组解析，失败 catch `JSONException` 时按 `String` 数组兜底
  - catch 块加 WARN 日志（含 url / body / 异常堆栈）
  - 增加 `Collections.emptyList()` / `ArrayList<LabelResponseDTO>` / `LabelResponseDTO.setName` 防御性处理

### Task 2: pipelineStatusListenerContainerFactory retry interceptor

- 文件：`src/main/java/com/openlibing/cicd/common/config/rabbitmq/RabbitConnectionFactoryConfig.java`
- 改动：
  - 关闭 `setDefaultRequeueRejected(false)`
  - 挂 `RetryInterceptorBuilder.stateless().maxAttempts(3).backOffOptions(1000, 2.0, 5000).recoverer(new RejectAndDontRequeueRecoverer()).build()`
  - 新增 import：`org.springframework.amqp.rabbit.config.RetryInterceptorBuilder` / `org.springframework.amqp.rabbit.retry.RejectAndDontRequeueRecoverer`

### Task 3: PipelineStatusUpdateConsumer 日志脱敏

- 文件：`src/main/java/com/openlibing/cicd/business/listener/PipelineStatusUpdateConsumer.java`
- 改动：
  - 新增 `SENSITIVE_FIELDS_PATTERN` 静态字段（覆盖 `accessToken` / `access_token` / `token` / `password` / `secret` / `privateKey` / `private_key`）
  - 新增 `maskSensitiveFields(String)` 静态工具方法
  - 替换 3 个日志点：`info` / `IllegalArgumentException catch` / `Exception catch`
  - 新增 import：`java.util.regex.Pattern`

## 业务仓 Commits

| commit | 说明 |
|---|---|
| `180fc080` | fix(pipeline-status): unblock pipeline_status_queue from ClassCastException poison message（Task 1 + Task 2） |
| `d9e41aea` | fix(pipeline-status): log fallback path when parsing PR labels response（Task 1 补充 WARN 日志） |
| `54bb6f47` | fix(security): mask sensitive fields (accessToken/token/etc) in pipeline status update logs（Task 3） |
| `0ba7a612` | 修改代码规范问题（用户自查修复 RabbitConnectionFactoryConfig.java 其他规范问题） |
| `98d2735c` | fix(security): reorder class declaration to comply with G.FMT.04（Task 4，静态方法移到方法区） |

## 验证状态

| 验证项 | 状态 | 证据 |
|---|---|---|
| 业务仓代码修改 | ✅ 完成 | 3 个 commit 已 push 到 fork |
| 业务仓单测 | ✅ 完成 | `mvn test -Dtest=PipelineServiceImplTest` 206/206 通过 |
| 业务仓 PR 创建 | ✅ 完成 | https://gitcode.com/openlibing/openlibing-cicd/merge_requests/449 |
| 业务仓 PR 标签 `ai-assisted` | ✅ 完成 | `gitcode pr edit 449 --labels ai-assisted` |
| 业务仓 PR CI | ✅ 通过 | `ci_state_passed: true` |
| 业务仓 PR 合入 | ⏳ 待用户/评审合入 | 当前 `state: open, merged: false` |
| 用户 dev 自测 | ✅ 用户已确认 | broker 端 60 条降为 0，3 次重试后入 DLQ |
| docs PR | ⏳ 本次提交 | target=master |
