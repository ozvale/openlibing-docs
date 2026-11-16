# fix-silent-refresh-csrf-bypass — 实现任务

## 进度: 3/3 complete

- [x] Task 1: AuthFilter 新增 `isCsrfRefererTrusted`（trust 名单精准匹配 + referer host 精准匹配）；主链路刷新成功分支改为降级校验，失败 401；公开接口 `checkPublicCredential` 同型修复，失败匿名降级
- [x] Task 2: AuthFilterTest 新增 5 个 `isCsrfRefererTrusted` 用例（trust 精准豁免 / 前缀不豁免 / 受信 referer / host 前缀拼接绕过拒绝 / 空 referer 拒绝）；适配 3 个既有静默刷新用例补可信 referer
- [x] Task 3: AuthFilterTest 全量 102 个用例通过，pre-commit 全门禁通过
