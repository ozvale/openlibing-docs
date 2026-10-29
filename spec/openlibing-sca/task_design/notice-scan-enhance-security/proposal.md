# 开源通告扫描（notice-scan）包下载解析增强与安全加固

## 需求背景

开源通告扫描链路存在两类问题：

**能力缺口**：SBOM 中 `pkg:cargo`、`pkg:nuget` 两类 purl 无对应解析器，通告扫描无法下载制品并生成 NOTICE；人工修正下载地址直接覆盖 `download_url`（SBOM 原始地址丢失），跨扫描继承与展示口径混乱；NuGet v2 下载地址末段是版本号、无归档扩展名，extractcode 按扩展名识别归档失败静默跳过解压，导致 nuget 包扫描全部失败；npm scoped 包 purl 中 `@` 被双重编码导致解析失败；批量导出跳过制品时前端无感知。

**安全问题**（来自安全 issue）：`ProjectNoticeScan startScan` 无身份与授权控制（#99，未授权触发扫描导致跨产品数据获取与资源滥用）；NOTICE 合并流程人工补充内容未转义，存储型内容注入（#100）；`supplement` 接口 `downloadUrl` 可驱动服务端访问云元数据与内网主机（#105、#118，CWE-918 SSRF）。

## 功能描述

### 功能增强

- 新增 `CargoPackageUrlResolver`（`pkg:cargo/<crate>@<version>`）：构造 `static.crates.io` 确定性下载直链；无版本号 purl 经 crates.io API 取 `max_version` 后构造；新增 rsproxy.cn 镜像候选（`sca.notice.download.mirror.cargo.download-template` 配置，默认 rsproxy.cn，配置为空禁用），镜像失败自动回落官方地址。
- 新增 `NugetPackageUrlResolver`（`pkg:nuget`）：无版本号 purl 优先取最新 stable 版本；下载执行器对无归档扩展名的 URL 按生态补默认扩展（nuget → `.nupkg`），使 extractcode 正常解压。
- 手动下载 URL 与 SBOM URL 分离：`tbl_project_notice_scan_detail` 新增 `manual_download_url` 列（Liquibase changelog，VARCHAR(2048)），`download_url` 恒为 SBOM 原始地址，下载/缓存/文档/展示按"生效地址"（补录地址非空优先，否则原始地址）取值；跨扫描继承匹配键升级为 `(software_name, version, download_url)`；兼容旧数据（历史 `manual_url=1` 行补录地址存于 `download_url` 的回落逻辑）。
- 下载先写同目录临时文件（`.part`）成功后再改名到目标，避免中断留下半成品文件。
- 批量导出 `exportBatch` 返回受理阶段跳过的制品名单 `skippedProductNames`，前端据此提示用户。
- 新增社区展示白名单端点 `GET /project/notice/scan/display/config`：读 Nacos 配置 `sca.notice.community.display.whitelist`（逗号分隔社区名，忽略大小写匹配），fail-closed（配置缺省/为空/未命中均不展示），按请求实时读取、Nacos 变更即生效。
- 修复 npm scoped purl `@` 双重编码：循环解码（≤3 轮，`+` 保留为 `%2B` 不误展开）。

### 安全加固

- `startScan` 调用方鉴权（Fixes #99）：仅 platform ops 或对应社区角色可触发扫描。
- NOTICE 合并内容注入中和（Fixes #100）：人工补充正文先经 Jsoup 白名单置空清洗（`Safelist.none()` + `prettyPrint(false)` 保留换行）剥除 HTML 并转义残留字符，限制单次补充 content ≤ 65536 字符；组装后正文中行首 `Software: ` 前缀（条目头伪造）统一改写为 `> ` 引用行（`neutralizeInjectedHeaders`），文本保留可见可审计但不构成条目边界；license 占位符（`[No license text available]`）不参与去重。
- SSRF 出口校验（Fixes #105、#118）：supplement 受理阶段对 http(s) `downloadUrl` 提前执行 `SsrfsafeUrlUtil.validateUrl`，拒绝 loopback/内网/link-local（含云元数据 169.254.169.254）与非 http(s) 协议，快速失败不写库不触发异步下载；DNS 解析失败不作为受理拒绝条件，交由下载 sink 兜底；下载执行器 `doDownload`/`doGitDownload`（服务端主动外联 sink）统一强制 SSRF 校验；HTTP 下载关闭自动重定向，改为手动逐跳跟随（上限 5 跳），每一跳目标重新过 SSRF 校验，相对 `Location` 以当前跳地址为基准解析。

### 范围说明（PR 描述与实际 diff 的差异）

- PR 描述提到"CmdInjection.runCmd 增加超时上限"（关联 #103），该改动曾在本分支实现（`a3676c2b`），后经 `d789657e` revert 移出本 PR，**最终 diff 中不包含 CmdInjection 改动**，issue #103 未由本 PR 交付，需另行处理。

## 验收标准

- [x] `pkg:cargo` / `pkg:nuget` 通告扫描可正常下载制品并生成 NOTICE（含 rsproxy 镜像回落、无版本号 purl 取最新版、nuget 补 `.nupkg`）。
- [x] 人工补录下载地址与 SBOM 原始地址分离，生效地址口径在下载/缓存/文档/查询一致；旧数据兼容回落不产生"manualUrl=1 但补录地址为空"的不一致态。
- [x] 未授权调用 `startScan` 被拒绝（platform ops / 社区角色校验）。
- [x] 人工补充内容经清洗与条目头中和后进入合并文档；超长 content（>65536）拒绝。
- [x] supplement 受理阶段拒绝内网/云元数据地址；下载 sink 对 loopback/内网/link-local 强制拒绝；302 跳转到内网地址被逐跳校验拦截。
- [x] 下载中断不留半成品目标文件（`.part` 临时文件机制）。
- [x] 批量导出返回 `skippedProductNames`。
- [x] 单元测试通过（Cargo/Nuget/Npm resolver、NoticeMerger、Executor、ServiceImpl、AsyncProcessor、Controller，测试约 1200 行）。
- [x] CI 流水线通过（标签 `ci-pipeline-passed`），PR 已合入。

## 影响范围

- 仅 `openlibing-sca` 仓：24 文件 +2149/−88（其中测试约 1200 行）。
- **DB 变化**：`tbl_project_notice_scan_detail` 新增 `manual_download_url VARCHAR(2048)` 列（Liquibase changelog `20261024_add_tbl_project_notice_scan_detail_manual_download_url`，含 preConditions MARK_RAN 与 rollback）。
- **新增对外端点**：`GET /project/notice/scan/display/config`。
- **行为变化**：`startScan` 增加鉴权（未授权调用从可用变为拒绝）；补录地址不再覆盖 `download_url`；导出响应新增 `skippedProductNames` 字段。
- **新增配置**：`sca.notice.community.display.whitelist`（Nacos）、`sca.notice.download.mirror.cargo.download-template`（默认 rsproxy.cn）。

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/353（`ms_notice` → `release_20261029`，已合入）
- 业务 Issue: Fixes openlibing/openlibing-sca#99、#100、#105、#118；#103（CmdInjection 超时）改动已 revert，未随本 PR 交付
