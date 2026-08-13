# Proposal: OSSinfo Extraction Notice API

## Summary

`POST /open/ossinfo/notice` 是一个异步接口，接收代码仓名称和软件列表，批量下载源码包后调用 `ossinfo_extraction` Python 工具提取版权与许可证信息，将各软件生成的 `Readme.opensource` 聚合为一个文件并上传到华为云 OBS（对象存储），供后续开源合规审计使用。

## Motivation

在开源合规场景中，需要对代码仓中使用的第三方开源软件进行版权与许可证信息提取。当前流程依赖人工或半自动化方式，效率低且难以规模化。该接口提供全自动化的批量处理能力：

1. **批量处理**：一次请求可包含多个软件条目，自动逐个下载、提取、聚合
2. **异步执行**：接口立即返回受理状态，实际处理在后台线程池完成，不阻塞调用方
3. **容错设计**：单个条目失败不影响其他条目，聚合文件非空即上传
4. **自动清理**：处理完成后自动清理临时工作目录和聚合目录，避免磁盘泄漏

## Scope

### 涉及文件

| 文件 | 角色 |
|------|------|
| `analysis/controller/OssInfoExtractionController.java` | REST 接口入口 |
| `analysis/service/OssInfoExtractionService.java` | 服务接口定义 |
| `analysis/service/impl/OssInfoExtractionServiceImpl.java` | 核心业务实现 |
| `analysis/entity/dto/OssInfoExtractionReq.java` | 请求体 DTO |
| `analysis/entity/dto/OssInfoExtractionItem.java` | 单条目 DTO |

### 核心方法

- `OssInfoExtractionController.extract(req)` — REST 接口入口，日志记录并委托 Service
- `OssInfoExtractionServiceImpl.extractAndUpload(req)` — 异步主流程，遍历 items 逐个处理并聚合上传
- `OssInfoExtractionServiceImpl.extractAndAppendItem(item, combinedFile)` — 单条目处理：下载→提取→定位→追加
- `OssInfoExtractionServiceImpl.downloadPackage(url, workDir)` — HTTP 下载源码包
- `OssInfoExtractionServiceImpl.runOssinfoExtraction(pkg, name, ver)` — 执行 Python 提取命令
- `OssInfoExtractionServiceImpl.uploadToObs(file, objectKey)` — 上传聚合文件到 OBS

### 不在范围内

- 不修改 `ossinfo_extraction` Python 工具本身
- 不提供处理结果查询接口（调用方自行查询 OBS）
- 不涉及 OBS 文件的清理/过期策略
- 不持久化任务状态或处理记录

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   调用方 POST /open/ossinfo/notice               │
│                   Body: { repoName, language, items[] }          │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
              ┌────────────────────────┐
              │  Controller.extract()  │  日志记录 repoName/language/itemsCount
              │  立即返回 200          │  委托 Service 异步处理
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  extractAndUpload()    │  @Async("syncFullThreadPool")
              │  创建聚合目录          │  objectKey = repoName + 时间戳 + .opensource
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  For each item         │
              │  ┌──────────────────┐  │
              │  │ downloadPackage  │  │  HTTP GET, 超时 600s
              │  └────────┬─────────┘  │
              │           ▼            │
              │  ┌──────────────────┐  │
              │  │ runOssinfo       │  │  python3 -m ossinfo_extraction, 超时 60min
              │  └────────┬─────────┘  │
              │           ▼            │
              │  ┌──────────────────┐  │
              │  │ locateReadme     │  │  定位 Readme.opensource
              │  └────────┬─────────┘  │
              │           ▼            │
              │  ┌──────────────────┐  │
              │  │ appendToCombined │  │  追加到聚合文件
              │  └────────┬─────────┘  │
              │           ▼            │
              │  ┌──────────────────┐  │
              │  │ cleanup workDir  │  │  清理单条目工作目录
              │  └──────────────────┘  │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  uploadToObs()         │  聚合文件非空 → 上传到 OBS
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  cleanupBatchDir()     │  清理批量聚合目录
              └────────────────────────┘
```

## Acceptance Criteria

1. 调用方发送 `POST /open/ossinfo/notice` 请求后，接口立即返回 200
2. 后台线程正确下载每个 item 的源码包并执行 `ossinfo_extraction`
3. 各软件生成的 `Readme.opensource` 被聚合到同一文件
4. 聚合文件非空时上传到 OBS，objectKey 格式为 `{repoName}{timestamp}.opensource`
5. 单个条目失败不影响其他条目处理
6. 所有临时目录在处理完成后被清理
7. 下载超时（600s）和 Python 执行超时（60min）正确生效
