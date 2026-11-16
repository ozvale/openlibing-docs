# fix-open-redirect-bind-authoriz — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/162 （【安全】M-0001 OAuth 账号绑定回调用 redirect 参数未校验导致开放重定向 CWE-601）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `bbba6249`: LoginController 新增 `isRedirectUrlTrusted`（相对路径白名单形态 + 绝对地址 host 与 cookie 域精准匹配），5 个 bind 端点写 Redis 前统一校验，不受信返回 400

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- LoginControllerTest 全量 62 个用例通过（新增 10 个：端点级 4 + helper 级 6，覆盖站外地址 / protocol-relative / 非 http 协议 / 反斜杠变体 / 非法语法）
- pre-commit 全门禁通过

## 设计偏差与取舍

- 受信 host 取自 `jwtConfig.getDomainName()`（与 cookie 域一致）；部署注意：生产 domain-name 必须与前端 PR 管理页面实际域名一致，否则合法 redirect 会被 400

## 归档日期

2026-11-16
