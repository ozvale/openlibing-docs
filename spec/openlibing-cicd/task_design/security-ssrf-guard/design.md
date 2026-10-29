# security-ssrf-guard — 工程设计

## 1. 方案设计

### 1.1 Sink（出站点）

| 链路                                   | 出站方式                                                                 | 可控输入               |
| -------------------------------------- | ------------------------------------------------------------------------ | ---------------------- |
| sec-option 包裹下载可达性探测          | `HttpURLConnection` → OkHttp `probeClient`（HEAD，405/401 降级 GET）     | 扫描请求中的包下载 URL |
| 日志/测试用例结果/UT 结果/构建产物下载 | `RestTemplate.getForObject` → OkHttp `DOWNLOAD_CLIENT`                   | OBS 下载 URL           |
| 通用请求入口                           | `HttpRequestUtil.sendRequest` 及其调用方                                 | 业务传入的 URL         |
| 流水线 webhook 回调                    | `HttpRequestUtil.sendRequest`（`PipelineStartEventHandler.runPipeline`） | 流水线 webhook 地址    |

### 1.2 Source（可控入口）

- sec-option 扫描请求中的 `package` 下载地址；
- 流水线事件消息中携带的 OBS 日志/结果/产物地址；
- 代码仓 push / MR 事件触发流水线时的 webhook 地址。

### 1.3 攻击链与原始缺陷

1. 攻击者提交形如 `http://169.254.169.254/...`、`http://127.0.0.1:port/...` 或内网 RFC1918 地址；
2. 服务端代其发起请求，读取元数据服务或内网接口；
3. 绕过原始防护的手段：
   - **字符串前缀黑名单**：`0x7f000001`、`0177.0.0.1`、`2130706433` 等非点分形态不匹配 `"127."`；
   - **IPv6 及其内嵌 IPv4**：IPv4 映射、NAT64 `64:ff9b::/96`、6to4 `2002::/16` 完全不在覆盖范围；
   - **多记录 DNS**：`getAllByName` 只取首条时，可把内网地址排在非首条绕过；
   - **DNS rebinding**：校验时解析为公网、建连时再解析为内网；
   - **302 跳转**：`RestTemplate` 默认跟随重定向，校验地址与实际请求地址不一致；
   - **超大响应体**：下载链路无上限，可直接打爆堆内存。

### 1.4 分层策略

按以下顺序逐层拦截，任一层命中即短路：

1. **协议白名单**：仅 `http` / `https`（`isSafeProtocol`）；
2. **主机白名单**（仅探测链路）：`isHostAllowed` 按 label 边界做后缀匹配，且禁止 userinfo、要求默认端口；
3. **地址分类**：`SafeDns.Scope` 分 `INTERNAL`（全部内网/保留地址）与 `METADATA_ONLY`（回环、链路本地、组播、保留网段，放行 RFC1918）；
4. **DNS 解析期拦截**：`SafeDns` 在解析结果上逐个校验，任一命中即抛 `UnknownHostException`，消除校验/建连两次解析的差异；
5. **IP 字面量显式校验**：OkHttp 对 IP 字面量主机不走 `Dns`，由 `SafeDns.verifyLiteralHost` 单独补位；
6. **不跟随重定向**：探测与下载客户端均 `followRedirects(false)` / `followSslRedirects(false)`；
7. **响应体与 URL 长度上限**：`MAX_DOWNLOAD_BYTES = 10MB`、`MAX_URL_LENGTH = 2048`；
8. **日志脱敏**：URL 统一经 `SafeRequestUtils.maskUrl`，只保留 host:port。

## 2. 实现逻辑设计

### 2.1 内网判定：字符串前缀 → 字节级 CIDR（!631）

改前：`SSRF_INTERNAL_HOST_PREFIXES` 字符串前缀 `startsWith` 匹配，非点分 IPv4、IPv6、内嵌地址全部漏检。

改后：两类字节级 CIDR 表 + 位掩码判定：

