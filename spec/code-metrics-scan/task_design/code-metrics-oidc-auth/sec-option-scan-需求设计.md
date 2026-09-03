# sec-option-scan 插件需求设计文档

> FE 需求：【openlibing】GitCode插件流水线交互适配OIDC认证方案
> 适用插件：openlibing-security-compilation-options-action（sec-option-scan，安全编译选项扫描）
> 涉及仓库：openlibing/security-compilation-options-action（发布仓）、openlibing/code-metrics-scan（插件源码仓，`.gitcode/actions/sec-option-scan`）
> SDK：`@openlibing/huaweicloud-oidc-client@0.0.3`

## 1. 方案设计

### 1.1 背景与现状

sec-option-scan 插件在 GitCode 流水线中扫描构建产物（ELF 文件）的 14 项安全编译选项，并将扫描结果上报到 openlibing-cicd 服务（经 APIG 网关，`https://apig.openlibing.com`）。

当前业务状态：插件使用 APIG App 认证（`apig-app-key` / `apig-app-secret`）完成上报鉴权。AK/SK 为长期静态凭证，经 workflow `secrets` 分发到每条流水线，存在以下业务问题：

- 长期静态凭证泄露面大：任何一条流水线配置泄漏即泄漏永久凭证，需人工轮换；
- 凭证与流水线强耦合：每个接入插件的仓库都需配置 secrets，接入成本高；
- 无法审计到流水线身份：网关侧只能识别到 APIG 应用，无法区分是哪个仓库哪条流水线发起的调用。

### 1.2 改造目标

- **双模式认证，平滑迁移**：为保证存量用户（workflow 尚未改造）不受影响，插件按 workflow 配置自动选择认证方式与上报接口（二者一一对应，不混用）：

| 模式 | 触发条件 | 上报接口 | 认证方式 |
| --- | --- | --- | --- |
| OIDC 联邦认证（新） | workflow 声明 `permissions: id-token: write` | `/action-api/build-artifact/sec-option/report` | OIDC ID Token → STS 临时凭证 → V11 签名（SDK），零凭证 |
| AK/SK 签名（旧，存量兼容） | 未声明 `permissions: id-token: write` | `/openlibing-cicd/build-artifact/sec-option/report`（保持不变） | `apig-app-key` / `apig-app-secret` SDK-HMAC-SHA256 签名（行为与升级前完全一致） |

- 已适配的 workflow 仅需声明 `permissions: id-token: write`，由 runner 注入 OIDC 环境变量，插件免密接入；
- 新接口（`/action-api/...`）在网关侧安全认证方式为 IAM 认证，IAM 侧配置 OIDC 身份提供商与信任委托；旧接口（`/openlibing-cicd/...`）保持 App 认证不变；
- 两套接口的 payload / 响应格式契约完全一致，后端 openlibing-cicd 无需改造。

### 1.3 总体方案

插件运行时以 `ACTIONS_ID_TOKEN_REQUEST_URL` 环境变量是否存在判定认证模式（该变量仅在 workflow 声明 `permissions: id-token: write` 后由 runner 注入），据此选择上报接口与签名方式。

OIDC 模式认证链路采用华为云 STS 联邦换证模型：

```
GitCode 流水线（permissions: id-token: write）
  │ runner 注入 ACTIONS_ID_TOKEN_REQUEST_URL / ACTIONS_ID_TOKEN_REQUEST_TOKEN
  ▼
插件申请 OIDC ID Token（iss=https://actions-results.atomgit.com, aud=huawei-cloud-service）
  ▼
SDK 调用华为云 STS AssumeAgencyWithOIDC（区域 cn-southwest-2，提供商 GitCodeActions，委托 gitcode-actions）
  ▼
获得 STS 临时凭证（accessKeyId / secretAccessKey / securityToken，短期有效）
  ▼
SDK 以 V11-HMAC-SHA256 签名（作用域服务名 apic）+ X-Security-Token 调用 APIG 接口
  ▼
APIG（IAM 认证模式）校验签名与安全令牌 → 转发后端 openlibing-cicd
```

改造过程分四个环节落地，环环相扣，任一环节缺失均会失败：

| 环节 | 责任侧 | 关键动作 | 缺失时的典型报错 |
| --- | --- | --- | --- |
| 1. 客户端认证切换 | 插件仓 | 引入 SDK，`CicdUploader` 按 `useOidc` 分流：OIDC 走 `callApig` + 新接口，AK/SK 走 `ApigSigner` + axios + 旧接口 | — |
| 2. workflow 声明 | 业务流水线仓 | OIDC 模式：workflow 级声明 `permissions: id-token: write`，凭证可不传；存量脚本保持原样（继续传 AK/SK） | `缺少 ACTIONS_ID_TOKEN_REQUEST_URL/ACTIONS_ID_TOKEN_REQUEST_TOKEN` |
| 3. 网关认证切换 | 平台侧（华为云 APIG 控制台） | 新接口安全认证为 IAM 认证；旧接口保持 App 认证不变 | `HTTP 401 Incorrect app authentication information: app not found`（网关把 V11 签名中的 STS 临时 AK 当 appkey 查找） |
| 4. IAM 信任委托 | 平台侧（华为云 IAM 控制台） | 委托 `gitcode-actions` 信任策略放行 `sts:agencies:assumeWithOIDC`，Condition 限定 iss/aud/sub | `STS5.1001 no identity-based policy allows sts:agencies:assumeWithOIDC` |

