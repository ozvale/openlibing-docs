# precommit-report-sarif-upload — 设计

## 1. 方案设计

pre-commit 检查完成后，将各工具生成的报告统一转成 SARIF 并归档到 OBS + 回调 openlibing 后端。

整体链路：

```
CI runner (push/schedule/workflow_dispatch)
  -> pre-commit 运行钩子（gitleaks 输出 /tmp/pre-commit-reports/gitleaks.json）
  -> pre-commit-action 读取报告目录
  -> gitleaks JSON -> SARIF 2.1.0 转换
  -> OIDC 换取华为云临时凭证（@openlibing/huaweicloud-oidc-client）
  -> esdk-obs-nodejs 上传 OBS 桶 openlibing-gitcode-action
  -> APIG 回调 codecheck 接口（V11 签名 + X-Security-Token）
```

关键决策：

| 决策点 | 方案 | 理由 |
|-------|------|------|
| 报告目录 | `/tmp/pre-commit-reports/`（input `report-dir` 可覆盖） | CI 机器临时目录，不污染代码仓 |
| gitleaks 报告格式 | json | 通用性好，插件统一转 SARIF，未来其他工具可复用转换器 |
| OBS 上传 | OIDC 临时凭证 + esdk-obs-nodejs | 零 Secret，参考 huaweicloud-oidc-sdk-nodejs 的 test-obs-action |
| OBS 路径 | `pre-commit-reports/<仓库名>/<日期>/<runId>/gitleaks.sarif` | 与 code-arts-check-results 前缀区分 |
| APIG 回调 | OIDC callApig（V11-HMAC-SHA256 + X-Security-Token） | 凭证统一走 OIDC，禁止 AppCode 明文 |
| PR 触发 | 只检查不回调 | PR 增量检查不产生全量报告，避免噪音 |

## 2. 实现逻辑设计

### pre-commit-action 主流程扩展（index.js run()）

```
[1] 检查 Python 环境
[2] 安装 pre-commit（含镜像测速）
[3] 定位代码目录
[4] 检查 .pre-commit-config.yaml
[5] 构建运行参数
[6] 运行 pre-commit 检查（记录 checkFailed）
[7] 新增：读取报告目录
    - 目录默认 /tmp/pre-commit-reports/（input report-dir 覆盖）
    - 扫描目录下 *.json 文件
[8] 新增：PR 类型判断
    - eventName ∈ {mr, pull_request, note} 且有 baseRef -> 跳过上传回调
[9] 新增：JSON -> SARIF 转换
[10] 新增：OIDC 换证 + OBS 上传（esdk-obs-nodejs putObject）
[11] 新增：APIG 回调 codecheck 接口（callApig POST）
[12] 按 checkFailed 决定退出码（上传失败只 warning）
```

### SARIF 转换规则（gitleaks JSON -> SARIF 2.1.0）

gitleaks JSON 数组元素 → SARIF result 映射：

| gitleaks 字段 | SARIF 字段 |
|--------------|-----------|
| RuleID | ruleId |
| Description | rule 的 shortDescription.text |
| File | locations[0].physicalLocation.artifactLocation.uri |
| StartLine / EndLine | region.startLine / endLine |
| StartColumn / EndColumn | region.startColumn / endColumn |
| Match | message.text（摘要） |
| Commit | partialFingerprints + properties |

SARIF 结构：
- version: "2.1.0"
- runs[0].tool.driver: name=gitleaks, version, rules[]
- runs[0].results[]: ruleId, level(="error"/"warning"), message.text, locations, partialFingerprints, properties
- runs[0].originalUriBaseIds / invocation：执行上下文（仓库、runId）放入 properties

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
await client.putObject({ Bucket, Key, SourceFile });
```

### APIG 回调（参考 SDK callApig）

```javascript
const { callApig } = require('@openlibing/huaweicloud-oidc-client');
await callApig('POST', callbackUrl, JSON.stringify(payload));
```

payload 复用 upload-sarif 结构：repoUrl / pipelineId / pipelineName / pipelineRunId / branch / commitId / obsUrl / category / source / sourceRunUrl。obsUrl 传 SARIF 下载地址（`https://openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com/<key>`），category 标识 pre-commit。

## 3. 类设计

不涉及后端类。插件侧模块化拆分：

| 模块 | 职责 |
|------|------|
| index.js | 主流程编排（现有 run() 扩展） |
| sarif-converter.js | gitleaks JSON -> SARIF 2.1.0 转换 |
| obs-uploader.js | OIDC 换证 + esdk-obs-nodejs 上传 |
| apig-callback.js | callApig 回调 codecheck（或内联于 index.js） |

考虑插件现有风格（单 index.js + ncc 打包），倾向：新增独立模块文件便于单测，ncc 会自动内联。

## 4. 数据模型设计

SARIF 2.1.0 标准结构（上传物）：
- `version`: "2.1.0"
- `$schema`: sarif-2.1.0 schema URL
- `runs`: [{ tool.driver, results[] }]

OBS 对象路径模型：
`pre-commit-reports/{repoBaseName}/{yyyyMMdd.HH}/{runId}/gitleaks.sarif`

APIG 回调 payload（对齐 upload-sarif）：
`{ repoUrl, pipelineId, pipelineName, pipelineRunId, branch, commitId, obsUrl, category, source: 'GITCODE_ACTION', sourceRunUrl }`

## 5. 性能设计

- 报告文件为小文件（KB 级），putObject 直传即可，无需分段
- 凭证缓存由 SDK getCredentials 内部处理（1 小时有效期自动刷新）
- 转换逻辑为单次内存遍历，无性能瓶颈

## 6. API接口设计

### OBS 上传（对外可读 URL）
```
GET https://openlibing-gitcode-action.obs.cn-southwest-2.myhuaweicloud.com/pre-commit-reports/<repo>/<date>/<runId>/gitleaks.sarif
```

### APIG 回调（插件 -> openlibing 后端）
```
POST https://apig.openlibing.com:443/openlibing-codecheck/codescan/v1/result/receive
Content-Type: application/json
Authorization: V11 签名（SDK callApig 自动生成）
X-Security-Token: <OIDC 临时凭证>
Body: { repoUrl, pipelineId, pipelineName, pipelineRunId, branch, commitId, obsUrl, category, source, sourceRunUrl }
```

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
- 记录上传成功/失败、回调成功/失败、报告文件清单
- 关键日志使用 sanitizePath 脱敏 IP