```java
private static final List<CidrBlock> INTERNAL_IPV4_CIDRS = ...; // 0/8,10/8,100.64/10,127/8,169.254/16,172.16/12,
                                                              // 192.0.0/24,192.0.2/24,192.168/16,198.18/15,
                                                              // 198.51.100/24,203.0.113/24,224/4,240/4
private static final List<CidrBlock> INTERNAL_IPV6_CIDRS = ...; // ::/128,::1/128,100::/64,2001::/32,
                                                               // 2001:2::/48,2001:20::/28,2001:db8::/32,
                                                               // 3fff::/20,fc00::/7,fe80::/10,ff00::/8
private static final CidrBlock NAT64_WELL_KNOWN_PREFIX = ...;   // 64:ff9b::/96
```

前缀黑名单常量删除，判定改为 `CidrBlock.contains(InetAddress)` 的字节位掩码比较。

### 2.2 `isInternalAddress(String)`：全记录遍历（!631）

改前：`InetAddress.getByName` 取单条 + 字符串前缀兜底。

改后：

1. `normalizeHostForResolution` 去掉 IPv6 方括号与 `%zone`；
2. `InetAddress.getAllByName(host)` 遍历全部 A/AAAA 记录；
3. 任一记录被 `isInternalAddress(InetAddress)` 判定为内网即返回 `true`。

### 2.3 `isInternalAddress(InetAddress)`：内置谓词 + 内嵌 IPv4 展开（!631）

改前：无此重载。

改后：

- 内置谓词：`isAnyLocalAddress` / `isLoopbackAddress` / `isLinkLocalAddress` / `isSiteLocalAddress` / `isMulticastAddress`；
- 16 字节地址经 `extractEmbeddedIpv4` 展开：IPv4 映射（`::ffff:0:0/96`）、NAT64（`64:ff9b::/96`）、6to4（`2002::/16` 取第 2–5 字节），对展开结果递归判定；
- 新增内部类 `CidrBlock` 提供字节级位掩码 `contains`。

### 2.4 主机白名单（!631）

改前：无白名单概念，任意公网域名均可探测。

改后：新增 `isHostAllowed(String downloadUrl, List<String> allowedHostSuffixes)`：

- 空 URL 或空白名单返回 `false`；
- 要求 `isSafeProtocol` 通过；
- 禁止 URL 携带 userinfo；
- 端口必须等于协议默认端口（https→443，http→80）；
- `getHost()` 不得以 `[` 开头（拒绝 IPv6 字面量）；
- 后缀按 label 边界匹配：`equals(suffix)` 或 `endsWith("." + suffix)`，因此 `gitcode.com` 命中 `api.gitcode.com`，不命中 `evilgitcode.com`。

`SSRF_FORBIDDEN_HOSTS` 由可变 `HashSet` 改为不可变 `Set.of("localhost","ip6-localhost","ip6-loopback")`。

### 2.5 sec-option 探测链路改造（!631）

改前：`checkDownloadAccessible` 返回 `Boolean`；`HttpURLConnection` 直接请求；不可达即 `false`，包含「不在探测范围」的情况。

改后：

- 新增配置 `@Value("${artifact-probe.allowed-host-suffixes}") private List<String> allowedHostSuffixes;`（本 PR 唯一新增配置项）；
- 新增 `DEFAULT_PROBE_CLIENT`：OkHttp，connect 5s / read 10s、不跟随 HTTP 与 SSL 重定向、`dns(new SafeDns(Dns.SYSTEM))`；保留可替换字段 `probeClient` 供单测指向本地服务；
- 新增 `static final class SafeDns implements Dns`：`lookup` 结果任一 `isInternalAddress` 即抛 `UnknownHostException("Internal address rejected: " + hostname)`；
- `checkDownloadAccessible` 返回 `Optional<Boolean>`，判定顺序：

```text
空 URL                                  -> false
非 http/https                           -> false（warn）
!isHostAllowed(...)                     -> empty（info: Skip accessibility check for non-allowlisted host）
isInternalAddress(...)                  -> false（warn）
HEAD（405/401 降级 GET）                -> status >= 200 && status < 400
```

