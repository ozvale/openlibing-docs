# Design: OSSinfo Extraction Notice API

## 概述

`POST /open/ossinfo/notice` 接口提供异步批量提取开源软件版权与许可证信息，并将生成的 `Readme.opensource` 文件上传到 OBS（对象存储）的能力。

**核心特征**：接口为异步受理模式，立即返回 200 仅表示请求已受理；实际的下载、提取、聚合、上传操作在 `syncFullThreadPool` 线程池中异步执行，调用方需通过查询 OBS 目标对象确认最终结果。

## Architecture

```
OssInfoExtractionController (REST)
    │
    │  POST /open/ossinfo/notice
    │  @Valid @RequestBody OssInfoExtractionReq
    │
    └── OssInfoExtractionService.extractAndUpload(req)  [@Async("syncFullThreadPool")]
            │
            ├── 遍历 req.items，逐个处理：
            │    ├── 1. 创建临时工作目录 (ossinfo-extraction-*)
            │    ├── 2. 下载源码包 (HttpClient, 超时 600s)
            │    ├── 3. 执行 ossinfo_extraction Python 命令 (超时 60min)
            │    ├── 4. 定位 Readme.opensource 输出文件
            │    ├── 5. 追加到聚合文件
            │    └── 6. 清理单个条目工作目录
            │
            ├── 聚合文件非空 → 上传到 OBS
            └── 清理批量聚合目录
```

## API Design

### Controller: OssInfoExtractionController

| 属性 | 说明 |
|------|------|
| 路径 | `@RestController` + `@RequestMapping("/open/ossinfo")` |
| 接口 | `POST /open/ossinfo/notice` |
| 鉴权 | 无应用层鉴权（由网关/网络策略控制） |
| 响应 | `ResponseEntity.success()` — 仅表示受理成功 |

**日志**：记录 `repoName`、`language`、`itemsCount` 三个关键参数。

### 请求体: OssInfoExtractionReq

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `repoName` | String | `@NotBlank` | 代码仓名称，用于构造 OBS objectKey |
| `language` | String | 可选 | 软件语言生态（java/python/go/nodejs），用于选择下载镜像 |
| `items` | List\<OssInfoExtractionItem\> | `@NotEmpty` `@Size(max=50)` `@Valid` | 待提取的软件列表。上限 50 条，防止单次请求耗尽线程池/磁盘/耗时过长 |

### 请求体子项: OssInfoExtractionItem

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `downloadUrl` | String | `@NotBlank` `@Pattern("^https?://.+$")` + 编程校验拒绝内网/云元数据 IP | 软件源码压缩包下载地址。格式校验由正则完成；SSRF 防护由编程逻辑校验目标 IP，拒绝 localhost、内网地址段（10/8、172.16/12、192.168/16）、云元数据地址（169.254.169.254） |
| `softwareName` | String | `@NotBlank` | 软件名称 |
| `softwareVersion` | String | `@NotBlank` | 软件版本号 |

## Service Design

### OssInfoExtractionService 接口

```java
@Async("syncFullThreadPool")
void extractAndUpload(OssInfoExtractionReq req);
```

方法立即返回，实际工作在后台线程池执行。

### OssInfoExtractionServiceImpl 实现

#### 核心常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `README_OPENSOURCE_FILE_NAME` | `Readme.opensource` | 输出文件名 |
| `WORK_DIR_PREFIX` | `ossinfo-extraction-` | 临时目录前缀 |
| `DOWNLOAD_TIMEOUT_SECONDS` | 600 | HTTP 下载超时（秒） |
| `PYTHON_TIMEOUT_MINUTES` | 60 | Python 进程执行超时（分钟） |
| `STREAM_READER_JOIN_MILLIS` | 60000 | 流读取线程等待超时（毫秒） |

#### 配置依赖

| 配置项 | 说明 |
|--------|------|
| `sca.notice.obs.bucketName` | OBS 目标 Bucket 名称 |

#### 主流程: extractAndUpload

