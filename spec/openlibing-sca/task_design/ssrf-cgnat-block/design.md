# 142 — 技术设计

## 方案概述

在 SSRF 判定的唯一入口 `SsrfsafeUrlUtil#resolveAndValidate` 中，把「解析后地址是否允许外联」的判定扩展为「JDK 四类判定 OR 逐字节 IPv4 CIDR 黑名单」，一次改动同时覆盖受理侧与下载侧。CIDR 用「前缀字节数组 + 前缀位数」表示，支持 `/10`、`/15` 这类非整字节掩码；匹配前把 IPv4-mapped IPv6 还原为 4 字节，避免以 IPv6 文本绕过。

## 判断链（修复后）

```
resolveAndValidate(url)
  ├─ 协议白名单 http/https
  ├─ host == "localhost" → 拒绝
  ├─ InetAddress.getAllByName(host)
  └─ 对每个 address：
       isLoopbackAddress || isAnyLocalAddress || isSiteLocalAddress || isLinkLocalAddress
       || isBlockedIpv4Cidr(address)        ← 新增
          ├─ 16 字节且 isIpv4Mapped → 取后 4 字节
          ├─ 非 4 字节 → 不匹配（IPv6 不落入 IPv4 网段空间）
          └─ 依次比对 BLOCKED_IPV4_CIDRS
     命中 → IllegalArgumentException("Internal network access not allowed")
  返回 List.of(addresses)  ← 供 #143 的连接层 pin 使用
```

黑名单数据（`BLOCKED_IPV4_CIDRS`）：

| 网段          | 前缀表示               | 用途                                                  |
| ------------- | ---------------------- | ----------------------------------------------------- |
| 100.64.0.0/10 | `{100, 64}` + 10 bit   | RFC 6598 CGNAT，含阿里云元数据 100.100.100.200（P0）  |
| 0.0.0.0/8     | `{0x00}` + 8 bit       | "本网络"段；`isAnyLocalAddress` 只匹配 0.0.0.0 单地址 |
| 192.0.0.0/24  | `{192, 0, 0}` + 24 bit | IETF 协议分配段                                       |
| 198.18.0.0/15 | `{198, 18}` + 15 bit   | RFC 2544 基准测试段（含 198.18/198.19）               |

## 架构决策

| 决策                                                            | 理由                                                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| D1 逐字节 CIDR 而非 `InetAddress` 分类                          | JDK 分类口径固定且漏段；自维护前缀表可精确覆盖 CGNAT 等特殊段，且不误伤相邻公网地址                        |
| D2 黑名单挂在 `resolveAndValidate` 单点，而非各 sink 分别加     | 受理侧（supplement）与下载侧（doDownload/doGitDownload）共用同一函数，一处生效即两侧同时生效，避免防护漂移 |
| D3 `record CidrBlock(byte[] prefix, int prefixBits)` + 逐位掩码 | 支持 /10、/15 非整字节前缀；匹配逻辑局部、无第三方依赖                                                     |
| D4 IPv4-mapped IPv6 归一化后再匹配                              | 防止以 `::ffff:100.100.100.200` 形式书写绕过 4 字节比较                                                    |
| D5 网段表硬编码常量、无开关                                     | 安全默认不可关闭，避免配置误关导致回归                                                                     |
| D6 测试用字面 IP + mock `getAllByName`                          | 不依赖真实 DNS/网络，CI 可稳定复现；同时验证「域名解析到该段」路径                                         |

## 涉及文件

| 文件                                                                                     | 操作 | 说明                                                                                                                               |
| ---------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/utils/SsrfsafeUrlUtil.java`                   | 修改 | 新增 `BLOCKED_IPV4_CIDRS`、`isBlockedIpv4Cidr`、`isIpv4Mapped`、`CidrBlock`；`resolveAndValidate` 拒绝条件追加 `isBlockedIpv4Cidr` |
| `src/test/java/com/openlibing/sca/analysis/utils/SsrfsafeUrlUtilTest.java`               | 新增 | 本 commit 新建 10 个用例，覆盖 CGNAT 元数据/边界/段外、域名解析、IPv4-mapped、其余三段、既有拦截不回退、公网字面 IP                |
| `src/test/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanServiceImplTest.java` | 修改 | 新增 `supplementNotice_ssrfCgnatUrl_rejected`（受理侧拒绝且不落库、不发事件）                                                      |
| `src/test/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutorTest.java`            | 修改 | 新增 `doDownload_rejectsCgnatCloudMetadataAddress`（下载侧拒绝）                                                                   |

## 风险 & 缓解

| 风险                                                                                                                     | 缓解                                                                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 误伤：合法服务部署在 100.64.0.0/10（如运营商级 NAT 环境下的公网出口）                                                    | 该段按 RFC 6598 不允许作为公网目标；段外相邻地址有专门用例保证不误伤                                                                                                                                       |
| 仅覆盖 IPv4 特殊段，IPv6 特殊段（`fc00::/7` 等）未逐段收敛                                                               | 依赖 JDK `isSiteLocalAddress` / `isLinkLocalAddress` 既有判定；列入后续加固项                                                                                                                              |
| 0.0.0.0/8 拦截可能影响历史以 `0.x.x.x` 书写的内网地址                                                                    | 该段本身不可作为有效目标，取舍为 fail-closed                                                                                                                                                               |
| `isIpv4Mapped` 实现判定为「前 11 字节为 0 且第 12 字节为 0xFF」，与注释「前 12 字节为 0、第 12 字节为 0xFF」的表述不一致 | JDK 会把 `::ffff:a.b.c.d` 归一为 `Inet4Address`（`getAddress()` 返回 4 字节），该分支实际很少触发；用例 `validateUrl_rejectsIpv4MappedCgnatAddress` 走的是归一后的 4 字节路径（跨 JVM 实现的一致性未验证） |
| 全部出网调用方共享该黑名单，可能改变既有集成分支行为                                                                     | 仅新增 4 个网段的拒绝面；其余判定逻辑未改动                                                                                                                                                                |

## 跨仓影响

无。仅 `openlibing-sca` 与 `openlibing-docs`。

## 明确不在范围

- 其余 IPv4 特殊用途段的完整收敛（TEST-NET-1/2/3、240.0.0.0/4 等）
- IPv6 特殊用途段逐段收敛
- DNS 校验与建连绑定（见 `ssrf-dns-rebinding-pinning`）
- git clone / HTTP 重定向封堵（见 `ssrf-redirect-hardening`）
