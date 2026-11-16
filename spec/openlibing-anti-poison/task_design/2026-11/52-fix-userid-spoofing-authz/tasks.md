# 52-fix-userid-spoofing-authz — 实现任务

## 进度: 3/3 complete

- [x] Task 1: ProblemShieldController 两个接口的 userId 改为服务端认证态获取
- [x] Task 2: reviewerId 改为服务端确定，去除对客户端 paramModel.getUser() 的信任
- [x] Task 3: 回归屏蔽申请与审批流程，验证伪造 userId 无法越权
