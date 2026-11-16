# 109 — NOTICE 扫描下载链路 SSRF 加固（DNS pin / 特殊网段 / git clone 重定向）

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/109
（【安全】【ICSL安全缺陷】SCA 软件包下载与 git clone 路径 SSRF，CWE-918，当前状态 closed）

受影响链路：`ProjectNoticeScanExecutor#downloadPackage` → `doDownload`（HTTP 下载）/ `doGitDownload`（git clone）。
`downloadUrl` 来自 NOTICE 扫描内容、`/project/notice/scan/supplement` 补录地址与 SBOM 解析结果，属外部可控输入。

Issue 列出的三类缺口及核实结论：

1. `isUrlSafe` 校验过弱：仅 scheme 前缀（`pkg:` / `http://` / `https://`）+ 字符黑名单，无 host 白名单，也无解析后私网 IP 校验；黑名单不含 `@`，可借 userinfo 伪装（如 `http://a@169.254.169.254/`）。
2. `followRedirects(ALWAYS)`：初始 URL 通过校验后，302 目标不再过校验。HTTP 下载侧此点已在前序 commit `efc6a17b`（关联 #105）改为「关闭自动重定向 + 逐跳手动校验」；本 issue 在本批次收口的重定向缺口是 git clone 子进程。
3. 校验与建连分离：`SsrfsafeUrlUtil.validateUrl` 的 DNS 解析结果被丢弃，连接层独立二次解析，形成 TOCTOU / DNS rebinding 窗口；且 JDK 四类地址判定不覆盖 CGNAT 等特殊用途网段（另见 `ssrf-cgnat-block`）。

风险与影响：服务端可被驱动访问云 metadata（169.254.169.254、100.100.100.200）获取实例临时凭证，或探测内网 Nexus/Artifactory 等组件仓库；响应内容不回显降低了信息直接外泄面，但请求本身已构成内网探测与凭证窃取通道，定级中危。

## 功能描述

**做什么**（本批次三个 commit）：

1. `eb7cb58d`：`SsrfsafeUrlUtil.resolveAndValidate` 返回核准地址集合；`doDownload` 改用共享 OkHttp 客户端 + 每请求 pinned `Dns`；`doGitDownload` 通过 `GIT_CONFIG_*` 注入 `http.curloptResolve` 钉住 host:port。
2. `3980eb33`：SSRF 黑名单补齐 CGNAT `100.64.0.0/10` 等特殊用途网段（子项细节见 `ssrf-cgnat-block`）。
3. `b18855ba`：git clone 子进程注入 `http.followRedirects=false`，重定向 fail-closed；同时按 curl 文档将 IPv6 核准地址写成方括号形式。

**不做什么**：

- 不引入 host 白名单（issue 建议 1 的备选方案之一，实际采用「解析后私网/特殊网段拒绝」）。
- 不把全部出网调用收敛到统一客户端工厂：`HttpClientUtil` / `HttpUtil` / `BasePackageUrlResolver` 等仍只调用 `validateUrl`，校验与连接依旧分离（issue 建议 4 未完全覆盖）。
- 不做连接后对端 IP 复验（issue 建议 2 的 P1 部分，见 `ssrf-dns-rebinding-pinning` 的遗留说明）。
- 不新增元数据端点连接告警、DNS rebinding 探测与监控接入。

## 验收标准

- [x] 解析到 loopback / 私网 / link-local / CGNAT 等特殊网段的目标被拒绝，且拒绝发生在建连之前（`SsrfsafeUrlUtilTest`、`ProjectNoticeScanExecutorTest#doDownload_rejectsCgnatCloudMetadataAddress`、`ProjectNoticeScanServiceImplTest#supplementNotice_ssrfCgnatUrl_rejected`）
- [x] HTTP 下载建连只发生在核准 IP 上（`doDownload_pinsConnectionToApprovedAddresses`）
- [x] 重定向每一跳重新解析、复核并重新 pin（`doDownload_redirectHopAlsoUsesPinnedResolution`；HTTP 侧关闭自动重定向沿用 `efc6a17b`）
- [x] git clone 建连钉到核准地址（`buildGitResolveEnv_pinsHttpsDefaultPortWithLowercasedHost`、`buildGitResolveEnv_httpDefaultPortAndExplicitPort`、`buildGitResolveEnv_multipleApprovedAddressesCommaJoined`、`buildGitResolveEnv_wrapsIpv6AddressesInBrackets`）
- [x] git clone 重定向 fail-closed（`buildGitResolveEnv` 断言 `http.followRedirects=false`，`GIT_CONFIG_COUNT=2`）
- [x] userinfo 伪装不再生效：校验基于 `URL#getHost()`，`http://a@<内网IP>/` 取到的是 `<内网IP>`，会被拒绝（未新增 `@` 字符黑名单）
- [x] 非重定向公网 clone 不受影响、重定向 clone 被拒绝：commit `b18855ba` 记录按批次 1 用例集 A8 本地验证；自动化仅覆盖环境变量构造，未覆盖真实 clone
- [ ] host 白名单（issue 建议 1 的备选方案，本轮未采用）
- [ ] 统一 SSRF 防护组件覆盖所有出网路径（issue 建议 4，本轮未覆盖：其他调用方仍仅 `validateUrl`）
- [ ] 连接后复验实际对端 IP（issue 建议 P1，本轮未覆盖）
- [ ] 重新执行单测：本轮为回溯补写，未运行 `mvn test`（未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`dm` 模块（`ProjectNoticeScanExecutor`）、`analysis` 模块（`SsrfsafeUrlUtil`）
- 外部接口 / 契约：无变化（`/project/notice/scan/supplement` 请求响应结构不变，仅拒绝行为增强）
- 配置：无新增配置项；下载超时仍由既有常量控制（连接 30s、读 10min、最大重定向 5 跳）
- 数据 schema：无变化
- 运行环境依赖：git ≥ 2.37（`http.curloptResolve`）与 curl ≥ 7.59；openEuler 24.03 自带 git 2.43 / curl 8.x 满足
