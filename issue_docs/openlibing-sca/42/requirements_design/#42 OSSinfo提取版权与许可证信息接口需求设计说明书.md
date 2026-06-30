# #42 OSSinfo提取版权与许可证信息接口需求设计说明书

## 1. 基础信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/42
* **需求名称**: OSSinfo提取版权与许可证信息异步接口
* **开发责任人**: musheng

---

## 2. 需求场景说明

> 在开源合规场景中，需要对代码仓中使用的第三方开源软件进行版权与许可证信息提取。当前流程依赖人工或半自动化方式，效率低且难以规模化。通过提供 REST 接口，接收代码仓名称和软件列表，异步批量下载源码包后调用 `ossinfo_extraction` Python 工具提取版权与许可证信息，将各软件生成的 `Readme.opensource` 聚合为一个文件并上传到华为云 OBS，供后续开源合规审计使用。

**场景描述**：调用方通过 `POST /open/ossinfo/notice` 提交代码仓名称和待提取软件列表（含下载地址、软件名称、版本号），接口立即返回受理状态，后台异步线程逐个下载源码包、执行 Python 提取命令、聚合 `Readme.opensource` 文件并上传到 OBS。

---

## 3 需求验收标准

- [x] 调用方发送 `POST /open/ossinfo/notice` 请求后，接口立即返回 200
- [x] 请求体参数校验：`repoName` 非空、`items` 非空、每个 item 的 `downloadUrl` 符合 http/https 格式、`softwareName` 和 `softwareVersion` 非空
- [x] 后台线程正确下载每个 item 的源码包并执行 `ossinfo_extraction`
- [x] 各软件生成的 `Readme.opensource` 被聚合到同一文件
- [x] 聚合文件非空时上传到 OBS，objectKey 格式为 `{repoName}{timestamp}.opensource`
- [x] 单个条目失败不影响其他条目处理，异常仅记录日志
- [x] 所有临时目录（工作目录和聚合目录）在处理完成后被清理
- [x] 下载超时（600s）和 Python 执行超时（60min）正确生效
- [x] 聚合文件为空时跳过 OBS 上传并记录 warn 日志

---

## 4. 需求设计与分解

### 4.1 核心逻辑方案

接口 `extractAndUpload` 的核心数据流如下：

```
┌─────────────────────────────────────────────────────────────────┐
│                   调用方 POST /open/ossinfo/notice               │
│                   Body: { repoName, language, items[] }          │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Controller 受理                                        │
│  日志记录 repoName/language/itemsCount                           │
│  委托 ossInfoExtractionService.extractAndUpload(req)             │
│  立即返回 ResponseEntity.success()                               │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: 异步主流程 extractAndUpload                             │
│  @Async("syncFullThreadPool")                                    │
│  构造 objectKey = {repoName}{yyyyMMddHHmmssSSS}.opensource       │
│  "/" 替换为 "-"                                                  │
│  创建聚合目录 ossinfo-combined-*                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: 遍历 req.items 逐个处理                                 │
│  for (OssInfoExtractionItem item : req.getItems())              │
│    ├─ 创建临时工作目录 ossinfo-extraction-*                      │
│    ├─ downloadPackage(item.downloadUrl, workDir)                │
│    │    → HTTP GET, 超时 600s, 支持重定向                         │
│    │    → 从 URL path 提取真实文件名，保留压缩格式                  │
│    │    → 状态码非200或文件为空 → ScaException                     │
│    ├─ runOssinfoExtraction(packageFile, name, version)           │
│    │    → python3 -m ossinfo_extraction -t <pkg> -n <name>      │
│    │      -v <ver>                                               │
│    │    → CompletableFuture 并发消费 stdout/stderr               │
│    │    → Process.waitFor(60, MINUTES) 超时等待                   │
│    │    → 超时 → destroyForcibly + 抛异常                         │
│    │    → 退出码非0 → 记录 stdout/stderr + 抛异常                 │
│    ├─ locateReadmeOpensource(workDir)                            │
│    │    → 先在工作目录根寻找，未找到则递归查找                       │
│    ├─ appendToCombinedFile(readmeFile, combinedFile)             │
│    │    → 流式追加到聚合文件                                       │
│    ├─ finally: cleanupBatchDir(workDir)                          │
│    └─ ScaException → 记录日志，continue 处理下一个                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: 上传聚合文件                                            │
│  聚合文件存在且非空 → uploadToObs(combinedFile, objectKey)        │
│  聚合文件为空 → WARN 日志，跳过上传                                │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: finally 清理聚合目录                                    │
│  cleanupBatchDir(batchDir)                                       │
└─────────────────────────────────────────────────────────────────┘
```

**关键设计决策**：

