# openlibing-pre-commit-action 安全威胁分析报告

## 报告元数据

| 字段 | 值 |
|------|-----|
| 分析模式 | 单次完整分析 (Single Analysis) |
| 分析开始时间 | 2026-09-03 03:17:53 UTC |
| 分析完成时间 | 2026-09-03 03:45:00 UTC |
| 仓库地址 | https://gitcode.com/sky140/openlibing-pre-commit-action.git |
| 分支 | dev |
| 提交 | baf4c3b |
| 提交日期 | 2026-08-26 14:53:45 +0800 |
| 主机名 | DESKTOP-ROGG1JQ |
| 分析工具 | STRIDE-A 威胁建模方法 |

---

## 一、系统概述

### 1.1 系统用途

openlibing-pre-commit-action 是一个 GitCode/AtomGit Actions 插件，用于在 CI/CD 流水线中自动安装 pre-commit 工具并对代码仓库执行钩子检查。该插件支持 PR 增量检查和全量检查自动切换，具备镜像源测速选择、Go/pip 代理配置、GC_TOKEN 私仓认证等功能。

### 1.2 关键组件

| 组件 | 类型 | 源文件 | 描述 |
|------|------|--------|------|
| ActionRunner | 进程 | index.js, dist/index.js | 核心 Node.js 脚本，编排整个 pre-commit 检查流程 |
| ActionMetadata | 配置 | action.yml | 插件元数据，定义输入参数 (gc_token, extra_args) 和输出 |
| PreCommitWorkflow | CI 流水线 | .gitcode/workflows/pre-commit.yml | 调用该 Action 的 CI/CD 流水线定义 |
| CodeQLWorkflow | CI 流水线 | .gitcode/workflows/codeql.yaml | CodeQL 安全分析流水线 |
| PackageScript | 构建工具 | zip.js | 打包脚本，生成发布 zip 文件 |
| VersionBumper | 构建工具 | bump-version.js | 版本号自增脚本 |

### 1.3 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | JavaScript (Node.js 16) |
| 运行时 | GitCode Actions Runner (node16) |
| 包管理 | npm, pip |
| 外部工具 | pre-commit, git, curl, find, python |
| CI/CD | GitCode Actions / AtomGit Actions |
| 安全扫描 | CodeQL (JavaScript) |

### 1.4 部署模型

**部署分类：CI/CD 插件 (CICD_PLUGIN)**

该插件以 Node.js 脚本形式运行在 CI/CD 执行机环境中（自托管或云端执行机），不直接暴露网络端口。执行机通过 CI 平台调度触发，插件读取环境变量和工作区文件执行操作。

| 组件 | 监听地址 | 认证屏障 | 外部可达性 | 最低前置条件 |
|------|----------|----------|------------|-------------|
| ActionRunner | 无监听 (CI 任务) | CI 平台调度 | 不可直接访问 | CI 平台触发权限 |
| PreCommitWorkflow | 无监听 (CI 定义) | CI 平台认证 | 不可直接访问 | CI 平台触发权限 |
| CodeQLWorkflow | 无监听 (CI 定义) | CI 平台认证 | 不可直接访问 | CI 平台触发权限 |

### 1.5 系统架构图

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryColor': '#ffffff', 'lineColor': '#666666' }}}%%
flowchart LR
    classDef service fill:#6baed6,stroke:#2171b5,stroke-width:2px,color:#000000
    classDef external fill:#fdae61,stroke:#d94701,stroke-width:2px,color:#000000
    classDef datastore fill:#74c476,stroke:#238b45,stroke-width:2px,color:#000000
    linkStyle default stroke:#666666,stroke-width:2px

    CIPlatform["CI/CD 平台"]:::external
    Operator["操作者/开发者"]:::external

    subgraph Runner["CI 执行机"]
        ActionRunner["ActionRunner<br/>(index.js)"]:::service
        PreCommitConfig[(".pre-commit-config.yaml")]:::datastore
    end

    PipMirror["PyPI / 华为镜像"]:::external
    GoProxy["Go Proxy / 华为镜像"]:::external
    GitRemote["GitCode 远程仓库"]:::external
    GitCodeAPI["GitCode API"]:::external

    Operator -->|"提交 PR/Push"| CIPlatform
    CIPlatform -->|"触发/环境变量/工作区"| ActionRunner
    ActionRunner -->|"curl 测速"| PipMirror
    ActionRunner -->|"curl 测速"| GoProxy
    ActionRunner -->|"pip install"| PipMirror
    ActionRunner -->|"git fetch/push"| GitRemote
    ActionRunner -->|"API 查询用户信息"| GitCodeAPI
    ActionRunner -->|"读取配置"| PreCommitConfig
    PreCommitConfig -->|"执行 hooks"| ActionRunner

    style Runner fill:#f0f4ff,stroke:#2171b5,stroke-width:2px,stroke-dasharray: 5 5
```

### 1.6 信任边界

| 边界 | 描述 | 包含组件 |
|------|------|----------|
| 外部网络边界 | CI 执行机与外部网络服务之间的边界 | PipMirror, GoProxy, GitRemote, GitCodeAPI |
| CI 平台边界 | CI 平台与 Action 插件之间的边界，通过环境变量传递数据 | CIPlatform → ActionRunner |
| 用户输入边界 | 用户可控输入（extra_args, gc_token, .pre-commit-config.yaml）进入插件 | Operator → ActionRunner |
| 代码执行边界 | pre-commit hooks 在执行机上执行任意代码 | PreCommitConfig → ActionRunner |

### 1.7 核心数据流

| ID | 源 | 目标 | 协议 | 描述 |
|----|------|------|------|------|
| DF01 | CIPlatform | ActionRunner | 环境变量 | 传递 WORKSPACE, ATOMGIT_EVENT_NAME, ATOMGIT_BASE_REF 等环境变量 |
| DF02 | ActionRunner | PipMirror | HTTPS | curl 测速 + pip install pre-commit |
| DF03 | ActionRunner | GoProxy | HTTPS | curl 测速 + go env 代理配置 |
| DF04 | ActionRunner | GitRemote | HTTPS | git fetch 拉取分支、git remote set-url 设置认证 |
| DF05 | ActionRunner | GitCodeAPI | HTTPS | curl 查询 GC_TOKEN 对应用户信息 |
| DF06 | ActionRunner | PreCommitConfig | 文件读写 | 读取 .pre-commit-config.yaml 配置文件 |
| DF07 | PreCommitConfig | ActionRunner | 进程执行 | pre-commit hooks 在执行机上执行任意代码 |

### 1.8 关键场景

#### 场景 1：PR 增量检查流程

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'background': '#ffffff',
  'actorBkg': '#6baed6', 'actorBorder': '#2171b5', 'actorTextColor': '#000000',
  'signalColor': '#666666', 'signalTextColor': '#666666',
  'noteBkgColor': '#fdae61', 'noteBorderColor': '#d94701', 'noteTextColor': '#000000',
  'activationBkgColor': '#ddeeff', 'activationBorderColor': '#2171b5'
}}}%%
sequenceDiagram
    actor Operator
    participant CI as CI 平台
    participant AR as ActionRunner
    participant Git as Git 远程仓库
    participant PC as pre-commit

    Operator->>CI: 提交 PR
    CI->>AR: 触发流水线 (环境变量)
    activate AR
    Note over AR: 读取 ATOMGIT_BASE_REF, ATOMGIT_HEAD_REF
    AR->>AR: 获取 gc_token, 设置 git remote URL
    AR->>Git: git fetch origin baseRef
    Git-->>AR: FETCH_HEAD
    AR->>AR: git diff FETCH_HEAD --name-only
    AR->>AR: 过滤增量文件列表
    AR->>PC: pre-commit run --files [files]
    PC-->>AR: 检查结果
    alt 检查通过
        AR-->>CI: 成功
    else 检查失败
        AR-->>CI: 失败 + 修复建议
    end
    deactivate AR
```

