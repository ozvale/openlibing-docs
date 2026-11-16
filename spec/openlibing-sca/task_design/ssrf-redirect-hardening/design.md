# 109 — 技术设计

## 方案概述

把「校验」与「建连」合并为同一次 DNS 解析：`SsrfsafeUrlUtil.resolveAndValidate(url)` 返回核准地址集合，调用方把该集合绑定到连接层（HTTP 走 OkHttp pinned `Dns`，git clone 走 `GIT_CONFIG_*` → libcurl `CURLOPT_RESOLVE`），从而消除校验后重新解析的 TOCTOU 窗口；同时补齐特殊网段黑名单，并让 git clone 对重定向 fail-closed。

三层防线：

1. 语法预过滤：`ProjectNoticeScanExecutor#isUrlSafe`（scheme 白名单 + `URL_BLOCKED_CHARS`），只做格式与 shell 元字符拦截，不承担 SSRF 判定。
2. SSRF 判定：`SsrfsafeUrlUtil#resolveAndValidate` —— 协议、localhost、解析后的 loopback/anyLocal/siteLocal/linkLocal + 逐字节 CIDR 黑名单。
3. 连接绑定：核准集合 pin 到实际建连，HTTP 与 git clone 两条 sink 各自实现，重定向逐跳重新执行第 2、3 步。

## 数据流（修复后）

```
downloadPackage (isUrlSafe 语法预过滤 + 候选解析)
  ├─ doDownload(url)
  │    └─ sendPinnedGet(url)
  │         ├─ resolveApprovedAddresses → SsrfsafeUrlUtil.resolveAndValidate（拒绝则 IllegalArgumentException）
  │         ├─ buildPinnedDns(originHost, approved) → DOWNLOAD_BASE_CLIENT.newBuilder().dns(...)
  │         └─ execute（followRedirects=false）
  │    重定向循环（≤ MAX_REDIRECT_HOPS=5）
  │         └─ Location → 相对解析 → response.close() → sendPinnedGet(下一跳)（重新核准 + 重新 pin）
  └─ doGitDownload(url)
       ├─ resolveApprovedAddresses(repoUrl)
       ├─ buildGitResolveEnv → GIT_CONFIG_COUNT=2
       │     ├─ http.curloptResolve = host:port:addr[,addr...]
       │     └─ http.followRedirects = false
       └─ CmdInjection.runCmd(clone..., env)（子进程仅连核准 IP，302 直接失败）
```

## 架构决策

| 决策                                                                                                  | 理由                                                                                                                                                         |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1 新增 `resolveAndValidate` 返回 `List<InetAddress>`，`validateUrl` 委托之                           | 保留既有 12 处 `validateUrl` 调用点零改动；需要闭环的 sink 拿到同一次解析结果（`eb7cb58d`）                                                                  |
| D2 HTTP 侧改用 OkHttp + 每请求 pinned `Dns`，不再用 `java.net.http.HttpClient`                        | JDK HttpClient 无法按请求替换 DNS 解析；OkHttp `Dns` 可只对本次 origin host 返回核准集合，其余 host（代理）回退 `Dns.SYSTEM`                                 |
| D3 基础客户端关闭自动重定向（`followRedirects(false)` / `followSslRedirects(false)`），重定向手动逐跳 | 每一跳都能重新核准 + 重新 pin；`MAX_REDIRECT_HOPS=5` 防环                                                                                                    |
| D4 git clone 通过 `GIT_CONFIG_KEY_n/VALUE_n` 注入 `http.curloptResolve`，不拼命令行                   | git 子进程独立解析、不共享 JVM DNS 缓存，必须用 libcurl 的 resolve 表钉住；环境变量注入避免 URL/参数泄露与注入面                                             |
| D5 git clone 追加 `http.followRedirects=false`（fail-closed）                                         | git 默认 `initial` 会跟随首个 302 并经 `update_url_from_redirect` 把对象传输整体搬到重定向目标，绕过核准 pin；fail-closed 后由上层回退候选地址（`b18855ba`） |
| D6 IPv6 核准地址按 curl 文档加方括号                                                                  | `CURLOPT_RESOLVE` 对 IPv6 的非方括号写法无文档保证；IPv4/IPv6 混合（A+AAAA）时仅 IPv6 加括号                                                                 |
| D7 `buildGitResolveEnv` 解析异常时防御性抛 `ScaException`                                             | 不给「无 pin 继续外联」留分支                                                                                                                                |
| D8 特殊网段逐字节 CIDR 黑名单                                                                         | 不依赖 JDK `InetAddress` 分类（漏 CGNAT 等），细节见 `ssrf-cgnat-block`                                                                                      |
| D9 下载临时文件与响应关闭语义保持原样（`.part` + 失败清理 + finally 关闭）                            | 避免为安全改造引入下载可靠性回归                                                                                                                             |

