# 开源通告扫描包下载解析增强与安全加固 — 技术设计

## 方案概述

在 notice-scan 链路上补齐 cargo/nuget 两个生态的 purl 解析与下载能力，将人工补录下载地址与 SBOM 原始地址分离（新增 `manual_download_url` 列），并在"受理入口 → 下载 sink → 重定向链"三层强制 SSRF 校验，同时对 startScan 加鉴权、对人工补充内容做注入中和，集中修复 #99/#100/#105/#118 四个安全问题。

## 包解析与下载链路

```
SBOM purl (pkg:cargo/... | pkg:nuget/... | pkg:npm/...)
  → PackageUrlResolver 展开 http(s) 下载候选（可多个，按序回退）
      Cargo: static.crates.io 确定性直链 + rsproxy.cn 镜像候选（可配置）
             无版本号 → crates.io API max_version 后构造
      Nuget:  无版本号 → 最新 stable；下载末段无归档扩展名 → 补 .nupkg
      Npm:    scoped 包 @ 双重编码修复（循环解码 ≤3 轮，+ 保留为 %2B）
  → ProjectNoticeScanExecutor.downloadCandidateWithRetry
      → doDownload: SSRF 校验 → 手动逐跳重定向（≤5 跳，逐跳校验）
                    → 下载到 .part 临时文件 → 成功后改名 → extractcode 解压
```

## 关键决策

1. **cargo 走确定性直链而非页面 API 抓取**：crates.io 的包文件下载地址是确定性的（`https://static.crates.io/crates/<crate>/<crate>-<version>.crate`，crates.io 仅 302 跳转该地址），直接构造 static 直链，少一次外部依赖；crate 名注册即全小写，无版本号 purl 经 crates.io API（`/api/v1/crates/<crate>`）取 `max_version`。
2. **cargo 镜像候选可配置、失败自动回落**：境外网络对 static.crates.io 的 TLS 握手可能被阻断，新增 `sca.notice.download.mirror.cargo.download-template`（默认 rsproxy.cn，配置为空禁用）生成镜像候选；镜像失败由下载执行器自动回落官方候选。
3. **补扩展名只按已知生态白名单，不做通用识别**：`KNOWN_ARCHIVE_EXTENSIONS` 覆盖本服务实际下载的归档生态（jar/tgz/whl/crate/nupkg/rpm 等），`ECOSYSTEM_DEFAULT_ARCHIVE_EXTENSION` 仅 nuget → `.nupkg`（NuGet v2 地址末段是版本号，extractcode 按扩展名识别归档失败会静默跳过解压，ossinfo_extraction 随即 exit 1）。
4. **`manual_download_url` 与 `download_url` 职责分离**：`download_url` 恒为 SBOM 原始地址（补录不再覆盖），生效地址 = 补录地址非空优先；跨扫描继承匹配键升级为 `(software_name, version, download_url)`；旧数据兼容——历史 `manual_url=1` 行的补录地址存于 `download_url`，命中后回落取 `latest.getDownloadUrl()` 作为补录地址，避免"manualUrl=1 但补录地址为空、生效地址退回坏地址"的不一致态。
5. **SSRF 三层防御**（受理入口快速失败 + sink 强制校验 + 重定向逐跳校验）：
   - supplement 受理阶段对 http(s) downloadUrl 提前 `validateUrl`，拒绝不写库不触发异步下载；DNS 解析失败不作为受理拒绝条件（内网隔离环境合法域名可能暂时解析不到），延迟到 sink 兜底。
   - `doDownload`/`doGitDownload` 是服务端主动外联 sink，统一强制校验，拒绝 loopback/内网/link-local（含云元数据 169.254.169.254）与非 http(s) 协议。
   - `HttpClient.Redirect.NEVER` 关闭自动重定向，手动逐跳跟随（上限 5 跳，防重定向环），每一跳目标重新校验，防止公网 URL 经 302 跳内网绕过；相对 `Location` 以当前跳地址为基准 `resolve`，避免首跳到 CDN 后相对路径被错拼回初始地址。
6. **内容注入双层中和**（#100）：Jsoup `Safelist.none()` 置空清洗剥 HTML（`prettyPrint(false)` 保留换行不压缩 NOTICE 文本）+ 65536 字符上限防超大载荷；组装后正文中行首 `Software: ` 条目头伪造统一改写为 `> ` 引用行——文本保留可见、可审计、不删改，但不再构成条目边界。
7. **白名单端点 fail-closed + 实时读取**：`sca.notice.community.display.whitelist` 配置缺省/为空/未命中均返回不可展示；经 `Environment` 按请求实时读取，Nacos 变更无需重启生效；`community` 参数可选，为空返回不可展示。
8. **临时文件落盘**：下载先写同目录 `.part` 文件，成功后改名到目标，避免进程中断留下半截归档被 extractcode 误处理。
9. **导出跳过名单防御性拷贝**：`ProjectNoticeExportVO.skippedProductNames` 在 VO 内做防御性拷贝（`8b275fc7`），避免外部修改内部列表。

