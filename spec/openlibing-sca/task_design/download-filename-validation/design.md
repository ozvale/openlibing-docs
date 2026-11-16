# 92 download-filename-validation — 技术设计

## 方案概述

两层收敛：

- **入口层**：`FileController` 在查库与下载前用 `FileUtils#isValidDownloadFileName` 做严格白名单判定，非法即拒，不做任何规范化改写（避免"校验值 ≠ 使用值"）。
- **输出层**：`ExportUtils` 的 `Content-Disposition` 改为 `filename`（ASCII 回退）+ `filename*`（UTF-8 percent）双写，CR/LF 无法进入响应头，中文名可正常显示。

第二提交 `b48b09d6` 在同一链路上把存在性查询绑定到 `userId`，关闭"按文件名下载他人导出"的横向越权（其 message 关联 #156）。

## 架构决策

| 决策                                 | 证据 / 理由                                                                                                                                                                                           |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 白名单"直接拒绝"而非"清洗/规范化" | 导出文件名由服务端生成，形态固定（`{community}-{repo}-{yyyyMMddHHmmss}.xls/.docx/.json/.pdf`）；只要拒绝非白名单输入，就能保证"校验值 = 查库值 = OBS 键值 = 响应头值"一致，不会出现规范化前后两套语义 |
| D2 拒绝字符集合覆盖四类绕过          | 控制字符（含 CR/LF，CWE-93）、`/` `\`（路径分隔符）、`..` 与前导 `.`（遍历/隐藏文件）、`%`（防 `%2e%2e` 二次编码绕过）                                                                                |
| D3 扩展名白名单收窄到 4 种           | 以导出链路实际产出为准（`xls` / `docx` / `json` / `pdf`）；`xlsx`、`txt` 等一律拒绝，避免放宽面                                                                                                       |
| D4 长度上限 200                      | 覆盖 `{community}-{repo}-{14 位时间戳}.docx` 的最长实际组合，同时限制异常长输入                                                                                                                       |
| D5 保留中文能力                      | 不要求 ASCII：校验只拒绝危险字符与非法扩展名；响应头通过 `filename*=UTF-8''<percent>` 表达中文，`+` 额外替换为 `%20` 以免被解析为空格                                                                 |
| D6 ASCII 回退名替换为下划线          | `[^A-Za-z0-9._\-]` → `_`，保证 `filename` 段不含引号、反斜杠、控制字符，老客户端也不会触发头分裂                                                                                                      |
| D7 归属校验用 `userId` 绑定          | `countByFileNameAndUserId(fileName, userId)` 与下载使用同一 `fileName`，他人文件名查询返回 0 行，直接"文件不存在"，不泄露文件是否存在                                                                 |
| D8 不引入 OBS 键前缀                 | 本轮未做：`getObject(bucketName, fileName)` 未加前缀约束，属残余面（见风险表）                                                                                                                        |

## 关键实现（当前代码）

```
// FileUtils#isValidDownloadFileName
if (StringUtils.isEmpty(fileName) || fileName.length() > 200) return false;
if (fileName.startsWith(".") || fileName.contains("..")) return false;
for (char c : fileName.toCharArray()) {
  if (c < 0x20 || c == 0x7F || c == '/' || c == '\\' || c == '%') return false;
}
String extension = fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase(Locale.ROOT);
return Set.of("xls", "docx", "json", "pdf").contains(extension);
```

```
// ExportUtils#getExportData2OBS
String encodedFileName = URLEncoder.encode(fileName, UTF_8).replace("+", "%20");
String asciiFallback = fileName.replaceAll("[^A-Za-z0-9._\\-]", "_");
response.setHeader("Content-Disposition",
    "attachment; filename=\"" + asciiFallback + "\"; filename*=UTF-8''" + encodedFileName);
```

## 涉及文件

| 文件                                                                                  | 操作 | 说明                                                                                                      |
| ------------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/utils/FileUtils.java`                      | 修改 | 新增 `isValidDownloadFileName`、`MAX_DOWNLOAD_FILE_NAME_LENGTH`、`DOWNLOAD_FILE_EXTENSIONS`（`b52cf276`） |
| `src/main/java/com/openlibing/sca/analysis/controller/FileController.java`            | 修改 | 下载前白名单拦截（`b52cf276`）；新增必填 `userId` 并传入存在性校验（`b48b09d6`）                          |
| `src/main/java/com/openlibing/sca/analysis/utils/ExportUtils.java`                    | 修改 | `Content-Disposition` 改 RFC 6266/5987 双写（`b52cf276`）                                                 |
| `src/main/java/com/openlibing/sca/analysis/dao/TblExportDataMapper.java`              | 修改 | `countByFileName` → `countByFileNameAndUserId`（`b48b09d6`）                                              |
| `src/main/resources/mapper/analysis/TblExportDataMapper.xml`                          | 修改 | SQL 增加 `and user_id = #{userId}`（`b48b09d6`）                                                          |
| `src/main/java/com/openlibing/sca/analysis/service/OpenScanService.java`              | 修改 | `countExportDataByFileName(fileName, userId)`（`b48b09d6`）                                               |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`     | 修改 | 委托新 Mapper 方法（`b48b09d6`）                                                                          |
| `src/test/java/com/openlibing/sca/analysis/utils/FileUtilsTest.java`                  | 修改 | 新增 4 组白名单用例（`b52cf276`）                                                                         |
| `src/test/java/com/openlibing/sca/analysis/utils/ExportUtilsTest.java`                | 修改 | 中文名编码与 CRLF 注入用例（`b52cf276`）                                                                  |
| `src/test/java/com/openlibing/sca/analysis/controller/FileControllerTest.java`        | 修改 | 非法名前置拒绝、中文名放行（`b52cf276`）；空 `userId`、他人文件拒绝（`b48b09d6`）                         |
| `src/test/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImplTest.java` | 修改 | 归属查询用例（`b48b09d6`，+19 行）                                                                        |

## 风险 & 缓解

| 风险                                                                | 缓解                                                                                                                       |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 新增导出类型（如 `xlsx`）被白名单拒下载                             | 扩展名集合集中在一处常量，新增类型时同步更新并补用例                                                                       |
| 老客户端只认 `filename`，中文名显示为下划线                         | 双写 `filename` + `filename*`；现代浏览器优先 `filename*`，老客户端至少可下载（名字不美观）                                |
| 仍以 `fileName` 直接作为 OBS 对象键，未强制导出前缀                 | 残余：入口校验已排除 `..`、分隔符、`%`，无法构造越界键；但同桶对象命名仍依赖上游生成规范，建议后续加前缀约束（本轮未覆盖） |
| 无频控，重复请求大文件可占用带宽                                    | 未覆盖，建议后续在网关/接口层限流                                                                                          |
| `userId` 由调用方传入可伪造                                         | 本轮未与服务端登录态绑定；属 #156 授权体系范围，未验证                                                                     |
| 存在性校验命中后文件名被复用，若 `tbl_export_data.file_name` 被污染 | 同一份 `fileName` 先过白名单再查库与下载，污染值也必须满足白名单才能进入下载                                               |

## 跨仓影响

无代码级依赖。接口新增必填 `userId` 会影响调用方（前端/集成方），需同步传参；OBS bucket 结构不变。
