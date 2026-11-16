# fix-plugin-auth-code-consumption — 实现任务

## 进度: 3/3 complete

- [x] Task 1: LoginController 预检 key 补 `PLUGIN_AUTH_CODE_PREFIX` 前缀
- [x] Task 2: RedisHelper 新增 `getAndDelete` 原子消费方法；LoginServiceImpl.generatePluginAuth 改原子消费并移除独立 del
- [x] Task 3: LoginControllerTest/LoginServiceImplTest 适配（前缀 stub + getAndDelete stub + 原子消费断言），两测试类全量通过
