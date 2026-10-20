# gitcode-token-header-auth — 实现任务

> 交付记录：随 PR https://gitcode.com/openlibing/openlibing-sca/pull/314（dev_gitcode_token -> release_20260923）合入，commit cbce184b（Task 1-7）+ 2a516fe4（Task 9-11）。

## 进度: 10/11 complete

- [x] Task 1: `HttpClientUtil` 新增 `get(url, token)` / `getResponse(url, token)` 重载（Bearer header），`HttpUtil` 新增 `doGet(code, url, token)` 重载，`PrCommonName` 新增 `AUTHORIZATION_HEADER` / `BEARER_PREFIX` 常量
  - **安全约束 SEC-1**：token 为 null/blank 时不添加 Authorization header（避免发送 `Bearer null`）。验证：HttpClientUtilTest / HttpUtilTest 断言空 token 时请求头无 Authorization
- [x] Task 2: `ScanCommonServiceImpl` 4 处 buildXxxApiUrl 按 platform 分流（`getFromPlatformApi`）——gitcode 分支 URL 不拼 token，调用处传 token 走 header；gitee 分支行为不变
  - **安全约束 SEC-2**：gitcode 分支构建的 URL 不得含 `access_token`；gitee 分支保持 query 参数不变。验证：ScanCommonServiceImplTest 断言 gitcode URL 无 token、gitee URL 仍含
- [x] Task 3: `IntegrationApiServiceImpl` 改造：urlGitCodeAdd 返回无 token URL 并透传 token；checkoutBranchFromGitcode / queryRepoSizeKb / checkFileNum / checkRepoSizeAndSendToMq（gitcode 分支）改 header
  - **安全约束 SEC-2**：同上。验证：IntegrationApiServiceImplTest + 代码走查 URL 构建点无 token 拼接
- [x] Task 4: `OpenScanServiceImpl.buildApiUrl` gitcode 分支改 header 认证（HttpURLConnection setRequestProperty）；`DownLoadFilesUtils.downloadScanossFile`/`buildScanossUrl` 增加平台参数分流——gitcode 分支 URL 不拼 token、HttpGet 加 Bearer header，gitee 分支行为不变
  - **安全约束 SEC-2 / SEC-3**：URL 无 token；不新增任何打印 header 值的日志语句。验证：代码走查
- [x] Task 5: 更新受影响单测断言（URL 不再含 token / gitee 仍含），新增 header 行为测试
  - 覆盖 SEC-1（空 token 无 header）、SEC-2（URL 断言）、SEC-4（401 走既有异常路径不降级放行）
- [x] Task 6: 编译 + 相关单测运行验证（全量单测 1558 个通过）
- [x] Task 7: AI 自检（生成前约束清单逐项核对，含 4 条 SEC 约束）+ 提交 commit（cbce184b）
- [ ] Task 8: 事后安全审查：用户触发 `gitcode-security-check` 验证 SEC-1 ~ SEC-4 实现符合性（合并前完成，形成设计→编码→审查闭环）
- [x] Task 9: `CmdInjection` 新增 `runCmd(cmd, extraEnv)` 重载（ProcessBuilder 追加环境变量，不清空原有环境），原 `runCmd(cmd)` 委托新方法；CmdInjectionTest 由 Runtime mock 改写为 ProcessBuilder mock
  - 验证：CmdInjectionTest 断言环境变量追加且原环境保留
- [x] Task 10: `DownLoadFilesUtils` clone/fetch 凭据改环境变量注入：删除 `buildAuthUrl`，新增 `buildGitAuthEnv`（`Base64(user:token)` → `GIT_CONFIG_COUNT=1` / `GIT_CONFIG_KEY_0=http.extraHeader` / `GIT_CONFIG_VALUE_0=Authorization: Basic <encoded>`）；`cloneAndCheckoutPR` / `downloadVersion` 的 clone 与 `fetchAndCheckoutPR` 的 fetch 改用干净 URL + authEnv
  - **安全约束 SEC-2 扩展**：token 不出现在 URL、argv 或磁盘配置（`.git/config`）中。验证：DownLoadFilesUtilsTest 断言 clone/fetch 命令参数不含 token、env 注入 Basic 头
- [x] Task 11: clone/fetch 相关测试运行验证（CmdInjectionTest 11 + DownLoadFilesUtilsTest 92 通过，commit 2a516fe4）

安全设计文档：[security-design.md](./security-design.md) · 威胁模型：[threat-model.md](./threat-model.md)
