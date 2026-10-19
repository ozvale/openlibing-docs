# 构建产物安全编译选项导出功能 — 技术设计

> 跨仓 Full 模式技术设计文档。章节按 AGENTS.md 固定：1.方案设计 / 2.实现逻辑设计 / 3.类设计 / 4.数据模型设计 / 5.性能设计 / 6.API 接口设计 / 7.安全设计。

## 1. 方案设计

### 1.1 总体方案

复用 `openlibing-cicd-fork` 既有"测试结果报告导出"三段式（`submitTestCaseExportTask` → `doAsyncExport` → `performExcelExport`）+ `openlibing-framework` "我的导出"异步任务中心 + `openlibing-cicd-web` 既有导出 UI 体系（`ExportFloatPanel` + `useExportTaskStore` + `triggerDownloadByAnchor`），零新框架、零 schema 变化、零 framework 仓改动。

```
openlibing-cicd-web（前端）
  ① 产物包详情页顶部按钮区新增"导出"按钮
  ② 点击 → POST /build-artifact/sec-option/export（带 projectId + recordId）
  ③ 把 exportTaskId 注册到 useExportTaskStore，触发 ExportFloatPanel 浮窗 3 秒轮询
        │
        ▼
openlibing-cicd-fork（后端）
  ④ BuildArtifactController.exportSecOption
     → SecOptionScanService.submitSecOptionExportTask
     → 校验有可导出数据 → 拼 .xlsx 文件名
     → frameworkProjectClient.createExportTask（type=SEC_OPTION, identifier=projectId:recordId, data=JSON）
     → tryReuseSecOptionExport（命中历史 SUCCESS → OBS copyObject 复用，直接返回）
     → asyncTaskExecutor.submit(doSecOptionExport)  ← 异步触发
     → 返回 {exportTaskId, message: "导出任务已创建"}
  ⑤ doSecOptionExport（异步线程）：
     → queryExportTask(logId) 拿记录
     → updateExportTask(BUILDING) 抢锁（expectedMessages=[INITIALIZED, THROTTLED]）
     → Files.createTempFile("sec_option_export_", ".xlsx")
     → 查 overviewData.options + file_detail（含 raw_options/options/filing 关联）
     → performSecOptionExcelExport：EasyExcel 多 sheet 写
     → updateExportTask(UPLOADING)
     → ObsBucketService.uploadFile(objectKey, tempFile, fileName, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
     → updateExportTask(SUCCESS, objectKey)
     → finally: Files.deleteIfExists(tempFile)
  ⑥ 失败任意节点 → updateExportTask(FAILED)
        │
        ▼
openlibing-framework（无改动，仅 Feign 调用）
  ⑦ ExportController 提供 3 个内部接口：create / update / query
  ⑧ ExportController 提供 2 个前端接口：/export/list（我的导出列表）、/export/download-url（3 小时签名 URL）
  ⑨ CleanObsFileJob 每天凌晨 1 点清理 create_time 早于 3 天的记录与 OBS 对象
```

### 1.2 关键设计决策

| 决策点               | 选择                                                                                                          | 理由                                                                                                                                       |
| -------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 导出触发方式         | 异步任务 + framework 任务表登记 + OBS 上传 + 签名 URL 下载                                                    | 既有测试结果报告导出已验证的成熟模式；产物包文件数百级 × 14 项 × 双列时同步导出会卡 controller，异步 + OBS 是必然选择                      |
| Excel 生成库         | 阿里 EasyExcel（多 sheet 写）                                                                                 | 既有 pom 已依赖；TestCaseVo 已是 EasyExcel 注解范式；多 sheet 只需多次 `excelWriter.write(data, EasyExcel.writerSheet("name").build())`    |
| Summary sheet 列设计 | 与产物包详情页"安全编译选项汇总"表逐字对齐（7 列）                                                            | 用户验收标准要求"扫描项数和数据列一致"；离线 Excel 与在线页面同字段同顺序，便于人工比对                                                    |
| Detail sheet 列设计  | 文件路径 + 每扫描项两列（原始值 + 备案值）                                                                    | 用户验收标准要求"区分原始数据与备案数据，每个扫描项都设置两列"；未备案时备案值列留空（空字符串），Excel 筛选/排序友好                      |
| 未扫描项处理         | Summary sheet 不输出该行；Detail sheet 输出对应两列值为 `N/A`                                                 | Summary 与详情页"隐藏 UNSCANNED"行为一致；Detail 矩阵需要列对齐（每行同列数），未扫描项用 N/A 占位                                         |
| 缓存复用             | 按 `identifier = projectId:recordId` + `type=SEC_OPTION` + `statuses=[SUCCESS]` 查历史，命中则 OBS copyObject | 仿 `tryReuseTestResultExport`；用户重复点导出秒级返回；OBS copyObject 走服务端拷贝，无重新生成 IO                                          |
| 文件命名             | `安全编译选项_<packageName>_<yyyyMMdd_HHmmss>.xlsx`                                                           | 与既有 `generateReadableFileName` 风格一致；含产物包名 + 扫描时间便于归档识别；packageName 含特殊字符时按既有 sanitize 规则处理            |
| objectKey 命名       | `yyyy-MM-dd/UUID`                                                                                             | 与既有 `ObsBucketServiceImpl` 完全一致；framework 签名 URL 按此 key 签发                                                                   |
| 前端 UI 复用         | `ExportFloatPanel` + `useExportTaskStore` + `triggerDownloadByAnchor`                                         | master 分支已有成熟导出 UI 体系，不重复造轮子；`ExportSource` 类型加 `'sec-option'` 值即可区分任务来源                                     |
| 接口路径             | `POST /build-artifact/sec-option/export`                                                                      | 与既有 `/build-artifact/sec-option/overview`、`/file-detail`、`/filing/save` 同前缀，模块内聚                                              |
| 扫描项裁剪入参       | 后端 `optionKeys` 可选参数；前端本期不暴露                                                                    | 未来可能要支持"只导出 fortify 和 rpath"，先开后端能力但不暴露 UI；本期前端默认传 null/空数组，导出全部已扫描项                             |
| 任务状态机           | INITIALIZED → BUILDING → UPLOADING → SUCCESS / FAILED                                                         | 复用 cicd-fork 业务侧扩展的 `ExportStatus` 枚举（比 framework 多 BUILDING/THROTTLED）；framework 不感知 BUILDING/THROTTLED，仅做字符串匹配 |
| framework 仓改动     | 无                                                                                                            | framework "我的导出"能力已成熟，本需求只消费不改动；避免跨仓回归风险                                                                       |

