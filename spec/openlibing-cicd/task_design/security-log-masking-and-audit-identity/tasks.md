# security-log-masking-and-audit-identity — 实现任务

## 进度: 7/7 complete

- [x] Task 1: 新增敏感字段脱敏与日志安全序列化，移除消息头携带的验签凭证（`4c8afa7ec`）
- [x] Task 2: 补齐脱敏回归用例，覆盖转义形态 JSON 凭证（`73ef06cbd`）
- [x] Task 3: 收敛 URL 令牌正则取值域并修正脱敏边界用例（`b533ce475`）
- [x] Task 4: 敏感值含转义字符时整段脱敏（`eb480a292`）
- [x] Task 5: 审计 `userId` 改取验签令牌声明并对齐日志转义（`b16378cd0`）
- [x] Task 6: 补充审计 `userId` 回退用例（`99b6d924d`）
- [x] Task 7: 收敛审计身份读取顺序并扩展日志控制字符转义（`3cf34a135`）

## 详细任务

### Task 1: 敏感字段脱敏与日志安全序列化

- 文件：`src/main/java/com/openlibing/cicd/common/utils/MessageMaskUtils.java`
- 改动：
  - 新增 `SENSITIVE_FIELDS_PATTERN`：`"\"((?:accessToken|access_token|token|password|secret|privateKey|private_key|x-gitee-token|x-gitee-password|x-gitcode-token|private-token|authorization))\"\\s*:\\s*\"(?:[^\"\\\\]|\\\\.)*\""`，`Pattern.CASE_INSENSITIVE`，替换为 `"$1":"******"`（最终形态，已能跨过转义引号）。
  - 新增 `ESCAPED_SENSITIVE_FIELDS_PATTERN`：匹配内嵌 JSON 被二次转义后的 `\\"password\\":\\"value\\"` 形态，替换时保留原转义层级。
  - 新增 `URL_TOKEN_PATTERN`：`([?&](?:access_token|private_token|accessToken)=)[^&\\s\"'<>\\\\]+`，替换为 `$1******`。
  - 新增 `maskSensitiveFields(String messageJson)`：空/空白原样返回，其余依次执行上述三条正则替换。
  - 新增 `toSafeLogJson(Object)`：序列化为日志用 JSON，剔除 `accessToken`、`configJson`、`tableData`；序列化失败返回 `<unavailable>`，不向调用方抛异常。
  - 移除消息头中携带的验签凭证：`ApigWebhookController`、`WebHookEventController`、`WebHookEventConsumer` 及对应两个测试类。
- commit：`4c8afa7ec` fix(webhook): 脱敏事件日志中的令牌并移除消息头携带的验签凭证
- 验证方式：日志文本中敏感字段显示为 `******`；`configJson` / `tableData` 不出现在日志 JSON；序列化失败返回 `<unavailable>`。

### Task 2: 脱敏回归用例

- 文件：`src/test/java/com/openlibing/cicd/common/utils/MessageMaskUtilsTest.java`
- 改动：补齐脱敏回归用例，覆盖转义形态 JSON 凭证
- commit：`73ef06cbd` test(webhook): 补齐脱敏回归用例并覆盖转义形态 JSON 凭证
- 验证方式：运行 `MessageMaskUtilsTest`（累计 21 条用例）全部通过。

### Task 3: 收敛 URL 令牌正则取值域

- 文件：`src/main/java/com/openlibing/cicd/common/utils/MessageMaskUtils.java`、`src/test/java/com/openlibing/cicd/common/utils/MessageMaskUtilsTest.java`
- 改动：收敛 URL 中 token 的取值域，避免误伤非凭证内容；同步修正脱敏边界用例
- commit：`b533ce475` fix(utils): 收敛 URL 令牌正则取值并修正脱敏边界用例
- 验证方式：含非凭证内容的 URL 不再被整体脱敏；边界用例通过。

### Task 4: 转义字符场景整段脱敏

