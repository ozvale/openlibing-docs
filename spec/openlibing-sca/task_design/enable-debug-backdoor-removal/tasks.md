# enable-debug-backdoor-removal — 实现任务

## 进度: 2/2 complete

- [x] Task 1: 删除 `dumpStack()` 与全部 28 处调用（`a16aef2f`）
  - `DefaultExceptionHandler` 移除 `dumpStack(HttpServletRequest, Throwable)`（含
    `request.getParameter("enable_debug")` 与 `LOGGER.error("enable.debug.error.stack->", tx)`）
  - 移除 `defaultErrorHandler` 及各 `@ExceptionHandler` 分支中的 `dumpStack(request, ex)`
  - `DefaultExceptionHandlerTest` 删除 `enable_debug` mock / `verify` 及无用静态导入，保留原有 16 个
    错误码与脱敏用例
- [x] Task 2: 静态核验与交付
  - 全量检索 `src`：`enable_debug`、`enable.debug`、`dumpStack` 0 命中
  - 主源码 `getParameter(` 0 命中，确认无其他请求参数控制的日志开关
  - 响应仍为 `ErrorCode` 固定文案 + 错误码，`logHandledException` 脱敏链路（#151）保持不变

## 交付记录

| commit     | 日期       | 摘要                                                        | 关联        |
| ---------- | ---------- | ----------------------------------------------------------- | ----------- |
| `a16aef2f` | 2026-11-05 | fix(common): remove enable_debug remote stack-dump backdoor | `Refs #149` |

- 分支：`ms_scan`（commit 为 HEAD 祖先）
- 变更规模：2 文件，+0 / -70 行
- 验证方式：静态核验（grep 0 命中）+ diff 复核；本轮为回溯文档，**未执行 `mvn test`**
  （会写入 `target/`，超出只读约束）
- 测试影响：`DefaultExceptionHandlerTest` 16 个用例保留，`testLogHandledExceptionWithNullRequestDoesNotRecurse`
  等防回归用例未受影响
- 未覆盖项：prod 日志级别/pattern 收紧（P1）、CI 静态规则（P2）
