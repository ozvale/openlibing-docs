| issueID | issue名称 | 责任人 | 评审结果 | 发布日期 |
|154|【安全】VULN-SEC-JAVA-SESSION-FILTER-001: CSRF token 校验仅验证签名未比对值导致防护绕过|chentao|通过|2026-11-16|
|155|【安全】【openlibing-gateway:gateway-auth-whitelist-range】【H-0002】网关认证过滤器豁免登录白名单迁移到数据库后使用子串 contains 匹配且忽略 HTTP 方法，可导致受保护兄弟端点被匿名放行|chentao|通过|2026-11-16|
|156|[CI] openlibing-gateway 接入 UT/build 门禁并升级 pre-commit 门禁|chentao|通过|2026-11-16|
|157|[CI] openlibing-gateway 接入 UT/build 门禁并升级 pre-commit 门禁|chentao|通过|2026-11-16|
|158|【安全】openlibing-gateway:gateway-auth-whitelist-range】【L-0011】新增凭证类登录端点（/login/gitee/account、/login/gitcode/token）缺少暴力破解与速率限制防护|chentao|通过|2026-11-16|
|159|【安全】【openlibing-gateway:operation-log-and-perm-scheme】【H-0002】登录/OAuth 操作审计日志失真：响应式与 void 端点失败被记为成功或漏记（CWE-778）|chentao|通过|2026-11-16|
|160|【安全】【openlibing-gateway:operation-log-and-perm-scheme】【H-0006】Netty 已知漏洞修复被回退：netty-bom 4.2.19.Final 覆盖被删除，网关 netty 回落至 4.2.16.Final（CVE-2026-75595 免认证 mTLS 绕过 / CVE-2026-75596 SNI DoS）|chentao|通过|2026-11-16|
|161|【安全】【openlibing-gateway:operation-log-and-perm-scheme】【M-0004】全局异常日志打印含 query string 的完整 URI，OAuth2 access_token/code 明文进入服务器日志|chentao|通过|2026-11-16|
|162|【安全】【openlibing-gateway:auth-session-gray-release】【M-0001】OAuth 账号绑定回调用 redirect 参数未校验导致开放重定向（CWE-601）|chentao|通过|2026-11-16|
|163|【安全】【openlibing-gateway:auth-session-gray-release】【M-0003】POST /user/set-check-platform 存在水平越权（IDOR）：任意已登录用户可通过请求参数 userId 篡改他人门禁检测平台标志|chentao|通过|2026-11-16|
|164|【安全】【openlibing-gateway:auth-session-gray-release】【M-0004】网关静默刷新绕过 CSRF/referer 校验，跨站 GET 可触发账号解绑等有状态变更（CWE-352）|chentao|通过|2026-11-16|
|165|【安全】【openlibing-gateway:auth-session-gray-release】【M-0005】插件一次性 auth code Redis key 命名空间不一致导致换取接口永久失败并残留非原子双消费竞态|chentao|通过|2026-11-16|
|166|【安全】【openlibing-gateway:auth-session-gray-release】【M-0007】登出未吊销 refresh token 轮换宽限期 key：60 秒窗口内旧 refresh token 仍可换发新会话（登出绕过/会话复活）|chentao|通过|2026-11-16|
|167|【安全】【openlibing-gateway:auth-session-gray-release】【M-0013】public 页面转发身份参数剥离不完整：携带伪造 token cookie 时 userId/userName/accountId/accountPlatform 仍可注入下游|chentao|通过|2026-11-16|
|168|【安全】OAuth回调接口存在access_token参数注入漏洞，可导致绕过授权码认证冒充他人身份|chentao|通过|2026-11-16|
|169|【安全】账号绑定流程 OAuth state 未绑定会话身份存在绑定劫持漏洞，可导致任意三方账号被绑定到他人OpenLiBing账号|chentao|通过|2026-11-16|
|170|【安全】网关纵向权限校验存在请求方法与动态参数校验盲区，可导致低权限用户越权访问管理接口|chentao|通过|2026-11-16|
|171|【安全】网关 HttpRequestUtil.getUserIpAddress 方法存在 X-Forwarded-For IP 伪造漏洞，可导致审计溯源失效与机机接口访问控制绕过|chentao|通过|2026-11-16|
|172|【安全】openlibing-gateway OAuth工具组件存在凭据泄露漏洞，可导致用户access_token经URL查询参数明文泄露|chentao|通过|2026-11-16|
