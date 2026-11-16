# fix-login-brute-force-protection — 实现任务

## 进度: 3/3 complete

- [x] Task 1: UserInfoConstants 新增 `LOGIN_FAILURE_COUNT_PREFIX`；LoginServiceImpl 注入阈值/窗口配置并新增 check/set/clear 三个计数方法（对齐 UserServiceImpl 验证码计数模式）
- [x] Task 2: giteePasswordLogin 账号维度、gitcodePatLogin 平台维度接入入口检查/失败计数/成功清零
- [x] Task 3: LoginFailureLimitTest 4 个用例（阈值封禁不触上游、认证失败计数+TTL、PAT 平台封禁不解密、白名单拒绝计数），LoginServiceImplTest 全量通过
