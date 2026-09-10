# precommit-report-sarif-upload — 设计

## 1. 方案设计

pre-commit 检查完成后，各工具的扫描报告经通用链路归档到 OBS + 回调 openlibing 后端。**SARIF 转换由业务仓负责**，插件只做"上传 + 回调"，不绑定任何具体工具。

整体链路：

```
CI runner (workflow_dispatch)
  -> pre-commit 运行钩子（以 detect-secrets 为例：扫描生成 detect-secrets.json）
  -> 业务仓钩子脚本内转 SARIF（convert-detect-secrets-to-sarif.py -> detect-secrets.sarif，写约定目录）
  -> pre-commit-action 读取约定目录下所有 *.sarif（不感知工具，不做转换）
  -> OIDC 换取华为云临时凭证（@openlibing/huaweicloud-oidc-client）
  -> esdk-obs-nodejs 上传 OBS 桶 openlibing-gitcode-action（ACL: public-read）
  -> APIG 回调 codecheck 接口（/action-api/...，V11 签名 + X-Security-Token）
  -> openlibing-codecheck 解析 SARIF（StandardSarifParser，指纹缺失时后端兜底）
```

关键决策：

| 决策点 | 方案 | 理由 |
|-------|------|------|
| 报告目录 | `/tmp/pre-commit-reports/`（input `report-dir` 可覆盖） | CI 机器临时目录，不污染代码仓 |
| SARIF 转换归属 | **业务仓**（按工具实现转换脚本） | 插件保持通用，不绑定具体工具；转换脚本随业务仓演进 |
| 上传物 | 约定目录下所有 `*.sarif` | 插件只认 SARIF，不解析任何工具私有格式 |
| OBS 上传 | OIDC 临时凭证 + esdk-obs-nodejs，对象 `ACL: public-read` | 零 Secret；后端匿名 HTTP GET 下载 |
| OBS 路径 | `pre-commit-reports/<仓库名>/<runId>/<file>.sarif` | 与 code-arts-check-results 前缀区分 |
| APIG 回调 | OIDC callApig（V11-HMAC-SHA256 + X-Security-Token） | 凭证统一走 OIDC，禁止 AppCode 明文；回调路径 `/action-api/` 为 IAM 认证分组（`/openlibing-codecheck/` 为 APP 认证分组，OIDC 签名不适用） |
| 回调成功判定 | HTTP 状态 + 响应体业务码 `code` 均成功 | 后端 DataResult 业务错误恒为 HTTP 200，只看状态会误报成功 |
| 环境切换 | `env-type`（prod/beta） | beta 走华为云 APIG 实例域名，测试数据不进正式环境 |
| 指纹 | 后端兜底 sha256(uri\|startLine\|ruleId) | detect-secrets/gitleaks 不带 `primaryLocationLineHash`，缺失会导致 issue 静默丢弃 |
| PR 触发 | 只检查不回调 | PR 增量检查不产生全量报告，避免噪音 |

## 2. 实现逻辑设计

### pre-commit-action 主流程扩展（index.js run()）

```
[1] 检查 Python 环境
[2] 安装 pre-commit（含镜像测速）
[3] 定位代码目录
[4] 检查 .pre-commit-config.yaml
[5] 构建运行参数
[6] 运行 pre-commit 检查（记录 checkFailed；钩子负责生成 *.sarif 到约定目录）
[7] 新增：读取报告目录
    - 目录默认 /tmp/pre-commit-reports/（input report-dir 覆盖）
    - 只收集 *.sarif 文件（业务仓已转换好），不做任何格式转换
[8] 新增：PR 类型判断
    - eventName ∈ {mr, pull_request, note} 且有 baseRef -> 跳过上传回调
[9] 新增：OIDC 换证 + OBS 上传（esdk-obs-nodejs putObject，ACL: public-read）
    - ObsClient 构造后 await Promise.resolve() 等待 initFactory 完成，避免签名上下文竞态
[10] 新增：APIG 回调 codecheck 接口（callApig POST）
    - 校验 HTTP 状态 + 响应体业务码；非成功打 WARN 并输出业务码
[11] 按 checkFailed 决定退出码（上传失败只 warning）
```

### 业务仓 SARIF 转换（以 detect-secrets 为例，脚本可复用该模式）

detect-secrets JSON → SARIF 2.1.0 映射（`scripts/convert-detect-secrets-to-sarif.py`）：

| detect-secrets 字段 | SARIF 字段 |
|--------------------|-----------|
| results 的 file key | locations[0].physicalLocation.artifactLocation.uri |
| secret.line_number | region.startLine |
| secret.type | ruleId + rule.shortDescription.text |
| secret.is_verified | level（true→error，false→warning） |
| secret.hashed_secret | 参与指纹（保证同位置不同密钥指纹不同） |

SARIF 结构：
- version: "2.1.0"
- runs[0].tool.driver: name=detect-secrets, rules[]
- runs[0].results[]: ruleId, level, message.text, locations, partialFingerprints
- 每个 result 生成 `partialFingerprints.primaryLocationLineHash = sha256(file|line|type|hashed_secret)`（稳定，供后端去重）