- `checkAccessibleByHead` / `checkAccessibleByGet` 改为 `probeClient.newCall(...)` + try-with-resources；GET 保留 `Range: bytes=0-0`；新增 `catch (IllegalArgumentException)`（OkHttp 的 HttpUrl 解析更严格）warn 后返回 `false`；
- `reportScan` 改调 `saveScanRecord(request, json, accessible.orElse(null))`，未命中白名单时 `package_download_accessible` 落 NULL（未检测），不再写 `false`。

### 2.6 新增 `SafeDns`（!639）

改前：仅 sec-option 内嵌的私有 `SafeDns`，只支持「拒绝全部内网」一档。

改后：抽出公共类 `src/main/java/com/openlibing/cicd/common/utils/SafeDns.java`：

- `enum Scope { INTERNAL, METADATA_ONLY }`：`INTERNAL` 拒绝全部内网/保留地址；`METADATA_ONLY` 只拒绝回环、链路本地、组播与保留网段（0/8、100.64/10、127/8、169.254/16、192.0.0/24），放行 RFC1918；
- `NUMERIC_HOST` 正则只认纯数字形态主机（点分十进制、整数形式、`0x` 十六进制），避免把 `cafe.de` 这类合法域名误判为 IP 字面量；
- `lookup` 对解析结果逐个校验；
- `static verifyLiteralHost(url, scope)` 单独处理主机为 IP 字面量的场景——OkHttp 对 IP 字面量不走 `Dns`，这是已知绕过点。

### 2.7 保留网段判定（!639）

改前：`SafeRequestUtils` 只有「内网/保留」合一的 CIDR 表。

改后：新增 `RESTRICTED_IPV4_CIDRS`（0.0.0.0/8、100.64.0.0/10、127.0.0.0/8、169.254.0.0/16、192.0.0.0/24）与 `isRestrictedNetworkAddress(InetAddress)`：IPv4 直接 CIDR 匹配；IPv6 先展开内嵌 IPv4（映射 / NAT64 / 6to4）再递归判定；`null` 视为命中。

### 2.8 `HttpRequestUtil` 通用入口加固（!639）

改前：`sendRequest` 内置请求构建与发送，无协议白名单、无地址校验，`HttpUrl` 解析失败会抛出未处理异常。

改后：

- 抽出私有 `doSend(OkHttpClient, method, url, body, headerMap)`，原 `sendRequest` 行为不变；
- 新增 `sendRequestSafely`：先 `SafeRequestUtils.isSafeProtocol`，再 `SafeDns.verifyLiteralHost(url, METADATA_ONLY)`，通过后走 `SAFE_CLIENT = CLIENT.newBuilder().dns(new SafeDns(Dns.SYSTEM, Scope.METADATA_ONLY))`；
- `doSend` 新增 `catch (IllegalArgumentException)`，返回 `ApiResponse(500, "请求错误")`，与 `IOException` 分支的 `ApiResponse(500, "连接失败")` 保持同一返回契约。

### 2.9 流水线 webhook 回调（!639）

改前：`PipelineStartEventHandler.runPipeline`（约 683–687 行）调用 `HttpRequestUtil.sendRequest`，直接回调 webhook。

改后：改为 `HttpRequestUtil.sendRequestSafely`，代码仓 push/MR 触发流水线时的回调受 SSRF 策略约束。

### 2.10 日志与结果下载链路（!639）

改前：`mergeToObsProducts`、`analyzeLatestTestCasesResult`、`processUtResult` 三处 `RestTemplate.getForObject` 直接拉取 URL，跟随重定向、无响应体上限、日志打印完整签名 URL。

改后：

- 新增 `DOWNLOAD_CLIENT`：connect 5s / read 10s / call 60s、不跟随 HTTP 与 SSL 重定向、`dns(new SafeDns(Dns.SYSTEM))`（INTERNAL 档）；
- 常量 `MAX_DOWNLOAD_BYTES = 10MB`、`MAX_URL_LENGTH = 2048`；
- 新增私有方法：
  - `downloadText(url)`：协议白名单 → `SafeDns.verifyLiteralHost(url, INTERNAL)` → 非法 URL 转 `IOException` → 非 2xx 或空 body 抛异常 → `contentLength` 超限直接拒 → 长度未知走 `readLimited`；
  - `readLimited(ResponseBody, url)`：8KB 分块累计，超限立即中断；
  - `normalizeUrl(rawUrl)`：trim，空或超长返回空串，超长打 warn `Discard abnormal url`；
