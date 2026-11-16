# fix-plugin-auth-code-consumption — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/165 （【安全】M-0005 插件一次性 auth code Redis key 命名空间不一致 + 非原子双消费竞态）
- 关联 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/143 （【安全】插件取 token 接口未认证 Redis Key 遍历探测，裸 code 预检缺陷的同源问题）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235 （fix(security): harden auth, oauth and redis handling，待合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `790bf0b4`: LoginController 预检 key 补齐 `PLUGIN_AUTH_CODE_PREFIX` 前缀；RedisHelper 新增 `getAndDelete`（Redis GETDEL 原子命令）；LoginServiceImpl.generatePluginAuth 改原子消费并移除独立 del

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- LoginControllerTest / LoginServiceImplTest 适配后全量通过（前缀 stub + getAndDelete stub + 原子消费断言）

## 设计偏差与取舍

- 无；按 proposal 方案落地

## 归档日期

2026-11-16