### 1.3 流程模式与风险

**Full 模式**。判定依据：

- 跨仓（cicd-fork 后端 + cicd-web 前端 + framework 复用），改动规模约 400-600 行。
- 有外部接口变化（新增 1 个后端导出接口）。
- 无 schema 变化（复用 framework `obs_file` 表，不新增表，不修改 `sec_option_scan_*` 表）。
- 安全影响低（导出按钮与"查看详情"同等权限，无新凭证/无注入风险面扩展；项目隔离由 `projectId` 保证）。
- 部署/发布影响低（无新配置项，复用既有 `obs.export.bucket` 等）。

| 风险                                                           | 对策                                                                                                                                                                                      |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 大产物包（500+ ELF 文件 × 14 项 × 2 列）Excel 生成慢           | EasyExcel 流式写（分批 1000 行）；`asyncTaskExecutor` 线程池隔离，不阻塞 controller；前端浮窗 5 分钟超时但后端任务继续，用户可在下载中心继续查看                                          |
| EasyExcel 多 sheet 写时内存占用                                | `excelWriter.write` 按 sheet 顺序调用，每 sheet 分批 1000 行；`Files.createTempFile` 落临时文件，不内存缓存全部数据；finally 删临时文件                                                   |
| framework 状态机被并发抢占（多用户同时点同一 recordId 导出）   | `expectedMessages=[INITIALIZED, THROTTLED]` CAS 抢锁（仿 `acquireTaskLock`）；未抢到的消费者立即退出；缓存复用按 identifier 命中历史 SUCCESS 任务，OBS copyObject 秒级返回，不进异步流程  |
| OBS 上传失败                                                   | 失败回写 framework `FAILED`；前端浮窗展示"导出失败"，可重试（重试会新建任务，不删旧 FAILED 记录）                                                                                         |
| packageName 含特殊字符（`/` `\` `:` `*` `?` `"` `<` `>` `\|`） | 既有 `generateReadableFileName` 已实现 sanitize；本需求复用，不重新实现                                                                                                                   |
| 临时文件残留（JVM 异常退出）                                   | `Files.createTempFile` 在系统临时目录，OS 周期性清理；finally 块用 `Files.deleteIfExists` 兜底；framework `CleanObsFileJob` 清理 OBS 旧对象，不影响本地临时文件                           |
| 用户在导出过程中删除了备案记录导致 Excel 数据与详情页不一致    | 导出是某个时刻的快照，与详情页实时数据可能短暂不一致；这是异步导出的固有特性，与既有测试结果报告导出行为一致；前端浮窗提示"导出中"                                                        |
| cicd-web develop_202608_iter2 分支与 master 分支代码结构不一致 | 前端实现需在 develop_202608_iter2 分支上做；master 分支无 sec-option 相关 Vue 组件，需切到 develop_202608_iter2 才能拿到源码级列定义；本设计文档基于既有 demo.html 与 interface-design.md |

### 1.4 回滚

- 后端导出接口与既有 sec-option 查询接口隔离，回滚只需删除新增的 controller 方法与 service 方法，不影响既有能力。
- framework `obs_file` 表的导出任务记录在回滚后仍存在，3 天后由 `CleanObsFileJob` 自动清理，无需手动处理。
- 前端导出按钮隐藏即可回滚，不影响既有页面交互。

## 2. 实现逻辑设计

### 2.1 后端（openlibing-cicd-fork）

#### 2.1.1 入口 Controller（BuildArtifactController 新增端点）

新增 `POST /build-artifact/sec-option/export`，与既有 `/overview`、`/file-detail`、`/filing/save` 同前缀。流程：

