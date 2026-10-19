# pr-op-mq — 归档

## 归档信息

| 项目 | 内容 |
|------|------|
| 需求名称 | reflashPrInfo 异步化：通过 RabbitMQ 解耦 PR 流水线三件外部 API 调用 + 限流/超时 30s 延迟重试 |
| 业务仓 | openlibing-cicd |
| 开发分支 | master-pr-mq |
| 流程模式 | Standard |
| 归档日期 | 2026-07-30 |

## 关联

- 业务 commit 1（`a76e3b87a`）：新建消息队列控制 PR 信息刷新
  - 新增 `PrOpEventConsumer` / `MessageMaskUtils` / `PrOpEventConsumerTest` / `MessageMaskUtilsTest`
  - `PipelineService` 接口新增 `reflashPrInfo(PipelineParamDTO)`
  - `PipelineServiceImpl` 注入 `PipelineEventProducer`；`reflashPrInfo` 改为 `public @Override`；`savePipelineInfoWithAsyncPrOps` 改为调 `sendPrOpEvent`
  - `PipelineEventProducer` 新增 `sendPrOpEvent` / `sendPrOpEventTimeoutRetry` 两个方法
  - `PipelineEventRabbitConfig` 新增 6 个 Bean（主队列 3 + 30s 延迟队列 3）
  - 三套环境 yaml 同步新增 6 个 key（`_beta` / `_gama` / `_prod` 后缀）
  - `PipelineStatusUpdateConsumer` 删减 28 行（迁移到 `PrOpEventConsumer`）
- 业务 commit 2（`2441d29b8`）：修复 fastjson 安全漏洞 — `start.sh` 新增 `-Dfastjson.parser.safeMode=true`
- 业务 commit 3（`43cc75ba6`）：修复 MQ 队列配置（`PipelineEventRabbitConfig` 1 行调整）

## 交付历程

| commit | 说明 |
|--------|------|
| `a76e3b87a` | feat(pr-op-mq): 新建 PR 操作异步化 MQ 链路（主队列 + 30s 延迟队列 + Consumer + Producer + 脱敏工具 + 单测） |
| `2441d29b8` | fix(security): 启用 fastjson 1.x Parser safe mode（`-Dfastjson.parser.safeMode=true`） |
| `43cc75ba6` | fix(rabbitmq): 修复 MQ 队列配置细节 |

## 用户自测反馈

- 第一轮（`a76e3b87a`）交付后用户要求加 `MessageMaskUtils` 脱敏 `accessToken` 等敏感字段，并补 `MessageMaskUtilsTest` 单测
- 第二轮（`2441d29b8`）交付后用户要求全仓排查 fastjson 用法并加 `-Dfastjson.parser.safeMode=true` JVM 参数；排查出 61 个文件使用 `com.alibaba.fastjson`，覆盖 `WebHookEvent` / `PullRequestEvent` / `NoteEvent` 等关键事件类
- 第三轮（`43cc75ba6`）修复第二轮遗留的 MQ 队列配置 1 行细节
- 用户明确触发 Phase 5 归档

## 最终验证

| 项 | 结果 |
|----|------|
| 业务代码修改 | ✅ 3 个 commit 在 `master-pr-mq` 分支 |
| 单元测试 | ✅ `PrOpEventConsumerTest` 7 个用例 + `MessageMaskUtilsTest` 通过 |
| Pre-commit 质量门禁 | ✅ 编译 / 单测 / 覆盖率 / 格式化 / 静态分析全部通过 |
| 业务 PR | ⏳ 用户尚未触发 Phase 4（业务 PR 提交） |
| 用户 dev 自测 | ✅ 用户确认通过 |
| docs PR | ⏳ 本次提交（target=master） |

## 设计偏差与取舍

### 偏差 1：`PipelineStatusUpdateConsumer` 删减 28 行

**背景**：原 `PipelineStatusUpdateConsumer` 中部分 PR 相关代码片段与 `PrOpEventConsumer` 职责重叠。

**取舍**：本次仅删除 `PipelineStatusUpdateConsumer` 中职责重叠的 28 行片段，把"PR 标签/评论/状态"三件套完整迁出到 `PrOpEventConsumer`；`PipelineStatusUpdateConsumer` 保留流水线状态本身更新逻辑。**未对 `PipelineStatusUpdateConsumer` 主体做改动**，符合"最小变更"原则。