- 三处调用点由 `RestTemplate.getForObject` 改为 `downloadText`；构建产物 JSON 由 Spring 消息转换器改为 `JSON.parseObject`（fastjson2）；
- 日志中所有 URL 统一经 `SafeRequestUtils.maskUrl` 脱敏，只保留 host:port。

## 3. 类设计

| 类                           | 类型              | 职责                                                                         |
| ---------------------------- | ----------------- | ---------------------------------------------------------------------------- |
| `SafeRequestUtils`           | 修改（工具类）    | 协议白名单、CIDR 判定、内嵌 IPv4 展开、主机白名单、保留网段判定、URL 脱敏    |
| `SafeRequestUtils.CidrBlock` | 新增（内部类）    | 字节级位掩码 `contains(InetAddress)`                                         |
| `SafeDns`                    | 新增（公共类）    | 实现 OkHttp `Dns`；`Scope` 双档校验；`verifyLiteralHost` 处理 IP 字面量      |
| `SafeDns.Scope`              | 新增（枚举）      | `INTERNAL` / `METADATA_ONLY`                                                 |
| `SecOptionScanServiceImpl`   | 修改（服务实现）  | 探测白名单配置、`probeClient`、内嵌 `SafeDns`、HEAD/GET 探测                 |
| `HttpRequestUtil`            | 修改（工具类）    | `doSend` 统一发送、`sendRequestSafely` 安全入口、`SAFE_CLIENT`               |
| `PipelineStartEventHandler`  | 修改（事件处理）  | webhook 回调切到 `sendRequestSafely`                                         |
| `PipelineEventConsumer`      | 修改（MQ 消费者） | `DOWNLOAD_CLIENT`、`downloadText`/`readLimited`/`normalizeUrl`、下载调用改造 |

`SecOptionScanServiceImpl` 中的内嵌 `SafeDns` 与 !639 新增的公共 `SafeDns` 同名但职责不同：前者只服务探测客户端且只实现拒绝全部内网一档，后者支持双档并对 IP 字面量补位。

## 4. 数据模型设计

无表结构变更：两个 PR 均未包含 liquibase 变更集，无 pom / yml 改动。

字段语义变更：

| 字段                          | 变更前                                                                 | 变更后                                                                       |
| ----------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `package_download_accessible` | 布尔二态（true/false），`false` 同时表示「不可下载」与「未在探测范围」 | 三态：`true` 可下载、`false` 明确不可下载、`NULL` 未命中允许探测来源故未检测 |

新增配置项：

| 配置项                                 | 类型           | 来源            | 约束                                                                  |
| -------------------------------------- | -------------- | --------------- | --------------------------------------------------------------------- |
| `artifact-probe.allowed-host-suffixes` | `List<String>` | Nacos，逗号分隔 | 必填，仓内无 yml 默认值；缺失会导致 `@Value` 注入失败（应用启动失败） |

## 5. 性能设计

- **DNS 解析次数增加**：探测链路与下载链路在校验阶段与建连前 `SafeDns.lookup` 各解析一次，且 `getAllByName` 返回全部记录，解析开销高于单次 `getByName`；未引入 DNS 缓存。
- **连接复用**：OkHttp 客户端为单例（`DEFAULT_PROBE_CLIENT` / `DOWNLOAD_CLIENT` / `SAFE_CLIENT`），复用连接池。
- **超时收紧**：探测 connect 5s / read 10s；下载 connect 5s / read 10s / call 60s，异常网络下请求快速失败。
- **内存上限**：下载 `contentLength` 已知且超 10MB 直接拒绝；长度未知时按 8KB 分块累计并在超限时立即中断，避免一次性读入。
- **探测多一次 HEAD**：405/401 时降级 GET（带 `Range: bytes=0-0`），仅在必要时发生。
- 未做性能基准测试，上表均为设计侧结论，无量化数据。

## 6. API接口设计

对外 HTTP 接口无变更：两个 PR 仅调整服务端出站请求策略与内部方法契约，Controller 与请求/响应 DTO 未改动。

