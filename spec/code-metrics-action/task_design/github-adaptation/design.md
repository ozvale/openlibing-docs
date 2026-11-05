# 代码度量指标插件支持 GitHub · 设计文档

> 配套页面原型：[prototype.html](./prototype.html)（浏览器打开查看目标态交互：GitHub/GitCode Summary、openLiBing 代码仓管理页指标展示、OBS 桶视图）。

## 1. 方案设计

### 1.1 总体方案

采用**单份代码、运行时识别平台**的方案，不维护 GitHub 专用分支：

- 入口按环境变量识别运行平台（GitHub / GitCode）；
- 平台判定一次完成，之后只读取该平台的环境变量，不跨平台混用；
- 认证、结果展示按平台选择适配实现；
- 扫描算法、指标口径、上报协议保持不变。

### 1.2 平台识别与上下文映射

平台判定：`GITHUB_ACTIONS=true` 即为 GitHub Actions，其余一律按 GitCode Actions 处理；判定结果在进程启动时固化，后续只读取对应平台的变量。

| 上下文      | GitHub                                    | GitCode                     |
| ----------- | ----------------------------------------- | --------------------------- |
| 平台判定    | `GITHUB_ACTIONS=true`                     | 无该标志                    |
| 仓库地址    | `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` | `git remote get-url origin` |
| 当前分支    | `GITHUB_REF_NAME`                         | `ATOMGIT_REF_NAME`          |
| PR 目标分支 | `GITHUB_BASE_REF`                         | `ATOMGIT_BASE_REF`          |
| 运行 ID     | `GITHUB_RUN_ID`                           | `ATOMGIT_RUN_ID`            |
| 运行编号    | `GITHUB_RUN_NUMBER`                       | `ATOMGIT_RUN_NUMBER`        |
| 提交 SHA    | `GITHUB_SHA`                              | `ATOMGIT_SHA`               |
| 工作流名称  | `GITHUB_WORKFLOW`                         | `ATOMGIT_WORKFLOW`          |
| 工作区      | `GITHUB_WORKSPACE`                        | `ATOMGIT_WORKSPACE`         |

分支优先取本地 git 信息（`git remote` / `git rev-parse`），失败或 detached HEAD 时回退上表 CI 上下文；PR 事件统一按**目标分支**归属数据。注意 GitCode 的 `ATOMGIT_HEAD_REF` 语义为 PR **源分支**（对应 `GITHUB_HEAD_REF`），目标分支必须取 `ATOMGIT_BASE_REF`，两者不可混用。

### 1.3 认证方案

| 模式            | 触发条件                              | 说明                                                                                                                                                                                  |
| --------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OIDC（推荐）    | 存在 `ACTIONS_ID_TOKEN_REQUEST_URL`   | 申请 OIDC ID Token → 华为云 STS 换临时凭证；GitHub 平台需同时将身份提供商切换为 `GitHubActions`、信任委托切换为 `github-actions`（SDK 默认值为 `GitCodeActions` / `gitcode-actions`） |
| AK/SK（已废弃） | 未声明 `id-token: write` 且传入 AK/SK | 保留兼容，仅在测试仓临时验证使用；README 不再对外说明                                                                                                                                 |

OIDC 下 APIG 走 `/action-api` 前缀，AK/SK 下走 `/openlibing-coderepo` 前缀，两条链路的上报报文一致。

### 1.4 结果展示方案

| 通道       | GitHub                       | GitCode                                |
| ---------- | ---------------------------- | -------------------------------------- |
| 富文本摘要 | `GITHUB_STEP_SUMMARY`        | `ATOMGIT_STEP_SUMMARY`                 |
| 输出面板   | 无对应能力                   | `ATOMGIT_OUTPUT`（保持原有键值对输出） |
| 步骤输出   | `core.setOutput`（5 项指标） | 同左（无副作用）                       |

摘要统一为 Markdown 表格：扫描信息表（仓库/分支/提交/流水线/完成时间）、指标概览表（5 项指标及说明）、平台详情链接。GitHub 没有输出面板，富文本展示只能依赖 summary，因此两平台统一使用 summary 承载主要展示。

### 1.5 依赖精简

| 依赖                      | 处理                   | 依据                                                                                                     |
| ------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------- |
| `config-file` + `js-yaml` | 移除                   | 无真实使用；唯一作用是关闭检测器，无实际诉求；`uploader.*` 会被代码覆盖，`threshold`/`parallel` 为死配置 |
| `winston`                 | 替换为 `@actions/core` | 仅做控制台输出，无多 transport/轮转能力；`@actions/core` 已是现有依赖，日志级别与平台一致                |

