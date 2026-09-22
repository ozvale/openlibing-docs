# Proposal: Fix Redis Key TTL=-1 in setVerificationCodeFailureCount

## Summary

修复 `UserServiceImpl.setVerificationCodeFailureCount` 方法中 Redis key 过期时间被置为 -1（永不过期）的 bug，恢复原始 60 分钟窗口设计。

## Motivation

### Bug 现象

生产环境中 `verificationCodeFailureCacheKey` 的 TTL 出现 -1，即 key 永不过期，导致验证码失败计数永远不会被清除，用户可能被永久锁定。

### 根因分析

原代码逻辑：

```java
// 1. 先 set(key, "0", 60min) 设置带 TTL 的初始值
// 2. 再 increase(key, 1) 原子递增
```

Redis `INCR` 命令（`stringRedisTemplate.opsForValue().increment()`）在递增时**不会保留 key 的 TTL**，执行后 key 的 TTL 被清除为 -1（永不过期）。

### 业务影响

- 验证码失败计数永不清零，用户可能被永久锁定
- Redis 中积累大量永不过期的 key，造成内存泄漏

## Scope

### 修改文件（1个）

| 文件 | 说明 |
|------|------|
| `business/service/impl/UserServiceImpl.java` | 修复 `setVerificationCodeFailureCount` 方法 |

### 不在范围内

- 不修改 `RedisHelper.increase()` 的行为（影响面太大）
- 不修改其他使用 `increase` 的地方
- 不修改 `verificationCodeFailCountLimiterTime` 配置值

## Fix Design

### 修复前

```java
if (StringUtils.isBlank(failureCountStr)) {
    redisHelper.set(verificationCodeFailureCacheKey, "0",
        Long.parseLong(verificationCodeFailCountLimiterTime));
}
redisHelper.increase(verificationCodeFailureCacheKey, 1);
```

### 修复后（v2 — 含竞态条件修复）

```java
long ttl = Long.parseLong(verificationCodeFailCountLimiterTime);
if (StringUtils.isBlank(failureCountStr)) {
    // 首次失败：直接设置为1并设置过期时间，避免set("0")+increase导致TTL被清除
    redisHelper.set(verificationCodeFailureCacheKey, "1", ttl);
} else {
    // 后续失败：仅递增计数，不刷新过期时间（保留原始60分钟窗口）
    redisHelper.increase(verificationCodeFailureCacheKey, 1);
    // 防竞态：若key在get与increase之间过期，INCR会创建无TTL的key，需补设过期时间
    if (redisHelper.getExpire(verificationCodeFailureCacheKey) == -1L) {
        redisHelper.expire(verificationCodeFailureCacheKey, ttl);
    }
}
```

### 竞态条件说明

v1 修复仅解决了"首次 set + increase 导致 TTL 丢失"的问题，但存在竞态条件：

1. `get(key)` 返回非空值（key 存在）
2. 进入 `else` 分支前，key 刚好过期被 Redis 删除
3. `increase(key, 1)` 在 key 不存在时执行 `INCR`，创建 key=1 且 **TTL=-1**

v2 通过在 `increase` 后检查 `getExpire == -1` 来兜底：如果 key 是 INCR 新创建的（无 TTL），则补设过期时间。

### 关键约束

60 分钟窗口从第一次失败开始计时，后续失败次数递增**不能刷新过期时间**。这是原始设计意图，修复后必须保持。

## Risks

- 风险极低：仅修改单个方法的分支逻辑，不影响其他业务
- 已有 `NumberFormatException` + `RedisConnectionFailureException` 异常兜底

## References

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/104
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/143