## 涉及文件

| 文件                                                                          | 操作        | 说明                                                                                                                                                                                                                                                                                                                              |
| ----------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/utils/SsrfsafeUrlUtil.java`        | 修改        | 新增 `resolveAndValidate`（`eb7cb58d`）；新增 `BLOCKED_IPV4_CIDRS` / `isBlockedIpv4Cidr` / `CidrBlock`（`3980eb33`）                                                                                                                                                                                                              |
| `src/main/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutor.java`     | 修改        | 新增 `DOWNLOAD_BASE_CLIENT` / `resolveApprovedAddresses` / `sendPinnedGet` / `buildPinnedDns` / `extractUrlHost` / `responseBodyOf` / `buildGitResolveEnv`；`doDownload` 改用 OkHttp 并逐跳重 pin；`doGitDownload` 注入 pin 环境（`eb7cb58d`）；`buildGitResolveEnv` 增 `http.followRedirects=false` 与 IPv6 方括号（`b18855ba`） |
| `src/test/java/com/openlibing/sca/analysis/utils/SsrfsafeUrlUtilTest.java`    | 新增 / 修改 | `3980eb33` 新建（黑名单用例）；`eb7cb58d` 追加 `resolveAndValidate_*` 三个用例                                                                                                                                                                                                                                                    |
| `src/test/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutorTest.java` | 修改        | 新增 `doDownload_pinsConnectionToApprovedAddresses`、`doDownload_redirectHopAlsoUsesPinnedResolution`、`buildPinnedDns_returnsApprovedForOriginHostAndSystemDnsForOthers`、`buildGitResolveEnv_*`（含 IPv6 方括号与重定向断言）                                                                                                   |

## 风险 & 缓解

| 风险                                                                                   | 缓解                                                                                                  |
| -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 域名解析结果同时含公网与私网地址时整体被拒绝，合法站点可用性下降                       | fail-closed 取舍；解析结果全量参与判定，避免「取第一个」被 rebinding 利用                             |
| 代理场景 pinned DNS 不适用（origin 由代理解析）                                        | pinned `Dns` 只对本次 origin host 生效，代理 host 走 `Dns.SYSTEM`；代码注释明确该边界                 |
| CDN 依赖重定向；git clone 拒绝所有重定向（含 http→https 升级）                         | 下载候选机制回退下一个候选地址；A8 用例验证非重定向 clone 不受影响                                    |
| git/curl 版本不满足 `http.curloptResolve`                                              | 运行环境固定 openEuler 24.03（git 2.43 / curl 8.x）；版本要求写入注释（`b18855ba` 修正为 git ≥ 2.37） |
| 受理阶段 DNS 解析失败（UnknownHostException）被放行                                    | 仅受理侧放行，下载 sink 仍强制校验；与既有 #105 设计一致                                              |
| 其他出网路径（`HttpClientUtil` / `HttpUtil` / `BasePackageUrlResolver`）仍只校验不 pin | 已知残余风险，见「明确不在范围」；本批次仅覆盖公告扫描下载与 git clone 两条 sink                      |

## 跨仓影响

无。仅 `openlibing-sca` 代码与 `openlibing-docs`（本目录）变更。

## 明确不在范围

- 统一出网客户端工厂与 host 白名单（issue 建议 1 / 4 的完整版本）
- 连接后对端 IP 复验、元数据端点连接告警（见 `ssrf-dns-rebinding-pinning`）
- 代理链路上的 SSRF 判定（代理侧解析不受 pin 约束）

## 关联 spec

- `ssrf-cgnat-block`（#142）：CIDR 黑名单子项
- `ssrf-dns-rebinding-pinning`（#143）：`resolveAndValidate` 与 pinned 连接子项
