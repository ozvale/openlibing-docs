# fix-idor-query-bind-accounts — 实现任务

## 进度: 7/7 complete

- [x] Task 1: LoginController.queryAlreadyBoundAccounts 增加 ServerHttpRequest 参数，解析 token userId 并与请求参数比对，不一致/缺失拒绝（commit d2ca7d9b）
- [x] Task 2: LoginControllerTest 既有 success 用例适配新签名；新增 token 缺失、userId 不一致（越权）用例
- [x] Task 3: LoginControllerTest 全量 53 个用例通过（QueryAlreadyBoundAccountsTest 3/3），pre-commit 全门禁通过
- [x] Task 4: UserController.saveThreePartUserInfo 取消 accountId/accountPlatform 入参，改读 AuthFilter 从 token 注入的 query params（横向排查补充项，登录中间态无 userId 的白名单端点），UserControllerTest 适配 + 新增 3 个注入参数缺失/为空拒绝用例
- [x] Task 5: UserControllerTest 全量 38 个用例通过（SaveThreePartUserInfoTest 8/8），pre-commit 全门禁通过（commit a6f287da）
- [x] Task 6: UserController.setCheckPlatform 取消 userId 入参，改读 AuthFilter token 注入的 query params（漏洞报告 1103-004 / M-0003 高危同型 IDOR），新增注入 userId 缺失拒绝用例
- [x] Task 7: UserControllerTest 全量 39 个用例通过（SetCheckPlatformTest 3/3），pre-commit 全门禁通过
