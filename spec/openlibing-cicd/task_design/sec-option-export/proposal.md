# 构建产物安全编译选项导出功能

> 跨仓 Full 模式需求设计文档。涉及 `openlibing-cicd-fork`（后端异步导出 + Excel 生成 + framework 对接 + OBS 上传）、`openlibing-cicd-web`（前端导出按钮 + 复用既有导出任务浮窗与下载中心）、`openlibing-framework`（"我的导出"任务表与签名 URL 复用，无需改动）。
>
> 目标：在产物包详情页新增"导出"按钮，点击后异步生成包含两个 sheet 的 Excel——Summary sheet 对齐"安全编译选项汇总"表（扫描项×数据列）；Detail sheet 对齐"文件扫描结果总览"矩阵，每个扫描项拆分为"原始值/备案值"两列，未备案文件的备案值列置空，便于离线审计与外部对接。

## 1. 需求背景

安全编译选项扫描能力（`sec-option-scan-optimization` 需求已交付）已经在产物包详情页提供了"安全编译选项汇总"表（逐扫描项的满足数/实际参与数/检测覆盖率/已确认文件数/确认覆盖率）与"文件扫描结果总览"矩阵弹窗（文件路径 × 扫描项，含原始值与备案值）。但当前能力仅在线查看，无法满足以下场景：

| 场景                                            | 现状                                          | 目标                                                                                                           |
| ----------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 合规审计要求离线留痕                            | 仅在线查看，刷新后非最新数据；无导出件可归档  | 一键生成 Excel 留档，文件按产物包 + 扫描时间命名                                                               |
| 安全评审需将原始扫描值与备案值并排对比          | 弹窗内"备案值 + 划线原值"展示，离线场景不可用 | Detail sheet 每个扫描项拆为"原始值/备案值"两列，未备案时备案值列置空                                           |
| 上级单位/外部供应商要求统一格式 Excel           | 各项目自行拼表，格式不一                      | Summary sheet 列与详情页汇总表逐字对齐，Detail sheet 列与文件矩阵弹窗逐字对齐                                  |
| 大产物包（数百 ELF 文件 × 14 扫描项）导出耗时长 | 无现成导出能力                                | 复用 framework "我的导出"异步任务 + cicd-fork 既有测试报告导出三段式（INITIALIZED→BUILDING→UPLOADING→SUCCESS） |

`openlibing-cicd-fork` 仓已有"测试结果报告导出"（`PipelineServiceImpl.submitTestCaseExportTask` / `doAsyncExport` / `performExcelExport`）作为最贴合的接入模板：EasyExcel + framework 三接口（create/update/query）+ OBS 上传 + 状态机回写 + 缓存复用。本需求直接沿用该模式，不引入新的导出框架。

## 2. 功能描述

### 2.1 做什么

1. **前端**：在产物包详情页（`/sec-option-detail`）顶部按钮区，与"返回概览"、"待备案项列表（批量备案）"同组新增"导出"按钮（`btn btn-primary btn-sm`，导出图标用 master 分支既有 `src/assets/sca/export.png` 或 Element Plus `Download` 图标）。点击后调用新的后端导出接口 `POST /build-artifact/sec-option/export`，并将返回的 `exportTaskId` 注册到既有 `useExportTaskStore`，复用 `ExportFloatPanel` 浮窗（右下角，3 秒轮询，自动下载，超时 5 分钟，保留 3 天）与下载中心弹窗。
2. **后端**：在 `BuildArtifactController` 新增 `exportSecOption` 接口，`SecOptionScanService` 新增 `submitSecOptionExportTask` + `doSecOptionExport` + `performSecOptionExcelExport` 三段式（仿 `submitTestCaseExportTask`）：
   - 入参 `SecOptionExportReqDTO`：`projectId`（项目隔离）、`recordId`（指定某次扫描记录）、可选 `optionKeys`（限定导出的扫描项，默认全部已扫描项）。
   - 出参 `SecOptionExportVO`：`exportTaskId` + `message`（初始 `INITIALIZED`）。
   - 调 `frameworkProjectClient.createExportTask` 落任务记录 → `asyncTaskExecutor.submit` 异步执行 → Excel 生成 → OBS 上传 → framework 状态回写。
