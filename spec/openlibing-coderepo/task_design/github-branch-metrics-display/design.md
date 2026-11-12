# 分支管理页 GitHub 度量结果展示适配（github-branch-metrics-display） · 设计文档

> 所属 FE：代码度量指标支持 GitHub 仓库扫描与展示（[Issue #74](https://gitcode.com/openlibing/code-metrics-action/issues/74)）。
> 配套设计：code-metrics-action GitHub 适配（插件侧平台识别、OIDC、结果摘要、OBS 桶隔离）。本 US 承接平台侧（openlibing-coderepo）的接收与展示链路。

## 1. 方案设计

### 1.1 背景与问题

GitHub 仓库接入 openLiBing 后，插件侧 US 已完成 `code-metrics-action` 的 GitHub 适配：GitHub Actions 中按 `GITHUB_ACTIONS` 识别平台、使用 `GitHubActions` 身份提供商完成 OIDC 换证、扫描结果上传到按平台隔离的 OBS 桶 `openlibing-github-action`（GitCode 仍为 `openlibing-gitcode-action`），report 报文与对象 key 规则保持不变。

openlibing-coderepo 侧接收链路未同步适配：

- `ObsBucketService#downloadToTempFile` 的下载白名单仅允许 `openlibing-gitcode-action`；
- GitHub 上报的 `obsUrl`（形如 `https://openlibing-github-action.obs.{region}.myhuaweicloud.com/code-metrics-action/...`）在解析桶名后被判定为非法，抛出 `IllegalArgumentException`；
- `reportMetrics` 随即落一条失败记录并返回失败，`code_metrics_record` 无成功记录；
- `refreshBranchMetricsSnapshot` 不执行，`repo_branch` 的 5 个度量快照列保持空值；
- 「代码仓管理 → 分支管理」页对 GitHub 分支的 5 项代码度量全部显示 `--`。

页面渲染、仓库归属解析、详情下钻均与平台无关（见 2.3），因此唯一阻断点是 OBS 下载白名单。

### 1.2 需求目标

1. GitHub 仓库在「代码仓管理 → 分支管理」页正常展示 5 项代码度量：代码规模、平均代码行数、平均圈复杂度、总代码重复率、总文件重复率；
2. 指标口径、展示形态与 GitCode / Gitee 仓库一致，无值仍展示 `--`；
3. 指标详情下钻、流水线链接跳转可用；
4. GitHub 上报链路端到端打通：GitHub Actions 扫描 → OBS（平台桶）→ `/metrics/code/report` → 异步入库 → 分支快照 → 页面；
5. GitCode / Gitee 存量上报、展示、UT 覆盖率链路无回归。

**不在本 US 范围**：

- 插件侧平台识别、OIDC 换证、运行摘要（由 `code-metrics-action` US 承接）；
- 前端页面改造（分支管理页读取统一 VO，无平台分支，零改动）；
- GitHub PR 增量门禁、趋势看板；
- 存量数据回填（GitHub 历史扫描数据不存在，首轮扫描后自然产生）。

### 1.3 总体方案

保持“OBS 桶按 CI 平台隔离”的既有方案，仅将后端下载白名单由单桶扩展为双桶：

- 允许桶：由 Nacos 配置项 `obs.action.buckets` 决定，当前值为 `openlibing-gitcode-action`、`openlibing-github-action`；
- 允许对象前缀保持不变：`code-metrics-action/`、`ut-coverage-action/`；
- 下载大小上限保持不变：`obs.download.max-size-mb`（默认 500MB）；
- 校验方式由“单桶等值判断”改为“配置集合包含判断”，其余 URL 解析、流式下载、临时文件清理逻辑不变；
- 不新增平台字段、不新增平台判断、不新增接口、不改表结构。

### 1.4 设计取舍

| 议题                                        | 选择               | 理由                                                                                                                                                                |
| ------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 是否将 GitHub 对象并入 GitCode 桶           | 否，保持双桶隔离   | 桶隔离是插件侧既定方案，GitHub 与 GitCode 的 OIDC 委托、桶策略、配额相互独立；后端兼容成本仅为一个白名单集合                                                        |
| 是否把桶名改为配置项                        | 是（实现阶段调整） | 原设计为固定常量，考虑配置漂移与可读桶范围扩大风险；按项目规范化要求改为 Nacos 配置项 `obs.action.buckets`，配置变更需走发布/安全评审并留审计，对象前缀仍为代码常量 |
| 是否新增平台字段或按平台走不同下载逻辑      | 否                 | 桶名即平台边界，下载/解析/入库链路无需感知平台                                                                                                                      |
| 是否放宽前缀或大小限制                      | 否                 | 本次只扩桶，不改变既有校验规则（桶 + 前缀 + 大小上限）；可读对象集合随桶扩展而扩大，跨仓库读取边界见 §7                                                             |
| 是否新增 objectKey 与 gitUrl 的归属绑定校验 | 本次不新增         | 改动范围限定为白名单扩桶；现有链路不解析 objectKey 中的 `{owner}/{repo}`，该暴露面作为已知边界在 §7 说明，后续单独加固                                              |
| 是否新增独立 MQ 队列                        | 否                 | GitHub 上报复用 `code_metrics_import_queue`，消费并发与重试策略不变                                                                                                 |

### 1.5 兼容性与前置依赖

- **GitCode 回归**：既有 `openlibing-gitcode-action` 对象、上报报文、入库与展示路径完全不变；
- **UT 覆盖率**：`ut-coverage-action/` 前缀对两个桶同样生效，后续 `upload-ut-action` 支持 GitHub 时后端无需再改；
- **前端零改动**：分支管理页读取统一 `BranchMetricsVO`，按值判空展示 `--`，无平台分支；
- **OBS 权限前置**：后端使用的 OBS 凭证需对 `openlibing-github-action` 具备 GetObject 权限，且该桶与 `obs.endpoint` 同区域；未授权时下载失败会落失败记录并返回明确错误，不会静默成功；
- **网关前置**：GitHub OIDC 身份提供商与信任委托由运维侧配置，不在本 US 代码范围。

## 2. 实现逻辑设计

### 2.1 上报与展示主链路

1. 插件扫描完成后，将全量明细上传到平台对应 OBS 桶，再调用 `POST /metrics/code/report`，请求仅携带归属元数据与 `obsUrl`；
2. `CodeMetricsController#reportMetrics` 校验请求后投递 MQ `code_metrics_import_queue`，HTTP 线程不做重活；
3. `CodeMetricsImportConsumer` 以 2~4 并发消费，失败按 1s / 5s / 15s 退避重试，最多 3 次，超限记录错误日志并 ACK 丢弃；
4. `CodeMetricsServiceImpl#reportMetrics` 调用 `ObsBucketService#downloadToTempFile(obsUrl)` 流式下载到本地临时文件；
5. 四遍流式解析 OBS 文件，幂等清理同 `gitUrl + branchName + pipelineRunId` 旧记录后落主记录与明细；
6. 主记录入库成功后调用 `refreshBranchMetricsSnapshot`，将最新成功扫描的 5 项指标刷入 `repo_branch` 快照列（失败仅告警，不阻断上报）；
7. 分支管理页查询时直接带出快照列，构建 `BranchMetricsVO`；无值项为 `null`，前端展示 `--`。

本次改动只影响第 4 步的桶名校验，其余步骤均无变更。

### 2.2 OBS 下载校验（本次改动）

`downloadToTempFile` 处理流程：

1. 解析 `obsUrl`，取 host 首个 label 作为桶名（`{bucket}.obs.{region}.myhuaweicloud.com`），取 URL path 去掉首个 `/` 作为 objectKey；
2. 桶名校验：`allowedMetricsObsBuckets.contains(bucketName)`，集合来自 Nacos 配置项 `obs.action.buckets`（当前包含 GitCode 与 GitHub 两个平台桶）；
3. 对象前缀校验：objectKey 必须以 `code-metrics-action/` 或 `ut-coverage-action/` 开头；
4. 通过后使用服务端凭证 `getObject(bucketName, objectKey)`；
5. 元数据标称大小超过上限时直接拒绝、不落盘；
6. 流式复制（8KB 缓冲）并按实际字节数计数，超过上限立即中止并清理临时文件；
7. 返回临时文件路径，调用方用后删除。

核心配置：

```java
// 代码度量 OBS 下载桶白名单：由 Nacos 配置项 obs.action.buckets 决定（逗号分隔），
// 当前值 openlibing-gitcode-action,openlibing-github-action；类上 @RefreshScope 支持热刷新
@Value("${obs.action.buckets}")
private List<String> allowedMetricsObsBuckets;
```

校验条件由单桶等值判断改为配置集合包含判断；配置缺失时首次调用 fail-fast，对象前缀与下载大小上限校验不变。

注意：上述校验只约束“桶名 + 对象前缀”，不校验 objectKey 中的 `{owner}/{repo}` 与本次上报 `gitUrl` 的仓库归属是否一致；该边界与加固建议见 §7。

### 2.3 分支管理页展示（无改动）

- **仓库归属**：`RepoUrlParser` 已支持 GitHub 标准两层路径（`/owner/repo`），`RepoCoordinateResolverImpl` 采用“精确匹配 + 平台坐标兜底（`platform=github`）”，GitHub 的 `gitUrl` 可正常反查 `repo_info`；PR 事件按插件上报的目标分支归属；
- **指标来源**：`repo_branch` 的 `code_scale`、`avg_function_loc`、`avg_cyclomatic_complexity`、`total_code_duplication_rate`、`total_file_duplication_rate` 快照列；
- **详情下钻**：前端不传 `pipelineRunId`，后端 `locateMetricsRecord` 兜底该分支最新一次成功记录，与快照同源；
- **流水线链接**：`buildPipelineLink` 使用 `git_url` 去 `.git` 后拼接 `/actions/runs/{pipelineRunId}`，GitHub Actions 的 URL 规则一致，无需平台分支；
- **前端渲染**：`branches.vue` 直接读取 `metrics[col.prop].value`，无 GitCode/GitHub 分支逻辑。

### 2.4 保底导入

XxlJob `codeMetricsObsImportHandler` 通过入参 `obsUrl` 调用 `importMetricsFromObsFile`，复用同一套下载与解析链路，因此 GitHub 桶 URL 同样可补导入，无需改动。

### 2.5 异常与降级

| 场景                          | 处理                                                                                            | 页面表现                             |
| ----------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------ |
| GitHub 桶不存在或凭证无读权限 | 下载返回 `empty`，`reportMetrics` 抛 `IllegalArgumentException`，落失败记录（含原因）并返回失败 | 保持上次成功快照；从未成功则为 `--`  |
| 对象不存在、网络异常          | 同上，记录 error 日志                                                                           | 同上                                 |
| 桶名或对象前缀不在白名单      | 直接抛 `IllegalArgumentException`，拒绝下载                                                     | 同上                                 |
| 元数据或实际流量超过大小上限  | 拒绝下载并清理临时文件                                                                          | 同上                                 |
| 主记录入库成功但快照刷新失败  | 仅 warn，不阻断上报成功；快照保持上次值                                                         | 指标可能延迟到下次成功扫描或刷数任务 |
| MQ 重试耗尽                   | 记录错误日志并 ACK 丢弃，避免毒消息阻塞队列                                                     | 同上                                 |

### 2.6 验证方式

- **单元测试**：`ObsBucketServiceImplTest` 新增 GitHub 桶下载成功用例；既有 GitCode 桶成功、其他桶拒绝、非法前缀拒绝、元数据超限、流量超限用例保持通过；
- **端到端**：GitHub 工作流上报后，确认 `code_metrics_record` 有成功记录、`repo_branch` 快照列刷新、分支管理页 5 项指标正常展示、详情下钻与流水线链接可跳转；
- **回归**：GitCode 存量工作流上报、UT 覆盖率上报与展示不受影响；
- **异常验证**：使用非白名单桶 URL 与超大对象验证拒绝语义与失败记录。

## 3. 类设计

| 类                                                                         | 变更                                                                                                                                                                                                            |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ObsBucketServiceImpl`                                                     | 移除单桶常量白名单判断，桶集合改为 Nacos 配置项 `obs.action.buckets`（`@Value` + `@RefreshScope`）；`downloadToTempFile` 桶名校验改为配置集合包含判断；URL 解析、前缀校验、大小限制、流式复制、临时文件清理不变 |
| `ObsBucketService`                                                         | 接口签名不变；`downloadToTempFile` 契约注释同步为桶名由 `obs.action.buckets` 配置决定（当前含 GitCode 与 GitHub 两个平台桶）                                                                                    |
| `ObsBucketServiceImplTest`                                                 | 新增 `downloadToTempFile_GithubBucket_Success`；单测注入两个平台桶，既有用例保持不变                                                                                                                            |
| `CodeMetricsReportDTO` / `UtCoverageReportDTO` / `XxlJobHandler`           | 桶名表述注释同步为配置化口径（commit `df377791`），无逻辑变更                                                                                                                                                   |
| `CodeMetricsServiceImpl` / `CodeMetricsImportConsumer` / `RepoServiceImpl` | 无改动                                                                                                                                                                                                          |

## 4. 数据模型设计

### 4.1 数据库

无 DDL、无索引、无字段变更。`code_metrics_record`、文件明细、重复块明细、`repo_branch` 快照列结构均保持不变。

### 4.2 OBS 对象模型

| 平台    | 桶                          | 允许前缀                                      | 对象 key                                                                      |
| ------- | --------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------- |
| GitCode | `openlibing-gitcode-action` | `code-metrics-action/`、`ut-coverage-action/` | `code-metrics-action/{owner}/{repo}/{pipelineRunId}/{timestamp}-metrics.json` |
| GitHub  | `openlibing-github-action`  | 同上                                          | 同上                                                                          |

两平台对象内容结构、上报报文结构完全一致，仅桶不同。

### 4.3 归属与展示映射

| 展示项       | 数据来源                       | 说明                                               |
| ------------ | ------------------------------ | -------------------------------------------------- |
| 5 项分支指标 | `repo_branch` 快照列           | 由最新一次成功扫描刷新，无值为 `null`              |
| 指标详情     | `code_metrics_record` + 明细表 | 按 `gitUrl + branchName` 兜底最新成功记录          |
| 流水线链接   | `git_url` + `pipelineRunId`    | GitHub 与 GitCode 的 `/actions/runs/{id}` 规则一致 |

## 5. 性能设计

- 桶名校验由一次字符串相等判断变为按配置集合做包含判断（当前集合两个元素），耗时可忽略；
- 不新增数据库查询、不新增 OBS 请求；下载仍为单次 `getObject` + 8KB 缓冲流式复制，不整体读入内存；
- 下载上限沿用 `obs.download.max-size-mb`（默认 500MB），配置中心可调，`@RefreshScope` 生效；
- GitHub 上报复用现有 MQ 队列与 2~4 并发消费，不新增线程池与队列；
- 分支管理页查询仍为单条分页 SQL 直接带出快照列，无额外查询与内存排序。

## 6. API 接口设计

无新增或修改的 HTTP 接口，请求/响应结构均不变。

| 接口                                                                                        | 变更                                                                                                            |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `POST /metrics/code/report`                                                                 | 无结构变更；`obsUrl` 允许 GitHub 平台桶，格式仍为 `https://{bucket}.obs.{region}.myhuaweicloud.com/{objectKey}` |
| `POST /metrics/code/file-detail`、`/file-content`、`/duplication-block/detail`              | 无变更                                                                                                          |
| 分支列表 `/repo/branch/list`、`/project-repo/query-repo-branch`、`/repo/branch/filter-meta` | 无变更；GitHub 仓库的 `metrics` 值由空变为可用                                                                  |
| XxlJob `codeMetricsObsImportHandler`                                                        | 入参 `obsUrl` 支持 GitHub 桶                                                                                    |

错误语义不变：非白名单桶、非法前缀、超限均返回业务失败并记录原因，不改为静默成功。

## 7. 安全设计

- **白名单收敛**：允许桶由 Nacos 配置项 `obs.action.buckets` 决定（当前仅两个平台桶），对象前缀仍为代码常量；配置变更需走发布/安全评审并留审计，不接受任意桶或任意对象；
- **读取范围约束**：桶名取自 URL host、objectKey 取自 URL path，仅允许配置集合内的桶与两个固定前缀，白名单之外一律拒绝。该校验只能约束“桶 + 前缀”，不能证明 objectKey 的 `{owner}/{repo}` 与本次上报 `gitUrl` 属于同一仓库；
- **已知边界（本次扩桶带来的暴露面）**：`/metrics/code/report` 与 XxlJob `codeMetricsObsImportHandler` 当前均未校验 objectKey 的 `{owner}/{repo}` 与 `gitUrl` 的仓库归属一致性。白名单由单桶扩为双桶后，GitHub 桶内符合前缀的对象由此前不可读变为可读；能够调用上报接口的调用方，理论上可提交“自己的 `gitUrl` + 他人仓库的 `obsUrl`”下载他人仓库的度量明细（含重复代码片段）并入库。`/metrics/code/report` 为机机接口、需通过 APIG 认证，但认证不等于仓级授权，不能消除该风险；`codeMetricsObsImportHandler` 为内部运维任务，不作为对外接口；
- **后续加固建议**：在下载前解析 objectKey 的 `{owner}/{repo}`，与上报 `gitUrl` 的平台坐标比对，不一致直接拒绝；补导入任务限定内部运维使用。该归属绑定校验不在本次改动范围，落地前安全评审应按“可读对象集合扩大”评估，不能认为越权面未变化；
- **大小上限**：元数据预检 + 实际流量计数双重限制，超限中止并清理临时文件，防止磁盘/内存耗尽；
- **凭证安全**：AK/SK 为加密配置，运行时经 `SecurityUtil` 解密，不写入日志；错误日志只包含 `obsUrl`、桶名与异常信息；
- **临时文件**：系统临时目录、唯一前缀 `code-metrics-`，调用方用后删除，异常路径同样清理；
- **最小权限**：后端 OBS 凭证对两个桶仅需 GetObject 权限，不需要 List/Put/Delete；
- **变更控制**：新增桶需走安全评审并更新 `obs.action.buckets` 配置（当前支持双平台桶）；对象前缀变更需走代码评审；配置变更应纳入审计与最小权限控制，禁止在运行时无评审放行。
