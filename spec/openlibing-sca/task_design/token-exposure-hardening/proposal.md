# token-exposure-hardening — gitee 文件检查 token 移出 URL 与 ScanossFileDto 脱敏（#140）

## 需求背景

对应安全 Issue：openlibing/openlibing-sca#140（Labels: 安全问题）
链接：https://gitcode.com/openlibing/openlibing-sca/issues/140

问题一：`IntegrationApiServiceImpl.buildFileCheckUrl`（`getPrFileSize` 调用链）的 gitee 分支把平台 access_token 直接拼进外发 API URL 查询参数（issue 引用的原 L540-547），token 明文出现在 URL 中，易经访问日志、网关日志、异常堆栈、代理记录泄露；原注释"gitee 仅支持查询参数鉴权"不成立——Gitee API v5 支持 `Authorization: Bearer`（同批 #85 已核实并整改，见本仓 spec 目录 `gitee-token-bearer-header`）。

问题二（issue 补充风险点）：`com.openlibing.sca.common.domain.ScanossFileDto` 使用 Lombok `@Data`，自动生成的 `toString()` 包含 `token` 字段。当前调用方未打印该 DTO，属"碰巧安全"；后续任何 `LOGGER.info("dto={}", dto)` 都会导致 token 明文落日志。

现状与调用链（代码核实）：

- `getPrFileSize`（L508-531）→ `buildFileCheckUrl` + `checkFileNum(url, headerToken)`；
- `checkFileNum`（L609-636）→ `HttpClientUtil.get(url, token)`（`HttpClientUtil` L225-231），内部 `addAuthorizationHeader`（L263-268）以 `PrCommonName.AUTHORIZATION_HEADER` + `BEARER_PREFIX` 发送 Bearer 头，空 token 不带鉴权头；
- 因此改造只需把 gitee 的 token 从 URL 移到 headerToken 参数，无需改动 HTTP 工具类。

## 功能描述

**做什么**

- gitee 文件检查 token 改走 `Authorization: Bearer`：`getPrFileSize` 在 gitee PR URL 场景下也取平台 token 作为 `headerToken`；`buildFileCheckUrl` 的 gitee 分支不再拼接 accessToken。
- 兼容存量配置模板：`gitee.file.url` 若残留 `access_token=` 片段，构建 URL 时截断该段并清理尾部 `?` / `&`。
- 修正 `buildFileCheckUrl` / `getPrFileSize` 中"gitee 仅支持查询参数鉴权"的不成立注释，统一表述为"统一走 Authorization 请求头（SEC-2）"。
- `ScanossFileDto.token` 增加 `@ToString.Exclude`，使 `toString()` 不再携带 token（不影响 getter/setter 与下载功能）。
- 单测：改造 `testBuildFileCheckUrl_Gitee`（由"URL 以 token 结尾"改为否定断言），新增 `testGetPrFileSize_Gitee_UsesHeaderToken`、`testBuildFileCheckUrl_Gitee_StripsLegacyAccessTokenFromConfig`。

**不做什么**

- 不改 `HttpClientUtil` 的鉴权实现（已支持 header token）。
- 不改 scanoss.json 下载链路（`DownLoadFilesUtils` 已走 Bearer，属 #85 整改范围）。
- 不引入统一日志脱敏/凭证加密框架，不改日志组件。
- 不强制运维迁移 Nacos 配置模板（代码侧做兼容剥离）。
- 本轮未执行单测与真实 gitee 环境回归。

## 验收标准

Issue 的三项验收 + 补充一项：

- [x] gitee 平台 `getPrFileSize` 调用链外发 URL 不含 access_token —— `buildFileCheckUrl` gitee 分支不再拼接 token（`d5d284ed`）；单测 `testBuildFileCheckUrl_Gitee` 断言 URL 不含 `test_token` 与 `access_token=`
- [x] token 通过 Authorization 请求头传递 —— `getPrFileSize` 将 gitee 平台 token 作为 `headerToken` 传入 `checkFileNum`，最终由 `HttpClientUtil.addAuthorizationHeader` 发 Bearer；单测 `testGetPrFileSize_Gitee_UsesHeaderToken` 验证 `checkFileNum(url, "test_token")`
- [x] 相关注释修正 —— `getPrFileSize` L510 与 `buildFileCheckUrl` L544、L560 注释更新为统一走 Authorization 请求头（SEC-2）
- [x] 相关单元测试已更新（3 个 gitee 用例）—— 断言与用例存在性经代码核实
- [ ] 单元测试实际执行通过 —— 未验证（本轮只读，未跑 mvn）
- [ ] 真实 gitee 环境功能回归（文件数检查返回正确、Bearer 鉴权被平台接受）—— 未验证
- [x] `ScanossFileDto.token` 添加 `@ToString.Exclude`，`toString()` 输出不含 token（`2e309ec5`，代码核实；无专门单测守护）
- [ ] 存量配置模板含 `access_token=` 的兼容行为在真实配置中心验证 —— 未验证（仅单测覆盖"`?access_token=` 尾部"场景）

## 影响范围

- 仓库：仅 `openlibing-sca`。代码：`dm/service/impl/IntegrationApiServiceImpl.java`、`common/domain/ScanossFileDto.java`；测试：`IntegrationApiServiceImplTest.java`。
- 配置：读取外部配置键 `gitee.file.url`（仓内 resources 未检索到该键，位于配置中心），建议模板改为不含 access_token 的形式；代码兼容旧模板。
- 接口 / 契约：无变化，`getPrFileSize` / `buildFileCheckUrl` / `checkFileNum` 签名不变。
- 行为变化：gitee PR 文件数检查由 URL 鉴权改为请求头鉴权，要求 gitee token 具备同等权限；若 `gitee.url` 前缀匹配不到 PR URL，则 `headerToken` 为 null（不携带鉴权头）。
- schema：无变化。
- 跨仓：无代码跨仓；配置中心模板清理属运维动作。
