# Tasks: fix-verify-token-allow-expired

- [x] 定位根因：`verifyTokenAllowExpired` 抛 `TokenExpiredException` 与返回 null 契约不符
- [x] 修复 `JwtHelper.verifyTokenAllowExpired`：catch `TokenExpiredException` 返回 null
- [x] 新增回归用例（真实签名，不 mock）：有效 / 过期签名合法 / 签名非法 / 无法解析
- [x] `JwtHelperTest` 55 例通过
- [x] `AuthFilterTest` 95 例回归通过
- [x] pre-commit 全门禁通过，提交 commit bc5281a1（develop_202611_iter1）
- [ ] 用户自测确认（页面持续活跃 / access token 过期场景不再跳登录页）
- [ ] 业务 PR（关联 Issue，打 ai-assisted 标签）
- [ ] docs PR 归档（含 archive.md）
