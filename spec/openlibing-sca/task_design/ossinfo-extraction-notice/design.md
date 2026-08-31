# Design: 项目 NOTICE 扫描（ossinfo-extraction-notice）

> 基于 openlibing-sca `ms_notice` 分支实现现状（2026-08-31 对齐）。包路径均省略 `com/openlibing/sca/` 前缀。

## 概述

项目 NOTICE 扫描将「产品 → SBOM → 软件清单 → 下载源码包 → Python 提取版权/许可证 → 合并生成 NOTICE 文档 → OBS 上传」整条链路产品化，并提供启动、查询、人工补充、发布名称管理 4 个接口。

**核心特征**：

- **受理即返回**：`start` 接口落库并投递消息后立即返回 `scanId`，实际执行由 RabbitMQ 单消费者串行完成
- **状态可追踪**：扫描与明细状态全程落库，`query` 接口返回状态、合并文档地址与失败明细
- **失败可兜底**：失败软件可由 `supplement` 接口人工补充并重建合并文档

## Architecture

```
ProjectNoticeScanController (REST, /project/notice/scan/*)
    │
    └── ProjectNoticeScanService(Impl)          @Transactional
            ├── startScan      ── SBOM 解析 ── 落库 ── publishEvent
            ├── saveOrUpdateRelease
            ├── queryNotice
            └── supplementNotice ── 复用 Executor 重建合并文档
                    │
                    ▼
    ProjectNoticeScanEventListener              @TransactionalEventListener(AFTER_COMMIT)
            │  RabbitTemplate.convertAndSend(scanId)
            ▼
    RabbitMQ: notice_scan_exchange ── notice_scan_key ──▶ notice_scan_queue ──▶ death(DLQ)
                                                            │
    ProjectNoticeScanAsyncProcessor ◀───────────────────────┘  单消费者、手动 ack
            │  processScan(scanId)：幂等 → 逐明细处理 → 合并上传 → 结果落库
            ▼
    ProjectNoticeScanExecutor（下载 / Python 子进程 / OBS / 合并 / 清理）
            ├── PackageUrlResolverComposite（purl → 候选下载地址 / 官方地址）
            └── NoticeMerger（合并文档生成）
```

## API Design

统一路径前缀 `/project/notice/scan`，全部为 `POST`，响应为通用 `ResponseEntity`（success 携带数据，failure 携带错误码/错误信息/建议）。无应用层鉴权（由网关/网络策略控制）。

### POST /start — 启动扫描

请求体 `ProjectNoticeScanStartPo`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `productName` | String | 产品名称，用于拉取 SBOM 与组织 OBS 目录 |

响应：`scanId`（UUID 去横线）。同步阶段完成落库与消息投递即返回；后续处理进度通过 `/query` 感知。

### POST /release — 保存/更新发布名称

请求体 `ProjectNoticeScanReleasePo`：`productName` + `releaseName`。

行为：按 `productName` 定位最新扫描记录——存在则更新其 `release_name`；不存在则插入一条仅承载产品名与发布名的占位记录（计数为 0、状态 PENDING，**不**发布扫描事件）。响应：落库记录的 `scanId`。

### POST /query — 查询结果

请求体 `ProjectNoticeScanQueryPo`：`productName` 与 `releaseName` 至少传一个；`releaseName` 非空时优先按发布名称查询最新记录，否则按产品名称。

响应 `ProjectNoticeScanVO`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `productName` | String | 产品名称 |
| `scanStatus` | Integer | 扫描状态原始值：0-待处理 / 1-处理中 / 2-成功 / 3-失败 |
| `scanStatusName` | String | 状态中文描述（`ProjectNoticeScanStatus.nameOf`，非法值返回空串不抛错） |
| `mergedOssUrl` | String | 合并 NOTICE 文件 OBS 签名 URL（扫描完成且有成功项时非空） |
| `failedDetails` | List | 失败软件明细：`softwareName` / `version` / `downloadUrl` |

### POST /supplement — 人工补充

请求体 `ProjectNoticeScanSupplementPo`：`productName` + `supplements[]`（`softwareName` 必填、`version` 可选、`downloadUrl` 可选、`content` 必填 `@NotNull`）。

前置条件：按 `productName` 定位的最新扫描必须已完成（状态非 PENDING/PROCESSING），否则拒绝。

## Data Model

