# security-log-masking-and-audit-identity: 工程设计

## 1. 方案设计

### 问题一：消息与事件日志中的凭证泄露（Issue #242）

- **Source（不可信输入）**：事件消息 JSON 文本与消息中携带的 URL；消息头中的验签凭证。
- **Sink（落地位置）**：日志文本（事件日志、日志文件与控制台输出）。
- **攻击链**：消息体/URL 中的 `accessToken`、`token`、`password`、`secret`、`privateKey` 等凭证 → 原样写入日志 → 具备日志读取权限者获取凭证 → 直接复用凭证调用上游接口。消息头携带验签凭证使凭证在链路中进一步扩散。
- **处置思路**：在日志输出前统一做脱敏，不改变消息在业务链路中的实际内容；对日志用序列化单独提供入口，剔除大字段（`configJson`、`tableData`）与 `accessToken`；消息头不再承载验签凭证。

### 问题二：可伪造的审计身份与日志控制字符注入（Issue #348）

- **Source（不可信输入）**：HTTP 请求参数中的 `userId`（调用方入参）；日志内容中携带的控制字符。
- **Sink（落地位置）**：`AsyncOperationLogIdentity.capture()` 产出的审计日志身份字段；`logback-spring.xml` 中三处日志 pattern 的文本输出。
- **攻击链 A**：请求方在请求参数中填写任意 `userId` → 验签只覆盖 `userName` / `accountId` / `accountName` / `accountPlatform`，`userId` 仍取入参 → 审计日志记录伪造身份，审计链路整体不可信。
- **攻击链 B**：消息内容携带 `\r\n` 之外的 C0 控制字符或 `\u0085`、`\u2028`、`\u2029` → 日志行被拆分/伪造，掩盖真实操作记录。
- **处置思路**：审计身份以验签令牌中的声明为准，声明缺失或验签失败时回退到网关注入参数；日志 pattern 的转义范围扩大到全量 C0 控制字符与 Unicode 行分隔符。

## 2. 实现逻辑设计

### 2.1 敏感字段脱敏（`MessageMaskUtils`）

改前：敏感字段在日志中按原始文本输出。

改后：以正则整段替换，保留字段名、统一掩码值。

以下为**最终形态**（`eb480a292` 之后，与当前代码一致）；`[^"]*` 为改前形态，仅用于说明修正原因。

```java
// 明文 JSON 敏感字段（含请求头形态字段名）
SENSITIVE_FIELDS_PATTERN = "\"((?:accessToken|access_token|token|password|secret|privateKey|private_key"
    + "|x-gitee-token|x-gitee-password|x-gitcode-token|private-token|authorization))\""
    + "\\s*:\\s*\"(?:[^\"\\\\]|\\\\.)*\"";     // CASE_INSENSITIVE，替换为 "$1":"******"

// 内嵌 JSON（消息体被二次序列化，引号转义为 \"）敏感字段，保留原转义形态
ESCAPED_SENSITIVE_FIELDS_PATTERN = "\\\\\"(<同上字段名组>)\\\\\"\\s*:\\s*\\\\\"(?:"
    + ESCAPED_VALUE_BACKSLASH + "|" + ESCAPED_VALUE_QUOTE + "|[^\"\\\\])*\\\\\"";
    // 替换为 \\"$1\\":\\"******\\"

// URL 查询参数中的凭证
URL_TOKEN_PATTERN = "([?&](?:access_token|private_token|accessToken)=)[^&\\s\"'<>\\\\]+";
    // CASE_INSENSITIVE，替换为 $1******
```

- `maskSensitiveFields(String messageJson)`：空/空白输入原样返回；否则依次执行上述三条正则替换（明文 JSON → 内嵌转义 JSON → URL 查询参数）。
- 两轮修正：
  - `b533ce475`：收敛 URL 中 token 的取值域，避免把非凭证内容一起吞掉。
  - `eb480a292`：敏感值内含转义反斜杠/引号时，旧的 `[^"]*` 会提前截断、只脱敏半截；改为 `(?:[^"\\]|\\.)*` 显式匹配转义对，并新增内嵌转义 JSON 专用正则，值结束符只认单个反斜杠加引号。

### 2.2 日志用序列化入口（`toSafeLogJson`）

改前：直接序列化对象后写日志，凭证与大字段一并落盘。

改后：序列化时剔除 `accessToken`、`configJson`、`tableData`；不向调用方抛异常，序列化失败返回常量 `<unavailable>`。

### 2.3 消息头移除验签凭证

改前：消息头中携带验签凭证。

改后：`ApigWebhookController`、`WebHookEventController` 下发事件消息时不再在消息头携带验签凭证，`WebHookEventConsumer` 消费侧同步调整（commit `4c8afa7ec`）。

### 2.4 审计 userId 取值（`AsyncOperationLogIdentity.capture()`，约 56-78 行）

改前：验签后仅覆盖 `userName` / `accountId` / `accountName` / `accountPlatform`，`userId` 始终取调用方入参。

改后：

