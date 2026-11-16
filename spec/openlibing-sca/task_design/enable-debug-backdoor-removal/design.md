# enable-debug-backdoor-removal — 技术设计

## 方案概述

删除 `DefaultExceptionHandler` 中由 HTTP 参数驱动的调试开关：移除 `dumpStack()` 方法体与全部调用点，
使异常处理链路只保留"固定文案响应 + 结构化 ERROR 日志"两条路径，不再存在外部可控的堆栈输出开关。
排障信息改由同批次 #151 建立的 `exceptionType` + 脱敏 `exceptionDetail` 日志提供。

## 数据流（修复后）

```
HTTP 请求（含 ?enable_debug=true）
  └─ 业务异常
       └─ DefaultExceptionHandler.@ExceptionHandler
            ├─ errorCode / errorMsg / adviceMsg ← ErrorCode 常量（固定文案）
            ├─ appendError(LoggerAppend ...)      ← 仅白名单参数、错误码/文案
            ├─ logHandledException(request, errorCode, errorMsg, ex)
            │     └─ ERROR 日志：errorCode、errorMsg、exceptionType、
            │        sanitizeExceptionDetail(ex.getMessage())（#151）、URI/Method/IP/UA/Referer
            └─ DataResult.failure(errorCode, errorMsg, adviceMsg)  → 客户端
```

`enable_debug` 参数在整个链路中不再被读取，携带与否对日志与响应均无影响。

## 架构决策

| 决策                                                          | 理由                                                                                                 |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| D1 直接删除 `dumpStack()`，不做 profile / 配置化保留          | 只要是"外部请求可开关"的堆栈输出就是后门；Issue P0 明确要求彻底移除请求参数开关                      |
| D2 同时删除 28 处调用点而非保留空方法                         | 空方法会被后续开发者误认为能力仍在并重新接线；编译器/静态检索可直接确认零残留                        |
| D3 不改变各 `@ExceptionHandler` 的返回结构与错误码            | 与 #151（响应文案与日志脱敏）解耦，避免同文件两批改动互相覆盖；错误码语义保持不变                    |
| D4 排障能力由 #151 的结构化日志承担                           | `exceptionType` + 脱敏 `exceptionDetail`（512 字符截断）+ 请求上下文，足以定位问题且不受请求参数控制 |
| D5 单测同步移除 `enable_debug` mock 与 `verify(getParameter)` | 避免测试固化已删除行为，防止后续误加回该参数                                                         |

## 涉及文件

| 文件                                                                                 | 操作 | 说明                                                                                                                                         |
| ------------------------------------------------------------------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/common/exception/DefaultExceptionHandler.java`     | 修改 | 删除 `dumpStack` 方法（-13 行）与 28 处调用（每个 handler -1 行），文件净减 41 行                                                            |
| `src/test/java/com/openlibing/sca/common/exception/DefaultExceptionHandlerTest.java` | 修改 | 删除 28 处 `when(request.getParameter("enable_debug"))` 及 1 处 `verify(...getParameter)`，删除不再使用的 `when`/`verify` 静态导入（-29 行） |

不涉及其他类：`getParameter(` 在 `src/main/java` 全量检索 0 命中，确认无其他请求参数驱动的日志开关。

## 风险 & 缓解

| 风险                                                       | 缓解                                                                                                          |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 线上排障时无法临时开启堆栈，定位效率下降                   | #151 已把异常类型与脱敏详情写入 ERROR 日志，且响应仍返回错误码；必要时通过日志级别与 APM 定位，不依赖请求参数 |
| ERROR 级固定文案日志仍可被匿名批量触发，日志洪泛未彻底消除 | 单条日志体积从完整堆栈降为单行，洪泛影响显著下降；频控/限流属网关层能力，本轮未覆盖                           |
| 删除调用点遗漏导致编译失败                                 | 编译期即可发现；`dumpStack` 方法已删除，残留调用无法编译                                                      |
| prod `logback-spring.xml` 仍为 root=info、FILE 阈值 INFO   | Issue P1 未覆盖，记为后续项；当前日志内容已不含堆栈（固定文案 + 脱敏详情）                                    |

## 跨仓影响

无。仅 `openlibing-sca` 内部异常处理实现，接口契约、配置与数据均不变。
