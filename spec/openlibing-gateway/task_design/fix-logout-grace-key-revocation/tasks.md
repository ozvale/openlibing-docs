# fix-logout-grace-key-revocation — 实现任务

## 进度: 2/2 complete

- [x] Task 1: LoginController.logout 补删 `WEB_LOGIN_REFRESH_GRACE-<accountId>-<accountName>`
- [x] Task 2: LogoutTest 适配断言（del 次数 3→4 + grace key 删除验证），LoginControllerTest 全量通过
