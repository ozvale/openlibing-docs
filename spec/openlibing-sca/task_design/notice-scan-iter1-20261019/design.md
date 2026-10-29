# NOTICE 扫描大版本迭代（20261019 iter1）— 技术设计

> 本 spec 为 PR 级统一归档。批量导出 / 多过滤查询 / 依赖类型 / ossinfo 提取等子需求已有独立 spec（见文末"关联 spec"），本文档侧重 PR 实际交付内容与跨需求整合点。

## 方案概述

按四条主线交付：

1. **接口层**（`ProjectNoticeScanController` + `ProjectNoticeScanService`）：新增 5 个接口、增强 2 个接口，所有批量/清空操作走异步受理 + 后台线程串行执行模式，接口立即返回。
2. **数据层**：Liquibase 2 个 changeset 扩展明细依赖类型与直接依赖合并文件地址；Mapper 新增拆解统计聚合、版本回填、依赖类型批量回填、按制品删除等查询。
3. **下载/解析链路**（`ProjectNoticeScanExecutor` + `packageurl` 五个 Resolver）：候选 URL 多源化 + 可重试失败分类 + 无版本 purl 最新版本解析。
4. **生成链路**（`ProjectNoticeScanAsyncProcessor` / `NoticeBatchMerger` / `NoticeMerger`）：直接依赖合并 NOTICE 预生成 + 跨制品合并器。

## 关键决策

1. **分页在 SCA 侧内存完成**：SBOM internal-api 契约忽略排序与分页，返回全量制品名清单后由 SCA 按 statuses 本地过滤 + 内存分页（pageNum 缺省 1、pageSize 缺省 10），前端与制品列表按 productName join。
2. **拆解统计口径**：`dependency_type=2`（直接&间接）在统计中仅计入直接依赖；明细按 `dependency_type IN (0,2)` 聚合直接依赖总数/失败数；无明细按 0 填充，聚合失败保持 null。
3. **重试只针对可重试失败**：`DownloadFailureException` 携带 `retryable` 标记（408/429/5xx 与网络瞬时故障为 true；404、200+HTML 壳为 false）；cause 链匹配 `SSLException / SocketTimeoutException / ConnectException / HttpTimeoutException / SocketException`，深度上限 10 防异常环。git clone 通道失败不属网络异常，保持单次尝试。
4. **签名 URL 不再直接 GET**：签名 URL 有效期仅 2 周，DB 中历史 URL 必然 403 过期；`downloadObsTextByUrl` 改为从 URL path 提取 objectKey 后按桶+key 读取。异常消息统一走 `redactSignedUrl`（去 query 串追加 `?<redacted>`），避免 AccessKeyId/Signature 进日志与 error_msg。
5. **无版本 purl 语义 = 最新版本**：SBOM versionInfo 缺失且 purl 无版本段时入库 NOASSERTION，下载成功后从产物文件名反解真实版本回填（`updateVersionById`），合并 NOTICE 与查询接口随之显示真实版本。
6. **Python 依赖跳过**：pypi purl 与 pythonhosted/pypi 镜像依赖不解析、不入库，避免无意义扫描项。
7. **批量 OBS 下载共用 ObsClient**：8 并发 daemon 线程池（`notice-obs-download`），复用 TLS 连接池，单对象失败跳过且保持入参顺序。
8. **Dockerfile 构建期冒烟兜底**：scancode-toolkit 对 pluggy 仅有 `>=1.0.0` 无上界约束，pluggy 1.7.0 与 plugincode 32.0.0 不兼容（import 即崩、运行期静默产出 null），故钉住 `pluggy<1.7.0` 并以 `pip3 check && scancode --version` 让依赖冲突在镜像构建期暴露。
9. **JVM 代理配置生效**：下载与仓库 API 查询的 `HttpClient` 显式挂 `ProxySelector.getDefault()`；OBS 客户端刻意不挂（内网/华为云节点）。

## 新增接口契约摘要

