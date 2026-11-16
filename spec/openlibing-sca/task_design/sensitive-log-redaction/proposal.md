# sensitive-log-redaction — 接口响应体与异常消息日志脱敏（#155）

## 需求背景

安全 Issue：[openlibing/openlibing-sca#155](https://gitcode.com/openlibing/openlibing-sca/issues/155)
（安全 / 敏感信息写入日志，CWE-532，低危；标签"安全问题"）。

`WeChatMessageSenderUtil#sendHttpRequest` 在 `/message/send` 调用成功时以 INFO 打印企业微信接口完整响应体，
失败时以 ERROR 打印 HTTP 状态码 + 完整错误响应体（修复前 `origin/master` 版本）：

```java
LOGGER.info("wechat message send success, response: {}", response);
LOGGER.error("wechat message send failed, Response code: {}, error: {}", responseCode, errorResponse);
LOGGER.error("wechat message send failed, Response code: {}", responseCode);
```

响应内容由外部接口控制，包含 `errmsg`、`invaliduser`（接收人 userid 列表）等业务/人员标识，且无长度限制；
一旦外部接口返回调试信息或 HTML 错误页，会原样落入应用日志，存在敏感信息落盘与日志洪泛风险。

同文件残留问题：`getAccessToken` 的 catch 分支打印 `e.getMessage()`，异常消息可能携带完整 gettoken URL
（含 `corpsecret`）。

## 功能描述

**做什么**：

1. 删除响应体打印：成功/失败/错误流三条日志改为固定文案
   （`wechat message send success`、`wechat message send failed`、`wechat message send errorStream`），
   响应体仅读取并丢弃以释放连接。
2. `getAccessToken` 异常日志改为固定文案 + 异常类名（`getAccessToken exception: {}` +
   `e.getClass().getSimpleName()`），不再输出 `e.getMessage()`；新增日志断言单测，确认日志不含
   gettoken URL 与 `corpsecret`。
3. 同批次日志噪声治理（批扫预期路径日志级别调整）：PR patch 非 JSON 是预期路径、公告扫描单明细失败
   已落库且候选失败有 WARN，相应日志降级为单行、不带堆栈，避免 ERROR 刷屏。

**不做什么**：

- 未改变企业微信接口的 URL 鉴权方式：`gettoken` 仍明文拼接 `corpid`/`corpsecret`，`send` 仍明文拼接
  `access_token`（接口规定）；本轮只保证这些值不进入日志。
- 未做 P2 全仓 `LOGGER` 打印外部响应体（response / errorResponse）排查与 CI 静态规则。
- 未引入日志脱敏组件或统一日志框架改造。

## 验收标准

- [x] 不再打印企业微信接口响应体/错误响应体：
      `sendHttpRequest` 成功、失败、errorStream 为空三条路径均为固定文案，响应流仅 drain
      （`6afc9a00`，已在 `ms_scan`；`origin/master` 是否已合入本 spec 未验证）
- [x] 日志中不出现 `corpsecret` / `access_token` 明文及完整 gettoken/send URL：
      `getAccessToken` 仅记录异常类名（`72fe1c0c`）；
      `WeChatMessageSenderUtilTest#getAccessToken_shouldReturnEmptyAndNotLogSensitiveInfo_whenIoExceptionOccurs`
      断言日志不含敏感 URL、`corpsecret` 与解密后的密钥
- [x] 成功/失败/异常路径仍保留可定位问题的固定文案日志：三条固定文案 + `sendMessage` 的异常固定文案
- [ ] 相关单测更新并通过（用例已落地：`WeChatMessageSenderUtilTest` 共 7 个用例；本轮未执行 `mvn test`，
      运行结果未验证）
- [ ] 全仓外部响应体日志排查与 CI 静态规则（P2，本轮未覆盖）

## 影响范围

- 业务仓：`openlibing-sca`
  - `analysis/utils/WeChatMessageSenderUtil.java` + 单测
  - 同批次日志治理：`dm/service/impl/ScanCommonServiceImpl.java`、`dm/service/impl/ProjectNoticeScanAsyncProcessor.java`
- 接口：无变化
- 配置：无变化（沿用 `wecat.cgi-bin`、`sca.corpid`、`sca.corpsecret`、`sca.agentid`、`sca.touser`、
  `security.part1`）
- 数据库 schema：无变化
