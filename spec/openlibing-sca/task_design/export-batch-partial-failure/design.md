# #134 — 技术设计

## 方案概述

把「下载失败」从执行器内部静默丢弃改为显式结果：`downloadObsObjectTexts` 返回成功文档与失败 objectKey 两个列表；`doExportBatch` 据此区分全部成功、部分失败、全部失败三种终态，部分失败时只回填任务状态（不回填 objectKey），并跳过合并上传。同时把 OBS 下载线程池的无界队列改为有界队列 + 调用方执行策略。

## 数据流（修复后）

```
exportNoticeBatch（受理，建立 framework 导出任务 INITIALIZED，提交 batchExportExecutor）
  └─ doExportBatch
       ├─ downloadObsObjectTexts(objectKeys)
       │     ├─ 并行读取（8 线程池，有界队列 256 + CallerRunsPolicy）
       │     └─ BatchDownloadResult(docs, failedObjectKeys)  # 顺序与入参一致
       ├─ failed 非空 && docs 非空 → buildPartialFailedMessage → markExportTask(部分失败文案, objectKey=null) → return
       ├─ docs 为空 → merge null → ScaException → catch → markExportTask(导出失败)
       └─ 全部成功 → NoticeBatchMerger.mergeProductNotices → 临时文件 → uploadFileToExportBucket
                     → markExportTask(导出成功, targetObjectKey)
  finally: cleanFile(tempFile)
```

## 架构决策

| 决策                                          | 理由                                                                                                                |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| D1 用 record `BatchDownloadResult` 承载双结果 | 不改调用方集合语义（docs 仍按入参顺序），新增失败明细，避免再查询/反推失败项                                        |
| D2 部分失败回填文案而非置「导出失败」         | 保留「已导出 X/Y」进度信息，用户可判断是否需要重新导出，且与全失败区分                                              |
| D3 部分失败不回填 objectKey、直接 return      | framework `getDownloadUrl` 按 message 精确 equals「导出成功」校验；回填 objectKey 会制造可下载但不完整的文件        |
| D4 文案截断到 255 并保留「等 N 个」           | 满足 framework `obs_file.message` 列与 `@Size(255)` 校验，避免因超长写库失败导致状态丢失                            |
| D5 `CallerRunsPolicy` 而非拒绝策略            | 队列打满时退化为提交线程执行，既不丢任务也不抛拒绝异常；提交方本就被 `batchExportExecutor` 限流（2 线程 + 队列 50） |
| D6 失败 objectKey → 制品名反向映射            | 日志/文案面向业务用户展示制品名；映射缺失时回退展示 objectKey                                                       |

## 涉及文件

| 文件                                                                                     | 操作 | 说明                                                                                                                                               |
| ---------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanServiceImpl.java`     | 修改 | `doExportBatch` 部分失败分支；新增 `EXPORT_MESSAGE_MAX_LENGTH`、`buildPartialFailedMessage`、`joinedLength`                                        |
| `src/main/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutor.java`                | 修改 | `downloadObsObjectTexts` 返回 `BatchDownloadResult`；新增 `OBS_DOWNLOAD_QUEUE_CAPACITY=256`、`CallerRunsPolicy`；新增 `BatchDownloadResult` record |
| `src/test/java/com/openlibing/sca/dm/service/impl/ProjectNoticeScanServiceImplTest.java` | 修改 | 部分失败/截断用例，既有用例适配新返回类型                                                                                                          |
| `src/test/java/com/openlibing/sca/dm/util/ProjectNoticeScanExecutorTest.java`            | 修改 | 下载结果含失败明细、空入参空结果的断言                                                                                                             |

## 风险 & 缓解

| 风险                                                                        | 缓解                                                                       |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 部分失败任务不可下载引发用户误解                                            | 任务 message 明确「已导出 X/Y … 下载失败：a、b … 请重新发起导出」          |
| 文案超长导致 framework 写库失败                                             | 按 255 预算裁剪名称列表，保留「等 N 个」总数概括；单测断言 ≤255            |
| `CallerRunsPolicy` 使提交线程（batchExport 线程）同步执行下载，拉长任务耗时 | 队列 256 相对单批数十 key 余量充足，仅异常积压时触发；不阻塞 Web 线程      |
| 失败项映射不到制品名                                                        | `keyToName.getOrDefault(objectKey, objectKey)` 回退展示 objectKey          |
| 既有调用方误用 `downloadObsObjectTexts` 的 `List` 返回                      | 编译期强制适配（已同步修改全部调用点与单测）                               |
| 部分失败分支未清理临时文件                                                  | 该分支在创建临时文件之前 return，`finally` 中 `tempFile == null`，无需清理 |

## 跨仓影响

无代码级跨仓依赖；导出任务状态与下载链接由 openlibing-framework（`obs_file` / `getDownloadUrl`）消费，本次仅利用其「message 精确等于导出成功」的既有校验，不改契约。spec 文档归档 openlibing-docs 仓（本目录）。
