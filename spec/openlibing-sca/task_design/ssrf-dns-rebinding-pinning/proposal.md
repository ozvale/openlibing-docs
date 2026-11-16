# 143 — SSRF 校验与连接解耦（DNS rebinding / TOCTOU）修复

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/143
（【安全】【Argus】SsrfsafeUrlUtil DNS 校验与连接分离导致 TOCTOU/DNS rebinding 绕过 SSRF 防护，CWE-918，中危，当前状态 closed）

漏洞来源：Argus 扫描批次 `openlibingsca-20261103130601-006`（置信度已验证）。

成因：`SsrfsafeUrlUtil.validateUrl` 用 `InetAddress.getAllByName(host)` 解析地址、做完四类判定后即丢弃结果；实际连接由 `java.net.http.HttpClient.send`（`doDownload`）与 git clone 子进程对 host 独立二次解析。校验与使用之间存在时间窗口：校验时解析为公网 IP、连接时被 rebinding 到内网/metadata 地址即可绕过。

风险放大点：

- `downloadUrl` 外部可控（SBOM 上传的 `downloadLocation`、`/project/notice/scan/supplement` 补录），经 `ProjectNoticeScanAsyncProcessor` 进入 `downloadPackage`；
- HTTP 路径受 JVM 默认 DNS 正缓存削弱（毫秒级窗口内通常命中同一解析结果），但 `doGitDownload` 的 git 子进程独立解析、不经 JVM 缓存，该支路风险更实；
- 重定向路径此前已收敛（`Redirect.NEVER` + 逐跳校验），本条与重定向无关，属校验时序缺陷；与本批次 CGNAT 网段覆盖缺口（`ssrf-cgnat-block`）根因不同、修复互不覆盖。

## 功能描述

**做什么**：

1. `SsrfsafeUrlUtil` 新增 `resolveAndValidate(String)`，返回通过全部检查的解析地址集合；`validateUrl` 委托它，保持既有调用方兼容；
2. `doDownload` 由 `java.net.http.HttpClient` 切换为共享 OkHttp 基础客户端：关闭自动重定向，每次请求派生 pinned `Dns`，只对本次 URL host 返回核准集合；重定向逐跳重新解析、重新核准、重新 pin；
3. `doGitDownload` 把 host:port 通过 `GIT_CONFIG_*` 注入 libcurl `CURLOPT_RESOLVE`（`http.curloptResolve`），使 git 子进程只连核准 IP；后续 `b18855ba` 追加 `http.followRedirects=false`（见 `ssrf-redirect-hardening`）；
4. 新增 `resolveApprovedAddresses`（包私有，便于单测模拟 rebinding）与 `buildPinnedDns` 两个可测点；
5. 单测以 `*.invalid` 主机名 + 本地回环服务验证「只有 pin 生效才会连到本地」。

**不做什么**：

- 不做连接后对端 IP 复验（issue 修复建议 P1：连接后校验实际对端与核准集合一致，本轮未覆盖）；
- 不关闭 `HttpClientUtil` / `HttpUtil` 的自动重定向，也未把其调用方收敛到统一客户端工厂（P1/P2，本轮未覆盖；这些调用方 URL 多为配置项，非本 issue 主入口）；
- 不做元数据端点连接告警（P2 未覆盖）；
- 不改变 TLS 证书校验与 SNI 行为（仍按 URL host 校验）。

## 验收标准

- [x] 交替应答 DNS 的恶意域名场景：`downloadUrl` 通过 `resolveAndValidate` 后，连接层只按核准集合建连（`ProjectNoticeScanExecutorTest#doDownload_pinsConnectionToApprovedAddresses`：模拟核准结果与系统解析不同，仍连到核准地址）
- [x] 重定向每一跳同样重新核准并 pin（`doDownload_redirectHopAlsoUsesPinnedResolution`）
- [x] 代理等非 origin host 回退系统解析，pin 不被误用（`buildPinnedDns_returnsApprovedForOriginHostAndSystemDnsForOthers`）
- [x] git clone 按核准 IP 建连（`buildGitResolveEnv_pinsHttpsDefaultPortWithLowercasedHost`、`buildGitResolveEnv_httpDefaultPortAndExplicitPort`、`buildGitResolveEnv_multipleApprovedAddressesCommaJoined`）
- [x] 核准集合以单次解析结果为准且保持原顺序（`SsrfsafeUrlUtilTest#resolveAndValidate_returnsApprovedLiteralAddress`、`resolveAndValidate_returnsAllResolvedAddressesInOrder`）
- [x] rebinding 到内网/metadata 的目标在核准阶段直接拒绝（`resolveAndValidate_rejectsReboundInternalAddress`）
- [x] 正常公网下载与合法重定向链回归：`doDownload_redirectToPublicAddress_followed`、`doDownload_relativeLocationInSecondHop_resolvedAgainstCurrentUrl`（本地 HTTP 服务模拟，非真实公网 CDN）
- [ ] 连接后复验实际对端 IP（issue P1，本轮未覆盖）
- [ ] `HttpClientUtil` / `HttpUtil` 关闭自动重定向或逐跳校验（issue P1，本轮未覆盖）
- [ ] 全部出网 HTTP 调用收敛到统一客户端工厂、元数据端点告警（issue P2，本轮未覆盖）
- [ ] 单测运行结果：本轮为回溯补写，未执行 `mvn test`（未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` 模块 `SsrfsafeUrlUtil`；`dm` 模块 `ProjectNoticeScanExecutor`（HTTP 下载实现由 JDK HttpClient 换为 OkHttp）
- 接口 / 契约：无变化
- 配置：无新增配置项；超时与原实现对齐（连接 30s、读 10min 间隔），`MAX_REDIRECT_HOPS=5` 不变
- 依赖：使用仓内已有的 OkHttp（`okhttp3`），无新增依赖
- schema：无变化
