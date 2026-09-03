# code-metrics-scan 插件需求设计文档

> FE 需求：【openlibing】GitCode插件流水线交互适配OIDC认证方案
> 适用插件：openlibing-code-metrics-action（code-metrics-scan，代码度量扫描）
> 涉及仓库：openlibing/code-metrics-action（发布仓）、openlibing/code-metrics-scan（插件源码仓，`.gitcode/actions/code-metrics-scan`）
> SDK：`@openlibing/huaweicloud-oidc-client@0.0.5`
> 说明：本插件与 sec-option-scan 插件同属本次 OIDC 认证改造，认证链路、信任委托等通用部分与《sec-option-scan 插件需求设计文档》一致，本文不重复展开，仅描述插件特有设计。

## 1. 方案设计

### 1.1 背景与现状

code-metrics-scan 插件在 GitCode 流水线中扫描代码仓的 5 项度量指标（代码规模、平均函数代码行数、平均圈复杂度、代码重复率、文件重复率），上报到 openlibing-coderepo 服务（经 APIG 网关，`https://apig.openlibing.com`）。

当前业务状态：插件上报需要四个静态凭证输入——APIG App 认证（`apig-app-key` / `apig-app-secret`）+ OBS 访问密钥（`obs-ak` / `obs-sk`，复用 upload-sarif-action 同一套）。OBS 上传走 obsutil 命令行工具，命令行参数直传 AK/SK。存在与 sec-option-scan 相同的长期静态凭证管理问题，且凭证数量更多（4 个）、暴露面更大（obsutil 进程参数携带 AK/SK）。

### 1.2 改造目标

- **双模式自动切换，存量兼容**：插件按 workflow 配置自动选择认证方式与上报接口（二者一一对应，不混用）：

| 模式 | 触发条件 | 上报接口 | 认证方式 |
| --- | --- | --- | --- |
| OIDC 联邦认证（新） | workflow 声明 `permissions: id-token: write` | `/action-api/metrics/code/report` | APIG 上报走 OIDC ID Token → STS 临时凭证 → V11 签名（SDK）；OBS 上传走 STS 临时凭证，零凭证接入 |
| AK/SK 签名（旧，存量兼容） | 未声明 `permissions: id-token: write` | `/openlibing-coderepo/metrics/code/report`（保持不变） | APIG 上报走 `apig-app-key` / `apig-app-secret` SDK-HMAC-SHA256 签名；OBS 上传走 `obs-ak` / `obs-sk`（行为与升级前完全一致） |

- OIDC 模式下 OBS 上传使用 STS 临时凭证 + SecurityToken，obsutil 经 `-t` 参数传递临时令牌；
- 4 个凭证输入参数（`apig-app-key` / `apig-app-secret` / `obs-ak` / `obs-sk`）保留为可选（仅 AK/SK 模式使用），存量脚本零修改继续可用；
- 两套接口的 payload / 响应格式契约与 OBS 桶/对象 key 规则一致，后端 openlibing-coderepo 与保底定时任务无感。

### 1.3 总体方案

插件运行时以 `ACTIONS_ID_TOKEN_REQUEST_URL` 环境变量是否存在判定认证模式（`useOidc`），据此选择上报接口与凭证方式，与 sec-option-scan 相同。

OIDC 模式认证链路（OIDC → STS → 临时凭证）与 sec-option-scan 一致，临时凭证消费方有两处：

```
GitCode 流水线（permissions: id-token: write）
  ▼
SDK getCredentials() → STS 临时凭证 {accessKeyId, secretAccessKey, securityToken}
  │
  ├─► OBS 上传：obsutil cp -e=<endpoint> -i=<临时AK> -k=<临时SK> -t=<SecurityToken>
  │     全量上报文件上传到桶 openlibing-gitcode-action（私有对象）
  │
  └─► APIG 上报：callApig('POST', /action-api/metrics/code/report, ...)
        V11 签名 + X-Security-Token，仅传元数据 + obsUrl
```

AK/SK 模式（存量兼容）链路保持改造前行为：obsutil 以静态 `obs-ak`/`obs-sk` 上传，`ApigSigner`（SDK-HMAC-SHA256）签名后调用旧接口 `/openlibing-coderepo/metrics/code/report`。

上报链路保持既有的「OBS 中转 + 单接口」设计（规避 APIG 12MB 请求体上限）：

1. 组装全量上报文件（元数据 + 总体指标 + fileDetails + identicalFileDetails + duplicationOccurrences），写本地临时 json；
2. 上传到 OBS（桶 `openlibing-gitcode-action`，对象 key `code-metrics-action/{owner}/{repo}/{pipelineRunId}/{ts}-metrics.json`，私有对象）；
3. 单次 `POST /metrics/code/report` 仅传元数据 + obsUrl，后端按 objectKey 下载解析入库。

### 1.4 SDK 引入方式

与 sec-option-scan 相同：依赖 `@openlibing/huaweicloud-oidc-client@0.0.5`，ncc 内联打包单文件分发。OBS 上传逻辑由插件基于 SDK 提供的临时凭证自行实现（SDK 设计边界：OBS 使用自身签名协议，由 obsutil 承担）。

