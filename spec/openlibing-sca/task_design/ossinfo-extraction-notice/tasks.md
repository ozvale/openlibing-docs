# Tasks: 项目 NOTICE 扫描（ossinfo-extraction-notice）

> 任务清单基于 openlibing-sca `ms_notice` 分支的已交付实现（2026-08-31 对齐），替代早期单接口 `POST /open/ossinfo/notice` 版本的任务清单。

## Task 1: REST 接口层 ✅

**文件**: `dm/controller/ProjectNoticeScanController.java`

- [x] `@RestController` + `@RequestMapping("/project/notice/scan")`
- [x] `POST /start` → `startScan(ProjectNoticeScanStartPo)`，返回 `scanId`
- [x] `POST /release` → `saveOrUpdateRelease(ProjectNoticeScanReleasePo)`
- [x] `POST /query` → `queryScan(ProjectNoticeScanQueryPo)`，javadoc 说明返回状态字段
- [x] `POST /supplement` → `supplementScan(ProjectNoticeScanSupplementPo)`
- [x] 统一异常处理：`ScaException` 返回 errorCode/errorMsg/adviceMsg，通用异常记日志返回兜底文案

## Task 2: 请求/响应 DTO 与 VO ✅

**文件**: `analysis/entity/dto/ProjectNoticeScan*Po.java`、`analysis/entity/vo/ProjectNoticeScan*VO.java`

- [x] `ProjectNoticeScanStartPo`：仅 `productName`（软件清单由 SBOM 自动解析，不再由调用方传入）
- [x] `ProjectNoticeScanReleasePo`：`productName` + `releaseName`
- [x] `ProjectNoticeScanQueryPo`：`productName` + `releaseName`（至少传一个，服务层校验）
- [x] `ProjectNoticeScanSupplementPo`：`productName` + `supplements[]`（`SupplementItem`：softwareName/version/downloadUrl/content `@NotNull`）
- [x] `ProjectNoticeScanVO`：`productName`、`scanStatus`、`scanStatusName`、`mergedOssUrl`、`failedDetails`
- [x] `ProjectNoticeScanDetailVO`：`softwareName`、`version`、`downloadUrl`

## Task 3: 持久化层 ✅

**文件**: `analysis/entity/TblProjectNoticeScan(Detail).java`、`dm/dao/*Mapper.java`、`mapper/dm/*.xml`、`db/changelog/mysql/20260716/create-tbl-project-notice-scan.xml`

- [x] Liquibase 建表：总表（scan_id 唯一键，project_name/release_name/status 索引）+ 明细表（`(scan_id, software_name, version)` 唯一，`(software_name, version)` 索引供缓存查询）
- [x] 总表 Mapper：insert、selectByScanId、selectLatestByProjectName、selectLatestByReleaseName（ORDER BY create_time DESC LIMIT 1）、updateStatusByScanId、updateResultByScanId、updateReleaseNameById
- [x] 明细 Mapper：batchInsert、selectByScanId、selectCachedSuccess（跨扫描全局缓存：同名称+版本+地址的历史 SUCCESS 明细）、updateStatusById

## Task 4: 状态枚举 ✅

**文件**: `common/enums/ProjectNoticeScanStatus.java`、`common/enums/ProjectNoticeScanDetailStatus.java`

- [x] 扫描状态：PENDING(0) / PROCESSING(1) / SUCCESS(2) / FAILED(3)
- [x] 明细状态：PENDING(0) / SUCCESS(1) / FAILED(2)
- [x] `ProjectNoticeScanStatus.nameOf(Integer)`：null/非法值返回空串不抛错（兼容占位记录无状态场景）

## Task 5: 启动扫描 startScan 与 SBOM 解析 ✅

**文件**: `dm/service/impl/ProjectNoticeScanServiceImpl.java`

