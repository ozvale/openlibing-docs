# fix-oauth-bind-state-session — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/169 （【安全】账号绑定流程 OAuth state 未绑定会话身份存在绑定劫持漏洞，可导致任意三方账号被绑定到他人 OpenLiBing 账号）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `ab7285a4`: LoginController 绑定发起时 Redis state 值改为 `userId|SHA256(token)`；5 平台（gitee/gitcode/github/uniportal/openubmc）绑定回调增加会话一致性校验（常量时间比较 `MessageDigest.isEqual`），不匹配/缺失/格式不合法一律 403 fail-closed

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- LoginControllerTest 69/69 通过（5 平台会话匹配通过 + 会话不匹配 403 负向用例全覆盖，prManages redirect 分支同受保护）
- spotless:apply / checkstyle:check 通过

## 设计偏差与取舍

- 无；按 proposal 方案落地。部署后 Redis 旧格式 state（TTL 30 分钟）自然失效，属预期，无需迁移

## 归档日期

2026-11-16
