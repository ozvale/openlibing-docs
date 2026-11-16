# exception-message-leak — 技术设计

## 方案概述

把"异常消息去往何处"收敛为两条通道：

- **客户端**：只返回 `ErrorCode` 常量文案 + 错误码 + 固定 advice，绝不拼接异常原文；
- **服务端日志**：由统一入口 `logHandledException` 记录 `exceptionType` 与经
  `sanitizeExceptionDetail` 脱敏的 `exceptionDetail`，并保留请求上下文（URI / Method / IP / UA / Referer，
  其中用户可控字段经 `sanitizeForLog` 做日志注入净化）。

同时清理 Controller catch 块与 `ScaException` 构造点中散落的 `e.getMessage()` 拼接，形成"错误响应统一
信封"。

## 数据流（修复后）

```
异常 → DefaultExceptionHandler.@ExceptionHandler
  ├─ errorCode/errorMsg/adviceMsg ← ErrorCode（固定）
  ├─ LoggerAppend.create(request, ERROR)  ← URI + 白名单参数（#161）
  ├─ logHandledException(request, errorCode, errorMsg, ex)
  │    ├─ exceptionType = ex.getClass().getName()
  │    ├─ exceptionDetail = sanitizeExceptionDetail(ex.getMessage())
  │    │    ├─ 512 字符截断
  │    │    ├─ UNSAFE_LOG_CHARS → "_"
  │    │    ├─ jdbc:\S+            → "[jdbc-url]"
  │    │    ├─ (select|insert|update|delete|drop|alter|truncate|create)\b[^;]* → "[sql]"
  │    │    ├─ 盘符/系统绝对路径   → "[path]"
  │    │    └─ https?://\S+        → "[url]"
  │    └─ ERROR：errorCode/errorMsg/exceptionType/exceptionDetail + 净化后的 URI/Method/IP/UA/Referer
  └─ DataResult.failure(errorCode, errorMsg, adviceMsg) → 客户端
```

## 架构决策

| 决策                                                                                   | 理由                                                                                                               |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| D1 客户端消息一律取 `ErrorCode` 常量                                                   | 常量在编译期确定，不可能反射外部输入；24 处拼接一次性清除，模式统一                                                |
| D2 日志侧用"异常类型 + 脱敏详情"补偿排障能力                                           | 移除原文回显后仍需定位问题；类型名区分异常族，脱敏详情保留有限上下文，512 截断防日志膨胀                           |
| D3 脱敏在日志写入前统一做（`sanitizeExceptionDetail`）                                 | 单点实现、可单测；避免每个 handler 各自处理，防止新 handler 遗漏                                                   |
| D4 日志注入防护独立于内容脱敏（`sanitizeForLog`）                                      | URI/UA/Referer 属用户可控，需剥离 `\r\n\t` 等控制字符防伪造日志行；与 SQL/路径脱敏职责不同                         |
| D5 Controller catch 统一为 `failure(code, msg, advice)` 三参信封                       | 保留业务错误码与建议文案，不再透传异常原文；与 `DefaultExceptionHandler` 的返回结构一致                            |
| D6 `ScaException` 构造点去除 `+ e.getMessage()`，缺 logger 处补 `LOGGER.error(..., e)` | 异常原文是回显的源头之一；服务端日志保留完整堆栈，客户端只见固定业务文案                                           |
| D7 修复 `methodNotSupportErrorException` 形参类型                                      | 声明 `HttpRequestMethodNotSupportedException` 但形参为 `BindException`，Spring 参数解析会失败；属同文件必修缺陷    |
| D8 聚合异常只输出固定文案                                                              | "all download candidates failed" 曾拼 `lastError.getMessage()`（含下载 URL 与 500 字符响应体），与固定文案契约冲突 |

## 涉及文件

