# enable-debug-backdoor-removal — 移除 enable_debug 远程堆栈日志后门（#149）

## 需求背景

安全 Issue：[openlibing/openlibing-sca#149](https://gitcode.com/openlibing/openlibing-sca/issues/149)
（安全 / 敏感日志与调试后门，CWE-532，中危；来源 Argus 批次 `openlibingsca-20261103130601-014`）。

修复前 `DefaultExceptionHandler#dumpStack()`（`common/exception/DefaultExceptionHandler.java`）读取 HTTP
请求参数 `enable_debug`，值等于 `"true"` 时执行
`LOGGER.error("enable.debug.error.stack->", tx)` 输出完整异常堆栈：29 个 `@ExceptionHandler` 中 28 处调用
该方法（含 catch-all 的 `defaultErrorHandler`）。该开关：

- 由外部请求参数控制，无 `@Profile` / `profiles.active` 门禁、无鉴权；
- `logback-spring.xml` root=info、FILE appender 阈值 INFO，ERROR 堆栈必然写入
  `/var/logs/openlibing-sca/openlibing-sca.log`（200MB / 7 天滚动）；
- 堆栈含内部类名、源码路径、调用链，`SQLException` / `BadSqlGrammarException` 场景含 SQL 语句；
- 可被匿名批量触发，造成日志洪泛、挤压磁盘并淹没有效告警。

## 功能描述

**做什么**：

1. 删除 `DefaultExceptionHandler#dumpStack` 方法；
2. 删除全部 28 处调用点（`defaultErrorHandler` 与各 `@ExceptionHandler` 分支）；
3. 清理单测中为该方法服务的 `enable_debug` mock 与 `verify(request).getParameter("enable_debug")` 断言，
   保持既有错误码/固定文案用例不变。

**不做什么**：

- 未调整 `logback-spring.xml` 的 prod 日志级别与 pattern（Issue P1：异常处理包不低于 WARN、
  pattern 不输出完整堆栈），本轮未覆盖，配置保持 `root level=info`、FILE `ThresholdFilter=INFO`。
- 未新增 CI 静态规则拦截"请求参数控制日志行为"（Issue P2，本轮未覆盖）。
- 未引入新的服务端配置化调试开关：排障依赖同批次 #151 落地的 `exceptionType` + 脱敏 `exceptionDetail`
  日志（见 `../exception-message-leak`）。

## 验收标准

- [x] 代码中不存在 `enable_debug` 参数读取与 `enable.debug.error.stack->` 日志文案：
      对 `openlibing-sca/src` 全量检索 `enable_debug`、`enable.debug`、`dumpStack` 均 0 命中
      （测试代码中同样为 0，`a16aef2f` 已删除相关 mock/verify）
- [x] 任意端点携带 `?enable_debug=true` 触发异常，不再输出完整堆栈：
      handler 不再读取该参数，响应体为 `ErrorCode` 固定文案 + 错误码
- [x] 不存在任何由 HTTP 请求参数控制的日志级别/堆栈开关：
      主源码中 `getParameter(` 检索 0 命中
- [x] 既有错误码返回与日志净化逻辑不回退：
      `DefaultExceptionHandlerTest` 16 个用例保留（`defaultErrorHandler` 三分类固定文案、
      各异常分支固定文案、`sanitizeExceptionDetail` 脱敏、`logHandledException` 空请求防递归），
      仅删除了已无意义的 `enable_debug` mock
- [ ] prod profile 异常处理包日志级别不低于 WARN、pattern 不输出完整堆栈（本轮未覆盖）

## 影响范围

- 业务仓：`openlibing-sca`（`common/exception/DefaultExceptionHandler.java` 及其单测）
- 接口：无契约变化（响应体、错误码均不变）
- 配置：无变化（`logback-spring.xml` 未改动）
- 数据库 schema：无变化
