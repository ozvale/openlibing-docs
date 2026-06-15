# Tasks: Fix Redis Key TTL=-1 in setVerificationCodeFailureCount

## Task 1: Fix setVerificationCodeFailureCount Method ✅

**文件**: `src/main/java/com/openlibing/gateway/business/service/impl/UserServiceImpl.java`

- [x] 移除 `set(key, "0", ttl)` + `increase(key, 1)` 的两步操作
- [x] 首次失败（key 不存在）：直接 `set(key, "1", ttl)` 原子设置值和 TTL
- [x] 后续失败（key 已存在）：仅 `increase(key, 1)`，保留原有 TTL 不刷新
- [x] 竞态兜底：`increase` 后检查 `getExpire == -1`，若 key 是 INCR 新创建的则补设 TTL
- [x] 保持原有异常处理逻辑（NumberFormatException + RedisConnectionFailureException）

## Task 2: Verification ✅

- [x] IDE 诊断：零错误
- [x] 代码审查：符合生成前约束清单 5 项
- [x] 用户自测确认：TTL 不再为 -1，后续失败不刷新 TTL

## Task 3: Documentation ✅

- [x] proposal.md：Bug 描述、根因分析、修复方案
- [x] design.md：Redis INCR 与 TTL 交互机制、方案选型、时序图
- [x] tasks.md：任务清单
- [x] archive.md：归档记录
- [x] ai_memory.md：沉淀 Redis INCR+TTL 规则

## Task 4: PR & Issue ✅

- [x] 业务 Issue: #104
- [x] 业务 PR: #143
- [x] PR 标签: ai-assisted