## 涉及文件

| 文件                                                          | 操作      | 说明                                                                                                   |
| ------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------ |
| `dm/util/packageurl/CargoPackageUrlResolver.java`             | 新增      | pkg:cargo 解析（static 直链 + rsproxy 镜像 + API 取版本）                                              |
| `dm/util/packageurl/NugetPackageUrlResolver.java`             | 新增      | pkg:nuget 解析（最新 stable、无扩展补 .nupkg 配合）                                                    |
| `dm/util/packageurl/NpmPackageUrlResolver.java`               | 修改      | scoped purl `@` 双重编码修复                                                                           |
| `dm/util/ProjectNoticeScanExecutor.java`                      | 修改      | 下载 sink SSRF 校验、手动逐跳重定向、.part 临时文件、生态补扩展名                                      |
| `dm/util/NoticeMerger.java`                                   | 修改      | `neutralizeInjectedHeaders` 条目头中和、license 占位符不去重                                           |
| `dm/service/impl/ProjectNoticeScanServiceImpl.java`           | 修改      | startScan 鉴权、supplement 受理期 SSRF 预检 + content 上限、补录地址兼容回落、展示生效地址、白名单检查 |
| `dm/controller/ProjectNoticeScanController.java`              | 修改      | 新增 `GET /display/config`；exportBatch 返回 skippedProductNames                                       |
| `analysis/entity/TblProjectNoticeScanDetail.java`             | 修改      | 新增 `manualDownloadUrl` 字段与 `getEffectiveDownloadUrl`                                              |
| `analysis/entity/vo/ProjectNoticeExportVO.java`               | 修改      | 新增 `skippedProductNames`（防御性拷贝）                                                               |
| `dm/dao/TblProjectNoticeScanDetailMapper.java`（+XML）        | 修改      | 补录地址持久化与继承匹配键升级                                                                         |
| `db/changelog/mysql/20261024/add-...-manual-download-url.xml` | 新增      | Liquibase 加列（preConditions MARK_RAN + rollback）                                                    |
| `db/changelog/db.changelog.xml`                               | 修改      | 引入新 changelog                                                                                       |
| 测试（8 个文件，约 1200 行）                                  | 新增/修改 | resolver/merger/executor/service/processor/controller 覆盖                                             |

## 配置项

| 配置键                                               | 默认            | 说明                                     |
| ---------------------------------------------------- | --------------- | ---------------------------------------- |
| `sca.notice.community.display.whitelist`             | 空（全不展示）  | Nacos 白名单，逗号分隔社区名，忽略大小写 |
| `sca.notice.download.mirror.cargo.download-template` | rsproxy.cn 模板 | cargo 镜像候选模板，配置为空禁用镜像     |

## 数据库变更

- `tbl_project_notice_scan_detail` 新增列 `manual_download_url VARCHAR(2048) NULL`（补录地址非空时下载与展示优先于 `download_url`），changeSet 含 `preConditions(MARK_RAN)` 幂等保护与 rollback。

## 风险与缓解

| 风险                                                             | 缓解                                                 |
| ---------------------------------------------------------------- | ---------------------------------------------------- |
| issue #103（CmdInjection 无超时）未随本 PR 交付（改动已 revert） | 已在 PR 描述遗留；需另行建 PR 交付，避免误认为已修复 |
| rsproxy 镜像不可用导致 cargo 下载失败                            | 镜像候选失败自动回落官方直链；镜像可经配置禁用       |
| 重定向上限 5 跳可能截断超长跳转链                                | 正常镜像链路 1-2 跳可达，5 跳足够且防重定向环        |
| 白名单配置错误导致 NOTICE 入口全量隐藏                           | fail-closed 语义明确；配置按请求实时读取，修正即生效 |
| 加列 changelog 在已有列环境重复执行                              | preConditions `columnExists → MARK_RAN` 幂等         |
| npm 循环解码可能过度解码                                         | 限定 ≤3 轮且收敛即停，`+` 强制保留为 `%2B` 不误展开  |

## 跨仓影响

- 无其他仓代码改动；前端需适配 `exportBatch` 响应新增的 `skippedProductNames` 字段与 `GET /display/config` 端点（控制 NOTICE 扫描入口展示）。
- 通告扫描结果经既有 NOTICE 合并/发布机制输出，格式兼容（中和改写仅影响条目边界解析，文本保留）。
