# #134 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: `ProjectNoticeScanExecutor.downloadObsObjectTexts` 改为返回 `BatchDownloadResult`（docs + failedObjectKeys），并新增 record 定义（`375eb04d`）
- [x] Task 2: `ProjectNoticeScanServiceImpl.doExportBatch` 部分失败回填「部分失败」文案、跳过合并上传；新增 `buildPartialFailedMessage` / `joinedLength` 与 255 上限常量（`375eb04d`）
- [x] Task 3: `obsDownloadExecutor` 改有界队列 256 + `CallerRunsPolicy`；补充/适配单测并交付 commit（`375eb04d`）

## 交付记录

| commit     | 日期       | 标题                                                                  | 关联      |
| ---------- | ---------- | --------------------------------------------------------------------- | --------- |
| `375eb04d` | 2026-11-06 | fix(notice-scan): report partial failure and bound obs download queue | Refs #134 |

- 分支：`ms_scan`（`openlibing-sca`）
- 验证方式（代码内证据）：
  - `ProjectNoticeScanServiceImplTest#doExportBatch_partialFailure_marksPartialFailedWithoutUpload`：message 等于「部分失败：已导出 1/2 个制品，下载失败：bad，请重新发起导出」，`objectKey` 为 null，未调用 `uploadFileToExportBucket` / `cleanFile`
  - `#doExportBatch_partialFailure_truncatesMessageToLimit`：60 制品场景 message ≤255，前缀「部分失败：已导出 1/60 个制品，下载失败：」、后缀「等 59 个，请重新发起导出」
  - `#doExportBatch_allDownloadsFailed_marksTaskFailed`、`#doExportBatch_success_marksTaskSuccess`、`#doExportBatch_uploadFailure_marksTaskFailedAndCleansTempFile`
  - `ProjectNoticeScanExecutorTest#downloadObsObjectTexts_keepsOrderAndSkipsFailedKeys`、`#downloadObsObjectTexts_emptyKeys_returnsEmptyWithoutObsClient`
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）
- 未覆盖（issue 修复建议）：
  - `productNames` 缺少 `@Size(max = 50)` 或服务端数量上限（当前 `ProjectNoticeBatchExportPo.productNames` 无约束、控制器未校验数量）
  - 幂等键、每用户配额与限流
