# openlibing-upload-sarif 通用 SARIF 上传插件 — 设计

## 1. 方案设计

### 1.1 总体流程

workflow 前置步骤：检出代码 → 任意扫描工具产出 SARIF → 运行本插件。插件内部自包含 OIDC 换证，无需 `huaweicloud-oidc-auth` 插件：

```
检出代码 → 扫描工具产出 SARIF → openlibing-upload-sarif（OIDC 免密换证 → 上传 OBS → APIG 回调）
```

插件内部执行步骤：

1. 校验输入参数（`sarif_file` 必填、OIDC SDK 加载状态）
2. OIDC 免密换证：SDK 自申请 OIDC ID Token + 调用华为云 STS 换取临时 AK/SK/SecurityToken
3. 检查 SARIF 文件存在（支持逗号分隔多路径：文件/目录，目录自动扫描 `.sarif`；缺失路径报错退出）
4. 检查并补齐 `region.snippet`（缺失时按 `uri`+行号读源码补齐，写回原文件）
5. 从 `runs[0].tool.driver.name` 提取工具名，构建 OBS 路径前缀
6. 生成 `build-result.json` 构建产物
7. 初始化 `esdk-obs-nodejs` 客户端（OIDC 临时凭证，等待签名上下文就绪），上传构建产物与 SARIF 到 OBS（`public-read`，指数退避重试 3 次）
8. APIG 回调 `/action-api/codescan/v1/result/receive`（V11-HMAC-SHA256 签名 + `X-Security-Token`，指数退避重试 3 次）

### 1.2 与现有插件的关系

与 `pre-commit-action` 对齐 OBS 上传机制、路径结构、动态 region 方案与 `sarif-file` 多值输入；差异仅由业务场景决定：

| 维度        | openlibing-upload-sarif                                      | pre-commit-action                     |
| ----------- | ------------------------------------------------------------ | ------------------------------------- |
| OBS 前缀    | `{toolName}-results`（动态，兜底 `code-arts-check-results`） | 固定 `pre-commit-results`             |
| 数据源      | `sarif_file`（文件/目录/逗号多值）                           | `sarif-file`（文件/目录/逗号多值）    |
| 上传 SDK    | `esdk-obs-nodejs`                                            | `esdk-obs-nodejs`                     |
| region 来源 | OIDC SDK `configure()` 动态返回                              | 同左                                  |
| 认证模式    | OIDC 自包含换证                                              | 依赖 `huaweicloud-oidc-auth` 插件注入 |

## 2. 实现逻辑设计

### 2.1 OIDC 免密换证（SDK 自包含）

- 插件内嵌 `@openlibing/huaweicloud-oidc-client`，入口动态 `require` 并做加载失败兜底
- `getCredentials()` 通过 Actions 兼容流水线环境变量（`ACTIONS_ID_TOKEN_REQUEST_URL/TOKEN`）自申请 OIDC ID Token，再调用华为云 STS `AssumeAgencyWithOIDC` 换取临时 AK/SK/SecurityToken
- workflow 仅需声明 `permissions: id-token: write`，无需额外运行 `huaweicloud-oidc-auth` 插件
- 换证失败：打印提示并 `result=failed` 退出

### 2.2 SARIF 文件收集

- `sarif_file` 按逗号拆分多路径，逐路径解析
- 路径不存在时依次尝试：`WORKSPACE` 下拼接 → 在工作区 `find .git` 定位的 Git 根目录下拼接
- 目录输入：读取目录下所有 `.sarif` 后缀文件（非递归）；目录为空时 WARN
- 任一路径缺失或最终无任何 SARIF 文件：`result=failed` 退出

### 2.3 region.snippet 补齐

- 遍历每个 SARIF 的 `runs[0].results`，取 `locations[0].physicalLocation`
- 补齐条件：`region` 存在且 `startLine >= 1` 且 `region.snippet.text` 缺失
- 源码定位 `resolveSourceFile`：`file://` URI（decode 后直读）→ 绝对路径（`盘符:` 或 `/` 开头）→ `sourceRoots` 直接拼接 → 按文件名 `find` 递归兜底
- `source_path` 输入多值时全部加入 `sourceRoots`，且始终追加 `ATOMGIT_WORKSPACE` 兜底
- 补齐逻辑：`startLine`~`endLine`（无则单行）切分源码行，写入 `region.snippet.text`，写回原文件；源码不可读静默跳过

### 2.4 OBS 路径构建

```
{prefix}/{repoBaseName}/{yyyyMMdd}.{HH}/{runId|manual}/{fileName}
```

- `prefix = {toolName}-results`：工具名转小写、非法字符替换为 `-`、去首尾 `-`；缺失兜底 `code-arts-check-results`
- `repoBaseName`：`ATOMGIT_REPOSITORY` / `GIT_REPOSITORY` 取最后一段，缺失 `unknown-repo`
- 时间戳：执行时刻 `yyyyMMdd.HH`（精确到小时）
- `runId`：`ATOMGIT_RUN_ID`，缺失 `manual` 兜底
- 多工具 SARIF 各自独立前缀（各归各位）；`build-result.json` 使用首个工具目录前缀，不单独使用 `code-arts-check-results`

### 2.5 构建产物 JSON

```json
{
  "type": "build",
  "buildings": {
    "name": "scan.sarif",
    "type": "CodeQL代码检查结果（sarif）",
    "downloadUrl": "https://..."
  }
}
```