### 1.6 兼容性策略

- GitCode 场景只读取 `ATOMGIT_*` 变量并保留 `ATOMGIT_OUTPUT` 输出，存量工作流无需修改；
- 移除旧配置 `PIPELINE_RUN_ID` / `PIPELINE_RUN_NUMBER` 兼容，运行信息统一取自平台标准变量；
- `action.yml` 保持 `runs.using: node16` 与 GitCode 专属元数据：GitCode runner 仅支持 node16；GitHub 会将 node16 动作强制按 node20 运行。Node 16 已于 2023-09 结束官方支持、不再获得安全修复，而本插件直接处理外部仓库不可信内容并持有 OBS 临时凭证；迁移条件为 GitCode runner 支持 node20 后立即升级，在此之前将 node16 视为已知风险并纳入依赖/运行时升级跟踪，不作为长期正确配置；
- AK/SK 入参保留，避免存量脚本立即失效；README 只描述 OIDC；
- 上报接口与对象 key 规则不变；OBS 桶按平台隔离（GitCode 为 `openlibing-gitcode-action`，GitHub 为 `openlibing-github-action`），后端下载白名单需支持 GitHub 桶；

## 2. 实现逻辑设计

### 2.1 主流程

1. 解析 action 输入（排除目录、扩展名、重复行阈值、输出文件、认证参数）；
2. 识别平台并解析仓库、分支、提交、运行信息；
3. 执行扫描：`scc`（代码规模）、`lizard`（函数级指标）、内置重复检测；
4. 组装上报数据并上传 OBS（全量明细）；
5. 调用 `/metrics/code/report`（仅元数据 + OBS 链接）；
6. 输出 5 项指标到 step outputs；
7. GitCode 写 `ATOMGIT_OUTPUT` 输出面板；
8. 两平台写运行摘要表格；
9. 输出平台详情链接或提示。

### 2.2 上下文解析顺序

- 仓库地址：`git remote get-url origin`（剥离 URL 内嵌凭证）→ 平台环境变量兜底；
- 分支：`git rev-parse --abbrev-ref HEAD` → detached HEAD 时取 tag → CI 上下文（PR 取目标分支）；
- 运行信息：按已判定平台读取 `GITHUB_*` 或 `ATOMGIT_*`（旧配置 `PIPELINE_*` 已移除）。

### 2.3 扫描与上报

- 扫描逻辑与 GitCode 场景完全一致，不引入平台分支；
- OBS 上传：按平台选择桶（GitCode: `openlibing-gitcode-action`，GitHub: `openlibing-github-action`），对象 key 统一为 `code-metrics-action/{owner}/{repo}/{pipelineRunId}/{时间戳}-metrics.json`，私有对象，不设置 ACL；
- 上报：OBS 上传成功后再调用一次 report 接口，避免 APIG 12MB 请求体上限；
- 上报失败时 OBS 文件保留，可由平台保底任务按 objectKey 补导入。

### 2.4 异常与降级

| 场景                           | 处理                                                                                                                                                                                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 未识别到 `lizard`/pip 安装失败 | 记录 error 日志，函数级指标置 0，不中断扫描；**已知限制**：0 值与真实优秀值不可区分且 `status` 仍为成功，属于以成功状态写入缺失数据。后续需引入可区分的降级语义（`status` 新增枚举或 `errorMessage` 标注缺失项，并在摘要中提示），避免缺失值被当作真实指标入库 |
| OBS 上传失败                   | 直接返回失败，提示可重跑                                                                                                                                                                                                                                       |
| report 接口失败                | 输出 OBS 链接与补导入提示，不影响已上传数据                                                                                                                                                                                                                    |
| 摘要/输出面板写入失败          | 仅告警降级，不影响扫描与上报结果                                                                                                                                                                                                                               |
| AK/SK 缺失且未启用 OIDC        | 返回明确失败原因，提示声明 `id-token: write`                                                                                                                                                                                                                   |

## 3. 类设计

| 模块                                | 职责                                                    | 本次变化                                            |
| ----------------------------------- | ------------------------------------------------------- | --------------------------------------------------- |
| `src/index.js`                      | Action 入口：输入解析、上下文解析、扫描调度、输出与摘要 | 新增平台上下文解析、摘要构建与双通道写入            |
| `src/config/loader.js`              | 内置默认配置                                            | 移除文件加载/深合并，仅保留默认值                   |
| `src/utils/logger.js`               | 日志封装                                                | winston → `@actions/core`                           |
| `src/scanner.js`                    | 扫描编排、结果落盘、上报调用                            | 仅适配无参 Logger                                   |
| `src/uploaders/CoderepoUploader.js` | 认证模式选择、OBS 上传、APIG 上报                       | 新增 GitHub OIDC provider / 委托切换与平台化 OBS 桶 |
| `src/detectors/*`                   | scc / lizard / 重复检测                                 | 无变化                                              |

