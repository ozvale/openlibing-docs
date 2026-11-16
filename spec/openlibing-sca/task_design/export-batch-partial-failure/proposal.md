# #134 — NOTICE 批量导出部分失败静默置成功与下载队列无界

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/134
（【安全】【Argus】exportBatch 批量导出缺少规模上限/幂等/配额且部分失败静默置成功，CWE-770，高危，当前状态 closed）

来源：安全扫描报告 `openlibingsca-20261021164919-003`（2026-10-21 批次，人工确认为问题/未修复）。

问题位置：

1. `ProjectNoticeScanServiceImpl.exportNoticeBatch`（约 L1150-1225）每次调用均创建导出任务并提交后台，无幂等键/配额/限流；
2. `ProjectNoticeScanExecutor.downloadObsObjectTexts`（约 L1098-1101）单制品 OBS 下载失败仅 `LOGGER.warn` 后返回 null 跳过；
3. `doExportBatch` 唯一失败分支是 `merged == null`（全部失败），部分失败时 `docs` 非空，必然落入 `markExportTask(EXPORT_STATUS_SUCCESS)`；
4. `obsDownloadExecutor`（8 线程）使用**无界** `LinkedBlockingQueue`；`batchExportExecutor` 为全局 2 线程 + 有界队列 50（非每用户隔离）。

风险与影响：

- 导出结果业务完整性受损——内容缺失的 NOTICE 合并文件被当作成功交付，用户无感知；
- 任一登录用户可高频重复提交，导出任务记录、OBS 下载/上传流量与导出桶对象无界增长；
- 批量合并任务占用后台导出线程与内存，拖慢甚至阻塞所有用户的导出能力。

## 功能描述

**做什么**：

1. `downloadObsObjectTexts` 返回值从 `List<String>` 改为 `BatchDownloadResult(List<String> docs, List<String> failedObjectKeys)`，保持入参顺序分别收集成功文档与失败 objectKey；
2. `doExportBatch` 在「部分成功、部分失败」（`docs` 非空且 `failedObjectKeys` 非空）时不再合并上传，改为 `markExportTask` 回填「部分失败」文案并直接返回——framework `getDownloadUrl` 只服务 message 精确等于 `ExportStatus.SUCCESS.getDesc()` 的任务，因此部分失败任务不可下载，文案即失败原因；
3. 新增 `buildPartialFailedMessage` / `joinedLength`：失败 objectKey 按导出源映射回制品名，输出 `部分失败：已导出 X/Y 个制品，下载失败：a、b 等 N 个，请重新发起导出`，并截断到 `EXPORT_MESSAGE_MAX_LENGTH = 255`（framework `obs_file.message` VARCHAR(255) + `@Size(255)`）；
4. `obsDownloadExecutor` 由无界队列改为有界队列 `OBS_DOWNLOAD_QUEUE_CAPACITY = 256` + `CallerRunsPolicy` 背压（不丢任务、不抛拒绝异常）。

**不做什么**：

- 未给 `ProjectNoticeBatchExportPo.productNames` 增加 `@Size(max = 50)` 或服务端数量/单名长度上限（本轮未覆盖）；
- 未增加幂等键（userId + 排序后制品列表摘要）与每用户配额/限流（本轮未覆盖）；
- 未调整 `batchExportExecutor`（保持 2 线程 / 有界队列 50 / 提交方捕获 `RejectedExecutionException` 置失败）；
- 未改变全部失败分支（仍置 `EXPORT_STATUS_FAILED`）与成功分支文案（必须严格等于「导出成功」）。

## 验收标准

- [x] 下载结果携带失败明细：成功文档与失败 objectKey 均按入参顺序返回，空/null 入参返回空结果且不构建 ObsClient（`ProjectNoticeScanExecutorTest#downloadObsObjectTexts_keepsOrderAndSkipsFailedKeys`、`#downloadObsObjectTexts_emptyKeys_returnsEmptyWithoutObsClient`）
- [x] 部分失败不再置成功：任务回填「部分失败：已导出 1/2 个制品，下载失败：bad，请重新发起导出」，`objectKey` 为空、期望前置状态为「导出任务已创建」（`ProjectNoticeScanServiceImplTest#doExportBatch_partialFailure_marksPartialFailedWithoutUpload`）
- [x] 部分失败时不上传导出桶、不创建/清理临时文件（同上，`verify(never()).uploadFileToExportBucket` / `never()).cleanFile`）
- [x] 失败制品过多时文案截断到 ≤255 且保留「等 N 个」总数概括（`#doExportBatch_partialFailure_truncatesMessageToLimit`）
- [x] 全部下载失败仍按失败回填（`#doExportBatch_allDownloadsFailed_marksTaskFailed`）
- [x] 成功路径保持「导出成功」精确文案，上传失败仍置失败并清理临时文件（`#doExportBatch_success_marksTaskSuccess`、`#doExportBatch_uploadFailure_marksTaskFailedAndCleansTempFile`）
- [x] 下载线程池有界（256）+ `CallerRunsPolicy`（代码证据：`ProjectNoticeScanExecutor#obsDownloadExecutor`）
- [ ] `productNames` 规模上限（issue 修复建议 1，本轮未覆盖）
- [ ] 幂等键 + 每用户配额 + 限流（issue 修复建议 2，本轮未覆盖）
- [ ] `mvn test` 全量执行结果（本轮为回溯补写文档，未执行，未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`dm` 模块 `ProjectNoticeScanServiceImpl`（`doExportBatch`）、`ProjectNoticeScanExecutor`（`downloadObsObjectTexts`、下载线程池）及对应单测
- 接口 / 契约：`POST /project/notice/scan/exportBatch` 入参/返回 VO 不变；改动的是导出任务最终 message 文案（部分失败时不再为「导出成功」）
- 配置 / schema：无变化；线程池队列容量为代码内常量
- 行为变化：部分失败任务由「可下载但内容缺失」变为「不可下载 + 失败原因/明细」