3. **Excel 结构**：
   - **Sheet1 "Summary"**：列与产物包详情页"安全编译选项汇总"表完全一致——`安全编译选项 / 描述 / 满足数 / 实际参与数 / 检测结果（覆盖率） / 已确认文件数 / 确认结果（覆盖率）`；每个已扫描项一行，未扫描项（`scanned=false`）不输出。
   - **Sheet2 "Detail"**：列与"文件扫描结果总览"矩阵弹窗对齐，但每个扫描项拆为两列（`{扫描项名} - 原始值` + `{扫描项名} - 备案值`）；列序：`文件路径` → 按 14 项固定顺序展开的各扫描项两列；行：每个文件一行；**未备案文件的备案值列留空**（不写"—"或"N/A"，Excel 单元格为空字符串），原始值列正常输出 `YES`/`NO`/`N/A`。
4. **文件命名**：`安全编译选项_<packageName>_<yyyyMMdd_HHmmss>.xlsx`（扫描时间取 `detectionCompletedAt`，与既有 `generateReadableFileName` 风格一致； packageName 含特殊字符时按既有 sanitize 规则处理）。
5. **缓存复用**：按 `identifier = projectId:recordId` + `type = SEC_OPTION` + `SUCCESS` 查 framework 历史任务，命中则 OBS `copyObject` 复用，避免重复生成；如果用户对同一记录重复点导出，命中缓存秒级返回。
6. **接入 framework "我的导出"**：导出文件统一上传到 framework 与 cicd-fork 共用的 OBS 桶（`obs.export.bucket`），`objectKey = yyyy-MM-dd/UUID`，与既有导出体系一致。用户在下载中心或 framework "我的导出"列表均可查到，签名 URL 有效期 3 小时（framework 既有 `SIGN_URL_EXPIRE_SECONDS = 10800`）。

### 2.2 不做什么

- **不做前端筛选**：导出按钮只发起整包导出，不前端选列；扫描项裁剪通过后端入参 `optionKeys` 支持，但本期前端不暴露该参数（默认全部已扫描项）。
- **不做模板下载**：不做"下载空模板让用户填备案值"的能力（那是 `sec-option-scan-optimization` 备选方案二文件上传解析的范畴，本期不实现）。
- **不修改 framework 仓**：framework "我的导出"能力已成熟（5 接口 + `obs_file` 表 + 3 小时签名 URL + 3 天清理 Job），本需求只消费不改动。
- **不修改产物包详情页其他交互**：导出按钮是新增项，不影响既有"返回概览"、"待备案项列表"、"文件扫描结果总览"弹窗。
- **不做异步进度条精确百分比**：状态机只用 framework `message` 字段（中文 desc），不引入实时百分比；前端用既有 `ExportFloatPanel` 三态（generating/ready/failed）。
- **不做权限收敛**：导出按钮对有产物包详情页查看权限的用户全部可见（与"查看详情"同等权限，不引入新角色）；项目隔离由后端 `projectId` 保证。

## 3. 验收标准