### tbl_project_notice_scan（扫描总表）

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | VARCHAR(64) PK | 主键 |
| `scan_id` | VARCHAR(64) UK | 扫描ID（对外暴露） |
| `project_name` | VARCHAR(256) NOT NULL | 产品名称（索引） |
| `release_name` | VARCHAR(256) | 发布名称（索引） |
| `total_count` / `success_count` / `fail_count` | INT | 计数 |
| `merged_oss_url` | VARCHAR(1024) | 合并文件 OBS 签名 URL |
| `status` | INT | 0-PENDING / 1-PROCESSING / 2-SUCCESS / 3-FAILED（索引） |
| `error_msg` | VARCHAR(1024) | 总体错误信息 |
| `create_time` / `update_time` / `finish_time` | DATETIME | 时间戳 |

### tbl_project_notice_scan_detail（扫描明细表）

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | VARCHAR(64) PK | 主键 |
| `scan_id` | VARCHAR(64) NOT NULL | 关联总表（索引） |
| `software_name` / `version` | VARCHAR(256)/(128) NOT NULL | 软件标识（`(scan_id, software_name, version)` 唯一） |
| `download_url` | VARCHAR(1024) NOT NULL | 下载地址（可为 purl 原文） |
| `readme_oss_url` | VARCHAR(1024) | 单包 Readme.opensource OBS 签名 URL |
| `status` | INT | 0-PENDING / 1-SUCCESS / 2-FAILED |
| `error_msg` | VARCHAR(1024) | 失败原因（截断至 1024） |
| `(software_name, version)` | 索引 | 全局缓存查询用 |

### 状态枚举

- `ProjectNoticeScanStatus`：`PENDING(0)` / `PROCESSING(1)` / `SUCCESS(2)` / `FAILED(3)`，附 `nameOf(Integer)` 取中文描述（null/非法返回空串）
- `ProjectNoticeScanDetailStatus`：`PENDING(0)` / `SUCCESS(1)` / `FAILED(2)`

## 异步执行机制

### 消息拓扑

| 项 | 值（配置键与默认值） |
|----|--------------------|
| Exchange | `${spring.rabbitmq.sca.notice_scan_exchange:notice_scan_exchange}` |
| Routing Key | `${spring.rabbitmq.sca.notice_scan_key:notice_scan_key}` |
| Queue | `${spring.rabbitmq.sca.notice_scan_queue:notice_scan_queue}` |
| 死信 | `x-dead-letter-exchange=${spring.rabbitmq.sca.death_queue}`，`x-dead-letter-routing-key=death` |

exchange/queue/binding 由 `@RabbitListener + @QueueBinding` 注解内联声明；`ProjectNoticeScanRabbitConfig` 仅提供独立容器工厂 `projectNoticeScanContainerFactory`（`AcknowledgeMode.MANUAL`、并发消费者 1/1），避免与全局 ack 模式耦合。

### 投递时序

1. `startScan` 在 `@Transactional` 内落库后发布 `ProjectNoticeScanCreatedEvent(scanId)`
2. `ProjectNoticeScanEventListener` 以 `@TransactionalEventListener(AFTER_COMMIT)` 监听，事务提交成功后 `rabbitTemplate.convertAndSend(scanId)`
3. 事务提交后发送失败时：scan 已落库 PENDING 但无消息驱动，仅记 ERROR 日志，靠监控/人工处理（已知缺口）

### 消费语义

- 单消费者（`concurrency="1"`）串行消费，多产品并发提交在 broker 排队，保证 Python 子进程/下载/磁盘不并发竞争
- 手动 ack：`processScan` 成功 `basicAck`；抛 `RuntimeException` 时 `basicNack(requeue=false)` 进死信队列，避免无限重投堵死队列
- 幂等：`processScan` 开头仅处理 `PENDING` 状态的 scan，兜住 broker 重投/崩溃未 ack 的重复消费

## Service 层设计

### startScan（@Transactional）

1. `openScanServiceImpl.getLicenseFromSbom(productName)` 获取产品 SBOM JSON；为空抛 `ScaException(60000, "启动失败")`。目录级 SBOM 可达数十 MB，日志仅记录长度
2. `parseSbomToDetails` 解析 SBOM（规则见下）；无有效软件包抛错
3. 生成 `scanId`/`rootId`（UUID 去横线），插入扫描总表（PENDING）与明细表（批量插入）
4. 发布 `ProjectNoticeScanCreatedEvent`，返回 `scanId`