1. 从 Cookie `token` 解析 `userId`（既有 sec-option 接口已实现，复用）。
2. `SecOptionScanService.submitSecOptionExportTask(userId, request)` 调用 service。
3. 返回 `DataResult<SecOptionExportVO>`（含 `exportTaskId` + `message`）。

#### 2.1.2 Service 三段式（SecOptionScanService 新增方法）

**第一段：submitSecOptionExportTask**（同步返回，仿 `submitTestCaseExportTask`）

1. **校验有可导出数据**：根据 `projectId + recordId` 查 `SecOptionScanRecordEntity`，不存在或 `overviewData.options` 全为未扫描时返回 `DataResult.failureMessage("无可导出的扫描数据")`。
2. **拼文件名**：`generateReadableFileName(record)` → `安全编译选项_<packageName>_<yyyyMMdd_HHmmss>.xlsx`，packageName 含特殊字符按既有 sanitize 规则处理；扫描时间取 `detectionCompletedAt`，未完成时取 `createTime`。
3. **组装 create 请求**：`ObsFileCreateRequestDTO` 设 `type=FileTypeEnums.SEC_OPTION.name()`、`identifier=projectId + ":" + recordId`、`fileName=readableFileName`、`data=JSON.toJSONString({projectId, recordId, optionKeys})`（注意 `data` 字段最长 500 字符，本需求 JSON 远小于此限制）。
4. **调 framework 创建**：`frameworkProjectClient.createExportTask(userId, requestDTO)` → 拿 `newLogId`。
5. **缓存复用**：`tryReuseSecOptionExport(newLogId, identifier, readableFileName, request)`：
   - 调 `queryExportTask(identifier + type + statuses=[SUCCESS] + limit=1)` 查 framework 历史。
   - 命中则 `obsBucketService.tryCopyCacheFile(历史.objectKey, newObjectKey, readableFileName)` + `updateExportTask(SUCCESS, objectKey=newObjectKey)`，直接返回 `TestCaseExportVO{exportTaskId, message: SUCCESS.desc}`，不进异步流程。
6. **异步触发**：未命中缓存则 `asyncTaskExecutor.submit(() -> doSecOptionExport(newLogId, request, readableFileName))`。
7. **返回**：`SecOptionExportVO{exportTaskId=String.valueOf(newLogId), message=ExportStatus.INITIALIZED.desc}`。

**第二段：doSecOptionExport**（异步线程，仿 `doAsyncExport`）

1. `queryExportTask(id=newLogId)` 拿 `ObsFileResponseDTO logEntity`。
2. **CAS 抢锁**：`updateExportLogStatus(logEntity, ExportStatus.BUILDING, expectedMessages=[INITIALIZED, THROTTLED])`（仿 `acquireTaskLock`）；影响行数=0 说明被其他消费者抢走，直接 return。
3. `Files.createTempFile("sec_option_export_", ".xlsx")` 建临时文件。
4. **executeSecOptionExportAndUpload**：
   - 查 `SecOptionScanRecordEntity` 拿 `overviewData`（含 options 数组、packageName、repoUrl、detectionCompletedAt 等）。
   - 查 `SecOptionScanFileDetailMapper` 拿该 `recordId` 下所有 file_detail 行（含 `file_path`、`raw_options`、`options`），按 `file_path` 升序排序。
   - 拼装 `SummarySheetRow` 列表与 `DetailSheetRow` 列表。
   - `performSecOptionExcelExport(tempFile, summaryRows, detailRows, scannedKeys)` 生成 Excel。
   - `updateExportLogStatus(logEntity, UPLOADING)`。
   - `obsBucketService.uploadFile(logEntity.getObjectKey(), tempFile, readableFileName, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")` 上传。
   - 成功 → `updateExportLogStatus(logEntity, SUCCESS)`；失败 → `updateExportLogStatus(logEntity, FAILED, errorMsg)`。
5. `finally`：`Files.deleteIfExists(tempFile)` 清理临时文件。

**第三段：performSecOptionExcelExport**（EasyExcel 多 sheet 写）

```java
// 关键骨架（不是最终代码，仅说明结构）
try (ExcelWriter excelWriter = EasyExcel.write(path.toFile())
        .registerWriteHandler(new LongestMatchColumnWidthStyleStrategy())
        .build()) {
  // Sheet1 "Summary"：动态表头 + 动态数据
  //   表头列：安全编译选项 / 描述 / 满足数 / 实际参与数 / 检测结果（覆盖率） / 已确认文件数 / 确认结果（覆盖率）
  //   数据行：每个 scanned=true 的扫描项一行
  List<List<String>> summaryHead = buildSummaryHead();
  List<List<Object>> summaryData = buildSummaryData(overviewData, scannedKeys);
  WriteSheet summarySheet = EasyExcel.writerSheet("Summary").head(summaryHead).build();
  excelWriter.write(summaryData, summarySheet);

  // Sheet2 "Detail"：动态表头（文件路径 + 每扫描项两列）+ 动态数据
  //   表头列：文件路径 / {opt1}-原始值 / {opt1}-备案值 / {opt2}-原始值 / {opt2}-备案值 / ...
  //   数据行：每个文件一行；未备案时备案值列留空字符串
  List<List<String>> detailHead = buildDetailHead(scannedKeys);
  List<List<Object>> detailData = buildDetailData(fileDetails, scannedKeys);
  WriteSheet detailSheet = EasyExcel.writerSheet("Detail").head(detailHead).build();
  excelWriter.write(detailData, detailSheet);
}
```