| 接口                         | 入参                                               | 核心语义                                                                                                                |
| ---------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `/scanStatusByMultiFilter`   | productType 必填，可选 statuses + pageNum/pageSize | 每制品最新扫描状态 + totalCount/failCount/directTotalCount/directFailCount；未扫描制品 status=null、statusName="未扫描" |
| `/startBatch`                | 同上（分页参数不参与语义）                         | statuses 命中过滤后后台串行逐制品调用 startScan，失败跳过记日志                                                         |
| `/exportBatch`               | productNames 集合 + 可选 exportScope               | 缺失制品跳过、全部缺失拒绝；后台合并为单文件转存导出桶，返回 taskId                                                     |
| `/clear`                     | productName 可选                                   | 传名单制品、传空全量（高危）；先删明细后删扫描记录，事务保证原子性                                                      |
| `/dependencyType/supplement` | productNames（空则全量制品）                       | 调 SBOM 查询依赖类型回填全部历史明细（幂等），完成后重建直接依赖合并 NOTICE                                             |
| `/export`（增强）            | +exportScope                                       | FULL 转存全量合并文件；DIRECT 转存预生成直接依赖合并文件（未生成报业务异常）                                            |
| `/info`（增强）              | +dependencyTypes、+pageNum/pageSize                | 明细分页（create_time asc）+ 2×2 拆解统计（成功直接/成功间接/失败直接/失败间接）                                        |

## 数据模型变更（Liquibase 20261014）

| changeset                                                     | 表.列                                            | 类型          | 说明                                           |
| ------------------------------------------------------------- | ------------------------------------------------ | ------------- | ---------------------------------------------- |
| `20261014_add_tbl_project_notice_scan_detail_dependency_type` | `tbl_project_notice_scan_detail.dependency_type` | INT           | 0-直接，1-间接，2-直接&间接，NULL-未补充       |
| `20261014_add_tbl_project_notice_scan_direct_merged_url`      | `tbl_project_notice_scan.direct_merged_oss_url`  | VARCHAR(1024) | 直接依赖合并 NOTICE 文件 OBS 地址，NULL-未生成 |

两个 changeset 均带 `preConditions onFail="MARK_RAN"` 幂等保护与 rollback 定义。

## 涉及文件（分组）

| 分组              | 文件                                                                                                                                                                                                                                                                              | 说明                                                                                                                                               |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 构建环境          | `Dockerfile`（license-scanner）、`pom.xml`                                                                                                                                                                                                                                        | pluggy 钉住 + 冒烟校验；amqp-client 5.34.0 显式引入                                                                                                |
| DB                | `db.changelog-master.xml` + 2 个新 changeset XML、2 个 Mapper XML                                                                                                                                                                                                                 | 新增列 + resultMap 映射                                                                                                                            |
| analysis 实体/DTO | `TblProjectNoticeScan`、`TblProjectNoticeScanDetail`、`ProjectNoticeExportPo`、`ProjectNoticeScanInfoQueryPo`、新增 DTO/VO 约 10 个（BatchExportPo、ClearPo、MultiFilterQueryPo、DependencyTypeSupplementPo、DependencyBreakdownDto、DependencyStatsDto、ScanStatusVO、DPage 等） | 承载新接口入参出参与统计聚合结果                                                                                                                   |
| analysis client   | `OpenlibingSbomClient`                                                                                                                                                                                                                                                            | 新增 queryProductNamesByMultiFilter、queryPackageDependencyTypes 调用                                                                              |
| dm controller     | `ProjectNoticeScanController`                                                                                                                                                                                                                                                     | 5 新增 + 2 增强接口                                                                                                                                |
| dm dao            | `TblProjectNoticeScanMapper`、`TblProjectNoticeScanDetailMapper`                                                                                                                                                                                                                  | selectDependencyBreakdownByScanId、updateVersionById、batchUpdateDependencyType、selectDependencyStatsByScanIds、deleteByProductName、deleteAll 等 |
| dm service        | `ProjectNoticeScanService`（接口）、`ProjectNoticeScanServiceImpl`（+约 1000 行）、`ProjectNoticeScanAsyncProcessor`                                                                                                                                                              | 批量受理/后台执行/统计/回填/预生成直接依赖合并 NOTICE                                                                                              |
| dm util           | `NoticeBatchMerger`（新增 193 行）、`NoticeMerger`、`packageurl/BasePackageUrlResolver`、`CGitPackageUrlResolver`（+221 行）、`GoPackageUrlResolver`、`MavenPackageUrlResolver`、`NpmPackageUrlResolver`、`PypiPackageUrlResolver`                                                | 跨制品合并、多源候选、无版本 purl 解析                                                                                                             |
| dm executor       | `ProjectNoticeScanExecutor`                                                                                                                                                                                                                                                       | 重试/退避、代理、OBS 对象读取、并行下载、导出桶上传、签名 URL 脱敏                                                                                 |
| 枚举              | `NoticeExportScope`、`ProjectNoticeDependencyType`（common/enums）                                                                                                                                                                                                                | FULL/DIRECT；依赖类型枚举                                                                                                                          |
| 测试              | 10 个测试类（ServiceImplTest +约 720 行、ControllerTest +208 行、AsyncProcessorTest +约 300 行、ExecutorTest +180 行、5 个 ResolverTest）+ 新增测试文件（147 行）                                                                                                                 | 接口契约、合并器、重试、purl 解析全覆盖                                                                                                            |

