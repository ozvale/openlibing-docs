# go-purl-ssrf-hardening — NOTICE Go purl 源码仓库还原 SSRF 加固（#97）

## 需求背景

- Issue：[#97](https://gitcode.com/openlibing/openlibing-sca/issues/97)（closed）
- 漏洞编号 `argus-openlibingsca-20260928173548-025`，中危，CWE-918（SSRF），来源 Argus 报告
  `reports/argus-openlibingsca-20260928173548-025.md`
- 报告定位：`src/main/java/com/openlibing/sca/dm/util/packageurl/BasePackageUrlResolver.java:208`
  （`httpGet`，当前实现位于同类 L213-L251）

事实与根因（issue 描述 + 当前代码核实）：

1. `BasePackageUrlResolver#httpGet` 直接使用 `java.net.http.HttpClient` 发起 GET，
   `followRedirects(HttpClient.Redirect.ALWAYS)`，未调用项目内已有的
   `com.openlibing.sca.analysis.utils.SsrfsafeUrlUtil#validateUrl`；重定向目标同样不校验，
   且允许 https → http 跨协议降级。
2. `GoPackageUrlResolver#queryGoImportSourceRepo`（当前 L390）以
   `"https://" + modulePath + "?go-import=1"` 构造出站 URL，`modulePath` 来源于用户提交/补充的
   purl，可注入内网 IP 或任意域名（如 `pkg:golang/169.254.169.254/x`）。
3. NOTICE 合并链路 `ProjectNoticeScanExecutor#mergeAndUpload`（L1375）→
   `PackageUrlResolverComposite#toOfficialUrl`（L84）→ `GoPackageUrlResolver#purlToSourceRepoUrl`
   （L314）不经过 `ProjectNoticeScanExecutor#isUrlSafe`（该检查仅覆盖 scheme 与字符白名单），
   恶意 purl 可直接到达未防护的 HTTP sink。
4. 触发者不需要管理员权限：具备 `startScan` / `supplementNotice` 调用权限的认证用户，
   通过 SBOM 提交或人工补充接口即可触发；影响面为服务端可达的内网服务、云元数据端点
   （169.254.169.254 IMDS）以及 DNS rebinding 跳板（盲 SSRF，响应体仅局部回显）。

## 功能描述

**做什么**

1. 出站单点收口：`BasePackageUrlResolver#httpGet` 在发请求前调用
   `SsrfsafeUrlUtil.validateUrl(url)`，覆盖协议白名单（http/https）、localhost、
   loopback / anyLocal / siteLocal / linkLocal 及特殊 IPv4 网段。
2. 重定向改造：`Redirect.ALWAYS` 改为 `Redirect.NEVER`，改为手动逐跳跟随
   （`MAX_QUERY_REDIRECT_HOPS = 5`，状态码 301/302/303/307/308），每跳重新
   `validateUrl`；相对 `Location` 以当前跳地址为基准 `URI.resolve`，避免首跳换域后错拼回初始 host。
3. 抽出 `sendQueryGet`（复用 `sca.notice.download.queryTimeoutSeconds`，默认 5 秒）与
   `isRedirectStatus`；最终状态非 200 时抛 `IllegalStateException`，异常信息同时包含初始
   `url` 与 `finalUrl`。
4. Go module host 结构化预检：`GoPackageUrlResolver#extractModuleHost` 提取首段，
   要求含 `.` 且不匹配 `IPv4 字面量`（`IPV4_HOST_PATTERN`），不满足时打印 WARN 并返回 null，
   保证 go-import 兜底零出站。

**不做什么**

- 不修改下载链路 `ProjectNoticeScanExecutor#doDownload` 的既有 SSRF 防护（属 #105 整改范围，
  本目录仅对齐其跳数上限与逐跳校验写法）。
- 不做校验结果与建连的地址 pinning（TOCTOU / DNS rebinding 闭环见 #143，
  目录 `ssrf-dns-rebinding-pinning`）。
- 未对 Go module host 实施托管域白名单（issue #133 建议的 github.com / golang.org / gitlab.com 白名单），
  改为结构化拒绝 IP 字面量与单标签 host（见 design D5，偏差说明）。
- 不新增配置项，不调整对外接口契约。

## 验收标准

- [x] `httpGet` 出站前调用 `SsrfsafeUrlUtil.validateUrl`（L218），自动重定向关闭
      （L222 `Redirect.NEVER`）
- [x] 重定向逐跳复核：循环 L236-L245，每跳在 `sendQueryGet` 前调用
      `validateUrl(currentUrl)`（L242），跳数上限 5（L43）
- [x] `pkg:golang/169.254.169.254/x` 与单标签 host 在解析阶段零 go-import 出站，
      并保持原 purl 作为唯一候选（单测
      `resolve_versionlessPurl_ipModuleHost_rejectedWithZeroGoImportOutbound`、
      `resolve_versionlessPurl_singleLabelHost_rejectedWithZeroGoImportOutbound`）
- [x] `httpGetText` 对 `https://169.254.169.254/...`、`https://10.0.0.1/...`、
      `https://localhost/...` 在出站前抛 `IllegalArgumentException`（3 个单测）
- [x] 合并链路（`mergeAndUpload` → `toOfficialUrl`）与无版本兜底链共用同一 `httpGet`，
      静态检索确认 packageurl 包内无其他直接 HttpClient 出站点
- [ ] 部署环境端到端验证：真实恶意 purl 走 NOTICE 合并/补充接口未见异常请求
      （本轮未覆盖：回溯文档阶段未部署环境）
- [ ] `mvn test` 全量回归结果（本轮未执行，结果未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`dm` 模块 `util/packageurl` 包；
  `BasePackageUrlResolver`、`GoPackageUrlResolver` 及其单测。
- 接口：无路径/参数变化；含内网或恶意 host 的 purl 由"发起请求"变为"查询失败并回退"
  （保持原 purl 或 proxy zip 候选）。
- 配置：无新增；沿用 `sca.notice.download.queryTimeoutSeconds`。
- 数据模型 / schema：无变化。
- 跨仓：无；spec 文档归档 `openlibing-docs`，代码改动仅在本仓。