**其他工具扩展方式**：新增对应转换脚本，输出 `<tool>.sarif` 到同一约定目录即可，插件与后端零改动。

### 后端指纹兜底（openlibing-codecheck StandardSarifParser）

```
extractLocationHash(result):
  if partialFingerprints.primaryLocationLineHash 非空 -> 直接使用（CodeQL 等自带）
  else -> buildFallbackLocationHash(result) = sha256(uri | startLine | ruleId)
```
- 保证任何工具都不因缺指纹而构建不了 `fingerprintKey = sha256(tool|ruleId|filePath|locationHashRaw)`
- 同一位置同一规则跨扫描稳定，去重/upsert 正确

### OBS 上传（参考 test-obs-action）

```javascript
const { configure, getCredentials } = require('@openlibing/huaweicloud-oidc-client');
const ObsClient = require('esdk-obs-nodejs');

const { region } = configure({ debug });
const cred = await getCredentials();
const client = new ObsClient({
  access_key_id: cred.accessKeyId,
  secret_access_key: cred.secretAccessKey,
  security_token: cred.securityToken,
  server: `https://obs.${region}.myhuaweicloud.com`
});
await Promise.resolve(); // 等待 initFactory 完成
await client.putObject({ Bucket, Key, SourceFile, ACL: 'public-read' });
```

### APIG 回调（参考 SDK callApig）

```javascript
const { callApig } = require('@openlibing/huaweicloud-oidc-client');
await callApig('POST', callbackUrl, JSON.stringify(payload));
```

payload 复用 upload-sarif 结构：repoUrl / pipelineId / pipelineName / pipelineRunId / branch / commitId / obsUrl / category / source / sourceRunUrl。obsUrl 传 SARIF 下载地址（`https://openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com/<key>`），category 标识 pre-commit。

## 3. 类设计

| 模块 | 职责 |
|------|------|
| pre-commit-action/index.js | 主流程编排（读取 `*.sarif` → OIDC 上传 → APIG 回调，**无转换模块**） |
| openlibing-cicd-test/scripts/convert-detect-secrets-to-sarif.py | 业务仓示例：detect-secrets JSON → SARIF 2.1.0（含指纹） |
| openlibing-cicd-test/scripts/detect-secrets-report.sh | pre-commit 钩子：扫描 + 调转换脚本 + baseline 拦截 |
| openlibing-codecheck/StandardSarifParser.java | 指纹解析 + 缺失时兜底计算 |

插件维持现有风格（单 index.js + ncc 打包），不引入转换器模块。

## 4. 数据模型设计

SARIF 2.1.0 标准结构（上传物）：
- `version`: "2.1.0"
- `$schema`: sarif-2.1.0 schema URL
- `runs`: [{ tool.driver, results[] }]

OBS 对象路径模型：
`pre-commit-reports/{repoBaseName}/{runId}/{tool}.sarif`

APIG 回调 payload（对齐 upload-sarif）：
`{ repoUrl, pipelineId, pipelineName, pipelineRunId, branch, commitId, obsUrl, category, source: 'GITCODE_ACTION', sourceRunUrl }`

## 5. 性能设计

- 报告文件为小文件（KB 级），putObject 直传即可，无需分段
- 凭证缓存由 SDK getCredentials 内部处理（1 小时有效期自动刷新）
- 转换逻辑为单次内存遍历，无性能瓶颈
- 转换内聚在钩子内，detect-secrets 只扫描一次（无重复扫描）

## 6. API接口设计

### OBS 上传（对外可读 URL）
```
GET https://openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com/pre-commit-reports/<repo>/<runId>/<tool>.sarif
```

### APIG 回调（插件 -> openlibing 后端）
```
POST <apig-domain>/action-api/codescan/v1/result/receive
Content-Type: application/json
Authorization: V11 签名（SDK callApig 自动生成）
X-Security-Token: <OIDC 临时凭证>
Body: { repoUrl, pipelineId, pipelineName, pipelineRunId, branch, commitId, obsUrl, category, source, sourceRunUrl }
```
- prod：`apig.openlibing.com`
- beta：华为云 APIG 实例域名（`*.apic.cn-southwest-2.huaweicloudapis.com`）
- 路径必须 `/action-api/` 前缀（IAM 认证分组）；`/openlibing-codecheck/` 为 APP 认证分组，OIDC 签名会 401

## 7. 安全设计

**鉴权**
- OBS / APIG 凭证全部来自 CI 流水线 OIDC -> 华为云 STS 临时凭证，不配置永久 AK/SK
- APIG 使用 V11-HMAC-SHA256 签名 + X-Security-Token，禁止 AppCode 明文

**敏感信息**
- SDK 日志对 Authorization / X-Security-Token / 临时 AK/SK 自动脱敏
- 插件日志不输出完整凭证，仅打印脱敏摘要

**硬编码**
- OBS 桶名、回调域名硬编码于插件（部署时确定的固定值）
- 不硬编码任何凭证

**审计日志**
- 记录上传成功/失败、回调成功/失败（含业务码）、报告文件清单
- 关键日志使用 sanitizePath 脱敏 IP
