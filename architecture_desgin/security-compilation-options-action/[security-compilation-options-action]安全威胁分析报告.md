# security-compilation-options-action 项目安全威胁分析报告

**分析日期：** 2026-10-09
**分析版本：** 分支 `full-check-update` / commit `4a2caef`
**分析方法：** STRIDE-A 威胁建模
**项目仓库：** https://gitcode.com/openlibing/security-compilation-options-action
**复核说明：** 本报告已对原始 STRIDE-A 报告（`threat-model-20261009-103731/`）的 15 条发现逐条打开真实源码核验（工作副本 `security-compilation-options-action`，该仓无 `src/`，执行代码位于 `dist/` 打包产物），核验结论见第 5 章与 7.2 节。

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [系统架构概述](#2-系统架构概述)
3. [数据流图（DFD）](#3-数据流图dfd)
4. [STRIDE-A 威胁分析](#4-stride-a-威胁分析)
5. [安全发现与漏洞详情](#5-安全发现与漏洞详情)
6. [修复建议与行动计划](#6-修复建议与行动计划)
7. [附录](#7-附录)

---

## 1. 执行摘要

### 1.1 分析概述

`openlibing-security-compilation-options-action` 是一个 GitCode Actions / GitHub Actions 兼容的 Node.js 16 复合插件，用于扫描构建产物（ELF 二进制）中 14 项安全编译选项（BIND_NOW、NX、PIC、PIE、RELRO、Rpath、SP、Strip、FORTIFY、Fvisibility、Ftrapv、StackClash、FstackCheck、ASLR）的开启率，并将合规报告通过华为云 APIG 网关上报到 openLiBing CI/CD 后端。

该插件不监听任何入站端口：它作为短生命周期进程运行在自托管 CI 执行机上，为每次扫描派生出 Python 扫描子进程（`dist/bin/sec_option_scan.py`），对输入产物做递归解压（含嵌套包与自解压包），并向外发起出站 HTTPS 调用（APIG、华为云 STS、Actions OIDC 端点、第三方 PyPI 镜像）。后端认证支持两种方式：OIDC 联邦认证（OIDC ID Token 经 STS 换取临时凭证）或存量静态 AK/SK（SDK-HMAC-SHA256 签名）。

**本次分析共识别 15 个安全问题**，覆盖 17 个系统元素、2 个信任边界、50 条 STRIDE-A 威胁。经过逐条源码复核：**14 条确认成立、1 条部分成立、0 条误报、0 条无法验证**（详见 [7.2 漏洞误报复核结果](#72-漏洞误报复核结果)）。

### 1.2 关键安全风险表

| 严重级别 | 数量 | 关键问题 |
|---------|------|---------|
| **严重（Critical）** | 1 | PR 代码在自托管执行机上执行（`pull_request_target` + `allow-unsafe-pr-checkout` + `npm install`） |
| **高危（High/Important）** | 5 | CI 流水线可变引用与超范围 OIDC 授权、Python 依赖无哈希校验、身份可被环境变量与未校验 URL 伪造、合规结果全链路可篡改、合规门禁可被绕过 |
| **中危（Medium/Moderate）** | 8 | 解压/递归无资源预算、凭证与内部路径写入 CI 日志、外部输入直达特权文件/URL/子进程操作、明文 HTTP 默认值与无证书固定、出站请求无超时与子进程输出无上限、Windows 可预测世界可写临时目录、打包内 TLS 校验旁路与可变 `fetch`、分发两份重复扫描脚本且无完整性校验 |
| **低危（Low）** | 1 | 已有防御控制（归档穿越防护、SHA 固定插件、STS 凭证脱敏）确认有效，存在残余缺口 |

### 1.3 核心结论

> **本仓最大风险不在 ELF 解析器，而在其周围的 CI/CD 流水线与供应链。**
>
> 1. `pre-commit` 流水线使用 `pull_request_target`，并显式以 `allow-unsafe-pr-checkout: true` 关闭 fork PR 检出拦截，检出 PR 合并提交后执行 `npm install`，使 PR 作者可在**持久、共享的自托管执行机**上执行任意生命周期脚本（FIND-01，严重）。
> 2. 插件在每次调用时以 `pip install --break-system-packages pyelftools==0.31 -i https://mirrors.aliyun.com/pypi/simple/` 从第三方镜像安装依赖且无哈希校验（FIND-03，高危）。
> 3. 作为**发布合规门禁**的合规数值，从产物到结果文件到上报体全链路无完整性绑定：产物无校验、结果写死在可预测路径后被重新读取、上报体签名的只是“被交到手上的 body”，`scan-options`/N/A 语义/静默上传失败还能进一步收窄或绕过门禁（FIND-05、FIND-06，高危）。
>
> 解析器本身体现了良好的工程习惯（归档路径穿越校验、符号链接环保护均正确），但缺乏任何资源预算，存在解压炸弹拒绝服务路径（FIND-07）。
>
> **鉴于 FIND-01 的影响面（共享执行机上的任意代码执行），建议优先加固 CI 流水线信任模型，再处理合规记录完整性问题。**

---

## 2. 系统架构概述

### 2.1 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 语言 | JavaScript / Node.js | Node.js 16 运行时 |
| 语言 | Python | Python 3（扫描脚本） |
| 框架/库 | @actions/core | ^1.10.0 |
| 框架/库 | @openlibing/huaweicloud-oidc-client | 0.0.5 |
| 框架/库 | axios | ^1.6.0 |
| 框架/库 | js-yaml | ^4.1.0 |
| 框架/库 | winston | ^3.11.0 |
| 框架/库 | pyelftools | 0.31（运行时安装） |
| 打包 | @vercel/ncc | ^0.38.1 |
| 打包 | adm-zip | ^0.5.16 |
| 数据存储 | 本地文件系统 | 构建产物归档、`sec-option-result.json`、`.git/config` |
| 基础设施 | GitCode Actions 自托管执行机 | `["self-hosted", "region=cn"]` / `region=overseas` |
| 安全机制 | APIG 签名（SDK-HMAC-SHA256 / V11-HMAC-SHA256）、OIDC 联邦认证（华为云 STS）、HTTPS/TLS、归档路径穿越校验、gitleaks + detect-private-key pre-commit 钩子 | — |

> 依赖清单依据 `package.json`（`main: dist/index.js`，`engines.node >=16.0.0`）。

### 2.2 关键组件

| 组件 ID | 类型 | 说明 | 源码位置 |
|---------|------|------|---------|
| ActionEntrypoint | Process | `run()` 入口，解析插件输入、选择认证模式、安装 Python 依赖、驱动扫描与输出 | `dist/index.js:54334` |
| SecOptionScanner | Process | 单个产物的扫描编排器，写结果 JSON 并触发上报 | `dist/scanner.js:16` |
| SecOptionDetector | Process | 通过 `child_process.spawn` 派生 Python 扫描脚本并解析其 JSON 输出 | `dist/detectors/SecOptionDetector.js:5` |
| SecOptionScanScript | Process | Python ELF 扫描脚本：递归解压、ELF 解析、14 项检测 | `dist/bin/sec_option_scan.py` |
| CicdUploader / ApigSigner | Process | 构建上报体并执行签名 HTTPS 上传 | `dist/uploaders/CicdUploader.js:16`、`:246` |
| HuaweiCloudOIDCClient | Process | 内置 OIDC/STS 客户端：Token 获取、凭证交换、V11 签名、日志脱敏 | `dist/index.js`（打包模块 5186-5763） |
| PreCommitWorkflow | Process | `pull_request_target` 流水线，检出 PR 代码并运行 pre-commit/ESLint | `.gitcode/workflows/pre-commit.yml` |
| NightlyScanWorkflow | Process | 每日定时全仓 pre-commit 扫描（含 SARIF 上传） | `.gitcode/workflows/nightly-schedule-scan.yml` |
| CodeMetricsScanWorkflow | Process | 推送触发、调用 commit-SHA 固定的第三方度量插件 | `.gitcode/workflows/code-metrics-scan.yml` |
| BuildArtifact | Data Store | 通过 `artifact-path` 传入的 ELF 产物或归档 | 执行机本地文件 |
| ScanResultFile | Data Store | `sec-option-result.json`（或 `output` 指定路径），承载 `summary`/`details` | 执行机本地文件 |
| GitRepository | Data Store | 检出的工作树与 `.git/config`，用于 `gitUrl` 溯源字段 | 执行机本地文件 |
| WorkflowAuthor | External Interactor | 编排工作流/提交 PR 的构建发布工程师 | 外部 |
| APIGGateway | External Service | `https://apig.openlibing.com:443`，接收合规报告 | 外部服务 |
| HuaweiCloudSTS | External Service | `https://sts.cn-southwest-2.myhuaweicloud.com`，OIDC 换证 | 外部服务 |
| GitCodeOIDCEndpoint | External Service | Actions 运行时 OIDC 端点（`ACTIONS_ID_TOKEN_REQUEST_URL`），签发流水线 ID Token | 外部服务 |
| PyPIMirror | External Service | `https://mirrors.aliyun.com/pypi/simple/`，安装 `pyelftools==0.31` | 外部服务 |

### 2.3 信任边界

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              External                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │WorkflowAuthor│  │ APIG Gateway │  │ HuaweiCloud  │  │GitCode OIDC  │  │
│  │ (PR 作者/工程师)│  │              │  │    STS       │  │  Endpoint    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │                 │           │
│         │        ┌────────┴─────────────────┴─────────────────┴─────┐     │
│         │        │              PyPI Mirror (aliyun)               │     │
│         │        └────────┬─────────────────────────────────────── ┘     │
└─────────┼─────────────────┼──────────────────────────────────────────────┘
          │ workflow inputs / PR / push / schedule（HTTPS 或 CI 平台凭证）
          │                 ▲ 出站 HTTPS（OIDC/STS/APIG/镜像）
          ▼                 │
┌──────────────────────────────────────────────────────────────────────────┐
│                          CI Runner（自托管执行机）                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  ActionEntrypoint  →  SecOptionScanner  →  SecOptionDetector        │  │
│  │        │                    │                    │                 │  │
│  │        │                    ▼                    ▼                 │  │
│  │        │            CicdUploader          SecOptionScanScript       │  │
│  │        │            OIDC Client                  │                 │  │
│  │        ▼                                         ▼                 │  │
│  │  BuildArtifact(文件)  ScanResultFile(文件)  GitRepository(.git)      │  │
│  │  PreCommitWorkflow / NightlyScanWorkflow / CodeMetricsScanWorkflow  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**信任边界说明：**

1. **边界 1 — External → CI Runner：** 工作流/PR 作者通过工作流输入、PR、推送或定时触发进入执行机；越过该边界需要 CI 平台身份（工作流/PR 作者）或执行机本地进程访问。这是本仓唯一的外部交互面，且**无入站监听端口**。
2. **边界 2 — CI Runner → External Services：** 执行机出站调用 APIG 网关、华为云 STS、OIDC 端点与第三方 PyPI 镜像（均为 HTTPS）。

### 2.4 部署模式

- **类型：** 短生命周期 Node.js 16 插件进程 + 每次扫描派生一个 Python 子进程。
- **网络暴露：** **无入站监听端口**；仅出站 HTTPS（`apig.openlibing.com:443`、`sts.cn-southwest-2.myhuaweicloud.com:443`、Actions OIDC 运行时 URL、`mirrors.aliyun.com:443`）。
- **执行机：** GitCode Actions 自托管执行机（`region=cn` / `region=overseas`），是**持久、多租户、任务与仓库间共享**的主机。
- **本地文件交互：** 产物路径、结果 JSON 路径（默认 `sec-option-result.json`）、Windows 短路径临时基目录 `D:\sec_option_tmp` / `C:\sec_option_tmp`。
- **部署分类：** `LOCALHOST_DESKTOP`（无监听端口；无 `None` 前置条件的威胁，故无 Tier 1 发现）。

---

## 3. 数据流图（DFD）

### 3.1 详细数据流图

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryColor': '#ffffff', 'lineColor': '#666666' }}}%%
flowchart LR
    classDef process fill:#6baed6,stroke:#2171b5,stroke-width:2px,color:#000000
    classDef external fill:#fdae61,stroke:#d94701,stroke-width:2px,color:#000000
    classDef datastore fill:#74c476,stroke:#238b45,stroke-width:2px,color:#000000

    WorkflowAuthor["Workflow Author"]:::external
    APIGGateway["APIG Gateway"]:::external
    HuaweiCloudSTS["Huawei Cloud STS"]:::external
    GitCodeOIDCEndpoint["GitCode OIDC Endpoint"]:::external
    PyPIMirror["PyPI Mirror"]:::external

    subgraph CIRunner["CI Runner"]
        ActionEntrypoint(("Action Entrypoint")):::process
        SecOptionScanner(("SecOption Scanner")):::process
        SecOptionDetector(("SecOption Detector")):::process
        SecOptionScanScript(("SecOption Scan Script")):::process
        CicdUploader(("CICD Uploader")):::process
        HuaweiCloudOIDCClient(("OIDC Client")):::process
        PreCommitWorkflow(("Pre-Commit Workflow")):::process
        NightlyScanWorkflow(("Nightly Scan Workflow")):::process
        CodeMetricsScanWorkflow(("Code Metrics Scan Workflow")):::process
        BuildArtifact[("Build Artifact")]:::datastore
        ScanResultFile[("Scan Result File")]:::datastore
        GitRepository[("Git Repository")]:::datastore
    end

    WorkflowAuthor <-->|"DF01: PR / commit trigger"| PreCommitWorkflow
    WorkflowAuthor <-->|"DF02: dispatch / schedule"| NightlyScanWorkflow
    WorkflowAuthor <-->|"DF03: push to master"| CodeMetricsScanWorkflow
    WorkflowAuthor <-->|"DF04: workflow inputs"| ActionEntrypoint
    ActionEntrypoint <-->|"DF05: scan config"| SecOptionScanner
    ActionEntrypoint <-->|"DF06: pip install pyelftools"| PyPIMirror
    ActionEntrypoint <-->|"DF07: git remote get-url origin"| GitRepository
    SecOptionScanner <-->|"DF08: detect()"| SecOptionDetector
    SecOptionDetector <-->|"DF09: spawn python3"| SecOptionScanScript
    SecOptionDetector <-->|"DF10: read result JSON"| ScanResultFile
    SecOptionScanScript <-->|"DF11: read ELF and extract archives"| BuildArtifact
    SecOptionScanScript <-->|"DF12: write result JSON"| ScanResultFile
    SecOptionScanner <-->|"DF13: write result JSON"| ScanResultFile
    SecOptionScanner <-->|"DF14: upload()"| CicdUploader
    CicdUploader <-->|"DF15: callApig / getCredentials"| HuaweiCloudOIDCClient
    CicdUploader <-->|"DF16: HTTPS POST report"| APIGGateway
    HuaweiCloudOIDCClient <-->|"DF17: GET OIDC ID token"| GitCodeOIDCEndpoint
    HuaweiCloudOIDCClient <-->|"DF18: AssumeAgencyWithOIDC"| HuaweiCloudSTS
    PreCommitWorkflow <-->|"DF19: checkout PR merge commit"| GitRepository
    NightlyScanWorkflow <-->|"DF20: checkout master"| GitRepository
    CodeMetricsScanWorkflow <-->|"DF21: checkout"| GitRepository

    style CIRunner fill:none,stroke:#e31a1c,stroke-width:3px,stroke-dasharray: 5 5

    linkStyle default stroke:#666666,stroke-width:2px
```

### 3.2 汇总数据流图

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryColor': '#ffffff', 'lineColor': '#666666' }}}%%
flowchart LR
    classDef process fill:#6baed6,stroke:#2171b5,stroke-width:2px,color:#000000
    classDef external fill:#fdae61,stroke:#d94701,stroke-width:2px,color:#000000
    classDef datastore fill:#74c476,stroke:#238b45,stroke-width:2px,color:#000000

    WorkflowAuthor["Workflow Author"]:::external
    ExternalServices["External Services<br/>(APIG Gateway, Huawei Cloud STS,<br/>GitCode OIDC Endpoint, PyPI Mirror)"]:::external

    subgraph CIRunner["CI Runner"]
        ActionEntrypoint(("Action Entrypoint")):::process
        ScanPipeline(("Scan and Upload Pipeline<br/>(SecOption Scanner, SecOption Detector,<br/>CICD Uploader, OIDC Client)")):::process
        PreCommitWorkflow(("Pre-Commit Workflow")):::process
        OtherWorkflows(("Scheduled Pipelines<br/>(Nightly Scan Workflow,<br/>Code Metrics Scan Workflow)")):::process
        SecOptionScanScript(("SecOption Scan Script")):::process
        BuildArtifact[("Build Artifact")]:::datastore
        LocalState[("Local State<br/>(Scan Result File, Git Repository)")]:::datastore
    end

    WorkflowAuthor <-->|"SDF01: workflow inputs"| ActionEntrypoint
    WorkflowAuthor <-->|"SDF02: PR / commit trigger"| PreCommitWorkflow
    WorkflowAuthor <-->|"SDF03: dispatch / schedule"| OtherWorkflows
    ActionEntrypoint <-->|"SDF04: scan config"| ScanPipeline
    ActionEntrypoint <-->|"SDF05: dependency install"| ExternalServices
    ScanPipeline <-->|"SDF06: spawn python3"| SecOptionScanScript
    SecOptionScanScript <-->|"SDF07: read ELF and extract archives"| BuildArtifact
    ScanPipeline <-->|"SDF08: result JSON"| LocalState
    ActionEntrypoint <-->|"SDF09: git metadata"| LocalState
    PreCommitWorkflow <-->|"SDF10: checkout PR merge commit"| LocalState
    OtherWorkflows <-->|"SDF11: checkout"| LocalState
    ScanPipeline <-->|"SDF12: signed report upload / OIDC exchange"| ExternalServices

    style CIRunner fill:none,stroke:#e31a1c,stroke-width:3px,stroke-dasharray: 5 5

    linkStyle default stroke:#666666,stroke-width:2px
```

### 3.3 关键数据流说明

| 数据流 ID | 源 → 目标 | 协议 | 数据内容 | 安全风险 |
|-----------|-----------|------|---------|---------|
| DF04 | WorkflowAuthor → ActionEntrypoint | 进程环境 / `INPUT_*` | 插件输入（`artifact-path`、`output`、`scan-options`、`apig-app-key`、`apig-app-secret`、`artifact-download-url`） | 环境变量可覆盖身份类输入（FIND-04、FIND-09） |
| DF06 | ActionEntrypoint → PyPIMirror | HTTPS | `pip install --break-system-packages pyelftools==0.31` | 第三方镜像无哈希校验（FIND-03） |
| DF07 | ActionEntrypoint → GitRepository | 本地 git / `.git/config` | `git remote get-url origin`（`gitUrl` 溯源字段） | 可变配置 + PATH 解析 `git`（FIND-05、FIND-08） |
| DF09 | SecOptionDetector → SecOptionScanScript | `child_process.spawn` argv | 脚本路径、扫描路径、输出路径、扫描项 | argv 拼装、无 shell（FIND-09、FIND-11） |
| DF10/DF12/DF13 | 扫描器/脚本 → ScanResultFile | 文件系统读/写 | `summary`/`details` | 结果写可预测路径后重读（FIND-05） |
| DF11 | SecOptionScanScript → BuildArtifact | 文件系统 / 归档解压 | 递归读取目录、解压嵌套归档 | 无资源预算、Windows 临时目录（FIND-07、FIND-12） |
| DF16 | CicdUploader → APIGGateway | HTTPS POST | 签名合规报告（OIDC V11 或 AK/SK SDK-HMAC-SHA256） | 上传体无溯源绑定、无证书固定（FIND-05、FIND-10） |
| DF17/DF18 | HuaweiCloudOIDCClient → OIDC 端点 / STS | HTTPS | OIDC ID Token、临时凭证 | 环境变量可注入 Token、请求 URL 未校验（FIND-04） |
| DF19 | PreCommitWorkflow → GitRepository | Git | 检出 PR 合并提交（`allow-unsafe-pr-checkout: true`） | 不受信任 PR 代码进入特权任务（FIND-01） |

---

## 4. STRIDE-A 威胁分析

### 4.1 威胁等级定义

| 等级 | 说明 | 前提条件 |
|------|------|---------|
| **Tier 1 (T1)** | 直接暴露，无需前置条件 | 攻击者可直接从网络利用（前提字段必须为 `None`） |
| **Tier 2 (T2)** | 需要单一前置条件 | 需要认证用户、特权用户、内网或单一 `{边界} Access` |
| **Tier 3 (T3)** | 需要高权限或多项前置条件 | 需要主机/OS 访问、管理员凭证、组件失陷或物理访问 |

> 说明：本仓部署分类为 `LOCALHOST_DESKTOP`（无入站监听），因此无任何威胁或发现的前置条件为 `None`，不存在 Tier 1 发现；`AV:N` 仅在攻击路径确实源自执行机边界之外（已认证的 CI 平台用户或出站连接被拦截）时使用。

### 4.2 威胁汇总表

| 组件 | S (欺骗) | T (篡改) | R (抵赖) | I (信息泄露) | D (拒绝服务) | E (提权) | A (滥用) | 总计 | 风险 |
|------|---------|---------|---------|-------------|-------------|---------|---------|------|------|
| ActionEntrypoint | 1 | 1 | 0 | 1 | 1 | 1 | 1 | **6** | High |
| SecOptionScanner | 0 | 1 | 0 | 0 | 1 | 0 | 1 | **3** | Medium |
| SecOptionDetector | 0 | 1 | 0 | 1 | 1 | 0 | 0 | **3** | Medium |
| SecOptionScanScript | 0 | 3 | 0 | 1 | 1 | 1 | 1 | **7** | High |
| CicdUploader | 1 | 1 | 0 | 1 | 0 | 0 | 0 | **3** | Medium |
| HuaweiCloudOIDCClient | 1 | 1 | 0 | 1 | 1 | 0 | 0 | **4** | High |
| PreCommitWorkflow | 1 | 1 | 0 | 1 | 0 | 1 | 1 | **5** | Critical |
| NightlyScanWorkflow | 1 | 1 | 0 | 0 | 0 | 1 | 0 | **3** | Medium |
| CodeMetricsScanWorkflow | 0 | 1 | 0 | 0 | 0 | 1 | 0 | **2** | Low |
| BuildArtifact | 0 | 2 | 0 | 0 | 0 | 0 | 0 | **2** | Medium |
| ScanResultFile | 0 | 1 | 0 | 1 | 0 | 0 | 0 | **2** | Medium |
| GitRepository | 0 | 1 | 0 | 1 | 0 | 0 | 0 | **2** | Medium |
| APIGGateway | 1 | 1 | 0 | 0 | 0 | 0 | 0 | **2** | Medium |
| HuaweiCloudSTS | 1 | 0 | 0 | 1 | 0 | 0 | 0 | **2** | Medium |
| GitCodeOIDCEndpoint | 1 | 0 | 0 | 1 | 0 | 0 | 0 | **2** | Medium |
| PyPIMirror | 1 | 1 | 0 | 0 | 0 | 0 | 0 | **2** | High |
| **总计** | **9** | **17** | **0** | **10** | **5** | **5** | **4** | **50** | |

> Repudiation（抵赖）为 0：每个组件要么自身不做安全相关决策，要么依赖平台侧审计记录。

### 4.3 各组件详细威胁分析

#### 4.3.1 ActionEntrypoint

**锚点：** `dist/index.js:54334`（`run()`）

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T01.S | S | `getInput()` 优先读取 `process.env.INPUT_*`，执行机上可预置环境变量的进程可伪造 `artifact-path`/`output`/`apig-app-key`/`apig-app-secret` | T2 | Authenticated User |
| T01.T | T | 溯源字段来自 `execSync('git remote get-url origin')`，被劫持的 `PATH` 上 `git` 或篡改的 `.git/config` 可改写上报的 `gitUrl` | T2 | Authenticated User |
| T01.I | I | `core.info` 打印 `artifact-path`/`gitUrl`/`pipelineName`/`runNumber`，清洗正则仅处理 `https://user@host` 形式 | T2 | Authenticated User |
| T01.D | D | 出站 HTTP 用 `fetch` 且无 `AbortSignal`/超时，端点不响应则阻塞到 CI 级超时 | T2 | Authenticated User |
| T01.E | E | `output` 输入与 `ATOMGIT_OUTPUT` 环境变量被直接用于 `fs.mkdirSync(recursive)` 与 `fs.writeFileSync`，可越界写入 | T2 | Authenticated User |
| T01.A | A | `artifact-download-url` 未校验即转发后端，工作流作者可定义展示给报告消费方的下载链接 | T2 | Authenticated User |

#### 4.3.2 SecOptionScanner

**锚点：** `dist/scanner.js:16`（`SecOptionScanner`）

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T02.T | T | 结果写入可预测路径后在上报前被重新读取，同主机进程可在扫描后替换文件篡改合规率 | T2 | Local Process Access |
| T02.D | D | 全量处理产物树且无文件数/字节/时间预算，超大产物可占满执行机直至任务被杀 | T2 | Authenticated User |
| T02.A | A | 上报失败时仅记 `uploadInfo.success=false` 且从不使步骤失败，流水线可在无合规记录时转绿 | T2 | Authenticated User |

#### 4.3.3 SecOptionDetector

**锚点：** `dist/detectors/SecOptionDetector.js:5`

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T03.T | T | Python argv 由调用方提供的扫描路径/输出路径/扫描项拼装；安全性仅依赖“从不使用 shell”这一未被断言的不变量 | T2 | Authenticated User |
| T03.I | I | Python `stdout`/`stderr`（含 `traceback.print_exc` 内部路径）被原样回显到 CI 日志 | T2 | Authenticated User |
| T03.D | D | `spawn` 无超时且两路输出累积进无界字符串，恶意产物可挂起任务并耗尽内存 | T2 | Authenticated User |

#### 4.3.4 SecOptionScanScript

**锚点：** `dist/bin/sec_option_scan.py`

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T04.T | T | 归档条目经路径校验后解压；校验拒绝 `..`/绝对路径/盘符，但不含 Windows 尾点/尾空格、保留设备名、UNC 前缀等怪癖 | T2 | Authenticated User |
| T04.T2 | T | `tarfile.open(...)` 与 `tf.extract(...)` 未显式传 `filter=`，采用解释器默认 `fully_trusted`，安全完全依赖手工预校验 | T2 | Authenticated User |
| T04.I | I | 每条失败路径都向 stderr 打印产物路径与完整 traceback，JS 层转发到 CI 日志，泄露内部目录结构 | T2 | Authenticated User |
| T04.D | D | 无解压字节数、条目数、嵌套深度或递归上限，解压炸弹/深层嵌套包可耗尽磁盘或挂起扫描 | T2 | Authenticated User |
| T04.E | E | Windows 下创建并使用可预测的世界可写基目录 `D:\sec_option_tmp` / `C:\sec_option_tmp`，本地攻击者可预创建目录或重解析点 | T2 | Local Process Access |
| T04.A | A | 无法判定的选项返回 `N/A` 并从分母剔除，静态/Go/strip 产物可虚高开启率 | T2 | Authenticated User |
| T04.T3 | T | 仓内存在两份逐字节相同的扫描脚本，仅 `bin/` 副本被执行，打包无完整性校验，漂移/静默替换不可检测 | T3 | Host/OS Access |

#### 4.3.5 CicdUploader

**锚点：** `dist/uploaders/CicdUploader.js:246`

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T05.S | S | 类默认 `baseUrl` 为 `http://localhost:8080`，省略 `cicdUrl` 的调用方将以明文 HTTP 传输签名报告 | T2 | Authenticated User |
| T05.T | T | 上报体自身无完整性绑定，签名器对所交付 body 照签，同主机进程可先改合规数值再签名 | T2 | Authenticated User |
| T05.I | I | 上传诊断打印 `gitUrl`/`packageName`/`pipelineRunId`/`runNumber`，AK/SK 以明文对象字段常驻进程生命周期 | T2 | Authenticated User |

#### 4.3.6 HuaweiCloudOIDCClient

**锚点：** `dist/index.js`（打包模块，`getOidcToken` / `_assumeAgencyWithOIDC`）

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T06.S | S | 攻击者可控的 OIDC ID Token 可经 `HUAWEICLOUD_OIDC_TOKEN` 环境变量注入，客户端优先于运行时端点使用它 | T2 | Local Process Access |
| T06.I | I | `_printTokenClaims` 在 error 级（非调试模式）打印 `iss/aud/azp/sub`，`mask()` 仅截断不完整脱敏 | T2 | Authenticated User |
| T06.D | D | `sendRequest` 的 `fetch` 无超时且凭证缓存无有界重试，STS/OIDC 不响应可无限阻塞 | T2 | Authenticated User |
| T06.T | T | `sendRequest` 在运行时选取 `globalThis.fetch`，进程内任意代码或失陷依赖替换全局 `fetch` 即可拦截 Token/凭证/Authorization 头 | T3 | Host/OS Access |

#### 4.3.7 PreCommitWorkflow

**锚点：** `.gitcode/workflows/pre-commit.yml`

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T07.S | S | 流水线以共享静态 `secrets.ROBOT_TOKEN` 认证，而非绑定本次运行的短时任务级令牌 | T2 | Authenticated User |
| T07.T | T | `pull_request_target` 结合 `allow-unsafe-pr-checkout: true` 检出 PR 代码并 `npm install`，在自托管执行机执行 PR 提供的生命周期脚本 | T2 | Authenticated User |
| T07.I | I | 任务将插件输入暴露为 `INPUT_*` 环境变量且检出步骤已获令牌，同任务内运行的 PR 代码可读取 | T2 | Authenticated User |
| T07.E | E | `extra_args: ${{ inputs.extra_args }}` 将表达式值直接插入插件输入 | T2 | Authenticated User |
| T07.A | A | 后置阶段由工作流表达式推导 `ci-pipeline-passed`/`ci-pipeline-failed` 标签，修改工作流可在检查未通过时标记为通过 | T2 | Authenticated User |

#### 4.3.8 NightlyScanWorkflow

**锚点：** `.gitcode/workflows/nightly-schedule-scan.yml`

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T08.S | S | 检出步骤以 `token: ${{ secrets.ROBOT_TOKEN }}`（长期共享身份）读取 `master` | T2 | Authenticated User |
| T08.T | T | 引用可变标签的第三方插件（`pre-commit-action@v1.0.2`、`upload-sarif-action@v1.0.0`），且 `npm install` 执行生命周期脚本 | T2 | Authenticated User |
| T08.E | E | 工作流级授予 `id-token: write`，每个步骤（含第三方插件）都可铸造 OIDC Token 并换云凭证 | T2 | Authenticated User |

#### 4.3.9 CodeMetricsScanWorkflow

**锚点：** `.gitcode/workflows/code-metrics-scan.yml`

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T09.T | T | `code-metrics-action` 固定到完整 commit SHA（`117c0606...`），可防止标签重定向与仿冒——已有且正确的控制 | T2 | Authenticated User |
| T09.E | E | 任务运行第三方插件的同时授予 `id-token: write`，失陷插件可获取联邦云凭证 | T2 | Authenticated User |

#### 4.3.10 BuildArtifact

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T10.T | T | 解压前不校验产物完整性与来源，产物内容单独决定上报的合规结果 | T2 | Authenticated User |
| T10.T2 | T | `artifact-path` 仅以 `fs.existsSync` 检查，跟随符号链接与工作区外路径 | T2 | Local Process Access |

#### 4.3.11 ScanResultFile

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T11.T | T | 结果路径可预测且写后被重读，同主机进程可预创建或替换以伪造合规记录 | T2 | Local Process Access |
| T11.I | I | 结果文件记录包内相对路径且以默认（可读）权限创建于工作区 | T2 | Local Process Access |

#### 4.3.12 GitRepository

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T12.T | T | 远端 URL 从可变 `.git/config` 读取并作为溯源提交，篡改配置可改写合规记录归属 | T2 | Local Process Access |
| T12.I | I | 远端常内嵌凭证（`https://user:token@host/...`），清洗仅去除 HTTPS userinfo，其他编码可进入日志与上报体 | T2 | Local Process Access |

#### 4.3.13 APIGGateway

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T13.S | S | 网关身份仅依赖 TLS、无证书固定，执行机级 CA 或代理失陷可让仿冒端点接收签名报告 | T2 | Authenticated User |
| T13.T | T | 任何持有效 OIDC Token 或 AK/SK 的调用方都可提交 `gitUrl`/`packagePath` 任意的报告，伪造合规记录 | T2 | Authenticated User |

#### 4.3.14 HuaweiCloudSTS

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T14.S | S | 临时凭证的可信度取决于 IAM 信任策略；`oidc:sub`/`oidc:aud` 通配过大可让非预期仓库/ref 的令牌承担委托 | T2 | Authenticated User |
| T14.I | I | 返回的 `access_key_id`/`secret_access_key`/`security_token` 在 info 与 debug 路径均先脱敏——已有且有效的控制 | T2 | Authenticated User |

#### 4.3.15 GitCodeOIDCEndpoint

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T15.S | S | Token 请求目标来自未校验的 `ACTIONS_ID_TOKEN_REQUEST_URL`，同主机进程可重定向到返回攻击者所选 Token 的仿冒端点 | T2 | Local Process Access |
| T15.I | I | ID Token 为 STS 接受的不记名凭证，`HUAWEICLOUD_OIDC_TOKEN` 回退使其可经环境变量提供，对子进程与崩溃转储可见 | T2 | Authenticated User |

#### 4.3.16 PyPIMirror

| ID | STRIDE | 威胁描述 | Tier | 前置条件 |
|----|--------|---------|------|---------|
| T16.S | S | 仅依赖 TLS 信任镜像（无索引签名、无 `--require-hashes`），失陷镜像/DNS/代理可投递仿冒发行包 | T2 | Authenticated User |
| T16.T | T | `pip install --break-system-packages pyelftools==0.31 -i ...aliyun...` 无哈希校验执行发行包安装钩子，被篡改的包可在执行机内代码执行 | T2 | Authenticated User |

---

## 5. 安全发现与漏洞详情

> 复核结论标注于每条发现开头（确认 / 误报 / 部分成立 / 无法验证）。经复核无“误报”与“无法验证”条目；全部发现均保留。

### 5.1 严重（Critical）漏洞

---

#### FIND-01: PR 代码在自托管执行机上执行，且长期机器人令牌在作用域内

**复核结论：** ✅ 确认（核心“不受信任 PR 代码在持久共享执行机上执行”经源码逐项核实；令牌作用域机制细节见 [7.2](#72-漏洞误报复核结果) 说明）

| 属性 | 值 |
|------|-----|
| **严重级别** | Critical |
| **CVSS 4.0 评分** | 8.7 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:L/SI:L/SA:L` |
| **CWE** | [CWE-94: Improper Control of Generation of Code ('Code Injection')](https://cwe.mitre.org/data/definitions/94.html) |
| **OWASP** | A03:2025 – Software Supply Chain Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Medium |

**描述：**

`pre-commit` 流水线由 `pull_request_target` 触发（读取默认分支 master 的工作流定义），但检出 PR 合并提交，并以 `allow-unsafe-pr-checkout: true` 显式关闭平台的 fork PR 检出拦截；随后的 `npm install` 因此会在**持久自托管执行机**上执行 PR 作者编写的生命周期脚本。由于 `pull_request_target` 语境下工作流可访问仓库 Secrets、且平台将插件输入导出为 `INPUT_*` 环境变量，攻击者提供的安装脚本可读取凭证、改写工作区，或持久化到供其他仓库任务复用的共享执行机。这把低权限的“提交一个 PR”动作，转化为在可信构建基础设施上的任意代码执行与凭证窃取（或后门持久化）。

**证据：**

`.gitcode/workflows/pre-commit.yml`：
- 第 8 行：`pull_request_target: ## 使用 pull_request_target 确保 PR 流水线始终读取默认分支（master）的最新配置文件`
- 第 47 行：`ref: ${{ atomgit.event.pull_request.merge_commit_sha || atomgit.event.pull_request.head.sha }}`
- 第 48 行：`allow-unsafe-pr-checkout: true # 关闭 fork PR 检出拦截，避免流水线在 fork PR 场景失败`
- 第 42 行：`runs-on: ["self-hosted", "region=overseas"]`（持久共享执行机）
- 第 56-57 行：`- name: Install npm dependencies` / `run: npm install`
- 第 33 行：`token: ${{ secrets.ROBOT_TOKEN }}`（同工作流内 `pr-label-running` 任务使用长期机器人令牌）

`dist/index.js:54278`（插件输入以 `INPUT_*` 形式暴露）：
```javascript
const hyphenKey = `INPUT_${name.toUpperCase()}`;
```

**修复建议：**

停止用特权凭证检出并构建不受信任的 PR 代码。移除 `allow-unsafe-pr-checkout: true`，将 PR 任务改为 `pull_request` 事件（不暴露 Secrets），或保留 `pull_request_target` 但拆分为“不受信任检出/`npm install`”阶段（无 Secrets、无 `INPUT_*`、临时执行机）与“可信处理”阶段。依赖安装使用 `npm ci --ignore-scripts`，并以任务级平台令牌与最小 `permissions:` 替换长期 `secrets.ROBOT_TOKEN`。

**验证步骤：**

从 fork 提交一个向 `package.json` 注入 `postinstall` 脚本（写出 `${process.env.INPUT_TOKEN}` 到文件）的 PR，确认脚本不执行且任务环境中不存在 `INPUT_TOKEN`/`INPUT_GC_TOKEN`；重跑流水线确认检出步骤不再携带 `allow-unsafe-pr-checkout: true`。

---

### 5.2 高危（High/Important）漏洞

---

#### FIND-02: CI 流水线中的表达式插值、可变插件引用与超范围 OIDC 授权

**复核结论：** ⚠️ 部分成立（可变标签引用、workflow 级 `id-token: write`、标签状态由表达式推导均确认；`extra_args` 表达式注入子项因工作流未声明 `inputs` 上下文而不成立——详见 [7.2](#72-漏洞误报复核结果)）

| 属性 | 值 |
|------|-----|
| **严重级别** | Important（复核后维持；理由见 7.2） |
| **CVSS 4.0 评分** | 8.3（原始评分，主要针对确认成立的可变引用 + 超范围 OIDC 组合） |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')](https://cwe.mitre.org/data/definitions/78.html) |
| **OWASP** | A05:2025 – Injection |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Medium |

**描述：**

本项汇集三处相关 CI 弱项：(1) `extra_args: ${{ inputs.extra_args }}` 将表达式值直接插入插件输入；(2) 第三方插件以可变标签引用（`openlibing/pre-commit-action@v1.0.2`、`openlibing/upload-sarif-action@v1.0.0`），重打标签或失陷发行版会静默改变执行内容；(3) 工作流级授予 `id-token: write`，使每个步骤（含第三方插件）都能铸造 OIDC Token 并到 STS 换取云凭证；此外基于工作流表达式推导的通过/失败标签，可在检查实际未成功时被打上 `ci-pipeline-passed`。

> **复核修正：** 子项 (1) 中 `inputs.extra_args` 在本工作流中无对应 `inputs` 声明（`on.workflow_dispatch` 未定义 `inputs`，也非 `workflow_call`），故该表达式实际求值为空字符串，不能构成命令/表达式注入；子项 (2)(3) 及标签推导均经源码确认。故本项标记“部分成立”，但确认子项各自达高危，严重级别维持 Important。

**证据：**

`.gitcode/workflows/pre-commit.yml`：
- 第 74 行：`extra_args: ${{ inputs.extra_args }}`（子项 1，值实际为空）
- 第 87 行：`add_labels: ${{ pipeline.upstream_status == 'COMPLETED' && 'ci-pipeline-passed' || 'ci-pipeline-failed' }}`（由表达式推导标签）

`.gitcode/workflows/nightly-schedule-scan.yml`：
- 第 10 行：`id-token: write`（工作流级）
- 第 47 行：`uses: openlibing/pre-commit-action@v1.0.2`（可变标签）
- 第 55 行：`uses: openlibing/upload-sarif-action@v1.0.0`（可变标签）

`.gitcode/workflows/code-metrics-scan.yml`：
- 第 11 行：`id-token: write`（授予一个只运行第三方插件的任务）

**修复建议：**

用户可控值通过 `env:` 传递并以带引号的环境变量引用（切勿插入 `run:`/`with:`），或按允许清单校验。将所有第三方插件固定到完整 commit SHA。把 `id-token: write` 从工作流级移到真正需要联邦的单个步骤，并添加任务级 `permissions:`。标签应依据平台任务状态而非工作流表达式推导，并用分支保护/评审规则保护工作流文件。

**验证步骤：**

确认每个 `uses:` 均为 40 位 SHA；确认不执行联邦的步骤环境中不再出现 `ACTIONS_ID_TOKEN_REQUEST_URL`；确认 `ci-pipeline-passed` 仅在检查实际通过时被打上。

---

#### FIND-03: 从第三方索引安装 Python 依赖且无哈希校验

**复核结论：** ✅ 确认

| 属性 | 值 |
|------|-----|
| **严重级别** | Important |
| **CVSS 4.0 评分** | 8.1 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:L/SI:L/SA:N` |
| **CWE** | [CWE-494: Download of Code Without Integrity Check](https://cwe.mitre.org/data/definitions/494.html) |
| **OWASP** | A03:2025 – Software Supply Chain Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Low |

**描述：**

插件启动时通过 shell 调用 `python -m pip install --break-system-packages pyelftools==0.31 -i https://mirrors.aliyun.com/pypi/simple/` 安装扫描依赖。版本已固定，但不校验发行包哈希，也不校验索引签名，且 `--break-system-packages` 移除了环境自身保护。由于 wheel 会执行安装代码，失陷/仿冒的镜像、被污染的 DNS/代理路径，或向索引投递的依赖混淆包，都可在执行机内以与构建任务相同的权限执行任意代码。这是本插件**最高杠杆的供应链入口**：它在每次调用、任何产物解析之前运行。

**证据：**

`dist/index.js:54385-54392`：
```javascript
const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
const pipInstallArgs = [
  '-m', 'pip', 'install', '--break-system-packages', 'pyelftools==0.31',
  '-i', 'https://mirrors.aliyun.com/pypi/simple/'
];
try {
  core.info('Installing Python dependencies (pyelftools)...');
  execSync([pythonCmd, ...pipInstallArgs].join(' '), { stdio: 'inherit', timeout: 120000 });
```
无 `--require-hashes`、无 `--only-binary`、无 `PIP_CONFIG_FILE` 固定。

**修复建议：**

将依赖内置（或从预构建镜像运行），并以 `--require-hashes` 从受审索引安装（使用官方 PyPI 与固定哈希集）。以虚拟环境替代 `--break-system-packages`。安装后再校验发行版版本与哈希。

**验证步骤：**

在除哈希允许清单外阻断镜像网络的条件下运行插件，确认使用 `--require-hashes` 成功、被篡改 wheel 失败；确认 `dist/index.js` 中不再存在 `--break-system-packages`。

---

#### FIND-04: 流水线身份可经环境变量与未校验的 OIDC 请求 URL 伪造

**复核结论：** ✅ 确认（身份输入的取值渠道经源码核实；最终换证可行性取决于外部 IAM 信任策略，见 Needs Verification）

| 属性 | 值 |
|------|-----|
| **严重级别** | Important |
| **CVSS 4.0 评分** | 7.7 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-290: Authentication Bypass by Spoofing](https://cwe.mitre.org/data/definitions/290.html) |
| **OWASP** | A07:2025 – Authentication Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Medium |

**描述：**

插件消费的每个身份输入都来自进程环境或可变配置，而非经认证的来源。`getInput()` 优先 `process.env.INPUT_*` 而非 toolkit 访问器，前序步骤可覆盖 `apig-app-key`/`apig-app-secret`；OIDC 客户端优先使用纯 `HUAWEICLOUD_OIDC_TOKEN` 环境变量而非运行时端点；Token 请求 URL 取自未校验的 `ACTIONS_ID_TOKEN_REQUEST_URL`，同主机进程可把换证重定向到返回攻击者所选 JWT 的仿冒端点。若 IAM 信任策略接受宽泛的 `oidc:sub`/`oidc:aud` 通配，注入或伪造的令牌即可在无真实流水线身份的情况下换取临时云凭证。

**证据：**

`dist/index.js`：
- 第 54280 行：`return process.env[hyphenKey] || process.env[underscoreKey] || core.getInput(name) || '';`
- 第 5719-5723 行：
```javascript
const fromEnv = process.env.HUAWEICLOUD_OIDC_TOKEN;
if (fromEnv) {
  info('-- OIDC ID Token 获取成功：来自环境变量 HUAWEICLOUD_OIDC_TOKEN 注入 --');
  return fromEnv;
}
```
- 第 5744-5750 行：
```javascript
const reqUrl = process.env.ACTIONS_ID_TOKEN_REQUEST_URL;
const reqToken = process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN;
if (!reqUrl || !reqToken) {
  return null;
}
const url = new URL(reqUrl);
url.searchParams.append('audience', cfg.audience);
```
- 第 5189-5197 行：
```javascript
accountId: '4d29a984c4fe4e6eb5d404a853d0084e',
audience: 'huawei-cloud-service',
agencyName: 'gitcode-actions',
oidcProviderName: 'GitCodeActions',
```

**修复建议：**

仅通过 `core.getInput` 接收输入，并用 `core.setSecret` 标记凭证输入。移除 `HUAWEICLOUD_OIDC_TOKEN` 环境回退，或置于显式且受审计的开关之后。对 `ACTIONS_ID_TOKEN_REQUEST_URL` 校验为预期的 Actions OIDC 主机并要求 HTTPS。平台侧将 IAM 信任策略约束为精确的 `oidc:sub`（仓库/ref）与精确 `aud`，而非通配。

**验证步骤：**

设置 `INPUT_ARTIFACT_PATH` 为意外值，确认插件忽略它而采用声明的输入；将 `ACTIONS_ID_TOKEN_REQUEST_URL` 设为攻击者主机，确认插件拒绝该请求；检查 IAM 信任策略确认 `oidc:sub` 匹配具体仓库/ref 模式。

---

#### FIND-05: 合规结果可被端到端篡改，因无任何环节将其绑定到扫描

**复核结论：** ✅ 确认

| 属性 | 值 |
|------|-----|
| **严重级别** | Important |
| **CVSS 4.0 评分** | 7.6 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:H/VA:N/SC:L/SI:H/SA:N` |
| **CWE** | [CWE-345: Insufficient Verification of Data Authenticity](https://cwe.mitre.org/data/definitions/345.html) |
| **OWASP** | A08:2025 – Software/Data Integrity Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Medium |

**描述：**

最终门禁发布的合规数值，由一串可变且未认证的产物生成：产物扫描前无校验和/来源检查（被扫字节不必对应已审构建）；结果写入可预测路径并在上传前从磁盘重读（同主机进程可替换）；上传体虽被签名，却从不绑定到生成它的那次扫描；来源字段（`gitUrl`）经 `PATH` 解析的 `git` 从可变 `.git/config` 读取。该链上任一参与方都可为一个任意仓库产出声称任意合规率的报告，而后端无法检测替换。

**证据：**

- `dist/index.js:54411-54415`（产物仅做存在性检查）：
```javascript
const resolvedArtifact = path.isAbsolute(line) ? line : path.resolve(process.cwd(), line);
if (!fs.existsSync(resolvedArtifact)) {
  throw new Error(`指定的构建产物文件不存在: ${resolvedArtifact}`);
}
```
- `dist/scanner.js:97-101`（结果写可预测路径后重读）：
```javascript
const outputDir = path.dirname(outputFile);
if (outputDir && !fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}
fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf8');
```
- `dist/detectors/SecOptionDetector.js:120-133`（重读并解析文件）：
```javascript
const content = fs.readFileSync(outputFile, 'utf8');
const result = JSON.parse(content);
if (!result.summary || !Array.isArray(result.details)) {
  throw new Error('Invalid scan result format: missing summary or details');
}
```
- `dist/uploaders/CicdUploader.js:299` 与 `:323-329`（签名覆盖“被交到手上的 body”）：
```javascript
const body = JSON.stringify(payload);
...
const signer = new ApigSigner(this.apigAppKey, this.apigAppSecret);
const headers = signer.sign({ method: 'POST', url: url, headers: { 'Content-Type': 'application/json' }, body: body });
const response = await axios.post(url, body, { headers, timeout: this.timeout });
```
- `dist/index.js:54368`（来源经 `PATH` 解析的 `git`）：`const remoteUrl = execSync('git remote get-url origin', { encoding: 'utf8', cwd: process.cwd() }).trim();`

**修复建议：**

计算被扫产物的摘要（或校验构建期签名）并将摘要与产物标识纳入上报体。将结果对象保留在内存、对其计算哈希，并签名/上传该内存对象，而非从可预测路径重读文件。`gitUrl` 取自平台注入变量（如运行器仓库元数据），而非 shell 调用 `git`。要求后端拒绝声明产物摘要与存储产物不符的报告。

**验证步骤：**

在扫描与上传之间用人工编辑的文件替换 `sec-option-result.json`，确认上传体被拒或摘要不符被检测；用被修改的产物重试，确认报告记录真实摘要。

---

#### FIND-06: 合规门禁可经 N/A 语义、扫描项收窄与静默上传失败绕过

**复核结论：** ✅ 确认

| 属性 | 值 |
|------|-----|
| **严重级别** | Important |
| **CVSS 4.0 评分** | 7.1 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:H/VA:N/SC:N/SI:L/SA:N` |
| **CWE** | [CWE-693: Protection Mechanism Failure](https://cwe.mitre.org/data/definitions/693.html) |
| **OWASP** | A09:2025 – Security Logging & Alerting Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Medium |

**描述：**

无需改动被审代码即可中和门禁：其一，任何无法确定状态的选项被报为 `N/A` 并从分母剔除（`applicableFiles = yes + no`），因此一个大量是静态/Go/strip 的产物会报告高开启率，而实际核验的选项很少；其二，调用方控制 `scan-options`，工作流作者可直接省略构建未通过的检查；其三，报告上传失败时扫描器仅记 `uploadInfo.success = false` 且从不使步骤失败，流水线可在完全没有合规记录的情况下转绿。三者叠加，把加固门禁变成“可选上报”。

**证据：**

- `dist/bin/sec_option_scan.py:483-495`（N/A 从分母剔除）：
```python
total_files = yes_count + no_count + na_count
applicable_files = yes_count + no_count
if applicable_files > 0:
    rate = round(yes_count / applicable_files * 100, 2)
else:
    rate = -1
```
- `dist/bin/sec_option_scan.py:992-999`（`scan-options` 逐字作为 14 项子集被接受）：
```python
if len(sys.argv) >= 4 and sys.argv[3]:
    scan_options = [opt.strip() for opt in sys.argv[3].split(',') if opt.strip()]
    invalid = set(scan_options) - set(ALL_OPTION_KEYS)
    if invalid:
        print(f"ERROR: Invalid scan-options: {invalid}", file=sys.stderr)
        sys.exit(1)
```
- `dist/scanner.js:120-127`（上传失败不使步骤失败）：
```javascript
if (uploadResult.success) {
  this.logger.info(`Successfully uploaded sec-option report, recordId: ${uploadResult.recordId}`);
  result.uploadInfo = { success: true, recordId: uploadResult.recordId };
} else {
  this.logger.error(`Failed to upload sec-option report: ${uploadResult.error}`);
  result.uploadInfo = { success: false, error: uploadResult.error };
}
```
- `dist/index.js:54602`（入口在扫描/上报后继续以成功收尾）：`core.info('Sec-option scan completed successfully');`

**修复建议：**

使门禁“失败关闭”：在接受报告前要求最低的适用文件比例与最低 N/A 比例；将生效选项集签名进报告，使收窄对后端可见；上报未成功时使步骤失败（或输出失败）。把 `scan-options` 视为显式、可审计的覆盖项并记入报告，而非静默缩减覆盖。

**验证步骤：**

以 `scan-options: nx` 运行并确认报告记录收窄后的选项集；将上传器指向不可达网关并确认步骤失败；扫描一个基本静态的二进制并确认 N/A 比例被显式呈现且门禁不只凭高开启率通过。

---

### 5.3 中危（Medium/Moderate）漏洞

---

#### FIND-07: 无界递归扫描与归档解压耗尽执行机资源

**复核结论：** ✅ 确认

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 6.9 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:L` |
| **CWE** | [CWE-409: Improper Handling of Highly Compressed Data (Data Amplification)](https://cwe.mitre.org/data/definitions/409.html) |
| **OWASP** | A10:2025 – Mishandling of Exceptional Conditions |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Medium |

**描述：**

归档处理没有资源预算。`try_extract_archive` 将任何被识别的归档解压进临时目录，却不限制总展开字节数、条目数、单条目大小或嵌套深度，且 `scan_directory` 会递归进每个嵌套归档。精心构造的产物（解压炸弹、深层嵌套 `.tar.gz` 链或超大目录树）会持续展开，直到执行机磁盘/内存耗尽或任务超时，从而对后续任务造成共享自托管执行机的拒绝服务。编排侧每次运行的工作量同样无界。

**证据：**

- `dist/bin/sec_option_scan.py:161-177`（解压无大小/条目计量，仅校验路径）：
```python
try:
    if is_zip:
        with zipfile.ZipFile(file_path, 'r') as zf:
            _safe_extract_zip(zf, tmp_dir)
    elif is_run:
        _extract_run_payload(file_path, tmp_dir)
    elif is_deb:
        _extract_deb(file_path, tmp_dir)
    else:
        with tarfile.open(file_path, 'r:*') as tf:
            _safe_extract_tar(tf, tmp_dir)
    return tmp_dir
```
- `dist/bin/sec_option_scan.py:95-99`（对嵌套归档无界递归）：
```python
extracted = try_extract_archive(item.path)
if extracted:
    extracted_dirs.append(extracted)
    result.extend(scan_directory(extracted, extracted_dirs, scan_options, extracted, visited))
```
- `dist/scanner.js:63-69`（状态仅由 `summary` 推导，无预算强制）：
```javascript
const succeededCount = scanResult.summary?.totalScannedFiles || 0;
const failedCount = scanResult.summary?.failedCount || 0;
if (failedCount > 0) {
  status = succeededCount > 0 ? 2 : 0;
} else {
  status = 1;
}
```

**修复建议：**

在扫描器中设定硬限制：总解压字节、解压条目数、最大嵌套深度与墙钟截止时间，越限即以显式失败状态中止。以运行字节计数器流式解压，而非完全展开；超出条目上限的成员跳过。把强制限制呈现到报告中，使越限产物可见而非被静默截断。

**验证步骤：**

扫描一个 zip 炸弹（如高压缩比 1GB 归档）与一条嵌套归档链，确认扫描器在配置上限处中止并给出清晰状态，而非填满磁盘或挂起。

---

#### FIND-08: 凭证材料与内部路径暴露于 CI 日志与工作区文件

**复核结论：** ✅ 确认

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 6.7 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html) |
| **OWASP** | A09:2025 – Security Logging & Alerting Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Low |

**描述：**

敏感材料进入共享、长期的 CI 日志与工作区文件。OIDC 客户端即使在非调试模式也以 error 级打印 Token 声明（`iss`/`aud`/`azp`/`sub`），其 `mask()` 辅助仅保留首六尾四字符而非完整脱敏。入口记录 `artifact-path`/`gitUrl`/`pipelineName`/`runNumber`，其凭证清洗仅去除 `https://user@host` 形式，git 远端 URL 中其他内嵌凭证编码会存活进日志与上报体。检测器逐字回显 Python `stdout`/`stderr`（含 `traceback.print_exc` 路径），结果 JSON 以默认权限写入工作区。自托管执行机上的日志可被运行器运维者与后续任务读取。

**证据：**

- `dist/index.js:5308-5319` 与 `:5368`（error 级打印声明）：
```javascript
function _printTokenClaims(claims, logFn) {
  if (!claims) { logFn('（无法解析 OIDC Token payload）'); return; }
  logFn('-- OIDC Token 声明（用于与华为云信任策略比对）--');
  logFn(`iss : ${JSON.stringify(claims.iss)}`);
  logFn(`aud : ${JSON.stringify(claims.aud)}`);
  logFn(`azp : ${JSON.stringify(claims.azp)}`);
  logFn(`sub : ${JSON.stringify(claims.sub)}`);
}
...
_printTokenClaims(claims, error);
```
- `dist/index.js:5632-5637`（截断式脱敏）：
```javascript
function mask(value, head = 6, tail = 4) {
  if (!value) return '(空)';
  const s = String(value);
  if (s.length <= head + tail) return s.slice(0, 2) + '***' + s.slice(-2);
  return s.slice(0, head) + '***' + s.slice(-tail) + `（长度 ${s.length}）`;
}
```
- `dist/index.js:54369`（仅去除 HTTPS userinfo）：`gitUrl = remoteUrl.replace(/https:\/\/[^@]+@/, 'https://');`
- `dist/index.js:54454-54456`（记录标识）：`core.info(\`gitUrl: ${gitUrl || '(empty)'}\`)` 等
- `dist/detectors/SecOptionDetector.js:94-99`（逐字回显子进程输出）：
```javascript
if (stdout.trim()) { this.logger.info(`Python stdout: ${stdout.trim()}`); }
if (stderr.trim()) { this.logger.warn(`Python stderr: ${stderr.trim()}`); }
```
- `dist/bin/sec_option_scan.py:179-181`（打印完整 traceback）：
```python
print(f"Warning: failed to extract {file_path}: {e}", file=sys.stderr)
 traceback.print_exc(file=sys.stderr)
```

**修复建议：**

绝不记录身份声明或原始远端 URL；仓库身份从平台变量取得并经 `core.setSecret` 传递。以完整脱敏替换部分掩码。记录前对子进程输出做截断与路径脱敏。以 `0600` 权限在私有临时目录创建结果文件；当上传在进程内完成时避免持久化中间文件。

**验证步骤：**

运行扫描并检索任务日志中的 `iss :`、`sub :`、`access_key_id` 与任意 `://user:token@` 模式，均应缺失或已完整脱敏；确认 `sec-option-result.json` 以 `0600` 权限创建。

---

#### FIND-09: 未校验的外部输入直达特权文件、URL 与子进程操作

**复核结论：** ✅ 确认

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 6.3 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:N/SI:L/SA:N` |
| **CWE** | [CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')](https://cwe.mitre.org/data/definitions/22.html) |
| **OWASP** | A05:2025 – Injection |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Low |

**描述：**

三个插件输入未经校验地流入特权操作。`output` 输入（及 `ATOMGIT_OUTPUT` 环境变量）被直接用于 `fs.mkdirSync(..., { recursive: true })` 与 `fs.writeFileSync`，因此调用方可创建目录并以运行器用户覆盖任意文件。`artifact-download-url` 未经校验转发后端，使工作流作者可定义展示给报告消费方的产物下载链接（链接仿冒与分发非预期内容）。Python 调用以调用方提供的路径拼装 argv，仅因从不使用 shell 而安全，故其遏制依赖一个无处断言的不变量；一旦改为 `exec`/shell 形式，这些输入即变为命令注入。

**证据：**

- `dist/index.js:54338` 与 `:54481-54483`（`output` 直接构建结果路径）：
```javascript
const outputFile = getInput('output') || 'sec-option-result.json';
...
const targetOutput = scanTargets.length > 1
  ? path.join(path.dirname(outputFile), `sec-option-result-${target.packageName || i}.json`)
  : outputFile;
```
- `dist/scanner.js:49-51` 与 `:97-101`（`path.resolve` 后可越出工作区，随后递归建目录与写文件）：
```javascript
const outputFile = path.isAbsolute(options.output || this.config.output)
  ? (options.output || this.config.output)
  : path.resolve(this.workingDir, options.output || this.config.output);
...
const outputDir = path.dirname(outputFile);
if (outputDir && !fs.existsSync(outputDir)) { fs.mkdirSync(outputDir, { recursive: true }); }
fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf8');
```
- `dist/index.js:54493-54499`（下载 URL 未校验转发）：
```javascript
let resolvedDownloadUrl = artifactDownloadUrl;
if (artifactDownloadUrl && artifactDownloadUrl.endsWith('/')) {
  const subdir = target.downloadSubdir;
  resolvedDownloadUrl = artifactDownloadUrl + (subdir ? subdir + '/' : '') + target.artifactName;
}
```
- `dist/detectors/SecOptionDetector.js:71-80`（argv 数组 spawn，无 shell）：
```javascript
const args = [this.scriptPath, sourceDir, outputFile];
if (scanOptions && scanOptions.length > 0) { args.push(scanOptions.join(',')); }
...
const proc = spawn(pythonCmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
```

**修复建议：**

以 `path.resolve` 归一化所有路径并拒绝工作区根之外者，结果文件以 `O_EXCL` 与模式 `0600` 创建。上传前对 `artifact-download-url` 按批准 scheme 与主机允许清单校验。保留 argv 数组 spawn 形式并显式断言参数不含 shell 元字符，配一个在引入 shell 调用时失败的单元测试。

**验证步骤：**

传入 `output: ../../evil.json` 确认插件拒绝该路径；传入 `artifact-download-url: https://evil.example/x.sh` 确认上传前被拒；确认有单测断言检测器从不使用 `shell: true`。

---

#### FIND-10: 弱传输信任默认值——明文 HTTP 回退与无证书固定

**复核结论：** ✅ 确认（明文默认值本仓入口不可达，属防御纵深；无证书固定为真实弱项）

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 5.9 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-319: Cleartext Transmission of Sensitive Information](https://cwe.mitre.org/data/definitions/319.html) |
| **OWASP** | A04:2025 – Cryptographic Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Low |

**描述：**

尽管入口始终传入 HTTPS 网关 URL，`CicdUploader` 类在省略 `cicdUrl` 时默认 `http://localhost:8080`。任何其他嵌入该类的调用方（或入口的未来改动）都将以明文 HTTP 传输 AK/SK 签名、OIDC 派生的 `X-Security-Token` 与合规报告，此时服务器身份不可验证、内容可被路径上任何一方恢复或篡改。独立地，网关身份仅依赖 TLS 而无证书/CA 固定，故执行机级 CA 失陷或中间代理可呈现接受签名报告的仿冒端点；由于后端认证调用方但不校验报告的 `gitUrl` 内容，即可为任意仓库伪造合规记录。

**证据：**

- `dist/uploaders/CicdUploader.js:248`（明文默认值）：`this.baseUrl = config.cicdUrl || 'http://localhost:8080';`
- `dist/index.js:54354`（入口覆盖为 HTTPS，但类本身不强制）：`const cicdUrl = 'https://apig.openlibing.com:443';`
- `dist/uploaders/CicdUploader.js:329`（无 agent/固定配置）：`const response = await axios.post(url, body, { headers, timeout: this.timeout });`

**修复建议：**

移除明文默认值，使 `CicdUploader` 在构造时与请求时拒绝任何非 `https:` URL。在客户端固定 APIG 证书或签发 CA（或依赖本身受随的执行机信任库），并检测代理拦截。服务端将接受的报告绑定到联邦主体并据此重新校验 `gitUrl`，使仿冒网关无法为任意仓库创建记录。

**验证步骤：**

以 `cicdUrl: 'http://apig.openlibing.com'` 实例化 `CicdUploader` 确认构造/请求抛错；通过替换 CA 的代理尝试上传并确认客户端拒绝连接。

---

#### FIND-11: 出站请求无超时且子进程输出无上限

**复核结论：** ✅ 确认

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 5.3 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-400: Uncontrolled Resource Consumption](https://cwe.mitre.org/data/definitions/400.html) |
| **OWASP** | A10:2025 – Mishandling of Exceptional Conditions |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Low |

**描述：**

三条执行路径可无限阻塞或无界增长。共享的 `sendRequest` 以无 `AbortSignal`、无超时的 `fetch` 发请求，故 OIDC Token 请求与 STS 换证（以及 OIDC 模式的 `callApig` 上传）在端点停摆时挂起到平台级任务超时。Python 子进程以无 `timeout` 派发，卡在恶意产物上的扫描器会让检测器永远等待 `close` 事件。两路子流输出被累积进无界字符串（`stdout += data.toString()`），使能令扫描器话多的恶意产物不仅耗时还能耗尽执行机内存。

**证据：**

- `dist/index.js:5463-5468`（无 `signal`/超时）：
```javascript
const fetchImpl = typeof fetch === 'function' ? fetch : (...args) => (__nccwpck_require2_(6752).fetch)(...args);
res = await fetchImpl(url, { method, headers, body: body || undefined });
```
- `dist/detectors/SecOptionDetector.js:78-91`（无 `timeout` 且无界累积）：
```javascript
const proc = spawn(pythonCmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
let stdout = '';
let stderr = '';
proc.stdout.on('data', (data) => { stdout += data.toString(); });
proc.stderr.on('data', (data) => { stderr += data.toString(); });
```

**修复建议：**

为每个出站请求传 `AbortSignal.timeout(...)` 并用退避限制重试。为 Python `spawn` 加 `timeout`（及 `killSignal`），触发时干净地使扫描失败。给捕获的子进程输出设上限（环形缓冲或字节限制），达上限即停止转发。

**验证步骤：**

将 OIDC/STS 端点指向黑洞 socket，确认请求在配置超时内中止而非等到任务超时；令扫描器输出无界内容并确认内存保持有界。

---

#### FIND-12: Windows 执行机上可预测的世界可写临时目录

**复核结论：** ✅ 确认（前缀随机子目录削弱了“预填充”场景，但重解析点/占用基目录场景成立）

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 5.1 |
| **CVSS 向量** | `CVSS:4.0/AV:L/AC:H/AT:N/PR:L/UI:N/VC:N/VI:L/VA:N/SC:N/SI:L/SA:N` |
| **CWE** | [CWE-379: Creation of Temporary File in Directory with Insecure Permissions](https://cwe.mitre.org/data/definitions/379.html) |
| **OWASP** | A01:2025 – Broken Access Control |
| **Tier** | Tier 2（Local Process Access） |
| **修复工作量** | Low |

**描述：**

Windows 下解压器为规避过长的默认临时路径，在调用 `tempfile.mkdtemp` 前刻意创建并使用固定、可预测的基目录 `D:\sec_option_tmp` 与 `C:\sec_option_tmp`（`os.makedirs(short_base, exist_ok=True)`）。每次运行的目录名前缀随机，但父目录是共享自托管执行机上稳定的世界可写位置。同主机进程可预创建基目录、在其中放置目录重解析点（junction/symlink）指向目标子路径、或耗尽该位置使解压失败；由于解压内容驱动合规结果，操纵这些目录也能影响扫描结论。

**证据：**

`dist/bin/sec_option_scan.py:150-159`：
```python
if sys.platform == 'win32':
    for short_base in (r'D:\sec_option_tmp', r'C:\sec_option_tmp'):
        try:
            os.makedirs(short_base, exist_ok=True)
            tmp_dir = tempfile.mkdtemp(prefix='s_', dir=short_base)
            break
        except Exception:
            continue
```
解压目录成为该归档的扫描根（`scan_directory(extracted, ..., extracted, visited)`，见 `dist/bin/sec_option_scan.py:99`），其内容被当作产物信任。

**修复建议：**

在 OS 临时目录或具受限 ACL 的执行机私有目录下创建工作目录，并在解压前验证所建目录不是重解析点。若长路径约束真实存在，优先启用长路径支持或在解压时缩短嵌套成员名，而非使用固定共享路径。

**验证步骤：**

在 Windows 执行机上将 `C:\sec_option_tmp` 预创建为指向攻击者位置的 junction，确认扫描器拒绝使用；确认工作目录创建于私有、ACL 受限的基目录下。

---

#### FIND-14: 打包内 HTTP 客户端支持 TLS 校验旁路，且 OIDC 换证依赖可变全局 `fetch`

**复核结论：** ✅ 确认（属防御纵深：`ignoreSslError` 路径当前不可达，但能力随包分发）

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 4.6 |
| **CVSS 向量** | `CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-295: Improper Certificate Validation](https://cwe.mitre.org/data/definitions/295.html) |
| **OWASP** | A04:2025 – Cryptographic Failures |
| **Tier** | Tier 3（Host/OS Access） |
| **修复工作量** | Low |

**描述：**

ncc 打包内联了 `@actions/http-client`，当 `requestOptions.ignoreSslError` 启用时其 `_getAgent`/`_getProxyAgentDispatcher` 会设置 `rejectUnauthorized: false`。这些代码路径当前无法从本仓自身逻辑到达（`_ignoreSslError` 默认 `false`，无调用方设置），故**不是活跃漏洞**；但把该能力装进被执行的分发包，意味着一处小配置或依赖改动即可静默关闭承载凭证流量的证书校验。与此同时，OIDC/STS 客户端在调用时解析 `globalThis.fetch` 而非捕获已导入引用，故进程中任何代码（或被篡改的打包依赖）都可替换它并拦截 ID Token、临时凭证与 `Authorization` 头。

**证据：**

- `dist/index.js:3230-3237` 与 `:3254-3260`：
```javascript
if (usingSsl && this._ignoreSslError) {
  agent.options = Object.assign(agent.options || {}, { rejectUnauthorized: false });
}
```
- `dist/index.js:2840` 与 `:2851-2854`：
```javascript
this._ignoreSslError = false;
...
if (requestOptions) {
  if (requestOptions.ignoreSslError != null) {
    this._ignoreSslError = requestOptions.ignoreSslError;
```
- `dist/index.js:5463`（运行时选取全局 `fetch`）：
```javascript
const fetchImpl = typeof fetch === 'function' ? fetch : (...args) => (__nccwpck_require2_(6752).fetch)(...args);
```

**修复建议：**

在模块加载时从显式导入捕获一次 `fetch` 实现，使其无法在运行中替换，并断言所解析实现符合预期。将 `ignoreSslError` 视为禁用项：启动时断言 TLS 校验开启，并在打包时移除此旁路或加防护。增加一个在设置 `rejectUnauthorized` 为 `false` 时失败的测试。

**验证步骤：**

在包装器中于调用插件前 patch `globalThis.fetch`，确认 OIDC 换证仍使用被捕获的实现（无拦截）；grep 构建产物确认无可达路径能设置 `rejectUnauthorized: false`。

---

#### FIND-15: 打包内分发两份相同扫描脚本且无完整性校验

**复核结论：** ✅ 确认（含实测哈希一致）

| 属性 | 值 |
|------|-----|
| **严重级别** | Moderate |
| **CVSS 4.0 评分** | 4.2 |
| **CVSS 向量** | `CVSS:4.0/AV:L/AC:H/AT:N/PR:H/UI:N/VC:N/VI:H/VA:N/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-1059: Insufficient Technical Documentation](https://cwe.mitre.org/data/definitions/1059.html) |
| **OWASP** | A08:2025 – Software/Data Integrity Failures |
| **Tier** | Tier 3（Host/OS Access） |
| **修复工作量** | Low |

**描述：**

仓内存在两份逐字节相同的扫描脚本：`dist/sec_option_scan.py` 与 `dist/bin/sec_option_scan.py`（SHA-256 同为 `183db31a7c32c01430848d8015ec6b917ebf9705f6e4bb9158ad2160d3acc700`）。仅 `bin/` 副本被执行，因为 `SecOptionDetector` 解析的是 `path.resolve(__dirname, '..', 'bin', 'sec_option_scan.py')`，而打包脚本会分发整个 `dist` 树。未被引用的副本是注定漂移的死重；且因分发包由 `zip.js` + `ncc build` 产出而无校验清单，审查者与消费方都无法判定给定报告究竟由哪个扫描脚本修订版生成。

**证据：**

- `dist/detectors/SecOptionDetector.js:10`（实际执行副本）：`this.scriptPath = config.scriptPath || path.resolve(__dirname, '..', 'bin', 'sec_option_scan.py');`
- `zip.js:15`（打包整个 `dist` 树，含未用副本）：`zip.addLocalFolder("./dist", "./dist");`
- 实测：`Get-FileHash dist/sec_option_scan.py` 与 `Get-FileHash dist/bin/sec_option_scan.py` 均返回 `183DB31A7C32C01430848D8015EC6B917EBF9705F6E4BB9158AD2160D3ACC700`（文件大小均 46944 字节）。

**修复建议：**

仅保留单一扫描脚本于 `dist/bin/sec_option_scan.py` 并删除 `dist/sec_option_scan.py`（或在打包时生成而非提交）。为发布包产出校验清单（`SHA256SUMS`）并在消费流水线中校验，使被执行的扫描脚本修订版可归因。

**验证步骤：**

确认仓内与构建 zip 中仅剩一个扫描脚本，且 `SecOptionDetector` 仍能解析其脚本路径；验证生成的清单与交付文件一致。

---

### 5.4 低危（Low）漏洞

---

#### FIND-13: 已确认有效的既有防御控制（归档穿越防护、SHA 固定插件、STS 凭证脱敏）

**复核结论：** ✅ 确认（本条为“已有控制”记录，非漏洞）

| 属性 | 值 |
|------|-----|
| **严重级别** | Low |
| **CVSS 4.0 评分** | 3.1 |
| **CVSS 向量** | `CVSS:4.0/AV:N/AC:H/AT:N/PR:L/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N` |
| **CWE** | [CWE-693: Protection Mechanism Failure](https://cwe.mitre.org/data/definitions/693.html) |
| **OWASP** | A08:2025 – Software/Data Integrity Failures |
| **Tier** | Tier 2（Authenticated User） |
| **修复工作量** | Low |

**描述：**

若干刻意设置的防御控制存在且正确，记录于此以免与上述缺口一同被忽略。Python 解压器在解压前校验每个归档成员与链接目标（`_entry_path_unsafe` 拒绝绝对路径、盘符路径与 `..` 段；`_safe_extract_tar` 还校验 symlink/hardlink 目标；`visited` realpath 集打破符号链接环），阻断 zip-slip/tar-slip 穿越。度量工作流将其第三方插件固定到完整 commit SHA，消除标签重定向与仿冒风险。OIDC 客户端在记录日志前对 `access_key_id`、`secret_access_key`、`security_token` 脱敏，其调试请求/响应转储应用字段级与 JWT 模式脱敏。残余缺口（Windows 名称怪癖、缺少显式 `tarfile` `filter=`、截断式脱敏）已在 FIND-08 与 `SecOptionScanScript` 的 STRIDE 条目中跟踪。

**证据：**

- `dist/bin/sec_option_scan.py:186-233`：`_entry_path_unsafe`、`_safe_extract_zip`、`_safe_extract_tar`（成员与 `linkname` 校验）。
- `dist/bin/sec_option_scan.py:78-82`（符号链接环保护）：
```python
real = os.path.realpath(scan_path)
if real in visited:
    return result
visited.add(real)
```
- `.gitcode/workflows/code-metrics-scan.yml:23`：`uses: openlibing/code-metrics-action@117c0606ad741ef5e6b564dca9307e25e1d9e2e8`
- `dist/index.js:5640-5644`（`SENSITIVE_KEYS`）、`:5670-5676`（`maskHeaders`/`maskBody`）、`:5387`（`debug(\`SecurityToken : ${mask(cred.security_token, 10, 10)}\`)`）。

**修复建议：**

保留穿越防护并扩展到 Windows 保留名与尾点/尾空格形式，另为纵深防御在 `tarfile.extract` 传 `filter='data'`（日志暴露见 FIND-08）。为每个工作流持续 SHA 固定第三方插件并记录所审 commit。将脱敏从截断升级为对令牌与身份声明的完整脱敏。

**验证步骤：**

解压一个含 `../evil.txt` 与绝对路径成员的 zip，确认两者均被跳过并告警；确认度量工作流仍引用 40 位 SHA；确认调试输出中不出现未脱敏的 `secret_access_key` 或 `security_token`。

---

## 6. 修复建议与行动计划

### 6.1 快速修复（Quick Wins）

以下修复工作量低、影响大，建议立即实施：

| 优先级 | 漏洞编号 | 修复内容 | 工作量 |
|--------|---------|---------|--------|
| P0 | FIND-03 | Python 依赖改用 `--require-hashes` + 受审索引，去除 `--break-system-packages` | Low |
| P0 | FIND-08 | 声明打印改由调试开关控制、令牌完整脱敏、停止记录原始远端 URL | Low |
| P0 | FIND-09 | 结果路径限定工作区 + `O_EXCL`/`0600`；`artifact-download-url` 加 scheme/主机允许清单 | Low |
| P0 | FIND-10 | 删除 `http://localhost:8080` 默认值，构造/请求时拒绝非 HTTPS | Low |
| P1 | FIND-11 | 出站请求加 `AbortSignal.timeout()`；`spawn` 加 `timeout`；捕获输出设上限 | Low |
| P1 | FIND-12 | 用 OS 临时目录下的 `tempfile.mkdtemp()` 替换固定基目录，校验非重解析点 | Low |
| P1 | FIND-15 | 保留单一扫描脚本、删除重复副本、产出 `SHA256SUMS` | Low |
| P1 | FIND-13 | 保留既有控制，扩展穿越防护到 Windows 名称怪癖，`tarfile` 传 `filter='data'` | Low |

### 6.2 中期修复

| 优先级 | 漏洞编号 | 修复内容 | 工作量 |
|--------|---------|---------|--------|
| P0 | FIND-01 | 拆分/隔离不受信任 PR 检出与执行；移除 `allow-unsafe-pr-checkout`；`npm ci --ignore-scripts`；以任务级令牌替换 `ROBOT_TOKEN` | Medium |
| P0 | FIND-02 | 第三方插件全部 SHA 固定；`id-token: write` 收敛到单步骤并加任务级 `permissions`；标签依据平台任务状态推导 | Medium |
| P0 | FIND-04 | 仅经 `core.getInput` 接收身份输入；移除 `HUAWEICLOUD_OIDC_TOKEN` 回退；校验 `ACTIONS_ID_TOKEN_REQUEST_URL` 主机/HTTPS；约束 IAM 信任策略 | Medium |
| P1 | FIND-05 | 计算被扫产物摘要并纳入上报体；签名内存对象而非重读文件；`gitUrl` 取自平台变量；后端拒绝摘要不符报告 | Medium |
| P1 | FIND-06 | 门禁失败关闭：最低适用文件比例/N/A 比例、选项集签名入报告、上传失败使步骤失败 | Medium |
| P1 | FIND-07 | 扫描器设定解压字节/条目数/嵌套深度/墙钟硬限制，越限显式失败 | Medium |
| P2 | FIND-14 | 模块加载时捕获 `fetch` 引用；禁止并可检测 `ignoreSslError` | Low |

### 6.3 长期安全改进

1. **建立 CI/CD 供应链安全基线**
   - 全部第三方插件 SHA 固定并在评审记录中登记所审 commit。
   - `dist/` 打包产物引入校验清单与可归因的构建来源（SLSA 思路）。
   - 在流水线中集成依赖漏洞扫描（如 lockfile 审计、SCA）与 SAST。

2. **强化无入站测听进程的运行时自检**
   - 启动时断言 TLS 校验开启、`fetch` 引用已捕获、临时目录非重解析点。
   - 为关键不变量（argv spawn 无 shell、结果路径限定工作区）编写会失败的回归测试。

3. **建立安全开发生命周期（SDL）**
   - 代码评审加入安全检查清单（信任边界、Secret 处理、路径校验）。
   - 对开发团队进行 CI 供应链与凭证处理培训，形成安全编码规范。

### 6.4 修复优先级矩阵

```
影响程度
  高 │ FIND-01（CI RCE）      │ FIND-02, FIND-04
     │ FIND-05, FIND-06       │ FIND-03
     ├────────────────────────┼────────────────────────┤
  中 │ FIND-07, FIND-08       │ FIND-09, FIND-10
     │ FIND-14, FIND-15       │ FIND-11, FIND-12
     ├────────────────────────┼────────────────────────┤
  低 │ FIND-13                │
     └────────────────────────┴────────────────────────┘
          低                        中/高
                      利用难度
```

---

## 7. 附录

### 7.1 威胁覆盖验证表

| 威胁 ID | 对应发现 | 状态 |
|---------|---------|------|
| T01.S | FIND-04 | ✅ 已覆盖 |
| T01.T | FIND-05 | ✅ 已覆盖 |
| T01.I | FIND-08 | ✅ 已覆盖 |
| T01.D | FIND-11 | ✅ 已覆盖 |
| T01.E | FIND-09 | ✅ 已覆盖 |
| T01.A | FIND-09 | ✅ 已覆盖 |
| T02.T | FIND-05 | ✅ 已覆盖 |
| T02.D | FIND-07 | ✅ 已覆盖 |
| T02.A | FIND-06 | ✅ 已覆盖 |
| T03.T | FIND-09 | ✅ 已覆盖 |
| T03.I | FIND-08 | ✅ 已覆盖 |
| T03.D | FIND-11 | ✅ 已覆盖 |
| T04.T | FIND-13 | ✅ 已缓解（既有控制） |
| T04.T2 | FIND-13 | ✅ 已覆盖 |
| T04.T3 | FIND-15 | ✅ 已覆盖 |
| T04.I | FIND-08 | ✅ 已覆盖 |
| T04.D | FIND-07 | ✅ 已覆盖 |
| T04.E | FIND-12 | ✅ 已覆盖 |
| T04.A | FIND-06 | ✅ 已覆盖 |
| T05.S | FIND-10 | ✅ 已覆盖 |
| T05.T | FIND-05 | ✅ 已覆盖 |
| T05.I | FIND-08 | ✅ 已覆盖 |
| T06.S | FIND-04 | ✅ 已覆盖 |
| T06.T | FIND-14 | ✅ 已覆盖 |
| T06.I | FIND-08 | ✅ 已覆盖 |
| T06.D | FIND-11 | ✅ 已覆盖 |
| T07.S | FIND-01 | ✅ 已覆盖 |
| T07.T | FIND-01 | ✅ 已覆盖 |
| T07.I | FIND-01 | ✅ 已覆盖 |
| T07.E | FIND-02 | ⚠️ 部分成立（表达式注入子项证据不足，整项保留） |
| T07.A | FIND-02 | ✅ 已覆盖 |
| T08.S | FIND-02 | ✅ 已覆盖 |
| T08.T | FIND-02 | ✅ 已覆盖 |
| T08.E | FIND-02 | ✅ 已覆盖 |
| T09.T | FIND-13 | ✅ 已缓解（既有控制） |
| T09.E | FIND-02 | ✅ 已覆盖 |
| T10.T | FIND-05 | ✅ 已覆盖 |
| T10.T2 | FIND-05 | ✅ 已覆盖 |
| T11.T | FIND-05 | ✅ 已覆盖 |
| T11.I | FIND-08 | ✅ 已覆盖 |
| T12.T | FIND-08 | ✅ 已覆盖 |
| T12.I | FIND-08 | ✅ 已覆盖 |
| T13.S | FIND-10 | ✅ 已覆盖 |
| T13.T | FIND-10 | ✅ 已覆盖 |
| T14.S | FIND-04 | ✅ 已覆盖 |
| T14.I | FIND-13 | ✅ 已缓解（既有控制） |
| T15.S | FIND-04 | ✅ 已覆盖 |
| T15.I | FIND-04 | ✅ 已覆盖 |
| T16.S | FIND-03 | ✅ 已覆盖 |
| T16.T | FIND-03 | ✅ 已覆盖 |

### 7.2 漏洞误报复核结果

对 `3-findings.md` 中 FIND-01..FIND-15 逐条打开真实源码（`dist/` 打包产物、`action.yml`、`.gitcode/workflows/*.yml`、`zip.js`、`package.json`、`.pre-commit-config.yaml`）核验。**结论分布：确认 14 条、部分成立 1 条、误报 0 条、无法验证 0 条。**

| 发现 ID | 原严重级别 | 复核结论 | 证据（文件:行号） | 说明 |
|---------|-----------|---------|------------------|------|
| FIND-01 | Critical | ✅ 确认 | `.gitcode/workflows/pre-commit.yml:8,42,47,48,56-57,33`；`dist/index.js:54278` | `pull_request_target` + `allow-unsafe-pr-checkout: true` + 自托管执行机 + `npm install` 均核实。**说明：** `ROBOT_TOKEN` 由同工作流内 `pr-label-running`/`label-pr` 任务使用，`pre-commit` 任务的检出步骤本身未显式传 token；但在 `pull_request_target` 语境下工作流可访问仓库 Secrets，且不受信任 PR 代码运行于持久共享执行机上，RCE 与跨任务/跨仓库影响面成立，严重级别维持 Critical。 |
| FIND-02 | Important | ⚠️ 部分成立 | `.gitcode/workflows/pre-commit.yml:74,87`；`nightly-schedule-scan.yml:10,47,55`；`code-metrics-scan.yml:11` | 子项 (2) 可变标签引用、(3) workflow 级 `id-token: write`、标签由表达式推导（第 87 行）均**确认**。子项 (1) `extra_args: ${{ inputs.extra_args }}` 行存在，但本工作流**未声明 `inputs`**（`workflow_dispatch` 无 `inputs`、非 `workflow_call`），故该表达式求值为空、不能构成命令/表达式注入，此子项**不成立**。因确认子项各自达高危，严重级别维持 Important（未按“部分成立下调”处理，理由：降级会使真实供应链风险被低估）。 |
| FIND-03 | Important | ✅ 确认 | `dist/index.js:54385-54392` | `--break-system-packages pyelftools==0.31 -i https://mirrors.aliyun.com/pypi/simple/` 核实，无 `--require-hashes`/`--only-binary`。 |
| FIND-04 | Important | ✅ 确认 | `dist/index.js:54280,5719-5723,5744-5750,5189-5197` | 环境覆盖 `INPUT_*`、`HUAWEICLOUD_OIDC_TOKEN` 回退、未校验 `ACTIONS_ID_TOKEN_REQUEST_URL`、IAM 固定配置均核实；换证可行性依赖外部 IAM 信任策略（报告已列为 Needs Verification）。 |
| FIND-05 | Important | ✅ 确认 | `dist/index.js:54411-54415,54368`；`dist/scanner.js:97-101`；`dist/detectors/SecOptionDetector.js:120-133`；`dist/uploaders/CicdUploader.js:299,323-329` | 产物仅存在性检查、结果写后重读、签名覆盖所交付 body、`gitUrl` 经 `git` 命令取全部核实。 |
| FIND-06 | Important | ✅ 确认 | `dist/bin/sec_option_scan.py:483-495,992-999`；`dist/scanner.js:120-127`；`dist/index.js:54602` | N/A 剔除分母、`scan-options` 逐字接受、上传失败不使步骤失败（入口以 `completed successfully` 收尾）均核实。 |
| FIND-07 | Moderate | ✅ 确认 | `dist/bin/sec_option_scan.py:161-177,95-99`；`dist/scanner.js:63-69` | 解压无大小/条目计量、对嵌套归档无界递归、状态无预算强制均核实。 |
| FIND-08 | Moderate | ✅ 确认 | `dist/index.js:5308-5319,5368,5632-5637,54369,54454-54456`；`dist/detectors/SecOptionDetector.js:94-99`；`dist/bin/sec_option_scan.py:179-181` | error 级声明打印、截断式脱敏、仅去 HTTPS userinfo、子进程输出逐字回显、traceback 打印均核实。 |
| FIND-09 | Moderate | ✅ 确认 | `dist/index.js:54338,54481-54483,54493-54499`；`dist/scanner.js:49-51,97-101`；`dist/detectors/SecOptionDetector.js:71-80` | `output` 越界建目录/写文件、下载 URL 未校验、argv spawn 无 shell 均核实。 |
| FIND-10 | Moderate | ✅ 确认 | `dist/uploaders/CicdUploader.js:248,329`；`dist/index.js:54354` | 明文默认值存在且本仓入口用 HTTPS 覆盖（明文路径需其他嵌入方）；无证书固定（`axios.post` 无 agent）核实。 |
| FIND-11 | Moderate | ✅ 确认 | `dist/index.js:5463-5468`；`dist/detectors/SecOptionDetector.js:78-91` | `fetch` 无 `signal`/超时、`spawn` 无 `timeout`、输出无界累积均核实。 |
| FIND-12 | Moderate | ✅ 确认 | `dist/bin/sec_option_scan.py:150-159,99` | 固定基目录 `D:\sec_option_tmp`/`C:\sec_option_tmp` + `mkdtemp(prefix='s_')` 核实。说明：前缀随机子目录削弱“预填充”场景，但 junction/占用基目录场景成立。 |
| FIND-13 | Low | ✅ 确认 | `dist/bin/sec_option_scan.py:186-233,78-82`；`code-metrics-scan.yml:23`；`dist/index.js:5640-5644,5670-5676,5387` | 归档穿越/链接校验、符号链接环保护、SHA 固定插件、STS 凭证脱敏均核实；本条为“已有控制”记录。 |
| FIND-14 | Moderate | ✅ 确认 | `dist/index.js:3230-3237,3254-3260,2840,2851-2854,5463` | TLS 旁路代码存在但当前不可达（`_ignoreSslError` 默认 false，无调用方设置）、运行时选取全局 `fetch` 均核实；属防御纵深。 |
| FIND-15 | Moderate | ✅ 确认 | `dist/detectors/SecOptionDetector.js:10`；`zip.js:15`；实测哈希 | 两份脚本 SHA-256 实测一致（`183DB31A...D3ACC700`，均 46944 字节），仅 `bin/` 副本被执行、`zip.js` 打包整个 `dist` 树均核实。 |

**复核结论汇总：** 确认 `14` / 误报 `0` / 部分成立 `1`（FIND-02）/ 无法验证 `0`。经复核无发现被移除，第 5 章各级别数量与原报告一致（仅 FIND-02 标注为部分成立，严重级别维持高危）。

### 7.3 参考资料

#### 安全标准

| 标准 | 链接 |
|------|------|
| Microsoft SDL Bug Bar | https://www.microsoft.com/en-us/msrc/sdlbugbar |
| OWASP Top 10:2025 | https://owasp.org/Top10/2025/ |
| CVSS 4.0 规范 | https://www.first.org/cvss/v4.0/specification-document |
| CWE 弱点库 | https://cwe.mitre.org/ |
| STRIDE 威胁建模 | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats |
| NIST SP 800-53 Rev. 5 | https://csrc.nist.gov/pubs/sp/800-53/r5/upd1/final |
| Python tarfile 解压过滤器 | https://docs.python.org/3/library/tarfile.html#extraction-filters |
| GitHub Actions 安全加固 | https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions |

#### 组件文档

| 组件 | 链接 |
|------|------|
| GitCode / GitHub Actions toolkit（`@actions/core`） | https://github.com/actions/toolkit/tree/main/packages/core |
| 华为云 APIG 签名（SDK-HMAC-SHA256 / V11） | https://support.huaweicloud.com/devg-apig/apig-devguide-python-sdk.html |
| 华为云 STS `AssumeAgencyWithOIDC` | https://support.huaweicloud.com/api-iam/iam_08_0020.html |
| 华为云 OIDC 身份提供商 / 委托 | https://support.huaweicloud.com/usermanual-iam/iam_08_0013.html |
| Axios 请求超时与 TLS/agent 配置 | https://axios-http.com/docs/req_config |
| winston 日志传输与级别 | https://github.com/winstonjs/winston |
| pyelftools | https://github.com/eliben/pyelftools |
| adm-zip | https://github.com/cthackers/adm-zip |

### 7.4 报告元数据

| 属性 | 值 |
|------|-----|
| 分析模型 | DeepSeek-V4.1-Flash |
| 分析方法 | STRIDE-A 威胁建模 + 源码逐条复核 |
| 分析日期 | 2026-10-09 |
| 分析版本 | 分支 `full-check-update` / commit `4a2caef`（2026-10-09） |
| 工作副本路径 | `c:\Users\abing\Documents\develop\openLiBing\security-compilation-options-action` |
| 原始 STRIDE-A 报告集 | `threat-model-20261009-103731/`（0-assessment、0.1-architecture、1-threatmodel、2-stride-analysis、3-findings、threat-inventory.json、report.md） |
| 报告版本 | 1.0（中文单文件版，含误报复核） |
| 分析范围 | 全仓（`action.yml`、`dist/` 运行时、两份 `sec_option_scan.py`、3 个 `.gitcode/workflows/`、`.pre-commit-config.yaml`、`package.json`、`zip.js`）；排除 `node_modules/`、`.git/`、`.idea/` |
| 部署分类 | `LOCALHOST_DESKTOP`（无入站监听端口） |

---

**报告结束**