# tasks: fix-oauth-bind-state-session

- [x] LoginController 新增 BIND_STATE_VALUE_SEPARATOR 常量与 buildBindStateValue/sha256Hex/resolveBindUserId
- [x] 5 处绑定发起改存 `userId|tokenHash`（uniportal/openubmc/gitee/gitcode/github）
- [x] 5 处绑定回调增加会话一致性校验，不匹配 403 + warn
- [x] 测试 helper：stubCallbackTokenCookie / bindStateValue
- [x] 5 平台 bind 回调测试适配新格式
- [x] 5 平台新增会话不匹配负向测试
- [x] `run-mvn.py test -Dtest=LoginControllerTest` 通过（69/69）
- [x] `run-mvn.py spotless:apply checkstyle:check` 通过
- [ ] 用户自测确认
- [ ] 业务 PR（打 ai-assisted 标签；暂不关联 Issue）
- [ ] docs PR 归档本 spec
