# go-purl-versionless-ssrf — 无版本 Go purl 兜底解析盲 SSRF 修复（#133）

## 需求背景

- Issue：[#133](https://gitcode.com/openlibing/openlibing-sca/issues/133)（closed）
- 来源：安全扫描报告 `openlibingsca-20261021164919-008`（2026-10-21 批次，人工确认为问题/未修复），
  中危，CWE-918（SSRF）
- 问题位置（issue 引用行号为当时版本）：
  - `GoPackageUrlResolver.java:380`（`queryGoImportSourceRepo` 出站拼接，当前实现 L390、拼接点 L400）
  - `BasePackageUrlResolver.java:209-213`（`httpGet`；当前 `httpGet` 位于 L213-L251，
    `followRedirects(ALWAYS)` 在修复前对应 L222 位置）

事实与根因（issue 描述 + 当前代码核实）：

1. 无版本 purl（`pkg:golang/...` 不带 `@version`）进入兜底链
   `resolveVersionlessOrInvalidPurl`（L209）→ `queryLatestVersion`（固定访问 proxy.golang.org）
   → 失败后 `resolveSourceRepoUrl`（L364）→ `queryGoImportSourceRepo`（L390）。
2. `queryGoImportSourceRepo` 直接以 `"https://" + modulePath + "?go-import=1"` 出站，
   `modulePath` 取自用户提交的 purl，可注入内网 IP / 任意域名（如 `pkg:golang/169.254.169.254/x`）。
3. 出站发生在**解析阶段**，早于下载阶段的 `ProjectNoticeScanExecutor#doDownload`，
   该处已有 `SsrfsafeUrlUtil`（L244、L565-L572）校验覆盖不到解析链路。
4. `Redirect.ALWAYS` 允许 https → http 跨协议降级；响应不回显（盲 SSRF），
   但可用于探测内网资产、触发内部 GET 接口副作用（如云元数据端点）。
5. 触发入口：`POST /project/notice/scan/supplement`（`ProjectNoticeScanController` L134）人工补充
   无版本 go purl。

## 功能描述

**做什么**

1. 解析阶段结构化拒绝：`queryGoImportSourceRepo` 在拼接 `metaUrl` 前调用 `extractModuleHost`
   （L426），满足任一条件即 WARN 并返回 null（零 go-import 出站）：
   - host 为 null
   - host 不含 `.`（单标签短主机名）
   - host 匹配 `IPV4_HOST_PATTERN = ^(\d{1,3}\.){3}\d{1,3}$`（纯 IPv4 字面量，含 169.254.169.254）
2. 出站统一防护：`BasePackageUrlResolver#httpGet` 首跳 `SsrfsafeUrlUtil.validateUrl`，
   `Redirect.NEVER` + 逐跳校验手动跟随（≤5 跳），与 issue 建议的
   "对齐 `ProjectNoticeScanExecutor#doDownload` 写法"一致。
3. 拒绝后保持原有回退语义：`resolveVersionlessOrInvalidPurl` 保持原 purl 作为唯一候选（L246-L249）；
   `toOfficialUrl` 链路（`purlToSourceRepoUrl` L323-L327）同样保持原 purl。
4. 回归测试：6 个用例覆盖 IP / 单标签零出站、toOfficialUrl 链路零出站、httpGet 对
   link-local / site-local / localhost 的出站前拒绝。

**不做什么**

- 未按 issue 修复建议 2 增加托管域白名单（github.com / golang.org / gitlab.com）。
  实际实现改为"拒绝 IP 字面量与单标签 host + 通用 SSRF 校验兜底"（偏差见 design D2/D5）。
- 不改造 `@latest` 查询（`https://proxy.golang.org/...` 为固定官方 host，非 SSRF 向量）。
- 不调整 supplement 接口契约、请求参数与受理流程。
- 不做 DNS 解析结果 pinning（#143）。
- 不修改下载阶段防护（#105）。

## 验收标准

- [x] `httpGet` 出站前调用 `SsrfsafeUrlUtil.validateUrl`，自动重定向关闭，
      逐跳手动跟随且每跳复核（L218、L222、L236-L245）
- [ ] `queryGoImportSourceRepo` 增加 module host 白名单：**未按建议实现**（本轮偏离）。
      等价防护为 IP 字面量 / 单标签 host 拒绝 + httpGet 解析校验兜底，见 design D5
- [x] `pkg:golang/169.254.169.254/x` 解析阶段被拒绝且零 go-import 出站
      （`resolve_versionlessPurl_ipModuleHost_rejectedWithZeroGoImportOutbound`：
      断言仅 `proxy.golang.org` 出站、候选为原 purl）
- [x] 单标签 host `pkg:golang/intranet-host/x` 零 go-import 出站
      （`resolve_versionlessPurl_singleLabelHost_rejectedWithZeroGoImportOutbound`）
- [x] github 模块正常解析路径不被破坏：既有用例
      `resolve_versionlessPurl_latestFail_githubModule_fallsBackToRepoUrl`、
      `toOfficialUrl_githubPurl_constructsReleasesTagUrl` 未修改且仍覆盖该路径
- [x] `toOfficialUrl` 链路对 IP host purl 不再发起 go-import 请求
      （`toOfficialUrl_versionlessIpHostPurl_keepsPurlWithoutGoImportOutbound`）
- [ ] 真实部署环境通过 supplement 接口端到端验证（本轮未覆盖）
- [ ] `mvn test` 全量回归（本轮未执行，结果未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`dm` 模块 `util/packageurl`（`GoPackageUrlResolver`、
  `BasePackageUrlResolver`）与对应单测。
- 接口：`POST /project/notice/scan/supplement` 契约不变；无版本 Go purl 在 host 结构非法或
  解析到内网时，解析结果回退为原 purl（下游报错更明确），不会静默发起外联。
- 配置：无新增；`queryTimeoutSeconds` 默认 5 秒。
- 数据模型 / schema：无变化。
- 跨仓：无；文档归档 `openlibing-docs`。
