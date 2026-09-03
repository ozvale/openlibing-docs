# openlibing-sbom-tools 威胁模型分析报告（STRIDE-A）

> **威胁计数说明：** 本报告共识别 **51 条具体威胁**（12 个组件 × STRIDE-A 七类，含 N/A 判定）与 **19 条安全发现**（FIND-01 ~ FIND-19，按可利用性 Tier 1/2/3 分组）。N/A 条目不计入威胁总数。所有发现均附 CVSS 4.0 评分与向量、CWE 与 OWASP Top 10:2025 映射。

---

## 1. 执行摘要

openlibing-sbom-tools 是基于开源工具（Syft、ORT）改造的 SBOM（软件物料清单）工具集，按交付形态分为两类：

- **sbom-ort**：OSS Review Toolkit 的 Kotlin 分支，以 **Maven JAR 库**形式交付（`org.ossreviewtoolkit:model / analyzer / reporter`，经 Gradle `maven-publish` 发布，[build.gradle.kts:364-393](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/build.gradle.kts#L364-L393)）。sbom-server 的 analyzer 模块以 Maven 依赖方式引入这组 JAR，并在**同一 JVM 进程内**调用其依赖解析与 SBOM 生成能力（[analyzer/pom.xml:64-73](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/pom.xml#L64-L73)）。
- **sbom-generator / sbom-tracer**：**离线 SBOM 生成工具**。sbom-generator 为 Syft 的 Go 语言分支，新增"自动解压"能力（zip / tar.gz / run / whl）与 CI 发布流水线脚本（`sbom_runner/`）；sbom-tracer 为基于 BCC 的构建过程追踪 CLI。二者均在 CI 作业中一次性运行，无网络监听端口，分析结果以文件/接口方式交付。

整体安全特征由两条主线构成：其一，**sbom-ort 的 JAR 在 sbom-server 进程内运行，其设计职能就是解析不可信外部项目**——ORT analyzer 在服务端 JVM 中调用包管理器解析被分析项目，项目内构建脚本因此获得 sbom-server 主机的代码执行面，且分析代码与服务端凭据、数据库连接共享同一权限域；其二，**JAR 制品链路全程无完整性校验**。STRIDE-A 分析显示，最高风险不在网络边界，而在上述业务逻辑本身：

1. **sbom-server 进程内代码执行链（Tier 1）**：sbom-server 的 analyzer 模块在 JVM 内直接调用 `org.ossreviewtoolkit.analyzer.Analyzer` 解析不可信项目（[AbstractBaseAnalyzer.java:187-228](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/src/main/java/org/opensourceway/sbom/analyzer/AbstractBaseAnalyzer.java#L187-L228)），包管理器仅屏蔽 Gradle/Sbt 少数几类（npm、pip、go 等均放行），项目内 `package.json` scripts、`setup.py` 等可在 **sbom-server 所在主机**执行；分析进程持有服务端全部权限，无沙箱隔离。这是全局影响最高的风险链。
2. **JAR 制品链完整性缺失（Tier 2）**：sbom-ort 发布的 JAR 无签名、发布身份未做密码学绑定，消费方以固定版本 1.0.0 引入（[pom.xml:309-323](file:///d:/CODE/JAVACODE/openlibing-sbom/pom.xml#L309-L323)）且无校验和校验；制品仓库一旦被篡改即可向 sbom-server 类路径注入恶意代码。
3. **凭据管理薄弱（Tier 2）**：OBS AK/SK 经命令行参数传入（进程列表可见）；构建日志中 wget/curl URL 内嵌凭据未剥离即写入 SBOM 的 `downloadLocation` 并发布；SSH 私钥被 COPY 进镜像层且克隆时禁用 StrictHostKeyChecking。
4. **SBOM 完整性无保障（Tier 2）**：生成的 SPDX JSON 到发布至 SBOM 服务全程无签名，OBS 下载的 `meta.json` 无 schema/来源校验即可驱动发布。

### Action Summary

| 优先级   | 主题                                                                            | 涉及发现                                             |
| -------- | ------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 立即处理 | sbom-server 进程内分析隔离（包管理器白名单收敛、沙箱化 ORT analyzer、最小权限） | FIND-03, FIND-16                                     |
| 短期     | JAR 制品链完整性（发布签名、消费侧校验、依赖树审计）                            | FIND-13, FIND-14, FIND-15                            |
| 短期     | 凭据传递与泄露治理（cmdline AK/SK、URL 内嵌凭据、SSH 私钥入镜像）               | FIND-01, FIND-04, FIND-06                            |
| 短期     | SBOM 签名与发布内容校验                                                         | FIND-08, FIND-05                                     |
| 常态化   | 供应链校验（GONOSUMDB、gradle wrapper、advisor 响应）、容器加固、审计日志       | FIND-07, FIND-09, FIND-10, FIND-17, FIND-18, FIND-19 |

### Quick Wins（低成本高收益）

| 发现    | 措施                                                                                                                          | 代价 |
| ------- | ----------------------------------------------------------------------------------------------------------------------------- | ---- |
| FIND-06 | 删除 `COPY id_* /root/.ssh/`，改用 BuildKit secret 挂载；恢复 `StrictHostKeyChecking=yes` 并预置 known_hosts；克隆固定 commit | Low  |
| FIND-07 | 删除 `go env -w GONOSUMDB=*`；GONOSUMDB 留空恢复 sumdb 校验                                                                   | Low  |
| FIND-04 | run.sh 改从环境变量/文件描述符读取 AK/SK，不再使用 `$1 $2` 位置参数                                                           | Low  |
| FIND-01 | `parse_download_files_from_log` 对 wget/curl URL 复用 `strip_credentials()`                                                   | Low  |
| FIND-03 | 将 `BLOCKED_MANAGERS` 黑名单改为显式白名单，仅放行业务确需的包管理器                                                          | Low  |
| FIND-13 | sbom-server 消费侧启用 Maven 仓库校验和（`dependencyVerifications`）并对 sbom-ort JAR 启用 Gradle signing 发布                | Low  |

---

## 2. 架构概览

### 2.1 系统用途

sbom-ort 将 ORT 的依赖解析、许可证与 SBOM 生成能力封装为 Maven JAR 库（`org.ossreviewtoolkit:model / analyzer / reporter`），发布至制品仓库供 sbom-server 消费——sbom-server 的 analyzer 模块通过 Maven 依赖引入 JAR，在服务端 JVM 进程内对提交的项目执行依赖分析并产出 SPDX 文档。sbom-generator 与 sbom-tracer 为离线 SBOM 生成工具：从制品（容器镜像 / 目录 / 归档文件 / git 构建日志）中提取软件物料清单（SPDX 2.2 JSON），并通过 API 发布到内部 SBOM 管理服务。

### 2.2 技术栈

| 层         | 技术                                                                                                                                     |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 扫描器     | Go 1.18（Syft 分支）、stereoscope、archiver                                                                                              |
| 流水线脚本 | Shell（run.sh）、Python 3.7/3.11（requests、click、esdk-obs-python、jq）                                                                 |
| 合规分析   | Kotlin/JVM 11（ORT 分支）、Gradle                                                                                                        |
| 构建追踪   | Python 3（BCC/eBPF：execsnoop、sslsniff、httpsniff、h2sniff）                                                                            |
| 外部依赖   | 华为云 OBS、内部 SBOM 服务（sbom-api）、gitcode.com、GitHub/Gitee/GitCode API、PyPI/NPM 等包仓库、OSV/OSS Index/Nexus IQ/ScanOSS advisor |
| 构建/部署  | Docker 多阶段构建（Dockerfile_local、Dockerfile_CodeArts、ORT Dockerfile）、华为 SWR 镜像源                                              |

### 2.3 部署分类

**部署分类（Deployment Classification）：双形态——`LIBRARY_EMBEDDED`（sbom-ort）+ `OFFLINE_CLI_TOOL`（sbom-generator / sbom-tracer）。**

判定依据：

- **sbom-ort（LIBRARY_EMBEDDED）**：以 JAR 库交付，本身无独立进程。sbom-server 通过 Maven 依赖将 `model / analyzer / reporter` 加载进服务端 JVM，ORT analyzer 在服务进程内被直接调用（[AbstractBaseAnalyzer.java:196-221](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/src/main/java/org/opensourceway/sbom/analyzer/AbstractBaseAnalyzer.java#L196-L221)）。其威胁**随宿主（sbom-server）的暴露面与权限域评估**——分析触发点前置条件为 `None`，影响上限按"服务端主机沦陷"计。
- **sbom-generator / sbom-tracer（OFFLINE_CLI_TOOL）**：命令行进程在 CI 作业内一次性运行，仓库中无 HTTP/gRPC server 监听代码；但其**输入来自外部不可信制品**（OBS 下载物、被扫归档、git 项目），因此"制品内容触发的威胁"不受离线部署的前置条件降级约束（详见 §10 分析假设）。

### 2.4 组件清单（Component Exposure Table）

组件 ID 遵循确定性命名规则，锚定真实代码工件，后续增量分析复用同一 ID。

| 组件 ID               | 类型            | 锚点（代码工件）                                                                                                                                                                                                                                                      | 监听地址            | 认证屏障                                 | 外部可达性                               | 最小前置条件（Min Prerequisite）  | 派生 Tier |
| --------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ---------------------------------------- | ---------------------------------------- | --------------------------------- | --------- |
| `Operator`            | 外部参与者      | CI 流水线触发者 / 安全工程师                                                                                                                                                                                                                                          | —                   | —                                        | —                                        | —                                 | —         |
| `SyftCLI`             | 进程            | [cmd/syft/main.go](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/cmd/syft/main.go)、[syft/source/extractor.go](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/syft/source/extractor.go)                                      | 无监听              | 无                                       | **按设计处理不可信制品**                 | None（制品内容触发）              | T1        |
| `SbomRunner`          | 进程            | [sbom_runner/run.sh](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/run.sh)、sbom-gen-upload.py、download_file_from_obs.py、sbomAnalyzeLog.py                                                                                         | 无监听              | 无                                       | **按设计处理不可信制品**                 | None（制品内容触发）              | T1        |
| `OrtCLI`              | 进程            | [cli/src/main/kotlin/OrtMain.kt](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/cli/src/main/kotlin/OrtMain.kt)                                                                                                                                         | 无监听              | 无                                       | **按设计处理不可信项目**（离线运行形态） | None（制品内容触发）              | T1        |
| `OrtJarArtifacts`     | 数据制品（T11） | [sbom-ort/build.gradle.kts:364-393](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/build.gradle.kts#L364-L393)（maven-publish，`org.ossreviewtoolkit:model/analyzer/reporter`）                                                                         | —                   | 发布无签名、消费无校验                   | **经 Maven 仓库分发至 sbom-server**      | Internal Network / 制品仓库写权限 | T2        |
| `SbomServerRuntime`   | 进程（T12）     | [analyzer/pom.xml:64-73](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/pom.xml#L64-L73)、[AbstractBaseAnalyzer.java:187-228](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/src/main/java/org/opensourceway/sbom/analyzer/AbstractBaseAnalyzer.java#L187-L228) | sbom-server（宿主） | 宿主自身认证体系之外无屏障               | **进程内执行不可信项目解析**             | None（提交项目触发）              | T1        |
| `TempExtractionDir`   | 数据存储        | extractor.go `ioutil.TempDir("syft-extract-...")`                                                                                                                                                                                                                     | —                   | 目录权限（后被放宽为 755）               | 本地进程                                 | Local Process Access              | T2        |
| `SbomOutputFiles`     | 数据存储        | sbom-gen-upload.py `sbom_spdx.json`；仓库根 `*.json`                                                                                                                                                                                                                  | —                   | 文件系统权限                             | 本地进程                                 | Local Process Access              | T2        |
| `ObsService`          | 外部服务        | download_file_from_obs.py（esdk-obs-python 客户端）                                                                                                                                                                                                                   | 远端                | AK/SK                                    | 由本系统出站访问                         | Privileged User（持有 AK/SK）     | T2        |
| `SbomService`         | 外部服务        | sbom-gen-upload.py `publishSbomFile` / `querySbomPublishResult`                                                                                                                                                                                                       | 远端                | HMAC(accountid+timestamp) / Bearer token | 由本系统出站访问                         | Internal Network（可截获签名）    | T2        |
| `CodeHostingPlatform` | 外部服务        | sbomAnalyzeLog.py tag API；Dockerfile_CodeArts `git clone git@gitcode.com`                                                                                                                                                                                            | 远端                | SSH key / 匿名 API                       | 由本系统出站访问                         | Host/OS Access（构建机凭据）      | T3        |
| `PackageRegistries`   | 外部服务        | extractor.go `pip3 install`；Dockerfile `pip/apk/go mod`                                                                                                                                                                                                              | 远端                | 匿名/凭据                                | 由本系统出站访问                         | Host/OS Access                    | T3        |
| `AdvisorServices`     | 外部服务        | sbom-ort/clients/（oss-index、osv、nexus-iq、scanoss）                                                                                                                                                                                                                | 远端                | API token                                | 由本系统出站访问                         | Host/OS Access                    | T3        |

> **暴露表是前置条件的唯一事实来源**：每条威胁/发现的前置条件不得低于其所属组件的上表下限。
>
> 注：sbom-tracer 与 sbom-generator 同属离线 SBOM 生成工具，威胁模式与 SyftCLI/SbomRunner 同构（处理不可信制品、一次性运行），其风险由 T01/T02 的分析结论按同类覆盖，不单独枚举。

### 2.5 信任边界

| 边界 ID            | 包含                                                                                             | 判定依据                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `BuildHost`        | SyftCLI、SbomRunner、OrtCLI、TempExtractionDir、SbomOutputFiles                                  | 单一构建容器/CI 作业内，同进程域（离线工具运行环境）                                       |
| `SbomServer`       | SbomServerRuntime、OrtJarArtifacts（加载后）                                                     | sbom-server JVM 进程域：JAR 经 Maven 仓库跨边界载入后即获得宿主全部权限，无进程/权限隔离层 |
| `ExternalServices` | ObsService、SbomService、CodeHostingPlatform、PackageRegistries、AdvisorServices、Maven 制品仓库 | 跨网络访问的外部系统                                                                       |

### 2.6 关键场景（前 3 个场景含时序图）

#### 场景 1：CI 流水线从 OBS 拉取制品并生成/发布 SBOM

```mermaid
sequenceDiagram
    autonumber
    participant OP as Operator(CI)
    participant SR as SbomRunner(run.sh)
    participant OBS as ObsService
    participant TMP as TempExtractionDir
    participant SY as SyftCLI
    participant SVC as SbomService
    OP->>SR: run.sh AK SK obs_endpoint bucket path sbom_url account_id secret_key
    SR->>OBS: download_file_from_obs.py --ak/--sk 列举并下载目录
    OBS-->>TMP: 制品包 + meta.json 落地 temp/
    SR->>SY: syft . -o spdx-json=sbom_spdx.json
    SY->>TMP: auto-extract 解压 zip/tar.gz/run/whl
    TMP-->>SY: 解压内容（含 requirements.txt）
    SY->>SR: SPDX JSON 写入 SbomOutputFiles
    SR->>SVC: POST publishSbomFile（HMAC 签名）
    SVC-->>SR: taskId / success
```

#### 场景 2：SyftCLI auto-extract 自动解压被扫制品

```mermaid
sequenceDiagram
    autonumber
    participant SY as SyftCLI
    participant TMP as TempExtractionDir
    participant SH as unzip/tar/被扫run文件
    participant PY as python3 venv
    SY->>TMP: ioutil.TempDir("syft-extract-<文件名>-")
    SY->>SH: unzip/tar -zxf 解压
    SY->>SH: chmod 0755 后 exec <制品.run> --extract=... --noexec
    SH-->>TMP: 解压内容（攻击者可控）
    SY->>SY: 合并 requirements.txt
    SY->>PY: python3 -m venv && pip3 install -r requirements.txt
    PY-->>TMP: pip3 freeze 回写 requirements.txt
```

#### 场景 3：ORT 依赖解析与漏洞咨询

```mermaid
sequenceDiagram
    autonumber
    participant OP as Operator
    participant ORT as OrtCLI
    participant REG as PackageRegistries
    participant ADV as AdvisorServices
    participant OUT as SbomOutputFiles
    OP->>ORT: ort analyze / scan / evaluate
    ORT->>REG: 包管理器解析并下载依赖
    REG-->>ORT: 依赖制品（含构建脚本）
    ORT->>ADV: 上传依赖清单查询漏洞
    ADV-->>ORT: 漏洞咨询结果（未签名）
    ORT->>OUT: 写入 evaluator/analyzer 结果
```

#### 场景 4：sbom-server 进程内消费 sbom-ort JAR 执行依赖分析

```mermaid
sequenceDiagram
    autonumber
    participant OP as Operator(提交项目)
    participant SVC as SbomServerRuntime
    participant MAV as Maven制品仓库
    participant PM as 包管理器(npm/pip/go...)
    participant WS as 工作区(不可信项目)
    OP->>SVC: 提交项目分析请求
    SVC->>MAV: 解析 org.ossreviewtoolkit:model/analyzer/reporter:1.0.0
    MAV-->>SVC: JAR 载入 JVM 类路径（无签名/校验和验证）
    SVC->>WS: Analyzer.findManagedFiles + analyze
    SVC->>PM: 调用包管理器解析依赖定义文件
    PM-->>WS: 执行项目内脚本（scripts/setup.py）
    SVC->>SVC: OrtResult → SPDX 输出（宿主权限域内）
```

### 2.7 安全基础设施清单

| 类别           | 现状                                                                                            | 结论                           |
| -------------- | ----------------------------------------------------------------------------------------------- | ------------------------------ |
| JAR 制品完整性 | sbom-ort 发布无 signing 配置；消费方固定 1.0.0 引入、无校验和/依赖校验                          | 缺失，见 FIND-13/FIND-14       |
| 进程隔离       | sbom-server JVM 内直接运行 ORT analyzer 解析不可信项目，与服务端凭据共享权限域                  | 缺失，见 FIND-03/FIND-16       |
| 密钥管理       | 无 Vault/KMS；凭据经 CLI 参数与环境变量传递                                                     | 缺失，见 FIND-04               |
| 传输加密       | requests 默认验证 TLS；但存在默认 `http` scheme 代码路径与未强制 https 的 URL                   | 部分缺失，见 FIND-09           |
| 完整性         | go sumdb 被禁用（GONOSUMDB=*）；gradle wrapper sha256 校验被删除；SBOM 未签名；OBS 制品无校验和 | 缺失，见 FIND-07/08/10         |
| 认证           | SbomService：HMAC(accountid+timestamp)（无 nonce）；query：Bearer token；OBS：AK/SK             | 弱化，见 FIND-05               |
| 审计日志       | 仅本地 stdout 打印，无防篡改审计                                                                | 缺失，见 FIND-17               |
| 容器安全       | 无 USER 指令（root 运行）；基础镜像 EOL（golang:1.18.2-alpine3.14）                             | 缺失，见 FIND-19               |
| 秘密扫描       | Syft secrets cataloger 存在，`reveal-values` 默认 false                                         | 平台默认安全（控制项，非缺口） |
| 注册表 TLS     | `insecure-skip-tls-verify`/`insecure-use-http` 默认 false                                       | 平台默认安全（控制项）         |

---

## 3. 威胁模型 DFD

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryColor': '#ffffff', 'lineColor': '#666666' }}}%%
flowchart LR
    classDef process fill:#6baed6,stroke:#2171b5
    classDef external fill:#fdae61,stroke:#d94701
    classDef datastore fill:#74c476,stroke:#238b45

    subgraph BuildHost["构建宿主 / CI 容器（离线工具）"]
        SY["SyftCLI"]:::process
        SR["SbomRunner"]:::process
        ORT["OrtCLI"]:::process
        TMP[("TempExtractionDir")]:::datastore
        OUT[("SbomOutputFiles")]:::datastore
    end

    subgraph SbomServer["sbom-server JVM（LIBRARY_EMBEDDED）"]
        JAR[("OrtJarArtifacts")]:::datastore
        SVCS["SbomServerRuntime"]:::process
    end

    subgraph ExternalServices["外部服务"]
        OP(["Operator"]):::external
        OBS(["ObsService"]):::external
        SVC(["SbomService"]):::external
        GIT(["CodeHostingPlatform"]):::external
        REG(["PackageRegistries"]):::external
        ADV(["AdvisorServices"]):::external
        MAV(["Maven制品仓库"]):::external
    end

    OP <-->|"DF01 AK/SK 与任务参数"| SR
    OP <-->|"DF10 直接 CLI 调用"| SY
    SR <-->|"DF02 OBS 下载(AK/SK)"| OBS
    OBS -->|"DF04 制品+meta.json 落地"| TMP
    SR <-->|"DF03 调度 syft 扫描"| SY
    SY <-->|"DF05 解压/读取制品"| TMP
    SY <-->|"DF06 pip3 install 依赖"| REG
    SY -->|"DF15 SPDX JSON 输出"| OUT
    SR <-->|"DF07 读取 SBOM 文件"| OUT
    SR <-->|"DF08 publishSbomFile(HMAC)"| SVC
    SR <-->|"DF09 git clone / tag API"| GIT
    ORT <-->|"DF11 依赖下载"| REG
    ORT <-->|"DF12 漏洞咨询"| ADV
    ORT <-->|"DF13 分析结果写入"| OUT
    JAR -->|"DF16 发布 JAR（无签名）"| MAV
    MAV -->|"DF17 下载 JAR 载入类路径"| SVCS
    OP -->|"DF18 提交不可信项目"| SVCS
    SVCS <-->|"DF19 调用包管理器解析"| REG
```

### 3.1 数据流清单

| 流 ID | 源 → 目标                                | 数据                                                                     | 协议/通道                       | 是否跨信任边界 |
| ----- | ---------------------------------------- | ------------------------------------------------------------------------ | ------------------------------- | -------------- |
| DF01  | Operator <--> SbomRunner                 | AK/SK、obs_endpoint、bucket、sbom_url、account_id、secret_key            | CLI 位置参数/环境变量           | 是             |
| DF02  | SbomRunner <--> ObsService               | AK/SK 签名请求、制品对象                                                 | HTTPS（endpoint 可被传为 http） | 是             |
| DF03  | SbomRunner <--> SyftCLI                  | 扫描指令与输出路径                                                       | subprocess                      | 否             |
| DF04  | ObsService --> TempExtractionDir         | 制品包、meta.json                                                        | 本地文件写入                    | 是             |
| DF05  | SyftCLI <--> TempExtractionDir           | 归档内容、解压命令                                                       | 本地文件 + exec                 | 否             |
| DF06  | SyftCLI <--> PackageRegistries           | requirements.txt 依赖、PyPI 元数据                                       | HTTPS                           | 是             |
| DF07  | SbomRunner <--> SbomOutputFiles          | sbom_spdx.json 读写                                                      | 本地文件                        | 否             |
| DF08  | SbomRunner <--> SbomService              | SBOM 内容、HMAC 签名、taskId                                             | HTTP(S)                         | 是             |
| DF09  | SbomRunner <--> CodeHostingPlatform      | git clone（SSH）、tag API 查询                                           | SSH/HTTPS                       | 是             |
| DF10  | Operator <--> SyftCLI                    | CLI 参数（制品路径、auto-extract）                                       | CLI                             | 否             |
| DF11  | OrtCLI <--> PackageRegistries            | 依赖包下载                                                               | HTTPS                           | 是             |
| DF12  | OrtCLI <--> AdvisorServices              | 依赖清单上传、漏洞结果                                                   | HTTPS                           | 是             |
| DF13  | OrtCLI <--> SbomOutputFiles              | analyzer/evaluator 结果                                                  | 本地文件                        | 否             |
| DF15  | SyftCLI --> SbomOutputFiles              | SPDX JSON                                                                | 本地文件                        | 否             |
| DF16  | OrtJarArtifacts --> Maven 制品仓库       | `org.ossreviewtoolkit:model/analyzer/reporter` JAR（含 sources/javadoc） | Gradle maven-publish            | 是             |
| DF17  | Maven 制品仓库 --> SbomServerRuntime     | JAR 制品（载入 JVM 类路径）                                              | Maven 依赖解析（HTTPS）         | 是             |
| DF18  | Operator --> SbomServerRuntime           | 不可信项目（分析请求）                                                   | sbom-server API                 | 是             |
| DF19  | SbomServerRuntime <--> PackageRegistries | 包管理器依赖解析与下载（进程内调用）                                     | HTTPS / 本地子进程              | 是             |

---

## 4. STRIDE-A 威胁枚举

**Exploitability Tiers（可利用性分层）：**

- **Tier 1（直接暴露）**：前置条件 `None`——攻击者只需让恶意制品进入正常扫描/发布工作流。
- **Tier 2（条件风险）**：单一前置条件（`Authenticated User` / `Privileged User` / `Internal Network` / `Local Process Access`）。
- **Tier 3（纵深防御）**：`Host/OS Access`、`Admin Credentials`、`{Component} Compromise` 或多条件组合。

### 4.1 Summary（威胁计数汇总）

| 组件                      | S     | T      | R     | I      | D     | E     | A     | 合计   |
| ------------------------- | ----- | ------ | ----- | ------ | ----- | ----- | ----- | ------ |
| SyftCLI (T01)             | 0     | 1      | 1     | 2      | 1     | 0     | 0     | 5      |
| SbomRunner (T02)          | 2     | 0      | 1     | 2      | 1     | 1     | 1     | 8      |
| OrtCLI (T03)              | 1     | 1      | 0     | 1      | 1     | 1     | 0     | 5      |
| TempExtractionDir (T04)   | 0     | 2      | 0     | 1      | 1     | 0     | 0     | 4      |
| SbomOutputFiles (T05)     | 0     | 2      | 0     | 1      | 0     | 0     | 0     | 3      |
| ObsService (T06)          | 1     | 1      | 0     | 1      | 0     | 0     | 0     | 3      |
| SbomService (T07)         | 1     | 1      | 1     | 1      | 0     | 0     | 0     | 4      |
| CodeHostingPlatform (T08) | 1     | 1      | 0     | 0      | 0     | 0     | 0     | 2      |
| PackageRegistries (T09)   | 0     | 2      | 0     | 1      | 0     | 1     | 0     | 4      |
| AdvisorServices (T10)     | 1     | 1      | 0     | 0      | 0     | 0     | 0     | 2      |
| OrtJarArtifacts (T11)     | 1     | 2      | 0     | 1      | 1     | 1     | 0     | 6      |
| SbomServerRuntime (T12)   | 0     | 1      | 0     | 1      | 1     | 1     | 1     | 5      |
| **合计**                  | **8** | **15** | **3** | **12** | **6** | **5** | **2** | **51** |

状态取值：`Open`（未缓解，需对应发现）、`Mitigated`（代码内已有控制）、`Platform`（由外部平台/默认配置兜底）。**本工具不判定"接受风险"**。

---

### 4.2 SyftCLI（T01）

锚点：[syft/source/extractor.go](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/syft/source/extractor.go)、[syft/source/source.go](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/syft/source/source.go)、[cmd/syft/cli/options/packages.go](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/cmd/syft/cli/options/packages.go)

#### Tier 1

| ID     | 类别 | 威胁                                                                                                                                                                                                                                   | 前置条件 | 状态 | 缓解建议                                              |
| ------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---- | ----------------------------------------------------- |
| T01.T2 | T    | **bash -c 命令注入**：`pipInstallCmd := fmt.Sprintf("source %s && pip3 install -r %s && ...")`，`venvPath/requirementsPath` 派生自归档内文件名（zip 成员名攻击者可控），含 shell 元字符即可注入。证据：installDependencies()（已复核） | None     | Open | 使用 `exec.Command` 参数数组替代 `bash -c` 字符串拼接 |
| T01.D1 | D    | **zip 炸弹 / 嵌套解压资源耗尽**：无解压大小/层数/数量上限，zip 炸弹可耗尽 CI 磁盘与 CPU。证据：processWhlPackages()、processTarGzPackages() 递归遍历                                                                                   | None     | Open | 限制解压总大小、嵌套层数、文件数；超限中止            |

#### Tier 2

| ID     | 类别 | 威胁                                                                                                                                                                                                                                                                                                | 前置条件             | 状态 | 缓解建议                                               |
| ------ | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ---- | ------------------------------------------------------ |
| T01.I1 | I    | **恶意归档内符号链接读取宿主文件**：解压内容含指向容器内敏感路径的 symlink，后续 cataloger 跟随链接读取，内容进入 SBOM 输出                                                                                                                                                                         | Local Process Access | Open | 解压时拒绝/跳过 symlink，或校验链接目标在临时目录内    |
| T01.I2 | I    | **anchore 客户端默认 http 明文 BasicAuth**：`prepareBaseURLForClient` 在 URL 无 scheme 时默认补 `http`，`newRequestContext` 注入 BasicAuth。证据：[internal/anchore/client.go:63-69](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/internal/anchore/client.go#L63-L69)、:47-58 | Internal Network     | Open | 默认补 `https`，或拒绝无 scheme URL                    |
| T01.R1 | R    | **扫描行为无防抵赖审计**：谁在何时扫描了哪个制品仅本地 stdout，无结构化审计日志                                                                                                                                                                                                                     | Local Process Access | Open | 输出结构化审计事件（操作者、制品哈希、时间）到远端日志 |

#### Tier 3

| ID     | 类别 | 威胁                                                                            | 前置条件 | 状态 | 缓解建议 |
| ------ | ---- | ------------------------------------------------------------------------------- | -------- | ---- | -------- |
| T01.T3 | T    | N/A — SyftCLI 本体不持久化可篡改状态，输出完整性归入 SbomOutputFiles（T05）分析 | —        | —    | —        |

---

### 4.3 SbomRunner（T02）

锚点：[run.sh](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/run.sh)、[sbom-gen-upload.py](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/sbom-gen-upload.py)、[download_file_from_obs.py](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/download_file_from_obs.py)、[sbomAnalyzeLog.py](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/sbomAnalyzeLog.py)

#### Tier 1

| ID     | 类别 | 威胁                                                                                                                                                                                                                                                                                                                                  | 前置条件                   | 状态 | 缓解建议                                                                    |
| ------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ---- | --------------------------------------------------------------------------- |
| T02.I1 | I    | **构建日志 URL 内嵌凭据泄露进 SBOM**：`parse_download_files_from_log` 从 wget/curl 命令提取 URL 直接作为 `downloadLocation`，未调用 `strip_credentials()`（该函数仅用于 git clone URL）。攻击者在构建日志植入 `wget https://user:token@host/pkg.tar.gz` 即可让凭据随 SBOM 发布。证据：sbomAnalyzeLog.py:118-152 vs :364-375（已复核） | None（攻击者控制构建日志） | Open | 对下载 URL 同样调用 `strip_credentials()`；发布前对 SBOM 全文做凭据模式扫描 |
| T02.A1 | A    | **伪造 meta.json 驱动伪造 SBOM 发布**：OBS 下载的 `meta.json`（type/name）无 schema 校验、无来源签名，直接注入 `PRODUCT_NAME/PRODUCT_TYPE` 环境变量并驱动发布流程，攻击者以桶写权限即可冒名发布他人产品 SBOM（run.sh 已复核：`jq -r '.type'/'.name'` → export）                                                                       | None（桶内制品即攻击面）   | Open | meta.json 增加 HMAC 签名校验；productName 与制品哈希绑定白名单              |

#### Tier 2

| ID     | 类别 | 威胁                                                                                                                                                                          | 前置条件                    | 状态 | 缓解建议                                             |
| ------ | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | ---- | ---------------------------------------------------- |
| T02.S1 | S    | **HMAC 签名可重放**：`sign = HMAC-SHA256(secret, accountid+timestamp)`，无 nonce/请求体绑定，截获后在时间窗内可重放冒充发布者。证据：sbom-gen-upload.py:150-186（已复核）     | Internal Network            | Open | 签名消息纳入请求体哈希与 nonce；服务端拒绝过期时间戳 |
| T02.I2 | I    | **AK/SK 经 CLI 位置参数传递**：run.sh `$1..$8` 与 download_file_from_obs.py `--ak/--sk` 均暴露于 `ps`/`/proc/*/cmdline`、shell history 与 CI 日志。证据：run.sh:1-8（已复核） | Local Process Access        | Open | 改环境变量或凭据文件（0600），由 CI secret 注入      |
| T02.D1 | D    | **OBS 目录全量下载无总量上限**：`listObjects` 全列全下，恶意桶可塞爆 CI 磁盘                                                                                                  | Privileged User（桶写权限） | Open | 限制对象数/总字节；分页 + 配额                       |
| T02.E1 | E    | **凭据环境变量过度传播**：run.sh 将 8 个敏感变量 `export` 给所有子进程（含 jq、python），任一子进程被攻陷即全部泄露                                                           | Local Process Access        | Open | 最小化传递：按需以参数/文件传给单个脚本              |
| T02.R1 | R    | **发布操作无持久审计**：成功/失败仅 echo 到 stdout，无操作者、制品哈希、taskId 的持久审计记录                                                                                 | Local Process Access        | Open | 结构化审计日志 + 远端上报                            |

#### Tier 3

| ID     | 类别 | 威胁                                                                                                                                                   | 前置条件       | 状态 | 缓解建议                     |
| ------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- | ---- | ---------------------------- |
| T02.S2 | S    | **meta.json 字段无校验注入发布参数**：`jq -r '.type'/.name` 结果未校验格式（可含空格/特殊字符污染 PRODUCT_NAME 等），配合宿主/桶写权限可注入发布元数据 | Host/OS Access | Open | 白名单校验 `[A-Za-z0-9._-]+` |

---

### 4.4 OrtCLI（T03）

锚点：[OrtMain.kt](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/cli/src/main/kotlin/OrtMain.kt)、[Dockerfile](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/Dockerfile)、advisor/、clients/

> 注：除 CLI 运行形态外，ORT 的 analyzer/reporter 能力还以 JAR 形式交付给 sbom-server 进程内调用（见 §2.3/§2.6 场景 4），该形态的威胁在 §4.12/§4.13 单独枚举；本节仅覆盖 CLI 形态。

#### Tier 1

| ID     | 类别 | 威胁                                                                                                                                                                             | 前置条件               | 状态 | 缓解建议                                          |
| ------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | ---- | ------------------------------------------------- |
| T03.E1 | E    | **包管理器执行不可信项目脚本**：ORT analyzer 调用 npm/gradle/pip 等解析依赖，项目内 `package.json` scripts、`pom.xml` 插件等可在扫描机执行代码（ORT 固有风险，本分支未额外隔离） | None（攻击者提交项目） | Open | 在一次性沙箱容器内运行 analyzer；禁网或代理白名单 |

#### Tier 2

| ID     | 类别 | 威胁                                                                                                                                                                                                                                                                                                    | 前置条件                     | 状态 | 缓解建议                                                 |
| ------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | ---- | -------------------------------------------------------- |
| T03.T1 | T    | **gradle-wrapper 完整性校验被删除**：ORT Dockerfile 构建期 `sed -i '/distributionSha256Sum=[0-9a-f]{64}/d' gradle/wrapper/gradle-wrapper.properties`，wrapper jar 下载不再校验哈希。证据：[Dockerfile:52-54](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/Dockerfile#L52-L54)（已复核） | Internal Network             | Open | 保留并更新 distributionSha256Sum；或预置校验过的 wrapper |
| T03.I1 | I    | **依赖清单上传第三方 advisor 泄露内部软件组成**：OSS Index/Nexus IQ/ScanOSS 上传包含内部组件坐标的清单                                                                                                                                                                                                  | Internal Network（出站可达） | Open | 私有组件脱敏/排除后上传；仅上传哈希而非完整坐标          |
| T03.S1 | S    | **advisor 凭据被本地进程冒用**：ORT 以配置文件/环境变量持有 OSS Index / Nexus IQ token，本地任意可读进程可冒充本系统调用 advisor                                                                                                                                                                        | Local Process Access         | Open | 凭据文件 0600 + 运行时注入；调用方最小化                 |
| T03.D1 | D    | **analyzer 资源耗尽**：提交超大/深嵌套项目触发包管理器全量解析与依赖下载，占满构建机磁盘与内存                                                                                                                                                                                                          | None（攻击者提交项目）       | Open | 限制项目大小与解析超时；沙箱资源配额                     |

#### Tier 3

| ID     | 类别 | 威胁                                                               | 前置条件 | 状态 | 缓解建议 |
| ------ | ---- | ------------------------------------------------------------------ | -------- | ---- | -------- |
| T03.T2 | T    | N/A — ORT 分析结果写入 SbomOutputFiles（T05），完整性归入 T05 分析 | —        | —    | —        |

---

### 4.5 TempExtractionDir（T04）

锚点：[syft/source/extractor.go](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/syft/source/extractor.go)（`ioutil.TempDir("syft-extract-...")`）

#### Tier 2

| ID     | 类别 | 威胁                                                                                                                                                                                                                               | 前置条件             | 状态 | 缓解建议                                        |
| ------ | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ---- | ----------------------------------------------- |
| T04.T1 | T    | **临时目录命名可预测 + 权限放宽，本地进程可篡改解压产物**：`ioutil.TempDir("syft-extract-<原名>-")` 以被扫文件名派生前缀，解压目录放宽为 0755（`addWritablePermissions`），同机低权进程可在扫描读取前替换/注入文件，污染 SBOM 结果 | Local Process Access | Open | 目录 0700；不以外部文件名作前缀；解压后校验归属 |
| T04.T2 | T    | **解压与扫描间隙的 TOCTOU 篡改**：解压完成到 cataloger 读取之间无完整性快照，本地进程可在间隙替换文件内容                                                                                                                          | Local Process Access | Open | 解压后立即计算文件哈希清单，扫描前复核          |
| T04.I1 | I    | **临时目录残留敏感制品未清理**：扫描失败/中断时临时目录残留，容器层与后续作业可读取全部解压内容                                                                                                                                    | Local Process Access | Open | defer 清理 + 异常退出钩子；每作业独立 tmpfs     |
| T04.D1 | D    | **解压产物占满磁盘影响同机作业**：超大归档解压无配额控制，临时目录与工作目录共享磁盘                                                                                                                                               | Local Process Access | Open | 独立 tmpfs + 大小配额（与 FIND-12 联动）        |

#### Tier 3

| ID     | 类别 | 威胁                                                            | 前置条件 | 状态 | 缓解建议 |
| ------ | ---- | --------------------------------------------------------------- | -------- | ---- | -------- |
| T04.E1 | E    | N/A — 临时目录无代码执行能力，执行类威胁归入 SyftCLI（T01）分析 | —        | —    | —        |

---

### 4.6 SbomOutputFiles（T05）

锚点：[sbom-gen-upload.py](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/sbom-gen-upload.py)（`sbom_spdx.json`）

#### Tier 2

| ID     | 类别 | 威胁                                                                                                              | 前置条件             | 状态 | 缓解建议                                       |
| ------ | ---- | ----------------------------------------------------------------------------------------------------------------- | -------------------- | ---- | ---------------------------------------------- |
| T05.T1 | T    | **SBOM 文件发布前被篡改**：sbom_spdx.json 从生成到发布无完整性校验，本地进程可注入/删改组件清单（如隐藏恶意组件） | Local Process Access | Open | 生成后立即分离签名，发布前验签                 |
| T05.T2 | T    | **固定路径覆盖写 + 符号链接攻击**：输出文件名固定可预测，本地攻击者预置 symlink 指向敏感文件被覆写                | Local Process Access | Open | O_EXCL 创建；输出目录 0700                     |
| T05.I1 | I    | **SBOM 携带敏感信息对外发布**：downloadLocation 内嵌凭据（FIND-01）、内部组件坐标、私有仓 URL 随 SBOM 发布扩散    | Local Process Access | Open | 发布前内容审查（凭据模式、内网域名、私有坐标） |

#### Tier 3

| ID     | 类别 | 威胁                                                          | 前置条件 | 状态 | 缓解建议 |
| ------ | ---- | ------------------------------------------------------------- | -------- | ---- | -------- |
| T05.E1 | E    | N/A — 数据存储无执行能力，执行类威胁归入调用方（T01/T02）分析 | —        | —    | —        |

---

### 4.7 ObsService（T06）

锚点：[download_file_from_obs.py](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/download_file_from_obs.py)

#### Tier 2

| ID     | 类别 | 威胁                                                                                                          | 前置条件                        | 状态 | 缓解建议                                                 |
| ------ | ---- | ------------------------------------------------------------------------------------------------------------- | ------------------------------- | ---- | -------------------------------------------------------- |
| T06.S1 | S    | **AK/SK 泄露后冒充合法扫描客户端**：AK/SK 一旦经 cmdline/日志泄露（FIND-04），攻击者可冒充本系统读写桶        | Privileged User（持有 AK/SK）   | Open | AK/SK 定期轮换 + 最小权限子账号 + 异常访问告警           |
| T06.T1 | T    | **桶内制品投毒**：对桶有写权限的账号替换制品或 meta.json，驱动本系统生成/发布被操纵的 SBOM                    | Privileged User（桶写权限）     | Open | 制品 manifest 校验和签名；meta.json HMAC（关联 FIND-08） |
| T06.I1 | I    | **桶策略过宽导致制品与 SBOM 被未授权读取**：OBS 对象 ACL/桶策略未收敛时，制品内容与内部结构信息可被第三方读取 | Privileged User（桶读权限过宽） | Open | 桶私有 ACL + 临时凭证（STS）下载                         |

#### Tier 3

| ID     | 类别 | 威胁                                                                | 前置条件 | 状态 | 缓解建议 |
| ------ | ---- | ------------------------------------------------------------------- | -------- | ---- | -------- |
| T06.E1 | E    | N/A — 外部对象存储无本系统代码执行面，相关执行威胁归入 T01/T09 分析 | —        | —    | —        |

---

### 4.8 SbomService（T07）

锚点：[sbom-gen-upload.py](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/sbom-gen-upload.py)（`publishSbomFile` / `querySbomPublishResult`）

#### Tier 2

| ID     | 类别 | 威胁                                                                                                                        | 前置条件         | 状态 | 缓解建议                                        |
| ------ | ---- | --------------------------------------------------------------------------------------------------------------------------- | ---------------- | ---- | ----------------------------------------------- |
| T07.S1 | S    | **HMAC 时间窗重放冒充发布者**：签名未绑定请求体与 nonce，内网截获即可在时间窗内重放                                         | Internal Network | Open | 签名绑定 body 哈希 + nonce（关联 FIND-05）      |
| T07.T1 | T    | **SBOM 传输中被篡改**：发布请求可经 http（scheme 未强制 https）且无应用层签名，中间人可替换 SBOM 内容                       | Internal Network | Open | 强制 https + 应用层签名（关联 FIND-08/FIND-09） |
| T07.R1 | R    | **发布行为服务端不可归责**：accountid+timestamp 可共享/复用，发布者身份不可靠，抵赖成本低                                   | Internal Network | Open | 签名绑定身份与 body；服务端留存防篡改审计       |
| T07.I1 | I    | **查询接口越权读取他人 SBOM**：querySbomPublishResult 按 taskId 查询无资源级授权时，内网用户可枚举 taskId 读取其他产品 SBOM | Internal Network | Open | taskId 与 account 绑定 + 资源级 ACL             |

#### Tier 3

| ID     | 类别 | 威胁                                                       | 前置条件 | 状态 | 缓解建议 |
| ------ | ---- | ---------------------------------------------------------- | -------- | ---- | -------- |
| T07.D1 | D    | N/A — 发布为单次出站请求，服务端可用性归服务方自身威胁模型 | —        | —    | —        |

---

### 4.9 CodeHostingPlatform（T08）

锚点：Dockerfile_CodeArts（`git clone git@gitcode.com`）、[sbomAnalyzeLog.py](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/sbomAnalyzeLog.py)（tag API）

#### Tier 3

| ID     | 类别 | 威胁                                                                                                                    | 前置条件                       | 状态 | 缓解建议                                  |
| ------ | ---- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ---- | ----------------------------------------- |
| T08.S1 | S    | **SSH 主机密钥不校验导致平台被冒充**：`StrictHostKeyChecking=no` 使 MITM 可冒充 gitcode.com，窃取部署私钥或篡改克隆内容 | Host/OS Access（构建网络位置） | Open | 预置 known_hosts + 强校验（关联 FIND-06） |
| T08.T1 | T    | **克隆内容被篡改（无 commit 锚定）**：构建按分支/HEAD 克隆、未固定 commit 哈希，篡改与回滚不可见                        | Host/OS Access                 | Open | 固定 commit SHA 并将哈希写入构建日志      |

---

### 4.10 PackageRegistries（T09）

锚点：extractor.go `pip3 install`、Dockerfile（`pip/apk/go mod`）

#### Tier 3

| ID     | 类别 | 威胁                                                                                                        | 前置条件       | 状态 | 缓解建议                             |
| ------ | ---- | ----------------------------------------------------------------------------------------------------------- | -------------- | ---- | ------------------------------------ |
| T09.T1 | T    | **依赖包投毒/typosquatting**：pip/go/apk 直接拉取上游注册表，requirements.txt 未 pin 哈希，无企业代理白名单 | Host/OS Access | Open | 内部代理仓 + lockfile + 哈希 pin     |
| T09.T2 | T    | **go sumdb 校验被禁用后模块任意替换**：`GONOSUMDB=*` 使 go 模块下载不做 checksum 校验（FIND-07）            | Host/OS Access | Open | 移除 GONOSUMDB 配置，恢复 sumdb 校验 |
| T09.I1 | I    | **内部组件坐标泄露至公共注册表**：go mod/pip 解析时将私有模块名/内部 URL 发往公共注册表（依赖混淆探测面）   | Host/OS Access | Open | GOPRIVATE 仅限私有域；内部代理仓优先 |
| T09.E1 | E    | **恶意包安装脚本执行**：pip `setup.py` / npm `postinstall` 在构建机执行任意代码                             | Host/OS Access | Open | 隔离构建环境；依赖白名单与准入扫描   |

---

### 4.11 AdvisorServices（T10）

锚点：sbom-ort/clients/（oss-index、osv、nexus-iq、scanoss）

#### Tier 3

| ID     | 类别 | 威胁                                                                                         | 前置条件       | 状态 | 缓解建议                                          |
| ------ | ---- | -------------------------------------------------------------------------------------------- | -------------- | ---- | ------------------------------------------------- |
| T10.S1 | S    | **advisor API token 泄露冒用**：OSS Index / Nexus IQ token 泄露后攻击者可冒充查询、耗尽配额  | Host/OS Access | Open | token 最小权限 + 轮换 + 配额告警                  |
| T10.T1 | T    | **漏洞咨询结果被篡改导致漏报**：advisor 响应无签名，中间人可剔除漏洞记录使恶意版本"通过"评估 | Host/OS Access | Open | 强制 https + 响应与请求一致性校验（关联 FIND-18） |

---

### 4.12 OrtJarArtifacts（T11）

锚点：[sbom-ort/build.gradle.kts:364-393](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/build.gradle.kts#L364-L393)（maven-publish，已复核：仅配置 publication 未启用 `signing`）、[pom.xml:309-323](file:///d:/CODE/JAVACODE/openlibing-sbom/pom.xml#L309-L323)（sbom-server 依赖管理，固定 1.0.0，已复核）

#### Tier 2

| ID     | 类别 | 威胁                                                                                                                                                                                                                                                                                                      | 前置条件                          | 状态 | 缓解建议                                                                                 |
| ------ | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ---- | ---------------------------------------------------------------------------------------- |
| T11.T1 | T    | **发布 JAR 无签名、消费侧无校验和**：`maven-publish` 仅配置 publication 未启用 `signing`；sbom-server 侧以固定版本 1.0.0 引入且无 `dependencyVerifications`/校验和约束。制品仓库任一写入路径被篡改，恶意 JAR 即载入 sbom-server 类路径并获得宿主代码执行。证据：build.gradle.kts:364-393、pom.xml:309-323 | Internal Network / 制品仓库写权限 | Open | Gradle `signing` 插件签名发布；消费侧启用 Maven dependency verification 锁定校验和与签名 |
| T11.S1 | S    | **发布身份未做密码学绑定**：publish 凭据仅凭仓库认证，同坐标更高/同版本可被恶意发布者覆盖（无版本不可变保护），下游按坐标拉取即中招                                                                                                                                                                       | 制品仓库发布权限                  | Open | 发布身份绑定签名密钥；仓库启用版本不可变（immutable releases）                           |
| T11.I1 | I    | **sourcesJar/dokkaJavadocJar 随包发布泄露内部实现**：源码与文档 JAR 中包含内部适配代码、注释与路径信息，可被用于侦察 sbom-server 集成方式                                                                                                                                                                 | 制品仓库读权限                    | Open | 评估内部模块源码 JAR 的发布必要性；敏感注释清理                                          |
| T11.D1 | D    | **发布链单点导致 sbom-server 交付中断**：JAR 是 sbom-server 分析能力的唯一来源，发布失败/坏版本（无 staging 验证）将直接阻断服务端 SBOM 生成                                                                                                                                                              | 制品仓库可用性                    | Open | 发布前 staging 验证 + 消费侧锁定多版本回退                                               |
| T11.E1 | E    | **恶意 JAR 载入即执行（静态初始化）**：T11.T1/S1 的后果链——被篡改 JAR 的 static initializer / SPI 注册在类加载时即执行，无需任何调用触发                                                                                                                                                                  | Internal Network / 制品仓库写权限 | Open | 同 T11.T1/S1；并对 sbom-server 运行账号做最小权限收敛                                    |

#### Tier 3

| ID     | 类别 | 威胁                                                                                                                                                                               | 前置条件       | 状态 | 缓解建议                                                                          |
| ------ | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---- | --------------------------------------------------------------------------------- |
| T11.T2 | T    | **传递依赖未审计进入 sbom-server 类路径**：model/analyzer/reporter 自 mavenCentral 拉取大量 ORT 传递依赖，无 SBOM/漏洞门禁，恶意或含漏洞的传递依赖随 JAR 进入服务端（关联 T09.T1） | Host/OS Access | Open | 对发布产物生成 SBOM 并做依赖准入扫描；消费侧 dependency verification 覆盖全依赖树 |

---

### 4.13 SbomServerRuntime（T12）

锚点：[analyzer/pom.xml:64-73](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/pom.xml#L64-L73)、[AbstractBaseAnalyzer.java:187-228](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/src/main/java/org/opensourceway/sbom/analyzer/AbstractBaseAnalyzer.java#L187-L228)（`ortAnalyze()` 进程内调用，已复核）

#### Tier 1

| ID     | 类别 | 威胁                                                                                                                                                                                                                                                                                    | 前置条件             | 状态 | 缓解建议                                                                                                          |
| ------ | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ---- | ----------------------------------------------------------------------------------------------------------------- |
| T12.E1 | E    | **进程内执行不可信项目构建脚本**：`ortAnalyze()` 在 sbom-server JVM 内调用 ORT analyzer，包管理器黑名单仅屏蔽 Gradle/Sbt/Tracer/Unmanaged（AbstractBaseAnalyzer.java:75-76，已复核），npm/pip/go 等放行——项目内 `package.json` scripts、`setup.py`、构建插件在 **sbom-server 主机**执行 | None（提交项目触发） | Open | 包管理器改显式白名单；analyzer 迁移至一次性沙箱容器（独立镜像、只读挂载、禁凭据注入），sbom-server 仅消费结果文件 |
| T12.A1 | A    | **以"合法分析职能"为跳板攻陷 sbom-server**：攻击者提交特制项目，借进程内分析获得服务端代码执行，进而访问数据库、SBOM 数据与其他租户任务（业务逻辑滥用，非漏洞注入）                                                                                                                     | None（提交项目触发） | Open | 同 T12.E1；分析进程使用独立 service account，与 web 层权限域隔离                                                  |
| T12.D1 | D    | **恶意项目耗尽服务端资源**：超大/深嵌套/病态依赖图项目触发包管理器全量解析，与在线服务共享 JVM 内存与磁盘，影响 sbom-server 对其他请求的可用性                                                                                                                                          | None（提交项目触发） | Open | 分析任务资源配额（内存/磁盘/超时）；大任务异步队列限流                                                            |

#### Tier 2

| ID     | 类别 | 威胁                                                                                                                                   | 前置条件                            | 状态 | 缓解建议                                                           |
| ------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ---- | ------------------------------------------------------------------ |
| T12.I1 | I    | **进程内代码执行直达服务端凭据**：分析代码运行于宿主 JVM，环境变量、配置中心、数据库连接串等对注入代码全部可读（无隔离层的后果放大项） | Local Process Access（承接 T12.E1） | Open | 进程级隔离（容器/独立 JVM）；凭据经短期 token 注入而非常驻环境变量 |
| T12.T1 | T    | **分析结果与数据库记录被篡改**：注入代码可直接改写 OrtResult→SPDX 的输出与后续落库数据，掩盖恶意组件或植入虚假依赖记录                 | Local Process Access（承接 T12.E1） | Open | 分析输出与落库分离；结果文件签名后由独立写库服务校验写入           |

#### Tier 3

| ID     | 类别 | 威胁                                                                    | 前置条件 | 状态 | 缓解建议 |
| ------ | ---- | ----------------------------------------------------------------------- | -------- | ---- | -------- |
| T12.R1 | R    | N/A — 服务端请求审计由 sbom-server 自身日志体系承载，超出本仓库代码范围 | —        | —    | —        |

---

## 5. 安全发现清单

> 每条发现给出 CVSS 4.0 Base（CVSS-B）评分与向量。向量按"攻击者让恶意制品进入正常工作流"的 CI 场景评估；严重度分级：Critical ≥ 9.0、High ≥ 6.0（此处按本报告内部标尺，Critical 9.0+，High 6.0–8.9，Medium 3.1–5.9，Low < 3.1）。

### 5.1 Tier 1 — 直接暴露（前置条件：None）

| ID      | 标题                                                                                 | 关联威胁       | CVSS 4.0          | 向量                                                              | CWE                                                        | OWASP Top 10:2025               | 证据                                                                                                                                                                     |
| ------- | ------------------------------------------------------------------------------------ | -------------- | ----------------- | ----------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FIND-01 | 构建日志 wget/curl URL 内嵌凭据未剥离即写入 SBOM `downloadLocation` 并发布           | T02.I1, T05.I1 | **8.7 High**      | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | [CWE-522](https://cwe.mitre.org/data/definitions/522.html) | A07:2025 – 认证与授权失效       | [sbomAnalyzeLog.py:118-152](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/sbomAnalyzeLog.py#L118-L152)                                  |
| FIND-02 | `bash -c` 字符串拼接 venv 路径与 requirements 路径，命令注入                         | T01.T2         | **9.3 Critical**  | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:N/SA:N` | [CWE-78](https://cwe.mitre.org/data/definitions/78.html)   | A03:2025 – 注入                 | extractor.go `installDependencies()`                                                                                                                                     |
| FIND-03 | sbom-server JVM 内运行 ORT analyzer 解析不可信项目，项目内构建脚本获得服务端代码执行 | T12.E1, T12.A1 | **10.0 Critical** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H` | [CWE-94](https://cwe.mitre.org/data/definitions/94.html)   | A08:2025 – 软件与数据完整性失效 | [AbstractBaseAnalyzer.java:187-228](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/src/main/java/org/opensourceway/sbom/analyzer/AbstractBaseAnalyzer.java#L187-L228) |

### 5.2 Tier 2 — 条件风险（单一前置条件）

| ID      | 标题                                                                                                       | 关联威胁                         | CVSS 4.0       | 向量                                                              | CWE                                                          | OWASP Top 10:2025               | 证据                                                                                                                                                                                                        |
| ------- | ---------------------------------------------------------------------------------------------------------- | -------------------------------- | -------------- | ----------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FIND-04 | OBS AK/SK 经 CLI 位置参数与环境变量传递，`ps`/日志可见并过度传播                                           | T02.I2, T02.E1, T06.S1           | **6.9 Medium** | `CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | [CWE-214](https://cwe.mitre.org/data/definitions/214.html)   | A07:2025 – 认证与授权失效       | [run.sh:1-8](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/run.sh#L1-L8)                                                                                                   |
| FIND-05 | 发布签名 `HMAC(secret, accountid+timestamp)` 无 nonce、未绑定请求体，可重放                                | T02.S1, T07.S1                   | **6.3 Medium** | `CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N` | [CWE-294](https://cwe.mitre.org/data/definitions/294.html)   | A07:2025 – 认证与授权失效       | [sbom-gen-upload.py:150-186](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/sbom_runner/sbom-gen-upload.py#L150-L186)                                                                   |
| FIND-06 | SSH 私钥 COPY 进镜像层 + `StrictHostKeyChecking=no` + 克隆未固定 commit                                    | T08.S1, T08.T1, T06.S1           | **6.9 Medium** | `CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N` | [CWE-798](https://cwe.mitre.org/data/definitions/798.html)   | A05:2025 – 安全配置错误         | Dockerfile_CodeArts                                                                                                                                                                                         |
| FIND-07 | `go env -w GONOSUMDB=*` 禁用 sumdb 校验，模块可被任意替换                                                  | T09.T2                           | **7.1 High**   | `CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N` | [CWE-494](https://cwe.mitre.org/data/definitions/494.html)   | A08:2025 – 软件与数据完整性失效 | sbom-generator Dockerfile                                                                                                                                                                                   |
| FIND-08 | SBOM 全程无签名；OBS `meta.json` 无 schema/来源校验即驱动发布                                              | T02.A1, T05.T1, T06.T1, T07.T1   | **7.7 High**   | `CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:N/VI:H/VA:N/SC:N/SI:H/SA:N` | [CWE-345](https://cwe.mitre.org/data/definitions/345.html)   | A08:2025 – 软件与数据完整性失效 | sbom-gen-upload.py                                                                                                                                                                                          |
| FIND-09 | 默认 `http` scheme 代码路径（anchore 客户端）与可传 http 的 OBS/SBOM endpoint，明文传输凭据与 SBOM         | T01.I2, T07.T1, T02（DF02/DF08） | **6.9 Medium** | `CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N` | [CWE-319](https://cwe.mitre.org/data/definitions/319.html)   | A02:2025 – 加密机制失效         | [internal/anchore/client.go:63-69](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-generator/internal/anchore/client.go#L63-L69)                                                                   |
| FIND-10 | ORT Dockerfile 删除 gradle wrapper `distributionSha256Sum`，构建期 wrapper 可被替换                        | T03.T1                           | **7.1 High**   | `CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N` | [CWE-494](https://cwe.mitre.org/data/definitions/494.html)   | A08:2025 – 软件与数据完整性失效 | [sbom-ort/Dockerfile:52-54](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/Dockerfile#L52-L54)                                                                                                |
| FIND-11 | 恶意归档内 symlink 指向宿主敏感文件，cataloger 跟随读取后内容进入 SBOM                                     | T01.I1, T04.T1                   | **5.9 Medium** | `CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N` | [CWE-59](https://cwe.mitre.org/data/definitions/59.html)     | A01:2025 – 访问控制失效         | extractor.go 解压流程                                                                                                                                                                                       |
| FIND-12 | zip 炸弹与 OBS 全量下载无总量上限，CI 磁盘/CPU 资源耗尽                                                    | T01.D1, T02.D1, T04.D1           | **5.9 Medium** | `CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N` | [CWE-409](https://cwe.mitre.org/data/definitions/409.html)   | A05:2025 – 安全配置错误         | extractor.go、download_file_from_obs.py                                                                                                                                                                     |
| FIND-13 | sbom-ort 发布 JAR 无签名、消费侧固定 1.0.0 引入且无校验和校验，制品仓库篡改即向 sbom-server 类路径注入代码 | T11.T1, T11.E1                   | **8.1 High**   | `CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H` | [CWE-494](https://cwe.mitre.org/data/definitions/494.html)   | A08:2025 – 软件与数据完整性失效 | [sbom-ort/build.gradle.kts:364-393](file:///d:/CODE/JAVACODE/openlibing-sbom/sbom-tools/sbom-ort/build.gradle.kts#L364-L393)、[pom.xml:309-323](file:///d:/CODE/JAVACODE/openlibing-sbom/pom.xml#L309-L323) |
| FIND-14 | JAR 发布身份未做密码学绑定、版本无不可变保护，同坐标版本可被恶意覆盖发布                                   | T11.S1                           | **6.3 Medium** | `CVSS:4.0/AV:A/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N` | [CWE-345](https://cwe.mitre.org/data/definitions/345.html)   | A08:2025 – 软件与数据完整性失效 | sbom-ort/build.gradle.kts（publishing 配置）                                                                                                                                                                |
| FIND-15 | ORT 传递依赖未做审计/门禁，恶意或含漏洞的传递依赖随 JAR 进入 sbom-server 类路径                            | T11.T2                           | **5.9 Medium** | `CVSS:4.0/AV:A/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N` | [CWE-1104](https://cwe.mitre.org/data/definitions/1104.html) | A06:2025 – 过时或有缺陷的组件   | sbom-ort build.gradle.kts（mavenCentral 依赖解析）                                                                                                                                                          |
| FIND-16 | 进程内分析与服务端凭据共享权限域，无进程/权限隔离，代码执行直达数据库连接串与配置中心                      | T12.I1, T12.T1                   | **6.9 Medium** | `CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N` | [CWE-250](https://cwe.mitre.org/data/definitions/250.html)   | A05:2025 – 安全配置错误         | [AbstractBaseAnalyzer.java:79-100](file:///d:/CODE/JAVACODE/openlibing-sbom/analyzer/src/main/java/org/opensourceway/sbom/analyzer/AbstractBaseAnalyzer.java#L79-L100)                                      |

### 5.3 Tier 3 — 纵深防御

| ID      | 标题                                                                                                  | 关联威胁               | CVSS 4.0       | 向量                                                              | CWE                                                        | OWASP Top 10:2025               | 证据                       |
| ------- | ----------------------------------------------------------------------------------------------------- | ---------------------- | -------------- | ----------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------- | -------------------------- |
| FIND-17 | 扫描与发布行为无持久化/防篡改审计日志，不可归责                                                       | T01.R1, T02.R1, T07.R1 | **5.3 Medium** | `CVSS:4.0/AV:L/AC:L/AT:N/PR:L/UI:N/VC:L/VI:N/VA:N/SC:N/SI:L/SA:N` | [CWE-778](https://cwe.mitre.org/data/definitions/778.html) | A09:2025 – 安全日志与监控失效   | run.sh、sbom-gen-upload.py |
| FIND-18 | advisor 漏洞咨询响应无完整性校验，可被篡改导致漏报/误报                                               | T10.T1                 | **5.3 Medium** | `CVSS:4.0/AV:A/AC:H/AT:N/PR:N/UI:N/VC:N/VI:H/VA:N/SC:N/SI:N/SA:N` | [CWE-345](https://cwe.mitre.org/data/definitions/345.html) | A08:2025 – 软件与数据完整性失效 | sbom-ort/clients/          |
| FIND-19 | 容器加固缺失：无 `USER` 指令（root 运行）、基础镜像 EOL（golang:1.18.2-alpine3.14）、环境变量过度传播 | T02.E1, T04.T1, T04.I1 | **6.2 Medium** | `CVSS:4.0/AV:L/AC:H/AT:N/PR:L/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N` | [CWE-250](https://cwe.mitre.org/data/definitions/250.html) | A05:2025 – 安全配置错误         | sbom-generator Dockerfile  |

### 5.4 发现与威胁覆盖核对

| Tier   | 发现数 | 覆盖威胁                                                                                                                                                       |
| ------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tier 1 | 3      | T01.T2, T02.I1, T05.I1, T12.E1, T12.A1                                                                                                                         |
| Tier 2 | 13     | T01.I1, T01.I2, T01.D1, T02.S1, T02.I2, T02.D1, T02.E1, T02.A1, T03.T1, T06.S1, T06.T1, T05.T1, T07.S1, T07.T1, T11.T1, T11.S1, T11.E1, T11.T2, T12.I1, T12.T1 |
| Tier 3 | 3      | T01.R1, T02.R1, T07.R1, T08.S1, T08.T1, T09.T2, T10.T1                                                                                                         |

> 未直接映射到 FIND 的威胁（T02.R1 并入 FIND-17、T11.I1/T11.D1/T12.D1 为纵深防御与可用性类、其余 Tier 3 项如 T09.T1/T09.I1/T09.E1/T10.S1 为供应链纵深防御类，随 §6.3 路线图统一治理），N/A 条目除外。

---

## 6. 风险评估

### 6.1 STRIDE 热图（按发现 Tier × 威胁类别）

| 类别           | Tier 1（直接暴露）               | Tier 2（条件风险）                                   | Tier 3（纵深防御） |
| -------------- | -------------------------------- | ---------------------------------------------------- | ------------------ |
| **S** 仿冒     | 0                                | FIND-05, FIND-14                                     | —                  |
| **T** 篡改     | —                                | FIND-07, FIND-08, FIND-10, FIND-13, FIND-15, FIND-16 | FIND-18            |
| **R** 抵赖     | —                                | —                                                    | FIND-17            |
| **I** 信息泄露 | FIND-01                          | FIND-04, FIND-09, FIND-11                            | —                  |
| **D** 拒绝服务 | —                                | FIND-12                                              | —                  |
| **E** 权限提升 | FIND-02, FIND-03                 | —                                                    | FIND-19            |
| **A** 业务滥用 | （并入 T12.A1，随 FIND-03 治理） | —                                                    | —                  |

**热图解读**：风险重心集中在 **E（提升/代码执行）与 T（篡改/完整性）**。Tier 1 的两条代码执行链中，FIND-03（sbom-server 进程内执行）影响面最大——它直接攻陷在线服务而非一次性 CI 作业；T 类发现横跨三个 Tier 且新增 JAR 制品链三项（FIND-13/14/15），反映"完整性控制整体缺位"延伸到了 sbom-server 的交付链路。

### 6.2 安全控制成熟度评估（1–5 级）

| 控制域       | 现状评级    | 依据                                                                           | 目标                   |
| ------------ | ----------- | ------------------------------------------------------------------------------ | ---------------------- |
| 凭据管理     | 1（临时性） | AK/SK 走 cmdline/env、SSH 私钥入镜像、无 Vault/KMS                             | 4：集中密管 + 短时凭据 |
| 完整性校验   | 1（临时性） | sumdb 禁用、wrapper 校验删除、SBOM 无签名、OBS 无校验和、JAR 发布/消费均无校验 | 4：全链路签名/校验和   |
| 输入处理     | 2（部分）   | strip_credentials 仅用于 git URL；归档内容（symlink/嵌套解压）缺统一校验       | 4：统一不可信输入规范  |
| 进程隔离     | 1（临时性） | sbom-server JVM 内直接解析不可信项目；容器 root 运行                           | 4：沙箱 + 最小权限容器 |
| 制品交付管控 | 1（临时性） | JAR 发布无 signing、版本不可变性未启用、传递依赖无准入门禁                     | 4：签名发布 + 依赖准入 |
| 审计与可追溯 | 2（部分）   | stdout 日志存在，但无结构化/防篡改/远端上报                                    | 4：结构化审计事件      |
| 传输加密     | 3（基线）   | requests 默认验 TLS，但存在默认 http 路径与未强制 https                        | 4：强制 https          |
| 平台默认安全 | 4（良好）   | secrets cataloger 默认不 reveal；注册表 TLS 校验默认开启                       | 维持                   |

### 6.3 修复优先级路线图

| 优先级            | ID                        | 修复措施                                                                                                                              | 状态 | 工作量 | 剩余风险                           | 所有权                    |
| ----------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---- | ------ | ---------------------------------- | ------------------------- |
| **P0**（立即）    | FIND-03                   | sbom-server 侧将 ORT 分析迁移为隔离子进程执行（容器/独立 JVM + 资源/时限限制），禁止在服务 JVM 内解析不可信项目                       | OPEN | 中     | 残余：子进程逃逸（低）             | sbom-server 团队          |
| **P1**（30 天内） | FIND-13                   | sbom-ort 发布启用 GPG 签名（maven-publish signing 插件）；sbom-server 消费侧固定版本 + 校验和（`dependency-verification` /锁文件）    | OPEN | 中     | 残余：签名私钥失窃                 | sbom-ort + sbom-server    |
| **P1**            | FIND-01                   | `parse_download_files_from_log` 对 wget/curl URL 复用 `strip_credentials()`，凭据不写入 SBOM `downloadLocation`                       | OPEN | 低     | 残余：历史已发布 SBOM 中的残留凭据 | sbom-generator 团队       |
| **P1**            | FIND-07, FIND-10          | 恢复并启用 sumdb 校验与 gradle wrapper `distributionSha256Sum`；锁定依赖版本                                                          | OPEN | 低     | 残余：注册表上游被攻陷             | sbom-generator / sbom-ort |
| **P1**            | FIND-04, FIND-06          | 凭据全部改经环境/临时文件注入并即时清除；SSH 私钥改用 BuildKit `--mount=secret`；克隆改用 commit + HTTPS；`StrictHostKeyChecking=yes` | OPEN | 中     | 残余：宿主内存转储                 | sbom-generator 团队       |
| **P1**            | FIND-08                   | SBOM 生成后即时签名（cosign / detached sig）；OBS `meta.json` 增加 schema 校验与签名验证后才允许驱动发布                              | OPEN | 中     | 残余：签名基础设施运维             | 平台团队                  |
| **P2**（90 天内） | FIND-05                   | 发布签名升级为带 nonce + 绑定请求体的 HMAC 或改用 mTLS/token                                                                          | OPEN | 低     | 残余：端点被仿冒                   | 平台团队                  |
| **P2**            | FIND-09, FIND-14          | 强制 https endpoint；启用制品库版本不可变策略                                                                                         | OPEN | 低     | 残余：终端误配置                   | 平台团队                  |
| **P2**            | FIND-11, FIND-12          | 解压前对 symlink 做白名单化处理或拒绝跨根解析；增加解压资源上限；OBS 下载限速/限量                                                    | OPEN | 中     | 残余：新型归档格式逃逸             | sbom-generator 团队       |
| **P2**            | FIND-15, FIND-16          | ORT 依赖引入 dependency audit + 准入门禁；sbom-server 分析子进程使用专用低权限账号与最小化凭据集                                      | OPEN | 中     | 残余：依赖投毒高级攻击             | sbom-ort + sbom-server    |
| **P3**（下季度）  | FIND-17, FIND-18, FIND-19 | 结构化审计日志（append-only + 远端上报）；advisor 响应加签验签；容器非 root + 基础镜像升级 + env 白名单                               | OPEN | 中     | 残余：合规基线差距                 | 各组件 owner              |

**路线图说明**：P0 针对"不可信输入直接代码执行"这一最高影响类别，建议在下一次发布前完成；P1 集中补齐完整性链条（签名/校验和），使 JAR 交付链与 SBOM 产物获得密码学保护；P2/P3 为条件风险收尾与纵深防御，可结合季度安全计划排期。

### 6.4 关键暴露风险摘要

1. **sbom-server 进程内分析不可信项目（FIND-03）是当前最严重的暴露面**：恶意构造的 build.gradle.kts/build.gradle/pom.xml 在服务 JVM 内获得完整代码执行能力，可直接波及数据库、配置中心与全部服务端凭据。这是 sbom-ort JAR 集成方式的直接安全代价，P0 修复（子进程隔离）不可延后。
2. **JAR 交付链整体缺完整性控制（FIND-13/14/15）**：发布无签名、消费无校验和、版本不可变性未启用、传递依赖无门禁。任一环节（构建机、制品库、网络）被攻陷，恶意代码将随 `org.opensourceway:sbom-ort` 静默进入 sbom-server 类路径。签名 + 校验和 + 依赖准入三件套应作为 P1 一并落地。
3. **离线工具虽不在生产边界内，但其凭据链（FIND-04/06）与 SBOM 产物链（FIND-01/08）会反噬上游**：扫描宿主上的凭据泄露可被用于伪造 SBOM 上传，进而污染下游发布决策。离线工具的安全基线必须与在线服务同级对待。

---

## 7. 风险接受与后续行动

### 7.1 需要风险所有者正式接受的风险

| 风险                                           | 所有者           | 接受理由（建议）                              | 复审日期   |
| ---------------------------------------------- | ---------------- | --------------------------------------------- | ---------- |
| FIND-12 剩余风险（OBS 大对象下载的可用性影响） | 平台团队         | CI 资源配额天然限流，下载限量落地后残余风险低 | 2026-Q4    |
| FIND-18 剩余风险（advisor 响应篡改导致漏报）   | 平台团队         | 漏报影响为运营性而非安全性；加签验签排期至 P3 | 2026-Q4    |
| 子进程隔离后的残余逃逸风险（FIND-03 修复后）   | sbom-server 团队 | 容器隔离 + gVisor/seccomp 后逃逸概率极低      | 修复验收时 |

### 7.2 后续行动项（本报告之外的配套工作）

1. 将本报告 FIND 清单同步至缺陷跟踪系统（Jira/GitLab Issue），逐项建立修复工单并关联 ownership。
2. 为 sbom-server 侧的 ORT 集成建立回归用例：恶意 gradle/pom 样本（命令执行、网络外联、文件写入）在隔离方案下必须全部失败。
3. 对 sbom-generator 建立模糊测试目标：tar/zip/squashfs extractor 与 dockerfile/frontmatter 解析器。
4. 建立 SBOM 产物签名与制品签名的验收清单，纳入发布流水线门禁。
5. 下一次增量威胁模型评估的基线为本目录 `threat-inventory.json`，复审触发条件：sbom-ort JAR 发布机制变更、sbom-server 分析架构调整、或新增扫描源支持。

---

## 8. 参考资料

- OWASP Top 10:2025 — <https://owasp.org/Top10/2025/>
- CVSS 4.0 规范 — <https://www.first.org/cvss/v4.0/specification-document>
- OWASP Cheat Sheet: Dependency & Supply Chain Security — <https://cheatsheetseries.owasp.org/>
- NIST SP 800-218 Secure Software Development Framework (SSDF)
- SLSA（Supply-chain Levels for Software Artifacts）— <https://slsa.dev/>
- Gradle 依赖验证 — <https://docs.gradle.org/current/userguide/dependency_verification.html>
- Maven 签名校验实践（GPG signing）— <https://maven.apache.org/plugins/maven-gpg-plugin/>
- Syft/ORT 官方文档（扫描器与分析器行为）

---

## 9. 附录

### 9.1 术语表

| 术语           | 定义                                                                                               |
| -------------- | -------------------------------------------------------------------------------------------------- |
| SBOM           | Software Bill of Materials，软件物料清单                                                           |
| STRIDE-A       | Spoofing / Tampering / Repudiation / Information Disclosure / DoS / Elevation of Privilege / Abuse |
| DFD            | 数据流图（Data Flow Diagram），用于威胁建模的结构化视图                                            |
| Trust Boundary | 信任边界，数据或控制权跨越不同信任级别的位置                                                       |
| ORT            | OSS Review Toolkit，开源组件分析与合规工具                                                         |
| Cataloger      | Syft 中负责从特定生态提取依赖信息的插件单元                                                        |
| Advisor        | ORT 中负责查询漏洞咨询数据的客户端组件                                                             |
| CSC            | Cloud Storage Credential，OBS 访问凭据（AK/SK）                                                    |

### 9.2 评估范围与限制

- **范围**：sbom-tools 仓库全部内容（sbom-generator、sbom-tracer、sbom-ort），并覆盖 sbom-server 通过 JAR 消费 sbom-ort 的集成面（analyzer 模块代码在仓库外，按集成面纳入）。
- **排除**：运行时基础设施（K8s/OBS/制品库服务端配置）、CI 平台自身安全、人员与社会工程风险。
- **方法**：静态代码审查 + STRIDE-A 威胁枚举 + CVSS 4.0 打分；未执行动态验证（PoC），Tier 评级中已考虑"未验证"保守系数。
- **限制**：`mvn` 本地解析未实测（凭据不可用），以静态证据为准；CVSS 分数为工程师视角的风险量化，不代表正式风险登记值。

### 9.3 基线快照

- 基线文件：`threat-inventory.json`（与本报告同目录），记录全部 19 项发现的 ID、Tier、状态与治理位置，供下次增量分析比对。
- 报告生成时间：2026-09-02（本地时间 18:33 UTC+8）
- 分析会话：threat-model-analyst / 单仓库全量模式
