# fix-login-brute-force-protection — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/158 （【安全】gateway-auth-whitelist-range L-0011 凭证类登录端点缺少暴力破解与速率限制防护）
- 关联 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/147 （同 L-0011 重复单，已关闭）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `8661bc75`: LoginServiceImpl 新增 `checkLoginFailureCount` / `setLoginFailureCount` / `clearLoginFailureCount`（Redis key `loginFailureCount_<platform>_<identity>`，默认阈值 5 次 / 60 分钟窗口，可配置覆盖）；gitee 账密登录按账号维度计数，gitcode PAT 登录退化为平台级窗口；入口检查、失败计数、成功清零全链路接入

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- LoginFailureLimitTest 4 个用例通过（阈值封禁不触上游、认证失败计数+TTL、PAT 平台封禁不解密、白名单拒绝计数），LoginServiceImplTest 全量通过

## 设计偏差与取舍

- PAT 平台级窗口存在 DoS 面：攻击者刷满失败次数可让白名单用户 PAT 登录暂停至窗口过期。接受原因：PAT 登录本身白名单 fail-closed 且低频，窗口自动恢复，不造成持久影响

## 归档日期

2026-11-16