## 配置项（均有默认值，不配置不影响启动）

| 配置键                                     | 默认                                        | 说明                                  |
| ------------------------------------------ | ------------------------------------------- | ------------------------------------- |
| `sca.notice.download.retry.maxAttempts`    | 2                                           | 单候选最大尝试次数（含首次）          |
| `sca.notice.download.retry.backoffMillis`  | 500                                         | 指数退避基数（上限 2^5=32 倍）        |
| `sca.notice.download.mirror.github.prefix` | `https://gh-proxy.com/,https://ghfast.top/` | GitHub 加速前缀（逗号分隔，空串禁用） |
| `sca.notice.python.timeoutMinutes`         | 60（原 20）                                 | ossinfo_extraction 进程超时（分钟）   |

## 测试策略

- **单测**：10 个测试类新增/更新，覆盖接口契约（Controller 层参数校验与异常映射）、服务层编排（跳过/拒绝/异步路径）、合并器（段落/表格/License 去重、异常文档跳过）、下载重试（可重试与确定性失败分类）、五个 Resolver 的无版本 purl 兜底链。
- **CI**：PR 流水线验证（测试计划勾选项）。
- **手动**：批量导出与多过滤状态查询结果正确性；Liquibase 存量库升级；license-scanner 镜像构建冒烟。

## 风险与缓解

| 风险                              | 缓解                                                                               |
| --------------------------------- | ---------------------------------------------------------------------------------- |
| 批量导出全量制品文档读入内存      | 单批制品数十量级；并行下载单失败跳过；文档为 markdown 文本，体量可控               |
| `/clear` 全量清空属高危操作       | 仅受理显式调用（productName 空才全量），文档明示调用方自行确认；删除条数落服务日志 |
| 内存分页在全量制品规模大时性能    | SBOM 返回的制品名清单为字符串列表，规模有限；分页仅内存切片                        |
| 公共 GitHub 加速器限流/间歇性阻断 | 多前缀按序换源 + 官方直连 + codeload 直链四层候选兜底                              |
| 无版本 purl 最新版本解析失败      | 各 Resolver 查询失败时兜底原始 purl（与旧行为一致），不会新增失败面                |
| SBOM 依赖类型查询失败             | 回填按制品跳过并告警，不影响其他制品；接口幂等可重试                               |
| pluggy 钉住与未来升级冲突         | 构建期 `pip3 check` 冒烟直接失败，问题前置到镜像构建                               |

## 关联 spec（本 PR 合并交付的子需求）

- `notice-scan-batch-export/` — 批量导出（跨制品合并）
- `notice-scan-status-multifilter/` — 多过滤状态查询
- `notice-scan-query-api/` — 查询接口（/info 分页化前身的查询能力）
- `notice-dependency-type/` — 依赖类型与按依赖范围导出
- `ossinfo-extraction-notice/` — ossinfo 提取 API

## 跨仓影响

- 仅 `openlibing-sca` 改动；对 SBOM 仓为调用方（internal-api 契约由对方提供），无其他仓改动。
- 部署侧：license-scanner 镜像需重新构建；SCA 服务库执行 Liquibase 增量 changeset。
