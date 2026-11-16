# 96 obs-signed-url-log-redaction — 实现任务

## 进度: 2/2 complete

- [x] Task 1: 消除签名 URL 日志汇聚点——`downloadObsTextByUrl` 改为按 objectKey 读取并删除 `LOGGER.error(..., signedUrl, e)`（`bc8e528a`，背景提交）
- [x] Task 2: `extractObjectKey` 异常消息脱敏（新增 `redactSignedUrl`，覆盖无 path 与 URI 解析失败两个分支）+ 单测（`c6720e8c`）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                                               | 关联                                                             |
| ---------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `c6720e8c` | fix(notice-scan): redact signed url query in extractObjectKey errors               | `Refs #96`                                                       |
| `bc8e528a` | fix(notice-scan): read cached OBS content by objectKey, not expired URL            | 背景：移除原始 `url={}` ERROR 日志；提交 message 未写 `Refs #96` |
| `eb7cb58d` | fix(notice-scan): pin connections to SSRF-approved addresses to stop DNS rebinding | 同链路重写背景（`Refs #143`），未恢复签名 URL 日志               |

关键 diff：

- `ProjectNoticeScanExecutor`：
  - `downloadObsTextByUrl(signedUrl)` → `downloadObsObjectText(extractObjectKey(signedUrl))`，原 `LOGGER.error("download obs text by url error, url={}", signedUrl, e)` 删除；
  - `extractObjectKey` 两个 `ScaException` 分支改为 `redactSignedUrl(signedUrl)`；
  - 新增 `private static String redactSignedUrl(String)`：`null` → `<null>`，含 `?` → 保留前缀 + `?<redacted>`。
- `ProjectNoticeScanExecutorTest`：新增 1 个用例（+26 行），分别用 `https://b.obs.r.myhuaweicloud.com:443?AccessKeyId=AK&Signature=sig`（无 path 分支）与 `https://host with space?AccessKeyId=AK&Signature=sig`（URI 非法分支）。

验证方式：

- 单测：本地 UT 日志（`5_ut.log`，2026-11-14）显示 `ProjectNoticeScanExecutorTest` 26 个用例全部通过；本次回溯未重新执行 `mvn test`。
- 静态核实：执行器内无 `url={}` 形式的签名 URL 日志；`downloadObsObjectText` 的失败日志只输出 `"download obs object text error"` / `"read obs object content error"`；`error_msg` 写入点为 `truncate(e.getMessage(), 1024)`，即脱敏后消息。
- 覆盖率：未验证。

## 备注：commit 映射

BRIEF 给出的 `c6720e8c` 是 `Refs #96` 的唯一直接提交；但该提交只修 `extractObjectKey` 的残余面（异常消息），issue 正文所指的第 801 行 `LOGGER.error(..., signedUrl, e)` 实际在 `bc8e528a`（"按 objectKey 读取"重构）中被整段删除。master 侧存在同主题、同作者时间、同文件 diff 的 `e1c403d9`（两提交分支基线不同，`ProjectNoticeScanExecutor` 的增删行逐行一致），ms_scan 上生效的是 `bc8e528a`。
