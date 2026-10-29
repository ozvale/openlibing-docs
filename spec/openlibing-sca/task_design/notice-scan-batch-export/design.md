# notice-scan-batch-export — 技术设计

## 1. 方案设计

一句话：新增异步批量导出——逐制品按既有对象 key 规则从 NOTICE 桶下载合并文档，段级解析后跨制品去重重组成单个 NOTICE，经 framework 统一导出任务交付。

```text
前端 → POST /project/notice/scan/exportBatch（productNames 集合 + userId）
     → Service.exportNoticeBatch
        1) 校验 + 入参去重；逐制品查最新扫描记录（跳过缺失）
        2) 全部缺失 → ScaException（不建任务）
        3) 创建统一导出任务（INITIALIZED）→ 立即返回 VO(taskId, fileName, 导出任务已创建)
        4) 提交专用线程池：doExportBatch
           逐制品 executor.downloadObsObjectText(objectKey)
           → NoticeBatchMerger.mergeProductNotices(docs)（段落去重 + License 去重 + 表格去重）
           → 写临时文件 → executor.uploadFileToExportBucket(临时文件, targetObjectKey, fileName)
           → markExportTask SUCCESS（有跳过时注明数量）；异常 → markExportTask FAILED
           → finally 清理临时文件
```

架构决策：

- **下载源用对象 key 规则而非 `merged_oss_url`**：签名 URL 有时效且随时可能过期；既有 `/export` 已按 `<sanitized>/open-source-notice-<sanitized>.md` 定位，本接口沿用（`merged_oss_url` 仅作文件已生成的存在性判断）。
- **段级去重而非重新走 detail 表重建**：每制品 1 次 OBS GET（对比 detail 重建的每软件 1 次），量级最优；段落分隔行 `Software: <名> <版本>` 由同一套生成代码产出，作为去重键稳定可靠。
- **复用 `NoticeMerger` 包私有能力**（`buildHeader` / `collapseDuplicateLicenses`）：合并器 `NoticeBatchMerger` 放同包 `dm/util`。
- **专用小线程池**（core 1 / max 2 / 队列 50 / daemon，`notice-batch-export-` 命名）：批量导出偶发，隔离避免占用公共池；拒绝时标记任务失败并提示稍后再试。
- **复用统一导出任务类型 `project_notice`**：framework《我的导出》下载链路不变。

## 2. 实现逻辑设计

`exportNoticeBatch(List<String> productNames, String userId)`：

1. `userId` 空白 / `productNames` 空集合 → `ScaException(60000, "导出失败", ...)`。
2. `LinkedHashSet` 去空白去重；逐制品 `selectLatestByProjectName` → 记录存在且 `mergedOssUrl` 非空的制品；缺失记入 skipped。
3. 可导出制品为空 → `ScaException(60000, "导出失败", "所选制品均无已生成的NOTICE文件")`。
4. `fileName = "open-source-notice-merged-" + yyyyMMddHHmmss + ".md"`；创建导出任务（data 里记 productNames + skipped）。
5. 提交后台任务；`RejectedExecutionException` → 标记任务失败 + `ScaException("导出任务繁忙，请稍后重试")`。
6. 返回 `ProjectNoticeExportVO(taskId, fileName, "导出任务已创建")`。

`doExportBatch(...)`（包私有，便于单测直调）：

1. 逐制品 `downloadObsObjectText`；单制品下载失败记 warn 跳过（与其他制品隔离）。
2. `NoticeBatchMerger.mergeProductNotices(docs)` → 合并文本。
3. `Files.createTempFile("notice-batch-", ".md")` 写入；`uploadFileToExportBucket(temp, targetObjectKey, fileName)`；finally `cleanFile(temp)`。
4. 成功 → `markExportTask(taskId, "导出成功"（或注明跳过数）, targetObjectKey, [导出任务已创建])`；任一步异常 → `markExportTask(FAILED)` 并记日志。

`NoticeBatchMerger.mergeProductNotices(List<String>)`：