**SBOM 解析规则（parseSbomToDetails）**：

- 遍历 `packages[]`，跳过无 `name` 的包
- `downloadLocation` 有效（非空、非 `NOASSERTION`、非 `NONE`）→ 1 条明细，`softwareName`/`version` 取 `name`/`versionInfo`
- 否则展开 `externalRefs[]` 中所有非空 `referenceLocator` 为独立明细（覆盖 syft 目录级扫描：项目整体为单一 package、依赖挂 externalRefs）：
  - `pkg:` 开头的 purl：`parsePurlNameVersion` 解析 name（最后一个 `/` 之后）与 version（`@` 之后、剥离 `?qualifiers`/`#subpath`），循环 URL 解码最多 3 次（`+` 先转 `%2B` 保护，防 form 解码误转空格）；解析不到时以包级 name/version 兜底
  - 非 purl：以包级 name/version 兜底，`downloadUrl` 取 referenceLocator 原文
- 跨 package 按 `(softwareName, version)` 全局去重，规避唯一键冲突与重复扫描
- `version` 为空兜底为 `NOASSERTION`（明细表 version 列 NOT NULL）

### saveOrUpdateRelease（@Transactional）

按 productName 查最新记录：存在则 `updateReleaseNameById`；不存在则插入占位记录（计数 0、PENDING，不发布事件、不会被消费）。

### queryNotice

`releaseName` 非空优先 `selectLatestByReleaseName`，否则 `selectLatestByProjectName`；两者皆空或记录不存在抛 `ScaException(60000)`。组装 VO：状态字段 + `mergedOssUrl` + 状态为 FAILED 的明细列表。

### supplementNotice（@Transactional）

1. 参数校验：`productName`、`supplements` 非空，每项 `softwareName`/`content` 非空
2. 定位最新扫描；状态为 PENDING/PROCESSING 拒绝（"扫描尚未完成"）
3. 逐补充项匹配明细：`softwareName` 必须相等；`version` 为空取名称匹配首项，否则须同时相等。未匹配抛错
4. 构建人工补充文本：`================ Software: {name} {version} (manually supplemented) ================` + 正文（与自动提取产物格式一致且边界可识别）
5. 临时文件上传 OBS（objectKey 规则与自动提取一致），明细置 SUCCESS 并回写 `readmeOssUrl`
6. 重建合并文档：原成功项在前（按明细顺序，内容从各自 `readmeOssUrl` 下载），人工补充项追加在后（即下载地址表之前）；文件名与 objectKey 与异步流程完全一致，覆盖原合并对象
7. 重算成功/失败计数与扫描状态，`updateResultByScanId`（finishTime 保留原完成时间）
8. 复用 `queryNotice` 返回最新视图

## 异步处理流程（ProjectNoticeScanAsyncProcessor）

### processScan

```
查 scan → 不存在记 ERROR 返回
幂等检查：非 PENDING 跳过（兼容 status 为 null）
scan → PROCESSING
├── For each detail: processSingleDetail
│     成功 → MergeEntry(softwareName, version, content, downloadUrl) 入 successEntries
│     异常 → 明细置 FAILED（error_msg 截断 1024）
├── successCount > 0:
│     mergeAndUpload → 成功: mergedOssUrl, finalStatus=SUCCESS
│                    → 失败: scan 置 FAILED("merge failed: ...") 返回
├── successCount == 0: finalStatus=FAILED("all software failed")
├── updateResultByScanId(status, counts, mergedOssUrl, errorMsg, finishTime)
└── finally: cleanupScanDir(scanId)
```

### processSingleDetail（缓存 + 生成）

