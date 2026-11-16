# fix-logout-grace-key-revocation — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/166 （【安全】M-0007 登出未吊销 refresh token 轮换宽限期 key，60 秒窗口会话复活）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `40fe979a`: LoginController.logout 补删 `WEB_LOGIN_REFRESH_GRACE-<accountId>-<accountName>` 宽限期 key

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- LogoutTest 适配断言（del 次数 3→4 + grace key 删除验证），LoginControllerTest 全量通过

## 设计偏差与取舍

- `deleteAccount`（UserServiceImpl）完全未清理 Redis 凭证属另一项已记录缺口，不在本修复范围（后续跟进项）

## 归档日期

2026-11-16
