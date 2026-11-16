# fix-verify-token-allow-expired — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/109 （fix(auth): token 过期返回 500 而非 401，缺陷类，非【安全】issue）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/232 （fix(auth): harden token, whitelist and csrf handling on release_20261116，已合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `bc5281a1`: 修复 `JwtHelper.verifyTokenAllowExpired` —— catch `TokenExpiredException` 后按 javadoc 契约返回 null（该异常仅在验签通过后抛出，签名合法性不受影响；签名非法仍抛异常，防止伪造 token 探测刷新通道）
- commit `d22f46d1`: 随批次合入 release_20261116

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- JwtHelperTest 55 例通过（新增真实签名回归用例，不 mock：有效 / 过期签名合法 / 签名非法 / 无法解析）
- AuthFilterTest 95 例回归通过，pre-commit 全门禁通过

## 设计偏差与取舍

- 公开接口分支无静默刷新的缺口本期不动（另行评估），见 proposal「范围与不做」

## 归档日期

2026-11-16