1. **全局缓存**：`selectCachedSuccess(softwareName, version, downloadUrl)` 查历史扫描中同（名称+版本+地址）的成功明细；命中则 `downloadObsTextByUrl(cached.readmeOssUrl)` 复用内容与地址
2. **未命中**：`generateAndUpload` ——
   - 包目录：`{workdir}/projectNoticeScan/{scanId}/{softwareName-version}`（名称中 `/` `\` `.` 替换为 `-`）
   - `executor.downloadPackage` 下载（记录耗时）
   - `executor.executeOssinfoExtraction` 提取（记录耗时）
   - 提取成功立即 `cleanFile(packagePath)` 释放磁盘（readme 与包同级，不受影响）
   - 读取 `Readme.opensource` 内容
   - **先上传 OBS 再清理**（顺序不可颠倒，否则文件被清理后上传失败）：`objectKey = {sanitize(productName)}/{sanitize(softwareName)}-{sanitize(version)}-Readme.opensource`
   - `finally`: `cleanDir(pkgDir)`
3. 明细置 SUCCESS，回写 `readmeOssUrl`，返回文本内容

### mergeAndUpload

- 文件名：`open-source-notice-{sanitize(productName)}.md`
- OBS key：`{sanitize(productName)}/{fileName}`（最外层目录为产品名而非 scanId，同产品再次扫描同 key 覆盖）
- 委托 `executor.mergeAndUpload`：每个 entry 先经 `packageUrlResolverComposite.toOfficialUrl(downloadUrl)` 还原官方地址，再交 `NoticeMerger.merge` 生成文档、写盘、上传
- 上传后清理本地合并目录

**文件名清洗规则（sanitizeFileName）**：`[/\\:*?"<>|]` 与空白替换为 `-`，清洗后为空回退 `unknown`。人工补充路径使用同规则，保证两条路径 objectKey 一致。

## Executor 设计（ProjectNoticeScanExecutor）

Bean 名 `projectNoticeScanExecutorUtil`。

### downloadPackage（多候选下载）

1. `isUrlSafe` 拦截：拒绝 shell 元字符、路径穿越 `..`、空白字符（`| ; $ > < \` \n # { } ( ) .. ' " \t \r 空格`）
2. `packageUrlResolverComposite.resolve(url, name, version)` 得到候选列表；空则抛错
3. 按序尝试候选：
   - git 仓库 URL（`CGitPackageUrlResolver.isGitRepoUrl`，如 `.git` 结尾）→ `doGitDownload`：剥离 query string 后 `git clone --depth 1`；version 非空时先以 `--branch {version}` 尝试，失败清理半成品后回退默认分支
   - 否则 → `doDownload`：HTTP GET（connectTimeout 30s、读超时 10min、`followRedirects ALWAYS`）；非 200 读取响应体前 500 字符入错误信息
4. 单候选失败继续下一个；全部失败抛 `ScaException("all download candidates failed")`

### executeOssinfoExtraction（Python 子进程）

- 命令：`python[3] -m ossinfo_extraction -t <pkgPath> -n <name> -v <version> -j <jobs>`（Windows 用 `python`）；三个参数先过 `CmdInjection.checkCommand`
- `-j`：`sca.notice.python.jobs` 显式指定，默认按 CPU 核数，上限 8、下限 1
- 超时：`sca.notice.python.timeoutMinutes`（默认 20 分钟），`waitFor(timeout)` 到期 `destroyForcibly`
- 流消费：显式 `ThreadPoolExecutor(2,2)` daemon 线程并行读 stdout/stderr（避免缓冲区满互相等待死锁，超时真正生效）；每路仅保留尾部 500 行（`ArrayDeque` 滚动），防 scancode 海量日志撑爆内存
- 字符集取 `sun.jnu.encoding`，回退 UTF-8
- 退出码非 0 记录 stdout/stderr 抛错；退出 0 后在 `packagePath.getParent()/Readme.opensource` 定位产物（与 Python 默认 `output_dir=target.parent` 对齐），缺失抛错并附输出日志
- `finally`：`ioService.shutdownNow()` + 进程存活则强杀

### OBS 上传/下载

- `uploadToObs(objectKey, filePath)`：`ObsClientFactory` 取客户端 → `putObject` → `SignUtils.getUrl` 生成**签名临时 URL（有效期 2 周）**返回；`ObsException` 转 `ScaException`，finally 关闭客户端
- `downloadObsTextByUrl(signedUrl)`：HTTP GET 签名 URL 取文本（缓存复用与人工补充重建用）

### 目录清理

- `cleanDir`：递归遍历 + `clearReadOnly`（Windows 只读属性）后删除；`IOException` 仅 WARN，**无重试**
- `cleanFile`：单文件删除，同上

### 工作目录

`getOssinfoExtractionWorkdir()` 返回 `ossinfo-extraction` 目录绝对路径；扫描产物统一落在 `{workdir}/projectNoticeScan/{scanId}/` 下。

## purl 解析器体系（dm/util/packageurl）

`PackageUrlResolverComposite` 按 `@Order` 顺序委托，首个 `supports` 命中的 resolver 处理：

| 顺序 | Resolver | 支持输入 | 候选构造策略 |
|------|----------|----------|--------------|
| 10 | `PypiPackageUrlResolver` | `pkg:pypi/` | 镜像 simple index（PEP 503）→ pypi.org JSON API → 原始地址兜底；sdist 优先、wheel 回退 |
| 20 | `MavenPackageUrlResolver` | `pkg:maven/` 前缀 + repo1.maven.org host | 解析 groupId/name/version 构造 maven2 路径；sources jar 优先、普通 jar 兜底；version 缺失回退 |
| 30 | `NpmPackageUrlResolver` | `pkg:npm/` | 离线确定性构造 `/{name}/-/{basename}-{version}.tgz`（scoped 包文件名去 scope 前缀）；零网络调用 |
| 40 | `GoPackageUrlResolver` | `pkg:golang/` | version 循环解码兼容双重编码（`%252B`）；module path 仅全小写 |
| 50 | `CGitPackageUrlResolver` | git 仓库 URL | 识别 `.git` 等仓库地址，交 Executor 走 `git clone` |
| 60 | `RpmPackageUrlResolver` | openEuler/CentOS 等 rpm 地址 | 版本目录拼 `-LTS` 后缀；main/update source 标准路径候选 |
| MAX | `DefaultPackageUrlResolver` | 其余 | 原始地址单候选兜底 |

**统一约定**：

- 候选顺序 = 镜像 → 官方 → 原始地址（原始地址保留诊断信息兜底）；`downloadPackage` 按序尝试
- `toOfficialUrl`（文档下载地址表还原官方地址）：Composite 统一分发——purl（`pkg:` 前缀）仅交 `supports` 命中的 resolver；非 purl 走基类镜像前缀剥离；转换失败原样返回不阻断文档生成
- 覆盖现状：Maven（→sources jar URL）、Go（→GitHub release 页，经 go-import meta API）、Pypi（→simple index/JSON API 解析后剥离镜像）、Npm（→确定性路径离线构造）已覆盖；**Rpm 未覆盖，Notice 下载表中输出裸 purl**（已知缺口）

**反直觉事实**：`pkg:` scheme 是 opaque URI，`URI.getHost()` 返回 null，基于 host 的 `supports` 判定对 purl 全部失效——purl 支持必须显式加前缀识别。

## NoticeMerger（合并文档生成）

输出结构：

```
**OPEN SOURCE SOFTWARE NOTICE**            ← 头部：纯 Markdown 加粗（不用标题/HTML）
**Please note we provide ...**             ← 说明段落
**Warranty Disclaimer** + 免责声明文本
**Copyright Notice and License Texts**
──────────────────────────────────────
各软件 Readme.opensource 内容（按条目顺序）
──────────────────────────────────────
**This software contains ... GPLv2 ...**   ← 尾部：加粗声明
| Software Name | Version | Download URL | ← 下载地址表（官方地址）
```

**License 去重规则**：

- 仅识别 `License: XXX` 行**紧接** `Full License Text:` 行（中间允许空行）的块，按 License 标识符去重
- 标识符已出现过 → 原文替换为 `Please see above`；块边界以下一个 `License:` 行或 `================ Software:` 分隔行为止
- 其他形式的 `License:` 行（如 bundled library 索引项后跟 "For details, see ..."）不参与去重，原样保留

**表格转义**：单元格中 `|` 转义为 `\|`，换行替换为空格。

## 配置项

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `sca.notice.obs.bucketName` | （必配） | OBS 目标 Bucket |
| `sca.notice.python.timeoutMinutes` | 20 | Python 单包提取超时（分钟） |
| `sca.notice.python.jobs` | 0（=CPU 核数，上限 8） | scancode 并行进程数 |
| `spring.rabbitmq.sca.notice_scan_exchange` | notice_scan_exchange | 扫描消息 exchange |
| `spring.rabbitmq.sca.notice_scan_key` | notice_scan_key | 路由键 |
| `spring.rabbitmq.sca.notice_scan_queue` | notice_scan_queue | 扫描队列 |
| `spring.rabbitmq.sca.death_queue` | （必配） | 死信 exchange |

## Error Handling

| 场景 | 行为 |
|------|------|
| SBOM 不存在 / 解析不出软件包 | `start` 同步返回 `ScaException(60000)` |
| 单包下载/提取/上传失败 | 明细置 FAILED（error_msg 截断 1024），继续处理其他明细 |
| 全部明细失败 | 扫描置 FAILED（"all software failed"），不生成合并文档 |
| 合并/上传失败 | 扫描置 FAILED（"merge failed: ..."），已成功的单包 Readme 仍保留在 OBS |
| 消费抛 RuntimeException | `basicNack(requeue=false)` 进死信队列 |
| 事务提交后消息发送失败 | 仅 ERROR 日志，scan 悬挂 PENDING（已知缺口，靠监控/人工） |
| query 两个查询参数都为空 / 记录不存在 | `ScaException(60000)` |
| supplement 匹配不到明细 / 扫描未完成 | `ScaException(60000)` |
| 目录清理失败 | 仅 WARN，不影响主流程 |

## File Structure

```
src/main/java/com/openlibing/sca/
├── analysis/
│   ├── entity/
│   │   ├── TblProjectNoticeScan.java / TblProjectNoticeScanDetail.java
│   │   ├── dto/ProjectNoticeScan{Start,Release,Query,Supplement}Po.java
│   │   └── vo/ProjectNoticeScanVO.java / ProjectNoticeScanDetailVO.java
│   └── service/impl/OpenScanServiceImpl.java          # getLicenseFromSbom
├── common/
│   ├── config/rabbitmq/ProjectNoticeScanRabbitConfig.java
│   └── enums/ProjectNoticeScanStatus.java / ProjectNoticeScanDetailStatus.java
├── dm/
│   ├── controller/ProjectNoticeScanController.java
│   ├── dao/TblProjectNoticeScan(Detail)Mapper.java
│   ├── event/ProjectNoticeScanCreatedEvent.java / ProjectNoticeScanEventListener.java
│   ├── service/ProjectNoticeScanService.java
│   ├── service/impl/ProjectNoticeScanServiceImpl.java
│   ├── service/impl/ProjectNoticeScanAsyncProcessor.java
│   └── util/
│       ├── ProjectNoticeScanExecutor.java
│       ├── NoticeMerger.java
│       └── packageurl/（Composite + Base/Default/Pypi/Maven/Npm/Go/CGit/Rpm + ResolvedUrl(s)）
src/main/resources/
├── db/changelog/mysql/20260716/create-tbl-project-notice-scan.xml
└── mapper/dm/TblProjectNoticeScan(Detail)Mapper.xml
tools/OSSinfo_extraction/                               # 本地化 Python 工具（Dockerfile COPY）
```

## Dependencies

| 依赖 | 用途 |
|------|------|
| Spring AMQP / RabbitMQ | 异步串行执行、死信 |
| `org.springframework.transaction.event` | 事务提交后投递消息 |
| MyBatis + Liquibase | 持久化与建表 |
| `com.alibaba.fastjson2` | SBOM JSON 解析 |
| `java.net.http.HttpClient` | 源码包/OBS 签名 URL 下载 |
| `com.obs.services.ObsClient` + `SignUtils` | OBS 上传与签名 URL |
| `ossinfo_extraction` (Python CLI) | 版权/许可证提取（镜像内置） |
| `git` CLI | git 仓库类依赖浅克隆 |

## Limitations

1. **串行消费**：单消费者逐个处理，大批量扫描吞吐受限于单包提取耗时（可通过 `python.timeoutMinutes`/`python.jobs` 调节单包速度）
2. **签名 URL 时效**：`mergedOssUrl`/`readmeOssUrl` 为 2 周有效期的临时签名 URL，过期需重新查询生成
3. **消息发送失败悬挂**：事务提交后投递失败无补偿机制，scan 悬挂 PENDING
4. **清理无重试**：`cleanDir`/`cleanFile` 失败仅 WARN；进程崩溃/清理自身异常/Python 子进程持句柄等场景可能残留临时目录
5. **Rpm 官方地址缺口**：Rpm resolver 未实现 `toOfficialUrl`，下载表中输出裸 purl
6. **Python 环境依赖**：部署镜像必须内置 `ossinfo_extraction` 工具与依赖（已随仓 `tools/` 本地化）
7. **占位记录语义**：`/release` 在无扫描历史时插入的占位记录状态恒为 PENDING，查询它返回"待处理"且无明细