1. **构造 objectKey**：`{repoName}{yyyyMMddHHmmssSSS}.opensource`，其中 `/` 替换为 `-`
2. **创建聚合目录**：`ossinfo-combined-*`，含聚合文件
3. **遍历 items**：逐个调用 `extractAndAppendItem`，单个失败不影响其他（仅记录日志）
4. **上传判断**：聚合文件存在且非空才上传到 OBS
5. **finally 清理**：删除批量聚合目录

#### 子流程: extractAndAppendItem（单条目处理）

1. 创建临时工作目录 `ossinfo-extraction-*`
2. **downloadPackage**：HTTP GET 下载源码包，超时 600s，支持重定向，状态码非 200 或文件为空时抛异常
3. **runOssinfoExtraction**：执行 `python3 -m ossinfo_extraction -t <pkg> -n <name> -v <ver>`
4. **locateReadmeOpensource**：先在工作目录根寻找 `Readme.opensource`，未找到则递归查找
5. **appendToCombinedFile**：将 Readme.opensource 内容以追加模式写入聚合文件
6. **finally 清理**：删除工作目录

#### Python 进程管理 (runOssinfoExtraction)

- 使用 `CompletableFuture` 并发消费 stdout/stderr，避免子进程因缓冲区满而死锁
- 主线程仅调用 `Process.waitFor(60, MINUTES)` 等待
- 超时则 `destroyForcibly` + 日志记录已读取输出
- 退出码非 0 时记录 stdout/stderr 并抛异常
- 进程退出后等待流读取线程最多 60 秒（`STREAM_READER_JOIN_MILLIS`），超时取消

#### 文件名提取 (extractFileName)

从下载 URL path 最后一段提取文件名，保留原始压缩格式（.zip/.tar/.tar.gz/.tgz/.tar.bz2/.tbz2）。提取失败回退到 `package.zip`。

#### OBS 上传 (uploadToObs)

- 通过 `ObsClientFactory` 获取 OBS 客户端
- 调用 `putObject(bucketName, objectKey, inputStream)` 上传
- 异常时抛出 `ScaException(500, "upload Readme.opensource failed")`
- finally 中关闭 FileInputStream 和 ObsClient

## Error Handling

| 场景 | 行为 |
|------|------|
| 单个条目提取失败 | 记录日志（含 downloadUrl/softwareName/softwareVersion），继续处理下一个 |
| 下载失败 | `ScaException(500)`，该条目跳过 |
| Python 执行超时/失败 | `ScaException(500)`，该条目跳过 |
| Readme.opensource 未生成 | `ScaException(500)`，该条目跳过 |
| 全部条目失败 | 聚合文件为空，跳过 OBS 上传 |
| OBS 上传失败 | 记录日志，不阻断主流程 |
| 工作目录清理失败 | 记录日志，不影响主流程 |

**异步注意事项**：由于 `@Async` 机制，后台线程中的异常不会回传给 HTTP 调用方。调用方无法通过 HTTP 响应判断处理是否成功。

## File Structure

```
src/main/java/com/openlibing/sca/analysis/
├── controller/
│   └── OssInfoExtractionController.java      # REST 接口
├── service/
│   ├── OssInfoExtractionService.java          # 服务接口
│   └── impl/
│       └── OssInfoExtractionServiceImpl.java  # 服务实现
└── entity/dto/
    ├── OssInfoExtractionReq.java              # 请求体 DTO
    └── OssInfoExtractionItem.java             # 单条目 DTO
```

## Dependencies

| 依赖 | 用途 |
|------|------|
| `java.net.http.HttpClient` | 下载源码包 |
| `com.obs.services.ObsClient` | 上传到华为云 OBS |
| `org.apache.commons.io.FileUtils` | 清理临时目录 |
| `ossinfo_extraction` (Python CLI) | 提取版权与许可证信息 |
| Spring `@Async` + `syncFullThreadPool` | 异步执行 |

## Limitations

1. **无结果回调**：调用方无法通过 HTTP 响应获知处理结果，需自行查询 OBS 确认
2. **无状态追踪**：不持久化任务状态，无重试/补偿机制
3. **Python 环境依赖**：部署节点必须安装 `ossinfo_extraction` Python 包
4. **磁盘空间**：源码包下载和临时解压需充足磁盘空间
5. **单线程串行处理**：items 逐个处理，非并行
