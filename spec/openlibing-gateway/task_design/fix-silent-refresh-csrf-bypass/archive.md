# fix-silent-refresh-csrf-bypass — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/164 （【安全】auth-session-gray-release M-0004 网关静默刷新绕过 CSRF/referer 校验，跨站 GET 可触发账号解绑等有状态变更 CWE-352）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `971790f3`: AuthFilter 新增 `isCsrfRefererTrusted`（trust 名单精准匹配 + referer host 精准匹配）；主链路静默刷新成功分支从整体短路降级为 referer host 校验，失败 401；公开接口分支同型修复，失败匿名降级
- commit `0985a802`: 过期 CSRF JWT 静默自愈（silent refresh）并同步 csrf Set-Cookie，配套刷新链路加固

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- AuthFilterTest 全量 102 个用例通过（新增 5 个 `isCsrfRefererTrusted` 用例：trust 精准豁免 / 前缀不豁免 / 受信 referer / host 前缀拼接绕过拒绝 / 空 referer 拒绝；适配 3 个既有静默刷新用例）
- pre-commit 全门禁通过

## 设计偏差与取舍

- 刷新成功不整体短路，降级为 referer host 精准匹配，trust 名单仅精准匹配豁免（前缀拼接不豁免）
- 部署注意 1：前端同站请求必须携带 referer（不得使用 no-referrer 策略），否则刷新后续请求会被 401
- 部署注意 2：`csrf.trust.list` 为外部部署配置（不入仓），上线时需按 proposal 参考值核对生产配置

## 归档日期

2026-11-16