1. **异步受理模式**：接口立即返回 200 表示请求已受理，实际处理在 `syncFullThreadPool` 线程池异步执行。后台线程的异常不会回传给调用方，调用方需通过查询 OBS 目标对象确认处理结果。
2. **单条目容错**：遍历 items 时，单个条目失败（下载失败、Python 执行超时/异常、Readme.opensource 未生成）仅记录日志并跳过，不影响其他条目处理。
3. **聚合上传**：所有成功条目的 `Readme.opensource` 追加到同一个聚合文件，最终一次性上传到 OBS。全部失败时聚合文件为空，跳过上传。
4. **Python 进程管理**：使用 `CompletableFuture` 并发消费 stdout/stderr 避免子进程因缓冲区满而死锁；主线程仅调用 `Process.waitFor` 等待，超时则 `destroyForcibly`；进程退出后等待流读取线程最多 60 秒，超时取消。
5. **文件名保留**：从下载 URL 提取真实文件名，保留原始压缩格式（.zip/.tar/.tar.gz/.tgz/.tar.bz2/.tbz2），提取失败回退到 `package.zip`。
6. **自动清理**：每个条目的工作目录和批量聚合目录均在 finally 块中清理，避免磁盘泄漏。

### 4.2 接口设计

##### 4.2.1 提取版权与许可证信息接口

- **URL**: `POST /open/ossinfo/notice`
- **Controller**: `OssInfoExtractionController`
- **请求体**:

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `repoName` | String | `@NotBlank` | 代码仓名称，用于构造 OBS objectKey |
| `language` | String | 可选 | 软件语言生态（java/python/go/nodejs） |
| `items` | List\<OssInfoExtractionItem\> | `@NotEmpty` `@Valid` | 待提取的软件列表 |

**OssInfoExtractionItem**:

| 字段 | 类型 | 校验 | 说明 |
|------|------|------|------|
| `downloadUrl` | String | `@NotBlank` `@Pattern("^https?://.+$")` | 软件源码压缩包下载地址 |
| `softwareName` | String | `@NotBlank` | 软件名称 |
| `softwareVersion` | String | `@NotBlank` | 软件版本号 |

- **返回**: `ResponseEntity.success()` — 仅表示请求受理状态
- **调用方**: 外部系统 / 上游编排服务

##### 4.2.2 OBS 上传

- **Bucket**: `${sca.notice.obs.bucketName}`
- **ObjectKey**: `{repoName}{yyyyMMddHHmmssSSS}.opensource`（`/` 替换为 `-`）
- **调用方**: `OssInfoExtractionServiceImpl.uploadToObs()`

### 4.3 配置清单

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `sca.notice.obs.bucketName` | OBS 目标 Bucket 名称 | - |

### 4.4 任务清单

| 任务 ID | 任务描述 (Task Description) | 预期产出 (Deliverables) | 预期工作量（人天） |
|---------|---------------------------|----------------------|-------------|
| **task1** | 实现 OssInfoExtractionController REST 接口 | Controller 类代码 | **0.5** |
| **task2** | 实现 OssInfoExtractionReq / OssInfoExtractionItem DTO | DTO 类代码 | **0.5** |
| **task3** | 实现 OssInfoExtractionServiceImpl 核心业务逻辑（下载/提取/聚合/上传/清理） | Service 实现类代码 | **2** |
| **task4** | 编写单元测试（正常流程/单条目失败/全部失败/超时场景） | 测试类代码 | **1** |

---

## 5. 需求相关性分析

### A. 安全相关性分析

* [ ] **边界变更**：新增公网端口、修改防火墙规则、变更网关配置。
* [ ] **凭证处理**：涉及密钥（Secret/Key）、Token、证书的存储或分发。
* [ ] **权限调整**：修改权限模型、服务账号（SA）权限或鉴权逻辑。
* [x] **供应链**：引入新的第三方二进制文件、SDK 或重大版本依赖升级。
  > 依赖 `ossinfo_extraction` Python 工具，部署节点需预装该包。
* [ ] **隐私风险评估**：涉及用户个人数据的处理。
* [ ] **AI使用**：涉及AIGC能力应用，并提供服务。

### B. 架构设计相关性分析

* [ ] A环节判定需要完成安全设计
* [ ] 改变了现有系统的物理/逻辑拓扑
* [x] 新增或大幅修改对外暴露的 API/CLI 接口
  > 新增 `POST /open/ossinfo/notice` 接口。
* [ ] 引入了新的中间件、数据库或三方核心组件

### C. 系统集成测试相关性分析

* [ ] 上述环节判定需要执行安全设计或架构设计。
* [ ] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。
* [ ] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
* [ ] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
* [ ] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑。

### D. 用户体验相关性分析

* [ ] **交互逻辑变更**：涉及 Web 门户、控制台或命令行工具的交互流程调整。
* [ ] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。
* [ ] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
* [ ] **无障碍与多语种**：涉及国际化支持、辅助功能或不同终端的适配。

### 5.1 需求相关性分析汇总结果

* [ ] need_security (需架构设计（含安全威胁分析和安全设计）)
* [ ] need_design (需架构设计)
* [ ] need_itest (需执行测试策略设计和全链路集成测试)
* [ ] need_ux (需架构设计（含UX设计)）
* [ ] need_light (上述均未勾选，走快速合入通道)

---
