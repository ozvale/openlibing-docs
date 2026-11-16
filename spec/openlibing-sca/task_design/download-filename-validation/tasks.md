# 92 download-filename-validation — 实现任务

## 进度: 5/5 complete

- [x] Task 1: `FileUtils#isValidDownloadFileName` 白名单校验（长度/字符集/扩展名/中文兼容）（`b52cf276`）
- [x] Task 2: `FileController#downloadFile` 在存在性查询与下载前拦截非法文件名（`b52cf276`）
- [x] Task 3: `ExportUtils#getExportData2OBS` 响应头改 RFC 6266/5987 双写（`b52cf276`）
- [x] Task 4: 补白名单/响应头编码/中文名单测（`FileUtilsTest`、`ExportUtilsTest`、`FileControllerTest`）（`b52cf276`）
- [x] Task 5: 下载文件归属绑定 `userId`：`countByFileName` → `countByFileNameAndUserId`，Controller 增加必填 `userId` 与空值校验（`b48b09d6`，其 message 关联 #156）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                                     | 关联                                                             |
| ---------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| `b52cf276` | fix(analysis): validate download file name and encode disposition header | `Refs #92`                                                       |
| `b48b09d6` | fix(analysis): enforce export file ownership on download                 | `Refs #156`（同链路的归属校验，issue #92 的攻击场景 3 依赖此项） |

关键 diff：

- `FileUtils`：新增 `MAX_DOWNLOAD_FILE_NAME_LENGTH = 200`、`DOWNLOAD_FILE_EXTENSIONS = {"xls","docx","json","pdf"}` 与 `isValidDownloadFileName`（+37 行）。
- `FileController`：`if (!FileUtils.isValidDownloadFileName(fileName)) return ResponseEntity.failure("文件名不合法");` 位于 `countExportDataByFileName` 之前；`b48b09d6` 增加 `@RequestParam("userId")` 与空值校验。
- `ExportUtils`：`Content-Disposition` 由字符串拼接改为 `filename`（ASCII 回退）+ `filename*=UTF-8''<percent>`。
- `TblExportDataMapper(.xml)`：`countByFileNameAndUserId`，SQL 增加 `and user_id = #{userId}`。
- 测试增量：`FileUtilsTest` +45 行（4 组用例）、`ExportUtilsTest` +64 行（2 个用例）、`FileControllerTest` +39/+37 行、`OpenScanServiceImplTest` +19 行。

验证方式：

- 单测：本地 UT 日志（`5_ut.log`，2026-11-14）显示 `FileUtilsTest` 28 个用例、`ExportUtilsTest` 9 个用例、`FileControllerTest` 5 个用例、`OpenScanServiceImplTest` 27 个用例全部通过；本次回溯未重新执行 `mvn test`。
- 静态核实：`FileController` 校验顺序为 空值 → `userId` 空值 → 白名单 → 存在性 → 下载；`ExportUtils` 响应头不含原始 `fileName` 拼接。
- 覆盖率：未验证。

## 备注：与 issue 验收项的差异

issue 还要求"OBS 键前缀约束、接口限流/并发控制、下载审计日志、OBS 临时签名 URL 直传"。本轮均未覆盖：`getObject(bucketName, fileName)` 仍直接使用校验后的文件名，无前缀约束；下载链路无限流；`FileController` 无审计日志（`@LogApi` 已在 `a7e7bc1b` 统一移除，是否由 `ScanLogHandler` 覆盖未验证）。
