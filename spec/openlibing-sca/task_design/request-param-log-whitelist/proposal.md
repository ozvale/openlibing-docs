# request-param-log-whitelist — 请求参数写日志改为白名单（#161）

## 需求背景

安全 Issue：[openlibing/openlibing-sca#161](https://gitcode.com/openlibing/openlibing-sca/issues/161)
（请求参数落日志未脱敏，P2）。

`LoggerAppend.create(request, type)`（`common/log/LoggerAppend.java:31-41`，修复前行号）无条件遍历
`request.getParameterMap()`，把**全部**请求参数的键值写入服务端 ERROR 日志：

- `userId`、`userName`、`token`、`password`、`code`、`repoUrl` 等敏感参数明文落盘；
- `repoUrl` 可能携带 `https://user:pass@host/repo.git` 形式的账号口令；
- 该日志由 `DefaultExceptionHandler` 的 28 个 `@ExceptionHandler` 分支统一调用，异常路径覆盖面大。

## 功能描述

**做什么**：

1. 引入参数白名单 `LOGGABLE_PARAMETERS`（18 项）：`scanid`、`repoid`、`projectid`、`communityid`、
   `issueid`、`deptid`、`producttype`、`valuelabel`、`platform`、`community`、`version`、`type`、
   `typelevel`、`pageno`、`pagesize`、`refreshtime`、`refreshcommunity`、`filehash`；
2. `create` 遍历参数时先经 `isLoggableParameter` 过滤，非白名单参数直接跳过（不落盘、不占位）；
3. 白名单匹配大小写不敏感（`name.toLowerCase(Locale.ROOT)`），兼容 `scanId` / `scanid` 两种写法；
4. 保留原有其他行为：`prefix:error`、`requestURI` 输出，白名单参数的多值 `[a, b]` 与空值 `null` 输出不变；
5. 新增单测覆盖白名单命中、敏感参数过滤、多值、空值、基础前缀/URI。

**不做什么**：

- 不按参数值做正则脱敏（如自动识别 token 形态）；白名单外参数一律不落盘。
- 不改动 `LoggerAppend` 的调用方（`DefaultExceptionHandler` 28 处），不改日志格式与分隔符。
- 不处理请求体（JSON body）与 URI query：`getParameterMap` 不包含 body；`getRequestURI` 本身不含 query，
  无需额外处理。

## 验收标准

- [x] `token`、`userId`、`userName`、`password`、`code`、`repoUrl` 等不在白名单的参数不写入日志：
      `create_skipsSensitiveParameters` 断言日志不含这些键名与值（含 `example.com`、`p@ssw0rd`、`auth-code`）
- [x] 白名单内参数正常落盘，大小写兼容：`create_appendsWhitelistedParameters`（`scanId`、`pageNo`）
- [x] 多值参数按 `[a, b]` 输出、空值输出 `null`：`create_appendsMultipleValuesOfWhitelistedParameter`、
      `create_appendsNullForEmptyValues`
- [x] 前缀与请求 URI 仍正常输出：`create_appendsUriAndType`
- [x] 既有异常日志链路不受影响：`DefaultExceptionHandler` 仍调用 `LoggerAppend.create(request, ERROR)`，
      仅参数部分被过滤；`DefaultExceptionHandlerTest` 通过 `mockStatic(LoggerAppend.class)` 不依赖具体参数内容

## 影响范围

- 业务仓：`openlibing-sca`（`common/log/LoggerAppend.java` + 新增单测）
- 接口：无变化
- 配置、数据库 schema：无变化
- 日志内容：ERROR 日志中的请求参数范围收窄（仅白名单），日志量下降
