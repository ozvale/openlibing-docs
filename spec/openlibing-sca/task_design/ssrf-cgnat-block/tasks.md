# 142 — 实现任务

## 进度: 2/2 complete

- [x] Task 1: `SsrfsafeUrlUtil` 增加 `BLOCKED_IPV4_CIDRS`（100.64.0.0/10、0.0.0.0/8、192.0.0.0/24、198.18.0.0/15）、`isBlockedIpv4Cidr`、`isIpv4Mapped`、`CidrBlock`，并接入 `resolveAndValidate` 统一拒绝分支（`3980eb33`）
- [x] Task 2: 单测覆盖受理侧与下载侧拒绝、边界与段外、域名解析、IPv4-mapped、既有拦截不回退（`3980eb33`）

## 交付记录

| commit     | 日期       | 标题                                                                     | 关联       |
| ---------- | ---------- | ------------------------------------------------------------------------ | ---------- |
| `3980eb33` | 2026-11-06 | fix(analysis): block CGNAT and special-purpose IPv4 ranges in SSRF guard | Fixes #142 |

- 分支：`ms_scan`（`openlibing-sca`）
- 变更规模：4 文件，+266/-1（`SsrfsafeUrlUtil.java` +68、`SsrfsafeUrlUtilTest.java` +161、`ProjectNoticeScanServiceImplTest.java` +22、`ProjectNoticeScanExecutorTest.java` +16）
- 验证方式（代码内证据）：
  - `SsrfsafeUrlUtilTest`（新建 10 个用例）：`validateUrl_rejectsAliyunMetadataInCgnatRange`、`validateUrl_rejectsCgnatRangeBoundaries`、`validateUrl_allowsAddressesJustOutsideCgnatRange`、`validateUrl_rejectsHostnameResolvingIntoCgnatRange`、`validateUrl_rejectsIpv4MappedCgnatAddress`、三段特殊用途网段用例、`validateUrl_keepsRejectingLegacyBlockedAddresses`、`validateUrl_allowsPublicLiteralAddresses`
  - `ProjectNoticeScanServiceImplTest#supplementNotice_ssrfCgnatUrl_rejected`：受理阶段拒绝，断言未 `markSupplementRescan`、未发布补充事件
  - `ProjectNoticeScanExecutorTest#doDownload_rejectsCgnatCloudMetadataAddress`：下载 sink 拒绝
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）
- 关联：本 commit 属 #109 三 commit 中的网段子项，总览见 `ssrf-redirect-hardening`
