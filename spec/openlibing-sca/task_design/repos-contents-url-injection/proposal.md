# repos-contents-url-injection — getReposContents 文件参数校验与外发 URL 加固

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/119
（【安全】【外部参数校验】/open/scan/getReposContents 接口 URL 拼接注入风险）

`GET /open/scan/getReposContents`（`scanId` + `file` 两个参数）把用户可控的 `file` 直接拼接进外发 gitee/gitcode contents API URL：

- `processFilePath` 仅剥离 `community/repo` 前缀，无字符校验；
- `buildApiUrl` 把 `file` 原样拼进路径段（`.../contents/` + file + `?ref=` + commitId）；
- `getFileContentFromUrl` 直接 `new URL(urlString)` 发起请求，未调用 `SsrfsafeUrlUtil.validateUrl`（同文件 `showFileHash` 已接入）。

`file` 可注入 `?`、`&`、`#`、`@`、`../`、CR/LF、空白等字符，篡改外发请求的路径与查询参数；请求结果（文件内容或错误文案）回显给调用方，可用于探测平台 API 行为。由于 host 固定为 gitee/gitcode API，SSRF 面受限，主要风险为 URL 参数篡改与路径穿越。

同一接口还存在越权读取问题：`file` 内容通过服务侧平台 token 拉取，缺少用户授权判断，未登录用户也能读取私仓文件内容（本轮一并整改）。

归类：CWE-20（Improper Input Validation）、CWE-88（Argument Injection）、CWE-862（Missing Authorization）。

## 功能描述

**做什么**：

1. 新增 `validateFilePath`（包级静态方法）并在 `getReposContents` 入口最先调用：拒绝空值、包含 `..`、以及 `?` `#` `&` `@` `\`、控制字符（`< 0x20`、`0x7F`）、任意空白；命中即抛 `ScaException(ErrorCode.PARAM_ERROR)`。
2. 新增 `encodeFilePath`（包级静态方法）：按 `/` 分段做 `URLEncoder.encode(UTF-8)` 并把 `+` 替换为 `%20`，保留路径分隔符；`buildApiUrl` 只使用编码后的 `file` 拼接 URL。
3. `getFileContentFromUrl` 在发起请求前调用 `SsrfsafeUrlUtil.validateUrl(urlString)`，与 `showFileHash` 行为一致。
4. 增加仓库权限校验（与 `getTree` 一致）：`userId` 为空时要求仓库为开源可见（`prIsOpenSourceRepo`），否则返回 `4001`（请登录后查看私仓文件内容）；`userId` 非空但框架 `checkRepoUserNamePermission` 返回无权限时返回 `403`。**信任边界**：`userId` 由调用方透传，本轮服务端未从登录票据解析、未强制覆盖客户端传入值；若认证层未注入可信 `userId`，攻击者可自报拥有权限用户的 `userId` 绕过校验（属 #156 可信身份遗留项，见设计文档风险表）。

**不做什么**：

- 不对 `community` / `repo`（来自 scanInfo 的仓库地址解析结果）做额外编码或校验，它们不由请求方任意指定。
- 不做 SSRF 域名白名单扩展或重定向处理（属于 SSRF 加固专项，见 `ssrf-*` 相关 spec 目录）。
- 不改变 `file` 的语义（仍支持 `community/repo/...` 前缀，由 `processFilePath` 剥离）。
- 不改造接口为 POST 或签名机制。

## 验收标准

- [x] 含 `..`、`?`、`&`、`#`、CRLF 的 `file` 参数被拒绝：`validateFilePath` 显式拦截；单测 `getReposContents_rejectsPathTraversal`、`getReposContents_rejectsUrlInjectionChars`、`getReposContents_rejectsCrlfAndControlChars`、`getReposContents_rejectsBlankFileParam`
- [x] `file` 参数经 URL 编码后再拼入外发 URL：`buildApiUrl` 使用 `encodeFilePath(apiUrlDto.getFile())`；单测 `encodeFilePath_encodesSegmentsButKeepsSlash` 断言 `src/中文/c+d.java` → `src/%E4%B8%AD%E6%96%87/c%2Bd.java`
- [x] 外发前统一经过 `SsrfsafeUrlUtil` 校验：`getFileContentFromUrl` 首行调用 `SsrfsafeUrlUtil.validateUrl`；单测 `getReposContents_validatesOutboundUrlBeforeRequest` 断言非法外发地址抛 `IllegalArgumentException`
- [x] 相关单元测试用例已补充：`OpenScanServiceImplTest` 中 9 个与本次改动相关用例
- [ ] 相关单元测试通过，覆盖率达标：本次回溯未重新执行 `mvn test`，执行结果未验证
- [x] 私仓未登录 / 无权限用户被拒绝：新增 `getReposContents_privateRepoWithoutUserRejected`（4001）、`getReposContents_userWithoutPermissionRejected`（403）、`getReposContents_openSourceRepoWithoutUserAllowed`；注：`userId` 为客户端自报参数、可伪造，伪造他人 `userId` 仍可绕过校验（未闭环，属 #156 遗留，见设计文档风险表）

## 影响范围

- 仓库：`openlibing-sca`（analysis 模块 Controller / Service / 单测）。
- 接口：`GET /open/scan/getReposContents` 新增可选查询参数 `userId`（不传视为未登录访问）；返回值新增业务错误码 `4001` / `403`；非法 `file` 从"透传到外发请求"变为参数错误。
- 配置 / schema：无。
- 调用方：前端/网关需要为已登录用户透传 `userId`，否则访问私仓文件会被拒绝；`userId` 必须由认证层/网关从登录票据解析并强制覆盖，客户端自报值不可作为鉴权依据（本轮实现直接信任请求参数，属 #156 遗留项）。
