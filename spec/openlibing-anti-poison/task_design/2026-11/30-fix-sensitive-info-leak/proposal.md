# 30-fix-sensitive-info-leak — 需求背景与验收标准

## 背景

墨菲安全扫描发现服务在异常处理与日志输出中直接打印原始异常信息（如 `e.getMessage()`、`e.toString()`），可能向日志和接口响应泄露系统内部路径、堆栈等敏感信息。涉及 ActionPRServiceImpl、HttpRequestUtils、PoisonPRServiceImpl、HttpUtil 等多处代码。

关联业务 Issue：openlibing/openlibing-anti-poison#30

## 需求范围

- 整改 ActionPRServiceImpl、PoisonPRServiceImpl 中 error 日志直接输出异常对象/消息的写法
- 整改 HttpRequestUtils、HttpUtil 中以 info/error 级别输出 `e.getMessage()` 的问题
- BusinessException 构造避免直接透传底层异常消息

## 验收标准

- [x] 墨菲扫描涉及的敏感信息泄露点全部整改，已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

日志信息收敛后排障信息可能减少，需保留必要的受控错误上下文。
