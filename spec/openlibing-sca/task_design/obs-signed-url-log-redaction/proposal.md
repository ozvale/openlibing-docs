# 96 obs-signed-url-log-redaction — OBS 签名 URL 不再进入日志与异常消息

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/96
（【安全】【Argus】OBS 临时签名 URL 在下载失败时完整写入错误日志，CWE-532 凭据/能力泄露）

Argus 报告 `argus-openlibingsca-20260928173548-028`（中危，CWE-532）指出：项目公告扫描回读存量 OBS 对象（`Readme.opensource` / 合并 NOTICE）失败时，`ProjectNoticeScanExecutor#downloadObsTextByUrl` 的 `catch(Exception)` 分支执行 `LOGGER.error("download obs text by url error, url={}", signedUrl, e)`，把含 `AccessKeyId` / `Signature` / `Expires` 的完整签名 URL 写入 ERROR 日志。该 URL 由 `SignUtils#getUrl` 通过 `ObsClient.createTemporarySignature` 生成，有效期 2 周，等同对象下载能力凭据；能读日志的内部人员或攻击者可在有效期内直接下载对象，绕过平台下载鉴权面。

同期还有一个残留面：`extractObjectKey` 把完整签名 URL 拼进 `ScaException` 消息，而 `ScaException` 自 `bc8e528a` 起通过 `super(errorMsg)` 透传 message，上层 `catch` 的 `LOGGER.error` 与数据库 `error_msg` 字段会再次带出签名 URL。

## 功能描述

**做什么**：

1. （背景改动，该 issue 的直接攻击面）`downloadObsTextByUrl` 不再 GET 签名 URL，而是 `downloadObsObjectText(extractObjectKey(signedUrl))`，整段 `LOGGER.error("download obs text by url error, url={}", signedUrl, e)` 被删除；下载失败日志只剩 `"download obs object text error"` / `"read obs object content error"`，不含 URL（`bc8e528a`）。
2. 新增 `ProjectNoticeScanExecutor#redactSignedUrl`：保留 `?` 之前的 URL 部分，追加 `?<redacted>`；`null` 返回 `<null>`。
3. `extractObjectKey` 的两个异常分支统一改用脱敏消息：
   - `"cannot extract object key from url: " + redactSignedUrl(signedUrl)`
   - `"invalid obs signed url: " + redactSignedUrl(signedUrl)`
4. 补单测 `extractObjectKey_invalidUrl_exceptionMessageRedactsSignatureQuery`：分别覆盖无 path 分支与 URI 解析失败分支，断言消息不含 `AccessKeyId` / `Signature=sig` 且含 `?<redacted>`。

**不做什么**：

- 不改 `logback-spring.xml` 的 `LOG_PATTERN`（未增加 `AccessKeyId`/`Signature` 参数级脱敏）；
- 不增强 `LogSanitizer`（该工具只转义控制字符，本就无法剥离 URL 凭据；执行器中当前也未使用）；
- 不清理历史日志、日志平台/SIEM 中的存量凭据，也不做数据库历史 `error_msg` 数据修复；
- 不改签名 URL 有效期（`SignUtils` 仍为 2 周）；
- 不涉及 `eb7cb58d`（同链路 SSRF DNS pinning 重写，Refs #143）的日志行为，该提交未重新引入签名 URL 日志。

## 验收标准

- [x] 下载失败不再把完整签名 URL 写入 ERROR 日志：`downloadObsTextByUrl` 改为按 objectKey 读取，原 `url={}` 日志行已删除（`bc8e528a`）
- [x] 异常消息不含 `AccessKeyId` / `Signature` / `Expires`：`extractObjectKey` 两个分支均走 `redactSignedUrl`（`c6720e8c`）
- [x] 单测覆盖两个异常分支的脱敏断言（`ProjectNoticeScanExecutorTest#extractObjectKey_invalidUrl_exceptionMessageRedactsSignatureQuery`，本提交 +26 行）
- [x] `ScaException` 透传脱敏后的 message，上层日志与 DB `error_msg` 落的是 `?<redacted>` 版本（`ProjectNoticeScanAsyncProcessor` 使用 `truncate(e.getMessage(), 1024)` 写 `error_msg`）
- [ ] 日志框架层（`logback-spring.xml`）对签名参数统一脱敏（本轮未覆盖）
- [ ] 历史日志/日志平台存量凭据清理与轮转（本轮未覆盖，不在代码仓范围）

## 影响范围

- 仓库：`openlibing-sca`（`dm` 模块 `ProjectNoticeScanExecutor`）。
- 接口：无变化。
- 数据：`error_msg` 中签名 URL 变为 `...?<redacted>`；历史记录未回修。
- 日志：`downloadObsTextByUrl` 失败日志不再含 URL，排障需依靠 objectKey 与异常堆栈。
- 配置 / schema / 部署：无。
