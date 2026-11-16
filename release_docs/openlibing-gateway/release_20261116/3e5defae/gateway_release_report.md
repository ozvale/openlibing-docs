| issueID | issue名称 | 责任人 | 评审结果 | 发布日期 |
|100|[缺陷]: cicd拦截器拦截了其他模块请求|chentao|通过|2026-11-16|
|109|fix(auth): token 过期返回 500 而非 401|chentao|通过|2026-11-16|
|145|[缺陷]: 已登录用户访问公开接口，转发前未校验凭证有效性（公开接口凭证校验加固）|chentao|通过|2026-11-16|
|149|【安全】【openlibing-gateway:gateway-auth-whitelist-range】【M-0004】GitCode PAT 登录账号 allowlist 配置为空时校验整体跳过（fail-open）|chentao|通过|2026-11-16|
|150|【安全】【openlibing-gateway:auth-session-gray-release】【H-0002】水平越权（IDOR）：GET /platform/query/already/bind/accounts 可查询任意用户已绑定三方账号|chentao|通过|2026-11-16|
|153|【安全】VULN-SEC-JAVA-SESSION-FILTER-001: CSRF token 校验仅验证签名未比对值导致防护绕过|chentao|通过|2026-11-16|
|154|【安全】【openlibing-gateway:gateway-auth-whitelist-range】【H-0002】网关认证过滤器豁免登录白名单使用子串匹配且忽略 HTTP 方法|chentao|通过|2026-11-16|
|170|【安全】网关纵向权限校验存在请求方法与动态参数校验盲区，可导致低权限用户越权访问管理接口|chentao|通过|2026-11-16|
