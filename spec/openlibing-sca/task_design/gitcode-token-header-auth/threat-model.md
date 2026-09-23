# 威胁模型：gitcode-token-header-auth

## 资产清单

| 资产                                                  | 分类                      | 责任域           | 备注                                                               |
| ----------------------------------------------------- | ------------------------- | ---------------- | ------------------------------------------------------------------ |
| GitCode 平台 token（gitcodeToken / majunAccessToken） | 机密                      | SCA 服务         | 来源 `platformUtil.getPlatformToken`，按 projectId 解析，不入仓    |
| 调用 GitCode API 的完整 URL                           | 敏感（现状含 token）      | SCA 服务         | 改造目标：URL 中不再出现 token                                     |
| `.git/config` 的 `remote.origin.url`                  | 机密（现状含 user:token） | SCA 扫描工作目录 | clone 内嵌凭据随工作目录落盘；改造目标：干净 URL                   |
| git 子进程命令行参数（argv）                          | 敏感（现状含 user:token） | SCA 服务         | argv 可经 `ps` / 进程列表 / 错误输出暴露；改造目标：凭据走环境变量 |

## 信任边界

- SCA 服务 → GitCode API：跨信任域，HTTPS（`SsrfsafeUrlUtil.validateUrl` 已校验协议白名单）
- SCA 服务 → 网关/访问日志/APM 链路追踪：**被动记录面，本次改造的主要泄露通道**（网关与中间件默认记录完整 URL，但不记录请求头）
- SCA 服务 → git 子进程：跨进程边界，凭据经环境变量传递；argv 与环境块的可见范围不同（argv 对同机其他用户可见，环境块仅限进程自身与调试接口）

## 数据流

1. `ScanCommonServiceImpl` / `IntegrationApiServiceImpl` / `OpenScanServiceImpl` / `DownLoadFilesUtils`（scanoss 下载链路）从 `platformUtil.getPlatformToken` 取得 token
2. **API 调用现状**：token 拼入 URL query（`?access_token=...`）→ 经 OkHttp / Apache HttpClient / HttpURLConnection 发出 → 全链路 URL 可见于日志与追踪
3. **API 调用目标**：token 放入 `Authorization: Bearer {token}` 请求头 → URL 不含凭证，日志与追踪天然干净
4. **clone/fetch 现状**：`user:token` 内嵌 clone URL → `CmdInjection.runCmd(cmd)` 执行 → token 暴露在 argv，并随 clone 持久化到 `.git/config` 的 `remote.origin.url`
5. **clone/fetch 目标**：干净 URL + `buildGitAuthEnv` 生成认证环境变量（`GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_0`/`GIT_CONFIG_VALUE_0` → `http.extraHeader: Authorization: Basic`）→ `runCmd(cmd, extraEnv)` 注入 git 子进程 → URL / argv / 磁盘配置均不含凭据

## STRIDE 评估

| 资产               | S   | T   | R   | I              | D      | E      | 缓解措施                                                                                                                                                                                 |
| ------------------ | --- | --- | --- | -------------- | ------ | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitCode 平台 token | 低  | 低  | 中  | **高**         | 无变化 | 无变化 | **本次改造**：API 调用 token 从 URL query 移入 Authorization header；clone/fetch 凭据从 URL/argv 移入 `GIT_CONFIG_*` 环境变量；HTTPS 传输；日志不记录 header 值；`LogSanitizer` 保留兜底 |
| API URL            | 低  | 低  | 低  | 中             | 无变化 | 无变化 | 改造后 URL 不含凭证，可直接入日志                                                                                                                                                        |
| `.git/config`      | 低  | 低  | 低  | **高**（现状） | 无变化 | 无变化 | 改造后 `remote.origin.url` 为干净 URL，凭据不再落盘                                                                                                                                      |
| git 子进程 argv    | 低  | 低  | 低  | **高**（现状） | 无变化 | 无变化 | 改造后 argv 仅含干净 URL，凭据经环境块传递                                                                                                                                               |

- **I（信息泄露）为本次核心威胁**：
  - API 链路：token 拼在 URL 中会被网关访问日志、Nginx/代理日志、APM trace、`LOGGER.info` 等多通道固化记录。现状的 `LogSanitizer.sanitizeForLog` 只覆盖显式调用点，属被动补救。
  - clone/fetch 链路：token 内嵌 URL 后持久化到磁盘（`.git/config`）并暴露在 argv，泄露面比 API 链路更持久。
- **R（抵赖）**：URL 含 token 时日志需脱敏后才能作为审计证据；header 化后审计日志天然合规。

## 残余风险（本次范围外，显式记录）

- Gitee 平台调用仍使用 `access_token` 查询参数（Gitee v5 API 不支持 Bearer header）：指向 gitee 的 URL 仍可能进入日志，依赖既有 `LogSanitizer` 缓解。后续如 Gitee 支持 header 认证再行改造。
- clone/fetch 的 `Authorization: Basic` 仍以 `Base64(user:token)` 形式传输，HTTPS 下与原 URL 内嵌凭据防护能力等价；`GIT_CONFIG_*` 机制依赖 git >= 2.31，低版本执行机认证不生效（fail secure，见 security-design.md 失败模式）。
- token 在服务内存中的生命周期不变，本次不涉及轮换/吊销机制调整。

## 关键决策

- 认证方式不变（平台 token），仅传输位置变更：API 从 URL query 改为 `Authorization: Bearer` header；clone/fetch 从 URL 内嵌改为 `GIT_CONFIG_*` 环境变量注入 `http.extraHeader`。依据：`DownLoadFilesUtils.downLoadGitcodeSence` 已在生产验证 GitCode 支持 Bearer header；`GIT_CONFIG_*` 为 git 原生机制
- 不新增依赖、不变更配置，改动收敛在 HTTP 调用层与命令执行层（HttpClientUtil / HttpUtil / CmdInjection / DownLoadFilesUtils）
- 凭据构建收口单一方法（`buildGitAuthEnv`），便于审计与测试断言
