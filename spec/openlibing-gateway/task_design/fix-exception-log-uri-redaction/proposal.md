# fix-exception-log-uri-redaction

## 背景

漏洞报告 openlibinggateway-20261103105553 M-0004 (1021-004)：异常日志打印完整
URI。GlobalExceptionHandler 两处日志输出 `request.getURI()`，URI 含 query
string，OAuth 登录/绑定回调类请求的 query 中携带 code/state 等一次性凭证，
异常日志将其明文落盘，存在敏感信息泄漏风险。

## 修复方案

- 两处日志改用 `request.getPath().value()` 仅记录请求路径，保留排障能力，
  不再输出 query string
- 全仓扫描确认无其他日志级 URI 泄漏点：GatewayOperationLogAspect 仅取 host、
  ApiGatewayFilter query 参与签名计算、AuthFilter query 用于参数注入剥离，
  均为功能用途非日志输出

## 验收标准

1. 带 `?code=xxx&state=xxx` 的请求触发异常后，WARN/ERROR 日志消息不含凭证值，
   仍包含请求路径
2. 既有 GlobalExceptionHandlerTest 全量通过