#### 场景 2：镜像源测速选择流程

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'background': '#ffffff',
  'actorBkg': '#6baed6', 'actorBorder': '#2171b5', 'actorTextColor': '#000000',
  'signalColor': '#666666', 'signalTextColor': '#666666',
  'noteBkgColor': '#fdae61', 'noteBorderColor': '#d94701', 'noteTextColor': '#000000',
  'activationBkgColor': '#ddeeff', 'activationBorderColor': '#2171b5'
}}}%%
sequenceDiagram
    participant AR as ActionRunner
    participant Pip as PyPI 源站
    participant Mirror as 华为镜像

    activate AR
    Note over AR: detectMirrorConfig() 启动
    AR->>Pip: curl 测速 (max-time 5s)
    Pip-->>AR: 响应时间
    AR->>Mirror: curl 测速 (max-time 5s)
    Mirror-->>AR: 响应时间
    Note over AR: 比较响应时间, 选择更快源
    AR->>AR: pip config set global.index-url
    alt Go 已安装
        AR->>Pip: Go proxy 测速
        AR->>Mirror: Go mirror 测速
        Note over AR: 设置 GOPROXY
    end
    deactivate AR
```

#### 场景 3：pip 安装与版本检查流程

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'background': '#ffffff',
  'actorBkg': '#6baed6', 'actorBorder': '#2171b5', 'actorTextColor': '#000000',
  'signalColor': '#666666', 'signalTextColor': '#666666',
  'noteBkgColor': '#fdae61', 'noteBorderColor': '#d94701', 'noteTextColor': '#000000',
  'activationBkgColor': '#ddeeff', 'activationBorderColor': '#2171b5'
}}}%%
sequenceDiagram
    participant AR as ActionRunner
    participant Pip as pip/PyPI

    activate AR
    AR->>Pip: python -m pip --version
    Pip-->>AR: pip 版本号
    alt pip >= 21.0
        Note over AR: 跳过升级
    else pip < 21.0
        AR->>Pip: pip install --ignore-installed --upgrade pip
        Note over AR: 使用 --ignore-installed 避免<br/>RECORD 文件缺失问题
    else pip 未安装
        AR->>Pip: pip install --upgrade pip
    end
    AR->>Pip: pip install pre-commit
    AR->>Pip: python -m pre_commit --version
    deactivate AR
```

---

## 二、威胁模型 DFD 图

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'background': '#ffffff', 'primaryColor': '#ffffff', 'lineColor': '#666666' }}}%%
flowchart LR
    classDef process fill:#6baed6,stroke:#2171b5,stroke-width:2px,color:#000000
    classDef external fill:#fdae61,stroke:#d94701,stroke-width:2px,color:#000000
    classDef datastore fill:#74c476,stroke:#238b45,stroke-width:2px,color:#000000
    linkStyle default stroke:#666666,stroke-width:2px

    Operator["操作者/开发者"]:::external
    CIPlatform["CI/CD 平台"]:::external

    subgraph Runner["CI 执行机信任域"]
        ActionRunner(("ActionRunner")):::process
        PreCommitConfig[(".pre-commit-config.yaml")]:::datastore
        Workspace[("工作区文件系统")]:::datastore
    end

    subgraph ExternalNet["外部网络信任域"]
        PipMirror["PyPI/华为镜像"]:::external
        GoProxy["Go Proxy/华为镜像"]:::external
        GitRemote["GitCode 远程仓库"]:::external
        GitCodeAPI["GitCode API"]:::external
    end

    Operator -->|"DF01: PR/Push 事件"| CIPlatform
    CIPlatform -->|"DF02: 环境变量/工作区"| ActionRunner
    ActionRunner -->|"DF03: curl 测速/pip install"| PipMirror
    ActionRunner -->|"DF04: curl 测速/go env"| GoProxy
    ActionRunner -->|"DF05: git fetch/remote set-url"| GitRemote
    ActionRunner -->|"DF06: API 查询用户信息"| GitCodeAPI
    ActionRunner -->|"DF07: 读取配置"| PreCommitConfig
    PreCommitConfig -->|"DF08: 执行 hooks"| ActionRunner
    ActionRunner -->|"DF09: 文件读写"| Workspace

    style Runner fill:none,stroke:#e31a1c,stroke-width:3px,stroke-dasharray: 5 5
    style ExternalNet fill:none,stroke:#e31a1c,stroke-width:3px,stroke-dasharray: 5 5