- [x] `@Transactional`：拉取失败/解析为空抛 `ScaException(60000)`
- [x] `openScanServiceImpl.getLicenseFromSbom(productName)` 获取 SBOM；日志仅记录长度（目录级 SBOM 可达数十 MB）
- [x] `parseSbomToDetails`：`downloadLocation` 有效（非空、非 `NOASSERTION`、非 `NONE`）→ 单条明细；否则展开 `externalRefs` 全部 `referenceLocator`
- [x] purl 解析 `parsePurlNameVersion`：剥离 `?qualifiers`/`#subpath`，name 取最后 `/` 之后、version 取 `@` 之后；循环 URL 解码最多 3 次（`+` 先转 `%2B` 保护）
- [x] 跨 package 按 `(softwareName, version)` 全局去重；version 空兜底 `NOASSERTION`
- [x] 落库 scan(PENDING) + 明细批量插入，事务内发布 `ProjectNoticeScanCreatedEvent`，返回 scanId

## Task 6: 事件投递与 MQ 拓扑 ✅

**文件**: `dm/event/ProjectNoticeScanCreatedEvent.java`、`dm/event/ProjectNoticeScanEventListener.java`、`common/config/rabbitmq/ProjectNoticeScanRabbitConfig.java`、`dm/service/impl/ProjectNoticeScanAsyncProcessor.java`

- [x] `@TransactionalEventListener(AFTER_COMMIT)` 事务提交后 `convertAndSend(scanId)`；发送失败仅记 ERROR（已知悬挂缺口）
- [x] `@QueueBinding` 内联声明 exchange/queue/binding（配置键带默认值），死信参数 `x-dead-letter-exchange=${spring.rabbitmq.sca.death_queue}` + `x-dead-letter-routing-key=death`
- [x] 独立容器工厂 `projectNoticeScanContainerFactory`：`AcknowledgeMode.MANUAL`、并发消费者 1/1；`@RabbitListener(concurrency="1")` 双保险
- [x] `onMessage` 手动 ack：成功 `basicAck`；`RuntimeException` → `basicNack(requeue=false)` 进死信

## Task 7: 异步处理主流程 processScan ✅

**文件**: `dm/service/impl/ProjectNoticeScanAsyncProcessor.java`

- [x] 幂等检查：仅处理 PENDING（兼容 status 为 null），防重投重复消费
- [x] scan → PROCESSING；逐明细处理，异常仅将该明细置 FAILED（error_msg 截断 1024）
- [x] 成功项 > 0 → `mergeAndUpload` → SUCCESS；合并失败 → FAILED("merge failed: ...")；全部失败 → FAILED("all software failed")
- [x] `updateResultByScanId` 回写状态/计数/地址/错误/完成时间
- [x] `finally` 兜底 `cleanupScanDir(scanId)`

## Task 8: 单包处理（缓存复用 + 生成上传）✅

**文件**: `dm/service/impl/ProjectNoticeScanAsyncProcessor.java`

