# security-ssrf-guard — 实现任务

## 进度: 18/18 complete

- [x] Task 1 — `SafeRequestUtils` 以 CIDR 表替换字符串前缀黑名单
- [x] Task 2 — 重写 `isInternalAddress(String)` 为全记录遍历
- [x] Task 3 — 新增 `isInternalAddress(InetAddress)` 与 `CidrBlock`
- [x] Task 4 — 新增 `isHostAllowed` 主机白名单
- [x] Task 5 — `SSRF_FORBIDDEN_HOSTS` 改为不可变集合
- [x] Task 6 — sec-option 新增 `artifact-probe.allowed-host-suffixes` 配置
- [x] Task 7 — sec-option 新增 `DEFAULT_PROBE_CLIENT` 与内嵌 `SafeDns`
- [x] Task 8 — `checkDownloadAccessible` 改 `Optional<Boolean>` 并切 OkHttp
- [x] Task 9 — `reportScan` 未命中白名单落 NULL
- [x] Task 10 — PR 631 补测 `SafeRequestUtilsTest` / `SecOptionScanServiceImplTest`
- [x] Task 11 — 新增公共 `SafeDns`（`Scope` / `NUMERIC_HOST` / `verifyLiteralHost`）
- [x] Task 12 — `SafeRequestUtils` 新增保留网段判定
- [x] Task 13 — `HttpRequestUtil` 抽出 `doSend` 并新增 `sendRequestSafely`
- [x] Task 14 — `PipelineStartEventHandler` 回调切到 `sendRequestSafely`
- [x] Task 15 — `PipelineEventConsumer` 新增下载客户端与下载方法
- [x] Task 16 — 三处下载调用改造、fastjson2 解析与 URL 脱敏
- [x] Task 17 — PR 639 补测四组测试类
- [x] Task 18 — `artifact-probe.allowed-host-suffixes` 改为空默认值并降级（已在 `!639` 分支完成）

## 详细任务

### Task 1 — `SafeRequestUtils` 以 CIDR 表替换字符串前缀黑名单

- 文件：`src/main/java/com/openlibing/cicd/common/utils/SafeRequestUtils.java`
- 改动：删除 `SSRF_INTERNAL_HOST_PREFIXES`；新增 `INTERNAL_IPV4_CIDRS`（0.0.0.0/8、10.0.0.0/8、100.64.0.0/10、127.0.0.0/8、169.254.0.0/16、172.16.0.0/12、192.0.0.0/24、192.0.2.0/24、192.168.0.0/16、198.18.0.0/15、198.51.100.0/24、203.0.113.0/24、224.0.0.0/4、240.0.0.0/4）、`INTERNAL_IPV6_CIDRS`（::/128、::1/128、100::/64、2001::/32、2001:2::/48、2001:20::/28、2001:db8::/32、3fff::/20、fc00::/7、fe80::/10、ff00::/8）、`NAT64_WELL_KNOWN_PREFIX = 64:ff9b::/96`
- 验证：内网与保留网段地址判定为拒绝；公网地址判定为放行

### Task 2 — 重写 `isInternalAddress(String)` 为全记录遍历

- 文件：`SafeRequestUtils.java`
- 改动：先用 `normalizeHostForResolution` 去除 IPv6 方括号与 `%zone`，再用 `InetAddress.getAllByName` 遍历全部 A/AAAA 记录，任一命中即拒；不再用字符串前缀兜底
- 验证：单条内网记录与「首条公网、后续内网」的多记录场景均被拒绝

### Task 3 — 新增 `isInternalAddress(InetAddress)` 与 `CidrBlock`

- 文件：`SafeRequestUtils.java`
- 改动：内置谓词（anyLocal / loopback / linkLocal / siteLocal / multicast）+ CIDR 匹配；16 字节地址经 `extractEmbeddedIpv4` 展开 IPv4 映射（`::ffff:0:0/96`）、NAT64（`64:ff9b::/96`）、6to4（`2002::/16` 取第 2–5 字节）后递归判定；新增内部类 `CidrBlock` 做字节级位掩码 `contains`
- 验证：三类内嵌 IPv4 的内网地址均被识别

### Task 4 — 新增 `isHostAllowed` 主机白名单

- 文件：`SafeRequestUtils.java`
- 改动：空 URL 或空列表返回 `false`；要求 `isSafeProtocol`；禁止 URL userinfo；端口必须等于协议默认端口（https→443，http→80）；`getHost()` 不得以 `[` 开头；后缀按 label 边界匹配（`equals` 或 `endsWith("." + suffix)`）
- 验证：白名单含 `gitcode.com` 时 `api.gitcode.com` 命中、`evilgitcode.com` 不命中

### Task 5 — `SSRF_FORBIDDEN_HOSTS` 改为不可变集合

- 文件：`SafeRequestUtils.java`
- 改动：`HashSet` 改为 `Set.of("localhost","ip6-localhost","ip6-loopback")`
- 验证：三个主机名均被拒绝，且集合不可被运行时修改