### 1.4 SDK 引入方式

- 依赖 `@openlibing/huaweicloud-oidc-client@0.0.4`（固定小版本），`ncc build` 打包时内联进 `dist/index.js`，插件分发物保持单文件；
- SDK 内置 openlibing 账号默认配置（accountId、region=cn-southwest-2、提供商 GitCodeActions、委托 gitcode-actions），插件零配置调用。

## 2. 实现逻辑设计

### 2.1 上报流程（改造后）

1. `SecOptionScanner.scan()` 完成 ELF 扫描，产出 `overviewData`（14 项开启率汇总）与 `fileDetails`（文件级明细）；
2. 上传开启时（默认开启），`CicdUploader.upload(scanResult, options)` 组装上报 payload；
3. 拼接上报 URL：`baseUrl + 上报接口路径`，路径按认证模式选择——OIDC 模式 `/action-api/build-artifact/sec-option/report`，AK/SK 模式 `/openlibing-cicd/build-artifact/sec-option/report`（baseUrl 失配时回退 `http://localhost:8080` 便于本地调试显式失败）；
4. 按模式调用上报：
   - **OIDC 模式**：调用 SDK `callApig('POST', url, { 'Content-Type': 'application/json' }, body)`——SDK 内部自动完成 OIDC ID Token 申请 → STS 换证（带缓存/并发去重/自动刷新）→ V11 签名 → 注入 `X-Security-Token`；
   - **AK/SK 模式**：凭证缺失时返回明确错误提示（说明两种模式的启用条件）；否则 `ApigSigner.sign()` 生成 SDK-HMAC-SHA256 签名头，axios 发送请求；
5. 解析响应：HTTP 非 2xx 返回失败（输出网关 msg）；`DataResult.code !== 200` 返回业务失败；成功时从 `data` 中提取 `recordId`；
6. 上传失败不影响扫描结果输出（结果文件已落盘），仅记录 `uploadInfo`。

### 2.2 失败处理与排查指引（改造过程中验证过的线上问题）

| 现象 | 根因 | 处理 |
| --- | --- | --- |
| `缺少 ACTIONS_ID_TOKEN_REQUEST_URL/ACTIONS_ID_TOKEN_REQUEST_TOKEN` | workflow 未声明 `permissions: id-token: write`，runner 不注入 OIDC 环境变量 | 补 workflow 级 permissions 声明 |
| `HTTP 401 Incorrect app authentication information: app not found, appkey HSTAP...` | 网关接口仍为 App 认证，把 V11 签名 Credential 中的 STS 临时 AK（HSTAP 前缀）当 appkey 查找 | 网关侧将该接口安全认证切换为 IAM 认证 |
| `STS5.1001 ... no identity-based policy allows sts:agencies:assumeWithOIDC` | 委托信任策略未命中 Allow：`oidc:iss` 不等于实际签发地址 `https://actions-results.atomgit.com`、`oidc:sub` 通配符未覆盖目标仓、或缺 `sts:agencies:assumeWithOIDC` Action | 按日志输出的 iss/aud/sub 逐项比对并修正信任策略 |
| 失败日志自动输出 Token 声明（iss/aud/azp/sub/provider_urn） | SDK 内置排查辅助 | 与信任策略逐项比对即可定位 |

### 2.3 workflow 侧变更

- 已适配 OIDC 的 workflow：新增 workflow 级声明，`apig-app-key` / `apig-app-secret` 传参可移除（传了也会被忽略）：

```yaml
permissions:
  id-token: write
```

- 存量 workflow（未改造）：保持原样即可，继续传入 `apig-app-key` / `apig-app-secret`，插件自动走旧接口 + AK/SK 认证，行为与升级前完全一致；
- 注意：GitCode 平台 schedule / pull_request 触发仅读取默认分支的 workflow 配置，permissions 修复合入默认分支后才能覆盖这两类触发方式。

## 3. 类设计

### 3.1 插件侧（Node.js，源码位于 code-metrics-scan 仓）

| 类 | 职责 | 改造点 |
| --- | --- | --- |
| `SecOptionScanner` | 扫描编排：调用检测器、组装结果、落盘、触发上传 | 无变化，构造 `CicdUploader` 时透传双模式配置（`useOidc` / AK/SK 凭证） |
| `SecOptionDetector` | 封装 Python 扫描脚本 `sec_option_scan.py`，支持 scan-options 圈定检测项 | 无变化 |
| `CicdUploader` | 上报器：组装 payload、按模式选择接口与认证方式、调用上报接口、解析响应 | 新增 `useOidc` 标志与新旧接口路径常量（`OIDC_REPORT_PATH` / `AKSK_REPORT_PATH`）；OIDC 分支走 SDK `callApig`，AK/SK 分支保留 `ApigSigner` + axios |
| `ApigSigner`（保留） | SDK-HMAC-SHA256 签名器（对齐 APIG 官方 SDK），仅 AK/SK 模式使用 | 保留，服务存量 workflow 兼容 |

