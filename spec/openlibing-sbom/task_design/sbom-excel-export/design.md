# SBOM 导出异步化改造 — 技术设计

> 本文件为归档用同步版本，与 [proposal.md](./proposal.md)、[archive.md](./archive.md) 配套。
> change-name: `sbom-excel-export`

## 1. 方案设计

### 1.1 总体架构

对齐 codecheck 静态告警异步导出既有模式，按任务类型双线程池隔离：

```
                          ┌──「全量导出」弹窗·类型=软件成分数据(.xlsx) ─► POST /sbom-api/exportSbomExcel
前端导出入口 ──► 提交任务  │                          (type=SBOM_PACKAGE, packageExportExecutor, 并发2)
                          └──「全量导出」弹窗·类型=软件物料清单(SBOM) ─► POST /sbom-api/exportSbomDocument
                                                     (type=SBOM_DOCUMENT, documentExportExecutor, 并发1)
        两条链路共用：framework /export/internal-server/create 建任务 → 按 type 路由到对应线程池 execute
        → 任务内 CAS 抢占 → 生成本地临时文件 → CAS → OBS 上传 → CAS 回写导出成功+objectKey
        生成阶段按 type 分发：
          SBOM_PACKAGE   → 分页游标全量取数 → EasyExcel 多 Sheet 写临时文件
          SBOM_DOCUMENT  → 复用 sbomService.writeSbom(productName,spec,specVersion,format) byte[] → 写临时文件
        前端浮窗（exportTask store）轮询 /export/detail → ready 后 /export/download-url 自动下载
```

### 1.2 职责划分

| 端                   | 职责                                                                                                            |
| -------------------- | --------------------------------------------------------------------------------------------------------------- |
| openlibing-web       | 「全量导出」弹窗改造（「类型」单选切换 + 统一异步提交 + 标题/气泡文案更新）；轮询/下载/《我的导出》复用现有设施 |
| openlibing-sbom      | 两类导出编排（建任务/线程池调度/CAS 状态）、全量取数、Excel 生成、规范文档生成（复用 writeSbom）、OBS 上传      |
| openlibing-framework | 任务记录/状态机/签名 URL/过期清理（零改动）                                                                     |

### 1.3 双线程池隔离

SBOM_DOCUMENT 生成是整树内存构建（重），SBOM_PACKAGE 是分批查询（轻）。独立线程池 + 独立并发度避免重任务占满工作线程：Excel 池并发 2，文档池并发 1。单实例内联调度，无中间件依赖；任务可靠性由「线程池内兜底 catch + 状态回写」保证。

## 2. 实现逻辑设计

### 2.1 提交导出（同步部分，两类共用编排）

1. 校验参数非空、制品存在；userId 非空。
2. 横向鉴权：`checkPermissionByProductType("/openlibing-sbom/sbom-api/<接口>", productType, userId)`。
3. SBOM_DOCUMENT 先本地校验 spec/specVersion/format 合法（`SbomFormat.EXT_TO_FORMAT` + `SbomSpecification.findSpecification`），避免建任务必失败。
4. framework 建任务：
   - SBOM_PACKAGE：`fileName=<制品名>-<yyyyMMddHHmmss>.xlsx`，`data={"productName":"..."}`
   - SBOM_DOCUMENT：`fileName=<制品名>-<spec>-<specVersion>-sbom.<ext>.tar.gz`（对齐同步接口 downloadSbom：文档 + sha256 + 签名打包 tar.gz），`data={"productName","spec","specVersion","format"}`
5. 按 type 路由到对应线程池 `executor.execute(() -> processExportQuietly(type, recordId))`；线程池拒绝（队列打满）时回写「导出失败：导出任务排队已满，请稍后重试」并向调用方抛业务异常。
6. 返回 `DataResult<String>` recordId。

### 2.2 异步生成（按 obs_file.type 分发）

共享骨架：CAS 抢占（导出任务已创建→导出文件生成中）→ 生成临时文件 → CAS（→正在上传文件）→ OBS 上传（objectKey=`yyyy-MM-dd/<UUID>`）→ CAS 回写导出成功+objectKey；失败回写「导出失败：原因」（截断 255）；finally 删临时文件。

- `processPackageExport`：`getPackageInfoByNameForPage`（size=500，按名称排序，page 递增到空页）→ `packageWithStatisticsVoFromPackage` 同源映射 → `SbomPackageExportVO`；EasyExcel 写临时文件，Sheet 分片 10 万行；零数据写空 Sheet 保表头。
- `processDocumentExport`：data 恢复参数 → 现有 `sbomService.writeSbom(...)` byte[] → `generateVerificationAndTar` 打包（sbom + sha256 + 签名，对齐同步导出）→ 落临时文件。Writer 三实现零改动。
- 状态中文文案为前后端契约（前端 `normalizeExportStatus` 靠「导出失败」前缀判失败）：`导出任务已创建 / 导出文件生成中 / 正在上传文件 / 导出成功`。