关键点：

- **动态表头**：因为扫描项是动态的（14 项中可能只有 8 项 scanned=true），用 `List<List<String>>` 而不是注解类；Summary sheet 表头固定 7 列，Detail sheet 表头 `1 + 2 * scannedKeys.size()` 列。
- **流式写**：本需求产物包文件数通常几十到几百级，不分批，一次性 `excelWriter.write`；如果未来出现千级文件，再加分批逻辑（仿 `performExcelExport` 的 1000/批）。
- **未备案留空**：Detail sheet 的备案值列，`rawOptions[key]` 有值但 `filedOptions[key]` 为 null 时，输出空字符串 `""`；不要输出 `"—"` 或 `"N/A"`（验收标准要求"未备案的文件-数据项置为空"）。
- **未扫描项处理**：Summary sheet 不输出该行；Detail sheet 输出对应两列值为 `"N/A"`（与详情页弹窗一致），保证矩阵对齐。

#### 2.1.3 Excel 列与详情页字段对齐

**Summary sheet（7 列）**

| Excel 列名         | 来源字段（`SecOptionRecordItem.overviewData.options[i]`）                              |
| ------------------ | -------------------------------------------------------------------------------------- |
| 安全编译选项       | `key`（如 `fortify`）                                                                  |
| 描述               | 14 项固定中文名 map（如 `fortify` → `_FORTIFY_SOURCE`），与详情页 `OPT_NAME[key]` 一致 |
| 满足数             | `yesCount`                                                                             |
| 实际参与数         | `applicableFiles`（= 满足数 + 不满足数，N/A 不参与）                                   |
| 检测结果（覆盖率） | `rate`（保留 1 位小数 + `%`，如 `86.1%`；未扫描项不输出该行，故无 N/A 场景）           |
| 已确认文件数       | `filedFiles`（该扫描项有备案记录的文件数）                                             |
| 确认结果（覆盖率） | `confirmationCoverage`（保留 1 位小数 + `%`）                                          |

**Detail sheet（1 + 2×N 列，N = scannedKeys.size()）**

| Excel 列名              | 来源字段                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------- |
| 文件路径                | `FileSecOptionItem.filePath`（包内相对路径）                                       |
| {扫描项中文名} - 原始值 | `FileSecOptionItem.rawOptions[key]`（`YES`/`NO`/`N/A`）                            |
| {扫描项中文名} - 备案值 | `FileSecOptionItem.filedOptions[key]`（已备案：`YES`/`NO`；未备案：空字符串 `""`） |

列序：`文件路径` → 按 14 项固定顺序（`bindNow, nx, pic, pie, relro, rpath, sp, strip, fortify, fvisibility, ftrapv, stackClash, fstackCheck, aslr`）展开的各扫描项两列；未扫描项不输出列（与详情页"隐藏 UNSCANNED"行为一致）。

> **关于未扫描项的 Detail 列**：如果选择"输出 N/A 占位列"会让 Excel 矩阵与详情页弹窗完全对齐（弹窗也是按 14 项全量列展示，未扫描项值 N/A）；如果选择"不输出列"则与详情页"隐藏 UNSCANNED"行为一致。本期采用**"不输出未扫描项的两列"**（与详情页隐藏规则一致），减少 Excel 宽度；如果未来需要全量列展示，调整 `scannedKeys` 为 14 项固定列表即可。

### 2.2 前端（openlibing-cicd-web）

#### 2.2.1 产物包详情页新增"导出"按钮

在产物包详情页（`/sec-option-detail` 路由对应的 Vue 组件）顶部按钮区，与"← 返回概览"、"待备案项列表（批量备案）"同组新增"导出"按钮：

```vue
<!-- 关键骨架，不是最终代码 -->
<el-button
  type="primary"
  size="small"
  :icon="Download"
  :loading="isExporting"
  @click="handleExport"
>
  导出
</el-button>
```

- 图标用 `@element-plus/icons-vue` 的 `Download`，或复用 master 分支既有 `src/assets/sca/export.png`。
- `loading` 状态绑定 `isExporting` ref，提交接口期间禁用按钮，防止重复点击。
- 按钮位置：放在"待备案项列表"按钮右侧，与既有按钮同 `header-actions` 区。

#### 2.2.2 handleExport 调用接口

```ts
// 关键骨架
async function handleExport() {
  if (!currentRecord?.id) return;
  isExporting.value = true;
  try {
    const resp = await exportSecOption({
      data: { projectId: currentRecord.projectId, recordId: currentRecord.id },
    });
    const exportTaskId = extractExportId(resp);
    if (exportTaskId) {
      // 注册到既有 exportTask store，触发浮窗轮询
      useExportTaskStore().addTask({
        exportTaskId,
        source: "sec-option",
        displayName: `安全编译选项_${currentRecord.packageName}`,
        createdAt: Date.now(),
      });
      ElMessage.success("导出任务已创建，请稍后在右下角浮窗查看");
    }
  } catch (e) {
    ElMessage.error("导出任务创建失败：" + (e.message || ""));
  } finally {
    isExporting.value = false;
  }
}
```

