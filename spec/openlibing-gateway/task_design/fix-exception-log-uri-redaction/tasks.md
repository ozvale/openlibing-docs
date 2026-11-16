# fix-exception-log-uri-redaction — 实现任务

## 进度: 2/2 complete

- [x] Task 1: GlobalExceptionHandler 两处 `request.getURI()` 改 `request.getPath().value()`
- [x] Task 2: 新增 ListAppender 日志捕获用例（断言 secret-code/secret-state 不出现在任何日志消息、路径仍被记录），GlobalExceptionHandlerTest 全量通过
