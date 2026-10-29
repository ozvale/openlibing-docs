# security-ssrf-guard: 收敛外部地址探测链路的 SSRF 攻击面

## 需求背景

`openlibing-cicd` 存在三处由用户可控 URL 驱动的服务端出站请求链路：

1. **sec-option 扫描的产物下载可达性探测**：对扫描请求中携带的包下载地址发起 HEAD/GET 请求，判定其是否可下载；
2. **流水线日志与测试结果下载**：`PipelineEventConsumer` 通过 `RestTemplate.getForObject` 拉取 OBS 上的测试用例结果、UT 结果与构建产物 JSON；
3. **通用请求入口与 webhook 回调**：`HttpRequestUtil.sendRequest` 被业务复用，`PipelineStartEventHandler.runPipeline` 用它回调流水线 webhook。

原有 SSRF 防护仅依赖字符串前缀黑名单（`"10."`、`"172.16."`、`"192.168."`、`"169.254."`、`"127."`、`"0."` 等），存在以下问题：

- 非点分 IPv4 形态（`http://0x7f000001/x`、`http://0177.0.0.1/x`、`http://2130706433/x`）不匹配前缀；
- IPv6 及其内嵌 IPv4 形态（IPv4 映射 `::ffff:0:0/96`、NAT64 `64:ff9b::/96`、6to4 `2002::/16`）完全不覆盖；
- 域名解析出多条 A/AAAA 记录时可轮询绕过，且校验阶段与建连阶段各解析一次，存在 DNS rebinding 窗口；
- 302 跳转可把请求带到未校验的地址；
- 下载响应体无上限，大响应可耗尽内存；
- 日志中直接打印完整 OBS 签名 URL，存在凭证泄露风险。

已有的 `security-injection-and-rce-fix` 只处理了 YAML 反序列化 RCE，未覆盖 SSRF。

## 功能描述

本 spec 覆盖两个堆叠 PR：

- **!631（基座，分支 `fix_ssrf_probe_allowlist`）**：重写 `SafeRequestUtils` 的内网判定为字节级 CIDR 匹配，新增主机白名单与 `SafeDns`，将 sec-option 探测链路切换到 OkHttp，并把「未命中白名单」的表达从 `false` 改为 `Optional.empty()`。
- **!639（在 !631 之上加固，分支 `fix/security-vuln-489-ssrf-guard`）**：新增独立 `SafeDns`（`INTERNAL` / `METADATA_ONLY` 双档），补 `RESTRICTED_IPV4_CIDRS`，为 `HttpRequestUtil` 抽出 `doSend` 并新增 `sendRequestSafely`，为日志/结果下载链路引入 `downloadText`（协议白名单 + IP 字面量校验 + 10MB 上限 + 不跟随重定向），并对日志中的 URL 统一脱敏。

## 验收标准

- [x] `SafeRequestUtils` 以字节级位掩码 CIDR 表（`INTERNAL_IPV4_CIDRS` / `INTERNAL_IPV6_CIDRS`）取代字符串前缀黑名单
- [x] IPv4 映射、NAT64、6to4 三类内嵌 IPv4 的 16 字节地址可被展开并递归判定
- [x] `isInternalAddress(String)` 遍历 `InetAddress.getAllByName` 的全部记录，任一命中即拒绝
- [x] `isHostAllowed` 按 label 边界做后缀匹配，`gitcode.com` 命中 `api.gitcode.com`、不命中 `evilgitcode.com`；拒绝 URL userinfo 与非默认端口
- [x] sec-option 探测使用禁用重定向的 OkHttp 客户端，并通过 `SafeDns` 消除 DNS rebinding
- [x] 未命中允许探测来源时不写 `false`，`package_download_accessible` 落 NULL 表示「未检测」
- [x] 日志/结果/构建产物下载增加协议白名单、IP 字面量校验、10MB 响应体上限与 URL 长度上限
- [x] `HttpRequestUtil` 新增 `sendRequestSafely`，`doSend` 统一 `IOException` 与 `IllegalArgumentException` 的返回契约
- [x] 下载与请求日志中的 URL 经 `SafeRequestUtils.maskUrl` 脱敏，仅保留 host:port
- [x] 补充 `SafeRequestUtilsTest`、`SecOptionScanServiceImplTest`、`SafeDnsTest`、`HttpRequestUtilTest`、`PipelineEventConsumerImplTest`、`PipelineStartEventHandlerTest`