#### 2.2.3 复用既有导出 UI 体系

| 复用项                    | 路径                                                         | 用途                                                            |
| ------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------- |
| `ExportFloatPanel`        | `src/components/ExportFloatPanel/ExportFloatPanel.vue`       | 右下角浮窗，3 秒轮询任务状态，generating/ready/failed 三态      |
| `useExportTaskStore`      | `src/stores/exportTask.ts`                                   | Pinia store，任务列表 + 轮询 + sessionStorage 持久化 + 自动下载 |
| `triggerDownloadByAnchor` | `src/utils/triggerDownloadByAnchor.ts`                       | a 标签触发下载，跨域 download 属性 + 防缓存 `_t` 时间戳         |
| `DownloadCenterDialog`    | `src/views/pipeline/DownloadCenter/DownloadCenterDialog.vue` | 下载中心弹窗，按 exportId 过滤，自动停止轮询                    |
| `extractExportId`         | `src/utils/extractExportId.ts`                               | 从响应里提取 exportTaskId                                       |
| `pickExportDisplayName`   | `src/utils/pickExportDisplayName.ts`                         | 任务展示名挑选                                                  |
| `exportLogTaskStatus`     | `src/utils/exportLogTaskStatus.ts`                           | 导出任务状态归一化                                              |

`ExportSource` 类型加 `'sec-option'` 值，区分任务来源（与既有 `'pipeline-log'`、`'test-report'` 等并列）。

#### 2.2.4 API 文件新增

在 `src/api/secOption/api.ts`（或既有 `src/api/pipeline/api.ts`，按 cicd-web develop_202608_iter2 分支实际目录结构）新增：

```ts
// 关键骨架
export const exportSecOption: RequestFunc = (a, s) =>
  apiClient.post(urls.SEC_OPTION_EXPORT, a, s);
```

在 `src/api/secOption/url.ts`（或 `src/api/pipeline/url.ts`）新增：

```ts
export const SEC_OPTION_EXPORT = "/build-artifact/sec-option/export";
```

#### 2.2.5 浮窗与下载中心

- 浮窗：复用既有 `ExportFloatPanel`，无需改动；任务状态从 framework `/export/list` 或 `/export/detail` 接口拿到（前端既有逻辑已实现）。
- 下载中心：复用既有 `DownloadCenterDialog`，按 `exportTaskId` 过滤即可看到本次导出任务。
- 自动下载：复用 `useExportTaskStore` 的自动下载逻辑，状态变 `SUCCESS` 后通过 `GET /export/download-url?userId=&id=` 拿签名 URL，调 `triggerDownloadByAnchor` 触发浏览器下载。

## 3. 类设计

### 3.1 后端新增/修改类清单

| 类                                  | 路径（cicd-fork 内）                                  | 改动类型                                                                                                                             |
| ----------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `BuildArtifactController`           | `business/controller/BuildArtifactController.java`    | 修改（新增 `exportSecOption` 端点，复用既有 userId 解析）                                                                            |
| `SecOptionScanService`              | `business/service/SecOptionScanService.java`          | 修改（新增 `submitSecOptionExportTask` 方法签名）                                                                                    |
| `SecOptionScanServiceImpl`          | `business/service/impl/SecOptionScanServiceImpl.java` | 修改（实现三段式：submit + doAsync + performExcel；新增 `tryReuseSecOptionExport`、`buildSummaryHead/Data`、`buildDetailHead/Data`） |
| `SecOptionExportReqDTO`             | `dto/secoption/SecOptionExportReqDTO.java`            | 新增（入参：projectId / recordId / optionKeys?）                                                                                     |
| `SecOptionExportVO`                 | `vo/secoption/SecOptionExportVO.java`                 | 新增（出参：exportTaskId + message，仿 `TestCaseExportVO`）                                                                          |
| `FileTypeEnums`                     | `common/enums/FileTypeEnums.java`                     | 修改（新增 `SEC_OPTION("安全编译选项", "_secoption")` 枚举值）                                                                       |
| `FrameworkProjectClient`            | `business/feign/FrameworkProjectClient.java`          | 无改动（复用既有 `createExportTask` / `updateExportTask` / `queryExportTask` 三接口）                                                |
| `ObsBucketService`                  | `business/service/ObsBucketService.java`              | 无改动（复用既有 `uploadFile` + `tryCopyCacheFile`）                                                                                 |
| `ObsBucketServiceImpl`              | `business/service/impl/ObsBucketServiceImpl.java`     | 无改动                                                                                                                               |
| `ExportStatus`                      | `common/enums/ExportStatus.java`                      | 无改动（复用既有 INITIALIZED / BUILDING / UPLOADING / SUCCESS / FAILED）                                                             |
| `SecOptionScanRecordMapper`         | `business/mapper/SecOptionScanRecordMapper.java`      | 无改动（复用既有 `selectById` 拿 record）                                                                                            |
| `SecOptionScanFileDetailMapper`     | `business/mapper/SecOptionScanFileDetailMapper.java`  | 修改（新增 `selectByRecordIdForExport` 方法，返回导出所需字段：file_path + raw_options + options，按 file_path 升序）                |
| `SecOptionScanFileDetailMapper.xml` | `resources/mapper/SecOptionScanFileDetailMapper.xml`  | 修改（新增 `selectByRecordIdForExport` SQL，复用既有 LEFT JOIN sec_option_filing 逻辑拿备案值）                                      |

