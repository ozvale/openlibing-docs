# 143 — 技术设计

## 方案概述

「解析一次、核准一次、按核准集合建连」：`SsrfsafeUrlUtil.resolveAndValidate` 把解析结果返回给调用方，`doDownload` 用 OkHttp 的按请求 `Dns` 把 origin host 钉在核准集合上，`doGitDownload` 用 `GIT_CONFIG_*` → libcurl `CURLOPT_RESOLVE` 把 host:port 钉在核准集合上。两条 sink 的重定向都不再自动跟随，改为逐跳重新执行「解析 → 判定 → pin」。

## 数据流（修复后）

```
doDownload(url)
  ├─ sendPinnedGet(url)
  │    ├─ approved = SsrfsafeUrlUtil.resolveAndValidate(url)      // 与校验同一次解析
  │    ├─ dns = buildPinnedDns(URL(url).getHost(), approved)      // 仅 origin host 返回核准集合
  │    ├─ client = DOWNLOAD_BASE_CLIENT.newBuilder().dns(dns).build()  // 共享连接池，followRedirects=false
  │    └─ client.newCall(GET url).execute()
  └─ 重定向循环（≤ 5 跳）
       ├─ Location 相对当前跳解析（URI.resolve）
       ├─ response.close() 释放上一跳连接
       └─ sendPinnedGet(下一跳)  // 重新核准 + 重新 pin；内网目标在此抛 IllegalArgumentException

doGitDownload(repoUrl)
  ├─ approved = resolveApprovedAddresses(repoUrl)      // 包私有方法，单测可替换解析结果
  ├─ env = buildGitResolveEnv(repoUrl, approved)       // http.curloptResolve=host:port:addr[,addr...]
  └─ CmdInjection.runCmd(git clone ..., env)           // 子进程只连核准 IP；解析失败防御性抛 ScaException
```

## 架构决策

| 决策                                                                        | 理由                                                                                                        |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| D1 `resolveAndValidate` 返回 `List<InetAddress>`，`validateUrl` 仅委托      | 12 处既有 `validateUrl` 调用点零改动；需要闭环的 sink 取到与校验同一份解析结果，从结构上消除 check-then-use |
| D2 HTTP 客户端从 `java.net.http.HttpClient` 换为 OkHttp                     | JDK HttpClient 不支持按请求替换 DNS；OkHttp `Dns` 可按 host 返回固定地址集合，且仓内已有 okhttp 4.11.0 依赖 |
| D3 共享 `DOWNLOAD_BASE_CLIENT` + 每请求 `newBuilder().dns(...)`             | 每请求 pin 不同 host，同时复用连接池与线程资源，避免请求级新建客户端                                        |
| D4 pinned `Dns` 只对本次 origin host 生效，其余 host 回退 `Dns.SYSTEM`      | 代理场景由代理侧解析 origin，pin 不适用；若对所有 host 都返回核准集合，会破坏代理建连                       |
| D5 关闭自动重定向，手动逐跳并重新 pin                                       | 每跳目标都要重新判定；`Location` 以当前跳 URL 为基准解析，避免相对 Location 拼回首跳 host                   |
| D6 git clone 用 `GIT_CONFIG_COUNT/KEY_n/VALUE_n` 注入 `http.curloptResolve` | git 子进程不共享 JVM DNS 缓存，只能在 libcurl 层固定解析表；环境变量注入不经过 shell，无注入与泄露面        |
| D7 `resolveApprovedAddresses` 抽为包私有方法                                | 单测可模拟「核准结果 ≠ 系统解析」的 rebinding 场景，不必真实污染 DNS                                        |
| D8 `buildGitResolveEnv` 解析失败抛 `ScaException`                           | 不给无 pin 继续外联的降级路径，保持 fail-closed                                                             |
| D9 TLS 仍按 URL host 做 SNI 与证书校验                                      | pin 只影响地址选择，不放宽证书校验                                                                          |

## 涉及文件

| 文件                                                                          | 操作 | 说明                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/utils/SsrfsafeUrlUtil.java`        | 修改 | 新增 `resolveAndValidate`（返回 `List.of(addresses)`）；`validateUrl` 改为委托                                                                                                                                                                             |
| `src/main/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutor.java`     | 修改 | 新增 `DOWNLOAD_BASE_CLIENT`、`resolveApprovedAddresses`、`sendPinnedGet`、`buildPinnedDns`、`extractUrlHost`、`responseBodyOf`、`buildGitResolveEnv`；`doDownload` 改用 OkHttp 并逐跳 re-pin；`doGitDownload` 注入 pin 环境；移除原 `buildDownloadRequest` |
| `src/test/java/com/openlibing/sca/analysis/utils/SsrfsafeUrlUtilTest.java`    | 修改 | 新增 `resolveAndValidate_returnsApprovedLiteralAddress`、`resolveAndValidate_returnsAllResolvedAddressesInOrder`、`resolveAndValidate_rejectsReboundInternalAddress`                                                                                       |
| `src/test/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutorTest.java` | 修改 | 新增 pinned 建连、重定向 re-pin、`buildPinnedDns`、`buildGitResolveEnv` 系列用例；新增本地 `HttpServer` 桩与 OkHttp `Response` 桩                                                                                                                          |

## 风险 & 缓解

| 风险                                                                           | 缓解                                                                                                          |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| 解析结果含多个地址（CDN 常见）时全部参与 pin，某一地址不可达仍需客户端按序重试 | OkHttp 按 `Dns` 返回顺序尝试；超时/失败沿用既有候选重试与候选回退                                             |
| 域名的解析结果在短 TTL 下变化，pin 的是请求时刻快照                            | 这是设计目标（连接必须使用校验时地址）；连接失败按候选回退，不回退到重新解析                                  |
| 代理环境下 pin 只作用于 origin，代理侧解析不受控                               | 明确边界：代理为部署方可信配置（JVM `http(s).proxyHost`），非外部输入；代码注释与 `buildPinnedDns` 保证不误用 |
| git 版本不支持 `http.curloptResolve`                                           | 运行环境 openEuler 24.03（git 2.43 / curl 8.x）；`b18855ba` 修正版本说明为 git ≥ 2.37                         |
| git 侧仍可能跟随重定向（本 commit 未关）                                       | 同一批次后续 commit `b18855ba` 注入 `http.followRedirects=false` 收口，见 `ssrf-redirect-hardening`           |
| 其他出网路径未绑定核准地址                                                     | 已知残余风险：`HttpClientUtil` / `HttpUtil` / `BasePackageUrlResolver` 仍只 `validateUrl`                     |

## 跨仓影响

无。仅 `openlibing-sca` 与 `openlibing-docs`。

## 明确不在范围

- 连接后对端 IP 复验、统一客户端工厂、元数据端点告警（issue P1/P2）
- 代理链路的 SSRF 判定

## 关联 spec

- `ssrf-redirect-hardening`（#109）：git clone 重定向 fail-closed 收口
- `ssrf-cgnat-block`（#142）：同一判定函数内的网段黑名单