内部方法签名变化：

| 位置                                               | 变更前                           | 变更后                                               |
| -------------------------------------------------- | -------------------------------- | ---------------------------------------------------- |
| `SecOptionScanServiceImpl#checkDownloadAccessible` | `Boolean`                        | `Optional<Boolean>`（empty = 未检测）                |
| `HttpRequestUtil`                                  | 仅 `sendRequest`                 | 新增 `sendRequestSafely`；抽出私有 `doSend`          |
| `PipelineEventConsumer`                            | 直接 `RestTemplate.getForObject` | 私有 `downloadText` / `readLimited` / `normalizeUrl` |
| `SafeRequestUtils`                                 | 前缀黑名单判定                   | 新增 `isHostAllowed` / `isRestrictedNetworkAddress`  |
| `SafeDns`                                          | sec-option 内嵌私有类            | 公共类，新增 `verifyLiteralHost` 与 `Scope`          |

## 7. 安全设计

### 7.1 已落地的防御

- 协议白名单：仅 `http` / `https`，阻断 `file:` / `jar:` / `ftp:` 等；
- 主机白名单（探测链路）：后缀 label 边界匹配，禁止 userinfo 与非默认端口，拒绝 IPv6 字面量主机；
- 地址判定：CIDR + 内置谓词，覆盖 IPv4 保留段、IPv6 保留段与三类内嵌 IPv4；
- 解析期拦截：`SafeDns` 对全部解析结果逐个校验，消除校验/建连之间的 DNS rebinding；
- IP 字面量补位：`verifyLiteralHost` 覆盖 OkHttp 不走 `Dns` 的绕过点；
- 重定向禁用：探测与下载客户端均不跟随 3xx，避免跳转绕过；
- 资源上限：响应体 10MB、URL 长度 2048，分块读取超限即中断；
- 日志脱敏：URL 仅保留 host:port，避免 OBS 签名凭证落日志；
- 返回契约统一：`doSend` 的 `IOException` 与 `IllegalArgumentException` 均返回 500 结构体，不向调用方抛裸异常。

### 7.2 残留风险

- 白名单后缀为配置驱动，若 Nacos 配置过宽（如配 `com` 或 `io`），白名单实际失效；
- `SafeDns` 未缓存解析结果，若上游 DNS 本身被污染，校验与建连两次解析仍可能得到不同结果（范围已收窄但未彻底消除）；
- 探测链路的 `SafeDns` 与下载链路的 `SafeDns` 为两套实现，行为口径需分别维护；
- `METADATA_ONLY` 放行 RFC1918，若 webhook 指向内网非元数据服务，仍可在内网发起请求（属设计取舍）；
- 未纳入本次范围：出站请求的 URL 来源若本身经过二次拼接（如 base + path），拼接后的校验依赖调用方正确传入。

### 7.3 已知取舍与功能风险

- **`followRedirects(false)`**：原 `RestTemplate` 跟随 3xx，现在 OBS/网关若返回 302 会直接失败，表现为「测试用例结果 / UT 结果 / 构建产物为空」且不抛错，日志特征 `Unexpected HTTP status: 302`。
- **`MAX_DOWNLOAD_BYTES = 10MB`**：用例数量多的测试结果 JSON 可能超限，日志特征 `Response body too large`。
- **`MAX_URL_LENGTH = 2048`**：带长签名的 OBS 预签名 URL 可能被丢弃，日志特征 `Discard abnormal url, length: N`。
- **`sendRequestSafely` 采用 `METADATA_ONLY`**：允许 RFC1918，但拒绝 `127.0.0.1` / `localhost` / `169.254.x.x` / `100.64/10`；若流水线 webhook 地址为回环或链路本地地址，会返回 `ApiResponse(500, "")`，表现为流水线静默不触发，日志特征 `Request rejected by SSRF policy`。
- **新增必填配置 `artifact-probe.allowed-host-suffixes`**：缺失会导致 `@Value` 注入失败（应用启动失败），部署前必须在 Nacos 配置。
- **`package_download_accessible` 出现 NULL 语义**：前端需按「未检测」处理而非「不可下载」。
