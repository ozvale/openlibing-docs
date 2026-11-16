# request-param-log-whitelist — 实现任务

## 进度: 2/2 complete

- [x] Task 1: `LoggerAppend` 参数白名单（`9bb8b7f1`）
  - 新增 `LOGGABLE_PARAMETERS`（18 项：scanid / repoid / projectid / communityid / issueid / deptid /
    producttype / valuelabel / platform / community / version / type / typelevel / pageno / pagesize /
    refreshtime / refreshcommunity / filehash）
  - 新增 `isLoggableParameter(String)`，`toLowerCase(Locale.ROOT)` 后判断
  - `create` 遍历 `getParameterMap()` 时跳过非白名单参数，其余行为（多值、空值、前缀、URI）不变
  - 新增 `LoggerAppendTest` 5 个用例：`create_appendsUriAndType`、`create_appendsWhitelistedParameters`、
    `create_skipsSensitiveParameters`、`create_appendsMultipleValuesOfWhitelistedParameter`、
    `create_appendsNullForEmptyValues`
- [x] Task 2: 静态核验与交付
  - 确认 `DefaultExceptionHandler` 28 处 `LoggerAppend.create(request, LoggerType.ERROR)` 签名未变
  - 确认敏感参数（token/userId/userName/password/code/repoUrl）不在白名单内
  - 单测断言日志既不含键名也不含值

## 交付记录

| commit     | 日期       | 摘要                                                            | 关联        |
| ---------- | ---------- | --------------------------------------------------------------- | ----------- |
| `9bb8b7f1` | 2026-11-13 | fix(common): whitelist request parameters written to error logs | `Refs #161` |

- 分支：`ms_scan`（commit 为 HEAD 祖先）
- 变更规模：2 文件 +123/-0（`LoggerAppend.java` +41，`LoggerAppendTest.java` +82）
- 验证方式：diff 复核 + 代码现状确认；本轮为回溯文档，**未执行 `mvn test`**（会写入 `target/`，
  超出只读约束）
- 测试覆盖（代码中已存在）：`LoggerAppendTest` 5 个用例
- 未覆盖项：白名单以外的日志语句（非 `LoggerAppend` 路径）未做全仓审查
