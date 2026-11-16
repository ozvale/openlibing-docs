# fix-refresh-token-key-alignment — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/148 （【安全】gateway-auth-whitelist-range L-0013 登录接口刷新令牌 Redis key 不一致，PAT/密码登录 refreshToken 永远无法刷新）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `e394104d`: buildGiteeAccountLoginResult / buildGitcodePatLoginResult 的 refresh token 写入 key 从 `userIdToken-*-refresh` 改为 `webLoginRefresh-<accountId>-<accountName>`（TTL 30 天不变），与 Web 静默刷新、logout 吊销（含宽限期 key）全部对齐

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- 新增 RefreshTokenKeyAlignmentTest 用例（断言写 webLoginRefresh key + never 写含 `-refresh` 后缀 key），LoginServiceImplTest 72/72 通过
- 旧前缀 key 全仓无读取方，存量依赖 30 天 TTL 自然过期，无需迁移

## 设计偏差与取舍

- 无；按 proposal 方案落地

## 归档日期

2026-11-16