## 4. 数据模型设计

### 4.1 report 接口报文（HTTP）

| 字段                                          | 类型   | 说明                    |
| --------------------------------------------- | ------ | ----------------------- |
| `gitUrl`                                      | string | 仓库地址（不含 `.git`） |
| `branchName`                                  | string | 分支（PR 为目标分支）   |
| `pipelineRunId`                               | string | 流水线运行 ID           |
| `commitId`                                    | string | 提交 SHA                |
| `runNumber`                                   | string | 运行编号                |
| `detectionStartedAt` / `detectionCompletedAt` | string | 扫描开始/完成时间       |
| `status`                                      | number | 扫描状态                |
| `obsUrl`                                      | string | 全量明细下载链接        |
| `errorMessage`                                | string | 失败原因（可选）        |

### 4.2 OBS 全量明细

桶按平台选择：GitCode 使用 `openlibing-gitcode-action`，GitHub 使用 `openlibing-github-action`；两平台对象 key 结构一致，均为 `code-metrics-action/` 前缀。

在 4.1 基础上追加：

| 字段                     | 说明                         |
| ------------------------ | ---------------------------- |
| `pipelineName`           | 工作流名称，供下钻页展示来源 |
| `metricsData`            | 5 项总体指标                 |
| `fileDetails`            | 文件级指标明细               |
| `identicalFileDetails`   | 完全一致文件分组             |
| `duplicationOccurrences` | 重复代码块位置（编码后）     |

### 4.3 摘要上下文

仓库、分支、提交（前 8 位）、流水线（编号 + 运行链接）、扫描完成时间（UTC+8）、平台详情链接。

## 5. 性能设计

- **产物体积**：移除 winston/js-yaml 后 `dist/index.js` 由约 2784KB 降至 2271KB（-513KB），减少下载与冷启动开销；
- **请求次数**：全量明细走 OBS，report 接口仅一次轻量调用，报文恒定极小；
- **超时控制**：上报 HTTP 超时 60s；OIDC/STS 由 SDK 内部缓存与并发去重，单次流水线只换证一次；
- **并发控制**：GitHub 示例工作流提供可选 `concurrency`，同分支仅保留最新一次扫描；
- **资源清理**：OBS 上传后删除 runner 临时文件；pip 依赖安装在独立临时目录并清理。

## 6. API 接口设计

| 项       | OIDC 模式                                                   | AK/SK 模式（已废弃）                            |
| -------- | ----------------------------------------------------------- | ----------------------------------------------- |
| 路径前缀 | `/action-api`                                               | `/openlibing-coderepo`                          |
| 上报接口 | `POST /action-api/metrics/code/report`                      | `POST /openlibing-coderepo/metrics/code/report` |
| 认证     | OIDC → STS 临时凭证 + V11 签名                              | APIG AppKey/AppSecret 签名                      |
| 网关     | `https://apig.openlibing.com:443`                           | 同左                                            |
| 响应     | `DataResult`：`code`/`message`/`data.detailLink`/`data.tip` | 同左                                            |

## 7. 安全设计

1. **免密优先**：OIDC 申请短期凭证，仓库不落任何长期密钥；AK/SK 仅作兼容通道，不再对外宣传；
2. **信任边界**：华为云 IAM 侧按平台注册 `GitHubActions` 身份提供商，信任策略通过 `iss/aud/sub` 限定到具体组织/仓库/分支；需兼容 GitHub 名称格式与不可变 ID 格式的 `sub`；
3. **对象存储**：OBS 全量明细为私有对象，不设置公开读 ACL，后端按 objectKey 以平台凭证下载；
4. **输出注入防护**：摘要表格单元格转义 `|` 并压平换行，防止 Markdown 表格被用户可控字段（分支名、仓库地址等）破坏；
5. **日志脱敏**：仓库地址、分支名等外部可控字段写入日志前做净化；不上送任何凭证；
6. **凭证传递**：OBS 凭证仅在进程内存中传递，不经命令行参数，避免同机进程读取；
7. **输入边界**：未识别的平台/缺失关键上下文时给出明确失败提示，不静默使用错误默认值。
