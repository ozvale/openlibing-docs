# pre-commit-action — AI Memory

## 架构与职责边界

- pre-commit-action 插件职责：执行 pre-commit 检查 + 读取约定目录下 `*.sarif` 上传 OBS + APIG 回调 openlibing 后端。**不内置任何 SARIF 转换器**，JSON→SARIF 转换由业务仓负责（如 detect-secrets/gitleaks 钩子脚本）。
- 数据源优先级：① 输入 `sarif-file`（文件/目录/逗号多值，优先于 report-dir）；② `report-dir` 目录下 `*.sarif`；③ 均无且日志有失败钩子时走兜底日志解析。同一工具已提供报告则直接使用，不再日志解析。
- 兜底日志解析支持工具（第一批，新增需扩展 tool-parsers.js）：clang-tidy / bandit / gosec / spotbugs / rust-clippy / eslint / gitleaks / detect-secrets。不支持的工具仅告警"未查询到 sarif 文件，且暂不支持日志自动解析"，不生成报告。
- PR 类型触发（mr / pull_request / note）只做检查不回调；版本级触发（push / workflow_dispatch / schedule）检查发现告警不按失败退出，仅 PR 门禁按失败退出（exit 1）。
- 上传/回调失败仅告警不阻断检查结果；回调校验 HTTP 状态 + 响应体业务码（后端业务错误恒为 HTTP 200，只看状态会误报成功）。

## OBS 与回调约定

- OBS 桶：`openlibing-gitcode-action`，对象 `ACL: public-read`（后端匿名 HTTP GET 下载）。
- OBS 路径结构：`pre-commit-results/{仓库名}/{yyyyMMdd}.{HH}/{runId|manual}/{文件名}`（与 openlibing-upload-sarif 的 `{toolName}-results` 共用同一结构，仅前缀不同；时间戳为 `yyyyMMdd.HH`）。
- OBS server 动态构造：`https://obs.${region}.myhuaweicloud.com`，region 来自 OIDC SDK 默认配置，禁止写死。
- 回调路径必须 `/action-api/` 前缀（IAM 认证分组，适用 OIDC V11 签名）；`/openlibing-codecheck/` 为 APP 认证分组，OIDC 签名会 401。
- 凭证全部来自 OIDC 临时凭证（OIDC → 华为云 STS），配合 `permissions.id-token: write`，禁止永久 AK/SK / AppCode 明文。
- OBS 上传与 APIG 回调必须实现指数退避重试（默认 3 次）防止数据丢失。

## 实现踩坑

- `esdk-obs-nodejs` 的 ObsClient 构造是异步的，构造后必须 `await Promise.resolve()` 等待 initFactory 完成再 putObject，否则签名上下文竞态。
- Node 16 runner 需要 bundle `undici`（ncc 打包后 dist 需自包含）。
- 回调 payload 的 `obsUrl` 字段必须传数组（后端 DTO 是 `List<String>`）。
- GitHub Action 用 `env-type` 区分 prod（apig.openlibing.com）/ beta（华为云 APIG 实例域名）。
- SARIF 的 `partialFingerprints.primaryLocationLineHash` 由业务仓转换脚本生成；缺失时后端 StandardSarifParser 兜底 `sha256(uri|startLine|ruleId)`，保证指纹非空。
