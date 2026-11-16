# sensitive-log-redaction — 技术设计

## 方案概述

对企业微信发送链路的日志做"去内容化"：响应体只读取并丢弃，不再格式化输出；异常分支只记录固定文案与
异常类型，不记录可能携带敏感 URL 的异常消息。由于凭据按企业微信接口规定放在 URL 查询参数中
（`corpsecret`、`access_token`），脱敏策略选择"不打印 URL / 不打印异常消息"，而非在打印时做正则替换。

## 数据流（修复后）

```
sendMessage(message)
  ├─ getAccessToken()
  │    ├─ GET {wecat}/gettoken?corpid=...&corpsecret=...
  │    ├─ 成功 → 解析 access_token 返回
  │    └─ IOException/JSONException → LOGGER.error("getAccessToken exception: {}", e.getClass().getSimpleName())
  └─ sendHttpRequest(accessToken, messageData, outputStream)
       ├─ POST {wecat}/message/send?access_token=...
       ├─ HTTP 200 → drain 响应流 → LOGGER.info("wechat message send success")
       ├─ HTTP != 200 且 errorStream != null → drain → LOGGER.error("wechat message send failed")
       └─ HTTP != 200 且 errorStream == null → LOGGER.error("wechat message send errorStream")
```

同批次日志治理（批扫路径）：

```
ScanCommonServiceImpl.extractDiffContent
  └─ JSONException（patch 为原始 unified diff，预期路径）→ LOGGER.debug("Patch is not JSON format, using as-is")

ProjectNoticeScanAsyncProcessor.processSingleDetail
  └─ 单明细失败（已落库，候选失败另有 WARN）→ LOGGER.info(..., reason=e.getMessage())，不带堆栈
```

## 架构决策

| 决策                                          | 理由                                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| D1 响应体只 drain 不落日志                    | 外部接口返回内容与长度不可控；drain 保证连接可复用/释放，日志不再承载外部数据                    |
| D2 三条路径使用互不相同的固定文案             | 成功 / 有错误流 / 无错误流可区分，保留最小可定位信息，不输出响应内容与状态码                     |
| D3 异常分支只记录异常类名                     | `IOException` 消息常携带完整请求 URL（含 `corpsecret`）；类名足以区分网络/解析类失败             |
| D4 不重构 URL 鉴权方式，只约束日志            | 企业微信 `gettoken` / `send` 的查询参数鉴权是接口规定，改造会破坏对接；控制点是"谁被写进日志"    |
| D5 同批次日志噪声治理按"预期路径"降级         | patch 字段为原始 unified diff，JSON 探测失败是设计内行为；单明细失败已落库，ERROR+堆栈会造成刷屏 |
| D6 单测用 logback `ListAppender` 断言日志内容 | 直接验证"日志不含敏感值"，比只断言代码分支更贴近安全验收                                         |

## 涉及文件

| 文件                                                                                    | 操作 | 说明                                                                                                         |
| --------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------ |
| `src/main/java/com/openlibing/sca/analysis/utils/WeChatMessageSenderUtil.java`          | 修改 | `sendHttpRequest` 删除响应体打印，改固定文案；`getAccessToken` 异常日志改类名                                |
| `src/test/java/com/openlibing/sca/analysis/utils/WeChatMessageSenderUtilTest.java`      | 修改 | 新增 `getAccessToken_shouldReturnEmptyAndNotLogSensitiveInfo_whenIoExceptionOccurs`；该文件共 7 个用例       |
| `src/main/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImpl.java`           | 修改 | `Patch is not JSON format, using as-is` 日志级别 ERROR → debug（经 debug → info → debug 回摆，最终为 debug） |
| `src/main/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanAsyncProcessor.java` | 修改 | `processSingleDetail error` 由 ERROR+堆栈改为单行 INFO（含 `reason=e.getMessage()`，不带堆栈）               |

## 风险 & 缓解

| 风险                                                                                      | 缓解                                                                                                    |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 失败时不再记录 HTTP 状态码与错误体，排障信息减少                                          | 固定文案可区分"有错误流/无错误流"；必要时通过监控或抓包定位，后续可加非敏感状态码                       |
| HTTP 200 一律记 success：企业微信业务错误（`errcode != 0`）被读取后丢弃，日志显示成功     | 属既有行为（修复前也只是打印响应体、未做判断）；如需业务级告警，应新增 `errcode` 解析与告警，本轮未覆盖 |
| `access_token` / `corpsecret` 仍在 URL 中，若开启 HTTP 客户端调试日志或链路抓包仍可能泄露 | 已消除应用日志输出面；底层客户端日志属独立配置，未验证                                                  |
| 日志级别多次调整（`9ad54887` → `2a521f71` → `471bc3e8`）导致预期路径可见性不一致          | 最终态：patch 非 JSON 为 debug、公告单明细失败为 info；以当前代码为准                                   |
| 同批次日志治理与 #155 主体问题关联度弱，commit 未写 `Refs`                                | 已在本 spec 中标明来源；如需严格追溯，应以 PR 描述为准（未验证）                                        |

## 跨仓影响

无。企业微信为外部服务，不涉及公司内其他仓；无接口、配置或数据模型变化。
