# fix-exception-log-uri-redaction — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/161 （【安全】operation-log-and-perm-scheme M-0004 全局异常日志打印含 query string 的完整 URI，OAuth2 access_token/code 明文进入服务器日志）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `5d826ed6`: GlobalExceptionHandler 两处 `request.getURI()` 改 `request.getPath().value()`，仅记录请求路径，不再输出 query string

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- 新增 ListAppender 日志捕获用例（断言 secret-code/secret-state 不出现在任何日志消息、路径仍被记录），GlobalExceptionHandlerTest 全量通过
- 全仓扫描确认无其他日志级 URI 泄漏点

## 设计偏差与取舍

- 无；按 proposal 方案落地

## 归档日期

2026-11-16