## 影响范围

| 文件                                                                                         | 操作 | 说明                                                                                                         |
| -------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------ |
| `src/main/java/com/openlibing/cicd/common/utils/SafeRequestUtils.java`                       | 修改 | CIDR 表、`isInternalAddress` 重写、`isHostAllowed`、`isRestrictedNetworkAddress`、`CidrBlock` 内部类         |
| `src/main/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImpl.java`      | 修改 | 新增白名单配置与 OkHttp 探测客户端、内嵌 `SafeDns`、`checkDownloadAccessible` 返回类型改 `Optional<Boolean>` |
| `src/main/java/com/openlibing/cicd/common/utils/SafeDns.java`                                | 新增 | `Scope` 双档 DNS 校验、`verifyLiteralHost`                                                                   |
| `src/main/java/com/openlibing/cicd/common/utils/HttpRequestUtil.java`                        | 修改 | 抽出 `doSend`、新增 `sendRequestSafely` 与 `SAFE_CLIENT`                                                     |
| `src/main/java/com/openlibing/cicd/business/listener/PipelineStartEventHandler.java`         | 修改 | `runPipeline` 改用 `sendRequestSafely`                                                                       |
| `src/main/java/com/openlibing/cicd/business/listener/PipelineEventConsumer.java`             | 修改 | 新增 `DOWNLOAD_CLIENT`、`downloadText`/`readLimited`/`normalizeUrl`，三处下载改造，URL 脱敏                  |
| `src/test/java/com/openlibing/cicd/common/utils/SafeRequestUtilsTest.java`                   | 修改 | +126 行，内网/保留网段、非点分 IPv4、IPv6 zoneId、白名单后缀边界                                             |
| `src/test/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImplTest.java`  | 修改 | +156 行，探测判定矩阵、`SafeDns`、HEAD/GET 状态码映射                                                        |
| `src/test/java/com/openlibing/cicd/common/utils/SafeDnsTest.java`                            | 新增 | 约 190 行，字面量主机、内嵌 IPv4、`METADATA_ONLY` 放行 RFC1918                                               |
| `src/test/java/com/openlibing/cicd/common/utils/HttpRequestUtilTest.java`                    | 修改 | +56 行                                                                                                       |
| `src/test/java/com/openlibing/cicd/business/service/impl/PipelineEventConsumerImplTest.java` | 修改 | +160 行，下载成功/非 2xx/超限/非 http 协议                                                                   |
| `src/test/java/com/openlibing/cicd/business/listener/PipelineStartEventHandlerTest.java`     | 修改 | +33 行                                                                                                       |

## 关联 Issue

- openlibing-cicd#328（sec-option 探测链路 SSRF，状态 open）：https://gitcode.com/openlibing/openlibing-cicd/issues/328
- openlibing-cicd#489（日志下载链路与通用请求入口 SSRF 加固）：https://gitcode.com/openlibing/openlibing-cicd/issues/489

## 关联 PR 与提交

**!631 —— SafeRequestUtils 网段漏检与探测白名单**

- 标题：《【安全】【漏洞挖掘】SafeRequestUtils SSRF 网段漏检 - 0929-012》，状态 open
- 分支：`fix_ssrf_probe_allowlist`，base：`upstream/release_20261029_iter2`
- diff 规模：4 文件，704 insertions / 102 deletions，无 pom/yml 改动
- 提交：
  - `18bdf7749` harden SSRF check with host allowlist and CIDR
  - `e562c9489` merge: sync release_20261029_iter2 into fix_ssrf_probe_allowlist
  - `c596cdf41` address SSRF review findings

**!639 —— 日志下载链路与通用请求入口加固（堆叠于 !631 之上）**

- 标题：《fix(ssrf): 日志下载链路增加 SSRF 防护与响应体上限》，状态 open
- 分支：`fix/security-vuln-489-ssrf-guard`，base：!631 的分支
- 提交：
  - `4daed16a7` 日志下载链路增加 SSRF 防护与响应体上限
  - `59d36f71e` 补齐下载链路协议白名单与保留网段拦截
  - `c54c44f77` 补齐元数据网段与安全请求入口的协议白名单
  - `126c332a3` 加固隧道内嵌地址判定与 URL 日志脱敏
  - `88a2c60e3` 统一 doSend 请求构建异常返回契约