```

### DFD 元素表

| 元素 | 类型 | 描述 | 信任边界 |
|------|------|------|----------|
| Operator | 外部交互者 | 提交 PR/Push 的开发者 | 外部 |
| CIPlatform | 外部交互者 | GitCode CI/CD 平台，触发流水线 | 外部 |
| ActionRunner | 进程 | 核心 Node.js 脚本，编排所有操作 | CI 执行机 |
| PreCommitConfig | 数据存储 | .pre-commit-config.yaml 配置文件 | CI 执行机 |
| Workspace | 数据存储 | CI 工作区文件系统 | CI 执行机 |
| PipMirror | 外部交互者 | PyPI 源站和华为镜像 | 外部网络 |
| GoProxy | 外部交互者 | Go 代理源站和华为镜像 | 外部网络 |
| GitRemote | 外部交互者 | GitCode 远程 Git 仓库 | 外部网络 |
| GitCodeAPI | 外部交互者 | GitCode REST API | 外部网络 |

---

## 三、STRIDE-A 威胁分析

### 3.1 可利用性分级

| 等级 | 标签 | 前置条件 | 分配规则 |
|------|------|----------|----------|
| **Tier 1** | 直接暴露 | 无 | 未认证外部攻击者无需任何前置访问即可利用 |
| **Tier 2** | 条件风险 | 单一前置条件 | 需要一种形式的访问：认证用户、内部网络等 |
| **Tier 3** | 纵深防御 | 多个前置条件或基础设施访问 | 需要主机访问、管理员凭据或组件已遭入侵 |

### 3.2 威胁汇总

| 组件 | 链接 | S | T | R | I | D | E | A | 合计 | T1 | T2 | T3 | 风险 |
|------|------|---|---|---|---|---|---|---|------|----|----|----|------|
| ActionRunner | [详情](#actionrunner) | 2 | 3 | 1 | 3 | 2 | 1 | 2 | 14 | 4 | 7 | 3 | 高 |
| ActionMetadata | [详情](#actionmetadata) | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 3 | 0 | 2 | 1 | 中 |
| PreCommitWorkflow | [详情](#precommitworkflow) | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 6 | 1 | 3 | 2 | 中 |
| CodeQLWorkflow | [详情](#codeqlworkflow) | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 2 | 0 | 1 | 1 | 低 |
| PackageScript | [详情](#packagescript) | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 2 | 低 |
| VersionBumper | [详情](#versionbumper) | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 低 |
| **合计** | | **3** | **7** | **1** | **6** | **3** | **2** | **6** | **28** | **5** | **13** | **10** | |

> **威胁计数说明：** 共识别 28 个威胁，其中 5 个为 Tier 1（直接暴露），13 个为 Tier 2（条件风险），10 个为 Tier 3（纵深防御）。Tier 1 威胁需要优先处理。

---

### 3.3 ActionRunner

**信任边界：** CI 执行机
**角色：** 核心执行引擎，编排 pre-commit 安装、配置、检查全流程
**数据流：** DF01-DF09

#### Tier 1 — 直接暴露（无前置条件）

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T01.S | 欺骗 | curl 测速请求可被中间人劫持，返回虚假响应时间引导使用恶意镜像源 | 无 | DF03, DF04 | 未实施 TLS 证书验证（curl -s 未使用 --cacert） | Open |
| T01.T | 篡改 | 网络测速结果可被篡改，引导插件使用恶意 pip/Go 镜像源下载被篡改的包 | 无 | DF03, DF04 | 未实施源站完整性校验（无 GPG 签名验证） | Open |
| T01.I | 信息泄露 | execCapture 和 exec 函数在 console.log 中输出完整命令，可能泄露 git remote URL 中嵌入的 GC_TOKEN | 无 | DF05 | 已使用 encodeURIComponent 编码 token，但 console.log 仍输出完整命令 | Open |
| T01.A | 滥用 | .pre-commit-config.yaml 中的 hooks 可在执行机上执行任意代码（如 local hooks 的 entry 字段） | 无 | DF07, DF08 | 无沙箱隔离机制，pre-commit hooks 以当前用户权限执行 | Open |

#### Tier 2 — 条件风险

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T02.T | 篡改 | extra_args 参数校验存在绕过风险：允许任何以 -- 开头的参数，攻击者可传入 --config 等未预期的参数 | 认证用户（PR 提交者） | DF01 | 已有 allowedArgs 白名单，但 -- 前缀检查过于宽松 | Open |
| T02.T | 篡改 | git diff FETCH_HEAD 输出的文件名可能包含特殊字符，传入 pre-commit run --files 时可能导致参数注入 | 认证用户（PR 提交者） | DF07 | 使用 execFileSync（非 shell 模式），降低了注入风险 | Mitigated |
| T02.R | 抵赖 | git remote set-url 操作修改了远程仓库 URL，但无审计日志记录操作者和时间 | 内部网络 | DF05 | 无审计日志机制 | Open |
| T02.I | 信息泄露 | GC_TOKEN 通过环境变量 INPUT_GC_TOKEN 传递，进程列表中可能可见 | 内部网络 | DF01 | 环境变量传递是 CI/CD 标准方式，但未在任务完成后清理 | Open |
| T02.I | 信息泄露 | execCapture('git remote get-url origin') 输出包含 token 的 URL 到 console.log | 内部网络 | DF05 | console.log 输出完整命令和结果 | Open |
| T02.D | 拒绝服务 | 大量 PR 变更文件（数万文件）传入 pre-commit run --files 可导致内存溢出或超时 | 认证用户（PR 提交者） | DF07 | 无文件数量上限检查 | Open |
| T02.E | 提权 | GC_TOKEN 具有代码推送权限，若被截获（如通过进程列表或日志），攻击者可向仓库推送恶意代码 | 认证用户（PR 提交者） | DF05 | token 已编码（encodeURIComponent），但仍在 URL 和环境变量中明文存在 | Open |

#### Tier 3 — 纵深防御

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T03.S | 欺骗 | pip install pre-commit 可能从被劫持的镜像源安装恶意版本的 pre-commit | 主机访问 + 镜像源控制 | DF03 | 依赖 pip 的 HTTPS 传输，但未验证包签名 | Open |
| T03.T | 篡改 | 工作区路径校验正则 `/^\/[\w\-\/.]+$/` 可被绕过（如使用 .. 路径遍历），可能导致访问工作区外的文件 | 主机/OS 访问 | DF09 | 有正则校验，但未解析真实路径 | Open |
| T03.D | 拒绝服务 | curl 测速使用 --max-time 5s 超时，但多个串行测速可累积导致流水线延迟 | 镜像源不可达 | DF03, DF04 | 有 5 秒超时限制 | Mitigated |

---

### 3.4 ActionMetadata

**信任边界：** 配置文件
**角色：** 定义插件输入参数（gc_token, extra_args）和输出
**数据流：** DF01

#### Tier 1 — 直接暴露（无前置条件）

*无 Tier 1 威胁*

#### Tier 2 — 条件风险

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T04.T | 篡改 | action.yml 中 gc_token 输入描述为"pre-commit 自动修复时所需密钥"，但实际代码中用于 git 认证，描述与实际用途不符可能导致误用 | 认证用户（仓库管理员） | DF01 | 无 | Open |
| T04.I | 信息泄露 | gc_token 默认值为空字符串，但在 CI 日志中可能通过 inputs 回显泄露 | 内部网络 | DF01 | action.yml 中 required: false | Open |

#### Tier 3 — 纵深防御

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T04.A | 滥用 | runs.using 固定为 "node16"，未升级到更新的 Node.js 版本，可能存在已知漏洞 | 主机/OS 访问 | DF01 | Node 16 已 EOL | Open |

---

### 3.5 PreCommitWorkflow

**信任边界：** CI 流水线定义
**角色：** 定义 PR 触发条件、执行机配置、步骤编排
**数据流：** DF01

#### Tier 1 — 直接暴露（无前置条件）

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T05.S | 欺骗 | pull_request_target 触发方式使用默认分支的流水线配置，但检出 PR 的代码，攻击者可通过修改 PR 代码影响检查结果 | 无 | DF01 | 使用 merge_commit_sha 检出预合并代码 | Mitigated |

#### Tier 2 — 条件风险

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T05.I | 信息泄露 | pre-commit 流水线中 ROBOT_TOKEN 通过 secrets 引用，但可能在步骤日志中泄露 | 认证用户（PR 提交者） | DF01 | 使用 ${{ secrets.ROBOT_TOKEN }} 引用 | Mitigated |
| T05.D | 拒绝服务 | PR 评论触发（/pre-commit）可被频繁触发，导致执行机资源耗尽 | 认证用户（PR 评论者） | DF01 | 无频率限制 | Open |
| T05.E | 提权 | 流水线权限设置为 pr: write，允许通过 PR 评论触发代码推送标签操作 | 认证用户（PR 评论者） | DF01 | 使用 pr-label-action 限制操作范围 | Mitigated |

#### Tier 3 — 纵深防御

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T05.A | 滥用 | pre-commit 流水线在 self-hosted 执行机上运行（region=overseas），执行机配置可能被未授权修改 | 主机/OS 访问 | DF01 | 执行机注册到 CI 平台 | Open |

---

### 3.6 CodeQLWorkflow

**信任边界：** CI 流水线定义
**角色：** CodeQL 安全分析流水线
**数据流：** DF01

#### Tier 1 — 直接暴露（无前置条件）

*无 Tier 1 威胁*

#### Tier 2 — 条件风险

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T06.I | 信息泄露 | CodeQL 流水线中 OPENLIBING_OBS_AK/SK 和 APIG 密钥通过 secrets 引用，若日志输出不当可能泄露 | 认证用户（仓库管理员） | DF01 | 使用 ${{ secrets.* }} 引用 | Mitigated |

#### Tier 3 — 纵深防御

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T06.A | 滥用 | CodeQL 报告上传使用 obs_ak/obs_sk 密钥，若密钥泄露可上传篡改的安全报告 | 主机/OS 访问 | DF01 | 密钥存储在 CI secrets 中 | Open |

---

### 3.7 PackageScript

**信任边界：** 构建工具
**角色：** 打包 README.md、action.yml、dist/ 为 zip 文件
**数据流：** 无运行时数据流

#### Tier 1 — 直接暴露（无前置条件）

*无 Tier 1 威胁*

#### Tier 2 — 条件风险

*无 Tier 2 威胁*

#### Tier 3 — 纵深防御

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T07.T | 篡改 | zip.js 通过正则匹配 action.yml 中的 version 字段并自增，正则可能匹配错误导致版本号异常 | 主机/OS 访问 | 无 | 正则 `/version:\s?'?(\d{1,2})\.(\d{1,2})\.(\d{1,2})'?/` 匹配范围有限 | Mitigated |
| T07.A | 滥用 | zip 打包内容固定（README.md, action.yml, dist/），但未校验文件完整性（如哈希），构建产物可被篡改 | 主机/OS 访问 | 无 | 无完整性校验 | Open |

---

### 3.8 VersionBumper

**信任边界：** 构建工具
**角色：** 自增 action.yml 中的版本号
**数据流：** 无运行时数据流

#### Tier 1 — 直接暴露（无前置条件）

*无 Tier 1 威胁*

#### Tier 2 — 条件风险

*无 Tier 2 威胁*

#### Tier 3 — 纵深防御

| ID | 类别 | 威胁 | 前置条件 | 影响数据流 | 缓解措施 | 状态 |
|----|------|------|----------|------------|----------|------|
| T08.T | 篡改 | bump-version.js 假设版本号格式为 X.Y.Z 并仅递增 Z，若格式不符（如使用语义化版本 pre-release 标签）可能导致版本号损坏 | 主机/OS 访问 | 无 | 正则匹配 `/version:\s*'([\d.]+)'/` | Mitigated |

---

## 四、安全发现

### 4.1 Tier 1 — 直接暴露（无前置条件）

#### FIND-01: curl 测速未实施 TLS 证书验证导致中间人攻击

**严重性：** Important
**CVSS 4.0：** 7.3 (AV:N/AC:L/AT:N/PR:N/UI:N/S:C/C:L/I:L/A:N)
**CWE：** [CWE-295](https://cwe.mitre.org/data/definitions/295.html): Improper Certificate Validation
**OWASP：** A04:2025 – Cryptographic Failures
**可利用性分级：** Tier 1
**修复成本：** Low
**相关威胁：** [T01.S](#actionrunner), [T01.T](#actionrunner)

**描述：**
`testUrlSpeed()` 函数使用 `curl -s` 进行网络测速，未指定 `--cacert` 或 TLS 证书验证选项。攻击者可通过中间人攻击篡改测速结果，引导插件使用恶意的 pip/Go 镜像源。

**证据：**
[index.js:69](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L69) - `execCapture(\`curl -s -o /dev/null -w "%{time_total}" --max-time ${SPEED_TEST_TIMEOUT} "${url}" 2>/dev/null\`)`

**修复建议：**
1. 在 curl 命令中添加 `--fail` 和 `--ssl-verify` 选项
2. 对 pip 镜像源使用 `--require-hashes` 验证包完整性
3. 考虑使用 HTTPS 证书固定 (certificate pinning)

---

#### FIND-02: 命令日志泄露 GC_TOKEN

**严重性：** Important
**CVSS 4.0：** 6.8 (AV:N/AC:L/AT:N/PR:N/UI:N/S:C/C:H/I:N/A:N)
**CWE：** [CWE-532](https://cwe.mitre.org/data/definitions/532.html): Insertion of Sensitive Information into Log File
**OWASP：** A04:2025 – Cryptographic Failures
**可利用性分级：** Tier 1
**修复成本：** Low
**相关威胁：** [T01.I](#actionrunner), [T02.I](#actionrunner), [T02.I](#actionrunner)

**描述：**
`exec()` 和 `execCapture()` 函数通过 `console.log` 输出完整命令。当 git remote URL 包含 GC_TOKEN 时（通过 `git remote set-url origin "https://oauth2:{token}@..."` 设置），token 会被明文输出到 CI 日志。此外 `execCapture('git remote get-url origin')` 也会输出包含 token 的 URL。

**证据：**
- [index.js:38](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L38) - `console.log(\`> ${cmd}\`)` 在 exec 函数中输出完整命令
- [index.js:130](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L130) - `execCapture('git remote get-url origin')` 获取并可能输出包含 token 的 URL
- [index.js:134](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L134) - `execCapture(\`git remote set-url origin "${authUrl}"\`)` 日志输出包含 token 的完整命令

**修复建议：**
1. 在 exec/execCapture 函数中添加敏感信息过滤，将 URL 中的 `oauth2:{token}@` 替换为 `oauth2:***@`
2. 避免在日志中输出完整的 git remote URL
3. 使用 `GIT_ASKPASS` 环境变量替代 URL 嵌入 token 的方式

---

#### FIND-03: pre-commit hooks 可执行任意代码无沙箱隔离

**严重性：** Important
**CVSS 4.0：** 7.0 (AV:N/AC:L/AT:N/PR:N/UI:N/S:C/C:H/I:H/A:N)
**CWE：** [CWE-250](https://cwe.mitre.org/data/definitions/250.html): Execution with Unnecessary Privileges
**OWASP：** A06:2025 – Insecure Design
**可利用性分级：** Tier 1
**修复成本：** Medium
**相关威胁：** [T01.A](#actionrunner)

**描述：**
`.pre-commit-config.yaml` 中的 hooks（尤其是 local hooks）可在执行机上执行任意命令。`entry` 字段直接作为命令执行，无沙箱或权限限制。攻击者可通过提交恶意的 `.pre-commit-config.yaml` 在 CI 执行机上执行任意代码。

**证据：**
- [.pre-commit-config.yaml:34](file:///e:/work/huawei/fork/openlibing-pre-commit-action/.pre-commit-config.yaml#L34) - `entry: npx prettier --write` 可被替换为任意命令
- [index.js:165](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L165) - `execFile('python', ['-m', 'pre_commit', 'run', ...])` 直接执行 hooks

**修复建议：**
1. 在 CI 中使用 `pull_request_target` 时，限制 `.pre-commit-config.yaml` 的来源（仅使用默认分支配置）
2. 对 local hooks 的 entry 字段进行白名单校验
3. 在容器化环境中运行 pre-commit，限制文件系统和网络访问
4. 考虑使用 `pre-commit run --hook-stage manual` 限制可执行的 hook 类型

---

#### FIND-04: 镜像源完整性校验缺失

**严重性：** Moderate
**CVSS 4.0：** 5.6 (AV:N/AC:L/AT:N/PR:N/UI:N/S:C/C:L/I:L/A:N)
**CWE：** [CWE-494](https://cwe.mitre.org/data/definitions/494.html): Download of Code Without Integrity Check
**OWASP：** A03:2025 – Software Supply Chain Failures
**可利用性分级：** Tier 1
**修复成本：** Medium
**相关威胁：** [T01.T](#actionrunner), [T03.S](#actionrunner)

**描述：**
插件通过 pip 和 go install 安装 pre-commit 及其依赖，但未实施包完整性校验。虽然使用 HTTPS 传输，但 HTTPS 无法防止镜像源本身被入侵。pip 未使用 `--require-hashes` 选项，Go 未使用 `GOSUMDB` 校验。

**证据：**
- [index.js:240](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L240) - `execFile('python', ['-m', 'pip', 'install', 'pre-commit', '--timeout', PIP_TIMEOUT])` 无 `--require-hashes`
- [index.js:223](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L223) - `execFile('go', ['env', '-w', 'GONOSUMDB=*'])` 禁用了 Go sumdb 校验

**修复建议：**
1. 为 pip install 添加 `--require-hashes` 选项并生成 hash 锁定文件
2. 移除 `GONOSUMDB=*` 设置，启用 Go 模块校验
3. 对关键依赖使用固定版本号

---

### 4.2 Tier 2 — 条件风险（认证/单一前置条件）

#### FIND-05: extra_args 参数校验过于宽松

**严重性：** Moderate
**CVSS 4.0：** 5.3 (AV:N/AC:L/AT:N/PR:L/UI:N/S:C/C:L/I:L/A:N)
**CWE：** [CWE-20](https://cwe.mitre.org/data/definitions/20.html): Improper Input Validation
**OWASP：** A05:2025 – Injection
**可利用性分级：** Tier 2
**修复成本：** Low
**相关威胁：** [T02.T](#actionrunner)

**描述：**
`getInput('extra_args')` 的校验逻辑允许任何以 `--` 开头的参数通过。攻击者可传入 `--config`、`--hook-stage` 等未预期的参数，可能影响 pre-commit 的行为。

**证据：**
[index.js:19-33](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L19) - `if (!allowedArgs.includes(arg) && !arg.startsWith('--'))` 允许任何 `--` 前缀参数

**修复建议：**
1. 使用严格白名单，拒绝不在 allowedArgs 中的 `--` 参数
2. 或使用正则校验参数格式，禁止 `--config`、`--hook-stage` 等危险参数

---

#### FIND-06: GC_TOKEN 在环境变量和 URL 中明文存储

**严重性：** Moderate
**CVSS 4.0：** 5.7 (AV:N/AC:L/AT:N/PR:L/UI:N/S:C/C:L/I:L/A:N)
**CWE：** [CWE-312](https://cwe.mitre.org/data/definitions/312.html): Cleartext Storage of Sensitive Information
**OWASP：** A04:2025 – Cryptographic Failures
**可利用性分级：** Tier 2
**修复成本：** Medium
**相关威胁：** [T02.I](#actionrunner), [T02.E](#actionrunner)

**描述：**
GC_TOKEN 通过环境变量 `INPUT_GC_TOKEN` 传递，随后通过 `encodeURIComponent` 编码后嵌入 git remote URL。虽然编码防止了特殊字符问题，但 token 仍以明文形式存在于环境变量、进程列表和 git 配置中。

**证据：**
- [index.js:128](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L128) - `const token = getInput('gc_token')` 从环境变量读取
- [index.js:132](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L132) - `const authUrl = remoteUrl.replace('https://', \`https://oauth2:${encodedToken}@\`)` 嵌入 URL
- [index.js:134](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L134) - `execCapture(\`git remote set-url origin "${authUrl}"\`)` 写入 git 配置

**修复建议：**
1. 使用 `GIT_ASKPASS` 环境变量脚本提供凭据，避免在 URL 中嵌入 token
2. 任务完成后清理环境变量和 git remote URL（恢复为无 token 版本）
3. 使用 `git config --system credential.helper` 管理凭据

---

#### FIND-07: 无审计日志记录 git 操作

**严重性：** Low
**CVSS 4.0：** 3.5 (AV:N/AC:L/AT:N/PR:L/UI:N/S:U/C:N/I:L/A:N)
**CWE：** [CWE-778](https://cwe.mitre.org/data/definitions/778.html): Insufficient Logging
**OWASP：** A09:2025 – Security Logging and Alerting Failures
**可利用性分级：** Tier 2
**修复成本：** Low
**相关威胁：** [T02.R](#actionrunner)

**描述：**
插件执行 `git remote set-url`、`git fetch`、`git diff` 等操作，但未记录操作审计日志。当 GC_TOKEN 被用于修改 remote URL 时，无法追踪操作者和时间。

**证据：**
- [index.js:134](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L134) - git remote set-url 无审计日志
- [index.js:137](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L137) - git fetch 无审计日志

**修复建议：**
1. 在关键 git 操作前后记录审计日志（操作类型、时间戳、操作者）
2. 将审计日志输出到独立的日志通道
3. 记录 GC_TOKEN 使用情况（不记录 token 值本身）

---

#### FIND-08: PR 变更文件数量无上限检查

**严重性：** Low
**CVSS 4.0：** 3.7 (AV:N/AC:L/AT:N/PR:L/UI:N/S:U/C:N/I:N/A:L)
**CWE：** [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling
**OWASP：** A10:2025 – Mishandling of Exceptional Conditions
**可利用性分级：** Tier 2
**修复成本：** Low
**相关威胁：** [T02.D](#actionrunner)

**描述：**
PR 增量检查时，所有变更文件直接传入 `pre-commit run --files`，无文件数量上限。大量文件可能导致命令行参数过长（ARG_MAX 限制）或内存消耗过大。

**证据：**
[index.js:166](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L166) - `execFile('python', ['-m', 'pre_commit', 'run', '--files', ...cmdResult.files])` 无数量限制

**修复建议：**
1. 设置文件数量上限（如 500），超过时分批执行
2. 或使用 `--files-from-file` 选项从文件读取列表
3. 添加超时限制

---

#### FIND-09: PR 评论触发无频率限制

**严重性：** Low
**CVSS 4.0：** 3.1 (AV:N/AC:L/AT:N/PR:L/UI:N/S:U/C:N/I:N/A:L)
**CWE：** [CWE-770](https://cwe.mitre.org/data/definitions/770.html): Allocation of Resources Without Limits or Throttling
**OWASP：** A10:2025 – Mishandling of Exceptional Conditions
**可利用性分级：** Tier 2
**修复成本：** Low
**相关威胁：** [T05.D](#precommitworkflow)

**描述：**
PreCommitWorkflow 支持通过 PR 评论 `/pre-commit` 触发流水线，但无频率限制。攻击者可频繁评论触发流水线，消耗执行机资源。

**证据：**
[.gitcode/workflows/pre-commit.yml:8-12](file:///e:/work/huawei/fork/openlibing-pre-commit-action/.gitcode/workflows/pre-commit.yml#L8) - `pull_request_comment: types: [created] comments: ["/pre-commit"]` 无频率限制

**修复建议：**
1. 在流水线中添加并发限制（concurrency）
2. 记录评论触发频率，超过阈值后拒绝执行
3. 限制同一 PR 的评论触发频率

---

### 4.3 Tier 3 — 纵深防御

#### FIND-10: 工作区路径校验可被路径遍历绕过

**严重性：** Moderate
**CVSS 4.0：** 4.2 (AV:L/AC:L/AT:N/PR:H/S:U/C:L/I:L/A:L)
**CWE：** [CWE-22](https://cwe.mitre.org/data/definitions/22.html): Path Traversal
**OWASP：** A01:2025 – Broken Access Control
**可利用性分级：** Tier 3
**修复成本：** Low
**相关威胁：** [T03.T](#actionrunner)

**描述：**
工作区路径校验使用正则 `/^\/[\w\-\/.]+$/`，允许 `.` 字符，可能允许 `..` 路径遍历。虽然正则要求路径以 `/` 开头，但 `/../etc/passwd` 等路径可匹配正则。

**证据：**
[index.js:247](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L247) - `if (!/^\/[\w\-\/.]+$/.test(workspace))`

**修复建议：**
1. 使用 `path.resolve()` 解析真实路径后校验
2. 禁止 `..` 在路径中出现
3. 校验解析后的路径是否在允许的根目录下

---

#### FIND-11: Node.js 16 已 EOL

**严重性：** Low
**CVSS 4.0：** 3.4 (AV:N/AC:L/AT:N/PR:H/UI:N/S:U/C:L/I:N/A:N)
**CWE：** [CWE-1104](https://cwe.mitre.org/data/definitions/1104.html): Use of Unmaintained Third Party Components
**OWASP：** A03:2025 – Software Supply Chain Failures
**可利用性分级：** Tier 3
**修复成本：** Low
**相关威胁：** [T04.A](#actionmetadata)

**描述：**
action.yml 中 `runs.using` 固定为 "node16"，Node.js 16 已于 2023 年 9 月结束生命周期 (EOL)，不再接收安全更新。

**证据：**
[action.yml:38](file:///e:/work/huawei/fork/openlibing-pre-commit-action/action.yml#L38) - `using: "node16"`

**修复建议：**
1. 升级到 Node.js 20 或更高版本
2. 更新 action.yml 中的 `using` 字段
3. 验证代码与新版 Node.js 的兼容性

---

#### FIND-12: 构建产物无完整性校验

**严重性：** Low
**CVSS 4.0：** 2.7 (AV:L/AC:L/AT:N/PR:H/S:U/C:L/I:L/A:N)
**CWE：** [CWE-494](https://cwe.mitre.org/data/definitions/494.html): Download of Code Without Integrity Check
**OWASP：** A03:2025 – Software Supply Chain Failures
**可利用性分级：** Tier 3
**修复成本：** Low
**相关威胁：** [T07.A](#packagescript)

**描述：**
zip.js 打包 README.md、action.yml、dist/ 为 zip 文件，但未生成哈希校验文件。构建产物在分发前可被篡改而无法被发现。

**证据：**
[zip.js:14-17](file:///e:/work/huawei/fork/openlibing-pre-commit-action/zip.js#L14) - `zip.addLocalFile` 和 `zip.addLocalFolder` 无哈希校验

**修复建议：**
1. 打包后生成 SHA256 校验文件
2. 在发布流程中验证 zip 文件完整性
3. 考虑使用 GPG 签名

---

### 4.4 已缓解的安全控制

#### FIND-13: extra_args 参数白名单校验（已缓解）

**严重性：** Low
**CVSS 4.0：** 2.0 (AV:N/AC:H/AT:N/PR:L/UI:N/S:U/C:L/I:N/A:N)
**CWE：** [CWE-20](https://cwe.mitre.org/data/definitions/20.html): Improper Input Validation
**OWASP：** A05:2025 – Injection
**可利用性分级：** Tier 2
**修复成本：** N/A（已实施）
**相关威胁：** [T02.T](#actionrunner)

**描述：**
插件对 `extra_args` 输入实施了参数白名单校验，限制只允许 `--all`、`--all-files`、`--help`、`--show-diff-on-failure`、`--from-ref`、`--to-ref`、`--files` 等参数，并正确处理带值参数的跳过逻辑。

**证据：**
[index.js:19-33](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L19) - allowedArgs 白名单 + argsWithValue 跳过逻辑

**缓解类型：** 已有控制

---

#### FIND-14: 使用 execFileSync 避免 shell 注入（已缓解）

**严重性：** Low
**CVSS 4.0：** 1.8 (AV:L/AC:H/AT:N/PR:L/UI:N/S:U/C:L/I:N/A:N)
**CWE：** [CWE-78](https://cwe.mitre.org/data/definitions/78.html): OS Command Injection
**OWASP：** A05:2025 – Injection
**可利用性分级：** Tier 2
**修复成本：** N/A（已实施）
**相关威胁：** [T02.T](#actionrunner)

**描述：**
插件在执行 git diff、pre-commit run 等命令时使用 `execFileSync`（非 shell 模式），避免了 shell 命令注入风险。文件名参数直接作为参数数组传递，不经过 shell 解析。

**证据：**
- [index.js:140](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L140) - `execFileSync('git', ['diff', 'FETCH_HEAD', ...])` 非 shell 模式
- [index.js:166](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L166) - `execFile('python', ['-m', 'pre_commit', 'run', '--files', ...])` 非 shell 模式

**缓解类型：** 已有控制

---

#### FIND-15: IP 地址脱敏处理（已缓解）

**严重性：** Low
**CVSS 4.0：** 1.6 (AV:L/AC:H/AT:N/PR:H/UI:N/S:U/C:L/I:N/A:N)
**CWE：** [CWE-200](https://cwe.mitre.org/data/definitions/200.html): Exposure of Sensitive Information
**OWASP：** A04:2025 – Cryptographic Failures
**可利用性分级：** Tier 3
**修复成本：** N/A（已实施）
**相关威胁：** 无直接关联

**描述：**
插件在错误处理中对 IP 地址进行脱敏处理，使用正则将 IP 地址替换为 `[IP_ADDRESS]`，防止 IP 地址泄露到 CI 日志。

**证据：**
[index.js:43](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L43) - `pathStr.replace(/(\d+\.\d+\.\d+\.\d+)/g, '[IP_ADDRESS]')`

**缓解类型：** 已有控制

---

#### FIND-16: curl 测速超时限制（已缓解）

**严重性：** Low
**CVSS 4.0：** 2.0 (AV:N/AC:L/AT:N/PR:H/UI:N/S:U/C:N/I:N/A:L)
**CWE：** [CWE-400](https://cwe.mitre.org/data/definitions/400.html): Uncontrolled Resource Consumption
**OWASP：** A10:2025 – Mishandling of Exceptional Conditions
**可利用性分级：** Tier 3
**修复成本：** N/A（已实施）
**相关威胁：** [T03.D](#actionrunner)

**描述：**
curl 测速命令使用 `--max-time 5` 超时限制，防止因镜像源不可达导致流水线长时间阻塞。

**证据：**
[index.js:69](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L69) - `--max-time ${SPEED_TEST_TIMEOUT}` (5秒)

**缓解类型：** 已有控制

---

#### FIND-17: GC_TOKEN 编码处理（已缓解）

**严重性：** Low
**CVSS 4.0：** 1.8 (AV:L/AC:H/AT:N/PR:L/UI:N/S:U/C:L/I:N/A:N)
**CWE：** [CWE-116](https://cwe.mitre.org/data/definitions/116.html): Improper Encoding or Escaping
**OWASP：** A04:2025 – Cryptographic Failures
**可利用性分级：** Tier 2
**修复成本：** N/A（已实施）
**相关威胁：** [T02.E](#actionrunner)

**描述：**
GC_TOKEN 在嵌入 URL 前使用 `encodeURIComponent` 编码，防止 token 中包含特殊字符（如 `@`、`/` 等）导致 URL 解析异常或命令注入。

**证据：**
[index.js:131](file:///e:/work/huawei/fork/openlibing-pre-commit-action/index.js#L131) - `const encodedToken = encodeURIComponent(token)`

**缓解类型：** 已有控制

---

## 五、威胁覆盖验证

| 威胁 ID | 类别 | 描述 | 状态 | 覆盖 |
|---------|------|------|------|------|
| T01.S | 欺骗 | curl 测速中间人攻击 | Open | ✅ Covered (FIND-01) |
| T01.T | 篡改 | 测速结果篡改引导使用恶意镜像 | Open | ✅ Covered (FIND-01, FIND-04) |
| T01.I | 信息泄露 | 命令日志泄露 GC_TOKEN | Open | ✅ Covered (FIND-02) |
| T01.A | 滥用 | pre-commit hooks 任意代码执行 | Open | ✅ Covered (FIND-03) |
| T02.T | 篡改 | extra_args 校验绕过 | Open | ✅ Covered (FIND-05) |
| T02.T | 篡改 | git diff 文件名注入 | Mitigated | ✅ Mitigated (FIND-14) |
| T02.R | 抵赖 | git 操作无审计日志 | Open | ✅ Covered (FIND-07) |
| T02.I | 信息泄露 | GC_TOKEN 环境变量明文 | Open | ✅ Covered (FIND-06) |
| T02.I | 信息泄露 | git remote URL 输出含 token | Open | ✅ Covered (FIND-02) |
| T02.D | 拒绝服务 | 大量文件导致内存溢出 | Open | ✅ Covered (FIND-08) |
| T02.E | 提权 | GC_TOKEN 推送权限泄露 | Open | ✅ Covered (FIND-06) |
| T03.S | 欺骗 | 恶意 pip 包安装 | Open | ✅ Covered (FIND-04) |
| T03.T | 篡改 | 工作区路径遍历 | Open | ✅ Covered (FIND-10) |
| T03.D | 拒绝服务 | 串行测速累积延迟 | Mitigated | ✅ Mitigated (FIND-16) |
| T04.T | 篡改 | action.yml 描述不符 | Open | ✅ Covered (FIND-05) |
| T04.I | 信息泄露 | gc_token 日志回显 | Open | ✅ Covered (FIND-02) |
| T04.A | 滥用 | Node.js 16 EOL | Open | ✅ Covered (FIND-11) |
| T05.S | 欺骗 | pull_request_target 欺骗 | Mitigated | ✅ Mitigated (FIND-13) |
| T05.I | 信息泄露 | ROBOT_TOKEN 日志泄露 | Mitigated | ✅ Mitigated |
| T05.D | 拒绝服务 | 评论频繁触发 | Open | ✅ Covered (FIND-09) |
| T05.E | 提权 | pr:write 权限滥用 | Mitigated | ✅ Mitigated |
| T05.A | 滥用 | self-hosted 执行机配置篡改 | Open | ✅ Covered (FIND-03) |
| T06.I | 信息泄露 | CodeQL 密钥泄露 | Mitigated | ✅ Mitigated |
| T06.A | 滥用 | CodeQL 报告篡改 | Open | ✅ Covered (FIND-12) |
| T07.T | 篡改 | zip 版本号异常 | Mitigated | ✅ Mitigated |
| T07.A | 滥用 | 构建产物无完整性校验 | Open | ✅ Covered (FIND-12) |
| T08.T | 篡改 | 版本号格式异常 | Mitigated | ✅ Mitigated |

---

## 六、行动摘要

### 快速修复建议 (Quick Wins)

| 发现 | 严重性 | 修复成本 | 描述 |
|------|--------|----------|------|
| FIND-02 | Important | Low | 在 exec/execCapture 中过滤 token，避免日志泄露 |
| FIND-05 | Moderate | Low | 收紧 extra_args 白名单，拒绝非预期参数 |
| FIND-07 | Low | Low | 添加 git 操作审计日志 |
| FIND-08 | Low | Low | 设置 PR 文件数量上限 |
| FIND-09 | Low | Low | 添加 PR 评论触发频率限制 |
| FIND-10 | Moderate | Low | 使用 path.resolve() 校验工作区路径 |
| FIND-11 | Low | Low | 升级 Node.js 版本到 20+ |
| FIND-12 | Low | Low | 打包后生成 SHA256 校验文件 |

### 优先修复顺序

1. **FIND-02** — 日志泄露 GC_TOKEN（Tier 1, Important, Low effort）
2. **FIND-03** — pre-commit hooks 任意代码执行（Tier 1, Important, Medium effort）
3. **FIND-01** — curl 测速 TLS 证书验证（Tier 1, Important, Low effort）
4. **FIND-04** — 镜像源完整性校验（Tier 1, Moderate, Medium effort）
5. **FIND-06** — GC_TOKEN 明文存储（Tier 2, Moderate, Medium effort）
6. **FIND-05** — extra_args 校验收紧（Tier 2, Moderate, Low effort）
7. **FIND-10** — 路径遍历修复（Tier 3, Moderate, Low effort）
8. 其余 Low 级发现按优先级排列

---

## 七、分析上下文与假设

### 需要验证的假设

| 编号 | 假设 | 需要验证 |
|------|------|----------|
| A1 | CI 执行机环境已预装 Python 和 pip | 检查执行机镜像配置 |
| A2 | GitCode CI 平台在任务完成后清理环境变量 | 检查 CI 平台文档 |
| A3 | .pre-commit-config.yaml 来自仓库默认分支（pull_request_target） | 验证 CI 检出策略 |
| A4 | self-hosted 执行机有物理安全控制 | 检查执行机管理规范 |

### 发现覆盖说明

| 发现 | 说明 |
|------|------|
| FIND-13 | extra_args 白名单已实施但仍有改进空间（FIND-05） |
| FIND-14 | execFileSync 已避免 shell 注入，但 exec/execCapture 仍使用 /bin/bash |
| FIND-15 | IP 脱敏仅覆盖错误消息，未覆盖 console.log 输出 |
| FIND-16 | curl 超时已限制单次测速，但未限制总测速次数 |
| FIND-17 | token 编码已实施，但 token 仍在 URL 和环境变量中明文存在 |

---

## 八、参考资源

### 安全标准

| 标准 | 版本 | URL |
|------|------|-----|
| OWASP Top 10 | 2025 | https://owasp.org/Top10/2025/ |
| STRIDE 威胁建模 | - | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling |
| CVSS 4.0 | 4.0 | https://www.first.org/cvss/v4.0/ |
| CWE | - | https://cwe.mitre.org/ |

### 组件文档

| 文档 | 版本 | URL |
|------|------|-----|
| pre-commit | - | https://pre-commit.com/ |
| Node.js 16 | 16 | https://nodejs.org/en/blog/announcements/nodejs16-eol |
| GitCode Actions | - | https://gitcode.com/docs/actions |
| npm ncc | 0.38.1 | https://github.com/vercel/ncc |

---

## 九、仓库结构

| 路径 | 用途 |
|------|------|
| index.js | 核心逻辑源码 |
| dist/index.js | webpack 编译产物（运行时入口） |
| action.yml | 插件元数据（输入/输出定义） |
| .pre-commit-config.yaml | 项目自身的 pre-commit 配置 |
| .gitcode/workflows/ | CI/CD 流水线定义 |
| zip.js | 打包脚本 |
| bump-version.js | 版本自增脚本 |
| package.json | npm 依赖和构建脚本 |
| README.md | 用户文档 |