### 偏差 2：消息体不引入新 DTO，直接序列化 `PipelineParamDTO`

**背景**：`reflashPrInfo` 需要 `accessToken` / `owner` / `repo` / `prId` / `commitId` / `status` / `pipelineRunId` / `projectId` / `pipelineId` 等十余个字段。

**取舍**：直接用 `Gson.toJson(param)` 序列化 `PipelineParamDTO` 全量字段（均为简单类型 + 已实现 Serializable 子结构），不在 Producer 端做字段裁剪。Consumer 端通过 `gson.fromJson(json, PipelineParamDTO.class)` 反序列化。**风险**：`accessToken` 落消息体有泄露面 → 缓解：Consumer INFO 日志只打 `pipelineRunId` / `status`，不打印全量消息体；同时 `MessageMaskUtils` 兜底任何未来需要打印消息体的日志。

### 偏差 3：限流/超时异常不限制最大重试次数

**背景**：原计划在 `PrOpEventConsumer` 内对 `ThirdPartyApiRateLimitException` / `ThirdPartyApiTimeoutException` 加 `retryNum` 字段 + 最大重试次数判断。

**取舍**：与现有 `PipelineStatusUpdateProducer.sendTimeoutRetry` 60s 延迟队列模式保持一致——**不限制最大重试次数**，让第三方限流自动恢复期持续重试。后续可按需扩展。

### 偏差 4：异常处理不抛避免消息错路由

**背景**：第一版 `PrOpEventConsumer` 在 `catch (Exception)` 中**抛出**异常，期望触发 Spring AMQP 重试；但实际触发后消息被路由到 `pipeline_event_exchange` / `pipeline_status_queue` 等其他队列，原因是 `setDefaultRequeueRejected(true)` 配置导致消息反复重新入队，与不同 listener 的 `RabbitListenerContainerFactory` 共享了错误恢复策略。

**取舍**：在 `PrOpEventConsumer` 的限流/超时分支**不抛**异常（仅 `LOGGER.warn` + `sendPrOpEventTimeoutRetry`），原消息 ACK，避免被错误路由到其他队列。其他业务异常仍原样抛出交给 Spring AMQP。

## 可复用经验

1. **异常处理"不抛"避免消息错路由**：当 `setDefaultRequeueRejected(true)` + 多个 listener 共享 `RabbitListenerContainerFactory` 时，抛出异常可能被错误的 recoverer 路由到其他队列。在"已通过 Producer 重新发布到正确延迟队列"的分支中，**应直接 ACK 原消息并 return**，不要抛出异常让框架重新分发。
2. **fastjson 1.x 必须开启 Parser safe mode**：项目内 61 个文件使用 `com.alibaba.fastjson` 做反序列化（含 `WebHookEvent` / `PullRequestEvent` / `NoteEvent` 等关键事件类）。**JVM 必须带 `-Dfastjson.parser.safeMode=true`** 启动，否则 `@type` 字段可被攻击者利用触发 RCE。该参数需要在 `start.sh` 等所有启动脚本中显式声明。
3. **复用 `MessageMaskUtils` 兜底所有含敏感字段的日志**：MQ 消息体常带 `accessToken` / `token` / `password` / `secret` / `privateKey` 等敏感字段。**通用模板**：在 `String` 类型 listener 入参处用静态工具方法对消息体做正则替换，覆盖 `accessToken` / `access_token` / `token` / `password` / `secret` / `privateKey` / `private_key` 七个字段。**避免** Gson 解析热路径开销。
4. **延迟队列 TTL 选 30s 而非 60s 的场景**：30s 与现有 `pipelineStatusDelayQueue30s` 一致，适合"让限流窗口过去即可"的场景；60s 适合"业务可容忍更长等待"的场景（如 `PipelineStatusUpdateProducer.sendTimeoutRetry`）。**队列 TTL 不能动态修改**，调整需先删除再重建。
5. **跨包调用 Service 必须走接口**：Consumer 与 Service 跨包（`business.listener` ↔ `business.service.impl`）时，直接调 impl 类会绕开 Spring AOP 代理；走 `PipelineService` 接口更规范。**普通方法（非 `@Transactional`）代理与否不影响行为**，但保持一致性更重要。

（以上经验已沉淀，可考虑同步到 `ai_memory.md`。）

## 归档日期

2026-07-30