| 文件                                                                                    | 操作 | 说明                                                                                                                                                                                                       |
| --------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/common/exception/DefaultExceptionHandler.java`        | 修改 | 移除 24 处 `errorMsg += ... getMessage()`；`logHandledException` 增加 `Throwable` 参数；新增 `sanitizeExceptionDetail` 及 4 个正则常量、`MAX_DETAIL_LENGTH`；修复 method-not-supported 形参；净改动 194 行 |
| `src/main/java/com/openlibing/sca/analysis/controller/FileController.java`              | 修改 | `failure(e.getMessage())` → 三参信封                                                                                                                                                                       |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenPersonScanController.java`    | 修改 | 2 处 catch 改三参信封                                                                                                                                                                                      |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenScanController.java`          | 修改 | 7 处 `ScaException` catch 改三参信封；2 处 `failure(500, e.getMessage())` 改固定文案 + `LOGGER.error`                                                                                                      |
| `src/main/java/com/openlibing/sca/analysis/controller/LicenseController.java`           | 修改 | `failure(500, e.getMessage())` → 固定文案"查询license兼容性分析数据失败" + `LOGGER.error`                                                                                                                  |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`       | 修改 | `exportNotice` 的 `IllegalArgumentException` 文案去掉 `e.getMessage()`，改记日志                                                                                                                           |
| `src/main/java/com/openlibing/sca/analysis/utils/security/DownLoadFilesUtils.java`      | 修改 | `deleteFolder` 的 advice 去原文，日志补堆栈                                                                                                                                                                |
| `src/main/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanAsyncProcessor.java` | 修改 | `generate readme error` 固定文案并记日志                                                                                                                                                                   |
| `src/main/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanServiceImpl.java`    | 修改 | SBOM 解析失败、SSRF 拒绝、人工补充写入失败 3 处去原文                                                                                                                                                      |
| `src/main/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImpl.java`           | 修改 | PR diff 获取失败 2 处去原文                                                                                                                                                                                |
| `src/main/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutor.java`               | 修改 | 15 处 `ScaException` 去原文（含 no download candidate 的 URL 回显），补 `LOGGER.error`；聚合失败异常去 `lastError.getMessage()`                                                                            |
| `src/test/java/com/openlibing/sca/common/exception/DefaultExceptionHandlerTest.java`    | 修改 | 新增固定文案、空消息、方法不支持、脱敏规则 4 类用例（该文件共 16 个用例）                                                                                                                                  |
| `src/test/java/com/openlibing/sca/analysis/controller/LicenseControllerTest.java`       | 修改 | 异常路径断言固定文案                                                                                                                                                                                       |
| `src/test/java/com/openlibing/sca/analysis/controller/OpenScanControllerTest.java`      | 修改 | 2 个异常路径断言固定文案                                                                                                                                                                                   |

## 风险 & 缓解

| 风险                                                                                                                                             | 缓解                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| 排障信息减少，线上定位变难                                                                                                                       | 服务端 ERROR 日志保留异常类型 + 脱敏详情 + 请求上下文；完整异常仍可由 `LOGGER.error(..., e)` 输出堆栈                  |
| `SQL_STATEMENT_PATTERN` 以 `create/update/select` 等通用动词开头匹配到句尾，可能把非 SQL 文案（如 `create target dir failed`）整体替换为 `[sql]` | 仅影响日志可读性，不影响客户端响应；如后续出现排查障碍可收窄正则以 `\b` + SQL 关键字组合匹配                           |
| 512 字符截断可能截断关键错误码/后缀                                                                                                              | 追加 `...(truncated)` 保留截断信号；错误码与异常类型独立字段，不受截断影响                                             |
| 客户端/调用方依赖异常原文做分支判断                                                                                                              | 属预期内的安全收紧；错误码与固定文案保持稳定语义                                                                       |
| 残留回显点：`JGitUtil.java:93`（advice 带 `e.getMessage()`）、`DownLoadFilesUtils.java:264`（errorMsg 拼接 `e.getMessage()`）                    | 已在本 spec 记为遗留项；`DownLoadFilesUtils` 的 `ScaException` 由 `CompletableFuture` 内抛出，是否最终回显客户端未验证 |
| 新增具体文案与前端既有提示不一致                                                                                                                 | 固定文案取自 `ErrorCode` 或业务常量（如"查询社区版本扫描记录失败"），Controller 测试已断言                             |

## 跨仓影响

无。仅本服务的错误响应文案与日志格式变化，不涉及接口结构、配置或数据模型；文档归档至
`openlibing-docs`（本目录）。