### 2.3 线程池配置（`SbomExportExecutorConfig`）

两个独立 `ThreadPoolTaskExecutor` Bean，AbortPolicy 拒绝策略，`waitForTasksToCompleteOnShutdown=true`：

| Bean                     | 池参数（`@Value` 带默认值，可选配置）                       | 线程名前缀         |
| ------------------------ | ----------------------------------------------------------- | ------------------ |
| `packageExportExecutor`  | core=2 / max=2 / queue=100（`sbom.export.package-pool.*`）  | `sbom-pkg-export-` |
| `documentExportExecutor` | core=1 / max=1 / queue=100（`sbom.export.document-pool.*`） | `sbom-doc-export-` |

线程池任务体 `processExportQuietly` 兜底 catch `RuntimeException` 并回写失败，防止异常静默导致状态卡死。

### 2.4 异常与边界

| 场景                            | 处理                                                                                          |
| ------------------------------- | --------------------------------------------------------------------------------------------- |
| 制品不存在 / 参数空 / spec 非法 | 提交侧拦截；异步侧 CAS 前校验回写失败                                                         |
| 线程池队列打满拒绝              | 捕获 `RejectedExecutionException`，回写「导出失败：导出任务排队已满，请稍后重试」+ 抛业务异常 |
| 任务执行中未预期异常            | `processExportQuietly` 兜底 catch + 回写失败                                                  |
| 重复触发                        | CAS 抢占失败直接 return（幂等）                                                               |
| 生成/上传异常                   | catch 精确异常回写原因，finally 删临时文件                                                    |
| CAS 失败（已被置 FAILED）       | 中止，防覆盖失败态                                                                            |
| 实例重启时在途任务              | 停留中间态，3 天后 framework CleanObsFileJob 清理（无持久化重投递，接受该边界）               |

## 3. 类设计

### openlibing-sbom

| 类                                                        | 操作 | 说明                                                                                                                                                                                             |
| --------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `SbomController`                                          | 修改 | 新增 `exportSbomExcel(productName, userId)`、`exportSbomDocument(productName, spec, specVersion, format, userId)`，返回 `ResponseEntity<DataResult<String>>` recordId                            |
| `SbomExportService`（接口，interface 模块 `api.sbom` 包） | 新增 | `exportSbomPackageExcel` / `exportSbomDocument` / `processExport(recordId)`（遵循 AuthService/SbomService 惯例）                                                                                 |
| `SbomExportServiceImpl`                                   | 新增 | 编排实现；私有：`submitExportTask`/`processExportQuietly`/`generatePackageExcel`/`generateDocument`/`writePackageExcel`/`toExportVo`/`casUpdateStatus`/`queryExportRecord`/`updateExportFailure` |
| `SbomExportExecutorConfig`                                | 新增 | 双 `ThreadPoolTaskExecutor`（Excel 并发 2 / 文档并发 1），AbortPolicy，参数 `@Value` 带默认值                                                                                                    |
| `SbomExportType`                                          | 新增 | `SBOM_PACKAGE` / `SBOM_DOCUMENT`，枚举名即 obs_file.type，并决定路由线程池                                                                                                                       |
| `SbomExportStatusEnum`                                    | 新增 | `INITIALIZED/BUILDING/UPLOADING/SUCCESS/FAILED`（中文 message 对齐 framework 与前端契约）+ `buildFailedMessage`（截断 255）+ `QUEUE_FULL_REASON`                                                 |
| `SbomObsBucketService` + Impl                             | 新增 | `uploadFile(objectKey, tempFile, downloadFileName)` / `deleteObject`；懒加载 ObsClient + `SecurityUtil.decrypt`                                                                                  |
| `FrameworkClient`（clients 模块）                         | 修改 | 新增 `createExportTask` / `updateExportTask` / `queryExportTask`                                                                                                                                 |
| Obs DTO ×4                                                | 新增 | `ObsFileCreateRequestDTO / ObsFileUpdateRequestDTO / ObsFileQueryRequestDTO / ObsFileResponseDTO`（照抄 codecheck 契约）                                                                         |
| `SbomPackageExportVO`                                     | 新增 | EasyExcel `@ExcelProperty` 列 VO                                                                                                                                                                 |
| `ProductRepository`                                       | 修改 | 附带改动：4 处查询 LEFT JOIN → INNER JOIN（见第 8 节）                                                                                                                                           |

### openlibing-web