## 2. 实现逻辑设计

### 2.1 上报流程（改造后）

1. `CoderepoUploader.upload(metricsData, options)` 分离总体指标与明细，组装全量 payload；
2. OBS 凭证按模式获取：OIDC 模式 `getCredentials()` 获取 STS 临时凭证（SDK 缓存，同一次运行内只换证一次）；AK/SK 模式使用 workflow 传入的 `obs-ak` / `obs-sk`（缺失时返回明确错误提示，说明两种模式的启用条件）；
3. `uploadToOBS()`：OIDC 模式 obsutil 参数为 `-i=<临时AK> -k=<临时SK> -t=<SecurityToken>`；AK/SK 模式为 `-i=<obs-ak> -k=<obs-sk>`，上传全量文件到 OBS；
4. 上传成功后拼出固定格式 obsUrl（`https://{bucket}.{endpoint}/{objectKey}`）；
5. report 上报 URL 按模式选择接口前缀（`/action-api` 或 `/openlibing-coderepo`），并按模式认证：OIDC 模式 `callApig(...)` 自动换证签名；AK/SK 模式 `ApigSigner.sign()` + axios；解析 DataResult 响应；
6. 兜底语义保持：上报失败但 OBS 文件已完整上传时，输出 obsUrl 提示可走平台保底定时任务（入参 objectKey）补导入，数据不丢失。

### 2.2 改造点清单

| 位置 | 变更 |
| --- | --- |
| `dist/uploaders/CoderepoUploader.js` | 保留 `ApigSigner` 类与 `axios`（AK/SK 模式）；新增 `useOidc` 标志与接口前缀常量（`OIDC_API_PREFIX` / `AKSK_API_PREFIX`）；OIDC 分支走 SDK `callApig` + `getCredentials()` 临时凭证，obsutil 参数增加 `-t=<SecurityToken>` |
| `dist/index.js` | 按 `ACTIONS_ID_TOKEN_REQUEST_URL` 判定 `useOidc`；读取 4 个凭证输入（可选）并透传；输出认证模式日志 |
| `dist/scanner.js` | 构造 `CoderepoUploader` 时透传双模式配置 |
| `package.json` | 新增 `@openlibing/huaweicloud-oidc-client@0.0.5`，保留 `axios` |
| `action.yml`（源码仓 + 发布仓） | 4 个凭证输入声明保留为可选（`required: false`，description 标注仅 AK/SK 模式使用） |
| `README.md`（源码仓 + 发布仓） | 参数表与使用示例同步，新增「上传认证（双模式自动切换）」章节 |
| 接入方 workflow | 已适配：新增 permissions 声明（凭证传参可移除）；存量：保持原样零修改 |

### 2.3 失败处理

- OBS 上传失败（含临时凭证获取失败）：数据未落盘，直接返回失败，可整体重扫重传；
- report 上报失败但 OBS 已上传：输出 obsUrl，走保底任务补导入；
- OIDC 链路失败（缺环境变量 / 网关认证模式 / 信任策略）的报错与排查指引同《sec-option-scan 插件需求设计文档》2.2 节。

## 3. 类设计

| 类 | 职责 | 改造点 |
| --- | --- | --- |
| `MetricsScanner` | 扫描编排：三个检测器 + 计算器 + 上传器 | 构造上传器时透传双模式配置（`useOidc` / AK/SK 与 OBS 凭证） |
| `SlocDetector` / `LizardDetector` / `DuplicationDetector` | 代码规模 / 函数指标 / 重复率检测 | 无变化 |
| `MetricsCalculator` | 指标合并、校验、格式化 | 无变化 |
| `CoderepoUploader` | OBS 中转上传 + APIG 上报（按模式选择接口与凭证） | 新增 `useOidc` 标志与接口前缀常量（`OIDC_API_PREFIX` / `AKSK_API_PREFIX`）；OIDC 分支走 SDK `callApig` + `getCredentials()`，obsutil 增 `-t` 参数；AK/SK 分支保留 `ApigSigner` + axios + 静态凭证 |
| `ApigSigner`（保留） | SDK-HMAC-SHA256 签名器（对齐 APIG 官方 SDK），仅 AK/SK 模式使用 | 保留，服务存量 workflow 兼容 |
| SDK `getCredentials` / `callApig` | 临时凭证获取 / APIG 一行调用 | 新增依赖（OIDC 模式） |

## 4. 数据模型设计

### 4.1 全量上报文件（上传 OBS）

