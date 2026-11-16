# 96 obs-signed-url-log-redaction — 技术设计

## 方案概述

分两步消除"签名 URL 进入日志"的通道：

1. **消灭日志汇聚点**：`bc8e528a` 把"按签名 URL 直接 GET"改为"从 URL 提取 objectKey 后用 ObsClient 读桶对象"，同时删除打印 `signedUrl` 的 ERROR 日志——该改动本身服务于"签名 URL 2 周过期导致缓存命中读失败"，但恰好移除了本 issue 的原始泄露点。
2. **脱敏异常消息**：`c6720e8c` 为 `extractObjectKey` 增加 `redactSignedUrl`，异常消息只保留 `?` 之前的部分 + `?<redacted>`，从而阻断"`ScaException.getMessage()` → 上层 `LOGGER.error` / DB `error_msg`"这条二次泄露路径。

## 架构决策

| 决策                                    | 证据 / 理由                                                                                                                                                                                                            |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 不再用签名 URL 发起下载              | 签名 URL 必然携带 `AccessKeyId`/`Signature`/`Expires`，任何围绕它的日志/异常都难以保证不泄露；改为 `downloadObsObjectText(extractObjectKey(signedUrl))` 后，链路只处理 objectKey（非凭据），顺带解决签名过期导致的 403 |
| D2 脱敏粒度选"保留 path、丢弃 query"    | URL 的 path（objectKey）是排障必需信息，query 是纯凭据；`?<redacted>` 标记明确提示"此处原本有 query"，便于日志检索与告警规则匹配                                                                                       |
| D3 在异常消息处脱敏，而不是在 logger 处 | 同一异常消息还会写入 `tbl_*` 的 `error_msg` 字段（`truncate(e.getMessage(), 1024)`），只在日志侧脱敏会漏掉数据库；在消息构造点脱敏一次即可覆盖两条出口                                                                 |
| D4 不改全局日志框架                     | `logback-spring.xml` 的 `LOG_PATTERN` 目前只做 `\r\n\t\f` 控制字符替换；为凭据做通用参数级脱敏需要引入日志遮蔽组件，影响面大，本轮不做（残余）                                                                         |
| D5 `null` 用 `<null>` 占位              | 避免 `"..." + null` 拼出字面量 `null` 造成的歧义，同时保证消息非空、便于测试断言                                                                                                                                       |
| D6 与 `eb7cb58d` 解耦                   | 该提交重写下载链路（OkHttp 固定 DNS + git `curloptResolve`，Refs #143），未恢复任何签名 URL 日志；两处改动互不冲突，均在 `ms_scan` 中                                                                                  |

## 关键实现（当前代码）

```
static String extractObjectKey(String signedUrl) {
  if (signedUrl == null || signedUrl.isBlank()) {
    throw new ScaException(500, "obs signed url is blank", "");
  }
  try {
    URI uri = URI.create(signedUrl);
    String path = uri.getPath();
    if (path == null || path.length() < 2) {
      throw new ScaException(500, "cannot extract object key from url: " + redactSignedUrl(signedUrl), "");
    }
    return path.substring(1);
  } catch (IllegalArgumentException e) {
    throw new ScaException(500, "invalid obs signed url: " + redactSignedUrl(signedUrl), "");
  }
}

private static String redactSignedUrl(String signedUrl) {
  if (signedUrl == null) return "<null>";
  int queryIdx = signedUrl.indexOf('?');
  return queryIdx >= 0 ? signedUrl.substring(0, queryIdx) + "?<redacted>" : signedUrl;
}
```

```
public String downloadObsTextByUrl(String signedUrl) {
  return downloadObsObjectText(extractObjectKey(signedUrl));   // 不再 LOGGER.error(..., signedUrl, e)
}
```

## 涉及文件

| 文件                                                                                    | 操作         | 说明                                                                                                                                                            |
| --------------------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutor.java`               | 修改         | `c6720e8c`：`extractObjectKey` 两个分支改用 `redactSignedUrl`，新增私有方法（+20 行）。背景：`bc8e528a` 已删除 `url={}` ERROR 日志并把下载改为按 objectKey 读取 |
| `src/test/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutorTest.java`           | 修改         | `c6720e8c`：新增 `extractObjectKey_invalidUrl_exceptionMessageRedactsSignatureQuery`（+26 行），覆盖两个分支                                                    |
| `src/main/java/com/openlibing/sca/common/exception/ScaException.java`                   | 修改（背景） | `bc8e528a`：构造函数 `super(errorMsg)`，使 message 透传（+1 行），也是本轮脱敏必须落在消息构造点的原因                                                          |
| `src/main/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanAsyncProcessor.java` | 修改（背景） | `bc8e528a`：缓存命中下载失败回退为全量重生成；`error_msg` 取 `truncate(e.getMessage(), 1024)`                                                                   |

## 风险 & 缓解

| 风险                                                                 | 缓解                                                                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 其他位置仍可能打印签名 URL（如 `readmeOssUrl` 落库后被其他日志输出） | 当前 `ProjectNoticeScanExecutor` 无 `url={}` 形式的签名 URL 日志；全仓 grep `LOG...OssUrl` 无命中，但日志框架层未做通用遮蔽（未验证所有路径） |
| 排障信息减少（看不到 query）                                         | 保留 host + path（objectKey），足以定位对象；`?<redacted>` 保留"曾有 query"的信息                                                             |
| DB 中历史 `error_msg` 仍含签名 URL                                   | 未做数据修复；签名 URL 最长 2 周有效，建议按需清理/等自然过期（未执行）                                                                       |
| 历史日志文件/日志平台仍留存凭据                                      | 不在代码仓范围，需运维侧按日志保留策略处理（未执行）                                                                                          |
| 后续有人改回"按 URL 下载"                                            | `downloadObsTextByUrl` 已改为 objectKey 读取并有注释说明签名 2 周失效；评审时需保持该约束                                                     |

## 跨仓影响

无。spec 文档归档 `openlibing-docs` 仓；日志平台/SIEM 侧的存量数据清理属运维动作，不在本仓范围。