| 文件                                 | 操作 | 说明                                                                                                                                                                                                                           |
| ------------------------------------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CompositionAnalysis/index.vue`      | 修改 | 下拉项不变；「全量导出」tooltip 更新                                                                                                                                                                                           |
| `component/sbomExportDialog.vue`     | 重构 | 标题改「导出软件物料数据」；新增「类型」radio（软件物料清单（SBOM）默认 / 软件成分数据（.xlsx））；SBOM→三级联动展示→`exportSbomDocument`；xlsx→隐藏三级联动→`exportSbomExcel`；统一 `useExportTaskSubmit`；移除 blob 下载逻辑 |
| `api/sbom/url.ts` + `api.ts`         | 修改 | 新增 `EXPORT_SBOM_EXCEL` / `EXPORT_SBOM_DOCUMENT`                                                                                                                                                                              |
| `views/MyExports/mapExportRecord.ts` | 修改 | `TYPE_LABEL` 增加 `SBOM_PACKAGE: 'SBOM包清单'`、`SBOM_DOCUMENT: 'SBOM文档'`                                                                                                                                                    |

## 4. 数据模型设计

- 不新增业务表：任务记录复用 framework `obs_file`（type/data/message）；取数复用现有 PG 表；无 schema 变化与迁移。
- 异步调度为本地线程池，无中间件资源新增。
- 配置获取：OBS 统一导出配置（`obs.export.bucket` / `obs.access-key-id` / `obs.secret-access-key` / `obs.endpoint` / `security.part1`）由 framework 在 Nacos `framework` data-id 统一管理；sbom 三个环境 properties 的 `spring.config.import` 增加 `optional:nacos:framework`（对齐 codecheck），配置键与 codecheck 完全一致，无需在 sbom data-id 重复维护。线程池参数 `sbom.export.*-pool.*` 代码默认值即可运行，可选配置。

### Excel 列（15 列，对齐前端表格口径）

软件包名称 / 版本 / 依赖类型 / 语言类型 / 包管理器类型 / 严重 / 高危 / 中危 / 低危 / 无风险 / 未知 / License（逗号拼接按 licenseId 排序）/ PURL / Supplier / 来源信息（statistics 为空时回退 externalVulRefs 现算，同 `PackageStatisticsVo.fromPackage`）。

## 5. 性能设计

- Excel：每批 500 分页游标 + EasyExcel 流式写 + Sheet 10 万行分片，内存峰值与包总量解耦；`default_batch_fetch_size=50` 缓解子集合 N+1。
- 规范文档：内存画像与现状相同，但脱离请求线程无 HTTP 超时；文档池并发 1 串行执行控内存峰值；流式序列化为二期优化。
- 并发控制：Excel 池并发 2、文档池并发 1（本地 `ThreadPoolTaskExecutor`，队列各 100），避免拖累在线查询。
- 前端浮窗 5 分钟超时提示（现有逻辑），任务本身不限时，以《我的导出》framework 记录为准。

## 6. API 接口设计

| 接口                           | 方法 | 入参（query）                                          | 出参                          |
| ------------------------------ | ---- | ------------------------------------------------------ | ----------------------------- |
| `/sbom-api/exportSbomExcel`    | POST | productName、userId（必填）                            | `DataResult<String>` recordId |
| `/sbom-api/exportSbomDocument` | POST | productName、spec、specVersion、format、userId（必填） | `DataResult<String>` recordId |

- 后续轮询/下载复用 framework `GET /export/detail`、`GET /export/download-url`（3 小时签名 URL）。
- `GET /sbom-api/exportSbom` 同步接口保留不变（Internal/Apig 机机调用方继续使用）。

## 7. 安全设计

- gateway 登录鉴权 + `checkPermissionByProductType` 横向鉴权（防越权导出他人制品 supplier/copyright 数据）。
- 参数非空/存在性校验；spec/format 提交前合法校验；异步任务 recordId 来自内存调度（非外部输入）。
- OBS AK/SK 密文存储 + 运行期解密，不落日志；objectKey 服务端生成；下载文件名 URL 编码 + `filename*` 双写。
- 临时文件 finally 删除；线程池队列上限 + AbortPolicy 拒绝回写失败，无资源无限堆积；先传后改状态无半态文件。

## 8. 附带改动：过滤「无解析状态」数据（与导出无关联，独立 commit）

### 8.1 根因与改法

`ProductRepository` 各查询对最新 raw_sbom 子查询均为 LEFT JOIN，无解析记录的制品 `scanStatus=NULL` 仍入列表（前端显示 `--`）。改法：`LEFT JOIN rs` → `INNER JOIN rs + rs.task_status IS NOT NULL`。

### 8.2 涉及查询

| 查询方法                                              | 用途                                                             | 改动                     |
| ----------------------------------------------------- | ---------------------------------------------------------------- | ------------------------ |
| `getProductListMultiFilterPage`（主+count）           | 制品信息列表                                                     | 改 INNER JOIN            |
| `getProductNamesMultiFilter`                          | `/internal-api/queryProductNamesByMultiFilter`（SCA 全量制品名） | 同上                     |
| `countProductsByAttributeKey` / `countProductsByName` | 筛选徽标聚合                                                     | 同上（口径一致）         |
| `countProductsByScanStatus`                           | 解析状态徽标                                                     | 不动（已有 IS NOT NULL） |

### 8.3 影响与边界

纯后端 SQL 改动、无接口契约变化、前端零改动（`--` 兜底渲染保留）；无解析状态制品仅列表不可见，详情直链仍可访问。