> **关于 `selectByRecordIdForExport` SQL**：与既有 `selectFileDetailPage` 查询逻辑一致（含 LEFT JOIN sec_option_filing 按 projectId + git_url + package_name + file_path + option_key 关联），但去掉分页、按 file_path 升序、字段精简为导出所需；不沿用 `selectFileDetailPage` 是因为后者带分页且字段更全（含 optionFilters 等），导出场景不需要。

### 3.2 前端新增/修改清单

| 文件                                                       | 改动类型 | 说明                                                      |
| ---------------------------------------------------------- | -------- | --------------------------------------------------------- |
| 产物包详情页 Vue 组件（`sec-option-detail` 路由对应文件）  | 修改     | 顶部按钮区新增"导出"按钮 + `handleExport` 方法            |
| `src/api/secOption/api.ts`（或 `src/api/pipeline/api.ts`） | 修改     | 新增 `exportSecOption` 函数                               |
| `src/api/secOption/url.ts`（或 `src/api/pipeline/url.ts`） | 修改     | 新增 `SEC_OPTION_EXPORT` URL 常量                         |
| `src/stores/exportTask.ts`                                 | 修改     | `ExportSource` 类型加 `'sec-option'` 值（其他逻辑无改动） |
| `src/components/ExportFloatPanel/ExportFloatPanel.vue`     | 无改动   | 复用                                                      |
| `src/utils/triggerDownloadByAnchor.ts`                     | 无改动   | 复用                                                      |
| `src/utils/extractExportId.ts`                             | 无改动   | 复用                                                      |

### 3.3 关键服务方法签名

```java
// SecOptionScanService 接口新增
DataResult<SecOptionExportVO> submitSecOptionExportTask(String userId, SecOptionExportReqDTO request);

// SecOptionScanServiceImpl 实现类新增
private void doSecOptionExport(Integer logId, SecOptionExportReqDTO request, String readableFileName);
private void performSecOptionExcelExport(Path path, List<SummarySheetRow> summaryRows,
    List<DetailSheetRow> detailRows, List<String> scannedKeys) throws IOException;
private boolean tryReuseSecOptionExport(Integer newLogId, String identifier,
    String readableFileName, SecOptionExportReqDTO request);
private void executeSecOptionExportAndUpload(ObsFileResponseDTO logEntity,
    SecOptionExportReqDTO request, Path tempFile) throws IOException;
private String generateSecOptionReadableFileName(SecOptionScanRecordEntity record);
private List<List<String>> buildSummaryHead();
private List<List<Object>> buildSummaryData(SecOptionOverviewData overviewData, List<String> scannedKeys);
private List<List<String>> buildDetailHead(List<String> scannedKeys);
private List<List<Object>> buildDetailData(List<SecOptionScanFileDetailEntity> files, List<String> scannedKeys);
```

> **不引入 SummarySheetRow / DetailSheetRow VO 类**：因为 EasyExcel 多 sheet 动态表头用 `List<List<String>>` 表头 + `List<List<Object>>` 数据更直接（无需为每个 sheet 定义注解类），与 `TestCaseVo` 注解模式不冲突；减少新增类数量。

## 4. 数据模型设计

### 4.1 无 schema 变化

本需求**不新增表，不修改表结构**：

- 复用 framework `obs_file` 表（已存在，changeSet id `20260820_create_table_obs_file`）登记导出任务记录。
- 复用 `sec_option_scan_record` 表查 overview_data（既有 JSON 字段含 options 数组、packageName、repoUrl、detectionCompletedAt 等）。
- 复用 `sec_option_scan_file_detail` 表查 file_path + raw_options + options（既有列，无需新增）。
- 复用 `sec_option_filing` 表关联备案值（既有 LEFT JOIN 逻辑）。

### 4.2 framework `obs_file` 表字段映射

| `obs_file` 列 | 本需求取值                                                                                                           |
| ------------- | -------------------------------------------------------------------------------------------------------------------- |
| `id`          | framework 自增主键，作为 `exportTaskId` 返回前端                                                                     |
| `type`        | `SEC_OPTION`（`FileTypeEnums.SEC_OPTION.name()`）                                                                    |
| `file_name`   | `安全编译选项_<packageName>_<yyyyMMdd_HHmmss>.xlsx`                                                                  |
| `object_key`  | `yyyy-MM-dd/UUID`（上传成功后回写）                                                                                  |
| `identifier`  | `projectId:recordId`（用于缓存复用按 identifier + SUCCESS 查历史）                                                   |
| `create_time` | framework 自动填充                                                                                                   |
| `update_time` | framework 自动更新                                                                                                   |
| `creator`     | 当前登录 userId                                                                                                      |
| `message`     | 状态机中文 desc：`导出任务已创建` → `导出文件生成中` → `正在上传文件` → `导出成功` / `导出失败：{原因}`（≤255 字符） |
| `data`        | `{"projectId":"...","recordId":123,"optionKeys":["fortify","rpath"]}` JSON（≤500 字符，远小于限制）                  |

