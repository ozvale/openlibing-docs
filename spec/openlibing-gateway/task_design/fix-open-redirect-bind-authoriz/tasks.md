# fix-open-redirect-bind-authoriz — 实现任务

## 进度: 3/3 complete

- [x] Task 1: LoginController 新增 `isRedirectUrlTrusted`（相对路径白名单形态 + 绝对地址 host 精准匹配），5 个 bind 端点写 Redis 前统一校验，不受信返回 400
- [x] Task 2: LoginControllerTest 新增 10 个用例（端点级 4：合法绝对/合法相对/站外 400/protocol-relative 400；helper 级 6：host 大小写/前缀拼接/非 http 协议/反斜杠变体/根路径/非法语法）
- [x] Task 3: LoginControllerTest 全量 62 个用例通过，pre-commit 全门禁通过