- 文件：`src/main/java/com/openlibing/cicd/common/utils/MessageMaskUtils.java`、`src/test/java/com/openlibing/cicd/common/utils/MessageMaskUtilsTest.java`
- 改动：敏感值含转义反斜杠/引号时 `[^"]*` 会提前截断导致只脱敏半截，改为整段脱敏
- commit：`eb480a292` fix(utils): 敏感值含转义字符时整段脱敏
- 验证方式：含转义字符的凭证值在日志中整体显示为 `******`，无残留尾部。

### Task 5: 审计 userId 改取验签令牌声明

- 文件：`src/main/java/com/openlibing/cicd/common/operationlog/AsyncOperationLogIdentity.java`、`src/main/resources/logback-spring.xml`
- 改动：
  - `capture()`（约 56-78 行）新增读取 `UserInfoConstants.FIELD_USER_ID`（`"userId"`）声明，`StringUtils.isNotBlank` 时覆盖 `userId`；覆盖语句置于最后，claim 形态异常时不连带丢弃其余已验签身份；外层 `catch (RuntimeException ignored)` 保留，验签异常回退网关注入参数。
  - `logback-spring.xml` 三处 `%replace` 正则与审计链路日志转义对齐。
- commit：`b16378cd0` 审计 userId 改取验签令牌声明并对齐日志转义
- 验证方式：令牌含 `userId` 声明时审计日志记录声明值；日志中控制字符被替换为 `|`。

### Task 6: 审计 userId 回退用例

- 文件：`src/test/java/com/openlibing/cicd/common/operationlog/AsyncOperationLogIdentityTest.java`
- 改动：
  - 改造 `authenticatedCookieAccountsOverrideRequestParameters`：加 `withClaim("userId","真实用户ID")` 并断言 `userId()` 为真实用户 ID。
  - 新增 3 例，均断言回退调用方 `u1`：`tokenWithoutUserIdClaimKeepsCallerSuppliedUserId`、`invalidTokenKeepsCallerSuppliedUserId`（token 为 null）、`tokenVerificationFailureKeepsCallerSuppliedUserId`（验签抛 `IllegalStateException`）。
- commit：`99b6d924d` 补充审计 userId 回退用例
- 验证方式：`AsyncOperationLogIdentityTest` 全部通过，4 条身份相关用例断言符合预期。

### Task 7: 收敛读取顺序并扩展控制字符转义

- 文件：`src/main/java/com/openlibing/cicd/common/operationlog/AsyncOperationLogIdentity.java`、`src/main/resources/logback-spring.xml`
- 改动：
  - 收敛审计身份读取顺序：`userId` 覆盖置于其余身份字段之后。
  - `CONSOLE_LOG_PATTERN`（13-15 行）、`FILE_LOG_PATTERN`（16 行）、`MANAGE_LOG_FILE` appender pattern（56-65 行）三处正则由 `'[\r\n\t\f\u007f\u0008\u000b]'` 扩为 `'[\r\n\t\f\u0000-\u0008\u000b\u000e-\u001f\u007f\u0085\u2028\u2029]'`，替换符仍为 `|`。
- commit：`3cf34a135` 收敛审计身份读取顺序并扩展日志控制字符转义
- 验证方式：构造含 C0 控制字符及 `\u0085` / `\u2028` / `\u2029` 的日志内容，输出被替换为 `|`，日志行不被拆分；claim 形态异常时其余已验签身份字段仍保留。

## PR 归属

| PR                             | 分支                                                                 | 覆盖任务 |
| ------------------------------ | -------------------------------------------------------------------- | -------- |
| openlibing/openlibing-cicd#633 | `fix/security-vuln-242-token-desensitize` → `release_20261029_iter2` | Task 1-4 |
| openlibing/openlibing-cicd#627 | `fix/security-vuln-1010-015`（head `3cf34a1`，merge-base `1a8efc1`） | Task 5-7 |
