# gitcode-token-header-auth — 技术设计

> 交付记录：本设计已随 PR https://gitcode.com/openlibing/openlibing-sca/pull/314（dev_gitcode_token -> release_20260923）合入实现，commit cbce184b（API header 鉴权）+ 2a516fe4（clone/fetch 凭据环境变量）。
> 业务 Issue: https://gitcode.com/openlibing/openlibing-sca/issues/74

## 方案概述

两部分改造，消除 GitCode 凭据在 URL / argv / 磁盘配置中的暴露：

1. **GitCode API 调用改用 `Authorization: Bearer {token}` 请求头**：在 `HttpClientUtil` 新增带 token 参数的 `get(url, token)` / `getResponse(url, token)` 重载（空 token 不携带鉴权头），`HttpUtil` 新增 `doGet(code, url, token)` 重载，各调用方按平台分流——gitcode 平台走 header 认证，gitee 平台保持 `access_token` 查询参数不变。
2. **git clone / fetch 凭据改走环境变量**：`CmdInjection` 新增 `runCmd(cmd, extraEnv)` 重载，`DownLoadFilesUtils` 的 clone / fetch 改用干净 URL，通过 `GIT_CONFIG_*` 环境变量向 git 子进程注入 `http.extraHeader`（`Authorization: Basic`，与 URL 内嵌 `user:token` 等价），token 不再出现在 URL、argv 或 `.git/config` 中。

## 架构决策

| 决策 | 理由 |
|------|------|
| 在 `HttpClientUtil` 新增 `get(url, token)` / `getResponse(url, token)` 重载而非改造所有调用点自建请求 | OkHttp 路径的 4+ 处调用（ScanCommonServiceImpl、queryRepoSizeKb）复用同一工具方法，改动集中、风格一致 |
| gitee/gitcode 双平台调用点在 URL 构建层分流：gitcode 分支不再拼接 token，调用时显式传 token | Gitee v5 API 不支持 Bearer header；分流保持 gitee 行为零变化 |
| `HttpUtil.doGet` 新增带 token 的重载，`getPrParams` 链路（urlGitCodeAdd）传递 token 用于 header | 该链路为 gitee/gitcode 共用，重载保持 gitee 老路径签名兼容 |
| HttpURLConnection 场景（buildApiUrl gitcode 分支）直接 `setRequestProperty("Authorization", "Bearer " + token)` | 与 `DownLoadFilesUtils.downLoadGitcodeSence` 现有先例一致 |
| `downloadScanossFile`/`buildScanossUrl` 双平台共用，调用方 `processScanossFiles` 已按平台 if/else 分流——方法增加平台参数：gitcode 分支 URL 不拼 token、HttpGet 加 Bearer header；gitee 分支保持 query 参数 | `buildDownloadUrl` 链路仅被 gitee（downLoadGiteeSence）调用不改 |
| `PrCommonName` 新增 `AUTHORIZATION_HEADER`/`BEARER_PREFIX` 常量，`TOKEN`/`ACCESS_TOKEN` 常量保留 | gitee 路径仍在使用，不删除避免大范围 churn |
| `CmdInjection` 新增 `runCmd(cmd, extraEnv)` 重载，ProcessBuilder 追加环境变量、不清空原有环境，原 `runCmd(cmd)` 委托新方法 | 单一入口注入认证环境变量，不影响既有调用方；不清空环境避免破坏 git 依赖的系统变量（PATH 等） |
| clone/fetch 凭据用 `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0`/`GIT_CONFIG_VALUE_0` 环境变量注入 `http.extraHeader: Authorization: Basic`，替代 URL 内嵌 `user:token` | git 原生机制（git >= 2.31），凭据仅存在于子进程环境块：不落盘（对比 credential helper / `.netrc`）、不进 argv、不持久化到 `.git/config` 的 `remote.origin.url`；Basic 头与原 URL 内嵌凭据语义等价 |
| 删除 `buildAuthUrl`，新增 `buildGitAuthEnv(user, token)`（`Base64(user:token)`，UTF-8） | 凭据构建收口在单一私有方法，便于审计与测试断言 |
| `fetchAndCheckoutPR` 增加 authEnv 参数，由 `cloneAndCheckoutPR` 构建后透传 | clone 与 fetch 复用同一份认证环境变量，避免重复构建与不一致 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `analysis/utils/HttpClientUtil.java` | 修改 | 新增 `get(String url, String token)` / `getResponse(url, token)` 重载，token 非空时加 Bearer header |
| `analysis/utils/HttpUtil.java` | 修改 | 新增 `doGet(String code, String url, String token)` 重载（空 token 不携带鉴权头） |
| `common/enums/PrCommonName.java` | 修改 | 新增 `AUTHORIZATION_HEADER` / `BEARER_PREFIX` 常量 |
| `dm/service/impl/ScanCommonServiceImpl.java` | 修改 | 4 处 buildXxxApiUrl 移除 gitcode 分支 token 拼接，`getFromPlatformApi` 按平台分流调用 |
| `dm/service/impl/IntegrationApiServiceImpl.java` | 修改 | urlGitCodeAdd / checkoutBranchFromGitcode / queryRepoSizeKb / buildRepoSizeCheckUrl 等 gitcode 分支改 header；`checkFileNum` / `checkRepoSizeAndSendToMq` 增加 token 参数 |
| `analysis/service/impl/OpenScanServiceImpl.java` | 修改 | buildApiUrl gitcode 分支改 header 认证 |
| `analysis/utils/security/DownLoadFilesUtils.java` | 修改 | buildScanossUrl gitcode 链路改 header（方法加平台参数分流）；clone/fetch 改干净 URL + `buildGitAuthEnv` 注入认证环境变量，删除 `buildAuthUrl` |
| `analysis/utils/security/CmdInjection.java` | 修改 | 新增 `runCmd(String[], Map<String,String>)` 重载（ProcessBuilder 追加环境变量），原方法委托 |
| 测试文件（HttpClientUtilTest / HttpUtilTest / ScanCommonServiceImplTest / IntegrationApiServiceImplTest / PrCommonNameTest / DownLoadFilesUtilsTest / CmdInjectionTest） | 修改 | 更新 URL 断言 + 新增 header 行为测试；新增 clone/fetch 不携带 token、env 注入 Basic 头断言；CmdInjectionTest 由 Runtime mock 改为 ProcessBuilder mock |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| GitCode 部分内部接口可能不接受 Bearer header | `downLoadGitcodeSence` 已在生产使用 Bearer header 验证过 GitCode 支持；改造后用户自测覆盖 PR 扫描、版本扫描链路 |
| 双平台分流遗漏导致 gitee 误用 header | 逐调用点核对 platform 判断分支；单测断言 gitee URL 仍含 access_token |
| URL 日志脱敏逻辑（LogSanitizer）依赖 token 位置 | header 化后 URL 天然不含 token，脱敏逻辑保留不删，属向后兼容 |
| `GIT_CONFIG_*` 注入机制依赖 git >= 2.31 | 运行环境（SCA 扫描执行机）需满足 git 版本要求，PR 评审风险项已确认 |
| 网关/代理可能剥离 Authorization 请求头 | 部署环境需确认不剥离；API 链路由用户自测、clone/fetch 链路由单测分别覆盖 |

## 跨仓影响

无。openlibing-platform-release 等仓的 token 拼接调用不在本次范围，后续另行处理。
