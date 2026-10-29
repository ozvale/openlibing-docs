# security-log-masking-and-audit-identity: 收敛日志中的凭证与可伪造的审计身份

## 需求背景

本 spec 覆盖两个同源问题，共同点是"日志/审计链路里流入了不可信数据"：

1. **日志中的凭证泄露（OpenLibing-cicd Issue #242）**：事件消息 JSON 与消息 URL 中的 `accessToken` / `token` / `password` / `secret` / `privateKey` 等字段被原样写入日志；同时在消息头中携带验签凭证，进一步扩大了凭证的暴露面。
2. **可伪造的审计身份（OpenLibing-cicd Issue #348）**：`AsyncOperationLogIdentity.capture()` 在验签成功后仅用验签令牌覆盖 `userName` / `accountId` / `accountName` / `accountPlatform`，`userId` 始终取调用方入参，攻击者可通过请求参数伪造审计身份；同时日志 pattern 的控制字符转义范围不足，存在日志注入伪造行的空间。

## 功能描述

- **PR 633（Issue #242）**：新增/收敛 `MessageMaskUtils`，对消息 JSON 中的敏感字段整段脱敏，对 URL 中的令牌取值域做收敛；新增 `toSafeLogJson` 作为日志用序列化入口，剔除 `accessToken` / `configJson` / `tableData` 并在序列化失败时返回常量 `<unavailable>`；移除消息头中携带的验签凭证。
- **PR 627（Issue #348）**：审计身份 `userId` 改为"验签令牌声明优先、调用方参数回退"，覆盖语句置于最后以避免 claim 形态异常时连带丢弃其余已验签身份；`logback-spring.xml` 三处 `%replace` 正则扩展为覆盖全部 C0 控制字符与 `\u0085` / `\u2028` / `\u2029`。

两项改动均只影响日志文本与审计日志取值来源，无 HTTP 接口与出入参变化，无 pom 变更，无新增配置项。

## 验收标准

- [x] `MessageMaskUtils.SENSITIVE_FIELDS_PATTERN` 以 `Pattern.CASE_INSENSITIVE` 匹配 `accessToken|access_token|token|password|secret|privateKey|private_key|x-gitee-token|x-gitee-password|x-gitcode-token|private-token|authorization` 字段，并整段替换为 `"$1":"******"`；`ESCAPED_SENSITIVE_FIELDS_PATTERN` 覆盖内嵌转义 JSON 形态
- [x] `maskSensitiveFields` 对空/空白输入原样返回，其余输入按正则整段替换
- [x] `toSafeLogJson` 剔除 `accessToken`、`configJson`、`tableData`，序列化失败返回 `<unavailable>` 且不向调用方抛异常
- [x] URL 中的令牌取值域已收敛：`URL_TOKEN_PATTERN` 仅匹配 `access_token` / `private_token` / `accessToken` 三个查询参数名，非凭证内容不再被误伤
- [x] 敏感值包含转义反斜杠/引号时整段脱敏，不再出现只脱敏半截的情况
- [x] 消息头不再携带验签凭证
- [x] `MessageMaskUtilsTest` 共 21 条用例全通过，覆盖 JSON 字段脱敏、非敏感字段保留、value 非字符串不误伤、转义值与引号边界、`toSafeLogJson` 剔除大字段与序列化失败兜底
- [x] `AsyncOperationLogIdentity.capture()` 在验签令牌含 `userId` 声明（非空白）时使用声明值覆盖调用方入参
- [x] 覆盖 `userId` 的语句位于其余身份字段覆盖之后，claim 形态异常时不连带丢弃其余已验签身份
- [x] 验签异常（`RuntimeException`）时仍回退网关注入参数，不中断审计写入
- [x] `AsyncOperationLogIdentityTest` 改造 `authenticatedCookieAccountsOverrideRequestParameters` 并新增 3 条回退用例，均断言回退调用方 `u1`
- [x] `logback-spring.xml` 的 `CONSOLE_LOG_PATTERN`、`FILE_LOG_PATTERN`、`MANAGE_LOG_FILE` 三处 `%replace` 正则统一扩展为 `'[\r\n\t\f\u0000-\u0008\u000b\u000e-\u001f\u007f\u0085\u2028\u2029]'`，替换符仍为 `|`
- [x] 无 HTTP 接口、出入参、数据模型、pom、配置项变更

## 影响范围

| 文件                                                                                       | 操作 | 说明                                                                           |
| ------------------------------------------------------------------------------------------ | ---- | ------------------------------------------------------------------------------ |
| `src/main/java/com/openlibing/cicd/common/utils/MessageMaskUtils.java`                     | 修改 | 敏感字段脱敏正则、URL 令牌取值收敛、转义值整段脱敏、`toSafeLogJson` 日志序列化 |
| `src/test/java/com/openlibing/cicd/common/utils/MessageMaskUtilsTest.java`                 | 修改 | 补齐脱敏回归用例，覆盖转义形态 JSON 凭证，共 21 条                             |
| `src/main/java/com/openlibing/cicd/common/operationlog/AsyncOperationLogIdentity.java`     | 修改 | `capture()` 审计 `userId` 改取验签令牌声明，声明缺失/验签异常时回退调用方入参  |
| `src/test/java/com/openlibing/cicd/common/operationlog/AsyncOperationLogIdentityTest.java` | 修改 | 改造 1 条既有用例 + 新增 3 条回退用例                                          |
| `src/main/resources/logback-spring.xml`                                                    | 修改 | 三处 `%replace` 正则扩展控制字符转义范围（13-15 行、16 行、56-65 行）          |
| `src/main/java/com/openlibing/cicd/business/controller/ApigWebhookController.java`         | 修改 | 移除事件消息头中携带的验签凭证                                                 |
| `src/main/java/com/openlibing/cicd/business/controller/WebHookEventController.java`        | 修改 | 移除事件消息头中携带的验签凭证                                                 |
| `src/main/java/com/openlibing/cicd/business/listener/WebHookEventConsumer.java`            | 修改 | 消息消费链路日志改走 `toSafeLogJson` / `maskSensitiveFields`                   |
| `src/test/java/com/openlibing/cicd/business/controller/ApigWebhookControllerTest.java`     | 修改 | 同步移除消息头验签凭证断言                                                     |
| `src/test/java/com/openlibing/cicd/business/controller/WebHookEventControllerTest.java`    | 修改 | 同步移除消息头验签凭证断言                                                     |

## 关联 Issue

- openlibing/openlibing-cicd#242 —— https://gitcode.com/openlibing/openlibing-cicd/issues/242
- openlibing/openlibing-cicd#348 —— https://gitcode.com/openlibing/openlibing-cicd/issues/348

## 关联 PR 与提交

| PR                             | 标题                                                                  | 分支                                                                 | commit                                             |
| ------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------- |
| openlibing/openlibing-cicd#633 | `fix(security): Webhook 事件日志令牌脱敏并移除消息头验签凭证（#242）` | `fix/security-vuln-242-token-desensitize` → `release_20261029_iter2` | `4c8afa7ec`、`73ef06cbd`、`b533ce475`、`eb480a292` |
| openlibing/openlibing-cicd#627 | `fix(security): 审计身份改取验签令牌并转义操作日志控制字符（#348）`   | `fix/security-vuln-1010-015`（head `3cf34a1`，merge-base `1a8efc1`） | `b16378cd0`、`99b6d924d`、`3cf34a135`              |