- 单文件：`buildings` 为对象；多文件：为数组
- `type`：`{toolName}代码检查结果（sarif）`，工具名缺失时 `SARIF代码检查结果（sarif）`
- 生成到临时目录 `sarif-analyze-output`，随 SARIF 一同上传

### 2.6 OBS 上传（esdk-obs-nodejs）

- server：`configure({})` 动态返回 region，拼装 `https://obs.{region}.myhuaweicloud.com`，不写死区域
- `ObsClient` 构造后 `await Promise.resolve()` 让出一个微任务，确保异步初始化完成（避免读到 null signatureContext）
- `putObject` 设置 `ACL: 'public-read'`（后端匿名 HTTP GET 下载）
- 上传结果校验：`CommonMsg.Status` 2xx 视为成功，否则抛错进入重试
- `build-result.json` 上传失败仅 WARN 不阻断；SARIF 上传失败则 `result=failed` 退出
- 上传结束 `client.close()`

### 2.7 APIG 回调

- 回调地址：`{OIDC_PROD|BETA_BASE}/action-api/codescan/v1/result/receive`（prod `https://apig.openlibing.com`；beta 临时使用已发布 `/action-api` 的 APIG 域名，待 beta 证书绑定后切回）
- 签名：`V11Signer`（region `cn-southwest-2`）+ 临时凭证 + `X-Security-Token` 头
- payload：repoUrl / pipelineId / pipelineName / pipelineRunId / branch / commitId / obsUrl（恒为数组，兼容后端 `List<String>` DTO）/ category / source（`GITCODE_ACTION`）/ sourceRunUrl
- 成功判定：HTTP 2xx 且 `code === 200 || code === 0`
- 回调失败：WARN 日志，不影响最终结果（SARIF 上传成功即视为成功）

## 3. 类设计

| 文件                        | 职责                                                                                                |
| --------------------------- | --------------------------------------------------------------------------------------------------- |
| `index.js`                  | 主入口：参数校验、流程编排、OIDC 换证、SARIF 收集、snippet 补齐、OBS 上传、APIG 回调、输出 `result` |
| `src/util/fetchPolyfill.js` | node16 fetch polyfill（OIDC SDK 依赖全局 fetch）                                                    |

插件为单文件主流程实现（`index.js` + 1 个 util），无独立模块拆分；核心辅助函数（`withRetrySync` / `withRetryAsync` / `buildToolPrefix` / `enrichRegionSnippet` / `resolveSourceFile` / `enrichSarifFiles`）均以函数形式导出便于复用与测试。

## 4. 数据模型设计

不涉及数据库/持久化。核心数据为：

- 输入：`sarif_file`（逗号分隔多路径）、`category`、`source_path`（逗号分隔多值）、`env_type`（prod/beta）
- 中间：`sarifUploads[]`（file / name / toolName / keyPrefix / downloadUrl）、`build-result.json`（type=build + buildings）
- 输出：`result`（success/failed）

## 5. 性能设计

- **指数退避重试**：同步（OBS 上传）`withRetrySync`、异步（APIG 回调）`withRetryAsync`，均默认 3 次，失败后 `2^(n-1)` 秒/毫秒退避，降低网络抖动导致的数据丢失风险
- **SARIF 解析**：仅读取 `runs[0]` 层，`region.snippet` 补齐按行切片，避免整体加载大报告
- **源码查找**：`find` 按文件名兜底时用 `head -1` 截断，路径拼接优先于递归查找

## 6. API接口设计

GitCode Action 输入参数：

| 参数          | 说明                                                                                                                                 | 必填 | 默认值 |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---- | ------ |
| `sarif_file`  | SARIF 文件/目录路径，逗号分隔支持多值（目录自动扫描 `.sarif`，非递归）                                                               | 是   | -      |
| `category`    | 检查结果分类（用户手动传入，不传则为空）                                                                                             | 否   | -      |
| `source_path` | 源码根目录（可选，逗号分隔多个），SARIF 缺 `region.snippet` 时按 `uri`+行号读源码补齐；不传默认在 `ATOMGIT_WORKSPACE` 下按文件名查找 | 否   | -      |
| `env_type`    | 环境类型：`prod`（正式环境）/ `beta`（测试环境）                                                                                     | 否   | `prod` |

输出参数：

| 参数     | 说明                            |
| -------- | ------------------------------- |
| `result` | 上传结果：`success` 或 `failed` |

凭证不通过输入参数配置：OBS 上传与 APIG 回调所需临时凭证由插件内嵌 SDK 自动换取。

## 7. 安全设计

### 鉴权

OBS 上传与 APIG 回调全程使用 OIDC 临时凭证（SDK 自申请 ID Token + STS 换证）；APIG 侧 V11-HMAC-SHA256 签名（region `cn-southwest-2`，携带 `X-Security-Token`）。插件不管理任何静态 AK/SK。

### 敏感信息

- 日志对 IP 地址脱敏（`sanitizePath` 替换为 `[IP_ADDRESS]`）
- 临时凭证仅存在于内存变量，不打印、不落盘、不进日志
- OBS 对象 `public-read` 仅暴露 SARIF 分析结果（非源码），由 OBS 桶策略控制

### 硬编码

无凭证硬编码。OBS 桶 `openlibing-gitcode-action`、APIG 回调地址、OBS 读取 Endpoint 为环境常量（与既有插件一致的维护约定，变更需改源码）。

### 审计日志

每个步骤输出 `[INFO]`/`[WARN]`/`[ERROR]` 日志：环境类型、回调地址、SARIF 收集数量、snippet 补齐数量、OBS 上传对象与路径、回调响应；不打印敏感参数。
