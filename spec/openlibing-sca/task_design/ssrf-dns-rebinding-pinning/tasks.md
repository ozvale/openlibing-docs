# 143 — 实现任务

## 进度: 2/2 complete

- [x] Task 1: `SsrfsafeUrlUtil#resolveAndValidate` 返回核准地址集合，`validateUrl` 委托；`doDownload` 改 OkHttp pinned DNS 并逐跳重新核准/重新 pin；`doGitDownload` 通过 `GIT_CONFIG_*` 注入 `http.curloptResolve`（`eb7cb58d`）
- [x] Task 2: 单测补充 —— `SsrfsafeUrlUtilTest#resolveAndValidate_*` 三个用例、`ProjectNoticeScanExecutorTest` 的 pinned 建连 / 重定向 re-pin / `buildPinnedDns` / `buildGitResolveEnv` 用例（`eb7cb58d`）

## 交付记录

| commit     | 日期       | 标题                                                                               | 关联      |
| ---------- | ---------- | ---------------------------------------------------------------------------------- | --------- |
| `eb7cb58d` | 2026-11-06 | fix(notice-scan): pin connections to SSRF-approved addresses to stop DNS rebinding | Refs #143 |

- 分支：`ms_scan`（`openlibing-sca`）
- 变更规模：4 文件，+600/-266（`ProjectNoticeScanExecutor.java` 335 行改动为主，`ProjectNoticeScanExecutorTest.java` 新增 465 行、含用例重写）
- 验证方式（代码内证据）：
  - `ProjectNoticeScanExecutorTest#doDownload_pinsConnectionToApprovedAddresses`：核准结果与系统解析不同，仍只连核准地址（本地回环服务 + `*.invalid` 主机名，pin 不生效则无法建连）
  - `#doDownload_redirectHopAlsoUsesPinnedResolution`、`#buildPinnedDns_returnsApprovedForOriginHostAndSystemDnsForOthers`
  - `#buildGitResolveEnv_pinsHttpsDefaultPortWithLowercasedHost`、`#buildGitResolveEnv_httpDefaultPortAndExplicitPort`、`#buildGitResolveEnv_multipleApprovedAddressesCommaJoined`
  - `SsrfsafeUrlUtilTest#resolveAndValidate_returnsApprovedLiteralAddress`、`#resolveAndValidate_returnsAllResolvedAddressesInOrder`、`#resolveAndValidate_rejectsReboundInternalAddress`
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）
- 后续收口：git clone 重定向由 `b18855ba`（2026-11-11）补 `http.followRedirects=false`，见 `ssrf-redirect-hardening`
