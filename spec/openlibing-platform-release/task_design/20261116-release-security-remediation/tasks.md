# 202611 release 安全整改批次 — 实现任务

关联业务 Issue 与业务 PR 见 [proposal.md](proposal.md)。

## 进度: 9/9 complete

已随业务仓 PR #247（`check_safe_202611` → `release_20261116`）交付。

- [x] Task 1: 认证与授权整改 — OpenEulerAuthFilter 根因修复、删除 RequiresPermissions 切面、全量接口项目权限注解校验、认证白名单收敛（#91 #92 #95 #114 #115 #89）
- [x] Task 2: 越权与数据归属 — 附件 IDOR 归属校验、评审单归属防篡改、issuanceReview 前置校验（#94 #87 #100 #98）
- [x] Task 3: 状态机竞态 — 撤回/决策/汇总分布式锁 + 条件更新 + 发布幂等校验（#103）
- [x] Task 4: SSRF — 出站地址点状校验与重定向锁定、Fake-IP 保留段拒绝；通用校验器按评审意见撤回留痕（#101 #117 #118 #119 #122）
- [x] Task 5: 路径穿越 — 产品名/版本号白名单、validatePathDir 恒真绕过修复、临时目录收敛（#102）
- [x] Task 6: 注入与反序列化 — fastjson2 回调 RCE、存储型 XSS、命令注入、软链接提权（#124 #99 #126 #116 #85）
- [x] Task 7: 凭证与敏感信息 — HeaderToken 收敛、令牌迁出 URL、硬编码清理、CWE-532 日志治理（#93 #110 #83 #86 #127）
- [x] Task 8: 证书与传输/供应链/运行时 — SMTP 证书校验、MongoDB TLS、TrustAll 清理、CI 投毒整改、Dockerfile 构建期校验、Actuator 收窄、限流原子化（#84 #130 #108 #105 #104 #106 #129）
- [x] Task 9: 质量收口 — 单测补齐至 diff 增量行覆盖率 80% 门禁、CI 门禁（UT/build/pre-commit）通过、google-java-format 格式统一、无引入功能语义变化（#107 #109 #121 及全批次回归）
