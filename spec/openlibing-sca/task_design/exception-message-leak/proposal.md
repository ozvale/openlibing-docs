# exception-message-leak — 全局异常处理器不再回显原始异常消息（#151）

## 需求背景

安全 Issue：[openlibing/openlibing-sca#151](https://gitcode.com/openlibing/openlibing-sca/issues/151)
（安全 / 敏感信息泄露，CWE-209，低危；来源 Argus 批次 `openlibingsca-20261103130601-013`）。

`DefaultExceptionHandler` 多个 `@ExceptionHandler` 分支把 `ex.getMessage()` 拼进响应体 `msg`
（`errorMsg += String.format(Locale.ROOT, "(%s)", ex.getMessage())` 模式，全文件 24 处），
`DataResult.failure` 直接返回客户端。可被外部输入稳定触发的泄露面包括：

- `SsrfsafeUrlUtil` 抛出的 `IllegalArgumentException`（含 URL/协议细节）；
- `DateUtils` 解析异常；
- `ConfirmReviewServceImpl` / `OpenScanDMServiceImpl` 解析外部数据时的 fastjson2 异常；
- `SQLException` 分支（`:712`）的 SQL 语句片段。

此外 Controller catch 块存在 `ResponseEntity.failure(e.getMessage())` /
`failure(500, e.getMessage())` 的直接回显，以及大量 `new ScaException(..., "xxx: " + e.getMessage(), ...)`
把异常原文写入客户端可见的 `errorMsg` / `adviceMsg`。

## 功能描述

**做什么**：

1. 移除 24 处 handler 响应消息拼接，响应统一为 `ErrorCode` 固定文案 + 错误码（`advice` 亦为固定文案）。
2. 服务端日志保留排障能力：`logHandledException(request, errorCode, errorMsg, ex)` 追加
   `exceptionType` 与 `exceptionDetail`；`sanitizeExceptionDetail` 负责控制字符替换、jdbc 连接串 /
   SQL 片段 / 绝对路径 / URL 剥离、512 字符截断。
3. 统一 Controller 异常信封：10 处 `ResponseEntity.failure(e.getMessage())` /
   `failure(e.getErrorMsg())` 改为三参 `failure(e.getErrorCode(), e.getErrorMsg(), e.getAdviceMsg())`
   （`FileController`、`OpenPersonScanController`、`OpenScanController`）。
4. 移除 22 处 `new ScaException(...)` 中拼接的原始异常消息（提交信息统计），改为固定业务文案；
   缺少 logger 的调用点补 `LOGGER.error(..., e)`，原始细节保留在服务端日志。
5. 修复 `methodNotSupportErrorException` 参数类型错配（声明 `HttpRequestMethodNotSupportedException`
   但形参为 `BindException`）。
6. 聚合异常不再拼接最后一个候选的错误消息（下载失败场景曾把 URL 与 500 字符响应片段带出）。
7. 补充/更新单测：固定文案断言、空消息不 NPE、脱敏规则、Controller 异常路径。

**不做什么**：

- 未落地 P2 静态检测规则（Checkstyle/SpotBugs/PMD 拦截 `getMessage()` 进响应），本轮未覆盖。
- 未统一全仓所有错误响应封装（仅处理 issue 指出的 handler、controller catch 与已识别的
  `ScaException` 构造点）；`JGitUtil`、`DownLoadFilesUtils` 仍有 2 处残留（见"验收标准"）。

## 验收标准

- [x] 对应异常类型触发时响应 `msg` 为固定文案 + 错误码，不含 `ex.getMessage()` 内容：
      24 处 `errorMsg += ... ex.getMessage()` 全部移除；`failure(... getMessage())` 在
      `src/main/java` 检索 0 命中（`DefaultExceptionHandlerTest#testHandlerReturnsFixedMsgWithoutExceptionDetail`、
      `#testHandlerWithBlankExceptionMessage`、`#testMethodNotSupportErrorReturnsFixedMsg`）
- [x] 服务端日志不出现 SQL 片段、jdbc 连接串、绝对路径：
      `sanitizeExceptionDetail` 四类正则替换 + 控制字符替换（`testSanitizeExceptionDetail` 覆盖
      `[sql]` / `[jdbc-url]` / `[path]` / `[url]` 与截断）
- [x] 空消息 / 超长消息异常不导致 NPE，仍返回固定文案：
      `sanitizeExceptionDetail(null/"")` 返回空串；超长输入截断并追加 `...(truncated)`
- [x] 既有正常业务响应不受影响；`defaultErrorHandler` 固定文案行为不变：
      该分支仍按 future / 参数缺失 / 未预期三类选择 `ErrorCode` 文案，未引入原始消息
- [ ] Controller 层 `ScaException` 的 `adviceMsg` 不回显原始异常（部分满足）：
      `JGitUtil.java:93` 仍将 `e.getMessage()` 作为 `adviceMsg`；
      `DownLoadFilesUtils.java:264` 仍将 `e.getMessage()` 拼入 `errorMsg`（异常是否最终回显客户端未验证）
- [ ] P2 静态规则（CI 门禁防回归）本轮未覆盖

## 影响范围

- 业务仓：`openlibing-sca`
  - `common/exception`：`DefaultExceptionHandler` + 单测
  - `analysis/controller`：`FileController`、`OpenPersonScanController`、`OpenScanController`、`LicenseController` + 相关单测
  - `analysis/service`、`analysis/utils/security`、`dm/service`、`dm/util`：`ScaException` 文案收敛
- 接口：无新增/删除，错误响应文案收紧为固定文案；依赖异常原文做判断的调用方可能受影响（预期内的安全收紧）
- 配置、数据库 schema：无变化