- [x] 全局缓存：`selectCachedSuccess(name, version, url)` 命中则 `downloadObsTextByUrl` 复用，跳过下载与提取
- [x] 包目录 `{workdir}/projectNoticeScan/{scanId}/{name-version}`（`/` `\` `.` 替换为 `-`）
- [x] 下载 + 提取均记录耗时日志
- [x] 提取成功后立即 `cleanFile(packagePath)`；`uploadToObs` 在 `cleanDir` 之前（顺序约束）
- [x] objectKey：`{sanitize(productName)}/{sanitize(name)}-{sanitize(version)}-Readme.opensource`，同产品重扫同 key 覆盖
- [x] `finally` 清理 pkgDir

## Task 9: Executor 下载能力 ✅

**文件**: `dm/util/ProjectNoticeScanExecutor.java`

- [x] `isUrlSafe`：拦截 shell 元字符/路径穿越/空白字符
- [x] `PackageUrlResolverComposite.resolve` 多候选，按序尝试，全部失败抛错
- [x] git 仓库候选走 `doGitDownload`：剥离 query string，`git clone --depth 1`，`--branch {version}` 失败回退默认分支（回退前清理半成品）
- [x] HTTP 候选走 `doDownload`：connectTimeout 30s、读超时 10min、`followRedirects ALWAYS`、非 200 附响应体前 500 字符
- [x] `extractFileName` 从 URL 末段提取，保留原始压缩格式

## Task 10: Python 子进程执行 ✅

**文件**: `dm/util/ProjectNoticeScanExecutor.java`

- [x] 命令 `python[3] -m ossinfo_extraction -t -n -v -j`；参数过 `CmdInjection.checkCommand`
- [x] `-j`：`sca.notice.python.jobs` 可配，默认 CPU 核数、上限 8、下限 1
- [x] 超时 `sca.notice.python.timeoutMinutes`（默认 20），`waitFor` 到期 `destroyForcibly`
- [x] `ThreadPoolExecutor(2,2)` daemon 线程并行读 stdout/stderr（解死锁、超时生效）；每路仅保留尾部 500 行
- [x] 字符集 `sun.jnu.encoding` 回退 UTF-8；退出码非 0 / Readme 缺失均抛错并附输出
- [x] 产物定位 `packagePath.getParent()/Readme.opensource`（对齐 Python 默认 output_dir）
- [x] `finally`：ioService.shutdownNow + 进程存活强杀

## Task 11: purl 解析器体系 ✅

**文件**: `dm/util/packageurl/*.java`

- [x] 接口 `PackageUrlResolver`：`supports` / `resolve` / `toOfficialUrl`（default 委托基类）
- [x] `BasePackageUrlResolver`：共享 `decodePurlVersion`/`urlDecode`（`+` 转 `%2B` 保护）；镜像前缀剥离的默认 `toOfficialUrl`
- [x] Pypi @Order(10)：镜像 simple index（PEP 503）→ pypi.org JSON API → 原始兜底；支持 `pkg:pypi/<name>@<version>`；sdist 优先
- [x] Maven @Order(20)：`pkg:maven/` 前缀 + repo1.maven.org host 双识别；sources jar 优先、普通 jar 兜底
- [x] Npm @Order(30)：离线确定性构造 `/{name}/-/{basename}-{version}.tgz`；scoped 包去 scope 前缀；兼容字面 `@` 与 `%40`
- [x] Go @Order(40)：version 循环解码兼容双重编码；`toOfficialUrl` → GitHub release 页（go-import meta API）
- [x] CGit @Order(50)：识别 git 仓库 URL（`isGitRepoUrl` 供 Executor 分流）
- [x] Rpm @Order(60)：版本目录拼 `-LTS`；main/update source 标准路径候选（未实现 `toOfficialUrl`，下载表输出裸 purl——已知缺口）
- [x] Default @Order(MAX)：原始地址单候选兜底
- [x] `ResolvedUrl(s)` 候选模型：统一 镜像 → 官方 → 原始 顺序；`toOfficialUrl` 失败原样返回不阻断文档生成

## Task 12: NoticeMerger 合并文档 ✅

**文件**: `dm/util/NoticeMerger.java`

- [x] 头部：纯 Markdown 加粗（`**OPEN SOURCE SOFTWARE NOTICE**` / 说明段 / `**Warranty Disclaimer**` / `**Copyright Notice and License Texts**`），不含 HTML
- [x] License 去重：仅 `License: XXX` 紧接 `Full License Text:` 的块参与；重复标识符原文替换为 `Please see above`；块边界以下一个 `License:` 或 `================ Software:` 分隔行为止；其他形式 `License:` 行（如 "For details, see ..."）原样保留
- [x] 尾部：加粗 GPLv2 声明 + `| Software Name | Version | Download URL |` 表格（调用方已传官方地址）
- [x] 单元格转义：`|` → `\|`，换行 → 空格
- [x] 输出文件名 `open-source-notice-{sanitize(productName)}.md`

## Task 13: OBS 上传与签名 URL ✅

**文件**: `dm/util/ProjectNoticeScanExecutor.java`

- [x] `uploadToObs(objectKey, filePath)`：`ObsClientFactory` → `putObject` → `SignUtils.getUrl` 生成 2 周有效期签名 URL
- [x] `downloadObsTextByUrl(signedUrl)`：HTTP GET 取文本（缓存复用/人工补充重建）
- [x] Bucket 来自 `sca.notice.obs.bucketName`；ObsClient 在 finally 关闭

## Task 14: 查询与人工补充 ✅

**文件**: `dm/service/impl/ProjectNoticeScanServiceImpl.java`

- [x] `queryNotice`：releaseName 优先、productName 回退，两者皆空/记录不存在抛错；VO 填充状态字段 + 失败明细
- [x] `saveOrUpdateRelease`：存在则更新 release_name；不存在插入占位记录（不发布事件）
- [x] `supplementNotice`：扫描未完成拒绝；按 softwareName(+version) 匹配，未匹配抛错
- [x] 人工补充文本头部 `================ Software: {name} {version} (manually supplemented) ================`，与自动提取格式一致且边界可识别
- [x] 补充内容经临时文件上传 OBS（objectKey 清洗规则与自动路径一致），明细置 SUCCESS
- [x] 重建合并文档：原成功项在前（按明细顺序，内容从 `readmeOssUrl` 下载）、补充项追加在下载地址表之前；同 key 覆盖原合并对象
- [x] 重算计数与状态，`updateResultByScanId`（finishTime 保留原完成时间），复用 `queryNotice` 返回

## Task 15: 临时目录清理 ✅

**文件**: `dm/util/ProjectNoticeScanExecutor.java`

- [x] `cleanDir`：递归遍历 + `clearReadOnly`（Windows 只读属性）；`IOException` 仅 WARN 无重试（已知缺口）
- [x] `cleanFile`：单文件删除同上
- [x] 清理时机：单包提取后删包 → 上传后清包目录 → 合并上传后清合并目录 → `processScan` finally 清整扫描目录

## Task 16: 工具本地化与关联改动 ✅

**文件**: `tools/OSSinfo_extraction/`、`Dockerfile`、`dm/service/impl/OpenPersonDMScanDMServiceImpl.java`

- [x] Python 工具随仓维护于 `tools/OSSinfo_extraction/`（含 DESIGN/FAQs/README）
- [x] Dockerfile 由运行时 git clone 改为 `COPY ./tools/OSSinfo_extraction`，`PYTHONPATH` 指向 `ossinfo-extraction/src`
- [x] License 文件名模式补充 `licence` 英式拼写
- [x] scancode-toolkit 32.x 输出兼容：`license_detections` / `license_expression_spdx` 字段（`OpenPersonDMScanDMServiceImpl`）
- [x] 修复 ossinfo_extraction 超时失效与流读取死锁（守护线程并行读流 + 主线程 waitFor）

## Task 17: 测试 ✅

**文件**: `src/test/java/com/openlibing/sca/...`

- [x] `ProjectNoticeScanControllerTest`（4 接口）、`ProjectNoticeScanServiceImplTest`（SBOM 解析/去重/查询/补充，含状态回填与 null 容错）
- [x] `ProjectNoticeScanAsyncProcessorTest`（幂等、缓存、失败隔离、合并失败）
- [x] `ProjectNoticeScanEventListenerTest`、`ProjectNoticeScanRabbitConfigTest`、`OpenPersonDMScanDMServiceImplTest`
- [x] purl 解析器单测：Pypi/Maven/Npm/Go/CGit/Default/Composite（含 toOfficialUrl）
- [x] `ProjectNoticeScanExecutorTest`（URL 安全校验等）
- [x] Spotbugs 安全告警修复（EI/RCN/NP）
