# Design: notice 生成优化与 Copyright 归一化（ms-notice-20260910）

> 基于 openlibing-sca PR [#304](https://gitcode.com/openlibing/openlibing-sca/pull/304) 实现对齐（head SHA `6366ddf`，2026-09-10 合入 `release_20260910`）。包路径均省略 `com/openlibing/sca/` 前缀。前置上下文：`ossinfo-extraction-notice`（NOTICE 扫描基线设计）。

## 概述

本次迭代在 NOTICE 扫描基线上完成两类工作：

1. **人工干预成果跨扫描固化（#75）**：以 `manual_url` / `manual_content` 两列标记人工干预来源，新扫描按 `(software_name, version)` 继承最近一次人工成功明细——地址继承覆盖 SBOM 原始地址（天然命中全局缓存），内容继承直接落库 SUCCESS 跳过下载提取。
2. **链路工程化**：补充接口异步受理（复用 notice_scan 单消费者串行化）、新增 `/info` 详情查询、导出切换 framework 统一导出、purl 解析路由修复、Copyright 归一化口径统一（#76）。

## Architecture

```
ProjectNoticeScanController (REST, /project/notice/scan/*)
    │
    └── ProjectNoticeScanService(Impl)          @Transactional
            ├── startScan        ── SBOM 解析 ── inheritManualSupplements ── 落库 ── publishEvent
            ├── exportNotice     ── framework 创建导出任务 ── OBS 桶间转存 ── 回填任务状态
            ├── queryScanInfo    ── 最新扫描 + 明细（剔除 OBS 内部地址）
            └── supplementNotice ── 受理（CAS 置 PENDING + 主表 CAS 置 PROCESSING）── publishEvent
                    │
                    ▼
    ProjectNoticeScanEventListener              @TransactionalEventListener(AFTER_COMMIT)
            │  scan 消息: body=scanId（无 header，兼容存量）
            │  supplement 消息: header msgType=supplement, body=JSON{scanId, contentDetailIds, rescanDetailIds}
            ▼
    RabbitMQ: notice_scan_exchange ──▶ notice_scan_queue ──▶ death(DLQ)
                    │
    ProjectNoticeScanAsyncProcessor ◀┘  单消费者、手动 ack、按 msgType 分派
            ├── processScan(scanId)          首扫/孤儿恢复；内容继承明细跳过下载
            └── processSupplement(scanId, contentIds, rescanIds)
                    └── 重扫 rescan → 重读 DB 全量明细 → 重建合并文档 → 统一置成功
                    ▼
    ProjectNoticeScanExecutor（下载 / Python 子进程 / OBS / 合并 / 桶间转存 / HTML 拦截）
            ├── OpenlibingFrameworkClient（统一导出任务 create / update）
            └── PackageUrlResolverComposite ── CGit / Maven resolver（路由修复）
```

## 关键设计

### 1. 人工干预继承机制（#75）

**数据模型**：`tbl_project_notice_scan_detail` 新增列（Liquibase `20260909_add_tbl_project_notice_scan_detail_manual_flag`，preConditions 幂等 + rollback dropColumn）：

| 列               | 类型                       | 说明                                    |
| ---------------- | -------------------------- | --------------------------------------- |
| `manual_url`     | TINYINT NOT NULL DEFAULT 0 | 下载地址来自人工修正（地址继承标记）    |
| `manual_content` | TINYINT NOT NULL DEFAULT 0 | NOTICE 内容来自人工补充（内容继承标记） |

注意：`batchInsert` 显式传值时 DB 默认值不生效，明细创建时必须显式初始化为 0，否则插入报 `Column cannot be null`。

**继承查询** `selectLatestManualSuccess(softwareName, version)`：

```sql
SELECT ... FROM tbl_project_notice_scan_detail
WHERE software_name = ? AND version = ?
  AND (manual_url = 1 OR manual_content = 1)
  AND status = 1 AND readme_oss_url IS NOT NULL
ORDER BY update_time DESC LIMIT 1
```

**继承决策**（`startScan` 内 `inheritManualSupplements`，SBOM 明细落库前原位更新）：

- `manual_content=1`（优先）：明细直接置 SUCCESS 并回填历史 `readme_oss_url`、`manual_content=1`；`processScan` 遇 SUCCESS 明细跳过下载提取，仅从 OBS 取内容参与合并。
- `manual_url=1`：以历史人工地址覆盖 SBOM 原始地址并置 `manual_url=1`，后续 `(name, version, url)` 全局缓存天然命中。
- 单条继承查询失败仅告警、明细保持 SBOM 原始地址，不阻断扫描主流程；FAILED/PENDING 的历史人工记录不参与继承。

### 2. 补充受理异步化（CAS 状态机）

`/supplement` 从「同步重建合并文档」改为「受理即返回」：

**明细级 CAS**（仅允许终态翻转，防并发重复受理）：

- `markSupplementContent(id, readmeOssUrl)`：`status IN (1,2) → 0`，回填 content 上传 OBS 后的地址、置 `manual_content=1`、清空 errorMsg。content 项在受理时已上传 OBS，消费端无需重扫，仅登记就绪。
- `markSupplementRescan(id, downloadUrl)`：`status IN (1,2) → 0`，更新修正地址、置 `manual_url=1`。由消费端重新下载提取。

**主表级 CAS** `markSupplementProcessing(scanId)`：`status IN (1,2,3) → 1(PROCESSING)`，使调用方通过 `/info` 可感知「补充处理中」；多轮并发补充时 PROCESSING→PROCESSING 幂等成功。前置校验拒绝 PENDING（首扫未完成）。

**入参契约变更**：每项 `content` 与 `downloadUrl` 二选一（都传冲突、都不传无事可做均拒绝），`downloadUrl` 长度 ≤ 2048；同一请求任一项受理失败整批事务回滚。

**消费端** `processSupplement(scanId, contentIds, rescanIds)`：

1. content 明细（PENDING）：直接登记就绪（内容已备好，按需从 OBS 取）。
2. rescan 明细（PENDING）：复用 `prepareDetailContent`（含全局缓存命中）重新下载提取并上传 OBS；失败仅置该明细 FAILED，不影响其他明细。
3. 重读 DB 全量明细（重读而非受理时快照）重建合并文档——往轮已生效的 SUCCESS 项 + 本轮就绪项共同参与，多次补充结果累积互不覆盖。
4. 合并成功后本轮就绪明细才统一置 SUCCESS 并回填地址（消除「明细已完成但合并文档尚未更新」的时间窗）；合并失败则本轮就绪明细置 FAILED 并连同 scan 一起 FAILED（避免卡 PENDING 无重试）。
5. 刷新 scan 计数 / 状态 / 合并文档地址（finishTime 保留原完成时间）。

消息体只携带明细 id 列表不携带补充文本（content 受理时已上传 OBS），避免大文本进 MQ 造成消息膨胀与丢失风险；无 `contentDetailIds` 字段的旧格式消息视为空列表（兼容存量死信）。

### 3. 孤儿 PROCESSING 恢复

`processScan` 状态门由「仅 PENDING」放宽为「PENDING 或 PROCESSING」：

- 单消费者串行下同一 scanId 不会并发消费；PROCESSING 视为进程崩溃 / 重启后 broker 重投的孤儿，续跑而非跳过。
- 已 SUCCESS 明细复用 OBS 内容不重扫，仅重扫 PENDING 明细，最终重建合并文档并置终态。

### 4. 详情查询 API（/info）

`POST /info`，body `ProjectNoticeScanInfoQueryPo{productName, status?}`：

- 按 `productName` 取 `tbl_project_notice_scan` 最新记录，返回 `ProjectNoticeScanInfoVO`（全字段，**剔除 `mergedOssUrl`**），携带 `ProjectNoticeScanDetailInfoVO` 列表（全字段，**剔除 `readmeOssUrl`**，`status` 传值时过滤：0-PENDING / 1-SUCCESS / 2-FAILED，空返回全部）。
- 产品尚未发起过扫描返回 `data: null`（正常现象，由调用方按未发起处理），不抛异常。
- `startScan` / `exportNotice` / `supplementScan` 入口补充参数日志（`JSONObject.toJSONString`）。

### 5. 统一平台导出（/export）

`POST /export?userId=...`，body `ProjectNoticeExportPo{productName}`，替换原 `/release` 与 `/query`：

1. 校验扫描存在且 `merged_oss_url` 非空（NOTICE 未生成时拒绝）。
2. Feign `OpenlibingFrameworkClient.createObsFile(userId, ObsFileCreateRequestDTO)` 在 framework 落 `obs_file` 记录（type=`project_notice`，identifier=清洗后产品名，data=JSON{productName, scanId}），任务进入「我的导出」。
3. `Executor.transferToExportBucket`：同一 ObsClient 内 getObject→putObject 流式转存至导出桶（`obs.export.bucket`，默认 `openlibing-export-prod`）。
4. 目标 objectKey 随机化为 `yyyy-MM-dd/<UUID>`，避免对象名被枚举猜測；下载文件名经对象元数据 `Content-Disposition: attachment; filename="<encoded>"; filename*=UTF-8''<encoded>`（URL 编码 + RFC 5987）指定——framework 签名 URL 不带响应头覆盖参数，浏览器默认取 key 末段 UUID 作文件名，故必须由对象元数据兜底。
5. 转存失败置任务失败并抛业务异常；成功后 `updateObsFile`（`expectedMessages` 乐观锁条件更新）置成功并回填 objectKey，条件更新失败同样抛业务异常提示重试。Feign update 异常按失败返回 false 不上抛，避免覆盖主流程异常。

### 6. Copyright 归一化（#76）

`OpenPersonDMScanDMServiceImpl.replaceSpecialCharsCopyright`：

```java
String replace = input.replaceAll("\\s+", "");
replace = replace.replaceAll("(?i)copyright", "");   // 剥离前缀单词
// specialChars 列表按序移除：©、(c)、(C) 必须排在 "("、")" 之前，
// 否则 "(c)" 被拆散后残留孤立的 "c"
```

归一化后 `copyright(c) 2026 Brain-inspired computing lab` 与 `2026 Brain-inspired computing lab` 结果一致（`braininspiredcomputinglab`），`checkCopyrightMatch` 的包含关系判定不再因前缀写法变体误判不匹配。

### 7. purl 解析路由修复

**CGitPackageUrlResolver** 识别规则（满足任一即 `supports`）：

1. path（去 query）以 `.git` 结尾（大小写不敏感）——任意 host，显式 clone URL。
2. 白名单 git host（`gitcode.com` / `github.com` / `gitee.com` / `atomgit.com` / `gitlab.com` / `bitbucket.org`，含子域）+ http(s) + path 至少两段 `/owner/repo`，且**排除**归档资产（`/archive/`、`/releases/download/`、归档后缀 `.tar.gz` 等）与网页 ref 页面。
3. 网页版 ref 页面（白名单 host 上 `/owner/repo/commit|commits|tree|blob|blame|tag|tags/<ref>`、`releases/tag/<tag>`、GitLab `/-/commit/<sha>`）——由本 resolver 归一化为归档下载地址：github `/archive/<ref>.tar.gz`、gitee `/repository/archive/<ref>.zip`、bitbucket `/get/<ref>.tar.gz`、gitlab `/-/archive/<ref>/...tar.gz`；gitcode / atomgit 格式未知时回退仓库基址由 git clone 兜底。

排除归档/ref 页面的原因：git clone 对这类 URL 拼接 `/info/refs?service=git-upload-pack` 请求会 404；此前仅识别 `.git` 后缀导致主页 URL 走 HTTP 下载通道、把 HTML 当软件包处理。

**MavenPackageUrlResolver**：镜像候选 URL 去掉 `maven2/` 前缀（镜像根路径已等价 Central 的 `/maven2/`，如华为云 `repository/maven` 对应 `repo1.maven.org/maven2`），官方候选保留前缀。

**HTML 响应拦截**：`Executor.downloadPackage` 检查响应 `Content-Type` 以 `text/html` 开头即抛 `ScaException`（显式失败可触发候选回退），避免 SPA 平台 200+HTML 首页壳被静默落盘后交给 scancode 扫出空结果。

### 8. NOTICE 文档格式统一

`NoticeMerger.SOFTWARE_SEPARATOR_PREFIX` 与 `buildManualReadmeContent` 头部统一为 `Software: <名称> <版本>`（与 ossinfo-extraction 的 `readme_opensource.py` 产物完全一致），去掉 `================` 边框与 `(manually supplemented)` 标注，保证人工补充项与自动提取项在合并文档中格式一致且边界可识别。

## Data Model 变更汇总

| 对象                              | 变更                                                                                                                                                                         |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tbl_project_notice_scan_detail`  | 新增 `manual_url`、`manual_content`（TINYINT NOT NULL DEFAULT 0）                                                                                                            |
| `TblProjectNoticeScanDetail` 实体 | 新增 `manualUrl`、`manualContent` 字段                                                                                                                                       |
| Mapper XML                        | `insert`/`batchInsert` 补列；新增 `selectLatestManualSuccess`、`markSupplementContent`、`markSupplementRescan`；`selectCachedSuccess` 补 `ORDER BY update_time DESC LIMIT 1` |
| `TblProjectNoticeScanMapper`      | `updateReleaseNameById` 删除，新增 `markSupplementProcessing`（CAS）                                                                                                         |
| db.changelog.xml                  | include `mysql/20260909/add-tbl-project-notice-scan-detail-manual-flag.xml`                                                                                                  |

## 测试策略

| 测试类                                | 覆盖点                                                                                                                                       |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProjectNoticeScanServiceImplTest`    | 继承（content/url 优先级、查询失败降级）、补充受理（二选一校验、CAS 冲突、PROCESSING 允许）、exportNotice 全链路、queryScanInfo（null/过滤） |
| `ProjectNoticeScanAsyncProcessorTest` | 内容继承明细跳过下载、孤儿 PROCESSING 恢复、processSupplement（就绪登记、重扫失败隔离、合并失败置 FAILED、重读累积）                         |
| `ProjectNoticeScanEventListenerTest`  | 补充消息 JSON body + msgType header、发送失败仅记日志                                                                                        |
| `ProjectNoticeScanControllerTest`     | /export、/info（含状态过滤）、/supplement 新契约                                                                                             |
| `CGitPackageUrlResolverTest`          | 白名单主页识别、归档/ref 页面路由与归一化、非白名单不受影响                                                                                  |
| `MavenPackageUrlResolverTest`         | 镜像去 `maven2/` 前缀、官方保留前缀                                                                                                          |
| `OpenPersonDMScanDMServiceImplTest`   | Copyright 前缀变体归一化一致性、checkCopyrightMatch 匹配语义                                                                                 |
| `ProjectNoticeScanExecutorTest`       | 转存 / Content-Disposition / HTML 拦截                                                                                                       |

## 风险与注意事项

- **Schema 变更**：新增 2 列需确认 Liquibase 在 release 环境的执行顺序与回滚语句；`batchInsert` 必须显式传 0。
- **接口契约变更**：`/release`、`/query` 下线，`/supplement` 返回体从 `ProjectNoticeScanVO` 变为受理结果 `ProjectNoticeScanSupplementVO`（scanId + acceptedItems），调用方需同步适配。
- **配置项**：`obs.export.bucket` 各环境需在配置中心核实（默认 `openlibing-export-prod`）。
- **消息兼容**：scan 与 supplement 消息共用 notice_scan 队列靠 header 区分，消费端对无 header 消息按 scan 处理（兼容存量）；supplement 消息投递失败仅记 ERROR（与 scan 消息一致），明细将停留在 PENDING，需监控发现。
- **合并失败无重试**：processSupplement 合并失败直接置 FAILED，依赖调用方重新发起补充。