### 4.3 既有表查询复用

**`sec_option_scan_record`**（导出时按 recordId 查单条）：

```sql
SELECT id, project_id, git_url, package_name, overview_data, detection_completed_at, create_time
FROM sec_option_scan_record
WHERE id = #{recordId} AND project_id = #{projectId}
```

**`sec_option_scan_file_detail` + LEFT JOIN `sec_option_filing`**（导出时按 recordId 查全量文件，复用既有 `selectFileDetailPage` 的 JOIN 逻辑但不分页）：

```sql
SELECT fd.file_path, fd.raw_options, fd.options,
       so.option_key AS filed_key, so.filing_value AS filed_value
FROM sec_option_scan_file_detail fd
LEFT JOIN sec_option_filing so
  ON so.project_id = fd.project_id
 AND so.git_url = fd.git_url
 AND so.package_name = fd.package_name
 AND so.file_path = fd.file_path
WHERE fd.record_id = #{recordId}
ORDER BY fd.file_path ASC
```

> **新增 Mapper 方法 `selectByRecordIdForExport`**：与既有 `selectFileDetailPage` 区别在于不分页、按 file_path 升序、字段精简（不含 optionFilters 等查询参数）；XML 复用既有 JOIN 模式但简化 WHERE。

## 5. 性能设计

### 5.1 异步任务隔离

- `asyncTaskExecutor` 线程池复用既有配置（与测试结果报告导出共用），不单独配置新池。
- controller 同步返回 < 100ms（仅 create framework 任务 + 触发 async），不阻塞 HTTP 线程。
- 异步线程内单次导出预计耗时：500 文件 × 14 项 × 2 列 = 14000 单元格，EasyExcel 写约 2-5 秒；OBS 上传 5-10 秒；总耗时 < 30 秒。

### 5.2 Excel 生成性能

- **流式写**：`EasyExcel.write` 默认流式（SXSSF），不内存缓存全部数据；本需求文件数几百级一次性 write 即可，无需分批。
- **动态表头**：`List<List<String>>` 表头 + `List<List<Object>>` 数据，EasyExcel 直接支持，无需注解类反射开销。
- **列宽自适应**：复用 `LongestMatchColumnWidthStyleStrategy`（与 `performExcelExport` 一致）。

### 5.3 数据查询性能

- `sec_option_scan_record` 按 `id` 主键查，O(1)。
- `sec_option_scan_file_detail` 按 `record_id` 查，复用既有 `idx_record_id` 索引；LEFT JOIN `sec_option_filing` 复用既有 `idx_filing_join` 复合索引（`project_id, git_url(128), package_name(64), file_path(128), option_key`）；排序按 `file_path` 升序走索引或 filesort（数百行级别可接受）。
- 不做内存分页（导出全量），避免 `subList` 开销。

### 5.4 缓存复用性能

- 按 `identifier + SUCCESS + limit=1` 查 framework 历史，O(1) 索引命中（`idx_obs_file_identifier`）。
- 命中时 OBS `copyObject` 走服务端拷贝，秒级返回，不进异步流程；用户重复点导出秒级拿到下载链接。

### 5.5 framework 任务表清理

- framework `CleanObsFileJob` 每天凌晨 1 点清理 `create_time` 早于 3 天的记录与 OBS 对象。
- 本需求导出文件 3 天后自动清理，与既有导出体系一致；用户可在下载中心或"我的导出"列表查看 3 天内的导出。

## 6. API 接口设计

### 6.1 新增导出接口

| 接口                                     | 方法签名                                                                                                                            | 说明                                                                       |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `POST /build-artifact/sec-option/export` | `exportSecOption(@RequestParam String userId, @Valid @RequestBody SecOptionExportReqDTO request)` → `DataResult<SecOptionExportVO>` | 触发异步导出，返回 exportTaskId；前端用此 id 轮询 framework `/export/list` |

**入参 `SecOptionExportReqDTO`**

| 字段         | 类型           | 必填 | 说明                                              |
| ------------ | -------------- | ---- | ------------------------------------------------- |
| `projectId`  | String         | 是   | 项目隔离                                          |
| `recordId`   | Long           | 是   | 扫描记录 ID（指定某次扫描）                       |
| `optionKeys` | List\<String\> | 否   | 限定导出的扫描项 key 列表；为空时导出全部已扫描项 |

**出参 `SecOptionExportVO`**

| 字段           | 类型   | 说明                                                      |
| -------------- | ------ | --------------------------------------------------------- |
| `exportTaskId` | String | framework 任务 id（前端轮询用）                           |
| `message`      | String | 状态 desc（初始 `导出任务已创建`，缓存命中时 `导出成功`） |

