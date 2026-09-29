# gitcode-token-header-auth

## 需求背景

openlibing-sca 服务中所有调用 GitCode API 的请求均通过 URL 拼接 `?access_token={token}` 传递凭证。token 暴露在 URL 中，容易泄露到网关日志、访问日志、APM 链路追踪等中间环节；现有代码多处依赖 `LogSanitizer.sanitizeForLog` 做事后脱敏，属于被动补救。代码库中 `DownLoadFilesUtils.downLoadGitcodeSence` 已有 `Authorization: Bearer` header 认证先例，GitCode API 支持 header 认证方式。

除 API 调用外，git clone / fetch 链路通过 clone URL 内嵌 `user:token` 传递凭证：token 会随 clone 持久化到 `.git/config` 的 `remote.origin.url`，并暴露在进程命令行参数与错误输出中。

- 业务 Issue: https://gitcode.com/openlibing/openlibing-sca/issues/74
- 交付 PR: https://gitcode.com/openlibing/openlibing-sca/pull/314（dev_gitcode_token -> release_20260923，已合入）

## 功能描述

**做什么**：

1. **GitCode API 调用从 URL 拼接 token 改为 `Authorization: Bearer {token}` 请求头传递**，涉及调用点：
   - `ScanCommonServiceImpl`：fileContent / compare / prCommits / prFiles 4 处 URL 构建（gitcode 分支，经 `getFromPlatformApi` 按平台分流）
   - `IntegrationApiServiceImpl` 7 处：urlGitCodeAdd（→ getPrParams）、buildFileCheckUrl（→ getPrFileSize / checkFileNum 增加 token 参数）、checkoutBranchFromGitcode、queryRepoSizeKb、buildRepoSizeCheckUrl（→ sendToMqBasedOnRepoSize / checkRepoSizeAndSendToMq 增加 token 参数）
   - `OpenScanServiceImpl.buildApiUrl`：contents API URL 构建（gitcode 分支）
   - `DownLoadFilesUtils.buildScanossUrl`：scanoss.json 下载 URL（`downloadScanossFile` 增加平台参数分流；`buildDownloadUrl` 为 gitee-only 链路不改）
2. **git clone / fetch 凭据改走环境变量**：
   - `CmdInjection` 新增 `runCmd(cmd, extraEnv)` 重载（ProcessBuilder 追加环境变量，不清空原有环境），原 `runCmd(cmd)` 委托新方法
   - `DownLoadFilesUtils`：`cloneAndCheckoutPR` / `downloadVersion` 的 clone 与 `fetchAndCheckoutPR` 的 fetch 改用干净 URL + `GIT_CONFIG_*` 环境变量注入 `http.extraHeader`（`Authorization: Basic`，与 URL 内嵌凭据等价），删除 `buildAuthUrl`，新增 `buildGitAuthEnv`

**不做什么**：

- Gitee 平台调用保留 `access_token` 查询参数（Gitee v5 API 不支持 Bearer header）
- 不修改 openlibing-platform-release 等其他仓库
- 不修改 WeChat 等非 GitCode 的 access_token 调用
- 不引入 git credential helper / `.netrc` 等其他凭据存储机制（避免凭据落盘）

## 验收标准（已随 PR #314 合入验证）

- [x] 所有 GitCode API 调用均通过 Authorization header 传递 token，URL 中不再出现 token
- [x] Gitee 平台调用行为保持不变（仍用 access_token 查询参数）
- [x] git clone / fetch 不再将 token 内嵌进 URL：token 不出现在 URL、argv 或磁盘配置（`.git/config`）中
- [x] 相关单元测试补充并通过：全量单测 1558 个通过（commit 1 验证）；CmdInjectionTest 11 + DownLoadFilesUtilsTest 92 相关测试通过（commit 2 验证）
- [x] 构建验证通过（CI 流水线通过，PR 标签 ai-assisted / ci-pipeline-passed / lgtm / approved）

## 影响范围

- `openlibing-sca` 仓 `dm/service/impl`、`analysis/service/impl`、`analysis/utils`（HttpClientUtil / HttpUtil / DownLoadFilesUtils / CmdInjection）、`common/enums/PrCommonName`
- PR 扫描、版本扫描、issue 继承等调用 GitCode API 的链路
- PR 代码下载 / 版本代码下载的 git clone / fetch 链路