```json
{
  "gitUrl": "https://gitcode.com/<owner>/<repo>.git",
  "branchName": "<分支或标签>",
  "pipelineRunId": "<ATOMGIT_RUN_ID>",
  "commitId": "<ATOMGIT_SHA>",
  "runNumber": "<ATOMGIT_RUN_NUMBER>",
  "metricsData": { "codeScale": 0, "avgFunctionLoc": 0, "avgCyclomaticComplexity": 0, "totalCodeDuplicationRate": 0, "totalFileDuplicationRate": 0 },
  "detectionStartedAt": "yyyy-MM-dd HH:mm:ss",
  "detectionCompletedAt": "yyyy-MM-dd HH:mm:ss",
  "status": 0,
  "errorMessage": "仅失败上报时携带",
  "fileDetails": [ { "filePath": "...", "...": "文件级指标" } ],
  "identicalFileDetails": [ { "...": "内容完全一致文件明细" } ],
  "duplicationOccurrences": [ { "groupId": "...", "contentHash": "...", "occurrenceIndex": 0, "filePath": "...", "startLine": 0, "endLine": 0, "contentB64": "<base64>" } ]
}
```

重复块内容编码为 `contentB64`（防二次编码回检），完整内容上传 OBS 不截断。

### 4.2 report 接口 payload（单次上报，body 恒定极小）

```json
{
  "gitUrl": "...", "branchName": "...", "pipelineRunId": "...", "commitId": "...", "runNumber": "...",
  "detectionStartedAt": "...", "detectionCompletedAt": "...", "status": 0,
  "obsUrl": "https://openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com/<objectKey>"
}
```

### 4.3 OBS 对象 key 规则（保持不变）

`code-metrics-action/{owner}/{repo}/{pipelineRunId}/{yyyyMMddHHmmss}-metrics.json`

branchName 不进入路径（远端分支可能含 `/` 造成歧义），仅存于文件内元数据。该 objectKey 同时供后端解析与保底定时任务补导入使用。

### 4.4 响应模型（DataResult）

与 sec-option-scan 一致：`{ code: 200, msg, data }`，`recordId` 兼容 `data.recordId` / `data.id` / 基础类型 `data`。

## 5. 性能设计

- OBS 中转设计使 report 接口 body 恒定极小（仅元数据 + obsUrl），不受 APIG 12MB 请求体上限约束，大型仓库全量明细照常上报；
- STS 换证在 SDK 内缓存并按过期时间自动刷新，同一次运行内 OBS 上传与 APIG 上报共用一次换证；并发去重避免重复请求；
- 本地临时文件用完即删（finally 中 unlink），避免 runner 残留大文件；
- 上报超时 60s，扫描与上传解耦，上传失败不影响本地 metrics.json 落盘与 workflow 输出。

## 6. API接口设计

### 6.1 report 接口

| 模式 | 接口 | 鉴权 |
| --- | --- | --- |
| OIDC 联邦认证（新） | `POST https://apig.openlibing.com/action-api/metrics/code/report` | V11-HMAC-SHA256 签名 + `X-Security-Token`（网关 IAM 认证模式） |
| AK/SK 签名（旧，存量兼容） | `POST https://apig.openlibing.com/openlibing-coderepo/metrics/code/report` | SDK-HMAC-SHA256 签名（网关 App 认证模式，保持不变） |

- 请求体：见 4.2；响应：见 4.4（两套接口契约一致）
- 报文契约保持不变，后端 openlibing-coderepo 无感

### 6.2 OBS 上传

- OIDC 模式：`obsutil cp <localFile> obs://openlibing-gitcode-action/<objectKey> -f -e=<endpoint> -i=<临时AK> -k=<临时SK> -t=<SecurityToken>`
- AK/SK 模式：`obsutil cp <localFile> obs://openlibing-gitcode-action/<objectKey> -f -e=<endpoint> -i=<obs-ak> -k=<obs-sk>`
- 私有对象，不带 `-acl=public-read`；后端/保底任务用平台侧 OBS 凭证按 objectKey 下载
- 桶与 endpoint 保持不变（`openlibing-gitcode-action` / `obs.cn-southwest-2.myhuaweicloud.com`）

### 6.3 依赖的华为云接口

与 sec-option-scan 一致：流水线 OIDC 接口 + `sts:agencies:assumeWithOIDC`（cn-southwest-2）。

## 7. 安全设计

- **存量凭证收敛**：OIDC 模式下插件与 workflow 零长期静态凭证；AK/SK 模式仅为存量兼容保留，4 个凭证仍经 workflow `secrets` 分发（不落明文），存量 workflow 逐步迁移至 OIDC 模式后即可彻底移除；
- **临时凭证**：OBS 与 APIG 共用同一份 STS 临时凭证（短时效、限本流水线运行），OBS 对象级权限由委托身份策略按桶收敛；
- **进程参数安全**：临时凭证虽经 obsutil 命令行参数传递，但均为短期令牌且 CI 平台对 secrets/令牌自动掩码；`execFileSync` 参数数组调用不经 shell 解析，避免路径注入；临时 SecurityToken 在日志中不打印；
- **最小信任**：OIDC → STS 信任链路的 iss/aud/sub 收敛与 sec-option-scan 相同（同一委托 `gitcode-actions`、同一信任策略覆盖）；
- **日志脱敏**：SDK debug 日志敏感字段自动脱敏；插件日志对 obsutil 参数做脱敏输出（`-k=***`），临时凭证不落日志。
