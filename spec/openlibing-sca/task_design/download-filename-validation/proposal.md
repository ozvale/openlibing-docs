# 92 download-filename-validation — 下载接口文件名白名单与响应头编码

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/92
（【安全】【安全威胁】文件下载接口 fileName 未校验，存在任意 OBS 对象访问与响应头注入风险）

`GET /open/download/file?fileName=xxx` 原先只做空值与 `tbl_export_data` 存在性校验，随后 `ExportUtils#getExportData2OBS` 把 `fileName` 原样拼进 `Content-Disposition` 并直接作为 OBS 对象键：

- 响应头未编码：`"attachment;" + "filename=" + fileName`，含 `\r\n` 时可注入额外响应头（T21）；
- 对象键无约束：`obsClient.getObject(bucketName, fileName)`，可越出导出对象命名空间（T19/T20）；
- 文件名可枚举、下载无频控（T22/T23）。

归类：CWE-22（Path Traversal）/ CWE-93（CRLF Injection，响应头注入）/ CWE-770（资源耗尽）。

## 功能描述

**做什么**：

1. 新增 `FileUtils#isValidDownloadFileName`（`analysis/utils/FileUtils.java`，L529）：
   - 长度 ≤ 200（`MAX_DOWNLOAD_FILE_NAME_LENGTH`）；
   - 拒绝前导 `.`、包含 `..`、控制字符（`c < 0x20` 或 `0x7F`）、路径分隔符 `/` `\`、百分号 `%`（防二次 URL 编码绕过）；
   - 要求扩展名落在导出链路实际产出的白名单 `xls` / `docx` / `json` / `pdf`（`DOWNLOAD_FILE_EXTENSIONS`，大小写不敏感）；
   - 允许中文等非 ASCII 字符，保持中文文件名下载可用。
2. `FileController#downloadFile` 在存在性查询与 OBS 下载**之前**调用白名单校验，非法返回"文件名不合法"，且不触达数据库与 OBS。
3. `ExportUtils#getExportData2OBS` 响应头改为 RFC 6266/5987 形式：`attachment; filename="<ASCII 回退>"; filename*=UTF-8''<percent 编码>`；ASCII 回退把非 `[A-Za-z0-9._-]` 字符替换为 `_`，UTF-8 percent 编码天然消除 CR/LF。
4. 同链路补充文件归属校验（`b48b09d6`，其 message 标注 `Refs #156`）：`/open/download/file` 新增必填 `userId`，`TblExportDataMapper#countByFileName` 改为 `#countByFileNameAndUserId`，SQL 增加 `and user_id = #{userId}`，他人导出文件返回"文件不存在"。

**不做什么**（本轮未覆盖）：

- 不强制 OBS 对象键前缀（`getExportData2OBS` 仍直接以 `fileName` 作为键，未拼接服务端导出前缀、未校验键归属前缀）；
- 不做接口级限流 / 并发下载上限，也未改为 OBS 临时签名 URL 直传；
- 不做下载审计日志（`FileController` 仅保留入参 `LOGGER.info`；原 `@LogApi` 注解已在 `a7e7bc1b` 统一移除，改由 `ScanLogHandler` 按 DTO 匹配，下载接口是否被覆盖未验证）；
- 不做 canonicalize 后再使用（改为"非白名单输入直接拒绝"）；
- 不校验 `userId` 的真实性（由调用方传入，服务端未与登录态绑定）。

## 验收标准

- [x] fileName 白名单/长度/扩展名校验生效，`..`、路径分隔符、CR/LF、URL 编码输入被拒绝（`FileUtilsTest#isValidDownloadFileName_shouldReject*` 4 组用例；`FileControllerTest#testDownloadFile_shouldRejectIllegalFileNameBeforeLookup` 覆盖 8 种非法名）
- [x] `Content-Disposition` 采用 RFC 5987/6266 编码，CRLF 注入用例无法注入响应头（`ExportUtilsTest#testGetExportData2OBS_CrlfCannotInjectContentDisposition`）
- [x] 中文文件名下载兼容（`ExportUtilsTest#testGetExportData2OBS_ContentDispositionEncodedForChineseName`、`FileControllerTest#testDownloadFile_shouldAcceptChineseFileName`）
- [ ] OBS 下载强制服务端键前缀，越界键访问被拒绝（本轮未覆盖：仍以校验后的 fileName 作为对象键）
- [ ] 接口具有限流/并发控制（本轮未覆盖）
- [ ] 下载操作有审计日志（本轮未覆盖 / 未验证）
- [ ] 文件归属校验：他人导出文件不可下载（部分满足）：`b48b09d6` 已按 `fileName + userId` 绑定查询
      （`FileControllerTest#testDownloadFile_shouldRejectFileOwnedByAnotherUser`），但 `userId` 由调用方
      传入、可伪造，传入受害者 `userId` 仍可取回他人导出；真实归属校验属 #156 授权体系范围
      （与 design.md 风险表一致）
- [ ] 相关单元测试通过、覆盖率达标（本次回溯未重新执行 `mvn test`）

## 影响范围

- 仓库：`openlibing-sca`（`analysis` 模块：Controller / Utils / Service / DAO / Mapper XML）。
- 接口：`GET /open/download/file` 新增**必填**参数 `userId`（不传返回"用户ID不得为空"），属契约变化；非法文件名统一返回"文件名不合法"。
- 数据访问：`tbl_export_data` 查询条件新增 `user_id`（`countByFileName` → `countByFileNameAndUserId`），无 schema 变更。
- 配置 / 部署：无。