- 每文档按行扫描：headerEnd=首个 `Software: ` 行；footerStart=首个 `**This software contains software` 行；两者间按 `Software: ` 起始行切段。
- 段落去重：`LinkedHashMap<段首行文本, 段落文本>`（同软件同版本保留首次）。
- License 去重：各段落顺序过 `NoticeMerger.collapseDuplicateLicenses(section, seenLicenses)`（共享 seen）。
- Footer：收集各文档 footerStart 后的表格行（`|` 开头且非表头/分隔行），用 `(?<!\\)\|` 切列，按前两列（名称,版本）去重保留首次；GPLv2 声明段仅输出一次。
- 解析不到任何段落的文档跳过（warn），全空时返回 null → 调用方置任务失败。
- 头部用 `NoticeMerger.buildHeader()`。

## 3. 类设计

| 类                                  | 位置                                                                                                   | 操作      | 说明                                                                                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------ | --------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProjectNoticeBatchExportPo`        | `analysis/entity/dto`                                                                                  | 新增      | `List<String> productNames`                                                                                                                 |
| `NoticeBatchMerger`                 | `dm/util`                                                                                              | 新增      | 段级解析 + 跨制品去重合并（复用 NoticeMerger 包私有方法）                                                                                   |
| `ProjectNoticeScanExecutor`         | `dm/util`                                                                                              | 修改      | 新增 `downloadObsObjectText(objectKey)`、`uploadFileToExportBucket(path, key, fileName)`（与 transfer 共享 Content-Disposition 元数据构建） |
| `ProjectNoticeScanService` / `Impl` | `dm/service`                                                                                           | 修改      | 新增 `exportNoticeBatch` + `doExportBatch` + 专用线程池字段                                                                                 |
| `ProjectNoticeScanController`       | `dm/controller`                                                                                        | 修改      | 新增 `POST /exportBatch`（userId query + body PO）                                                                                          |
| 单测                                | `NoticeBatchMergerTest`（新增）、`ProjectNoticeScanServiceImplTest`、`ProjectNoticeScanControllerTest` | 新增/修改 | 覆盖合并算法与同步/后台路径                                                                                                                 |

## 4. 数据模型设计

无表结构变更。只读复用 `tbl_project_notice_scan`（`selectLatestByProjectName`）。

## 5. 性能设计

- OBS GET 次数 = 制品数；内存峰值 ≈ Σ单制品文档大小 + 合并结果（用户选择不设上限，已知风险：目录级制品文档可达数十 MB，大批量时内存占用高——由调用方控制规模，设计记录不做代码拦截）。
- 合并为纯内存字符串操作；上传走导出桶单次 PUT。
- 线程池隔离，慢任务不阻塞 Web 线程与其他业务池。

## 6. API 接口设计

`POST /project/notice/scan/exportBatch?userId=<创建者>`

```json
{ "productNames": ["openEuler-24.03", " MindCluster-v1.0 "] }
```

成功响应（异步受理）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "exportTaskId": 101,
    "fileName": "open-source-notice-merged-20261014130000.md",
    "message": "导出任务已创建"
  }
}
```

失败：`code=60000, message="导出失败", data`=原因（userId 不能为空 / productNames 不能为空 / 所选制品均无已生成的NOTICE文件 / 导出任务繁忙）。

## 7. 安全设计

- 输入：productNames 仅作为 DB 查询参数（MyBatis 参数化）与对象 key 拼接前先过既有 `sanitizeFileName`（与 `/export` 相同路径规则），无命令/SQL 注入面；不新增 URL/出站目标可控点（objectKey 由服务端规则推导）。
- 输出：导出桶对象 key 随机 UUID，不透出内部桶名；下载文件名固定模式，无用户可控路径。
- 失败安全：后台失败必置任务失败，避免"成功但无文件"；临时文件 finally 清理。
- 审计：沿用 info 级入参日志 + 任务失败 error 日志。

## 风险 & 缓解

- 单制品文档异常（缺 Software 段/损坏）→ 解析跳过该文档并 warn，不影响整批。
- 大批量内存峰值高 → 用户已确认不设上限，风险由调用方控制；必要时后续加配置化上限。
- 线程池队列打满 → 拒绝时任务置失败并提示稍后再试。

## 跨仓影响

- 无（framework 统一导出任务复用既有 `project_notice` 类型）。