```java
// 读取 UserInfoConstants.FIELD_USER_ID（"userId"）声明
// StringUtils.isNotBlank 时覆盖 userId
// 该覆盖语句放在最后，claim 形态异常时不会连带丢弃其余已验签身份
```

外层 `catch (RuntimeException ignored)` 保留：验签异常时仍回退网关注入参数。

### 2.5 日志控制字符转义（`logback-spring.xml`）

改前（`CONSOLE_LOG_PATTERN` 13-15 行、`FILE_LOG_PATTERN` 16 行、`MANAGE_LOG_FILE` appender pattern 56-65 行）：

```
'[\r\n\t\f\u007f\u0008\u000b]'
```

改后（三处统一，替换符仍为 `|`）：

```
'[\r\n\t\f\u0000-\u0008\u000b\u000e-\u001f\u007f\u0085\u2028\u2029]'
```

覆盖全部 C0 控制字符，并补充 `\u0085`（NEL）、`\u2028`（LINE SEPARATOR）、`\u2029`（PARAGRAPH SEPARATOR）。

## 3. 类设计

| 类型                                                                | 职责变化                                                                        | 关键成员                                                                                                                                                |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `com.openlibing.cicd.common.utils.MessageMaskUtils`                 | 日志脱敏工具：字段脱敏 + 内嵌转义 JSON 脱敏 + URL 查询参数脱敏 + 日志安全序列化 | `SENSITIVE_FIELDS_PATTERN`、`ESCAPED_SENSITIVE_FIELDS_PATTERN`、`URL_TOKEN_PATTERN`（静态正则）、`maskSensitiveFields(String)`、`toSafeLogJson(Object)` |
| `com.openlibing.cicd.common.operationlog.AsyncOperationLogIdentity` | 审计身份采集，`capture()` 增加 `userId` 声明覆盖逻辑                            | `capture()`（约 56-78 行）；引用 `UserInfoConstants.FIELD_USER_ID`                                                                                      |
| `logback-spring.xml`（配置文件，非类）                              | 三处日志 pattern 的转义正则扩展                                                 | `CONSOLE_LOG_PATTERN`、`FILE_LOG_PATTERN`、`MANAGE_LOG_FILE`                                                                                            |

无新增类、无接口/抽象层调整。

## 4. 数据模型设计

无变更：不涉及数据库表、字段、liquibase changeset、缓存结构或消息体 schema。审计 `userId` 的取值来源变化不改变其存储字段与类型。

## 5. 性能设计

无性能敏感改动。两项改动均在日志路径上做纯字符串/正则处理：脱敏为单次正则替换，转义由原有的 `%replace` 承担，未新增 IO、远程调用或锁竞争。本次未做压测，不引入新的性能结论。

## 6. API接口设计

无变更：HTTP 接口路径、入参、出参与出参结构均未调整。脱敏只作用于日志文本，审计 `userId` 只改变取值来源，两者均不改变对外契约。

## 7. 安全设计

### 防护边界

- **覆盖范围**：JSON 形态的敏感字段（`accessToken`、`access_token`、`token`、`password`、`secret`、`privateKey`、`private_key`，以及请求头形态 `x-gitee-token`、`x-gitee-password`、`x-gitcode-token`、`private-token`、`authorization`）、内嵌转义 JSON 的同名字段、URL 查询参数 `access_token` / `private_token` / `accessToken`；日志用序列化剔除 `accessToken`、`configJson`、`tableData`；日志文本中的 C0 控制字符与 `\u0085` / `\u2028` / `\u2029`。
- **生效位置**：`WebHookEventConsumer` 等事件日志出口统一走 `MessageMaskUtils.maskSensitiveFields` / `toSafeLogJson`；未接入这两个入口的日志出口不在覆盖范围（见残留风险）。
- **身份可信边界**：审计 `userId` 以验签令牌声明为可信来源，请求参数仅在声明缺失或验签失败时作为回退来源。

### 失败语义

- `toSafeLogJson`：序列化失败不抛异常，返回常量 `<unavailable>`，不影响调用方主流程。
- `maskSensitiveFields`：空/空白输入原样返回，不做额外处理。
- `capture()`：仅捕获 `RuntimeException`，验签异常时回退网关注入参数，审计写入不中断。
- 脱敏与转义均为无条件执行，无开关、无降级路径。

### 残留风险

- **回退路径仍可伪造身份**：验签失败或令牌不含 `userId` 声明时，审计 `userId` 回退调用方入参，该场景下伪造仍然成立；回退为可用性取舍，需依赖验签链路本身可用。
- **非 JSON 形态的凭证不覆盖**：`SENSITIVE_FIELDS_PATTERN` 只匹配 `"字段名":"值"` 结构与 URL 令牌，自定义文本格式、嵌套非字符串值等形态不在脱敏范围内（`value` 非字符串时按设计不误伤）。
- **只脱敏输出，不改数据**：脱敏发生在日志输出环节，敏感值在内存对象与业务链路中仍为原文，若有其他未走 `MessageMaskUtils` 的日志出口，则不在本次防护内。
- **转义为文本层防护**：控制字符转义解决的是日志行完整性问题，不改变日志承载的业务语义，也不覆盖日志系统之外的消费端。
