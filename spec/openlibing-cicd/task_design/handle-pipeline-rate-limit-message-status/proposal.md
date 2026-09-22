# 流水线状态更新 429 限流异常兜底机制

## 需求背景
华为云流水线 API 存在限流策略（200次/秒/IP），当 `PipelineStatusUpdateConsumer` 消费消息进入 `recordPipelineInfo` → `getPipelineRunDetail` 调用华为云 API 时，可能触发 429 限流异常。

限流发生时，`getPipelineRunDetail` 返回 `DataResult.failureMessage()`，`recordPipelineInfo` 随即返回失败，不会进入 `savePipelineInfoWithAsyncPrOps`，消息也不会重新入队。这意味着该流水线状态更新消息被静默丢弃，流水线记录将停留在旧状态，无法被后续轮询更新。

## 功能描述
1. 在 `getPipelineRunDetail` 的 `ConnectionException` catch 块中，检测限流特征（429/throttl/APIGW.0308/rate limit），命中时将 `messageStatus` 标记为 `FAILED`
2. 在 `getPipelineRunDetail` 的 `ServiceResponseException` catch 块中，检测 `httpStatusCode == 429`，命中时同样将 `messageStatus` 标记为 `FAILED`
3. `fullPipelineMonitor` 定时任务（每5分钟）扫描 `status IN (RUNNING, QUEUED, INIT) AND messageStatus = FAILED` 的记录，调用 `resendFailedMessage` 重新入队
4. 消费者再次消费，若限流已解除则正常处理；若仍在限流则再次标记 FAILED，等待下一轮兜底

不做：
- 不修改消费者重入队逻辑（`defaultRequeueRejected=true` 保持不变）
- 不修改 `fullPipelineMonitor` 的扫描频率或退避策略
- 不修改数据库表结构

## 验收标准
- [ ] 429 限流以 `ConnectionException` 抛出时，`messageStatus` 被标记为 `FAILED`
- [ ] 429 限流以 `ServiceResponseException` 抛出时，`messageStatus` 被标记为 `FAILED`
- [ ] `fullPipelineMonitor` 能扫描到 `messageStatus=FAILED` 的记录并重新入队
- [ ] 重新入队后消费者能正常消费，直到流水线达到终态
- [ ] 非429异常不影响 `messageStatus`，不触发兜底重发

## 影响范围
- 后端：`openlibing-cicd` 仓（PipelineServiceImpl.getPipelineRunDetail）
