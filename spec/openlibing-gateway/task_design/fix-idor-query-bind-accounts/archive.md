# fix-idor-query-bind-accounts — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/151 （【安全】auth-session-gray-release H-0002 水平越权 IDOR：GET /platform/query/already/bind/accounts 可查询任意用户已绑定三方账号）
- 关联 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/163 （【安全】M-0003 POST /user/set-check-platform 水平越权 IDOR，Task 6 同型修复）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/232 （已合入，commit 9e14a5ec）+ https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （待合入，commit e55584ba）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `9e14a5ec`: LoginController.queryAlreadyBoundAccounts 增加 token userId 与请求参数一致性校验，不一致/缺失拒绝（Task 1-3）
- commit `a6f287da`: UserController.saveThreePartUserInfo 取消 accountId/accountPlatform 入参，改读 AuthFilter token 注入值（Task 4-5，横向排查补充项）
- commit `e55584ba`: UserController.setCheckPlatform 取消 userId 入参，改读 AuthFilter token 注入值（Task 6-7，M-0003 高危同型 IDOR）

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- LoginControllerTest 全量 53 个用例通过（QueryAlreadyBoundAccountsTest 3/3，含 token 缺失、userId 越权负向用例）
- UserControllerTest 全量 39 个用例通过（SaveThreePartUserInfoTest 8/8、SetCheckPlatformTest 3/3，含注入参数缺失/为空拒绝用例）
- pre-commit 全门禁通过

## 设计偏差与取舍

- saveThreePartUserInfo 处于隐私协议签署前登录中间态（白名单端点属设计使然），以注入参数覆盖替代鉴权，与既有 AuthFilter 参数注入机制保持一致

## 归档日期

2026-11-16
