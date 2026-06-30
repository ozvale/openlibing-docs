# Tasks: OSSinfo Extraction Notice API

## Task 1: REST 接口层 ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/controller/OssInfoExtractionController.java`

- [x] `@RestController` + `@RequestMapping("/open/ossinfo")`
- [x] `@PostMapping("/notice")` 接口
- [x] `@Valid @RequestBody OssInfoExtractionReq` 参数校验
- [x] `@Operation` Swagger 注解（summary/description/tags）
- [x] 日志记录 repoName、language、itemsCount
- [x] 委托 `ossInfoExtractionService.extractAndUpload(req)`
- [x] 返回 `ResponseEntity.success()`

## Task 2: 请求体 DTO ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/entity/dto/OssInfoExtractionReq.java`

- [x] `@Data` Lombok 注解
- [x] `repoName` 字段 `@NotBlank`
- [x] `language` 字段可选
- [x] `items` 字段 `@NotEmpty` + `@Size(max=50)` + `@Valid` 级联校验（上限防止单次请求耗尽线程池/磁盘/耗时过长）

**文件**: `src/main/java/com/openlibing/sca/analysis/entity/dto/OssInfoExtractionItem.java`

- [x] `@Data` Lombok 注解
- [x] `downloadUrl` 字段 `@NotBlank` + `@Pattern("^https?://.+$")`（格式校验） + SSRF 防护：拒绝 localhost/127.0.0.0/8、内网地址段（10.0.0.0/8、172.16.0.0/12、192.168.0.0/16）、云元数据地址（169.254.169.254）
- [x] `softwareName` 字段 `@NotBlank`
- [x] `softwareVersion` 字段 `@NotBlank`

## Task 3: 服务接口定义 ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/OssInfoExtractionService.java`

- [x] 接口方法 `void extractAndUpload(OssInfoExtractionReq req)`
- [x] Javadoc 说明异步行为与单条目失败不影响其他条目

## Task 4: 异步主流程 extractAndUpload ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/OssInfoExtractionServiceImpl.java`

- [x] `@Service` + `@Async("syncFullThreadPool")`
- [x] 构造 objectKey = `{repoName}{yyyyMMddHHmmssSSS}.opensource`，`/` 替换为 `-`
- [x] 创建聚合目录 `ossinfo-combined-*`
- [x] 遍历 items 逐个调用 `extractAndAppendItem`
- [x] 单个条目 `ScaException` 仅记录日志，继续处理下一个
- [x] 聚合文件存在且非空时调用 `uploadToObs`
- [x] 聚合文件为空时 WARN 日志并跳过上传
- [x] `ScaException` 和通用 `Exception` 分别捕获
- [x] `finally` 块调用 `cleanupBatchDir` 清理聚合目录

## Task 5: 单条目处理 extractAndAppendItem ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/OssInfoExtractionServiceImpl.java`

- [x] 创建临时工作目录 `ossinfo-extraction-*`
- [x] 调用 `downloadPackage` 下载源码包
- [x] 调用 `runOssinfoExtraction` 执行 Python 命令
- [x] 调用 `locateReadmeOpensource` 定位输出文件
- [x] 调用 `appendToCombinedFile` 追加到聚合文件
- [x] `ScaException` 直接抛出，`InterruptedException` 转为 `ScaException`，通用 `Exception` 转为 `ScaException`
- [x] `finally` 块清理工作目录

## Task 6: 源码包下载 downloadPackage ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/OssInfoExtractionServiceImpl.java`

- [x] 共享 `HttpClient` 实例（连接池复用，connectTimeout 60s，followRedirects NORMAL）
- [x] 请求超时 `DOWNLOAD_TIMEOUT_SECONDS = 600`
- [x] HTTP 状态码非 200 → `ScaException`
- [x] 文件不存在或大小为 0 → `ScaException`
- [x] `extractFileName` 从 URL path 提取真实文件名，保留原始压缩格式
- [x] 文件名提取失败回退到 `package.zip`

## Task 7: Python 进程管理 runOssinfoExtraction ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/OssInfoExtractionServiceImpl.java`

- [x] 命令：`python3 -m ossinfo_extraction -t <pkg> -n <name> -v <ver>`
- [x] `ProcessBuilder` 启动进程，工作目录为源码包所在目录
- [x] `CompletableFuture` 并发消费 stdout/stderr（避免缓冲区满死锁）
- [x] `Process.waitFor(PYTHON_TIMEOUT_MINUTES=60, MINUTES)` 超时等待
- [x] 超时 → `destroyForcibly` + 日志记录 stdout/stderr + 抛 `ScaException`
- [x] 退出码非 0 → 日志 + 抛 `ScaException`
- [x] 字符集使用 `file.encoding` 系统属性，回退 UTF-8
- [x] `safeJoinStreamFuture` 等待流读取线程最多 60s，超时取消

## Task 8: Readme.opensource 定位与追加 ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/OssInfoExtractionServiceImpl.java`

- [x] `locateReadmeOpensource` 先在工作目录根寻找
- [x] 未找到则 `findFile` 递归查找
- [x] 仍未找到 → `ScaException("Readme.opensource not generated")`
- [x] `appendToCombinedFile` 使用 `StandardOpenOption.CREATE + WRITE + APPEND` 追加模式
- [x] `InputStream.transferTo(OutputStream)` 流式复制

## Task 9: OBS 上传 uploadToObs ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/OssInfoExtractionServiceImpl.java`

- [x] 通过 `ObsClientFactory.getObsClient()` 获取客户端
- [x] `putObject(bucketName, objectKey, fis)` 上传
- [x] Bucket 名称来自 `@Value("${sca.notice.obs.bucketName}")`
- [x] `ObsException | IOException` 捕获 → `ScaException`
- [x] `finally` 块关闭 `FileInputStream` 和 `ObsClient`

## Task 10: 临时目录清理 cleanupBatchDir ✅

**文件**: `src/main/java/com/openlibing/sca/analysis/service/impl/OssInfoExtractionServiceImpl.java`

- [x] `FileUtils.deleteDirectory` 递归删除目录
- [x] null 参数安全处理
- [x] `IOException` 捕获并记录日志，不影响主流程
