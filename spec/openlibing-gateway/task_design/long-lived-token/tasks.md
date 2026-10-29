# long-lived-token — 实现任务

## 进度: 10/10 complete

- [x] Task 1: `UserInfoConstants` 新增 `WEB_LOGIN_REFRESH`、`WEB_LOGIN_REFRESH_GRACE`、refresh cookie 名常量；`JwtHelper.generateCookie` 增加带 cookie 名的重载（bd10a31）
- [x] Task 2: `UserController` 会话确立点签发 refresh token（Redis `webLoginRefresh-*` + `refresh_token` Cookie），新增私有 helper（bd10a31）
- [x] Task 3: `AuthFilter` 静默刷新分支：token 状态判定（缺失/过期/Redis key 过期/非法）→ 刷新 → 新 token/refresh Cookie + CSRF 重建（bd10a31）
- [x] Task 4: `LoginController` 登出清理 Redis web refresh key + 清除 `refresh_token` Cookie（bd10a31）
- [x] Task 5: 单元测试：刷新成功/JWT 过期/Redis key 过期/refresh 重放/非法签名不刷新/登出清理/会话确立点 Cookie 签发（bd10a31）
- [x] Task 6: 全量验证（compile + 相关测试 + spotless）+ AI 自检 + commit（bd10a31）
- [x] Task 7（实现演进）: AuthFilter 新增第 4 触发条件——需 CSRF 校验的请求未携带 csrf 凭证时触发换发，信任路径豁免（4ec5994）
- [x] Task 8（实现演进）: OAuth 回调 `LoginServiceImpl.responseLoginInfo` 新增 `establishWebLoginSession`，主登录入口签发 refresh token + 重建 CSRF，临时用户跳过（71b5757）
- [x] Task 9（实现演进）: 轮换 60 秒宽限期 `webLoginRefreshGrace-*`，宽限期内旧 token 换发不再轮换，解决首屏并发竞态（a6e9360）
- [x] Task 10（实现演进）: refresh token 固定 30 天（轮换沿用主 key 剩余 TTL，`c1281e2`）；access JWT 本体 8h → 24h（`ca96ba7`）

## 实现期偏差记录

初版设计为"refresh token 滑动续期 + 仅 3 个会话确立点 + 3 个刷新触发条件"。实测反馈驱动 4 轮演进（Task 7-10），最终语义见 design.md D3/D7/D8/D9/D10。前端仓零改动闭环（原预期需前端配合持久化 CSRF header，实测落地页为首页、既有逻辑已捕获）。
