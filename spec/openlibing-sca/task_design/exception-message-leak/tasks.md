# exception-message-leak — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 全局异常处理器去原文回显，日志侧补脱敏详情（`590ecb39`）
  - `DefaultExceptionHandler`：移除 24 处 `errorMsg += ... ex.getMessage()`，响应取 `ErrorCode` 固定文案
  - 新增 `sanitizeExceptionDetail`（控制字符、jdbc 连接串、SQL 片段、绝对路径、URL、512 截断）与
    `logHandledException(..., Throwable ex)`
  - 修复 `methodNotSupportErrorException` 形参类型（`BindException` → `HttpRequestMethodNotSupportedException`）
  - 统一 10 处 Controller catch 为三参 `failure(errorCode, errorMsg, adviceMsg)`
    （`FileController`、`OpenPersonScanController`、`OpenScanController`）
  - `DefaultExceptionHandlerTest` 新增 4 类用例（固定文案 / 空消息 / 方法不支持 / 脱敏）
- [x] Task 2: 清理 Controller 与 `ScaException` 内嵌原始消息（`88496e5c`）
  - `LicenseController`、`OpenScanController` 3 处 `failure(500, e.getMessage())` → 固定文案 + `LOGGER.error`
  - 22 处 `new ScaException(..., "xxx: " + e.getMessage(), ...)` 去原文，覆盖
    `ProjectNoticeScanExecutor`、`ProjectNoticeScanAsyncProcessor`、`ProjectNoticeScanServiceImpl`、
    `ScanCommonServiceImpl`、`DownLoadFilesUtils`、`OpenScanServiceImpl`
  - 缺 logger 的调用点补 `LOGGER.error(..., e)`
  - `LicenseControllerTest`、`OpenScanControllerTest` 断言固定文案
- [x] Task 3: 聚合异常不再拼接最后候选错误（`a7e439bb`）
  - `ProjectNoticeScanExecutor` 全部候选下载失败时改为
    `LOGGER.error("all download candidates failed", lastError)` + `ScaException(500, "all download candidates failed", "")`
- [x] Task 4: 静态核验与交付
  - `src/main/java` 检索 `failure(...getMessage())` 0 命中
  - `DefaultExceptionHandler` 仅 `permissionException` 分支返回 `ex.getMessage()`（`PermissionException`
    为 SDK 业务异常，文案为常量"权限不足"，非外部输入回显）
  - 残留：`JGitUtil.java:93`（advice）、`DownLoadFilesUtils.java:264`（errorMsg）仍含 `e.getMessage()`，
    记为遗留项

## 交付记录

| commit     | 日期       | 摘要                                                                     | 关联        |
| ---------- | ---------- | ------------------------------------------------------------------------ | ----------- |
| `590ecb39` | 2026-11-05 | fix(common): stop echoing raw exception messages to clients              | `Refs #151` |
| `88496e5c` | 2026-11-11 | fix(exception): stop echoing raw exception details to clients            | `Refs #151` |
| `a7e439bb` | 2026-11-11 | fix(exception): stop leaking download error details in aggregate message | `Refs #151` |

- 分支：`ms_scan`（三个 commit 均为 HEAD 祖先）
- 变更规模：`590ecb39` 5 文件 +230/-120；`88496e5c` 10 文件 +57/-33；`a7e439bb` 1 文件 +3/-5
- 验证方式：diff 复核 + 静态检索；本轮为回溯文档，**未执行 `mvn test`**（会写入 `target/`，
  超出只读约束）
- 测试覆盖（代码中已存在）：
  - `DefaultExceptionHandlerTest` 16 个用例，含 `testHandlerReturnsFixedMsgWithoutExceptionDetail`、
    `testHandlerWithBlankExceptionMessage`、`testMethodNotSupportErrorReturnsFixedMsg`、
    `testSanitizeExceptionDetail`
  - `LicenseControllerTest#testGetScanByCommunityException`、`OpenScanControllerTest` 异常路径断言固定文案
- 未覆盖项：P2 静态规则；`JGitUtil` / `DownLoadFilesUtils` 两处残留；`DownLoadFilesUtils` 残留是否
  客户端可见未验证
