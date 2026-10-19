# openlibing-upload-sarif 通用 SARIF 上传插件

## 需求背景

OpenLibing 工作流平台已支持多类静态扫描工具接入（CodeQL、CodeArts Check、SpotBugs 等）。扫描工具产出的结果以 SARIF 2.1.0 格式为载体，需要统一上传到华为云 OBS 对象存储并通过 APIG 网关回调通知 OpenLibing 服务入库展示。

早期各扫描插件各自实现 OBS 上传（`obsutil` CLI 方式）与回调链路，存在以下问题：

1. **上传实现不统一**：不同插件分别下载/配置 `obsutil` CLI，上传逻辑各自维护，与 `pre-commit-action` 的上传机制不一致，维护成本高。
2. **路径结构不统一**：OBS 路径前缀与时间戳格式在各插件间存在差异（如 `build-result.json` 单独放 `code-arts-check-results/` 前缀、时间戳无小时精度），后端解析与运营采集需要做兼容。
3. **凭证管理不统一**：早期依赖 workflow 中显式运行 `huaweicloud-oidc-auth` 插件注入临时凭证，插件本身不含换证能力。
4. **代码上下文缺失**：部分扫描工具（如 SpotBugs）的原生 SARIF 只输出行号、不含代码文本，后端告警可读性差。

需要一个**通用 SARIF 上传插件**，作为任意扫描工具产物的统一入口，并在实现上与 `pre-commit-action` 对齐 OBS 上传机制、路径结构与凭证方案。

## 功能描述

新增 GitCode Action 插件 `openlibing-upload-sarif`：

- **通用 SARIF 上传**：不绑定任何具体扫描工具，`sarif_file` 支持单文件 / 多文件 / 目录（自动扫描目录下所有 `.sarif` 文件）/ 逗号分隔多值
- **自动识别工具名**：从 `runs[0].tool.driver.name` 提取工具名，动态拼装 OBS 路径前缀（如 `spotbugs-results`）；无法解析时兜底 `code-arts-check-results`
- **自动补齐 `region.snippet`**：SARIF 缺少代码上下文时，按 `artifactLocation.uri` + 行号从源码根目录读取代码补齐（`source_path` 支持多值，未配置时按文件名在 `ATOMGIT_WORKSPACE` 下递归查找）
- **OIDC 免静态凭证**：插件内嵌 `@openlibing/huaweicloud-oidc-client` SDK 自包含换证（自申请 OIDC ID Token + 调用华为云 STS 换取临时凭证），无需 workflow 运行 `huaweicloud-oidc-auth` 插件，仅需声明 `permissions: id-token: write`
- **OBS 上传统一为 `esdk-obs-nodejs` SDK**：与 `pre-commit-action` 对齐，上传对象设置 `public-read`（后端匿名 HTTP GET 下载），server 由 OIDC SDK `configure()` 动态返回 region 拼装 `https://obs.{region}.myhuaweicloud.com`，不写死区域
- **OBS 路径结构统一**：`{toolPrefix}/{repoBaseName}/{yyyyMMdd}.{HH}/{runId|manual}/{fileName}`，`build-result.json` 与 SARIF 同一路径（首个工具目录），时间戳精确到小时
- **APIG 回调**：上传成功后经 `/action-api/codescan/v1/result/receive` 回调 OpenLibing（V11-HMAC-SHA256 签名 + `X-Security-Token`，支持 prod / beta 环境）
- **失败重试**：OBS 上传与 APIG 回调均采用指数退避重试（默认 3 次），回调失败仅 WARN 不影响最终结果

**不做什么**：

- 不在插件内运行任何扫描工具（扫描由 workflow 前置步骤完成，插件只负责上传）
- 不做 SARIF 生成/转换（`region.snippet` 补齐是唯一的内容增强）
- 不改造后端 `openlibing-codecheck`（SARIF 解析路由为既有能力）
- 不保留 `obsutil` CLI 上传路径（已整体迁移到 `esdk-obs-nodejs` SDK）

## 验收标准

- [ ] `sarif_file` 支持单文件 / 多文件 / 目录（扫描 `.sarif`）/ 逗号分隔多值；路径不存在或最终未收集到任何 SARIF 文件时报错退出，单个目录为空时仅告警
- [ ] 工具名从 `runs[0].tool.driver.name` 正确提取，OBS 前缀按 `{toolName}-results` 动态拼装，缺失时兜底 `code-arts-check-results`
- [ ] SARIF 缺少 `region.snippet` 时按 `uri`+行号读源码补齐并写回；已有 snippet 的 result 跳过；源码不可读时静默跳过
- [ ] OBS 上传使用 `esdk-obs-nodejs` SDK + OIDC 临时凭证，对象 `public-read`；server 由 `configure()` 动态 region 拼装
- [ ] OBS 路径结构为 `{前缀}/{仓库名}/{yyyyMMdd}.{HH}/{runId|manual}/{文件名}`，时间戳精确到小时，`runId` 缺失用 `manual` 兜底
- [ ] `build-result.json` 与 SARIF 同一路径（首个工具目录），单文件时 `buildings` 为对象、多文件时为数组
- [ ] OBS 上传与 APIG 回调内置指数退避重试（默认 3 次）；回调失败仅 WARN，SARIF 上传成功即视为成功
- [ ] APIG 回调 payload 字段正确（repoUrl / pipelineId / pipelineName / pipelineRunId / branch / commitId / obsUrl（恒为数组）/ category / source / sourceRunUrl）
- [ ] 插件不打印凭证明文，日志对敏感信息脱敏
- [ ] `npm run build` 产出 `dist/index.js` 可运行（ncc 打包），zip 产物可交付

## 影响范围

- 新增/改造仓：`openlibing/upload-sarif-action`（本地目录 `openlibing-upload-sarif`），开发分支 `feat-full-check-compliance`
- 复用：OBS 桶 `openlibing-gitcode-action`、APIG `/action-api` 回调、`@openlibing/huaweicloud-oidc-client` SDK、`esdk-obs-nodejs`
- 对齐对象：`pre-commit-action`（OBS 上传机制、路径结构、动态 region、`sarif-file` 多值输入）
- 不涉及：`openlibing-codecheck` 后端