### Task 6 — sec-option 新增 `artifact-probe.allowed-host-suffixes` 配置

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImpl.java`
- 改动：新增 `@Value("${artifact-probe.allowed-host-suffixes:}") private List<String> allowedHostSuffixes;`，Nacos 逗号分隔，仓内不提供 yml 默认值（空默认值由 Task 18 补齐）
- 验证：配置存在时列表正确注入；配置缺失时注入为空集合，`isHostAllowed` 返回 false，降级为跳过探测、落 NULL，应用可正常启动

### Task 7 — sec-option 新增 `DEFAULT_PROBE_CLIENT` 与内嵌 `SafeDns`

- 文件：`SecOptionScanServiceImpl.java`
- 改动：OkHttpClient，connect 5s / read 10s、`followRedirects(false)`、`followSslRedirects(false)`、`dns(new SafeDns(Dns.SYSTEM))`；保留可替换字段 `probeClient` 供单测指向本地服务；新增 `static final class SafeDns implements Dns`，`lookup` 结果任一为内网即抛 `UnknownHostException("Internal address rejected: " + hostname)`
- 验证：单测用 `probeClient` 指向本地服务；`SafeDns` 对内外网域名行为符合预期

### Task 8 — `checkDownloadAccessible` 改 `Optional<Boolean>` 并切 OkHttp

- 文件：`SecOptionScanServiceImpl.java`
- 改动：返回类型 `Boolean` → `Optional<Boolean>`；判定顺序为空 URL→false、非 http/https→false（warn）、`!isHostAllowed`→empty（info 日志 `Skip accessibility check for non-allowlisted host`）、`isInternalAddress`→false（warn）、随后 HEAD（405/401 降级 GET）；`checkAccessibleByHead` / `checkAccessibleByGet` 改用 `probeClient.newCall(...)` + try-with-resources，可达判定为 `status >= 200 && status < 400`，GET 保留 `Range: bytes=0-0`，新增 `catch (IllegalArgumentException)` warn 后返回 `false`
- 验证：`SecOptionScanServiceImplTest` 覆盖空 URL、非 http、非白名单、内网、白名单公网地址，以及 HEAD/GET 状态码映射与不跟随重定向

### Task 9 — `reportScan` 未命中白名单落 NULL

- 文件：`SecOptionScanServiceImpl.java`
- 改动：`saveScanRecord(request, json, accessible.orElse(null))`，未命中白名单时 `package_download_accessible` 为 NULL（未检测），不再写 `false`
- 验证：非白名单地址的扫描记录中该字段为 NULL

### Task 10 — PR 631 补测

- 文件：`src/test/java/com/openlibing/cicd/common/utils/SafeRequestUtilsTest.java`（+126 行）、`src/test/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImplTest.java`（+156 行）
- 改动：`SafeRequestUtilsTest` 覆盖内网/保留网段参数化、公网地址、非点分 IPv4（`http://0x7f000001/x` 与 `http://0177.0.0.1/x` 的 `isInternalAddress` 返回 false，`http://2130706433/x` 返回 **true**——`true` 表示判定为内网并拒绝，属 fail-closed；三者实际拦截口径见 design §7.4）、IPv6 zoneId 归一化（`http://[fe80::1%25eth0]/x`）、`isHostAllowed` 后缀边界与空白名单；`SecOptionScanServiceImplTest` 覆盖探测判定矩阵、`SafeDns` 内外网行为
- 验证：两个测试类全部用例通过

### Task 11 — 新增公共 `SafeDns`

- 文件：`src/main/java/com/openlibing/cicd/common/utils/SafeDns.java`（新增）
- 改动：`enum Scope { INTERNAL, METADATA_ONLY }`（INTERNAL 拒绝全部内网/保留地址；METADATA_ONLY 只拒绝回环、链路本地、组播与保留网段 0/8、100.64/10、127/8、169.254/16、192.0.0/24，放行 RFC1918）；`NUMERIC_HOST` 正则只认纯数字形态主机（点分十进制、整数形式、`0x` 十六进制）；`lookup` 逐个校验解析结果；`static verifyLiteralHost(url, scope)` 处理 IP 字面量主机
- 验证：`SafeDnsTest` 通过，含 `cafe.de` 不被误判为 IP 字面量

### Task 12 — `SafeRequestUtils` 新增保留网段判定

- 文件：`src/main/java/com/openlibing/cicd/common/utils/SafeRequestUtils.java`
- 改动：新增 `RESTRICTED_IPV4_CIDRS`（0.0.0.0/8、100.64.0.0/10、127.0.0.0/8、169.254.0.0/16、192.0.0.0/24）与 `isRestrictedNetworkAddress(InetAddress)`：IPv4 直接 CIDR 匹配，IPv6 先展开内嵌 IPv4（映射 / NAT64 / 6to4）再递归判定，`null` 视为命中
- 验证：`SafeDnsTest` 的保留网段与内嵌地址用例通过