### 3.2 SDK 侧（`@openlibing/huaweicloud-oidc-client`）

| 模块 | 职责 |
| --- | --- |
| `oidc.js` | 从 Actions 兼容流水线注入的环境变量申请 OIDC ID Token |
| `credentials.js` | `getCredentials()`：STS 换证（缓存 / force / 并发去重），返回 `{accessKeyId, secretAccessKey, securityToken, expiresAt, expiresIn}` |
| `signer-v11.js` | `V11Signer`：V11-HMAC-SHA256 签名（服务名固定 apic） |
| `apig.js` | `callApig()`：一行调用 APIG（自动换证 + 签名 + X-Security-Token） |
| `config.js` | 内置 openlibing 账号默认配置 + `configure()` 覆盖 |
| `logger.js` / `http.js` | 分级日志（关键步骤 info、失败详情 error、debug 可选且敏感字段脱敏）/ HTTPS 工具 |

## 4. 数据模型设计

### 4.1 上报 payload

```json
{
  "gitUrl": "https://gitcode.com/<owner>/<repo>.git",
  "pipelineRunId": "<ATOMGIT_RUN_ID>",
  "runNumber": "<ATOMGIT_RUN_NUMBER>",
  "packageName": "<构建产物压缩包名>",
  "overviewData": { "<option>": { "totalFiles": 0, "yesCount": 0, "rate": "0%" } },
  "fileDetails": [ { "filePath": "...", "options": { "<option>": "YES|NO|N/A" } } ],
  "detectionStartedAt": "yyyy-MM-dd'T'HH:mm:ss",
  "detectionCompletedAt": "yyyy-MM-dd'T'HH:mm:ss",
  "status": 0,
  "errorMessage": "仅失败上报时携带",
  "artifactDownloadUrl": "构建产物 OBS 下载链接，可选",
  "pipelineName": "<ATOMGIT_WORKFLOW，可选>"
}
```

时间字段为东八区（UTC+8）ISO 格式，与 Java 端 `DateTimeFormatter.ISO_DATE_TIME` 兼容。

### 4.2 响应模型（DataResult）

```json
{ "code": 200, "msg": "success", "data": { "recordId": "..." } }
```

`recordId` 兼容三种形态：`data.recordId`、`data.id`、`data` 本身为基础类型。

## 5. 性能设计

- STS 换证结果在 SDK 内缓存并按过期时间自动刷新，同一次流水线运行内多次调用只换证一次；并发调用通过去重合并为一次请求；
- 扫描与上传解耦：上传失败不影响扫描结果落盘与 workflow 输出；
- SDK 仅依赖 Node 内置模块（https/crypto/url），ncc 打包后单文件分发，无运行时网络依赖安装。

## 6. API接口设计

### 6.1 上报接口

| 模式 | 接口 | 鉴权 |
| --- | --- | --- |
| OIDC 联邦认证（新） | `POST https://apig.openlibing.com/action-api/build-artifact/sec-option/report` | V11-HMAC-SHA256 签名 Authorization 头 + `X-Security-Token`（网关 IAM 认证模式） |
| AK/SK 签名（旧，存量兼容） | `POST https://apig.openlibing.com/openlibing-cicd/build-artifact/sec-option/report` | SDK-HMAC-SHA256 签名 Authorization 头（网关 App 认证模式，保持不变） |

- 请求体：见 4.1；响应：见 4.2（两套接口契约一致）
- 报文契约保持不变，后端 openlibing-cicd 无感

### 6.2 依赖的华为云接口

| 接口 | 用途 |
| --- | --- |
| 流水线 OIDC 接口（ACTIONS_ID_TOKEN_REQUEST_URL） | 申请 OIDC ID Token |
| `sts:agencies:assumeWithOIDC`（cn-southwest-2） | OIDC ID Token 换取 STS 临时凭证 |

## 7. 安全设计

- **存量凭证收敛**：OIDC 模式下插件与 workflow 零长期静态凭证；AK/SK 模式仅为存量兼容保留，凭证仍经 workflow `secrets` 分发（不落明文），存量 workflow 逐步迁移至 OIDC 模式后即可彻底移除；
- **临时凭证**：STS 临时凭证短时效（约 1 小时内），仅在本流水线运行内有效，无法离线重放；
- **最小信任**：委托 `gitcode-actions` 信任策略通过 `oidc:iss`（精确匹配签发地址）、`oidc:aud`（`huawei-cloud-service`）、`oidc:sub`（通配符限定仓库范围）收敛可换证来源，防范混淆代理攻击；
- **日志脱敏**：SDK debug 日志对 Token、签名等敏感字段自动脱敏；error 日志输出 Token 声明（iss/aud/sub 等非敏感 claim）用于排查，不输出完整 Token；
- **凭证不落盘**：OIDC ID Token 与临时凭证仅在进程内存中流转，不写文件、不进环境变量持久化。