- [ ] 产物包详情页（`/sec-option-detail`）顶部按钮区新增"导出"按钮，样式与既有按钮一致（`btn btn-primary btn-sm` + 导出图标），位置在"待备案项列表"按钮右侧。
- [ ] 点击导出按钮 → 调用 `POST /build-artifact/sec-option/export`，返回 `{exportTaskId, message: "导出任务已创建"}`；前端立即把任务注册到 `useExportTaskStore`，`ExportFloatPanel` 浮窗出现"生成中"状态。
- [ ] 后端异步生成 Excel，状态流转 `INITIALIZED → BUILDING → UPLOADING → SUCCESS` 全部正确回写 framework `obs_file.message` 字段；失败任意节点回写 `FAILED`。
- [ ] Excel 文件名为 `安全编译选项_<packageName>_<yyyyMMdd_HHmmss>.xlsx`，扫描时间取 `detectionCompletedAt`；packageName 含特殊字符时被 sanitize（不出现 `/` `\` `:` `*` `?` `"` `<` `>` `|`）。
- [ ] Excel Sheet1 名为 `Summary`，列序与表头：`安全编译选项 / 描述 / 满足数 / 实际参与数 / 检测结果（覆盖率） / 已确认文件数 / 确认结果（覆盖率）`；每个已扫描项一行；未扫描项不输出；覆盖率保留 1 位小数 + `%`（如 `86.1%`），未扫描项本就不出现。
- [ ] Excel Sheet2 名为 `Detail`，列序：`文件路径` → 按 14 项固定顺序（`bindNow, nx, pic, pie, relro, rpath, sp, strip, fortify, fvisibility, ftrapv, stackClash, fstackCheck, aslr`）展开的各扫描项两列（`{扫描项中文名} - 原始值` + `{扫描项中文名} - 备案值`）；每个文件一行；未扫描项的对应两列输出 `N/A`（与详情页一致）或留空，本期采用"输出 N/A"以保持矩阵对齐；未备案文件的备案值列留空（空字符串）。
- [ ] 缓存复用：同一 `projectId + recordId` 重复点导出，命中 framework 历史 SUCCESS 任务时秒级返回，不重复生成 Excel。
- [ ] 文件上传到 `obs.export.bucket` 桶，`objectKey = yyyy-MM-dd/UUID`；Content-Type 为 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`；Content-Disposition 为 `attachment; filename*=utf-8''<URL编码文件名>`（中文文件名浏览器下载不乱码）。
- [ ] 前端浮窗生成完毕后自动触发下载（复用 `triggerDownloadByAnchor`），下载链接通过 `GET /export/download-url?userId=&id=` 拿到 framework 签发的 3 小时签名 URL。
- [ ] 失败场景：异步生成中任意异常（DB 查询失败 / EasyExcel 写失败 / OBS 上传失败）均回写 framework `FAILED` 状态，前端浮窗展示"导出失败"，可重试。
- [ ] 不修改 framework 仓任何代码（仅通过 Feign 调用 3 个既有接口）。

## 4. 影响范围

| 仓                     | 改动类型       | 说明                                                                                                                                                                                                                                                                                                                        |
| ---------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `openlibing-cicd-fork` | 新增代码       | `BuildArtifactController` 新增导出接口；`SecOptionScanService` 新增 `submitSecOptionExportTask` + `doSecOptionExport` + `performSecOptionExcelExport`；新增 `SecOptionExportReqDTO` / `SecOptionExportVO` / `SummarySheetRow` / `DetailSheetRow` VO；`FileTypeEnums` 新增 `SEC_OPTION("安全编译选项", "_secoption")` 枚举值 |
| `openlibing-cicd-web`  | 新增代码       | 产物包详情页（`sec-option-detail` 路由对应 Vue 组件）顶部按钮区新增"导出"按钮；调用既有 `useExportTaskStore` + `ExportFloatPanel` + `triggerDownloadByAnchor`；`ExportSource` 类型加 `'sec-option'` 值；API 文件新增 `exportSecOption` 函数与 URL 常量                                                                      |
| `openlibing-framework` | 无改动         | 仅通过 Feign 调用 `ExportController` 既有 5 个接口（`/export/internal-server/create`、`/update`、`/query` + `/export/list`、`/download-url`）                                                                                                                                                                               |
| `openlibing-docs`      | 新增 spec      | `spec/openlibing-cicd/task_design/sec-option-export/` 下 `proposal.md` + `design.md` + `tasks.md` + `export-demo.html`                                                                                                                                                                                                      |
| 数据库                 | 无 schema 变化 | 复用 framework `obs_file` 表（已存在）；不新增表，不修改 `sec_option_scan_*` 表                                                                                                                                                                                                                                             |

## 5. 关联文档

- 上游需求：[`sec-option-scan-optimization/proposal.md`](../sec-option-scan-optimization/proposal.md)（安全编译选项扫描能力优化，已交付，提供产物包详情页与文件矩阵弹窗基础）
- 上游接口：[`sec-option-scan-optimization/interface-design.md`](../sec-option-scan-optimization/interface-design.md)（`/overview`、`/file-detail` 出参字段，本需求 Excel 列直接对齐这些字段）
- 上游 demo：[`sec-option-scan-optimization/demo.html`](../sec-option-scan-optimization/demo.html)（产物包详情页 + 文件矩阵弹窗交互原型，本需求 `export-demo.html` 在其基础上增加导出按钮与导出后浮窗）
- 接入参考：`openlibing-cicd-fork` 仓 `PipelineServiceImpl.submitTestCaseExportTask` + `doAsyncExport` + `performExcelExport`（既有测试结果报告导出三段式）
- framework 能力：`openlibing-framework` 仓 `ExportController` + `ObsServiceImpl` + `FrameworkObsUtil` + `CleanObsFileJob`
