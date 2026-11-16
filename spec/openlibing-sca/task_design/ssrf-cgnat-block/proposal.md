# 142 — NOTICE 扫描 SSRF 校验补齐 CGNAT 与特殊用途网段

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/142
（【安全】【Argus】NOTICE 扫描下载 SSRF 校验未覆盖 CGNAT 段 100.64.0.0/10，阿里云元数据 100.100.100.200 可被服务端访问，CWE-918，中危，当前状态 closed）

漏洞来源：Argus 扫描批次 `openlibingsca-20261103130601-005`（置信度已验证、可实际利用）。

问题成因：`SsrfsafeUrlUtil.validateUrl` 只依赖 JDK `InetAddress` 的四类判定（`isLoopbackAddress` / `isAnyLocalAddress` / `isSiteLocalAddress` / `isLinkLocalAddress`），不覆盖 RFC 6598 CGNAT 共享地址段 `100.64.0.0/10`（100.64.0.0–100.127.255.255）。阿里云元数据服务 `100.100.100.200` 落在该段内，四类判定均不命中，校验必然放行。

受影响面（同一防护函数同时服务两侧）：

- 受理侧：`POST /project/notice/scan/supplement` 的 `SupplementItem.downloadUrl`，`ProjectNoticeScanServiceImpl#supplementNotice` 逐条调用 `SsrfsafeUrlUtil.validateUrl`；
- 下载侧：`ProjectNoticeScanExecutor#doDownload`（HTTP）与 `doGitDownload`（git clone）经 `resolveApprovedAddresses` → `SsrfsafeUrlUtil.resolveAndValidate`。

重定向路径此前已收敛为 `Redirect.NEVER` + 逐跳校验（`efc6a17b`），本缺口与重定向无关，属网段覆盖遗漏：若部署在阿里云或该段可路由网络中，服务端可被驱动访问 100.100.100.200 获取实例角色/临时凭证。

## 功能描述

**做什么**：

1. 在 `SsrfsafeUrlUtil` 增加逐字节 IPv4 CIDR 黑名单 `BLOCKED_IPV4_CIDRS`：`100.64.0.0/10`（P0）、`0.0.0.0/8`、`192.0.0.0/24`、`198.18.0.0/15`（P1 三个段）；
2. 新增 `isBlockedIpv4Cidr(InetAddress)`，与既有四类判定并列进入 `resolveAndValidate` 的统一拒绝分支（单点生效，受理与下载两侧同时覆盖）；
3. IPv4-mapped IPv6（`::ffff:0:0/96`）先还原为 4 字节再做网段匹配，防止以 IPv6 书写绕过；
4. 单测覆盖元数据地址、CGNAT 边界、段外不误伤、域名解析到 CGNAT、IPv4-mapped、其余三段、既有拦截不回退。

**不做什么**：

- 不做 IPv6 特殊用途段（如唯一本地地址 `fc00::/7`）的逐段收敛，仅依赖 JDK 既有判定（本轮未覆盖）；
- 不补齐全部 IPv4 特殊用途段（`192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`、`240.0.0.0/4` 等未加入，本轮未覆盖）；
- 不改变 DNS 校验与建连的绑定关系（DNS rebinding 修复见 `ssrf-dns-rebinding-pinning`）；
- 不新增配置项开关，黑名单硬编码在工具类（安全默认不可关闭）。

## 验收标准

- [x] `http://100.100.100.200/latest/meta-data/` 在 `validateUrl` 层被拒绝（`SsrfsafeUrlUtilTest#validateUrl_rejectsAliyunMetadataInCgnatRange`）
- [x] `100.64.0.0`、`100.127.255.255` 两个边界地址被拒绝（`validateUrl_rejectsCgnatRangeBoundaries`）；段外相邻地址 `100.63.255.255`、`100.128.0.0` 不误伤（`validateUrl_allowsAddressesJustOutsideCgnatRange`）
- [x] supplement 受理侧拒绝该地址且不写库、不触发异步补充（`ProjectNoticeScanServiceImplTest#supplementNotice_ssrfCgnatUrl_rejected`，断言未调用 `markSupplementRescan` 与未发布异步事件）
- [x] `doDownload` 侧拒绝该地址（`ProjectNoticeScanExecutorTest#doDownload_rejectsCgnatCloudMetadataAddress`，抛 `IllegalArgumentException` 且信息为 `Internal network access not allowed`，发生在请求发出之前）
- [x] 域名解析到 CGNAT 段被拒绝（`validateUrl_rejectsHostnameResolvingIntoCgnatRange`，mock `InetAddress.getAllByName` 结果）
- [x] IPv4-mapped IPv6 书写形式被拒绝（`validateUrl_rejectsIpv4MappedCgnatAddress`）
- [x] `169.254.169.254`、`10.x`、`172.16.x`、`192.168.x`、`127.0.0.1`、`0.0.0.0`、`localhost`、`ftp://` 既有拦截不回退（`validateUrl_keepsRejectingLegacyBlockedAddresses`）
- [x] 新增三段各有一条拒绝 + 段外不误伤用例（`validateUrl_rejectsThisNetworkRange`、`validateUrl_rejectsIetfProtocolAssignmentRange`、`validateUrl_rejectsBenchmarkRange`）
- [x] 公网字面 IP 下载地址回归通过（`validateUrl_allowsPublicLiteralAddresses`）
- [ ] 公网合法软件包真实下载回归：仅有字面 IP 的 URL 校验用例，未验证真实公网下载链路（未验证）
- [ ] 单测运行结果：本轮为回溯补写，未执行 `mvn test`（未验证）
- [ ] P1「覆盖其余特殊用途段」仅覆盖 3 段，其余段未覆盖

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `SsrfsafeUrlUtil`（唯一判定点）
- 被动影响面：所有调用 `SsrfsafeUrlUtil.validateUrl` / `resolveAndValidate` 的出网路径（公告扫描受理与下载、git clone、`HttpClientUtil`、`HttpUtil`、`BasePackageUrlResolver`、`IntegrationApiServiceImpl`、`OpenScanServiceImpl` 等），行为变化为「原来放行、现被拒绝」的仅限上述 4 个网段
- 接口 / 契约：无变化；被拒绝时受理侧返回 `60000 补充失败 / downloadUrl被SSRF防护拒绝`
- 配置 / schema：无变化
