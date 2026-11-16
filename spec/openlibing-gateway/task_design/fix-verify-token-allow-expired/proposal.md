# Proposal: fix-verify-token-allow-expired

## 需求背景

用户反馈：refresh_token 未过期、access token 已过期时，页面接口返回 401 并跳转登录页。
原设计为网关 `AuthFilter` 自动使用 refresh token 静默换发 access token，不应退出登录。

## 根因

`JwtHelper.verifyTokenAllowExpired` 的 javadoc 契约是"签名合法但已过期返回 null"，
但实现直接调用 `verifier.verify(token)`，过期时抛出 `TokenExpiredException`
（`JWTVerificationException` 子类）。`AuthFilter.shouldAttemptSilentRefresh` 的
catch 分支将该异常误判为签名非法，返回 false 不触发静默刷新，导致过期 access token
直接走 401 流程。

触发场景：页面持续活跃超过 24 小时（access JWT 24h 过期，30min Cookie 每次请求续期
保持存活），所有请求 401 被踢回登录页。关浏览器场景（Cookie 已删、token 为空）不受
影响，因此此前未被发现。

## 修复方案（简述）

捕获 `TokenExpiredException` 后按契约返回 null。该异常仅在验签通过后抛出，签名合法性
不受影响；签名非法仍抛异常，防止伪造 token 探测刷新通道。

## 验收标准

1. 签名合法且未过期的 access token：`verifyTokenAllowExpired` 返回 DecodedJWT。
2. 签名合法但已过期的 access token：返回 null（触发静默刷新）。
3. 签名非法或无法解析的 token：抛出 `JWTVerificationException`（不触发刷新）。
4. 回归用例不 mock `verifyTokenAllowExpired`，使用真实签名 token。
5. `JwtHelperTest`、`AuthFilterTest` 全部通过，pre-commit 门禁通过。

## 范围与不做

- 仅修复 `verifyTokenAllowExpired` 的过期语义 bug。
- 公开接口分支无静默刷新的缺口本期不动（另行评估）。
