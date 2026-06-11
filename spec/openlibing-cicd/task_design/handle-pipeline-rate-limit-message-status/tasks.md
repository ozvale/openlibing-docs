# 流水线状态更新 429 限流异常兜底机制 — 实现任务

## 进度: 2/2 complete

- [x] Task 1: `ConnectionException` catch 块中增加限流识别，命中时执行 `updateMessageStatus(pipelineRunId, "FAILED")`（通过 `isThrottledConnectionException` 检测 message 中的 429/throttl/APIGW.0308/rate limit 关键词及 cause 链中的 ServiceResponseException）
- [x] Task 2: `ServiceResponseException` catch 块中增加 `e.getHttpStatusCode() == 429` 判断，命中时执行 `updateMessageStatus(pipelineRunId, "FAILED")`
