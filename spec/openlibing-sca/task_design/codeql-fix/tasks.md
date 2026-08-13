# openlibing-sca CodeQL 静态扫描安全问题修复 — 实现任务清单

> 状态标记基于 `codeql-fix` 分支当前代码（19 个 commit），均已实现。

## SSRF 防护

- [x] 新增 `SsrfsafeUrlUtil.validateUrl`：协议白名单（http/https）+ localhost/127.0.0.1/0.0.0.0 拒绝 + DNS 解析校验（site-local/loopback/link-local）+ 手写 IPv4 私网段判定（10.x / 172.16-31.x / 192.168.x / 169.254.x）
- [x] `HttpClientUtil.sendPost`：接入 `validateUrl`，捕获 `IllegalArgumentException` → warn 日志返回 null
- [x] `HttpClientUtil.get` / `getResponse`：接入 `validateUrl`
- [x] `HttpUtil.doGet`：拼接完整 URL 后接入 `validateUrl`，捕获异常返回空 body
- [x] `IntegrationApiServiceImpl`：`getRemoteBranch` 接入校验 + `ScaException(500)` 兜底
- [x] `IntegrationApiServiceImpl`：`checkoutBranch` 接入校验 + 返回 1 降级
- [x] `IntegrationApiServiceImpl`：`checkRepoSizeAndSendToMq` 接入校验
- [x] `IntegrationApiServiceImpl`：其余 URL 请求（含 PRScan 相关）接入校验
- [x] `OpenScanServiceImpl.showFileHash`：fileHash 非法字符净化（`[\\/:*?"<>|\x00-\x1F\x7F]` → `_`）+ `validateUrl`
- [x] `GitCodeUtil`：`getUbmcToken` / `getUbmcUserInfo` 对 `sendPost` null 返回 warn 日志 + 空 HashMap 兜底（防 NPE）

## 日志注入防御

- [x] 新增 `LogSanitizer.sanitizeForLog`：`\` → `\\`、`\r` → `\r` 字面、`\n` → `\n` 字面，null 返回 null
- [x] `DefaultExceptionHandler`：新增 `UNSAFE_LOG_CHARS` 正则 + `sanitizeForLog`（控制字符替换 `_`）
- [x] `DefaultExceptionHandler`：新增 `logHandledException(request, errorCode, errorMsg)` 参数化日志，携带 uri/method/clientIp/userAgent/referer
- [x] `DefaultExceptionHandler`：新增 `getClientIp`（X-Forwarded-For → X-Real-IP → RemoteAddr，逗号截断）
- [x] `DefaultExceptionHandler`：全部 `LOGGER.error(append.toString())` 替换为 `logHandledException(...)`
- [x] `DefaultExceptionHandler`：`request == null` 分支修复（避免无限递归 / NPE）
- [x] `DefaultExceptionHandler`：`systemException` 分支使用参数化日志
- [x] `IntegrationApiServiceImpl`：prUrl / repoUrl 日志经 `LogSanitizer` 净化
- [x] `OpenScanServiceImpl`：flag 日志经 `LogSanitizer` 净化

## 日志质量

- [x] 替换 25 处 `append.toString()` 字符串拼接为参数化日志
- [x] `OpenPersonScanServiceImpl.refreshVersionData`：补齐缺失的 `repoName` 参数
- [x] `OpenPersonScanServiceImpl.refreshPersonData`：`e.getMessage()` 改为参数化占位符

## 正则构造

- [x] `OpenScanDMServiceImpl.wildCard2RegEx`：改为逐字符单遍扫描（`*`→`.*`、`?`→`.?`、元字符显式转义）
- [x] `ShieldRoleServiceImpl.wildCard2RegEx`：改为逐字符单遍扫描，两处实现对齐

## JWT 解析

- [x] `JwtUtils.getAccessToken`：返回 map 增加 `sub` claim
- [x] `OpenScanDMServiceImpl.scanPathConfirmParseV2`：改用 `JwtUtils.getAccessToken(httpRequest)`，使 gitee / gitcode 前缀判定生效

## 接口语义（GET → POST）

- [x] `BinaryLicenseController`：`/export/notice`、`/export/license/check`
- [x] `LicenseController`：`/export/community`
- [x] `OpenPersonScanController`：`/refreshVersionData`、`/refreshPersonData`
- [x] `OpenScanController`：`/putExportXLS`、`/export/community/count`、`/versionSchedule`
- [x] `TblScancodeInfoController`：`/getScanCodeInfo`
- [x] `OpenScanDMController`：`/refresh/confirmNum`、`/refresh/repoid-community-repo`

## 工程配置

- [x] 新增 `.gitignore`：排除 `target/`、`.trae/`、CodeQL 修复脚本产物（findings.json 等）
- [x] `.pre-commit-config.yaml`：各 hook 增加 `exclude: '^target/'`

## 单元测试

- [x] `JwtUtilsTest`：`sub` claim 断言（map size 4 → 5）
- [x] `DefaultExceptionHandlerTest`：移除 `loggerAppend.toString()` mock，适配参数化日志
- [x] `OpenScanDMServiceImplTest`：`mockStatic(JwtUtils)` 注入 token map，验证 sub 判定

## 验证

- [x] Maven 编译通过（`cc0fe023` 修复编译错误与 pre-commit 失败）
- [x] pre-commit 检查通过
- [ ] 修复后 CodeQL 复扫：原 81 处告警清零确认
- [ ] 集成环境验证：gitee / gitcode 登录前缀判定、导出类接口 POST 调用正常
