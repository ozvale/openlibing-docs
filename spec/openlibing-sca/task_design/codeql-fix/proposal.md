# openlibing-sca CodeQL 静态扫描安全问题修复 — 需求提案

## 1. 需求背景

openlibing-sca 接入 CodeQL 静态安全扫描后，扫描报告发现 **81 处安全漏洞 / 代码质量问题**，主要分布在 HTTP 请求处理、日志输出、鉴权解析、正则构造等代码路径上：

- **SSRF 风险**：多处 HTTP 客户端（OkHttp / Apache HttpClient / RestTemplate / URLConnection）直接请求用户可控 URL，未校验目标地址，可被构造为访问内网地址（如 127.0.0.1、10.x、172.16-31.x、192.168.x）。
- **日志注入（Log Injection）**：`DefaultExceptionHandler` 及各 Service 将用户可控字段（URI、User-Agent、Referer、repoUrl、prUrl 等）直接拼接进日志，攻击者可伪造换行符注入虚假日志行。
- **日志质量**：大量 `append.toString()` 字符串拼接日志、缺失占位符参数、异常信息不携带请求上下文，导致生产排障困难，同时触发 CodeQL 的 `log-injection` / `format-string` 类告警。
- **正则构造缺陷**：`wildCard2RegEx` 通配符转正则依赖多轮 `replace` 链式替换，特殊字符（`.` 与 `\`）处理存在顺序依赖，可能产生双重转义或错误匹配。
- **JWT 解析缺陷**：`JwtUtils.getAccessToken` 返回的 map 缺少 `sub` claim，导致 `scanPathConfirmParseV2` 中 `"gitee".equals(mapToken.get("sub"))` 恒为 false，gitee 用户登录名被错误加 `gitcode-` 前缀。
- **接口语义**：多处仅触发数据刷新的 GET 接口携带查询参数，可能造成敏感信息泄漏到访问日志 / 浏览器历史，且 GET 不应产生副作用。

## 2. 需求目标

在 `codeql-fix` 分支上系统性修复 CodeQL 扫描发现的全部问题，同时保证既有功能行为不回归：

1. 所有出站 HTTP 请求（OkHttp / Apache HttpClient / RestTemplate / URLConnection 四种客户端）统一经过 SSRF 防护校验，阻断对本地/内网/保留地址的访问。
2. 所有用户可控字段进入日志前做日志注入净化（剥离控制字符），并将异常日志改为参数化格式，携带请求上下文。
3. 修复 `wildCard2RegEx` 正则构造缺陷，与 `ShieldRoleServiceImpl` 对齐。
4. `JwtUtils.getAccessToken` 补充 `sub` claim，修正 gitee / gitcode 登录名前缀判定。
5. 有副作用的接口从 GET 调整为 POST。
6. 补充 / 调整单元测试，保证上述行为变化被覆盖。

## 3. 验收标准

| # | 验收项 | 预期结果 |
|---|--------|----------|
| AC-1 | SSRF 防护覆盖 | 所有 HTTP 出站入口调用 `SsrfsafeUrlUtil.validateUrl`；访问 localhost / 127.0.0.1 / 0.0.0.0 / 私网段 / 链路本地地址 / 非 http(s) 协议时请求被拒绝，服务不抛未捕获异常 |
| AC-2 | 日志注入防御 | 用户可控字段（URI、UA、Referer、repoUrl、prUrl、flag 等）写入日志前均经过净化；`DefaultExceptionHandler` 异常日志含请求上下文（URI / Method / ClientIP / UA / Referer）且为参数化日志 |
| AC-3 | 日志格式修复 | 全部 `append.toString()` 拼接日志改为参数化占位符；缺失参数补齐（如 OpenPersonScanServiceImpl 日志缺 repoName） |
| AC-4 | 正则修复 | `OpenScanDMServiceImpl.wildCard2RegEx` 与 `ShieldRoleServiceImpl.wildCard2RegEx` 行为一致，`*`→`.*`、`?`→`.?`、正则元字符转义正确 |
| AC-5 | JWT 修复 | `getAccessToken` 返回 map 含 `sub`；`scanPathConfirmParseV2` 中 gitee 用户不加 `gitcode-` 前缀，gitcode 用户保留前缀 |
| AC-6 | 接口方法调整 | 导出类、刷新类、触发类接口全部改为 POST；调用方同步适配 |
| AC-7 | 无回归 | 修改涉及的模块相关单元测试全部通过；Maven 编译 + pre-commit 检查通过 |
| AC-8 | CodeQL 复扫 | 修复后重新运行 CodeQL 扫描，原 81 处告警清零（或已逐条确认处理） |

## 4. 影响范围

- **后端**：openlibing-sca 仓（`codeql-fix` 分支，19 个 commit）
- **代码**：25 个文件（21 个 src 文件 + 3 个测试 + 配置文件），`+438 / -625` 行（含相对 origin/master 的差异）
- **接口**：9 个接口由 GET 调整为 POST（前端 / 调用方需同步）
- **依赖**：无新增第三方依赖
- **数据库**：无 schema 变更

## 5. 关联信息

- Issue：[openlibing/openlibing-sca#58 修复 CodeQL 静态扫描发现的 81 处安全漏洞](https://gitcode.com/openlibing/openlibing-sca/issues/58)
- 分支：`codeql-fix`（基于 `origin/master`）
- 归属：安全合规迭代（2026-07）
