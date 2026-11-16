# fix-refresh-token-key-alignment — 实现任务

## 进度: 2/2 complete

- [x] Task 1: buildGiteeAccountLoginResult / buildGitcodePatLoginResult 的 refresh token 写入 key 从 `userIdToken-*-refresh` 改为 `webLoginRefresh-<accountId>-<accountName>`
- [x] Task 2: 新增 RefreshTokenKeyAlignmentTest 用例（断言写 webLoginRefresh key + never 写含 -refresh 后缀 key），LoginServiceImplTest 72/72 通过