### Task 13 — `HttpRequestUtil` 抽出 `doSend` 并新增 `sendRequestSafely`

- 文件：`src/main/java/com/openlibing/cicd/common/utils/HttpRequestUtil.java`
- 改动：抽出私有 `doSend(OkHttpClient, method, url, body, headerMap)`；新增 `sendRequestSafely`（先 `SafeRequestUtils.isSafeProtocol`，再 `SafeDns.verifyLiteralHost(url, METADATA_ONLY)`，通过后走 `SAFE_CLIENT = CLIENT.newBuilder().dns(new SafeDns(Dns.SYSTEM, Scope.METADATA_ONLY))`）；`doSend` 新增 `catch (IllegalArgumentException)` 返回 `ApiResponse(500, "请求错误")`，与 IOException 分支的 `ApiResponse(500, "连接失败")` 同契约；`sendRequest` 行为不变
- 验证：`HttpRequestUtilTest`（+56 行）通过，原 `sendRequest` 用例无回归

### Task 14 — `PipelineStartEventHandler` 回调切到 `sendRequestSafely`

- 文件：`src/main/java/com/openlibing/cicd/business/listener/PipelineStartEventHandler.java`
- 改动：`runPipeline`（约 683–687 行）中 `HttpRequestUtil.sendRequest` 改为 `sendRequestSafely`
- 验证：`PipelineStartEventHandlerTest`（+33 行）通过；webhook 为目标地址时正常回调

### Task 15 — `PipelineEventConsumer` 新增下载客户端与下载方法

- 文件：`src/main/java/com/openlibing/cicd/business/listener/PipelineEventConsumer.java`
- 改动：新增 `DOWNLOAD_CLIENT`（connect 5s / read 10s / call 60s、不跟随 HTTP 与 SSL 重定向、`dns(new SafeDns(Dns.SYSTEM))`）；常量 `MAX_DOWNLOAD_BYTES = 10MB`、`MAX_URL_LENGTH = 2048`；新增 `downloadText(url)`（协议白名单 + `SafeDns.verifyLiteralHost(url, INTERNAL)` + 非法 URL 转 IOException + 非 2xx 或空 body 抛异常 + contentLength 超限直接拒 + 长度未知走 `readLimited`）、`readLimited(ResponseBody, url)`（8KB 分块累计，超限立即中断）、`normalizeUrl(rawUrl)`（trim，空或超长返回空串，超长打 warn `Discard abnormal url`）
- 验证：`PipelineEventConsumerImplTest` 覆盖下载成功、非 2xx、响应体超限、非 http 协议

### Task 16 — 三处下载调用改造、fastjson2 解析与 URL 脱敏

- 文件：`src/main/java/com/openlibing/cicd/business/listener/PipelineEventConsumer.java`
- 改动：`mergeToObsProducts`、`analyzeLatestTestCasesResult`、`processUtResult` 由 `RestTemplate.getForObject` 改为 `downloadText`；构建产物 JSON 由 Spring 消息转换器改为 `JSON.parseObject`（fastjson2）；日志中所有 URL 统一经 `SafeRequestUtils.maskUrl` 脱敏，只保留 host:port
- 验证：`PipelineEventConsumerImplTest`（+160 行）通过；日志中不出现完整签名 URL

### Task 17 — PR 639 补测四组测试类

- 文件：`src/test/java/com/openlibing/cicd/common/utils/SafeDnsTest.java`（新增约 190 行）、`src/test/java/com/openlibing/cicd/common/utils/HttpRequestUtilTest.java`（+56 行）、`src/test/java/com/openlibing/cicd/business/service/impl/PipelineEventConsumerImplTest.java`（+160 行）、`src/test/java/com/openlibing/cicd/business/listener/PipelineStartEventHandlerTest.java`（+33 行）
- 改动：`SafeDnsTest` 覆盖字面量主机、内网/保留网段、IPv4 映射/NAT64/6to4 内嵌、`METADATA_ONLY` 放行 RFC1918
- 验证：四个测试类全部用例通过

### Task 18 — 探测白名单配置降级

- 文件：`src/main/java/com/openlibing/cicd/business/service/impl/SecOptionScanServiceImpl.java`
- 改动（已完成，提交在 `!639` 分支 `fix/security-vuln-489-ssrf-guard`）：`@Value("${artifact-probe.allowed-host-suffixes}")` 改为 `@Value("${artifact-probe.allowed-host-suffixes:}")`，空列表时 `checkDownloadAccessible` 直接返回 `Optional.empty()`，经 `saveScanRecord(..., accessible.orElse(null))` 落 NULL，避免配置漏配导致应用启动失败。
- 验证方式：`mvn -DskipTests compile` 通过；`isHostAllowed` 对 null/空列表返回 false（已有单测覆盖），配置缺失时跳过探测而非启动失败。
- 归属说明：该配置行由 PR `!631`（`fix_ssrf_probe_allowlist`）引入，分支位于其他开发者 fork，故本修复落在堆叠 PR `!639` 上。
