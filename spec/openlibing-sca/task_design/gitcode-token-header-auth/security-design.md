# 安全设计：gitcode-token-header-auth

对应威胁模型：[threat-model.md](./threat-model.md) · 业务 Issue: https://gitcode.com/openlibing/openlibing-sca/issues/74 · 交付 PR: https://gitcode.com/openlibing/openlibing-sca/pull/314

## 1. 认证授权

- **方案**：认证凭证与机制不变（平台 token，来源 `platformUtil.getPlatformToken`），仅传输方式变更：
  - **API 调用**：从 URL query 参数改为 `Authorization: Bearer {token}` 请求头。选型理由：`DownLoadFilesUtils.downLoadGitcodeSence` 已在生产使用该方式调用 GitCode `/pulls/{n}/files` 接口，兼容性已验证；不引入 OAuth2/mTLS 等新协议（超出本次范围且收益不成比例）。
  - **git clone / fetch（SEC-2 扩展）**：原实现把 `user:token` 内嵌进 clone URL，token 会持久化到 `.git/config` 的 `remote.origin.url` 并暴露在进程命令行参数中。改为 `GIT_CONFIG_*` 环境变量向 git 子进程注入 `http.extraHeader: Authorization: Basic`（与 URL 内嵌凭据语义等价），凭据仅存在于子进程环境块，不落盘、不进 argv。
- **凭证生命周期**：签发/存储/轮换/吊销均不变（token 由平台侧管理，SCA 侧每次调用时解析获取）。
- **越权防护**：无变化（不涉及授权模型调整）。
- **边界约束**：仅 gitcode 平台调用走 header；gitee 调用保持 query 参数（Gitee v5 API 不支持 Bearer header，改动会导致 401 故障——安全设计不能以牺牲可用性为代价）。

## 2. 输入输出

- **token 空值防护（安全约束 SEC-1）**：token 为 null/blank 时不添加 Authorization header（避免发出 `Bearer null` 这类无效凭证请求），由 GitCode 返回 401 走既有失败处理。实现位置：`HttpClientUtil.get(url, token)` / `HttpUtil.doGet(code, url, token)` 重载内部判断。
- **URL 输出（安全约束 SEC-2）**：gitcode 路径构建的 URL 不得包含 `access_token`。所有 `buildXxxApiUrl` 的 gitcode 分支移除 token 拼接；clone/fetch 链路使用干净 URL（不含 `user:token`），认证信息经 `buildGitAuthEnv` 以环境变量注入。
- **argv 输出（SEC-2 扩展）**：clone/fetch 命令参数中不得出现 token；token 仅通过 `runCmd(cmd, extraEnv)` 的环境变量通道进入 git 子进程。
- **日志输出（安全约束 SEC-3）**：禁止将 Authorization header 值写入任何日志；URL 可正常记录（天然无凭证）。`LogSanitizer` 保留用于 gitee 路径兜底，不删除。

## 3. 数据保护

- **分类分级**：GitCode token = 机密级；API URL（改造后）= 内部级。
- **传输加密**：沿用 HTTPS，`SsrfsafeUrlUtil.validateUrl` 协议白名单不变。header 与 query 在 TLS 下防窃听能力等价，差异在于**日志/追踪通道**：header 不会被网关与中间件默认记录，query 会。
- **磁盘驻留（SEC-2 扩展）**：clone/fetch 改造后 `.git/config` 的 `remote.origin.url` 不再包含凭据，token 不在磁盘任何位置驻留；环境变量仅在 git 子进程生命周期内可见。
- **脱敏策略**：gitee 路径 URL 入日志前继续经 `LogSanitizer.sanitizeForLog`；gitcode 路径 URL 无需脱敏。

## 4. 依赖供应链

- **新增依赖**：无。`OkHttp`（HttpClientUtil）、`Apache HttpClient`（HttpUtil / DownLoadFilesUtils）、`HttpURLConnection`（OpenScanServiceImpl）、`ProcessBuilder`（CmdInjection）均为既有依赖/标准库。
- 无私有源、无 replace 引入。

## 5. 部署运行时

- **配置管理**：无配置变更、无凭证变更；token 获取链路（DB/配置解密）不动。
- **环境依赖**：`GIT_CONFIG_*` 注入机制依赖 git >= 2.31，扫描执行机需满足版本要求。
- **审计日志**：现有 URL 日志在改造后天然不含 token，满足"凭证不入日志"要求；无需新增审计字段。
- **告警/入侵检测**：无新增要求（不新增数据流与暴露面）。

## 6. 失败模式

- **Fail Secure（安全约束 SEC-4）**：token 无效/缺失 → GitCode 返回 401 → 各调用点沿用既有失败路径（`ScaException` / `Optional.empty()` / 返回 1 走大队列兜底），不允许任何"鉴权失败仍放行"的降级。
- **git 版本不满足**：低版本 git 不识别 `GIT_CONFIG_*` 机制时认证不生效，clone/fetch 以 401 失败（fail secure），不会回退到 URL 内嵌凭据方式。
- **应急响应**：如 header 方式在某个 GitCode 接口出现不兼容（返回 401/403），回滚方案为 revert 本次 commit，恢复 URL 拼接方式；token 本身未变，无需轮换。

## 7. 验证计划

| 约束 | 验证方式 | 时机 |
|------|---------|------|
| SEC-1 token 空值不加 header | 单测：token 为 null/blank 时请求头无 Authorization（HttpClientUtilTest / HttpUtilTest） | Phase 3 编码时 |
| SEC-2 gitcode URL 无 token | 单测：断言 gitcode 分支构建的 URL 不含 `access_token`，gitee 分支仍含 | Phase 3 编码时 |
| SEC-2 扩展 clone/fetch 凭据 | 单测：clone/fetch 命令的 URL 参数不含 token；`GIT_CONFIG_VALUE_0` 为 `Authorization: Basic`（DownLoadFilesUtilsTest） | Phase 3 编码时（commit 2a516fe4） |
| SEC-3 日志不含凭证 | 代码走查（无 header 值日志语句）+ 事后 `gitcode-security-check` 扫描 | Phase 3 后事后审查 |
| SEC-4 失败不降级放行 | 单测：401 响应走既有异常路径；回归现有失败处理用例 | Phase 3 编码时 |
| 整体功能不回退 | 用户自测 PR 扫描、版本扫描链路 | 用户自测环 |

事后审查闭环：SEC-1 ~ SEC-4 的实现符合性交由 `gitcode-security-check` 在 Phase 3 交付后验证（用户触发或合并前）。