**鉴权**：与既有 `/build-artifact/sec-option/overview`、`/file-detail` 等接口一致，从 Cookie `token` 解析 `userId`，由 gateway 注入；项目级横向鉴权通过 `projectId` 隔离（既有 sec-option 接口已实现，复用）。

**错误码**：

| HTTP 状态 | 场景                                      | 返回体                                               |
| --------- | ----------------------------------------- | ---------------------------------------------------- |
| 200       | 任务创建成功                              | `DataResult.successData(SecOptionExportVO)`          |
| 200       | 无可导出数据（recordId 不存在或全未扫描） | `DataResult.failureMessage("无可导出的扫描数据")`    |
| 403       | 用户无该项目访问权限                      | `DataResult.failureMessage("无项目访问权限")`        |
| 500       | framework 调用失败                        | `DataResult.failureMessage("创建导出任务失败：...")` |

### 6.2 复用 framework 接口

| framework 接口                         | 调用方         | 用途                                                     |
| -------------------------------------- | -------------- | -------------------------------------------------------- |
| `POST /export/internal-server/create`  | cicd-fork 后端 | 创建导出任务记录，返回 id                                |
| `POST /export/internal-server/update`  | cicd-fork 后端 | 回写状态机 + objectKey                                   |
| `POST /export/internal-server/query`   | cicd-fork 后端 | 查历史 SUCCESS 任务用于缓存复用 + 查当前任务用于异步流程 |
| `GET /export/list?userId=&id=`         | cicd-web 前端  | "我的导出"列表，浮窗轮询任务状态                         |
| `GET /export/download-url?userId=&id=` | cicd-web 前端  | 获取 3 小时签名 URL，触发浏览器下载                      |

### 6.3 复用既有 sec-option 接口

| 既有接口                                      | 用途                                                  |
| --------------------------------------------- | ----------------------------------------------------- |
| `POST /build-artifact/sec-option/overview`    | 详情页基础信息 + 汇总数据来源（与 Excel Sheet1 同源） |
| `POST /build-artifact/sec-option/file-detail` | 文件矩阵弹窗数据来源（与 Excel Sheet2 同源）          |

> **关键点**：导出 Excel 的数据来源**直接走后端内部 Mapper 查询**，不通过前端调用 `/overview` 和 `/file-detail` 接口拿数据（避免 HTTP 自调用与序列化开销）；但**字段语义与这两个接口的出参严格对齐**，便于人工比对 Excel 与页面。

## 7. 安全设计

### 7.1 鉴权与项目隔离

- 导出按钮对有产物包详情页查看权限的用户全部可见（与"查看详情"同等权限，不引入新角色）。
- `userId` 从 Cookie `token` 解析（gateway 注入），不信任前端入参；与既有 sec-option 接口一致。
- 项目级横向鉴权：`projectId` 必填，后端校验当前 `userId` 是否有该 `projectId` 的访问权限（既有 sec-option 接口已实现，复用）。
- framework `obs_file` 表 `creator` 字段存当前 `userId`，framework `/export/list` 与 `/export/download-url` 接口均做 `creator = userId` 越权校验（framework 已实现，复用）。

### 7.2 输入校验

- `recordId` 必填且为正整数，后端校验存在性（`sec_option_scan_record` 表查不到时返回"无可导出的扫描数据"）。
- `projectId` 必填且非空字符串，后端校验格式（既有 sec-option 接口已实现）。
- `optionKeys` 可选，若非空则每项必须是 14 项固定枚举之一（`bindNow, nx, pic, pie, relro, rpath, sp, strip, fortify, fvisibility, ftrapv, stackClash, fstackCheck, aslr`），后端用枚举白名单校验，拒绝任意字符串。

### 7.3 敏感信息处理

- Excel 内容仅为扫描项值（`YES`/`NO`/`N/A`）与文件路径（包内相对路径，已由 `sec-option-scan-optimization` 插件源头相对化），不含 AK/SK、token、用户密码等敏感信息。
- OBS `objectKey` 为 `yyyy-MM-dd/UUID`，不含业务信息；framework `obs_file.data` 字段存 `{projectId, recordId, optionKeys}` JSON，不含敏感信息。
- framework 签名 URL 有效期 3 小时，过期后失效；用户需重新点导出获取新链接。

### 7.4 注入风险

- Excel 单元格值均为枚举（`YES`/`NO`/`N/A`/空字符串）或后端字段（packageName、filePath），不经用户输入；EasyExcel 写时自动转义特殊字符，无 CSV 公式注入风险（`=cmd|...` 等以 `=` 开头的值会被 EasyExcel 转义为文本）。
- SQL 查询全部用 MyBatis 参数化（`#{}` 占位符），无 SQL 注入风险。
- framework Feign 调用通过 HTTPS，无中间人风险。

### 7.5 速率限制

- 本需求不引入主动限流（与既有测试结果报告导出一致）。
- framework `obs_file` 表 `identifier` 字段为 `projectId:recordId`，同一用户对同一 recordId 重复点导出会命中缓存复用，OBS copyObject 秒级返回，不会重复生成 Excel。
- 如果出现恶意刷导出（不同 recordId 高频点击），可由 gateway 层做限流（既有 gateway 限流配置，不在本需求范围）。
